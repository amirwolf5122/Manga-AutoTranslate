#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
DEFAULT_TARGET = REPO / "android" / "app" / "src" / "main" / "python"

FIRST_PARTY = {
    "bridge.py",
    "native_bridge.py",
    "launcher.py",
    "extract_ui.py",
    "app_server.py",
    "onnxruntime",
    "pyclipper",
}

PINS = [
    ("openai",            "1.35.13",   "openai"),
    ("pydantic",          "1.10.17",   "pydantic"),
    ("rapidocr",          "3.9.2",     "rapidocr"),
    ("huggingface_hub",   "0.36.0",    "huggingface_hub"),
    ("httpx",             "0.27.2",    "httpx"),
    ("httpcore",          "1.0.9",     "httpcore"),
    ("h11",               "0.16.0",    None),
    ("anyio",             "4.15.1",    "anyio"),
    ("sniffio",           "1.3.1",     None),
    ("idna",              "3.20",      None),
    ("certifi",           "2026.7.22", None),
    ("distro",            "1.9.0",     None),
    ("filelock",          "4.0.1",     None),
    ("fsspec",            "2026.9.0",  "fsspec"),
    ("packaging",         "26.3",      None),
    ("beautifulsoup4",    "4.15.0",    "bs4"),
    ("soupsieve",         "2.9.2",     None),
    ("exceptiongroup",    "1.3.1",     None),
    ("typing_extensions", "4.16.0",    None),
]


def _dist_info(target: Path, name: str):
    return list(target.glob(f"{name}-*.dist-info"))


def clean(target: Path) -> int:
    removed = 0
    if not target.is_dir():
        print(f"[!] مسیر هدف وجود ندارد: {target}")
        return 0
    for name, _ver, _path in PINS:
        for p in list(target.glob(name)) + list(target.glob(f"{name}-*.dist-info")):
            if p.is_dir() and p.name not in FIRST_PARTY:
                shutil.rmtree(p, ignore_errors=True)
                removed += 1
        if name == "typing_extensions":
            p = target / "typing_extensions.py"
            if p.exists():
                p.unlink()
                removed += 1
    for junk in ("bin", "__pycache__"):
        p = target / junk
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
            removed += 1
    print(f"[*] {removed} مورد vendored از {target} پاک شد")
    return removed


def check(target: Path) -> bool:
    ok = True
    for name, ver, path in PINS:
        di = _dist_info(target, name)
        ver_ok = any(v.name == f"{name}-{ver}.dist-info" for v in di)
        path_ok = (path is None) or (target / path).is_dir()
        if not (ver_ok and path_ok):
            ok = False
            print(f"[غایب] {name}=={ver}  (dist-info: {[v.name for v in di] or '—'})")
    if ok:
        print(f"[OK] هر {len(PINS)} بستهٔ vendored در {target} حاضر است")
    return ok


def install(target: Path) -> int:
    target.mkdir(parents=True, exist_ok=True)
    clean(target)
    reqs = [f"{name}=={ver}" for name, ver, _p in PINS]
    cmd = [
        sys.executable, "-m", "pip", "install",
        "--target", str(target),
        "--no-deps",
        "--only-binary=:all:",
        "--no-compile",
        "--upgrade",
        "--disable-pip-version-check",
        "-q",
        *reqs,
    ]
    print("[*] دانلود و ریختن ۱۹ بستهٔ vendored …")
    r = subprocess.run(cmd)
    if r.returncode != 0:
        print("[!] pip ناموفق بود — خروجی بالا را ببین")
        return r.returncode
    for junk in ("bin", "__pycache__"):
        p = target / junk
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
    if not check(target):
        print("[!] بعد از نصب بعضی بسته‌ها پیدا نشدند!")
        return 1
    n = sum(1 for _ in target.rglob("*"))
    print(f"[OK] تمام شد — {n} فایل/پوشه در {target}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="دانلود بسته‌های vendored اندروید")
    ap.add_argument("--target", default=str(DEFAULT_TARGET))
    ap.add_argument("--check", action="store_true", help="فقط بررسی حاضر بودن")
    ap.add_argument("--list", action="store_true", help="چاپ لیست پین‌ها")
    ap.add_argument("--clean", action="store_true", help="پاک‌کردن vendoredها")
    args = ap.parse_args()
    target = Path(args.target).resolve()

    if args.list:
        for name, ver, _path in PINS:
            print(f"{name}=={ver}")
        return 0
    if args.clean:
        clean(target)
        return 0
    if args.check:
        return 0 if check(target) else 1
    return install(target)


if __name__ == "__main__":
    sys.exit(main())
