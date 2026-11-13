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
_j = app.index('js = r\"\"\"', app.index("def build_reader_html"))
standalone = app[_j + 10:app.index('"""', _j + 10)]

print("== ۱) اندروید reader.html ==")
chk("fabDefs پنج‌تایی با cmp",
    "key: 'cmp', ic: '\\u21c4', lb: 'قبل/بعد'" in android)
chk("کلیکِ cmp مقایسه را باز/بسته میکند",
    "if (k === 'cmp') { if (cmpOn) cmpClose(); else cmpOpenFn(); updateFan(); return; }" in android)
chk("fabUp فقط دوحالته است (باز/بسته — بدون چرخهٔ سه‌تایی)",
    "fanState = fanState ? 0 : 1;" in android and "(fanState + 1) % 3" not in android)
chk("برچسبِ فاب: بسته=منو، باز=✕",
    "fab.textContent = show ? '\\u2715' : 'منو';" in android)
chk("کلاسِ open روی فاب",
    "fab.classList.toggle('open', show);" in android)
chk("CSS حالتِ open",
    "#fab.open{background:#2c1210;color:#ffb3ab;font-size:1.2rem}" in android)
chk("cmpClose دیگر فن را نمی‌بندد (فن برای گزینهٔ بعدی باز می‌ماند)",
    "if (fanState === 2) { fanState = 0; updateFan(); }" not in android.split("cmpClose")[1][:400])
chk("fanPositions: جهت به مرکزِ صفحه",
    "Math.atan2(window.innerHeight / 2 - cy" in android)
chk("مانعِ خودِ فاب در جداسازی",
    "فاب ثابت است" in android)
chk("فاصلهٔ فن‌به‌فن ۱۰px و فن‌به‌فاب ۱۵px",
    "68 - Math.abs" in android and "74 - Math.abs" in android)

print("== ۲) وبِ زنده (_LIVE_READER_TMPL) ==")
chk("fanDefs پنج‌تایی با cmp", "key: 'cmp', ic: '⇄', lb: 'قبل/بعد'" in live)
chk("کلیکِ cmp", "if (k === 'cmp') { if (cmpOn) cmpClose(); else cmpOpenFn(); updateFan(); return; }" in live)
chk("fabUp دوحالته", "fanState = fanState ? 0 : 1;" in live and "(fanState + 1) % 3" not in live)
chk("برچسبِ فاب ✕", "fab.textContent = show ? '✕' : 'منو';" in live)
chk("کلاسِ open", "fab.classList.toggle('open', show);" in live)
chk("CSS حالتِ open", "#fab.open{background:#2c1210;color:#ffb3ab;font-size:1.2rem}" in live)
chk("fanPositions + مانعِ فاب", "Math.atan2(window.innerHeight / 2 - cy" in live and "فاب ثابت است" in live)
chk("cmpClose بدون بستنِ فن",
    "if (fanState === 2) { fanState = 0; updateFan(); }" not in live.split("cmpClose")[1][:400])

print("== ۳) نمایشگرِ مستقل (build_reader_html) ==")
chk("fanDefs پنج‌تایی با صفحه‌ها",
    "key: 'seek', ic: '\\u21c4', lb: 'صفحه‌ها'" in standalone)
chk("دکمهٔ صفحه‌ها خطِ seek را باز/بسته میکند",
    "fanState = (fanState === 2) ? 1 : 2;" in standalone)
chk("fabUp دوحالته", "fanState = fanState ? 0 : 1;" in standalone
    and "(fanState + 1) % 3" not in standalone)
chk("برچسبِ فاب ✕", "fab.textContent = show ? '\\u2715' : 'منو';" in standalone)
chk("fanPositions + مانعِ فاب", "Math.atan2(window.innerHeight / 2 - cy" in standalone
    and "فاب ثابت است" in standalone)
chk("CSS حالتِ open", "#fab.open{background:#2c1210;color:#ffb3ab;font-size:1.2rem}" in app)

print("== ۴) همگامیِ نسخه ==")
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
chk("APP_VER سه‌جا یکسان (manga.py / 00_base / VERSION)",
    m and b and v_name and m.group(1) == b.group(1) == v_name.group(1))
chk("versionCode در VERSION و gradle یکسان",
    v_code and g_code and v_code.group(1) == g_code.group(1))
chk("versionName در VERSION و gradle یکسان",
    v_name and g_name and v_name.group(1) == g_name.group(1))
print(f"  نسخه: {m.group(1) if m else '?'} / code={v_code.group(1) if v_code else '?'}")

print()
if FAILS:
    print(f"✗ {len(FAILS)} مورد قرمز: {FAILS}")
    sys.exit(1)
print(f"✓ همهٔ {OKS} چک سبز — v1.14.266")
