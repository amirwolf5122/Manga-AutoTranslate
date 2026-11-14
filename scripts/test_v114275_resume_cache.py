import ast
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SEC = os.path.join(ROOT, "manga_sections")
APP = os.path.join(ROOT, "manga_app.py")
ENGINE = os.path.join(ROOT, "manga.py")

fails = []


def check(name, cond, extra=""):
    print(("  ✔ " if cond else "  ✘ ") + name + ((" — " + extra) if extra else ""))
    if not cond:
        fails.append(name)


print("۱) سینتکس")
for fn in sorted(os.listdir(SEC)):
    if fn.endswith(".py"):
        try:
            ast.parse(open(os.path.join(SEC, fn), encoding="utf-8").read())
            check(fn, True)
        except SyntaxError as e:
            check(fn, False, str(e)[:80])
for fn in (APP, ENGINE):
    try:
        ast.parse(open(fn, encoding="utf-8").read())
        check(os.path.basename(fn), True)
    except SyntaxError as e:
        check(os.path.basename(fn), False, str(e)[:80])

print("۲) نشانه‌های موتور در بخش‌ها (manga.py لودر است)")
esrc = open(os.path.join(SEC, "95_run.py"), encoding="utf-8").read() \
    + open(os.path.join(SEC, "60_input.py"), encoding="utf-8").read() \
    + open(os.path.join(SEC, "99_cli.py"), encoding="utf-8").read()
for marker, desc in [
    ("_cache_dir_for", "کشِ مستقل از فرمت"),
    ("_trans_sig_of", "امضای ترجمه"),
    ("trans.json", "انبارِ ترجمه"),
    ("state.json", "وضعیتِ امضا/تست"),
    ("_cleanonly", "جداییِ خروجیِ فقط-پاکسازی"),
    ("--translate-retranslate", "فلگِ از-نو"),
    ("از کشِ دانلود", "رزومِ دانلود"),
    ("map.json", "نقشهٔ نرمال‌سازیِ پایدار"),
    ("--translate-retranslate", "فلگ CLI"),
]:
    check(desc, marker in esrc)

print("۳) همخوانیِ امضای ترجمه: موتور ↔ اپ")
sec95 = open(os.path.join(SEC, "95_run.py"), encoding="utf-8").read()
m = re.search(
    r"    @staticmethod\n    def _trans_sig_of\(.*?\n(?=    @staticmethod|    def run\()",
    sec95, re.S)
check("متد در 95_run.py", m is not None)
eng_fn = None
if m:
    body = m.group(0)
    lines = body.split("\n")
    body = "\n".join(ln[4:] if ln.startswith("    ") else ln for ln in lines)
    ns = {}
    exec(body, ns)
    eng_fn = ns.get("_trans_sig_of")
    check("اجرای مستقلِ متد", callable(eng_fn))
asrc = open(APP, encoding="utf-8").read()
ma = re.search(
    r"def _trans_sig_of\(.*?\n(?=\ndef |\nclass )", asrc, re.S)
check("تابع در manga_app.py", ma is not None)
app_fn = None
if ma:
    prelude = """
import re
def _norm_instr(text):
    return re.sub(r"\\s+", " ", (text or "").strip())
def is_custom_instruction(text):
    t = (text or "").strip()
    if not t:
        return False
    return t != "__KNOWN_DEFAULT__"
"""
    ns2 = {}
    exec(prelude + ma.group(0), ns2)
    app_fn = ns2.get("_trans_sig_of")
    check("اجرای مستقلِ تابعِ اپ", callable(app_fn))

if eng_fn and app_fn:
    cases = [
        ("gemini", "", "", "auto", "", False, 0.7, 0.9),
        ("gemini", "gemini-2.5-flash", "", "auto", "", False, 0.7, 0.9),
        ("custom", "gpt-4o-mini", "https://api.example.com/v1", "professional",
         "متنِ فارسیِ محاوره‌ای", False, 0.7, 0.9),
        ("gemini", "", "", "auto", "", True, 0.7, 0.9),
        ("custom", "m", "https://x/v1", "lite", "دستور", True, 0.3, 0.8),
    ]
    all_match = True
    for c in cases:
        e = eng_fn(*c)
        c_app = list(c)
        if c_app[4] == "__KNOWN_DEFAULT__":
            c_app[4] = ""
        a = app_fn(*c_app)
        if e != a:
            all_match = False
            print(f"      ناهمخوان: {c} → eng={e} app={a}")
    check("امضا برایِ ۵ حالت یکسان", all_match)
    base = eng_fn("gemini", "m1", "", "auto", "", False, 0.7, 0.9)
    check("مدلِ عوض‌شده → امضای دیگر",
          base != eng_fn("gemini", "m2", "", "auto", "", False, 0.7, 0.9))
    check("پرامپتِ عوض‌شده → امضای دیگر",
          base != eng_fn("gemini", "m1", "", "auto", "دستورِ نو", False, 0.7, 0.9))
    check("تستِ روشن → امضای دیگر",
          base != eng_fn("gemini", "m1", "", "auto", "", True, 0.7, 0.9))
    check("دما → امضای دیگر",
          base != eng_fn("gemini", "m1", "", "auto", "", False, 0.5, 0.9))
    check("همان تنظیم → همان امضا",
          base == eng_fn("gemini", "m1", "", "auto", "", False, 0.7, 0.9))
    check("api_base برایِ غیرِ custom نادیده",
          eng_fn("gemini", "m", "https://a/v1", "auto", "", False, 0.7, 0.9)
          == eng_fn("gemini", "m", "https://b/v2", "auto", "", False, 0.7, 0.9))

print("۴) مسیرِ کشِ مشترک (_cache_dir_for)")
mc = re.search(
    r"def _cache_dir_for\(.*?\n(?=\ndef |\nclass )", asrc, re.S)
check("تابع در manga_app.py", mc is not None)
if mc:
    ns3 = {}
    exec("import os\n" + mc.group(0), ns3)
    f = ns3["_cache_dir_for"]
    check("pdf و html → یک کش",
          f("/out/ch.5.pdf") == f("/out/ch.5.html") == "/out/ch.5.cache")
    check("zip و psd → همان کش",
          f("/out/ch.5.zip") == f("/out/ch.5.psd") == "/out/ch.5.cache")
    check("پوشه (بی‌پسوند) هم فقط یک کش",
          f("/out/ch.5") == "/out/ch.5.cache")
    check("پسوندِ ناشناخته دست نمی‌خورد",
          f("/out/ch.5.weird") == "/out/ch.5.weird.cache")

print("۵) متن‌های پنجرهٔ پرسش")
spec = importlib.util.spec_from_file_location(
    "uix", os.path.join(SEC, "05_ui_texts.py"))
mm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mm)
T = mm.UI_TEXTS
for k in ("app.ask_title", "app.ask_body", "app.ask_continue",
          "app.ask_fresh", "app.ask_cancel", "app.ask_log"):
    check(k, k in T and isinstance(T[k], str) and len(T[k]) > 2)

print("۶) اپ: پنجرهٔ پرسش و مسیرِ ثابت")
for marker, desc in [
    ("ask_group", "گروهِ پنجره"),
    ("ask_continue_btn", "دکمهٔ ادامه"),
    ("ask_fresh_btn", "دکمهٔ از اول"),
    ("ask_cancel_btn", "دکمهٔ بی‌خیال"),
    ("_ASK_ANSWER", "پاسخِ کاربر"),
    ('_ask_wrap("continue")', "سیم‌کشیِ ادامه"),
    ('_ask_wrap("fresh")', "سیم‌کشیِ از اول"),
    ("input_batch\", \"single", "مسیرِ ثابتِ تک‌آپلود"),
    ("--translate-retranslate", "فلگِ از-نو در cmd"),
    ("_cache_dir_for(out_v)", "کشِ مشترک در نمایشگر"),
    ("modal=gr.update(visible=True)", "نمایشِ پنجره"),
]:
    check(desc, marker in asrc)

print("۷) موتور: جزئیاتِ ادامه/از-نو")
for marker, desc in [
    ("_trans_store_save", "ذخیرهٔ انبار"),
    ("_tkey(page_i", "کلیدِ حباب"),
    ("r._tkey = _tkey", "نشان‌گذاریِ حباب در صف"),
    ("حبابِ ترجمه‌شدهٔ از کش", "پرش از ترجمهٔ تکراری"),
    ("_trans_apply", "اعمالِ انبار"),
    ("not _n.endswith(\"_cleanonly\")", "پاک‌سازیِ بدونِ خروجیِ cleanonly"),
    ("از کشِ دانلود", "رزومِ دانلود"),
]:
    check(desc, marker in esrc)

print("۸) CLI")
cli = open(os.path.join(SEC, "99_cli.py"), encoding="utf-8").read()
check("--translate-retranslate در پارسر", "--translate-retranslate" in cli)
check("passed به سازنده", "translate_retranslate=bool(getattr(args" in cli)
check("فلگ در بخشِ CLI", "--translate-retranslate" in esrc)


print("۹) فیکسِ فرمِ اندروید (extract_ui)")
import subprocess, json as _json
r = subprocess.run([sys.executable,
                    os.path.join(ROOT, "android", "app", "src", "main",
                                 "python", "extract_ui.py"),
                    APP], capture_output=True, text=True)
check("اجرای extract_ui روی manga_app.py", r.returncode == 0,
      r.stderr[-100:] if r.returncode else "")
if r.returncode == 0:
    mf = _json.loads(r.stdout)
    titles = [s["title"] for s in mf.get("sections", [])]
    check("۶ بخشِ فرم برگشته", len(mf.get("sections", [])) >= 6,
          str(len(mf.get("sections", []))))
    check("بخشِ ورودی (آپلود/لینک) هست",
          any("ورودی" in t for t in titles))
    check("بخشِ تنظیمات پیشرفته هست",
          any("تنظیمات پیشرفته" in t for t in titles))
    check("بخشِ بکاپ هست", any("بکاپ" in t or "پشتیبان" in t for t in titles))
    check("بخشِ هوش مصنوعی ۵ فیلد دارد",
          any("هوش مصنوعی" in s["title"] and len(s["fields"]) == 5
              for s in mf["sections"]))
    _fids = set()
    for s in mf["sections"]:
        for f in s["fields"]:
            _fids.add(f.get("id"))
    for _need in ("inp_upload", "inp_path", "provider", "manga_api_keys",
                  "font_upload", "workers", "out_fmt", "quality"):
        check("فیلدِ " + _need, _need in _fids)

print("۱۰) فیکسِ ریدرِ زنده (UT بدون تزریق)")
_esrc = open(ENGINE if os.path.isfile(ENGINE) else APP, encoding="utf-8").read()
_tmpl = re.search(r'_LIVE_READER_TMPL = r"""(.*?)"""',
                  open(APP, encoding="utf-8").read(), re.S)
check("تمپلیتِ ریدر پیدا شد", _tmpl is not None)
if _tmpl:
    _t = _tmpl.group(1)
    check("تعریفِ UT داخلِ خودِ تمپلیت",
          "function UT(k,d)" in _t)
    check("تعریفِ UT قبل از اولین استفاده",
          _t.find("function UT(k,d)") < _t.find("UT('say.pat'"))
check("helper همیشه در _ui_t_head",
      'out += _UT_JS_HELPER' in open(APP, encoding="utf-8").read())

print()
if fails:
    print("✘ %d چک قرمز: %s" % (len(fails), "; ".join(fails[:8])))
    sys.exit(1)
print("✔ همهٔ چکها سبز است (ادامه از همان‌جا / کشِ هوشمند)")
