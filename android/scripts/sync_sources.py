#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""کپی manga.py / manga_app.py از ریشه مخزن به assets اندروید.

قبل از هر بیلد APK اجرا شود:  python scripts/sync_sources.py
"""
import os
import shutil

# android/scripts/sync_sources.py → ریشه = سه سطح بالاتر
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PY_SRC = os.path.join(ROOT, "android", "app", "src", "main", "python")

for name in ("manga.py", "manga_app.py"):
    src = os.path.join(ROOT, name)
    dst = os.path.join(PY_SRC, name)
    shutil.copy2(src, dst)
    print("کپی شد:", name)
print("آماده بیلد ✅")
