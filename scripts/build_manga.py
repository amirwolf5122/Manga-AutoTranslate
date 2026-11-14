#!/usr/bin/env python3
import os
import py_compile
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SEC_DIR = os.path.join(ROOT, "manga_sections")
MANIFEST_PATH = os.path.join(SEC_DIR, "MANIFEST")
OUT_SINGLE = os.path.join(ROOT, "manga_single.py")
LOADER_PATH = os.path.join(ROOT, "manga.py")

STRIP_START = "# BUILD-STRIP-START"
STRIP_END = "# BUILD-STRIP-END"

VER_RE = re.compile(r'APP_VER\s*=\s*"([0-9][0-9.]*)"')

def _sort_key(name: str):
    i = 0
    while i < len(name) and name[i].isdigit():
        i += 1
    return (int(name[:i]) if i else 10 ** 9, name)

def disk_sections():
    if not os.path.isdir(SEC_DIR):
        return []
    return sorted((n for n in os.listdir(SEC_DIR)
                   if n.endswith(".py") and n[:1].isdigit()),
                  key=_sort_key)

def manifest_sections():
    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            names = [ln.strip() for ln in f.read().split("\n")]
    except OSError:
        return None
    return [n for n in names
            if n and not n.startswith("#") and n.endswith(".py")]

def write_manifest(names):
    body = list(names) + [""]
    with open(MANIFEST_PATH, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(body))

def read_stripped(path: str):
    with open(path, "r", encoding="utf-8", newline="") as f:
        lines = f.read().split("\n")
    out, stripping = [], False
    for ln in lines:
        if ln.strip() == STRIP_START:
            stripping = True
            continue
        if stripping:
            if ln.strip() == STRIP_END:
                stripping = False
            continue
        out.append(ln)
    if out and out[-1] == "":
        out = out[:-1]
    return out

def combined(names):
    parts = []
    for n in names:
        lines = read_stripped(os.path.join(SEC_DIR, n))
        if lines:
            parts.append("\n".join(lines) + "\n")
    return "".join(parts)

def _ver_of_source(src: str):
    m = VER_RE.search(src[:8192])
    return m.group(1) if m else None

def run_checks(names, fix_manifest: bool):
    ok = True

    if not names:
        print("❌ ۱) هیچ بخشی در manga_sections/ نیست.")
        return False

    listed = manifest_sections()
    if listed is None:
        if fix_manifest:
            write_manifest(names)
            print("✔ ۲) MANIFEST نبود — ساخته شد (%d بخش)." % len(names))
        else:
            print("❌ ۲) MANIFEST نیست — python scripts/build_manga.py را اجرا کن.")
            ok = False
    elif listed != names:
        miss = [n for n in names if n not in listed]
        extra = [n for n in listed if n not in names]
        if fix_manifest:
            write_manifest(names)
            why = []
            if miss:
                why.append("فایلِ جدید: %s" % ", ".join(miss))
            if extra:
                why.append("فایلِ حذفشده: %s" % ", ".join(extra))
            print("✔ ۲) MANIFEST بازنویسی شد (%s)." % "؛ ".join(why))
        else:
            print("❌ ۲) MANIFEST ناهمخوان — فایلهایِ بدونِ MANIFEST یا زامبی: %s"
                  % ", ".join(sorted(set(miss) | set(extra))))
            ok = False
    else:
        print("✔ ۲) MANIFEST همخوان (%d بخش)." % len(names))

    bad = []
    for n in names:
        try:
            py_compile.compile(os.path.join(SEC_DIR, n), doraise=True)
        except Exception as e:
            bad.append("%s: %s" % (n, e))
    if bad:
        print("❌ ۳) سینتکسِ خراب:")
        for b in bad:
            print("      • %s" % b)
        ok = False
    else:
        print("✔ ۳) هر %d بخش py_compile شد." % len(names))

    base_ver = _ver_of_source(
        "\n".join(read_stripped(os.path.join(SEC_DIR, names[0]))))
    loader_src = ""
    try:
        with open(LOADER_PATH, "r", encoding="utf-8") as f:
            loader_src = f.read()
    except OSError:
        pass
    loader_ver = _ver_of_source(loader_src)
    if not base_ver:
        print("❌ ۴) APP_VER در %s پیدا نشد." % names[0])
        ok = False
    elif not loader_ver:
        print("❌ ۴) APP_VER در manga.py (لودر) پیدا نشد.")
        ok = False
    elif base_ver != loader_ver:
        print("❌ ۴) APP_VER ناهمخوان: بخشِ %s=%s ولی لودر=%s — یکی کن."
              % (names[0], base_ver, loader_ver))
        ok = False
    else:
        print("✔ ۴) APP_VER=%s در لودر و %s همخوان." % (loader_ver, names[0]))

    src = combined(names)
    try:
        compile(src, "manga_combined", "exec")
        print("✔ ۵) خروجیِ ترکیبی کامپایل شد (%d خط، %d بایت)."
              % (src.count("\n"), len(src.encode("utf-8"))))
    except SyntaxError as e:
        print("❌ ۵) خروجیِ ترکیبی سینتکسِ خراب دارد: خط %s: %s"
              % (e.lineno, e.msg))
        ok = False

    return ok

def main(argv):
    names = disk_sections()

    if "--list" in argv:
        if not names:
            print("پوشهٔ manga_sections/ خالی است یا وجود ندارد.")
            return 1
        total = 0
        for n in names:
            ln = len(read_stripped(os.path.join(SEC_DIR, n)))
            print("  %-20s %6d خط" % (n, ln))
            total += ln
        print("  %s" % ("─" * 30))
        print("  %-20s %6d خط" % ("مجموع", total))
        return 0

    fix = "--check" not in argv
    ok = run_checks(names, fix_manifest=fix)
    if not ok:
        return 1

    if "--single" in argv:
        src = combined(names)
        with open(OUT_SINGLE, "w", encoding="utf-8", newline="") as f:
            f.write(src)
        py_compile.compile(OUT_SINGLE, doraise=True)
        print("✔ manga_single.py ساخته شد (%d خط، %d بایت) — توزیعِ تک‌فایلی."
              % (src.count("\n"), len(src.encode("utf-8"))))

    print("✔ همهٔ چکها سبز است." if ok else "❌ — بالاتر را ببین.")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
