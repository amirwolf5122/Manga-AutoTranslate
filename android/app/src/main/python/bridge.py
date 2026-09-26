# -*- coding: utf-8 -*-

import contextlib
import json
import logging
import os
import re
import threading
import time
import traceback

try:
    import manga
except Exception:
    manga = None
from extract_ui import extract

import manga_app


def _manga():
    global manga
    if manga is None:
        import importlib
        manga = importlib.import_module("manga")
    return manga

STATE = {"job": None, "lock": threading.Lock()}
_MF_CACHE = {"mf": None}


def _pil_webp_ok():
    try:
        from PIL import features
        return bool(features.check("webp"))
    except Exception:
        return False


def _webp_to_png_android(src):
    try:
        from android.graphics import BitmapFactory, Bitmap
        from java.io import FileOutputStream
        bm = BitmapFactory.decodeFile(src)
        if bm is None:
            return None
        dst = os.path.splitext(src)[0] + ".png"
        out = FileOutputStream(dst)
        ok = bm.compress(Bitmap.CompressFormat.PNG, 100, out)
        out.flush()
        out.close()
        bm.recycle()
        return dst if ok else None
    except Exception:
        return None


def _is_webp_file(path):
    try:
        with open(path, "rb") as f:
            head = f.read(12)
        return head[:4] == b"RIFF" and head[8:12] == b"WEBP"
    except Exception:
        return False


def install_webp_guards():
    if _pil_webp_ok():
        return
    try:
        from PIL import Image

        if not getattr(Image.Image.save, "_manga_webp_guard", False):
            _orig_save = Image.Image.save

            def _safe_save(self, fp, format=None, **params):
                try:
                    return _orig_save(self, fp, format=format, **params)
                except KeyError as e:
                    if str(e).strip("'\"").upper() != "WEBP":
                        raise
                    path = str(fp)
                    base, ext = os.path.splitext(path)
                    new_path = (base + ".jpg") if ext.lower() == ".webp" else path
                    print("[!] کدک WEBP در Pillow نیست → ذخیره به‌صورت JPG: %s" % new_path)
                    try:
                        q = int(params.get("quality", 90))
                    except Exception:
                        q = 90
                    q = max(40, min(q, 100))
                    return _orig_save(self, new_path, format="JPEG", quality=q, optimize=True)

            _safe_save._manga_webp_guard = True
            Image.Image.save = _safe_save

        if not getattr(Image.open, "_manga_webp_guard", False):
            _orig_open = Image.open

            def _safe_open(fp, *a, **kw):
                try:
                    return _orig_open(fp, *a, **kw)
                except Exception:
                    try:
                        path = str(getattr(fp, "name", fp))
                    except Exception:
                        path = ""
                    if path and os.path.isfile(path) and _is_webp_file(path):
                        png = _webp_to_png_android(path)
                        if png:
                            print("[!] ورودی WEBP با کدک اندروید به PNG تبدیل شد: %s" % png)
                            return _orig_open(png, *a, **kw)
                    raise

            _safe_open._manga_webp_guard = True
            Image.open = _safe_open
    except Exception:
        pass


def _resolve_img_format(p):
    fmt = str(p.get("img_format") or p.get("format") or "").strip().lstrip(".").lower()
    if fmt == "jpeg":
        fmt = "jpg"
    if fmt not in ("webp", "jpg", "png"):
        fmt = "webp" if _pil_webp_ok() else "jpg"
    elif fmt == "webp" and not _pil_webp_ok():
        fmt = "jpg"
    return fmt


install_webp_guards()

_IMG_MAGICS = (
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"\xff\xd8\xff", ".jpg"),
    (b"GIF87a", ".gif"),
    (b"GIF89a", ".gif"),
    (b"BM", ".bmp"),
    (b"PK\x03\x04", ".zip"),
    (b"PK\x05\x06", ".zip"),
    (b"%PDF", ".pdf"),
)
_ACCEPTED_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".zip", ".pdf"}


def _fix_input_ext(path):

    try:
        if not path or "://" in path or not os.path.isfile(path):
            return path
        ext = os.path.splitext(path)[1].lower()
        if ext in _ACCEPTED_EXTS:
            if ext != ".webp" or _pil_webp_ok():
                return path
            png = _webp_to_png_android(path)
            return png if png else path
        with open(path, "rb") as f:
            head = f.read(16)
        fixed = ""
        for magic, e in _IMG_MAGICS:
            if head.startswith(magic):
                fixed = e
                break
        if not fixed and head[:4] == b"RIFF" and head[8:12] == b"WEBP":
            fixed = ".webp"
            if not _pil_webp_ok():
                png = _webp_to_png_android(path)
                if png:
                    return png
        if not fixed:
            try:
                from PIL import Image
                with Image.open(path) as im:
                    fmt = (im.format or "").lower()
                if fmt == "jpeg":
                    fmt = "jpg"
                if fmt in ("png", "jpg", "webp", "bmp", "gif"):
                    fixed = "." + fmt
            except Exception:
                return path
        if not fixed:
            return path
        base = os.path.basename(path).replace(":", "_")
        new_path = os.path.join(os.path.dirname(path), base + fixed)
        if os.path.abspath(new_path) == os.path.abspath(path):
            return path
        import shutil as _sh
        _sh.copyfile(path, new_path)
        return new_path
    except Exception:
        return path


def _bundles():
    try:
        b = list(manga_app.FONT_BUNDLES)
        if b:
            return b
    except Exception:
        pass
    return []


def _font_dir():
    try:
        return manga_app.FONT_DIR
    except Exception:
        return os.path.join(os.getcwd(), "fonts")


def _tone_ready(fname):
    p = os.path.join(_font_dir(), fname)
    try:
        return os.path.isfile(p) and os.path.getsize(p) > 20_000
    except Exception:
        return False


def _slot_fields(mf):

    slots = [b[0] for b in _bundles()]
    if not slots:
        return {}
    mapping = {}
    for sec in mf.get("sections", []):
        for f in sec.get("fields", []):
            fid = f.get("id") or ""
            for slot in slots:
                if fid.endswith("_" + slot):
                    m = mapping.setdefault(slot, {})
                    if f.get("type") == "file":
                        m["file"] = fid
                    elif f.get("type") == "bool":
                        m["en"] = fid
    return mapping


def _defaults(mf):
    try:
        dflt_instr = _manga().DEFAULT_SYSTEM_INSTRUCTION_STYLE.strip()
    except Exception:
        dflt_instr = ""
    for sec in mf.get("sections", []):
        for f in sec.get("fields", []):
            if not isinstance(f, dict):
                continue
            if f.get("id") == "instruction_text":
                cur = f.get("default")
                cur = cur.get("default") if isinstance(cur, dict) else cur
                if not (isinstance(cur, str) and cur.strip()):
                    f["default"] = dflt_instr or "خالی = متن پیش‌فرض داخل کد"
            elif f.get("id") == "readord":
                cur = f.get("default")
                if isinstance(cur, dict):
                    cur.setdefault("default", "rtl")
                elif cur not in ("rtl", "ltr"):
                    f["default"] = "rtl"


def _bundled_source(name):

    import importlib
    mod = importlib.import_module(name)
    loader = getattr(mod, "__loader__", None)
    if loader is None:
        raise RuntimeError("no loader for " + name)
    return loader.get_source(name)


def manifest():

    files_dir = os.environ.get("MANGA_FILES_DIR") or os.getcwd()
    upd = os.path.join(files_dir, "updates", "manga_app.py")
    mf = None
    err = None
    for get_src in (
        lambda: (open(upd, encoding="utf-8").read(), "file")
        if os.path.isfile(upd) else (_ for _ in ()).throw(IOError(upd)),
        lambda: (_bundled_source("manga_app"), "loader"),
    ):
        try:
            src, _how = get_src()
            mf = extract(src, is_source=True)
            break
        except Exception as e:
            err = e
    if mf is None:
        try:
            mf = extract(manga_app.__file__)
        except Exception as e2:
            return json.dumps({"error": str(err or e2)}, ensure_ascii=False)
    try:
        provs = [str(x) for x in manga_app.PROVIDERS]
    except Exception:
        provs = ["gemini", "openai", "chatgpt", "deepseek", "groq"]
    for sec in mf.get("sections", []):
        for f in sec.get("fields", []):
            if f.get("choices_from") == "PROVIDERS" or f.get("id") == "provider":
                f["choices"] = [[p, p] for p in provs]
                f.pop("choices_from", None)
            if f.get("id") in ("manga_api_base", "api_base"):
                f["visible_if"] = {"field": "provider", "equals": "custom"}
                f["label"] = "دامنهٔ API سفارشی (فقط برای custom — مثال: https://api.example.com/v1)"
    try:
        _defaults(mf)
    except Exception:
        traceback.print_exc()
    _MF_CACHE["mf"] = mf
    return json.dumps(mf, ensure_ascii=False)


def _cfg(key, dflt=None):
    try:
        return manga_app.load_config().get(key, dflt)
    except Exception:
        return dflt


def _resolve_main_font(job):
    custom = job["params"].get("font_upload_file") or job["params"].get("font_file")
    if custom and os.path.isfile(custom):
        _log(job, "🔤 فونت اصلی (آپلودی): %s" % os.path.basename(custom))
        return custom
    fp = ""
    try:
        fp = manga_app.find_font() or ""
    except Exception:
        pass
    if fp:
        return fp
    _log(job, "⬇ فونت روی دستگاه نیست — دانلود خودکار…")
    try:
        manga_app.download_fonts(log=lambda m: _log(job, str(m)))
    except Exception as e:
        _log(job, "⚠ دانلود فونت ناموفق: %s" % e)
    try:
        fp = manga_app.find_font() or ""
    except Exception:
        fp = ""
    return fp


def _resolve_tones(job, mf):

    slot_map = _slot_fields(mf)
    p = job["params"]
    font_by_style, active = {}, []
    for slot, fname, _desc, _u in _bundles():
        ids = slot_map.get(slot, {})
        en_fid = ids.get("en")
        on = True if en_fid is None else bool(p.get(en_fid, True))
        file_fid = ids.get("file")
        custom = p.get(file_fid + "_file") if file_fid else None
        path = custom if (custom and os.path.isfile(custom)) \
            else os.path.join(_font_dir(), fname)
        lbl = slot
        if not on:
            _log(job, "🔇 لحن خاموش: %s" % lbl)
            continue
        if path and os.path.isfile(path) and os.path.getsize(path) > 20_000:
            font_by_style[slot] = path
            active.append(slot)
        else:
            _log(job, "⚠ فونت لحن «%s» پیدا نشد — با فونت اصلی رندر می‌شود" % lbl)
    return font_by_style, active


def _out_stem_from_src(src: str) -> str:
    s = str(src or "").strip()
    if not s:
        return ""
    try:
        if s.lower().startswith(("http://", "https://")):
            from urllib.parse import urlparse, unquote
            name = os.path.basename(unquote(urlparse(s).path))
        else:
            name = os.path.basename(s.replace("\\", "/"))
        stem = os.path.splitext(name)[0].strip()
    except Exception:
        stem = ""
    stem = re.sub(r'[\\/:*?"<>|]+', "_", stem).strip(" ._")
    return stem[:80]


def start_job(params_json, files_dir):
    with STATE["lock"]:
        if STATE["job"] and not STATE["job"].get("done"):
            return json.dumps({"error": "یک کار در حال اجراست"}, ensure_ascii=False)
        p = json.loads(params_json)
        work = os.path.join(files_dir, "work")
        os.makedirs(work, exist_ok=True)
        out = os.path.join(work, "out")
        fmt = str(p.get("fmt", "PDF")).upper()
        ext = "pdf" if fmt == "PDF" else fmt.lower()
        _stem = _out_stem_from_src(p.get("src") or p.get("url") or "")
        out_file = os.path.join(out, (_stem or "manga") + "." + ext)
        job = {
            "done": False, "log": "⏳ آماده‌سازی…", "error": None,
            "out_file": None, "images": [], "debug_images": [],
            "params": p, "out": out, "out_file_path": out_file,
        }
        STATE["job"] = job
    threading.Thread(target=_run, args=(job,), daemon=True).start()
    return json.dumps({"ok": True}, ensure_ascii=False)


def _log(job, msg):
    with STATE["lock"]:
        txt = str(job.get("log") or "")
        job["log"] = (txt + "\n" + str(msg))[-12000:]


_ANSI = re.compile(r"\x1b\[[0-9;]*m")


class _TeeStream:


    def __init__(self, job):
        self._job = job
        self._lock = threading.Lock()
        self._parts = []
        self._len = 0
        self._tail = []

    def write(self, s):
        if not s:
            return 0
        with self._lock:
            self._tail.append(s)
            if len(self._tail) > 800:
                del self._tail[:-400]
            self._parts.append(s)
            self._len += len(s)
            big = self._len >= 256
        if big or "\n" in s or "\r" in s:
            self.flush()
        return len(s)

    def flush(self):
        with self._lock:
            chunk = "".join(self._parts)
            self._parts = []
            self._len = 0
        if not chunk:
            return
        pieces = chunk.replace("\r", "\n").split("\n")
        for ln in pieces[:-1]:
            self._emit(ln)
        if pieces[-1]:
            with self._lock:
                self._parts.append(pieces[-1])
                self._len = len(pieces[-1])

    def _emit(self, ln):
        ln = _ANSI.sub("", ln).rstrip()
        if not ln:
            return
        if len(ln) > 300:
            ln = "…" + ln[-300:]
        with STATE["lock"]:
            txt = str(self._job.get("log") or "")
            lines = txt.split("\n") if txt else []
            prev = lines[-1] if lines else ""
            if "%|" in ln and "%|" in prev:
                lines[-1] = ln
            else:
                lines.append(ln)
            self._job["log"] = ("\n".join(lines))[-12000:]

    def getvalue(self):
        self.flush()
        with self._lock:
            return "".join(self._tail)


def _heartbeat(job):

    t0 = time.time()
    last = -1
    while True:
        time.sleep(30)
        with STATE["lock"]:
            if job.get("done"):
                return
            cur = len(str(job.get("log") or ""))
        if cur == last:
            _log(job, "⏳ موتور در حال کار است… %d ثانیه از شروع — صفحه‌های سنگین/دانلود مدل طول می‌کشد" % int(time.time() - t0))
        last = cur


def _attach_log_handlers(tee):

    class _H(logging.Handler):
        def emit(self, record):
            try:
                tee.write(self.format(record) + "\n")
            except Exception:
                pass

    h = _H(level=logging.INFO)
    h.setFormatter(logging.Formatter("[%(name)s] %(message)s"))
    targets = [logging.getLogger()]
    rapid = logging.getLogger("RapidOCR")
    if rapid not in targets:
        targets.append(rapid)
    attached = []
    for lg in targets:
        try:

            if lg.getEffectiveLevel() > logging.INFO:
                lg.setLevel(logging.INFO)
            lg.addHandler(h)
            attached.append(lg)
        except Exception:
            pass
    return (h, attached)


def _detach_log_handlers(attached):
    try:
        h, lgs = attached
        for lg in lgs:
            lg.removeHandler(h)
    except Exception:
        pass


def _run(job):
    p = job["params"]
    try:
        os.makedirs(job["out"], exist_ok=True)
        for old in os.listdir(job["out"]):
            try:
                os.remove(os.path.join(job["out"], old))
            except Exception:
                pass
        langs = [x for x in str(p.get("ocr_lang") or "en").split() if x.strip()]
        _src0 = str(p.get("src") or "")
        _src1 = _fix_input_ext(_src0)
        if _src1 != _src0:
            p["src"] = _src1
            _log(job, "🧩 پسوند ورودی اصلاح شد → %s" % os.path.basename(_src1))
        keys = [k.strip() for k in str(p.get("keys") or "").split(",") if k.strip()]
        if not keys and not (bool(p.get("fake")) or bool(p.get("clean_only"))):
            _log(job, "❌ حداقل یک کلید API لازم است — کلید بده یا "
                      "«حالت تست» / «فقط پاکسازی» را در تنظیمات پیشرفته فعال کن.")
            with STATE["lock"]:
                job["done"] = True
                job["error"] = True
            return
        glossary_path = None
        if p.get("glossary"):
            glossary_path = os.path.join(job["out"], "glossary.txt")
            with open(glossary_path, "w", encoding="utf-8") as f:
                f.write(str(p["glossary"]))

        fp = _resolve_main_font(job)
        if not fp:
            _log(job, "❌ فونت اصلی پیدا نشد — اینترنت را چک کن یا فونت .ttf آپلود کن.")
            with STATE["lock"]:
                job["done"] = True
                job["error"] = True
            return

        def _f(key, dflt):
            try:
                return float(p.get(key) or dflt)
            except Exception:
                return dflt

        def _i(key, dflt):
            try:
                return int(float(p.get(key) or dflt))
            except Exception:
                return dflt

        tee = _TeeStream(job)
        hb = threading.Thread(target=_heartbeat, args=(job,), daemon=True)
        hb.start()
        handlers = _attach_log_handlers(tee)
        try:
            with contextlib.redirect_stdout(tee), contextlib.redirect_stderr(tee):
                _log(job, "🚀 در حال بارگذاری موتور و مدل‌ها…"
                          " (بار اول دانلود مدل چند دقیقه طول می‌کشد)")
                mf = _MF_CACHE["mf"]
                if mf is None:
                    try:
                        mf = json.loads(manifest())
                    except Exception:
                        mf = {}
                font_by_style, active = _resolve_tones(job, mf)
                tr = _manga().MangaTranslator(
                    api_key=keys or ["placeholder"],
                    provider=str(p.get("provider") or "gemini"),
                    model_name=(str(p.get("model")) or None) if p.get("model") else None,
                    api_base=(str(p.get("api_base") or "").strip()
                              or _cfg("api_base") or None) or None,
                    ocr_langs=langs,
                    font_path=fp,
                    reading_order=str(p.get("readord") or "rtl"),
                    gpu=False if p.get("force_cpu") else None,
                    two_pass_ocr=bool(p.get("two_pass", True)),
                    debug=bool(p.get("debug")),
                    glossary_path=glossary_path,
                    story_brief=bool(p.get("story_brief", True)),
                    fake_translate=bool(p.get("fake")),
                    clean_only=bool(p.get("clean_only")),
                    max_workers=_i("workers", 2),
                    bubbles_per_request=_i("bubbles", 6),
                    api_timeout=_f("timeout", 40.0),
                    max_retries=_i("maxre", 8),
                    request_delay=_f("reqdelay", 0.0),
                    translation_temperature=_f("temp", 0.85),
                    img_quality=_i("quality", 92),
                    img_format=_resolve_img_format(p),
                    style_fonts=bool(active),
                    active_tones=active or None,
                    instruction_text=(str(p["instruction"]).strip() or None)
                    if p.get("instruction") else None,
                )

                if (getattr(manga, "_on_android", lambda: False)()
                        and getattr(tr, "det", None) is not None):
                    tr.stitch_max_height = 4000
                tr.batch_workers = _i("batchw", 3)

                if bool(p.get("use_lama")):
                    tr.use_lama = True
                    _log(job, "🩹 پاک‌سازی LaMa-Manga فعال شد (تنظیمات) — بار اول "
                              "مدل ~۱۹۸MB دانلود می‌شود؛ کندتر ولی تمیزتر از OpenCV."
                              " اگر رم گوشی کم باشد خودکار به OpenCV برمی‌گردد.")
                if font_by_style:
                    tr.font_by_style = font_by_style
                    tr.style_fonts = True
                    _log(job, "🎨 لحن‌های فعال: %s" % "، ".join(active))
                _log(job, "🎬 موتور شروع شد — استخراج صفحات و فازها از این‌جا در لاگ می‌آید")
                tr.run(str(p.get("src")), job["out_file_path"], resume=False)
        finally:
            _detach_log_handlers(handlers)

        _ORIG_DIRS = ("src", "normalized", "stitched")
        imgs, dbg = [], []
        cache = job["out_file_path"] + ".cache"
        for root, _d, files in os.walk(cache):
            dname = os.path.basename(os.path.normpath(root)).lower()
            if any("/" + o + "/" in root.lower().replace(os.sep, "/") + "/"
                   for o in _ORIG_DIRS):
                continue
            is_dbg = dname.startswith("debug")
            is_out = dname == "out" or dname.startswith("out_")
            if not is_out and not is_dbg:
                continue
            for f in sorted(files):
                if not f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                    continue
                lp = os.path.join(root, f)
                if is_dbg or "debug" in f.lower():
                    dbg.append(lp)
                else:
                    imgs.append(lp)
        import re as _re

        def _natkey(s):
            return [int(t) if t.isdigit() else t for t in _re.split(r"(\d+)", s)]

        imgs.sort(key=_natkey)
        dbg.sort(key=_natkey)
        if not imgs:

            for root, dirs_, files in os.walk(job["out"]):
                rel = root.lower().replace(os.sep, "/")
                segs = [s for s in rel.split("/") if s]
                dname = os.path.basename(os.path.normpath(root)).lower()
                in_cache = any(s.endswith(".cache") for s in segs)
                if in_cache and not (
                        dname == "out" or dname.startswith("out_")
                        or dname.startswith("debug")):
                    dirs_[:] = []
                    continue
                if any("/" + o + "/" in rel + "/" for o in _ORIG_DIRS):
                    dirs_[:] = []
                    continue
                for f in sorted(files):
                    lp = os.path.join(root, f)
                    if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                        (dbg if "debug" in f.lower() else imgs).append(lp)
        dl = job["out_file_path"] if os.path.isfile(job["out_file_path"]) else None
        with STATE["lock"]:
            job["images"] = imgs
            job["debug_images"] = dbg
            job["out_file"] = dl
            job["done"] = True
        _log(job, "✅ تمام شد — %d صفحه، خروجی: %s" % (len(imgs), dl or "-"))
        if bool(p.get("debug")) and not dbg:
            _log(job, "🔍 دیباگ روشن بود ولی تصویر دیباگی ساخته نشد — "
                      "تصویر دیباگ فقط برای صفحه‌هایی که متن/حباب دارند تولید می‌شود.")
    except BaseException:
        try:
            _txt = tee.getvalue()
            if _txt.strip():
                _log(job, "…" + _txt[-4000:])
        except Exception:
            pass
        _log(job, "❌ خطا:\n" + traceback.format_exc()[-2500:])
        with STATE["lock"]:
            job["done"] = True
            job["error"] = True


def poll():
    with STATE["lock"]:
        job = STATE["job"]
        if not job:
            return json.dumps({"idle": True}, ensure_ascii=False)
        return json.dumps({
            "idle": False,
            "done": bool(job.get("done")),
            "error": bool(job.get("error")),
            "log": job.get("log", ""),
            "images": job.get("images", []),
            "debug_images": job.get("debug_images", []),
            "out_file": job.get("out_file"),
            "debug_on": bool((job.get("params") or {}).get("debug")),
        }, ensure_ascii=False)


def cancel():
    with STATE["lock"]:
        job = STATE["job"]
    if job and not job.get("done"):
        _log(job, "⏹ درخواست توقف ثبت شد (پایان مرحله فعلی)")
    return json.dumps({"ok": True}, ensure_ascii=False)
