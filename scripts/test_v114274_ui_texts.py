#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import ast
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEC = os.path.join(HERE, "manga_sections")
APP = os.path.join(HERE, "manga_app.py")
RDR = os.path.join(HERE, "android", "app", "src", "main", "assets", "reader.html")
KT = os.path.join(HERE, "android", "app", "src", "main", "java", "com",
                  "amirwolf", "mangatranslator", "MainActivity.kt")
BR = os.path.join(HERE, "android", "app", "src", "main", "python", "bridge.py")

fails = []


def check(name, cond, extra=""):
    print(("  ✔ " if cond else "  ✘ ") + name + ((" — " + extra) if extra else ""))
    if not cond:
        fails.append(name)


print("۱) فایلِ واحدِ متن‌ها")
spec = importlib.util.spec_from_file_location(
    "uix", os.path.join(SEC, "05_ui_texts.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
T = m.UI_TEXTS
check("UI_TEXTS دیکشنری است", isinstance(T, dict), "%d کلید" % len(T))
check("کلیدها یونیک", len(set(T)) == len(T))
bad_type = [k for k, v in T.items()
            if not (isinstance(v, str) or (isinstance(v, list) and all(isinstance(x, str) for x in v)))]
check("مقدارها str یا لیستِ str", not bad_type, str(bad_type[:3]))
groups = {}
for k in T:
    groups.setdefault(k.split(".")[0], 0)
    groups[k.split(".")[0]] += 1
check("گروههای app/rdr/cmp/say/mcat", set(groups) == {"app", "rdr", "cmp", "say", "mcat"}, str(groups))
check("say.* همگی لیستند (به‌جز تک‌متنها)", all(
    isinstance(v, list) for k, v in T.items()
    if k.startswith("say.") and k not in ("say.still_angry", "say.tired", "say.fresh")))

print("۲) ui_texts_json")
j = m.ui_texts_json()
check("JSON معتبر", isinstance(json.loads(j), dict))
check("همان تعداد کلید", len(json.loads(j)) == len(T))

print("۳) manga_app.py")
src = open(APP, encoding="utf-8").read()
ast.parse(src)
check("سورس پایتون سالم", True)
n_tx = len(re.findall(r'\bTX\("', src))
check("≥45 فراخوانِ TX(", n_tx >= 45, str(n_tx))
check("لودرِ importlib 05_ui_texts", "05_ui_texts.py" in src and "_load_ui_texts" in src)
check("helperِ UT تعریف شده", "_UT_JS_HELPER" in src and "function UT(k,d)" in src)
check("دو تزریقِ _ui_t_head", src.count("+ _ui_t_head() +") + src.count("_uit_head = _ui_t_head()") >= 2)

seg = re.search(
    r"(def _load_ui_texts\(\):.*?)\nUI_TEXTS = _load_ui_texts\(\)",
    src, re.S)
check("بلوکِ لودر پیدا شد", seg is not None)
h = "<script>window.UI_T={};function UT(k,d){return d}</script>"
if seg:
    ns = {"os": os, "json": json, "HERE": HERE}
    exec(compile(ast.parse(seg.group(1), APP, "exec"), APP, "exec"), ns)
    ns["UI_TEXTS"] = ns["_load_ui_texts"]()
    for fn in ("TX", "_ui_t_json_file", "_ui_t_head"):
        fm = re.search(r"(def %s\(.*?\n    return [^\n]*\n)" % fn, src, re.S)
        if fm:
            try:
                exec(compile(ast.parse(fm.group(1), APP, "exec"), APP, "exec"), ns)
            except SyntaxError:
                pass
    if "TX" in ns:
        check("TX فایل برنده", ns["TX"]("app.run", "x") == T["app.run"])
        check("TX پیش‌فرض", ns["TX"]("__nope__", "dft") == "dft")
    else:
        check("TX قابلِ استخراج", False)
    if "_ui_t_head" in ns:
        h = ns["_ui_t_head"]()
    check("_ui_t_head محتوا", "window.UI_T=" in h and "function UT" in h
          and "DOMContentLoaded" in h)

print("۴) شبه‌سازیِ ریدرِ زنده")
tmpl_m = re.search(r'_LIVE_READER_TMPL = r"""(.*?)"""', src, re.S)
check("قالب موجود", tmpl_m is not None)
if tmpl_m:
    tmpl = tmpl_m.group(1)
    injected = tmpl.replace("</style></head>", "</style>" + h + "</head>")
    check("window.UI_T در head", "window.UI_T=" in injected)
    check("UT قبل از body", injected.find("function UT") < injected.find("<body>"))
    check("حرفها UT-پیچ", "UT('say.pat'" in injected and "UT('say.fresh'" in injected)
    check("منو/✕/نهایی UT", "UT('rdr.menu'" in injected and "UT('rdr.final'" in injected)

print("۵) reader.html اندروید")
r = open(RDR, encoding="utf-8").read()
check("helperِ UT در head", "function UT(k,d)" in r and r.find("function UT") < r.find("<body"))
for arr in ("MCAT_PAT", "MCAT_HIDE_SAY", "MCAT_BACK2"):
    check("UT " + arr, "UT('say." in r and re.search(r"var %s = UT\(" % arr, r) is not None)
check("UT متنِ ترجمه", "UT('rdr.translating'" in r)
check("UT منو/✕", "UT('rdr.menu'" in r and "UT('rdr.close'" in r)
check("UT فن", "UT('rdr.fan_cmp'" in r and "UT('rdr.fan_close'" in r)
check("UT چیپِ صفحه", "UT('rdr.page'" in r and "UT('rdr.of'" in r)
check("UT خاموشی", "UT('mcat.off_t1'" in r)

print("۶) MainActivity.kt")
k = open(KT, encoding="utf-8").read()
check("خواندنِ ui_texts.json", 'ui_texts.json' in k)
check("تزریقِ window.UI_T", "window.UI_T=" in k)
check("ut() عنوان", 'ut("rdr.title_default"' in k)
check("ut() پیشوندها", 'ut("rdr.live_dbg"' in k)
check("ut() توست", 'ut("rdr.toast_no_reader"' in k)
check("ut() جای‌خالی", 'ut("rdr.translating"' in k)

print("۷) bridge.py")
b = open(BR, encoding="utf-8").read()
ast.parse(b)
check("نوشتنِ ui_texts.json", 'ui_texts.json' in b and "_ui_t_json_file" in b)

print("۸) MANIFEST و لودر")
man = open(os.path.join(SEC, "MANIFEST"), encoding="utf-8").read()
check("در MANIFEST", "05_ui_texts.py" in man)
idx = [man.index(x) for x in ("00_base.py", "05_ui_texts.py", "10_install.py")]
check("بعد از 00_base", idx == sorted(idx), str(idx))

print()
if fails:
    print("✘ %d خراب: %s" % (len(fails), fails))
    sys.exit(1)
print("✔ همهٔ چکها سبز است (%d کلید متن)" % len(T))
