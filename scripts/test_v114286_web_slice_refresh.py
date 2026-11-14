#!/usr/bin/env python3
import json
import os
import re
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

APP = os.path.join(HERE, "manga_app.py")
SRC = open(APP, encoding="utf-8").read()

PASS = []
FAIL = []


def chk(name, ok, info=""):
    (PASS if ok else FAIL).append(name)
    print(("  ✔ " if ok else "  ✘ ") + name + (f" — {info}" if info else ""))


def dedent_nested(code, pad):
    n = len(pad)
    return "\n".join((ln[n:] if ln.startswith(pad) else ln)
                     for ln in code.split("\n"))


print("۱) برشکارِ وب (کدِ واقعی از manga_app.py):")
m = re.search(r"(        def _start_live_slicer\(.*?)(?=\n        def _poll_live_gallery)",
              SRC, re.S)
chk("کدِ برشکار پیدا شود", bool(m))
ns = {"json": json, "os": os, "threading": threading, "time": time}
exec(compile(dedent_nested(m.group(1), "        "), "_sl", "exec"), ns)
start_slicer = ns["_start_live_slicer"]

from PIL import Image

tmp = tempfile.mkdtemp(prefix="manga_slice_test_")
live = os.path.join(tmp, "live")
os.makedirs(live, exist_ok=True)
job = {"lock": threading.Lock(), "live_slicer": None}
start_slicer(live, job)


def wait_slices(mark, want_n, timeout=6.0):
    t0 = time.time()
    p = os.path.join(live, mark)
    while time.time() - t0 < timeout:
        try:
            with open(p, encoding="utf-8") as f:
                j = json.load(f)
            if int(j.get("n", -1)) == want_n:
                return j
        except Exception:
            pass
        time.sleep(0.1)
    return None


Image.new("RGB", (900, 4300), (200, 30, 30)).save(
    os.path.join(live, "live_0001.jpg"), quality=90)
j1 = wait_slices("w_0001.json", 3)
chk("عکسِ بلند → ۳ برشِ ۲۰۰۰px + مارکر", bool(j1))
if j1:
    d1 = Image.open(os.path.join(live, "w_0001_1.jpg")).size
    d3 = Image.open(os.path.join(live, "w_0001_3.jpg")).size
    chk("ابعادِ برشها: ۲۰۰۰/۲۰۰۰/۳۰۰",
        d1 == (900, 2000) and d3 == (900, 300))
src1 = int(j1.get("src") or 0) if j1 else 0
chk("مارکر src = میلیثانیهٔ فایل (۱۳ رقم)",
    src1 > 10 ** 12)

mt_before = os.path.getmtime(os.path.join(live, "w_0001_1.jpg"))
time.sleep(0.6)
mt_after = os.path.getmtime(os.path.join(live, "w_0001_1.jpg"))
chk("idempotent — بدونِ تغییر، برش بازنویسی نمیشود",
    mt_before == mt_after)

Image.new("RGB", (800, 1200), (30, 200, 30)).save(
    os.path.join(live, "live_0002.jpg"), quality=90)
j2 = wait_slices("w_0002.json", 0)
chk("عکسِ کوتاه → مارکرِ n=0 (بدونِ برش)", bool(j2))
chk("برشی برایِ عکسِ کوتاه ساخته نشد",
    not os.path.exists(os.path.join(live, "w_0002_1.jpg")))

Image.new("RGB", (900, 6500), (30, 30, 200)).save(
    os.path.join(live, "live_0001.jpg"), quality=90)
j1b = wait_slices("w_0001.json", 4, timeout=8)
chk("تغییرِ فایل → برشِ تازه (۳→۴)", bool(j1b))
chk("برشِ تازه srcِ تازه دارد",
    bool(j1b) and int(j1b.get("src") or 0) > src1)

cnt = sum(1 for f in os.listdir(live)
          if f.lower().endswith(".jpg") and f.startswith("live_")
          and not f.lower().endswith("_base.jpg"))
chk("شمارشِ live_ فقط عکسهایِ اصلی (۲)", cnt == 2,
    f"found {cnt}")

job["live_slicer"]["stop"] = True

print("۲) ریدرِ نهایی (build_reader_html — کدِ واقعی):")
src_lines = SRC.split("\n")
s = next(i for i, l in enumerate(src_lines)
         if l.startswith("    def build_reader_html("))
e = next(i for i in range(s + 1, len(src_lines))
         if src_lines[i].strip() == "return page")
code = dedent_nested("\n".join(src_lines[s:e + 1]), "    ")
ns2 = {"os": os,
       "TX": lambda k, d=None, **kw: d if d is not None else k,
       "_ui_t_head": lambda: ""}
exec(compile(code, "_br", "exec"), ns2)
build = ns2["build_reader_html"]

outd = os.path.join(tmp, "out")
os.makedirs(outd, exist_ok=True)
Image.new("RGB", (690, 5000), (90, 30, 140)).save(
    os.path.join(outd, "tall.jpg"), quality=90)
Image.new("RGB", (784, 1280), (30, 90, 140)).save(
    os.path.join(outd, "short.jpg"), quality=90)
html = build([os.path.join(outd, "tall.jpg"),
              os.path.join(outd, "short.jpg")], standalone=True)
urls = re.findall(r'data-src="([^"]+)"', html)
chk("عکسِ بلند → ۳ <img> + کوتاه → ۱ <img>", len(urls) == 4,
    f"got {len(urls)}")
chk("برشها با _v2_ نامگذاری میشوند",
    any("_v2_1.jpg" in u for u in urls))
chk("عکسِ کوتاه تک‌پیش‌نمایشِ _v2.jpg",
    any(u.endswith("_v2.jpg") for u in urls))
html2 = build([os.path.join(outd, "tall.jpg"),
               os.path.join(outd, "short.jpg")], standalone=True)
urls2 = re.findall(r'data-src="([^"]+)"', html2)
chk("کش: بازسازیِ دوم همان URLها", urls == urls2)

print("۳) قالبِ ریدرِ زنده (JS — فیکسِ حلقهٔ رفرش):")
chk("آخرین-خط-برای-هر-اسلات (last[s0])",
    "last[s0] = m[1]" in SRC and "for (var slotStr in last)" in SRC)
chk("فیکسِ closure — IIFE برایِ هر اسلات",
    "(function(slot, engMt){" in SRC)
chk("parseInt برایِ src مارکر (نه |0)",
    "parseInt(j && j.src, 10)" in SRC)
chk("سرکِ سبک — HEAD/مارکر (نه دانلودِ کامل)",
    "method: 'HEAD'" in SRC and "sliceMark(a)" in SRC)
chk("برشِ وب در قالب — slotw + sliceUrl",
    "slotw" in SRC and "sliceUrl(i, k)" in SRC)
chk("پیشفرضِ بدونِ برشکار — فال‌بکِ عکسِ کامل",
    "swapFullSlot(el2, slot)" in SRC)

print("۴) نسخهها:")
for p, v in (("manga_app.py", "1.14.287"), ("manga.py", "1.14.287"),
             ("manga_sections/00_base.py", "1.14.287")):
    t = open(os.path.join(HERE, p), encoding="utf-8").read()
    chk(f"APP_VER در {p} = {v}", f'APP_VER = "{v}"' in t)
vt = open(os.path.join(HERE, "VERSION"), encoding="utf-8").read()
chk("VERSION = 288 / 1.14.287",
    "versionCode=289" in vt and "versionName=1.14.287" in vt)
gt = open(os.path.join(HERE, "android/app/build.gradle.kts"),
          encoding="utf-8").read()
chk("gradle = 288 / 1.14.287",
    "versionCode = 289" in gt and 'versionName = "1.14.287"' in gt)

print(f"\n{'='*50}\n✔ {len(PASS)} سبز | ✘ {len(FAIL)} قرمز")
if FAIL:
    print("شکستها:", ", ".join(FAIL))
    sys.exit(1)
print("همهٔ چکها سبز است.")
