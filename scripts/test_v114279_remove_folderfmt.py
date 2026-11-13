#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "android", "app", "src", "main", "python"))

PASS = 0
FAIL = 0


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name} {extra}")


print("۱) فرمتِ پوشه‌ای از UIها حذف شده؟")
app_src = open(os.path.join(ROOT, "manga_app.py"), encoding="utf-8").read()
check("رادیوی وب بدونِ «پوشهٔ تصاویر»",
      'gr.Radio(["PDF", "ZIP", "HTML", "PSD"],' in app_src)
check("منوی CLI بدونِ گزینهٔ پوشه",
      "4) PSD" in app_src and "پوشهٔ تصاویر   5" not in app_src)
check("ext-map بدونِ کلیدِ پوشه",
      '"پوشهٔ تصاویر": ""' not in app_src)
cli_src = open(os.path.join(ROOT, "manga_sections", "99_cli.py"),
               encoding="utf-8").read()
run_src = open(os.path.join(ROOT, "manga_sections", "95_run.py"),
               encoding="utf-8").read()
check("موتور: شاخهٔ کپیِ پوشه‌ای حذف شد",
      "تصویر در پوشه‌ی" not in run_src)
check("موتور: پسوندِ ناشناخته → PDF",
      "پسوندِ ناشناخته/خالی → PDF" in run_src)

print("۲) مقدارِ کهنه → PDF (بدونِ KeyError)")
import importlib.util
spec = importlib.util.spec_from_file_location(
    "oc", os.path.join(ROOT, "android", "app", "src", "main", "python",
                       "out_collect.py"))
oc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oc)

def web_ext(out_fmt_v):
    out_fmt_v = str(out_fmt_v or "PDF")
    if out_fmt_v not in ("PDF", "ZIP", "HTML", "PSD"):
        out_fmt_v = "PDF"
    return {"PDF": ".pdf", "ZIP": ".zip", "HTML": ".html",
            "PSD": ".psd"}[out_fmt_v]

check("کهنه: «پوشهٔ تصاویر» → .pdf", web_ext("پوشهٔ تصاویر") == ".pdf")
check("کهنه: رشتهٔ خالی → .pdf", web_ext("") == ".pdf")
check("نرمال: PSD → .psd", web_ext("PSD") == ".psd")

print("۳) فالبکِ نمایشگر: فقط جدیدترینِ out* (شبیه‌سازیِ دو سبک)")
tmp = tempfile.mkdtemp(prefix="qa279_")
try:
    cache = os.path.join(tmp, "mix.cache")
    old_d = os.path.join(cache, "out_safe_v3_style-AAAA")
    new_d = os.path.join(cache, "out_safe_v3_style-BBBB")
    co_d = os.path.join(cache, "out_safe_v3_style-CCCC_cleanonly")
    for d in (old_d, new_d, co_d):
        os.makedirs(d, exist_ok=True)
    open(os.path.join(old_d, "p1.jpg"), "wb").write(b"x")
    open(os.path.join(old_d, "p2.jpg"), "wb").write(b"x")
    os.utime(old_d, (1000, 1000))
    open(os.path.join(new_d, "p1.jpg"), "wb").write(b"x")
    open(os.path.join(new_d, "p2.jpg"), "wb").write(b"x")
    os.utime(new_d, (2000, 2000))
    open(os.path.join(co_d, "p1.jpg"), "wb").write(b"x")
    os.utime(co_d, (1500, 1500))

    imgs, dbg = oc.collect(os.path.join(tmp, "mix.pdf"), tmp)
    check("اندروید فالبک: فقط جدیدترین (۲ صفحه از BBBB)",
          len(imgs) == 2 and all("BBBB" in p for p in imgs),
          f"got={imgs}")

    with open(os.path.join(cache, "last_out.json"), "w",
              encoding="utf-8") as fh:
        json.dump({"dir": "out_safe_v3_style-BBBB"}, fh)
    imgs2, _ = oc.collect(os.path.join(tmp, "mix.pdf"), tmp)
    check("اندروید نشانگر: همان BBBB",
          len(imgs2) == 2 and all("BBBB" in p for p in imgs2))

    def web_collect(out_v):
        search_dirs = [out_v if os.path.isdir(out_v) else None]
        _last = ""
        try:
            cr = oc.cache_dir_of(out_v)
            with open(os.path.join(cr, "last_out.json"),
                      encoding="utf-8") as fh:
                j = json.load(fh) or {}
            d = os.path.join(cr, str(j.get("dir") or ""))
            if (j.get("dir") and os.path.isdir(d)
                    and any(f.lower().endswith((".webp", ".png", ".jpg",
                                                ".jpeg"))
                            for f in os.listdir(d))):
                _last = d
        except Exception:
            _last = ""
        if _last and os.path.isdir(_last):
            search_dirs.append(_last)
        else:
            cr = oc.cache_dir_of(out_v)
            newest, nmt = "", -1.0
            if os.path.isdir(cr):
                for n in os.listdir(cr):
                    if n != "out" and not n.startswith("out_"):
                        continue
                    p = os.path.join(cr, n)
                    if not os.path.isdir(p):
                        continue
                    if not any(f.lower().endswith((".webp", ".png", ".jpg",
                                                   ".jpeg"))
                               for f in os.listdir(p)):
                        continue
                    mt = os.path.getmtime(p)
                    if mt > nmt:
                        newest, nmt = p, mt
            if newest:
                search_dirs.append(newest)
        found, seen = [], set()
        for root in search_dirs:
            if not root or not os.path.isdir(root):
                continue
            for f in sorted(os.listdir(root)):
                if f.lower().endswith((".webp", ".png", ".jpg", ".jpeg")):
                    p = os.path.join(root, f)
                    if p not in seen:
                        seen.add(p)
                        found.append(p)
        return found

    os.remove(os.path.join(cache, "last_out.json"))
    w1 = web_collect(os.path.join(tmp, "mix.pdf"))
    check("وب فالبک: فقط جدیدترین (۲ صفحه از BBBB)",
          len(w1) == 2 and all("BBBB" in p for p in w1), f"got={w1}")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\nنتیجه: {PASS} ✓ / {FAIL} ✗")
sys.exit(1 if FAIL else 0)
