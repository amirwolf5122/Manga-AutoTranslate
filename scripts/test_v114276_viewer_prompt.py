#!/usr/bin/env python3
import os
import re
import sys
import tempfile
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEC = os.path.join(ROOT, "manga_sections")
APP = os.path.join(ROOT, "manga_app.py")
READER = os.path.join(ROOT, "android", "app", "src", "main", "assets",
                      "reader.html")
BRIDGE = os.path.join(ROOT, "android", "app", "src", "main", "python",
                      "bridge.py")
OUTCOLLECT = os.path.join(ROOT, "android", "app", "src", "main", "python",
                          "out_collect.py")
MAIN_KT = os.path.join(ROOT, "android", "app", "src", "main", "java", "com",
                       "amirwolf", "mangatranslator", "MainActivity.kt")

fails = []
def check(desc, ok, extra=""):
    print(("  [✓] " if ok else "  [✗] ") + desc + ("" if ok else " — " + str(extra)[:160]))
    if not ok:
        fails.append(desc)

print("۱) نشتِ دیباگ به نمایشِ اصلی (bridge + out_collect)")
sys.path.insert(0, os.path.dirname(OUTCOLLECT))
import out_collect as oc

check("مسیرِ کش = همسانِ موتور (res.pdf → res.cache)",
      oc.cache_dir_of("/x/y/res.pdf") == "/x/y/res.cache")
check("کشِ html هم مشترک", oc.cache_dir_of("/x/y/res.html") == "/x/y/res.cache")
check("پوشهٔ بیپسوند همان میماند",
      oc.cache_dir_of("/x/y/outdir") == "/x/y/outdir.cache")

tmp = tempfile.mkdtemp(prefix="v276_")
try:
    os.makedirs(os.path.join(tmp, "res.cache", "out_safe_v3_style-abc"))
    os.makedirs(os.path.join(tmp, "res.cache", "debug_safe_v3"))
    os.makedirs(os.path.join(tmp, "live"))
    os.makedirs(os.path.join(tmp, "live_debug"))
    os.makedirs(os.path.join(tmp, "input_batch"))
    os.makedirs(os.path.join(tmp, "res.cache", "src"))
    for n, d in [("t1.jpg", "res.cache/out_safe_v3_style-abc"),
                 ("t2.jpg", "res.cache/out_safe_v3_style-abc"),
                 ("t1_debug.jpg", "res.cache/debug_safe_v3"),
                 ("t1_debug_base.jpg", "res.cache/debug_safe_v3"),
                 ("t1.json", "res.cache/debug_safe_v3"),
                 ("live_0001.jpg", "live"), ("live_0002.jpg", "live"),
                 ("live_0001.jpg", "live_debug"),
                 ("live_0002.jpg", "live_debug"),
                 ("live_0001_base.jpg", "live_debug"),
                 ("live_0001.json", "live_debug"),
                 ("p1.jpg", "input_batch"), ("src_img.jpg", "res.cache/src")]:
        io_p = os.path.join(tmp, d, n)
        open(io_p, "wb").write(b"x")
    imgs, dbg = oc.collect(os.path.join(tmp, "res.pdf"), tmp)
    bn = lambda l: [os.path.basename(x) for x in l]
    check("نمایشِ اصلی = فقط نهاییهایِ کش", bn(imgs) == ["t1.jpg", "t2.jpg"], bn(imgs))
    check("لیستِ دیباگ = فقط دیباگ (بدونِ پایه)", bn(dbg) == ["t1_debug.jpg"], bn(dbg))
    check("هیچ فایلِ live_debug در نمایشِ اصلی نیست",
          all("live_debug" not in x for x in imgs))
    check("هیچ فایلِ live_debug در دیباگ نیست (پایه=روکشِ نمایشگر است)",
          all("live_debug" not in x for x in dbg))
    check("input_batch در هیچ‌کدام نیست",
          all("input_batch" not in x for x in imgs + dbg))

    shutil.rmtree(os.path.join(tmp, "res.cache"))
    imgs2, dbg2 = oc.collect(os.path.join(tmp, "res.pdf"), tmp)
    check("فالبک: نمایشِ اصلی = live (نهایی)", bn(imgs2) == ["live_0001.jpg", "live_0002.jpg"], bn(imgs2))
    check("فالبک: live_debug → دیباگ (نه نمایشِ اصلی)",
          all("live_debug" in x for x in dbg2) and not any("live_debug" in x for x in imgs2),
          (bn(imgs2), bn(dbg2)))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

bsrc = open(BRIDGE, encoding="utf-8").read()
check("bridge از out_collect استفاده میکند",
      "from out_collect import collect" in bsrc)
check("فالبکِ قدیمیِ bridge هم پوشهٔ debugدار را میشناسد",
      '_dir_dbg = "debug" in dname' in bsrc)

print("۲) ریدرِ اندروید (reader.html)")
r = open(READER, encoding="utf-8").read()
check("دکمهٔ فول‌اسکرین حذف شد", 'data-act="fs"' not in r)
check("هندلرِ fs هم حذف شد", "act === 'fs'" not in r)
check("میانبرِ f هم حذف شد", "e.key === 'f'" not in r)
check("نشانِ زیرِ گربه حذف شد", '<div class="mcat-bub"' not in r)
check("گاردِ mcatBub (null-safe)", "if (mcatBub) mcatBub.textContent" in r
      and "if (mcatBub) mcatBub.classList" in r)
check("چیپِ پیشرفت روی نوارِ پایین",
      r.count('id="progLab"') == 1 and ".prog-lab{" in r)
check("چیپ: درصد + صفحهٔ جاری", "fa(curPageIdx() + 1) + '/' + fa(stackCount())" in r)
check("نوشتههایِ ناحیهها حذف (جعبهها ماندهاند)",
      "آویزون شو" not in r and 'class="mz mz-top" data-z="top"' in r)
check("شنوندهٔ دیباگ همیشه وصل است",
      "mtEl.addEventListener('click'" in r and
      re.search(r"if \(mtEl && ndbg > 0\) \{\s*mtEl.style.display = '';\s*mtEl.addEventListener", r) is None)
check("دیباگِ دیررس دکمه را روشن میکند",
      "if (mtEl && mtEl.style.display === 'none') mtEl.style.display = ''" in r)

print("۳) وب (manga_app.py)")
a = open(APP, encoding="utf-8").read()
m = re.search(r'_LIVE_READER_TMPL = r"""(.*?)"""', a, re.S)
check("تمپلیتِ ریدرِ زنده پیدا شد", m is not None)
if m:
    t = m.group(1)
    check("وبِ زنده: نوشتههایِ ناحیه حذف", "آویزون شو" not in t)
    check("وبِ زنده: نشانِ گربه حذف", '<div class="mcat-bub"' not in t)
    check("وبِ زنده: چیپِ پیشرفت + نوار", 'id="plab"' in t and ".plab{" in t)
    check("وبِ زنده: چیپ خودکفا (بدونِ faNِ بیرون)",
          "var fa = function" in t and "faN(Math.round(pc))" not in t)
check("مستقل: چیپِ پیشرفت", a.count('id="progLab"') == 1)
check("مستقل: نشانِ گربه حذف", "'<div class=\"mcat-bub\"" not in a)
check("گاردهای mcatBub در هر دو تمپلیت",
      a.count("if (mcatBub) mcatBub.textContent") == 2)
check("نوشتههایِ ناحیه در کلِ فایل حذف", "آویزون شو!" not in a)

print("۴) پرامپت — «\\n شو نشون نده»")
sys.path.insert(0, ROOT)
import manga
lit = "\\" + "n"
check("pramptها \nِ لفظی ندارند",
      lit not in manga.FLASH_PROMPT and lit not in manga.FLASH_LITE_PROMPT)
check("خطِ نوِ واقعی دارند", "\n" in manga.FLASH_LITE_PROMPT)
check("سه‌خطِ پشتِهم جمع شد", "\n\n\n" not in manga.FLASH_LITE_PROMPT
      and "\n\n\n" not in manga.FLASH_PROMPT)
old_lite = ("قوانین ترجمه:" + lit + lit + "\r\n1. روانی، سلیس بودن و جذابیت کلام: "
            "ترجمه باید به زبان فارسی امروزی، طبیعی و پویا باشد.")
check("بکاپِ قدیمی (با \\n) باز هم پیشفرض شناخته میشود",
      manga.is_known_default_instruction(manga.FLASH_LITE_PROMPT) and
      not manga._norm_prompt_text(manga.FLASH_LITE_PROMPT).startswith("x"))

print("۵) اندروید (MainActivity.kt)")
k = open(MAIN_KT, encoding="utf-8").read()
check("بازیابیِ بکاپ: \\nِ لفظی پاک میشود",
      's.replace("\\\\r\\\\n", "\\n").replace("\\\\n", "\\n")' in k)
check("هینتِ نمایشگر بدونِ فول‌اسکرین",
      "بزرگ/کوچک/پهنا\"" in k and "فول‌اسکرین\"" not in k)

print("۶) نسخهها")
check("APP_VER = 1.14.287", manga.APP_VER == "1.14.287")
v = open(os.path.join(ROOT, "VERSION"), encoding="utf-8").read()
check("VERSION = 289 / 1.14.287",
      "versionCode=289" in v and "versionName=1.14.287" in v)
g = open(os.path.join(ROOT, "android", "app", "build.gradle.kts"),
         encoding="utf-8").read()
check("gradle = 289 / 1.14.287",
      'versionCode = 289' in g and 'versionName = "1.14.287"' in g)

print()
if fails:
    print("✘ %d چک قرمز: %s" % (len(fails), "; ".join(fails[:8])))
    sys.exit(1)
print("✓ همهٔ چکهایِ v1.14.276 سبز است.")
