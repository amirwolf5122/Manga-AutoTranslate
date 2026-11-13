#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import glob
import json
import os
import re
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(ROOT, "fonts", "Vazirmatn-Bold.ttf")


def run_one(img: str, method: str) -> dict:
    out = os.path.join(tempfile.mkdtemp(prefix="bench_"), "r.pdf")
    cmd = [sys.executable, os.path.join(ROOT, "manga_single.py"),
           "-i", img, "-o", out, "--font", FONT, "--clean-only",
           "--ocr-lang", "en", "--cpu", "--clean-method", method,
           "--no-resume"]
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True,
                       timeout=900, cwd=ROOT)
    wall = time.time() - t0
    cleans = [float(m) for m in
              re.findall(r"clean=([0-9.]+)s", p.stdout + p.stderr)]
    regs = re.search(r"متن استخراج شد: (\d+) ناحیه", p.stdout)
    return {"rc": p.returncode, "wall": round(wall, 1),
            "clean_s": cleans, "clean_total": round(sum(cleans), 1),
            "regions": int(regs.group(1)) if regs else 0,
            "pdf": out if os.path.isfile(out) else ""}


def main():
    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    imgs = []
    for f in sorted(glob.glob(os.path.join(ROOT, "ci_imgs", "*"))):
        b = os.path.basename(f)
        if b.lower().endswith((".png", ".jpg", ".jpeg", ".webp")) \
                and os.path.isdir(os.path.join(ROOT, "ci_imgs", "fixtures")) \
                and os.path.commonpath([f, os.path.join(ROOT, "ci_imgs",
                                                        "fixtures")]) \
                == os.path.join(ROOT, "ci_imgs", "fixtures"):
            continue
        if b.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            if only and not any(o in b for o in only):
                continue
            imgs.append(f)
    res = {}
    for f in imgs:
        b = os.path.basename(f)
        res[b] = {}
        for method in ("lama-manga", "opencv"):
            r = run_one(f, method)
            res[b][method] = r
            print(f"  {b:36s} {method:10s} clean={r['clean_total']:6.1f}s "
                  f"(ناحیه={r['regions']}) rc={r['rc']}", flush=True)
    print("\n──────── جدولِ نهایی ────────")
    print(f"{'عکس':36s} {'lama(s)':>9s} {'opencv(s)':>10s}")
    for b, d in res.items():
        l = d.get("lama-manga", {}).get("clean_total", 0)
        o = d.get("opencv", {}).get("clean_total", 0)
        print(f"{b:36s} {l:9.1f} {o:10.1f}")
    with open("/tmp/clean_bench.json", "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print("ذخیره شد: /tmp/clean_bench.json")


if __name__ == "__main__":
    main()
