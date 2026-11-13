#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import math
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

FIX = os.path.join(ROOT, "ci_imgs", "fixtures")


def ensure_fixtures():
    if not os.path.isfile(os.path.join(FIX, "ground_truth.json")):
        subprocess.run([sys.executable,
                        os.path.join(ROOT, "scripts", "make_ocr_fixture.py")],
                       check=True, cwd=ROOT)


def _norm(t: str) -> str:
    return " ".join("".join(c for c in t.upper() if c.isalnum()).split()) \
        if False else "".join(c for c in t.upper() if c.isalnum())


def _words(t: str):
    import re
    return [w for w in re.split(r"[^A-Za-z0-9]+", t.upper()) if w]


def _fuzzy_in(word: str, text: str) -> bool:
    import difflib
    if not word:
        return False
    if word in text:
        return True
    best = 0.0
    for i in range(max(1, len(text) - len(word) + 1)):
        seg = text[i:i + len(word) + 2]
        r = difflib.SequenceMatcher(None, word, seg).ratio()
        best = max(best, r)
    return best >= 0.72


def _quad_angle(box) -> float:
    pts = [(float(q[0]), float(q[1])) for q in box]
    best_ang, best_len = 0.0, -1.0
    for i in range(4):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % 4]
        ln = math.hypot(x1 - x0, y1 - y0)
        if ln > best_len:
            best_len = ln
            a = math.degrees(math.atan2(y1 - y0, x1 - x0))
            if a <= -90:
                a += 180
            elif a > 90:
                a -= 180
            best_ang = a
    return best_ang


def _quad_center(box):
    xs = [float(q[0]) for q in box]
    ys = [float(q[1]) for q in box]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


_ok = [0, 0]
_report = {"platform": sys.platform, "results": {}}


def check(name, cond):
    _ok[0] += 1 if cond else 0
    _ok[1] += 0 if cond else 1
    print(("  ✓ " if cond else "  ✘ ") + name)
    return cond


def run_backend():
    import cv2
    from manga_single import RapidOCRBackend
    return RapidOCRBackend(lang="en", prefer_gpu=False)


def ocr_lines(backend, path):
    import cv2
    img = cv2.imread(path)
    out = backend.ocr(img)
    lines = []
    if out and out[0]:
        for box, pair in out[0]:
            t = str(pair[0]).strip()
            if t:
                lines.append((box, t, float(pair[1])))
    return lines


def main():
    ensure_fixtures()
    gt = json.load(open(os.path.join(FIX, "ground_truth.json"),
                        encoding="utf-8"))
    backend = run_backend()
    print("موتور:", type(backend).__name__)

    print("۱) متنِ کج (rotated) — متن + مرکز + زاویه")
    for name, g in gt["fixtures"].items():
        if not name.startswith("rot_"):
            continue
        lines = ocr_lines(backend, os.path.join(FIX, name))
        joined = _norm(" ".join(t for _, t, _ in lines))
        gt_t = _norm(g["text"])
        text_ok = gt_t[:14] in joined or _fuzzy_in(gt_t[:14], joined)
        cx, cy = None, None
        ang = None
        best = None
        for box, t, _s in lines:
            if _fuzzy_in(_norm(g["text"])[:10], _norm(t)):
                best = (box, t)
                break
        if best:
            cx, cy = _quad_center(best[0])
            ang = _quad_angle(best[0])
        pos_ok = False
        if cx is not None:
            gx, gy = g["center"]
            tol = 0.22 * max(g["size"])
            pos_ok = math.hypot(cx - gx, cy - gy) <= tol
        gt_img_ang = -float(g["angle"])
        ang_ok = (ang is not None
                  and abs(((ang - gt_img_ang + 90) % 180) - 90) <= 8.0)
        ok = check(f"{name}: متن={text_ok} مرکز={pos_ok} "
                   f"زاویه={ang_ok} (det={ang and round(ang, 1)}°/"
                   f"هدف={gt_img_ang}°)",
                   text_ok and pos_ok and ang_ok)
        _report["results"][name] = {"text": text_ok, "pos": pos_ok,
                                    "angle": ang_ok,
                                    "det_angle": ang}

    print("۲) متنِ خمیده (curved) — توکنها + مرکز")
    for name, g in gt["fixtures"].items():
        if not name.startswith("arc_"):
            continue
        lines = ocr_lines(backend, os.path.join(FIX, name))
        joined = _norm(" ".join(t for _, t, _ in lines))
        words = _words(g["text"])
        hit = sum(1 for w in words if _fuzzy_in(w, joined))
        text_ok = hit >= max(1, int(0.6 * len(words)))
        boxes = [b for b, _, _ in lines]
        pos_ok = False
        if boxes:
            cs = [_quad_center(b) for b in boxes]
            ux = sum(c[0] for c in cs) / len(cs)
            uy = sum(c[1] for c in cs) / len(cs)
            gx, gy = g["center"]
            tol = 0.30 * max(g["size"])
            pos_ok = math.hypot(ux - gx, uy - gy) <= tol
        ok = check(f"{name}: کلماتِ {hit}/{len(words)} مرکز={pos_ok}",
                   text_ok and pos_ok)
        _report["results"][name] = {"words": f"{hit}/{len(words)}",
                                    "pos": pos_ok}

    print("۳) صفحهٔ ترکیبی (page_mixed) — حداقلِ ناحیهها")
    lines = ocr_lines(backend, os.path.join(FIX, "page_mixed.png"))
    joined = _norm(" ".join(t for _, t, _ in lines))
    want = ["WHEREAREYOUGOING", "THEHIDDENPOWER",
            "IWILLNEVERGIVEUP", "SHADOWSTRIKE", "DESTINY"]
    hit = sum(1 for w in want if _fuzzy_in(w, joined))
    check(f"page_mixed: {hit}/5 متنِ موردِ انتظار خوانده شد",
          hit >= 3)
    _report["results"]["page_mixed"] = {"found": f"{hit}/5"}

    with open(os.path.join(FIX, "ocr_report.json"), "w",
              encoding="utf-8") as fh:
        json.dump(_report, fh, ensure_ascii=False, indent=1)
    print()
    if _ok[1]:
        print(f"✘ {_ok[1]} چک قرمز")
        sys.exit(1)
    print(f"✔ همهٔ چکها سبز است ({_ok[0]} چک — جهتِ OCR: کج+خمیده)")


if __name__ == "__main__":
    main()
