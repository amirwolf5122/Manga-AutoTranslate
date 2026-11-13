#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIME_RE = re.compile(r"\[TIME\]\s*([^=]+)=([0-9.]+)s?(.*)")

def find_images(img_dir: str):
    exts = (".jpg", ".jpeg", ".png", ".webp", ".bmp")
    files = []
    for name in sorted(os.listdir(img_dir)):
        if name.lower().endswith(exts):
            files.append(os.path.join(img_dir, name))
    return files

def run_cli(imgs, out_dir, workers=2, label="run"):
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    inp = ",".join(imgs)
    cmd = [
        sys.executable, "manga.py",
        "-i", inp,
        "-o", out_dir,
        "--font", os.path.join("fonts", "Lalezar-Regular.ttf"),
        "--fake-translate",
        "--clean-method", "lama-manga",
        "--img-format", "jpg",
        "--workers", str(workers),
    ]
    t0 = time.time()
    proc = subprocess.run(
        cmd, cwd=ROOT, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        timeout=3600,
    )
    wall = time.time() - t0
    log = proc.stdout.decode("utf-8", "replace")
    log_path = out_dir + "_log_" + label + ".txt"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(log)
    stages = {}
    for m in TIME_RE.finditer(log):
        k = m.group(1).strip()
        v = float(m.group(2))
        stages[k] = stages.get(k, 0.0) + v
    n_out = 0
    if os.path.isdir(out_dir):
        n_out = len([f for f in os.listdir(out_dir)
                     if f.lower().endswith((".jpg", ".png", ".webp"))])
    return {
        "label": label,
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "wall_s": round(wall, 1),
        "n_inputs": len(imgs),
        "n_outputs": n_out,
        "stages_s": {k: round(v, 1) for k, v in sorted(stages.items())},
        "log": log_path,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--imgs", required=True, help="پوشهٔ تصاویر ورودی")
    ap.add_argument("--out", required=True, help="پوشهٔ خروجیِ پایه")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--label", default="pc")
    ap.add_argument("--report", default=None)
    ap.add_argument("--warmup", type=int, default=1,
                    help="۰ = بدونِ رانِ گرم‌کردن")
    args = ap.parse_args()

    imgs = find_images(args.imgs)
    if not imgs:
        print("هیچ تصویری پیدا نشد:", args.imgs, file=sys.stderr)
        sys.exit(2)
    print(f"[*] bench: {len(imgs)} تصویر | workers={args.workers}")
    for f in imgs:
        print("   -", os.path.basename(f))

    report = {
        "label": args.label,
        "when_utc": datetime.now(timezone.utc).isoformat(),
        "cores": os.cpu_count(),
        "platform": sys.platform,
        "runs": [],
    }

    if args.warmup:
        w_out = args.out + "_warmup"
        shutil.rmtree(w_out, ignore_errors=True)
        print("[*] گرم‌کردن (کشِ مدل‌ها) — تایم نمی‌شود ...")
        wr = run_cli(imgs[:1], w_out, args.workers, label="warmup")
        report["warmup"] = {k: wr[k] for k in ("ok", "wall_s", "returncode")}
        print(f"    warmup ok={wr['ok']} wall={wr['wall_s']}s")

    out_dir = args.out
    shutil.rmtree(out_dir, ignore_errors=True)
    print("[*] رانِ تایم‌شدهٔ کامل ...")
    r = run_cli(imgs, out_dir, args.workers, label=args.label)
    report["runs"].append(r)
    print(json.dumps({k: v for k, v in r.items() if k != "log"},
                     ensure_ascii=False, indent=2))

    rep_path = args.report or (args.out + "_report.json")
    with open(rep_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    md_path = os.path.splitext(rep_path)[0] + ".md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Speed report — {args.label}\n\n")
        f.write(f"- when: {report['when_utc']}\n- cores: {report['cores']}\n\n")
        for r in report["runs"]:
            f.write(f"## {r['label']}\n\n")
            f.write(f"- ok: {r['ok']}\n- inputs: {r['n_inputs']} → outputs: {r['n_outputs']}\n")
            f.write(f"- **wall: {r['wall_s']}s**\n\n")
            f.write("| stage | s |\n|---|---|\n")
            for k, v in r["stages_s"].items():
                f.write(f"| {k} | {v} |\n")
    print("[✓] گزارش:", rep_path, "و", md_path)
    sys.exit(0 if r["ok"] else 1)

if __name__ == "__main__":
    main()
