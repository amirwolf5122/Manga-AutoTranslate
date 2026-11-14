#!/usr/bin/env python3
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MANIFEST, CLEAN_D, DUMPS_D, OUT_D = sys.argv[1:5]
os.makedirs(OUT_D, exist_ok=True)

report_lines = []

def rep(s=""):
    print(s, flush=True)
    report_lines.append(s)

def load_gray(p):
    im = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
    return im

def contract_check(name, orig, clean, donor, cmp2):
    if clean is None:
        rep(f"  !! خروجیِ clean خوانده نشد")
        return
    if cmp2 is not None and cmp2.shape == clean.shape:
        m = cmp2 > 0
        m_d = cv2.dilate((m * 255).astype(np.uint8),
                         np.ones((25, 25), np.uint8)) > 0
        d_out = np.abs(clean.astype(np.int16) - orig.astype(np.int16))
        viol_out = int(((d_out > 26) & (~m_d)).sum())
        tot_out = int((~m_d).sum())
        rep(f"  قرارداد — بیرونِ ماسک: {viol_out}px تخلف از {tot_out}px "
            f"({100.0 * viol_out / max(1, tot_out):.4f}%)"
            + ("  ← تخلف!" if viol_out > max(200, 0.0002 * tot_out) else " ✓"))
        if donor is not None and donor.shape == clean.shape:
            d_in = np.abs(clean.astype(np.int16) - donor.astype(np.int16))
            viol_in = int(((d_in > 26) & m).sum())
            tot_in = int(m.sum())
            rep(f"  قرارداد — داخلِ ماسک (عینِ donor): {viol_in}px تخلف از "
                f"{tot_in}px ({100.0 * viol_in / max(1, tot_in):.4f}%)")
    else:
        rep("  (ماسکِ cmp2 نیست — رد شد)")

def cmp2_stats(name, orig, cmp2):
    if cmp2 is None or orig is None:
        return
    if cmp2.shape != orig.shape:
        cmp2 = cv2.resize(cmp2, (orig.shape[1], orig.shape[0]),
                          interpolation=cv2.INTER_NEAREST)
    m = (cmp2 > 0).astype(np.uint8)
    n, lb, st, _ = cv2.connectedComponentsWithStats(m, 8)
    comps = []
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if a < 150:
            continue
        comps.append((a, x, y, w, h))
    comps.sort(reverse=True)
    tot = int(m.sum())
    rep(f"  ماسکِ کامپوز: {tot}px در {len(comps)} مولفه "
        f"({100.0 * tot / max(1, m.size):.3f}٪ صفحه)")
    g = orig
    ink_thr = float(np.median(g)) - 60.0
    for k, (a, x, y, w, h) in enumerate(comps[:8]):
        sub = m[y:y + h, x:x + w]
        ink = int(((g[y:y + h, x:x + w] < ink_thr) & (sub > 0)).sum())
        fill = a / float(w * h)
        flag = ""
        if a > 60000 and min(w, h) > 150 and fill > 0.55:
            flag = "  ← مشکوک: کلِ حباب؟"
        elif ink > 0 and a > 8.0 * ink:
            flag = f"  ← ماسک ≫ متن ({a / max(1, ink):.1f}×)"
        rep(f"    #{k + 1}: bbox=({x},{y},{w}x{h}) area={a} fill={fill:.2f}"
            f" ink={ink}{flag}")
    if orig is not None:
        ov = cv2.cvtColor(orig, cv2.COLOR_GRAY2BGR)
        for (a, x, y, w, h) in comps[:8]:
            cv2.rectangle(ov, (x, y), (x + w, y + h), (0, 255, 0), 3)
        ow = 720
        sc = ow / ov.shape[1]
        ov = cv2.resize(ov, (ow, max(8, int(ov.shape[0] * sc))),
                        interpolation=cv2.INTER_AREA)
        cv2.imwrite(os.path.join(OUT_D, f"{name}_overlay.jpg"), ov,
                    [cv2.IMWRITE_JPEG_QUALITY, 82])

def main():
    rows = []
    with open(MANIFEST, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln or "\t" not in ln:
                continue
            nm, rel = ln.split("\t", 1)
            rows.append((nm, rel))
    if not rows:
        rep("!! manifest خالی است")
        return

    tr = None
    try:
        import manga
        tr = manga.MangaTranslator(
            api_key=["dummy"], provider="gemini", ocr_langs=["en"],
            font_path="fonts/Sahel-Bold.ttf",
            reading_order="rtl", gpu=False, clean_method="opencv",
            det_confidence=0.16, min_confidence=0.12,
            two_pass_ocr=False, img_format="jpg",
        )
    except Exception as e:
        rep(f"(OCR غیرفعال: {e})")

    def ocr_texts(img):
        res = []
        if tr is None:
            return res
        try:
            boxes = tr.det.detect(img)
        except Exception:
            return res
        for b in boxes:
            r = b.get("rect")
            if not r:
                continue
            x, y, w, h = [int(v) for v in r]
            x0, y0 = max(0, x - 6), max(0, y - 6)
            x1 = min(img.shape[1], x + w + 7)
            y1 = min(img.shape[0], y + h + 7)
            if x1 - x0 < 8 or y1 - y0 < 8:
                continue
            try:
                txt, score = tr.ocr_read(img[y0:y1, x0:x1])
            except Exception:
                continue
            txt = (txt or "").strip()
            if txt and score >= 0.45:
                res.append((txt, score, (x, y, w, h)))
        return res

    total_resid = 0
    for (nm, rel) in rows:
        rep(f"\n===== {nm} ({rel}) =====")
        orig = load_gray(rel)
        cl_p = os.path.join(CLEAN_D, f"{nm}_clean.jpg")
        clean = load_gray(cl_p) if os.path.isfile(cl_p) else None
        dn_p = os.path.join(DUMPS_D, f"{nm}_donor.png")
        donor = load_gray(dn_p) if os.path.isfile(dn_p) else None
        cm_p = os.path.join(DUMPS_D, f"{nm}_cmp2.png")
        cmp2 = load_gray(cm_p) if os.path.isfile(cm_p) else None
        if orig is None:
            rep("  !! اورجینال خوانده نشد")
            continue
        if clean is not None and clean.shape != orig.shape:
            orig_r = cv2.resize(orig, (clean.shape[1], clean.shape[0]),
                                interpolation=cv2.INTER_AREA)
        else:
            orig_r = orig
        contract_check(nm, orig_r, clean, donor, cmp2)
        if cmp2 is not None and clean is not None:
            cmp2_stats(nm, clean if clean.shape == cmp2.shape else orig_r,
                       cmp2)
        if clean is not None:
            found = ocr_texts(clean)
            if not found:
                rep("  OCR خروجی: هیچ متنی خوانده نشد ✓")
            else:
                orig_texts = []
                if tr is not None:
                    orig_texts = [t for (t, s, r) in ocr_texts(orig_r)]
                for (t, s, r) in found:
                    in_orig = any(t[:6].lower() in ot.lower()
                                  for ot in orig_texts) \
                        if orig_texts else True
                    if in_orig:
                        total_resid += 1
                    rep(f"  [!] «{t}» (score={s:.2f} rect={r})"
                        f"{' — جامانده از اورجینال' if in_orig else ' — جدید/واترمارک'}")

    rep(f"\n>>> جمعِ متنِ جاماندهٔ مشکوک (همهٔ صفحات): {total_resid}")
    with open(os.path.join(OUT_D, "qa_report.txt"), "w",
              encoding="utf-8") as f:
        f.write("\n".join(report_lines) + "\n")

if __name__ == "__main__":
    main()
