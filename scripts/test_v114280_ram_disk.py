#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

_ok = [0, 0]


def check(name, cond):
    if cond:
        _ok[0] += 1
        print(f"  ✓ {name}")
    else:
        _ok[1] += 1
        print(f"  ✘ {name}")


run_src = open(os.path.join(ROOT, "manga_sections", "95_run.py"),
               encoding="utf-8").read()

print("۱) منطقِ مرجعِ اسلات — بازِ واحدی")
check("تابعِ _ref_img در ران تعریف شده",
      "def _ref_img(v):" in run_src
      and "isinstance(v, np.ndarray)" in run_src
      and "MangaTranslator._imread_any(str(v))" in run_src)

import numpy as np

def ref_img(v, _imread):
    if v is None:
        return None
    if isinstance(v, np.ndarray):
        return v
    try:
        return _imread(str(v))
    except Exception:
        return None

_img = (np.arange(12, dtype=np.uint8).reshape(3, 4) * 20)
check("None → None", ref_img(None, lambda p: _img) is None)
_arr = ref_img(_img, lambda p: None)
check("ndarray → همان آرایه", _arr is _img)
_tmpd = tempfile.mkdtemp(prefix="mt280_")
_p1 = os.path.join(_tmpd, "p.png")
import cv2
cv2.imwrite(_p1, _img)
_back = ref_img(_p1, lambda p: cv2.imread(p))
check("مسیر → لودِ دیسک", _back is not None
      and _back.shape[:2] == _img.shape[:2])

print("۲) دیباگِ ریخته — همیشه بازنویسی (ضدِ کهنهٔ resume)")
check("spillِ دیباگ: بدونِ شرطِ isfile (همیشه imwrite)",
      "def _dbg_spill(dbg, page_i: int):" in run_src
      and "cv2.imwrite(_p, np.asarray(dbg))" in run_src
      and "if not os.path.isfile(_p):" not in run_src)
check("spillِ پاکشده: بدونِ شرطِ isfile (همیشه imwrite)",
      "cv2.imwrite(_ccp, _pc2)" in run_src
      and "if not os.path.isfile(_ccp):" not in run_src)
check("بازِ _dbg_view: نمایِ _DebugPageVis + ovl + base",
      "def _dbg_view(dbg, image:" in run_src
      and "_img.view(_DebugPageVis)" in run_src
      and "_v.ovl = _ovl" in run_src and "_v.base = image" in run_src)
check("بازنویسیِ دیباگِ سبکِ مرجع → عکسِ سوختهٔ تازه (کهنه نمیماند)",
      "# همیشه بازنویسی — در رانِ «ادامه» (resume) دیباگِ همین صفحه"
      in run_src)

print("۳) مسیرِ پاکسازی — نوشتنِ دیسک + ذخیرهٔ «مسیر» در اسلات")
check("imwriteِ کشِ پاکسازی بعد از clean_image",
      run_src.find("import cv2 as _cv2") > run_src.find("self.clean_image(im, regs")
      and "_cv2.imwrite(_cc_path, _pcn)" in run_src)
check("اسلاتِ بعد از پاکسازی = مسیرِ دیسک (نه ndarray)",
      '(_cc_path if _cc_wrote else _pcn)' in run_src and "del _pcn" in run_src)
check("hitِ کشِ دیسک هم اسلات را مسیر میگذارد",
      "extracted_map[_p] = (_cur[0], _cur[1], _cc_path," in run_src)

print("۴) جایگاهِ فراخوانیها")
_spill_at = run_src.find("_map_spill_page(page_i)")
_qd_at = run_src.find("_qd_inflight.discard(page_i)")
check("spill بعد از نجات/صفشدنِ هر صفحه",
      _spill_at > 0 and _qd_at > 0 and _spill_at > _qd_at)
check("finish_page_now مرجعها را حل میکند",
      "image = _ref_img(image)" in run_src
      and "precleaned = _ref_img(precleaned)" in run_src)
check("پیشنمایش هم مرجعها را حل میکند",
      run_src.count("image = _ref_img(image)") >= 2
      and run_src.count("precleaned = _ref_img(precleaned)") >= 2)
check("پاکسازِ صفحه: im = _ref_img(im) + گاردِ None",
      "im = _ref_img(im)" in run_src
      and run_src.find("im = _ref_img(im)") > run_src.find("clean_claimed.add(_p)"))
check("حلقهٔ ذخیرهٔ پایانی: بازسازیِ نمایِ دیباگ از مرجع",
      "dbg = _dbg_view(dbg, _bs_img)" in run_src
      and "_bs_img = _ref_img(_src_of_page.get(page_i))" in run_src)
check("صفحهٔ بی‌ناحیه: نوشتنِ فوری + True (بدونِ pinِ ndarray)",
      "results_by_i[page_i] = (out_file, True, dbg)" in run_src
      and "results_by_i[page_i] = (out_file, image, dbg)" not in run_src)

print("۵) رانِ واقعیِ رفتاری (۳ صفحه، فیک-ترجمه)")
if "--real" in sys.argv:
    _in = tempfile.mkdtemp(prefix="mt280in_")
    _out = tempfile.mkdtemp(prefix="mt280out_")
    for _f in ("ci_imgs/img4.jpg", "ci_imgs/img6.jpg", "ci_imgs/img7.jpg"):
        shutil.copy(os.path.join(ROOT, _f), _in)
    _font = os.path.join(ROOT, "fonts", "Vazirmatn-Bold.ttf")
    _op = os.path.join(_out, "res.pdf")
    _env = dict(os.environ, PYTHONUNBUFFERED="1")
    _cmd = [sys.executable, os.path.join(ROOT, "manga_single.py"),
            "-i", _in, "-o", _op, "--font", _font,
            "--fake-translate", "--ocr-lang", "en", "--cpu"]
    _r1 = subprocess.run(_cmd, capture_output=True, text=True,
                         timeout=1200, env=_env, cwd=ROOT)
    _cache = _op[:-4] + ".cache"
    _cc_dir = ""
    for _n in os.listdir(_cache) if os.path.isdir(_cache) else []:
        if _n.startswith("clean"):
            _cc_dir = os.path.join(_cache, _n)
    _pages = sorted(os.listdir(_cc_dir)) if _cc_dir else []
    check("رانِ اول سبز", _r1.returncode == 0)
    check("کشِ پاکسازی: page_0000..2.png روی دیسک",
          len(_pages) == 3 and all(_p.startswith("page_") for _p in _pages))
    _r2 = subprocess.run(_cmd + ["--translate-retranslate"],
                         capture_output=True, text=True,
                         timeout=1200, env=_env, cwd=ROOT)
    _n_disk = _r2.stdout.count("پاکسازی از کشِ دیسک")
    check("رانِ دوم: هر ۳ صفحه از کشِ دیسک (بدونِ LaMa)",
          _r2.returncode == 0 and _n_disk == 3)
    shutil.rmtree(_tmpd, ignore_errors=True)
    shutil.rmtree(_in, ignore_errors=True)
    shutil.rmtree(_out, ignore_errors=True)
else:
    print("  (برای رانِ واقعی: python3 scripts/test_v114280_ram_disk.py --real)")

print()
if _ok[1]:
    print(f"✘ {_ok[1]} چک قرمز")
    sys.exit(1)
print(f"✔ همهٔ چکها سبز است ({_ok[0]} چک — رم → دیسک)")
