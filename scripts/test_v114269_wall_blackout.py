# -*- coding: utf-8 -*-
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILS = []
OKS = 0


def chk(name, cond):
    global OKS
    if cond:
        OKS += 1
        print(f"  [ok] {name}")
    else:
        FAILS.append(name)
        print(f"  [FAIL] {name}")


def read(p):
    with open(os.path.join(ROOT, p), encoding="utf-8") as f:
        return f.read()


android = read("android/app/src/main/assets/reader.html")
app = read("manga_app.py")

_i = app.index("_LIVE_READER_TMPL")
live = app[_i:app.index('"""', app.index("</body></html>", _i))]
_j = app.index('js = r"""', app.index("def build_reader_html"))
standalone = app[_j + 10:app.index('"""', _j + 10)]

STATES = ["st-read", "st-exc", "st-sleep", "st-stress", "st-sad", "st-pat",
          "st-annoy", "st-angry", "st-hide", "st-peek", "st-spin",
          "st-ball", "st-music"]
GIRL2_MARKS = ["cg-shift", "cg-wall", "cg-hold", "cg-legs", "cg-bell-l",
               "cg-bell-r", "cg-book", "cg-tail", "cg-blush",
               "M33 44 L9 1 L60 22", "M87 44 L111 1 L60 22",
               'circle cx="32.5" cy="47" r="4.8"', 'line x1="51" y1="112.5"',
               "M63 13 Q57.5 0 72 3.5", "M46 82 Q60 75 74 82"]

print("== ۱) اندروید reader.html ==")
chk("شخصیتِ چبیِ جدید (گوشِ بزرگ + زنگوله/پاپیون + آهوگه + جوراب)",
    'id="mcat"' in android and all(k in android for k in GIRL2_MARKS))
chk("۱۳ حالتِ CSS",
    all(f".mcat.{s} " in android or f".mcat.{s}{{" in android or
        f".mcat.{s} ." in android for s in STATES))
chk("دیوارِ قایم‌شدن: cg-wall + پنهان‌شدنِ دست/کتاب/پا + lean (cg-shift)",
    ".mcat.st-hide .cg-wall{display:block}" in android and
    ".mcat.st-hide .cg-hold{display:none}" in android and
    ".mcat.st-hide .cg-legs{display:none}" in android and
    ".mcat.st-hide .cg-shift{transform:translateX(6px)}" in android and
    'fill="#b7aa92"' in android)
chk("دیوار در SVG: آجر + لبه + دو دستِ روی لبه + نوکِ دُم",
    'class="cg-wall"' in android and 'fill="#5d3f69"' in android and
    'M66 102 Q80 97 85 109' in android)
chk("hide-l آینه‌ای + حبابِ سمتِ چپ",
    ".mcat.hide-l svg{transform:scaleX(-1)}" in android and
    ".mcat.hide-l .mcat-bub" in android)
chk("mcatGoHide: لبهٔ نزدیک + چسبیده به لبه + وسطِ عمودی (نه بالا)",
    "function mcatGoHide" not in android and "mcatGoHide" in android and
    "window.innerWidth - w + 1" in android and
    "window.innerHeight * 0.36" in android and "mcatGoCorner" not in android)
chk("خاموشیِ صفحه: پوششِ mcatOff + چشمهای درخشان + فارسی",
    'id="mcatOff"' in android and "mcOffG" in android and
    "دخترِ گربه‌ای خسته شد!" in android and
    "برای روشن‌کردن، صفحه را لمس کن" in android and
    "@keyframes offBlink" in android)
chk("شمارشِ اذیت: ۱۰ بار = خاموشی (ضربه در چج/اعصابی + اپیزودها)",
    "mcatTeaseN" in android and
    "if (mcatAnnoyT > now || mcatAngryT > now) mcatTeaseN++;" in android and
    "if (mcatTeaseN >= 10) { mcatBlackout(); return; }" in android)
chk("بیداری با لمس + خودکار (۵٫۲ث)",
    "mcatOffEl.addEventListener('pointerdown'" in android and
    "setTimeout(mcatWake, 5200)" in android)
chk("PC: بزرگ‌تر (۹۴px) + پایین-راست + عرضِ پویا",
    "@media (min-width:768px){.mcat{width:94px" in android and
    "bottom:112px" in android and "mcHalf" in android and
    "MCAT.style.bottom = 'auto'" in android)
chk("منو: بدونِ دیباگ/نهایی — قبلی/بعدیِ مقایسه داخلِ فن",
    "{ key: 'dbg'" not in android and "{ key: 'prev'" in android and
    "{ key: 'next'" in android and "cmpOnly: true" in android and
    "(!def.cmpOnly || cmpOn)" in android)
chk("مقایسه: نوارِ بالا حذف + عنوانِ chip + فن بالای مقایسه",
    "cmp-bar" not in android and 'class="cmp-tchip"' in android and
    "#fab{position:fixed;z-index:80" in android and
    ".fbtn{position:fixed;z-index:79" in android)
chk("قلابِ تست (۱۳ حالت + خاموشی)",
    "__mcatForce" in android and "st-away" in android and "st-blackout" in android)

print("== ۲) وبِ زنده (_LIVE_READER_TMPL — ES5) ==")
chk("دخترِ چبی + دیوار + خاموشی",
    'id="mcat"' in live and all(k in live for k in GIRL2_MARKS) and
    'id="mcatOff"' in live and 'class="cg-wall"' in live)
chk("ES5 (بدون const/arrow در بلوکِ mcat)",
    "var mcatState = 'st-read';" in live and
    "function mcatTick(){" in live and "function mcatGoHide(){" in live)
chk("mcatGoHide + شمارشِ اذیت + خاموشی + بیداری",
    all(k in live for k in ["mcatGoHide", "mcatTeaseN", "mcatBlackout",
                            "mcatWake", "window.innerWidth - w + 1",
                            "if (mcatTeaseN >= 10) { mcatBlackout(); return; }"]))
chk("منو: بدونِ دیباگ + قبلی/بعدی داخلِ فن + بدونِ cmpX",
    "{ key: 'dbg'" not in live and "cmpOnly: true" in live and
    "cmpX" not in live and 'class="cmp-tchip"' in live and
    "fanState = 1;\n    updateFan();" in live)
chk("PC: media query + mcHalf",
    "@media (min-width:768px){.mcat{width:94px" in live and "mcHalf" in live)

print("== ۳) نمایشگرِ مستقل (build_reader_html) ==")
chk("_MCAT_HTML دخترِ چبی + دیوار + mcatOff",
    "_MCAT_HTML = (" in app and "+ _MCAT_HTML +" in app and
    all(k in app for k in GIRL2_MARKS) and 'mcatOff' in app)
chk("CSS مستقل: دیوار + خاموشی + PC",
    all(k in app for k in [".mcat.st-hide .cg-wall{display:block}",
                           "#mcatOff", "offBlink",
                           "@media (min-width:768px){.mcat{width:94px"]))
chk("mcatGoHide + خاموشی در ES6 مستقل",
    all(k in standalone for k in ["mcatGoHide", "mcatTeaseN", "mcatBlackout",
                                  "mcatWake", "mcHalf", "st-blackout"]))
chk("قلابِ تست",
    "__mcatForce" in standalone and "st-away" in standalone)

print("== ۴) همگامیِ سه نمایشگر ==")
keys = ["mcatGoHide", "mcatGoAway", "mcatBlackout", "mcatWake", "MCAT_OFF",
        "cg-wall", "cg-shift", "st-peek", "mcHalf", "hide-l"]
for k in keys:
    chk(f"«{k}» در هر سه",
        k in android and k in live and (k in standalone or k in app))
chk("دکمهٔ دیباگ/نهایی فقط بالای صفحه (هر دو نمایشگرِ مانها)",
    'id="mtoggle"' in android and 'id="mtoggle"' in live and
    "{ key: 'dbg'" not in android and "{ key: 'dbg'" not in live)

print("== ۵) همگامیِ نسخه ==")
manga = read("manga.py")
base = read("manga_sections/00_base.py")
ver = read("VERSION")
gradle = read("android/app/build.gradle.kts")
m = re.search(r'APP_VER = "([^"]+)"', manga)
b = re.search(r'APP_VER = "([^"]+)"', base)
v_name = re.search(r'versionName=([\d.]+)', ver)
v_code = re.search(r'versionCode=(\d+)', ver)
g_name = re.search(r'versionName = "([\d.]+)"', gradle)
g_code = re.search(r'versionCode = (\d+)', gradle)
chk("APP_VER سه‌جا یکسانِ 1.14.269",
    m and b and v_name and m.group(1) == b.group(1) == v_name.group(1)
    == "1.14.269")
chk("versionCode/Name یکسان (273)",
    v_code and g_code and v_code.group(1) == g_code.group(1) == "273"
    and v_name and g_name and v_name.group(1) == g_name.group(1))
print(f"  نسخه: {m.group(1) if m else '?'} / code={v_code.group(1) if v_code else '?'}")

print()
if FAILS:
    print(f"✗ {len(FAILS)} مورد قرمز: {FAILS}")
    sys.exit(1)
print(f"✓ همهٔ {OKS} چک سبز — v1.14.269")
