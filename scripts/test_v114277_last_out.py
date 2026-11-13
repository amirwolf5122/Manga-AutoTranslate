# -*- coding: utf-8 -*-
import importlib.util
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SEC = os.path.join(ROOT, "manga_sections")
APP = os.path.join(ROOT, "manga_app.py")

fails = []


def check(name, cond, extra=""):
    print(("  ✔ " if cond else "  ✘ ") + name + ((" — " + extra) if extra else ""))
    if not cond:
        fails.append(name)


print("۱) سینتکس")
import ast
for fn in ("manga_sections/95_run.py", "manga_app.py",
           "android/app/src/main/python/out_collect.py"):
    try:
        ast.parse(open(os.path.join(ROOT, fn), encoding="utf-8").read())
        check(fn, True)
    except SyntaxError as e:
        check(fn, False, str(e)[:80])

print("۲) موتور: نشانگرِ last_out.json")
run_src = open(os.path.join(SEC, "95_run.py"), encoding="utf-8").read()
check("نوشتنِ نشانگر در ران",
      'last_out.json' in run_src and '"dir": os.path.basename(out_dir)'
      in run_src)
check("نوشتهشدن در همان ابتدای ران (قبل از حلقهٔ صفحات)",
      run_src.find('last_out.json') < run_src.find("pending = []"))
check("ثبتِ حالتِ فقط-پاکسازی در نشانگر",
      '"clean_only": bool(getattr(self, "clean_only"' in run_src)

print("۳) اندروید: out_collect.py")
oc_path = os.path.join(ROOT, "android", "app", "src", "main",
                       "python", "out_collect.py")
spec = importlib.util.spec_from_file_location("oc", oc_path)
oc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oc)

tmp = tempfile.mkdtemp(prefix="oc277_")
try:
    cache = os.path.join(tmp, "ch5.cache")
    out_tr = os.path.join(cache, "out_safe_v3_style-aaaa1111")
    out_co = os.path.join(cache, "out_safe_v3_style-aaaa1111_cleanonly")
    out_old = os.path.join(cache, "out_safe_v3_style-bbbb2222")
    dbg_dir = os.path.join(cache, "debug_safe_v3")
    for d in (out_tr, out_co, out_old, dbg_dir):
        os.makedirs(d)
    for d, name in ((out_tr, "page_1.jpg"), (out_tr, "page_2.jpg"),
                    (out_co, "page_1.jpg"), (out_co, "page_2.jpg"),
                    (out_old, "page_1.jpg"),
                    (dbg_dir, "page_1_debug.jpg")):
        open(os.path.join(d, name), "wb").write(b"x")
    job_out = os.path.join(tmp, "job")
    os.makedirs(job_out)

    out_pdf = os.path.join(tmp, "ch5.pdf")
    os.utime(out_tr, (3000, 3000))
    os.utime(out_co, (2000, 2000))
    os.utime(out_old, (1000, 1000))
    imgs, dbg = oc.collect(out_pdf, job_out)
    check("بدونِ نشانگر: فقط جدیدترینِ out (۲ صفحه از ترجمه)",
          len(imgs) == 2 and all(out_tr in p for p in imgs),
          f"{len(imgs)}: {imgs}")
    check("بدونِ نشانگر: دیباگ جدا", len(dbg) == 1)

    with open(os.path.join(cache, "last_out.json"), "w",
              encoding="utf-8") as fh:
        json.dump({"dir": os.path.basename(out_co), "clean_only": True},
                  fh)
    imgs, dbg = oc.collect(out_pdf, job_out)
    check("نشانگرِ پاکسازی: فقط ۲ صفحهٔ cleanonly",
          len(imgs) == 2 and all("_cleanonly" in p for p in imgs),
          f"{len(imgs)}")
    check("نشانگرِ پاکسازی: دیباگ سرِ جایش", len(dbg) == 1)

    with open(os.path.join(cache, "last_out.json"), "w",
              encoding="utf-8") as fh:
        json.dump({"dir": os.path.basename(out_tr), "clean_only": False},
                  fh)
    imgs, dbg = oc.collect(out_pdf, job_out)
    check("نشانگرِ ترجمه: فقط صفحاتِ همین سبک",
          len(imgs) == 2 and all("style-aaaa1111" in p
                                 and "_cleanonly" not in p for p in imgs),
          f"{len(imgs)}")

    with open(os.path.join(cache, "last_out.json"), "w",
              encoding="utf-8") as fh:
        fh.write("{not json")
    imgs, _ = oc.collect(out_pdf, job_out)
    check("نشانگرِ خراب: فالبکِ نو — فقط جدیدترین",
          len(imgs) == 2 and all(out_tr in p for p in imgs),
          f"{len(imgs)}")

    os.remove(os.path.join(cache, "last_out.json"))
    imgs, _ = oc.collect(out_pdf, job_out)
    check("حذفِ نشانگر: فالبکِ نو — فقط جدیدترین",
          len(imgs) == 2 and all(out_tr in p for p in imgs),
          f"{len(imgs)}")

    os.makedirs(os.path.join(tmp, "evil"), exist_ok=True)
    open(os.path.join(tmp, "evil", "x.jpg"), "wb").write(b"x")
    with open(os.path.join(cache, "last_out.json"), "w",
              encoding="utf-8") as fh:
        json.dump({"dir": "../evil"}, fh)
    imgs, _ = oc.collect(out_pdf, job_out)
    check("نشانگرِ مسیر-فرار: نادیده گرفته شد",
          all("evil" not in p for p in imgs))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("۴) وب (manga_app.py)")
asrc = open(APP, encoding="utf-8").read()
check("خواندنِ نشانگر در نمایشگرِ وب", "last_out.json" in asrc)
check("اولویتِ نشانگر بر جمع‌آوریِ همهٔ outها",
      "_last_out_dir" in asrc and "if _last_out_dir and os.path.isdir" in asrc)
check("فالبکِ نو (فقط جدیدترینِ out*) در وب",
      "_newest_out" in asrc and "out_safe_v3")
check("شرطِ داشتنِ تصویر در پوشهٔ نشانگر (فالبک اگر خالی)",
      'any(_fn.lower().endswith(' in asrc)

print("۵) نسخهها")
base = open(os.path.join(SEC, "00_base.py"), encoding="utf-8").read()
check("APP_VER بخشها = 1.14.287", 'APP_VER = "1.14.287"' in base)
loader = open(os.path.join(ROOT, "manga.py"), encoding="utf-8").read()
check("APP_VER لودر = 1.14.287", 'APP_VER = "1.14.287"' in loader)
check("APP_VER اپ = 1.14.287", 'APP_VER = "1.14.287"' in asrc)
v = open(os.path.join(ROOT, "VERSION"), encoding="utf-8").read()
check("VERSION = 288 / 1.14.287",
      "versionCode=289" in v and "versionName=1.14.287" in v)
g = open(os.path.join(ROOT, "android", "app", "build.gradle.kts"),
         encoding="utf-8").read()
check("gradle = 289 / 1.14.287",
      'versionCode = 289' in g and 'versionName = "1.14.287"' in g)

print()
if fails:
    print("✘ %d چک قرمز: %s" % (len(fails), "; ".join(fails[:8])))
    sys.exit(1)
print("✔ همهٔ چکها سبز است (نشانگرِ خروجیِ همین ران — v1.14.277)")
