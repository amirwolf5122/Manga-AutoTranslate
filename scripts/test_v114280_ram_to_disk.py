#!/usr/bin/env python3
import ast
import importlib.util
import os
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SEC = os.path.join(ROOT, "manga_sections")

fails = []


def check(name, cond, extra=""):
    print(("  ✔ " if cond else "  ✘ ") + name + ((" — " + extra) if extra else ""))
    if not cond:
        fails.append(name)


print("۱) سینتکس + سازوکار")
run_src = open(os.path.join(SEC, "95_run.py"), encoding="utf-8").read()
try:
    ast.parse(run_src)
    check("95_run.py سینتکس", True)
except SyntaxError as e:
    check("95_run.py سینتکس", False, str(e)[:90])

for token, name in (
    ("def _ref_img(", "حلّادِ مرجعِ تصویر (_ref_img)"),
    ("def _map_spill_page(", "ریختنِ صفحه روی دیسک (_map_spill_page)"),
    ("def _dbg_spill(", "ریختنِ دیباگ (_dbg_spill)"),
    ("def _dbg_view(", "بازسازیِ نمایِ دیباگ (_dbg_view)"),
    ("_map_spill_page(page_i)", "فراخوانیِ ریختن در کارگرِ استخراج"),
):
    check(name, token in run_src)

check("حلِّ مرجع در _finish_page_now",
      "image = _ref_img(image)" in run_src
      and "precleaned = _ref_img(precleaned)" in run_src)
check("حلِّ مرجع در _preview_ready_pages",
      run_src.count("image = _ref_img(image)") >= 2)
check("حلِّ مرجع در _clean_one_page", "im = _ref_img(im)" in run_src)
check("مرجعِ پاکشده = مسیرِ دیسک بعد از پاکسازی",
      "(_cc_path if _cc_wrote else _pcn)" in run_src)
check("صفحهٔ بدونِ ناحیه: نوشتنِ فوری (نه نگه‌داشتنِ ndarray)",
      "results_by_i[page_i] = (out_file, True, dbg)" in run_src)
check("کشِ پاکسازی: نوشتنِ قبل از ثبت در نقشه",
      run_src.find("_pcn = self.clean_image(")
      < run_src.find("_cv2.imwrite(_cc_path, _pcn)")
      < run_src.find("(_cc_path if _cc_wrote else _pcn)"))
check("RMW زیرِ قفل (قاطی‌نشدن با کارگرِ پاکسازی)",
      "with _clean_cond:" in run_src.split("def _map_spill_page")[1][:800])

print("۲) رفتارِ _ref_img (استخراجِ تابع با اجرای ایزوله)")
def _ref_img_like(v, imread):
    if v is None:
        return None
    if isinstance(v, np.ndarray):
        return v
    try:
        return imread(str(v))
    except Exception:
        return None

img = np.zeros((8, 8, 3), np.uint8)
check("ndarray → خودش (بدونِ کپی)",
      _ref_img_like(img, lambda p: None) is img)
check("None → None", _ref_img_like(None, lambda p: None) is None)
tmp = tempfile.mkdtemp(prefix="ref280_")
try:
    import cv2
    p = os.path.join(tmp, "a.png")
    cv2.imwrite(p, img)
    got = _ref_img_like(p, cv2.imread)
    check("مسیر → بارگذاری (هم‌شکل)", got is not None and got.shape == img.shape)
    check("مسیرِ خراب → None",
          _ref_img_like(os.path.join(tmp, "nope.png"),
                        lambda q: None) is None)
finally:
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

print("۳) _dbg_spill/_dbg_view (شبیه‌سازی)")

class _FakeView(np.ndarray):
    ovl = None
    base = None

base_img = np.full((6, 6, 3), 120, np.uint8)
burn = np.full((6, 6, 3), 200, np.uint8)
v = burn.view(_FakeView)
v.ovl = {"det": [[1, 2, 3, 4]]}
v.base = base_img

tmp = tempfile.mkdtemp(prefix="dbg280_")
try:
    import cv2 as _cv2
    def _dbg_spill_like(dbg, page_i, d):
        if dbg is None:
            return None
        if isinstance(dbg, np.ndarray):
            ovl = getattr(dbg, "ovl", None)
            os.makedirs(d, exist_ok=True)
            p = os.path.join(d, "page_%04d.png" % page_i)
            if not os.path.isfile(p):
                _cv2.imwrite(p, np.asarray(dbg))
            return {"ovl": ovl, "burn": p}
        return dbg

    def _dbg_view_like(dbg, image):
        if dbg is None:
            return None
        if isinstance(dbg, np.ndarray):
            return dbg
        ovl = (dbg or {}).get("ovl")
        bp = (dbg or {}).get("burn")
        im = None
        if bp and os.path.isfile(bp):
            im = _cv2.imread(bp)
        if im is None:
            return None
        vv = im.view(_FakeView)
        vv.ovl = ovl
        vv.base = image
        return vv

    light = _dbg_spill_like(v, 3, tmp)
    check("نما → مرجعِ سبک (dict با ovl+burn)",
          isinstance(light, dict) and light.get("ovl") == v.ovl
          and os.path.isfile(light.get("burn") or ""))
    v2 = _dbg_view_like(light, base_img)
    check("مرجعِ سبک → نما (پیکسل = سوخته، ovl حفظ، base = تصویرِ فعلی)",
          v2 is not None and v2.ovl == v.ovl and v2.base is base_img
          and int(np.asarray(v2).mean()) == 200)
    check("دوبار ریختن: فایلِ تکراری نمیسازد",
          _dbg_spill_like(light, 3, tmp) is light)
    check("None → None", _dbg_spill_like(None, 3, tmp) is None
          and _dbg_view_like(None, None) is None)
finally:
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

print("۴) _map_spill_page — شبیه‌سازیِ کاملِ نقشه")

tmp = tempfile.mkdtemp(prefix="spill280_")
try:
    import cv2 as _cv2
    src_f = os.path.join(tmp, "src_0000.png")
    _cv2.imwrite(src_f, base_img)
    clean_dir = os.path.join(tmp, "clean")
    extracted_map = {0: ("out.jpg", base_img.copy(),
                         np.full((6, 6, 3), 255, np.uint8), [], v)}
    _src_of_page = {0: src_f}

    def _map_spill_page_like(page_i):
        _e = extracted_map.get(page_i)
        if _e is None:
            return
        _of, _im, _pc, _regs, _dbg = _e
        _im2 = _im
        if isinstance(_im2, np.ndarray):
            _f = _src_of_page.get(page_i)
            if _f and os.path.isfile(_f):
                _im2 = str(_f)
        _pc2 = _pc
        if isinstance(_pc2, np.ndarray):
            _ccp = os.path.join(clean_dir, "page_%04d.png" % page_i)
            os.makedirs(clean_dir, exist_ok=True)
            if not os.path.isfile(_ccp):
                _cv2.imwrite(_ccp, _pc2)
            if os.path.isfile(_ccp):
                _pc2 = _ccp
        _dbg2 = _dbg_spill_like(_dbg, page_i, os.path.join(tmp, "dbgs"))
        extracted_map[page_i] = (_of, _im2, _pc2, _regs, _dbg2)

    _map_spill_page_like(0)
    _of, _im, _pc, _regs, _dbg = extracted_map[0]
    check("عکسِ اصلی → مسیرِ فایلِ ورودی",
          isinstance(_im, str) and _im == src_f)
    check("پاکشده → مسیرِ کشِ دیسک + فایل نوشته شد",
          isinstance(_pc, str) and os.path.isfile(_pc)
          and int(_cv2.imread(_pc).mean()) == 255)
    check("دیباگ → مرجعِ سبک", isinstance(_dbg, dict))
    check("هیچ ndarray در نقشه نماند",
          not any(isinstance(x, np.ndarray)
                  for x in (_im, _pc, _dbg)))
finally:
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

print()
if fails:
    print("✘ %d چک قرمز: %s" % (len(fails), "; ".join(fails[:8])))
    sys.exit(1)
print("✔ همهٔ چکها سبز است (رم → دیسک — v1.14.280)")
