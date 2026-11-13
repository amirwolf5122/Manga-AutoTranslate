#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import ast
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "manga_sections", "20_models.py")

fails = []


def check(name, cond, extra=""):
    print(("  ✔ " if cond else "  ✘ ") + name + ((" — " + extra) if extra else ""))
    if not cond:
        fails.append(name)


src = open(SRC, encoding="utf-8").read()

print("۱) سینتکس")
try:
    ast.parse(src)
    check("20_models.py", True)
except SyntaxError as e:
    check("20_models.py", False, str(e)[:80])
    sys.exit(1)

print("۲) گاردهای سورس")
check("پلکانِ واحد — شاخهٔ «not prefer_gpu → 256» حذف شد",
      "if not self.prefer_gpu:\n            return 256" not in src)
check("هکِ فقط-CPU (cov>0.22→512) حذف شد", "cov > 0.22" not in src)
check("پلکانِ ۲۵۶/۳۸۴/۵۱۲ موجود",
      "if m <= 180:" in src and "if m <= 320:" in src
      and "return min(self.size, 512)" in src)

print("۳) رفتارِ _pick_size (هر دو حالتِ GPU/CPU)")


def pick(prefer_gpu, w, h, size=512, fixed=False):
    m = max(int(w), int(h))
    if fixed:
        return size
    if m <= 180:
        return 256
    if m <= 320:
        return 384
    return min(size, 512)


cases = [(120, 90), (200, 100), (500, 400), (900, 700), (60, 60)]
same = all(pick(True, w, h) == pick(False, w, h) for (w, h) in cases)
for (w, h) in cases:
    print(f"    {w}x{h}: GPU={pick(True, w, h)} CPU={pick(False, w, h)}")
check("GPU == CPU در همهٔ اندازه‌ها", same)
check("گروهِ کوچک → ۲۵۶ (سرعت حفظ شد)", pick(True, 120, 90) == 256)
check("گروهِ متوسط → ۳۸۴", pick(True, 200, 100) == 384)
check("گروهِ بزرگ → ۵۱۲", pick(True, 500, 400) == 512)

print("۴) شبیه‌سازیِ قدیم/جدید — CPU چه چیزی عوض شد")
old_cpu = {(w, h): 256 for (w, h) in cases}
changed = [(w, h) for (w, h) in cases if old_cpu[(w, h)] != pick(False, w, h)]
print(f"    اندازه‌هایی که CPUشان بالاتر رفت: {changed}")
check("CPU برایِ گروههایِ متوسط/بزرگ بالاتر رفت (کیفیت = GPU)",
      (200, 100) in changed and (500, 400) in changed)

print()
if fails:
    print("✘ %d چک قرمز: %s" % (len(fails), "; ".join(fails)))
    sys.exit(1)
print("✔ همهٔ چکها سبز است (یکسانیِ GPU/CPU — v1.14.285)")
