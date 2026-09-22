#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""استخراج سورس pure-python ویل rapidocr داخل پایتون اپ اندروید.

rapidocr با pip قابل نصب روی اندروید نیست (وابستگی onnxruntime) — ولی خودش
pure-python است؛ ویل را دانلود و باز می‌کنیم و onnxruntime به شیم خودمان
می‌افتد.
"""
import os
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PY_SRC = os.path.join(ROOT, "android", "app", "src", "main", "python")
TMP = os.path.join(PY_SRC, "_vendor_tmp")


def main():
    os.makedirs(TMP, exist_ok=True)
    subprocess.check_call([
        sys.executable, "-m", "pip", "download", "rapidocr==3.9.2",
        "--no-deps", "-q", "-d", TMP,
    ])
    wheels = [f for f in os.listdir(TMP) if f.endswith(".whl")]
    assert wheels, "ویل rapidocr دانلود نشد"
    dst = os.path.join(PY_SRC, "rapidocr")
    os.makedirs(dst, exist_ok=True)
    with zipfile.ZipFile(os.path.join(TMP, wheels[0])) as z:
        for info in z.infolist():
            name = info.filename
            if not name.startswith("rapidocr/"):
                continue
            target = os.path.join(PY_SRC, name)
            if name.endswith("/"):
                os.makedirs(target, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "wb") as f:
                f.write(z.read(name))
    print("rapidocr vendor شد →", dst)
    # پاکسازی
    import shutil
    shutil.rmtree(TMP, ignore_errors=True)
    print("آماده بیلد ✅")


if __name__ == "__main__":
    main()
