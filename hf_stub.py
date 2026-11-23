import io
import os
import sys
import tarfile
import urllib.request

try:
    import spaces  # noqa: F401
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
RAW_VER = "https://raw.githubusercontent.com/amirwolf5122/Manga-AutoTranslate/main/VERSION"
TARBALL = "https://codeload.github.com/amirwolf5122/Manga-AutoTranslate/tar.gz/refs/heads/main"
STAMP = os.path.join(HERE, ".code_ver")


def _local_ver():
    try:
        with open(os.path.join(HERE, "VERSION"), encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def _stamp_ver():
    try:
        with open(STAMP, encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def _remote_ver():
    try:
        with urllib.request.urlopen(RAW_VER, timeout=30) as r:
            return r.read().decode("utf-8", "replace").strip()
    except Exception:
        return ""


def _have_code():
    return (os.path.exists(os.path.join(HERE, "manga.py"))
            and os.path.exists(os.path.join(HERE, "manga_app.py"))
            and os.path.isdir(os.path.join(HERE, "manga_sections")))


def _refresh():
    data = urllib.request.urlopen(TARBALL, timeout=300).read()
    tf = tarfile.open(fileobj=io.BytesIO(data), mode="r:gz")
    for m in tf.getmembers():
        if not m.isfile():
            continue
        parts = m.name.split("/", 1)
        if len(parts) < 2:
            continue
        rel = parts[1]
        keep = (rel in ("manga.py", "manga_app.py", "VERSION")
                or rel.startswith("manga_sections/"))
        if not keep:
            continue
        dst = os.path.join(HERE, rel)
        d = os.path.dirname(dst)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(dst, "wb") as f:
            f.write(tf.extractfile(m).read())
    with open(STAMP, "w", encoding="utf-8") as f:
        f.write(_local_ver())


def _ensure_code():
    if _have_code() and _stamp_ver() and _stamp_ver() == _local_ver():
        rv = _remote_ver()
        if not rv or rv == _local_ver():
            return
    try:
        _refresh()
    except Exception as e:
        print("[hf-stub] code refresh failed:", e)


_ensure_code()

if not _have_code():
    print("[hf-stub] manga.py not available")
    sys.exit(1)

import runpy

sys.argv = [os.path.abspath(__file__)]
runpy.run_path(os.path.join(HERE, "manga_app.py"), run_name="__main__")

import time

while True:
    time.sleep(60)

