#!/usr/bin/env python3
import os
import sys
import glob

import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import manga

OUT = sys.argv[1]
INP = sys.argv[2]

def ocr_texts(tr, img):
    res = []
    try:
        boxes = tr.det.detect(img)
    except Exception:
        boxes = []
    for b in boxes:
        r = b.get("rect")
        if not r:
            continue
        x, y, w, h = [int(v) for v in r]
        x0 = max(0, x - 6)
        y0 = max(0, y - 6)
        x1 = min(img.shape[1], x + w + 7)
        y1 = min(img.shape[0], y + h + 7)
        if x1 - x0 < 8 or y1 - y0 < 8:
            continue
        crop = img[y0:y1, x0:x1]
        try:
            txt, score = tr.ocr_read(crop)
        except Exception:
            continue
        txt = (txt or "").strip()
        if txt and score >= 0.45:
            res.append((txt, score, (x, y, w, h)))
    return res

def main():
    tr = manga.MangaTranslator(
        api_key=["dummy"], provider="gemini", ocr_langs=["en"],
        font_path="fonts/Sahel-Bold.ttf",
        reading_order="rtl", gpu=False, clean_method="opencv",
        det_confidence=0.16, min_confidence=0.12,
        two_pass_ocr=False, img_format="jpg",
    )
    outs = sorted(glob.glob(os.path.join(OUT, "*")))
    if not outs:
        print("!! خروجی‌ای پیدا نشد")
        return
    total_left = 0
    for op in outs:
        if not os.path.isfile(op):
            continue
        base = os.path.splitext(os.path.basename(op))[0]
        cands = glob.glob(os.path.join(INP, base + ".*"))
        print(f"\n===== {os.path.basename(op)} =====")
        im_o = cv2.imread(op)
        if im_o is None:
            print("  خواندن نشد")
            continue
        found = ocr_texts(tr, im_o)
        if not found:
            print("  ✓ هیچ متنی در خروجی خوانده نشد (تمیز)")
            continue
        orig_texts = []
        if cands:
            im_i = cv2.imread(cands[0])
            if im_i is not None:
                orig_texts = [t for (t, s, r) in ocr_texts(tr, im_i)]
        for (t, s, r) in found:
            in_orig = any(t[:6].lower() in ot.lower() for ot in orig_texts) \
                if orig_texts else True
            tag = "جامانده از اورجینال" if in_orig else "جدید/واترمارک؟"
            total_left += 1 if in_orig else 0
            print(f"  [!] «{t}» (score={s:.2f} rect={r}) — {tag}")
    print(f"\n>>> جمعِ متنِ جاماندهٔ مشکوک: {total_left}")

if __name__ == "__main__":
    main()
