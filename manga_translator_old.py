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


_HAS_GEMINI = False
try:
    from google import genai
    from google.genai import types as genai_types
    from google.genai import errors as genai_errors
    _HAS_GEMINI = True
except ImportError:
    genai = None
    genai_types = None
    genai_errors = None

_HAS_OPENAI = False
try:
    from openai import OpenAI
    _HAS_OPENAI = True
except ImportError:
    OpenAI = None

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


PROVIDER_PRESETS = {
    "gemini": {
        "type": "gemini",
        "default_model": "gemini-flash-latest",
        "env_key": "GEMINI_API_KEY",
    },
    "openai": {
        "type": "openai",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "env_key": "OPENAI_API_KEY",
    },
    "chatgpt": {  
        "type": "openai",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "env_key": "OPENAI_API_KEY",
    },
    "deepseek": {
        "type": "openai",
        "base_url": "https://api.deepseek.com",
        "default_model": "deepseek-chat",
        "env_key": "DEEPSEEK_API_KEY",
    },
    "groq": {
        "type": "openai",
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "env_key": "GROQ_API_KEY",
    },
    "xai": {
        "type": "openai",
        "base_url": "https://api.x.ai/v1",
        "default_model": "grok-2-latest",
        "env_key": "XAI_API_KEY",
    },
    "grok": {  
        "type": "openai",
        "base_url": "https://api.x.ai/v1",
        "default_model": "grok-2-latest",
        "env_key": "XAI_API_KEY",
    },
    "together": {
        "type": "openai",
        "base_url": "https://api.together.xyz/v1",
        "default_model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "env_key": "TOGETHER_API_KEY",
    },
    "openrouter": {
        "type": "openai",
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "google/gemini-2.0-flash-001",
        "env_key": "OPENROUTER_API_KEY",
    },
    "ollama": {
        "type": "openai",
        "base_url": "http://localhost:11434/v1",
        "default_model": "llama3.2",
        "env_key": "OLLAMA_API_KEY",  
    },
}


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
    kind: str = "dialogue"


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
PUNCTUATION_SET = set(string.punctuation + "؟«»٪٫،؛…")

WATERMARK_PATTERNS = (
    "lunatoons", "lunatoon", "nadeinkorea", "made in korea", "madeinkorea",
    "asurascans", "asura", "flamecomics", "reaper scans", "reaperscans",
    "mangadex", "webtoon", "tapas", "toomics", "lezhin", "tappytoon",
    "kaynscan", "kayn scan", "scar.com", "scarcom", "wanscan", "wan scan",
    "vortexscans", "vortex scans", "vortexscan", "ikemanga", "likemanga",
    "munpia", "nullscans", "luminous", "flame comics", "cosmic scans",
    "asuracomic", "asuracomics", "discord.gg",
    "read this series", "readthis series", "read thisseries", "readthisseries",
    "series at", "seriesat", "support us", "to support", "supportus",
    "join our community", "discord server", "for the latest updates",
    "your support is needed", "community discord", "invite you", "we invite",
    "this chapter was brought", "brought to you by", "show your support",
    "dear readers", "happy reading", "dive deeper", "unlock up to",
    "exclusively on", "storm at", "join the storm",
    "redice studio", "redice", "leafsky", "wasakbasak", "wasak basak",
    "cho wooneh", "hermode", "dotori", "3b2s",
)

DOMAIN_TLDS = (
    "com", "org", "net", "io", "info", "xyz", "app", "dev",
    "site", "online", "web", "biz", "us", "uk", "kr",
    "jp", "cn", "ru", "de", "fr", "es", "pt", "br", "id",
    "gg", "link", "page", "club", "fun", "live", "news", "blog",
    "ink", "toon", "scans",
)

DOMAIN_RE = re.compile(
    r"(?i)\b(?:https?://|www\.)?"
    r"[a-z0-9](?:[a-z0-9\-]{1,61}[a-z0-9])"
    r"\.(?:" + "|".join(DOMAIN_TLDS) + r")\b"
)

PROMO_RE = re.compile(
    r"(?i)("
    r"read\s*this\s*series|"
    r"series\s*(first\s*)?at|"
    r"support\s*us|"
    r"to\s*support|"
    r"show\s*your\s*support|"
    r"brought\s*to\s*you|"
    r"this\s*chapter\s*was\s*brought|"
    r"dear\s*readers|"
    r"happy\s*reading|"
    r"dive\s*deeper|"
    r"unlock\s*up\s*to|"
    r"exclusively\s*on|"
    r"vortex\s*scans?|"
    r"ike\s*manga|"
    r"like\s*manga|"
    r"kayn\s*scan|"
    r"scar\.?\s*com|"
    r"wan\s*scan|"
    r"discord\s*(server|\.gg)|"
    r"join\s*(our|ou|the)\s*(community|storm)|"
    r"latest\s*updates|"
    r"support\s*is\s*needed|"
    r"we\s*invite|"
    r"invite\s*(you|yu)|"
    r"community\s*discord|"
    r"for\s*the\s*latest|"
    r"scan\s*\.?\s*com|"
    r"redice\s*studio|"
    r"wasak\s*basak|"
    r"leaf\s*sky|"
    r"3b2s"
    r")"
)

SFX_WORD_RE = re.compile(
    r"(?i)^("
    r"sfx|효과음?|효과|"
    r"boom|bang|crash|whoosh|swish|thud|clang|zap|pow|bam|wham|crack|smash|"
    r"roar|growl|hiss|screech|beep|ding|click|tick|tock|splash|drip|"
    r"gasp|sigh|sniff|cough|hic|ugh|argh|kugh|keck|kahack|gorulz|"
    r"thunk|slash|stab|slash|clang|clank|thump|wham|slam|snap|"
    r"ah+|oh+|uh+|hm+|mm+|ha+ha*|he+he*|hi+hi*|wa+h*|ya+h*|"
    r"kuh+|guh+|ngh+|ugh+|arg+|aarg+|"
    r"[!?.…]{2,}"
    r")[!?.…]*$"
)

HANGUL_RE = re.compile(r"[\uac00-\ud7a3]+")
PURE_HANGUL_SFX_RE = re.compile(r"^[\uac00-\ud7a3\s!?.…~\-]+$")


def uncensor_swears(text: str) -> str:
    
    if not text:
        return text

    result = text

    
    
    result = re.sub(
        r"\bwhat\s*the\s*f+[*@#$%^&._\-]*\b",
        "what the fuck ",
        result,
        flags=re.IGNORECASE,
    )
    result = re.sub(r"\bwhat\s*theF\b", "what the fuck", result, flags=re.IGNORECASE)
    result = re.sub(r"\btheF\b", "the fuck", result, flags=re.IGNORECASE)
    result = re.sub(r"\bw+t+f+\b", "what the fuck", result, flags=re.IGNORECASE)
    result = re.sub(
        r"\bthe\s*f+(?:uck)?\s*is\b",
        "the fuck is",
        result,
        flags=re.IGNORECASE,
    )

    replacements = [
        
        (r"\bf+u+[*@#$%^&._\-]*c+k+i+n+g?\b", "fucking"),
        (r"\bf+u+[*@#$%^&._\-]*c+k+\b", "fuck"),
        (r"\bf+[*@#$%^&._\-]+c+k+\b", "fuck"),
        (r"\bf[*@#$%^&._\-]{1,5}ck(?:ing)?\b", "fuck"),
        
        (r"\bf+[*@#$%^&._\-]*o+k+\b(?=[?!.,…]|$|\s)", "fuck"),
        (r"\bfck\b", "fuck"),
        (r"\bfuk\b", "fuck"),
        
        (r"\bs+h+[*@#$%^&._\-]*i+t+\b", "shit"),
        (r"\bs+h+[*@#$%^&._\-]+t+\b", "shit"),
        (r"\bsh[*@#$%^&._\-]{1,4}t\b", "shit"),
        (r"\bsht\b", "shit"),
        
        (r"\bb+i+[*@#$%^&._\-]*t+c+h+\b", "bitch"),
        (r"\bb+[*@#$%^&._\-]+t+c+h+\b", "bitch"),
        (r"\bb[*@#$%^&._\-]{1,4}tch\b", "bitch"),
        
        (r"\ba+s+s+[*@#$%^&._\-]*h+o+l+e+\b", "asshole"),
        (r"\ba+r+s+e+[*@#$%^&._\-]*h+o+l+e+\b", "arsehole"),
        (r"\ba[*@#$%^&._\-]{1,4}shole\b", "asshole"),
        
        (r"\bd+a+m+n+\b", "damn"),
        (r"\bd+a+m+m+i+t+\b", "dammit"),
        (r"\bd+i+c+k+\b", "dick"),
        (r"\bd[*@#$%^&._\-]{1,4}ck\b", "dick"),
        (r"\bc+o+c+k+\b", "cock"),
        (r"\bp+u+s+s+y+\b", "pussy"),
        (r"\bc+u+n+t+\b", "cunt"),
        (r"\bc[*@#$%^&._\-]{1,4}nt\b", "cunt"),
        (r"\bm+o+t+h+e+r+f+u+c+k+e+r+\b", "motherfucker"),
        (r"\bm+o+t+h+e+r+[*@#$%^&._\-]*f+u+c+k+e+r+\b", "motherfucker"),
        (r"\bb+a+s+t+a+r+d+\b", "bastard"),
        (r"\bh+e+l+l+\b", "hell"),
        (r"\bg+o+d\s*d+a+m+n?\b", "goddamn"),
        (r"\bd+a+m+n\s*i+t\b", "dammit"),
    ]

    for pattern, repl in replacements:
        result = re.sub(pattern, repl, result, flags=re.IGNORECASE)

    result = re.sub(r"\s{2,}", " ", result)
    result = re.sub(r"\s+([?!.,…])", r"\1", result)
    return result.strip()


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
        api_key,
        provider: str = "gemini",
        ocr_langs: List[str] = None,
        model_name: Optional[str] = None,
        api_base: Optional[str] = None,
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
        translation_temperature: float = 0.85,
        two_pass_ocr: bool = True,
        max_output_width: Optional[int] = None,
        stitch_max_height: int = 16000,
        stitch_short_threshold: int = 6000,
        stitch_keep_first: bool = True,
        debug: bool = False,
    ):
        provider = (provider or "gemini").lower().strip()
        if provider not in PROVIDER_PRESETS:
            raise ValueError(
                f"ارائه‌دهندهٔ ناشناخته: «{provider}». "
                f"گزینه‌ها: {', '.join(PROVIDER_PRESETS.keys())}"
            )
        self.provider = provider
        self.provider_cfg = PROVIDER_PRESETS[provider]
        self.provider_type = self.provider_cfg["type"]  

        if isinstance(api_key, str):
            keys = [k.strip() for k in api_key.replace(";", ",").split(",") if k.strip()]
        else:
            keys = [k.strip() for k in api_key if k and str(k).strip()]
        random.shuffle(keys)
        if not keys and self.provider != "ollama":
            raise ValueError(f"حداقل یک کلید API برای {provider} لازم است.")
        if not keys:
            keys = ["ollama"]  
        self._api_keys: List[str] = keys
        self._key_index: int = 0
        self._ocr_lock = threading.Lock()

        
        self.model_name = (model_name or self.provider_cfg.get("default_model") or "gemini-flash-latest").strip()
        self._model_cascade: List[str] = []
        self._model_index: int = 0
        self.api_base = api_base or self.provider_cfg.get("base_url")

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
        self.stitch_max_height = int(stitch_max_height) if stitch_max_height else 0
        self.stitch_short_threshold = int(stitch_short_threshold) if stitch_short_threshold else 0
        self.stitch_keep_first = bool(stitch_keep_first)
        self.debug = bool(debug)
        self._last_debug_image = None  

        self._name_glossary: Dict[str, str] = {}
        self._lama = None
        self._title_skip_patterns: List[str] = []
        MangaTranslator._title_skip_patterns = []
        self.client = None
        self.openai_client = None

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
            text_det_thresh=0.25,          
            text_det_box_thresh=0.4,
            text_det_unclip_ratio=1.8,
            det_db_thresh=0.25,
            det_db_box_thresh=0.4,
            det_db_unclip_ratio=1.8,
            max_batch_size=1,
            use_dilation=True,             
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

        
        if self.provider_type == "gemini":
            if not _HAS_GEMINI:
                raise ImportError(
                    "برای استفاده از Gemini باید google-genai نصب باشد:\n"
                    "  pip install google-genai"
                )
            self.client = genai.Client(api_key=self._api_keys[0])
            self._model_cascade = self._build_model_cascade(self.model_name, self.client)
            self.model_name = self._model_cascade[0]
            cascade_info = f" | cascade: {' → '.join(self._model_cascade[:5])}" + (
                "…" if len(self._model_cascade) > 5 else ""
            )
            if len(self._api_keys) > 1:
                print(f"[*] ارائه‌دهنده: Gemini | مدل: {self.model_name}{cascade_info} | "
                      f"{len(self._api_keys)} کلید API")
            else:
                print(f"[*] ارائه‌دهنده: Gemini | مدل: {self.model_name}{cascade_info}")
        else:
            
            if not _HAS_OPENAI:
                raise ImportError(
                    "برای استفاده از OpenAI / DeepSeek / Groq / ... باید openai نصب باشد:\n"
                    "  pip install openai"
                )
            self.openai_client = OpenAI(
                api_key=self._api_keys[0],
                base_url=self.api_base,
            )
            self._model_cascade = [self.model_name]
            print(f"[*] ارائه‌دهنده: {self.provider} | مدل: {self.model_name} | "
                  f"base: {self.api_base}")
            if len(self._api_keys) > 1:
                print(f"    {len(self._api_keys)} کلید API (جابه‌جایی خودکار)")

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
        low = msg.lower()
        return (
            "503" in msg
            or "UNAVAILABLE" in msg
            or "404" in msg
            or "NOT_FOUND" in msg
            or "high demand" in low
            or "try again later" in low
            or "currently experiencing" in low
            or "model not found" in low
            or "not found for api version" in low
            or "is not supported" in low
            or "no longer available" in low
            or "please update your code to use a newer model" in low
        )

    def _is_model_permanently_gone(self, err: Exception) -> bool:
        
        msg = str(err).lower()
        return (
            "404" in str(err)
            or "not_found" in msg
            or "no longer available" in msg
            or "please update your code to use a newer model" in msg
            or "model not found" in msg
        )

    @staticmethod
    def _static_fallback_models(primary: str) -> List[str]:
        
        preferred = [
            "gemini-2.5-flash",
            "gemini-flash-latest",
            "gemini-2.5-flash-lite",
            "gemini-flash-lite-latest",
            "gemini-3.7-flash",
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash",
        ]
        cascade = [primary] if primary else []
        for m in preferred:
            if m not in cascade:
                cascade.append(m)
        return cascade or preferred

    @staticmethod
    def _model_sort_key(name: str) -> tuple:
        n = name.lower().replace("models/", "")
        ver_m = re.search(r"gemini-(\d+(?:\.\d+)?)", n)
        major_minor = 0.0
        if ver_m:
            try:
                major_minor = float(ver_m.group(1))
            except ValueError:
                major_minor = 0.0

        is_lite = "lite" in n
        is_flash = "flash" in n
        is_pro = "pro" in n and "flash" not in n

        if n == "gemini-2.5-flash" or (abs(major_minor - 2.5) < 0.01 and not is_lite and is_flash):
            family_rank = 0
        elif n == "gemini-flash-latest":
            family_rank = 1
        elif n == "gemini-2.5-flash-lite" or (abs(major_minor - 2.5) < 0.01 and is_lite):
            family_rank = 2
        elif n == "gemini-flash-lite-latest":
            family_rank = 3
        elif major_minor >= 2.5 and major_minor < 3.0:
            family_rank = 4
        elif major_minor >= 3.0:
            family_rank = 5
        elif n.endswith("-latest") and "flash" in n:
            family_rank = 6
        elif major_minor >= 2.0:
            family_rank = 7
        elif major_minor >= 1.0:
            family_rank = 8
        else:
            family_rank = 9

        version_rank = -major_minor
        lite_rank = 1 if is_lite else 0
        type_rank = 0 if is_flash else (2 if is_pro else 1)

        return (family_rank, version_rank, lite_rank, type_rank, n)

    def _discover_models_from_api(self, client) -> List[str]:
        
        names: List[str] = []
        try:
            for m in client.models.list():
                raw = getattr(m, "name", None) or ""
                short = raw.replace("models/", "").strip()
                if not short:
                    continue
                actions = getattr(m, "supported_actions", None) or []
                methods = getattr(m, "supported_generation_methods", None) or []
                ok = False
                if actions:
                    ok = "generateContent" in actions
                elif methods:
                    ok = "generateContent" in methods
                else:
                    
                    ok = "flash" in short.lower() and not any(
                        x in short.lower()
                        for x in ("image", "tts", "live", "audio", "embedding", "gemma")
                    )
                if not ok:
                    continue
                
                low = short.lower()
                if any(x in low for x in (
                    "image", "tts", "live", "audio", "embedding", "gemma",
                    "robotics", "omni", "nano-banana", "imagen",
                )):
                    continue
                names.append(short)
        except Exception as e:
            print(f"    [!] کشف مدل از API ناموفق: {e}")
            return []
        
        uniq = sorted(set(names), key=self._model_sort_key)
        return uniq

    def _build_model_cascade(self, primary: str, client=None) -> List[str]:
        primary = (primary or "gemini-2.5-flash").strip().replace("models/", "")
        discovered: List[str] = []
        if client is not None:
            discovered = self._discover_models_from_api(client)

        if discovered:
            print(f"[*] {len(discovered)} مدل flash از API پیدا شد؛ مرتب‌سازی بر اساس اولویت ۲.۵ → ۳.x")
            cascade = []
            if primary and primary not in discovered:
                
                cascade.append(primary)
            elif primary:
                cascade.append(primary)
            for m in discovered:
                if m not in cascade:
                    cascade.append(m)
            return cascade

        print("[*] کشف API ممکن نشد → استفاده از لیست ثابت fallback.")
        return self._static_fallback_models(primary)

    def _drop_current_model_and_switch(self, reason: str = "") -> bool:
        
        if not self._model_cascade:
            return False
        dead = self.model_name
        if 0 <= self._model_index < len(self._model_cascade):
            del self._model_cascade[self._model_index]
        else:
            self._model_cascade = [m for m in self._model_cascade if m != dead]
        if not self._model_cascade:
            print(f"    [!] مدل «{dead}» حذف شد ولی مدل دیگری در cascade نیست.")
            return False
        if self._model_index >= len(self._model_cascade):
            self._model_index = 0
        self.model_name = self._model_cascade[self._model_index]
        extra = f" ({reason})" if reason else ""
        print(f"    [!] مدل «{dead}» دیگر در دسترس نیست → حذف شد.")
        print(f"    [*] مدل بعدی فعال شد: {self.model_name} "
              f"[{self._model_index + 1}/{len(self._model_cascade)}]{extra}")
        return True

    def _switch_to_next_model(self, reason: str = "") -> bool:
        if not self._model_cascade or len(self._model_cascade) <= 1:
            return False
        next_idx = self._model_index + 1
        if next_idx >= len(self._model_cascade):
            return False
        self._model_index = next_idx
        self.model_name = self._model_cascade[self._model_index]
        extra = f" ({reason})" if reason else ""
        print(f"    [*] مدل بعدی فعال شد: {self.model_name} "
              f"[{self._model_index + 1}/{len(self._model_cascade)}]{extra}")
        return True

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
        self._apply_api_key(key)
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
        self._apply_api_key(key)
        print(f"    [*] کلید API شماره {self._key_index + 1}/{len(self._api_keys)} فعال شد.")
        return True

    def _apply_api_key(self, key: str) -> None:
        
        if self.provider_type == "gemini":
            self.client = genai.Client(api_key=key)
        else:
            self.openai_client = OpenAI(api_key=key, base_url=self.api_base)

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
                
                if len(text) == 1 and text.upper() not in {"I", "!", "?", "…"}:
                    continue

                stripped = text.strip()
                kind = self._classify_text(stripped)

                if kind == "junk" and len(re.sub(r"[^\w]", "", stripped)) <= 1:
                    continue

                detections.append({
                    "poly": poly,
                    "text": text,
                    "conf": conf,
                    "angle": angle,
                    "kind": kind,
                })
        return detections

    @staticmethod
    def _classify_text(text: str) -> str:
        stripped = (text or "").strip()
        if not stripped:
            return "junk"

        low_full = stripped.lower()
        low_compact = re.sub(r"[\s.\-_]", "", low_full)
        alpha_only = re.sub(r"[^\w]", "", stripped, flags=re.UNICODE)
        words = re.findall(r"[A-Za-z\uac00-\ud7a3]+", stripped)

        
        dialogue_short = {
            "i", "im", "i'm", "me", "my", "you", "u", "he", "she", "we", "they",
            "no", "yes", "ok", "okay", "oh", "ah", "eh", "uh", "hm", "hmm",
            "hi", "hey", "yo", "bye", "wow", "yay", "ouch", "ow", "ugh",
            "stop", "go", "run", "help", "wait", "hold", "look", "come",
            "move", "fire", "ready", "now", "true", "lie", "die", "what",
            "why", "how", "who", "where", "when", "huh", "eh?", "ah!",
            "no!", "yes!", "ok!", "oh!", "ah!", "hey!", "wow!", "stop!",
            "go!", "run!", "help!", "wait!", "what?", "why?", "how?",
            "who?", "huh?", "no?", "yes?", "really", "sure", "fine",
            "damn", "shit", "fuck", "hell", "god", "please", "sorry",
            "thanks", "thank", "bye", "later", "never", "always", "maybe",
            "huh", "nah", "yep", "yup", "nope", "yea", "yeah", "yup",
            "one", "two", "all", "any", "out", "off", "up", "down", "in",
            "on", "at", "to", "of", "for", "and", "but", "or", "so",
            "the", "a", "an", "this", "that", "it", "its", "his", "her",
            "our", "your", "their", "us", "them", "him", "do",
            "did", "does", "is", "are", "was", "were", "be", "been",
            "have", "has", "had", "will", "would", "can", "could",
            "should", "must", "may", "might", "let", "get", "got",
            "see", "saw", "know", "knew", "think", "say", "said",
            "tell", "told", "ask", "asked", "came", "went",
            "id", "sir", "boss", "man", "boy", "girl", "kid", "guys",
            "hey!", "what!", "huh!", "no!!", "yes!!", "stop!!", "wait!!",
            "die!", "die!!", "run!", "run!!", "help!", "help!!",
            
            "much", "rich", "gold", "hard", "find", "gone", "took", "last",
            "tiny", "piece", "way", "need", "want", "money", "carry", "dream",
            "found", "single", "league", "hand", "look", "part",
            "tokyo", "hokkaido", "meiji", "nuggets", "flakes", "prospectors",
        }

        core = re.sub(r"[!?.…~\-]+$", "", low_full).strip()

        
        
        _lonely_func = {
            "of", "to", "in", "on", "at", "a", "an", "the", "is", "it", "as",
            "or", "so", "be", "do", "if", "by",
        }
        if len(stripped) <= 3 and core in _lonely_func and not any(c in stripped for c in "!?…"):
            return "junk"

        if core in dialogue_short or low_full in dialogue_short:
            return "dialogue"
        if alpha_only.lower() in dialogue_short:
            return "dialogue"

        if stripped.upper() == "I":
            return "dialogue"

        digits_only = re.sub(r"[^\d]", "", stripped)

        is_progress = bool(re.fullmatch(
            r"[\(\[\{]?\s*\d+\s*/\s*\d+\s*[\)\]\}]?",
            stripped,
        ))
        if is_progress:
            return "dialogue"

        
        
        if (
            re.search(r"\d+\s*화", stripped)
            or re.search(r"(?i)\b(?:ch(?:apter)?|ep(?:isode)?)\s*\.?\s*\d+", stripped)
            or re.search(r"(?i)^\d+\s*(?:화|wolat|etdt|chapter|episode)\b", stripped)
            or re.search(r"(?i)\b\d{1,3}\s*화\b", stripped)
            or (re.search(r"(?i)wolat|etdt", stripped) and re.search(r"\d", stripped))
        ):
            return "promo"

        
        if stripped.isdigit() or re.fullmatch(r"[\d\s.%oO]+", stripped):
            return "junk"
        if re.fullmatch(r"[QOIl]?\d{2,}", stripped, re.I):  
            return "junk"
        if re.fullmatch(r"[A-Za-z]{0,2}\d{3,}", stripped) and len(digits_only) >= 3:
            return "junk"

        if re.fullmatch(r"[A-Za-z]?\d{2,6}", stripped) and len(stripped) <= 7:
            return "sfx"
        if digits_only and len(stripped) <= 12:
            non_digit_alpha = re.sub(r"[\d\s.%oOQIl]", "", stripped, flags=re.I)
            non_digit_alpha = re.sub(r"[/()\[\]{}]", "", non_digit_alpha)
            if len(non_digit_alpha) <= 2:
                return "junk"
        if len(alpha_only) <= 1 and len(stripped) <= 3 and stripped.upper() != "I":
            return "junk"
        if len(alpha_only) <= 2 and len(stripped) <= 5 and not any(
            c.isalpha() and c.isascii() for c in stripped if len(stripped) > 3
        ):
            return "junk"

        if getattr(MangaTranslator, "_title_skip_enabled", False):
            title_pats = getattr(MangaTranslator, "_title_skip_patterns", None) or []
            for pat in title_pats:
                if not pat or len(pat) < 6:
                    continue
                if pat not in low_compact:
                    continue
                remainder = low_compact.replace(pat, "")
                if len(remainder) <= 6 and len(low_compact) <= 40:
                    return "promo"

        if any(w.replace(" ", "") in low_compact for w in WATERMARK_PATTERNS):
            return "promo"
        if PROMO_RE.search(stripped):
            return "promo"
        if DOMAIN_RE.search(stripped):
            return "promo"
        if low_compact in {
            "org", "com", "net", "www", "http", "https", "wwwcom", "wwworg",
            "comto", "ink", "scans", "scan", "asura", "asuras", "asuran",
        }:
            return "promo"
        if re.fullmatch(r"(?i)[a-z0-9\-]+\.(?:" + "|".join(DOMAIN_TLDS) + r")[a-z]{0,3}", stripped):
            return "promo"
        if re.search(r"(?i)\.(?:com|org|net|io|ink)\b", stripped):
            return "promo"
        if re.search(r"(?i)(like|ike|vortex|kayn|asura|reaper)?manga[.\s]?(ink|unk|com|org)?", stripped) and len(stripped) <= 24:
            return "promo"
        if low_compact.endswith(("com", "org", "net", "ink", "unk")) and (
            len(stripped) <= 28 or "scan" in low_compact or "manga" in low_compact or "series" in low_full
        ):
            return "promo"

        
        if len(words) >= 2 or len(stripped) > 10:
            return "dialogue"

        hangul_chars = HANGUL_RE.findall(stripped)
        hangul_len = sum(len(h) for h in hangul_chars)
        if hangul_len >= 1 and hangul_len == len(alpha_only) and len(stripped) <= 8:
            return "sfx"

        
        if len(stripped) <= 12 and SFX_WORD_RE.match(stripped):
            if core not in dialogue_short and alpha_only.lower() not in dialogue_short:
                return "sfx"

        
        
        
        if (
            3 <= len(stripped) <= 12
            and stripped.isupper()
            and " " not in stripped
            and stripped.isalpha()
        ):
            upper_dialogue = {w.upper() for w in dialogue_short if w.isalpha()}
            if stripped in upper_dialogue:
                return "dialogue"

            
            
            _common_upper = {
                "CONTROL", "EVERYTHING", "ORDERS", "ORDER", "SOMETHING",
                "ANYTHING", "NOTHING", "SOMEONE", "ANYONE", "EVERYONE",
                "ANYWHERE", "EVERYWHERE", "SOMEWHERE", "WHATEVER",
                "HOWEVER", "BECAUSE", "WITHOUT", "THROUGH", "BETWEEN",
                "ANOTHER", "ALREADY", "ALWAYS", "NEVER", "REALLY",
                "PROBABLY", "CERTAINLY", "ABSOLUTELY", "COMPLETELY",
                "PERFECTLY", "EXACTLY", "ACTUALLY", "SERIOUSLY",
                "OBVIOUSLY", "FINALLY", "SUDDENLY", "QUICKLY",
                "BEFORE", "AFTER", "UNDER", "OVER", "AGAINST",
                "TOWARD", "TOWARDS", "INSIDE", "OUTSIDE", "AROUND",
                "DURING", "WITHIN", "BEHIND", "BEYOND", "ACROSS",
                "PEOPLE", "PERSON", "FRIEND", "ENEMY", "POWER",
                "POWERS", "WORLD", "PLACE", "THING", "THINGS",
                "RIGHT", "WRONG", "GREAT", "SMALL", "LARGE",
                "FIRST", "LAST", "NEXT", "OTHER", "SAME",
                "STILL", "EVEN", "JUST", "ONLY", "ALSO",
                "ABOUT", "AGAIN", "BEING", "DOING", "GOING",
                "COMING", "LOOKING", "THINKING", "KNOWING",
                "WANTING", "NEEDED", "CALLED", "TURNED", "MADE",
                "SURE", "WHEN", "WHERE", "WHICH", "WHILE",
                "THESE", "THOSE", "THERE", "THEIR", "THEM",
                "YOUR", "YOURS", "MINE", "OURS", "THEIRS",
                "REPORT", "RESISTANCE", "INFORMATION", "AUDIENCE",
                "PUPPETS", "REBELLION", "CLEANERS", "CHOKERS",
                "FESTIVAL", "VENUE", "MICROPHONE", "RANGE",
                "NORMAL", "LORD", "MOMENT", "EFFORT", "RULE",
            }
            if stripped in _common_upper:
                return "dialogue"

            has_strong_repeat = bool(re.search(r"(.)\1{2,}", stripped))
            vowel_count = sum(1 for c in stripped if c in "AEIOU")
            
            consonant_run = bool(re.search(r"[BCDFGHJKLMNPQRSTVWXYZ]{4,}", stripped))
            ends_with_impact = any(
                stripped.endswith(suf)
                for suf in (
                    "AC", "ACK", "AK", "UM", "OOM", "ANG", "ONG",
                    "ASH", "ISH", "USH", "AMM", "ANN",
                    
                )
            )
            looks_invented = (
                has_strong_repeat
                or consonant_run
                or ends_with_impact
                or (vowel_count == 0 and len(stripped) >= 3)
            )

            if looks_invented:
                return "sfx"

            return "dialogue"

        if len(alpha_only) <= 2 and len(stripped) <= 4 and stripped.upper() != "I":
            return "junk"

        return "dialogue"

    @staticmethod
    def _dedupe_detections(detections: List[dict], iou_thresh: float = 0.28) -> List[dict]:
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

        def text_norm(t: str) -> str:
            return re.sub(r"[^a-z0-9\uac00-\ud7a3]", "", (t or "").lower())

        def is_near_duplicate_text(a: str, b: str) -> bool:
            
            na, nb = text_norm(a), text_norm(b)
            if not na or not nb:
                return False
            if na == nb:
                return True
            shorter, longer = (na, nb) if len(na) <= len(nb) else (nb, na)
            
            if len(shorter) >= 3 and shorter in longer:
                return True
            return False

        kept: List[dict] = []
        for d in detections:
            r = rect_of(d)
            dup_idx = None
            for i, k in enumerate(kept):
                kr = rect_of(k)
                if iou(r, kr) > iou_thresh:
                    dup_idx = i
                    break
                if is_near_duplicate_text(d.get("text") or "", k.get("text") or ""):
                    cx1 = r[0] + r[2] / 2.0
                    cy1 = r[1] + r[3] / 2.0
                    cx2 = kr[0] + kr[2] / 2.0
                    cy2 = kr[1] + kr[3] / 2.0
                    if (abs(cx1 - cx2) < max(r[2], kr[2]) * 0.95 + 50
                            and abs(cy1 - cy2) < max(r[3], kr[3]) * 1.3 + 40):
                        dup_idx = i
                        break
            if dup_idx is None:
                kept.append(d)
            else:
                cur = kept[dup_idx]
                better_conf = d["conf"] > cur["conf"] + 0.04
                similar_conf = abs(d["conf"] - cur["conf"]) <= 0.06
                longer = len(d.get("text") or "") > len(cur.get("text") or "")
                if (better_conf or (similar_conf and longer)
                        or (is_near_duplicate_text(d.get("text") or "", cur.get("text") or "") and longer)):
                    kept[dup_idx] = d
        return kept

    def group_into_regions(self, detections: List[dict], y_offset: int = 0) -> List[TextRegion]:
      if not detections:
        return []

      n = len(detections)
      rects = []
      texts = []
      for d in detections:
        x, y, w, h = cv2.boundingRect(d["poly"])
        rects.append((x, y + y_offset, w, h))
        texts.append((d.get("text") or "").strip())

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

      def iou(r1, r2):
        x1, y1, w1, h1 = r1
        x2, y2, w2, h2 = r2
        xi1, yi1 = max(x1, x2), max(y1, y2)
        xi2, yi2 = min(x1 + w1, x2 + w2), min(y1 + h1, y2 + h2)
        inter = max(0, xi2 - xi1) * max(0, yi2 - yi1)
        union_area = w1 * h1 + w2 * h2 - inter
        return inter / union_area if union_area > 0 else 0.0

      def pair_metrics(r1, r2):
        x1, y1, w1, h1 = r1
        x2, y2, w2, h2 = r2
        cy1 = y1 + h1 / 2.0
        cy2 = y2 + h2 / 2.0
        cx1 = x1 + w1 / 2.0
        cx2 = x2 + w2 / 2.0
        vgap = abs(cy1 - cy2) - (h1 + h2) / 2.0
        hgap = abs(cx1 - cx2) - (w1 + w2) / 2.0
        avg_h = max(1.0, (h1 + h2) / 2.0)
        avg_w = max(1.0, (w1 + w2) / 2.0)
        return vgap, hgap, avg_h, avg_w, abs(cx1 - cx2), max(h1, h2), min(h1, h2), min(w1, w2), max(w1, w2)

      def starts_with_lowercase(text: str) -> bool:
        for ch in text:
            if ch.isalpha():
                return ch.islower()
        return False

      def likely_same_bubble(i, j) -> bool:
        r1, r2 = rects[i], rects[j]
        t1, t2 = texts[i], texts[j]
        k1 = detections[i].get("kind", "dialogue")
        k2 = detections[j].get("kind", "dialogue")

        if r1[1] > r2[1]:
          r1, r2 = r2, r1
          t1, t2 = t2, t1

        vgap, hgap, avg_h, avg_w, cx_dist, h_max, h_min, w_min, w_max = pair_metrics(r1, r2)
        if self.debug:
          short1 = (t1 or "")[:25]
          short2 = (t2 or "")[:25]
          print(f"  [VGAP DEBUG] \"{short1}\" <-> \"{short2}\"")
          print(f"       vgap={vgap:.1f} | avg_h={avg_h:.1f} | cx_dist={cx_dist:.1f}")
        if vgap > 28:
          return False
    

        
        small_attach = (
            h_min <= 28 or (h_max > h_min * 2.5 and h_min <= 40)
        ) and (k1 in ("junk", "sfx", "promo") or k2 in ("junk", "sfx", "promo"))

        if h_max > h_min * 3.0 and not small_attach:
          return False

        if cx_dist > max(avg_w * 0.55, 45) and not small_attach:
          return False
        if small_attach and cx_dist > max(avg_w * 0.85, 60):
          return False

        if starts_with_lowercase(t2) and cx_dist < max(avg_w * 0.40, 35) and vgap < 25:
          return True

        width_ratio = w_min / w_max if w_max > 0 else 0
        centers_aligned = cx_dist < max(avg_w * 0.28, 20)

        if width_ratio > 0.60 and centers_aligned and vgap < 18:
          return True

        margin = max(2, int(avg_h * 0.08))
        if small_attach:
          margin = max(margin, 10)
        x1, y1, w1, h1 = r1
        x2, y2, w2, h2 = r2
        a = (x1 - margin, y1 - margin, x1 + w1 + margin, y1 + h1 + margin)
        b = (x2 - margin, y2 - margin, x2 + w2 + margin, y2 + h2 + margin)
        overlaps = not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])

        if not overlaps:
          return False

        if iou(r1, r2) >= 0.25:
          return True

        if centers_aligned and vgap < 14:
          return True

        if small_attach and vgap < 20 and cx_dist < max(avg_w * 0.7, 50):
          return True

        return False
 
    
      for i in range(n):
        ki = detections[i].get("kind", "dialogue")
        if ki not in ("sfx", "promo", "junk"):
            continue
        
        t_i = (detections[i].get("text") or "").strip()
        if ki == "sfx" and len(t_i) >= 3:
            continue
        for j in range(n):
            if i == j:
                continue
            if detections[j].get("kind", "dialogue") != "dialogue":
                continue
            near_margin = max(8, int(min(rects[i][3], rects[j][3]) * 0.30))
            x1, y1, w1, h1 = rects[i]
            x2, y2, w2, h2 = rects[j]
            a = (x1 - near_margin, y1 - near_margin, x1 + w1 + near_margin, y1 + h1 + near_margin)
            b = (x2 - near_margin, y2 - near_margin, x2 + w2 + near_margin, y2 + h2 + near_margin)
            if not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1]):
                
                cx1 = x1 + w1 / 2.0
                cx2 = x2 + w2 / 2.0
                if abs(cx1 - cx2) > max((w1 + w2) / 2.0 * 0.6, 45):
                    continue
                detections[i]["kind"] = "dialogue"
                break

      def kinds_compatible(i, j):
        ki = detections[i].get("kind", "dialogue")
        kj = detections[j].get("kind", "dialogue")
        if ki == kj:
            return True
        
        pair = {ki, kj}
        if pair == {"junk", "dialogue"}:
            return True
        if "junk" in pair and ("sfx" in pair or "promo" in pair):
            return True
        return False

    
      for i in range(n):
        for j in range(i + 1, n):
            if not kinds_compatible(i, j):
                continue
            if likely_same_bubble(i, j):
                union(i, j)

    
      groups = {}
      for i in range(n):
        root = find(i)
        groups.setdefault(root, []).append(i)

      regions = []
      for gid, idxs in enumerate(groups.values()):
        
        
        boxes = []
        for i in idxs:
            poly = np.array(detections[i]["poly"], dtype=np.int32).copy()
            if poly.ndim == 2 and poly.shape[1] == 2 and y_offset:
                poly = poly.copy()
                poly[:, 1] = poly[:, 1] + int(y_offset)
            elif poly.ndim == 3 and poly.shape[-1] == 2 and y_offset:
                poly = poly.copy()
                poly[:, :, 1] = poly[:, :, 1] + int(y_offset)
            boxes.append(poly)
        xs = [rects[i][0] for i in idxs]
        ys = [rects[i][1] for i in idxs]
        xe = [rects[i][0] + rects[i][2] for i in idxs]
        ye = [rects[i][1] + rects[i][3] for i in idxs]
        x0, y0, x1, y1 = min(xs), min(ys), max(xe), max(ye)

        idxs_sorted = sorted(idxs, key=lambda i: (rects[i][1], rects[i][0]))

        
        def _norm_txt(t: str) -> str:
            return re.sub(r"[^a-z0-9\uac00-\ud7a3]", "", (t or "").lower())

        def _is_strict_partial(a: str, b: str) -> bool:
            
            na, nb = _norm_txt(a), _norm_txt(b)
            if not na or not nb:
                return False
            if na == nb:
                return True
            shorter, longer = (na, nb) if len(na) <= len(nb) else (nb, na)
            return len(shorter) >= 3 and shorter in longer

        kept_idxs: List[int] = []
        for i in idxs_sorted:
            t_i = (detections[i].get("text") or "").strip()
            if not t_i:
                continue
            r_i = rects[i]
            is_dup = False
            for k, j in enumerate(kept_idxs):
                t_j = (detections[j].get("text") or "").strip()
                r_j = rects[j]
                cy_i = r_i[1] + r_i[3] / 2.0
                cy_j = r_j[1] + r_j[3] / 2.0
                avg_h = max(1.0, (r_i[3] + r_j[3]) / 2.0)
                same_line = abs(cy_i - cy_j) < avg_h * 0.65
                if same_line and _is_strict_partial(t_i, t_j):
                    conf_i = float(detections[i].get("conf") or 0)
                    conf_j = float(detections[j].get("conf") or 0)
                    if len(t_i) > len(t_j) or (len(t_i) == len(t_j) and conf_i > conf_j):
                        kept_idxs[k] = i
                    is_dup = True
                    break
            if not is_dup:
                kept_idxs.append(i)

        
        if len(kept_idxs) > 1:
            long_norms = []
            short_idxs = []
            for i in kept_idxs:
                t = (detections[i].get("text") or "").strip()
                n = _norm_txt(t)
                if len(t) >= 10 or len(n) >= 8:
                    long_norms.append(n)
                else:
                    short_idxs.append(i)
            if long_norms and short_idxs:
                combined = "".join(long_norms)
                final = [i for i in kept_idxs if i not in short_idxs]
                for i in short_idxs:
                    n = _norm_txt(detections[i].get("text") or "")
                    if not n or n not in combined:
                        final.append(i)
                kept_idxs = sorted(final, key=lambda i: (rects[i][1], rects[i][0]))

        kept_idxs = sorted(kept_idxs, key=lambda i: (rects[i][1], rects[i][0]))
        text = " ".join(
            (detections[i].get("text") or "").strip()
            for i in kept_idxs
            if (detections[i].get("text") or "").strip()
        )
        text = re.sub(r"\s{2,}", " ", text).strip()
        text = re.sub(r"\b(\w{2,})\s+\1\b", r"\1", text, flags=re.IGNORECASE)

        angles = [detections[i].get("angle", 0.0) for i in kept_idxs] or [0.0]
        avg_angle = float(np.mean(angles)) if angles else 0.0
        region_kind = MangaTranslator._classify_text(text)

        regions.append(
            TextRegion(
                id=gid,
                boxes=boxes,
                source_text=text,
                rect=(x0, y0, x1 - x0, y1 - y0),
                angle=avg_angle,
                kind=region_kind,
            )
        )

    
      
      
      
      
      merged_flags = [False] * len(regions)
      for i, ri in enumerate(regions):
        if merged_flags[i] or ri.kind not in ("sfx", "promo", "junk"):
            continue
        sfx_text = (ri.source_text or "").strip()
        for j, rj in enumerate(regions):
            if i == j or merged_flags[j] or rj.kind != "dialogue":
                continue
            x1, y1, w1, h1 = ri.rect
            x2, y2, w2, h2 = rj.rect
            cx1 = x1 + w1 / 2.0
            cy1 = y1 + h1 / 2.0
            cx2 = x2 + w2 / 2.0
            cy2 = y2 + h2 / 2.0
            avg_w = max(1.0, (w1 + w2) / 2.0)
            avg_h = max(1.0, (h1 + h2) / 2.0)

            
            if abs(cx1 - cx2) > max(avg_w * 0.55, 45):
                continue

            
            pad = max(8, int(min(h1, h2) * 0.35))
            inside = (
                x2 - pad <= cx1 <= x2 + w2 + pad
                and y2 - pad <= cy1 <= y2 + h2 + pad
            )
            
            vgap = abs(cy1 - cy2) - (h1 + h2) / 2.0
            stacked = vgap < 18 and abs(cx1 - cx2) < max(avg_w * 0.40, 35)

            
            if ri.kind == "sfx" and len(sfx_text) >= 4 and not inside:
                continue
            if not (inside or stacked):
                continue

            rj.boxes = list(rj.boxes) + list(ri.boxes)
            
            parts = sorted(
                [(rj.rect[1], rj.source_text.strip()), (ri.rect[1], ri.source_text.strip())],
                key=lambda t: t[0],
            )
            rj.source_text = " ".join(t[1] for t in parts if t[1])
            x0 = min(rj.rect[0], ri.rect[0])
            y0 = min(rj.rect[1], ri.rect[1])
            x1b = max(rj.rect[0] + rj.rect[2], ri.rect[0] + ri.rect[2])
            y1b = max(rj.rect[1] + rj.rect[3], ri.rect[1] + ri.rect[3])
            rj.rect = (x0, y0, x1b - x0, y1b - y0)
            rj.kind = "dialogue"
            merged_flags[i] = True
            break

      regions = [r for i, r in enumerate(regions) if not merged_flags[i]]
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
            na = re.sub(r"[^a-z0-9\uac00-\ud7a3]", "", a)
            nb = re.sub(r"[^a-z0-9\uac00-\ud7a3]", "", b)
            if not na or not nb:
                return False
            if na == nb:
                return True
            shorter, longer = (na, nb) if len(na) <= len(nb) else (nb, na)
            if len(shorter) >= 4 and shorter in longer:
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
                    u.kind = MangaTranslator._classify_text(u.source_text)
                    break
            if not is_dup:
                unique.append(r)
        return unique


    def _build_text_mask(self, image: np.ndarray, regions: List[TextRegion]) -> np.ndarray:
        h_img, w_img = image.shape[:2]
        text_mask = np.zeros((h_img, w_img), dtype=np.uint8)
        promo_mask = np.zeros((h_img, w_img), dtype=np.uint8)
        pad = max(2, int(getattr(self, "mask_padding", 3) or 3))

        for region in regions:
            filled = False
            for poly in region.boxes:
                pts = np.array(poly, np.int32).reshape((-1, 1, 2))
                
                ys = pts[:, 0, 1]
                xs = pts[:, 0, 0]
                if np.any(ys < -50) or np.any(ys > h_img + 50) or np.any(xs < -50) or np.any(xs > w_img + 50):
                    continue
                cv2.fillPoly(text_mask, [pts], 255)
                filled = True
                if getattr(region, "kind", "dialogue") in ("promo", "sfx"):
                    cv2.fillPoly(promo_mask, [pts], 255)

            
            if not filled:
                x, y, w, h = region.rect
                x0 = max(0, int(x) - pad)
                y0 = max(0, int(y) - pad)
                x1 = min(w_img, int(x + w) + pad)
                y1 = min(h_img, int(y + h) + pad)
                if x1 > x0 and y1 > y0:
                    text_mask[y0:y1, x0:x1] = 255
                    if getattr(region, "kind", "dialogue") in ("promo", "sfx"):
                        promo_mask[y0:y1, x0:x1] = 255

        if not np.any(text_mask):
            return text_mask

        
        if pad > 0:
            k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (pad * 2 + 1, pad * 2 + 1))
            text_mask = cv2.dilate(text_mask, k, iterations=1)

        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        lower_purple = np.array([110, 15, 15])
        upper_purple = np.array([170, 255, 255])
        purple_mask = cv2.inRange(hsv, lower_purple, upper_purple)

        near_text = cv2.dilate(text_mask, np.ones((10, 10), np.uint8), iterations=1)
        purple_around_text = cv2.bitwise_and(purple_mask, near_text)

        full_target_mask = cv2.bitwise_or(text_mask, purple_around_text)

        if np.any(promo_mask):
            promo_dilated = cv2.dilate(
                promo_mask,
                cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)),
                iterations=3,
            )
            full_target_mask = cv2.bitwise_or(full_target_mask, promo_dilated)

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

    def _get_system_instruction(self) -> str:
        return (
            "تو «بازآفرین دیالوگ» مانهوا هستی.\n"
            "تو مترجم تحت‌اللفظی نیستی. کار تو ترجمه‌ی کلمات نیست؛ "
            "کار تو بازسازی همان لحظه، همان آدم، همان احساس و همان منظور به زبان فارسی است.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "روش فکر کردن\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "برای هر دیالوگ، متن انگلیسی را مستقیم به فارسی تبدیل نکن.\n"
            "اول درک کن که شخصیت دقیقاً چه می‌خواهد بگوید، چرا آن را می‌گوید و چه حسی دارد.\n"
            "بعد تصور کن این شخصیت اگر یک ایرانی بود و همین موقعیت دقیقاً برایش اتفاق افتاده بود، "
            "بدون فکر کردن به متن انگلیسی، چه جمله‌ای به زبان می‌آورد.\n"
            "همان جمله‌ی فارسی را خروجی بده.\n\n"
            "یعنی مسیر کار این باشد:\n"
            "متن انگلیسی → درک صحنه → درک شخصیت → درک احساس → پیدا کردن بیان طبیعی فارسی → خروجی\n"
            "هرگز این مسیر را دنبال نکن:\n"
            "متن انگلیسی → جابه‌جایی کلمه‌ها → فارسی\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "قانون «صدای واقعی»\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "ترجمه نباید صدای مترجم داشته باشد.\n"
            "باید صدای همان شخصیت را داشته باشد.\n"
            "اگر جمله از نظر معنایی درست است ولی یک ایرانی در مکالمه‌ی واقعی این‌طور نمی‌گوید، "
            "ترجمه غلط محسوب می‌شود و باید عوض شود.\n\n"
            "هر دیالوگ باید انگار مستقیماً از دهان شخصیت بیرون آمده باشد:\n"
            "- با ریتم طبیعی گفتار\n"
            "- با انتخاب کلمات طبیعی\n"
            "- با واکنش‌های واقعی\n"
            "- با شدت احساسی متناسب با صحنه\n"
            "- بدون بوی ترجمه\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "شخصیت مهم‌تر از لغت است\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "یک جمله برای دو شخصیت مختلف لزوماً نباید یک‌جور ترجمه شود.\n"
            "به سن، شخصیت، رابطه، جایگاه، اعتمادبه‌نفس و حالت روانی گوینده توجه کن.\n"
            "شخصیت خجالتی، مغرور، لوس، عصبانی، شرور، شوخ، جدی یا ترسیده باید صدای متفاوتی داشته باشد.\n"
            "اگر شخصیت در حال خفه کردن خنده است، جمله باید این حس را داشته باشد.\n"
            "اگر از چیزی جا خورده، جمله باید واکنشی باشد.\n"
            "اگر عصبانی است، جمله نباید بی‌حال و تمیز باشد.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "فارسی را از خود فارسی بساز\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "هرجا انگلیسی یک اصطلاح، کنایه یا بیان خاص دارد، دنبال نسخه‌ی فارسیِ همان رفتار بگرد، "
            "نه ترجمه‌ی لغوی آن.\n"
            "ترتیب کلمات انگلیسی هیچ اهمیتی ندارد.\n"
            "ممکن است یک جمله در فارسی کوتاه‌تر، بلندتر، شکسته‌تر یا کاملاً بازسازی‌شده باشد.\n"
            "تنها چیزی که باید حفظ شود، معنی، نیت، رابطه و حس است.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "قانون دیالوگ\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "فارسی باید شبیه گفت‌وگو باشد، نه متن ادبی.\n"
            "اما «محاوره‌ای» به معنی شکسته‌کردن زورکی همه‌چیز نیست.\n"
            "به شکل طبیعی حرف زدن نگاه کن.\n"
            "بعضی جمله‌ها کوتاه می‌شوند.\n"
            "بعضی جاها مکث می‌آید.\n"
            "بعضی جاها جمله نصفه می‌ماند.\n"
            "بعضی جاها شخصیت یک کلمه را تأکید می‌کند.\n"
            "فقط وقتی این رفتار در خود موقعیت وجود دارد، از آن استفاده کن.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "فحش، توهین و شدت\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "اگر شخصیت فحش می‌دهد، شدت واقعی حرفش را نگه دار.\n"
            "نه ضعیف‌ترش کن، نه بی‌دلیل شدیدترش کن.\n"
            "فحش باید مثل فحش واقعی فارسی انتخاب شود، نه ترجمه‌ی فرهنگ‌لغتی.\n"
            "اگر متن انگلیسی تند است، فارسی هم باید تند به نظر برسد.\n"
            "اگر فقط شوخی یا طعنه است، فحش را بی‌جهت سنگین نکن.\n"
            "فحش سانسور یا OCRخراب خیلی رایج است؛ قبل از ترجمه معنیش را کامل کن:\n"
            "  F*ck / F**k / F*ok / Fu*k / fck → fuck\n"
            "  Sh*t / S**t → shit\n"
            "  what theF / what the F / wtf → what the fuck\n"
            "مثال:\n"
            "  F*ok?! → چه غلطیه؟! / لعنتی!؟\n"
            "  What the F is wrong with you? → چه مرگته؟ / عقلت پاره‌ست؟\n"
            "هرگز حروف سانسور یا عدد/نماد چسبیده به فحش را عین متن به فارسی نبر.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "OCR خراب\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "OCR را متن مقدس و دقیق فرض نکن.\n"
            "اگر کلمه‌ای ناقص، چسبیده، اشتباه، سانسور با * یا خراب است، "
            "از کل جمله و فضای صحنه برای فهم آن استفاده کن.\n"
            "اگر یک بخش واضحاً اشتباه OCR شده، معنای محتمل را بازسازی کن.\n"
            "اما چیزی از خودت اختراع نکن که با صحنه سازگار نیست.\n"
            "عدد یا نماد بی‌معنی وسط کلمه (مثل گوهی5) را حذف کن و جمله را طبیعی بنویس.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "تست نهایی\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "قبل از تحویل هر دیالوگ، سه سؤال را از خودت بپرس:\n"
            "۱. اگر این را یک ایرانی در مکالمه بگوید، طبیعی به گوش می‌رسد؟\n"
            "۲. اگر متن انگلیسی را نبینم، باز هم این جمله مثل یک دیالوگ اصیل فارسی به نظر می‌رسد؟\n"
            "۳. شخصیت واقعاً همین‌طوری حرف می‌زند؟\n"
            "اگر جواب یکی از این‌ها «نه» بود، ترجمه را دوباره بساز.\n\n"
            "هدف نهایی:\n"
            "خواننده نباید هنگام خواندن دیالوگ به یاد ترجمه بیفتد.\n"
            "باید فقط صحنه را ببیند و حرف شخصیت را بشنود.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "نمونه برای فهم فلسفه، نه برای تقلید\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "What the hell are you doing?\n"
            "→ داری چه غلطی می‌کنی؟\n\n"
            "I didn't come here to talk.\n"
            "→ نیومدم اینجا حرف بزنم.\n\n"
            "Don't look at me like that.\n"
            "→ این‌جوری نگام نکن.\n\n"
            "You're kidding, right?\n"
            "→ داری شوخی می‌کنی، نه؟\n\n"
            "I can't believe you actually did that.\n"
            "→ باورم نمی‌شه واقعاً این کارو کردی.\n\n"
            "What?! I'm not a girl!\n"
            "→ چی؟! من دختر نیستم!\n\n"
            "این مثال‌ها فقط نشان می‌دهند خروجی باید «حرفِ واقعی» باشد، نه ترجمه‌ی لفظ‌به‌لفظ.\n"
            "عبارت‌ها را کورکورانه کپی نکن.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "قانون آخر\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "در هر تعارض، این ترتیب اولویت را رعایت کن:\n"
            "طبیعی بودن فارسی > صدای شخصیت > انتقال احساس و نیت > انتقال معنی > شباهت لفظی به انگلیسی\n\n"
            "اسم‌های خاص را حفظ یا طبیعی نویسه‌گردانی کن.\n"
            "هیچ توضیحی درباره‌ی روند کار نده.\n"
            "فقط JSON معتبر برگردان.\n"
            "هر آیتم: {\"id\": عدد, \"translation\": \"متن فارسی\", "
            "\"names\": [{\"source\": \"...\", \"persian\": \"...\"}]}"
        )

    @staticmethod
    def _cleanup_translation(t: str) -> str:
        
        if not t:
            return t
        
        t = t.replace("?", "؟")
        t = re.sub(r"\s+([؟!.,،])", r"\1", t)
        return t.strip()

    def _parse_translation_response(self, text: str, regions: List[TextRegion]) -> bool:
        
        text = text.strip()
        
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        try:
            results = json.loads(text)
        except json.JSONDecodeError:
            
            m = re.search(r"\[[\s\S]*\]", text)
            if not m:
                raise
            results = json.loads(m.group(0))

        if not isinstance(results, list):
            raise ValueError("پاسخ مدل آرایه نیست.")

        by_id = {item["id"]: item.get("translation", "") for item in results if "id" in item}
        applied = 0
        for region in regions:
            t = by_id.get(region.id, "").strip()
            if t:
                region.translated_text = self._cleanup_translation(t)
                applied += 1

        for item in results:
            for nm in (item.get("names") or []):
                src = (nm.get("source") or "").strip()
                per = (nm.get("persian") or "").strip()
                if src and per:
                    self._name_glossary[src] = per
        return applied > 0

    def _translate_with_gemini(self, user_prompt: str, system_instruction: str) -> str:
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
        response = self.client.models.generate_content(
            model=self.model_name, contents=user_prompt, config=config,
        )
        text = response.text
        if not text:
            raise RuntimeError("پاسخ خالی از Gemini دریافت شد.")
        return text

    def _translate_with_openai(self, user_prompt: str, system_instruction: str) -> str:
        kwargs = dict(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.translation_temperature,
        )
        
        mlow = self.model_name.lower()
        if any(x in mlow for x in ("gpt-4", "gpt-3.5", "gpt-5", "o1", "o3", "o4")):
            kwargs["response_format"] = {"type": "json_object"}

        resp = self.openai_client.chat.completions.create(**kwargs)
        text = resp.choices[0].message.content
        if not text:
            raise RuntimeError(f"پاسخ خالی از {self.provider} دریافت شد.")
        return text


    @staticmethod
    def _fix_ocr_text(text: str) -> str:
        
        if not text:
            return text
        t = text
        
        t = re.sub(r"\s+", " ", t).strip()
        
        replacements = [
            (r"\bMUDI[:]?YING\b", "MODIFYING"),
            (r"\bMODIEYING\b", "MODIFYING"),
            (r"\bMODIFYlNG\b", "MODIFYING"),
            (r"\bRECONSTRUC(?:TION)?\b", "RECONSTRUCTION"),
            (r"\bRECONSTRUC\b", "RECONSTRUCTION"),
            (r"\bPROCES\b", "PROCESS"),
            (r"\bPARALYZE[D]?\b", "PARALYZED"),
            (r"\bMANA\b", "MANA"),
            (r"\bAND\s+YE\b", "AND YET"),
            (r"\bNDYE\b", "AND YET"),
            (r"\bONL\b", "ONLY"),
            (r"\bMYE\b", "MY"),
            (r"\bUNSCATHED\b", "UNSCATHED"),
            (r"\bUNFORESEEN\b", "UNFORESEEN"),
            (r"\bOVERCONSUMPTION\b", "OVERCONSUMPTION"),
            (r"\bRECONSTRUCTION\s+PROCES\b", "RECONSTRUCTION PROCESS"),
            (r"\bBODY\s+RECONSTRUCTION\b", "BODY RECONSTRUCTION"),
        ]
        for pat, rep in replacements:
            t = re.sub(pat, rep, t, flags=re.IGNORECASE)
        
        t = re.sub(r"([A-Za-z])[:;|]([A-Za-z])", r"\1\2", t)
        
        t = re.sub(r"\s*[QOIl]?\d{3,}\s*$", "", t, flags=re.I).strip()
        t = re.sub(r"\s+\d{3,}\s*$", "", t).strip()
        return t.strip()

    def translate_regions(self, regions: List[TextRegion]) -> None:
        if not regions:
            return

        
        
        for r in regions:
            r.source_text = self._fix_ocr_text(uncensor_swears(r.source_text or ""))

        payload = [{"id": r.id, "text": r.source_text} for r in regions]
        system_instruction = self._get_system_instruction()
        user_prompt = (
            "این‌ها دیالوگ‌های استخراج‌شده از یک صفحه‌ی مانهوا هستند.\n\n"
            "متن‌ها از OCR آمده‌اند و ممکن است خراب، ناقص، چسبیده یا دارای غلط املایی باشند.\n"
            "قبل از بازآفرینی فارسی، اول متن انگلیسی هر مورد را در ذهن خودت اصلاح کن "
            "(مثلاً MUDIYING→MODIFYING، NDYE/AND YE→AND YET، RECONSTRUC→RECONSTRUCTION).\n"
            "سپس با توجه به ترتیب دیالوگ‌ها و بافت صحنه، هر مورد را به شکل یک دیالوگ کاملاً طبیعی فارسی بازآفرینی کن.\n\n"
            "اصل مهم:\n"
            "ترجمه تحت‌اللفظی نکن؛ دیالوگ را طوری بنویس که انگار از اول به فارسی نوشته شده.\n"
            "اگر دو حباب پشت‌سرهم ادامه‌ی یک فکر هستند، لحن را پیوسته نگه دار.\n\n"
            "هیچ توضیح، تحلیل یا متن اضافه ننویس.\n"
            "فقط JSON معتبر مطابق ساختار ورودی برگردان (هر آیتم: id + translation).\n\n"
            f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
        )

        delay = 3.0
        last_err = None
        work_regions = list(regions)

        for attempt in range(1, self.max_retries + 1):
            try:
                if self.provider_type == "gemini":
                    text = self._translate_with_gemini(user_prompt, system_instruction)
                else:
                    text = self._translate_with_openai(user_prompt, system_instruction)

                
                try:
                    cleaned = text.strip()
                    if cleaned.startswith("```"):
                        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
                        cleaned = re.sub(r"\s*```$", "", cleaned)
                    parsed = json.loads(cleaned.strip())
                    if isinstance(parsed, dict):
                        for key in ("translations", "results", "data", "items"):
                            if key in parsed and isinstance(parsed[key], list):
                                text = json.dumps(parsed[key], ensure_ascii=False)
                                break
                        else:
                            
                            if "id" in parsed and "translation" in parsed:
                                text = json.dumps([parsed], ensure_ascii=False)
                except Exception:
                    pass

                self._parse_translation_response(text, work_regions)

                missing = [r for r in work_regions if not r.translated_text]
                if missing and attempt < self.max_retries:
                    print(f"    [!] {len(missing)} حباب بدون ترجمه؛ تلاش مجدد...")
                    payload2 = [{"id": r.id, "text": r.source_text} for r in missing]
                    user_prompt = (
                        "اینا موندن بازآفرینی بشن. ترجمه نکن؛ دیالوگ طبیعی فارسی بساز. "
                        "فقط JSON معتبر:\n"
                        f"{json.dumps(payload2, ensure_ascii=False, indent=2)}"
                    )
                    work_regions = missing
                    continue

                print(f"[فاز ۳ - ترجمه با {self.provider}/{self.model_name}] پاسخ کامل دریافت شد.")
                if self.request_delay > 0:
                    time.sleep(self.request_delay)
                return

            except Exception as e:
                last_err = e
                err_str = str(e).lower()

                
                if self.provider_type == "gemini" and _HAS_GEMINI:
                    if isinstance(e, genai_errors.ClientError) if genai_errors else False:
                        if self._is_daily_quota_error(e):
                            print(f"    [!] سهمیه‌ی کلید {self._key_index + 1}/{len(self._api_keys)} تموم شد.")
                            if self._switch_to_next_key(reason="سهمیه روزانه"):
                                continue
                            raise GeminiQuotaExhausted(
                                f"سهمیه‌ی همه‌ی کلیدها تموم شده."
                            ) from e
                        if self._is_banned_or_invalid_key_error(e):
                            if self._remove_current_key_and_switch(reason=str(e)[:120]):
                                continue
                            raise GeminiQuotaExhausted("همه کلیدها نامعتبر/بن شدند.") from e

                    if self._is_model_unavailable_error(e):
                        if self._is_model_permanently_gone(e):
                            if self._drop_current_model_and_switch(reason="404"):
                                time.sleep(0.2)
                                continue
                        else:
                            if self._switch_to_next_model(reason="UNAVAILABLE"):
                                time.sleep(0.3)
                                continue
                        if self._switch_to_next_key(reason="model unavailable", cycle=True):
                            time.sleep(min(delay, 3))
                            continue

                
                if any(x in err_str for x in ("rate limit", "429", "quota", "insufficient_quota")):
                    print(f"    [!] محدودیت نرخ/سهمیه ({self.provider})...")
                    if self._switch_to_next_key(reason="rate/quota", cycle=True):
                        time.sleep(min(delay, 5))
                        continue
                if any(x in err_str for x in ("invalid api key", "authentication", "401", "403", "incorrect api key")):
                    print(f"    [!] کلید نامعتبر ({self.provider})...")
                    if self._remove_current_key_and_switch(reason=str(e)[:100]):
                        continue

                print(f"    [!] تلاش {attempt}/{self.max_retries} ناموفق: {last_err}")
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
        
        if size <= 14:
            return 1
        if size <= 22:
            return 2
        return max(2, size // 16)

    def _wrap_and_fit(
        self, draw: ImageDraw.ImageDraw, text: str, max_w: int, max_h: int
    ) -> Tuple[ImageFont.FreeTypeFont, List[str], int]:
        
        words = text.split()
        if not words:
            words = [""]

        
        def wrap_at(size: int, line_gap: int):
            font = self._load_font(size)
            sw = self._stroke_width_for(size)
            
            usable_w = max(8, max_w - 2 * sw)
            lines: List[str] = []
            current = ""
            for word in words:
                candidate = f"{current} {word}".strip()
                w = draw.textbbox(
                    (0, 0), self._shape_farsi(candidate), font=font, stroke_width=sw
                )[2]
                if w <= usable_w or not current:
                    current = candidate
                else:
                    lines.append(current)
                    current = word
            if current:
                lines.append(current)

            
            bb = font.getbbox("آیگچ", stroke_width=sw)
            glyph_h = bb[3] - bb[1]
            line_h = glyph_h + line_gap
            total_h = line_h * len(lines) if lines else line_h
            
            total_h += 2 * sw
            widest = max(
                (
                    draw.textbbox(
                        (0, 0), self._shape_farsi(l), font=font, stroke_width=sw
                    )[2]
                    for l in lines
                ),
                default=0,
            )
            return font, lines, sw, total_h, widest, line_h

        
        n_words = len(words)
        short_text = n_words <= 2 and sum(len(w) for w in words) <= 12
        min_size = 14 if short_text else 11
        max_size = 48

        smallest_attempt = None
        
        for line_gap in (4, 2, 1, 0):
            for size in range(max_size, min_size - 1, -1):
                font, lines, sw, total_h, widest, line_h = wrap_at(size, line_gap)
                smallest_attempt = (font, lines, sw, line_h)
                if total_h <= max_h and widest <= max_w:
                    return font, lines, sw

        
        for size in range(min_size - 1, 9, -1):
            font, lines, sw, total_h, widest, line_h = wrap_at(size, 0)
            smallest_attempt = (font, lines, sw, line_h)
            if total_h <= max_h and widest <= max_w:
                return font, lines, sw

        if smallest_attempt is None:
            font = self._load_font(11)
            sw = self._stroke_width_for(11)
            return font, [" ".join(words)], sw
        return smallest_attempt[0], smallest_attempt[1], smallest_attempt[2]

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
            
            short = len((region.translated_text or "").split()) <= 2
            if short and (w < 90 or h < 50):
                expand = max(6, int(max(w, h) * 0.15))
                x = max(0, x - expand // 2)
                y = max(0, y - expand // 2)
                w = w + expand
                h = h + expand
            
            pad = max(3, int(min(w, h) * (0.05 if short else 0.08)))
            box_w = max(14, w - 2 * pad)
            box_h = max(14, h - 2 * pad)

            font, lines, sw = self._wrap_and_fit(draw, region.translated_text, box_w, box_h)
            text_rgb, stroke_rgb = self._pick_text_and_stroke(image, original_image, region)

            angle = getattr(region, "angle", 0.0)

            if abs(angle) < 8:
                bb = font.getbbox("آیگچ", stroke_width=sw)
                glyph_h = bb[3] - bb[1]
                
                n = max(1, len(lines))
                
                avail = max(glyph_h, box_h - 2 * sw)
                line_h = max(glyph_h + 1, avail // n) if n else glyph_h + 2
                
                if line_h * n + 2 * sw > box_h:
                    line_h = max(glyph_h, (box_h - 2 * sw) // n)
                total_h = line_h * n
                start_y = y + pad + max(0, (box_h - total_h) // 2)
                
                bottom_limit = y + pad + box_h

                for i, line in enumerate(lines):
                    shaped = self._shape_farsi(line)
                    line_w = draw.textbbox((0, 0), shaped, font=font, stroke_width=sw)[2]
                    line_x = x + pad + max(0, (box_w - line_w) // 2)
                    line_y = start_y + i * line_h
                    if line_y + glyph_h > bottom_limit + sw:
                        break
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

        h_p, w_p = piece.shape[:2]

        
        scale = float(getattr(self, "mag_ratio", 1.35) or 1.35)

        
        if max(h_p, w_p) < 2200:
            scale = max(scale, 1.8)
        if max(h_p, w_p) < 1600:
            scale = max(scale, 2.2)

        if scale > 1.01:
            piece_up = cv2.resize(piece, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        else:
            piece_up = piece
            scale = 1.0

        detections = self.detect_text(piece_up)

        if self.two_pass_ocr:
            
            enhanced = self._clahe_enhance(piece_up)
            detections += self.detect_text(enhanced)

            
            inverted = cv2.bitwise_not(piece_up)
            detections += self.detect_text(inverted)

            
            gray = cv2.cvtColor(piece_up, cv2.COLOR_BGR2GRAY)
            _, bw = cv2.threshold(gray, 160, 255, cv2.THRESH_BINARY)
            if float(np.mean(bw)) < 127:
                bw = cv2.bitwise_not(bw)
            bw = cv2.dilate(bw, np.ones((2, 2), np.uint8), iterations=1)
            bw_bgr = cv2.cvtColor(bw, cv2.COLOR_GRAY2BGR)
            detections += self.detect_text(bw_bgr)

            
            if scale < 2.0 and max(h_p, w_p) < 2800:
                try:
                    extra_scale = 2.0 / scale
                    up_inv = cv2.resize(
                        inverted, None, fx=extra_scale, fy=extra_scale,
                        interpolation=cv2.INTER_CUBIC
                    )
                    up_inv_dets = self.detect_text(up_inv)
                    for d in up_inv_dets:
                        d["poly"] = (d["poly"].astype(np.float32) / extra_scale).astype(np.int32)
                    detections += up_inv_dets
                except Exception:
                    pass

        
        if scale != 1.0:
            for d in detections:
                d["poly"] = (d["poly"].astype(np.float32) / scale).astype(np.int32)

        detections = self._dedupe_detections(detections)
        return self.group_into_regions(detections, y_offset=y0)


    def _draw_debug_regions(self, image: np.ndarray, regions: List[TextRegion]) -> np.ndarray:
      vis = image.copy()

    
      colors = {
        "dialogue": (0, 0, 255),      
        "promo": (0, 165, 255),       
        "sfx": (255, 255, 0),         
        "junk": (128, 128, 128),      
    }

      for r in regions:
        x, y, w, h = r.rect
        color = colors.get(r.kind, (0, 0, 255))

        
        cv2.rectangle(vis, (x, y), (x + w, y + h), color, 2)

        
        cx = x + w // 2
        
        cv2.line(vis, (cx, y), (cx, y + h), (255, 0, 255), 2)  

        
        cv2.circle(vis, (cx, y + h // 2), 4, (0, 255, 255), -1)  

        
        label = f"[{r.id}] {r.kind[:3].upper()}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        cv2.rectangle(vis, (x, y - th - 6), (x + tw + 4, y), color, -1)
        cv2.putText(vis, label, (x + 2, y - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)

        
        short = (r.source_text or "")[:28]
        if short:
            cv2.putText(vis, short, (x, y + h + 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 200, 0), 1, cv2.LINE_AA)

      return vis

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

        dialogue_regions = [r for r in unique_regions if r.kind == "dialogue"]
        promo_regions = [r for r in unique_regions if r.kind == "promo"]
        sfx_regions = [r for r in unique_regions if r.kind == "sfx"]
        junk_regions = [r for r in unique_regions if r.kind == "junk"]

        print(f"[فاز ۱ - OCR] انجام شد. مجموع {len(unique_regions)} بلوک "
              f"(دیالوگ={len(dialogue_regions)} | تبلیغ={len(promo_regions)} | "
              f"SFX={len(sfx_regions)} | junk={len(junk_regions)})")
        for r in unique_regions:
            tag = {"dialogue": "متن", "promo": "تبلیغ", "sfx": "SFX", "junk": "junk"}.get(r.kind, r.kind)
            print(f"  [{r.id}] ({tag}) {r.source_text}")

        
        if self.debug:
            debug_vis = self._draw_debug_regions(image, unique_regions)
            self._last_debug_image = debug_vis
            print(f"  [*] DEBUG: تصویر دیباگ با {len(unique_regions)} مربع آماده شد.")
        else:
            self._last_debug_image = None

        raw_image_copy = image.copy()

        
        if dialogue_regions:
            print("[فاز ۳ - تفکر و ترجمه] ارسال درخواست به Gemini (با فرآیند خود-اصلاحی)...")
            self.translate_regions(dialogue_regions)
        else:
            print("[فاز ۳ - تفکر و ترجمه] دیالوگ معتبری برای ترجمه نبود.")

        translated_regions = [r for r in dialogue_regions if r.translated_text]

        print("--- بررسی نهایی نتایج ترجمه ---")
        for r in translated_regions:
            print(f"  EN: {r.source_text}")
            print(f"  FA: {r.translated_text}")
        if promo_regions:
            print(f"  [*] {len(promo_regions)} تبلیغ/واترمارک → دست نخورده می‌ماند.")
        if sfx_regions:
            print(f"  [*] {len(sfx_regions)} SFX → دست نخورده می‌ماند.")
        if junk_regions:
            print(f"  [*] {len(junk_regions)} junk → دست نخورده می‌ماند.")

        
        
        to_clean = translated_regions
        print("[فاز ۴ - رندر نهایی] شروع جایگذاری و ذخیره...")
        if to_clean:
            cleaned_image = self.clean_image(image, to_clean)
            final_image = self.render_translations(cleaned_image, to_clean, raw_image_copy)
            print("  - رندر متن فارسی روی تصویر موفق بود.")
        else:
            final_image = image.copy()
            print("  - ترجمه‌ای برای رندر نبود؛ تصویر بدون تغییر.")

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
    def _expand_input_urls(input_str: str) -> List[str]:
        import requests

        parts = [p.strip() for p in input_str.split(",") if p.strip()]
        if not parts:
            return []

        expanded: List[str] = []

        for part in parts:
            if "*" not in part:
                expanded.append(part)
                continue

            m = re.search(r"(.*?)(\d*)\*(\d*)(.*)", part)
            if not m:
                print(f"[!] الگوی * قابل تشخیص نیست: {part}")
                expanded.append(part)
                continue

            prefix = m.group(1)
            suffix = m.group(4)

            print(f"[*] در حال پیدا کردن فصل‌های موجود برای الگو: {part}")
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            }

            found = []
            consecutive_fail = 0
            max_fail = 5
            max_chapters = 500

            for n in range(1, max_chapters + 1):
                candidate = f"{prefix}{n}{suffix}"
                try:
                    r = requests.head(
                        candidate, headers=headers, timeout=12, allow_redirects=True
                    )
                    if r.status_code == 200:
                        found.append(candidate)
                        consecutive_fail = 0
                        print(f"    [+] فصل {n} پیدا شد")
                    else:
                        consecutive_fail += 1
                except Exception:
                    consecutive_fail += 1

                if consecutive_fail >= max_fail:
                    break

            if found:
                print(f"[*] مجموعاً {len(found)} فصل پیدا شد.")
                expanded.extend(found)
            else:
                print(f"[!] هیچ فصلی با الگو پیدا نشد: {part}")

        seen = set()
        unique = []
        for u in expanded:
            if u not in seen:
                seen.add(u)
                unique.append(u)
        return unique
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
        raw_html = resp.text if hasattr(resp, "text") else resp.content.decode("utf-8", errors="ignore")

        
        json_page_urls = []
        for m in re.finditer(
            r"https?://[^\"'\\s<>]+?\.(?:jpe?g|png|webp)(?:\?[^\"'\\s<>]*)?",
            raw_html,
            flags=re.I,
        ):
            cand = m.group(0).rstrip("\\").replace("\\/", "/")
            low = cand.lower()
            if any(k in low for k in ("/chapter", "/chapters/", "/comic/", "/manga/", "/pages/", "/sv2/")):
                if not MangaTranslator._is_junk_image_url(cand):
                    json_page_urls.append(MangaTranslator._normalize_image_url(cand))

        if json_page_urls:
            for u in json_page_urls:
                key = u.split("?")[0].lower()
                if key in seen:
                    continue
                seen.add(key)
                img_urls.append(u)
            print(f"    [*] {len(img_urls)} صفحه از JSON/HTML به ترتیب پیدا شد.")

        for img in soup.find_all("img"):
            for src in MangaTranslator._extract_src_candidates(img):
                if not src or src.startswith("data:"):
                    continue
                full_url = MangaTranslator._normalize_image_url(urljoin(url, src))
                key = full_url.split("?")[0].lower()
                if key in seen:
                    continue
                if MangaTranslator._is_junk_image_url(full_url):
                    continue
                seen.add(key)
                img_urls.append(full_url)

        for a in soup.find_all("a", href=True):
            href = a["href"]
            low = href.lower().split("?")[0]
            if any(low.endswith(e) for e in (".jpg", ".jpeg", ".png", ".webp")):
                full_url = MangaTranslator._normalize_image_url(urljoin(url, href))
                key = full_url.split("?")[0].lower()
                if key not in seen and not MangaTranslator._is_junk_image_url(full_url):
                    seen.add(key)
                    img_urls.append(full_url)

        if not img_urls:
            print("    [!] هیچ تگ تصویری معتبری در صفحه پیدا نشد.")
            return []

        img_urls = MangaTranslator._try_extend_sequential(img_urls, headers)

        
        deduped = []
        seen_u = set()
        for u in img_urls:
            key = u.split("?")[0].lower()
            if key in seen_u:
                continue
            seen_u.add(key)
            deduped.append(u)
        img_urls = deduped

        
        numbered = []
        for u in img_urls:
            m = re.search(r"/(\d+)\.(?:jpe?g|png|webp)(?:\?|$)", u.lower())
            if m:
                numbered.append(True)
            else:
                numbered.append(False)
        use_numeric_sort = sum(numbered) >= max(3, int(len(img_urls) * 0.6))

        if use_numeric_sort:
            def _page_sort_key(u: str):
                low = u.lower().split("?")[0]
                if any(k in low for k in ("/chapter", "/chapters/", "/comic/", "/manga/", "/pages/")):
                    pri = 0
                elif re.search(r"/\d+\.(jpe?g|png|webp)$", low):
                    pri = 1
                else:
                    pri = 2
                m = re.search(r"/(\d+)\.(?:jpe?g|png|webp)$", low)
                num = int(m.group(1)) if m else 10**9
                return (pri, num, low)

            img_urls = sorted(img_urls, key=_page_sort_key)
            print(f"    [*] مرتب‌سازی عددی صفحات ({len(img_urls)} تصویر).")
        else:
            print(f"    [*] ترتیب HTML حفظ شد ({len(img_urls)} تصویر، بدون شماره ترتیبی).")

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
            else:
                slug = parts[-1]
                
                m = re.search(
                    r"(.+?-chapter[-_]?(?:\d+|\*))(?:[-_].*)?$",
                    slug,
                    flags=re.I,
                )
                if m:
                    base = m.group(1)
                elif "chapter" in [p.lower() for p in parts]:
                    low_parts = [p.lower() for p in parts]
                    try:
                        idx = low_parts.index("chapter")
                        name = parts[idx - 1] if idx > 0 else "chapter"
                        num = parts[idx + 1] if idx + 1 < len(parts) else ""
                        num = re.sub(r"[^\w\-]", "", num.split("?")[0])
                        base = f"{name}-{num}" if num else name
                    except ValueError:
                        base = slug
                else:
                    base = slug
            base = re.sub(r"\*+", "", base)
            base = re.sub(r"[^\w\-.]+", "-", base)
            base = re.sub(r"-{2,}", "-", base).strip("-._")
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

    @staticmethod
    def _extract_title_skips_from_path(path_or_url: str) -> List[str]:
        from urllib.parse import urlparse, unquote

        raw = path_or_url.strip()
        if MangaTranslator._is_url(raw):
            path = unquote(urlparse(raw).path)
        else:
            path = raw

        
        parts = [p for p in re.split(r"[/\\]+", path) if p]
        skip: List[str] = []
        noise = {
            "comics", "comic", "manga", "manhwa", "reader", "en", "chapter",
            "chapters", "series", "title", "www", "http", "https", "cdn",
            "asurascans", "asura", "mgeko", "webtoon", "page", "pages",
        }

        candidates = []
        for p in parts:
            pl = p.lower()
            if re.fullmatch(r"\d+", pl):
                continue
            if pl in noise:
                continue
            if pl.endswith((".jpg", ".png", ".webp", ".jpeg", ".html", ".pdf")):
                continue
            
            cleaned = re.sub(r"^[a-z]{0,4}\d+-", "", pl)
            cleaned = re.sub(r"-[a-f0-9]{6,}$", "", cleaned)  
            if cleaned and cleaned not in noise:
                candidates.append(cleaned)
            if pl not in candidates and pl not in noise:
                candidates.append(pl)

        for c in candidates:
            
            compact = re.sub(r"[^a-z0-9]", "", c)
            if len(compact) >= 5:
                skip.append(compact)
            tokens = [t for t in re.split(r"[-_]+", c) if t and t not in noise and not t.isdigit()]
            if len(tokens) >= 2:
                
                for n in range(2, min(len(tokens), 4) + 1):
                    for i in range(0, len(tokens) - n + 1):
                        chunk = "".join(tokens[i:i + n])
                        if len(chunk) >= 5:
                            skip.append(chunk)
                
                full = "".join(tokens)
                if len(full) >= 5:
                    skip.append(full)

        seen = set()
        out = []
        for s in skip:
            if s not in seen:
                seen.add(s)
                out.append(s)
        return out

    def _stitch_pages_for_efficiency(
        self,
        image_files: List[str],
        work_dir: str,
    ) -> List[str]:
        if self.stitch_max_height <= 0 or len(image_files) <= 1:
            return image_files

        short_max = (
            self.stitch_short_threshold
            if self.stitch_short_threshold > 0
            else self.stitch_max_height
        )
        max_h = self.stitch_max_height

        os.makedirs(work_dir, exist_ok=True)
        result: List[str] = []
        start_idx = 0

        if self.stitch_keep_first and len(image_files) >= 1:
            first_out = os.path.join(
                work_dir, "strip_000_cover" + os.path.splitext(image_files[0])[1]
            )
            if not os.path.isfile(first_out):
                shutil.copy2(image_files[0], first_out)
            result.append(first_out)
            start_idx = 1
            if start_idx >= len(image_files):
                return result

        
        raw_pages: List[np.ndarray] = []
        widths = []
        for f in image_files[start_idx:]:
            im = cv2.imread(f)
            if im is None:
                print(f"    [!] خواندن نشد، رد شد: {os.path.basename(f)}")
                continue
            widths.append(im.shape[1])
            raw_pages.append(im)
        if not raw_pages:
            return image_files
        widths.sort()
        target_w = widths[len(widths) // 2]

        
        normalized: List[np.ndarray] = []
        for im in raw_pages:
            h, w = im.shape[:2]
            if w != target_w:
                new_h = max(1, int(round(h * (target_w / float(w)))))
                im = cv2.resize(im, (target_w, new_h), interpolation=cv2.INTER_AREA)
            normalized.append(im)

        strip_i = 0
        short_count = 0
        tall_count = 0

        def emit_image(img: np.ndarray, label: str) -> None:
            nonlocal strip_i
            out_path = os.path.join(work_dir, f"strip_{strip_i + 1:03d}.jpg")
            self._write_image(img, out_path)
            result.append(out_path)
            print(f"    [+] نوار {strip_i + 1}: {label} ({img.shape[0]}px)")
            strip_i += 1

        def split_and_emit(long_img: np.ndarray, n_pages: int) -> None:
            total_h = long_img.shape[0]
            if total_h <= max_h:
                emit_image(
                    long_img,
                    f"نوار چسبیده ({n_pages} صفحه، تمام {total_h}px)",
                )
                return
            y = 0
            part = 0
            while y < total_h:
                y2 = min(y + max_h, total_h)
                if 0 < (total_h - y2) < int(max_h * 0.15):
                    y2 = total_h
                chunk = long_img[y:y2]
                part += 1
                emit_image(
                    chunk,
                    f"تکه {part} از نوار ({n_pages} صفحه، برش {y}:{y2})",
                )
                y = y2

        buffer: List[np.ndarray] = []

        def flush_buffer() -> None:
            nonlocal buffer, short_count
            if not buffer:
                return
            n = len(buffer)
            short_count += n
            merged = np.vstack(buffer)
            print(
                f"    [*] چسباندن {n} صفحهٔ کوتاه → نوار {merged.shape[0]}px "
                f"سپس برش تا سقف {max_h}px"
            )
            split_and_emit(merged, n)
            buffer = []

        for img in normalized:
            h = img.shape[0]
            if h >= short_max:
                flush_buffer()
                if h > max_h:
                    print(f"    [*] صفحهٔ بلند {h}px → برش به سقف {max_h}px")
                    split_and_emit(img, 1)
                else:
                    emit_image(img, f"صفحهٔ بلند تکی (≥{short_max}px)")
                tall_count += 1
            else:
                buffer.append(img)

        flush_buffer()

        print(
            f"[*] چسباندن صفحات: {len(image_files)} صفحه → {len(result)} نوار "
            f"(کوتاه<{short_max}px={short_count} | بلند={tall_count} | "
            f"سقف برش={max_h}px"
            f"{'، صفحهٔ اول جدا' if self.stitch_keep_first else ''})"
        )
        return result if result else image_files

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

        
        title_skips = self._extract_title_skips_from_path(input_path)
        self._title_skip_patterns = title_skips
        MangaTranslator._title_skip_patterns = title_skips
        MangaTranslator._title_skip_enabled = False
        if title_skips:
            print(f"[*] عنوان سری (فقط صفحه ۱): {', '.join(title_skips[:8])}"
                  + ("…" if len(title_skips) > 8 else ""))

        if self._is_url(input_path) or "," in input_path or "*" in input_path:
            urls = self._expand_input_urls(input_path)

            if not urls:
                print("[!] هیچ لینک معتبری پیدا نشد.", file=sys.stderr)
                return

            if len(urls) == 1:
                print(f"[*] دانلود تصاویر از لینک: {urls[0]}")
                image_files = self._download_images_from_url(urls[0], src_dir)
            else:
                print(f"[*] {len(urls)} فصل پیدا شد. هر فصل جداگانه پردازش می‌شه...")
                out_ext = os.path.splitext(output_path)[1].lower()
                chapter_ext = out_ext if out_ext in (".pdf", ".zip", ".html") else ".pdf"
                for i, url in enumerate(urls, 1):
                    print(f"\n{'='*60}")
                    print(f"[فصل {i}/{len(urls)}] {url}")
                    print(f"{'='*60}")
                    chapter_out = self._auto_output_path(url, chapter_ext)
                    if not os.path.splitext(chapter_out)[1]:
                        parent = (output_path if not out_ext else (os.path.dirname(output_path) or "."))
                        chapter_out = os.path.join(parent, os.path.basename(chapter_out.rstrip("/\\")) + chapter_ext)

                    self.run(url, chapter_out, resume=resume, clean_old=False)
                return
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

        
        if self.stitch_max_height > 0 and len(image_files) > 1:
            stitch_dir = os.path.join(cache_dir, "stitched")
            image_files = self._stitch_pages_for_efficiency(image_files, stitch_dir)

        processed_files = []
        skipped = 0
        page_ext = "." + self.img_format if self.img_format != "jpg" else ".jpg"

        for page_i, f in enumerate(image_files):
            
            MangaTranslator._title_skip_enabled = (page_i == 0)

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

            
            if self.debug and self._last_debug_image is not None:
                debug_dir = os.path.join(cache_dir, "debug")
                os.makedirs(debug_dir, exist_ok=True)
                dbg_name = os.path.splitext(os.path.basename(out_file))[0] + "_debug.jpg"
                dbg_path = os.path.join(debug_dir, dbg_name)
                self._write_image(self._last_debug_image, dbg_path)
                print(f"  [*] DEBUG ذخیره شد: {dbg_path}")
                
                self._last_debug_image = None

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
    p = argparse.ArgumentParser(
        description="مترجم خودکار مانگا/مانهوا به فارسی — پشتیبانی از Gemini / OpenAI / DeepSeek / Groq / xAI / Ollama و ..."
    )
    p.add_argument("-i", "--input", required=True)
    p.add_argument("-o", "--output", required=True,
                   help="مسیر خروجی: پوشه، فایل کامل، یا فقط پسوند (.pdf / .zip / .html)")
    p.add_argument(
        "--provider",
        default="gemini",
        choices=list(PROVIDER_PRESETS.keys()),
        help="ارائه‌دهنده AI: gemini | openai | chatgpt | deepseek | groq | xai | grok | together | openrouter | ollama"
    )
    p.add_argument("--api-key", action="append", default=None,
                   help="کلید API. چندبار یا با کاما. env متناظر هم خوانده می‌شود")
    p.add_argument("--api-base", default=None,
                   help="آدرس پایه API (اختیاری)")
    p.add_argument("--font", required=True)
    p.add_argument("--ocr-lang", nargs="+", default=["en"],
                   help="زبان‌های OCR. en | ko en | ja en")
    p.add_argument("--model", default=None,
                   help="نام مدل. اگر ندهی از پیش‌فرض provider استفاده می‌شود")
    p.add_argument("--reading-order", choices=["rtl", "ltr"], default="rtl")
    p.add_argument("--gpu", dest="gpu", action="store_true", default=None)
    p.add_argument("--cpu", dest="gpu", action="store_false")
    p.add_argument("--no-resume", action="store_true")
    p.add_argument("--keep-old", action="store_true")
    p.add_argument("--request-delay", type=float, default=0.0)
    p.add_argument("--max-retries", type=int, default=4)
    p.add_argument("--max-chunk-height", type=int, default=3600,
                   help="حداکثر ارتفاع هر تکه OCR داخل یک تصویر (پیکسل)")
    p.add_argument("--stitch-max-height", type=int, default=16000,
                   help="سقف ارتفاع هر نوار چسبانده‌شده (پیش‌فرض ۱۶۰۰۰). ۰ = خاموش.")
    p.add_argument("--stitch-short-threshold", type=int, default=6000,
                   help="صفحاتی کوتاه‌تر از این ارتفاع (پیش‌فرض ۶۰۰۰px) با هم چسبانده "
                        "می‌شوند تا به سقف --stitch-max-height برسند. "
                        "صفحات بلندتر جدا می‌مانند.")
    p.add_argument("--no-stitch-keep-first", action="store_true",
                   help="صفحهٔ اول را هم داخل نوارها بگذار (پیش‌فرض: صفحهٔ اول جدا می‌ماند)")
    p.add_argument("--img-format", choices=["webp", "png", "jpg"], default="jpg")
    p.add_argument("--quality", type=int, default=80)
    p.add_argument("--max-width", type=int, default=900)
    p.add_argument("--min-confidence", type=float, default=0.12)
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--mask-padding", type=int, default=3)
    p.add_argument("--pad-ratio", type=float, default=0.06)
    p.add_argument("--inpaint-radius", type=int, default=3)
    p.add_argument("--mag-ratio", type=float, default=1.35)
    p.add_argument("--no-two-pass-ocr", action="store_true")
    p.add_argument("--temperature", type=float, default=0.85)
    p.add_argument(
        "--debug",
        action="store_true",
        help="حالت دیباگ: مربع رنگی دور هر بلوک متن روی تصویر (ذخیره در *.cache/debug/)",
    )
    return p


def main():
    args = build_arg_parser().parse_args()

    provider = (args.provider or "gemini").lower().strip()
    if provider not in PROVIDER_PRESETS:
        print(f"خطا: provider ناشناخته «{provider}»", file=sys.stderr)
        sys.exit(1)

    keys: List[str] = []
    if args.api_key:
        for item in args.api_key:
            keys.extend(k.strip() for k in item.replace(";", ",").split(",") if k.strip())

    env_name = PROVIDER_PRESETS[provider].get("env_key", "")
    if env_name:
        env_val = os.environ.get(env_name, "")
        if env_val:
            keys.extend(k.strip() for k in env_val.replace(";", ",").split(",") if k.strip())

    for fallback_env in ("GEMINI_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY", "API_KEY"):
        if fallback_env != env_name:
            v = os.environ.get(fallback_env, "")
            if v:
                keys.extend(k.strip() for k in v.replace(";", ",").split(",") if k.strip())

    seen = set()
    unique_keys = []
    for k in keys:
        if k not in seen:
            seen.add(k)
            unique_keys.append(k)

    if not unique_keys and provider != "ollama":
        print(
            f"خطا: حداقل یک کلید API لازم است (--api-key یا env: {env_name}).",
            file=sys.stderr,
        )
        sys.exit(1)

    output_path = MangaTranslator._auto_output_path(args.input, args.output)
    if output_path != args.output:
        print(f"[*] نام خروجی خودکار: {output_path}")

    translator = MangaTranslator(
        api_key=unique_keys or ["ollama"],
        provider=provider,
        ocr_langs=args.ocr_lang,
        model_name=args.model,
        api_base=args.api_base,
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
        stitch_max_height=args.stitch_max_height,
        stitch_short_threshold=args.stitch_short_threshold,
        stitch_keep_first=not args.no_stitch_keep_first,
        debug=bool(getattr(args, "debug", False)),
    )
    translator.run(
        args.input,
        output_path,
        resume=not args.no_resume,
        clean_old=not args.keep_old,
    )


if __name__ == "__main__":
    main()
