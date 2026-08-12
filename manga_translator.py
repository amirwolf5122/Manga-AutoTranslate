#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import glob
import shutil
import string
import tempfile
import time
import zipfile
import base64
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
import threading
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
import random

os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("FLAGS_onednn", "0")

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
except ImportError:
    print("خطا: کتابخانه‌های arabic_reshaper و python-bidi نصب نیستند.\n"
          "دستور: pip install arabic-reshaper python-bidi", file=sys.stderr)
    raise

try:
    from google import genai
    from google.genai import types as genai_types
    from google.genai import errors as genai_errors
except ImportError:
    print("خطا: کتابخانه google-genai نصب نیست.\nدستور: pip install google-genai",
          file=sys.stderr)
    raise

try:
    from paddleocr import PaddleOCR
except ImportError:
    print("خطا: کتابخانه paddleocr نصب نیست.\n"
          "دستور: pip install paddleocr paddlepaddle", file=sys.stderr)
    raise

_HAS_LAMA = False
try:
    from simple_lama_inpainting import SimpleLama
    _HAS_LAMA = True
except ImportError:
    pass


class GeminiQuotaExhausted(Exception):
    pass


@dataclass
class TextRegion:
    id: int
    boxes: List[np.ndarray]
    source_text: str = ""
    translated_text: str = ""
    rect: Tuple[int, int, int, int] = field(default=(0, 0, 0, 0))
    angle: float = 0.0


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
PUNCTUATION_SET = set(string.punctuation + "؟«»٪٫،؛…")
WATERMARK_PATTERNS = (
    "lunatoons", "lunatoon", "nadeinkorea", "made in korea", "madeinkorea",
    "asurascans", "asura", "flamecomics", "reaper scans", "reaperscans",
    "mangadex", "webtoon", "tapas", "toomics", "lezhin", "tappytoon",
)


class MangaTranslator:
    _LAMA_MIN_VRAM_GB = 3.5

    @staticmethod
    def _detect_paddle_gpu() -> bool:
        try:
            import paddle
            return bool(paddle.is_compiled_with_cuda() and paddle.device.get_device() is not None)
        except Exception:
            return False

    @staticmethod
    def _detect_torch_cuda() -> bool:
        try:
            import torch
            return bool(torch.cuda.is_available())
        except Exception:
            return False

    @staticmethod
    def _cuda_vram_gb() -> float:
        try:
            import torch
            if not torch.cuda.is_available():
                return 0.0
            props = torch.cuda.get_device_properties(0)
            return float(props.total_memory) / (1024 ** 3)
        except Exception:
            return 0.0

    @staticmethod
    def _cuda_device_name() -> str:
        try:
            import torch
            if torch.cuda.is_available():
                return torch.cuda.get_device_name(0)
        except Exception:
            pass
        return ""

    def _decide_lama(self, force_gpu: Optional[bool]) -> bool:
        if not _HAS_LAMA:
            return False

        has_cuda = self._detect_torch_cuda()
        vram = self._cuda_vram_gb()
        name = self._cuda_device_name()

        if force_gpu is False:
            print("[*] --cpu زده شده → پاک‌سازی با OpenCV inpaint.")
            return False

        if force_gpu is True:
            if not has_cuda:
                print("[!] --gpu زده شده ولی torch CUDA در دسترس نیست → OpenCV.")
                return False
            print(f"[*] --gpu زده شده → LaMa فعال ({name or 'CUDA'}, {vram:.1f} GB).")
            return True

        if not has_cuda:
            print("[*] CUDA پیدا نشد → پاک‌سازی با OpenCV inpaint.")
            return False

        if vram > 0 and vram < self._LAMA_MIN_VRAM_GB:
            print(f"[*] GPU هست ({name}, {vram:.1f} GB) ولی VRAM کم‌تر از "
                  f"{self._LAMA_MIN_VRAM_GB} GB → OpenCV (LaMa سنگین می‌شه).")
            return False

        print(f"[*] GPU مناسب برای LaMa پیدا شد ({name or 'CUDA'}, "
              f"{vram:.1f} GB) → LaMa inpainting فعال.")
        return True

    def __init__(
        self,
        gemini_api_key,
        ocr_langs: List[str] = None,
        model_name: str = "gemini-flash-latest",
        font_path: Optional[str] = None,
        reading_order: str = "rtl",
        gpu: Optional[bool] = None,
        group_margin: int = 5,
        inpaint_radius: int = 3,
        mask_padding: int = 3,
        pad_ratio: float = 0.06,
        min_confidence: float = 0.12,
        max_retries: int = 4,
        request_delay: float = 0.0,
        max_chunk_height: int = 3600,
        chunk_overlap: int = 300,
        img_format: str = "jpg",
        img_quality: int = 80,
        max_workers: int = 1,
        mag_ratio: float = 1.35,
        translation_temperature: float = 0.55,
        two_pass_ocr: bool = True,
        max_output_width: Optional[int] = None
    ):
        if isinstance(gemini_api_key, str):
            keys = [k.strip() for k in gemini_api_key.replace(";", ",").split(",") if k.strip()]
        else:
            keys = [k.strip() for k in gemini_api_key if k and str(k).strip()]
        random.shuffle(keys)
        if not keys:
            raise ValueError("حداقل یک کلید Gemini API لازم است.")
        self._api_keys: List[str] = keys
        self._key_index: int = 0
        self._ocr_lock = threading.Lock()
        self.model_name = model_name
        self.font_path = font_path
        self.reading_order = reading_order
        self.group_margin = group_margin
        self.inpaint_radius = inpaint_radius
        self.mask_padding = mask_padding
        self.pad_ratio = pad_ratio
        self.min_confidence = min_confidence
        self.max_retries = max_retries
        self.request_delay = request_delay
        self.max_chunk_height = max_chunk_height
        self.chunk_overlap = chunk_overlap
        self.img_format = img_format
        self.img_quality = img_quality
        self.max_workers = max(1, int(max_workers))
        self.mag_ratio = mag_ratio
        self.translation_temperature = translation_temperature
        self.two_pass_ocr = two_pass_ocr
        self.max_output_width = max_output_width

        self._name_glossary: Dict[str, str] = {}
        self._lama = None

        if not font_path or not os.path.isfile(font_path):
            raise FileNotFoundError(
                "یک فونت معتبر فارسی (ttf) با --font مشخص کنید. "
                "پیشنهاد: فونت Vazirmatn (رایگان و متن‌باز)."
            )

        if gpu is None:
            ocr_gpu = self._detect_paddle_gpu()
            if ocr_gpu:
                print("[*] GPU شناسایی شد؛ OCR روی GPU اجرا می‌شه (برای اجبار به CPU از --cpu استفاده کن).")
            else:
                print("[*] GPU برای Paddle پیدا نشد؛ OCR روی CPU اجرا می‌شه. "
                      "اگه توی Colab هستی و GPU داری، Runtime > Change runtime type رو روی GPU بذار.")
        else:
            ocr_gpu = bool(gpu)
            if ocr_gpu:
                print("[*] --gpu زده شده؛ OCR روی GPU.")
            else:
                print("[*] --cpu زده شده؛ OCR روی CPU.")

        self.use_gpu = ocr_gpu

        if not _HAS_LAMA:
            print("[!] simple-lama-inpainting نصب نیست → فقط OpenCV.\n"
                  "    نصب: pip install simple-lama-inpainting")
            self.use_lama = False
        else:
            self.use_lama = self._decide_lama(force_gpu=gpu)

        self.ocr_langs = ocr_langs or ["en"]
        print(f"[*] در حال بارگذاری مدل PaddleOCR برای زبان(های) {self.ocr_langs} (gpu={ocr_gpu}) ...")

        lang_map = {
            "en": "en",
            "fa": "fa",
            "ko": "korean",
            "ja": "japan",
            "zh": "ch",
            "fr": "french",
            "de": "german",
            "es": "spanish",
            "it": "italian",
            "pt": "portuguese",
            "ru": "russian",
            "ar": "arabic",
        }

        main_lang = "en"
        for lang in self.ocr_langs:
            if lang in lang_map:
                main_lang = lang_map[lang]
                break

        device = "gpu" if ocr_gpu else "cpu"

        ocr_kwargs = dict(
            lang=main_lang,
            show_log=False,
            text_det_thresh=0.3,
            text_det_box_thresh=0.5,
            text_det_unclip_ratio=1.6,
            det_db_thresh=0.3,
            det_db_box_thresh=0.5,
            det_db_unclip_ratio=1.6,
            max_batch_size=1,
            use_dilation=False,
        )

        try:
            self.ocr = PaddleOCR(
                use_textline_orientation=True,
                device=device,
                enable_mkldnn=False,
                **ocr_kwargs,
            )
        except TypeError:
            try:
                self.ocr = PaddleOCR(
                    use_angle_cls=True,
                    use_gpu=ocr_gpu,
                    enable_mkldnn=False,
                    **ocr_kwargs,
                )
            except TypeError:
                try:
                    self.ocr = PaddleOCR(
                        use_textline_orientation=True,
                        device=device,
                        **ocr_kwargs,
                    )
                except TypeError:
                    self.ocr = PaddleOCR(
                        use_angle_cls=True,
                        use_gpu=ocr_gpu,
                        **ocr_kwargs,
                    )

        print(f"[*] مدل PaddleOCR با زبان '{main_lang}' و دستگاه '{device}' بارگذاری شد "
              f"(MKLDNN خاموش، workers={self.max_workers}).")

        self.client = genai.Client(api_key=self._api_keys[0])
        if len(self._api_keys) > 1:
            print(f"[*] مدل ترجمه: {self.model_name} | {len(self._api_keys)} کلید API (جابه‌جایی خودکار روی سهمیه/۵۰۳/خطا)")
        else:
            print(f"[*] مدل ترجمه: {self.model_name}")

    def _get_lama(self):
        if self._lama is None and self.use_lama:
            try:
                print("    [*] بارگذاری مدل LaMa ...")
                self._lama = SimpleLama()
            except Exception as e:
                print(f"    [!] بارگذاری LaMa ناموفق بود ({e})؛ به OpenCV برمی‌گردیم.")
                self.use_lama = False
                self._lama = None
        return self._lama

    def _mask_key(self, key: str) -> str:
        if not key:
            return "(خالی)"
        if len(key) <= 10:
            return key[:3] + "..."
        return key[:6] + "..." + key[-4:]

    def _is_banned_or_invalid_key_error(self, err: Exception) -> bool:
        msg = str(err).lower()
        indicators = (
            "api key not valid",
            "api_key_invalid",
            "invalid api key",
            "permission denied",
            "permission_denied",
            "unauthenticated",
            "api key expired",
            "api_key_service_blocked",
            "consumer_suspended",
            "billing",
            "has been blocked",
            "key is invalid",
            "invalid_argument",
            "403",
            "401",
        )
        return any(ind in msg for ind in indicators)

    def _is_model_unavailable_error(self, err: Exception) -> bool:
        msg = str(err)
        return (
            "503" in msg
            or "UNAVAILABLE" in msg
            or "high demand" in msg.lower()
            or "try again later" in msg.lower()
            or "currently experiencing" in msg.lower()
        )

    def _switch_to_next_key(self, reason: str = "", cycle: bool = False) -> bool:
        if not self._api_keys:
            return False
        next_idx = self._key_index + 1
        if next_idx >= len(self._api_keys):
            if cycle and len(self._api_keys) > 1:
                next_idx = 0
            else:
                return False
        self._key_index = next_idx
        key = self._api_keys[self._key_index]
        self.client = genai.Client(api_key=key)
        extra = f" ({reason})" if reason else ""
        print(f"    [*] کلید API شماره {self._key_index + 1}/{len(self._api_keys)} فعال شد{extra}.")
        return True

    def _remove_current_key_and_switch(self, reason: str = "") -> bool:
        if not self._api_keys:
            return False
        bad_key = self._api_keys[self._key_index]
        masked = self._mask_key(bad_key)
        print(f"    [!] کلید فعلی ({masked}) حذف شد. دلیل: {reason or 'نامعتبر/بن'}")
        del self._api_keys[self._key_index]
        if not self._api_keys:
            return False
        if self._key_index >= len(self._api_keys):
            self._key_index = 0
        key = self._api_keys[self._key_index]
        self.client = genai.Client(api_key=key)
        print(f"    [*] کلید API شماره {self._key_index + 1}/{len(self._api_keys)} فعال شد.")
        return True

    @staticmethod
    def _clahe_enhance(image: np.ndarray) -> np.ndarray:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        l2 = clahe.apply(l)
        enhanced = cv2.merge((l2, a, b))
        return cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)

    def detect_text(self, image: np.ndarray) -> List[dict]:
        results = None
        with self._ocr_lock:
            last_err = None
            for attempt in range(3):
                try:
                    results = self.ocr.ocr(image)
                    break
                except RuntimeError as e:
                    last_err = e
                    msg = str(e).lower()
                    if "could not execute a primitive" in msg or "could not create a primitive" in msg:
                        print(f"    [!] OneDNN/primitive crash (تلاش {attempt + 1}/3)...")
                        time.sleep(0.4 * (attempt + 1))
                        continue
                    raise
                except Exception as e:
                    last_err = e
                    if attempt < 2:
                        time.sleep(0.3)
                        continue
                    raise
            if results is None and last_err is not None:
                raise last_err

        detections = []
        if results and results[0]:
            for line in results[0]:
                poly = np.array(line[0], dtype=np.int32)
                text = line[1][0].strip()
                conf = line[1][1]

                dx = poly[1][0] - poly[0][0]
                dy = poly[1][1] - poly[0][1]
                angle = float(np.degrees(np.arctan2(dy, dx)))

                if not text or conf < self.min_confidence or set(text).issubset(PUNCTUATION_SET):
                    continue
                if len(text) == 1 and text not in {"!", "?", "…"}:
                    continue
                if text.isdigit() and len(text) <= 5 and conf < 0.55:
                    continue
                low = text.lower().replace(" ", "").replace(".", "")
                if any(w.replace(" ", "") in low for w in WATERMARK_PATTERNS):
                    continue
                if low in {"org", "com", "net", "www"}:
                    continue

                detections.append({
                    "poly": poly,
                    "text": text,
                    "conf": conf,
                    "angle": angle
                })
        return detections

    @staticmethod
    def _dedupe_detections(detections: List[dict], iou_thresh: float = 0.4) -> List[dict]:
        def rect_of(d):
            return cv2.boundingRect(d["poly"])

        def iou(r1, r2):
            x1, y1, w1, h1 = r1
            x2, y2, w2, h2 = r2
            xi1, yi1 = max(x1, x2), max(y1, y2)
            xi2, yi2 = min(x1 + w1, x2 + w2), min(y1 + h1, y2 + h2)
            inter = max(0, xi2 - xi1) * max(0, yi2 - yi1)
            union = w1 * h1 + w2 * h2 - inter
            return inter / union if union > 0 else 0

        kept: List[dict] = []
        for d in detections:
            r = rect_of(d)
            dup_idx = None
            for i, k in enumerate(kept):
                if iou(r, rect_of(k)) > iou_thresh:
                    dup_idx = i
                    break
            if dup_idx is None:
                kept.append(d)
            elif d["conf"] > kept[dup_idx]["conf"]:
                kept[dup_idx] = d
        return kept

    def group_into_regions(self, detections: List[dict], y_offset: int = 0) -> List[TextRegion]:
        if not detections:
            return []

        n = len(detections)
        rects = []
        for d in detections:
            x, y, w, h = cv2.boundingRect(d["poly"])
            rects.append((x, y + y_offset, w, h))

        parent = list(range(n))

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        def expanded_overlap(r1, r2, margin):
            x1, y1, w1, h1 = r1
            x2, y2, w2, h2 = r2
            a = (x1 - margin, y1 - margin, x1 + w1 + margin, y1 + h1 + margin)
            b = (x2 - margin, y2 - margin, x2 + w2 + margin, y2 + h2 + margin)
            return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])

        def likely_same_bubble(r1, r2):
            x1, y1, w1, h1 = r1
            x2, y2, w2, h2 = r2
            cy1, cy2 = y1 + h1 / 2, y2 + h2 / 2
            vgap = abs(cy1 - cy2) - (h1 + h2) / 2
            if vgap > max(self.group_margin * 2, 8):
                xi1 = max(x1, x2)
                xi2 = min(x1 + w1, x2 + w2)
                h_overlap = max(0, xi2 - xi1)
                if h_overlap < 0.4 * min(w1, w2):
                    return False
            return True

        for i in range(n):
            for j in range(i + 1, n):
                if expanded_overlap(rects[i], rects[j], self.group_margin) and likely_same_bubble(rects[i], rects[j]):
                    union(i, j)

        groups = {}
        for i in range(n):
            root = find(i)
            groups.setdefault(root, []).append(i)

        regions: List[TextRegion] = []
        for gid, idxs in enumerate(groups.values()):
            if not idxs:
                continue

            boxes = []
            for i in idxs:
                if i >= len(detections):
                    continue
                poly = detections[i]["poly"].copy()
                poly[:, 1] += y_offset
                boxes.append(poly)

            if not boxes:
                continue

            xs = [rects[i][0] for i in idxs if i < len(rects)]
            ys = [rects[i][1] for i in idxs if i < len(rects)]
            xe = [rects[i][0] + rects[i][2] for i in idxs if i < len(rects)]
            ye = [rects[i][1] + rects[i][3] for i in idxs if i < len(rects)]

            if not xs or not ys or not xe or not ye:
                continue

            x0, y0, x1, y1 = min(xs), min(ys), max(xe), max(ye)

            valid_idxs = [i for i in idxs if i < len(detections) and i < len(rects)]
            idxs_sorted = sorted(valid_idxs, key=lambda i: rects[i][1])
            text = " ".join(detections[i]["text"] for i in idxs_sorted if i < len(detections))
            angles = [detections[i].get("angle", 0.0) for i in idxs_sorted if i < len(detections)]
            avg_angle = float(np.mean(angles)) if angles else 0.0
            regions.append(
                TextRegion(
                    id=gid,
                    boxes=boxes,
                    source_text=text,
                    rect=(x0, y0, x1 - x0, y1 - y0),
                    angle=avg_angle,
                )
            )

        return regions

    @staticmethod
    def _deduplicate_regions(regions: List[TextRegion], overlap_thresh: float = 0.25) -> List[TextRegion]:
        if not regions:
            return []

        def get_iou(r1, r2):
            x1, y1, w1, h1 = r1
            x2, y2, w2, h2 = r2
            xi1, yi1 = max(x1, x2), max(y1, y2)
            xi2, yi2 = min(x1 + w1, x2 + w2), min(y1 + h1, y2 + h2)
            inter_area = max(0, xi2 - xi1) * max(0, yi2 - yi1)
            r1_area = max(1, w1 * h1)
            r2_area = max(1, w2 * h2)
            union_area = r1_area + r2_area - inter_area
            return inter_area / float(union_area) if union_area > 0 else 0

        def containment(r1, r2):
            x1, y1, w1, h1 = r1
            x2, y2, w2, h2 = r2
            xi1, yi1 = max(x1, x2), max(y1, y2)
            xi2, yi2 = min(x1 + w1, x2 + w2), min(y1 + h1, y2 + h2)
            inter = max(0, xi2 - xi1) * max(0, yi2 - yi1)
            return inter / max(1, w1 * h1)

        def centers_close(r1, r2, max_dist=100):
            cx1 = r1[0] + r1[2] / 2
            cy1 = r1[1] + r1[3] / 2
            cx2 = r2[0] + r2[2] / 2
            cy2 = r2[1] + r2[3] / 2
            return abs(cx1 - cx2) < max_dist and abs(cy1 - cy2) < max_dist

        def text_similar(a: str, b: str) -> bool:
            a, b = a.strip().lower(), b.strip().lower()
            if not a or not b:
                return False
            if a == b:
                return True
            if len(a) >= 4 and (a in b or b in a):
                return True
            return False

        ordered = sorted(regions, key=lambda r: r.rect[2] * r.rect[3], reverse=True)
        unique: List[TextRegion] = []
        for r in ordered:
            is_dup = False
            for u in unique:
                iou = get_iou(r.rect, u.rect)
                c1 = containment(r.rect, u.rect)
                c2 = containment(u.rect, r.rect)
                near_same = centers_close(r.rect, u.rect) and text_similar(r.source_text, u.source_text)
                if iou > overlap_thresh or c1 > 0.5 or c2 > 0.5 or near_same:
                    is_dup = True
                    if len(r.source_text) > len(u.source_text):
                        u.source_text = r.source_text
                        u.boxes = u.boxes + r.boxes
                        x0 = min(u.rect[0], r.rect[0])
                        y0 = min(u.rect[1], r.rect[1])
                        x1 = max(u.rect[0] + u.rect[2], r.rect[0] + r.rect[2])
                        y1 = max(u.rect[1] + u.rect[3], r.rect[1] + r.rect[3])
                        u.rect = (x0, y0, x1 - x0, y1 - y0)
                    break
            if not is_dup:
                unique.append(r)
        return unique

    def _build_text_mask(self, image: np.ndarray, regions: List[TextRegion]) -> np.ndarray:
        h_img, w_img = image.shape[:2]
        text_mask = np.zeros((h_img, w_img), dtype=np.uint8)

        for region in regions:
            for poly in region.boxes:
                pts = np.array(poly, np.int32).reshape((-1, 1, 2))
                cv2.fillPoly(text_mask, [pts], 255)

        if not np.any(text_mask):
            return text_mask

        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        lower_purple = np.array([110, 15, 15])
        upper_purple = np.array([170, 255, 255])
        purple_mask = cv2.inRange(hsv, lower_purple, upper_purple)

        near_text = cv2.dilate(text_mask, np.ones((10, 10), np.uint8), iterations=1)
        purple_around_text = cv2.bitwise_and(purple_mask, near_text)

        full_target_mask = cv2.bitwise_or(text_mask, purple_around_text)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        dilated = cv2.dilate(full_target_mask, kernel, iterations=2)
        return dilated

    def clean_image(self, image: np.ndarray, regions: List[TextRegion]) -> np.ndarray:
        mask = self._build_text_mask(image, regions)
        if not np.any(mask):
            return image.copy()

        if self.use_lama:
            lama = self._get_lama()
            if lama is not None:
                try:
                    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    result_pil = lama(rgb, mask)
                    result_bgr = cv2.cvtColor(np.array(result_pil), cv2.COLOR_RGB2BGR)
                    print("  - پاکسازی با LaMa (simple-lama-inpainting) انجام شد.")
                    return result_bgr
                except Exception as e:
                    print(f"  [!] LaMa خطا داد ({e})؛ به OpenCV برمی‌گردیم.")

        cleaned = image.copy()

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        dilated = cv2.dilate(mask, kernel, iterations=2)

        cleaned = cv2.inpaint(cleaned, dilated, inpaintRadius=max(5, self.inpaint_radius + 2),
                              flags=cv2.INPAINT_TELEA)
        residual = cv2.dilate(dilated, np.ones((3, 3), np.uint8), iterations=1)
        cleaned = cv2.inpaint(cleaned, residual, inpaintRadius=3, flags=cv2.INPAINT_NS)

        print("  - پاکسازی با OpenCV inpaint (دو پاس) انجام شد.")
        return cleaned

    @staticmethod
    def _is_daily_quota_error(err: Exception) -> bool:
        msg = str(err)
        return "RESOURCE_EXHAUSTED" in msg and ("PerDay" in msg or "RequestsPerDay" in msg)

    def translate_regions(self, regions: List[TextRegion]) -> None:
        if not regions:
            return

        payload = [{"id": r.id, "text": r.source_text} for r in regions]

        system_instruction = (
            "تو مترجم مانهوا هستی. باید دیالوگ‌ها رو جوری بنویسی که انگار دو نفر دارن "
            "تو زندگی واقعی یا تو گیم با هم حرف می‌زنن — کاملاً امروزی، خودمونی و طبیعی.\n\n"

            "قانون اصلی:\n"
            "اگر جمله‌ات حس کتاب، دوبله قدیمی، ادبی یا ترجمه‌ی ماشینی بده، باید کامل عوضش کنی.\n\n"

            "بعد از ترجمهٔ هر خط این سه سؤال رو از خودت بپرس:\n"
            "1. یه آدم عادی امروزی اینجوری حرف می‌زنه؟\n"
            "2. بوی کتاب یا ترجمه می‌ده؟\n"
            "3. می‌تونم خودمونی‌تر، کوتاه‌تر و طبیعی‌ترش کنم؟\n"
            "اگر جواب حتی یکی منفی بود، دوباره بنویس.\n\n"

            "قوانین اجباری:\n"
            "• فقط فارسی محاوره‌ای و امروزی بنویس. از کلمات و ساختارهای کتابی، ادبی یا رسمی پرهیز کن.\n"
            "• جمله‌ها کوتاه، شکسته و طبیعی باشن.\n"
            "• فحش و تندی متن اصلی رو کامل و بدون سانسور نگه دار.\n"
            "• لکنت و تردید رو طبیعی بنویس (مـ... من...).\n"
            "• اسامی خاص رو ترجمه نکن، فقط نویسه‌گردانی ثابت کن و توی فیلد names برگردون.\n"
            "• خروجی فقط JSON معتبر باشه. هیچ توضیح اضافه‌ای ننویس."
        )
        user_prompt = (
            "این متن‌های استخراج‌شده از یک صفحه مانهوا هستن (ممکنه OCR ناقص باشه).\n"
            "هر خط رو به فارسی کاملاً محاوره‌ای و طبیعی (مثل حرف زدن واقعی آدم‌ها) ترجمه کن.\n\n"
            "خروجی دقیقاً با این ساختار JSON باشد:\n"
            f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
        )

        config = genai_types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            temperature=self.translation_temperature,
            response_schema={
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "id": {"type": "INTEGER"},
                        "translation": {"type": "STRING"},
                        "names": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {
                                    "source": {"type": "STRING"},
                                    "persian": {"type": "STRING"},
                                },
                                "required": ["source", "persian"],
                            },
                        },
                    },
                    "required": ["id", "translation"],
                },
            },
        )

        delay = 3.0
        last_err = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name, contents=user_prompt, config=config,
                )
                text = response.text
                if not text:
                    raise RuntimeError("پاسخ خالی از Gemini دریافت شد.")
                results = json.loads(text)

                by_id = {item["id"]: item.get("translation", "") for item in results}
                for region in regions:
                    t = by_id.get(region.id, "").strip()
                    if t:
                        region.translated_text = t

                for item in results:
                    for nm in (item.get("names") or []):
                        src = (nm.get("source") or "").strip()
                        per = (nm.get("persian") or "").strip()
                        if src and per:
                            self._name_glossary[src] = per

                missing = [r for r in regions if not r.translated_text]
                if missing and attempt < self.max_retries:
                    print(f"    [!] {len(missing)} حباب بدون ترجمه؛ تلاش مجدد...")
                    payload2 = [{"id": r.id, "text": r.source_text} for r in missing]
                    user_prompt = (
                        "متن‌های زیر از یک صفحه‌ی مانهوا/مانگا هستن. فرآیند سه‌گامی خود-اصلاحی "
                        "را اجرا کن و هر کدام را به فارسی محاوره‌ای طبیعی و وفادار به لحن شخصیت ترجمه کن:\n"
                        f"{json.dumps(payload2, ensure_ascii=False, indent=2)}"
                    )
                    regions = missing
                    continue

                print("[فاز ۳ - تفکر و ترجمه] دریافت پاسخ کامل از مدل انجام شد.")
                if self.request_delay > 0:
                    time.sleep(self.request_delay)
                return
            except genai_errors.ClientError as e:
                last_err = e
                if self._is_daily_quota_error(e):
                    print(f"    [!] سهمیه‌ی کلید {self._key_index + 1}/{len(self._api_keys)} تموم شد.")
                    if self._switch_to_next_key(reason="سهمیه روزانه"):
                        continue
                    raise GeminiQuotaExhausted(
                        f"سهمیه‌ی همه‌ی {len(self._api_keys)} کلید Gemini برای مدل «{self.model_name}» تموم شده."
                    ) from e

                if self._is_banned_or_invalid_key_error(e):
                    print(f"    [!] کلید فعلی بن یا نامعتبر تشخیص داده شد.")
                    if self._remove_current_key_and_switch(reason=str(e)[:120]):
                        continue
                    raise GeminiQuotaExhausted(
                        f"همه کلیدهای Gemini بن/نامعتبر شدن یا تموم شدن."
                    ) from e

                if self._is_model_unavailable_error(e):
                    print(f"    [!] مدل موقتاً در دسترس نیست (۵۰۳/high demand). تست کلید بعدی...")
                    if self._switch_to_next_key(reason="۵۰۳ UNAVAILABLE", cycle=True):
                        time.sleep(min(delay, 5))
                        continue
                    print(f"    [!] فقط یک کلید موجوده و ۵۰۳ گرفت؛ کمی صبر و تلاش مجدد...")
            except Exception as e:
                last_err = e
                if self._is_model_unavailable_error(e):
                    print(f"    [!] خطای در دسترس نبودن مدل. تست کلید بعدی...")
                    if self._switch_to_next_key(reason="UNAVAILABLE", cycle=True):
                        time.sleep(min(delay, 5))
                        continue
                if self._is_banned_or_invalid_key_error(e):
                    if self._remove_current_key_and_switch(reason=str(e)[:120]):
                        continue

            print(f"    [!] تلاش {attempt}/{self.max_retries} برای ترجمه ناموفق بود: {last_err}")
            if attempt < self.max_retries:
                time.sleep(delay)
                delay = min(delay * 2, 30)

        print(f"    [!] ترجمه‌ی این بخش بعد از {self.max_retries} تلاش ناموفق موند.")

    @staticmethod
    def _shape_farsi(text: str) -> str:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)

    def _load_font(self, size: int) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(self.font_path, size, layout_engine=ImageFont.Layout.BASIC)

    @staticmethod
    def _stroke_width_for(size: int) -> int:
        return max(2, size // 14)

    def _wrap_and_fit(
        self, draw: ImageDraw.ImageDraw, text: str, max_w: int, max_h: int
    ) -> Tuple[ImageFont.FreeTypeFont, List[str], int]:
        words = text.split()
        if not words:
            words = [""]

        def wrap_at(size: int):
            font = self._load_font(size)
            sw = self._stroke_width_for(size)
            lines: List[str] = []
            current = ""
            for word in words:
                candidate = f"{current} {word}".strip()
                w = draw.textbbox((0, 0), self._shape_farsi(candidate), font=font,
                                   stroke_width=sw)[2]
                if w <= max_w or not current:
                    current = candidate
                else:
                    lines.append(current)
                    current = word
            if current:
                lines.append(current)

            line_h = font.getbbox("آی", stroke_width=sw)[3] + 5
            total_h = line_h * len(lines)
            widest = max(
                (
                    draw.textbbox((0, 0), self._shape_farsi(l), font=font, stroke_width=sw)[2]
                    for l in lines
                ),
                default=0,
            )
            return font, lines, sw, total_h, widest

        smallest_attempt = None
        for size in range(52, 9, -1):
            font, lines, sw, total_h, widest = wrap_at(size)
            smallest_attempt = (font, lines, sw)
            if total_h <= max_h and widest <= max_w:
                return font, lines, sw

        return smallest_attempt

    @staticmethod
    def _pick_text_and_stroke(
        cleaned: np.ndarray, original: np.ndarray, region: TextRegion
    ) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
        h_img, w_img = original.shape[:2]
        x, y, w, h = region.rect
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(w_img, x + w), min(h_img, y + h)

        poly_mask = np.zeros((h_img, w_img), dtype=np.uint8)
        for poly in region.boxes:
            cv2.fillPoly(poly_mask, [poly], 255)

        local_mask = poly_mask[y0:y1, x0:x1]
        local_orig = original[y0:y1, x0:x1]
        local_clean = cleaned[y0:y1, x0:x1] if cleaned is not None else local_orig

        if local_orig.size == 0:
            return (15, 15, 15), (255, 255, 255)

        if local_clean.size > 0:
            bg_gray = float(np.median(cv2.cvtColor(local_clean, cv2.COLOR_BGR2GRAY)))
        else:
            bg_gray = 128.0

        orig_gray = cv2.cvtColor(local_orig, cv2.COLOR_BGR2GRAY).astype(np.float32)
        if bg_gray < 128:
            ink_m = (orig_gray > bg_gray + 20) & (local_mask > 0)
        else:
            ink_m = (orig_gray < bg_gray - 20) & (local_mask > 0)

        ink_pixels = local_orig[ink_m]

        if len(ink_pixels) >= 8:
            bgr = np.median(ink_pixels, axis=0)
            r, g, b = int(bgr[2]), int(bgr[1]), int(bgr[0])

            mx, mn = max(r, g, b), min(r, g, b)
            saturation = mx - mn
            lum = 0.299 * r + 0.587 * g + 0.114 * b

            if saturation < 25:
                if bg_gray >= 140:
                    text_rgb = (18, 18, 18)
                    stroke_rgb = (255, 255, 255)
                else:
                    text_rgb = (245, 245, 245)
                    stroke_rgb = (10, 10, 10)
            else:
                text_rgb = (r, g, b)
                if lum >= 140:
                    stroke_rgb = (20, 20, 20)
                else:
                    stroke_rgb = (255, 255, 255)
        else:
            if bg_gray >= 140:
                text_rgb, stroke_rgb = (18, 18, 18), (255, 255, 255)
            else:
                text_rgb, stroke_rgb = (245, 245, 245), (10, 10, 10)

        return text_rgb, stroke_rgb

    def render_translations(self, image: np.ndarray, regions: List[TextRegion],
                            original_image: np.ndarray) -> np.ndarray:
        pil_img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)

        for region in regions:
            if not region.translated_text:
                continue

            x, y, w, h = region.rect
            pad = max(3, int(min(w, h) * 0.05))
            box_w = max(12, w - 2 * pad)
            box_h = max(12, h - 2 * pad)

            font, lines, sw = self._wrap_and_fit(draw, region.translated_text, box_w, box_h)
            text_rgb, stroke_rgb = self._pick_text_and_stroke(image, original_image, region)

            angle = getattr(region, "angle", 0.0)

            if abs(angle) < 8:
                line_h = font.getbbox("آی", stroke_width=sw)[3] + 5
                total_h = line_h * len(lines)
                start_y = y + pad + max(0, (box_h - total_h) // 2)

                for i, line in enumerate(lines):
                    shaped = self._shape_farsi(line)
                    line_w = draw.textbbox((0, 0), shaped, font=font, stroke_width=sw)[2]
                    line_x = x + pad + max(0, (box_w - line_w) // 2)
                    line_y = start_y + i * line_h
                    draw.text(
                        (line_x, line_y),
                        shaped,
                        font=font,
                        fill=text_rgb,
                        stroke_width=sw,
                        stroke_fill=stroke_rgb,
                    )
            else:
                line_h = font.getbbox("آی", stroke_width=sw)[3] + 6
                tmp_h = line_h * len(lines) + 30
                tmp_w = 0
                for line in lines:
                    shaped = self._shape_farsi(line)
                    lw = draw.textbbox((0, 0), shaped, font=font, stroke_width=sw)[2]
                    tmp_w = max(tmp_w, lw)
                tmp_w += 40

                tmp = Image.new("RGBA", (tmp_w, tmp_h), (0, 0, 0, 0))
                tmp_draw = ImageDraw.Draw(tmp)

                for i, line in enumerate(lines):
                    shaped = self._shape_farsi(line)
                    line_w = tmp_draw.textbbox((0, 0), shaped, font=font, stroke_width=sw)[2]
                    tx = (tmp_w - line_w) // 2
                    ty = 15 + i * line_h
                    tmp_draw.text(
                        (tx, ty),
                        shaped,
                        font=font,
                        fill=text_rgb + (255,),
                        stroke_width=sw,
                        stroke_fill=stroke_rgb + (255,),
                    )

                rotated = tmp.rotate(-angle, expand=True, resample=Image.BICUBIC)
                cx = x + w // 2
                cy = y + h // 2
                rw, rh = rotated.size
                paste_x = int(cx - rw / 2)
                paste_y = int(cy - rh / 2)

                pil_img.paste(rotated, (paste_x, paste_y), rotated)

        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    def _process_chunk_worker(self, args_tuple) -> List[TextRegion]:
        idx, y0, y1, image = args_tuple
        print(f"    [>] OCR تیکه‌ی {idx + 1} (ردیف {y0} تا {y1})")
        piece = image[y0:y1, :]

        detections = self.detect_text(piece)

        if self.two_pass_ocr:
            enhanced = self._clahe_enhance(piece)
            detections += self.detect_text(enhanced)
            inverted = cv2.bitwise_not(piece)
            detections += self.detect_text(inverted)
            gray = cv2.cvtColor(piece, cv2.COLOR_BGR2GRAY)
            _, bw = cv2.threshold(gray, 160, 255, cv2.THRESH_BINARY)
            if float(np.mean(bw)) < 127:
                bw = cv2.bitwise_not(bw)
            bw = cv2.dilate(bw, np.ones((2, 2), np.uint8), iterations=1)
            bw_bgr = cv2.cvtColor(bw, cv2.COLOR_GRAY2BGR)
            detections += self.detect_text(bw_bgr)
            detections = self._dedupe_detections(detections)

        return self.group_into_regions(detections, y_offset=y0)

    def process_core(self, image: np.ndarray) -> np.ndarray:
        h, w = image.shape[:2]

        chunk_ranges = []
        y = 0
        while y < h:
            y_end = min(y + self.max_chunk_height, h)
            chunk_ranges.append((y, y_end))
            if y_end == h:
                break
            y = y_end - self.chunk_overlap

        all_raw_regions: List[TextRegion] = []

        tasks = [(i, r[0], r[1], image) for i, r in enumerate(chunk_ranges)]

        if self.max_workers <= 1 or len(tasks) <= 1:
            for t in tasks:
                all_raw_regions.extend(self._process_chunk_worker(t))
        else:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                results = executor.map(self._process_chunk_worker, tasks)
                for res in results:
                    all_raw_regions.extend(res)

        unique_regions = self._deduplicate_regions(all_raw_regions)
        if self.reading_order == "rtl":
            unique_regions.sort(key=lambda r: (r.rect[1] // 80, -(r.rect[0] + r.rect[2])))
        else:
            unique_regions.sort(key=lambda r: (r.rect[1] // 80, r.rect[0]))

        for idx, r in enumerate(unique_regions):
            r.id = idx

        if not unique_regions:
            print("    [!] هیچ متن/حبابی یافت نشد.")
            return image

        print(f"[فاز ۱ - OCR] انجام شد. مجموع {len(unique_regions)} بلوک متن استخراج گردید.")
        for r in unique_regions:
            print(f"  [{r.id}] {r.source_text}")

        raw_image_copy = image.copy()

        print("[فاز ۳ - تفکر و ترجمه] ارسال درخواست به Gemini (با فرآیند خود-اصلاحی)...")
        self.translate_regions(unique_regions)

        translated_regions = [r for r in unique_regions if r.translated_text]
        if not translated_regions:
            print("    [!] ترجمه‌ی هیچ حبابی موفق نبود؛ تصویر بدون تغییر برمی‌گرده.")
            return image

        print("--- بررسی نهایی نتایج ترجمه ---")
        for r in translated_regions:
            print(f"  EN: {r.source_text}")
            print(f"  FA: {r.translated_text}")

        print("[فاز ۴ - رندر نهایی] شروع جایگذاری و ذخیره...")
        cleaned_image = self.clean_image(image, translated_regions)
        final_image = self.render_translations(cleaned_image, translated_regions, raw_image_copy)
        print("  - رندر متن فارسی روی تصویر موفق بود.")

        return final_image

    @staticmethod
    def _is_mostly_blank(image: np.ndarray, std_thresh: float = 12.0, unique_thresh: int = 24) -> bool:
        if image is None or image.size == 0:
            return True
        h, w = image.shape[:2]
        if h < 40 or w < 40:
            return True
        y0, y1 = int(h * 0.15), int(h * 0.85)
        x0, x1 = int(w * 0.1), int(w * 0.9)
        crop = image[y0:y1, x0:x1]
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
        if float(np.std(gray)) < std_thresh:
            return True
        hist = cv2.calcHist([gray], [0], None, [64], [0, 256]).flatten()
        if int(np.count_nonzero(hist > (gray.size * 0.002))) < unique_thresh and float(np.std(gray)) < 22:
            return True
        return False

    def process_image_file(self, in_path: str) -> Optional[np.ndarray]:
        image = cv2.imread(in_path)
        if image is None:
            raise ValueError(f"تصویر قابل خواندن نیست: {in_path}")
        basename = os.path.basename(in_path)
        print(f"-------------------- شروع عملیات جدید --------------------")
        if self._is_mostly_blank(image):
            print(f"- رد شد (صفحه تقریباً خالی/کارت پایان): '{basename}'")
            return None
        print(f"[فاز ۱ - OCR] شروع استخراج متن...")
        print(f"- پردازش '{basename}'...")
        return self.process_core(image)

    @staticmethod
    def _is_url(s: str) -> bool:
        return s.lower().startswith("http://") or s.lower().startswith("https://")

    @staticmethod
    def _normalize_image_url(url: str) -> str:
        if "github.com/" in url and "/blob/" in url:
            url = url.replace("github.com/", "raw.githubusercontent.com/").replace("/blob/", "/")
        return url

    @staticmethod
    def _is_junk_image_url(u: str) -> bool:
        low = u.lower()
        junk_parts = (
            "logo", "loading", "spinner", "placeholder", "avatar", "icon",
            "credits", "credit-", "watermark", "banner", "ads/", "/ad.",
            "radio", "vline", "favicon", "sprite", "emoji", "badge",
            "/static/", "data:image", ".svg", "tracking", "pixel",
            "1x1", "blank.", "transparent", "spacer",
        )
        if any(p in low for p in junk_parts):
            return True
        path = low.split("?")[0]
        if path.endswith((".js", ".css", ".html", ".php", ".json", ".xml")):
            return True
        return False

    @staticmethod
    def _extract_src_candidates(img_tag) -> List[str]:
        attrs = (
            "src", "data-src", "data-original", "data-lazy-src", "data-lazy",
            "data-url", "data-image", "data-full", "data-srcset", "srcset",
            "data-pagespeed-lazy-src", "data-orig-src",
        )
        found = []
        for a in attrs:
            val = img_tag.get(a)
            if not val:
                continue
            if "srcset" in a:
                for part in val.split(","):
                    part = part.strip().split()[0] if part.strip() else ""
                    if part:
                        found.append(part)
            else:
                found.append(val)
        return found

    @staticmethod
    def _natural_sort_key(path: str):
        name = os.path.basename(path)
        return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", name)]

    @staticmethod
    def _try_extend_sequential(urls: List[str], headers: dict, max_extra: int = 80) -> List[str]:
        import requests

        if len(urls) < 2:
            return urls

        pattern = re.compile(
            r"^(?P<prefix>.+/)(?P<num>\d+)(?P<suffix>\.(?:jpe?g|png|webp|gif))(?:\?.*)?$",
            re.I,
        )
        parsed = []
        for u in urls:
            m = pattern.match(u.split("?")[0])
            if m:
                parsed.append((int(m.group("num")), m.group("prefix"), m.group("suffix"), u))

        if len(parsed) < 2:
            return urls

        parsed.sort(key=lambda x: x[0])
        nums = [p[0] for p in parsed]
        if nums[-1] - nums[0] + 1 > len(nums) * 2:
            return urls

        prefix, suffix = parsed[0][1], parsed[0][2]
        if not all(p[1] == prefix and p[2].lower() == suffix.lower() for p in parsed):
            return urls

        end = max(nums)
        existing = set(nums)
        extra = []
        consecutive_fail = 0
        for n in range(end + 1, end + 1 + max_extra):
            if n in existing:
                consecutive_fail = 0
                continue
            candidate = f"{prefix}{n}{suffix}"
            try:
                r = requests.head(candidate, headers=headers, timeout=12, allow_redirects=True)
                if r.status_code == 200 and (r.headers.get("Content-Type") or "").startswith("image/"):
                    extra.append(candidate)
                    consecutive_fail = 0
                else:
                    consecutive_fail += 1
            except Exception:
                consecutive_fail += 1
            if consecutive_fail >= 3:
                break

        if extra:
            print(f"    [+] {len(extra)} تصویر اضافی با الگوی شماره‌ای پیدا شد.")
            return urls + extra
        return urls

    @staticmethod
    def _download_images_from_url(url: str, dest_dir: str) -> List[str]:
        import requests
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin, urlparse

        os.makedirs(dest_dir, exist_ok=True)
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": url,
        }
        url = MangaTranslator._normalize_image_url(url)

        def _save_bytes(content: bytes, index: int, hint_url: str = "") -> Optional[str]:
            ext = os.path.splitext(urlparse(hint_url or url).path)[1].lower()
            if ext not in IMAGE_EXTS:
                if content[:3] == b"\xff\xd8\xff":
                    ext = ".jpg"
                elif content[:8] == b"\x89PNG\r\n\x1a\n":
                    ext = ".png"
                elif content[:4] == b"RIFF" and content[8:12] == b"WEBP":
                    ext = ".webp"
                else:
                    ext = ".jpg"
            out_file = os.path.join(dest_dir, f"page_{index:03d}{ext}")
            with open(out_file, "wb") as f:
                f.write(content)
            arr = np.frombuffer(content, dtype=np.uint8)
            test_img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if test_img is None:
                try:
                    os.remove(out_file)
                except OSError:
                    pass
                return None
            h, w = test_img.shape[:2]
            if min(h, w) < 80 or max(h, w) < 200:
                try:
                    os.remove(out_file)
                except OSError:
                    pass
                return None
            return out_file

        path_ext = os.path.splitext(urlparse(url).path)[1].lower()
        resp = requests.get(url, headers=headers, timeout=60, stream=True)
        resp.raise_for_status()
        content_type = (resp.headers.get("Content-Type") or "").lower()
        is_direct_image = (
            path_ext in IMAGE_EXTS
            or content_type.startswith("image/")
        )

        if is_direct_image:
            content = resp.content
            saved_path = _save_bytes(content, 1, url)
            if saved_path:
                print(f"    1 تصویر مستقیم از لینک دانلود شد.")
                return [saved_path]
            raise ValueError(f"محتوای لینک تصویر معتبر نبود: {url}")

        soup = BeautifulSoup(resp.content, "html.parser")
        img_urls, seen = [], set()

        for img in soup.find_all("img"):
            for src in MangaTranslator._extract_src_candidates(img):
                if not src or src.startswith("data:"):
                    continue
                full_url = MangaTranslator._normalize_image_url(urljoin(url, src))
                if full_url in seen:
                    continue
                if MangaTranslator._is_junk_image_url(full_url):
                    continue
                seen.add(full_url)
                img_urls.append(full_url)

        for a in soup.find_all("a", href=True):
            href = a["href"]
            low = href.lower().split("?")[0]
            if any(low.endswith(e) for e in (".jpg", ".jpeg", ".png", ".webp")):
                full_url = MangaTranslator._normalize_image_url(urljoin(url, href))
                if full_url not in seen and not MangaTranslator._is_junk_image_url(full_url):
                    seen.add(full_url)
                    img_urls.append(full_url)

        if not img_urls:
            print("    [!] هیچ تگ تصویری معتبری در صفحه پیدا نشد.")
            return []

        img_urls = MangaTranslator._try_extend_sequential(img_urls, headers)

        def _priority(u: str) -> int:
            low = u.lower()
            if any(k in low for k in ("/chapter", "/chapters/", "/comic/", "/manga/", "/pages/")):
                return 0
            if re.search(r"/\d+\.(jpe?g|png|webp)$", low):
                return 1
            return 2

        img_urls = sorted(set(img_urls), key=lambda u: (_priority(u), u))

        saved = []
        for img_url in img_urls:
            try:
                r = requests.get(img_url, headers=headers, timeout=60)
                r.raise_for_status()
            except Exception as e:
                print(f"    [!] رد شد ({img_url[:90]}…): {e}")
                continue
            path = _save_bytes(r.content, len(saved) + 1, img_url)
            if path:
                saved.append(path)

        saved = sorted(saved, key=MangaTranslator._natural_sort_key)
        print(f"    {len(saved)} تصویر از {url} دانلود شد.")
        return saved

    @staticmethod
    def _auto_output_path(input_path: str, output_spec: str) -> str:
        spec = (output_spec or "").strip()
        is_ext_only = (
            spec.startswith(".")
            and "/" not in spec
            and "\\" not in spec
            and re.fullmatch(r"\.(pdf|zip|html)", spec, re.I) is not None
        )
        if not is_ext_only:
            return output_spec

        ext = spec.lower()
        if MangaTranslator._is_url(input_path):
            from urllib.parse import urlparse, unquote
            path = unquote(urlparse(input_path).path).strip("/")
            parts = [p for p in path.split("/") if p]
            base = "chapter"
            if not parts:
                base = "chapter"
            elif "chapter" in [p.lower() for p in parts]:
                low_parts = [p.lower() for p in parts]
                try:
                    idx = low_parts.index("chapter")
                    name = parts[idx - 1] if idx > 0 else "chapter"
                    num = parts[idx + 1] if idx + 1 < len(parts) else ""
                    num = re.sub(r"[^\w\-]", "", num.split("?")[0])
                    base = f"{name}-{num}" if num else name
                except ValueError:
                    base = parts[-1]
            else:
                base = parts[-1]
            base = re.sub(r"[^\w\-.]+", "-", base).strip("-._")
            if not base:
                base = "chapter"
        else:
            raw = input_path.rstrip("/\\")
            base = os.path.splitext(os.path.basename(raw))[0] or "output"
            base = re.sub(r"[^\w\-.]+", "-", base).strip("-._") or "output"

        return base + ext

    @staticmethod
    def _extract_zip(zip_path: str, dest_dir: str) -> List[str]:
        os.makedirs(dest_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(dest_dir)
        files = []
        for root, _, names in os.walk(dest_dir):
            for name in names:
                if os.path.splitext(name)[1].lower() in IMAGE_EXTS:
                    files.append(os.path.join(root, name))
        return sorted(files, key=MangaTranslator._natural_sort_key)

    @staticmethod
    def _pdf_to_images(pdf_path: str, dest_dir: str) -> List[str]:
        import fitz
        os.makedirs(dest_dir, exist_ok=True)
        doc = fitz.open(pdf_path)
        zoom = 200 / 72
        matrix = fitz.Matrix(zoom, zoom)
        files = []
        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=matrix)
            out_file = os.path.join(dest_dir, f"page_{i + 1:03d}.png")
            pix.save(out_file)
            files.append(out_file)
        doc.close()
        return files

    @staticmethod
    def _save_as_pdf(image_paths_in_order: List[str], out_path: str) -> None:
        images = [Image.open(p).convert("RGB") for p in image_paths_in_order]
        if not images:
            raise ValueError("هیچ تصویری برای ساخت PDF وجود نداره.")
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        images[0].save(out_path, save_all=True, append_images=images[1:])

    @staticmethod
    def _save_as_zip(folder: str, out_path: str) -> None:
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for name in sorted(os.listdir(folder), key=MangaTranslator._natural_sort_key):
                zf.write(os.path.join(folder, name), arcname=name)

    def _write_image(self, image: np.ndarray, path: str) -> None:
        ext = os.path.splitext(path)[1].lower()

        out_image = image
        if self.max_output_width and self.max_output_width > 0:
            target_w = int(self.max_output_width)
            if out_image.shape[1] != target_w:
                scale = target_w / float(out_image.shape[1])
                new_h = max(1, int(round(out_image.shape[0] * scale)))
                interp = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC
                out_image = cv2.resize(out_image, (target_w, new_h), interpolation=interp)

        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

        if ext == ".webp":
            rgb = cv2.cvtColor(out_image, cv2.COLOR_BGR2RGB)
            Image.fromarray(rgb).save(path, format="WEBP", quality=self.img_quality, method=6)
        elif ext in (".jpg", ".jpeg"):
            cv2.imwrite(
                path, out_image,
                [cv2.IMWRITE_JPEG_QUALITY, self.img_quality, cv2.IMWRITE_JPEG_OPTIMIZE, 1],
            )
        elif ext == ".png":
            cv2.imwrite(path, out_image, [cv2.IMWRITE_PNG_COMPRESSION, 9])
        else:
            cv2.imwrite(path, out_image)

    @staticmethod
    def _save_as_html(image_paths: List[str], out_path: str, title: str = "مانهوا ترجمه شده") -> None:
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

        css = """
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { background: #0a0a0b; }
.strip {
  max-width: 900px;
  margin: 0 auto;
  background: #000;
}
.strip img {
  width: 100%;
  height: auto;
  display: block;
  vertical-align: top;
}
"""

        parts = [
            "<!DOCTYPE html>",
            '<html lang="fa" dir="rtl">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            '<meta name="color-scheme" content="dark">',
            '<meta name="theme-color" content="#0a0a0b">',
            f"<title>{title}</title>",
            "<style>",
            css.strip(),
            "</style>",
            "</head>",
            "<body>",
            '<div class="strip">',
        ]

        for i, p in enumerate(image_paths, 1):
            with open(p, "rb") as f:
                data = f.read()
            ext = os.path.splitext(p)[1].lower().lstrip(".")
            mime = {
                "jpg": "image/jpeg",
                "jpeg": "image/jpeg",
                "png": "image/png",
                "webp": "image/webp",
            }.get(ext, "image/jpeg")
            b64 = base64.b64encode(data).decode("ascii")
            parts.append(
                f'<img src="data:{mime};base64,{b64}" alt="" '
                f'loading="{"eager" if i <= 2 else "lazy"}" decoding="async">'
            )

        parts.append("</div>")
        parts.append("</body></html>")

        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(parts))

    @staticmethod
    def _cleanup_previous_artifacts(output_path: str, keep_outputs: bool = False) -> None:
        abs_out = os.path.abspath(output_path)
        parent = os.path.dirname(abs_out) or "."
        current_base = os.path.basename(abs_out)
        current_cache = abs_out + ".cache"
        current_stem = os.path.splitext(current_base)[0]

        if not os.path.isdir(parent):
            return

        series_prefix = current_stem
        for marker in ("-chapter-", "_chapter_", "-ch-", "_ch-"):
            if marker in current_stem.lower():
                idx = current_stem.lower().index(marker)
                series_prefix = current_stem[:idx]
                break
        if len(series_prefix) < 3:
            series_prefix = current_stem[: max(4, len(current_stem) // 2)]

        removed = 0
        for name in os.listdir(parent):
            path = os.path.join(parent, name)

            if name.endswith(".cache") and os.path.isdir(path):
                if os.path.abspath(path) != os.path.abspath(current_cache):
                    print(f"[*] پاک کردن کش قدیمی: {name}")
                    shutil.rmtree(path, ignore_errors=True)
                    removed += 1
                continue

            if keep_outputs:
                continue

            low = name.lower()
            if not low.endswith((".pdf", ".html", ".zip")):
                continue
            if os.path.abspath(path) == abs_out:
                continue
            if not os.path.isfile(path):
                continue

            stem = os.path.splitext(name)[0]
            if series_prefix and series_prefix.lower() in stem.lower():
                try:
                    print(f"[*] پاک کردن خروجی قدیمی: {name}")
                    os.remove(path)
                    removed += 1
                except OSError as e:
                    print(f"    [!] نتوانست پاک شود ({name}): {e}")

        if removed:
            print(f"[*] {removed} مورد قدیمی پاک شد.")
        else:
            print("[*] مورد قدیمی برای پاک کردن پیدا نشد.")

    def run(self, input_path: str, output_path: str, resume: bool = True,
            clean_old: bool = True) -> None:
        if clean_old:
            self._cleanup_previous_artifacts(output_path, keep_outputs=False)

        cache_dir = output_path + ".cache"
        if not resume:
            shutil.rmtree(cache_dir, ignore_errors=True)

        src_dir = os.path.join(cache_dir, "src")
        out_dir = os.path.join(cache_dir, "out")
        os.makedirs(out_dir, exist_ok=True)

        if self._is_url(input_path):
            print(f"[*] دانلود تصاویر از لینک: {input_path}")
            image_files = self._download_images_from_url(input_path, src_dir)
        elif input_path.lower().endswith(".zip"):
            print(f"[*] استخراج فایل zip: {input_path}")
            image_files = self._extract_zip(input_path, src_dir)
        elif input_path.lower().endswith(".pdf"):
            print(f"[*] استخراج صفحات از PDF: {input_path}")
            image_files = self._pdf_to_images(input_path, src_dir)
        elif os.path.isdir(input_path):
            image_files = sorted(
                (f for f in glob.glob(os.path.join(input_path, "*"))
                 if os.path.splitext(f)[1].lower() in IMAGE_EXTS),
                key=MangaTranslator._natural_sort_key,
            )
        elif os.path.isfile(input_path) and os.path.splitext(input_path)[1].lower() in IMAGE_EXTS:
            image_files = [input_path]
        else:
            raise ValueError(f"نوع ورودی پشتیبانی نمی‌شه: {input_path}")

        if not image_files:
            print("[!] هیچ تصویری برای پردازش پیدا نشد.", file=sys.stderr)
            return

        processed_files = []
        skipped = 0
        page_ext = "." + self.img_format if self.img_format != "jpg" else ".jpg"

        for f in image_files:
            out_file = os.path.join(out_dir, os.path.splitext(os.path.basename(f))[0] + page_ext)

            if resume and os.path.isfile(out_file):
                processed_files.append(out_file)
                skipped += 1
                continue

            try:
                result = self.process_image_file(f)
            except GeminiQuotaExhausted as e:
                print(f"\n[!] {e}")
                print(f"    {len(processed_files)}/{len(image_files)} صفحه تا الان با موفقیت پردازش شده.")
                break
            except Exception as e:
                print(f"    [!] خطا در پردازش {os.path.basename(f)}: {e}", file=sys.stderr)
                continue

            if result is None:
                continue

            self._write_image(result, out_file)
            processed_files.append(out_file)

        if skipped:
            print(f"[*] {skipped} صفحه از قبل توی کش بود و دوباره پردازش نشد (resume فعاله).")

        if not processed_files:
            print("[!] هیچ خروجی‌ای تولید نشد.", file=sys.stderr)
            return

        out_ext = os.path.splitext(output_path)[1].lower()
        if out_ext == ".pdf":
            self._save_as_pdf(processed_files, output_path)
            print(f"[✓] PDF نهایی ذخیره شد در: {output_path}")
        elif out_ext == ".zip":
            self._save_as_zip(out_dir, output_path)
            print(f"[✓] فایل zip نهایی ذخیره شد در: {output_path}")
        elif out_ext == ".html":
            self._save_as_html(processed_files, output_path)
            print(f"[✓] HTML نهایی (با تصاویر base64) ذخیره شد در: {output_path}")
        elif len(processed_files) == 1 and out_ext in IMAGE_EXTS:
            img = cv2.imread(processed_files[0])
            self._write_image(img, output_path)
            print(f"[✓] ذخیره شد در: {output_path}")
        else:
            os.makedirs(output_path, exist_ok=True)
            for f in processed_files:
                shutil.copy(f, os.path.join(output_path, os.path.basename(f)))
            print(f"[✓] {len(processed_files)} تصویر در پوشه‌ی {output_path} ذخیره شد.")
            html_path = output_path.rstrip("/\\") + ".html"
            try:
                self._save_as_html(processed_files, html_path)
                print(f"[✓] HTML همراه هم ساخته شد: {html_path}")
            except Exception as e:
                print(f"    [!] ساخت HTML همراه ناموفق: {e}")


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="مترجم خودکار مانگا با OCR + Gemini")
    p.add_argument("-i", "--input", required=True)
    p.add_argument("-o", "--output", required=True,
                   help="مسیر خروجی: پوشه، فایل کامل، یا فقط پسوند (.pdf / .zip / .html) "
                        "که در این صورت نام از روی ورودی ساخته می‌شود")
    p.add_argument("--api-key", action="append", default=None,
                   help="کلید Gemini API. می‌تونی چند بار بنویسی یا با کاما جدا کنی. "
                        "اگه یکی تموم شد خودکار می‌ره بعدی. "
                        "یا env: GEMINI_API_KEY=key1,key2,key3")
    p.add_argument("--font", required=True)
    p.add_argument("--ocr-lang", nargs="+", default=["en"],
                   help="زبان‌های OCR. برای نسخه‌ی انگلیسی: en | کره‌ای: ko en | ژاپنی: ja en")
    p.add_argument("--model", default="gemini-flash-latest",
                   help="مدل Gemini برای ترجمه. پیش‌فرض gemini-flash-latest برای لحن "
                        "محاوره‌ای‌تر و طبیعی‌تره؛ اگه به کوتای رایگان بیشتری نیاز داری "
                        "(به قیمت لحن رسمی‌تر) با --model gemini-flash-lite-latest عوضش کن.")
    p.add_argument("--reading-order", choices=["rtl", "ltr"], default="rtl")
    p.add_argument("--gpu", dest="gpu", action="store_true", default=None,
                   help="اجبار به استفاده از GPU (پیش‌فرض: خودکار تشخیص داده می‌شه)")
    p.add_argument("--cpu", dest="gpu", action="store_false",
                   help="اجبار به استفاده از CPU حتی اگه GPU در دسترس باشه")
    p.add_argument("--no-resume", action="store_true")
    p.add_argument("--keep-old", action="store_true",
                   help="کش و خروجی فصل‌های قبلی را پاک نکن (پیش‌فرض: پاک می‌شوند)")
    p.add_argument("--request-delay", type=float, default=0.0)
    p.add_argument("--max-retries", type=int, default=4)
    p.add_argument("--max-chunk-height", type=int, default=3600)
    p.add_argument("--img-format", choices=["webp", "png", "jpg"], default="jpg")
    p.add_argument("--quality", type=int, default=80,
                   help="کیفیت فشرده‌سازی خروجی (۱-۱۰۰)؛ برای حجم کمتر عدد رو پایین‌تر بیار")
    p.add_argument("--max-width", type=int, default=900,
                   help="عرض ثابت همه تصاویر خروجی (پیکسل). پیش‌فرض ۹۰۰. "
                        "برای غیرفعال کردن: --max-width 0")
    p.add_argument("--min-confidence", type=float, default=0.12)
    p.add_argument("--workers", type=int, default=1,
                   help="تعداد تیکه‌های موازی برای OCR (پیش‌فرض: ۱ برای پایداری روی CPU)")
    p.add_argument("--mask-padding", type=int, default=3,
                   help="حداقل حاشیه‌ی ثابت (پیکسل) دور حروف هنگام پاک‌سازی")
    p.add_argument("--pad-ratio", type=float, default=0.06,
                   help="حاشیه‌ی نسبی دور حروف؛ کم نگه دار تا شکل حباب خراب نشه")
    p.add_argument("--inpaint-radius", type=int, default=3,
                   help="شعاع inpaint برای حالت OpenCV")
    p.add_argument("--mag-ratio", type=float, default=1.35,
                   help="ضریب بزرگ‌نمایی EasyOCR؛ بالاتر = متن ریزتر ولی کندتر")
    p.add_argument("--no-two-pass-ocr", action="store_true",
                   help="غیرفعال کردن پاس دوم OCR (سریع‌تر، دقت کمتر)")
    p.add_argument("--temperature", type=float, default=0.55,
                   help="دمای مدل Gemini برای ترجمه؛ پایین‌تر = ثابت‌تر و یکدست‌تر")
    return p


def main():
    args = build_arg_parser().parse_args()

    keys: List[str] = []
    if args.api_key:
        for item in args.api_key:
            keys.extend(k.strip() for k in item.replace(";", ",").split(",") if k.strip())
    env_key = os.environ.get("GEMINI_API_KEY", "")
    if env_key:
        keys.extend(k.strip() for k in env_key.replace(";", ",").split(",") if k.strip())
    seen = set()
    unique_keys = []
    for k in keys:
        if k not in seen:
            seen.add(k)
            unique_keys.append(k)

    if not unique_keys:
        print("خطا: حداقل یک کلید Gemini API لازم است (--api-key یا GEMINI_API_KEY).", file=sys.stderr)
        sys.exit(1)

    output_path = MangaTranslator._auto_output_path(args.input, args.output)
    if output_path != args.output:
        print(f"[*] نام خروجی خودکار: {output_path}")

    translator = MangaTranslator(
        gemini_api_key=unique_keys,
        ocr_langs=args.ocr_lang,
        model_name=args.model,
        font_path=args.font,
        reading_order=args.reading_order,
        gpu=args.gpu,
        max_retries=args.max_retries,
        request_delay=args.request_delay,
        max_chunk_height=args.max_chunk_height,
        img_format=args.img_format,
        img_quality=args.quality,
        min_confidence=args.min_confidence,
        max_workers=args.workers,
        mask_padding=args.mask_padding,
        pad_ratio=args.pad_ratio,
        inpaint_radius=args.inpaint_radius,
        mag_ratio=args.mag_ratio,
        two_pass_ocr=not args.no_two_pass_ocr,
        translation_temperature=args.temperature,
        max_output_width=(args.max_width or None),
    )
    translator.run(
        args.input,
        output_path,
        resume=not args.no_resume,
        clean_old=not args.keep_old,
    )


if __name__ == "__main__":
    main()
