# -*- coding: utf-8 -*-
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SEC = os.path.join(ROOT, "manga_sections")
APP = os.path.join(ROOT, "manga_app.py")
ENGINE = os.path.join(ROOT, "manga.py")
BRIDGE = os.path.join(ROOT, "android", "app", "src", "main",
                      "python", "bridge.py")
MAIN_KT = os.path.join(ROOT, "android", "app", "src", "main", "java",
                       "com", "amirwolf", "mangatranslator", "MainActivity.kt")
FONT = os.path.join(ROOT, "fonts", "Vazirmatn-Regular.ttf")
IMG = os.path.join(ROOT, "ci_imgs", "up0822_en.jpg")

fails = []


def check(name, cond, extra=""):
    print(("  ✔ " if cond else "  ✘ ") + name + ((" — " + extra) if extra else ""))
    if not cond:
        fails.append(name)


print("۱) سینتکس")
for fn in ("manga_sections/95_run.py", "manga_app.py",
           "android/app/src/main/python/bridge.py"):
    try:
        ast.parse(open(os.path.join(ROOT, fn), encoding="utf-8").read())
        check(fn, True)
    except SyntaxError as e:
        check(fn, False, str(e)[:80])

print("۲) موتور: کشِ دیسکِ تصویرِ پاکسازی‌شده (95_run.py)")
run_src = open(os.path.join(SEC, "95_run.py"), encoding="utf-8").read()
check("برچسبِ مخصوصِ کشِ پاکسازی (_clean_img_tag)",
      "def _clean_img_tag" in run_src)
_i_tag = run_src[run_src.find("def _clean_img_tag"):
                 run_src.find("def _clean_img_tag") + 1200]
check("پوشهٔ کش با برچسبِ پاکسازی ساخته میشود",
      '"clean" + cache_tag + "_c-"' in run_src)
check("پارامترهایِ پاکسازی در برچسب",
      all(k in _i_tag for k in ("clean_method", "force_lama", "clean_sfx",
                                "mask_padding", "pad_ratio", "inpaint_radius",
                                "mag_ratio")))
check("clean_only در برچسب (جunk فقط در حالتِ پاکسازی پاک میشود)",
      'getattr(self, "clean_only", False)' in _i_tag)
check("فرمت/کیفیت/عرضِ رندر در برچسبِ پاکسازی نیست (تعویضشان LaMa را از نو نگیرد)",
      not any(k in _i_tag for k in ("img_format", "img_quality", "max_width")))
check("خواندن از کشِ دیسک در _clean_one_page",
      "کشِ دیسک" in run_src and "_cc_path" in run_src
      and 'page_%04d.png' in run_src)
check("نوشتنِ تصویرِ پاکشده روی دیسک بعد از clean_image",
      run_src.find("import cv2 as _cv2") > run_src.find("self.clean_image(im, regs")
      and "_cv2.imwrite(_cc_path, _pcn)" in run_src)
check("تطبیقِ ابعادِ صفحه در خواندنِ کش (ضدِ فایلِ خراب)",
      "_pc_disk.shape[:2] == im.shape[:2]" in run_src)
_wipe = run_src[run_src.find("ورودی/تنظیمات تغییر کرد"):
                run_src.find("ورودی/تنظیمات تغییر کرد") + 700]
check("پاک‌شدنِ کشِ پاکسازی با عوض‌شدنِ ورودی",
      '_n.startswith("clean")' in _wipe)
check("کشِ پاکسازی در «از-نو ترجمه» پاک نمیشود (فقطِ ترجمه عوض میشود)",
      run_src.find('translate_retranslate') >= 0
      and 'endswith("_cleanonly")' in run_src)

print("۳) اندروید: bridge.py")
br_src = open(BRIDGE, encoding="utf-8").read()
_i = br_src.find("def trans_sig_check")
_tsc = br_src[_i:_i + 7000] if _i >= 0 else ""
check("تابعِ trans_sig_check هست", _i >= 0)
check("پاسِ retranslate به موتور",
      'translate_retranslate=bool(p.get("retranslate"))' in br_src)
check("clean_only → بدونِ پرسش",
      'bool(p.get("clean_only"))' in _tsc)
check("auto → بدونِ پرسش (قبل از استارت قابلِ پیش‌بینی نیست)",
      '_prov == "auto"' in _tsc)
check("عوض‌شدنِ حالتِ تست → خودکار از نو (بدونِ پرسش)",
      'bool(_fake_prev) != bool(p.get("fake"))' in _tsc)
check("همان امضای وب/موتور (manga_app._trans_sig_of)",
      'manga_app, "_trans_sig_of"' in _tsc)
check("همان کشِ مشترک (manga_app._cache_dir_for)",
      'manga_app, "_cache_dir_for"' in _tsc)
check("خروجیِ همیشهٔ JSON معتبر (ask: false در خطا)",
      _tsc.count('return json.dumps({"ask": False}') >= 5)

print("۴) اندروید: MainActivity.kt (پنجرهٔ پرسش)")
kt_src = open(MAIN_KT, encoding="utf-8").read()
check("سنجش در پس‌زمینه پیش از استارت",
      'callAttr(\n                    "trans_sig_check"' in kt_src
      or '"trans_sig_check"' in kt_src)
check("پنجرهٔ «ادامه یا از-نو»",
      "askRetranslate" in kt_src and "از اول ترجمه کن" in kt_src
      and "ادامه بده" in kt_src)
check("گزینهٔ انصراف", "بی‌خیال" in kt_src)
check("پاسخ → پرچمِ retranslate",
      'p.put("retranslate", true)' in kt_src
      and 'p.put("retranslate", false)' in kt_src)
check("شروعِ کار جدا شد (beginJob)",
      "private fun beginJob(p: JSONObject)" in kt_src)
check("مسیرِ استارت فقط یکی است (onStartJob → پرسش/شروع)",
      kt_src.count("beginJob(p)") >= 4)

print("۵) رانِ واقعیِ موتور — ۶ سناریو")
_models_root = os.environ.get("MANGA_FILES_DIR") or os.getcwd()
_have_models = (os.path.isdir(os.path.join(_models_root, "det_models"))
                and os.path.isdir(os.path.join(_models_root, "rapidocr_models")))
if not (_have_models and os.path.isfile(IMG) and os.path.isfile(FONT)):
    print("  ــ مدلها/ورودی در دسترس نیست — بخشِ رانِ واقعی رد شد"
          " (MANGA_FILES_DIR=<پوشهٔ det_models+rapidocr_models>)")
else:
    TMP = tempfile.mkdtemp(prefix="mt278_")
    ENV = dict(os.environ, MANGA_FILES_DIR=_models_root)
    IMG_DST = os.path.join(TMP, "up0822_en.jpg")
    IMG2 = os.path.join(ROOT, "ci_imgs", "up0904_en.jpg")
    IMG2_DST = os.path.join(TMP, "up0904_en.jpg")
    shutil.copy(IMG, IMG_DST)
    shutil.copy(IMG2, IMG2_DST)
    OUT = os.path.join(TMP, "up0822_en.pdf")
    CACHE = os.path.splitext(OUT)[0] + ".cache"

    def engine(extra, out=OUT, img=IMG_DST, timeout=280):
        cmd = [sys.executable, "-u", ENGINE, "-i", img, "-o", out,
               "--font", FONT, "--clean-method", "opencv",
               "--api-key", "placeholder"] + list(extra)
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, cwd=TMP, env=ENV)
        return (r.stdout or "") + "\n" + (r.stderr or "")

    def clean_dirs():
        if not os.path.isdir(CACHE):
            return []
        return sorted(n for n in os.listdir(CACHE) if n.startswith("clean"))

    try:
        t0 = time.time()
        logA = engine(["--fake-translate"])
        check("A) رانِ فیک تمام شد", "PDF نهایی ذخیره شد" in logA,
              re.findall(r"total=[\d.]+s", logA)[-1] if logA else "")
        _cd = clean_dirs()
        check("A) پوشهٔ کشِ پاکسازی ساخته شد", len(_cd) == 1, str(_cd))
        _pc = os.path.join(CACHE, _cd[0], "page_0000.png") if _cd else ""
        check("A) تصویرِ پاکشدهٔ صفحه در دیسک", _pc and os.path.isfile(_pc))

        logB = engine(["--fake-translate", "--translate-retranslate"])
        check("B) استخراج از کش", "از کشِ استخراج" in logB)
        check("B) پاکسازی از کشِ دیسک (بدونِ اجرای دوباره)",
              "پاکسازی از کشِ دیسک" in logB)
        check("B) پاکسازیِ واقعی اجرا نشد",
              not re.search(r"page#1 clean=[\d.]+s", logB))
        check("B) ترجمه از نو (بدونِ انبارِ قبلی)",
              "ترجمه: 5/5" in logB and "از کشِ ترجمه" not in logB)

        logC = engine(["--fake-translate", "--mask-padding", "8"])
        check("C) استخراج از کش ماند", "از کشِ استخراج" in logC)
        check("C) ترجمه از انبار برگشت", "از کشِ ترجمه" in logC)
        check("C) پاکسازی با پارامترِ تازه اجرا شد",
              "پاکسازی از کشِ دیسک" not in logC
              and re.search(r"page#1 clean=[\d.]+s", logC) is not None)
        check("C) پوشهٔ کشِ سبکِ تازه جدا",
              len(clean_dirs()) == 2, str(clean_dirs()))

        logD = engine(["--fake-translate", "--mask-padding", "8",
                       "--img-format", "webp"])
        check("D) تعویضِ فرمت، پاکسازی را از نو نگیرد",
              "پاکسازی از کشِ دیسک" in logD)
        check("D) تعدادِ پوشههایِ پاکسازی تغییر نکرد (۲ سبک)",
              len(clean_dirs()) == 2, str(clean_dirs()))

        snap = os.path.join(TMP, "fake_files", "work", "out",
                            "up0822_en.cache")
        os.makedirs(os.path.dirname(snap), exist_ok=True)
        shutil.copytree(CACHE, snap)

        logE = engine(["--max-retries", "1", "--api-timeout", "6"])
        check("E) تشخیصِ تعویضِ حالتِ تست",
              "حالتِ تست عوض شد" in logE)
        check("E) استخراج از کش", "از کشِ استخراج" in logE)
        check("E) پاکسازی از کشِ دیسک", "پاکسازی از کشِ دیسک" in logE)

        logF = engine(["--fake-translate"], img=IMG2_DST)
        check("F) تشخیصِ ورودیِ تازه", "ورودی/تنظیمات تغییر کرد" in logF)
        check("F) کشهایِ پاکسازیِ ورودیِ قبلی پاک شدند",
              len(clean_dirs()) == 1, str(clean_dirs()))
        check("F) استخراج از اول (بدونِ کش)",
              "از کشِ استخراج" not in logF)

        print("۶) trans_sig_check عملکردی (اندروید)")
        sys.path.insert(0, os.path.dirname(BRIDGE))
        sys.path.insert(0, ROOT)
        import bridge
        fd = os.path.join(TMP, "fake_files")
        base = {"src": IMG_DST, "provider": "gemini", "model": "",
                "keys": "k", "fmt": "PDF", "fake": True,
                "prompt_mode": "auto", "prompt_body": "",
                "temp": 0.7, "top_p": 0.9}

        def ask_of(p):
            return json.loads(bridge.trans_sig_check(
                json.dumps(p), fd)).get("ask")

        check("همان تنظیم → بدونِ پرسش", ask_of(base) is False)
        check("مدل عوض شد + کارِ مانده → پرسش",
              ask_of({**base, "model": "gemini-2.5-flash"}) is True)
        check("پرامپت عوض شد + کارِ مانده → پرسش",
              ask_of({**base, "prompt_body": "لحن خیلی خودمونی باشه"}) is True)
        check("فیک خاموش شد → خودکار از نو (بدونِ پرسش)",
              ask_of({**base, "fake": False}) is False)
        check("ورودیِ بدونِ کش → بدونِ پرسش",
              ask_of({**base, "model": "x", "src": "/nope.jpg"}) is False)
    finally:
        shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("✘ %d چک قرمز: %s" % (len(fails), "; ".join(fails[:8])))
    sys.exit(1)
print("✔ همهٔ چکها سبز است (کشِ مرحله‌به‌مرحله — هرچی عوض شد، فقطِ همان بخش)")
