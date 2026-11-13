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
GIRL_MARKS = ["cg-tail", "cg-ear-l", "cg-book", "cg-blush",
              "M28 36 Q10 42 12 62", "M92 36 Q110 42 108 62",
              'rect x="46" y="124"', 'line x1="52" y1="112"',
              "l-8 -5.5 l1.5 10.5", "M47 84 Q60 78"]
EXTRA_MARKS = ["cg-anger", "cg-steam", "cg-ball", "cg-music", "cg-mv-pout",
               "cg-mv-shout", "cg-mv-o", "cg-mv-song", "cg-eyes-annoy",
               "cg-eyes-angry", "cg-eyes-up"]

print("== ۱) اندروید reader.html ==")
chk("شخصیتِ دخترِ گربه‌ای (گوش/دُم/کتاب/دُم‌گوشی/پاپیون/پاها)",
    'id="mcat"' in android and
    all(k in android for k in GIRL_MARKS))
chk("۱۳ حالتِ CSS",
    all(f".mcat.{s} " in android or f".mcat.{s}{{" in android or
        f".mcat.{s} ." in android for s in STATES))
chk("عناصرِ اضافه (خشم/بخار/توپ/نت/دهانها)",
    all(k in android for k in EXTRA_MARKS))
chk("توپِ بزرگ‌شده + نتهای کشیده (SVG)",
    'r="7.5"' in android and 'class="cg-music"' in android and
    'class="n1"' in android)
chk("علامتِ خشمِ ضربدری (۴ خطِ قرمز)",
    android.count('stroke="#ff3d2e" stroke-width="3.6"') == 1 and
    "M81 15 L88 22" in android)
chk("چج: سرِ به‌دور + گونهٔ پف‌کرده + مخفی‌شدنِ blush",
    "translateX(-7px) rotate(-10deg)" in android and
    ".mcat.st-annoy .cg-blush{display:none}" in android and
    'circle cx="35" cy="61.5" r="5.2"' in android)
chk("کتک: ۵ ضربهٔ <۲٫۲ث = اعصابی + احتمالِ خروج",
    "fast >= 5" in android and "mcatAngryT = now + 2100" in android and
    "Math.random() < 0.45" in android and "mcatGoAway" in android)
chk("نوازشِ زیاد: ۵ ضربه = چج → گوشهٔ سایت",
    "mcatTaps.length >= 5" in android and "mcatGoCorner" in android and
    "mcatHideTill = Date.now() + 12000" in android)
chk("قهر: لبه + محو + سرک + برگشت",
    ".mcat.away{opacity:0" in android and "mcatStartPeek" in android and
    ".mcat.st-peek svg{clip-path:inset(0 0 22% 34%)" in android and
    ".mcat.peek-r svg{clip-path:inset(0 34% 22% 0)" in android)
chk("حوصله‌سررفتگی: ۸–۲۰ث = چرخش/توپ/آهنگِ تصادفی",
    "now - 8000" in android and "now - 21000" in android and
    "'st-spin', 'st-ball', 'st-music'" in android)
chk("اسکرول بازی را قطع می‌کند",
    "if (mcatActT) { mcatActT = 0; mcatActSt = ''; }" in android)
chk("اولویت: نوازش > چج > اعصابی > بازی > غم > هیجان > خواب > استرس",
    android.index("mcatPatT > now) { mcatSet('st-pat')") <
    android.index("mcatAnnoyT > now) { mcatSet('st-annoy')") <
    android.index("mcatAngryT > now) { mcatSet('st-angry')") <
    android.index("now - mcatBotT > 2200) mcatSet('st-sad')") <
    android.index("mcatFastT > now - 1200) mcatSet('st-exc')") <
    android.index("now - 22000) mcatSet('st-sleep')") <
    android.index("scrollable && p >= 0.9) mcatSet('st-stress')"))
chk("جشنهای ۲۵/۵۰/۷۵٪ یک‌بار",
    "MCAT_MILE" in android and "mstep > mcatMile" in android)
chk("سلامِ اولِ صفحه",
    "سلام! بریم بخونیم؟" in android)
chk("ضربه به قایم/سرک = برگشت",
    "پیدا کردی؟!" in android and "MCAT_BACK" in android)
chk("قلابِ تستِ بی‌ضرر (۱۳ حالت)",
    "__mcatForce" in android and "st-away" in android)

print("== ۲) وبِ زنده (_LIVE_READER_TMPL) ==")
chk("دخترِ گربه‌ای + ۱۳ حالت",
    'id="mcat"' in live and all(k in live for k in GIRL_MARKS) and
    "st-music .cg-mv-song" in live and "st-angry .cg-anger" in live)
chk("ES5 (بدون const/arrow در بلوکِ mcat)",
    "var mcatState = 'st-read';" in live and
    "function mcatTick(){" in live)
chk("کتک/چج/قایم/سرک + جشن + سلام",
    all(k in live for k in ["fast >= 5", "mcatGoCorner", "mcatGoAway",
                            "mcatStartPeek", "MCAT_MILE", "بریم بخونیم؟",
                            "یه صفحهٔ تازه رسید!"]))
chk("window-scroll + mcatInfo",
    "window.addEventListener('scroll'" in live and
    "function mcatInfo(){" in live)

print("== ۳) نمایشگرِ مستقل (build_reader_html) ==")
chk("_MCAT_HTML دخترِ گربه‌ای",
    "_MCAT_HTML = (" in app and "+ _MCAT_HTML +" in app and
    all(k in app for k in GIRL_MARKS))
chk("۱۳ حالت + عناصرِ اضافه در CSS مستقل",
    all(k in standalone or k in app for k in STATES + EXTRA_MARKS))
chk("کتک/چج/قایم/سرک + جشن (بدون جشنِ صفحهٔ تازه)",
    all(k in standalone for k in ["fast >= 5", "mcatGoCorner", "mcatGoAway",
                                  "mcatStartPeek", "MCAT_MILE"]))
chk("قلابِ تست",
    "__mcatForce" in standalone and "st-away" in standalone)

print("== ۴) همگامیِ سه نمایشگر ==")
keys = ["mcatGoCorner", "mcatGoAway", "mcatStartPeek", "MCAT_MILE",
        "MCAT_ANGRY", "cg-music", "st-peek"]
for k in keys:
    chk(f"«{k}» در هر سه",
        k in android and k in live and (k in standalone or k in app))

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
chk("APP_VER سه‌جا یکسانِ 1.14.268",
    m and b and v_name and m.group(1) == b.group(1) == v_name.group(1)
    == "1.14.268")
chk("versionCode/Name یکسان (272)",
    v_code and g_code and v_code.group(1) == g_code.group(1) == "272"
    and v_name and g_name and v_name.group(1) == g_name.group(1))
print(f"  نسخه: {m.group(1) if m else '?'} / code={v_code.group(1) if v_code else '?'}")

print()
if FAILS:
    print(f"✗ {len(FAILS)} مورد قرمز: {FAILS}")
    sys.exit(1)
print(f"✓ همهٔ {OKS} چک سبز — v1.14.268")
