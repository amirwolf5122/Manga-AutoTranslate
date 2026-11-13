# -*- coding: utf-8 -*-
import json
import os
import re

_IMG_EXTS = (".jpg", ".jpeg", ".png", ".webp")
_KNOWN_OUT_EXTS = (".pdf", ".zip", ".html", ".psd",
                   ".webp", ".png", ".jpg", ".jpeg")
_ORIG_DIRS = ("src", "normalized", "stitched")


def cache_dir_of(out_file_path: str) -> str:
    p = str(out_file_path or "")
    root, ext = os.path.splitext(p)
    if ext.lower() in _KNOWN_OUT_EXTS:
        return root + ".cache"
    return p + ".cache"


def _natkey(s):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]


def last_out_dir(cache):
    try:
        with open(os.path.join(cache, "last_out.json"),
                  encoding="utf-8") as fh:
            name = str((json.load(fh) or {}).get("dir") or "").strip()
        if (name and name not in (".", "..")
                and "/" not in name and os.sep not in name):
            p = os.path.join(cache, name)
            if os.path.isdir(p):
                return p
    except Exception:
        pass
    return ""


def latest_out_dir(cache):
    best, best_mt = "", -1.0
    try:
        for name in os.listdir(cache):
            if name != "out" and not name.startswith("out_"):
                continue
            p = os.path.join(cache, name)
            if not os.path.isdir(p):
                continue
            try:
                if not any(f.lower().endswith(_IMG_EXTS)
                           for f in os.listdir(p)):
                    continue
            except Exception:
                continue
            mt = os.path.getmtime(p)
            if mt > best_mt:
                best, best_mt = p, mt
    except Exception:
        return ""
    return best


def collect(out_file_path: str, job_out: str):
    imgs, dbg = [], []
    cache = cache_dir_of(out_file_path)
    last = last_out_dir(cache) or latest_out_dir(cache)
    for root, _d, files in os.walk(cache):
        dname = os.path.basename(os.path.normpath(root)).lower()
        if any("/" + o + "/" in root.lower().replace(os.sep, "/") + "/"
               for o in _ORIG_DIRS):
            continue
        is_dbg = dname.startswith("debug")
        is_out = dname == "out" or dname.startswith("out_")
        if not is_out and not is_dbg:
            continue
        take_imgs = (not last) and is_out and not is_dbg
        if last and os.path.normpath(root) == os.path.normpath(last):
            take_imgs = True
        for f in sorted(files):
            if not f.lower().endswith(_IMG_EXTS):
                continue
            lp = os.path.join(root, f)
            if is_dbg or "debug" in f.lower():
                if "_base." in f.lower():
                    continue
                dbg.append(lp)
            elif take_imgs:
                imgs.append(lp)
    if not imgs:
        for root, dirs_, files in os.walk(job_out):
            rel = root.lower().replace(os.sep, "/")
            segs = [s for s in rel.split("/") if s]
            dname = os.path.basename(os.path.normpath(root)).lower()
            in_cache = any(s.endswith(".cache") for s in segs)
            if in_cache and not (dname == "out" or dname.startswith("out_")
                                 or dname.startswith("debug")):
                dirs_[:] = []
                continue
            if dname == "input_batch":
                dirs_[:] = []
                continue
            if any("/" + o + "/" in rel + "/" for o in _ORIG_DIRS):
                dirs_[:] = []
                continue
            dir_dbg = "debug" in dname
            for f in sorted(files):
                lp = os.path.join(root, f)
                if f.lower().endswith(_IMG_EXTS):
                    if "_base." in f.lower():
                        continue
                    (dbg if (dir_dbg or "debug" in f.lower()) else imgs).append(lp)
    imgs.sort(key=_natkey)
    dbg.sort(key=_natkey)
    return imgs, dbg
