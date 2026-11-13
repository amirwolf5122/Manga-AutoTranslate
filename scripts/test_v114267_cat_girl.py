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

print("== ۱) اندروید reader.html ==")
chk("عنصرِ mcat با SVG گربه", 'id="mcat"' in android and "cg-tail" in android)
chk("گوش/صورت/کتاب/دُم در SVG",
    all(k in android for k in ["cg-ear-l", "cg-eyes-open", "cg-book", "cg-zzz"]))
chk("شش حالتِ CSS",
    all(k in android for k in
        ["st-read .cg-eyes-open", "st-exc .cg-eyes-happy", "st-sleep .cg-eyes-sleep",
         "st-stress .cg-eyes-worry", "st-sad .cg-eyes-sad", "st-pat .cg-heart"]))
chk("انیمیشنها: باب/پرش/نفس/ویگل/دُم/گوش/پلک",
    all(k in android for k in
        ["mcBob", "mcBounce", "mcBreath", "mcWiggle", "mcTail", "mcEarT", "mcBlink"]))
chk("حبابِ درصد فارسی", "mcat-bub" in android and "FAD" in android)
chk("محوِ حباب بعدِ ۴ثانیه", ".mcat-bub.dim{opacity:0}" in android
    and "toggle('dim', now - mcatMoveT > 4000)" in android)
chk("اولویت: غم > هیجان > خواب > استرس > خواندن",
    android.index("now - mcatBotT > 2200) mcatSet('st-sad')") <
    android.index("mcatFastT > now - 1200) mcatSet('st-exc')")
    < android.index("now - 22000) mcatSet('st-sleep')")
    < android.index("scrollable && p >= 0.9) mcatSet('st-stress')"))
chk("سرعتِ اسکرول > ۰٫۸۵px/ms = هیجان", "0.85) mcatFastT" in android)
chk("خواب بعدِ ۲۲ثانیه", "now - 22000) mcatSet('st-sleep')" in android)
chk("استرس ≥ ۹۰٪ (فقط اسکرول‌پذیر)", "scrollable && p >= 0.9" in android)
chk("غم بعدِ ۲٫۲ثانیه در انتها", "now - mcatBotT > 2200) mcatSet('st-sad')" in android)
chk("نوازش با ضربه + بیداری", "mcatPatT = Date.now() + 1700" in android
    and "MCAT_PAT" in android)
chk("درگ + ذخیرهٔ موقعیت", "mangaCatPos" in android)
chk("جشنِ صفحهٔ تازه", "یه صفحهٔ تازه رسید!" in android or
    "\\u06cc\\u0647 \\u0635\\u0641\\u062d\\u0647\\u0654 \\u062a\\u0627\\u0632\\u0647 \\u0631\\u0633\\u06cc\\u062f!" in android)
chk("قلابِ تستِ بی‌ضرر", "__mcatForce" in android)

print("== ۲) وبِ زنده (_LIVE_READER_TMPL) ==")
chk("mcat + SVG", 'id="mcat"' in live and "cg-tail" in live)
chk("شش حالت + انیمیشنها", "st-pat .cg-heart" in live and "mcBlink" in live)
chk("درصد فارسی + محو", "FAD" in live and ".mcat-bub.dim" in live)
chk("اولویتِ خواب > استرس (ES5)",
    live.index("mcatMoveT < now - 22000) mcatSet('st-sleep');")
    < live.index("inf.m > 320 && inf.pct >= 0.9) mcatSet('st-stress');"))
chk("سرعت/خواب/استرس/غم/نوازش/درگ/جشن/قلاب",
    all(k in live for k in ["0.85) mcatFastT", "now - 22000", "pct >= 0.9",
                            "now - mcatBotT > 2200", "MCAT_PAT", "mangaCatPos",
                            "یه صفحهٔ تازه رسید!", "__mcatForce"]))

print("== ۳) نمایشگرِ مستقل (build_reader_html) ==")
chk("_MCAT_HTML با SVG", "_MCAT_HTML = (" in app and "+ _MCAT_HTML +" in app)
chk("درج در صفحه", "+ _MCAT_HTML +" in app)
chk("CSS/JS مستقل", ".mcat .cg-zzz text:nth-child(2)" in app
    and standalone.count("mcatSet") >= 5)
chk("اولویتِ خواب > استرس (مستقل)",
    standalone.index("mcatMoveT < now - 22000) mcatSet('st-sleep');")
    < standalone.index("inf.m > 320 && inf.pct >= 0.9) mcatSet('st-stress');"))
chk("سرعت/خواب/استرس/غم/نوازش/درگ/قلاب",
    all(k in standalone for k in ["0.85) mcatFastT", "now - 22000", "pct >= 0.9",
                                  "now - mcatBotT > 2200", "MCAT_PAT",
                                  "mangaCatPos", "__mcatForce"]))

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
chk("APP_VER سه‌جا یکسان",
    m and b and v_name and m.group(1) == b.group(1) == v_name.group(1))
chk("versionCode/Name در VERSION و gradle یکسان",
    v_code and g_code and v_code.group(1) == g_code.group(1)
    and v_name and g_name and v_name.group(1) == g_name.group(1))
print(f"  نسخه: {m.group(1) if m else '?'} / code={v_code.group(1) if v_code else '?'}")

print()
if FAILS:
    print(f"✗ {len(FAILS)} مورد قرمز: {FAILS}")
    sys.exit(1)
print(f"✓ همهٔ {OKS} چک سبز — v1.14.267")
