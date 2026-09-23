# -*- coding: utf-8 -*-

import json
import os
import shutil
import traceback

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
            return path
        with open(path, "rb") as f:
            head = f.read(16)
        fixed = ""
        for magic, e in _IMG_MAGICS:
            if head.startswith(magic):
                fixed = e
                break
        if not fixed and head[:4] == b"RIFF" and head[8:12] == b"WEBP":
            fixed = ".webp"
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
        shutil.copyfile(path, new_path)
        return new_path
    except Exception:
        return path


_ENGINE_FILES = ("manga.py", "manga_app.py", "bridge.py", "extract_ui.py",
                 "app_server.py")


def _files_dir():
    return os.environ.get("MANGA_FILES_DIR") or os.getcwd()


def _syntax_check(path):
    try:
        with open(path, "rb") as f:
            src = f.read()
        try:
            compile(src, path, "exec")
        except SyntaxError as e:
            return "خطای سینتکس خط %s: %s" % (e.lineno, e.msg)
        except Exception as e:
            return "%s: %s" % (type(e).__name__, e)
    except Exception as e:
        return "خواندن ناموفق: %s" % e
    return None


def health():

    files_dir = _files_dir()
    upd = os.path.join(files_dir, "updates")
    lines = []
    ok = True

    lines.append("📋 وضعیت فایل‌های موتور (updates):")
    for n in _ENGINE_FILES:
        p = os.path.join(upd, n)
        if not os.path.isfile(p):
            lines.append("  • %s — نیست (از داخل APK استفاده می‌شود)" % n)
            continue
        size = os.path.getsize(p)
        if size < 1000:
            ok = False
            lines.append("  • %s — ❌ خراب (فقط %d بایت)" % (n, size))
            continue
        err = _syntax_check(p)
        if err:
            ok = False
            lines.append("  • %s — ❌ %s" % (n, err))
        else:
            lines.append("  • %s — ✔ سالم (%.1f KB)" % (n, size / 1024.0))

    culprit = None
    tb_full = ""
    try:
        import manga
        lines.append("📥 import manga.py — ✔ موفق")
    except Exception:
        ok = False
        tb_full = traceback.format_exc()
        culprit = _find_culprit(tb_full)
        lines.append("📥 import manga.py — ❌ خطا:")
        lines.append("```")
        lines.append(tb_full.strip()[-2500:])
        lines.append("```")
        lines.append("👉 فایل مقصر: %s" % (culprit or "نامشخص — traceback بالا را ببین"))
    try:
        import manga_app
        lines.append("📥 import manga_app.py — ✔ موفق")
    except Exception:
        ok = False
        tb_full = traceback.format_exc()
        culprit2 = _find_culprit(tb_full) or culprit
        lines.append("📥 import manga_app.py — ❌ خطا:")
        lines.append("```")
        lines.append(tb_full.strip()[-2500:])
        lines.append("```")
        lines.append("👉 فایل مقصر: %s" % (culprit2 or "نامشخص"))

    if ok:
        lines.insert(0, "✅ موتور سالم است.")
        lines.append("💡 اگر باز هم خطا گرفتی، متن کامل خطای زمان اجرا در همین "
                     "کادر لاگ، موقع شروع ترجمه نمایش داده می‌شود.")
    else:
        lines.insert(0, "❌ موتور خرابه — دقیقاً این‌جا:")
        lines.append("🔧 راه‌حل سریع: تنظیمات اپ → پاک‌کردن داده اپ (Clear Data) "
                     "→ باز کردن دوباره؛ یا نسخه جدید اپ را نصب کن.")
    return json.dumps({"ok": ok, "report": "\n".join(lines)}, ensure_ascii=False)


def _find_culprit(tb_text):
    import re
    for n in _ENGINE_FILES:
        if re.search(r'File "[^"]*%s"' % re.escape(n), tb_text):
            return n
    return None

def manifest():
    import bridge
    return bridge.manifest()

def _ollama_base(p):
    b = str(p.get("api_base") or "").strip().rstrip("/")
    if b and not b.endswith("/v1"):
        b += "/v1"
    return b or "http://localhost:11434/v1"


def _ollama_check(p):

    import requests

    base = _ollama_base(p)
    headers = {}
    key0 = str(p.get("keys") or "").split(",")[0].strip()
    if key0:
        headers["Authorization"] = "Bearer " + key0
    try:
        r = requests.get(base + "/models", timeout=(4, 10), headers=headers)
        r.raise_for_status()
        data = r.json().get("data") or []
        models = [str(m.get("id") or "").strip() for m in data if m.get("id")]
    except Exception as e:
        host = base.replace("/v1", "")
        return (
            "اتصال به Ollama برقرار نشد (%s)\n"
            "│  خطا: %s\n"
            "├─ آدرس استفاده‌شده: %s (پیش‌فرض لوکال)\n"
            "├─ اگه Ollama روی خود گوشی (Termux) است: مطمئن شو «ollama serve» در حال اجراست\n"
            "└─ نکته: از v1.22 فیلد آدرس از تنظیمات حذف شده؛ Ollama فقط روی همین دستگاه پشتیبانی می‌شود."
            % (host, type(e).__name__, host)
        ), base

    if not str(p.get("model") or "").strip() and models:
        p["model"] = models[0]
    return None, base + ("  |  مدل‌ها: " + "، ".join(models[:8]) if models else "")


def start_job(params_json, files_dir):
    p = json.loads(params_json)

    src0 = str(p.get("src") or "")
    src1 = _fix_input_ext(src0)
    if src1 != src0:
        p["src"] = src1

    prov = str(p.get("provider") or "gemini").strip().lower()
    if prov == "ollama":
        if not str(p.get("keys") or "").strip():
            p["keys"] = "ollama"
        if not p.get("timeout"):
            p["timeout"] = 180
        err, info = _ollama_check(p)
        if err:
            return json.dumps(
                {"ok": False, "error": "❌ " + err + "\n\n🔎 " + info},
                ensure_ascii=False)
        try:
            import manga
            manga.PROVIDER_PRESETS["ollama"]["base_url"] = _ollama_base(p)
        except Exception:
            pass

    return _delegate_start(json.dumps(p, ensure_ascii=False), files_dir)


def _delegate_start(params_json, files_dir):
    import bridge
    return bridge.start_job(params_json, files_dir)


def poll():
    import bridge
    return bridge.poll()


def cancel():
    import bridge
    return bridge.cancel()


def status():
    try:
        import launcher
        return launcher.status()
    except Exception:
        return "status error"


def check_engine_files():
    return health()
