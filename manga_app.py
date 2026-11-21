import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.request
import urllib.parse
from datetime import datetime
from typing import Optional

APP_NAME = "مانگا مترجم"
APP_VER = "1.14.376"
HERE = os.path.dirname(os.path.abspath(__file__))
MANGA_PY = os.path.join(HERE, "manga.py")
WORK_DIR = os.path.join(HERE, "workspace")
UPLOAD_DIR = os.path.join(WORK_DIR, "input")
OUT_DIR = os.path.join(WORK_DIR, "output")
FONT_DIR = os.path.join(HERE, "fonts")
CFG_PATH = os.path.join(WORK_DIR, "config.json")
HIST_PATH = os.path.join(WORK_DIR, "history.jsonl")
MODELS_DIR = os.path.expanduser("~/.cache/manga_translator_models")

KEY_ENV_ORDER = ("GEMINI_API_KEYS", "GEMINI_API_KEY", "GOOGLE_API_KEY",
                 "OPENAI_API_KEY", "DEEPSEEK_API_KEY", "GROQ_API_KEY",
                 "XAI_API_KEY", "TOGETHER_API_KEY", "OPENROUTER_API_KEY", "API_KEY")
PROVIDER_ALIASES = {"chatgpt": "openai", "grok": "xai"}
PROVIDERS = ["gemini", "custom"]

def _load_ui_texts():
    try:
        import importlib.util
        _p = os.path.join(HERE, "manga_sections", "05_ui_texts.py")
        _sp = importlib.util.spec_from_file_location("manga_ui_texts", _p)
        _m = importlib.util.module_from_spec(_sp)
        _sp.loader.exec_module(_m)
        _t = getattr(_m, "UI_TEXTS", None)
        return _t if isinstance(_t, dict) else {}
    except Exception as _e:
        try:
            print("[UI_TEXTS] خطا در خواندنِ manga_sections/05_ui_texts.py — "
                  "متن‌های پیش‌فرض استفاده میشوند:", _e)
        except Exception:
            pass
        return {}

UI_TEXTS = _load_ui_texts()

def TX(k, d=None):
    try:
        v = UI_TEXTS.get(k, d)
        return d if v is None else v
    except Exception:
        return d

def _ui_t_script():
    try:
        _j = json.dumps(UI_TEXTS, ensure_ascii=False, separators=(",", ":"))
        return "<script>window.UI_T=" + _j + ";</script>"
    except Exception:
        return ""

def _ui_t_json_file():
    try:
        return json.dumps(UI_TEXTS, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        return ""


_UT_JS_HELPER = (
    "<script>function UT(k,d){try{var t=window.UI_T;return (t&&t[k]!=null)?t[k]:d}"
    "}catch(e){return d}}"
    "(function(){function p(){try{"
    "if(!window.UI_T)return;"
    "var q=function(s){return document.querySelector(s)},e;"
    "e=q('.bar .t');if(e)e.textContent=UT('rdr.live_title',e.textContent);"
    "e=q('#hF');if(e)e.textContent=UT('rdr.wait_first',e.textContent);"
    "e=q('#hD');if(e)e.textContent=UT('rdr.wait_debug',e.textContent);"
    "e=q('#mtoggle');if(e){e.title=UT('rdr.t_mode',e.title);if(e.textContent)e.textContent=UT('rdr.debug',e.textContent);}"
    "e=q('#zo');if(e)e.title=UT('rdr.t_small',e.title);"
    "e=q('#zi');if(e)e.title=UT('rdr.t_big',e.title);"
    "e=q('#zf');if(e){e.title=UT('rdr.t_fit',e.title);if(e.textContent=='\u067e\u0647\u0646\u0627')e.textContent=UT('rdr.zfit',e.textContent);}"
    "e=q('.off-t1');if(e)e.textContent=UT('mcat.off_t1',e.textContent);"
    "e=q('.off-t2');if(e)e.textContent=UT('mcat.off_t2',e.textContent);"
    "e=q('.off-t3');if(e)e.textContent=UT('mcat.off_t3',e.textContent);"
    "e=q('#cmpT');if(e)e.textContent=UT('rdr.page','\u0635\u0641\u062d\u0647\u0654 ')+'\u06f1';"
    "e=q('#sbub');if(e)e.textContent=UT('rdr.page','\u0635\u0641\u062d\u0647\u0654 ')+'\u06f1';"
    "e=q('#fab');if(e){if(e.textContent)e.textContent=UT('rdr.menu',e.textContent);e.setAttribute('aria-label',UT('rdr.menu',e.getAttribute('aria-label')||''));}"
    "e=q('#mcat');if(e)e.setAttribute('title',UT('mcat.title',e.getAttribute('title')||''));"
    "e=q('.cmp-lab.b');if(e)e.textContent=UT('cmp.before',e.textContent);"
    "e=q('.cmp-lab.a');if(e)e.textContent=UT('cmp.after',e.textContent);"
    "e=q('[data-act=close]');if(e)e.title=UT('rdr.btn_close',e.title);"
    "e=q('[data-act=zoom-out]');if(e)e.title=UT('rdr.btn_zout',e.title);"
    "e=q('[data-act=zoom-in]');if(e)e.title=UT('rdr.btn_zin',e.title);"
    "e=q('[data-act=zoom-fit]');if(e)e.title=UT('rdr.t_fit',e.title);"
    "e=q('[data-act=fs]');if(e)e.title=UT('rdr.btn_fs',e.title);"
    "e=q('#sprev');if(e)e.title=UT('rdr.prev_page',e.title);"
    "e=q('#snext');if(e)e.title=UT('rdr.next_page',e.title);"
    "var rl=document.querySelectorAll('.rlab span');"
    "if(rl.length==2){rl[0].textContent=UT('rdr.last',rl[0].textContent);rl[1].textContent=UT('rdr.first',rl[1].textContent);}"
    "}catch(err){}}"
    "if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',p)}else{p()}})();</script>")

def _ui_t_head():
    _j = _ui_t_json_file()
    out = ""
    if _j and _j != "{}":
        out += "<script>window.UI_T=" + _j + ";</script>\n"
    out += _UT_JS_HELPER + "\n"
    return out


DEFAULT_GEMINI_KEYS = []

_WEB_PROG_PHASES = (
    ("بارگذاری موتور", "بارگذاری مدلها"),
    ("لود نشد", "خطا"),
    ("استخراج متن", "استخراج متن"),
    ("متن استخراج شد", "استخراج متن"),
    ("(PaddleOCR)", "استخراج متن"),
    ("OCR]", "استخراج متن"),
    ("ترجمه:", "ترجمه"),
    ("فاز ۳", "ترجمه"),
    ("ترجمه با", "ترجمه"),
    ("پاکسازی متن", "پاکسازی"),
    ("روش پاکسازی", "پاکسازی"),
    ("پاکسازی:", "پاکسازی"),
    ("ذخیرهٔ نهایی", "ذخیرهٔ نهایی"),
    ("[✓] تمام شد", "تمام شد"),
    ("لغو شد", "لغو شد"),
    ("خطا:", "خطا"),
    ("آماده شد", "رندر و ذخیره"),
    ("OCR:", "استخراج متن"),
    ("پدلِ رسمیِ اندروید", "استخراج متن"),
    ("پدلِ اندروید", "استخراج متن"),
)

_WEB_PROG_COUNT_RES = (
    (r"استخراج متن[:：]\s*(\d{1,4})\s*/\s*(\d{1,4})\s*صفحه",
     "استخراج متن", "صفحه"),
    (r"پاکسازی متن[:：]\s*(\d{1,4})\s*/\s*(\d{1,4})\s*صفحه",
     "پاکسازی", "صفحه"),
    (r"ترجمه[:：]\s*(\d{1,4})\s*/\s*(\d{1,4})\s*ناحیه",
     "ترجمه", "ناحیه"),
    (r"استریم[:：]\s*(\d{1,4})\s*/\s*(\d{1,4})\s*دیالوگ",
     "ترجمه", "ناحیه"),
)

FONT_BUNDLES = [
    ("normal",       "Vazirmatn-Bold.ttf", "کودک — متن عادی حباب", [
        "https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@master/fonts/ttf/Vazirmatn-Bold.ttf",
        "https://raw.githubusercontent.com/rastikerdar/vazirmatn/master/fonts/ttf/Vazirmatn-Bold.ttf",
    ]),
    ("free_text",    "Vazirmatn-Regular.ttf", "متن بیرون حباب", [
        "https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@master/fonts/ttf/Vazirmatn-Regular.ttf",
        "https://raw.githubusercontent.com/rastikerdar/vazirmatn/master/fonts/ttf/Vazirmatn-Regular.ttf",
    ]),
    ("shout",        "Vazirmatn-Black.ttf", "داد خشم", [
        "https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@master/fonts/ttf/Vazirmatn-Black.ttf",
        "https://raw.githubusercontent.com/rastikerdar/vazirmatn/master/fonts/ttf/Vazirmatn-Black.ttf",
    ]),
    ("comedy_shout", "Gandom.ttf", "داد کمدی", [
        "https://cdn.jsdelivr.net/gh/rastikerdar/gandom-font@master/dist/Gandom.ttf",
        "https://raw.githubusercontent.com/rastikerdar/gandom-font/master/dist/Gandom.ttf",
        "https://cdn.jsdelivr.net/gh/rastikerdar/shabnam-font@master/dist/Shabnam-Bold.ttf",
        "https://raw.githubusercontent.com/rastikerdar/shabnam-font/master/dist/Shabnam-Bold.ttf",
    ]),
    ("whisper",      "Nahid.ttf", "زمزمه دست‌نویس", [
        "https://cdn.jsdelivr.net/gh/rastikerdar/nahid-font@master/dist/Nahid.ttf",
        "https://raw.githubusercontent.com/rastikerdar/nahid-font/master/dist/Nahid.ttf",
        "https://cdn.jsdelivr.net/gh/rastikerdar/sahel-font@master/dist/Sahel.ttf",
        "https://raw.githubusercontent.com/rastikerdar/sahel-font/master/dist/Sahel.ttf",
    ]),
    ("thought",      "Samim-Bold.ttf", "تفکر ابری", [
        "https://cdn.jsdelivr.net/gh/rastikerdar/samim-font@master/dist/Samim-Bold.ttf",
        "https://raw.githubusercontent.com/rastikerdar/samim-font/master/dist/Samim-Bold.ttf",
    ]),
    ("system",       "Sahel-Bold.ttf", "پنجرهٔ سیستم/UI (دیجیتال)", [
        "https://cdn.jsdelivr.net/gh/rastikerdar/sahel-font@master/dist/Sahel-Bold.ttf",
        "https://raw.githubusercontent.com/rastikerdar/sahel-font/master/dist/Sahel-Bold.ttf",
        "https://cdn.jsdelivr.net/gh/amirwolf5122/Manga-AutoTranslate@main/fonts/Sahel-Bold.ttf",
        "https://raw.githubusercontent.com/amirwolf5122/Manga-AutoTranslate/main/fonts/Sahel-Bold.ttf",
    ]),
    ("letter",       "Amiri-Regular.ttf", "نامه/طومار", [
        "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/amiri/Amiri-Regular.ttf",
        "https://raw.githubusercontent.com/google/fonts/main/ofl/amiri/Amiri-Regular.ttf",
    ]),
    ("narrator",     "Shabnam-Bold.ttf", "راوی مستطیل", [
        "https://cdn.jsdelivr.net/gh/rastikerdar/shabnam-font@master/dist/Shabnam-Bold.ttf",
        "https://raw.githubusercontent.com/rastikerdar/shabnam-font/master/dist/Shabnam-Bold.ttf",
    ]),
    ("monster",      "Sahel-Black.ttf", "صدای هیولا", [
        "https://cdn.jsdelivr.net/gh/rastikerdar/sahel-font@master/dist/Sahel-Black.ttf",
        "https://raw.githubusercontent.com/rastikerdar/sahel-font/master/dist/Sahel-Black.ttf",
    ]),
    ("cry",          "NotoNaskhArabic-Regular.ttf", "گریه", [
        "https://cdn.jsdelivr.net/gh/amirwolf5122/Manga-AutoTranslate@main/fonts/NotoNaskhArabic-Regular.ttf",
        "https://raw.githubusercontent.com/amirwolf5122/Manga-AutoTranslate/main/fonts/NotoNaskhArabic-Regular.ttf",
    ]),
    ("fear",         "Sahel-Light.ttf", "ترس", [
        "https://cdn.jsdelivr.net/gh/rastikerdar/sahel-font@master/dist/Sahel-Light.ttf",
        "https://raw.githubusercontent.com/rastikerdar/sahel-font/master/dist/Sahel-Light.ttf",
    ]),
    ("broadcast",    "Vazirmatn-Medium.ttf", "بی‌سیم/موبایل/تلویزیون", [
        "https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@master/fonts/ttf/Vazirmatn-Medium.ttf",
        "https://raw.githubusercontent.com/rastikerdar/vazirmatn/master/fonts/ttf/Vazirmatn-Medium.ttf",
    ]),
    ("sun_thought",  "Parastoo.ttf", "تفکر خورشیدی", [
        "https://cdn.jsdelivr.net/gh/amirwolf5122/Manga-AutoTranslate@main/fonts/Parastoo.ttf",
        "https://raw.githubusercontent.com/amirwolf5122/Manga-AutoTranslate/main/fonts/Parastoo.ttf",
        "https://cdn.jsdelivr.net/gh/rastikerdar/parastoo-font@master/dist/Parastoo.ttf",
        "https://raw.githubusercontent.com/rastikerdar/parastoo-font/master/dist/Parastoo.ttf",
    ]),
    ("square_thought", "NotoNaskhArabic-Bold.ttf", "فکر مربعی", [
        "https://cdn.jsdelivr.net/gh/amirwolf5122/Manga-AutoTranslate@main/fonts/NotoNaskhArabic-Bold.ttf",
        "https://raw.githubusercontent.com/amirwolf5122/Manga-AutoTranslate/main/fonts/NotoNaskhArabic-Bold.ttf",
    ]),
    ("black",        "Tanha.ttf", "دارک تیره", [
        "https://cdn.jsdelivr.net/gh/amirwolf5122/Manga-AutoTranslate@main/fonts/Tanha.ttf",
        "https://raw.githubusercontent.com/amirwolf5122/Manga-AutoTranslate/main/fonts/Tanha.ttf",
        "https://cdn.jsdelivr.net/gh/rastikerdar/tanha-font@master/dist/Tanha.ttf",
        "https://raw.githubusercontent.com/rastikerdar/tanha-font@master/dist/Tanha.ttf",
    ]),
]

def _norm_instr(text: str) -> str:
    t = (text or "").replace("\\n", "\n")
    return re.sub(r"\s+", " ", t.strip())

def is_custom_instruction(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    for d in _known_default_instruction_texts():
        if d and _norm_instr(t) == _norm_instr(d):
            return False
    return True

def _known_default_instruction_texts() -> list:
    out = []
    try:
        from manga import PROMPT_PRESETS
        out += [v for v in PROMPT_PRESETS.values() if isinstance(v, str)]
    except Exception:
        pass
    try:
        from manga import visible_prompt_presets as _vpp
        out += [v for v in _vpp().values() if isinstance(v, str)]
    except Exception:
        pass
    try:
        from manga import PROMPT_PRESETS_LEGACY
        out += [p for p in PROMPT_PRESETS_LEGACY if isinstance(p, str)]
    except Exception:
        pass
    return out

def normalize_api_base(url: str) -> str:
    if not url:
        return ""
    u = str(url).strip().strip('"').strip("'").rstrip("/")
    if not u:
        return ""
    if "://" not in u:
        u = "https://" + u
    try:
        from urllib.parse import urlparse
        p = urlparse(u)
        host = (p.hostname or "").lower()
    except Exception:
        return ""
    if not host:
        return ""
    if "." not in host and host != "localhost" and not host.startswith("127."):
        return ""
    return u

def _cli_ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return ""

PROMPT_MODE_DEFAULT = "professional"

PROMPT_MODE_LABELS = {
    "professional": "حرفه‌ای — مخصوص Gemini Flash و Pro",
    "lite": "سبک — مخصوص Flash Lite و سرویس‌های غیر Gemini",
}

_PROMPT_MODE_LEGACY_LABELS = {
    "auto": "professional",
    "خودکار (بر اساس سرویس و مدل)": "professional",
    "حرفه‌ای — Flash و Pro": "professional",
    "سبک — Flash Lite و غیرِ Gemini": "lite",
}

def sanitize_prompt_mode(v) -> str:
    s = str(v or "").strip()
    if s in ("professional", "lite"):
        return s
    if s in _PROMPT_MODE_LEGACY_LABELS:
        return _PROMPT_MODE_LEGACY_LABELS[s]
    for _k, _lab in PROMPT_MODE_LABELS.items():
        if s == _lab:
            return _k
    return "professional"

def resolve_prompt_preview(mode_v, provider_v, model_v, instr_v):
    t = (instr_v or "").strip()
    try:
        from manga import strip_hidden_rules as _shr
    except Exception:
        _shr = None
    if t and is_custom_instruction(t):
        return _shr(t) if _shr else t
    m = sanitize_prompt_mode(mode_v)
    prov = (provider_v or "gemini").strip()
    mdl = _model_str(model_v)
    try:
        from manga import resolve_prompt_mode as _rpm, PROMPT_PRESETS as _PP
        resolved = _rpm(m, prov, mdl)
        txt = _PP[resolved]
    except Exception:
        resolved, txt = "professional", ""
    if _shr:
        txt = _shr(txt)
    return txt

def ensure_dirs():
    for d in (WORK_DIR, UPLOAD_DIR, OUT_DIR, FONT_DIR):
        os.makedirs(d, exist_ok=True)

def default_keys() -> str:
    for name in KEY_ENV_ORDER:
        v = os.environ.get(name, "").strip()
        if v:
            return v
    return DEFAULT_GEMINI_KEYS

def load_config() -> dict:
    try:
        with open(CFG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        return {}
    try:
        p = str(cfg.get("provider") or "").strip().lower()
        if p in PROVIDER_ALIASES:
            cfg["provider"] = PROVIDER_ALIASES[p]
    except Exception:
        pass
    return cfg

def save_config(cfg: dict) -> None:
    try:
        with open(CFG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

CUSTOM_MODELS_PATH = os.path.join(WORK_DIR, "manga_models.json")

def _web_host() -> bool:
    return (os.environ.get("GITHUB_ACTIONS", "").strip() not in ("", "false")
            or os.environ.get("MANGA_WEB", "").strip() == "1"
            or os.environ.get("RAILWAY_STATIC_URL", "").strip() != ""
            or os.environ.get("SPACE_ID", "").strip() != ""
            or os.environ.get("HF_SPACE_ID", "").strip() != "")


_OCR_LANG_ORDER = {"ja": 0, "ko": 1, "zh": 2, "en": 3}

def _ocr_lang_norm(v) -> str:
    try:
        if isinstance(v, str):
            _s = str(v or "").strip()
            _s = _s.strip("[]").replace("'", "").replace('"', "")
            parts = [p for p in re.split(r"[,\s]+", _s) if p]
        elif isinstance(v, (list, tuple)):
            parts = []
            for x in (v or []):
                parts += [p for p in re.split(r"[,\s]+", str(x or "").strip()) if p]
        else:
            parts = []
        parts = [p.lower() for p in parts]
        if "multi" in parts:
            return "multi"
        if len([p for p in parts if p in ("ja", "ko", "zh")]) >= 2:
            return "multi"
        keep = [p for p in parts if p in _OCR_LANG_ORDER]
        if not keep:
            return "en"
        keep.sort(key=lambda p: _OCR_LANG_ORDER[p])
        return " ".join(keep)
    except Exception:
        return "en"

def _ocr_lang_ui_value(v):
    s = _ocr_lang_norm(v)
    if s == "multi":
        return ["ja", "ko", "zh", "en"]
    return s.split() if s else ["en"]


def _web_file_ttl() -> int:
    try:
        _m = int(os.environ.get("MANGA_WEB_TTL_MIN", "120") or 120)
    except Exception:
        _m = 120
    return max(15, min(1440, _m)) * 60


_WEB_SEEN_PATH = os.path.join(WORK_DIR, "sessions", "web_last_seen.json")
_WEB_LAST_SEEN: dict = {}
_web_seen_lock = threading.Lock()
_web_seen_flush_ts = 0.0


def _web_seen_load() -> None:
    global _WEB_LAST_SEEN
    try:
        with open(_WEB_SEEN_PATH, encoding="utf-8") as _fh:
            _WEB_LAST_SEEN = json.load(_fh) or {}
    except Exception:
        _WEB_LAST_SEEN = {}


def _web_touch(sid: str) -> None:
    global _web_seen_flush_ts
    sid = str(sid or "").strip()
    if not sid or not _web_host():
        return
    now = time.time()
    flush = False
    with _web_seen_lock:
        _WEB_LAST_SEEN[sid[:12]] = now
        if now - _web_seen_flush_ts > 30:
            _web_seen_flush_ts = now
            flush = True
    if flush:
        try:
            os.makedirs(os.path.dirname(_WEB_SEEN_PATH), exist_ok=True)
            with _web_seen_lock:
                with open(_WEB_SEEN_PATH, "w", encoding="utf-8") as _fh:
                    json.dump(_WEB_LAST_SEEN, _fh)
        except Exception:
            pass


def _web_last_seen_of(sid12: str) -> float:
    with _web_seen_lock:
        return float(_WEB_LAST_SEEN.get(str(sid12 or "")) or 0)

def load_custom_models() -> list:
    if _web_host():
        return []
    try:
        with open(CUSTOM_MODELS_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            out = []
            for it in data:
                if not isinstance(it, dict):
                    continue
                name = str(it.get("name") or "").strip()
                if not name:
                    continue
                out.append({
                    "name": name,
                    "api_base": str(it.get("api_base") or "").strip(),
                    "api_key": str(it.get("api_key") or "").strip(),
                    "model": str(it.get("model") or "").strip(),
                })
            return out
    except Exception:
        pass
    return []

def save_custom_models(models: list) -> bool:
    if _web_host():
        return False
    try:
        with open(CUSTOM_MODELS_PATH, "w", encoding="utf-8") as f:
            json.dump(models, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def purge_web_secrets(log=print) -> None:
    if not _web_host():
        return
    import glob as _glob
    victims = [CUSTOM_MODELS_PATH, CFG_PATH, HIST_PATH]
    victims += _glob.glob(os.path.join(WORK_DIR, "manga_backup_*.json"))
    for p in victims:
        try:
            if os.path.isfile(p):
                os.remove(p)
                try:
                    log(f"[🛡] وبِ عمومی — فایلِ حساس از دیسک پاک شد: "
                        f"{os.path.basename(p)}")
                except Exception:
                    pass
        except Exception:
            pass

def _cm_names(models: list) -> list:
    out = []
    for m in (models or []):
        nm = str(m.get("name") or "").strip()
        if nm and nm not in out:
            out.append(nm)
    return out

def _cm_mask_key(k) -> str:
    k = str(k or "").strip()
    if not k:
        return ""
    if len(k) <= 10:
        return k[:2] + "…" + k[-2:]
    return k[:6] + "…" + k[-4:]

def _cm_info_html(models: list, name: str) -> str:
    nm = str(name or "").strip()
    m = next((x for x in (models or [])
              if str(x.get("name") or "").strip() == nm), None)
    if not m:
        return ""
    esc = (lambda s: str(s or "").replace("&", "&amp;")
           .replace("<", "&lt;").replace(">", "&gt;"))
    base = str(m.get("api_base") or "").strip()
    mdl = str(m.get("model") or "").strip()
    key = _cm_mask_key(m.get("api_key"))
    parts = [f"مدلِ ذخیره‌شدهٔ «{esc(nm)}»",
             "لینک: " + (f"<code>{esc(base)}</code>" if base
                         else "Gemini رسمی (بدونِ دامنهٔ سفارشی)")]
    if mdl:
        parts.append("مدلِ هوش: " + f"<code>{esc(mdl)}</code>")
    if key:
        parts.append(f"کلید: <code>{esc(key)}</code>")
    return "<div class='hint'>" + " — ".join(parts) + "</div>"

def _ai_choices(models: list) -> list:
    names = [n for n in _cm_names(models)
             if n not in ("auto", "gemini", "custom")]
    out = (["auto"] if names else []) + ["gemini"]
    out.extend(names)
    out.append("custom")
    return out

def _model_str(v) -> str:
    if v is None:
        return ""
    if isinstance(v, (list, tuple, set)):
        items = [str(x or "").strip() for x in v]
    else:
        s = str(v or "").strip()
        if s.startswith("[") and s.endswith("]"):
            try:
                import json as _js
                _p = _js.loads(s)
                if isinstance(_p, list):
                    items = [str(x or "").strip() for x in _p]
                else:
                    items = [s]
            except Exception:
                items = [s]
        else:
            items = [s]
    out = []
    for m in items:
        for piece in str(m).replace(";", ",").split(","):
            piece = piece.strip().strip('"').strip("'")
            if piece and piece not in out:
                out.append(piece)
    return ",".join(out)

def _gemini_offline_models() -> list:
    try:
        from manga import gemini_offline_models as _g
        _lst = _g()
        if _lst:
            return list(_lst)
    except Exception:
        pass
    return [
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-4-hydrogen",
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-3-flash-preview",
    ]

def _gemini_default_models_str() -> str:
    return ",".join(_gemini_offline_models())

def _models_join(models) -> str:
    try:
        from manga import join_model_list as _j
        return _j(list(models or []))
    except Exception:
        return ",".join(str(m or "").strip() for m in (models or [])
                        if str(m or "").strip())

def resolve_ai_named(models: list, pick: str, api_keys: str = "",
                     model_id: str = ""):
    pick = str(pick or "").strip()
    if not pick or pick in ("auto", "gemini", "custom"):
        return None
    for m in (models or []):
        if str(m.get("name") or "").strip() == pick:
            base = str(m.get("api_base") or "").strip()
            return ("custom" if base else "gemini",
                    base,
                    str(m.get("api_key") or "").strip() or (api_keys or ""),
                    str(m.get("model") or "").strip() or (model_id or ""))
    return None

def resolve_ai_auto(models: list, api_keys: str = "", model_id: str = "",
                    probe=None):
    models = [m for m in (models or [])
              if isinstance(m, dict) and str(m.get("name") or "").strip()]
    cands = [("gemini", "Gemini", "", str(api_keys or ""),
              str(model_id or ""))]
    for m in models:
        cands.append(("custom",
                      str(m.get("name") or "").strip(),
                      str(m.get("api_base") or "").strip(),
                      str(m.get("api_key") or "").strip(),
                      str(m.get("model") or "").strip()))
    lines = ["🤖 حالتِ auto — بررسیِ دسترسیِ مدلها…"]
    if probe is None:
        try:
            from manga import test_api_keys as probe
        except Exception as e:
            lines.append(f"⚠ موتور برایِ تستِ دسترسی بارگذاری نشد "
                         f"({str(e)[:120]}) — «gemini» انتخاب شد.")
            return ("gemini", "", str(api_keys or ""),
                    str(model_id or ""), lines)
    for prov, label, base, key, mdl in cands:
        try:
            res = probe(key, prov, base, model=mdl)
            ok = any(isinstance(r, dict) and r.get("ok") for r in (res or []))
            err = "; ".join(str(r.get("error") or "") for r in (res or [])
                            if isinstance(r, dict) and not r.get("ok"))[:160]
        except Exception as e:
            ok, err = False, str(e)[:160]
        if ok:
            lines.append(f"🤖 auto: «{label}» در دسترس است → انتخاب شد.")
            return (prov, base, key, mdl, lines)
        lines.append(f"🤖 auto: «{label}» در دسترس نیست"
                     + (f" ({err})" if err else "") + " → بعدی…")
    lines.append("❌ auto: هیچ‌کدام از مدلها در دسترس نبودند.")
    return ("", "", "", "", lines)

def _server_has_gpu() -> bool:
    _cache = globals().get("_SERVER_GPU_CACHE")
    if _cache is not None:
        return _cache
    ok = False
    try:
        r = subprocess.run(["nvidia-smi", "-L"], capture_output=True,
                           timeout=8)
        ok = r.returncode == 0 and b"GPU" in (r.stdout or b"")
    except Exception:
        ok = False
    if not ok and sys.platform == "win32":
        try:
            import onnxruntime as _ort
            ok = "DmlExecutionProvider" in _ort.get_available_providers()
        except Exception:
            ok = False
    globals()["_SERVER_GPU_CACHE"] = ok
    return ok

def _server_gpu_label() -> str:
    _cache = globals().get("_SERVER_GPU_NAME_CACHE")
    if _cache is not None:
        return _cache
    name = ""
    try:
        r = subprocess.run(["nvidia-smi", "-L"], capture_output=True,
                           timeout=8)
        if r.returncode == 0:
            _lines = [ln.strip() for ln in
                      (r.stdout or b"").decode("utf-8", "ignore").splitlines()
                      if ln.strip()]
            if _lines:
                _m = re.search(r"GPU\s*\d+\s*:\s*(.+?)\s*\(UUID", _lines[0])
                name = (_m.group(1).strip() if _m else _lines[0][:48])
    except Exception:
        name = ""
    if not name and sys.platform == "win32":
        try:
            import onnxruntime as _ort
            if "DmlExecutionProvider" in _ort.get_available_providers():
                name = "DirectML"
        except Exception:
            pass
    globals()["_SERVER_GPU_NAME_CACHE"] = name
    return name

def find_font() -> str:
    cands = []
    if os.path.isdir(FONT_DIR):
        for f in sorted(os.listdir(FONT_DIR)):
            if f.lower().endswith((".ttf", ".otf")):
                cands.append((0 if "vazir" in f.lower() else 1, os.path.join(FONT_DIR, f)))
    for d in (HERE, os.path.expanduser("~/fonts"), os.path.expanduser("~/.fonts")):
        if os.path.isdir(d):
            for f in sorted(os.listdir(d)):
                if f.lower().endswith((".ttf", ".otf")):
                    cands.append((1, os.path.join(d, f)))
    return cands[0][1] if cands else ""

def _download(url: str, dst: str) -> bool:
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as r, open(dst, "wb") as f:
            shutil.copyfileobj(r, f)
        return os.path.getsize(dst) > 20_000
    except Exception:
        try:
            os.remove(dst)
        except Exception:
            pass
        return False

def download_fonts(log=print) -> int:
    
    os.makedirs(FONT_DIR, exist_ok=True)
    n = 0
    for slot, fname, desc, urls in FONT_BUNDLES:
        dst = os.path.join(FONT_DIR, fname)
        if os.path.isfile(dst) and os.path.getsize(dst) > 20_000:
            continue
        log(f"  ⬇ {fname} ({desc}) ...")
        ok = False
        for url in urls:
            if _download(url, dst):
                ok = True
                break
        if ok:
            n += 1
            log(f"  ✔ {fname}")
        else:
            log(f"  ✖ {fname} ناموفق — بعداً خودتان در fonts/ بگذارید")
    return n

GITHUB_RAW_BASE = ("https://raw.githubusercontent.com/"
                   "amirwolf5122/Manga-AutoTranslate/main/")
UPDATE_FILES = ("manga.py", "manga_app.py", "Manga.bat", "manga.sh")
UPDATE_INTERVAL_S = 30 * 60
UPD_DIR = os.path.join(WORK_DIR, "updates")

def _read_ver_from_src(src: str) -> str:
    m = re.search(r'APP_VER\s*=\s*"([^"]+)"', src or "")
    return m.group(1) if m else "0"

def _cmp_ver(a: str, b: str) -> int:
    try:
        pa = [int(x) for x in str(a).split(".")]
        pb = [int(x) for x in str(b).split(".")]
    except Exception:
        return 0
    while len(pa) < len(pb):
        pa.append(0)
    while len(pb) < len(pa):
        pb.append(0)
    return (pa > pb) - (pa < pb)

def _local_file_ver(name: str) -> str:
    try:
        with open(os.path.join(HERE, name), encoding="utf-8") as f:
            return _read_ver_from_src(f.read(8192))
    except Exception:
        return "0"

def _http_get(url: str, timeout: float = 30.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def _remote_app_ver(log=print) -> str:
    try:
        txt = _http_get(GITHUB_RAW_BASE + "VERSION?cb="
                        + str(int(time.time() // 300)), timeout=12).decode("utf-8", "ignore")
        m = re.search(r"versionName\s*=\s*([0-9][0-9.]*)", txt or "")
        if m:
            return m.group(1).strip()
    except Exception as e:
        log(f"[!] چک نسخهٔ remote ناموفق: {str(e)[:80]}")
    return ""

def _local_app_ver() -> str:
    try:
        vp = os.path.join(HERE, "VERSION")
        if os.path.isfile(vp):
            with open(vp, encoding="utf-8") as f:
                m = re.search(r"versionName\s*=\s*([0-9][0-9.]*)", f.read(2048) or "")
                if m:
                    return m.group(1).strip()
    except Exception:
        pass
    return _local_file_ver("manga_app.py")

def _remote_section_names(log=print):
    try:
        txt = _http_get(GITHUB_RAW_BASE + "manga_sections/MANIFEST?cb="
                        + str(int(time.time() // 300)),
                        timeout=12).decode("utf-8", "ignore")
        return [ln.strip() for ln in txt.split("\n")
                if ln.strip() and not ln.strip().startswith("#")
                and ln.strip().endswith(".py")]
    except Exception as e:
        log(f"[!] گرفتنِ MANIFEST ناموفق: {str(e)[:80]}")
        return None

def _stage_update_file(name: str, log=print) -> dict:
    info = {"local": "", "remote": "", "newer": False}
    try:
        src = _http_get(GITHUB_RAW_BASE + name + "?cb="
                        + str(int(time.time() // 300)), timeout=60).decode("utf-8", "ignore")
        info["remote"] = _read_ver_from_src(src[:8192])
        info["local"] = _local_file_ver(name)
        staged = os.path.join(UPD_DIR, name + ".staged")
        os.makedirs(os.path.dirname(staged) or UPD_DIR, exist_ok=True)
        with open(staged, "w", encoding="utf-8") as f:
            f.write(src)
        info["newer"] = True
    except Exception as e:
        info["error"] = str(e)[:120]
    return info

def check_updates(force: bool = False, log=print) -> dict:
    try:
        last = float(load_config().get("last_update_check", 0) or 0)
    except Exception:
        last = 0.0
    now = time.time()
    if not force and last and (now - last) < UPDATE_INTERVAL_S:
        return {"checked": False}

    rep: dict = {"checked": True, "update_available": False, "files": {}}
    remote_ver = _remote_app_ver(log=log)
    local_ver = _local_app_ver()
    newer_global = bool(remote_ver and _cmp_ver(remote_ver, local_ver) > 0)

    if newer_global:
        files = list(UPDATE_FILES)
        sections = _remote_section_names(log=log)
        if sections:
            files += [f"manga_sections/{s}" for s in sections]
        log(f"🔄 آپدیت جدید پیدا شد: v{local_ver} → v{remote_ver} — در حال گرفتن…")
        results: dict = {}
        threads = []

        def _worker(n):
            results[n] = _stage_update_file(n, log=log)

        for name in files:
            th = threading.Thread(target=_worker, args=(name,), daemon=True)
            th.start()
            threads.append(th)
        for th in threads:
            th.join(timeout=180)
        for name in files:
            info = results.get(name) or {"local": "", "remote": remote_ver,
                                         "newer": False, "error": "timeout"}
            rep["files"][name] = info
            if info.get("newer"):
                rep["update_available"] = True
    else:
        for name in UPDATE_FILES:
            rep["files"][name] = {"local": _local_file_ver(name),
                                  "remote": local_ver, "newer": False}
        log("✔ برنامه به‌روز است.")
    try:
        cfg = load_config()
        cfg["last_update_check"] = now
        save_config(cfg)
    except Exception:
        pass
    return rep

def apply_updates(report: Optional[dict] = None, log=print) -> list:

    installed = []
    rep = report if (report and report.get("checked")) else check_updates(force=True, log=log)
    gver = _local_app_ver()
    for name, info in (rep.get("files") or {}).items():
        staged = os.path.join(UPD_DIR, name + ".staged")
        if not (info.get("newer") and os.path.isfile(staged)):
            continue
        try:
            dst = os.path.join(HERE, name)
            os.makedirs(os.path.dirname(dst) or HERE, exist_ok=True)
            bak = dst + ".bak"
            if os.path.isfile(dst):
                shutil.copyfile(dst, bak)
            os.replace(staged, dst)
            v = info.get("remote") or gver
            installed.append(f"{name} → v{v}")
            log(f"✔ نصب شد: {name} v{v} (بکاپ: {os.path.basename(bak)})")
        except Exception as e:
            log(f"✖ نصب {name} ناموفق: {e}")

    sec_dir = os.path.join(HERE, "manga_sections")
    keep = {os.path.basename(n) for n in (rep.get("files") or {})
            if n.startswith("manga_sections/")}
    if keep and os.path.isdir(sec_dir):
        for n in os.listdir(sec_dir):
            if n.endswith(".py") and n[:1].isdigit() and n not in keep:
                try:
                    os.remove(os.path.join(sec_dir, n))
                    log(f"🧹 بخشِ زامبیِ آپدیتِ قبلی حذف شد: {n}")
                except Exception:
                    pass

    if installed:
        log("🔁 برای فعال‌شدن کامل، برنامه را ببندید و دوباره باز کنید.")
    return installed

def auto_update_on_start(log=print) -> None:

    def _worker():
        while True:
            try:
                rep = check_updates(force=False, log=log)
                if rep.get("update_available"):
                    apply_updates(rep, log=log)
            except Exception:
                pass
            time.sleep(UPDATE_INTERVAL_S)

    try:
        th = threading.Thread(target=_worker, daemon=True)
        th.start()
    except Exception:
        pass

_ft_checked: dict = {}

def _font_persian_ok(path: str) -> bool:
    if path in _ft_checked:
        return _ft_checked[path]
    ok = True
    try:
        from fontTools.ttLib import TTFont
        import arabic_reshaper
        from bidi.algorithm import get_display
    except ImportError:
        try:
            for _pkg in ("fonttools", "arabic-reshaper", "python-bidi"):
                subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", _pkg])
            from fontTools.ttLib import TTFont
            import arabic_reshaper
            from bidi.algorithm import get_display
        except Exception:
            _ft_checked[path] = True
            return True
    try:
        shaped = get_display(arabic_reshaper.reshape("من قرفتم باهاش حرف بزنم ژاله پک‌بک"))
        cps = {ord(c) for c in shaped
               if ord(c) > 0x2000 and not 0x200C <= ord(c) <= 0x200F}
        cmap = TTFont(path).getBestCmap()
        ok = all(c in cmap for c in cps)
    except Exception:
        ok = True
    _ft_checked[path] = ok
    return ok

def font_args() -> list:
    
    args = []
    main = find_font()
    if main:
        args += ["--font", main]
    cli_font = {"free_text": "free"}
    for slot, fname, _desc, _urls in FONT_BUNDLES:
        p = os.path.join(FONT_DIR, fname)
        if os.path.isfile(p) and _font_persian_ok(p):
            flag = cli_font.get(slot, slot.replace("_", "-"))
            args += [f"--font-{flag}", p]
    return args

def human_size(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"

def smart_output_base(input_path: str) -> str:
    
    raw = (input_path or "").strip()
    if not raw:
        return "chapter_fa"

    _rg = re.match(r"^(https?://\S+?)\s*[<>]\s*(https?://\S+)$", raw)
    if _rg:
        _b1 = smart_output_base(_rg.group(1))
        _b1 = re.sub(r"_fa$", "", _b1)
        _last = _rg.group(2).split("?")[0].rstrip("/").split("/")[-1] or ""
        _m2 = re.search(r"(\d+)", _last)
        if _m2:
            return _b1 + "-" + _m2.group(1) + "_fa"

    raw = re.split(r"[,\n\r\t]+", raw)[0].strip()
    is_url = raw.lower().startswith(("http://", "https://"))
    if is_url:
        from urllib.parse import urlparse, unquote
        path_u = unquote(urlparse(raw).path).strip("/")
        parts = [p for p in path_u.split("/") if p and p != "*"]
        base = "chapter"
        if parts:
            
            while parts and (
                parts[-1].startswith("*")
                or re.search(r"(?i)\.(jpe?g|png|webp|gif|bmp)(\?.*)?$", parts[-1])
                or re.fullmatch(r"\d+", parts[-1] or "")
            ):
                
                if re.fullmatch(r"\d+", parts[-1] or ""):
                    parts.pop()
                    break
                parts.pop()
                if not parts:
                    break
            slug = parts[-1] if parts else "chapter"
            
            m = re.search(
                r"(?i)(?:^|-)(chapter[-_]?\d+|ch[-_]?\d+|ep[-_]?\d+)$",
                slug,
            )
            if m:
                
                series = parts[-2] if len(parts) >= 2 else ""
                ch = m.group(1)
                base = f"{series}-{ch}" if series else ch
            elif re.search(r"(?i)chapter[-_]?\d+", slug):
                base = slug
            elif any(re.search(r"(?i)^chapter[-_]?\d+$", p) for p in parts):
                for p in parts:
                    if re.search(r"(?i)^chapter[-_]?\d+$", p):
                        series = parts[parts.index(p) - 1] if parts.index(p) > 0 else ""
                        base = f"{series}-{p}" if series else p
                        break
            elif "chapter" in [p.lower() for p in parts]:
                low_parts = [p.lower() for p in parts]
                try:
                    idx = low_parts.index("chapter")
                    name = parts[idx - 1] if idx > 0 else "chapter"
                    num = parts[idx + 1] if idx + 1 < len(parts) else ""
                    num = re.sub(r"[^\w\-]", "", num.split("?")[0])
                    base = f"{name}-{num}" if num else name
                except ValueError:
                    base = slug
            else:
                base = slug if slug else "chapter"
        base = re.sub(r"\*+", "", base)
        base = re.sub(r"(?i)\.(jpe?g|png|webp|gif|bmp)$", "", base)
        base = re.sub(r"[^\w\-.]+", "-", base)
        base = re.sub(r"-{2,}", "-", base).strip("-._") or "chapter"
    else:
        path_only = raw.rstrip("/\\")
        base = os.path.splitext(os.path.basename(path_only))[0] or "output"
        base = re.sub(r"\*+", "", base)
        base = re.sub(r"[^\w\-.]+", "-", base).strip("-._") or "output"
    if not base.lower().endswith("_fa"):
        base = base + "_fa"
    return base

def _stage_data_urls(src_text: str, dest_dir: str) -> str:
    raw = str(src_text or "")
    try:
        import base64 as _b64
        lines = [x.strip() for x in re.split(r"[\n\r]+", raw)]
        if not any(x.lower().startswith("data:image/") for x in lines):
            return raw
        os.makedirs(dest_dir, exist_ok=True)
        out, n = [], 0
        for ln in lines:
            if not ln:
                continue
            if not ln.lower().startswith("data:image/"):
                out.append(ln)
                continue
            head, _, b64 = ln.partition(",")
            try:
                content = _b64.b64decode(b64)
            except Exception:
                content = b""
            if not content:
                continue
            ext = ".jpg"
            m = re.search(r"data:image/(jpe?g|png|webp|bmp)",
                          head.lower())
            if m:
                ext = "." + ("jpg" if m.group(1) in ("jpg", "jpeg")
                             else m.group(1))
            n += 1
            fp = os.path.join(dest_dir, "page_%03d%s" % (n, ext))
            with open(fp, "wb") as f:
                f.write(content)
            out.append(fp)
        return "\n".join(out)
    except Exception:
        return raw

_ASK_ANSWER = {}

def _cache_dir_for(output_path) -> str:
    _p = str(output_path or "")
    root, ext = os.path.splitext(_p)
    if ext.lower() in (".pdf", ".zip", ".html", ".psd",
                       ".webp", ".png", ".jpg", ".jpeg"):
        return root + ".cache"
    return _p + ".cache"

def _trans_sig_of(provider, model, api_base, prompt_mode,
                  instruction, fake, temperature, top_p,
                  deep_thinking=True, safety_settings=False,
                  max_tokens=None, brief=False, glossary_sig="") -> str:
    import hashlib as _hl

    def _ms(v) -> str:
        if v is None:
            return ""
        if isinstance(v, (list, tuple, set)):
            items = [str(x or "").strip() for x in v]
        else:
            items = [str(v or "").strip()]
        out = []
        for m0 in items:
            for piece in m0.replace(";", ",").split(","):
                piece = piece.strip().strip('"').strip("'")
                if piece and piece not in out:
                    out.append(piece)
        return ",".join(out)

    try:
        prov = str(provider or "").strip().lower()
        mdl = _ms(model)
        ab = (str(api_base or "").strip().lower()
              if prov == "custom" else "")
        pm = str(prompt_mode or "professional").strip().lower() or "professional"
        instr = str(instruction or "").strip()
        if instr and not is_custom_instruction(instr):
            instr = ""
        try:
            _mt = ("mt%d" % int(max_tokens)) if max_tokens else "mt-"
        except Exception:
            _mt = "mt-"
        parts = [
            "t2", prov, mdl, ab, pm,
            (_hl.sha256(instr.encode("utf-8", "ignore")).hexdigest()[:12]
             if instr else "-"),
            "fake" if fake else "real",
            "%.2f" % float(temperature if temperature is not None else 0.7),
            "%.2f" % float(top_p if top_p is not None else 0.9),
            "think" if deep_thinking else "nothink",
            "sbn" if safety_settings else "nosbn",
            _mt,
            "brf" if brief else "nbrf",
            (str(glossary_sig).strip() or "-"),
        ]
        return _hl.sha256("|".join(parts).encode("utf-8", "ignore")).hexdigest()[:16]
    except Exception:
        return ""

def _glossary_text_sig(txt) -> str:
    try:
        items = {}
        for ln in str(txt or "").splitlines():
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            for sep in ("=", ":", "\t"):
                if sep in ln:
                    k, v = ln.split(sep, 1)
                    k, v = k.strip(), v.strip()
                    if k and v:
                        items[k] = v
                    break
        if not items:
            return ""
        import hashlib as _hl
        _j = "\n".join(f"{k}={v}" for k, v in sorted(items.items()))
        return _hl.sha256(_j.encode("utf-8", "ignore")).hexdigest()[:10]
    except Exception:
        return ""

def append_history(entry: dict) -> None:
    try:
        with open(HIST_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass

def has_display() -> bool:
    if os.name == "nt" or sys.platform == "darwin":
        return True
    return bool(os.environ.get("DISPLAY"))

def manga_py_ok() -> bool:
    
    try:
        with open(MANGA_PY, encoding="utf-8") as f:
            head = f.read()
    except Exception:
        return False
    return ("def run_desktop" not in head) and ("def run_web" not in head)

MANGA_MIXED_MSG = (
    "❌ فایل manga.py کنار برنامه، فایل «مترجم» نیست — کد خود برنامه داخلش ذخیره شده\\n"
    "(احتمالاً manga_app.py را با نام manga.py ذخیره کرده‌اید).\\n"
    "فایل manga.py اصلی (مترجم) را کنار manga_app.py بگذارید و دوباره اجرا کنید."
)

def run_cli_interactive():
    
    print(f"\n══════════ {APP_NAME} v{APP_VER} — CLI ══════════\n")
    if not manga_py_ok():
        print(MANGA_MIXED_MSG)
        return

    cfg = load_config()
    src = input("📄 مسیر فایل/پوشه یا URL ورودی: ").strip().strip('"')
    if not src:
        print("❌ ورودی خالی است.")
        return
    if not os.path.exists(src) and not src.lower().startswith(("http://", "https://")):
        print(f"❌ مسیر پیدا نشد: {src}")
        return

    print("\nقالب خروجی:  1) PDF   2) ZIP   3) HTML   4) PSD")
    f = input("انتخاب [1-4] (پیش‌فرض 1): ").strip() or "1"
    ext = {"1": ".pdf", "2": ".zip", "3": ".html", "4": ".psd",
           "5": ".psd"}.get(f, ".pdf")

    print("\nارائه‌دهندهٔ AI را انتخاب کنید:")
    prov_menu = [
        ("gemini", "Google Gemini - رایگان با سهمیه"),
        ("custom", "سرویس دلخواه — ۴ فرمت: OpenAI / Responses / Anthropic / Google (دامنه + توکن + مدل)"),
    ]
    for i, (pid, desc) in enumerate(prov_menu, 1):
        print(f"  {i}) {pid:12} ({desc})")
    pc = input("انتخاب [پیش‌فرض 1]: ").strip() or "1"
    try:
        provider = prov_menu[int(pc) - 1][0]
    except (ValueError, IndexError):
        provider = "gemini"
    keys = input("کلید API (خالی = env/config): ").strip() \
        or cfg.get("api_keys") or default_keys()
    model = input(f"مدل [{cfg.get('model', '') or 'پیش‌فرض'}]: ").strip() \
        or cfg.get("model", "")
    api_base_v = ""
    if provider == "custom":
        print("── سرویس دلخواه (۴ فرمت: OpenAI / Responses / Anthropic / Google) ──")
        api_base_v = str(cfg.get("api_base", "") or "")
        for _try in range(3):
            hint = f" [Enter = همان {api_base_v}]" if api_base_v else " [خالی = انصراف]"
            raw = _cli_ask("دامنهٔ API (مثال: https://api.example.com/v1)" + hint + ": ")
            if not raw and api_base_v:
                break
            if not raw:
                print("  ✗ provider «custom» بدون دامنهٔ API کار نمی‌کند — دوباره وارد کن.")
                continue
            _ab = normalize_api_base(raw)
            if not _ab:
                print("  ✗ آدرس معتبر نیست — مثل https://api.example.com/v1 بنویس "
                      "(https:// خودکار اضافه می‌شود).")
                continue
            api_base_v = _ab
            break
        if not api_base_v:
            print("❌ انصراف — دامنهٔ API داده نشد. provider دیگری انتخاب کن یا دوباره اجرا کن.")
            return
        if not model:
            for _try in range(3):
                model = _cli_ask("نام مدل (مثال: gpt-4o-mini) [اجباری]: ")
                if model:
                    break
                print("  ✗ مدل نمی‌تواند خالی باشد — مثال: gpt-4o-mini")
            if not model:
                print("❌ انصراف — نام مدل داده نشد.")
                return
        print(f"  ✔ دامنه: {api_base_v} | مدل: {model}")

    font_v = cfg.get("font") or find_font()
    if not font_v or not os.path.isfile(font_v):
        print("❌ فونت فارسی پیدا نشد — fonts/ را آماده کنید.")
        return

    base = smart_output_base(src)
    out_v = os.path.join(OUT_DIR, base + ext)
    os.makedirs(OUT_DIR, exist_ok=True)

    cmd = [sys.executable, MANGA_PY, "-i", src, "-o", out_v, "--font", font_v,
           "--provider", provider,
           "--workers", str(int(cfg.get("workers", 2))),
           "--bubbles-per-request", str(int(cfg.get("bubbles", 6))),
           "--api-timeout", str(int(cfg.get("timeout", 40))),
           "--quality", str(int(cfg.get("quality", 92))),
           "--batch-workers", str(int(cfg.get("batch_workers", 3))),
           "--max-retries", str(int(cfg.get("max_retries", 8))),
           "--request-delay", str(float(cfg.get("request_delay", 0))),
           "--temperature", str(float(cfg.get("temperature", 0.7))),
           "--top-p", str(float(cfg.get("top_p", 0.9))),
           "--reading-order", str(cfg.get("reading_order", "rtl"))]
    cmd += font_args()
    klist = [k.strip() for k in (keys or "").replace(";", ",").split(",") if k.strip()]
    if klist:
        cmd += ["--api-key", ",".join(klist)]
    if model:
        cmd += ["--model", model]
    if provider == "custom" and api_base_v:
        cmd += ["--api-base", api_base_v]
    cmd += ["--clean-method", str(cfg.get("clean_method") or "lama-manga")]
    _dv_cli = str(cfg.get("device") or "auto").strip().lower()
    if _dv_cli not in ("auto", "cpu", "gpu"):
        _dv_cli = "auto"
    if _dv_cli != "auto":
        cmd += ["--device", _dv_cli]

    print("\n▶ " + " ".join(cmd) + "\n")
    proc = subprocess.Popen(cmd, cwd=HERE, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True,
                            encoding="utf-8", errors="replace", bufsize=1)
    t0 = time.time()
    for line in proc.stdout:
        print(line.rstrip())
    proc.wait()
    dur_s = f"{int((time.time()-t0)//60)}:{int((time.time()-t0)%60):02d}"
    if proc.returncode != 0:
        print(f"\n❌ خطا — کد خروج {proc.returncode}")
    else:
        print(f"\n✅ تمام شد ({dur_s}) — خروجی: {out_v}")

def run_cli(argv):
    if not argv:
        run_cli_interactive()
        return
    if not manga_py_ok():
        print(MANGA_MIXED_MSG)
        sys.exit(1)
    sys.argv = [MANGA_PY] + list(argv)
    import importlib.util
    spec = importlib.util.spec_from_file_location("manga_cli", MANGA_PY)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["manga_cli"] = mod
    spec.loader.exec_module(mod)
    if hasattr(mod, "main"):
        mod.main()

def _ensure_webview() -> bool:
    try:
        import webview
        return True
    except Exception:
        pass
    try:
        print("[*] نصب pywebview برای پنجرهٔ دسکتاپ (فقط بار اول)...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q",
                               "pywebview"], timeout=600)
        import webview
        return True
    except Exception as e:
        print(f"[!] pywebview نصب نشد ({e}) → مرورگر")
        return False


_MT_BROWSER_WIN_JS = """
(function(){
  if (window.__mtBwBtn) return; window.__mtBwBtn = 1;
  var st=null;
  function css(){
    try{
      if(st&&st.parentNode)return;
      st=document.createElement('style');
      st.textContent='#mtbw{position:fixed!important;left:0!important;'
        +'right:0!important;top:0!important;z-index:2147483647!important;'
        +'direction:rtl;font-family:Tahoma,Arial,sans-serif;'
        +'display:flex!important;align-items:center;gap:8px;'
        +'background:rgba(13,13,16,.97) !important;'
        +'border-bottom:1px solid #1f1f24;padding:8px 10px;box-sizing:border-box;'
        +'box-shadow:0 8px 28px rgba(0,0,0,.55)}'
        +'#mtbw .mturl{flex:1;min-width:110px;direction:ltr;text-align:left;'
        +'background:#1a1f2b;color:#e7ebf3;border:1px solid #273043;'
        +'border-radius:20px;padding:9px 14px;font-size:13px;outline:none;'
        +'font-family:inherit}'
        +'#mtbw .mturl:focus{border-color:#e8590c}'
        +'#mtbw button{border:0;cursor:pointer;font-weight:700;font-size:13px;'
        +'color:#fff;background:linear-gradient(135deg,#ff4a3d,#c9271c);'
        +'border-radius:12px;padding:9px 14px;font-family:inherit;'
        +'white-space:nowrap}'
        +'#mtbw .mtgo{background:#2d3649}'
        +'#mtbw .mtnav{background:#2d3649;width:42px;flex:0 0 42px;'
        +'padding:9px 0;text-align:center;font-size:16px;line-height:1}'
        +'#mtbw .mtcnt{color:#97948c;font-size:11.5px;max-width:170px;'
        +'overflow:hidden;text-overflow:ellipsis;white-space:nowrap}'
        +'.mtmenu{position:fixed;z-index:2147483647;direction:rtl;'
        +'background:rgba(20,22,28,.98);border:1px solid #273043;'
        +'border-radius:14px;padding:8px;box-shadow:0 14px 38px rgba(0,0,0,.6);'
        +'display:flex;flex-direction:column;gap:6px;'
        +'font-family:Tahoma,Arial,sans-serif}'
        +'.mtmenu .mtmi{background:#1a1f2b;color:#e7ebf3;border:0;'
        +'cursor:pointer;font-weight:700;font-size:13px;border-radius:10px;'
        +'padding:11px 18px;text-align:right;font-family:inherit;'
        +'white-space:nowrap}'
        +'.mtmenu .mtmi:hover{background:#2d3649}';
      (document.head||document.documentElement).appendChild(st);
    }catch(e){}
  }
  function abs(u){try{var a=document.createElement('a');a.href=u;return a.href}
    catch(e){return null}}
  function qsz(u){
    var m=String(u).match(/[?&](?:type|size|w|h|width|height)=(f?)(\\d{1,4})(?:[_x](\\d{1,4}))?/i);
    if(!m)return 0;
    var a=parseInt(m[2],10)||0;
    var b=parseInt(m[3]||'0',10)||0;
    if(a>0&&b>0)return Math.max(a,b);
    if(m[1]&&a>0)return a;
    return 0}
  function junk(u){
    if(!u)return 1;
    if(u.indexOf('data:')===0)return 1;
    if(!/^https?:/i.test(u))return 1;
    var b=String(u).split(/[?#]/)[0];
    if(/\\.(svg|ico|gif)$/i.test(b))return 1;
    if(/[-_]\\d{2,4}x\\d{2,4}\\.(jpe?g|png|webp)$/i.test(b))return 1;
    var q=qsz(u);
    if(q>0&&q<=400)return 1;
    if(/(logo|icon|avatar|banner|sprite|favicon|badge|flag|button|emoji|thumb(nail)?s?|placeholder|blank|spacer|transparen|loading|spinner|pixel|profile|rating|share|follow|comment|credits)/i.test(b))return 1;
    if(/(?:^|[^a-z0-9])ads?[._/-]/i.test(b))return 1;
    return 0}
  function keyOf(u){
    var b=String(u).split(/[?#]/)[0];
    return b.replace(/[-_]\\d{2,4}x\\d{2,4}\\./i,'.')}
  function collect(){
    try{
      if(/(^|\\.)mangaplus\\.shueisha\\.co\\.jp$/i.test(location.host)&&location.pathname.indexOf('/viewer/')===0)return [location.href];
    }catch(e){}
    var seen={},picked=[];
    function add(u){
      try{
        if(!u)return;
        u=abs(String(u).trim());
        if(!u)return;
        if(junk(u))return;
        try{if(u===location.href)return}catch(e){}
        var k=keyOf(u);
        if(Object.prototype.hasOwnProperty.call(seen,k))return;
        seen[k]=1;picked.push(u)
      }catch(e){}
    }
    function domPass(){
      var els=document.querySelectorAll('img');
      for(var i=0;i<els.length;i++){
        var el=els[i],ok=false,nw=0,nh=0;
        try{ok=!!el.complete&&el.naturalWidth>0;nw=el.naturalWidth||0;nh=el.naturalHeight||0}catch(e){}
        if(!ok)continue;
        if(nw&&nh&&Math.max(nw,nh)<300)continue;
        var u='';
        try{u=el.currentSrc||el.src||''}catch(e){}
        if(u)add(u)
      }
    }
    function resPass(){
      var rs=[];
      try{rs=performance.getEntriesByType('resource')}catch(e){}
      for(var i=0;i<rs.length;i++){
        var en=rs[i]||{};
        var t=String(en.initiatorType||'');
        if(t!=='img'&&t!=='css'&&t!=='link'&&t!=='other'&&t!=='svg'&&t!=='embed'&&t!=='fetch'&&t!=='xmlhttprequest')continue;
        var n=String(en.name||'');
        if(!n)continue;
        var b=n.split(/[?#]/)[0];
        var ext=/\\.(jpe?g|png|webp|avif|bmp|tiff?)$/i.test(b);
        if(!ext){
          if(t==='fetch'||t==='xmlhttprequest')continue;
          if(!/(^|\\/)(pages?|images?|img|media|manga|manhwa|webtoon|chapters?|episodes?|comic|uploads|wp-content|cdn)(\\/|[_\\-.]|$)/i.test(b))continue
        }
        add(n)
      }
    }
    var rsLen=0;
    try{rsLen=performance.getEntriesByType('resource').length}catch(e){}
    if(rsLen>=250){domPass();resPass()}
    else{resPass();domPass()}
    if(picked.length)return picked;
    var all=[],good=[],idx=0;
    var els=document.querySelectorAll('img,source');
    for(var i=0;i<els.length;i++){
      var el=els[i],cs=null;
      try{cs=el.currentSrc||el.src||null}catch(e){}
      var c=[cs,el.getAttribute('data-src'),el.getAttribute('data-lazy-src'),
             el.getAttribute('data-original'),el.getAttribute('data-original-src'),
             el.getAttribute('data-orig-src'),el.getAttribute('data-lazy'),
             el.getAttribute('data-url'),el.getAttribute('data-image'),
             el.getAttribute('data-echo')];
      var ss=el.getAttribute('srcset')||el.getAttribute('data-srcset');
      if(ss){var p=ss.split(','),best='',bw=0;
        for(var k=0;k<p.length;k++){
          var tk=p[k].trim().split(/\\s+/);
          var u0=tk[0]||'';
          var w0=parseInt(String(tk[1]||'').replace(/[^0-9]/g,''),10)||0;
          if(u0&&w0>=bw){bw=w0;best=u0}}
        if(best)c.push(best)}
      if(el.tagName==='SOURCE'&&el.parentNode){
        var pp=el.parentNode.querySelector('img');
        if(pp&&pp.src)c.push(pp.src)}
      var pick=null,pj=1;
      for(var j=0;j<c.length;j++){
        var u=c[j];if(!u)continue;
        u=abs(String(u).trim());
        if(!u||u.indexOf('data:')===0)continue;
        try{if(u===location.href)continue}catch(e2){}
        if(!pick)pick=u;
        if(!junk(u)){pick=u;pj=0;break}}
      if(!pick)continue;
      var w=el.naturalWidth||0,h=el.naturalHeight||0;
      if(w&&h&&Math.max(w,h)<300)continue;
      all.push([pick,idx]);
      if(!pj)good.push([pick,idx]);
      idx++}
    function dd(list){
      var by={},order=[];
      for(var i=0;i<list.length;i++){
        var it=list[i],k=keyOf(it[0]);
        if(Object.prototype.hasOwnProperty.call(by,k)){
          var o=by[k];
          if(qsz(it[0])>qsz(o[0]))by[k]=it}
        else{by[k]=it;order.push(k)}}
      var out=[];
      for(var j=0;j<order.length;j++)out.push(by[order[j]][0]);
      return out}
    var res=dd(good);
    if(!res.length)res=dd(all);
    return res;
  }
  css();
  var box=document.createElement('div');box.id='mtbw';
  var back=document.createElement('button');
  back.type='button';back.className='mtnav';
  back.textContent='\u2190';back.title='\u0639\u0642\u0628';
  back.onclick=function(){try{history.back()}catch(e){}};
  var fwd=document.createElement('button');
  fwd.type='button';fwd.className='mtnav';
  fwd.textContent='\u2192';fwd.title='\u062c\u0644\u0648';
  fwd.onclick=function(){try{history.forward()}catch(e){}};
  var url=document.createElement('input');url.type='text';
  url.className='mturl';
  url.placeholder='\u062c\u0633\u062a\u062c\u0648 \u06cc\u0627 \u0622\u062f\u0631\u0633 \u0633\u0627\u06cc\u062a\u2026';
  try{url.value=location.href}catch(e){}
  function isDomain(u){
    return !/\\s/.test(u)&&/^[A-Za-z0-9_-]+(\\.[A-Za-z0-9_-]+)+(:\\d+)?([\\/?#].*)?$/.test(u)
  }
  function go(){
    try{
      var u=String(url.value||'').trim();
      if(!u)return;
      if(!/^https?:/i.test(u)){
        if(isDomain(u))u='https://'+u;
        else u='https://www.google.com/search?q='+encodeURIComponent(u);
      }
      if(u===location.href)return;
      location.href=u;
    }catch(e){}
  }
  url.addEventListener('keydown',function(ev){
    if(ev.key==='Enter'||ev.keyCode===13){ev.preventDefault();go()}
  });
  var goBtn=document.createElement('button');
  goBtn.type='button';goBtn.className='mtgo';goBtn.textContent='\\u0628\\u0631\\u0648';
  goBtn.onclick=go;
  var cnt=document.createElement('span');cnt.className='mtcnt';cnt.textContent='\\u2026';
  function doLinks(){
    try{
      var out=collect();
      if(!out.length){
        alert('عکسی پیدا نشد — اول فصل را باز کن و تا آخرِ صفحه اسکرول کن تا عکس‌های تنبل لود بشن');
        return;
      }
      cnt.textContent=out.length+' عکس — در حالِ انتقال…';
      try{window.pywebview.api.onExtract(JSON.stringify(out));}
      catch(e){alert('خطا در ارسال به اپ: '+e)}
    }catch(e){alert('خطا در استخراج: '+e)}
  }
  function doDl(){
    try{
      var out=collect();
      if(!out.length){
        alert('عکسی پیدا نشد — اول فصل را باز کن و تا آخرِ صفحه اسکرول کن تا عکس‌های تنبل لود بشن');
        return;
      }
      cnt.textContent='\u2B07 0/'+out.length;
      var i=0;
      function step(){
        if(i>=out.length)return;
        var u=out[i];var idx=i;i++;
        try{
          fetch(u,{credentials:'include'}).then(function(r){
            if(!r.ok)return '';
            return r.blob()
          }).then(function(b){
            if(!b)return '';
            return new Promise(function(res){
              try{
                var f=new FileReader();
                f.onload=function(){res(String(f.result||''))};
                f.onerror=function(){res('')};
                f.readAsDataURL(b)
              }catch(e){res('')}
            })
          }).then(function(d){
            try{window.pywebview.api.onDlOne(idx,out.length,d||'')}catch(e){}
            cnt.textContent='\u2B07 '+(idx+1)+'/'+out.length;
            setTimeout(step,30)
          }).catch(function(){
            try{window.pywebview.api.onDlOne(idx,out.length,'')}catch(e){}
            cnt.textContent='\u2B07 '+(idx+1)+'/'+out.length;
            setTimeout(step,30)
          })
        }catch(e){setTimeout(step,30)}
      }
      step();
    }catch(e){alert('خطا در دانلود: '+e)}
  }
  var btn=document.createElement('button');
  btn.type='button';btn.textContent='🖼 استخراج';
  var menu=document.createElement('div');menu.className='mtmenu';
  var mi1=document.createElement('button');
  mi1.type='button';mi1.className='mtmi';
  mi1.textContent='استخراج با لینک';
  mi1.onclick=function(ev){
    ev.stopPropagation();closeMenu();doLinks()
  };
  var mi2=document.createElement('button');
  mi2.type='button';mi2.className='mtmi';
  mi2.textContent='استخراج با دانلود';
  mi2.onclick=function(ev){
    ev.stopPropagation();closeMenu();doDl()
  };
  menu.appendChild(mi2);menu.appendChild(mi1);
  function closeMenu(){
    try{if(menu.parentNode)menu.parentNode.removeChild(menu)}catch(e){}
  }
  function openMenu(){
    try{
      closeMenu();
      var r=btn.getBoundingClientRect();
      menu.style.top=(r.bottom+6)+'px';
      menu.style.right=Math.max(6,(window.innerWidth-r.right))+'px';
      (document.documentElement||document.body).appendChild(menu);
      setTimeout(function(){
        function off(e){
          try{if(!menu.contains(e.target))closeMenu()}catch(e2){}
          document.removeEventListener('mousedown',off,true)
        }
        document.addEventListener('mousedown',off,true)
      },0)
    }catch(e){}
  }
  btn.onclick=openMenu;
  box.appendChild(fwd);box.appendChild(back);box.appendChild(url);
  box.appendChild(goBtn);box.appendChild(btn);
  box.appendChild(cnt);
  function mount(){
    try{
      css();
      if(box.parentNode!==document.documentElement){
        try{if(box.parentNode)box.parentNode.removeChild(box)}catch(e){}
        document.documentElement.appendChild(box);
      }
    }catch(e){}
  }
  mount();setTimeout(mount,300);setTimeout(mount,900);setTimeout(mount,2500);
  try{
    var pend=0;
    var obs=new MutationObserver(function(ms){
      for(var i=0;i<ms.length;i++){
        var m=ms[i];
        if(!m.removedNodes||!m.removedNodes.length)continue;
        for(var j=0;j<m.removedNodes.length;j++){
          var n=m.removedNodes[j];
          if(n===box||n===st){
            if(!pend){pend=1;setTimeout(function(){pend=0;mount()},80)}
            return;
          }
        }
      }
    });
    obs.observe(document.documentElement||document,{childList:true,subtree:true});
  }catch(e){}
  setInterval(function(){
    mount();
    try{
      if(document.activeElement!==url&&url.value!==location.href)
        url.value=location.href;
    }catch(e){}
  },2000);
  function upd(){try{cnt.textContent=collect().length+' \\u0639\\u06a9\\u0633 \\u0622\\u0645\\u0627\\u062f\\u0647'}catch(e){}}
  setTimeout(upd,400);setTimeout(upd,1600);setInterval(upd,5000);
})();
"""


class _DesktopApi:

    def __init__(self):
        self._main_win = None
        self._br_win = None
        self._last_site = None

    def _br_target(self, raw):
        s = str(raw or "").strip()
        lines = [x.strip() for x in s.replace(",", "\n").splitlines()
                 if x.strip()]
        fallback = self._last_site or "https://www.google.com"
        if not lines:
            return fallback
        n_http = sum(1 for x in lines
                     if x.lower().startswith(("http://", "https://")))
        if n_http >= 2:
            return fallback
        u = lines[0]
        if n_http == 1:
            path = u.split("?", 1)[0].split("#", 1)[0]
            if re.search(r"\.(jpe?g|png|webp|gif|avif|bmp|tiff?)$",
                         path, re.I):
                return fallback
            return u
        if not re.search(r"\s", u) and re.match(
                r"^[A-Za-z0-9_-]+(\.[A-Za-z0-9_-]+)+(:\d+)?([/?#].*)?$",
                u):
            return "https://" + u
        return ("https://www.google.com/search?q="
                + urllib.parse.quote_plus(u))

    def openBrowser(self, raw):
        try:
            import webview
            u = self._br_target(raw)
            try:
                if self._br_win is not None:
                    self._br_win.destroy()
            except Exception:
                pass
            self._br_win = webview.create_window(
                "مرورگر داخلی — استخراج عکس مانهوا", u,
                width=1150, height=840, min_size=(760, 520),
                background_color="#060607", js_api=self)
            self._br_win.events.loaded += self._on_br_loaded
            self._br_win.events.closed += self._on_br_closed
        except Exception as e:
            print(f"[!] مرورگرِ داخلی باز نشد: {e}")

    def _on_br_closed(self):
        self._br_win = None

    def _on_br_loaded(self):
        try:
            if self._br_win is not None:
                try:
                    u = self._br_win.get_current_url()
                except Exception:
                    u = None
                if not u:
                    try:
                        u = self._br_win.evaluate_js("location.href")
                    except Exception:
                        u = None
                if u and str(u).lower().startswith(("http://", "https://")):
                    self._last_site = str(u)
                self._br_win.evaluate_js(_MT_BROWSER_WIN_JS)
        except Exception:
            pass

    def onExtract(self, payload):
        try:
            import json as _j
            links = None
            if isinstance(payload, str):
                s = payload.strip()
                if s.startswith("["):
                    try:
                        links = _j.loads(s)
                    except Exception:
                        links = [x for x in s.splitlines() if x.strip()]
                else:
                    links = [x for x in s.splitlines() if x.strip()]
            elif isinstance(payload, (list, tuple)):
                links = list(payload)
            text = "\n".join(str(x).strip() for x in (links or [])
                            if str(x).strip())
            if not text:
                return
            if self._main_win is not None:
                try:
                    _n = len([x for x in text.splitlines() if x.strip()])
                    self._main_win.evaluate_js(
                        "window.__mtFillLinks && (window.__mtFillLinks(%s),"
                        " alert('%d لینک عکس در فیلدِ ورودی نشست — "
                        "«شروع ترجمه» را بزن'));" % (_j.dumps(text), _n))
                except Exception as e:
                    print(f"[!] پرکردنِ فیلدِ لینک ناموفق: {e}")
            try:
                if self._br_win is not None:
                    self._br_win.destroy()
            except Exception:
                pass
            self._br_win = None
        except Exception as e:
            print(f"[!] استخراجِ مرورگرِ داخلی: خطا — {e}")

    def onDlOne(self, idx, total, data_url):
        try:
            import base64 as _b64
            import json as _j
            idx = int(idx or 0)
            total = int(total or 0)
            if idx <= 0:
                try:
                    shutil.rmtree(os.path.join(WORK_DIR, "browser_dl"),
                                  ignore_errors=True)
                except Exception:
                    pass
            s = str(data_url or "").strip()
            if not s.lower().startswith("data:image/"):
                return
            head, _, b64 = s.partition(",")
            try:
                content = _b64.b64decode(b64)
            except Exception:
                return
            if not content:
                return
            ext = ".jpg"
            m = re.search(r"data:image/(jpe?g|png|webp|bmp)", head.lower())
            if m:
                ext = "." + ("jpg" if m.group(1) in ("jpg", "jpeg")
                             else m.group(1))
            d = os.path.join(WORK_DIR, "browser_dl")
            os.makedirs(d, exist_ok=True)
            fp = os.path.join(d, "page_%03d%s" % (idx + 1, ext))
            with open(fp, "wb") as f:
                f.write(content)
            if total > 0 and idx >= total - 1:
                try:
                    files = sorted(
                        os.path.join(d, x) for x in os.listdir(d)
                        if os.path.isfile(os.path.join(d, x)))
                except Exception:
                    files = []
                if files and self._main_win is not None:
                    text = "\n".join(files)
                    try:
                        self._main_win.evaluate_js(
                            "window.__mtFillLinks && (window.__mtFillLinks(%s),"
                            " alert('%d عکس دانلود شد و مسیرشان در فیلدِ"
                            " ورودی نشست — «شروع ترجمه» را بزن'));"
                            % (_j.dumps(text), len(files)))
                    except Exception as e:
                        print(f"[!] پرکردنِ فیلدِ دانلود ناموفق: {e}")
                elif not files and self._main_win is not None:
                    try:
                        self._main_win.evaluate_js(
                            "alert('هیچ عکسی دانلود نشد');")
                    except Exception:
                        pass
                try:
                    if self._br_win is not None:
                        self._br_win.destroy()
                except Exception:
                    pass
                self._br_win = None
        except Exception as e:
            print(f"[!] دانلودِ مرورگرِ داخلی: خطا — {e}")


def run_desktop():
    import socket
    import time as _t
    import webbrowser

    _no_proxy_localhost()

    port = int(os.environ.get("MANGA_APP_PORT", "7860") or 7860)
    url = f"http://127.0.0.1:{port}/?desktop=1"

    def _up() -> bool:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except Exception:
            return False

    proc = None
    if not _up():
        print("[*] راه‌اندازی سرور رابط وب ...")
        proc = subprocess.Popen([sys.executable, os.path.abspath(__file__), "--web"])
        for _ in range(300):
            if _up():
                break
            _t.sleep(0.2)
            if proc.poll() is not None:
                break
        if not _up():
            print("[!] سرور وب بالا نیامد")
            try:
                proc.terminate()
            except Exception:
                pass
            sys.exit(1)
    print(f"[i] رابط وب آماده: {url}")

    opened_browser = False
    if not _ensure_webview():
        webbrowser.open(url)
        opened_browser = True
    else:
        try:
            import webview
            _store = os.path.join(WORK_DIR, "webview_profile")
            try:
                os.makedirs(_store, exist_ok=True)
            except Exception:
                _store = None
            _start_kw = {"private_mode": False}
            if _store:
                _start_kw["storage_path"] = _store
            _api = _DesktopApi()
            _api._main_win = webview.create_window(
                f"{APP_NAME} v{APP_VER}", url,
                width=1280, height=880,
                min_size=(980, 640),
                background_color="#060607",
                js_api=_api)
            print("[i] پنجرهٔ دسکتاپ (همان رابط وب) باز شد — با بستن پنجره، برنامه تمام می‌شود")
            webview.start(**_start_kw)
        except Exception as e:
            print(f"[!] پنجرهٔ وب‌ویو ناموفق ({e}) → مرورگر")
            webbrowser.open(url)
            opened_browser = True

    if opened_browser:
        try:
            if proc is not None:
                proc.wait()
            else:
                while True:
                    _t.sleep(3600)
        except KeyboardInterrupt:
            pass
    else:
        try:
            if proc is not None:
                proc.terminate()
        except Exception:
            pass
    sys.exit(0)

WEB_CSS = """
@font-face{font-family:'Vazirmatn';font-style:normal;font-weight:400;
  src:url('__FONTPFX__/Vazirmatn-Regular.ttf') format('truetype');
  font-display:swap}
@font-face{font-family:'Vazirmatn';font-style:normal;font-weight:700;
  src:url('__FONTPFX__/Vazirmatn-Bold.ttf') format('truetype');
  font-display:swap}

:root, .gradio-container {
  --ink-bg: #060607;
  --ink-surface: #0d0d10;
  --ink-surface2: #121216;
  --ink-line: #1f1f24;
  --ink-text: #e8e6e1;
  --ink-dim: #97948c;
  --ink-red: #ff4a3d;
  --ink-red-deep: #c9271c;
}
body, .gradio-container, footer, .gradio-container .prose {
  background: var(--ink-bg) !important; color: var(--ink-text) !important;
  font-family: 'Vazirmatn', 'Segoe UI', Tahoma, system-ui, sans-serif !important;
}
.gradio-container {
  background:
    radial-gradient(ellipse 120% 70% at 50% -10%, rgba(255,74,61,.06), transparent 60%),
    radial-gradient(rgba(232,230,225,.028) 1px, transparent 1.4px) 0 0 / 14px 14px,
    #060607 !important;
}
.gradio-container { max-width: 880px !important; margin: 0 auto !important; }

.nav {
  display: flex; align-items: center; justify-content: space-between;
  flex-wrap: wrap; gap: 10px 16px;
  background: linear-gradient(180deg, #101014, #0a0a0c);
  border: 1px solid var(--ink-line);
  border-radius: 18px; padding: 20px 24px; margin: 6px 0 18px 0;
  box-shadow: 0 18px 40px rgba(0,0,0,.55), inset 0 1px 0 rgba(255,255,255,.05);
  position: relative; overflow: hidden;
  animation: rise .55s cubic-bezier(.2,.7,.2,1) both;
}
.nav::after {
  content: ''; position: absolute; inset: 0; pointer-events: none;
  background: radial-gradient(rgba(232,230,225,.03) 1px, transparent 1.4px) 0 0 / 10px 10px;
}
.nav-left { display: flex; align-items: center; gap: 14px; flex: 1 1 auto; min-width: 230px; }
.stamp {
  width: 52px; height: 52px; flex: none;
  background: linear-gradient(145deg, var(--ink-red), var(--ink-red-deep));
  border-radius: 10px; transform: rotate(-4deg);
  display: flex; align-items: center; justify-content: center;
  font-size: 1.7rem; font-weight: 900; color: #fff;
  box-shadow: 0 6px 18px rgba(224,53,42,.4), inset 0 0 0 2px rgba(255,255,255,.22);
  font-family: serif;
}
.nav-brand { color: var(--ink-text); font-size: 1.3rem; font-weight: 700; line-height: 1.25; white-space: nowrap; }
.nav-brand b { color: var(--ink-red); font-weight: 900; }
.nav-sub { display: block; color: var(--ink-dim); font-size: .74rem; font-weight: 400; letter-spacing: .04em; }
.nav-chips { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
.chip {
  font-family: ui-monospace, 'Cascadia Mono', Consolas, monospace; font-size: .7rem;
  background: var(--ink-surface2); border: 1px solid var(--ink-line);
  color: var(--ink-dim); padding: 4px 11px; border-radius: 999px;
  display: inline-flex; align-items: center; gap: 6px;
}
.chip::before { content: ''; width: 5px; height: 5px; border-radius: 50%;
  background: var(--ink-red); box-shadow: 0 0 6px var(--ink-red); }

.stepcard {
  background: linear-gradient(180deg, var(--ink-surface), #0a0a0c) !important;
  border: 1px solid var(--ink-line) !important;
  border-radius: 18px !important; padding: 20px 22px 18px; margin-bottom: 16px;
  box-shadow: 0 10px 28px rgba(0,0,0,.4);
  position: relative;
  animation: rise .55s cubic-bezier(.2,.7,.2,1) both;
}
.stepcard:nth-of-type(1) { animation-delay: .06s; }
.stepcard:nth-of-type(2) { animation-delay: .14s; }
.stepcard:nth-of-type(3) { animation-delay: .22s; }
.stepcard:nth-of-type(4) { animation-delay: .3s; }
@keyframes rise {
  from { opacity: 0; transform: translateY(14px); }
  to   { opacity: 1; transform: none; }
}
.steptitle {
  display: flex; align-items: center; gap: 12px;
  color: var(--ink-text); font-weight: 700; font-size: 1.08rem; margin-bottom: 14px;
  padding-bottom: 10px; border-bottom: 1px solid var(--ink-line);
}
.stepnum {
  background: linear-gradient(145deg, var(--ink-red), var(--ink-red-deep));
  color: #fff; width: 30px; height: 30px; border-radius: 8px;
  transform: rotate(-3deg);
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 1rem; font-weight: 900; flex: none;
  box-shadow: 0 4px 12px rgba(224,53,42,.35), inset 0 0 0 1.5px rgba(255,255,255,.2);
}
.hint { color: var(--ink-dim) !important; font-size: .83rem; margin-top: 8px; }
.hint, .hint *, #manga_cm_info, #manga_cm_info * {
  overflow-wrap: anywhere !important;
  word-break: break-word !important;
  max-width: 100% !important;
}
#manga_cm_info code, .hint code { white-space: normal !important; }

#manga_out_fmt fieldset > div,
#manga_out_fmt .wrap {
  display: grid !important;
  grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
  gap: 6px 10px !important;
  align-items: center;
}
#manga_out_fmt .wrap label {
  margin: 0 !important; padding: 5px 4px !important;
  min-height: 38px; justify-content: flex-start !important;
}

#manga_mode_grid {
  display: grid !important;
  grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
  gap: 8px 6px !important;
  align-items: stretch;
  margin: 2px 0 10px 0;
}
#manga_mode_grid > .form {
  grid-column: 1 / -1;
  display: grid !important;
  grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
  gap: 8px 6px !important;
  align-items: stretch;
}
#manga_mode_grid > * { min-width: 0 !important; }
#manga_mode_grid > .form > * { min-width: 0 !important; }
#manga_mode_grid .block { padding: 3px 5px !important; margin: 0 !important; }
#manga_mode_grid label {
  display: flex !important;
  align-items: center !important;
  gap: 6px !important;
  padding: 4px 1px !important;
  margin: 0 !important;
  min-width: 0 !important;
}
#manga_mode_grid label > span,
#manga_mode_grid .label-text {
  flex: 1 1 auto !important;
  min-width: 0 !important;
  overflow-wrap: break-word !important;
  white-space: normal !important;
  line-height: 1.6 !important;
}
#manga_mode_grid label > button.k3q {
  margin: 0 !important;
  width: 15px !important;
  height: 15px !important;
  font-size: 9px !important;
}
@media (max-width: 640px) {
  #manga_mode_grid label {
    display: grid !important;
    grid-template-columns: auto minmax(0, 1fr);
    align-items: center !important;
    column-gap: 5px !important;
    row-gap: 4px !important;
    padding: 6px 2px 5px !important;
  }
  #manga_mode_grid label > input[type="checkbox"] { grid-column: 1; grid-row: 1; }
  #manga_mode_grid label > button.k3q { grid-column: 2; grid-row: 1; justify-self: end; }
  #manga_mode_grid label > span,
  #manga_mode_grid .label-text {
    grid-column: 1 / -1;
    grid-row: 2;
    flex: none !important;
    font-size: .78rem !important;
    text-align: right;
  }
}
button.k3q {
  display: inline-flex; align-items: center; justify-content: center;
  width: 17px; height: 17px; border-radius: 50%;
  border: 1px solid var(--ink-line); background: var(--ink-surface2);
  color: var(--ink-dim); font-size: 10px; font-weight: 800; line-height: 1;
  cursor: pointer; padding: 0; margin: 0 5px; flex: none;
  vertical-align: middle; font-family: inherit; user-select: none;
}
button.k3q:hover { color: var(--ink-text); border-color: var(--ink-red); }
button.k3q:active { transform: scale(.9); }
div.k3tip {
  position: fixed; z-index: 99999;
  background: #15151b; border: 1px solid var(--ink-line);
  color: var(--ink-text); font-size: .8rem; line-height: 1.8;
  padding: 10px 14px; border-radius: 12px;
  box-shadow: 0 14px 34px rgba(0,0,0,.65);
  max-width: min(320px, 86vw);
  direction: rtl; text-align: right; white-space: normal;
  animation: rise .25s cubic-bezier(.2,.7,.2,1) both;
}

div.styler{background:transparent !important;border:none !important;
  box-shadow:none !important}
#manga_cm_del_btn{max-width:30px !important;min-width:30px !important;
  width:30px !important;height:30px !important;min-height:30px !important;
  max-height:30px !important;
  flex:none !important;align-self:flex-end !important;
  background:transparent !important;border:1px solid rgba(255,90,90,.4) !important;
  border-radius:999px !important;color:#ff7b7b !important;font-size:.8rem !important;
  line-height:1 !important;padding:0 !important;margin:0 0 16px 0 !important;
  transition:all .15s ease}
#manga_cm_del_btn:hover{background:rgba(255,70,70,.18) !important;color:#ff4d4d !important}
#manga_cm_del_btn:active{transform:scale(.94)}
#manga_provider_row{flex-wrap:nowrap !important}
#manga_provider_row > *{min-width:0 !important}
#manga_token_btn{max-width:30px !important;min-width:30px !important;
  width:30px !important;height:30px !important;min-height:30px !important;
  max-height:30px !important;
  flex:none !important;align-self:flex-end !important;
  background:transparent !important;border:1px solid rgba(255,210,138,.4) !important;
  border-radius:999px !important;color:#ffd28a !important;font-size:.95rem !important;
  line-height:1 !important;padding:0 !important;margin:0 0 16px 0 !important;
  transition:all .15s ease}
#manga_token_btn:hover{background:rgba(255,210,138,.14) !important;color:#ffd28a !important}
#manga_token_btn:active{transform:scale(.94)}
#manga_api_keys .wrap, #manga_api_keys .input-container{position:relative !important}
#manga_api_keys input{padding-inline-start:44px !important}
.manga-eye{position:absolute !important;top:50% !important;
  inset-inline-start:6px !important;transform:translateY(-50%) !important;
  width:32px !important;min-width:32px !important;max-width:32px !important;
  height:32px !important;min-height:32px !important;max-height:32px !important;
  border-radius:9px !important;background:rgba(255,255,255,.04) !important;
  border:1px solid rgba(255,255,255,.14) !important;color:#b9b6ad !important;
  font-size:1rem !important;line-height:1 !important;padding:0 !important;
  cursor:pointer !important;z-index:6;transition:all .15s ease;
  box-shadow:none !important;margin:0 !important;flex:none !important}
.manga-eye.on{color:#ffd28a !important;border-color:rgba(255,210,138,.45) !important}
.manga-eye:active{transform:translateY(-50%) scale(.93)}
.manga-hide-channel{display:none !important;visibility:hidden !important;
  height:0 !important;min-height:0 !important;margin:0 !important;
  padding:0 !important;border:0 !important;overflow:hidden !important}

.livehint { color: var(--ink-dim) !important; font-size: .8rem; margin-top: 8px; text-align: center; }

label, span, .prose, p, li { color: var(--ink-dim) !important; }
span:not(.stepnum):not(.chip) {
  background: transparent !important;
  background-image: none !important;
  box-shadow: none !important;
}
label span, label > span:first-child {
  background: transparent !important;
  background-image: none !important;
  color: var(--ink-dim) !important;
  box-shadow: none !important;
  font-size: .85rem; font-weight: 500;
}
input[type=text], input[type=password], textarea, select {
  background: #08080a !important; color: var(--ink-text) !important;
  border-color: var(--ink-line) !important;
}
.block, .form, .gr-box, .gr-panel, .gr-group, .gr-form,
.gradio-group, .wrap.full, .container > .wrap {
  background: var(--ink-surface) !important; border-color: var(--ink-line) !important;
}
.gr-box input, .gr-box textarea, .gr-input, .gr-textbox {
  background: #08080a !important; color: var(--ink-text) !important;
}
.options, .options ul, ul.options, .dropdown-menu, .wrap .options {
  background: #101014 !important; border-color: var(--ink-line) !important;
}
.options li, .options li:hover { background: #101014 !important; color: var(--ink-text) !important; }
.options li.selected, .options li:hover { background: #1a1114 !important; }
accordion, .accordion, details {
  background: var(--ink-surface) !important; border-color: var(--ink-line) !important; color: var(--ink-dim) !important;
}
summary { color: var(--ink-dim) !important; }
input[type=range], input[type=radio], input[type=checkbox] { accent-color: var(--ink-red) !important; }
input[type=radio], input[type=checkbox] {
  appearance: auto !important;
  background-image: none !important;
  background-color: transparent !important;
  border: none !important;
  width: 16px; height: 16px; margin: 0 2px;
  cursor: pointer;
}
input[type=range] {
  appearance: none !important;
  -webkit-appearance: none !important;
  height: 6px !important; border-radius: 4px !important;
  background: linear-gradient(to right, var(--ink-red) var(--range_progress, 50%),
              #1f1f24 var(--range_progress, 50%)) !important;
  border: none !important;
  cursor: pointer;
}
input[type=range]::-webkit-slider-runnable-track {
  background: linear-gradient(to right, var(--ink-red) var(--range_progress, 50%),
              #1f1f24 var(--range_progress, 50%)) !important;
  height: 6px !important; border-radius: 4px !important; border: none !important;
}
input[type=range]::-moz-range-track {
  background: linear-gradient(to right, var(--ink-red) var(--range_progress, 50%),
              #1f1f24 var(--range_progress, 50%)) !important;
  height: 6px !important; border-radius: 4px !important; border: none !important;
}
input[type=range]::-webkit-slider-thumb {
  -webkit-appearance: none !important; appearance: none !important;
  width: 17px; height: 17px; border-radius: 50%;
  background: var(--ink-red); border: 2.5px solid #fff;
  box-shadow: 0 2px 10px rgba(255, 74, 61, .55);
}
input[type=number], .gr-box input[type=number] {
  background: #08080a !important; color: var(--ink-text) !important;
  border-color: var(--ink-line) !important;
}
.gr-checkbox, .gr-radio, .wrap label { background: transparent !important; }

button.primary, .lg.primary, #runbtn {
  background: linear-gradient(160deg, var(--ink-red), var(--ink-red-deep)) !important;
  color: #fff !important; border: none !important;
  font-weight: 700 !important; letter-spacing: .02em;
  box-shadow: 0 8px 22px rgba(224,53,42,.35), inset 0 1px 0 rgba(255,255,255,.25) !important;
  transition: transform .12s ease, box-shadow .12s ease, filter .12s ease;
}
button.primary:hover, #runbtn:hover { filter: brightness(1.08); transform: translateY(-1px); }
button.primary:active, #runbtn:active { transform: translateY(1px) scale(.99); }
button.secondary, .lg.secondary, button.gr-button {
  background: var(--ink-surface2) !important; color: var(--ink-text) !important;
  border: 1px solid var(--ink-line) !important;
}
button.gr-button:hover { background: #17171c !important; border-color: #2c2c33 !important; }
#runbtn {
  font-size: 1.12rem !important; padding: 15px 0 !important;
  border-radius: 14px !important; margin: 8px 0 12px 0; position: relative; overflow: hidden;
}
#runbtn::after {
  content: ''; position: absolute; inset: 0;
  background: radial-gradient(rgba(255,255,255,.14) 1px, transparent 1.4px) 0 0 / 9px 9px;
  opacity: 0; transition: opacity .18s ease; pointer-events: none;
}
#runbtn:hover::after { opacity: 1; }

textarea { scrollbar-color: var(--ink-line) #08080a !important; }
.compact-upload .empty, .compact-upload button {
  min-height: 48px !important; height: auto !important;
  padding: 6px 8px !important; font-size: .85rem !important;
  background: #08080a !important; color: var(--ink-dim) !important;
  border-color: var(--ink-line) !important;
}
.compact-upload .wrap.center, .compact-upload .wrap {
  padding: 6px 0 !important; min-height: 48px !important;
  background: transparent !important;
}
.compact-upload .empty .icon-wrap { display: none !important; }
.compact-upload label { position: static !important; margin: 4px 0 !important; }

#manga_ocr_lang .wrap { padding: 2px 0 !important; background: transparent !important; gap: 4px 16px !important; flex-wrap: wrap !important; }
#manga_ocr_lang label { margin: 0 !important; flex: 0 0 calc(50% - 10px) !important; }
#manga_ocr_lang .wrap > label:nth-child(1), #manga_ocr_lang .wrap > label:nth-child(2) { padding-top: 2px !important; }

footer { display: none !important; }

#manga_live_log,
#manga_live_log textarea,
#manga_live_log.generating,
.generating #manga_live_log textarea {
  opacity: 1 !important;
  filter: none !important;
  transition: none !important;
  animation: none !important;
  color: #e8e6e1 !important;
  background: #08080a !important;
  min-height: 220px !important;
  display: block !important;
  visibility: visible !important;
}
#manga_live_log textarea {
  -webkit-text-fill-color: #e8e6e1 !important;
}

.credit {
  display: flex; gap: 12px; justify-content: center; align-items: center;
  padding: 6px 0 22px; flex-wrap: wrap;
}
.credit img.gh-avatar {
  width: 22px; height: 22px; border-radius: 50%;
  object-fit: cover; flex: none;
  border: 1.5px solid var(--ink-line);
}
.credit a {
  display: inline-flex; align-items: center; gap: 7px;
  color: var(--ink-dim) !important; text-decoration: none !important;
  font-size: 13px; border: 1px solid var(--ink-line);
  padding: 7px 16px; border-radius: 999px; background: #0a0a0d;
  transition: border-color .2s, color .2s, transform .2s;
}
.credit a:hover { color: var(--ink-red) !important; border-color: var(--ink-red);
                  transform: translateY(-1px); }
.credit svg { width: 15px; height: 15px; fill: currentColor; flex: none; }
.credit-reset {
  display: inline-flex; align-items: center; gap: 7px;
  color: var(--ink-dim) !important; font-size: 13px !important;
  border: 1px solid var(--ink-line) !important;
  padding: 7px 16px !important; border-radius: 999px !important;
  background: #0a0a0d !important;
  cursor: pointer; font-family: inherit; min-height: 38px !important;
  line-height: 1.25 !important;
  transition: border-color .2s, color .2s, transform .2s;
}
.credit-reset:hover { color: var(--ink-red) !important; border-color: var(--ink-red) !important;
                      transform: translateY(-1px); }
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: #060607; }
::-webkit-scrollbar-thumb { background: #232329; border-radius: 6px; }
::-webkit-scrollbar-thumb:hover { background: var(--ink-red-deep); }
::selection { background: var(--ink-red); color: #fff; }
@media (prefers-reduced-motion: reduce) {
  .nav, .stepcard { animation: none; }
}

#manga_test_key {
  background: linear-gradient(160deg, #16161a, #050506) !important;
  color: #fff !important;
  border: none !important;
  border-radius: 14px !important;
  font-weight: 800 !important;
  font-size: 1rem !important;
  padding: 14px 18px !important;
  min-height: 52px !important;
  box-shadow: 0 8px 22px rgba(0,0,0,.45), inset 0 0 0 1.5px rgba(255,255,255,.16) !important;
  transition: filter .18s ease, transform .18s ease !important;
}
#manga_test_key:hover { filter: brightness(1.35); transform: translateY(-1px); }
#manga_test_key:active { transform: translateY(0); filter: brightness(.9); }
#manga_test_key span, #manga_test_key div { color: #fff !important; }

#manga_test_key_out textarea {
  background: #08080a !important;
  color: #d9d9e0 !important;
  font-family: 'IBM Plex Mono', monospace !important;
  font-size: .88rem !important;
  border: 1px solid rgba(255,255,255,.14) !important;
  border-radius: 12px !important;
  direction: rtl !important;
}

#manga_status_chip {
  display: none; align-items: center; gap: 9px; flex-wrap: wrap;
  margin: 2px 0 10px; padding: 9px 16px;
  background: linear-gradient(180deg, #101014, #0a0a0c);
  border: 1px solid var(--ink-line); border-radius: 999px;
  width: fit-content; max-width: 100%;
  color: var(--ink-text); font-size: .85rem; line-height: 1;
  box-shadow: 0 4px 14px rgba(0,0,0,.4);
  animation: rise .35s ease both;
}
#manga_status_chip b { color: var(--ink-text); font-weight: 700; }
#manga_status_chip span { background: transparent !important; box-shadow: none !important; }
.chip-sep { color: var(--ink-dim) !important; opacity: .55; }
.chip-dot {
  width: 9px; height: 9px; border-radius: 50%; flex: none;
}
.chip-dot.run  { background: #ffb02e; box-shadow: 0 0 8px #ffb02e; animation: chipPulse 1.15s ease-in-out infinite; }
.chip-dot.ok   { background: #38c98a; box-shadow: 0 0 8px #38c98a; }
.chip-dot.err  { background: var(--ink-red); box-shadow: 0 0 8px var(--ink-red); }
.chip-dot.idle { background: var(--ink-dim); }
@keyframes chipPulse { 50% { opacity: .3; } }

#manga_prog_row .mprog {
  display: flex; align-items: center; gap: 14px; flex-wrap: wrap;
  margin: 10px 0 2px; padding: 11px 16px;
  background: linear-gradient(180deg, #101014, #0a0a0c);
  border: 1px solid var(--ink-line); border-radius: 14px;
  box-shadow: 0 4px 14px rgba(0,0,0,.4);
  animation: rise .35s ease both;
}
#manga_prog_row .mprog-track {
  flex: 1 1 170px; height: 10px; border-radius: 999px;
  background: #17171b; overflow: hidden; direction: ltr;
}
#manga_prog_row .mprog-fill {
  height: 100%; border-radius: 999px; min-width: 0;
  background: linear-gradient(90deg, var(--ink-red), #ff8a5e);
  transition: width .6s ease;
}
#manga_prog_row .mprog-fill.done { background: linear-gradient(90deg, #2e7d4f, #38c98a); }
#manga_prog_row .mprog-fill.err  { background: linear-gradient(90deg, #a3271e, #ff6a5e); }
#manga_prog_row .mprog-txt {
  color: var(--ink-text); font-size: .85rem; font-weight: 600;
  white-space: nowrap; line-height: 1.2;
  font-variant-numeric: tabular-nums;
}

.log-tools { display: flex; gap: 8px; margin: 0 0 10px; flex-wrap: wrap; }
.log-tool-btn {
  background: #121216 !important; color: var(--ink-dim) !important;
  border: 1px solid var(--ink-line) !important; border-radius: 999px !important;
  padding: 4px 11px !important; font-size: .72rem !important; cursor: pointer;
  font-family: inherit; min-height: 28px !important; line-height: 1.25 !important;
  transition: color .18s, border-color .18s, transform .18s;
}
.log-tool-btn:hover { color: var(--ink-red) !important; border-color: var(--ink-red) !important; transform: translateY(-1px); }
.log-tool-btn:active { transform: translateY(0); }

.support {
  max-width: 620px; margin: 2px auto 4px; text-align: center;
}
.support-toggle {
  display: inline-flex; align-items: center; gap: 8px;
  color: var(--ink-dim) !important; text-decoration: none !important;
  font-size: 13px !important; font-weight: 600;
  border: 1px solid var(--ink-line) !important;
  padding: 8px 20px !important; border-radius: 999px !important;
  background: #0a0a0d !important;
  cursor: pointer; font-family: inherit; min-height: 38px !important;
  line-height: 1.25 !important;
  transition: border-color .2s, color .2s, transform .2s;
}
.support-toggle:hover {
  color: var(--ink-red) !important; border-color: var(--ink-red) !important;
  transform: translateY(-1px);
}
.support-toggle svg {
  width: 15px; height: 15px; fill: currentColor; flex: none;
  transition: transform .22s;
}
.support.open .support-toggle svg { transform: rotate(180deg); }
.support-kao { font-size: 1.05rem; font-weight: 400; }
.support-body {
  display: none; border: 1px solid var(--ink-line);
  border-radius: 16px; background: #0a0a0d;
  padding: 14px 16px 12px; margin-top: 10px;
}
.support.open .support-body { display: block; }
.support-row {
  display: flex; align-items: center; justify-content: center;
  gap: 8px; flex-wrap: wrap; margin: 7px 0;
}
.support-net {
  font-size: .72rem; font-weight: 800; color: #fff; letter-spacing: .6px;
  border-radius: 8px; padding: 5px 11px; flex: none;
  background: linear-gradient(135deg, #0098ea, #41c7e8);
}
.support-row.trx .support-net { background: linear-gradient(135deg, #e84142, #ff7a4d); }
.support-addr {
  direction: ltr; unicode-bidi: embed;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: .78rem; color: var(--ink-text); background: #121216;
  border: 1px solid var(--ink-line); border-radius: 10px;
  padding: 7px 12px; word-break: break-all; line-height: 1.5;
  user-select: all; cursor: pointer; max-width: 100%;
  transition: border-color .18s;
}
.support-row.ton .support-addr:hover { border-color: #0098ea; }
.support-row.trx .support-addr:hover { border-color: #e84142; }
.support-copy {
  background: #121216 !important; color: var(--ink-dim) !important;
  border: 1px solid var(--ink-line) !important; border-radius: 10px !important;
  padding: 6px 13px !important; font-size: .74rem !important; cursor: pointer;
  font-family: inherit; min-height: 32px !important; flex: none;
  line-height: 1.25 !important;
  transition: color .18s, border-color .18s, transform .18s;
}
.support-copy:hover, .support-copy.ok {
  color: #38c98a !important; border-color: #2e7d4f !important; transform: translateY(-1px);
}

@media (max-width: 620px) {
  .gradio-container { max-width: 100% !important; }
  .stepcard { padding: 14px 12px 12px !important; border-radius: 14px !important; }
  .nav { padding: 14px 12px !important; }
  .nav-brand { font-size: 1.12rem !important; white-space: normal !important; }
  #runbtn, #manga_test_key { min-height: 56px !important; font-size: 1.04rem !important; }
  .stepcard button:not(.log-tool-btn):not(.credit-reset):not(.support-copy):not(.support-toggle) { min-height: 44px !important; }
  #manga_live_log textarea { font-size: 10.5px !important; max-height: 34vh !important; }
  #manga_status_chip { font-size: .78rem; padding: 8px 13px; }
  .credit { gap: 8px; }
  .credit a { padding: 8px 13px; }
  .credit-reset { padding: 8px 13px; }
  .support { padding: 0; }
  .support-body { padding: 12px 10px 10px; }
  .support-row { gap: 6px; }
  .support-addr { font-size: .7rem; padding: 6px 9px; }
}
"""

def _detect_codespace() -> bool:
    if os.environ.get("CODESPACE_NAME"):
        return True
    if os.environ.get("MANGA_SHARE", "").strip() in ("1", "true", "yes"):
        return True
    try:
        import socket
        if socket.gethostname().startswith("codespaces-"):
            return True
    except Exception:
        pass
    try:
        with open("/etc/environment", encoding="utf-8") as f:
            if "CODESPACE_NAME=" in f.read():
                return True
    except Exception:
        pass
    return False

def _hostname_codespace_name() -> str:
    try:
        import socket
        host = socket.gethostname()
        if host.startswith("codespaces-"):
            return host
    except Exception:
        pass
    return ""

def _safe(cls, *args, **kw):
    while True:
        try:
            return cls(*args, **kw)
        except TypeError as e:
            mobj = re.search(r"unexpected keyword argument '(\w+)'", str(e))
            if not mobj or mobj.group(1) not in kw:
                raise
            kw.pop(mobj.group(1))

def _gradio_major() -> int:
    try:
        import gradio
        return int(gradio.__version__.split(".")[0])
    except Exception:
        return 0


_MT_BM_CODE = (
    "(function(){"
    "var seen={},picked=[];"
    "function abs(u){try{var a=document.createElement('a');a.href=u;"
    "return a.href}catch(e){return null}}"
    "function qsz(u){"
    "var m=String(u).match(/[?&](?:type|size|w|h|width|height)=(f?)(\\d{1,4})(?:[_x](\\d{1,4}))?/i);"
    "if(!m)return 0;"
    "var a=parseInt(m[2],10)||0;"
    "var b=parseInt(m[3]||'0',10)||0;"
    "if(a>0&&b>0)return Math.max(a,b);"
    "if(m[1]&&a>0)return a;"
    "return 0}"
    "function junk(u){"
    "if(!u)return 1;"
    "if(u.indexOf('data:')===0)return 1;"
    "if(u.indexOf('blob:')===0)return 1;"
    "if(!/^https?:/i.test(u))return 1;"
    "var b=String(u).split(/[?#]/)[0];"
    "if(/\\.(svg|ico|gif)$/i.test(b))return 1;"
    "if(/[-_]\\d{2,4}x\\d{2,4}\\.(jpe?g|png|webp)$/i.test(b))return 1;"
    "var q=qsz(u);"
    "if(q>0&&q<=400)return 1;"
    "if(/(logo|icon|avatar|banner|sprite|favicon|badge|flag|button|emoji|thumb(nail)?s?|placeholder|blank|spacer|transparen|loading|spinner|pixel|profile|rating|share|follow|comment|credits)/i.test(b))return 1;"
    "if(/(?:^|[^a-z0-9])ads?[._\\/-]/i.test(b))return 1;"
    "return 0}"
    "function keyOf(u){"
    "var b=String(u).split(/[?#]/)[0];"
    "return b.replace(/[-_]\\d{2,4}x\\d{2,4}\\./i,'.')}"
    "function add(u){"
    "try{"
    "if(!u)return;"
    "u=abs(String(u).trim());"
    "if(!u)return;"
    "if(junk(u))return;"
    "try{if(u===location.href)return}catch(e){}"
    "var k=keyOf(u);"
    "if(Object.prototype.hasOwnProperty.call(seen,k))return;"
    "seen[k]=1;picked.push(u)"
    "}catch(e){}}"
    "function domPass(){"
    "var els=document.querySelectorAll('img');"
    "for(var i=0;i<els.length;i++){"
    "var el=els[i],ok=false,nw=0,nh=0;"
    "try{ok=!!el.complete&&el.naturalWidth>0;nw=el.naturalWidth||0;nh=el.naturalHeight||0}catch(e){}"
    "if(!ok)continue;"
    "if(nw&&nh&&Math.max(nw,nh)<300)continue;"
    "var u='';"
    "try{u=el.currentSrc||el.src||''}catch(e){}"
    "if(u)add(u)"
    "}"
    "}"
    "function resPass(){"
    "var rs=[];"
    "try{rs=performance.getEntriesByType('resource')}catch(e){}"
    "for(var i=0;i<rs.length;i++){"
    "var en=rs[i]||{};"
    "var t=String(en.initiatorType||'');"
    "if(t!=='img'&&t!=='css'&&t!=='link'&&t!=='other'&&t!=='svg'&&t!=='embed'&&t!=='fetch'&&t!=='xmlhttprequest')continue;"
    "var n=String(en.name||'');"
    "if(!n)continue;"
    "var b=n.split(/[?#]/)[0];"
    "var ext=/\\.(jpe?g|png|webp|avif|bmp|tiff?)$/i.test(b);"
    "if(!ext){"
    "if(t==='fetch'||t==='xmlhttprequest')continue;"
    "if(!/(^|\\/)(pages?|images?|img|media|manga|manhwa|webtoon|chapters?|episodes?|comic|uploads|wp-content|cdn)(\\/|[_\\-.]|$)/i.test(b))continue"
    "}"
    "add(n)"
    "}"
    "}"
    "try{"
    "if(/(^|\\.)mangaplus\\.shueisha\\.co\\.jp$/i.test(location.host)&&location.pathname.indexOf('/viewer/')===0)picked.push(location.href);"
    "}catch(e){}"
    "if(!picked.length){"
    "domPass();resPass()"
    "}"
    "if(!picked.length){"
    "var all=[],good=[],idx=0;"
    "var els=document.querySelectorAll('img,source');"
    "for(var i=0;i<els.length;i++){"
    "var el=els[i],cs=null;"
    "try{cs=el.currentSrc||el.src||null}catch(e){}"
    "var c=[cs,el.getAttribute('data-src'),el.getAttribute('data-lazy-src'),el.getAttribute('data-original'),el.getAttribute('data-original-src'),el.getAttribute('data-orig-src'),el.getAttribute('data-lazy'),el.getAttribute('data-url'),el.getAttribute('data-image'),el.getAttribute('data-echo')];"
    "var ss=el.getAttribute('srcset')||el.getAttribute('data-srcset');"
    "if(ss){var p=ss.split(','),best='',bw=0;"
    "for(var k=0;k<p.length;k++){"
    "var tk=p[k].trim().split(/\\s+/);"
    "var u0=tk[0]||'';"
    "var w0=parseInt(String(tk[1]||'').replace(/[^0-9]/g,''),10)||0;"
    "if(u0&&w0>=bw){bw=w0;best=u0}}"
    "if(best)c.push(best)}"
    "if(el.tagName==='SOURCE'&&el.parentNode){"
    "var pp=el.parentNode.querySelector('img');"
    "if(pp&&pp.src)c.push(pp.src)}"
    "var pick=null,pj=1;"
    "for(var j=0;j<c.length;j++){"
    "var u=c[j];if(!u)continue;"
    "u=abs(String(u).trim());"
    "if(!u||u.indexOf('data:')===0)continue;"
    "try{if(u===location.href)continue}catch(e2){}"
    "if(!pick)pick=u;"
    "if(!junk(u)){pick=u;pj=0;break}}"
    "if(!pick)continue;"
    "var w=el.naturalWidth||0,h=el.naturalHeight||0;"
    "if(w&&h&&Math.max(w,h)<300)continue;"
    "all.push(pick);"
    "if(!pj)good.push(pick);"
    "idx++}"
    "function dd(list){"
    "var by={},order=[];"
    "for(var i=0;i<list.length;i++){"
    "var u=list[i],k=keyOf(u);"
    "if(Object.prototype.hasOwnProperty.call(by,k)){"
    "var o=by[k];"
    "if(qsz(u)>qsz(o))by[k]=u}"
    "else{by[k]=u;order.push(k)}}"
    "var r=[];"
    "for(var j=0;j<order.length;j++)r.push(by[order[j]]);"
    "return r}"
    "var res=dd(good);"
    "if(!res.length)res=dd(all);"
    "for(var q3=0;q3<res.length;q3++)picked.push(res[q3]);"
    "}"
    "if(!picked.length){alert('__MT_NOLINKS__');return}"
    "var payload=picked.join('\\n');"
    "var app='__MTAPP__';"
    "try{var url=app+'#imgs='+encodeURIComponent(payload);"
    "if(url.length<=1600000){window.open(url,'_blank');return}}catch(e){}"
    "try{navigator.clipboard.writeText(payload).then(function(){"
    "alert('__MT_COPIED__'+picked.length)},function(){prompt('__MT_COPY2__',payload)})"
    "}catch(e){prompt('__MT_COPY2__',payload)}})();"
)


def _browser_extract_js() -> str:
    import json as _json
    tpl = """() => {
  try {
    if (!window.__mtLinksInstalled) {
      window.__mtLinksInstalled = true;

      const hostToggle = () => {
        try {
          const pw = !!(window.pywebview && window.pywebview.api
                       && window.pywebview.api.openBrowser);
          const wv2 = !!(window.chrome && window.chrome.webview
                        && window.chrome.webview.postMessage);
          const row = document.getElementById('mt_browser_row');
          if (row) row.style.display = pw ? '' : 'none';
          const bm = document.querySelector('details.mt-browser');
          if (bm) bm.style.display = (pw || wv2 || window.__mtWebFab)
            ? 'none' : '';
        } catch (e) {}
      };

      const setVal = (el, val) => {
        const s = String(val == null ? "" : val);
        try {
          const proto = el.tagName === "TEXTAREA"
            ? window.HTMLTextAreaElement.prototype
            : window.HTMLInputElement.prototype;
          const desc = Object.getOwnPropertyDescriptor(proto, "value");
          if (desc && desc.set) desc.set.call(el, s); else el.value = s;
        } catch (e) { el.value = s; }
        el.dispatchEvent(new Event("input", { bubbles: true }));
        el.dispatchEvent(new Event("change", { bubbles: true }));
      };

      const findLinksEl = () =>
        document.querySelector("#manga_inp_path textarea")
        || document.querySelector('[id*="manga_inp_path"] textarea')
        || document.querySelector("#manga_inp_path input");

      window.__mtFillLinks = (text) => {
        try {
          const el = findLinksEl();
          if (!el) return false;
          setVal(el, text);
          try {
            const box = document.querySelector(
              '[id*="manga_inp_path"], #manga_inp_path');
            if (box) box.scrollIntoView({ behavior: "smooth",
                                          block: "center" });
          } catch (e) {}
          return true;
        } catch (e) { return false; }
      };

      window.__mtAppendLinks = (text) => {
        try {
          const el = findLinksEl();
          if (!el) return false;
          const s = String(text == null ? "" : text).trim();
          if (!s) return false;
          const cur = String(el.value || "");
          setVal(el, cur ? cur + "\\n" + s : s);
          return true;
        } catch (e) { return false; }
      };

      const applyHash = () => {
        try {
          const m = (location.hash || "").match(/^#imgs=(.+)$/);
          if (!m) return;
          const txt = decodeURIComponent(m[1]);
          if (!txt) return;
          if (window.__mtFillLinks(txt)) {
            try {
              history.replaceState(null, "",
                location.pathname + location.search);
            } catch (e) { location.hash = ""; }
            try {
              const n = txt.split(/\\n/).filter(Boolean).length;
              alert("__MT_FILLED__" + n + "__MT_FILLED2__");
            } catch (e) {}
          }
        } catch (e) {}
      };

      const buildBmk = () => {
        try {
          const a = document.getElementById("mt_bmk");
          if (!a) return;
          const code = __BM_CODE__.replace(/__MTAPP__/g, location.origin);
          try { window.__mtBmCode = code; } catch (e) {}
          a.setAttribute("href", "javascript:" + encodeURIComponent(code));
          a.addEventListener("click", (ev) => {
            ev.preventDefault();
          });
        } catch (e) {}
        try {
          const btn = document.getElementById("mt_bmk_copy");
          const done = document.getElementById("mt_bmk_done");
          if (btn && !btn._mtBound) {
            btn._mtBound = true;
            btn.addEventListener("click", async () => {
              try {
                const a = document.getElementById("mt_bmk");
                const code = (a && a.getAttribute("href") || "").trim();
                if (!code) return;
                await navigator.clipboard.writeText(code);
                if (done) {
                  done.style.display = "inline";
                  setTimeout(() => { done.style.display = "none"; }, 2200);
                }
              } catch (e) {
                try { prompt("__MT_COPY2__", code); } catch (e2) {}
              }
            });
          }
        } catch (e) {}
      };

      window.addEventListener("hashchange", applyHash);

      const installWebBrowser = () => {
        try {
          if (window.__mtWebFabInst) return;
          // وبِ میزبانی‌شده (هاست/HF): مرورگرِ داخلی فقط در اپِ کلود و
          // اپِ واقعی است — در مرورگرِ کاربر گزینه‌ای نمایش داده نمیشود؛
          // راهِ استخراجِ وب، بلوکِ نشانک (سایت‌های کپچادار) است.
          if (__WEB_HOST__) return;
          const pw = !!(window.pywebview && window.pywebview.api
                       && window.pywebview.api.openBrowser);
          const wv2 = !!(window.chrome && window.chrome.webview
                        && window.chrome.webview.postMessage);
          const andr = /;\\s*wv\\)/i.test(navigator.userAgent || "");
          if (pw || wv2 || andr) return;
          window.__mtWebFabInst = true;
          window.__mtWebFab = true;
          const bm = document.querySelector('details.mt-browser');
          if (bm) bm.style.display = 'none';

          const toUrl = (t) => {
            t = String(t || "").trim();
            if (!t) return "https://www.google.com";
            if (/^https?:/i.test(t)) return t;
            if (!/\\s/.test(t) &&
                /^[A-Za-z0-9_-]+(\\.[A-Za-z0-9_-]+)+([\\/?#].*)?$/.test(t))
              return "https://" + t;
            return "https://www.google.com/search?q=" + encodeURIComponent(t);
          };
          const fieldTarget = () => {
            let t = "";
            try {
              const el = document.querySelector("#manga_inp_path textarea")
                || document.querySelector('[id*="manga_inp_path"] textarea')
                || document.querySelector("#manga_inp_path input");
              t = String((el && el.value) || "").trim();
            } catch (e) {}
            if (!t) return "https://www.google.com";
            const parts = t.split(/[\\n,]/).map(s => s.trim()).filter(Boolean);
            const nLinks = parts.filter(p => /^https?:/i.test(p)).length;
            if (nLinks > 1 ||
                /\\.(jpe?g|png|webp|gif|avif|bmp)([?#]|$)/i.test(parts[0])) {
              let last = "";
              try { last = localStorage.getItem("mt_last_site") || ""; } catch (e) {}
              return last || "https://www.google.com";
            }
            return toUrl(parts[0]);
          };

          const css = document.createElement("style");
          css.textContent = ""
            + "#mtWebFab{position:fixed;left:16px;bottom:16px;width:52px;"
            + "height:52px;border-radius:50%;background:#1f2431;"
            + "border:3px solid #e8590c;cursor:pointer;z-index:2147483000;"
            + "display:flex;align-items:center;justify-content:center;"
            + "box-shadow:0 6px 18px rgba(0,0,0,.55);padding:0;"
            + "transition:transform .15s}"
            + "#mtWebFab:hover{transform:scale(1.08)}"
            + "#mtWebFab:active{transform:scale(.95)}"
            + "#mtWbrOv{position:fixed;top:0;left:0;right:0;bottom:0;"
            + "z-index:2147483600;background:#000;display:flex;"
            + "flex-direction:column;direction:rtl;"
            + "font-family:Tahoma,Arial,sans-serif}"
            + "#mtWbrBar{display:flex;align-items:center;gap:8px;"
            + "background:rgba(13,13,16,.97);border-bottom:1px solid #1f1f24;"
            + "padding:8px 10px;box-sizing:border-box;"
            + "box-shadow:0 8px 28px rgba(0,0,0,.55);flex:none}"
            + "#mtWbrBar .u{flex:1;min-width:110px;direction:ltr;text-align:left;"
            + "background:#1a1f2b;color:#e7ebf3;border:1px solid #273043;"
            + "border-radius:20px;padding:9px 14px;font-size:13px;outline:none;"
            + "font-family:inherit}"
            + "#mtWbrBar .u:focus{border-color:#e8590c}"
            + "#mtWbrBar button{border:0;cursor:pointer;font-weight:700;"
            + "font-size:13px;color:#fff;background:#2d3649;border-radius:12px;"
            + "padding:9px 14px;font-family:inherit;white-space:nowrap}"
            + "#mtWbrBar .nav{width:42px;flex:0 0 42px;padding:9px 0;"
            + "text-align:center;font-size:16px;line-height:1}"
            + "#mtWbrBar .ext{background:linear-gradient(135deg,#ff4a3d,#c9271c)}"
            + "#mtWbrBar .cls{width:42px;flex:0 0 42px;padding:9px 0;"
            + "text-align:center;font-size:15px;line-height:1}"
            + "#mtWbrBar .cnt{color:#97948c;font-size:11.5px;max-width:170px;"
            + "overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"
            + "flex:0 1 auto}"
            + "#mtWbrFr{flex:1;border:0;width:100%;background:#fff}"
            + "#mtWbrFb{flex:1;overflow:auto;background:#0d0d10;color:#e7ebf3;"
            + "padding:28px 22px;line-height:2.1;font-size:14.5px;"
            + "box-sizing:border-box}"
            + "#mtWbrFb .b{display:inline-block;"
            + "background:linear-gradient(135deg,#f59e0b,#ea580c);"
            + "color:#fff;font-weight:800;padding:10px 18px;border-radius:10px;"
            + "text-decoration:none;cursor:grab;margin:4px}"
            + "#mtWbrFb .k{background:#2d3649;border:0;color:#fff;"
            + "font-weight:700;padding:10px 18px;border-radius:10px;"
            + "cursor:pointer;font-family:inherit;font-size:13.5px;margin:4px}"
            + "#mtWbrFb .u2{color:#7aa2f7;word-break:break-all;direction:ltr;"
            + "display:block;font-size:12.5px}";
          (document.head || document.documentElement).appendChild(css);

          const fab = document.createElement("button");
          fab.type = "button";
          fab.id = "mtWebFab";
          fab.title = "مرورگر داخلی";
          fab.setAttribute("aria-label", "مرورگر داخلی");
          fab.innerHTML = "<svg viewBox='0 0 24 24' width='26' height='26' "
            + "fill='none' stroke='#fff' stroke-width='1.6'>"
            + "<circle cx='12' cy='12' r='9'/>"
            + "<ellipse cx='12' cy='12' rx='4.2' ry='9'/>"
            + "<path d='M3 12h18'/></svg>";
          document.body.appendChild(fab);

          const openBrowser = () => {
            try {
              const old = document.getElementById("mtWbrOv");
              if (old && old.parentNode) old.parentNode.removeChild(old);
            } catch (e) {}
            const start = fieldTarget();
            const ov = document.createElement("div");
            ov.id = "mtWbrOv";
            const bar = document.createElement("div");
            bar.id = "mtWbrBar";
            const mk = (cls, txt, title) => {
              const b = document.createElement("button");
              b.type = "button";
              if (cls) b.className = cls;
              b.textContent = txt;
              if (title) b.title = title;
              return b;
            };
            const fwd = mk("nav", "\u2192", "جلو");
            const back = mk("nav", "\u2190", "عقب");
            const url = document.createElement("input");
            url.type = "text";
            url.className = "u";
            url.placeholder = "جستجو یا آدرس سایت…";
            url.value = start;
            const goBtn = mk("", "برو");
            const extBtn = mk("ext", "🖼 استخراج لینک");
            const dlBtn = mk("ext", "⬇ استخراج دانلود");
            const cnt = document.createElement("span");
            cnt.className = "cnt";
            cnt.textContent = "…";
            const clsBtn = mk("cls", "\u2715", "بازگشت به اپ");
            bar.appendChild(fwd); bar.appendChild(back);
            bar.appendChild(url); bar.appendChild(goBtn);
            bar.appendChild(extBtn); bar.appendChild(dlBtn);
            bar.appendChild(cnt);
            bar.appendChild(clsBtn);
            const fr = document.createElement("iframe");
            fr.id = "mtWbrFr";
            fr.setAttribute("referrerpolicy", "no-referrer-when-downgrade");
            const fb = document.createElement("div");
            fb.id = "mtWbrFb";
            fb.style.display = "none";
            ov.appendChild(bar); ov.appendChild(fr); ov.appendChild(fb);
            document.body.appendChild(ov);
            try { document.body.style.overflow = "hidden"; } catch (e) {}

            const hist = [start];
            let pos = 0;
            const setCount = (n) => {
              cnt.textContent = (n > 0) ? (n + " عکس آماده") : "—";
            };
            const load = (u, push) => {
              try { if (u && u.indexOf("http") === 0)
                localStorage.setItem("mt_last_site", u); } catch (e) {}
              if (push) {
                hist.splice(pos + 1);
                hist.push(u); pos = hist.length - 1;
              }
              url.value = u;
              fb.style.display = "none";
              fr.style.display = "";
              fr.src = u;
            };
            const close = () => {
              try {
                const o = document.getElementById("mtWbrOv");
                if (o && o.parentNode) o.parentNode.removeChild(o);
              } catch (e) {}
              try { document.body.style.overflow = ""; } catch (e) {}
            };
            const go = () => {
              const u = toUrl(url.value);
              if (u) load(u, true);
            };
            fwd.addEventListener("click", () => {
              if (pos < hist.length - 1) { pos++; load(hist[pos], false); }
            });
            back.addEventListener("click", () => {
              if (pos > 0) { pos--; load(hist[pos], false); }
            });
            url.addEventListener("keydown", (ev) => {
              if (ev.key === "Enter" || ev.keyCode === 13) {
                ev.preventDefault(); go();
              }
            });
            goBtn.addEventListener("click", go);
            clsBtn.addEventListener("click", close);

            const collectDoc = (d) => {
              const abs = (u) => {
                try {
                  const a = d.createElement("a");
                  a.href = u;
                  return a.href;
                } catch (e) { return null; }
              };
              const qsz = (u) => {
                const m = String(u).match(/[?&](?:type|size|w|h|width|height)=(f?)(\\d{1,4})(?:[_x](\\d{1,4}))?/i);
                if (!m) return 0;
                const a = parseInt(m[2], 10) || 0;
                const b = parseInt(m[3] || "0", 10) || 0;
                if (a > 0 && b > 0) return Math.max(a, b);
                if (m[1] && a > 0) return a;
                return 0;
              };
              const junk = (u) => {
                if (!u) return 1;
                if (u.indexOf("data:") === 0) return 1;
                if (u.indexOf("blob:") === 0) return 1;
                if (!/^https?:/i.test(u)) return 1;
                const b = String(u).split(/[?#]/)[0];
                if (/\\.(svg|ico|gif)$/i.test(b)) return 1;
                if (/[-_]\\d{2,4}x\\d{2,4}\\.(jpe?g|png|webp)$/i.test(b)) return 1;
                const q = qsz(u);
                if (q > 0 && q <= 400) return 1;
                if (/(logo|icon|avatar|banner|sprite|favicon|badge|flag|button|emoji|thumb(nail)?s?|placeholder|blank|spacer|transparen|loading|spinner|pixel|profile|rating|share|follow|comment|credits)/i.test(b)) return 1;
                if (/(?:^|[^a-z0-9])ads?[._/-]/i.test(b)) return 1;
                return 0;
              };
              const keyOf = (u) => String(u).split(/[?#]/)[0]
                .replace(/[-_]\\d{2,4}x\\d{2,4}\\./i, ".");
              const seen = {}, picked = [];
              const add = (u) => {
                try {
                  if (!u) return;
                  u = abs(String(u).trim());
                  if (!u) return;
                  if (junk(u)) return;
                  try { if (u === d.location.href) return; } catch (e) {}
                  const k = keyOf(u);
                  if (Object.prototype.hasOwnProperty.call(seen, k)) return;
                  seen[k] = 1; picked.push(u);
                } catch (e) {}
              };
              const domPass = () => {
                const im2 = d.querySelectorAll("img");
                for (let i = 0; i < im2.length; i++) {
                  const el = im2[i];
                  let ok = false, nw = 0, nh = 0;
                  try {
                    ok = !!(el.complete && el.naturalWidth > 0);
                    nw = el.naturalWidth || 0;
                    nh = el.naturalHeight || 0;
                  } catch (e) {}
                  if (!ok) continue;
                  if (nw && nh && Math.max(nw, nh) < 300) continue;
                  let u = "";
                  try { u = el.currentSrc || el.src || ""; } catch (e) {}
                  if (u) add(u);
                }
              };
              const resPass = () => {
                let rs = [];
                try {
                  const pw = d.defaultView || window;
                  rs = pw.performance.getEntriesByType("resource");
                } catch (e) {}
                for (let i = 0; i < rs.length; i++) {
                  const en = rs[i] || {};
                  const t = String(en.initiatorType || "");
                  if (t !== "img" && t !== "css" && t !== "link"
                      && t !== "other" && t !== "svg" && t !== "embed"
                      && t !== "fetch" && t !== "xmlhttprequest") continue;
                  const n = String(en.name || "");
                  if (!n) continue;
                  const b = n.split(/[?#]/)[0];
                  const ext = /\\.(jpe?g|png|webp|avif|bmp|tiff?)$/i.test(b);
                  if (!ext) {
                    if (t === "fetch" || t === "xmlhttprequest") continue;
                    if (!/(^|\\/)(pages?|images?|img|media|manga|manhwa|webtoon|chapters?|episodes?|comic|uploads|wp-content|cdn)(\\/|[_\\-.]|$)/i.test(b)) continue;
                  }
                  add(n);
                }
              };
              domPass();
              resPass();
              if (picked.length) return picked;
              const all = [], good = [];
              let idx = 0;
              const els = d.querySelectorAll("img,source");
              for (let i = 0; i < els.length; i++) {
                const el = els[i];
                let cs = null;
                try { cs = el.currentSrc || el.src || null; } catch (e) {}
                const c = [cs, el.getAttribute("data-src"),
                  el.getAttribute("data-lazy-src"),
                  el.getAttribute("data-original"),
                  el.getAttribute("data-original-src"),
                  el.getAttribute("data-orig-src"),
                  el.getAttribute("data-lazy"),
                  el.getAttribute("data-url"),
                  el.getAttribute("data-image"),
                  el.getAttribute("data-echo")];
                const ss = el.getAttribute("srcset")
                  || el.getAttribute("data-srcset");
                if (ss) {
                  const p = ss.split(",");
                  let best = "", bw = 0;
                  for (let k = 0; k < p.length; k++) {
                    const tk = p[k].trim().split(/\\s+/);
                    const u0 = tk[0] || "";
                    const w0 = parseInt(String(tk[1] || "")
                      .replace(/[^0-9]/g, ""), 10) || 0;
                    if (u0 && w0 >= bw) { bw = w0; best = u0; }
                  }
                  if (best) c.push(best);
                }
                if (el.tagName === "SOURCE" && el.parentNode) {
                  const pp = el.parentNode.querySelector("img");
                  if (pp && pp.src) c.push(pp.src);
                }
                let pick = null, pj = 1;
                for (let j = 0; j < c.length; j++) {
                  let u = c[j];
                  if (!u) continue;
                  u = abs(String(u).trim());
                  if (!u || u.indexOf("data:") === 0) continue;
                  try { if (u === d.location.href) continue; } catch (e) {}
                  if (!pick) pick = u;
                  if (!junk(u)) { pick = u; pj = 0; break; }
                }
                if (!pick) continue;
                const w = el.naturalWidth || 0, h = el.naturalHeight || 0;
                if (w && h && Math.max(w, h) < 300) continue;
                all.push([pick, idx]);
                if (!pj) good.push([pick, idx]);
                idx++;
              }
              const dd = (list) => {
                const by = {}, order = [];
                for (let i = 0; i < list.length; i++) {
                  const it = list[i], k = keyOf(it[0]);
                  if (Object.prototype.hasOwnProperty.call(by, k)) {
                    const o = by[k];
                    if (qsz(it[0]) > qsz(o[0])) by[k] = it;
                  } else { by[k] = it; order.push(k); }
                }
                const res = [];
                for (let j = 0; j < order.length; j++)
                  res.push(by[order[j]][0]);
                return res;
              };
              let out = dd(good);
              if (!out.length) out = dd(all);
              return out;
            };

            const readFrame = () => {
              try {
                const d = fr.contentDocument;
                if (!d) return null;
                return collectDoc(d);
              } catch (e) { return null; }
            };

            const showBlocked = () => {
              const cur = String(url.value || "");
              fr.style.display = "none";
              fb.style.display = "";
              fb.innerHTML = ""
                + "<div style='font-weight:800;font-size:16px;"
                + "margin-bottom:6px'>این سایت اجازه نمی‌دهد عکس‌هایش"
                + " داخلِ اپ خوانده شود (امنیتِ مرورگر) — یا هنوز لود"
                + " نشده است.</div>"
                + "<div>۱) «در مرورگرِ سیستم باز کن» را بزن، کپچا را رد"
                + " کن و فصلِ دلخواه را باز کن و تا آخرِ صفحه اسکرول"
                + " کن.</div>"
                + "<div>۲) نشانکِ نارنجیِ زیر را با ماوس بگیر و در"
                + " نوارِ نشانک‌های مرورگرت رها کن (موبایل: «کپی نشانک»).</div>"
                + "<div>۳) روی سایت، روی نشانکِ «استخراج عکس» بزن —"
                + " لینک‌ها خودکار در فیلدِ ورودی همین اپ می‌نشینند.</div>"
                + "<div style='margin:12px 0 4px'>"
                + "<a id='mtWbrBm' href='#' draggable='true' class='b'>"
                + "🖼 استخراج عکس مانهوا</a>"
                + "<button type='button' id='mtWbrBmC' class='k'>"
                + "📋 کپی نشانک</button> "
                + "<button type='button' id='mtWbrSys' class='k'>"
                + "🌐 در مرورگرِ سیستم باز کن</button></div>"
                + "<span class='u2'></span>";
              try {
                const code = window.__mtBmCode || "";
                const bl = fb.querySelector("#mtWbrBm");
                if (bl && code)
                  bl.setAttribute("href", "javascript:"
                    + encodeURIComponent(code));
                bl.addEventListener("click", (ev) => ev.preventDefault());
                const bc = fb.querySelector("#mtWbrBmC");
                bc.addEventListener("click", async () => {
                  try {
                    await navigator.clipboard.writeText(code);
                    bc.textContent = "✔ کپی شد";
                    setTimeout(() => { bc.textContent = "📋 کپی نشانک"; }, 2000);
                  } catch (e) {}
                });
                const sy = fb.querySelector("#mtWbrSys");
                sy.addEventListener("click", () => {
                  try { window.open(cur, "_blank", "noopener"); }
                  catch (e) {}
                });
                fb.querySelector(".u2").textContent = cur;
              } catch (e) {}
            };

            const curUrl = () => {
              try {
                const w2 = fr.contentWindow;
                if (w2 && w2.location && w2.location.href)
                  return String(w2.location.href);
              } catch (e) {}
              return String(url.value || "");
            };
            const mpViewer = () => {
              try {
                const u = curUrl().trim();
                if (/^https?:\\/\\/([^\\/]+\\.)?mangaplus\\.shueisha\\.co\\.jp\\/viewer\\//i.test(u))
                  return u;
              } catch (e) {}
              return "";
            };
            const fillMp = () => {
              const mp = mpViewer();
              if (!mp) return false;
              if (window.__mtFillLinks && window.__mtFillLinks(mp)) {
                close();
                try { alert("لینکِ فصلِ مانگاپلاس در فیلدِ ورودی نشست —"
                  + " موتور خودش عکس‌ها را از API رسمی می‌گیرد —"
                  + " «شروع ترجمه» را بزن"); } catch (e) {}
                return true;
              }
              return false;
            };

            extBtn.addEventListener("click", () => {
              if (fillMp()) return;
              const out = readFrame();
              if (out && out.length) {
                if (window.__mtFillLinks
                    && window.__mtFillLinks(out.join("\\n"))) {
                  close();
                  try { alert(out.length
                    + " لینک عکس در فیلدِ ورودی نشست — «شروع ترجمه» را بزن"); }
                  catch (e) {}
                }
                return;
              }
              showBlocked();
            });

            dlBtn.addEventListener("click", async () => {
              if (fillMp()) return;
              const out = readFrame();
              if (!out || !out.length) { showBlocked(); return; }
              dlBtn.disabled = true;
              extBtn.disabled = true;
              const items = new Array(out.length);
              let dn = 0, ok = 0, bad = 0;
              const upOne = async (fd) => {
                let r = await fetch("gradio_api/upload",
                                    { method: "POST", body: fd });
                if (r.status === 404)
                  r = await fetch("upload", { method: "POST", body: fd });
                return r;
              };
              const setCnt = (t) => {
                try { cnt.textContent = t; } catch (e) {}
              };
              const pool = async (n, len, worker) => {
                let next = 0;
                const run = async () => {
                  while (next < len) {
                    const k = next++;
                    await worker(k);
                  }
                };
                const ws = [];
                for (let w = 0; w < n && w < len; w++) ws.push(run());
                await Promise.all(ws);
              };
              await pool(3, out.length, async (k) => {
                const u = out[k];
                try {
                  const r = await fetch(u, { credentials: "include" });
                  if (!r.ok) throw 0;
                  const b = await r.blob();
                  items[k] = b;
                } catch (e) { items[k] = null; }
                dn++;
                setCnt("⬇ " + dn + "/" + out.length);
              });
              let up = 0;
              await pool(3, out.length, async (k) => {
                const b = items[k];
                if (!b) { bad++; return; }
                try {
                  let ext = String((b && b.type) || "")
                    .split("/")[1] || "";
                  ext = ext === "jpeg" ? "jpg" : ext;
                  if (!/^[a-z0-9]{2,5}$/.test(ext)) ext = "jpg";
                  const fd = new FormData();
                  fd.append("files", b, "page_" + (k + 1) + "." + ext);
                  const ur = await upOne(fd);
                  if (!ur.ok) throw 0;
                  const a = await ur.json();
                  if (a && a[0]) { items[k] = String(a[0]); ok++; }
                  else throw 0;
                } catch (e) {
                  items[k] = out[k];
                  bad++;
                }
                up++;
                setCnt("⬆ " + up + "/" + out.length
                  + " — در حالِ آپلود");
              });
              dlBtn.disabled = false;
              extBtn.disabled = false;
              const lines = [];
              for (let k = 0; k < out.length; k++) {
                const it = items[k];
                lines.push((typeof it === "string") ? it : out[k]);
              }
              const text = lines.join("\\n");
              if (text && window.__mtFillLinks
                  && window.__mtFillLinks(text)) {
                close();
                try { alert(ok
                  + " عکس دانلود و روی سرور نشست — «شروع ترجمه» را بزن"
                  + (bad ? " — " + bad + " تا فقط لینک شد"
                    + " (سرور خودش میگیرد)" : "")); } catch (e) {}
              } else {
                try { alert("دانلودِ مستقیم ممکن نشد — از «استخراج لینک»"
                  + " استفاده کن (سرور خودش دانلود میکند)"); } catch (e) {}
              }
            });

            const tick = () => {
              const out = readFrame();
              setCount(out ? out.length : -1);
            };
            setTimeout(tick, 900);
            setTimeout(tick, 2500);
            const iv = setInterval(() => {
              const o = document.getElementById("mtWbrOv");
              if (!o) { clearInterval(iv); return; }
              tick();
            }, 5000);

            fr.addEventListener("load", () => setTimeout(tick, 300));
            load(start, false);
            try { url.focus(); url.select(); } catch (e) {}
          };

          fab.addEventListener("click", openBrowser);
          try { window.__mtFabEl = fab; } catch (e) {}
        } catch (e) {}
      };
      const reFab = () => {
        try {
          if (window.__mtFabEl && !document.getElementById("mtWebFab"))
            document.body.appendChild(window.__mtFabEl);
        } catch (e) {}
      };

      const ready = () => {
        buildBmk(); applyHash(); hostToggle(); installWebBrowser();
      };
      if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", ready);
      } else { ready(); }
      setTimeout(applyHash, 700);
      setTimeout(applyHash, 1800);
      try { window.addEventListener("pywebviewready", hostToggle); } catch (e) {}
      setTimeout(hostToggle, 300);
      setTimeout(hostToggle, 1500);
      const mo = new MutationObserver(() => {
        try { buildBmk(); hostToggle(); installWebBrowser(); reFab(); }
        catch (e) {}
      });
      try { mo.observe(document.body, { childList: true, subtree: true }); }
      catch (e) {}
    }
  } catch (e) {}
  return [];
}
"""
    return (tpl
            .replace("__BM_CODE__", _json.dumps(_MT_BM_CODE))
            .replace("__WEB_HOST__",
                     "true" if _web_host() else "false"))


def _prov_keys_js() -> str:
    return """() => {
  if (window.__mangaProvKeysInit) return [];
  window.__mangaProvKeysInit = true;
  const MAP = "manga_prov_keys_v1";
  const provEl = () => document.querySelector(
    "#manga_provider_row input, #manga_provider_row select, #manga_provider_row textarea");
  const keyEl = () => {
    const root = document.getElementById("manga_api_keys");
    if (!root) return null;
    return root.querySelector("input, textarea") || null;
  };
  const setVal = (el, s) => {
    try {
      const proto = (el.tagName === "TEXTAREA")
        ? window.HTMLTextAreaElement.prototype
        : window.HTMLInputElement.prototype;
      const desc = Object.getOwnPropertyDescriptor(proto, "value");
      if (desc && desc.set) desc.set.call(el, s); else el.value = s;
    } catch (e) { el.value = s; }
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  };
  const loadMap = () => {
    try { return JSON.parse(localStorage.getItem(MAP) || "{}") || {}; }
    catch (e) { return {}; }
  };
  const saveMap = (m) => {
    try { localStorage.setItem(MAP, JSON.stringify(m)); } catch (e) {}
  };
  const curProv = () => {
    const pe = provEl();
    return pe ? String(pe.value || "").trim() : "";
  };
  if (!window.__mangaLastProv) window.__mangaLastProv = curProv();
  const onChange = (ev) => {
    try {
      const t = ev.target;
      if (!t || !t.closest || !t.closest("#manga_provider_row")) return;
      const np = String(t.value || "").trim();
      const lp = String(window.__mangaLastProv || "").trim();
      if (!np || np === lp) return;
      const kel = keyEl();
      const cur = kel ? String(kel.value || "").trim() : "";
      const m = loadMap();
      if ((lp === "gemini" || lp === "custom") && cur && cur !== m[np]) {
        m[lp] = cur;
        saveMap(m);
      }
      window.__mangaLastProv = np;
      if ((np === "gemini" || np === "custom") && kel) {
        const saved = String(m[np] || "").trim();
        if (saved) setVal(kel, saved);
        else if (cur && m[lp] === cur) setVal(kel, "");
      }
    } catch (e) {}
  };
  document.addEventListener("change", onChange, true);
  const _t0 = Date.now();
  setInterval(() => {
    try {
      if (Date.now() - _t0 < 8000) return;
      const p = curProv();
      if (p !== "gemini" && p !== "custom") return;
      const kel = keyEl();
      const k = kel ? String(kel.value || "").trim() : "";
      if (!k) return;
      const m = loadMap();
      const other = (p === "gemini") ? "custom" : "gemini";
      if (m[other] && m[other] === k) return;
      if (m[p] !== k) { m[p] = k; saveMap(m); }
    } catch (e) {}
  }, 4000);
  [300, 900, 2000, 4000].forEach((t) => setTimeout(() => {
    if (!window.__mangaLastProv) window.__mangaLastProv = curProv();
  }, t));
  return [];
}
"""


def _dark_js_src() -> str:
    return """() => {
  document.body.classList.add('dark');
  document.documentElement.classList.add('dark');
  try {
    if (window.__mangaWakeLockInstalled) return [];
    window.__mangaWakeLockInstalled = true;
    window.__mangaWL = null;
    const isRunning = () => {
      try {
        const root = document.getElementById('runbtn');
        const btn = root ? (root.querySelector('button') || root) : null;
        const t = (btn && btn.textContent) || '';
        return (t.indexOf('متوقف') >= 0 || t.indexOf('⏹') >= 0);
      } catch (e) { return false; }
    };
    const req = async () => {
      try {
        if (!window.__mangaWL && navigator.wakeLock && navigator.wakeLock.request) {
          window.__mangaWL = await navigator.wakeLock.request('screen');
        }
      } catch (e) {}
    };
    const rel = () => {
      try { if (window.__mangaWL) { window.__mangaWL.release(); } } catch (e) {}
      window.__mangaWL = null;
    };
    setInterval(() => { if (isRunning()) req(); else rel(); }, 4000);
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible' && isRunning()) req();
    });
  } catch (e) {}
  window.__mangaUpdateChip = (logText, btnLabel) => {
    try {
      const el = document.getElementById('manga_status_chip');
      if (!el) return;
      const log = (logText || '').toString();
      const t = (btnLabel || '').toString();
      const running = (t.indexOf('متوقف') >= 0 || t.indexOf('⏹') >= 0);
      const done = (log.indexOf('✅') >= 0 || log.indexOf('تمام شد') >= 0);
      const err = (log.indexOf('❌') >= 0 || log.indexOf('خطا — کد خروج') >= 0);
      if (!running && !done && !err &&
          (!log || log.indexOf('— لاگ بعد') === 0)) {
        el.style.display = 'none';
        el.innerHTML = '';
        return;
      }
      let phase = 'شروع';
      const ph = [
        [/\\[فاز ۱/, 'فاز ۱ — تشخیص حباب + OCR'],
        [/\\[فاز ۲/, 'فاز ۲ — ترجمه'],
        [/\\[فاز ۳/, 'فاز ۳ — ترجمهٔ بافر'],
        [/\\[فاز ۴/, 'فاز ۴ — پاکسازی + رندر'],
      ];
      for (const p of ph) {
        if (log.lastIndexOf(p[0]) >= 0) phase = p[1];
      }
      if (log.indexOf('ذخیرهٔ نهایی') >= 0) phase = 'ذخیرهٔ نهایی';
      const pages = (log.match(/شروع عملیات جدید/g) || []).length;
      let state = running ? 'run' : (err ? 'err' : (done ? 'ok' : 'idle'));
      const stateTxt = running ? 'در حال اجرا' : (err ? 'خطا' : (done ? 'تمام شد' : 'آماده'));
      let html = '<span class="chip-dot ' + state + '"></span>' +
        '<b>' + stateTxt + '</b>';
      html += '<span class="chip-sep">•</span><span>' + phase + '</span>';
      if (pages > 0) html += '<span class="chip-sep">•</span><span>📄 ' + pages + ' صفحه</span>';
      el.innerHTML = html;
      el.style.display = 'flex';
    } catch (e) {}
  };
  try { window.__mangaUpdateChip('', ''); } catch (e) {}
  try {
    const copyBtn = document.getElementById('manga_copy_log');
    if (copyBtn && !copyBtn._bound) {
      copyBtn._bound = true;
      copyBtn.addEventListener('click', () => {
        const ta = document.querySelector('#manga_live_log textarea');
        const txt = ta ? ta.value : '';
        const ok = () => {
          const old = copyBtn.textContent;
          copyBtn.textContent = '✔ کپی شد';
          setTimeout(() => { copyBtn.textContent = old; }, 1400);
        };
        const fallback = () => {
          let tmp = null;
          try {
            tmp = document.createElement('textarea');
            tmp.value = txt;
            tmp.style.position = 'fixed';
            tmp.style.opacity = '0';
            document.body.appendChild(tmp);
            tmp.focus();
            tmp.select();
            document.execCommand('copy');
            tmp.remove();
            tmp = null;
          } catch (e) {
            if (tmp) { try { tmp.remove(); } catch (e2) {} }
          }
          ok();
        };
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(txt).then(ok).catch(fallback);
        } else {
          fallback();
        }
      });
    }
  } catch (e) {}
  try {
    const dlLogBtn = document.getElementById('manga_dl_log');
    if (dlLogBtn && !dlLogBtn._bound) {
      dlLogBtn._bound = true;
      dlLogBtn.addEventListener('click', async () => {
        const mark = (t) => {
          const old = dlLogBtn.textContent;
          dlLogBtn.textContent = t;
          setTimeout(() => { dlLogBtn.textContent = old; }, 1600);
        };
        const tools = document.querySelector('.log-tools');
        const sessdir = tools ? (tools.getAttribute('data-sessdir') || '') : '';
        let sid = '';
        try {
          const el = document.querySelector('#manga_sid textarea')
            || document.querySelector('[id*="manga_sid"] textarea');
          sid = ((el && el.value) || '').toString().trim();
          if (!sid) sid = (localStorage.getItem('manga_sid') || '').trim();
        } catch (e) {}
        if (!sessdir || !sid) { mark('✖ لاگی نیست'); return; }
        const url = '/gradio_api/file=' +
          encodeURIComponent(sessdir + '/' + sid + '.log').replace(/%2F/g, '/');
        try {
          const r = await fetch(url, { method: 'HEAD' });
          if (!r.ok) { mark('✖ لاگی نیست'); return; }
        } catch (e) {}
        const a = document.createElement('a');
        a.href = url;
        a.download = 'manga_log_' + sid.slice(0, 8) + '.txt';
        document.body.appendChild(a);
        a.click();
        a.remove();
        mark('✔ دانلود شد');
      });
    }
  } catch (e) {}
  return [];
}
"""

def _no_proxy_localhost():
    hosts = "localhost,127.0.0.1,0.0.0.0,::1"
    for k in ("NO_PROXY", "no_proxy"):
        cur = os.environ.get(k, "").strip()
        parts = [p.strip() for p in cur.split(",") if p.strip()]
        for h in hosts.split(","):
            if h not in parts:
                parts.insert(0, h)
        os.environ[k] = ",".join(parts)
    try:
        import httpx
        try:
            httpx._utils.get_environment_proxies.cache_clear()
        except Exception:
            pass
    except Exception:
        pass


_REFRESH_FAB_JS = """
() => {
  try {
    if (document.getElementById('mtRefreshFab')) return [];
    var css = document.createElement('style');
    css.textContent = ""
      + "#mtRefreshFab{position:fixed;left:16px;bottom:80px;width:46px;"
      + "height:46px;border-radius:50%;background:rgba(13,13,16,.97);"
      + "border:2px solid #e8590c;cursor:pointer;z-index:2147483640;"
      + "display:flex;align-items:center;justify-content:center;"
      + "box-shadow:0 6px 18px rgba(0,0,0,.55);padding:0;"
      + "transition:transform .15s}"
      + "#mtRefreshFab:hover{transform:scale(1.08)}"
      + "#mtRefreshFab:active{transform:scale(.95)}"
      + "#mtRefreshFab svg{pointer-events:none}";
    (document.head || document.documentElement).appendChild(css);
    var b = document.createElement('button');
    b.type = 'button';
    b.id = 'mtRefreshFab';
    b.title = '\u0631\u0641\u0631\u0634 \u0635\u0641\u062d\u0647';
    b.setAttribute('aria-label', '\u0631\u0641\u0631\u0634');
    b.innerHTML = "<svg viewBox='0 0 24 24' width='22' height='22' "
      + "fill='none' stroke='#fff' stroke-width='2' stroke-linecap='round'>"
      + "<path d='M21 12a9 9 0 1 1-2.64-6.36'/>"
      + "<path d='M21 3v6h-6'/></svg>";
    b.onclick = function() {
      try {
        var ov = document.getElementById('mtWbrOv');
        if (ov) {
          var fr = document.getElementById('mtWbrFr');
          if (fr) { var u = fr.src; fr.src = u; }
          return;
        }
        var rd = document.getElementById('mangaReaderOverlay');
        if (rd) {
          var rf = rd.querySelector('iframe');
          if (rf) {
            try {
              if (rf.contentWindow && rf.contentWindow.location)
                rf.contentWindow.location.reload();
            } catch (e) { rf.src = rf.src; }
          }
          return;
        }
        var vw = document.getElementById('reader_wrap');
        if (vw && vw.offsetWidth > 0) {
          var imgs = vw.querySelectorAll('img');
          var n = 0;
          for (var i = 0; i < imgs.length; i++) {
            var im = imgs[i];
            var src = im.getAttribute('src') || '';
            if (src) { im.src = src; n++; }
          }
          if (n > 0) return;
        }
        location.reload();
      } catch (e) { location.reload(); }
    };
    (document.body || document.documentElement).appendChild(b);
  } catch (e) {}
  return [];
}
"""


def run_web():
    try:
        purge_web_secrets()
    except Exception:
        pass

    _no_proxy_localhost()
    os.environ["GRADIO_ALLOWED_PATHS"] = os.pathsep.join(
        {str(WORK_DIR), str(OUT_DIR), str(UPLOAD_DIR), str(FONT_DIR), str(HERE)})
    os.environ.setdefault("GRADIO_ANALYTICS_CACHE_FREQUENCY", "1000000000")
    try:
        import gradio  
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "gradio"])
    import gradio as gr
    try:
        from gradio import queueing as _q
        _q.Queue.compute_analytics_summary = (
            lambda self, records: self.cached_event_analytics_summary)
    except Exception:
        pass

    cfg = load_config()
    print("[*] بررسی فونت‌های لحن…")
    try:
        n = download_fonts()
        print(f"[+] {n} فونت دانلود شد.")
    except Exception as e:
        print(f"[!] فونت‌ها: {e}")

    def natural_key(s):
        return [int(t) if t.isdigit() else t.lower()
                for t in re.split(r"(\d+)", s)]

    def _dl_label(path: str) -> str:
        try:
            if path and os.path.isfile(path):
                return f"⬇ دانلود ({human_size(os.path.getsize(path))})"
        except Exception:
            pass
        return "⬇ دانلود"

    _LIVE_READER_TMPL = r"""<!DOCTYPE html><html lang="fa" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>نمایش</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:#000;color:#e8e6e1;font-family:system-ui,-apple-system,sans-serif;overscroll-behavior-y:contain;-webkit-user-select:none;user-select:none;touch-action:pan-y}
.bar{display:flex;align-items:center;flex-wrap:wrap;gap:6px;padding:9px 12px;background:#0c0c0e;border-bottom:1px solid #232326;direction:rtl;position:sticky;top:0;z-index:10;transform:translateZ(0);backface-visibility:hidden;will-change:transform}
.dot{width:9px;height:9px;border-radius:50%;background:#ff4a3d;animation:p 1.2s infinite;flex:none}
.dot.off{background:#2e7d4f;animation:none}
@keyframes p{0%,100%{opacity:1}50%{opacity:.25}}
.t{flex:1;color:#97948c;font-size:.82rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.n{color:#fff;background:#ff4a3d;border-radius:999px;padding:3px 11px;font-size:.8rem;font-weight:700;font-variant-numeric:tabular-nums;flex:none}
.n.done{background:#2e7d4f}
.zbtn{background:#161619;color:#e8e6e1;border:1px solid #2a2a2e;border-radius:8px;padding:7px 11px;font-size:.85rem;cursor:pointer;font-family:inherit;flex:none;min-height:36px;min-width:36px}
.zbtn:active{background:#2a2a30}
.zv{color:#97948c;font-size:.78rem;min-width:42px;text-align:center;flex:none;font-variant-numeric:tabular-nums}
#vport{width:100%;overflow-x:clip}/* سند هرگز افقی سرریز نمیکند؛ پنِ افقیِ زوم فقط با transform روی wrap — نوارِ بالایی (sticky) با چپ‌وراست‌کردن کنار نمی‌رود */
#wrap{max-width:min(100%,900px);margin:0 auto;width:100%}
.c{position:relative;width:100%}
.c.hide{display:none}
.c img{display:block;width:100%;height:auto;user-select:none;-webkit-user-drag:none;pointer-events:none}/* content-visibility:auto حذف شد: تصویرِ دیده‌نشده با ارتفاعِ غلطِ ۱۲۰۰px چیده می‌شد و وقت ورود به دید می‌پرید — عاملِ «هی می‌پره میاد» و لگِ زوم */
.slotw{width:100%}
.slotw img{background:#0b0b0d}
.dslot{position:relative;width:100%}
.dslot>img{display:block;width:100%;height:auto}
.dslot>svg.dovl{position:absolute;left:0;top:0;width:100%;height:100%;pointer-events:none;display:block}
.c.no-det .g-det{display:none}
.c.no-pdet .g-pdet{display:none}
.c.no-rec .g-rec{display:none}
.ph{width:100%;aspect-ratio:2/3;background:linear-gradient(100deg,#101012 40%,#17171a 50%,#101012 60%);background-size:200% 100%;animation:sh 1.6s infinite;border-radius:10px;margin:0 0 10px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;color:#5d5b55;font-size:.8rem}
@keyframes sh{0%{background-position:120% 0}100%{background-position:-80% 0}}
.sp{width:26px;height:26px;border-radius:50%;border:3px solid #26262a;border-top-color:#ff4a3d;animation:spin 1s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.hint{padding:16px;text-align:center;color:#6b6963;font-size:.85rem}
.pbar{position:fixed;bottom:0;left:0;right:0;height:4px;background:#1a1a1c;z-index:4}
.pfill{height:100%;width:0;background:linear-gradient(90deg,#ff4a3d,#ff8a5e)}
.plab{position:fixed;bottom:10px;left:50%;transform:translateX(-50%);background:rgba(10,10,12,.85);border:1px solid #2a2a2e;color:#ffcf9e;border-radius:9px;padding:2px 10px;font-size:.68rem;font-variant-numeric:tabular-nums;z-index:5;pointer-events:none;white-space:nowrap;direction:rtl}
#fab{position:fixed;z-index:80;left:18px;bottom:26px;width:60px;height:60px;border-radius:50%;background:#161619;border:2px solid #ff4a3d;color:#fff;font-family:inherit;font-size:.82rem;font-weight:700;cursor:pointer;display:flex;align-items:center;justify-content:center;touch-action:none;box-shadow:0 6px 20px rgba(0,0,0,.6);-webkit-tap-highlight-color:transparent;user-select:none}
#fab:active{transform:scale(.93)}
#fab.open{background:#2c1210;color:#ffb3ab;font-size:1.2rem}
.fbtn{position:fixed;z-index:79;width:58px;height:58px;border-radius:50%;background:#1c1c20;border:2px solid #2e2e33;color:#e8e6e1;font-family:inherit;font-size:.6rem;font-weight:700;cursor:pointer;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:1px;touch-action:manipulation;-webkit-tap-highlight-color:transparent;box-shadow:0 4px 14px rgba(0,0,0,.55);opacity:0;pointer-events:none;transform:scale(.3);transition:opacity .15s ease-out,transform .15s ease-out,left .15s linear,top .15s linear}
.fbtn.show{opacity:1;pointer-events:auto;transform:scale(1)}
.fbtn .ic{font-size:1.02rem;line-height:1.1}
.fbtn.on{border-color:#3a8bff;background:#101f38;color:#fff}
.fbtn.fdbg.on{border-color:#ff4a3d;background:#2c1210}
.fbtn.fcmp.on{border-color:#ff4a3d;background:#2c1210}
.zbtn.hot{background:#ff4a3d;border-color:#ff4a3d;color:#fff;font-weight:700}
#cmp{position:fixed;inset:0;z-index:70;background:#000;display:none}
#cmp.show{display:block}
.cmp-stage{position:absolute;inset:0;overflow:hidden;touch-action:none;background:#0b0b0d}
.cmp-stage img{position:absolute;left:0;top:0;width:100%;height:100%;max-width:none;object-fit:contain;pointer-events:none;user-select:none;-webkit-user-drag:none;background:#0b0b0d}
#cmpBWrap{position:absolute;inset:0;overflow:hidden;clip-path:inset(0 0 0 50%);-webkit-clip-path:inset(0 0 0 50%)}
#cmpDiv{position:absolute;top:0;bottom:0;left:50%;width:2px;background:#fff;box-shadow:0 0 10px rgba(0,0,0,.75);z-index:3;pointer-events:none}
#cmpDiv .cmp-h{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:40px;height:40px;border-radius:50%;background:#fff;color:#151517;display:flex;align-items:center;justify-content:center;font-size:1.05rem;box-shadow:0 2px 12px rgba(0,0,0,.6)}
.cmp-lab{position:absolute;top:10px;background:rgba(0,0,0,.6);color:#fff;border-radius:8px;padding:3px 10px;font-size:.78rem;z-index:3;pointer-events:none}
.cmp-lab.b{right:12px}
.cmp-lab.a{left:12px}
.cmp-tchip{position:absolute;top:12px;left:50%;transform:translateX(-50%);background:rgba(0,0,0,.62);color:#fff;border-radius:9px;padding:4px 12px;font-size:.8rem;z-index:4;pointer-events:none;direction:rtl;white-space:nowrap}
.mcat{position:fixed;z-index:57;right:10px;top:58px;width:70px;touch-action:none;-webkit-tap-highlight-color:transparent;user-select:none;filter:drop-shadow(0 3px 8px rgba(0,0,0,.45));cursor:pointer;transition:opacity .3s}
.mcat svg{display:block;width:100%;height:auto;pointer-events:none}
@media (min-width:768px){.mcat{width:76px;right:18px;top:auto;bottom:112px;filter:drop-shadow(0 6px 14px rgba(0,0,0,.55))}}
.mcat.hide-l svg{transform:scaleX(-1)}
.mcat.hide-l .mcat-bub,.mcat.hide-l .mcat-say{right:auto;left:0}
.mcat.hide-l .mcat-say:after{right:auto;left:14px}
.mcat-bub{position:absolute;top:calc(100% + 3px);right:0;white-space:nowrap;background:rgba(12,12,14,.92);border:1px solid #2a2a2e;color:#e8e6e1;border-radius:10px;padding:2px 8px;font-size:.66rem;font-variant-numeric:tabular-nums;direction:rtl;pointer-events:none;opacity:1;transition:opacity .35s}
.mcat-bub.dim{opacity:0}
.mcat-say{position:absolute;top:calc(100% + 22px);right:-2px;white-space:nowrap;background:#fff;color:#1d1d21;border-radius:12px;padding:4px 10px;font-size:.72rem;pointer-events:none;opacity:0;transform:translateY(4px) scale(.9);transition:opacity .18s ease,transform .18s ease;z-index:2}
.mcat-say.show{opacity:1;transform:translateY(0) scale(1)}
.mcat-say:after{content:'';position:absolute;top:-4px;right:14px;width:9px;height:9px;background:#fff;transform:rotate(45deg)}
.cg-eyes,.cg-mv,.cg-zzz,.cg-sweat,.cg-tears,.cg-heart,.cg-spark,.cg-anger,.cg-steam,.cg-ball,.cg-music,.cg-glass,.cg-shyhands,.cg-shyblush,.cg-hand-chin,.cg-arms-up,.cg-arms-stretch,.cg-snack,.cg-crumbs,.cg-rumble,.cg-think,.cg-speed{display:none}
.mcat.st-read .cg-eyes-open,.mcat.st-study .cg-eyes-open,.mcat.st-hide .cg-eyes-open,.mcat.st-peek .cg-eyes-open,.mcat.st-exc .cg-eyes-happy,.mcat.st-pat .cg-eyes-happy,.mcat.st-spin .cg-eyes-happy,.mcat.st-music .cg-eyes-happy,.mcat.st-dance .cg-eyes-happy,.mcat.st-run .cg-eyes-happy,.mcat.st-sleep .cg-eyes-sleep,.mcat.st-yawn .cg-eyes-sleep,.mcat.st-think .cg-eyes-think,.mcat.st-stress .cg-eyes-worry,.mcat.st-sad .cg-eyes-sad,.mcat.st-shy .cg-eyes-down,.mcat.st-hungry .cg-eyes-down,.mcat.st-eat .cg-eyes-shifty,.mcat.st-annoy .cg-eyes-annoy,.mcat.st-angry .cg-eyes-angry,.mcat.st-ball .cg-eyes-up,.mcat.st-hang .cg-eyes-happy,.mcat.st-edgesit .cg-eyes-happy,.mcat.st-sidepeek .cg-eyes-open{display:block}
.mcat.st-read .cg-mv-smile,.mcat.st-exc .cg-mv-smile,.mcat.st-sleep .cg-mv-smile,.mcat.st-stress .cg-mv-smile,.mcat.st-sad .cg-mv-smile,.mcat.st-pat .cg-mv-smile,.mcat.st-spin .cg-mv-smile,.mcat.st-peek .cg-mv-smile,.mcat.st-hide .cg-mv-smile,.mcat.st-dance .cg-mv-smile,.mcat.st-run .cg-mv-smile,.mcat.st-hang .cg-mv-smile,.mcat.st-edgesit .cg-mv-smile,.mcat.st-sidepeek .cg-mv-smile,.mcat.st-study .cg-mv-focus,.mcat.st-think .cg-mv-focus,.mcat.st-shy .cg-mv-tee,.mcat.st-hungry .cg-mv-tee,.mcat.st-annoy .cg-mv-pout,.mcat.st-angry .cg-mv-shout,.mcat.st-ball .cg-mv-o,.mcat.st-music .cg-mv-song,.mcat.st-yawn .cg-mv-yawn,.mcat.st-eat .cg-mv-munch{display:block}
.mcat.st-sleep .cg-zzz{display:block}
.mcat.st-stress .cg-sweat{display:block}
.mcat.st-sad .cg-tears{display:block}
.mcat.st-pat .cg-heart{display:block}
.mcat.st-exc .cg-spark{display:block}
.mcat.st-angry .cg-anger{display:block}
.mcat.st-angry .cg-steam{display:block}
.mcat.st-ball .cg-ball{display:block}
.mcat.st-music .cg-music{display:block}
.mcat.st-dance .cg-music{display:block}
.mcat.st-study .cg-glass{display:block}
.mcat.st-shy .cg-shyhands{display:block}
.mcat.st-shy .cg-shyblush{display:block}
.mcat.st-hungry .cg-shyblush{display:block}
.mcat.st-hungry .cg-rumble{display:block}
.mcat.st-think .cg-hand-chin{display:block}
.mcat.st-think .cg-think{display:block}
.mcat.st-run .cg-speed{display:block}
.mcat.st-eat .cg-snack{display:block}
.mcat.st-eat .cg-crumbs{display:block}
.mcat.st-dance .cg-hug,.mcat.st-dance .cg-book,.mcat.st-yawn .cg-hug,.mcat.st-yawn .cg-book,.mcat.st-eat .cg-hug,.mcat.st-hang .cg-hug,.mcat.st-hang .cg-book{display:none}
.mcat.st-dance .cg-arms-up{display:block}
.mcat.st-yawn .cg-arms-stretch,.mcat.st-hang .cg-arms-stretch{display:block}
@keyframes mcBob{0%,100%{transform:translateY(0)}50%{transform:translateY(-2.5px)}}
@keyframes mcBounce{0%,100%{transform:translateY(0) scale(1)}30%{transform:translateY(-7px) scale(1.05)}60%{transform:translateY(0) scale(.97)}}
@keyframes mcBreath{0%,100%{transform:scale(1)}50%{transform:scale(1.035)}}
@keyframes mcWiggle{0%,100%{transform:rotate(0)}25%{transform:rotate(-7deg)}75%{transform:rotate(7deg)}}
@keyframes mcTail{0%,100%{transform:rotate(-6deg)}50%{transform:rotate(10deg)}}
@keyframes mcEarT{0%,90%,100%{transform:rotate(0)}95%{transform:rotate(-9deg)}}
@keyframes mcPop{0%{opacity:0;transform:translateY(4px)}25%{opacity:1;transform:translateY(0)}80%{opacity:1}100%{opacity:0;transform:translateY(-18px)}}
@keyframes mcBlink{0%,93.5%,100%{transform:scaleY(1)}95.5%{transform:scaleY(.08)}}
@keyframes mcShake{0%,100%{transform:translateX(0)}25%{transform:translateX(-2.6px)}75%{transform:translateX(2.6px)}}
@keyframes mcHmph{0%,100%{transform:translateX(0) rotate(0)}35%{transform:translateX(-5px) rotate(-5deg)}75%{transform:translateX(-3px) rotate(-3deg)}}
@keyframes mcSpin{0%{transform:rotate(0)}45%{transform:rotate(-185deg) scale(1.07,.93)}100%{transform:rotate(-360deg)}}
@keyframes mcSway{0%,100%{transform:rotate(0)}30%{transform:rotate(-7deg)}70%{transform:rotate(7deg)}}
@keyframes mcBall{0%{transform:translateY(0)}22%{transform:translateY(-56px)}46%{transform:translateY(0)}60%{transform:translateY(-20px)}74%{transform:translateY(0)}86%{transform:translateY(-7px)}100%{transform:translateY(0)}}
@keyframes mcAnger{0%,100%{transform:scale(1)}50%{transform:scale(1.4)}}
@keyframes mcFume{0%{opacity:0;transform:translateY(6px)}30%{opacity:.95}100%{opacity:0;transform:translateY(-16px)}}
@keyframes mcNote{0%{opacity:0;transform:translateY(6px)}25%{opacity:1}100%{opacity:0;transform:translateY(-17px)}}
@keyframes mcPeekBob{0%,100%{transform:translateY(0) rotate(0)}50%{transform:translateY(-3px) rotate(3deg)}}
@keyframes mcDance{0%,100%{transform:rotate(-8deg) translateY(0)}25%{transform:rotate(0) translateY(-4px)}50%{transform:rotate(8deg) translateY(0)}75%{transform:rotate(0) translateY(-4px)}}
@keyframes mcWave{0%,100%{transform:rotate(-12deg)}50%{transform:rotate(14deg)}}
@keyframes mcYawnS{0%{transform:scale(1)}45%{transform:scale(1.05,1.09)}100%{transform:scale(1)}}
@keyframes mcThinkS{0%,100%{transform:rotate(-4deg)}50%{transform:rotate(4deg)}}
@keyframes mcRunBob{0%,100%{transform:translateY(0)}50%{transform:translateY(-5px)}}
@keyframes mcShyWig{0%,100%{transform:rotate(0)}30%{transform:rotate(-4deg) translateY(1px)}70%{transform:rotate(3deg)}}
@keyframes mcScan{0%,100%{transform:translateX(-2.5px)}50%{transform:translateX(2.5px)}}
@keyframes mcDart{0%,18%{transform:translateX(-2.4px)}36%,58%{transform:translateX(2.4px)}76%,100%{transform:translateX(0)}}
@keyframes mcMunch{0%,100%{transform:scaleY(1)}50%{transform:scaleY(.35)}}
@keyframes mcRumble{0%,100%{opacity:.15;transform:scale(.8)}50%{opacity:1;transform:scale(1.18)}}
@keyframes mcMunchBob{0%,100%{transform:translateY(0)}50%{transform:translateY(1.6px)}}
@keyframes mcHang{0%,100%{transform:translateY(0) rotate(0)}50%{transform:translateY(4px) rotate(2deg)}}
@keyframes mcCrumbs{0%{opacity:0;transform:translateY(0)}30%{opacity:1}100%{opacity:0;transform:translateY(9px)}}
@keyframes mcSpeedFlick{0%,100%{opacity:.15}50%{opacity:1}}
.mcat .cg-all{transform-origin:60px 108px;animation:mcBob 3.4s ease-in-out infinite}
.mcat.st-exc .cg-all{animation:mcBounce .55s ease-in-out infinite}
.mcat.st-sleep .cg-all{animation:mcBreath 2.8s ease-in-out infinite}
.mcat.st-pat .cg-all{animation:mcWiggle .45s ease-in-out 3}
.mcat.st-sad .cg-all{animation:mcBob 4.6s ease-in-out infinite}
.mcat.st-angry .cg-all{animation:mcShake .09s linear 18}
.mcat.st-annoy .cg-all{animation:mcHmph 1.9s ease-in-out 1}
.mcat.st-spin .cg-all{animation:mcSpin 1.45s ease-in-out 2}
.mcat.st-ball .cg-all{animation:mcBounce 1.3s ease-in-out 2}
.mcat.st-music .cg-all{animation:mcSway 1.6s ease-in-out 2}
.mcat.st-dance .cg-all{animation:mcDance 1.1s ease-in-out infinite}
.mcat.st-yawn .cg-all{animation:mcYawnS 2.6s ease-in-out 1}
.mcat.st-think .cg-all{animation:mcThinkS 3.2s ease-in-out infinite}
.mcat.st-run .cg-all{animation:mcRunBob .5s ease-in-out infinite}
.mcat.st-hungry .cg-all{animation:mcBob 2.1s ease-in-out infinite}
.mcat.st-eat .cg-all{animation:mcMunchBob .6s ease-in-out infinite}
.mcat.st-shy .cg-all{animation:mcShyWig 2.2s ease-in-out infinite}
.mcat.st-hide .cg-all{animation:mcPeekBob 3s ease-in-out infinite}
.mcat.st-peek .cg-all{animation:mcPeekBob 2.4s ease-in-out infinite}
.mcat .cg-head{transform-origin:60px 82px}
.mcat.st-annoy .cg-head{transform:translateX(-7px) rotate(-10deg)}
.mcat.st-annoy .cg-blush{display:none}
.mcat.st-shy .cg-head{transform:rotate(-3deg)}
.mcat.st-study .cg-head{transform:translateY(2px)}
.mcat .cg-tail{transform-origin:84px 108px;animation:mcTail 3s ease-in-out infinite}
.mcat.st-exc .cg-tail,.mcat.st-ball .cg-tail,.mcat.st-spin .cg-tail,.mcat.st-dance .cg-tail,.mcat.st-run .cg-tail{animation:mcTail .45s ease-in-out infinite}
.mcat.st-stress .cg-tail{animation:mcTail .9s ease-in-out infinite}
.mcat.st-angry .cg-tail{animation:mcTail .3s linear infinite}
.mcat.st-eat .cg-tail{animation:mcTail 1.5s ease-in-out infinite}
.mcat.st-sleep .cg-tail{animation:none}
.mcat .cg-ear-l{transform-origin:40px 28px;animation:mcEarT 6s ease-in-out infinite}
.mcat .cg-ear-r{transform-origin:80px 28px;animation:mcEarT 6s ease-in-out .8s infinite}
.mcat.st-sleep .cg-ear-l,.mcat.st-sleep .cg-ear-r,.mcat.st-pat .cg-ear-l,.mcat.st-pat .cg-ear-r{animation:none}
.mcat.st-eat .cg-ear-l,.mcat.st-eat .cg-ear-r{animation:mcEarT 2.2s ease-in-out infinite}
.mcat .cg-eyes-open{transform-origin:60px 56px;animation:mcBlink 5.6s infinite}
.mcat .cg-heart{animation:mcPop 1.6s ease-out}
.mcat .cg-zzz text{animation:mcPop 2.4s ease-in-out infinite}
.mcat .cg-zzz text:nth-child(2){animation-delay:.5s}
.mcat .cg-ball{animation:mcBall 2.9s cubic-bezier(.33,.66,.45,1) infinite}
.mcat .cg-anger{transform-origin:113px 12px;animation:mcAnger .55s ease-in-out 4}
.mcat .cg-steam circle{animation:mcFume 1.6s ease-out 2}
.mcat .cg-steam circle:nth-child(2){animation-delay:.4s}
.mcat .cg-music .n1{animation:mcNote 1.6s ease-out 2}
.mcat .cg-music .n2{animation:mcNote 1.6s ease-out .55s 2}
.mcat .cg-think circle{animation:mcPop 2.1s ease-in-out infinite}
.mcat .cg-think circle:nth-child(2){animation-delay:.35s}
.mcat .cg-think circle:nth-child(3){animation-delay:.7s}
.mcat .cg-rumble .r1{animation:mcRumble 1.4s ease-in-out infinite}
.mcat .cg-rumble .r2{animation:mcRumble 1.4s ease-in-out .25s infinite}
.mcat .cg-rumble .r3{animation:mcRumble 1.4s ease-in-out .5s infinite}
.mcat .cg-rumble text{animation:mcPop 1.7s ease-in-out infinite}
.mcat .cg-mv-munch{transform-origin:60px 66.5px;animation:mcMunch .5s ease-in-out infinite}
.mcat .cg-crumbs circle{animation:mcCrumbs 1.25s ease-in infinite}
.mcat .cg-crumbs circle:nth-child(2){animation-delay:.4s}
.mcat .cg-crumbs circle:nth-child(3){animation-delay:.8s}
.mcat .cg-speed line{animation:mcSpeedFlick .34s linear infinite}
.mcat .cg-speed line:nth-child(2){animation-delay:.11s}
.mcat .cg-speed line:nth-child(3){animation-delay:.22s}
.mcat.st-study .cg-eyes-open .cg-pupil{animation:mcScan 2.8s ease-in-out infinite}
.mcat.st-eat .cg-eyes-shifty .cg-pupil{animation:mcDart 1.6s ease-in-out infinite}
.mcat.st-dance .cg-arms-up .arm-l{transform-origin:38px 94px;animation:mcWave 1.1s ease-in-out infinite}
.mcat.st-dance .cg-arms-up .arm-r{transform-origin:82px 94px;animation:mcWave 1.1s ease-in-out .55s infinite}
.mcat.st-think .cg-hand-chin{transform-origin:72px 97px;animation:mcBob 2.6s ease-in-out infinite}
.mcat.st-hide .mcat-bub,.mcat.st-peek .mcat-bub,.mcat.st-hang .mcat-bub,.mcat.st-edgesit .mcat-bub,.mcat.st-sidepeek .mcat-bub{display:none}
.mcat.st-hide .mcat-say{top:auto;bottom:calc(100% + 10px)}
.mcat.st-hide .mcat-say:after{top:auto;bottom:-4px}
.mcat.st-peek .mcat-say{top:auto;bottom:calc(100% + 10px);right:auto;left:36px}
.mcat.st-peek .mcat-say:after{top:auto;bottom:-4px;right:auto;left:18px}
.mcat.peek-r .mcat-say{left:auto;right:38px}
.mcat.peek-r .mcat-say:after{left:auto;right:18px}
.mcat.away{opacity:0;pointer-events:none;transition:opacity .35s .7s}
.mcat.glide{transition:left .75s cubic-bezier(.35,.8,.35,1),top .75s cubic-bezier(.35,.8,.35,1),opacity .3s}
.cg-eyes-open .cg-pupil{transition:transform .18s ease-out}
.mcat.st-hang svg{transform:scaleY(-1)}
.mcat.st-hang .cg-all{animation:mcHangSway 2.6s ease-in-out infinite;transform-origin:60px 26px}
.mcat.st-hang .cg-tail{animation:none}
.mcat.st-edgesit .cg-all{animation:mcSitBob 2.3s ease-in-out infinite;transform-origin:60px 108px}
.mcat.st-edgesit .cg-tail{animation:mcTail 1.2s ease-in-out infinite}
.mcat.st-edgesit .mcat-say{top:auto;bottom:calc(100% + 8px)}
.mcat.st-edgesit .mcat-say:after{top:auto;bottom:-4px}
.mcat.st-sidepeek .cg-all{animation:mcLean 2.1s ease-in-out infinite;transform-origin:60px 108px}
.mcat.st-sidepeek .mcat-say{top:auto;bottom:calc(100% + 10px);left:28px;right:auto}
.mcat.st-sidepeek .mcat-say:after{top:auto;bottom:-4px;left:20px;right:auto}
.mcat.st-sidepeek.peek-r .mcat-say{left:auto;right:28px}
.mcat.st-sidepeek.peek-r .mcat-say:after{left:auto;right:20px}
.mcat.st-eat .cg-snack .fish{transform-box:fill-box;transform-origin:50% 50%;animation:mcBite 1.9s ease-in-out infinite}
@keyframes mcHangSway{0%,100%{transform:rotate(0)}50%{transform:rotate(5deg)}}
@keyframes mcSitBob{0%,100%{transform:translateY(0) rotate(-2deg)}50%{transform:translateY(-2px) rotate(2deg)}}
@keyframes mcLean{0%,100%{transform:translateX(0)}50%{transform:translateX(5px)}}
@keyframes mcBite{0%,40%,100%{transform:translate(0,0)}55%,70%{transform:translate(-5px,-6px)}}
#mcatzones{position:fixed;left:0;top:0;right:0;bottom:0;z-index:56;pointer-events:none;display:none}
#mcatzones.show{display:block}
.mz{position:absolute;border:2.5px dashed rgba(217,89,112,.5);border-radius:16px;background:rgba(217,89,112,.05);display:flex;align-items:center;justify-content:center;color:#d95970;font-size:12px;font-weight:800;opacity:.8;transition:opacity .15s,background .15s,transform .15s}
.mz.on{border-color:#d95970;background:rgba(217,89,112,.16);opacity:1;transform:scale(.97)}
.mz-top{top:8px;left:8px;right:8px;height:16%}
.mz-bottom{bottom:8px;left:8px;right:8px;height:16%}
.mz-left{left:8px;top:24%;bottom:24%;width:13%}
.mz-right{right:8px;top:24%;bottom:24%;width:13%}
.mz-center{left:17%;right:17%;top:24%;bottom:24%;border-radius:26px}
.cg-wall{display:none}
.mcat.st-hide .cg-wall{display:block}
#mcatOff{position:fixed;inset:0;z-index:95;background:#000;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;opacity:0;pointer-events:none;transition:opacity .5s ease;direction:rtl}
#mcatOff.show{opacity:1;pointer-events:auto;cursor:pointer}
#mcatOff .off-eyes{width:min(220px,46vw);height:auto;animation:offBlink 4.6s ease-in-out infinite}
#mcatOff .off-t1{color:#ffd964;font-weight:700;font-size:1.06rem}
#mcatOff .off-t2{color:#cfd2da;font-size:.92rem}
#mcatOff .off-t3{color:#6d6a63;font-size:.74rem;margin-top:16px}
@keyframes offBlink{0%,86%,100%{transform:scaleY(1)}90%,94%{transform:scaleY(.06)}}

</style></head><body>
<div class="bar"><span class="dot" id="dot"></span><div class="t">نمایش — صفحه‌ها سر جایشان پر می‌شوند</div><button type="button" class="zbtn" id="mtoggle" style="display:none" title="حالتِ دیباگ/نهایی">دیباگ</button><button type="button" class="zbtn" id="zo" title="کوچک‌تر">−</button><span class="zv" id="zv">100%</span><button type="button" class="zbtn" id="zi" title="بزرگ‌تر">+</button><button type="button" class="zbtn" id="zf" title="پهنای صفحه">پهنا</button><div class="n" id="n">0</div></div>
<div id="vport">
<div id="wrap">
<main class="c" id="cF"><div class="hint" id="hF">در انتظار اولین صفحه…</div></main>
<main class="c hide" id="cD"><div class="hint" id="hD">در انتظار دیباگ…</div></main>
</div>
</div>
<div class="plab" id="plab" dir="rtl"></div>
<div class="pbar"><div class="pfill" id="pf"></div></div>
<button type="button" id="fab" aria-label="منو" style="display:none">منو</button>
<div class="mcat st-read" id="mcat" title="هم‌خوانِ نکو-گِرل — ۲۴ حالت! بکش و رها کن: بالا/پایین/بغل/وسط، ضربه = نوازش (زیادش نکن!)">
<svg viewBox="0 0 120 140" aria-hidden="true">
<defs>
<linearGradient id="cgHair" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#cfe7fa"/><stop offset="1" stop-color="#a8cdec"/></linearGradient>
<linearGradient id="cgDress" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f9c0cc"/><stop offset="1" stop-color="#f2a0b1"/></linearGradient>
<linearGradient id="cgTail" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#cfe7fa"/><stop offset="1" stop-color="#9fc4ea"/></linearGradient>
<radialGradient id="cgEye" cx=".5" cy=".42" r=".75"><stop offset="0" stop-color="#ffe9ae"/><stop offset=".55" stop-color="#f4b95c"/><stop offset="1" stop-color="#e89b3c"/></radialGradient>
</defs>
<ellipse cx="60" cy="134" rx="26" ry="3.4" fill="rgba(0,0,0,.13)"/>
<g class="cg-all">
<g class="cg-speed" stroke="#aebfd6" stroke-width="2.6" stroke-linecap="round"><line x1="2" y1="98" x2="14" y2="98"/><line x1="0" y1="110" x2="12" y2="110"/><line x1="3" y1="122" x2="14" y2="122"/></g>
<g class="cg-tail"><path d="M78 112 Q112 108 106 82" fill="none" stroke="url(#cgTail)" stroke-width="11.5" stroke-linecap="round"/><path d="M78 112 Q112 108 106 82" fill="none" stroke="#bcd9f2" stroke-width="9.2" stroke-linecap="round"/><path d="M106 84 Q103 72 92 71" fill="none" stroke="#9fc4ea" stroke-width="9" stroke-linecap="round"/><path d="M106 84 Q103 72 92 71" fill="none" stroke="#bcd9f2" stroke-width="7" stroke-linecap="round"/><path d="M97.5 76.5 Q94.8 73.4 92.5 71.5" fill="none" stroke="#ffffff" stroke-width="6.4" stroke-linecap="round"/><path d="M99 101 q4.5 -1.5 6.5 -4.5" fill="none" stroke="#9fc4ea" stroke-width="1.5" stroke-linecap="round"/><path d="M100 93 q4 -.5 6 -3" fill="none" stroke="#9fc4ea" stroke-width="1.5" stroke-linecap="round"/></g>
<path d="M44 100 Q60 95.5 76 100 L85.5 119.5 Q87.5 125 81.5 125.4 L38.5 125.4 Q32.5 125 34.5 119.5 Z" fill="url(#cgDress)"/>
<path d="M35.5 120.5 Q60 124.5 84.5 120.5" fill="none" stroke="#e28b9d" stroke-width="1.8" stroke-linecap="round"/>
<path d="M42 88 Q30 89 30 99 Q30 108 41 107 Q48.5 106 48 96.5 Q47.5 89.5 42 88 Z" fill="#f4a9b8" stroke="#d97a90" stroke-width=".9"/>
<path d="M78 88 Q90 89 90 99 Q90 108 79 107 Q71.5 106 72 96.5 Q72.5 89.5 78 88 Z" fill="#f4a9b8" stroke="#d97a90" stroke-width=".9"/>
<ellipse cx="47.5" cy="126" rx="6.6" ry="4.6" fill="#fff6ea" stroke="#e7cbb6" stroke-width="1.1"/>
<ellipse cx="72.5" cy="126" rx="6.6" ry="4.6" fill="#fff6ea" stroke="#e7cbb6" stroke-width="1.1"/>
<g fill="#f2a9b8"><circle cx="45.2" cy="124.4" r="1.5"/><circle cx="47.9" cy="123.9" r="1.5"/><circle cx="50.5" cy="124.8" r="1.4"/><circle cx="70.2" cy="124.4" r="1.5"/><circle cx="72.9" cy="123.9" r="1.5"/><circle cx="75.5" cy="124.8" r="1.4"/></g>
<path d="M43.6 127 a4.9 4.9 0 0 0 8.4 0 z" fill="#d98a9c"/>
<path d="M68.6 127 a4.9 4.9 0 0 0 8.4 0 z" fill="#d98a9c"/>
<g class="cg-book"><g transform="translate(2,9) rotate(-2 60 103)"><rect x="32" y="89" width="56" height="29" rx="3" fill="#a83050"/><rect x="34.5" y="91.5" width="51" height="24" rx="2" fill="#fbf7ee"/><line x1="60" y1="93" x2="60" y2="114" stroke="#a83050" stroke-width="2.6"/><g stroke="#c5bba8" stroke-width="1.7" stroke-linecap="round"><line x1="39" y1="97.5" x2="56" y2="97.5"/><line x1="39" y1="102" x2="56" y2="102"/><line x1="39" y1="106.5" x2="52" y2="106.5"/><line x1="64" y1="97.5" x2="81" y2="97.5"/><line x1="64" y1="102" x2="81" y2="102"/><line x1="68" y1="106.5" x2="81" y2="106.5"/></g><path d="M75 115 l0 5 2.2 -1.8 2.2 1.8 0 -5 z" fill="#e8b84b"/></g></g>
<g class="cg-hug"><path d="M43 88 Q35 93 35.5 102" fill="none" stroke="#d97a90" stroke-width="13.5" stroke-linecap="round"/><path d="M77 88 Q85 93 84.5 102" fill="none" stroke="#d97a90" stroke-width="13.5" stroke-linecap="round"/><path d="M43 88 Q35 93 35.5 102" fill="none" stroke="#f4a9b8" stroke-width="10.5" stroke-linecap="round"/><path d="M77 88 Q85 93 84.5 102" fill="none" stroke="#f4a9b8" stroke-width="10.5" stroke-linecap="round"/><g transform="translate(35.5,103)"><circle r="6" fill="#ffe9dc"/><path d="M-3.3 2.1 q3.3 2.3 6.6 0" fill="none" stroke="#e8b9a4" stroke-width="1.2" stroke-linecap="round"/><path d="M-2.5 -1.4 q1 -2 1.9 -2.2 M.5 -2 q1 -2 1.9 -2.2" stroke="#e8b9a4" stroke-width="1" fill="none" stroke-linecap="round"/></g><g transform="translate(84.5,103)"><circle r="6" fill="#ffe9dc"/><path d="M-3.3 2.1 q3.3 2.3 6.6 0" fill="none" stroke="#e8b9a4" stroke-width="1.2" stroke-linecap="round"/><path d="M-2.5 -1.4 q1 -2 1.9 -2.2 M.5 -2 q1 -2 1.9 -2.2" stroke="#e8b9a4" stroke-width="1" fill="none" stroke-linecap="round"/></g></g>
<g class="cg-arms-up"><g class="arm-l"><path d="M38 94 Q24 90 15.5 68" fill="none" stroke="#d97a90" stroke-width="14.5" stroke-linecap="round"/><path d="M38 94 Q24 90 15.5 68" fill="none" stroke="#f4a9b8" stroke-width="11" stroke-linecap="round"/><g transform="translate(14.5,66)"><circle r="5.8" fill="#ffe9dc"/><path d="M-3.2 2.1 q3.2 2.3 6.4 0" fill="none" stroke="#e8b9a4" stroke-width="1.2" stroke-linecap="round"/><path d="M-2.4 -1.4 q1 -2 1.9 -2.2 M.4 -2 q1 -2 1.9 -2.2" stroke="#e8b9a4" stroke-width="1" fill="none" stroke-linecap="round"/></g></g><g class="arm-r"><path d="M82 94 Q96 90 104.5 68" fill="none" stroke="#d97a90" stroke-width="14.5" stroke-linecap="round"/><path d="M82 94 Q96 90 104.5 68" fill="none" stroke="#f4a9b8" stroke-width="11" stroke-linecap="round"/><g transform="translate(105.5,66)"><circle r="5.8" fill="#ffe9dc"/><path d="M-3.2 2.1 q3.2 2.3 6.4 0" fill="none" stroke="#e8b9a4" stroke-width="1.2" stroke-linecap="round"/><path d="M-2.4 -1.4 q1 -2 1.9 -2.2 M.4 -2 q1 -2 1.9 -2.2" stroke="#e8b9a4" stroke-width="1" fill="none" stroke-linecap="round"/></g></g></g>
<g class="cg-arms-stretch"><path d="M38 94 Q24 97 13.5 86" fill="none" stroke="#d97a90" stroke-width="14.5" stroke-linecap="round"/><path d="M38 94 Q24 97 13.5 86" fill="none" stroke="#f4a9b8" stroke-width="11" stroke-linecap="round"/><g transform="translate(12,85)"><circle r="5.6" fill="#ffe9dc"/><path d="M-3.1 2 q3.1 2.2 6.2 0" fill="none" stroke="#e8b9a4" stroke-width="1.2" stroke-linecap="round"/></g><path d="M82 94 Q96 97 106.5 86" fill="none" stroke="#d97a90" stroke-width="14.5" stroke-linecap="round"/><path d="M82 94 Q96 97 106.5 86" fill="none" stroke="#f4a9b8" stroke-width="11" stroke-linecap="round"/><g transform="translate(108,85)"><circle r="5.6" fill="#ffe9dc"/><path d="M-3.1 2 q3.1 2.2 6.2 0" fill="none" stroke="#e8b9a4" stroke-width="1.2" stroke-linecap="round"/></g></g>
<g class="cg-head">
<path d="M60 13 C86 13 103 27 104 50 C105 68 97 82 82 90 C74 94 66 95 60 95 C54 95 46 94 38 90 C23 82 15 68 16 50 C17 27 34 13 60 13 Z" fill="url(#cgHair)"/>
<g class="cg-ear cg-ear-l"><path d="M24 30 Q15 13 12.5 2.5 Q30 7 52 20 Q49 28 39 30.6 Q31 32 24 30 Z" fill="#c3ddf5" stroke="#9fc4ea" stroke-width="1.4"/><path d="M27.5 24.5 Q21.5 12.5 20.5 6.5 Q33 10.5 46 19.5 Q42.5 26.5 35 27 Q30.8 27.3 27.5 24.5 Z" fill="#f7c6d1"/><path d="M25.5 29 q-3 -10 2 -16.5 q6 7 5 17.5 q-3.5 1.6 -7 -.9 z" fill="#ffffff"/></g>
<g class="cg-ear cg-ear-r"><path d="M96 30 Q105 13 107.5 2.5 Q90 7 68 20 Q71 28 81 30.6 Q89 32 96 30 Z" fill="#c3ddf5" stroke="#9fc4ea" stroke-width="1.4"/><path d="M92.5 24.5 Q98.5 12.5 99.5 6.5 Q87 10.5 74 19.5 Q77.5 26.5 85 27 Q89.2 27.3 92.5 24.5 Z" fill="#f7c6d1"/><path d="M94.5 29 q3 -10 -2 -16.5 q-6 7 -5 17.5 q3.5 1.6 7 -.9 z" fill="#ffffff"/></g>
<path d="M46 79 Q60 88 74 79 L79.5 91 Q60 100.5 40.5 91 Z" fill="#fffdf6" stroke="#e8d9c8" stroke-width="1" stroke-linejoin="round"/>
<path d="M45.5 85.5 Q60 94.5 74.5 85.5" fill="none" stroke="#e28b9d" stroke-width="1.6" stroke-linecap="round"/>
<path d="M60 92.5 L53.6 89.4 Q51.6 93.4 54 96.6 Z" fill="#ff8fa8" stroke="#e8738e" stroke-width=".6" stroke-linejoin="round"/>
<path d="M60 92.5 L66.4 89.4 Q68.4 93.4 66 96.6 Z" fill="#ff8fa8" stroke="#e8738e" stroke-width=".6" stroke-linejoin="round"/>
<circle cx="60" cy="92.8" r="2" fill="#e8738e"/>
<circle cx="60" cy="98.8" r="3.5" fill="#f6c957" stroke="#c9992e" stroke-width="1.1"/>
<path d="M56.8 99.5 Q60 101.5 63.2 99.5" fill="none" stroke="#c9992e" stroke-width="1" stroke-linecap="round"/>
<line x1="58.7" y1="99.1" x2="61.3" y2="99.1" stroke="#c9992e" stroke-width="1"/>
<circle cx="60" cy="97.4" r="1" fill="#fff" opacity=".9"/>
<path d="M60 26 C78 26 90 35 91 52 C92 66 84 78 71 82 C67 83.5 63 84 60 84 C57 84 53 83.5 49 82 C36 78 28 66 29 52 C30 35 42 26 60 26 Z" fill="#ffe9dc"/>
<path d="M28 20 Q19 38 19.5 56 Q20 72 26 85 Q30 92 34.5 88 Q31 80 30 66 Q29 48 34 31 Q37 23 35 18.5 Q29.5 16.5 28 20 Z" fill="#bcd9f2"/>
<path d="M92 20 Q101 38 100.5 56 Q100 72 94 85 Q90 92 85.5 88 Q89 80 90 66 Q91 48 86 31 Q83 23 85 18.5 Q90.5 16.5 92 20 Z" fill="#bcd9f2"/>
<path d="M22.5 41 Q24 17.5 60 15 Q96 17.5 97.5 41 Q94 45.5 90.5 41.5 Q87 47 82.5 42.5 Q78.5 48 73.5 43 Q69.5 48.5 64.5 43.5 Q61.5 48 56.5 43.5 Q51.5 48.5 47.5 43 Q42.5 48 38.5 42.5 Q34 47 30.5 41.5 Q27 45.5 22.5 41 Z" fill="#bcd9f2"/>
<path d="M50 18 Q52 27 50.5 35" fill="none" stroke="#a9cdf0" stroke-width="1.4" stroke-linecap="round"/>
<path d="M70 18 Q68 27 69.5 35" fill="none" stroke="#a9cdf0" stroke-width="1.4" stroke-linecap="round"/>
<path d="M51 44 Q54.5 51 52.5 58 Q49.5 51 48.5 45 Z" fill="#bcd9f2"/>
<path d="M69 44 Q65.5 51 67.5 58 Q70.5 51 71.5 45 Z" fill="#bcd9f2"/>
<path class="cg-ahoge" d="M58 14 Q54.5 8 59 4.5 Q63.5 1.5 64.5 5.5 Q65.2 8.3 62 8.8 Q60.2 9 60.6 7" fill="none" stroke="#bcd9f2" stroke-width="2.6" stroke-linecap="round"/>
<path d="M68 26 l-7.5 -3.6 1 7.2 z M68 26 l7.5 -3.6 -1 7.2 z" fill="#ff9eb5"/>
<circle cx="68" cy="26.2" r="2.3" fill="#fff"/>
<path d="M46 23 q6 -3.5 12 -3.5" fill="none" stroke="#e4f1fb" stroke-width="2.4" stroke-linecap="round"/>
<path d="M64 19.5 q6.5 .5 11.5 3.5" fill="none" stroke="#e4f1fb" stroke-width="2.4" stroke-linecap="round"/>
<g class="cg-eyes cg-eyes-open"><path d="M38.6 50.5 Q45 45.8 51.4 50.5" fill="none" stroke="#4a323e" stroke-width="2.6" stroke-linecap="round"/><path d="M68.6 50.5 Q75 45.8 81.4 50.5" fill="none" stroke="#4a323e" stroke-width="2.6" stroke-linecap="round"/><g class="cg-pupil"><ellipse cx="45" cy="56" rx="6.4" ry="7.8" fill="url(#cgEye)"/><ellipse cx="45" cy="58.4" rx="4.8" ry="4.4" fill="#f8cf7a"/><ellipse cx="45" cy="56" rx="2.8" ry="4.3" fill="#45301f"/><circle cx="42.9" cy="52.9" r="2.1" fill="#fff"/><circle cx="47.5" cy="59.7" r="1" fill="#fff"/><circle cx="47.9" cy="57.9" r=".6" fill="#fff" opacity=".9"/></g><g class="cg-pupil"><ellipse cx="75" cy="56" rx="6.4" ry="7.8" fill="url(#cgEye)"/><ellipse cx="75" cy="58.4" rx="4.8" ry="4.4" fill="#f8cf7a"/><ellipse cx="75" cy="56" rx="2.8" ry="4.3" fill="#45301f"/><circle cx="72.9" cy="52.9" r="2.1" fill="#fff"/><circle cx="77.5" cy="59.7" r="1" fill="#fff"/><circle cx="77.9" cy="57.9" r=".6" fill="#fff" opacity=".9"/></g><path d="M38.2 52.2 L35.2 51 M38.5 55 L35.3 54.6 M81.8 52.2 L84.8 51 M81.5 55 L84.7 54.6" stroke="#4a323e" stroke-width="1.8" stroke-linecap="round"/></g>
<g class="cg-eyes cg-eyes-happy" fill="none" stroke="#4a323e" stroke-width="2.5" stroke-linecap="round"><path d="M38.5 55.5 Q45 47 51.5 55.5"/><path d="M68.5 55.5 Q75 47 81.5 55.5"/></g>
<g class="cg-eyes cg-eyes-sleep" fill="none" stroke="#4a323e" stroke-width="2.2" stroke-linecap="round"><path d="M38.5 53 Q45 58 51.5 53"/><path d="M68.5 53 Q75 58 81.5 53"/></g>
<g class="cg-eyes cg-eyes-worry"><path d="M40 45 Q45 43.2 50 45.2" fill="none" stroke="#93b8de" stroke-width="1.8" stroke-linecap="round"/><path d="M80 45 Q75 43.2 70 45.2" fill="none" stroke="#93b8de" stroke-width="1.8" stroke-linecap="round"/><ellipse cx="45" cy="56" rx="5.8" ry="7.2" fill="url(#cgEye)"/><ellipse cx="44" cy="57" rx="2.6" ry="3.8" fill="#563a22"/><circle cx="43.4" cy="53.2" r="1.7" fill="#fff"/><ellipse cx="75" cy="56" rx="5.8" ry="7.2" fill="url(#cgEye)"/><ellipse cx="74" cy="57" rx="2.6" ry="3.8" fill="#563a22"/><circle cx="73.4" cy="53.2" r="1.7" fill="#fff"/></g>
<g class="cg-eyes cg-eyes-sad"><path d="M40 45.5 Q44 43 49 43.6" fill="none" stroke="#93b8de" stroke-width="1.8" stroke-linecap="round"/><path d="M80 45.5 Q76 43 71 43.6" fill="none" stroke="#93b8de" stroke-width="1.8" stroke-linecap="round"/><ellipse cx="45" cy="56" rx="6.2" ry="7.8" fill="url(#cgEye)"/><ellipse cx="45" cy="56" rx="2.8" ry="4.3" fill="#563a22"/><circle cx="42.9" cy="53" r="2" fill="#fff"/><circle cx="47.3" cy="60.5" r="1.3" fill="#fff"/><ellipse cx="75" cy="56" rx="6.2" ry="7.8" fill="url(#cgEye)"/><ellipse cx="75" cy="56" rx="2.8" ry="4.3" fill="#563a22"/><circle cx="72.9" cy="53" r="2" fill="#fff"/><circle cx="77.3" cy="60.5" r="1.3" fill="#fff"/></g>
<g class="cg-eyes cg-eyes-annoy"><ellipse cx="45" cy="56.5" rx="5.4" ry="5" fill="url(#cgEye)"/><ellipse cx="47.8" cy="56.5" rx="2.3" ry="3.2" fill="#563a22"/><path d="M39.5 51 Q45 48 50.5 51 L50.5 46.5 Q45 43.5 39.5 46.5 Z" fill="#ffe9dc"/><path d="M39 51 Q45 49 51 51" fill="none" stroke="#4a323e" stroke-width="2.2" stroke-linecap="round"/><ellipse cx="75" cy="56.5" rx="5.4" ry="5" fill="url(#cgEye)"/><ellipse cx="77.8" cy="56.5" rx="2.3" ry="3.2" fill="#563a22"/><path d="M69.5 51 Q75 48 80.5 51 L80.5 46.5 Q75 43.5 69.5 46.5 Z" fill="#ffe9dc"/><path d="M69 51 Q75 49 81 51" fill="none" stroke="#4a323e" stroke-width="2.2" stroke-linecap="round"/><circle cx="37.5" cy="62.5" r="4.4" fill="#ffb3ba" opacity=".95"/><circle cx="82.5" cy="62.5" r="4.4" fill="#ffb3ba" opacity=".95"/></g>
<g class="cg-eyes cg-eyes-angry"><path d="M38.5 43 L51.5 47.5" stroke="#4a323e" stroke-width="2.5" stroke-linecap="round"/><path d="M81.5 43 L68.5 47.5" stroke="#4a323e" stroke-width="2.5" stroke-linecap="round"/><ellipse cx="45" cy="56.5" rx="5.8" ry="6.6" fill="url(#cgEye)"/><ellipse cx="45" cy="57" rx="2.6" ry="3.7" fill="#563a22"/><path d="M38.8 48.5 L52 51.8" stroke="#4a323e" stroke-width="2.3" stroke-linecap="round"/><ellipse cx="75" cy="56.5" rx="5.8" ry="6.6" fill="url(#cgEye)"/><ellipse cx="75" cy="57" rx="2.6" ry="3.7" fill="#563a22"/><path d="M81.2 48.5 L68 51.8" stroke="#4a323e" stroke-width="2.3" stroke-linecap="round"/></g>
<g class="cg-eyes cg-eyes-up"><path d="M38.6 50.5 Q45 45.8 51.4 50.5" fill="none" stroke="#4a323e" stroke-width="2.6" stroke-linecap="round"/><path d="M68.6 50.5 Q75 45.8 81.4 50.5" fill="none" stroke="#4a323e" stroke-width="2.6" stroke-linecap="round"/><ellipse cx="45" cy="56" rx="6.4" ry="7.8" fill="url(#cgEye)"/><ellipse cx="45" cy="52.5" rx="2.8" ry="4.3" fill="#45301f"/><circle cx="47.8" cy="50.4" r="2.1" fill="#fff"/><ellipse cx="75" cy="56" rx="6.4" ry="7.8" fill="url(#cgEye)"/><ellipse cx="75" cy="52.5" rx="2.8" ry="4.3" fill="#45301f"/><circle cx="77.8" cy="50.4" r="2.1" fill="#fff"/></g>
<g class="cg-eyes cg-eyes-down"><path d="M38.6 52.6 Q45 49.6 51.4 52.6" fill="none" stroke="#4a323e" stroke-width="2.6" stroke-linecap="round"/><path d="M68.6 52.6 Q75 49.6 81.4 52.6" fill="none" stroke="#4a323e" stroke-width="2.6" stroke-linecap="round"/><ellipse cx="45" cy="58.6" rx="5.9" ry="5" fill="url(#cgEye)"/><ellipse cx="45" cy="60" rx="2.6" ry="3.1" fill="#563a22"/><circle cx="43.3" cy="57.4" r="1.5" fill="#fff"/><ellipse cx="75" cy="58.6" rx="5.9" ry="5" fill="url(#cgEye)"/><ellipse cx="75" cy="60" rx="2.6" ry="3.1" fill="#563a22"/><circle cx="73.3" cy="57.4" r="1.5" fill="#fff"/></g>
<g class="cg-eyes cg-eyes-shifty"><path d="M38.6 50.5 Q45 45.8 51.4 50.5" fill="none" stroke="#4a323e" stroke-width="2.6" stroke-linecap="round"/><path d="M68.6 50.5 Q75 45.8 81.4 50.5" fill="none" stroke="#4a323e" stroke-width="2.6" stroke-linecap="round"/><g class="cg-pupil"><ellipse cx="45" cy="56" rx="6.4" ry="7.8" fill="url(#cgEye)"/><ellipse cx="45" cy="56" rx="2.8" ry="4.3" fill="#45301f"/><circle cx="42.9" cy="52.9" r="2.1" fill="#fff"/></g><g class="cg-pupil"><ellipse cx="75" cy="56" rx="6.4" ry="7.8" fill="url(#cgEye)"/><ellipse cx="75" cy="56" rx="2.8" ry="4.3" fill="#45301f"/><circle cx="72.9" cy="52.9" r="2.1" fill="#fff"/></g></g>
<g class="cg-eyes cg-eyes-think"><path d="M38.6 50.5 Q45 45.8 51.4 50.5" fill="none" stroke="#4a323e" stroke-width="2.6" stroke-linecap="round"/><path d="M68.6 50.5 Q75 45.8 81.4 50.5" fill="none" stroke="#4a323e" stroke-width="2.6" stroke-linecap="round"/><g class="cg-pupil" transform="translate(1.6,-2.2)"><ellipse cx="45" cy="56" rx="6.2" ry="7.5" fill="url(#cgEye)"/><ellipse cx="45" cy="56" rx="2.7" ry="4.1" fill="#45301f"/><circle cx="42.9" cy="52.9" r="1.9" fill="#fff"/></g><g class="cg-pupil" transform="translate(1.6,-2.2)"><ellipse cx="75" cy="56" rx="6.2" ry="7.5" fill="url(#cgEye)"/><ellipse cx="75" cy="56" rx="2.7" ry="4.1" fill="#45301f"/><circle cx="72.9" cy="52.9" r="1.9" fill="#fff"/></g></g>
<ellipse class="cg-blush" cx="37" cy="68" rx="6.2" ry="3.3" fill="#ffc2cd" opacity=".8"/>
<ellipse class="cg-blush" cx="83" cy="68" rx="6.2" ry="3.3" fill="#ffc2cd" opacity=".8"/>
<path d="M59 60.4 q1.4 1.1 2.8 0" fill="none" stroke="#eda39b" stroke-width="1.3" stroke-linecap="round"/>
<path class="cg-mv cg-mv-smile" d="M54 64.8 Q57.2 69 60 65.3 Q62.8 69 66 64.8" fill="none" stroke="#c26375" stroke-width="2.2" stroke-linecap="round"/>
<path class="cg-mv cg-mv-smile" d="M62.9 67.4 L63.9 69.6 L64.9 67.5 Z" fill="#ffffff" stroke="#e8cfcf" stroke-width=".5" stroke-linejoin="round"/>
<path class="cg-mv cg-mv-pout" d="M56 67.5 Q60 65.2 64 67.5" fill="none" stroke="#c26375" stroke-width="2.1" stroke-linecap="round"/>
<ellipse class="cg-mv cg-mv-shout" cx="60" cy="67" rx="4.2" ry="3.6" fill="#9e4a5e"/>
<path class="cg-mv cg-mv-shout" d="M57.6 68.6 q2.4 2.4 4.8 0 z" fill="#e58ea0"/>
<ellipse class="cg-mv cg-mv-o" cx="60" cy="66.5" rx="2.7" ry="3.5" fill="#9e4a5e"/>
<ellipse class="cg-mv cg-mv-song" cx="60" cy="66.5" rx="2.4" ry="2.9" fill="#9e4a5e"/>
<g class="cg-mv cg-mv-yawn"><ellipse cx="60" cy="67.5" rx="5.6" ry="6.6" fill="#8a4050"/><ellipse cx="60" cy="69.8" rx="3.3" ry="3" fill="#e58ea0"/></g>
<path class="cg-mv cg-mv-munch" d="M55.5 66.5 q2.2 -2.5 4.5 0 q2.2 2.5 4.5 0" fill="none" stroke="#c26375" stroke-width="2.2" stroke-linecap="round"/>
<path class="cg-mv cg-mv-tee" d="M55.5 66.8 q2.2 2.6 4.5 0 q2.2 -2.6 4.5 0" fill="none" stroke="#c26375" stroke-width="2.1" stroke-linecap="round"/>
<path class="cg-mv cg-mv-focus" d="M56.5 66.6 h7" fill="none" stroke="#c26375" stroke-width="2.3" stroke-linecap="round"/>
<g class="cg-glass" fill="none" stroke="#7a6a75" stroke-width="2"><circle cx="45" cy="56" r="9.6"/><circle cx="75" cy="56" r="9.6"/><path d="M54.6 55.5 h10.8"/><path d="M35.4 54.5 L28.5 50.5"/><path d="M84.6 54.5 L91.5 50.5"/><path d="M40 50 q5 -3.6 10 -1.2" stroke="#ffffff" stroke-width="2.6" opacity=".9"/><path d="M70 50 q5 -3.6 10 -1.2" stroke="#ffffff" stroke-width="2.6" opacity=".9"/></g>
<g class="cg-shyhands"><circle cx="36" cy="68" r="6.6" fill="#ffe9dc"/><circle cx="84" cy="68" r="6.6" fill="#ffe9dc"/><path d="M33 71.3 q3 2.2 6 .6" fill="none" stroke="#e8b9a4" stroke-width="1.2" stroke-linecap="round"/><path d="M81 71.3 q3 2.2 6 .6" fill="none" stroke="#e8b9a4" stroke-width="1.2" stroke-linecap="round"/></g>
<g class="cg-shyblush"><ellipse cx="34" cy="66" rx="7" ry="3.8" fill="#ffb0bc" opacity=".92"/><ellipse cx="86" cy="66" rx="7" ry="3.8" fill="#ffb0bc" opacity=".92"/><circle cx="25" cy="40" r="3" fill="#ffc9d4" opacity=".85"/><circle cx="95" cy="38" r="3.4" fill="#ffc9d4" opacity=".85"/></g>
<g class="cg-hand-chin"><path d="M73 98 Q71 88 70.5 81" fill="none" stroke="#f4a9b8" stroke-width="10.5" stroke-linecap="round"/><circle cx="70.5" cy="80.5" r="6.2" fill="#ffe9dc"/><path d="M67.5 79.5 q3 -1.5 6 0" fill="none" stroke="#e8b9a4" stroke-width="1.2" stroke-linecap="round"/></g>
<g class="cg-sweat"><path d="M112 29 q5.5 7.5 0 11.5 q-5.5 -4 0 -11.5" fill="#7ec8f2"/></g>
<g class="cg-tears"><ellipse cx="41" cy="63.5" rx="2.6" ry="4.4" fill="#7ec8f2"/><ellipse cx="79" cy="63.5" rx="2.6" ry="4.4" fill="#7ec8f2"/></g>
<g class="cg-spark" fill="#ffd86b"><path d="M24 42 l1.5 3.7 3.7 1.5 -3.7 1.5 -1.5 3.7 -1.5 -3.7 -3.7 -1.5 3.7 -1.5 Z"/><path d="M94 34 l1.2 3 3 1.2 -3 1.2 -1.2 3 -1.2 -3 -3 -1.2 3 -1.2 Z"/></g>
<g class="cg-anger" stroke="#ff3d2e" stroke-width="3.2" stroke-linecap="round" fill="none"><path d="M109 4 L114 9"/><path d="M118 4 L113 9"/><path d="M109 20 L114 15"/><path d="M118 20 L113 15"/></g>
<g class="cg-steam" fill="#dfe4ec"><circle cx="109" cy="34" r="4.6"/><circle cx="116" cy="45" r="3.2"/></g>
</g>
<g class="cg-snack"><g transform="translate(-5,0)"><path d="M84 101 Q80 93 76 88" fill="none" stroke="#d97a90" stroke-width="13" stroke-linecap="round"/><path d="M84 101 Q80 93 76 88" fill="none" stroke="#f4a9b8" stroke-width="10" stroke-linecap="round"/><g transform="translate(75.5,86)"><circle r="6.2" fill="#ffe9dc"/><path d="M-3.4 2.2 q3.4 2.3 6.8 0" fill="none" stroke="#e8b9a4" stroke-width="1.2" stroke-linecap="round"/><path d="M-2.6 -1.5 q1 -2 1.9 -2.2 M.4 -2.1 q1 -2 1.9 -2.2" stroke="#e8b9a4" stroke-width="1" fill="none" stroke-linecap="round"/></g><g transform="translate(66.5,75.5) scale(1.32) translate(-66.5,-75.5)"><g class="fish"><path d="M58 77 Q64 68 74 69.5 Q81 71 82.5 75.5 Q81 80 74 81.5 Q64 83 58 77 Z" fill="#eab26b" stroke="#c9944e" stroke-width="1.5"/><path d="M58 77 L50.5 72.5 L52 82 Z" fill="#eab26b" stroke="#c9944e" stroke-width="1.3" stroke-linejoin="round"/><circle cx="77.6" cy="73.3" r="1.5" fill="#6d4a26"/><path d="M67.5 71.5 q2 2 .4 4 M71 71 q2 2 .4 4 M74.5 71.5 q2 2 .4 4" fill="none" stroke="#c9944e" stroke-width="1.1" stroke-linecap="round"/><path d="M65.5 79.5 q4.5 2.5 8.5 .5" fill="none" stroke="#c9944e" stroke-width="1" stroke-linecap="round"/><path d="M79.5 70 a3.4 3.4 0 0 0 -2.6 4.8" fill="none" stroke="#fff6e8" stroke-width="2.4" stroke-linecap="round"/></g></g></g></g>
<g class="cg-crumbs" fill="#b58a45"><circle cx="54" cy="84" r="1.8"/><circle cx="49.5" cy="89" r="1.5"/><circle cx="58" cy="90" r="1.6"/></g>
<g class="cg-music"><g class="n1"><ellipse cx="106" cy="28" rx="3.2" ry="2.4" transform="rotate(-20 106 28)" fill="#ff9ec4"/><path d="M109.1 27 L109.1 15 q4.2 1.4 4.2 5.6" fill="none" stroke="#ff9ec4" stroke-width="1.8" stroke-linecap="round"/></g><g class="n2"><ellipse cx="113.5" cy="41" rx="2.8" ry="2.1" transform="rotate(-20 113.5 41)" fill="#ff9ec4"/><path d="M115.8 40.3 L115.8 30 q3.7 1.2 3.7 4.9" fill="none" stroke="#ff9ec4" stroke-width="1.6" stroke-linecap="round"/></g></g>
<g class="cg-ball"><circle cx="92" cy="100" r="7.5" fill="#fdfdfd" stroke="#d95970" stroke-width="2.2"/><path d="M84.5 100 a7.5 7.5 0 0 1 15 0 Z" fill="#d95970"/></g>
<path class="cg-heart" d="M97 22s-8-4.5-8-11a4 4 0 018-1 4 4 0 018 1c0 6.5-8 11-8 11z" fill="#ff5d78"/>
</g>
<g class="cg-zzz" fill="#cfd2da" font-family="system-ui,sans-serif" font-weight="700"><text x="103" y="40" font-size="8">z</text><text x="111" y="30" font-size="11">Z</text></g>
<g class="cg-think" fill="#a9c0dd"><circle cx="104" cy="32" r="2"/><circle cx="110" cy="25" r="2.6"/><circle cx="116" cy="17" r="3.2"/></g>
<g class="cg-rumble" stroke="#e2a2b2" fill="none" stroke-width="2.4" stroke-linecap="round"><path class="r1" d="M42 111 q-8 3 -9 12"/><path class="r2" d="M78 111 q8 3 9 12"/><path class="r3" d="M60 119 q0 6 0 9"/><text class="rt" x="60" y="132" text-anchor="middle" font-size="7" font-weight="800" fill="#e2a2b2" stroke="none" font-family="system-ui,sans-serif">قار قور!</text></g>
<g class="cg-wall">
<rect x="71" y="-2" width="49" height="144" fill="#b7aa92"/>
<rect x="71" y="-2" width="49" height="7" rx="3.5" fill="#998b70"/>
<rect x="71" y="-2" width="2.4" height="144" fill="#d0c2a6"/>
<rect x="73.4" y="-2" width="1.4" height="144" fill="rgba(0,0,0,.22)"/>
<path d="M66 96 Q80 90 86 103 Q75 110 66 96 Z" fill="#bcd9f2" stroke="#9fc4ea" stroke-width="2"/>
<circle cx="82.5" cy="103" r="3.4" fill="#9fc4ea"/>
<g><path d="M65 55 q6.5 -6 14 -1.5 q1.5 6 -4.5 7.5 q-8 1.5 -9.5 -6 Z" fill="#f4a9b8"/><circle cx="78" cy="64" r="6.5" fill="#ffe9dc" stroke="#e8b9a4" stroke-width="1.3"/><path d="M74.9 69 l-.5 2.8 M78 69.4 l.2 2.8" stroke="#e8b9a4" stroke-width="1.6" stroke-linecap="round"/></g>
<g><path d="M66 71 q6.5 -6 14 -1.5 q1.5 6 -4.5 7.5 q-8 1.5 -9.5 -6 Z" fill="#f4a9b8"/><circle cx="79" cy="80" r="6.5" fill="#ffe9dc" stroke="#e8b9a4" stroke-width="1.3"/><path d="M75.9 85 l-.5 2.8 M79 85.4 l.2 2.8" stroke="#e8b9a4" stroke-width="1.6" stroke-linecap="round"/></g>
</g>
</svg>
<div class="mcat-say"></div>
</div>
<div id="cmp">
  <div class="cmp-stage" id="cmpStage">
    <img id="cmpA" alt="بعد — ترجمه‌شده" draggable="false">
    <div id="cmpBWrap"><img id="cmpB" alt="قبل — اصلی" draggable="false"></div>
    <div id="cmpDiv"><span class="cmp-h">⇔</span></div>
    <span class="cmp-lab b">قبل</span>
    <span class="cmp-lab a">بعد</span>
    <div class="cmp-tchip" id="cmpT">صفحهٔ ۱</div>
  </div>
</div>

<div id="mcatOff" aria-hidden="true">
<svg class="off-eyes" viewBox="0 0 150 58" aria-hidden="true"><defs><radialGradient id="mcOffG"><stop offset="0" stop-color="#ffd964" stop-opacity=".55"/><stop offset=".55" stop-color="#ffd964" stop-opacity=".2"/><stop offset="1" stop-color="#ffd964" stop-opacity="0"/></radialGradient></defs><path d="M28 24 L33 8 L44 19 Z" fill="#ffd964" opacity=".38"/><path d="M122 24 L117 8 L106 19 Z" fill="#ffd964" opacity=".38"/><g><ellipse cx="40" cy="36" rx="34" ry="19" fill="url(#mcOffG)"/><path d="M16 36 Q40 18 64 36 Q40 52 16 36 Z" fill="#ffd964"/><circle cx="32" cy="33" r="3.2" fill="#fff" opacity=".95"/><circle cx="48" cy="39" r="2.1" fill="#fff" opacity=".75"/></g><g><ellipse cx="110" cy="36" rx="34" ry="19" fill="url(#mcOffG)"/><path d="M86 36 Q110 18 134 36 Q110 52 86 36 Z" fill="#ffd964"/><circle cx="102" cy="33" r="3.2" fill="#fff" opacity=".95"/><circle cx="118" cy="39" r="2.1" fill="#fff" opacity=".75"/></g></svg>
<div class="off-t1">دخترِ گربه‌ای خسته شد!</div>
<div class="off-t2">صفحه رو خاموش کرد… دیگه اذیت نکن!</div>
<div class="off-t3">برای روشن‌کردن، صفحه را لمس کن</div>
</div>
<script>
function UT(k,d){try{var t=window.UI_T;return (t&&t[k]!=null)?t[k]:d}catch(e){return d}}
(function(){
  var P = "__PREFIX__", D = "__DIR__", DBG = "__DBGDIR__", RUN = "__RUN__";
  function ck(u){ return RUN + '|' + u; }
  var cF = document.getElementById('cF'), cD = document.getElementById('cD'),
      hF = document.getElementById('hF'), hD = document.getElementById('hD');
  var arrived = 0, total = 0, dbgArrived = 0, dbgMode = false, busy = false;
  var haveDbg = !!DBG, dbgTotal = -1;
  function pad(i){ return ('000' + i).slice(-4); }
  function curCont(){ return dbgMode ? cD : cF; }
  function imgSrc(i, dbg){ return P + (dbg ? DBG : D) + 'live_' + pad(i + 1)
                           + (dbg ? '_base.jpg' : '.jpg'); }
  function bakedSrc(i){ return P + D + 'live_' + pad(i + 1) + '.jpg'; }
  function sliceMark(i){ return P + D + 'w_' + pad(i + 1) + '.json'; }
  function sliceUrl(i, k){ return P + D + 'w_' + pad(i + 1) + '_' + k + '.jpg'; }
  var sliceMem = {};
  function slicesFor(i, fresh){
    var now = Date.now();
    var m = sliceMem[i];
    if (!fresh && m && (now - m.t) < 5000)
      return Promise.resolve(m.ok ? m : null);
    return fetch(sliceMark(i) + '?r=' + now, { cache: 'no-store' })
      .then(function(r){ if (!r.ok) throw 0; return r.json(); })
      .then(function(j){
        m = { n: (parseInt(j && j.n, 10) || 0),
              src: (parseInt(j && j.src, 10) || 0),
              t: Date.now(), ok: true };
        sliceMem[i] = m;
        return m;
      })
      .catch(function(){
        sliceMem[i] = { n: 0, src: 0, t: Date.now(), ok: false };
        return null;
      });
  }

  var idbOK = true, _db = null;
  function idb(){
    if (!idbOK) return Promise.resolve(null);
    if (_db) return Promise.resolve(_db);
    return new Promise(function(res){
      try {
        var q = indexedDB.open('mangaLiveCache', 1);
        q.onupgradeneeded = function(e){
          var d = e.target.result;
          if (!d.objectStoreNames.contains('imgs')) d.createObjectStore('imgs');
          if (!d.objectStoreNames.contains('ovls')) d.createObjectStore('ovls');
        };
        q.onsuccess = function(e){ _db = e.target.result; res(_db); };
        q.onerror = function(){ idbOK = false; res(null); };
        q.onblocked = function(){ res(null); };
      } catch (e) { idbOK = false; res(null); }
    });
  }
  function idbGet(st, k){
    return idb().then(function(d){
      if (!d) return undefined;
      return new Promise(function(res){
        try {
          var t = d.transaction(st, 'readonly').objectStore(st).get(k);
          t.onsuccess = function(){ res(t.result); };
          t.onerror = function(){ res(undefined); };
        } catch (e) { res(undefined); }
      });
    });
  }
  function idbPut(st, k, v){
    return idb().then(function(d){
      if (!d) return;
      try {
        var tx = d.transaction(st, 'readwrite');
        tx.objectStore(st).put(v, k);
        tx.oncomplete = function(){ if (st === 'imgs') prune(); };
      } catch (e) {}
    });
  }
  var _pruning = false;
  function prune(){
    if (_pruning) return;
    _pruning = true;
    idb().then(function(d){
      if (!d) { _pruning = false; return; }
      try {
        var rq = d.transaction('imgs', 'readonly').objectStore('imgs').count();
        rq.onsuccess = function(){
          var n = rq.result;
          if (n < 1600) { _pruning = false; return; }
          var tx = d.transaction('imgs', 'readonly');
          var cur = tx.objectStore('imgs').openCursor();
          var items = [];
          cur.onsuccess = function(e){
            var c2 = e.target.result;
            if (c2) { items.push([c2.key, (c2.value && c2.value.t) || 0]); c2.continue(); }
            else {
              items.sort(function(a, b){ return a[1] - b[1]; });
              var del = items.slice(0, Math.max(0, n - 1200));
              try {
                var tx2 = d.transaction('imgs', 'readwrite');
                for (var i = 0; i < del.length; i++)
                  tx2.objectStore('imgs').delete(del[i][0]);
              } catch (e3) {}
              _pruning = false;
            }
          };
        };
        rq.onerror = function(){ _pruning = false; };
      } catch (e) { _pruning = false; }
    });
  }
  var blobs = new Map(), fails = new Map();
  function imgGet(url, fresh, noFail){
    if (!fresh && blobs.has(url)) return Promise.resolve(blobs.get(url));
    if (!noFail && !fresh && fails.has(url) && (Date.now() - fails.get(url)) < 8000)
      return Promise.reject(0);
    if (fresh) fails.delete(url);
    var pre = (!fresh)
      ? idbGet('imgs', ck(url)).then(function(hit){
          if (hit && hit.b) {
            var u = URL.createObjectURL(hit.b);
            blobs.set(url, u);
            return u;
          }
          return null;
        })
      : Promise.resolve(null);
    return pre.then(function(u){
      if (u) return u;
      return fetch(url + (fresh ? ('?r=' + Date.now()) : ''),
                   fresh ? { cache: 'no-store' } : {})
        .then(function(r){ if (!r.ok) throw 0; return r.blob(); })
        .then(function(b){
          idbPut('imgs', ck(url), { b: b, t: Date.now() });
          var u2 = URL.createObjectURL(b);
          blobs.set(url, u2);
          return u2;
        })
        .catch(function(e){ fails.set(url, Date.now()); throw e; });
    });
  }
  var ovlMem = new Map();
  function ovlGet(url, fresh){
    if (!fresh && ovlMem.has(url)) return Promise.resolve(ovlMem.get(url));
    var pre = (!fresh)
      ? idbGet('ovls', ck(url)).then(function(h){ return (h && h.j) ? h.j : null; })
      : Promise.resolve(null);
    return pre.then(function(j){
      if (j) { ovlMem.set(url, j); return j; }
      return fetch(url + (fresh ? ('?r=' + Date.now()) : ''),
                   fresh ? { cache: 'no-store' } : {})
        .then(function(r){ if (!r.ok) throw 0; return r.json(); })
        .then(function(j2){
          ovlMem.set(url, j2);
          idbPut('ovls', ck(url), { j: j2, t: Date.now() });
          return j2;
        });
    });
  }

  // نسبتِ واقعیِ صفحه از اولین تصویرِ لودشده یاد گرفته میشود و روی
  // placeholderهای بعدی اعمال میشود — وگرنه placeholder با نسبتِ ثابتِ
  // ۲:3 جایگزینِ تصویرِ واقعی می‌شد و محتوای زیرش با هر استخراج جابه‌جا
  // می‌شد (همان «هی می‌پره»). صفحاتِ یک فصل معمولاً هم‌نسبت‌اند.
  var phAR = '';
  function phApply(d){
    if (phAR) { try { d.style.aspectRatio = phAR; } catch (e) {} }
  }
  function mkPh(){
    var d = document.createElement('div');
    d.className = 'ph';
    phApply(d);
    d.innerHTML = '<span class="sp"></span>' + UT('rdr.translating', 'در حال ترجمه…');
    return d;
  }
  function learnAR(node){
    try {
      if (phAR || !node) return;
      if (node.classList && node.classList.contains('slotw')) return;
      var im = (node.tagName === 'IMG') ? node
        : (node.querySelector ? node.querySelector('img') : null);
      if (!im || im.naturalWidth < 2 || im.naturalHeight < 2) return;
      phAR = im.naturalWidth + '/' + im.naturalHeight;
      var cs = [cF, cD];
      for (var ci = 0; ci < cs.length; ci++) {
        var phs = cs[ci].querySelectorAll('.ph');
        for (var pi = 0; pi < phs.length; pi++) phApply(phs[pi]);
      }
    } catch (e) {}
  }
  var SVGNS = 'http://www.w3.org/2000/svg';
  function svgEl(t, at){
    var e = document.createElementNS(SVGNS, t);
    for (var k in at) e.setAttribute(k, at[k]);
    return e;
  }
  function buildOvlSvg(j){
    var W = (j.size && j.size[0]) || 900, H = (j.size && j.size[1]) || 1200;
    var svg = svgEl('svg', {'class': 'dovl', 'viewBox': '0 0 ' + W + ' ' + H,
                            'preserveAspectRatio': 'none'});
    var gDet = svgEl('g', {'class': 'g-det'});
    var gPdet = svgEl('g', {'class': 'g-pdet'});
    var gRec = svgEl('g', {'class': 'g-rec'});
    if (j.det) {
      var sw = Math.max(2, W / 300), fs = Math.max(12, Math.round(W / 45));
      for (var i = 0; i < j.det.length; i++) {
        var d = j.det[i];
        gDet.appendChild(svgEl('rect', {
          x: d[0], y: d[1], width: Math.max(1, d[2] - d[0]),
          height: Math.max(1, d[3] - d[1]),
          fill: 'none', stroke: '#00e640', 'stroke-width': sw}));
        var t = svgEl('text', {x: d[0] + 4, y: d[1] + Math.max(12, fs),
                               fill: '#00e640', 'font-size': fs,
                               'font-weight': 'bold',
                               'font-family': 'sans-serif'});
        t.textContent = 'D' + ('0' + i).slice(-2) + ' ' + (d[4] || '');
        gDet.appendChild(t);
      }
    }
    if (j.pdet) {
      var sw2 = Math.max(2, W / 340);
      for (var k = 0; k < j.pdet.length; k++) {
        var q = j.pdet[k];
        if (!q || q.length < 2) continue;
        var pts = [];
        for (var p2 = 0; p2 < q.length; p2++) pts.push(q[p2][0] + ',' + q[p2][1]);
        gPdet.appendChild(svgEl('polygon', {points: pts.join(' '),
                                            fill: 'none', stroke: '#3a8bff',
                                            'stroke-width': sw2}));
      }
    }
    if (j.rec) {
      var sw3 = Math.max(1.5, W / 380), fs2 = Math.max(11, Math.round(W / 50));
      for (var m = 0; m < j.rec.length; m++) {
        var r = j.rec[m];
        var col = (r[4] === 'promo') ? '#ff9f0a' : '#ff3b30';
        gRec.appendChild(svgEl('rect', {x: r[0], y: r[1],
                                        width: Math.max(1, r[2]),
                                        height: Math.max(1, r[3]),
                                        fill: 'none', stroke: col,
                                        'stroke-width': sw3}));
        if (r[5]) {
          var t2 = svgEl('text', {x: r[0],
                                  y: Math.max(fs2, r[1] - Math.round(W / 42)),
                                  fill: (r[4] === 'promo') ? '#ff9f0a' : '#ffd60a',
                                  'font-size': fs2,
                                  'font-family': 'sans-serif'});
          t2.textContent = ('[' + m + '] ' + r[5]).slice(0, 44);
          gRec.appendChild(t2);
        }
      }
    }
    svg.appendChild(gDet); svg.appendChild(gPdet); svg.appendChild(gRec);
    return svg;
  }
  function putOvl(el, j){
    try {
      var old = el.querySelectorAll('svg.dovl');
      for (var i = 0; i < old.length; i++) {
        if (old[i].parentNode === el) el.removeChild(old[i]);
      }
      el.appendChild(buildOvlSvg(j));
    } catch (e) {}
  }
  var ovlBusy = {};
  function ensureOvl(slot){
    var el = cD.children[slot - 1];
    if (!el || !el.classList || !el.classList.contains('dslot') || !el.__ok) return;
    if (el.querySelector('svg.dovl')) return;
    if (ovlBusy[slot]) return;
    ovlBusy[slot] = 1;
    ovlGet(P + DBG + 'live_' + pad(slot) + '.json')
      .then(function(j){ putOvl(el, j); ovlBusy[slot] = 0; })
      .catch(function(){ ovlBusy[slot] = 0; });
  }
  function slotFilled(el){
    return !!(el && el.__ok);
  }
  function fillSlot(cont, i){
    var cur = cont.children[i];
    if (!cur || slotFilled(cur) || cur.__pend) return;
    if (cur.__failT && (Date.now() - cur.__failT) < 8000) return;
    var dbg = (cont === cD);
    var node = null, im = null;
    cur.__pend = 1;
    var placed = false;
    var place = function(ok){
      if (placed) return;
      placed = true;
      var c2 = cont.children[i];
      if (ok && c2 === cur) {
        cont.replaceChild(node, cur);
        node.__ok = 1;
        learnAR(node);
        if (dbg) ensureOvl(i + 1);
      } else if (!ok) {
        cur.__pend = 0;
        cur.__failT = Date.now();
      }
    };
    if (dbg) {
      node = document.createElement('div');
      node.className = 'dslot';
      im = document.createElement('img');
      im.alt = 'صفحهٔ ' + (i + 1);
      im.decoding = 'async';
      node.appendChild(im);
      im.onload = function(){ place(1); };
      im.onerror = function(){
        if (String(im.getAttribute('src') || '').indexOf('_base') >= 0) {
          node.__baked = 1;
          placed = false;
          imgGet(bakedSrc(i)).then(function(u){ im.src = u; })
            .catch(function(){ im.src = bakedSrc(i); });
          im.onerror = function(){ place(0); };
          return;
        }
        place(0);
      };
      imgGet(imgSrc(i, true))
        .then(function(u){ im.src = u; if (im.complete && im.naturalWidth > 0) place(1); })
        .catch(function(){ im.src = imgSrc(i, true); });
    } else {
      slicesFor(i).then(function(sl){
        if (placed) return;
        if (sl && sl.n > 0) {
          node = document.createElement('div');
          node.className = 'slotw';
          node.__n = sl.n;
          var firstIm = null;
          for (var k = 1; k <= sl.n; k++) {
            (function(kk){
              var im2 = document.createElement('img');
              im2.alt = 'صفحهٔ ' + (i + 1) + ' — ' + kk + '/' + sl.n;
              im2.decoding = 'async';
              node.appendChild(im2);
              if (kk === 1) firstIm = im2;
              imgGet(sliceUrl(i, kk)).then(function(u){ im2.src = u; })
                .catch(function(){ im2.src = sliceUrl(i, kk); });
            })(k);
          }
          if (firstIm) {
            firstIm.onload = function(){ place(1); };
            firstIm.onerror = function(){ place(0); };
          } else { place(0); }
        } else {
          im = document.createElement('img');
          im.alt = 'صفحهٔ ' + (i + 1);
          im.decoding = 'async';
          node = im;
          im.onload = function(){ place(1); };
          im.onerror = function(){ place(0); };
          imgGet(imgSrc(i, false))
            .then(function(u){ im.src = u; if (im.complete && im.naturalWidth > 0) place(1); })
            .catch(function(){ im.src = imgSrc(i, false); });
        }
      });
    }
  }
  var b = document.getElementById('n'), dot = document.getElementById('dot');
  function render(){
    var cont = dbgMode ? cD : cF, hEl = dbgMode ? hD : hF;
    var a = dbgMode ? dbgArrived : arrived;
    var want = Math.max(total, a);
    if (hEl && hEl.parentNode === cont && (a > 0 || total > 0)) {
      cont.removeChild(hEl);
    }
    while (cont.children.length < want) cont.appendChild(mkPh());
    for (var i = 0; i < want && i < a; i++)
      fillSlot(cont, i);
    b.textContent = a + (total > 0 ? ' / ' + total : '');
    var fin = (total > 0 && a >= total);
    b.className = 'n' + (fin ? ' done' : '');
    dot.className = 'dot' + (fin ? ' off' : '');
  }

  function setMode(dbg){
    if (dbg && !haveDbg) return;
    if (dbg === dbgMode) return;
    dbgMode = dbg;
    cF.classList.toggle('hide', dbgMode);
    cD.classList.toggle('hide', !dbgMode);
    applyOv();
    updateFabVis();
    updateFan();
    render();
    probe();
  }
  function updateFabVis(){
    var mt = document.getElementById('mtoggle');
    if (mt) {
      mt.style.display = haveDbg ? '' : 'none';
      mt.textContent = dbgMode ? UT('rdr.final', 'نهایی') : UT('rdr.debug', 'دیباگ');
      if (dbgMode) mt.classList.add('hot'); else mt.classList.remove('hot');
    }
    var show = !!(dbgMode && haveDbg);
    fab.style.display = show ? '' : 'none';
    if (!show) {
      fanState = 0;
      updateFan();
      if (cmpOn) cmpClose();
    }
  }
  var ov = { det: 1, pdet: 1, rec: 1 };
  try {
    var _so = JSON.parse(localStorage.getItem('mangaLiveOv') || 'null');
    if (_so && typeof _so === 'object')
      ov = { det: _so.det ? 1 : 0, pdet: _so.pdet ? 1 : 0, rec: _so.rec ? 1 : 0 };
  } catch (e) {}
  function saveOv(){
    try { localStorage.setItem('mangaLiveOv', JSON.stringify(ov)); } catch (e) {}
  }
  function applyOv(){
    cD.classList.toggle('no-det', !ov.det);
    cD.classList.toggle('no-pdet', !ov.pdet);
    cD.classList.toggle('no-rec', !ov.rec);
  }
  applyOv();

  var fab = document.getElementById('fab');
  var fanState = 0;
  var fans = [];
  var fanDefs = [
    { key: 'det', ic: '◫', lb: UT('rdr.fan_det', 'det') },
    { key: 'pdet', ic: '◺', lb: UT('rdr.fan_pdet', 'p-det') },
    { key: 'rec', ic: '▤', lb: UT('rdr.fan_rec', 'rec') },
    { key: 'cmp', ic: '⇄', lb: UT('rdr.fan_cmp', 'قبل/بعد') },
    { key: 'prev', ic: '‹', lb: UT('rdr.fan_prev', 'قبلی'), cmpOnly: true },
    { key: 'next', ic: '›', lb: UT('rdr.fan_next', 'بعدی'), cmpOnly: true }
  ];
  for (var fi = 0; fi < fanDefs.length; fi++) {
    var fb = document.createElement('button');
    fb.type = 'button';
    fb.className = 'fbtn';
    fb.innerHTML = '<span class="ic"></span><span class="lb"></span>';
    fb.setAttribute('data-k', fanDefs[fi].key);
    document.body.appendChild(fb);
    fans.push(fb);
  }
  (function(){
    var px = null;
    try { px = JSON.parse(localStorage.getItem('mangaLiveFabPos2') || 'null'); } catch (e) {}
    if (px && typeof px.x === 'number' && typeof px.y === 'number') {
      placeFabXY(px.x, px.y);
    }
  })();
  var mtEl = document.getElementById('mtoggle');
  if (mtEl) mtEl.addEventListener('click', function(){ setMode(!dbgMode); });
  updateFabVis();
  function placeFabXY(cx, cy){
    var r = 30;
    var x = Math.min(Math.max(cx, r + 4), window.innerWidth - r - 4);
    var y = Math.min(Math.max(cy, r + 46), window.innerHeight - r - 8);
    fab.style.left = (x - r) + 'px';
    fab.style.top = (y - r) + 'px';
    fab.style.right = 'auto';
    fab.style.bottom = 'auto';
    fab.style.marginLeft = '0';
  }
  var fdrag = null;
  fab.addEventListener('pointerdown', function(e){
    fdrag = { x: e.clientX, y: e.clientY, moved: false, id: e.pointerId };
    try { fab.setPointerCapture(e.pointerId); } catch (e2) {}
    e.preventDefault();
  });
  fab.addEventListener('pointermove', function(e){
    if (!fdrag) return;
    var dx = e.clientX - fdrag.x, dy = e.clientY - fdrag.y;
    if (!fdrag.moved && Math.hypot(dx, dy) > 10) fdrag.moved = true;
    if (fdrag.moved) {
      fdrag.x = e.clientX; fdrag.y = e.clientY;
      placeFabXY(e.clientX, e.clientY);
      updateFan();
    }
  });
  function fabUp(e){
    if (!fdrag) return;
    var moved = fdrag.moved;
    fdrag = null;
    if (moved) {
      try {
        var fr = fab.getBoundingClientRect();
        localStorage.setItem('mangaLiveFabPos2',
          JSON.stringify({ x: fr.left + fr.width / 2, y: fr.top + fr.height / 2 }));
      } catch (e2) {}
      return;
    }
    fanState = fanState ? 0 : 1;
    updateFan();
  }
  fab.addEventListener('pointerup', fabUp);
  fab.addEventListener('pointercancel', function(){ fdrag = null; });
  function fanPositions(){
    var fr = fab.getBoundingClientRect();
    var cx = fr.left + fr.width / 2, cy = fr.top + fr.height / 2;
    var n = fans.length;
    var bis = Math.atan2(window.innerHeight / 2 - cy,
                        window.innerWidth / 2 - cx);
    var step = Math.min(40 * Math.PI / 180, 2.6 / Math.max(1, n - 1));
    var half = step * (n - 1) / 2;
    var R = Math.min(104, Math.max(84, window.innerWidth * 0.16));
    var pts = [];
    for (var i0 = 0; i0 < n; i0++) {
      var a = bis - half + i0 * step;
      pts.push({ x: cx + Math.cos(a) * R, y: cy + Math.sin(a) * R });
    }
    var fabPt = { x: cx, y: cy };
    var sep = function(pa, pb, w){
      var dx = pb.x - pa.x, dy = pb.y - pa.y;
      var ox = 68 - Math.abs(dx), oy = 68 - Math.abs(dy);
      if (ox > 0 && oy > 0) {
        if (ox <= oy) {
          var sx = (dx >= 0 ? 1 : -1) * ox * w;
          pa.x -= sx; pb.x += sx;
        } else {
          var sy = (dy >= 0 ? 1 : -1) * oy * w;
          pa.y -= sy; pb.y += sy;
        }
        return true;
      }
      return false;
    };
    for (var it = 0; it < 20; it++) {
      var moved = false;
      for (var i1 = 0; i1 < n; i1++) for (var j1 = i1 + 1; j1 < n; j1++)
        if (sep(pts[i1], pts[j1], 0.3)) moved = true;
      for (var i2 = 0; i2 < n; i2++) {
        var fdx = pts[i2].x - fabPt.x, fdy = pts[i2].y - fabPt.y;
        var fox = 74 - Math.abs(fdx), foy = 74 - Math.abs(fdy);
        if (fox > 0 && foy > 0) {
          if (fox <= foy) pts[i2].x += (fdx >= 0 ? 1 : -1) * fox;
          else pts[i2].y += (fdy >= 0 ? 1 : -1) * foy;
          moved = true;
        }
      }
      for (var k1 = 0; k1 < n; k1++) {
        pts[k1].x = Math.min(Math.max(pts[k1].x, 32), window.innerWidth - 32);
        pts[k1].y = Math.min(Math.max(pts[k1].y, 76), window.innerHeight - 32);
      }
      if (!moved) break;
    }
    return pts;
  }
  function updateFan(){
    var pts = fanPositions();
    var show = fanState >= 1 && haveDbg;
    fab.textContent = show ? UT('rdr.close', '✕') : UT('rdr.menu', 'منو');
    fab.classList.toggle('open', show);
    for (var i = 0; i < fans.length; i++) {
      var fb = fans[i];
      var def = fanDefs[i];
      fb.style.left = (pts[i].x - 29) + 'px';
      fb.style.top = (pts[i].y - 29) + 'px';
      var isCmp = def.key === 'cmp';
      fb.querySelector('.ic').textContent =
        (isCmp && cmpOn) ? '✕' : def.ic;
      fb.querySelector('.lb').textContent =
        (isCmp && cmpOn) ? UT('rdr.fan_close', 'بستن') : def.lb;
      fb.classList.toggle('fcmp', isCmp);
      fb.classList.toggle('on', isCmp ? !!cmpOn : !!ov[def.key]);
      fb.title = isCmp ? UT('rdr.fan_cmp_title', 'مقایسهٔ قبل/بعد') :
        (def.key === 'prev' || def.key === 'next') ? UT('rdr.fan_pp_title', 'صفحهٔ قبل/بعد در مقایسه') :
        (({ det: 'detector.onnx', pdet: 'paddle det', rec: 'paddle rec' })[def.key] || '');
      fb.classList.toggle('show', show && (!def.cmpOnly || cmpOn));
    }
  }
  for (var fj = 0; fj < fans.length; fj++) {
    (function(fb){
      fb.addEventListener('click', function(e){
        e.stopPropagation();
        var k = fb.getAttribute('data-k');
        if (k === 'cmp') { if (cmpOn) cmpClose(); else cmpOpenFn(); updateFan(); return; }
        if (k === 'prev') { cmpLoad(cmpIdx - 1); updateFan(); return; }
        if (k === 'next') { cmpLoad(cmpIdx + 1); updateFan(); return; }
        ov[k] = ov[k] ? 0 : 1;
        saveOv();
        applyOv();
        if (!dbgMode) setMode(true);
        updateFan();
      });
    })(fans[fj]);
  }

  function stackCount(){
    return Math.max(1, (dbgMode ? dbgArrived : arrived) || curCont().children.length || 1);
  }
  function curPageIdx(){
    var cont = curCont();
    var best = 0;
    for (var i = 0; i < cont.children.length; i++) {
      var ch = cont.children[i];
      var top = ch.getBoundingClientRect().top;
      if (top <= window.innerHeight * 0.35) best = i;
      else break;
    }
    return best;
  }
  function goToPage(idx){
    var cont = curCont();
    if (idx < 0) idx = 0;
    var n = cont.children.length;
    if (idx >= n) idx = n - 1;
    var ch = cont.children[idx];
    if (!ch) return;
    var top = ch.getBoundingClientRect().top + window.scrollY - 54;
    window.scrollTo(0, Math.max(0, top));
  }
  var cmpEl = document.getElementById('cmp'),
      cmpStage = document.getElementById('cmpStage'),
      cmpBWrap = document.getElementById('cmpBWrap'),
      cmpBImg = document.getElementById('cmpB'),
      cmpAImg = document.getElementById('cmpA'),
      cmpDivEl = document.getElementById('cmpDiv'),
      cmpT = document.getElementById('cmpT');
  var cmpOn = false, cmpFracV = 0.5, cmpIdx = 0;
  function cmpSet(f){
    cmpFracV = Math.min(1, Math.max(0, f));
    var pc = (cmpFracV * 100).toFixed(2) + '%';
    cmpBWrap.style.clipPath = 'inset(0 0 0 ' + pc + ')';
    try { cmpBWrap.style.webkitClipPath = 'inset(0 0 0 ' + pc + ')'; } catch (e) {}
    cmpDivEl.style.left = pc;
  }
  function cmpPages(){
    return Math.max(1, Math.max(arrived || 0, dbgArrived || 0));
  }
  function cmpLoad(idx){
    var n = cmpPages();
    cmpIdx = Math.min(Math.max(0, idx), n - 1);
    var au = imgSrc(cmpIdx, false), bu = imgSrc(cmpIdx, true);
    imgGet(au).then(function(u){ cmpAImg.src = u; })
      .catch(function(){ cmpAImg.src = au; });
    imgGet(bu).then(function(u){ cmpBImg.src = u; })
      .catch(function(){
        imgGet(bakedSrc(cmpIdx)).then(function(u){ cmpBImg.src = u; })
          .catch(function(){ cmpBImg.src = au; });
      });
    cmpT.textContent = UT('rdr.page', 'صفحهٔ ') + String(cmpIdx + 1).replace(/\d/g, function(d){ return '\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9'[+d]; }) + UT('rdr.of', ' از ') + String(n).replace(/\d/g, function(d){ return '\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9'[+d]; });
    goToPage(cmpIdx);
  }
  function cmpOpenFn(){
    cmpOn = true;
    cmpEl.classList.add('show');
    cmpLoad(curPageIdx());
    cmpSet(cmpFracV);
    fanState = 1;
    updateFan();
  }
  function cmpClose(){
    cmpOn = false;
    try { cmpEl.classList.remove('show'); } catch (e) {}
    updateFan();
  }
  var cdrag = false;
  function cmpFromX(x){
    var r = cmpStage.getBoundingClientRect();
    if (r.width < 2) return;
    cmpSet((x - r.left) / r.width);
  }
  cmpStage.addEventListener('pointerdown', function(e){
    cdrag = true;
    try { cmpStage.setPointerCapture(e.pointerId); } catch (e2) {}
    cmpFromX(e.clientX);
    e.preventDefault();
  });
  cmpStage.addEventListener('pointermove', function(e){ if (cdrag) cmpFromX(e.clientX); });
  cmpStage.addEventListener('pointerup', function(){ cdrag = false; });
  cmpStage.addEventListener('pointercancel', function(){ cdrag = false; });
  document.addEventListener('pointerdown', function(e){
    if (cmpOn) return;
    if (fanState === 0) return;
    if (e.target === fab || fab.contains(e.target)) return;
    for (var i = 0; i < fans.length; i++)
      if (fans[i].contains(e.target)) return;
    fanState = 0;
    updateFan();
  });
  document.addEventListener('keydown', function(e){
    if (e.key === 'Escape') {
      if (cmpOn) { cmpClose(); return; }
      fanState = 0; updateFan();
    }
  });

  function pollDbgTotal(){
    if (!haveDbg || dbgTotal > 0) return;
    fetch(P + DBG + 'total.txt', { cache: 'no-store' })
      .then(function(r){ return r.ok ? r.text() : ''; })
      .then(function(t){
        var v = parseInt((t || '').trim(), 10);
        if (v > 0) { dbgTotal = v; if (dbgMode) render(); }
      })
      .catch(function(){});
  }
  setInterval(pollDbgTotal, 4000);
  pollDbgTotal();
  var probeMiss = 0;
  function probe(){
    if (busy) return;
    var a = dbgMode ? dbgArrived : arrived, mode = dbgMode;
    if (total > 0 && a >= total) return;
    busy = true;
    var done = function(ok){
      busy = false;
      if (ok && dbgMode === mode) {
        if (mode) dbgArrived = Math.max(dbgArrived, a + 1);
        else arrived = Math.max(arrived, a + 1);
        render();
        setTimeout(probe, 60);
      }
    };
    if (mode) {
      // در حالتِ دیباگ، اول تصویرِ دیباگِ همان صفحه چک میشود —
      // تا هم‌زمان با استخراج (قبل از پایانِ کل کار) دیده شود؛
      // اگر نبود، تصویرِ نهایی (baked) به‌عنوان جایگزین.
      fetch(P + DBG + 'live_' + pad(a + 1) + '_base.jpg',
            { method: 'HEAD', cache: 'no-store' })
        .then(function(r){
          if (r.ok) { done(true); return; }
          fetch(bakedSrc(a), { method: 'HEAD', cache: 'no-store' })
            .then(function(r2){ done(r2.ok); })
            .catch(function(){ done(false); });
        })
        .catch(function(){
          fetch(bakedSrc(a), { method: 'HEAD', cache: 'no-store' })
            .then(function(r2){ done(r2.ok); })
            .catch(function(){ done(false); });
        });
    } else {
      fetch(sliceMark(a) + '?r=' + Date.now(), { cache: 'no-store' })
        .then(function(r){
          if (r.ok) { probeMiss = 0; done(true); return; }
          probeMiss++;
          if (probeMiss >= 12) {
            imgGet(imgSrc(a, false), false, true)
              .then(function(){ probeMiss = 0; done(true); })
              .catch(function(){ done(false); });
          } else if (probeMiss >= 5) {
            fetch(imgSrc(a, false), { method: 'HEAD', cache: 'no-store' })
              .then(function(r2){ done(r2.ok); })
              .catch(function(){ done(false); });
          } else done(false);
        })
        .catch(function(){ done(false); });
    }
  }
  function hotSwap(el, url){
    try {
      if (!el || el.tagName !== 'IMG') return;
      if (el.getAttribute('src') === url) return;
      if (el.__swapBusy) { el.__swapNext = url; return; }
      el.__swapBusy = 1;
      var par = el.parentNode;
      if (!par) { el.__swapBusy = 0; return; }
      var cov = document.createElement('img');
      cov.alt = ''; cov.draggable = false;
      cov.style.cssText = 'position:absolute;z-index:6;pointer-events:none;user-select:none;-webkit-user-drag:none;margin:0;content-visibility:visible;';
      var place = function(){
        try {
          cov.style.left = el.offsetLeft + 'px';
          cov.style.top = el.offsetTop + 'px';
          cov.style.width = el.offsetWidth + 'px';
          cov.style.height = el.offsetHeight + 'px';
        } catch (e0) {}
      };
      var cleanup = function(){
        try { cov.remove(); } catch (e4) { try { par.removeChild(cov); } catch (e6) {} }
        el.__swapBusy = 0;
        var nx = el.__swapNext; el.__swapNext = null;
        if (nx) hotSwap(el, nx);
      };
      var step2 = function(){
        try { el.onerror = function(){ cleanup(); }; } catch (e5) {}
        try { el.src = url; } catch (e3) { cleanup(); return; }
        var fin = function(){ requestAnimationFrame(cleanup); };
        if (el.decode) { el.decode().then(fin, fin); } else { setTimeout(fin, 90); }
      };
      var cover = function(){
        try {
          if (cov.naturalWidth > 1 && cov.naturalHeight > 1)
            el.style.aspectRatio = cov.naturalWidth + '/' + cov.naturalHeight;
        } catch (e2) {}
        place();
        par.appendChild(cov);
        requestAnimationFrame(step2);
      };
      cov.src = url;
      if (cov.decode) { cov.decode().then(cover, cover); }
      else { cov.onload = cover; cov.onerror = cover; }
    } catch (err) {
      try { el.src = url; } catch (e2) {}
    }
  }
  function swapFullSlot(el2, slot){
    var u = P + D + 'live_' + pad(slot) + '.jpg';
    if (el2.tagName === 'IMG') {
      imgGet(u, true)
        .then(function(w){ if (!dbgMode) hotSwap(el2, w); else el2.src = w; })
        .catch(function(){});
      return;
    }
    var im = document.createElement('img');
    im.alt = 'صفحهٔ ' + slot;
    im.decoding = 'async';
    im.onload = function(){
      try { cF.replaceChild(im, el2); im.__ok = 1; } catch (e) {}
    };
    imgGet(u, true)
      .then(function(w){ im.src = w; })
      .catch(function(){ im.src = u; });
  }
  function rebuildSlotSlices(el2, slot, n){
    var d = document.createElement('div');
    d.className = 'slotw';
    d.__n = n;
    var firstIm = null;
    for (var k = 1; k <= n; k++) {
      (function(kk){
        var im = document.createElement('img');
        im.alt = 'صفحهٔ ' + slot + ' — ' + kk + '/' + n;
        im.decoding = 'async';
        d.appendChild(im);
        if (kk === 1) firstIm = im;
        imgGet(sliceUrl(slot - 1, kk), true)
          .then(function(u){ im.src = u; })
          .catch(function(){ im.src = sliceUrl(slot - 1, kk); });
      })(k);
    }
    var swapped = false;
    var swap = function(){
      if (swapped) return;
      swapped = true;
      try { cF.replaceChild(d, el2); d.__ok = 1; } catch (e) {}
    };
    if (firstIm) {
      firstIm.onload = swap;
      setTimeout(swap, 2500);
    } else swap();
  }
  var mtF = {}, mtD = {};
  function pollMtimesDir(mm, dirKey, isDbg){
    if (!(isDbg ? dbgArrived : arrived)) return;
    fetch(P + dirKey + 'mtimes.txt?r=' + Date.now(), { cache: 'no-store' })
      .then(function(r){ return r.ok ? r.text() : ''; })
      .then(function(t){
        if (!t) return;
        var firstPass = !mm.__init;
        var lines = t.split('\n');
        var last = {};
        for (var k = 0; k < lines.length; k++) {
          var m = lines[k].trim().split(/\s+/);
          if (m.length < 2) continue;
          var s0 = parseInt(m[0], 10);
          if (s0 >= 1) last[s0] = m[1];
        }
        var cnt = isDbg ? dbgArrived : arrived;
        for (var slotStr in last) {
          var slot = parseInt(slotStr, 10);
          var mt = last[slotStr];
          if (!(slot >= 1 && slot <= cnt)) continue;
          if (mm[slot] === mt) continue;
          mm[slot] = mt;
          if (firstPass) continue;
          if (isDbg) {
            (function(slot){
              var el = cD.children[slot - 1];
              var im = el && el.querySelector ? el.querySelector('img') : null;
              if (!im) return;
              var nu = P + DBG + 'live_' + pad(slot) + '_base.jpg';
              imgGet(nu, true)
                .then(function(u){
                  if (dbgMode) hotSwap(im, u);
                  else { im.src = u; }
                })
                .catch(function(){});
              // تعویضِ اتمیِ اورلی: قبلاً svgها بلافاصله حذف و ۴۵۰ms بعد
              // دوباره ساخته می‌شدند — با هر استخراج، کادرهای دیباگ محو و
              // برمی‌گشتند («می‌ره میاد»). حالا اورلیِ تازه وقتی می‌آید که
              // json آماده است و در همان لحظه جایگزین می‌شود — بدون خلأ.
              var ojU = P + DBG + 'live_' + pad(slot) + '.json';
              ovlMem.delete(ojU);
              (function(el2, u2){
                var tries = 0;
                var go = function(){
                  ovlGet(u2, true)
                    .then(function(j){
                      if (el2 && el2.parentNode) putOvl(el2, j);
                    })
                    .catch(function(){
                      if (tries++ < 3) setTimeout(go, 700);
                    });
                };
                go();
              })(el, ojU);
            })(slot);
          } else {
            (function(slot, engMt){
              var el2 = cF.children[slot - 1];
              if (!el2) return;
              var applySlices = function(sl2){
                if (sl2 && sl2.n > 0 && sl2.src >= engMt - 400) {
                  if (el2.classList && el2.classList.contains('slotw')
                      && el2.__n === sl2.n) {
                    for (var k2 = 1; k2 <= sl2.n; k2++) {
                      (function(kk){
                        var im3 = el2.children[kk - 1];
                        if (!im3) return;
                        imgGet(sliceUrl(slot - 1, kk), true)
                          .then(function(u){
                            if (!dbgMode) hotSwap(im3, u);
                            else im3.src = u;
                          })
                          .catch(function(){});
                      })(k2);
                    }
                  } else {
                    rebuildSlotSlices(el2, slot, sl2.n);
                  }
                } else if (sl2 && sl2.n > 0) {
                  setTimeout(function(){
                    slicesFor(slot - 1, true).then(function(sl3){
                      if (sl3 && sl3.n > 0 && sl3.src >= engMt - 400)
                        applySlices(sl3);
                      else
                        swapFullSlot(el2, slot);
                    });
                  }, 450);
                } else {
                  swapFullSlot(el2, slot);
                }
              };
              slicesFor(slot - 1, true).then(applySlices);
            })(slot, parseInt(mt, 10) || 0);
          }
        }
        mm.__init = 1;
      })
      .catch(function(){});
  }
  function pollMtimes(){
    pollMtimesDir(mtF, D, false);
    if (haveDbg) pollMtimesDir(mtD, DBG, true);
  }
  function pollTotal(){
    if (total > 0) return;
    fetch(P + D + 'total.txt', { cache: 'no-store' })
      .then(function(r){ return r.ok ? r.text() : ''; })
      .then(function(t){
        var v = parseInt((t || '').trim(), 10);
        if (v > 0) { total = v; render(); }
      })
      .catch(function(){});
  }
  setInterval(function(){
    pollTotal();
    pollMtimes();
    probe();
  }, 1800);

  var zv = document.getElementById('zv'), pf = document.getElementById('pf');
  var wrap = document.getElementById('wrap');
  var z = 1, panX = 0;
  var baseW = function(){ return Math.max(200, Math.min(900, window.innerWidth || 360)); };
  // زومِ درست در صفحهٔ RTL: سند هیچ سرریزِ افقی ندارد (#vport با
  // overflow-x:clip میبُرد) و جابه‌جاییِ افقیِ محتوای زوم‌شده فقط با
  // transform روی wrap انجام میشود. لنگرِ زوم (نقطهٔ زیرِ انگشت) به‌صورتِ
  // «کسری از عرضِ wrap» محاسبه میشود که جهت‌آزاد است — قبلاً فرمول
  // مبتنی بر scrollX با فرضِ LTR بود و در RTL زوم می‌پرید پایین‌سمت‌راست.
  var applyZoom = function(nz, cx, cy){
    nz = Math.min(4, Math.max(0.5, +nz || 1));
    var vw = window.innerWidth || 360;
    var sx = (typeof cx === 'number') ? cx : (vw / 2);
    var sy = (typeof cy === 'number') ? cy : (window.innerHeight / 2);
    var r0 = wrap.getBoundingClientRect();
    var topDoc = r0.top + window.scrollY;
    var oldW = Math.max(1, r0.width || 1);
    var frX = Math.max(0, Math.min(1, (sx - r0.left) / oldW));
    var relY = (window.scrollY + sy - topDoc) / Math.max(0.01, z);
    z = nz;
    var newW = Math.round(baseW() * z);
    wrap.style.maxWidth = 'none';
    wrap.style.width = newW + 'px';
    wrap.style.marginLeft = 'auto';
    wrap.style.marginRight = 'auto';
    if (newW > vw) {
      var r1 = wrap.getBoundingClientRect();
      var wantLeft = sx - frX * newW;
      panX = Math.max(0, Math.min(newW - vw, panX + (wantLeft - r1.left)));
      wrap.style.transform = 'translateX(' + Math.round(panX) + 'px)';
    } else {
      panX = 0;
      wrap.style.transform = '';
    }
    window.scrollTo(0, Math.max(0, topDoc + relY * z - sy));
    if (zv) zv.textContent = Math.round(z * 100) + '%';
  };
  var zi = document.getElementById('zi'), zo = document.getElementById('zo'),
      zf = document.getElementById('zf');
  if (zi) zi.addEventListener('click', function(){ applyZoom(z * 1.25); });
  if (zo) zo.addEventListener('click', function(){ applyZoom(z * 0.8); });
  if (zf) zf.addEventListener('click', function(){ applyZoom(1); });
  window.addEventListener('wheel', function(e){
    if (!e.ctrlKey && !e.metaKey) return;
    e.preventDefault();
    applyZoom(z * (e.deltaY < 0 ? 1.12 : 1 / 1.12), e.clientX, e.clientY);
  }, { passive: false });
  document.addEventListener('keydown', function(e){
    if (e.key === '+' || e.key === '=') applyZoom(z * 1.15);
    else if (e.key === '-' || e.key === '_') applyZoom(z * 0.87);
    else if (e.key === '0') applyZoom(1);
  });
  // زومِ لمسی (اندروید/موبایل): دوانگشت = زوم، یک‌انگشت وقتی زوم
  // است = جابه‌جایی، دوضربه = زومِ روشن/خاموش — با touch-action:pan-y
  // روی body، مرورگر ژستِ pinch را به دستِ همین کد میسپارد.
  // applyZoom در هر touchmove اجرا می‌شد (چندبار در هر فریم) و هر بار
  // relayout کاملِ صفحه می‌داد — روی گوشی لگ می‌گرفت. حالا با rAF
  // در هر فریم فقط یک‌بار (آخرین مقدار) اعمال می‌شود.
  var _zqArg = null, _zqRaf = 0;
  var applyZoomQ = function(nz, cx, cy){
    _zqArg = [nz, cx, cy];
    if (_zqRaf) return;
    _zqRaf = requestAnimationFrame(function(){
      _zqRaf = 0;
      var q = _zqArg; _zqArg = null;
      if (q) applyZoom(q[0], q[1], q[2]);
    });
  };
  var pinch = null, pan = null, lastTapT = 0, lastTapX = 0, lastTapY = 0;
  var tDist = function(a, b){ return Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY); };
  var tMid = function(a, b){ return { x: (a.clientX + b.clientX) / 2, y: (a.clientY + b.clientY) / 2 }; };
  var tapOnCtl = function(t){
    try { return !!(t && t.closest && t.closest('button, a, input, select, textarea, .zbtn, .fbtn')); }
    catch (e) { return false; }
  };
  document.addEventListener('touchstart', function(e){
    if (e.touches.length === 2) {
      pinch = { startDist: tDist(e.touches[0], e.touches[1]), startZ: z };
      pan = null;
    } else if (e.touches.length === 1) {
      pan = { x: e.touches[0].clientX, y: e.touches[0].clientY,
              st: window.scrollY, px: panX, moved: false };
    }
  }, { passive: true });
  document.addEventListener('touchmove', function(e){
    if (pinch && e.touches.length === 2) {
      e.preventDefault();
      var d = tDist(e.touches[0], e.touches[1]);
      var m = tMid(e.touches[0], e.touches[1]);
      applyZoomQ(pinch.startZ * (d / Math.max(1, pinch.startDist)), m.x, m.y);
    } else if (pan && e.touches.length === 1) {
      var t = e.touches[0];
      var dx = t.clientX - pan.x, dy = t.clientY - pan.y;
      if (Math.abs(dx) > 12 || Math.abs(dy) > 12)
        pan.moved = true;
      if (z > 1.05) {
        e.preventDefault();
        var vw2 = window.innerWidth || 360;
        var w2 = wrap.offsetWidth || 0;
        if (w2 > vw2) {
          panX = Math.max(0, Math.min(w2 - vw2, pan.px + dx));
          wrap.style.transform = 'translateX(' + Math.round(panX) + 'px)';
        }
        window.scrollTo(0, Math.max(0, pan.st - dy));
      }
    }
  }, { passive: false });
  document.addEventListener('touchend', function(e){
    if (e.touches.length < 2) pinch = null;
    if (e.touches.length === 0) {
      var ct = (e.changedTouches && e.changedTouches[0]) || null;
      if (pan && !pan.moved && ct && !tapOnCtl(ct.target)) {
        var now = Date.now();
        if (now - lastTapT <= 320
            && Math.abs(ct.clientX - lastTapX) < 44
            && Math.abs(ct.clientY - lastTapY) < 44) {
          if (z > 1.3) applyZoom(1, ct.clientX, ct.clientY);
          else applyZoom(2.2, ct.clientX, ct.clientY);
          lastTapT = 0;
        } else {
          lastTapT = now; lastTapX = ct.clientX; lastTapY = ct.clientY;
        }
      }
      pan = null;
    }
  });
  document.addEventListener('touchcancel', function(){ pinch = null; pan = null; });
  window.addEventListener('dblclick', function(e){
    if (tapOnCtl(e.target)) return;
    e.preventDefault();
    if (z > 1.3) applyZoom(1, e.clientX, e.clientY);
    else applyZoom(2.2, e.clientX, e.clientY);
  });
  var updateProgress = function(){
    if (!pf) return;
    var m = document.documentElement.scrollHeight - window.innerHeight;
    var pc = m > 0 ? Math.min(100, Math.max(0, window.scrollY / m * 100)) : 0;
    pf.style.width = pc + '%';
    var pl = document.getElementById('plab');
    if (pl) {
      var fa = function(v){ return String(v).replace(/[0-9]/g, function(d){ return '۰۱۲۳۴۵۶۷۸۹'.charAt(+d); }); };
      var txt = fa(Math.round(pc)) + '٪';
      try {
        if (typeof curPageIdx === 'function' && typeof stackCount === 'function')
          txt += ' · ' + fa(curPageIdx() + 1) + '/' + fa(stackCount());
      } catch (err) {}
      pl.textContent = txt;
    }
  };
  window.addEventListener('scroll', function(){
    updateProgress();
  }, { passive: true });
  window.addEventListener('resize', function(){
    if (z !== 1) applyZoom(z);
    updateProgress();
    updateFan();
  });
  var MCAT = document.getElementById('mcat');
  if (MCAT) {
  var mcatBub = MCAT.querySelector('.mcat-bub');
  var mcatSayEl = MCAT.querySelector('.mcat-say');
  var MCAT_USE_S = true;
  var FAD = '۰۱۲۳۴۵۶۷۸۹';
  function faN(v) { return String(v).replace(/[0-9]/g, function (d) { return FAD[+d]; }); }
  function faR(a) { return a[Math.floor(Math.random() * a.length)]; }
  var mcatScrollEl = null;
  if (MCAT_USE_S) { try { if (typeof s !== 'undefined' && s && s.scrollTop !== undefined && s !== window) mcatScrollEl = s; } catch (err) {} }
  function mcatInfo() {
    var m, y;
    if (mcatScrollEl) { m = mcatScrollEl.scrollHeight - mcatScrollEl.clientHeight; y = mcatScrollEl.scrollTop; }
    else { m = document.documentElement.scrollHeight - window.innerHeight; y = window.scrollY || window.pageYOffset || 0; }
    if (m < 0) m = 0;
    return { m: m, y: y, pct: Math.min(1, Math.max(0, y / Math.max(1, m))), atEnd: m > 320 && (m - y) < 5 };
  }
  var MCAT_PAT = UT('say.pat', ['میییو~', 'آخ جووون، همینه!', 'بغلم کن دیگه!', 'ولی ول نکن ها~', 'دلم برات تنگ شده بود!']);
  var MCAT_READ = UT('say.read', ['ورق بزن دیگه!', 'اوه، ادامه‌ش چیه؟!', 'این صحنه وای…', 'چایی میل دارید؟', 'اِ این یکی الان چی گفت؟!', 'ترجمه‌ش دست من بود، بهتر میشد!']);
  var MCAT_STUDY = UT('say.study', ['ششش! دارم به قسمتِ خوبِ قصه میرسم…', 'یه لحظه وایسا، خودم می‌خونم!', 'هوم… هوم… این فصل چی میگه!', 'این کتاب مالِ منه ها، دست نزن!']);
  var MCAT_THINK = UT('say.think', ['هوم… بعدِ این چی میشه؟', 'اگه نویسنده یه چیزِ دیگه میگفت چی؟', 'هوم هوم… دارم فکر میکنم…', 'چرا هی دلم میخواد دُم بگیرم؟!']);
  var MCAT_YAWN = UT('say.yawn', ['خمووووام…', 'یه چرتِ کوچولو بد نیست…', 'خمیازه اومد، شرمنده!', 'چشمام سنگین شدن…']);
  var MCAT_DANCE = UT('say.dance', ['لالالا~ دارم می‌رقصم!', 'حالِ دلم خوبه، ببین!', 'رقصِ گربه‌ایِ خاصِ خودم!', 'بزن برقصیم!']);
  var MCAT_RUN = UT('say.run', ['نمیگیری منو!', 'دورِ صفحه می‌چرخم، ووووو!', 'برس به من، برسسس!', 'هوووووم، چه حالی میده!']);
  var MCAT_HUNGRY = UT('say.hungry', ['قار قور؟!… شرمنده', 'شکمم داره آهنگ میخونه!', 'وا، این صدا از شکمم بود؟!', 'غذا یادم رفت بخورم…', 'کسی بیسکویت داره؟']);
  var MCAT_EAT = UT('say.eat', ['چیزی ندیدم ها! تو هم ندیدی؟!', 'نگاه نکن! دارم شام میخورم!', 'این مالِ من شد، تو که ندیدیش!', 'ششش… صدای جویدن نمیاد!']);
  var MCAT_SHY = UT('say.shy', ['خجالت کشیدم ببینم!', 'چرا اینجوری نگاه میکنی؟!', 'وییی… به کسی نگو!', 'اِ خودتو ندیدم!']);
  var MCAT_WAKE = UT('say.wake', ['نخوابیدم ها! چشمام فقط استراحت میکردن!', 'من؟! خواب نبودم اصلاً!']);
  var MCAT_ANNOY = UT('say.annoy', ['وایسا وایسا، بسه!', 'نازکیدم ول کن!', 'خیلی شیطون شدی ها!', 'بسه دیگه، گوشه‌م میرم!']);
  var MCAT_ANGRY = UT('say.angry', ['آخ! چرا میزنی؟!', 'دلم شکست تو!', 'بدجنسیه این کارت!']);
  var MCAT_AWAY = UT('say.away', ['خوش باش، من رفتم!', 'قهرم ازت، جدی!', 'بای بای، دیگه نمیام!']);
  var MCAT_BACK = UT('say.back', ['ولی دلم تنگ شد، برگشتم…', 'قصه‌ات رو ول نمیکردم دیگه…', 'باشه باشه، بخشیدمت!']);
  var MCAT_HIDE_SAY = UT('say.hide', ['پشتِ دیوال قایم شدم، گیرم نمیاری!', 'هیشکی اینجا منو پیدا نمیکنه!', 'از پشتِ دیوال دارم نگاه می‌کنم!']);
  var MCAT_FOUND = UT('say.found', ['اِ پیدام کردی؟! زرنگی!', 'وا! از کجا فهمیدی اینجام؟!', 'باشه باشه، باختم!']);
  var MCAT_OFF = UT('say.off', ['بس بود! صفحه رو خاموش می‌کنم!', 'دیگه بسه! دکمهٔ خاموش کجاست…']);
  var MCAT_MILE = UT('say.mile', ['یه چهارمش رفت!', 'نصفش رفته، بزن بریم!', 'سه چهارمش که تمومه، وایسا!']);
  var MCAT_HANG = UT('say.hang', ['وا! چطور وارونه شدم؟!', 'از سقف آویزونم، جاذبه هی بلاگه!', 'خونم رفت گوشم! یعنی… پام شد سرم!']);
  var MCAT_SIT = UT('say.sit', ['اینجا دمِ صفحه خنک‌تره!', 'لبِ پایین، جای آدمیزادها!', 'نشستم راحت، خبری نیست؟']);
  var MCAT_SIDE = UT('say.side', ['از این ور فقط نگاه می‌کنم…', 'من؟! من که هیشی کار نکردم!', 'یه سرک از بغل زدم!']);
  var MCAT_PIC = UT('say.pic', ['وای! این صحنه رو به یاد دارم!', 'اِ این قاب رو قبلاً دیدم!', 'این تصویر خوشگله! مال کدوم فصله؟']);
  var MCAT_DROP = UT('say.drop', ['حوووپا!', 'دوباره بنداز، دوباره!', 'ایول، جالب بود!']);
  var MCAT_BACK2 = UT('say.back2', ['جای خودم، جای خودم!', 'خوش بود؟ یه بار دیگه بندازم؟!']);
  var ACT_DUR = { 'st-spin': 3000, 'st-ball': 3200, 'st-music': 3400, 'st-dance': 3600, 'st-study': 5200, 'st-think': 3600, 'st-yawn': 2800, 'st-hungry': 3000, 'st-eat': 5200, 'st-run': 6200, 'st-hang': 7000, 'st-edgesit': 6500, 'st-sidepeek': 6000 };
  var ACT_POOL = ['st-spin', 'st-spin', 'st-ball', 'st-ball', 'st-music', 'st-music', 'st-dance', 'st-dance', 'st-study', 'st-study', 'st-think', 'st-yawn', 'st-hungry', 'st-eat', 'st-eat', 'st-run'];
  var ACT_SAY = {
    'st-spin': UT('say.spin', ['دُمم بیا اینجا!', 'ووووو، سرم گیج رفت!']),
    'st-ball': UT('say.ball', ['بگیر بگیر!', 'توپ! توپ!', 'بالا بَر، اَ بالا!']),
    'st-music': UT('say.music', ['هوم هوم~', 'لالالالا~', 'دلم میخواد آهنگ بخونم~']),
    'st-dance': MCAT_DANCE,
    'st-study': MCAT_STUDY,
    'st-think': MCAT_THINK,
    'st-yawn': MCAT_YAWN,
    'st-hungry': MCAT_HUNGRY,
    'st-eat': MCAT_EAT,
    'st-run': MCAT_RUN,
    'st-hang': MCAT_HANG,
    'st-edgesit': MCAT_SIT,
    'st-sidepeek': MCAT_SIDE
  };
  var mcatState = 'st-read';
  var mcatLastTs = 0, mcatLastY = -1, mcatFastT = 0, mcatMoveT = Date.now();
  var mcatBotT = 0, mcatPatT = 0, mcatSayUntil = 0;
  var mcatHideTill = 0, mcatAwayTill = 0, mcatPeekTill = 0, mcatPeekR = false;
  var mcatAnnoyT = 0, mcatAngryT = 0, mcatShyT = 0;
  var mcatActT = 0, mcatActSt = '', mcatActCd = 0, mcatNextAct = '';
  var mcatRunning = false, mcatRunT = null;
  var mcatTaps = [], mcatAngerN = 0, mcatAngerLast = 0;
  var mcatTeaseN = 0;
  var mcatSaved = null, mcatMile = 0;
  var mcatForceSt = '', mcatForceTill = 0;
  var mcatZoneBack = 0, ZONES = null, mcatZoneCur = '';
  var mcatLastN = -1, mcatLastMk = '';
  function mcatSet(st) { if (mcatState === st) return; MCAT.classList.remove(mcatState); MCAT.classList.add(st); mcatState = st; }
  function mcatSayNow(txt, ms) { mcatSayEl.textContent = txt; mcatSayEl.classList.add('show'); mcatSayUntil = Date.now() + (ms || 5000); }
  function mcatUpdate() {
    var inf = mcatInfo();
    var txt = faN(Math.round(inf.pct * 100)) + '٪';
    if (typeof curPageIdx === 'function' && typeof stackCount === 'function') txt += ' · ' + faN(curPageIdx() + 1) + '/' + faN(stackCount());
    if (mcatBub) mcatBub.textContent = txt;
  }
  function mcatGlide(fn) { MCAT.classList.add('glide'); fn(); setTimeout(function () { MCAT.classList.remove('glide'); }, 800); }
  function mcatPlace(cx, cy) {
    var x = Math.min(Math.max(cx, 52), window.innerWidth - 52);
    var y = Math.min(Math.max(cy, 78), window.innerHeight - 112);
    MCAT.style.left = (x - MCAT.offsetWidth / 2) + 'px';
    MCAT.style.top = (y - MCAT.offsetHeight / 2) + 'px';
    MCAT.style.right = 'auto';
    MCAT.style.bottom = 'auto';
  }
  function mcatRestore(say) {
    mcatHideTill = mcatAwayTill = mcatPeekTill = 0;
    MCAT.classList.remove('away', 'peek-r', 'hide-l');
    if (mcatSaved) { var sv = mcatSaved; mcatGlide(function () { mcatPlace(sv.x, sv.y); }); }
    mcatMoveT = Date.now();
    mcatSet('st-read');
    if (say) mcatSayNow(say, 3000);
    mcatTick();
  }
  function mcatGoHide() {
    if (mcatState === 'st-hide') return;
    var r = MCAT.getBoundingClientRect();
    var hw = MCAT.offsetWidth || 70, hh = MCAT.offsetHeight || 82;
    mcatSaved = { x: r.left + r.width / 2, y: r.top + r.height / 2 };
    var onRight = (r.left + r.width / 2) >= window.innerWidth / 2;
    MCAT.classList.toggle('hide-l', !onRight);
    var hy = Math.min(Math.max(r.top + r.height / 2, window.innerHeight * 0.36),
      window.innerHeight - hh / 2 - 30);
    mcatGlide(function () {
      MCAT.style.left = (onRight ? window.innerWidth - hw + 1 : -1) + 'px';
      MCAT.style.top = (hy - hh / 2) + 'px';
      MCAT.style.right = 'auto';
      MCAT.style.bottom = 'auto';
    });
    mcatSet('st-hide');
    mcatHideTill = Date.now() + 12000 + Math.random() * 6000;
    mcatSayNow(faR(MCAT_HIDE_SAY), 2800);
  }
  function mcatGoAway() {
    if (mcatState === 'st-hide' || mcatState === 'st-peek' || MCAT.classList.contains('away')) return;
    var r = MCAT.getBoundingClientRect();
    mcatSaved = { x: r.left + r.width / 2, y: r.top + r.height / 2 };
    mcatPeekR = r.left + r.width / 2 >= window.innerWidth / 2;
    var ay = Math.min(Math.max(r.top + r.height / 2, 130), window.innerHeight - 110);
    mcatGlide(function () {
      MCAT.style.left = (mcatPeekR ? window.innerWidth - 30 : -34) + 'px';
      MCAT.style.top = (ay - MCAT.offsetHeight / 2) + 'px';
      MCAT.style.right = 'auto';
    });
    setTimeout(function () { MCAT.classList.add('away'); }, 700);
    mcatAwayTill = Date.now() + 25000 + Math.random() * 15000;
    mcatSayNow(faR(MCAT_AWAY), 2200);
  }
  function mcatStartPeek() {
    mcatAwayTill = 0;
    MCAT.classList.remove('away');
    if (mcatPeekR) MCAT.classList.add('peek-r'); else MCAT.classList.remove('peek-r');
    mcatSet('st-peek');
    mcatPeekTill = Date.now() + 9000;
    mcatSayNow(UT('say.still_angry', '…هنوز قهرم ها!'), 2400);
  }
  var mcatOffEl = document.getElementById('mcatOff');
  var mcatOffTimer = null;
  function mcatWake() {
    if (!mcatOffEl || !mcatOffEl.classList.contains('show')) return;
    mcatOffEl.classList.remove('show');
    if (mcatOffTimer) { clearTimeout(mcatOffTimer); mcatOffTimer = null; }
    mcatRestore('دیدی چیکار می‌کنم؟! دیگه اذیت نکن~');
  }
  function mcatBlackout() {
    mcatTeaseN = 0;
    mcatTaps = [];
    mcatAnnoyT = mcatAngryT = mcatPatT = mcatActT = mcatShyT = 0;
    mcatSayNow(faR(MCAT_OFF), 1900);
    mcatSet('st-annoy');
    mcatTick();
    setTimeout(function () {
      if (!mcatOffEl) return;
      mcatOffEl.classList.add('show');
      if (mcatOffTimer) clearTimeout(mcatOffTimer);
      mcatOffTimer = setTimeout(mcatWake, 5200);
    }, 1600);
  }
  function mcatStartRun() {
    if (mcatRunning) return;
    var r = MCAT.getBoundingClientRect();
    mcatSaved = { x: r.left + r.width / 2, y: r.top + r.height / 2 };
    mcatRunning = true;
    mcatActSt = 'st-run';
    mcatActT = Date.now() + 6200;
    mcatMoveT = Date.now();
    mcatSayNow(faR(MCAT_RUN), 3400);
    mcatSet('st-run');
    var vw = window.innerWidth, vh = window.innerHeight;
    var mx = 54, ty = 84, by = vh - 90;
    var pts = [[mx, ty], [vw - mx, ty], [vw - mx, by], [mx, by], [mx, ty]];
    MCAT.classList.add('glide');
    var i = 0;
    function step() {
      if (!mcatRunning) return;
      mcatPlace(pts[i][0], pts[i][1]);
      i++;
      if (i < pts.length) mcatRunT = setTimeout(step, 1050);
      else mcatEndRun(false);
    }
    step();
  }
  function mcatEndRun(interrupted) {
    if (!mcatRunning) return;
    mcatRunning = false;
    if (mcatRunT) { clearTimeout(mcatRunT); mcatRunT = null; }
    MCAT.classList.remove('glide');
    var sv = mcatSaved;
    if (sv) mcatGlide(function () { mcatPlace(sv.x, sv.y); });
    mcatMoveT = Date.now();
    mcatActT = 0; mcatActSt = '';
    mcatSet('st-read');
    if (!interrupted) mcatSayNow(UT('say.tired', 'اوف اوف… خسته شدم!'), 2600);
  }
  function mcatTick() {
    var now = Date.now();
    var inf = mcatInfo();
    if (mcatSayUntil && mcatSayUntil < now) { mcatSayEl.classList.remove('show'); mcatSayUntil = 0; }
    if (mcatZoneBack && now > mcatZoneBack) {
      mcatZoneBack = 0;
      if (mcatState === 'st-hang' || mcatState === 'st-edgesit' || mcatState === 'st-sidepeek') {
        MCAT.classList.remove('peek-r');
        if (mcatSaved) { var zb = mcatSaved; mcatGlide(function () { mcatPlace(zb.x, zb.y); }); }
        mcatSet('st-read');
        mcatSayNow(faR(MCAT_BACK2), 2400);
      }
    }
    if (mcatState === 'st-hide') {
      if (now > mcatHideTill) mcatRestore('دیدی دلم برات تنگ شد!');
      return;
    }
    if (MCAT.classList.contains('away')) {
      if (now > mcatAwayTill) mcatStartPeek();
      return;
    }
    if (mcatState === 'st-peek') {
      if (now > mcatPeekTill) mcatRestore(faR(MCAT_BACK));
      return;
    }
    if (inf.atEnd) { if (!mcatBotT) mcatBotT = now; } else mcatBotT = 0;
    if (mcatForceTill > now && mcatForceSt) { mcatSet(mcatForceSt); return; }
    if (mcatPatT > now) { mcatSet('st-pat'); return; }
    if (mcatShyT > now) { mcatSet('st-shy'); return; }
    if (mcatAnnoyT > now) { mcatSet('st-annoy'); return; }
    if (mcatAngryT > now) { mcatSet('st-angry'); return; }
    if (mcatRunning) { mcatSet('st-run'); return; }
    if (mcatActT > now && mcatActSt) { mcatSet(mcatActSt); return; }
    if (mcatZoneBack > now) return;
    if (inf.m > 320 && mcatMoveT < now - 8000 && mcatMoveT > now - 21000 && now > mcatActCd && mcatPatT < now && mcatShyT < now) {
      if (Math.random() < 0.09) {
        mcatActCd = now + 30000 + Math.random() * 15000;
        mcatGoHide();
        return;
      }
      var st = mcatNextAct || faR(ACT_POOL);
      mcatNextAct = '';
      mcatActCd = now + 26000 + Math.random() * 14000;
      mcatMoveT = now;
      if (st === 'st-run') { mcatStartRun(); return; }
      mcatActSt = st;
      mcatActT = now + ACT_DUR[st];
      mcatSayNow(faR(ACT_SAY[st]), ACT_DUR[st] - 300);
      mcatSet(st);
      if (st === 'st-hungry' && Math.random() < 0.55) mcatNextAct = 'st-eat';
      return;
    }
    if (inf.atEnd && now - mcatBotT > 2200) mcatSet('st-sad');
    else if (mcatFastT > now - 1200) mcatSet('st-exc');
    else if (mcatMoveT < now - 22000) mcatSet('st-sleep');
    else if (inf.m > 320 && inf.pct >= 0.9) mcatSet('st-stress');
    else mcatSet('st-read');
    if (mcatBub) mcatBub.classList.toggle('dim', now - mcatMoveT > 4000);
  }
  function mcatOnScroll() {
    var now = Date.now();
    var y = mcatInfo().y;
    if (mcatLastY < 0) mcatLastY = y;
    var dt = Math.max(40, now - mcatLastTs);
    if (Math.abs(y - mcatLastY) / dt > 0.85) mcatFastT = now;
    mcatLastY = y; mcatLastTs = now;
    mcatMoveT = now;
    if (mcatRunning) mcatEndRun(true);
    if (mcatState === 'st-hang' || mcatState === 'st-edgesit' || mcatState === 'st-sidepeek') {
      mcatZoneBack = 0;
      MCAT.classList.remove('peek-r');
      if (mcatSaved) { var zs2 = mcatSaved; mcatGlide(function () { mcatPlace(zs2.x, zs2.y); }); }
      mcatSet('st-read');
    }
    if (mcatActT) { mcatActT = 0; mcatActSt = ''; mcatNextAct = ''; }
    if (mcatForceTill) mcatForceTill = 0;
    if (mcatState === 'st-sleep') {
      if (Math.random() < 0.4) { mcatShyT = now + 2600; mcatSayNow(faR(MCAT_WAKE), 2800); }
      else mcatSet('st-read');
    }
    mcatUpdate();
    mcatTick();
  }
  var mcatDrag = null;
  MCAT.addEventListener('pointerdown', function (e) {
    mcatDrag = { x: e.clientX, y: e.clientY, moved: false };
    mcatMoveT = Date.now();
    if (mcatRunning) mcatEndRun(true);
    try { MCAT.setPointerCapture(e.pointerId); } catch (err) {}
    e.preventDefault();
  });
  MCAT.addEventListener('pointermove', function (e) {
    if (!mcatDrag) return;
    var dx = e.clientX - mcatDrag.x, dy = e.clientY - mcatDrag.y;
    if (!mcatDrag.moved && Math.sqrt(dx * dx + dy * dy) > 10) {
      mcatDrag.moved = true;
      if (!ZONES) mcatZonesBuild();
      ZONES.classList.add('show');
    }
    if (mcatDrag.moved) {
      mcatMoveT = Date.now();
      mcatPlace(e.clientX, e.clientY);
      mcatZonesMark(mcatZoneOf(e.clientX, e.clientY));
    }
  });
  function mcatUp(e) {
    if (!mcatDrag) return;
    var moved = mcatDrag.moved;
    mcatDrag = null;
    if (ZONES) { ZONES.classList.remove('show'); mcatZoneCur = ''; }
    if (moved) {
      var now = Date.now();
      var r = MCAT.getBoundingClientRect();
      var cx = r.left + r.width / 2, cy = r.top + r.height / 2;
      try { localStorage.setItem('mangaCatPos', JSON.stringify({ x: cx, y: cy })); } catch (err) {}
      var z = mcatZoneOf(e.clientX, e.clientY);
      if (z === 'center') {
        var el = null, oldPe = MCAT.style.pointerEvents;
        MCAT.style.pointerEvents = 'none';
        try { el = document.elementFromPoint(e.clientX, e.clientY); } catch (err2) {}
        MCAT.style.pointerEvents = oldPe;
        while (el && el !== document.body && el.tagName !== 'IMG') el = el.parentElement;
        mcatMoveT = now;
        if (el && el.tagName === 'IMG') {
          mcatFastT = now + 1400;
          mcatSayNow(faR(MCAT_PIC), 3400);
          mcatSet('st-exc');
        } else {
          mcatActSt = 'st-dance'; mcatActT = now + 3800;
          mcatSayNow(faR(MCAT_DROP), 3200);
          mcatSet('st-dance');
        }
        mcatTick(); setTimeout(mcatTick, 4000);
      } else {
        mcatZoneLand(z, cx, cy);
        mcatTick();
      }
      return;
    }
    var now = Date.now();
    if (mcatState === 'st-hide') {
      mcatRestore(Math.random() < 0.5 ? faR(MCAT_FOUND) : faR(MCAT_SHY));
      return;
    }
    if (mcatState === 'st-peek' || MCAT.classList.contains('away')) {
      mcatRestore(faR(MCAT_BACK));
      return;
    }
    if (mcatRunning) mcatEndRun(true);
    mcatTaps.push(now);
    while (mcatTaps.length && mcatTaps[0] < now - 6000) mcatTaps.shift();
    var fast = 0, i;
    for (i = 0; i < mcatTaps.length; i++) if (mcatTaps[i] > now - 2200) fast++;
    if (mcatAnnoyT > now || mcatAngryT > now) mcatTeaseN++;
    if (fast >= 5 || mcatTaps.length >= 5) mcatTeaseN++;
    if (mcatTeaseN >= 10) { mcatBlackout(); return; }
    if (fast >= 5) {
      mcatAngryT = now + 2100;
      mcatPatT = mcatAnnoyT = mcatActT = mcatShyT = 0; mcatActSt = '';
      mcatSayNow(faR(MCAT_ANGRY), 2400);
      if (now - mcatAngerLast > 90000) mcatAngerN = 0;
      mcatAngerN++; mcatAngerLast = now;
      if (mcatAngerN >= 2 && Math.random() < 0.45) {
        setTimeout(function () { mcatGoAway(); }, 2150);
        mcatAngerN = 0;
      }
      mcatTaps = [];
      mcatTick(); setTimeout(mcatTick, 2150);
      return;
    }
    if (mcatTaps.length >= 5) {
      mcatAnnoyT = now + 1900;
      mcatPatT = mcatActT = mcatShyT = 0; mcatActSt = '';
      mcatSayNow(faR(MCAT_ANNOY), 1900);
      setTimeout(function () { mcatGoHide(); }, 1950);
      mcatTaps = [];
      mcatTick(); setTimeout(mcatTick, 1980);
      return;
    }
    mcatPatT = now + 1700;
    mcatMoveT = now;
    if (mcatTaps.length === 4 && Math.random() < 0.4) {
      mcatPatT = now + 1500;
      mcatShyT = now + 3900;
      mcatSayNow(faR(MCAT_PAT), 1400);
      setTimeout(function () { mcatSayNow(faR(MCAT_SHY), 2300); }, 1550);
    } else {
      mcatSayNow(faR(MCAT_PAT), 2600);
    }
    mcatTick();
    setTimeout(mcatTick, 1800);
  }
  MCAT.addEventListener('pointerup', mcatUp);
  MCAT.addEventListener('pointercancel', function () { mcatDrag = null; if (ZONES) { ZONES.classList.remove('show'); mcatZoneCur = ''; } });
  if (mcatOffEl) mcatOffEl.addEventListener('pointerdown', function () { mcatWake(); });
  function mcatZoneOf(x, y) {
    var vw = window.innerWidth, vh = window.innerHeight;
    if (y < vh * 0.17) return 'top';
    if (y > vh * 0.83) return 'bottom';
    if (x < vw * 0.14) return 'left';
    if (x > vw * 0.86) return 'right';
    return 'center';
  }
  function mcatZonesBuild() {
    ZONES = document.createElement('div');
    ZONES.id = 'mcatzones';
    ZONES.innerHTML = '<div class="mz mz-top" data-z="top"></div><div class="mz mz-bottom" data-z="bottom"></div><div class="mz mz-left" data-z="left"></div><div class="mz mz-right" data-z="right"></div><div class="mz mz-center" data-z="center"></div>';
    document.body.appendChild(ZONES);
  }
  function mcatZonesMark(z) {
    if (!ZONES || z === mcatZoneCur) return;
    mcatZoneCur = z;
    var zs = ZONES.children, i;
    for (i = 0; i < zs.length; i++) zs[i].classList.toggle('on', zs[i].getAttribute('data-z') === z);
  }
  function mcatZoneLand(z, cx, cy) {
    var now = Date.now();
    mcatSaved = { x: cx, y: cy };
    mcatHideTill = mcatAwayTill = mcatPeekTill = 0;
    mcatActT = 0; mcatActSt = ''; mcatNextAct = '';
    MCAT.classList.remove('away', 'hide-l');
    if (z === 'top') {
      mcatGlide(function () {
        MCAT.style.left = (window.innerWidth / 2 - MCAT.offsetWidth / 2) + 'px';
        MCAT.style.top = '-46px';
        MCAT.style.right = 'auto';
      });
      mcatSet('st-hang');
      mcatSayNow(faR(MCAT_HANG), 4200);
    } else if (z === 'bottom') {
      mcatGlide(function () {
        MCAT.style.left = Math.max(8, Math.min(cx - MCAT.offsetWidth / 2, window.innerWidth - MCAT.offsetWidth - 8)) + 'px';
        MCAT.style.top = (window.innerHeight - 66) + 'px';
        MCAT.style.right = 'auto';
      });
      mcatSet('st-edgesit');
      mcatSayNow(faR(MCAT_SIT), 3800);
    } else {
      var rightSide = z === 'right';
      MCAT.classList.toggle('peek-r', rightSide);
      mcatGlide(function () {
        MCAT.style.left = (rightSide ? window.innerWidth - 40 : -48) + 'px';
        MCAT.style.top = Math.max(70, Math.min(cy - MCAT.offsetHeight / 2, window.innerHeight - 170)) + 'px';
        MCAT.style.right = 'auto';
      });
      mcatSet('st-sidepeek');
      mcatSayNow(faR(MCAT_SIDE), 3800);
    }
    mcatMoveT = now;
    mcatZoneBack = now + 7500;
  }
  var mcatFine = false;
  try {
    mcatFine = !!(window.matchMedia && window.matchMedia('(hover: hover) and (pointer: fine)').matches);
    if (!mcatFine && navigator.maxTouchPoints === 0 && !/Android|iPhone|iPad|Mobile/i.test(navigator.userAgent)) mcatFine = true;
  } catch (err) {}
  var mcatPupL = null, mcatPupR = null;
  function mcatEyes(e) {
    if (!mcatPupL) {
      var ps = MCAT.querySelectorAll('.cg-eyes-open .cg-pupil');
      if (ps.length < 2) return;
      mcatPupL = ps[0]; mcatPupR = ps[1];
    }
    var svg = MCAT.querySelector('svg');
    if (!svg) return;
    var r = svg.getBoundingClientRect();
    if (r.width < 4 || r.height < 4) return;
    var ex = r.left + r.width * 0.5, ey = r.top + r.height * 0.4;
    var dx = e.clientX - ex, dy = e.clientY - ey;
    var d = Math.sqrt(dx * dx + dy * dy) || 1;
    var k = Math.min(1, d / 260) * 2.4;
    var t = 'translate(' + ((dx / d) * k).toFixed(2) + 'px,' + ((dy / d) * k * 0.8).toFixed(2) + 'px)';
    mcatPupL.style.transform = t;
    mcatPupR.style.transform = t;
  }
  if (mcatFine) {
    window.addEventListener('mousemove', mcatEyes, { passive: true });
    document.addEventListener('mouseleave', function () {
      if (mcatPupL) { mcatPupL.style.transform = 'translate(0,0)'; mcatPupR.style.transform = 'translate(0,0)'; }
    });
  }
  window.__mcatForce = function (st) {
    mcatForceSt = ''; mcatForceTill = 0;
    mcatPatT = 0; mcatAnnoyT = 0; mcatAngryT = 0; mcatShyT = 0;
    mcatActT = 0; mcatActSt = ''; mcatNextAct = '';
    if (mcatRunning) mcatEndRun(true);
    if (st === 'st-hide') { mcatGoHide(); mcatHideTill = Date.now() + 60000; return; }
    if (st === 'st-blackout') { mcatBlackout(); return; }
    if (st === 'st-away') {
      mcatAwayTill = 0;
      if (mcatState !== 'st-peek' && !MCAT.classList.contains('away')) mcatGoAway();
      mcatAwayTill = Date.now() + 2600;
      setTimeout(function () { if (MCAT.classList.contains('away')) mcatStartPeek(); }, 2700);
      setTimeout(function () { if (mcatState === 'st-peek') mcatRestore('برگشتم!'); }, 5400);
      return;
    }
    if (st === 'st-run') { if (!mcatRunning) { mcatActCd = 0; mcatStartRun(); } return; }
    if (st === 'st-hang' || st === 'st-edgesit' || st === 'st-sidepeek') {
      var zr = MCAT.getBoundingClientRect();
      mcatZoneLand(st === 'st-hang' ? 'top' : st === 'st-edgesit' ? 'bottom' : (Math.random() < 0.5 ? 'left' : 'right'), zr.left + zr.width / 2, zr.top + zr.height / 2);
      mcatTick();
      return;
    }
    if (ACT_DUR[st]) {
      mcatActSt = st; mcatActT = Date.now() + ACT_DUR[st] + 400; mcatMoveT = Date.now();
      mcatSayNow(faR(ACT_SAY[st]), ACT_DUR[st]);
      if (st === 'st-hungry' && Math.random() < 0.55) mcatNextAct = 'st-eat';
      mcatSet(st);
      mcatTick();
      setTimeout(mcatTick, ACT_DUR[st] + 500);
      return;
    }
    if (st === 'st-pat') { mcatPatT = Date.now() + 2000; mcatMoveT = Date.now(); mcatSayNow(faR(MCAT_PAT), 2600); }
    else if (st === 'st-annoy') { mcatAnnoyT = Date.now() + 2600; mcatSayNow(faR(MCAT_ANNOY), 2600); }
    else if (st === 'st-angry') { mcatAngryT = Date.now() + 2600; mcatSayNow(faR(MCAT_ANGRY), 2400); }
    else if (st === 'st-shy') { mcatShyT = Date.now() + 3200; mcatSayNow(faR(MCAT_SHY), 3200); }
    else if (st === 'st-exc') { mcatFastT = Date.now(); mcatSayNow('ایول، این ورق رو دیدی؟!', 2600); }
    else if (st === 'st-sleep') { mcatMoveT = 0; }
    else if (st === 'st-read' || st === 'st-sad' || st === 'st-stress') {
      mcatForceSt = st; mcatForceTill = Date.now() + 6000;
      if (st === 'st-sad') mcatSayNow('تموم شد؟! ننووو', 3000);
      if (st === 'st-stress') mcatSayNow('وای، یه کم مونده…', 3000);
      if (st === 'st-read') mcatSayNow(faR(MCAT_READ), 3000);
    }
    mcatTick();
  };
  var iv = setInterval(function () {
    mcatTick();
    mcatUpdate();
    if (typeof stackCount === 'function' && typeof dbgMode !== 'undefined') {
      var mk = dbgMode ? 'd' : 'f';
      var n = stackCount();
      if (mcatLastN >= 0 && n > mcatLastN && mk === mcatLastMk) {
        if (mcatState === 'st-hide' || mcatState === 'st-peek' || MCAT.classList.contains('away')) mcatRestore('صفحهٔ تازه؟ اومدم اومدم!');
        else if (mcatPatT < Date.now()) { mcatFastT = Date.now() + 900; mcatSayNow(UT('say.fresh', 'یه صفحهٔ تازه رسید!'), 3200); mcatTick(); }
      }
      mcatLastN = n; mcatLastMk = mk;
    }
    var mp = mcatInfo().pct;
    var mstep = mp >= 0.75 ? 3 : mp >= 0.5 ? 2 : mp >= 0.25 ? 1 : 0;
    if (mstep > mcatMile) {
      mcatMile = mstep;
      if (mcatState !== 'st-hide' && mcatState !== 'st-peek' && !MCAT.classList.contains('away') && mcatPatT < Date.now()) {
        mcatFastT = Date.now() + 900;
        mcatSayNow(MCAT_MILE[mstep - 1], 3200);
        mcatTick();
      }
    }
    if (mcatState === 'st-read' && !mcatSayUntil && Math.random() < 0.02) mcatSayNow(faR(MCAT_READ), 5200);
  }, 900);
  var welcomeT = setTimeout(function () {
    if (mcatState === 'st-read') mcatSayNow('سلام!', 3600);
  }, 900);
  try {
    var sp = JSON.parse(localStorage.getItem('mangaCatPos') || 'null');
    if (sp && typeof sp.x === 'number') mcatPlace(sp.x, sp.y);
    else mcatPlace(window.innerWidth - 60, 170);
  } catch (err) { mcatPlace(window.innerWidth - 60, 170); }
  if (mcatScrollEl) mcatScrollEl.addEventListener('scroll', mcatOnScroll, { passive: true });
  else window.addEventListener('scroll', mcatOnScroll, false);
  mcatUpdate();
  mcatTick();
  window.__mcatKill = function () {
    clearInterval(iv);
    clearTimeout(welcomeT);
    if (mcatRunT) clearTimeout(mcatRunT);
    window.removeEventListener('scroll', mcatOnScroll, false);
    window.removeEventListener('mousemove', mcatEyes, false);
    if (ZONES && ZONES.parentNode) ZONES.parentNode.removeChild(ZONES);
    ZONES = null; mcatZoneCur = '';
    if (mcatScrollEl) { try { mcatScrollEl.removeEventListener('scroll', mcatOnScroll); } catch (err) {} }
  };
    mcatUpdate();
    mcatTick();
  }

  pollTotal();
  probe();
  updateProgress();
})();
</script>
</body></html>"""

    def build_reader_html(files, standalone: bool = True):

        import gradio as _gr
        gv = getattr(_gr, "__version__", "4")
        major = int(str(gv).split(".")[0] or 4)
        prefix = "/gradio_api/file=" if major >= 5 else "/file="
        urls = [prefix + str(p).replace(os.sep, "/") for p in files]
        if not urls:
            body = "<div style='text-align:center;opacity:.6;padding:24px'>" + str(TX("app.no_images", "تصویری برای نمایش پیدا نشد.")) + "</div>"
            if not standalone:
                return body
            return (
                "<!DOCTYPE html><html lang='fa' dir='rtl'><head><meta charset='utf-8'>"
                "<meta name='viewport' content='width=device-width,initial-scale=1'>"
                f"<title>{TX('app.read_title', 'خواندن')}</title></head><body style='background:#000;color:#999'>{body}</body></html>"
            )
        try:
            import zlib as _zlib
            from PIL import Image as _PILImage
            _lz = getattr(_PILImage, "LANCZOS", None)
            if _lz is None:
                _lz = _PILImage.Resampling.LANCZOS
            _prev = {}
            for _p in files:
                try:
                    _ps = str(_p)
                    if _ps.lower().endswith(".gif") or not os.path.isfile(_ps):
                        continue
                    _dir, _fn = os.path.split(_ps)
                    _stem = os.path.splitext(_fn)[0]
                    _pvd = _dir + "_webprev"
                    _crc = "%08x" % (_zlib.crc32(_ps.encode("utf-8"))
                                     & 0xFFFFFFFF)
                    _pv1 = os.path.join(_pvd, _crc + "_" + _stem + "_v2.jpg")
                    _pvk = os.path.join(_pvd, _crc + "_" + _stem + "_v2_%d.jpg")
                    _pvdn = os.path.join(_pvd, _crc + "_" + _stem + "_v2.done")
                    _mt = os.path.getmtime(_ps)
                    _done_short = (os.path.isfile(_pv1)
                                   and os.path.getmtime(_pv1) >= _mt)
                    _done_tall = (os.path.isfile(_pvdn)
                                  and os.path.getmtime(_pvdn) >= _mt)
                    if not (_done_short or _done_tall):
                        os.makedirs(_pvd, exist_ok=True)
                        with _PILImage.open(_ps) as _im:
                            _im = _im.convert("RGB")
                            if _im.width > 1100:
                                _im = _im.resize(
                                    (1100, max(1, round(
                                        _im.height * 1100.0 / _im.width))),
                                    _lz)
                            if _im.height > 2000:
                                _n = (_im.height + 1999) // 2000
                                _us = []
                                for _k in range(_n):
                                    _chk = _im.crop(
                                        (0, _k * 2000, _im.width,
                                         min(_im.height, (_k + 1) * 2000)))
                                    _fp = _pvk % (_k + 1)
                                    _chk.save(_fp, format="JPEG", quality=80,
                                              optimize=True, progressive=True)
                                    _us.append(prefix
                                               + _fp.replace(os.sep, "/"))
                                _prev[_ps] = _us
                                with open(_pvdn, "wb") as _f:
                                    _f.write(b"1")
                            else:
                                _im.save(_pv1, format="JPEG", quality=80,
                                         optimize=True, progressive=True)
                                _prev[_ps] = prefix + _pv1.replace(os.sep, "/")
                    elif _done_tall:
                        _us = []
                        _k = 1
                        while (_k < 99 and os.path.isfile(_pvk % _k)):
                            _us.append(prefix
                                       + (_pvk % _k).replace(os.sep, "/"))
                            _k += 1
                        _prev[_ps] = (_us if _us
                                      else prefix + _pv1.replace(os.sep, "/"))
                    else:
                        _prev[_ps] = prefix + _pv1.replace(os.sep, "/")
                except Exception:
                    continue
            if _prev:
                _urls2 = []
                for _p, _u in zip(files, urls):
                    _v = _prev.get(str(_p))
                    if isinstance(_v, list) and _v:
                        _urls2.extend(_v)
                    else:
                        _urls2.append(_v if _v else _u)
                urls = _urls2
        except Exception:
            pass
        imgs = "".join(
            f'<img data-src="{u}" alt="" draggable="false">'
            for u in urls
        )
        title = os.path.basename(os.path.dirname(files[0])) or "مانهوا"
        title_esc = (
            str(title).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;")
        )
        css = (
            "#rtryChip{position:fixed;left:50%;bottom:96px;transform:translateX(-50%) translateY(24px);"
            "z-index:70;display:flex;align-items:center;gap:8px;background:rgba(18,18,22,.96);"
            "color:#fff;border:1px solid #2f2f36;border-radius:999px;padding:10px 18px;"
            "font-family:inherit;font-size:.92rem;font-weight:700;cursor:pointer;opacity:0;"
            "pointer-events:none;transition:opacity .2s ease-out,transform .2s ease-out;"
            "box-shadow:0 6px 22px rgba(0,0,0,.65);-webkit-tap-highlight-color:transparent;user-select:none}"
            "#rtryChip.show{opacity:1;pointer-events:auto;transform:translateX(-50%) translateY(0)}"
            "#rtryChip:active{transform:translateX(-50%) translateY(0) scale(.94)}"
            "#rtryChip .sp{display:inline-block;font-size:1.08rem;line-height:1}"
            "#rtryChip.busy .sp{animation:rtryS 1s linear infinite}"
            "@keyframes rtryS{to{transform:rotate(360deg)}}"
            "*{box-sizing:border-box;margin:0;padding:0}"
            "html,body{background:#000;color:#e8e6e1;font-family:system-ui,-apple-system,sans-serif;"
            "overscroll-behavior-y:contain;-webkit-user-select:none;user-select:none;touch-action:pan-y}",
            ".rdr{background:#000;direction:ltr}"
            ".rdr-bar{display:flex;align-items:center;flex-wrap:wrap;gap:6px;padding:8px 10px;"
            "background:#0c0c0e;border-bottom:1px solid #232326;position:sticky;top:0;"
            "z-index:10;transform:translateZ(0);backface-visibility:hidden;will-change:transform}"
            ".rdr-btn{background:#161619;color:#e8e6e1;border:1px solid #2a2a2e;border-radius:8px;"
            "padding:8px 12px;font-size:.95rem;cursor:pointer;font-family:inherit;"
            "min-width:40px;min-height:40px;touch-action:manipulation;-webkit-tap-highlight-color:transparent}"
            ".rdr-btn:active{background:#2a2a30}"
            ".rdr-btn.fs{background:#ff4a3d;border-color:#ff4a3d;color:#fff;font-weight:700}"
            ".rdr-title{flex:1 1 120px;color:#97948c;font-size:.8rem;white-space:nowrap;"
            "overflow:hidden;text-overflow:ellipsis;text-align:right;direction:rtl;min-width:0}"
            ".rdrS{position:relative;background:#000;overflow-x:clip}"
            ".rdrC{margin:0 auto;max-width:min(100%,900px);width:100%}"
            ".rdrC img{display:block;width:100%;height:auto;max-width:none;user-select:none;"
            "-webkit-user-drag:none;pointer-events:none;"
            "background:#0b0b0d}"
            ".rdr-progress{position:fixed;bottom:0;left:0;right:0;height:3px;background:#1a1a1c;z-index:3}"
            ".rdrB{height:100%;width:0;background:linear-gradient(90deg,#ff4a3d,#ff8a5e)}"
            ".prog-lab{position:fixed;bottom:9px;left:50%;transform:translateX(-50%);background:rgba(10,10,12,.85);border:1px solid #2a2a2e;color:#ffcf9e;border-radius:9px;padding:2px 10px;font-size:.68rem;font-variant-numeric:tabular-nums;z-index:4;pointer-events:none;white-space:nowrap;direction:rtl}"
            ".zlv{color:#97948c;font-size:.8rem;min-width:44px;text-align:center;font-variant-numeric:tabular-nums}"
            "#fab{position:fixed;z-index:60;left:50%;bottom:26px;width:60px;height:60px;margin-left:-30px;"
            "border-radius:50%;background:#161619;border:2px solid #ff4a3d;color:#fff;font-family:inherit;"
            "font-size:.82rem;font-weight:700;cursor:pointer;display:flex;align-items:center;"
            "justify-content:center;touch-action:none;box-shadow:0 6px 20px rgba(0,0,0,.6);"
            "-webkit-tap-highlight-color:transparent;user-select:none}"
            "#fab:active{transform:scale(.93)}"
            "#fab.open{background:#2c1210;color:#ffb3ab;font-size:1.2rem}"
            ".fbtn{position:fixed;z-index:59;width:58px;height:58px;border-radius:50%;background:#1c1c20;"
            "border:2px solid #2e2e33;color:#e8e6e1;font-family:inherit;font-size:.6rem;font-weight:700;"
            "cursor:pointer;display:flex;flex-direction:column;align-items:center;justify-content:center;"
            "gap:1px;touch-action:manipulation;-webkit-tap-highlight-color:transparent;"
            "box-shadow:0 4px 14px rgba(0,0,0,.55);opacity:0;pointer-events:none;transform:scale(.3);"
            "transition:opacity .15s ease-out,transform .15s ease-out,left .15s linear,top .15s linear}"
            ".fbtn.show{opacity:1;pointer-events:auto;transform:scale(1)}"
            ".fbtn .ic{font-size:1.05rem;line-height:1.1}"
            ".fbtn.on{border-color:#3a8bff;background:#101f38;color:#fff}"
            "#seek{position:fixed;left:0;right:0;top:40%;z-index:58;display:none;padding:12px 8px 8px;"
            "direction:ltr;background:rgba(8,8,10,.86)}"
            "#seek.show{display:block}"
            "#seek .rail{position:relative;height:44px;display:flex;align-items:center;justify-content:space-between}"
            "#seek .line{position:absolute;left:48px;right:48px;top:50%;height:4px;margin-top:-2px;"
            "border-radius:2px;background:#33333a}"
            "#seek .fill{position:absolute;left:48px;top:50%;height:4px;margin-top:-2px;border-radius:2px;"
            "background:linear-gradient(90deg,#ff4a3d,#ff8a5e);width:0}"
            "#seek .th{position:absolute;top:50%;left:48px;width:28px;height:28px;border-radius:50%;"
            "background:#fff;border:3px solid #ff4a3d;transform:translate(-50%,-50%);cursor:grab;"
            "touch-action:none;z-index:2}"
            "#seek .th:active{cursor:grabbing}"
            "#seek .bub{position:absolute;top:4px;left:48px;transform:translateX(-50%);background:#161619;"
            "border:1px solid #2a2a2e;color:#fff;border-radius:8px;padding:3px 10px;font-size:.78rem;"
            "white-space:nowrap;direction:rtl;font-variant-numeric:tabular-nums;pointer-events:none}"
            ".snav{width:42px;height:42px;border-radius:50%;background:#161619;border:1px solid #2a2a2e;"
            "color:#e8e6e1;font-size:1.15rem;cursor:pointer;flex:none;touch-action:manipulation;"
            "-webkit-tap-highlight-color:transparent;z-index:2}"
            ".snav:active{background:#2a2a30}"
            "#seek .rlab{display:flex;justify-content:space-between;direction:rtl;color:#8b8880;"
            "font-size:.68rem;padding:0 48px;margin-top:2px}"
            "@media (max-width:480px){"
            ".rdr-bar{gap:4px;padding:6px 8px}"
            ".rdr-btn{padding:7px 10px;font-size:.9rem;min-width:36px}"
            ".rdr-title{font-size:.72rem;order:10;flex:1 1 100%;text-align:center}"
            "}"
            ".mcat{position:fixed;z-index:57;right:10px;top:58px;width:70px;touch-action:none;-webkit-tap-highlight-color:transparent;user-select:none;filter:drop-shadow(0 3px 8px rgba(0,0,0,.45));cursor:pointer;transition:opacity .3s}"
            ".mcat svg{display:block;width:100%;height:auto;pointer-events:none}"
            "@media (min-width:768px){.mcat{width:76px;right:18px;top:auto;bottom:112px;filter:drop-shadow(0 6px 14px rgba(0,0,0,.55))}}"
            ".mcat.hide-l svg{transform:scaleX(-1)}"
            ".mcat.hide-l .mcat-bub,.mcat.hide-l .mcat-say{right:auto;left:0}"
            ".mcat.hide-l .mcat-say:after{right:auto;left:14px}"
            ".mcat-bub{position:absolute;top:calc(100% + 3px);right:0;white-space:nowrap;background:rgba(12,12,14,.92);border:1px solid #2a2a2e;color:#e8e6e1;border-radius:10px;padding:2px 8px;font-size:.66rem;font-variant-numeric:tabular-nums;direction:rtl;pointer-events:none;opacity:1;transition:opacity .35s}"
            ".mcat-bub.dim{opacity:0}"
            ".mcat-say{position:absolute;top:calc(100% + 22px);right:-2px;white-space:nowrap;background:#fff;color:#1d1d21;border-radius:12px;padding:4px 10px;font-size:.72rem;pointer-events:none;opacity:0;transform:translateY(4px) scale(.9);transition:opacity .18s ease,transform .18s ease;z-index:2}"
            ".mcat-say.show{opacity:1;transform:translateY(0) scale(1)}"
            ".mcat-say:after{content:'';position:absolute;top:-4px;right:14px;width:9px;height:9px;background:#fff;transform:rotate(45deg)}"
            ".cg-eyes,.cg-mv,.cg-zzz,.cg-sweat,.cg-tears,.cg-heart,.cg-spark,.cg-anger,.cg-steam,.cg-ball,.cg-music,.cg-glass,.cg-shyhands,.cg-shyblush,.cg-hand-chin,.cg-arms-up,.cg-arms-stretch,.cg-snack,.cg-crumbs,.cg-rumble,.cg-think,.cg-speed{display:none}"
            ".mcat.st-read .cg-eyes-open,.mcat.st-study .cg-eyes-open,.mcat.st-hide .cg-eyes-open,.mcat.st-peek .cg-eyes-open,.mcat.st-exc .cg-eyes-happy,.mcat.st-pat .cg-eyes-happy,.mcat.st-spin .cg-eyes-happy,.mcat.st-music .cg-eyes-happy,.mcat.st-dance .cg-eyes-happy,.mcat.st-run .cg-eyes-happy,.mcat.st-sleep .cg-eyes-sleep,.mcat.st-yawn .cg-eyes-sleep,.mcat.st-think .cg-eyes-think,.mcat.st-stress .cg-eyes-worry,.mcat.st-sad .cg-eyes-sad,.mcat.st-shy .cg-eyes-down,.mcat.st-hungry .cg-eyes-down,.mcat.st-eat .cg-eyes-shifty,.mcat.st-annoy .cg-eyes-annoy,.mcat.st-angry .cg-eyes-angry,.mcat.st-ball .cg-eyes-up,.mcat.st-hang .cg-eyes-happy,.mcat.st-edgesit .cg-eyes-happy,.mcat.st-sidepeek .cg-eyes-open{display:block}"
            ".mcat.st-read .cg-mv-smile,.mcat.st-exc .cg-mv-smile,.mcat.st-sleep .cg-mv-smile,.mcat.st-stress .cg-mv-smile,.mcat.st-sad .cg-mv-smile,.mcat.st-pat .cg-mv-smile,.mcat.st-spin .cg-mv-smile,.mcat.st-peek .cg-mv-smile,.mcat.st-hide .cg-mv-smile,.mcat.st-dance .cg-mv-smile,.mcat.st-run .cg-mv-smile,.mcat.st-hang .cg-mv-smile,.mcat.st-edgesit .cg-mv-smile,.mcat.st-sidepeek .cg-mv-smile,.mcat.st-study .cg-mv-focus,.mcat.st-think .cg-mv-focus,.mcat.st-shy .cg-mv-tee,.mcat.st-hungry .cg-mv-tee,.mcat.st-annoy .cg-mv-pout,.mcat.st-angry .cg-mv-shout,.mcat.st-ball .cg-mv-o,.mcat.st-music .cg-mv-song,.mcat.st-yawn .cg-mv-yawn,.mcat.st-eat .cg-mv-munch{display:block}"
            ".mcat.st-sleep .cg-zzz{display:block}"
            ".mcat.st-stress .cg-sweat{display:block}"
            ".mcat.st-sad .cg-tears{display:block}"
            ".mcat.st-pat .cg-heart{display:block}"
            ".mcat.st-exc .cg-spark{display:block}"
            ".mcat.st-angry .cg-anger{display:block}"
            ".mcat.st-angry .cg-steam{display:block}"
            ".mcat.st-ball .cg-ball{display:block}"
            ".mcat.st-music .cg-music{display:block}"
            ".mcat.st-dance .cg-music{display:block}"
            ".mcat.st-study .cg-glass{display:block}"
            ".mcat.st-shy .cg-shyhands{display:block}"
            ".mcat.st-shy .cg-shyblush{display:block}"
            ".mcat.st-hungry .cg-shyblush{display:block}"
            ".mcat.st-hungry .cg-rumble{display:block}"
            ".mcat.st-think .cg-hand-chin{display:block}"
            ".mcat.st-think .cg-think{display:block}"
            ".mcat.st-run .cg-speed{display:block}"
            ".mcat.st-eat .cg-snack{display:block}"
            ".mcat.st-eat .cg-crumbs{display:block}"
            ".mcat.st-dance .cg-hug,.mcat.st-dance .cg-book,.mcat.st-yawn .cg-hug,.mcat.st-yawn .cg-book,.mcat.st-eat .cg-hug,.mcat.st-hang .cg-hug,.mcat.st-hang .cg-book{display:none}"
            ".mcat.st-dance .cg-arms-up{display:block}"
            ".mcat.st-yawn .cg-arms-stretch,.mcat.st-hang .cg-arms-stretch{display:block}"
            "@keyframes mcBob{0%,100%{transform:translateY(0)}50%{transform:translateY(-2.5px)}}"
            "@keyframes mcBounce{0%,100%{transform:translateY(0) scale(1)}30%{transform:translateY(-7px) scale(1.05)}60%{transform:translateY(0) scale(.97)}}"
            "@keyframes mcBreath{0%,100%{transform:scale(1)}50%{transform:scale(1.035)}}"
            "@keyframes mcWiggle{0%,100%{transform:rotate(0)}25%{transform:rotate(-7deg)}75%{transform:rotate(7deg)}}"
            "@keyframes mcTail{0%,100%{transform:rotate(-6deg)}50%{transform:rotate(10deg)}}"
            "@keyframes mcEarT{0%,90%,100%{transform:rotate(0)}95%{transform:rotate(-9deg)}}"
            "@keyframes mcPop{0%{opacity:0;transform:translateY(4px)}25%{opacity:1;transform:translateY(0)}80%{opacity:1}100%{opacity:0;transform:translateY(-18px)}}"
            "@keyframes mcBlink{0%,93.5%,100%{transform:scaleY(1)}95.5%{transform:scaleY(.08)}}"
            "@keyframes mcShake{0%,100%{transform:translateX(0)}25%{transform:translateX(-2.6px)}75%{transform:translateX(2.6px)}}"
            "@keyframes mcHmph{0%,100%{transform:translateX(0) rotate(0)}35%{transform:translateX(-5px) rotate(-5deg)}75%{transform:translateX(-3px) rotate(-3deg)}}"
            "@keyframes mcSpin{0%{transform:rotate(0)}45%{transform:rotate(-185deg) scale(1.07,.93)}100%{transform:rotate(-360deg)}}"
            "@keyframes mcSway{0%,100%{transform:rotate(0)}30%{transform:rotate(-7deg)}70%{transform:rotate(7deg)}}"
            "@keyframes mcBall{0%{transform:translateY(0)}22%{transform:translateY(-56px)}46%{transform:translateY(0)}60%{transform:translateY(-20px)}74%{transform:translateY(0)}86%{transform:translateY(-7px)}100%{transform:translateY(0)}}"
            "@keyframes mcAnger{0%,100%{transform:scale(1)}50%{transform:scale(1.4)}}"
            "@keyframes mcFume{0%{opacity:0;transform:translateY(6px)}30%{opacity:.95}100%{opacity:0;transform:translateY(-16px)}}"
            "@keyframes mcNote{0%{opacity:0;transform:translateY(6px)}25%{opacity:1}100%{opacity:0;transform:translateY(-17px)}}"
            "@keyframes mcPeekBob{0%,100%{transform:translateY(0) rotate(0)}50%{transform:translateY(-3px) rotate(3deg)}}"
            "@keyframes mcDance{0%,100%{transform:rotate(-8deg) translateY(0)}25%{transform:rotate(0) translateY(-4px)}50%{transform:rotate(8deg) translateY(0)}75%{transform:rotate(0) translateY(-4px)}}"
            "@keyframes mcWave{0%,100%{transform:rotate(-12deg)}50%{transform:rotate(14deg)}}"
            "@keyframes mcYawnS{0%{transform:scale(1)}45%{transform:scale(1.05,1.09)}100%{transform:scale(1)}}"
            "@keyframes mcThinkS{0%,100%{transform:rotate(-4deg)}50%{transform:rotate(4deg)}}"
            "@keyframes mcRunBob{0%,100%{transform:translateY(0)}50%{transform:translateY(-5px)}}"
            "@keyframes mcShyWig{0%,100%{transform:rotate(0)}30%{transform:rotate(-4deg) translateY(1px)}70%{transform:rotate(3deg)}}"
            "@keyframes mcScan{0%,100%{transform:translateX(-2.5px)}50%{transform:translateX(2.5px)}}"
            "@keyframes mcDart{0%,18%{transform:translateX(-2.4px)}36%,58%{transform:translateX(2.4px)}76%,100%{transform:translateX(0)}}"
            "@keyframes mcMunch{0%,100%{transform:scaleY(1)}50%{transform:scaleY(.35)}}"
            "@keyframes mcRumble{0%,100%{opacity:.15;transform:scale(.8)}50%{opacity:1;transform:scale(1.18)}}"
            "@keyframes mcMunchBob{0%,100%{transform:translateY(0)}50%{transform:translateY(1.6px)}}"
            "@keyframes mcHang{0%,100%{transform:translateY(0) rotate(0)}50%{transform:translateY(4px) rotate(2deg)}}"
            "@keyframes mcCrumbs{0%{opacity:0;transform:translateY(0)}30%{opacity:1}100%{opacity:0;transform:translateY(9px)}}"
            "@keyframes mcSpeedFlick{0%,100%{opacity:.15}50%{opacity:1}}"
            ".mcat .cg-all{transform-origin:60px 108px;animation:mcBob 3.4s ease-in-out infinite}"
            ".mcat.st-exc .cg-all{animation:mcBounce .55s ease-in-out infinite}"
            ".mcat.st-sleep .cg-all{animation:mcBreath 2.8s ease-in-out infinite}"
            ".mcat.st-pat .cg-all{animation:mcWiggle .45s ease-in-out 3}"
            ".mcat.st-sad .cg-all{animation:mcBob 4.6s ease-in-out infinite}"
            ".mcat.st-angry .cg-all{animation:mcShake .09s linear 18}"
            ".mcat.st-annoy .cg-all{animation:mcHmph 1.9s ease-in-out 1}"
            ".mcat.st-spin .cg-all{animation:mcSpin 1.45s ease-in-out 2}"
            ".mcat.st-ball .cg-all{animation:mcBounce 1.3s ease-in-out 2}"
            ".mcat.st-music .cg-all{animation:mcSway 1.6s ease-in-out 2}"
            ".mcat.st-dance .cg-all{animation:mcDance 1.1s ease-in-out infinite}"
            ".mcat.st-yawn .cg-all{animation:mcYawnS 2.6s ease-in-out 1}"
            ".mcat.st-think .cg-all{animation:mcThinkS 3.2s ease-in-out infinite}"
            ".mcat.st-run .cg-all{animation:mcRunBob .5s ease-in-out infinite}"
            ".mcat.st-hungry .cg-all{animation:mcBob 2.1s ease-in-out infinite}"
            ".mcat.st-eat .cg-all{animation:mcMunchBob .6s ease-in-out infinite}"
            ".mcat.st-shy .cg-all{animation:mcShyWig 2.2s ease-in-out infinite}"
            ".mcat.st-hide .cg-all{animation:mcPeekBob 3s ease-in-out infinite}"
            ".mcat.st-peek .cg-all{animation:mcPeekBob 2.4s ease-in-out infinite}"
            ".mcat .cg-head{transform-origin:60px 82px}"
            ".mcat.st-annoy .cg-head{transform:translateX(-7px) rotate(-10deg)}"
            ".mcat.st-annoy .cg-blush{display:none}"
            ".mcat.st-shy .cg-head{transform:rotate(-3deg)}"
            ".mcat.st-study .cg-head{transform:translateY(2px)}"
            ".mcat .cg-tail{transform-origin:84px 108px;animation:mcTail 3s ease-in-out infinite}"
            ".mcat.st-exc .cg-tail,.mcat.st-ball .cg-tail,.mcat.st-spin .cg-tail,.mcat.st-dance .cg-tail,.mcat.st-run .cg-tail{animation:mcTail .45s ease-in-out infinite}"
            ".mcat.st-stress .cg-tail{animation:mcTail .9s ease-in-out infinite}"
            ".mcat.st-angry .cg-tail{animation:mcTail .3s linear infinite}"
            ".mcat.st-eat .cg-tail{animation:mcTail 1.5s ease-in-out infinite}"
            ".mcat.st-sleep .cg-tail{animation:none}"
            ".mcat .cg-ear-l{transform-origin:40px 28px;animation:mcEarT 6s ease-in-out infinite}"
            ".mcat .cg-ear-r{transform-origin:80px 28px;animation:mcEarT 6s ease-in-out .8s infinite}"
            ".mcat.st-sleep .cg-ear-l,.mcat.st-sleep .cg-ear-r,.mcat.st-pat .cg-ear-l,.mcat.st-pat .cg-ear-r{animation:none}"
            ".mcat.st-eat .cg-ear-l,.mcat.st-eat .cg-ear-r{animation:mcEarT 2.2s ease-in-out infinite}"
            ".mcat .cg-eyes-open{transform-origin:60px 56px;animation:mcBlink 5.6s infinite}"
            ".mcat .cg-heart{animation:mcPop 1.6s ease-out}"
            ".mcat .cg-zzz text{animation:mcPop 2.4s ease-in-out infinite}"
            ".mcat .cg-zzz text:nth-child(2){animation-delay:.5s}"
            ".mcat .cg-ball{animation:mcBall 2.9s cubic-bezier(.33,.66,.45,1) infinite}"
            ".mcat .cg-anger{transform-origin:113px 12px;animation:mcAnger .55s ease-in-out 4}"
            ".mcat .cg-steam circle{animation:mcFume 1.6s ease-out 2}"
            ".mcat .cg-steam circle:nth-child(2){animation-delay:.4s}"
            ".mcat .cg-music .n1{animation:mcNote 1.6s ease-out 2}"
            ".mcat .cg-music .n2{animation:mcNote 1.6s ease-out .55s 2}"
            ".mcat .cg-think circle{animation:mcPop 2.1s ease-in-out infinite}"
            ".mcat .cg-think circle:nth-child(2){animation-delay:.35s}"
            ".mcat .cg-think circle:nth-child(3){animation-delay:.7s}"
            ".mcat .cg-rumble .r1{animation:mcRumble 1.4s ease-in-out infinite}"
            ".mcat .cg-rumble .r2{animation:mcRumble 1.4s ease-in-out .25s infinite}"
            ".mcat .cg-rumble .r3{animation:mcRumble 1.4s ease-in-out .5s infinite}"
            ".mcat .cg-rumble text{animation:mcPop 1.7s ease-in-out infinite}"
            ".mcat .cg-mv-munch{transform-origin:60px 66.5px;animation:mcMunch .5s ease-in-out infinite}"
            ".mcat .cg-crumbs circle{animation:mcCrumbs 1.25s ease-in infinite}"
            ".mcat .cg-crumbs circle:nth-child(2){animation-delay:.4s}"
            ".mcat .cg-crumbs circle:nth-child(3){animation-delay:.8s}"
            ".mcat .cg-speed line{animation:mcSpeedFlick .34s linear infinite}"
            ".mcat .cg-speed line:nth-child(2){animation-delay:.11s}"
            ".mcat .cg-speed line:nth-child(3){animation-delay:.22s}"
            ".mcat.st-study .cg-eyes-open .cg-pupil{animation:mcScan 2.8s ease-in-out infinite}"
            ".mcat.st-eat .cg-eyes-shifty .cg-pupil{animation:mcDart 1.6s ease-in-out infinite}"
            ".mcat.st-dance .cg-arms-up .arm-l{transform-origin:38px 94px;animation:mcWave 1.1s ease-in-out infinite}"
            ".mcat.st-dance .cg-arms-up .arm-r{transform-origin:82px 94px;animation:mcWave 1.1s ease-in-out .55s infinite}"
            ".mcat.st-think .cg-hand-chin{transform-origin:72px 97px;animation:mcBob 2.6s ease-in-out infinite}"
            ".mcat.st-hide .mcat-bub,.mcat.st-peek .mcat-bub,.mcat.st-hang .mcat-bub,.mcat.st-edgesit .mcat-bub,.mcat.st-sidepeek .mcat-bub{display:none}"
            ".mcat.st-hide .mcat-say{top:auto;bottom:calc(100% + 10px)}"
            ".mcat.st-hide .mcat-say:after{top:auto;bottom:-4px}"
            ".mcat.st-peek .mcat-say{top:auto;bottom:calc(100% + 10px);right:auto;left:36px}"
            ".mcat.st-peek .mcat-say:after{top:auto;bottom:-4px;right:auto;left:18px}"
            ".mcat.peek-r .mcat-say{left:auto;right:38px}"
            ".mcat.peek-r .mcat-say:after{left:auto;right:18px}"
            ".mcat.away{opacity:0;pointer-events:none;transition:opacity .35s .7s}"
            ".mcat.glide{transition:left .75s cubic-bezier(.35,.8,.35,1),top .75s cubic-bezier(.35,.8,.35,1),opacity .3s}"
            ".cg-eyes-open .cg-pupil{transition:transform .18s ease-out}"
            ".mcat.st-hang svg{transform:scaleY(-1)}"
            ".mcat.st-hang .cg-all{animation:mcHangSway 2.6s ease-in-out infinite;transform-origin:60px 26px}"
            ".mcat.st-hang .cg-tail{animation:none}"
            ".mcat.st-edgesit .cg-all{animation:mcSitBob 2.3s ease-in-out infinite;transform-origin:60px 108px}"
            ".mcat.st-edgesit .cg-tail{animation:mcTail 1.2s ease-in-out infinite}"
            ".mcat.st-edgesit .mcat-say{top:auto;bottom:calc(100% + 8px)}"
            ".mcat.st-edgesit .mcat-say:after{top:auto;bottom:-4px}"
            ".mcat.st-sidepeek .cg-all{animation:mcLean 2.1s ease-in-out infinite;transform-origin:60px 108px}"
            ".mcat.st-sidepeek .mcat-say{top:auto;bottom:calc(100% + 10px);left:28px;right:auto}"
            ".mcat.st-sidepeek .mcat-say:after{top:auto;bottom:-4px;left:20px;right:auto}"
            ".mcat.st-sidepeek.peek-r .mcat-say{left:auto;right:28px}"
            ".mcat.st-sidepeek.peek-r .mcat-say:after{left:auto;right:20px}"
            ".mcat.st-eat .cg-snack .fish{transform-box:fill-box;transform-origin:50% 50%;animation:mcBite 1.9s ease-in-out infinite}"
            "@keyframes mcHangSway{0%,100%{transform:rotate(0)}50%{transform:rotate(5deg)}}"
            "@keyframes mcSitBob{0%,100%{transform:translateY(0) rotate(-2deg)}50%{transform:translateY(-2px) rotate(2deg)}}"
            "@keyframes mcLean{0%,100%{transform:translateX(0)}50%{transform:translateX(5px)}}"
            "@keyframes mcBite{0%,40%,100%{transform:translate(0,0)}55%,70%{transform:translate(-5px,-6px)}}"
            "#mcatzones{position:fixed;left:0;top:0;right:0;bottom:0;z-index:56;pointer-events:none;display:none}"
            "#mcatzones.show{display:block}"
            ".mz{position:absolute;border:2.5px dashed rgba(217,89,112,.5);border-radius:16px;background:rgba(217,89,112,.05);display:flex;align-items:center;justify-content:center;color:#d95970;font-size:12px;font-weight:800;opacity:.8;transition:opacity .15s,background .15s,transform .15s}"
            ".mz.on{border-color:#d95970;background:rgba(217,89,112,.16);opacity:1;transform:scale(.97)}"
            ".mz-top{top:8px;left:8px;right:8px;height:16%}"
            ".mz-bottom{bottom:8px;left:8px;right:8px;height:16%}"
            ".mz-left{left:8px;top:24%;bottom:24%;width:13%}"
            ".mz-right{right:8px;top:24%;bottom:24%;width:13%}"
            ".mz-center{left:17%;right:17%;top:24%;bottom:24%;border-radius:26px}"
            ".cg-wall{display:none}"
            ".mcat.st-hide .cg-wall{display:block}"
            "#mcatOff{position:fixed;inset:0;z-index:95;background:#000;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;opacity:0;pointer-events:none;transition:opacity .5s ease;direction:rtl}"
            "#mcatOff.show{opacity:1;pointer-events:auto;cursor:pointer}"
            "#mcatOff .off-eyes{width:min(220px,46vw);height:auto;animation:offBlink 4.6s ease-in-out infinite}"
            "#mcatOff .off-t1{color:#ffd964;font-weight:700;font-size:1.06rem}"
            "#mcatOff .off-t2{color:#cfd2da;font-size:.92rem}"
            "#mcatOff .off-t3{color:#6d6a63;font-size:.74rem;margin-top:16px}"
            "@keyframes offBlink{0%,86%,100%{transform:scaleY(1)}90%,94%{transform:scaleY(.06)}}"
            ""
        )
        js = r"""
(function(){
  const root = document.getElementById('manga_rdr');
  if (!root) return;
  const c = root.querySelector('.rdrC');
  const bar = root.querySelector('.zlv');
  const prog = root.querySelector('.rdrB');
  if (!c) return;
  const PH1 = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';
  let z = 1, panX = 0;
  const MIN = 0.5, MAX = 4;
  const baseWidth = () => Math.max(200, Math.min(900, window.innerWidth || 360));
  // مانند ریدر زنده: سند هیچ سرریزِ افقی ندارد (.rdrS با overflow-x:
  // clip میبُرد)؛ پنِ افقی با transform و لنگرِ زومِ جهت‌آزاد (کسری از
  // عرض) — در RTL دیگر زوم نمیپرد و نوارِ بالایی با چپ‌وراست‌کردن
  // خراب نمیشود.
  const applyZoom = (nz, cx, cy) => {
    nz = Math.min(MAX, Math.max(MIN, +nz || 1));
    const vw = window.innerWidth || 360;
    const sx = (typeof cx === 'number') ? cx : (vw / 2);
    const sy = (typeof cy === 'number') ? cy : (window.innerHeight / 2);
    const r0 = c.getBoundingClientRect();
    const topDoc = r0.top + window.scrollY;
    const oldW = Math.max(1, r0.width || 1);
    const frX = Math.max(0, Math.min(1, (sx - r0.left) / oldW));
    const relY = (window.scrollY + sy - topDoc) / Math.max(0.01, z);
    z = nz;
    const newW = Math.round(baseWidth() * z);
    c.style.maxWidth = 'none';
    c.style.width = newW + 'px';
    c.style.marginLeft = 'auto';
    c.style.marginRight = 'auto';
    if (newW > vw) {
      const r1 = c.getBoundingClientRect();
      const wantLeft = sx - frX * newW;
      panX = Math.max(0, Math.min(newW - vw, panX + (wantLeft - r1.left)));
      c.style.transform = 'translateX(' + Math.round(panX) + 'px)';
    } else {
      panX = 0;
      c.style.transform = '';
    }
    window.scrollTo(0, Math.max(0, topDoc + relY * z - sy));
    if (bar) bar.textContent = Math.round(z * 100) + '%';
    root.dataset.zoom = String(z);
  };
  const setZoom = (nz) => applyZoom(nz);
  const zoomBy = (f, cx, cy) => applyZoom(z * f, cx, cy);
  const idbOK = (() => { try { return !!window.indexedDB; } catch (err) { return false; } })();
  let _db = null;
  const idb = () => {
    if (!idbOK) return Promise.resolve(null);
    if (_db) return Promise.resolve(_db);
    return new Promise((res) => {
      try {
        const q = indexedDB.open('mangaLiveCache', 1);
        q.onupgradeneeded = (e) => {
          const d = e.target.result;
          if (!d.objectStoreNames.contains('imgs')) d.createObjectStore('imgs');
          if (!d.objectStoreNames.contains('ovls')) d.createObjectStore('ovls');
        };
        q.onsuccess = (e) => { _db = e.target.result; res(_db); };
        q.onerror = () => res(null);
        q.onblocked = () => res(null);
      } catch (err) { res(null); }
    });
  };
  const idbGet = (st, k) => idb().then((d) => {
    if (!d) return undefined;
    return new Promise((res) => {
      try {
        const t = d.transaction(st, 'readonly').objectStore(st).get(k);
        t.onsuccess = () => res(t.result);
        t.onerror = () => res(undefined);
      } catch (err) { res(undefined); }
    });
  });
  let _pruneBusy = false;
  const idbPut = (st, k, v) => idb().then((d) => {
    if (!d) return;
    try {
      const tx = d.transaction(st, 'readwrite');
      tx.objectStore(st).put(v, k);
      tx.oncomplete = () => { if (st === 'imgs' && !_pruneBusy && Math.random() < 0.1) pruneOld(); };
    } catch (err) {}
  });
  const pruneOld = () => {
    _pruneBusy = true;
    idb().then((d) => {
      if (!d) { _pruneBusy = false; return; }
      try {
        const rq = d.transaction('imgs', 'readonly').objectStore('imgs').count();
        rq.onsuccess = () => {
          const n = rq.result;
          if (n < 1600) { _pruneBusy = false; return; }
          const cur = d.transaction('imgs', 'readonly').objectStore('imgs').openCursor();
          const items = [];
          cur.onsuccess = (e) => {
            const c2 = e.target.result;
            if (c2) { items.push([c2.key, (c2.value && c2.value.t) || 0]); c2.continue(); }
            else {
              items.sort((a, b) => a[1] - b[1]);
              try {
                const tx2 = d.transaction('imgs', 'readwrite');
                items.slice(0, Math.max(0, n - 1200)).forEach((it) => {
                  tx2.objectStore('imgs').delete(it[0]);
                });
              } catch (err) {}
              _pruneBusy = false;
            }
          };
        };
        rq.onerror = () => { _pruneBusy = false; };
      } catch (err) { _pruneBusy = false; }
    });
  };
  const abs = (u) => { try { return new URL(u, location.href).href; } catch (err) { return u; } };
  const blobMem = new Map(), blobFail = new Map();
  const imgGet = (u) => {
    if (blobMem.has(u)) return Promise.resolve(blobMem.get(u));
    if (blobFail.has(u) && (Date.now() - blobFail.get(u)) < 8000) return Promise.reject(0);
    return idbGet('imgs', u).then((h) => {
      if (h && h.b) { const u2 = URL.createObjectURL(h.b); blobMem.set(u, u2); return u2; }
      return null;
    }).then((b) => {
      if (b) return b;
      return fetch(u).then((r) => { if (!r.ok) throw 0; return r.blob(); })
        .then((b2) => {
          idbPut('imgs', u, { b: b2, t: Date.now() });
          const u3 = URL.createObjectURL(b2);
          blobMem.set(u, u3);
          return u3;
        })
        .catch((err) => { blobFail.set(u, Date.now()); throw err; });
    });
  };
  const mgIO = ('IntersectionObserver' in window) ? new IntersectionObserver((es) => {
    for (const en of es) {
      const im = en.target;
      if (en.isIntersecting) {
        const r = im.dataset.src || '';
        if (r && !im.__infl && im.getAttribute('src') !== im.__cur) {
          if (im.__blob) { im.__cur = im.__blob; im.setAttribute('src', im.__blob); }
          else {
            im.__infl = 1;
            imgGet(r).then((u) => {
              im.__infl = 0; im.__blob = u; im.__cur = u;
              im.setAttribute('src', u);
            }).catch(() => {
              im.__infl = 0; im.__cur = r;
              im.setAttribute('src', r);
            });
          }
        }
      } else if (im.naturalWidth > 1 && im.naturalHeight > 1) {
        try { im.style.aspectRatio = im.naturalWidth + '/' + im.naturalHeight; } catch (err) {}
        if (im.getAttribute('src') !== PH1) im.setAttribute('src', PH1);
      }
    }
  }, { rootMargin: '220% 0px 220% 0px' }) : null;
  try {
    c.querySelectorAll('img[data-src]').forEach((im) => {
      im.setAttribute('src', PH1);
      im.decoding = 'async';
      if (mgIO) mgIO.observe(im);
      else {
        imgGet(im.dataset.src).then((u) => { im.setAttribute('src', u); })
          .catch(() => { im.setAttribute('src', im.dataset.src); });
      }
    });
  } catch (err) {}
  const rtryChip = document.createElement('button');
  rtryChip.type = 'button';
  rtryChip.id = 'rtryChip';
  rtryChip.innerHTML = '<span class="sp">&#8635;</span><span class="tx">' + UT('rdr.retry', 'تلاش دوباره') + '</span>';
  try { document.body.appendChild(rtryChip); } catch (err) {}
  const RTRY_L = [800, 2000, 4000, 8000, 15000];
  let rtryBusy = 0, rtryBad = 0;
  const rtryState = (cls, txt) => {
    try {
      rtryChip.className = cls;
      rtryChip.querySelector('.tx').textContent = txt;
    } catch (err) {}
  };
  const rtrySync = () => {
    if (rtryBusy > 0) rtryState('show busy', UT('rdr.retrying', 'در حال تلاش…'));
    else if (rtryBad > 0) rtryState('show', UT('rdr.retry', 'تلاش دوباره'));
    else rtryState('', UT('rdr.retry', 'تلاش دوباره'));
  };
  const rtryKick = (im, now) => {
    if (im.__ok || im.__rl) return;
    if (im.__pend) { im.__pend = 0; rtryBusy--; }
    const src = im.dataset.src || '';
    if (!src) return;
    const rung = im.__run || 0;
    if (rung >= RTRY_L.length) {
      if (!im.__bad) { im.__bad = 1; rtryBad++; }
      rtrySync();
      return;
    }
    im.__rl = 1; rtryBusy++;
    im.__run = rung + 1;
    rtrySync();
    const d = (now && rung === 0) ? 0
      : RTRY_L[rung] * (0.75 + Math.random() * 0.5);
    setTimeout(() => {
      im.__rl = 0;
      if (im.__ok) { rtrySync(); return; }
      const key = (rung === 0) ? src
        : src + (src.indexOf('?') >= 0 ? '&' : '?') + '_mr=' + Date.now();
      im.__key = key;
      try { blobFail.delete(src); blobFail.delete(key); } catch (err) {}
      im.__pend = 1;
      im.__infl = 1;
      imgGet(key).then((u) => {
        im.__infl = 0;
        if (im.__ok) {
          if (im.__pend) { im.__pend = 0; rtryBusy--; }
          rtrySync(); return;
        }
        im.__blob = u; im.__cur = u;
        im.setAttribute('src', u);
      }).catch(() => {
        im.__infl = 0;
        if (im.__ok) {
          if (im.__pend) { im.__pend = 0; rtryBusy--; }
          rtrySync(); return;
        }
        im.__cur = key;
        im.setAttribute('src', key);
      });
      rtrySync();
    }, d);
  };
  c.querySelectorAll('img[data-src]').forEach((im) => {
    im.addEventListener('load', () => {
      if (im.__ok || im.getAttribute('src') === PH1) return;
      im.__ok = 1;
      if (im.__pend) { im.__pend = 0; rtryBusy--; }
      if (im.__bad) { im.__bad = 0; rtryBad--; }
      try {
        blobFail.delete(im.dataset.src);
        if (im.__key) blobFail.delete(im.__key);
      } catch (err) {}
      rtrySync();
    });
    im.addEventListener('error', () => {
      if (im.__ok || im.getAttribute('src') === PH1) return;
      rtryKick(im);
    });
  });
  rtryChip.addEventListener('click', () => {
    let n = 0;
    c.querySelectorAll('img[data-src]').forEach((im) => {
      if (im.__ok || !im.__run) return;
      im.__run = 0;
      n++;
      rtryKick(im, true);
    });
    if (n > 0) rtryState('show busy', UT('rdr.retrying', 'در حال تلاش…'));
  });
  window.addEventListener('online', () => {
    c.querySelectorAll('img[data-src]').forEach((im) => {
      if (im.__ok || !im.__run) return;
      im.__run = 0;
      rtryKick(im, true);
    });
  });
  root.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-act]');
    if (!btn || !root.contains(btn)) return;
    e.preventDefault();
    const act = btn.getAttribute('data-act');
    if (act === 'close') {
      try {
        const isFs = document.fullscreenElement || document.webkitFullscreenElement;
        if (isFs) (document.exitFullscreen || document.webkitExitFullscreen).call(document);
      } catch (err) {}
      try { window.close(); } catch (err) {}
      try { if (history.length > 1) history.back(); } catch (err) {}
      return;
    }
    if (act === 'zoom-in') zoomBy(1.25);
    else if (act === 'zoom-out') zoomBy(0.8);
    else if (act === 'zoom-fit') setZoom(1);
    else if (act === 'fs') {
      const isFs = document.fullscreenElement || document.webkitFullscreenElement
                || document.mozFullScreenElement || document.msFullscreenElement;
      if (isFs) {
        (document.exitFullscreen || document.webkitExitFullscreen
         || document.mozCancelFullScreen || document.msExitFullscreen).call(document);
      } else {
        const el = document.documentElement;
        const req = el.requestFullscreen || el.webkitRequestFullscreen
                 || el.mozRequestFullScreen || el.msRequestFullscreen;
        if (req) {
          try { req.call(el); } catch (err) {
            try { req.call(root); } catch (err2) {}
          }
        }
      }
    }
  });
  window.addEventListener('wheel', (e) => {
    if (!e.ctrlKey && !e.metaKey) return;
    e.preventDefault();
    zoomBy(e.deltaY < 0 ? 1.12 : 1 / 1.12, e.clientX, e.clientY);
  }, { passive: false });
  window.addEventListener('dblclick', (e) => {
    e.preventDefault();
    if (z > 1.3) setZoom(1);
    else zoomBy(2.2, e.clientX, e.clientY);
  });
  let pinch = null, pan = null, lastTap = 0, lastTapX = 0, lastTapY = 0;
  const dist = (a, b) => Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
  const mid = (a, b) => ({ x: (a.clientX + b.clientX) / 2, y: (a.clientY + b.clientY) / 2 });
  const tapOnCtl = (t) => {
    try { return !!(t && t.closest && t.closest('button, a, input, select, textarea, .rdr-btn')); }
    catch (err) { return false; }
  };
  document.addEventListener('touchstart', (e) => {
    if (e.touches.length === 2) {
      pinch = { startDist: dist(e.touches[0], e.touches[1]), startZ: z };
      pan = null;
    } else if (e.touches.length === 1) {
      pan = { x: e.touches[0].clientX, y: e.touches[0].clientY,
              st: window.scrollY, px: panX, moved: false };
    }
  }, { passive: true });
  document.addEventListener('touchmove', (e) => {
    if (pinch && e.touches.length === 2) {
      e.preventDefault();
      const d = dist(e.touches[0], e.touches[1]);
      const m = mid(e.touches[0], e.touches[1]);
      applyZoom(pinch.startZ * (d / Math.max(1, pinch.startDist)), m.x, m.y);
    } else if (pan && e.touches.length === 1) {
      const t1 = e.touches[0];
      const dx = t1.clientX - pan.x, dy = t1.clientY - pan.y;
      if (Math.abs(dx) > 12 || Math.abs(dy) > 12)
        pan.moved = true;
      if (z > 1.05) {
        e.preventDefault();
        const vw2 = window.innerWidth || 360;
        const w2 = c.offsetWidth || 0;
        if (w2 > vw2) {
          panX = Math.max(0, Math.min(w2 - vw2, pan.px + dx));
          c.style.transform = 'translateX(' + Math.round(panX) + 'px)';
        }
        window.scrollTo(0, Math.max(0, pan.st - dy));
      }
    }
  }, { passive: false });
  document.addEventListener('touchend', (e) => {
    if (e.touches.length < 2) pinch = null;
    if (e.touches.length === 0) {
      const ct = (e.changedTouches && e.changedTouches[0]) || null;
      if (pan && !pan.moved && ct && !tapOnCtl(ct.target)) {
        const now = Date.now();
        if (now - lastTap <= 320
            && Math.abs(ct.clientX - lastTapX) < 44
            && Math.abs(ct.clientY - lastTapY) < 44) {
          if (z > 1.3) setZoom(1);
          else zoomBy(2.2, ct.clientX, ct.clientY);
          lastTap = 0;
        } else {
          lastTap = now; lastTapX = ct.clientX; lastTapY = ct.clientY;
        }
      }
      pan = null;
    }
  });
  document.addEventListener('touchcancel', () => { pinch = null; pan = null; });
  const updateProgress = () => {
    if (!prog) return;
    const m = document.documentElement.scrollHeight - window.innerHeight;
    const pc = m > 0 ? Math.min(100, Math.max(0, window.scrollY / m * 100)) : 0;
    prog.style.width = pc + '%';
    const pl = document.getElementById('progLab');
    if (pl) {
      const fa = (v) => String(v).replace(/[0-9]/g, (d) => '\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9'[+d]);
      let txt = fa(Math.round(pc)) + '\u066a';
      try {
        if (typeof stackCount === 'function' && typeof curPageIdx === 'function')
          txt += ' \u00b7 ' + fa(curPageIdx() + 1) + '/' + fa(stackCount());
      } catch (err) {}
      pl.textContent = txt;
    }
  };
  window.addEventListener('scroll', () => { updateProgress(); updateSeekPos(); }, { passive: true });
  window.addEventListener('resize', () => { if (z !== 1) applyZoom(z); updateProgress(); updateFan(); updateSeekPos(); });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      try {
        const isFs = document.fullscreenElement || document.webkitFullscreenElement;
        if (isFs) { (document.exitFullscreen || document.webkitExitFullscreen).call(document); return; }
      } catch (err) {}
      try { window.close(); } catch (err) {}
    } else if (e.key === '+' || e.key === '=') zoomBy(1.15);
    else if (e.key === '-' || e.key === '_') zoomBy(0.87);
    else if (e.key === '0') setZoom(1);
    else if (e.key === 'f' || e.key === 'F') {
      const btn = root.querySelector('[data-act="fs"]');
      if (btn) btn.click();
    }
  });
  const fab = document.getElementById('fab');
  let fanState = 0;
  const fanDefs = [
    { key: 'zin', ic: '+', lb: UT('rdr.zin', 'نزدیک') },
    { key: 'zout', ic: '\u2212', lb: UT('rdr.zout', 'دور') },
    { key: 'zfit', ic: '\u2194', lb: UT('rdr.zfit', 'پهنا') },
    { key: 'fs', ic: '\u26f6', lb: UT('rdr.zfs', 'تمام') },
    { key: 'seek', ic: '\u21c4', lb: UT('rdr.zseek', 'صفحه‌ها') }
  ];
  const fans = fanDefs.map((def) => {
    const fb = document.createElement('button');
    fb.type = 'button';
    fb.className = 'fbtn';
    fb.innerHTML = '<span class="ic"></span><span class="lb"></span>';
    fb.setAttribute('data-k', def.key);
    document.body.appendChild(fb);
    fb.addEventListener('click', (e) => {
      e.stopPropagation();
      const k = fb.getAttribute('data-k');
      if (k === 'zin') zoomBy(1.25);
      else if (k === 'zout') zoomBy(0.8);
      else if (k === 'zfit') setZoom(1);
      else if (k === 'fs') {
        const b = root.querySelector('[data-act="fs"]');
        if (b) b.click();
      }
      else if (k === 'seek') {
        fanState = (fanState === 2) ? 1 : 2;
        updateFan();
        updateSeekVis();
        return;
      }
      updateFan();
    });
    return fb;
  });
  const placeFabXY = (cx, cy) => {
    const r = 30;
    const x = Math.min(Math.max(cx, r + 4), window.innerWidth - r - 4);
    const y = Math.min(Math.max(cy, r + 46), window.innerHeight - r - 8);
    fab.style.left = (x - r) + 'px';
    fab.style.top = (y - r) + 'px';
    fab.style.right = 'auto';
    fab.style.bottom = 'auto';
    fab.style.marginLeft = '0';
  };
  try {
    const sp = JSON.parse(localStorage.getItem('mangaRdrFab') || 'null');
    if (sp && typeof sp.x === 'number') placeFabXY(sp.x, sp.y);
  } catch (err) {}
  let fdrag = null;
  fab.addEventListener('pointerdown', (e) => {
    fdrag = { x: e.clientX, y: e.clientY, moved: false };
    try { fab.setPointerCapture(e.pointerId); } catch (err) {}
    e.preventDefault();
  });
  fab.addEventListener('pointermove', (e) => {
    if (!fdrag) return;
    const dx = e.clientX - fdrag.x, dy = e.clientY - fdrag.y;
    if (!fdrag.moved && Math.hypot(dx, dy) > 10) fdrag.moved = true;
    if (fdrag.moved) {
      fdrag.x = e.clientX; fdrag.y = e.clientY;
      placeFabXY(e.clientX, e.clientY);
      updateFan();
    }
  });
  const fabUp = () => {
    if (!fdrag) return;
    const moved = fdrag.moved;
    fdrag = null;
    if (moved) {
      try {
        const fr = fab.getBoundingClientRect();
        localStorage.setItem('mangaRdrFab',
          JSON.stringify({ x: fr.left + fr.width / 2, y: fr.top + fr.height / 2 }));
      } catch (err) {}
      return;
    }
    fanState = fanState ? 0 : 1;
    updateFan();
    updateSeekVis();
  };
  fab.addEventListener('pointerup', fabUp);
  fab.addEventListener('pointercancel', () => { fdrag = null; });
  const fanPositions = () => {
    const fr = fab.getBoundingClientRect();
    const cx = fr.left + fr.width / 2, cy = fr.top + fr.height / 2;
    const n = fans.length;
    const bis = Math.atan2(window.innerHeight / 2 - cy,
                          window.innerWidth / 2 - cx);
    const step = Math.min(40 * Math.PI / 180, 2.6 / Math.max(1, n - 1));
    const half = step * (n - 1) / 2;
    const R = Math.min(104, Math.max(84, window.innerWidth * 0.16));
    const pts = [];
    for (let i = 0; i < n; i++) {
      const a = bis - half + i * step;
      pts.push({ x: cx + Math.cos(a) * R, y: cy + Math.sin(a) * R });
    }
    const fabPt = { x: cx, y: cy };
    const sep = (pa, pb, w) => {
      const dx = pb.x - pa.x, dy = pb.y - pa.y;
      const ox = 68 - Math.abs(dx), oy = 68 - Math.abs(dy);
      if (ox > 0 && oy > 0) {
        if (ox <= oy) {
          const s = (dx >= 0 ? 1 : -1) * ox * w;
          pa.x -= s; pb.x += s;
        } else {
          const s = (dy >= 0 ? 1 : -1) * oy * w;
          pa.y -= s; pb.y += s;
        }
        return true;
      }
      return false;
    };
    for (let it = 0; it < 20; it++) {
      let moved = false;
      for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++)
        if (sep(pts[i], pts[j], 0.3)) moved = true;
      for (let i = 0; i < n; i++) {
        const dx = pts[i].x - fabPt.x, dy = pts[i].y - fabPt.y;
        const ox = 74 - Math.abs(dx), oy = 74 - Math.abs(dy);
        if (ox > 0 && oy > 0) {
          if (ox <= oy) pts[i].x += (dx >= 0 ? 1 : -1) * ox;
          else pts[i].y += (dy >= 0 ? 1 : -1) * oy;
          moved = true;
        }
      }
      for (const p of pts) {
        p.x = Math.min(Math.max(p.x, 32), window.innerWidth - 32);
        p.y = Math.min(Math.max(p.y, 76), window.innerHeight - 32);
      }
      if (!moved) break;
    }
    return pts;
  };
  function updateFan() {
    const pts = fanPositions();
    const show = fanState >= 1;
    fab.textContent = show ? UT('rdr.close', '\u2715') : UT('rdr.menu', 'منو');
    fab.classList.toggle('open', show);
    for (let i = 0; i < fans.length; i++) {
      const fb = fans[i], def = fanDefs[i];
      fb.style.left = (pts[i].x - 29) + 'px';
      fb.style.top = (pts[i].y - 29) + 'px';
      fb.querySelector('.ic').textContent = def.ic;
      fb.querySelector('.lb').textContent = def.lb;
      fb.classList.toggle('show', show);
    }
  }
  const seek = document.getElementById('seek'),
        sth = document.getElementById('sth'),
        sfill = document.getElementById('sfill'),
        sbub = document.getElementById('sbub'),
        rail = document.getElementById('rail');
  const stackCount = () => Math.max(1, c.children.length);
  const curPageIdx = () => {
    let best = 0;
    for (let i = 0; i < c.children.length; i++) {
      const ch = c.children[i];
      if (ch.getBoundingClientRect().top <= window.innerHeight * 0.35) best = i;
      else break;
    }
    return best;
  };
  const goToPage = (idx) => {
    const n = c.children.length;
    idx = Math.max(0, Math.min(n - 1, idx));
    const ch = c.children[idx];
    if (!ch) return;
    window.scrollTo(0, Math.max(0, ch.getBoundingClientRect().top + window.scrollY - 54));
  };
  const setSeekFrac = (f) => {
    const n = stackCount();
    const pg = Math.min(n, Math.max(1, Math.round(f * (n - 1)) + 1));
    const w = Math.max(0, rail.clientWidth - 96);
    const x = 48 + f * w;
    sth.style.left = x + 'px';
    sfill.style.width = (f * w) + 'px';
    sbub.style.left = x + 'px';
    sbub.textContent = UT('rdr.page', 'صفحهٔ ') + String(pg).replace(/\d/g, (d) => '\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9'[+d]) + UT('rdr.of', ' از ') + String(n).replace(/\d/g, (d) => '\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9'[+d]);
    return pg;
  };
  const updateSeekPos = () => {
    if (!seek.classList.contains('show')) return;
    const n = stackCount();
    setSeekFrac(n > 1 ? Math.min(n - 1, curPageIdx()) / (n - 1) : 0);
  };
  const updateSeekVis = () => {
    seek.classList.toggle('show', fanState === 2);
    if (fanState === 2) updateSeekPos();
  };
  let sdrag = false, sraf = 0;
  const seekFromX = (cx) => {
    const r = rail.getBoundingClientRect();
    const w = Math.max(1, r.width - 96);
    const f = Math.min(1, Math.max(0, (cx - r.left - 48) / w));
    const pg = setSeekFrac(f);
    if (!sraf) sraf = requestAnimationFrame(() => {
      sraf = 0;
      goToPage(pg - 1);
    });
  };
  sth.addEventListener('pointerdown', (e) => {
    sdrag = true;
    try { sth.setPointerCapture(e.pointerId); } catch (err) {}
    e.preventDefault();
  });
  sth.addEventListener('pointermove', (e) => { if (sdrag) seekFromX(e.clientX); });
  sth.addEventListener('pointerup', () => { sdrag = false; });
  sth.addEventListener('pointercancel', () => { sdrag = false; });
  rail.addEventListener('pointerdown', (e) => {
    if (e.target === sth) return;
    if (e.target.closest && e.target.closest('.snav')) return;
    seekFromX(e.clientX);
  });
  document.getElementById('sprev').addEventListener('click', () => {
    goToPage(curPageIdx() - 1); updateSeekPos();
  });
  document.getElementById('snext').addEventListener('click', () => {
    goToPage(curPageIdx() + 1); updateSeekPos();
  });
  document.addEventListener('pointerdown', (e) => {
    if (fanState === 0) return;
    if (e.target === fab || fab.contains(e.target)) return;
    for (let i = 0; i < fans.length; i++)
      if (fans[i].contains(e.target)) return;
    if (seek.contains(e.target)) return;
    fanState = 0;
    updateFan();
    updateSeekVis();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') { fanState = 0; updateFan(); updateSeekVis(); }
  });
  var MCAT = document.getElementById('mcat');
  if (MCAT) {
  var mcatBub = MCAT.querySelector('.mcat-bub');
  var mcatSayEl = MCAT.querySelector('.mcat-say');
  var MCAT_USE_S = true;
  var FAD = '۰۱۲۳۴۵۶۷۸۹';
  function faN(v) { return String(v).replace(/[0-9]/g, function (d) { return FAD[+d]; }); }
  function faR(a) { return a[Math.floor(Math.random() * a.length)]; }
  var mcatScrollEl = null;
  if (MCAT_USE_S) { try { if (typeof s !== 'undefined' && s && s.scrollTop !== undefined && s !== window) mcatScrollEl = s; } catch (err) {} }
  function mcatInfo() {
    var m, y;
    if (mcatScrollEl) { m = mcatScrollEl.scrollHeight - mcatScrollEl.clientHeight; y = mcatScrollEl.scrollTop; }
    else { m = document.documentElement.scrollHeight - window.innerHeight; y = window.scrollY || window.pageYOffset || 0; }
    if (m < 0) m = 0;
    return { m: m, y: y, pct: Math.min(1, Math.max(0, y / Math.max(1, m))), atEnd: m > 320 && (m - y) < 5 };
  }
  var MCAT_PAT = UT('say.pat', ['میییو~', 'آخ جووون، همینه!', 'بغلم کن دیگه!', 'ولی ول نکن ها~', 'دلم برات تنگ شده بود!']);
  var MCAT_READ = UT('say.read', ['ورق بزن دیگه!', 'اوه، ادامه‌ش چیه؟!', 'این صحنه وای…', 'چایی میل دارید؟', 'اِ این یکی الان چی گفت؟!', 'ترجمه‌ش دست من بود، بهتر میشد!']);
  var MCAT_STUDY = UT('say.study', ['ششش! دارم به قسمتِ خوبِ قصه میرسم…', 'یه لحظه وایسا، خودم می‌خونم!', 'هوم… هوم… این فصل چی میگه!', 'این کتاب مالِ منه ها، دست نزن!']);
  var MCAT_THINK = UT('say.think', ['هوم… بعدِ این چی میشه؟', 'اگه نویسنده یه چیزِ دیگه میگفت چی؟', 'هوم هوم… دارم فکر میکنم…', 'چرا هی دلم میخواد دُم بگیرم؟!']);
  var MCAT_YAWN = UT('say.yawn', ['خمووووام…', 'یه چرتِ کوچولو بد نیست…', 'خمیازه اومد، شرمنده!', 'چشمام سنگین شدن…']);
  var MCAT_DANCE = UT('say.dance', ['لالالا~ دارم می‌رقصم!', 'حالِ دلم خوبه، ببین!', 'رقصِ گربه‌ایِ خاصِ خودم!', 'بزن برقصیم!']);
  var MCAT_RUN = UT('say.run', ['نمیگیری منو!', 'دورِ صفحه می‌چرخم، ووووو!', 'برس به من، برسسس!', 'هوووووم، چه حالی میده!']);
  var MCAT_HUNGRY = UT('say.hungry', ['قار قور؟!… شرمنده', 'شکمم داره آهنگ میخونه!', 'وا، این صدا از شکمم بود؟!', 'غذا یادم رفت بخورم…', 'کسی بیسکویت داره؟']);
  var MCAT_EAT = UT('say.eat', ['چیزی ندیدم ها! تو هم ندیدی؟!', 'نگاه نکن! دارم شام میخورم!', 'این مالِ من شد، تو که ندیدیش!', 'ششش… صدای جویدن نمیاد!']);
  var MCAT_SHY = UT('say.shy', ['خجالت کشیدم ببینم!', 'چرا اینجوری نگاه میکنی؟!', 'وییی… به کسی نگو!', 'اِ خودتو ندیدم!']);
  var MCAT_WAKE = UT('say.wake', ['نخوابیدم ها! چشمام فقط استراحت میکردن!', 'من؟! خواب نبودم اصلاً!']);
  var MCAT_ANNOY = UT('say.annoy', ['وایسا وایسا، بسه!', 'نازکیدم ول کن!', 'خیلی شیطون شدی ها!', 'بسه دیگه، گوشه‌م میرم!']);
  var MCAT_ANGRY = UT('say.angry', ['آخ! چرا میزنی؟!', 'دلم شکست تو!', 'بدجنسیه این کارت!']);
  var MCAT_AWAY = UT('say.away', ['خوش باش، من رفتم!', 'قهرم ازت، جدی!', 'بای بای، دیگه نمیام!']);
  var MCAT_BACK = UT('say.back', ['ولی دلم تنگ شد، برگشتم…', 'قصه‌ات رو ول نمیکردم دیگه…', 'باشه باشه، بخشیدمت!']);
  var MCAT_HIDE_SAY = UT('say.hide', ['پشتِ دیوال قایم شدم، گیرم نمیاری!', 'هیشکی اینجا منو پیدا نمیکنه!', 'از پشتِ دیوال دارم نگاه می‌کنم!']);
  var MCAT_FOUND = UT('say.found', ['اِ پیدام کردی؟! زرنگی!', 'وا! از کجا فهمیدی اینجام؟!', 'باشه باشه، باختم!']);
  var MCAT_OFF = UT('say.off', ['بس بود! صفحه رو خاموش می‌کنم!', 'دیگه بسه! دکمهٔ خاموش کجاست…']);
  var MCAT_MILE = UT('say.mile', ['یه چهارمش رفت!', 'نصفش رفته، بزن بریم!', 'سه چهارمش که تمومه، وایسا!']);
  var MCAT_HANG = UT('say.hang', ['وا! چطور وارونه شدم؟!', 'از سقف آویزونم، جاذبه هی بلاگه!', 'خونم رفت گوشم! یعنی… پام شد سرم!']);
  var MCAT_SIT = UT('say.sit', ['اینجا دمِ صفحه خنک‌تره!', 'لبِ پایین، جای آدمیزادها!', 'نشستم راحت، خبری نیست؟']);
  var MCAT_SIDE = UT('say.side', ['از این ور فقط نگاه می‌کنم…', 'من؟! من که هیشی کار نکردم!', 'یه سرک از بغل زدم!']);
  var MCAT_PIC = UT('say.pic', ['وای! این صحنه رو به یاد دارم!', 'اِ این قاب رو قبلاً دیدم!', 'این تصویر خوشگله! مال کدوم فصله؟']);
  var MCAT_DROP = UT('say.drop', ['حوووپا!', 'دوباره بنداز، دوباره!', 'ایول، جالب بود!']);
  var MCAT_BACK2 = UT('say.back2', ['جای خودم، جای خودم!', 'خوش بود؟ یه بار دیگه بندازم؟!']);
  var ACT_DUR = { 'st-spin': 3000, 'st-ball': 3200, 'st-music': 3400, 'st-dance': 3600, 'st-study': 5200, 'st-think': 3600, 'st-yawn': 2800, 'st-hungry': 3000, 'st-eat': 5200, 'st-run': 6200, 'st-hang': 7000, 'st-edgesit': 6500, 'st-sidepeek': 6000 };
  var ACT_POOL = ['st-spin', 'st-spin', 'st-ball', 'st-ball', 'st-music', 'st-music', 'st-dance', 'st-dance', 'st-study', 'st-study', 'st-think', 'st-yawn', 'st-hungry', 'st-eat', 'st-eat', 'st-run'];
  var ACT_SAY = {
    'st-spin': UT('say.spin', ['دُمم بیا اینجا!', 'ووووو، سرم گیج رفت!']),
    'st-ball': UT('say.ball', ['بگیر بگیر!', 'توپ! توپ!', 'بالا بَر، اَ بالا!']),
    'st-music': UT('say.music', ['هوم هوم~', 'لالالالا~', 'دلم میخواد آهنگ بخونم~']),
    'st-dance': MCAT_DANCE,
    'st-study': MCAT_STUDY,
    'st-think': MCAT_THINK,
    'st-yawn': MCAT_YAWN,
    'st-hungry': MCAT_HUNGRY,
    'st-eat': MCAT_EAT,
    'st-run': MCAT_RUN,
    'st-hang': MCAT_HANG,
    'st-edgesit': MCAT_SIT,
    'st-sidepeek': MCAT_SIDE
  };
  var mcatState = 'st-read';
  var mcatLastTs = 0, mcatLastY = -1, mcatFastT = 0, mcatMoveT = Date.now();
  var mcatBotT = 0, mcatPatT = 0, mcatSayUntil = 0;
  var mcatHideTill = 0, mcatAwayTill = 0, mcatPeekTill = 0, mcatPeekR = false;
  var mcatAnnoyT = 0, mcatAngryT = 0, mcatShyT = 0;
  var mcatActT = 0, mcatActSt = '', mcatActCd = 0, mcatNextAct = '';
  var mcatRunning = false, mcatRunT = null;
  var mcatTaps = [], mcatAngerN = 0, mcatAngerLast = 0;
  var mcatTeaseN = 0;
  var mcatSaved = null, mcatMile = 0;
  var mcatForceSt = '', mcatForceTill = 0;
  var mcatZoneBack = 0, ZONES = null, mcatZoneCur = '';
  var mcatLastN = -1, mcatLastMk = '';
  function mcatSet(st) { if (mcatState === st) return; MCAT.classList.remove(mcatState); MCAT.classList.add(st); mcatState = st; }
  function mcatSayNow(txt, ms) { mcatSayEl.textContent = txt; mcatSayEl.classList.add('show'); mcatSayUntil = Date.now() + (ms || 5000); }
  function mcatUpdate() {
    var inf = mcatInfo();
    var txt = faN(Math.round(inf.pct * 100)) + '٪';
    if (typeof curPageIdx === 'function' && typeof stackCount === 'function') txt += ' · ' + faN(curPageIdx() + 1) + '/' + faN(stackCount());
    if (mcatBub) mcatBub.textContent = txt;
  }
  function mcatGlide(fn) { MCAT.classList.add('glide'); fn(); setTimeout(function () { MCAT.classList.remove('glide'); }, 800); }
  function mcatPlace(cx, cy) {
    var x = Math.min(Math.max(cx, 52), window.innerWidth - 52);
    var y = Math.min(Math.max(cy, 78), window.innerHeight - 112);
    MCAT.style.left = (x - MCAT.offsetWidth / 2) + 'px';
    MCAT.style.top = (y - MCAT.offsetHeight / 2) + 'px';
    MCAT.style.right = 'auto';
    MCAT.style.bottom = 'auto';
  }
  function mcatRestore(say) {
    mcatHideTill = mcatAwayTill = mcatPeekTill = 0;
    MCAT.classList.remove('away', 'peek-r', 'hide-l');
    if (mcatSaved) { var sv = mcatSaved; mcatGlide(function () { mcatPlace(sv.x, sv.y); }); }
    mcatMoveT = Date.now();
    mcatSet('st-read');
    if (say) mcatSayNow(say, 3000);
    mcatTick();
  }
  function mcatGoHide() {
    if (mcatState === 'st-hide') return;
    var r = MCAT.getBoundingClientRect();
    var hw = MCAT.offsetWidth || 70, hh = MCAT.offsetHeight || 82;
    mcatSaved = { x: r.left + r.width / 2, y: r.top + r.height / 2 };
    var onRight = (r.left + r.width / 2) >= window.innerWidth / 2;
    MCAT.classList.toggle('hide-l', !onRight);
    var hy = Math.min(Math.max(r.top + r.height / 2, window.innerHeight * 0.36),
      window.innerHeight - hh / 2 - 30);
    mcatGlide(function () {
      MCAT.style.left = (onRight ? window.innerWidth - hw + 1 : -1) + 'px';
      MCAT.style.top = (hy - hh / 2) + 'px';
      MCAT.style.right = 'auto';
      MCAT.style.bottom = 'auto';
    });
    mcatSet('st-hide');
    mcatHideTill = Date.now() + 12000 + Math.random() * 6000;
    mcatSayNow(faR(MCAT_HIDE_SAY), 2800);
  }
  function mcatGoAway() {
    if (mcatState === 'st-hide' || mcatState === 'st-peek' || MCAT.classList.contains('away')) return;
    var r = MCAT.getBoundingClientRect();
    mcatSaved = { x: r.left + r.width / 2, y: r.top + r.height / 2 };
    mcatPeekR = r.left + r.width / 2 >= window.innerWidth / 2;
    var ay = Math.min(Math.max(r.top + r.height / 2, 130), window.innerHeight - 110);
    mcatGlide(function () {
      MCAT.style.left = (mcatPeekR ? window.innerWidth - 30 : -34) + 'px';
      MCAT.style.top = (ay - MCAT.offsetHeight / 2) + 'px';
      MCAT.style.right = 'auto';
    });
    setTimeout(function () { MCAT.classList.add('away'); }, 700);
    mcatAwayTill = Date.now() + 25000 + Math.random() * 15000;
    mcatSayNow(faR(MCAT_AWAY), 2200);
  }
  function mcatStartPeek() {
    mcatAwayTill = 0;
    MCAT.classList.remove('away');
    if (mcatPeekR) MCAT.classList.add('peek-r'); else MCAT.classList.remove('peek-r');
    mcatSet('st-peek');
    mcatPeekTill = Date.now() + 9000;
    mcatSayNow(UT('say.still_angry', '…هنوز قهرم ها!'), 2400);
  }
  var mcatOffEl = document.getElementById('mcatOff');
  var mcatOffTimer = null;
  function mcatWake() {
    if (!mcatOffEl || !mcatOffEl.classList.contains('show')) return;
    mcatOffEl.classList.remove('show');
    if (mcatOffTimer) { clearTimeout(mcatOffTimer); mcatOffTimer = null; }
    mcatRestore('دیدی چیکار می‌کنم؟! دیگه اذیت نکن~');
  }
  function mcatBlackout() {
    mcatTeaseN = 0;
    mcatTaps = [];
    mcatAnnoyT = mcatAngryT = mcatPatT = mcatActT = mcatShyT = 0;
    mcatSayNow(faR(MCAT_OFF), 1900);
    mcatSet('st-annoy');
    mcatTick();
    setTimeout(function () {
      if (!mcatOffEl) return;
      mcatOffEl.classList.add('show');
      if (mcatOffTimer) clearTimeout(mcatOffTimer);
      mcatOffTimer = setTimeout(mcatWake, 5200);
    }, 1600);
  }
  function mcatStartRun() {
    if (mcatRunning) return;
    var r = MCAT.getBoundingClientRect();
    mcatSaved = { x: r.left + r.width / 2, y: r.top + r.height / 2 };
    mcatRunning = true;
    mcatActSt = 'st-run';
    mcatActT = Date.now() + 6200;
    mcatMoveT = Date.now();
    mcatSayNow(faR(MCAT_RUN), 3400);
    mcatSet('st-run');
    var vw = window.innerWidth, vh = window.innerHeight;
    var mx = 54, ty = 84, by = vh - 90;
    var pts = [[mx, ty], [vw - mx, ty], [vw - mx, by], [mx, by], [mx, ty]];
    MCAT.classList.add('glide');
    var i = 0;
    function step() {
      if (!mcatRunning) return;
      mcatPlace(pts[i][0], pts[i][1]);
      i++;
      if (i < pts.length) mcatRunT = setTimeout(step, 1050);
      else mcatEndRun(false);
    }
    step();
  }
  function mcatEndRun(interrupted) {
    if (!mcatRunning) return;
    mcatRunning = false;
    if (mcatRunT) { clearTimeout(mcatRunT); mcatRunT = null; }
    MCAT.classList.remove('glide');
    var sv = mcatSaved;
    if (sv) mcatGlide(function () { mcatPlace(sv.x, sv.y); });
    mcatMoveT = Date.now();
    mcatActT = 0; mcatActSt = '';
    mcatSet('st-read');
    if (!interrupted) mcatSayNow(UT('say.tired', 'اوف اوف… خسته شدم!'), 2600);
  }
  function mcatTick() {
    var now = Date.now();
    var inf = mcatInfo();
    if (mcatSayUntil && mcatSayUntil < now) { mcatSayEl.classList.remove('show'); mcatSayUntil = 0; }
    if (mcatZoneBack && now > mcatZoneBack) {
      mcatZoneBack = 0;
      if (mcatState === 'st-hang' || mcatState === 'st-edgesit' || mcatState === 'st-sidepeek') {
        MCAT.classList.remove('peek-r');
        if (mcatSaved) { var zb = mcatSaved; mcatGlide(function () { mcatPlace(zb.x, zb.y); }); }
        mcatSet('st-read');
        mcatSayNow(faR(MCAT_BACK2), 2400);
      }
    }
    if (mcatState === 'st-hide') {
      if (now > mcatHideTill) mcatRestore('دیدی دلم برات تنگ شد!');
      return;
    }
    if (MCAT.classList.contains('away')) {
      if (now > mcatAwayTill) mcatStartPeek();
      return;
    }
    if (mcatState === 'st-peek') {
      if (now > mcatPeekTill) mcatRestore(faR(MCAT_BACK));
      return;
    }
    if (inf.atEnd) { if (!mcatBotT) mcatBotT = now; } else mcatBotT = 0;
    if (mcatForceTill > now && mcatForceSt) { mcatSet(mcatForceSt); return; }
    if (mcatPatT > now) { mcatSet('st-pat'); return; }
    if (mcatShyT > now) { mcatSet('st-shy'); return; }
    if (mcatAnnoyT > now) { mcatSet('st-annoy'); return; }
    if (mcatAngryT > now) { mcatSet('st-angry'); return; }
    if (mcatRunning) { mcatSet('st-run'); return; }
    if (mcatActT > now && mcatActSt) { mcatSet(mcatActSt); return; }
    if (mcatZoneBack > now) return;
    if (inf.m > 320 && mcatMoveT < now - 8000 && mcatMoveT > now - 21000 && now > mcatActCd && mcatPatT < now && mcatShyT < now) {
      if (Math.random() < 0.09) {
        mcatActCd = now + 30000 + Math.random() * 15000;
        mcatGoHide();
        return;
      }
      var st = mcatNextAct || faR(ACT_POOL);
      mcatNextAct = '';
      mcatActCd = now + 26000 + Math.random() * 14000;
      mcatMoveT = now;
      if (st === 'st-run') { mcatStartRun(); return; }
      mcatActSt = st;
      mcatActT = now + ACT_DUR[st];
      mcatSayNow(faR(ACT_SAY[st]), ACT_DUR[st] - 300);
      mcatSet(st);
      if (st === 'st-hungry' && Math.random() < 0.55) mcatNextAct = 'st-eat';
      return;
    }
    if (inf.atEnd && now - mcatBotT > 2200) mcatSet('st-sad');
    else if (mcatFastT > now - 1200) mcatSet('st-exc');
    else if (mcatMoveT < now - 22000) mcatSet('st-sleep');
    else if (inf.m > 320 && inf.pct >= 0.9) mcatSet('st-stress');
    else mcatSet('st-read');
    if (mcatBub) mcatBub.classList.toggle('dim', now - mcatMoveT > 4000);
  }
  function mcatOnScroll() {
    var now = Date.now();
    var y = mcatInfo().y;
    if (mcatLastY < 0) mcatLastY = y;
    var dt = Math.max(40, now - mcatLastTs);
    if (Math.abs(y - mcatLastY) / dt > 0.85) mcatFastT = now;
    mcatLastY = y; mcatLastTs = now;
    mcatMoveT = now;
    if (mcatRunning) mcatEndRun(true);
    if (mcatState === 'st-hang' || mcatState === 'st-edgesit' || mcatState === 'st-sidepeek') {
      mcatZoneBack = 0;
      MCAT.classList.remove('peek-r');
      if (mcatSaved) { var zs2 = mcatSaved; mcatGlide(function () { mcatPlace(zs2.x, zs2.y); }); }
      mcatSet('st-read');
    }
    if (mcatActT) { mcatActT = 0; mcatActSt = ''; mcatNextAct = ''; }
    if (mcatForceTill) mcatForceTill = 0;
    if (mcatState === 'st-sleep') {
      if (Math.random() < 0.4) { mcatShyT = now + 2600; mcatSayNow(faR(MCAT_WAKE), 2800); }
      else mcatSet('st-read');
    }
    mcatUpdate();
    mcatTick();
  }
  var mcatDrag = null;
  MCAT.addEventListener('pointerdown', function (e) {
    mcatDrag = { x: e.clientX, y: e.clientY, moved: false };
    mcatMoveT = Date.now();
    if (mcatRunning) mcatEndRun(true);
    try { MCAT.setPointerCapture(e.pointerId); } catch (err) {}
    e.preventDefault();
  });
  MCAT.addEventListener('pointermove', function (e) {
    if (!mcatDrag) return;
    var dx = e.clientX - mcatDrag.x, dy = e.clientY - mcatDrag.y;
    if (!mcatDrag.moved && Math.sqrt(dx * dx + dy * dy) > 10) {
      mcatDrag.moved = true;
      if (!ZONES) mcatZonesBuild();
      ZONES.classList.add('show');
    }
    if (mcatDrag.moved) {
      mcatMoveT = Date.now();
      mcatPlace(e.clientX, e.clientY);
      mcatZonesMark(mcatZoneOf(e.clientX, e.clientY));
    }
  });
  function mcatUp(e) {
    if (!mcatDrag) return;
    var moved = mcatDrag.moved;
    mcatDrag = null;
    if (ZONES) { ZONES.classList.remove('show'); mcatZoneCur = ''; }
    if (moved) {
      var now = Date.now();
      var r = MCAT.getBoundingClientRect();
      var cx = r.left + r.width / 2, cy = r.top + r.height / 2;
      try { localStorage.setItem('mangaCatPos', JSON.stringify({ x: cx, y: cy })); } catch (err) {}
      var z = mcatZoneOf(e.clientX, e.clientY);
      if (z === 'center') {
        var el = null, oldPe = MCAT.style.pointerEvents;
        MCAT.style.pointerEvents = 'none';
        try { el = document.elementFromPoint(e.clientX, e.clientY); } catch (err2) {}
        MCAT.style.pointerEvents = oldPe;
        while (el && el !== document.body && el.tagName !== 'IMG') el = el.parentElement;
        mcatMoveT = now;
        if (el && el.tagName === 'IMG') {
          mcatFastT = now + 1400;
          mcatSayNow(faR(MCAT_PIC), 3400);
          mcatSet('st-exc');
        } else {
          mcatActSt = 'st-dance'; mcatActT = now + 3800;
          mcatSayNow(faR(MCAT_DROP), 3200);
          mcatSet('st-dance');
        }
        mcatTick(); setTimeout(mcatTick, 4000);
      } else {
        mcatZoneLand(z, cx, cy);
        mcatTick();
      }
      return;
    }
    var now = Date.now();
    if (mcatState === 'st-hide') {
      mcatRestore(Math.random() < 0.5 ? faR(MCAT_FOUND) : faR(MCAT_SHY));
      return;
    }
    if (mcatState === 'st-peek' || MCAT.classList.contains('away')) {
      mcatRestore(faR(MCAT_BACK));
      return;
    }
    if (mcatRunning) mcatEndRun(true);
    mcatTaps.push(now);
    while (mcatTaps.length && mcatTaps[0] < now - 6000) mcatTaps.shift();
    var fast = 0, i;
    for (i = 0; i < mcatTaps.length; i++) if (mcatTaps[i] > now - 2200) fast++;
    if (mcatAnnoyT > now || mcatAngryT > now) mcatTeaseN++;
    if (fast >= 5 || mcatTaps.length >= 5) mcatTeaseN++;
    if (mcatTeaseN >= 10) { mcatBlackout(); return; }
    if (fast >= 5) {
      mcatAngryT = now + 2100;
      mcatPatT = mcatAnnoyT = mcatActT = mcatShyT = 0; mcatActSt = '';
      mcatSayNow(faR(MCAT_ANGRY), 2400);
      if (now - mcatAngerLast > 90000) mcatAngerN = 0;
      mcatAngerN++; mcatAngerLast = now;
      if (mcatAngerN >= 2 && Math.random() < 0.45) {
        setTimeout(function () { mcatGoAway(); }, 2150);
        mcatAngerN = 0;
      }
      mcatTaps = [];
      mcatTick(); setTimeout(mcatTick, 2150);
      return;
    }
    if (mcatTaps.length >= 5) {
      mcatAnnoyT = now + 1900;
      mcatPatT = mcatActT = mcatShyT = 0; mcatActSt = '';
      mcatSayNow(faR(MCAT_ANNOY), 1900);
      setTimeout(function () { mcatGoHide(); }, 1950);
      mcatTaps = [];
      mcatTick(); setTimeout(mcatTick, 1980);
      return;
    }
    mcatPatT = now + 1700;
    mcatMoveT = now;
    if (mcatTaps.length === 4 && Math.random() < 0.4) {
      mcatPatT = now + 1500;
      mcatShyT = now + 3900;
      mcatSayNow(faR(MCAT_PAT), 1400);
      setTimeout(function () { mcatSayNow(faR(MCAT_SHY), 2300); }, 1550);
    } else {
      mcatSayNow(faR(MCAT_PAT), 2600);
    }
    mcatTick();
    setTimeout(mcatTick, 1800);
  }
  MCAT.addEventListener('pointerup', mcatUp);
  MCAT.addEventListener('pointercancel', function () { mcatDrag = null; if (ZONES) { ZONES.classList.remove('show'); mcatZoneCur = ''; } });
  if (mcatOffEl) mcatOffEl.addEventListener('pointerdown', function () { mcatWake(); });
  function mcatZoneOf(x, y) {
    var vw = window.innerWidth, vh = window.innerHeight;
    if (y < vh * 0.17) return 'top';
    if (y > vh * 0.83) return 'bottom';
    if (x < vw * 0.14) return 'left';
    if (x > vw * 0.86) return 'right';
    return 'center';
  }
  function mcatZonesBuild() {
    ZONES = document.createElement('div');
    ZONES.id = 'mcatzones';
    ZONES.innerHTML = '<div class="mz mz-top" data-z="top"></div><div class="mz mz-bottom" data-z="bottom"></div><div class="mz mz-left" data-z="left"></div><div class="mz mz-right" data-z="right"></div><div class="mz mz-center" data-z="center"></div>';
    document.body.appendChild(ZONES);
  }
  function mcatZonesMark(z) {
    if (!ZONES || z === mcatZoneCur) return;
    mcatZoneCur = z;
    var zs = ZONES.children, i;
    for (i = 0; i < zs.length; i++) zs[i].classList.toggle('on', zs[i].getAttribute('data-z') === z);
  }
  function mcatZoneLand(z, cx, cy) {
    var now = Date.now();
    mcatSaved = { x: cx, y: cy };
    mcatHideTill = mcatAwayTill = mcatPeekTill = 0;
    mcatActT = 0; mcatActSt = ''; mcatNextAct = '';
    MCAT.classList.remove('away', 'hide-l');
    if (z === 'top') {
      mcatGlide(function () {
        MCAT.style.left = (window.innerWidth / 2 - MCAT.offsetWidth / 2) + 'px';
        MCAT.style.top = '-46px';
        MCAT.style.right = 'auto';
      });
      mcatSet('st-hang');
      mcatSayNow(faR(MCAT_HANG), 4200);
    } else if (z === 'bottom') {
      mcatGlide(function () {
        MCAT.style.left = Math.max(8, Math.min(cx - MCAT.offsetWidth / 2, window.innerWidth - MCAT.offsetWidth - 8)) + 'px';
        MCAT.style.top = (window.innerHeight - 66) + 'px';
        MCAT.style.right = 'auto';
      });
      mcatSet('st-edgesit');
      mcatSayNow(faR(MCAT_SIT), 3800);
    } else {
      var rightSide = z === 'right';
      MCAT.classList.toggle('peek-r', rightSide);
      mcatGlide(function () {
        MCAT.style.left = (rightSide ? window.innerWidth - 40 : -48) + 'px';
        MCAT.style.top = Math.max(70, Math.min(cy - MCAT.offsetHeight / 2, window.innerHeight - 170)) + 'px';
        MCAT.style.right = 'auto';
      });
      mcatSet('st-sidepeek');
      mcatSayNow(faR(MCAT_SIDE), 3800);
    }
    mcatMoveT = now;
    mcatZoneBack = now + 7500;
  }
  var mcatFine = false;
  try {
    mcatFine = !!(window.matchMedia && window.matchMedia('(hover: hover) and (pointer: fine)').matches);
    if (!mcatFine && navigator.maxTouchPoints === 0 && !/Android|iPhone|iPad|Mobile/i.test(navigator.userAgent)) mcatFine = true;
  } catch (err) {}
  var mcatPupL = null, mcatPupR = null;
  function mcatEyes(e) {
    if (!mcatPupL) {
      var ps = MCAT.querySelectorAll('.cg-eyes-open .cg-pupil');
      if (ps.length < 2) return;
      mcatPupL = ps[0]; mcatPupR = ps[1];
    }
    var svg = MCAT.querySelector('svg');
    if (!svg) return;
    var r = svg.getBoundingClientRect();
    if (r.width < 4 || r.height < 4) return;
    var ex = r.left + r.width * 0.5, ey = r.top + r.height * 0.4;
    var dx = e.clientX - ex, dy = e.clientY - ey;
    var d = Math.sqrt(dx * dx + dy * dy) || 1;
    var k = Math.min(1, d / 260) * 2.4;
    var t = 'translate(' + ((dx / d) * k).toFixed(2) + 'px,' + ((dy / d) * k * 0.8).toFixed(2) + 'px)';
    mcatPupL.style.transform = t;
    mcatPupR.style.transform = t;
  }
  if (mcatFine) {
    window.addEventListener('mousemove', mcatEyes, { passive: true });
    document.addEventListener('mouseleave', function () {
      if (mcatPupL) { mcatPupL.style.transform = 'translate(0,0)'; mcatPupR.style.transform = 'translate(0,0)'; }
    });
  }
  window.__mcatForce = function (st) {
    mcatForceSt = ''; mcatForceTill = 0;
    mcatPatT = 0; mcatAnnoyT = 0; mcatAngryT = 0; mcatShyT = 0;
    mcatActT = 0; mcatActSt = ''; mcatNextAct = '';
    if (mcatRunning) mcatEndRun(true);
    if (st === 'st-hide') { mcatGoHide(); mcatHideTill = Date.now() + 60000; return; }
    if (st === 'st-blackout') { mcatBlackout(); return; }
    if (st === 'st-away') {
      mcatAwayTill = 0;
      if (mcatState !== 'st-peek' && !MCAT.classList.contains('away')) mcatGoAway();
      mcatAwayTill = Date.now() + 2600;
      setTimeout(function () { if (MCAT.classList.contains('away')) mcatStartPeek(); }, 2700);
      setTimeout(function () { if (mcatState === 'st-peek') mcatRestore('برگشتم!'); }, 5400);
      return;
    }
    if (st === 'st-run') { if (!mcatRunning) { mcatActCd = 0; mcatStartRun(); } return; }
    if (st === 'st-hang' || st === 'st-edgesit' || st === 'st-sidepeek') {
      var zr = MCAT.getBoundingClientRect();
      mcatZoneLand(st === 'st-hang' ? 'top' : st === 'st-edgesit' ? 'bottom' : (Math.random() < 0.5 ? 'left' : 'right'), zr.left + zr.width / 2, zr.top + zr.height / 2);
      mcatTick();
      return;
    }
    if (ACT_DUR[st]) {
      mcatActSt = st; mcatActT = Date.now() + ACT_DUR[st] + 400; mcatMoveT = Date.now();
      mcatSayNow(faR(ACT_SAY[st]), ACT_DUR[st]);
      if (st === 'st-hungry' && Math.random() < 0.55) mcatNextAct = 'st-eat';
      mcatSet(st);
      mcatTick();
      setTimeout(mcatTick, ACT_DUR[st] + 500);
      return;
    }
    if (st === 'st-pat') { mcatPatT = Date.now() + 2000; mcatMoveT = Date.now(); mcatSayNow(faR(MCAT_PAT), 2600); }
    else if (st === 'st-annoy') { mcatAnnoyT = Date.now() + 2600; mcatSayNow(faR(MCAT_ANNOY), 2600); }
    else if (st === 'st-angry') { mcatAngryT = Date.now() + 2600; mcatSayNow(faR(MCAT_ANGRY), 2400); }
    else if (st === 'st-shy') { mcatShyT = Date.now() + 3200; mcatSayNow(faR(MCAT_SHY), 3200); }
    else if (st === 'st-exc') { mcatFastT = Date.now(); mcatSayNow('ایول، این ورق رو دیدی؟!', 2600); }
    else if (st === 'st-sleep') { mcatMoveT = 0; }
    else if (st === 'st-read' || st === 'st-sad' || st === 'st-stress') {
      mcatForceSt = st; mcatForceTill = Date.now() + 6000;
      if (st === 'st-sad') mcatSayNow('تموم شد؟! ننووو', 3000);
      if (st === 'st-stress') mcatSayNow('وای، یه کم مونده…', 3000);
      if (st === 'st-read') mcatSayNow(faR(MCAT_READ), 3000);
    }
    mcatTick();
  };
  var iv = setInterval(function () {
    mcatTick();
    mcatUpdate();
    if (typeof stackCount === 'function' && typeof dbgMode !== 'undefined') {
      var mk = dbgMode ? 'd' : 'f';
      var n = stackCount();
      if (mcatLastN >= 0 && n > mcatLastN && mk === mcatLastMk) {
        if (mcatState === 'st-hide' || mcatState === 'st-peek' || MCAT.classList.contains('away')) mcatRestore('صفحهٔ تازه؟ اومدم اومدم!');
        else if (mcatPatT < Date.now()) { mcatFastT = Date.now() + 900; mcatSayNow(UT('say.fresh', 'یه صفحهٔ تازه رسید!'), 3200); mcatTick(); }
      }
      mcatLastN = n; mcatLastMk = mk;
    }
    var mp = mcatInfo().pct;
    var mstep = mp >= 0.75 ? 3 : mp >= 0.5 ? 2 : mp >= 0.25 ? 1 : 0;
    if (mstep > mcatMile) {
      mcatMile = mstep;
      if (mcatState !== 'st-hide' && mcatState !== 'st-peek' && !MCAT.classList.contains('away') && mcatPatT < Date.now()) {
        mcatFastT = Date.now() + 900;
        mcatSayNow(MCAT_MILE[mstep - 1], 3200);
        mcatTick();
      }
    }
    if (mcatState === 'st-read' && !mcatSayUntil && Math.random() < 0.02) mcatSayNow(faR(MCAT_READ), 5200);
  }, 900);
  var welcomeT = setTimeout(function () {
    if (mcatState === 'st-read') mcatSayNow('سلام! من نکو-گِرلم — بکشم ببر جاهای مختلف!', 3600);
  }, 900);
  try {
    var sp = JSON.parse(localStorage.getItem('mangaCatPos') || 'null');
    if (sp && typeof sp.x === 'number') mcatPlace(sp.x, sp.y);
    else mcatPlace(window.innerWidth - 60, 170);
  } catch (err) { mcatPlace(window.innerWidth - 60, 170); }
  if (mcatScrollEl) mcatScrollEl.addEventListener('scroll', mcatOnScroll, { passive: true });
  else window.addEventListener('scroll', mcatOnScroll, false);
  mcatUpdate();
  mcatTick();
  window.__mcatKill = function () {
    clearInterval(iv);
    clearTimeout(welcomeT);
    if (mcatRunT) clearTimeout(mcatRunT);
    window.removeEventListener('scroll', mcatOnScroll, false);
    window.removeEventListener('mousemove', mcatEyes, false);
    if (ZONES && ZONES.parentNode) ZONES.parentNode.removeChild(ZONES);
    ZONES = null; mcatZoneCur = '';
    if (mcatScrollEl) { try { mcatScrollEl.removeEventListener('scroll', mcatOnScroll); } catch (err) {} }
  };
    mcatUpdate();
    mcatTick();
  }
  updateProgress();
})();
"""

        _MCAT_HTML = (
            '<div class="mcat st-read" id="mcat" title="هم‌خوانِ نکو-گِرل — ۲۴ حالت! بکش و رها کن: بالا/پایین/بغل/وسط، ضربه = نوازش (زیادش نکن!)">\n'
            '<svg viewBox="0 0 120 140" aria-hidden="true">\n'
            '<defs>\n'
            '<linearGradient id="cgHair" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#cfe7fa"/><stop offset="1" stop-color="#a8cdec"/></linearGradient>\n'
            '<linearGradient id="cgDress" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f9c0cc"/><stop offset="1" stop-color="#f2a0b1"/></linearGradient>\n'
            '<linearGradient id="cgTail" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#cfe7fa"/><stop offset="1" stop-color="#9fc4ea"/></linearGradient>\n'
            '<radialGradient id="cgEye" cx=".5" cy=".42" r=".75"><stop offset="0" stop-color="#ffe9ae"/><stop offset=".55" stop-color="#f4b95c"/><stop offset="1" stop-color="#e89b3c"/></radialGradient>\n'
            '</defs>\n'
            '<ellipse cx="60" cy="134" rx="26" ry="3.4" fill="rgba(0,0,0,.13)"/>\n'
            '<g class="cg-all">\n'
            '<g class="cg-speed" stroke="#aebfd6" stroke-width="2.6" stroke-linecap="round"><line x1="2" y1="98" x2="14" y2="98"/><line x1="0" y1="110" x2="12" y2="110"/><line x1="3" y1="122" x2="14" y2="122"/></g>\n'
            '<g class="cg-tail"><path d="M78 112 Q112 108 106 82" fill="none" stroke="url(#cgTail)" stroke-width="11.5" stroke-linecap="round"/><path d="M78 112 Q112 108 106 82" fill="none" stroke="#bcd9f2" stroke-width="9.2" stroke-linecap="round"/><path d="M106 84 Q103 72 92 71" fill="none" stroke="#9fc4ea" stroke-width="9" stroke-linecap="round"/><path d="M106 84 Q103 72 92 71" fill="none" stroke="#bcd9f2" stroke-width="7" stroke-linecap="round"/><path d="M97.5 76.5 Q94.8 73.4 92.5 71.5" fill="none" stroke="#ffffff" stroke-width="6.4" stroke-linecap="round"/><path d="M99 101 q4.5 -1.5 6.5 -4.5" fill="none" stroke="#9fc4ea" stroke-width="1.5" stroke-linecap="round"/><path d="M100 93 q4 -.5 6 -3" fill="none" stroke="#9fc4ea" stroke-width="1.5" stroke-linecap="round"/></g>\n'
            '<path d="M44 100 Q60 95.5 76 100 L85.5 119.5 Q87.5 125 81.5 125.4 L38.5 125.4 Q32.5 125 34.5 119.5 Z" fill="url(#cgDress)"/>\n'
            '<path d="M35.5 120.5 Q60 124.5 84.5 120.5" fill="none" stroke="#e28b9d" stroke-width="1.8" stroke-linecap="round"/>\n'
            '<path d="M42 88 Q30 89 30 99 Q30 108 41 107 Q48.5 106 48 96.5 Q47.5 89.5 42 88 Z" fill="#f4a9b8" stroke="#d97a90" stroke-width=".9"/>\n'
            '<path d="M78 88 Q90 89 90 99 Q90 108 79 107 Q71.5 106 72 96.5 Q72.5 89.5 78 88 Z" fill="#f4a9b8" stroke="#d97a90" stroke-width=".9"/>\n'
            '<ellipse cx="47.5" cy="126" rx="6.6" ry="4.6" fill="#fff6ea" stroke="#e7cbb6" stroke-width="1.1"/>\n'
            '<ellipse cx="72.5" cy="126" rx="6.6" ry="4.6" fill="#fff6ea" stroke="#e7cbb6" stroke-width="1.1"/>\n'
            '<g fill="#f2a9b8"><circle cx="45.2" cy="124.4" r="1.5"/><circle cx="47.9" cy="123.9" r="1.5"/><circle cx="50.5" cy="124.8" r="1.4"/><circle cx="70.2" cy="124.4" r="1.5"/><circle cx="72.9" cy="123.9" r="1.5"/><circle cx="75.5" cy="124.8" r="1.4"/></g>\n'
            '<path d="M43.6 127 a4.9 4.9 0 0 0 8.4 0 z" fill="#d98a9c"/>\n'
            '<path d="M68.6 127 a4.9 4.9 0 0 0 8.4 0 z" fill="#d98a9c"/>\n'
            '<g class="cg-book"><g transform="translate(2,9) rotate(-2 60 103)"><rect x="32" y="89" width="56" height="29" rx="3" fill="#a83050"/><rect x="34.5" y="91.5" width="51" height="24" rx="2" fill="#fbf7ee"/><line x1="60" y1="93" x2="60" y2="114" stroke="#a83050" stroke-width="2.6"/><g stroke="#c5bba8" stroke-width="1.7" stroke-linecap="round"><line x1="39" y1="97.5" x2="56" y2="97.5"/><line x1="39" y1="102" x2="56" y2="102"/><line x1="39" y1="106.5" x2="52" y2="106.5"/><line x1="64" y1="97.5" x2="81" y2="97.5"/><line x1="64" y1="102" x2="81" y2="102"/><line x1="68" y1="106.5" x2="81" y2="106.5"/></g><path d="M75 115 l0 5 2.2 -1.8 2.2 1.8 0 -5 z" fill="#e8b84b"/></g></g>\n'
            '<g class="cg-hug"><path d="M43 88 Q35 93 35.5 102" fill="none" stroke="#d97a90" stroke-width="13.5" stroke-linecap="round"/><path d="M77 88 Q85 93 84.5 102" fill="none" stroke="#d97a90" stroke-width="13.5" stroke-linecap="round"/><path d="M43 88 Q35 93 35.5 102" fill="none" stroke="#f4a9b8" stroke-width="10.5" stroke-linecap="round"/><path d="M77 88 Q85 93 84.5 102" fill="none" stroke="#f4a9b8" stroke-width="10.5" stroke-linecap="round"/><g transform="translate(35.5,103)"><circle r="6" fill="#ffe9dc"/><path d="M-3.3 2.1 q3.3 2.3 6.6 0" fill="none" stroke="#e8b9a4" stroke-width="1.2" stroke-linecap="round"/><path d="M-2.5 -1.4 q1 -2 1.9 -2.2 M.5 -2 q1 -2 1.9 -2.2" stroke="#e8b9a4" stroke-width="1" fill="none" stroke-linecap="round"/></g><g transform="translate(84.5,103)"><circle r="6" fill="#ffe9dc"/><path d="M-3.3 2.1 q3.3 2.3 6.6 0" fill="none" stroke="#e8b9a4" stroke-width="1.2" stroke-linecap="round"/><path d="M-2.5 -1.4 q1 -2 1.9 -2.2 M.5 -2 q1 -2 1.9 -2.2" stroke="#e8b9a4" stroke-width="1" fill="none" stroke-linecap="round"/></g></g>\n'
            '<g class="cg-arms-up"><g class="arm-l"><path d="M38 94 Q24 90 15.5 68" fill="none" stroke="#d97a90" stroke-width="14.5" stroke-linecap="round"/><path d="M38 94 Q24 90 15.5 68" fill="none" stroke="#f4a9b8" stroke-width="11" stroke-linecap="round"/><g transform="translate(14.5,66)"><circle r="5.8" fill="#ffe9dc"/><path d="M-3.2 2.1 q3.2 2.3 6.4 0" fill="none" stroke="#e8b9a4" stroke-width="1.2" stroke-linecap="round"/><path d="M-2.4 -1.4 q1 -2 1.9 -2.2 M.4 -2 q1 -2 1.9 -2.2" stroke="#e8b9a4" stroke-width="1" fill="none" stroke-linecap="round"/></g></g><g class="arm-r"><path d="M82 94 Q96 90 104.5 68" fill="none" stroke="#d97a90" stroke-width="14.5" stroke-linecap="round"/><path d="M82 94 Q96 90 104.5 68" fill="none" stroke="#f4a9b8" stroke-width="11" stroke-linecap="round"/><g transform="translate(105.5,66)"><circle r="5.8" fill="#ffe9dc"/><path d="M-3.2 2.1 q3.2 2.3 6.4 0" fill="none" stroke="#e8b9a4" stroke-width="1.2" stroke-linecap="round"/><path d="M-2.4 -1.4 q1 -2 1.9 -2.2 M.4 -2 q1 -2 1.9 -2.2" stroke="#e8b9a4" stroke-width="1" fill="none" stroke-linecap="round"/></g></g></g>\n'
            '<g class="cg-arms-stretch"><path d="M38 94 Q24 97 13.5 86" fill="none" stroke="#d97a90" stroke-width="14.5" stroke-linecap="round"/><path d="M38 94 Q24 97 13.5 86" fill="none" stroke="#f4a9b8" stroke-width="11" stroke-linecap="round"/><g transform="translate(12,85)"><circle r="5.6" fill="#ffe9dc"/><path d="M-3.1 2 q3.1 2.2 6.2 0" fill="none" stroke="#e8b9a4" stroke-width="1.2" stroke-linecap="round"/></g><path d="M82 94 Q96 97 106.5 86" fill="none" stroke="#d97a90" stroke-width="14.5" stroke-linecap="round"/><path d="M82 94 Q96 97 106.5 86" fill="none" stroke="#f4a9b8" stroke-width="11" stroke-linecap="round"/><g transform="translate(108,85)"><circle r="5.6" fill="#ffe9dc"/><path d="M-3.1 2 q3.1 2.2 6.2 0" fill="none" stroke="#e8b9a4" stroke-width="1.2" stroke-linecap="round"/></g></g>\n'
            '<g class="cg-head">\n'
            '<path d="M60 13 C86 13 103 27 104 50 C105 68 97 82 82 90 C74 94 66 95 60 95 C54 95 46 94 38 90 C23 82 15 68 16 50 C17 27 34 13 60 13 Z" fill="url(#cgHair)"/>\n'
            '<g class="cg-ear cg-ear-l"><path d="M24 30 Q15 13 12.5 2.5 Q30 7 52 20 Q49 28 39 30.6 Q31 32 24 30 Z" fill="#c3ddf5" stroke="#9fc4ea" stroke-width="1.4"/><path d="M27.5 24.5 Q21.5 12.5 20.5 6.5 Q33 10.5 46 19.5 Q42.5 26.5 35 27 Q30.8 27.3 27.5 24.5 Z" fill="#f7c6d1"/><path d="M25.5 29 q-3 -10 2 -16.5 q6 7 5 17.5 q-3.5 1.6 -7 -.9 z" fill="#ffffff"/></g>\n'
            '<g class="cg-ear cg-ear-r"><path d="M96 30 Q105 13 107.5 2.5 Q90 7 68 20 Q71 28 81 30.6 Q89 32 96 30 Z" fill="#c3ddf5" stroke="#9fc4ea" stroke-width="1.4"/><path d="M92.5 24.5 Q98.5 12.5 99.5 6.5 Q87 10.5 74 19.5 Q77.5 26.5 85 27 Q89.2 27.3 92.5 24.5 Z" fill="#f7c6d1"/><path d="M94.5 29 q3 -10 -2 -16.5 q-6 7 -5 17.5 q3.5 1.6 7 -.9 z" fill="#ffffff"/></g>\n'
            '<path d="M46 79 Q60 88 74 79 L79.5 91 Q60 100.5 40.5 91 Z" fill="#fffdf6" stroke="#e8d9c8" stroke-width="1" stroke-linejoin="round"/>\n'
            '<path d="M45.5 85.5 Q60 94.5 74.5 85.5" fill="none" stroke="#e28b9d" stroke-width="1.6" stroke-linecap="round"/>\n'
            '<path d="M60 92.5 L53.6 89.4 Q51.6 93.4 54 96.6 Z" fill="#ff8fa8" stroke="#e8738e" stroke-width=".6" stroke-linejoin="round"/>\n'
            '<path d="M60 92.5 L66.4 89.4 Q68.4 93.4 66 96.6 Z" fill="#ff8fa8" stroke="#e8738e" stroke-width=".6" stroke-linejoin="round"/>\n'
            '<circle cx="60" cy="92.8" r="2" fill="#e8738e"/>\n'
            '<circle cx="60" cy="98.8" r="3.5" fill="#f6c957" stroke="#c9992e" stroke-width="1.1"/>\n'
            '<path d="M56.8 99.5 Q60 101.5 63.2 99.5" fill="none" stroke="#c9992e" stroke-width="1" stroke-linecap="round"/>\n'
            '<line x1="58.7" y1="99.1" x2="61.3" y2="99.1" stroke="#c9992e" stroke-width="1"/>\n'
            '<circle cx="60" cy="97.4" r="1" fill="#fff" opacity=".9"/>\n'
            '<path d="M60 26 C78 26 90 35 91 52 C92 66 84 78 71 82 C67 83.5 63 84 60 84 C57 84 53 83.5 49 82 C36 78 28 66 29 52 C30 35 42 26 60 26 Z" fill="#ffe9dc"/>\n'
            '<path d="M28 20 Q19 38 19.5 56 Q20 72 26 85 Q30 92 34.5 88 Q31 80 30 66 Q29 48 34 31 Q37 23 35 18.5 Q29.5 16.5 28 20 Z" fill="#bcd9f2"/>\n'
            '<path d="M92 20 Q101 38 100.5 56 Q100 72 94 85 Q90 92 85.5 88 Q89 80 90 66 Q91 48 86 31 Q83 23 85 18.5 Q90.5 16.5 92 20 Z" fill="#bcd9f2"/>\n'
            '<path d="M22.5 41 Q24 17.5 60 15 Q96 17.5 97.5 41 Q94 45.5 90.5 41.5 Q87 47 82.5 42.5 Q78.5 48 73.5 43 Q69.5 48.5 64.5 43.5 Q61.5 48 56.5 43.5 Q51.5 48.5 47.5 43 Q42.5 48 38.5 42.5 Q34 47 30.5 41.5 Q27 45.5 22.5 41 Z" fill="#bcd9f2"/>\n'
            '<path d="M50 18 Q52 27 50.5 35" fill="none" stroke="#a9cdf0" stroke-width="1.4" stroke-linecap="round"/>\n'
            '<path d="M70 18 Q68 27 69.5 35" fill="none" stroke="#a9cdf0" stroke-width="1.4" stroke-linecap="round"/>\n'
            '<path d="M51 44 Q54.5 51 52.5 58 Q49.5 51 48.5 45 Z" fill="#bcd9f2"/>\n'
            '<path d="M69 44 Q65.5 51 67.5 58 Q70.5 51 71.5 45 Z" fill="#bcd9f2"/>\n'
            '<path class="cg-ahoge" d="M58 14 Q54.5 8 59 4.5 Q63.5 1.5 64.5 5.5 Q65.2 8.3 62 8.8 Q60.2 9 60.6 7" fill="none" stroke="#bcd9f2" stroke-width="2.6" stroke-linecap="round"/>\n'
            '<path d="M68 26 l-7.5 -3.6 1 7.2 z M68 26 l7.5 -3.6 -1 7.2 z" fill="#ff9eb5"/>\n'
            '<circle cx="68" cy="26.2" r="2.3" fill="#fff"/>\n'
            '<path d="M46 23 q6 -3.5 12 -3.5" fill="none" stroke="#e4f1fb" stroke-width="2.4" stroke-linecap="round"/>\n'
            '<path d="M64 19.5 q6.5 .5 11.5 3.5" fill="none" stroke="#e4f1fb" stroke-width="2.4" stroke-linecap="round"/>\n'
            '<g class="cg-eyes cg-eyes-open"><path d="M38.6 50.5 Q45 45.8 51.4 50.5" fill="none" stroke="#4a323e" stroke-width="2.6" stroke-linecap="round"/><path d="M68.6 50.5 Q75 45.8 81.4 50.5" fill="none" stroke="#4a323e" stroke-width="2.6" stroke-linecap="round"/><g class="cg-pupil"><ellipse cx="45" cy="56" rx="6.4" ry="7.8" fill="url(#cgEye)"/><ellipse cx="45" cy="58.4" rx="4.8" ry="4.4" fill="#f8cf7a"/><ellipse cx="45" cy="56" rx="2.8" ry="4.3" fill="#45301f"/><circle cx="42.9" cy="52.9" r="2.1" fill="#fff"/><circle cx="47.5" cy="59.7" r="1" fill="#fff"/><circle cx="47.9" cy="57.9" r=".6" fill="#fff" opacity=".9"/></g><g class="cg-pupil"><ellipse cx="75" cy="56" rx="6.4" ry="7.8" fill="url(#cgEye)"/><ellipse cx="75" cy="58.4" rx="4.8" ry="4.4" fill="#f8cf7a"/><ellipse cx="75" cy="56" rx="2.8" ry="4.3" fill="#45301f"/><circle cx="72.9" cy="52.9" r="2.1" fill="#fff"/><circle cx="77.5" cy="59.7" r="1" fill="#fff"/><circle cx="77.9" cy="57.9" r=".6" fill="#fff" opacity=".9"/></g><path d="M38.2 52.2 L35.2 51 M38.5 55 L35.3 54.6 M81.8 52.2 L84.8 51 M81.5 55 L84.7 54.6" stroke="#4a323e" stroke-width="1.8" stroke-linecap="round"/></g>\n'
            '<g class="cg-eyes cg-eyes-happy" fill="none" stroke="#4a323e" stroke-width="2.5" stroke-linecap="round"><path d="M38.5 55.5 Q45 47 51.5 55.5"/><path d="M68.5 55.5 Q75 47 81.5 55.5"/></g>\n'
            '<g class="cg-eyes cg-eyes-sleep" fill="none" stroke="#4a323e" stroke-width="2.2" stroke-linecap="round"><path d="M38.5 53 Q45 58 51.5 53"/><path d="M68.5 53 Q75 58 81.5 53"/></g>\n'
            '<g class="cg-eyes cg-eyes-worry"><path d="M40 45 Q45 43.2 50 45.2" fill="none" stroke="#93b8de" stroke-width="1.8" stroke-linecap="round"/><path d="M80 45 Q75 43.2 70 45.2" fill="none" stroke="#93b8de" stroke-width="1.8" stroke-linecap="round"/><ellipse cx="45" cy="56" rx="5.8" ry="7.2" fill="url(#cgEye)"/><ellipse cx="44" cy="57" rx="2.6" ry="3.8" fill="#563a22"/><circle cx="43.4" cy="53.2" r="1.7" fill="#fff"/><ellipse cx="75" cy="56" rx="5.8" ry="7.2" fill="url(#cgEye)"/><ellipse cx="74" cy="57" rx="2.6" ry="3.8" fill="#563a22"/><circle cx="73.4" cy="53.2" r="1.7" fill="#fff"/></g>\n'
            '<g class="cg-eyes cg-eyes-sad"><path d="M40 45.5 Q44 43 49 43.6" fill="none" stroke="#93b8de" stroke-width="1.8" stroke-linecap="round"/><path d="M80 45.5 Q76 43 71 43.6" fill="none" stroke="#93b8de" stroke-width="1.8" stroke-linecap="round"/><ellipse cx="45" cy="56" rx="6.2" ry="7.8" fill="url(#cgEye)"/><ellipse cx="45" cy="56" rx="2.8" ry="4.3" fill="#563a22"/><circle cx="42.9" cy="53" r="2" fill="#fff"/><circle cx="47.3" cy="60.5" r="1.3" fill="#fff"/><ellipse cx="75" cy="56" rx="6.2" ry="7.8" fill="url(#cgEye)"/><ellipse cx="75" cy="56" rx="2.8" ry="4.3" fill="#563a22"/><circle cx="72.9" cy="53" r="2" fill="#fff"/><circle cx="77.3" cy="60.5" r="1.3" fill="#fff"/></g>\n'
            '<g class="cg-eyes cg-eyes-annoy"><ellipse cx="45" cy="56.5" rx="5.4" ry="5" fill="url(#cgEye)"/><ellipse cx="47.8" cy="56.5" rx="2.3" ry="3.2" fill="#563a22"/><path d="M39.5 51 Q45 48 50.5 51 L50.5 46.5 Q45 43.5 39.5 46.5 Z" fill="#ffe9dc"/><path d="M39 51 Q45 49 51 51" fill="none" stroke="#4a323e" stroke-width="2.2" stroke-linecap="round"/><ellipse cx="75" cy="56.5" rx="5.4" ry="5" fill="url(#cgEye)"/><ellipse cx="77.8" cy="56.5" rx="2.3" ry="3.2" fill="#563a22"/><path d="M69.5 51 Q75 48 80.5 51 L80.5 46.5 Q75 43.5 69.5 46.5 Z" fill="#ffe9dc"/><path d="M69 51 Q75 49 81 51" fill="none" stroke="#4a323e" stroke-width="2.2" stroke-linecap="round"/><circle cx="37.5" cy="62.5" r="4.4" fill="#ffb3ba" opacity=".95"/><circle cx="82.5" cy="62.5" r="4.4" fill="#ffb3ba" opacity=".95"/></g>\n'
            '<g class="cg-eyes cg-eyes-angry"><path d="M38.5 43 L51.5 47.5" stroke="#4a323e" stroke-width="2.5" stroke-linecap="round"/><path d="M81.5 43 L68.5 47.5" stroke="#4a323e" stroke-width="2.5" stroke-linecap="round"/><ellipse cx="45" cy="56.5" rx="5.8" ry="6.6" fill="url(#cgEye)"/><ellipse cx="45" cy="57" rx="2.6" ry="3.7" fill="#563a22"/><path d="M38.8 48.5 L52 51.8" stroke="#4a323e" stroke-width="2.3" stroke-linecap="round"/><ellipse cx="75" cy="56.5" rx="5.8" ry="6.6" fill="url(#cgEye)"/><ellipse cx="75" cy="57" rx="2.6" ry="3.7" fill="#563a22"/><path d="M81.2 48.5 L68 51.8" stroke="#4a323e" stroke-width="2.3" stroke-linecap="round"/></g>\n'
            '<g class="cg-eyes cg-eyes-up"><path d="M38.6 50.5 Q45 45.8 51.4 50.5" fill="none" stroke="#4a323e" stroke-width="2.6" stroke-linecap="round"/><path d="M68.6 50.5 Q75 45.8 81.4 50.5" fill="none" stroke="#4a323e" stroke-width="2.6" stroke-linecap="round"/><ellipse cx="45" cy="56" rx="6.4" ry="7.8" fill="url(#cgEye)"/><ellipse cx="45" cy="52.5" rx="2.8" ry="4.3" fill="#45301f"/><circle cx="47.8" cy="50.4" r="2.1" fill="#fff"/><ellipse cx="75" cy="56" rx="6.4" ry="7.8" fill="url(#cgEye)"/><ellipse cx="75" cy="52.5" rx="2.8" ry="4.3" fill="#45301f"/><circle cx="77.8" cy="50.4" r="2.1" fill="#fff"/></g>\n'
            '<g class="cg-eyes cg-eyes-down"><path d="M38.6 52.6 Q45 49.6 51.4 52.6" fill="none" stroke="#4a323e" stroke-width="2.6" stroke-linecap="round"/><path d="M68.6 52.6 Q75 49.6 81.4 52.6" fill="none" stroke="#4a323e" stroke-width="2.6" stroke-linecap="round"/><ellipse cx="45" cy="58.6" rx="5.9" ry="5" fill="url(#cgEye)"/><ellipse cx="45" cy="60" rx="2.6" ry="3.1" fill="#563a22"/><circle cx="43.3" cy="57.4" r="1.5" fill="#fff"/><ellipse cx="75" cy="58.6" rx="5.9" ry="5" fill="url(#cgEye)"/><ellipse cx="75" cy="60" rx="2.6" ry="3.1" fill="#563a22"/><circle cx="73.3" cy="57.4" r="1.5" fill="#fff"/></g>\n'
            '<g class="cg-eyes cg-eyes-shifty"><path d="M38.6 50.5 Q45 45.8 51.4 50.5" fill="none" stroke="#4a323e" stroke-width="2.6" stroke-linecap="round"/><path d="M68.6 50.5 Q75 45.8 81.4 50.5" fill="none" stroke="#4a323e" stroke-width="2.6" stroke-linecap="round"/><g class="cg-pupil"><ellipse cx="45" cy="56" rx="6.4" ry="7.8" fill="url(#cgEye)"/><ellipse cx="45" cy="56" rx="2.8" ry="4.3" fill="#45301f"/><circle cx="42.9" cy="52.9" r="2.1" fill="#fff"/></g><g class="cg-pupil"><ellipse cx="75" cy="56" rx="6.4" ry="7.8" fill="url(#cgEye)"/><ellipse cx="75" cy="56" rx="2.8" ry="4.3" fill="#45301f"/><circle cx="72.9" cy="52.9" r="2.1" fill="#fff"/></g></g>\n'
            '<g class="cg-eyes cg-eyes-think"><path d="M38.6 50.5 Q45 45.8 51.4 50.5" fill="none" stroke="#4a323e" stroke-width="2.6" stroke-linecap="round"/><path d="M68.6 50.5 Q75 45.8 81.4 50.5" fill="none" stroke="#4a323e" stroke-width="2.6" stroke-linecap="round"/><g class="cg-pupil" transform="translate(1.6,-2.2)"><ellipse cx="45" cy="56" rx="6.2" ry="7.5" fill="url(#cgEye)"/><ellipse cx="45" cy="56" rx="2.7" ry="4.1" fill="#45301f"/><circle cx="42.9" cy="52.9" r="1.9" fill="#fff"/></g><g class="cg-pupil" transform="translate(1.6,-2.2)"><ellipse cx="75" cy="56" rx="6.2" ry="7.5" fill="url(#cgEye)"/><ellipse cx="75" cy="56" rx="2.7" ry="4.1" fill="#45301f"/><circle cx="72.9" cy="52.9" r="1.9" fill="#fff"/></g></g>\n'
            '<ellipse class="cg-blush" cx="37" cy="68" rx="6.2" ry="3.3" fill="#ffc2cd" opacity=".8"/>\n'
            '<ellipse class="cg-blush" cx="83" cy="68" rx="6.2" ry="3.3" fill="#ffc2cd" opacity=".8"/>\n'
            '<path d="M59 60.4 q1.4 1.1 2.8 0" fill="none" stroke="#eda39b" stroke-width="1.3" stroke-linecap="round"/>\n'
            '<path class="cg-mv cg-mv-smile" d="M54 64.8 Q57.2 69 60 65.3 Q62.8 69 66 64.8" fill="none" stroke="#c26375" stroke-width="2.2" stroke-linecap="round"/>\n'
            '<path class="cg-mv cg-mv-smile" d="M62.9 67.4 L63.9 69.6 L64.9 67.5 Z" fill="#ffffff" stroke="#e8cfcf" stroke-width=".5" stroke-linejoin="round"/>\n'
            '<path class="cg-mv cg-mv-pout" d="M56 67.5 Q60 65.2 64 67.5" fill="none" stroke="#c26375" stroke-width="2.1" stroke-linecap="round"/>\n'
            '<ellipse class="cg-mv cg-mv-shout" cx="60" cy="67" rx="4.2" ry="3.6" fill="#9e4a5e"/>\n'
            '<path class="cg-mv cg-mv-shout" d="M57.6 68.6 q2.4 2.4 4.8 0 z" fill="#e58ea0"/>\n'
            '<ellipse class="cg-mv cg-mv-o" cx="60" cy="66.5" rx="2.7" ry="3.5" fill="#9e4a5e"/>\n'
            '<ellipse class="cg-mv cg-mv-song" cx="60" cy="66.5" rx="2.4" ry="2.9" fill="#9e4a5e"/>\n'
            '<g class="cg-mv cg-mv-yawn"><ellipse cx="60" cy="67.5" rx="5.6" ry="6.6" fill="#8a4050"/><ellipse cx="60" cy="69.8" rx="3.3" ry="3" fill="#e58ea0"/></g>\n'
            '<path class="cg-mv cg-mv-munch" d="M55.5 66.5 q2.2 -2.5 4.5 0 q2.2 2.5 4.5 0" fill="none" stroke="#c26375" stroke-width="2.2" stroke-linecap="round"/>\n'
            '<path class="cg-mv cg-mv-tee" d="M55.5 66.8 q2.2 2.6 4.5 0 q2.2 -2.6 4.5 0" fill="none" stroke="#c26375" stroke-width="2.1" stroke-linecap="round"/>\n'
            '<path class="cg-mv cg-mv-focus" d="M56.5 66.6 h7" fill="none" stroke="#c26375" stroke-width="2.3" stroke-linecap="round"/>\n'
            '<g class="cg-glass" fill="none" stroke="#7a6a75" stroke-width="2"><circle cx="45" cy="56" r="9.6"/><circle cx="75" cy="56" r="9.6"/><path d="M54.6 55.5 h10.8"/><path d="M35.4 54.5 L28.5 50.5"/><path d="M84.6 54.5 L91.5 50.5"/><path d="M40 50 q5 -3.6 10 -1.2" stroke="#ffffff" stroke-width="2.6" opacity=".9"/><path d="M70 50 q5 -3.6 10 -1.2" stroke="#ffffff" stroke-width="2.6" opacity=".9"/></g>\n'
            '<g class="cg-shyhands"><circle cx="36" cy="68" r="6.6" fill="#ffe9dc"/><circle cx="84" cy="68" r="6.6" fill="#ffe9dc"/><path d="M33 71.3 q3 2.2 6 .6" fill="none" stroke="#e8b9a4" stroke-width="1.2" stroke-linecap="round"/><path d="M81 71.3 q3 2.2 6 .6" fill="none" stroke="#e8b9a4" stroke-width="1.2" stroke-linecap="round"/></g>\n'
            '<g class="cg-shyblush"><ellipse cx="34" cy="66" rx="7" ry="3.8" fill="#ffb0bc" opacity=".92"/><ellipse cx="86" cy="66" rx="7" ry="3.8" fill="#ffb0bc" opacity=".92"/><circle cx="25" cy="40" r="3" fill="#ffc9d4" opacity=".85"/><circle cx="95" cy="38" r="3.4" fill="#ffc9d4" opacity=".85"/></g>\n'
            '<g class="cg-hand-chin"><path d="M73 98 Q71 88 70.5 81" fill="none" stroke="#f4a9b8" stroke-width="10.5" stroke-linecap="round"/><circle cx="70.5" cy="80.5" r="6.2" fill="#ffe9dc"/><path d="M67.5 79.5 q3 -1.5 6 0" fill="none" stroke="#e8b9a4" stroke-width="1.2" stroke-linecap="round"/></g>\n'
            '<g class="cg-sweat"><path d="M112 29 q5.5 7.5 0 11.5 q-5.5 -4 0 -11.5" fill="#7ec8f2"/></g>\n'
            '<g class="cg-tears"><ellipse cx="41" cy="63.5" rx="2.6" ry="4.4" fill="#7ec8f2"/><ellipse cx="79" cy="63.5" rx="2.6" ry="4.4" fill="#7ec8f2"/></g>\n'
            '<g class="cg-spark" fill="#ffd86b"><path d="M24 42 l1.5 3.7 3.7 1.5 -3.7 1.5 -1.5 3.7 -1.5 -3.7 -3.7 -1.5 3.7 -1.5 Z"/><path d="M94 34 l1.2 3 3 1.2 -3 1.2 -1.2 3 -1.2 -3 -3 -1.2 3 -1.2 Z"/></g>\n'
            '<g class="cg-anger" stroke="#ff3d2e" stroke-width="3.2" stroke-linecap="round" fill="none"><path d="M109 4 L114 9"/><path d="M118 4 L113 9"/><path d="M109 20 L114 15"/><path d="M118 20 L113 15"/></g>\n'
            '<g class="cg-steam" fill="#dfe4ec"><circle cx="109" cy="34" r="4.6"/><circle cx="116" cy="45" r="3.2"/></g>\n'
            '</g>\n'
            '<g class="cg-snack"><g transform="translate(-5,0)"><path d="M84 101 Q80 93 76 88" fill="none" stroke="#d97a90" stroke-width="13" stroke-linecap="round"/><path d="M84 101 Q80 93 76 88" fill="none" stroke="#f4a9b8" stroke-width="10" stroke-linecap="round"/><g transform="translate(75.5,86)"><circle r="6.2" fill="#ffe9dc"/><path d="M-3.4 2.2 q3.4 2.3 6.8 0" fill="none" stroke="#e8b9a4" stroke-width="1.2" stroke-linecap="round"/><path d="M-2.6 -1.5 q1 -2 1.9 -2.2 M.4 -2.1 q1 -2 1.9 -2.2" stroke="#e8b9a4" stroke-width="1" fill="none" stroke-linecap="round"/></g><g transform="translate(66.5,75.5) scale(1.32) translate(-66.5,-75.5)"><g class="fish"><path d="M58 77 Q64 68 74 69.5 Q81 71 82.5 75.5 Q81 80 74 81.5 Q64 83 58 77 Z" fill="#eab26b" stroke="#c9944e" stroke-width="1.5"/><path d="M58 77 L50.5 72.5 L52 82 Z" fill="#eab26b" stroke="#c9944e" stroke-width="1.3" stroke-linejoin="round"/><circle cx="77.6" cy="73.3" r="1.5" fill="#6d4a26"/><path d="M67.5 71.5 q2 2 .4 4 M71 71 q2 2 .4 4 M74.5 71.5 q2 2 .4 4" fill="none" stroke="#c9944e" stroke-width="1.1" stroke-linecap="round"/><path d="M65.5 79.5 q4.5 2.5 8.5 .5" fill="none" stroke="#c9944e" stroke-width="1" stroke-linecap="round"/><path d="M79.5 70 a3.4 3.4 0 0 0 -2.6 4.8" fill="none" stroke="#fff6e8" stroke-width="2.4" stroke-linecap="round"/></g></g></g></g>\n'
            '<g class="cg-crumbs" fill="#b58a45"><circle cx="54" cy="84" r="1.8"/><circle cx="49.5" cy="89" r="1.5"/><circle cx="58" cy="90" r="1.6"/></g>\n'
            '<g class="cg-music"><g class="n1"><ellipse cx="106" cy="28" rx="3.2" ry="2.4" transform="rotate(-20 106 28)" fill="#ff9ec4"/><path d="M109.1 27 L109.1 15 q4.2 1.4 4.2 5.6" fill="none" stroke="#ff9ec4" stroke-width="1.8" stroke-linecap="round"/></g><g class="n2"><ellipse cx="113.5" cy="41" rx="2.8" ry="2.1" transform="rotate(-20 113.5 41)" fill="#ff9ec4"/><path d="M115.8 40.3 L115.8 30 q3.7 1.2 3.7 4.9" fill="none" stroke="#ff9ec4" stroke-width="1.6" stroke-linecap="round"/></g></g>\n'
            '<g class="cg-ball"><circle cx="92" cy="100" r="7.5" fill="#fdfdfd" stroke="#d95970" stroke-width="2.2"/><path d="M84.5 100 a7.5 7.5 0 0 1 15 0 Z" fill="#d95970"/></g>\n'
            '<path class="cg-heart" d="M97 22s-8-4.5-8-11a4 4 0 018-1 4 4 0 018 1c0 6.5-8 11-8 11z" fill="#ff5d78"/>\n'
            '</g>\n'
            '<g class="cg-zzz" fill="#cfd2da" font-family="system-ui,sans-serif" font-weight="700"><text x="103" y="40" font-size="8">z</text><text x="111" y="30" font-size="11">Z</text></g>\n'
            '<g class="cg-think" fill="#a9c0dd"><circle cx="104" cy="32" r="2"/><circle cx="110" cy="25" r="2.6"/><circle cx="116" cy="17" r="3.2"/></g>\n'
            '<g class="cg-rumble" stroke="#e2a2b2" fill="none" stroke-width="2.4" stroke-linecap="round"><path class="r1" d="M42 111 q-8 3 -9 12"/><path class="r2" d="M78 111 q8 3 9 12"/><path class="r3" d="M60 119 q0 6 0 9"/><text class="rt" x="60" y="132" text-anchor="middle" font-size="7" font-weight="800" fill="#e2a2b2" stroke="none" font-family="system-ui,sans-serif">قار قور!</text></g>\n'
            '<g class="cg-wall">\n'
            '<rect x="71" y="-2" width="49" height="144" fill="#b7aa92"/>\n'
            '<rect x="71" y="-2" width="49" height="7" rx="3.5" fill="#998b70"/>\n'
            '<rect x="71" y="-2" width="2.4" height="144" fill="#d0c2a6"/>\n'
            '<rect x="73.4" y="-2" width="1.4" height="144" fill="rgba(0,0,0,.22)"/>\n'
            '<path d="M66 96 Q80 90 86 103 Q75 110 66 96 Z" fill="#bcd9f2" stroke="#9fc4ea" stroke-width="2"/>\n'
            '<circle cx="82.5" cy="103" r="3.4" fill="#9fc4ea"/>\n'
            '<g><path d="M65 55 q6.5 -6 14 -1.5 q1.5 6 -4.5 7.5 q-8 1.5 -9.5 -6 Z" fill="#f4a9b8"/><circle cx="78" cy="64" r="6.5" fill="#ffe9dc" stroke="#e8b9a4" stroke-width="1.3"/><path d="M74.9 69 l-.5 2.8 M78 69.4 l.2 2.8" stroke="#e8b9a4" stroke-width="1.6" stroke-linecap="round"/></g>\n'
            '<g><path d="M66 71 q6.5 -6 14 -1.5 q1.5 6 -4.5 7.5 q-8 1.5 -9.5 -6 Z" fill="#f4a9b8"/><circle cx="79" cy="80" r="6.5" fill="#ffe9dc" stroke="#e8b9a4" stroke-width="1.3"/><path d="M75.9 85 l-.5 2.8 M79 85.4 l.2 2.8" stroke="#e8b9a4" stroke-width="1.6" stroke-linecap="round"/></g>\n'
            '</g>\n'
            '</svg>\n'
            '<div class="mcat-say"></div>\n'
            '</div>\n'
            '<div id="mcatOff" aria-hidden="true">\n'
            '<svg class="off-eyes" viewBox="0 0 150 58" aria-hidden="true"><defs><radialGradient id="mcOffG"><stop offset="0" stop-color="#ffd964" stop-opacity=".55"/><stop offset=".55" stop-color="#ffd964" stop-opacity=".2"/><stop offset="1" stop-color="#ffd964" stop-opacity="0"/></radialGradient></defs><path d="M28 24 L33 8 L44 19 Z" fill="#ffd964" opacity=".38"/><path d="M122 24 L117 8 L106 19 Z" fill="#ffd964" opacity=".38"/><g><ellipse cx="40" cy="36" rx="34" ry="19" fill="url(#mcOffG)"/><path d="M16 36 Q40 18 64 36 Q40 52 16 36 Z" fill="#ffd964"/><circle cx="32" cy="33" r="3.2" fill="#fff" opacity=".95"/><circle cx="48" cy="39" r="2.1" fill="#fff" opacity=".75"/></g><g><ellipse cx="110" cy="36" rx="34" ry="19" fill="url(#mcOffG)"/><path d="M86 36 Q110 18 134 36 Q110 52 86 36 Z" fill="#ffd964"/><circle cx="102" cy="33" r="3.2" fill="#fff" opacity=".95"/><circle cx="118" cy="39" r="2.1" fill="#fff" opacity=".75"/></g></svg>\n'
            '<div class="off-t1">دخترِ گربه‌ای خسته شد!</div>\n'
            '<div class="off-t2">صفحه رو خاموش کرد… دیگه اذیت نکن!</div>\n'
            '<div class="off-t3">برای روشن‌کردن، صفحه را لمس کن</div>\n'
            '</div>\n'
        )
        page = (
            "<!DOCTYPE html>\n"
            '<html lang="fa" dir="rtl">\n'
            "<head>\n"
            '<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=5,user-scalable=yes">\n'
            '<meta name="apple-mobile-web-app-capable" content="yes">\n'
            f"<title>{title_esc}</title>\n"
            f"<style>{css}</style>\n"
            + _ui_t_head() +
            "</head>\n"
            "<body>\n"
            '<div class="rdr" id="manga_rdr" data-zoom="1">\n'
            '  <div class="rdrS">\n'
            '    <div class="rdr-bar">\n'
            '      <button type="button" class="rdr-btn" data-act="close" title="بستن">✕</button>\n'
            f'      <div class="rdr-title">{title_esc}</div>\n'
            '      <button type="button" class="rdr-btn" data-act="zoom-out" title="دور">−</button>\n'
            '      <span class="zlv">100%</span>\n'
            '      <button type="button" class="rdr-btn" data-act="zoom-in" title="نزدیک">+</button>\n'
            '      <button type="button" class="rdr-btn" data-act="zoom-fit" title="پهنای صفحه">پهنا</button>\n'
            '      <button type="button" class="rdr-btn fs" data-act="fs" title="فول‌اسکرین">⛶</button>\n'
            "    </div>\n"
            f'    <div class="rdrC">{imgs}</div>\n'
            "  </div>\n"
            '  <div class="prog-lab" id="progLab" dir="rtl"></div>\n'
            '  <div class="rdr-progress"><div class="rdrB"></div></div>\n'
            "</div>\n"
            '<button type="button" id="fab" aria-label="منو">منو</button>\n'
            + _MCAT_HTML +
            '<div id="seek" dir="ltr">\n'
            '  <div class="rail" id="rail">\n'
            '    <span class="bub" id="sbub">صفحهٔ ۱</span>\n'
            '    <div class="line"></div><div class="fill" id="sfill"></div>\n'
            '    <button type="button" class="snav" id="sprev" title="صفحهٔ قبل">‹</button>\n'
            '    <div class="th" id="sth"></div>\n'
            '    <button type="button" class="snav" id="snext" title="صفحهٔ بعد">›</button>\n'
            "  </div>\n"
            '  <div class="rlab"><span>آخر</span><span>اول</span></div>\n'
            "</div>\n"
            f"<script>\n{js}\n</script>\n"
            "</body>\n</html>\n"
        )
        return page

    g6 = _gradio_major() >= 6
    try:
        import gradio as _gr_css
        _gmaj = int(str(getattr(_gr_css, "__version__", "4")).split(".")[0] or 4)
    except Exception:
        _gmaj = 4
    _fpfx = ("/gradio_api/file=" if _gmaj >= 5 else "/file=") \
        + urllib.parse.quote(str(FONT_DIR).replace(os.sep, "/"), safe="/")
    WEB_CSS_RUNTIME = WEB_CSS.replace("__FONTPFX__", _fpfx)
    blocks_kw = {} if g6 else {"theme": gr.themes.Soft(primary_hue="indigo",
                                                       neutral_hue="slate"),
                               "css": WEB_CSS_RUNTIME}
    with gr.Blocks(title=APP_NAME, **blocks_kw) as demo:

        gr.HTML(
            """
<div class="nav">
  <div class="nav-left">
    <div class="stamp">漫</div>
    <div class="nav-brand">مانگا مترجم <span class="nav-sub">ترجمهٔ خودکار مانهوا</span></div>
  </div>
  <div class="nav-chips">
    <span class="chip">CPU / GPU</span>
    <span class="chip">Gemini · ChatGPT · Groq</span>
    <span class="chip">LaMa-Manga</span>
  </div>
</div>
"""
        )

        with gr.Group(elem_classes=["stepcard"]):
            gr.HTML('<div class="steptitle"><span class="stepnum">۱</span> ورودی — فایل یا لینک مانهوا</div>')
            inp_upload = gr.File(label=TX("app.upload", "آپلود فایل‌ها (چندتایی) — کلیک کن"),
                                 file_count="multiple", type="filepath",
                                 file_types=[".pdf", ".zip", ".cbz", ".webp", ".jpg", ".jpeg", ".png"],
                                 elem_classes=["compact-upload"])
            inp_path = gr.Textbox(label=TX("app.url", "یا URL تصویر/مانهوا (چند لینک = هر لینک در یک خط با اینتر)"),
                                  placeholder=TX("app.url_ph", "https://mgread.io/manga/cute-war/chapter-20/ > https://mgread.io/manga/cute-war/chapter-24/\nیا هر لینک در یک خط:\nhttps://cdn.example.com/chapter/1/001.webp"),
                                  elem_id="manga_inp_path")
            gr.HTML(
                '<details class="mt-browser" style="margin-top:8px;'
                'border:1px solid rgba(148,163,184,.28);border-radius:12px;'
                'background:rgba(127,127,152,.07);padding:8px 12px 10px">'
                '<summary style="cursor:pointer;font-weight:700;'
                'font-size:.95em;color:inherit">'
                '🌐 ' + TX("app.br_title",
                           "باز کردن مرورگر — سایت‌هایی که کپچا دارند") +
                '</summary>'
                '<div style="font-size:.86em;line-height:2;margin-top:8px;'
                'opacity:.92">'
                '<div>' + TX("app.br_s1",
                             "۱) دکمهٔ نارنجیِ زیر را با ماوس بگیر و در نوارِ "
                             "نشانک‌های مرورگرت رها کن (موبایل: «کپی نشانک» و "
                             "دستی به نشانک‌ها اضافه کن).") + '</div>'
                '<div>' + TX("app.br_s2",
                             "۲) به سایتِ مانهوا برو، کپچا را خودت رد کن، فصلِ "
                             "دلخواه را باز کن و تا آخرِ صفحه اسکرول کن تا "
                             "همهٔ عکس‌ها لود بشن.") + '</div>'
                '<div>' + TX("app.br_s3",
                             "۳) روی نشانکِ «🖼 استخراج عکس» کلیک کن — لینکِ "
                             "همهٔ عکس‌های فصل خودکار در فیلدِ بالا می‌نشیند؛ "
                             "بعد فقط «شروع ترجمه» را بزن.") + '</div>'
                '<div style="margin:10px 0 2px;display:flex;gap:8px;'
                'flex-wrap:wrap;align-items:center">'
                '<a id="mt_bmk" href="#" draggable="true" rel="noopener" '
                'style="display:inline-block;background:linear-gradient(135deg,'
                '#f59e0b,#ea580c);color:#fff;font-weight:800;font-size:.95em;'
                'padding:8px 16px;border-radius:10px;text-decoration:none;'
                'cursor:grab;box-shadow:0 2px 8px rgba(234,88,12,.35)">'
                '🖼 ' + TX("app.br_bm", "استخراج عکس مانهوا") + '</a>'
                '<button id="mt_bmk_copy" type="button" '
                'style="background:transparent;border:1px solid rgba(148,163,'
                '184,.4);color:inherit;border-radius:10px;padding:7px 14px;'
                'font-size:.88em;cursor:pointer">📋 ' + TX("app.br_copy",
                                                           "کپی نشانک") +
                '</button><span id="mt_bmk_done" style="color:#7fd18a;'
                'display:none;font-size:.85em">✔ ' + TX("app.br_done",
                                                        "کپی شد") + '</span>'
                '</div>'
                '<div style="opacity:.7;font-size:.88em">' +
                TX("app.br_note",
                   "نشانک فقط در مرورگرِ خودِ تو اجرا میشود — پسورد و "
                   "کوکی هیچ‌وقت به این اپ نمی‌رسد. اپِ اندروید: دکمهٔ 🌐 "
                   "داخلِ خودِ اپ مرورگرِ داخلی دارد.") + '</div>'
                '</div></details>')
            _pc_local = not _web_host()
            with gr.Row(visible=_pc_local, elem_id="mt_browser_row") as browser_row:
                mt_ibtn = gr.Button(
                    TX("app.br_open2", "🌐 مرورگر داخلی"),
                    elem_id="mt_ibtn")

        with gr.Group(elem_classes=["stepcard"]):
            gr.HTML('<div class="steptitle"><span class="stepnum">۲</span> مترجم هوش مصنوعی</div>')
            _init_models = list(load_custom_models())
            _init_ch = _ai_choices(_init_models)
            _init_prov = "auto" if "auto" in _init_ch else "gemini"
            with gr.Row(elem_id="manga_provider_row"):
                provider = gr.Dropdown(
                    _init_ch, value=_init_prov,
                    label=TX("app.ai_menu", "منوی انتخاب AI"), scale=6,
                    elem_id="manga_provider")
                cm_del_btn = gr.Button(
                    TX("app.del_model", "✖"), variant="secondary", scale=0,
                    elem_id="manga_cm_del_btn",
                    visible=(_init_prov in _cm_names(_init_models)))
                token_btn = gr.Button(
                    TX("app.get_token", "↗"), variant="secondary",
                    scale=0, elem_id="manga_token_btn")
            cm_info_md = gr.Markdown("", visible=False,
                                     elem_id="manga_cm_info")
            fields_bank = gr.State({
                "_last": _init_prov,
                "custom": {"base": str(cfg.get("api_base", "") or ""),
                           "key": "", "model": ""},
                "gemini": {"base": "", "key": "", "model": ""},
            })
            api_base = gr.Textbox(label=TX("app.api_base", "دامنهٔ API سفارشی (فقط برای provider «custom»)"),
                                  value=str(cfg.get("api_base", "") or ""),
                                  placeholder=TX("app.api_base_ph", "https://opencode.ai/inference/openai/v1/chat/completions"),
                                  elem_id="manga_api_base",
                                  visible=False,
                                  scale=3)
            with gr.Row(visible=(_init_prov != "auto")) as api_row:
                api_keys = gr.Textbox(label=TX("app.api_keys", "کلیدهای API شما (با کاما = چرخش خودکار)"),
                                      value="",
                                      type="password", scale=3,
                                      elem_id="manga_api_keys")

                model = gr.Textbox(
                    value=(_gemini_default_models_str()
                           if _init_prov == "gemini" else ""),
                    label=TX("app.model_gemini", "مدل (ها)"),
                    placeholder=TX("app.model_ph", "gemini-3.5-flash-lite,gemini-3.8-flash"),
                    scale=2, elem_id="manga_model")
                model_ref_btn = gr.Button(
                    TX("app.refresh_models", "↻ مدل‌ها"), variant="secondary", scale=1,
                    elem_id="manga_model_ref",
                    visible=(_init_prov == "gemini"))
            add_model_btn = gr.Button(
                TX("app.add_model", "+ افزودن به لیست مدل‌ها"), variant="secondary", scale=1,
                elem_id="manga_cm_add", visible=False)
            cm_edit_btn = gr.Button(
                TX("app.edit_model", "✎ ویرایش این مدل"), variant="secondary", scale=1,
                elem_id="manga_cm_edit", visible=False)
            cm_save_btn = gr.Button(
                TX("app.save_edit", "💾 ذخیرهٔ ویرایش"), variant="primary", scale=1,
                elem_id="manga_cm_save", visible=False)
            cm_hint_md = gr.Markdown("", visible=False,
                        elem_id="manga_cm_hint")
            test_key_btn = gr.Button(
                TX("app.test_keys", "تست کلیدها / لینک"),
                scale=1, elem_id="manga_test_key")
            test_key_out = gr.Textbox(
                label="", value="", interactive=False, show_label=False,
                elem_id="manga_test_key_out", visible=False,
                placeholder=TX("app.test_key_ph", "وضعیت هر کلید — سالم ✔ / خراب ✘ (بعد از ۶۰ ثانیه خودکار پاک می‌شود)"))
            custom_models_state = gr.State(_init_models)
            cm_json_box = gr.Textbox(
                value=json.dumps(custom_models_state.value, ensure_ascii=False),
                visible=True, elem_id="manga_cm_json", container=False,
                elem_classes=["manga-hide-channel"])
            cm_restore_box = gr.Textbox(
                value="", visible=True, elem_id="manga_cm_restore",
                elem_classes=["manga-hide-channel"], container=False)
            cm_add_box = gr.Textbox(
                value="", visible=True, elem_id="manga_cm_add_box",
                elem_classes=["manga-hide-channel"], container=False)
            ocr_lang = gr.CheckboxGroup(
                choices=[
                    ("ژاپنی", "ja"),
                    ("انگلیسی", "en"),
                    ("کره‌ای", "ko"),
                    ("چینی", "zh"),
                ],
                value=_ocr_lang_ui_value(cfg.get("ocr_lang", "en")),
                label=TX("app.ocr_lang", "زبانهای متن مانگا (OCR) — تیک بزن"),
                elem_id="manga_ocr_lang", scale=1)

        with gr.Group(elem_classes=["stepcard"]):
            gr.HTML('<div class="steptitle"><span class="stepnum">۳</span> خروجی</div>')
            with gr.Row():
                _of0 = str(cfg.get("out_fmt", "PDF") or "PDF")
                if _of0 not in ("PDF", "ZIP", "HTML", "PSD"):
                    _of0 = "PDF"
                out_fmt = gr.Radio(["PDF", "ZIP", "HTML", "PSD"],
                                   value=_of0, label=TX("app.out_fmt", "قالب"),
                                   elem_id="manga_out_fmt")
                quality = gr.Slider(60, 100, value=int(cfg.get("quality", 92)),
                                    step=1, label=TX("app.quality", "کیفیت تصویر"),
                                    elem_id="manga_quality")

        with gr.Accordion("✒️ فونت‌ها (اصلی + لحن‌ها — اختیاری، خالی = فونت سرور)", open=False,
                          elem_id="manga_accordion_fonts"):
            font_upload = gr.File(label=TX("app.font", "فونت اصلی (.ttf)"),
                                  file_count="single", type="filepath",
                                  file_types=[".ttf", ".otf"],
                                  elem_id="manga_font_upload",
                                  elem_classes=["compact-upload"])
            SLOT_LABELS = {
                "normal": "کودک (عادی)", "shout": "افسانه (خشم)",
                "comedy_shout": "کروش (کمدی)", "whisper": "زمزمه",
                "thought": "تفکر", "system": "سیستم/تگ",
                "letter": "نامه/طومار", "narrator": "راوی", "free_text": "متن آزاد",
                "monster": "هیولا (رکاس)", "cry": "گریه (بالو)",
                "fear": "ترس (کتیبه)", "broadcast": "بی‌سیم (چنگا)",
                "sun_thought": "تفکر خورشیدی (پرستو)",
                "square_thought": "فکر مربعی (کوفی)", "black": "دارک (تنها)",
            }
            tone_uploads = []
            tone_slots = []
            tone_enables = []
            with gr.Row():
                col1 = gr.Column()
                col2 = gr.Column()
            slots = list(FONT_BUNDLES)
            half = (len(slots) + 1) // 2
            for ci, chunk in enumerate((slots[:half], slots[half:])):
                with (col1 if ci == 0 else col2):
                    for slot, fname, desc, _u in chunk:
                        have = os.path.isfile(os.path.join(FONT_DIR, fname))
                        up = gr.File(label=f"{SLOT_LABELS.get(slot, slot)} ({desc})"
                                          f"{' ✓' if have else ''}",
                                     file_count="single", type="filepath",
                                     file_types=[".ttf", ".otf"],
                                     elem_classes=["compact-upload"])
                        en = gr.Checkbox(label=f"فعال: {SLOT_LABELS.get(slot, slot)}",
                                         value=True)
                        tone_uploads.append(up)
                        tone_slots.append(slot)
                        tone_enables.append(en)
                        try:
                            en.change(lambda v, u=up: gr.update(visible=bool(v)),
                                      inputs=[en], outputs=[up])
                        except Exception:
                            pass

        with gr.Accordion("⚙️ تنظیمات پیشرفته", open=False,
                          elem_id="manga_accordion_advanced"):
            with gr.Row():
                workers = _safe(gr.Slider, 1, 8, value=int(cfg.get("workers", 2)),
                                step=1, label=TX("app.ocr_workers", "ورکر OCR (فقط حالت تک‌عکس)"),
                                elem_id="manga_sl_workers")
                bubbles = _safe(gr.Slider, 1, 12, value=int(cfg.get("bubbles", 6)),
                                step=1, label=TX("app.bubbles", "حباب در هر درخواست ترجمه"),
                                elem_id="manga_sl_bubbles")
                batchw = _safe(gr.Slider, 1, 8, value=int(cfg.get("batch_workers", 3)),
                               step=1, label=TX("app.batch", "بستهٔ ترجمهٔ موازی (کلید جدا برای هر بسته)"),
                               elem_id="manga_sl_batchw")
            with gr.Row():
                timeout = _safe(gr.Slider, 10, 120, value=int(cfg.get("timeout", 40)),
                                step=5, label=TX("app.timeout", "تایم‌اوت هر درخواست (ثانیه)"),
                                elem_id="manga_sl_timeout")
                maxre = _safe(gr.Slider, 1, 15, value=int(cfg.get("max_retries", 8)),
                              step=1, label=TX("app.max_retry", "حداکثر تلاش ترجمه"),
                              elem_id="manga_sl_maxre")
                reqdelay = _safe(gr.Slider, 0, 5, value=float(cfg.get("request_delay", 0)),
                                 step=0.5, label=TX("app.delay", "تأخیر بین درخواست‌ها (ثانیه)"),
                                 elem_id="manga_sl_delay")
            with gr.Row():
                temp = _safe(gr.Slider, 0.0, 1.5,
                             value=float(cfg.get("temperature", 0.7)),
                             step=0.05, label=TX("app.temperature", "Temperature (خلاقیت)"),
                             elem_id="manga_sl_temp")
                top_p = _safe(gr.Slider, 0.1, 1.0,
                              value=float(cfg.get("top_p", 0.9)),
                              step=0.05, label=TX("app.top_p", "Top P"),
                              elem_id="manga_sl_topp")
                readord = gr.Radio(["rtl", "ltr"], value=str(cfg.get("reading_order", "rtl")),
                                   label=TX("app.order", "ترتیب خواندن حباب‌ها"),
                                   elem_id="manga_readord")
            with gr.Row():
                _cm0 = str(cfg.get("clean_method") or "lama-manga").strip()
                if _cm0 not in ("lama-manga", "lama-big", "opencv"):
                    _cm0 = "lama-manga"
                clean_method = gr.Radio(
                    choices=[["lama.onnx", "lama-manga"],
                             ["big-lama", "lama-big"],
                             ["opencv", "opencv"]],
                    value=_cm0,
                    label=TX("app.cleanup", "روش پاکسازی"),
                    elem_id="manga_clean_method")
            with gr.Row(elem_id="manga_mode_grid"):
                two_pass = gr.Checkbox(
                    label=TX("app.two_pass", "OCR دومرحله‌ای"), value=True,
                    elem_id="manga_cb_twopass")
                deep_thinking = gr.Checkbox(
                    label=TX("app.thinking", "حالت تفکر عمیق"),
                    value=bool(cfg.get("deep_thinking", True)),
                    elem_id="manga_cb_thinking")
                safety_settings = gr.Checkbox(
                    label=TX("app.safety", "تنظیمات ایمنی"),
                    value=bool(cfg.get("safety_settings", False)),
                    elem_id="manga_cb_safety")
                fake_test = gr.Checkbox(
                    label=TX("app.fake_test", "حالت تست"),
                    value=bool(cfg.get("fake_test", False)),
                    elem_id="manga_cb_faketest")
                clean_only = gr.Checkbox(
                    label=TX("app.cleanup_mode", "حالت پاکسازی"),
                    value=bool(cfg.get("clean_only", False)),
                    elem_id="manga_cb_cleanup")
                web_debug = gr.Checkbox(
                    label=TX("app.web_debug", "حالت دیباگ"),
                    value=bool(cfg.get("web_debug", False)),
                    elem_id="manga_cb_debug")
            with gr.Row():
                _dv0 = str(cfg.get("device") or "auto").strip().lower()
                if _dv0 not in ("auto", "cpu", "gpu"):
                    _dv0 = "auto"
                _gpu_nm = _server_gpu_label()
                _gpu_lbl = (f"gpu (سه‌تایی GPU — CUDA: {_gpu_nm})"
                            if _gpu_nm else "gpu (سه‌تایی GPU)")
                device = gr.Dropdown(
                    choices=[("auto (خودکار)", "auto"),
                             ("cpu (سه‌تایی CPU)", "cpu"),
                             (_gpu_lbl, "gpu")],
                    value=_dv0,
                    visible=_server_has_gpu(),
                    scale=2,
                    elem_id="manga_device",
                    label=TX("app.device", "دستگاه پردازش (استخراج + پاکسازی)"))
            with gr.Row():
                _mt0 = str(cfg.get("max_tokens_mode", "auto") or "auto").strip().lower()
                if _mt0 not in ("auto", "8192", "16384", "32768",
                                "65536", "custom"):
                    _mt0 = "auto"
                max_tokens = gr.Dropdown(
                    choices=[("خودکار (پیش‌فرض)", "auto"),
                             ("۸۱۹۲", "8192"), ("۱۶۳۸۴", "16384"),
                             ("۳۲۷۶۸", "32768"), ("۶۵۵۳۶", "65536"),
                             ("دلخواه", "custom")],
                    value=_mt0,
                    label=TX("app.max_tokens", "حداکثر توکن خروجی (Max Tokens)"),
                    scale=2,
                    elem_id="manga_max_tokens")
                _mtc0 = int(cfg.get("max_tokens_custom", 4096) or 4096)
                max_tokens_custom = gr.Number(
                    value=_mtc0,
                    label=TX("app.max_tokens_custom", "مقدار دلخواه (حداقل ۱۰۲۴)"),
                    precision=0, minimum=1024, scale=1,
                    visible=(_mt0 == "custom"),
                    elem_id="manga_max_tokens_custom")
                try:
                    max_tokens.change(
                        lambda v: gr.update(visible=(str(v) == "custom")),
                        inputs=[max_tokens], outputs=[max_tokens_custom])
                except Exception:
                    pass
            glossary_text = gr.Textbox(
                label=TX("app.glossary", "واژه‌نامهٔ اسامی و اصطلاحات (هر خط: English=فارسی)"),
                placeholder=TX("app.glossary_ph",
                               "Raphdonia=رافدونیا\nBarbarian=بربرین\nGuild Master=استاد گیلد"),
                lines=3, max_lines=10, interactive=True,
                info=TX("app.glossary_info",
                        "معادل‌های قفل‌شده — همیشه با همین شکل ترجمه می‌شوند؛ "
                        "اسم‌های جدیدی که AI پیدا کند خودکار یادش می‌ماند (glossary.json) "
                        "و دفعهٔ بعد خودش خوانده می‌شود"),
                value=str(cfg.get("glossary_text", "") or ""),
                elem_id="manga_glossary_text")
            story_brief = gr.Checkbox(
                label=TX("app.brief", "بریف داستان (AI اول کل فصل را می‌خواند)"),
                info=TX("app.brief_info",
                        "قبل از ترجمه یک درخواست اضافه: خلاصهٔ داستان و لحن "
                        "شخصیت‌ها ساخته می‌شود تا لحن‌ها ثابت بمانند — "
                        "پیش‌فرض خاموش"),
                value=bool(cfg.get("story_brief", False)),
                elem_id="manga_cb_brief")
            prompt_mode = gr.Dropdown(
                choices=["professional", "lite"],
                value=PROMPT_MODE_DEFAULT,
                label=TX("app.prompt_style", "سبک پرامپت مترجم"), scale=1,
                elem_id="manga_prompt_mode")
            _pp_body0 = resolve_prompt_preview(
                PROMPT_MODE_DEFAULT, cfg.get("provider"), cfg.get("model"),
                str(cfg.get("instruction_text") or ""))
            prompt_preview_body = gr.Textbox(
                label=TX("app.prompt", "پرامپت مترجم (همین به مدل فرستاده می‌شود — قابل ویرایش)"),
                lines=10, max_lines=25, interactive=True,
                placeholder=TX("app.prompt_ph", "خالی = پرامپتِ خودکارِ بر اساسِ سبک و مدل…"),
                value=_pp_body0,
                elem_id="manga_prompt_body")

        with gr.Accordion("💾 بکاپ و بازیابی — مدلها + تنظیمات", open=False,
                          elem_classes=["stepcard"],
                          elem_id="manga_accordion_backup"):
            with gr.Row():
                backup_btn = gr.Button(TX("app.backup_btn", "⬇️ گرفتن بکاپ (دانلود JSON)"),
                                       variant="primary", scale=1,
                                       elem_id="manga_backup_btn")
                import_file = gr.UploadButton(
                    "⬆️ Import — بازیابی از بکاپ",
                    file_count="single", type="filepath",
                    file_types=[".json"], variant="secondary", scale=1,
                    elem_id="manga_import_file")
            backup_out = gr.File(label=str(TX("app.backup_file", "فایلِ پشتیبان — اگر دانلودِ خودکار شروع نشد، از همین‌جا دانلودش کنید")),
                                 visible=False, elem_id="manga_backup_out")
            backup_json = gr.Textbox(value="", visible=False, container=False,
                                     elem_id="manga_backup_json")
            backup_status = gr.Textbox(
                label="", show_label=False, interactive=False, visible=False,
                elem_id="manga_backup_status")

        JOB_TTL = 12 * 3600
        live_jobs = {}

        def _get_job(sid: str) -> dict:
            if sid not in live_jobs:
                live_jobs[sid] = {
                    "proc": None,
                    "log": "— لاگ بعد از شروع ترجمه اینجا می‌آید —",
                    "lock": threading.Lock(),
                    "ts": time.time(),
                    "download_path": None,
                    "html_state": "",
                    "reader_path": None,
                    "result_visible": False,
                    "running": False,
                    "returncode": None,
                    "buf": [],
                    "t0": None,
                    "live_dir": None,
                    "live_files": [],
                    "live_slicer": None,
                }
            return live_jobs[sid]

        def _job_running(job: dict) -> bool:
            p = job.get("proc")
            if p is not None:
                try:
                    if p.poll() is None:
                        return True
                except Exception:
                    pass
            return bool(job.get("running"))

        def _kill_job(sid: str) -> None:
            job = _get_job(sid)
            with job["lock"]:
                p = job.get("proc")
                job["running"] = False
                if p is not None:
                    try:
                        if p.poll() is None:
                            try:
                                os.killpg(p.pid, signal.SIGTERM)
                            except Exception:
                                try:
                                    p.terminate()
                                except Exception:
                                    pass
                            try:
                                p.wait(timeout=2.5)
                            except Exception:
                                try:
                                    os.killpg(p.pid, signal.SIGKILL)
                                except Exception:
                                    try:
                                        p.kill()
                                    except Exception:
                                        pass
                                try:
                                    p.wait(timeout=1)
                                except Exception:
                                    pass
                    except Exception:
                        pass
                job["proc"] = None
                job["ts"] = time.time()
                job["log"] = (job.get("log") or "") + "\n⏹ ترجمه متوقف شد توسط کاربر."
                _append_job_logfile(sid, "⏹ ترجمه متوقف شد توسط کاربر.")
            try:
                _persist_job_meta(sid)
            except Exception:
                pass

        def _new_sid() -> str:
            import uuid
            return uuid.uuid4().hex

        SESS_DIR = os.path.join(WORK_DIR, "sessions")
        os.makedirs(SESS_DIR, exist_ok=True)

        def _persist_job_meta(sid: str) -> None:
            if not sid:
                return
            job = _get_job(sid)
            try:
                with job["lock"]:
                    meta = {
                        "sid": sid,
                        "running": _job_running(job),
                        "log": (job.get("log") or "")[-24000:],
                        "ts": job.get("ts") or time.time(),
                        "download_path": job.get("download_path"),
                        "download_debug": job.get("download_debug"),
                        "result_visible": bool(job.get("result_visible")),
                        "returncode": job.get("returncode"),
                        "out_v": job.get("out_v"),
                        "src": str(job.get("src") or "")[:500],
                        "reader_path": job.get("reader_path"),
                        "reader_debug_path": job.get("reader_debug_path"),
                        "live_dir": job.get("live_dir"),
                        "html_debug": (job.get("html_debug") or "")[:500] and True,
                        "has_debug": bool(job.get("download_debug") or job.get("reader_debug_path")),
                        "want_debug": bool(job.get("want_debug")),
                    }
                path = os.path.join(SESS_DIR, f"{sid}.json")
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(meta, f, ensure_ascii=False)
            except Exception:
                pass

        def _load_job_meta(sid: str) -> dict:
            path = os.path.join(SESS_DIR, f"{sid}.json")
            try:
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}

        def _append_job_logfile(sid: str, text: str) -> None:
            if not sid or not text:
                return
            try:
                os.makedirs(SESS_DIR, exist_ok=True)
                with open(os.path.join(SESS_DIR, f"{sid}.log"), "a",
                          encoding="utf-8") as f:
                    f.write(text if text.endswith("\n") else text + "\n")
            except Exception:
                pass

        def _src_signature(src) -> str:
            import hashlib
            parts = []
            for p in str(src or "").split(","):
                p = p.strip()
                if not p:
                    continue
                if os.path.isfile(p):
                    try:
                        st = os.stat(p)
                        h = hashlib.md5()
                        h.update(
                            f"{os.path.basename(p)}:{st.st_size}".encode())
                        with open(p, "rb") as f:
                            h.update(f.read(65536))
                            if st.st_size > 131072:
                                f.seek(max(0, st.st_size - 65536))
                                h.update(f.read(65536))
                        parts.append(h.hexdigest()[:16])
                    except Exception:
                        parts.append("f?")
                else:
                    parts.append("u:" + p)
            return "|".join(parts)

        def _find_active_sid(preferred: str = "") -> str:
            
            pref = (preferred or "").strip()
            if not pref:
                return ""
            job = live_jobs.get(pref)
            if job is not None:
                return pref
            meta = _load_job_meta(pref)
            if meta:
                j = _get_job(pref)
                with j["lock"]:
                    if meta.get("log"):
                        j["log"] = meta.get("log")
                    if meta.get("download_path"):
                        j["download_path"] = meta.get("download_path")
                    if meta.get("result_visible"):
                        j["result_visible"] = True
                    if meta.get("html_state"):
                        j["html_state"] = meta.get("html_state")
                    if meta.get("reader_path"):
                        j["reader_path"] = meta.get("reader_path")
                    if meta.get("reader_debug_path"):
                        j["reader_debug_path"] = meta.get("reader_debug_path")
                    if meta.get("live_dir"):
                        j["live_dir"] = meta.get("live_dir")
                    if meta.get("download_debug"):
                        j["download_debug"] = meta.get("download_debug")
                    if meta.get("want_debug"):
                        j["want_debug"] = meta.get("want_debug")
                    j["ts"] = meta.get("ts") or time.time()
                    j["out_v"] = meta.get("out_v")
                    j["src"] = meta.get("src")
                    if not _job_running(j):
                        j["running"] = False
                return pref
            return pref

        def _finalize_job_success(sid: str) -> None:
            job = _get_job(sid)
            with job["lock"]:
                if job.get("result_visible"):
                    return
                out_v = job.get("out_v") or ""
                src = job.get("src") or ""
                t0 = job.get("t0") or time.time()
                buf = list(job.get("buf") or [])
            if not out_v:
                return
            el = int(time.time() - t0)
            dur_s = f"{el // 60}:{el % 60:02d}"
            target = out_v
            try:
                if os.path.isdir(out_v):
                    target = shutil.make_archive(out_v, "zip", out_v)
            except Exception:
                target = out_v
            try:
                append_history({
                    "time": datetime.now().strftime("%m-%d %H:%M"),
                    "input": src, "status": "✅", "duration": dur_s
                })
            except Exception:
                pass
            def _collect_imgs(root_paths, exclude_debug=False):
                found = []
                seen = set()
                for root in root_paths:
                    if not root:
                        continue
                    if exclude_debug and "debug" in os.path.basename(str(root)).lower():
                        continue
                    if os.path.isfile(root) and root.lower().endswith(
                        (".webp", ".png", ".jpg", ".jpeg")
                    ):
                        if exclude_debug and "debug" in os.path.basename(root).lower():
                            continue
                        if root not in seen:
                            seen.add(root)
                            found.append(root)
                        continue
                    if not os.path.isdir(root):
                        continue
                    try:
                        names = sorted(os.listdir(root), key=natural_key)
                    except Exception:
                        continue
                    for f in names:
                        if f.lower().endswith((".webp", ".png", ".jpg", ".jpeg")):
                            if exclude_debug and ("debug" in f.lower() or "debug" in root.lower()):
                                continue
                            if "_base." in f.lower():
                                continue
                            p = os.path.join(root, f)
                            if p not in seen:
                                seen.add(p)
                                found.append(p)
                return found

            def _pdf_to_reader_imgs(pdf_path, dest_dir, limit=80):
                
                try:
                    import fitz
                except ImportError:
                    try:
                        subprocess.check_call(
                            [sys.executable, "-m", "pip", "install", "-q", "pymupdf"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        )
                        import fitz
                    except Exception:
                        return []
                os.makedirs(dest_dir, exist_ok=True)
                out = []
                try:
                    doc = fitz.open(pdf_path)
                    zoom = 120 / 72.0
                    mat = fitz.Matrix(zoom, zoom)
                    for i, page in enumerate(doc):
                        if i >= limit:
                            break
                        pix = page.get_pixmap(matrix=mat)
                        fp = os.path.join(dest_dir, f"view_{i+1:03d}.jpg")
                        pix.save(fp)
                        out.append(fp)
                    doc.close()
                except Exception as e:
                    print(f"[!] استخراج PDF برای نمایشگر: {e}")
                return out

            parent = os.path.dirname(str(out_v)) or "."
            search_dirs = [
                out_v if os.path.isdir(out_v) else None,
            ]
            _last_out_dir = ""
            try:
                _cache_root_v = _cache_dir_for(out_v)
                with open(os.path.join(_cache_root_v, "last_out.json"),
                          encoding="utf-8") as _fh:
                    _lo_j = json.load(_fh) or {}
                _lo_d = os.path.join(_cache_root_v,
                                     str(_lo_j.get("dir") or ""))
                if (_lo_j.get("dir") and os.path.isdir(_lo_d)
                        and any(_fn.lower().endswith(
                            (".webp", ".png", ".jpg", ".jpeg"))
                            for _fn in os.listdir(_lo_d))):
                    _last_out_dir = _lo_d
            except Exception:
                _last_out_dir = ""
            if _last_out_dir and os.path.isdir(_last_out_dir):
                search_dirs.append(_last_out_dir)
            else:
                _cache_root_fb = _cache_dir_for(out_v)
                _newest_out = ""
                _newest_mt = -1.0
                try:
                    if os.path.isdir(_cache_root_fb):
                        for _name_fb in os.listdir(_cache_root_fb):
                            if _name_fb != "out" and not _name_fb.startswith("out_"):
                                continue
                            _p_fb = os.path.join(_cache_root_fb, _name_fb)
                            if not os.path.isdir(_p_fb):
                                continue
                            try:
                                if not any(_fn.lower().endswith(
                                        (".webp", ".png", ".jpg", ".jpeg"))
                                        for _fn in os.listdir(_p_fb)):
                                    continue
                            except Exception:
                                continue
                            _mt_fb = os.path.getmtime(_p_fb)
                            if _mt_fb > _newest_mt:
                                _newest_mt = _mt_fb
                                _newest_out = _p_fb
                except Exception:
                    _newest_out = ""
                if _newest_out:
                    search_dirs.append(_newest_out)
            cache_debug = os.path.join(_cache_dir_for(out_v), "debug_safe_v3")
            if not os.path.isdir(cache_debug):
                cache_debug = os.path.join(_cache_dir_for(out_v), "debug")

            imgs = _collect_imgs(search_dirs, exclude_debug=True)
            if not imgs and str(target).lower().endswith((".webp", ".png", ".jpg", ".jpeg")):
                imgs = [target]

            pdf_for_view = None
            if not imgs:
                for cand in (out_v, target):
                    if cand and str(cand).lower().endswith(".pdf") and os.path.isfile(cand):
                        pdf_for_view = cand
                        break
            debug_pdf = os.path.splitext(str(out_v))[0] + "_debug.pdf"
            debug_imgs = []
            if os.path.isfile(debug_pdf):
                dbg_dir = os.path.join(parent, "_debug_view")
                debug_imgs = _pdf_to_reader_imgs(debug_pdf, dbg_dir)
            if pdf_for_view and not imgs:
                view_dir = os.path.join(parent, "_pdf_view")
                imgs = _pdf_to_reader_imgs(pdf_for_view, view_dir)

            if not debug_imgs:
                debug_imgs = _collect_imgs([cache_debug])

            try:
                reader_html = build_reader_html(imgs, standalone=True)
            except Exception:
                reader_html = ""
            try:
                debug_reader_html = build_reader_html(debug_imgs, standalone=True) if debug_imgs else ""
            except Exception:
                debug_reader_html = ""

            reader_path = None
            debug_reader_path = None
            try:
                base_dir = out_v if os.path.isdir(out_v) else os.path.dirname(str(out_v))
                if not base_dir or not os.path.isdir(base_dir):
                    base_dir = os.path.join(OUT_DIR, sid[:12])
                    os.makedirs(base_dir, exist_ok=True)
                reader_path = os.path.join(base_dir, "reader.html")
                with open(reader_path, "w", encoding="utf-8") as rf:
                    rf.write(reader_html or "")
                if debug_reader_html:
                    debug_reader_path = os.path.join(base_dir, "reader_debug.html")
                    with open(debug_reader_path, "w", encoding="utf-8") as rf:
                        rf.write(debug_reader_html)
            except Exception as e:
                print(f"[!] ذخیره reader.html ناموفق: {e}")
                reader_path = None

            download_debug = debug_pdf if os.path.isfile(debug_pdf) else None
            if not download_debug and debug_imgs:
                try:
                    import zipfile
                    zpath = os.path.join(parent, os.path.splitext(os.path.basename(str(out_v)))[0] + "_debug_imgs.zip")
                    with zipfile.ZipFile(zpath, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                        for p in debug_imgs:
                            zf.write(p, arcname=os.path.basename(p))
                    download_debug = zpath
                except Exception:
                    download_debug = None

            extra = ""
            if not imgs:
                extra = "\n⚠ تصاویر برای نمایشگر پیدا نشد — فقط دانلود فعال است."
            if debug_imgs or download_debug:
                extra += f"\n🔍 دیباگ: {len(debug_imgs)} صفحه آماده نمایش/دانلود"
            _done_line = (f"✅ تمام شد ({dur_s}) — دکمه‌های نمایش و دانلود پایین فعال شدند"
                          + extra)
            final_log = "\n".join(buf[-120:]) + _done_line
            _append_job_logfile(sid, _done_line)
            with job["lock"]:
                job["log"] = final_log
                job["download_path"] = target
                job["download_debug"] = download_debug
                job["html_state"] = reader_html
                job["html_debug"] = debug_reader_html
                job["reader_path"] = reader_path
                job["reader_debug_path"] = debug_reader_path
                job["result_visible"] = True
                job["ts"] = time.time()
            _persist_job_meta(sid)

        def _start_job_reader(sid: str, proc: subprocess.Popen, t0: float) -> None:
            job = _get_job(sid)

            def _fmt(buf_lines):
                return "\n".join(buf_lines[-120:]) if buf_lines else "… در حال دریافت خروجی …"

            def _reader():
                buf = list(job.get("buf") or [])
                n = 0
                partial = b""
                log_fh = None
                try:
                    os.makedirs(SESS_DIR, exist_ok=True)
                    log_fh = open(os.path.join(SESS_DIR, f"{sid}.log"), "a",
                                  encoding="utf-8")
                except Exception:
                    log_fh = None
                try:
                    stream = proc.stdout
                    fd = None
                    try:
                        fd = stream.fileno()
                    except Exception:
                        fd = None
                    while True:
                        with job["lock"]:
                            if job.get("proc") is None and not job.get("running"):
                                break
                        ended = proc.poll() is not None
                        chunk = b""
                        try:
                            if fd is not None:
                                import select as _sel
                                try:
                                    ready, _, _ = _sel.select([stream], [], [], 0.25)
                                except Exception:
                                    ready = [stream]
                                if ready:
                                    chunk = os.read(fd, 8192)
                            else:
                                chunk = stream.read(4096) if stream else b""
                        except Exception:
                            chunk = b""
                        if chunk:
                            if isinstance(chunk, str):
                                chunk = chunk.encode("utf-8", "replace")
                            partial += chunk
                            while b"\n" in partial:
                                line, partial = partial.split(b"\n", 1)
                                text = line.decode("utf-8", "replace").rstrip("\r")
                                buf.append(text)
                                if log_fh is not None:
                                    try:
                                        log_fh.write(text + "\n")
                                        log_fh.flush()
                                    except Exception:
                                        log_fh = None
                                if len(buf) > 400:
                                    del buf[:-300]
                                with job["lock"]:
                                    job["buf"] = buf
                                    job["log"] = _fmt(buf)
                                    job["ts"] = time.time()
                                n += 1
                                
                                if n % 2 == 0:
                                    _persist_job_meta(sid)
                        elif ended:
                            break
                        else:
                            time.sleep(0.05)
                    if partial.strip():
                        _tail_txt = partial.decode("utf-8", "replace").rstrip("\r")
                        buf.append(_tail_txt)
                        if log_fh is not None:
                            try:
                                log_fh.write(_tail_txt + "\n")
                                log_fh.flush()
                            except Exception:
                                log_fh = None
                    try:
                        proc.wait(timeout=5)
                    except Exception:
                        pass
                except Exception as e:
                    with job["lock"]:
                        job["log"] = (job.get("log") or "") + f"\n⚠ reader: {e}"
                    _append_job_logfile(sid, f"⚠ reader: {e}")
                finally:
                    if log_fh is not None:
                        try:
                            log_fh.close()
                        except Exception:
                            pass
                    log_fh = None
                    rc = None
                    try:
                        rc = proc.poll()
                    except Exception:
                        pass
                    with job["lock"]:
                        if job.get("proc") is proc:
                            job["proc"] = None
                        job["running"] = False
                        job["returncode"] = rc
                        job["buf"] = buf
                        if buf:
                            job["log"] = _fmt(buf)
                        job["ts"] = time.time()
                        job["done_event"] = True
                    if rc == 0:
                        try:
                            _finalize_job_success(sid)
                        except Exception as e:
                            with job["lock"]:
                                job["log"] = (job.get("log") or "") + f"\n⚠ finalize: {e}"
                    elif rc not in (None, 0) and rc not in (-15, -9, 15, 9):
                        with job["lock"]:
                            job["log"] = (job.get("log") or "") + f"\n\n❌ خطا — کد خروج {rc}"
                        _append_job_logfile(sid, f"❌ خطا — کد خروج {rc}")
                    _persist_job_meta(sid)

            threading.Thread(target=_reader, daemon=True, name=f"manga-job-{sid[:8]}").start()

            def _heartbeat():
                while True:
                    with job["lock"]:
                        if not _job_running(job):
                            break
                        buf = list(job.get("buf") or [])
                        job["log"] = _fmt(buf)
                        job["ts"] = time.time()
                    try:
                        _persist_job_meta(sid)
                    except Exception:
                        pass
                    time.sleep(1.0)
            threading.Thread(target=_heartbeat, daemon=True, name=f"manga-hb-{sid[:8]}").start()

        session_id = gr.State("")
        sid_box = gr.Textbox(value="", visible=True, elem_id="manga_sid", label="sid",
                             elem_classes=["manga-hide-channel"])
        
        sid_holder = gr.Textbox(value="", visible=True, elem_id="manga_sid_holder",
                                label="sid_holder", elem_classes=["manga-hide-channel"])

        run_btn = gr.Button(TX("app.run", "🚀  شروع ترجمه"), variant="primary", elem_id="runbtn")

        with gr.Group(visible=False, elem_id="askmode") as ask_group:
            gr.HTML(
                "<div style='text-align:right;font-weight:700;"
                "margin:2px 0 4px'>"
                + TX("app.ask_title", "مدل یا پرامپتِ ترجمه عوض شده")
                + "</div>"
                "<div style='text-align:right;opacity:.85;font-size:.95em;"
                "margin-bottom:8px'>"
                + TX("app.ask_body",
                     "همان ورودی، ولی تنظیمِ ترجمه با دفعهٔ قبل فرق داره — "
                     "از کجا ادامه بدم؟")
                + "</div>")
            with gr.Row():
                ask_continue_btn = gr.Button(
                    TX("app.ask_continue", "ادامه بده (همون‌جا که بود)"),
                    variant="primary")
                ask_fresh_btn = gr.Button(
                    TX("app.ask_fresh", "از اول ترجمه کن"),
                    variant="stop")
                ask_cancel_btn = gr.Button(
                    TX("app.ask_cancel", "بی‌خیال"))

        with gr.Accordion("📡 لاگ زنده", open=True):
            gr.HTML(
                f"""
<div id="manga_status_chip"></div>
<div class="log-tools" data-sessdir="{SESS_DIR.replace('&', '&amp;').replace('"', '&quot;')}">
  <button type="button" class="log-tool-btn" id="manga_copy_log" title="کپی متن لاگ">📋 کپی لاگ</button>
  <button type="button" class="log-tool-btn" id="manga_dl_log" title="دانلودِ فایلِ کاملِ لاگ — از اولِ کار تا همین لحظه">⬇ دانلود لاگ</button>
</div>
"""
            )
            log_box = _safe(gr.Textbox, lines=16, max_lines=50, autoscroll=True,
                            show_label=False, interactive=True,
                            elem_id="manga_live_log",
                            value=TX("app.log_ph", "— لاگ بعد از شروع ترجمه اینجا می‌آید —"))
            prog_html = _safe(gr.HTML, elem_id="manga_prog_row",
                              visible=True, value="")

        html_state = gr.State("")
        html_debug_state = gr.State("")
        with gr.Group(elem_classes=["stepcard"], visible=False) as result_group:
            gr.HTML('<div class="steptitle"><span class="stepnum">📖</span> '
                    'نمایش</div>')
            live_btn = _safe(gr.Button, "📖 نمایش", visible=False, elem_id="manga_live_btn")
            gr.HTML('<div class="livehint" id="manga_live_hint" style="display:none">'
                    'تا کار در جریان است، هر صفحهٔ جدید خودش داخل نمایش اضافه می‌شود — '
                    'دکمهٔ 🔍 دیباگ هم داخل خودِ نمایش است</div>')
            with gr.Row():
                btn_view = _safe(gr.Button, "👁 نمایش", visible=False,
                                 elem_id="manga_view_btn")
                dl_btn = _safe(gr.DownloadButton, label=TX("app.download", "⬇ دانلود"), visible=False)
            debug_row = gr.Row(visible=False)
            with debug_row:
                btn_view_debug = _safe(gr.Button, "🔍 صفحه دیباگ", visible=False,
                                       elem_id="manga_view_debug_btn")
                dl_btn_debug = _safe(gr.DownloadButton, label=TX("app.download_debug", "⬇ دانلود دیباگ"), visible=False)
            viewer_html = gr.HTML(visible=False, elem_id="reader_wrap")

        LS_KEY = "manga_autotranslate_form_v2"
        JOB_KEY = "manga_job_v1"
        save_form_js = f"""
(sid, sidBox, inp, prov, keys, model, fmt, qual, workers, bubbles, timeout, batchw, maxre, reqdelay, temp, topp, readord, cleanm, device, twopass, fake, cleano, think, safety, mtmode, mtcust, glos, brief) => {{
  try {{
    const realSid = (sid || sidBox || "").toString().trim();
    const clean = (v) => {{
      const s = (v === null || v === undefined) ? "" : String(v).trim();
      return (s === "null" || s === "undefined") ? "" : s;
    }};
    const data = {{
      sid: realSid,
      inp: clean(inp),
      prov: clean(prov),
      keys: clean(keys),
      model: clean(model),
      fmt: clean(fmt),
      qual: qual,
      workers: workers,
      bubbles: bubbles,
      timeout: timeout,
      batchw: batchw,
      maxre: maxre,
      reqdelay: reqdelay,
      temp: (temp === null || temp === undefined) ? 0.7 : temp,
      top_p: (topp === null || topp === undefined) ? 0.9 : topp,
      readord: readord || "",
      cleanm: clean(cleanm) || "lama-manga",
      device: (clean(device) || "auto"),
      twopass: twopass === null || twopass === undefined ? true : !!twopass,
      fake_test: !!fake,
      clean_only: !!cleano,
      deep_thinking: think === null || think === undefined ? true : !!think,
      safety_settings: !!safety,
      max_tokens: clean(mtmode) || "auto",
      max_tokens_custom: (mtcust === null || mtcust === undefined) ? 4096 : Number(mtcust),
      glossary_text: clean(glos),
      story_brief: brief === null || brief === undefined ? false : !!brief,
      ts: Date.now()
    }};
    localStorage.setItem("{LS_KEY}", JSON.stringify(data));
    try {{
      const kk = clean(keys);
      if (kk) localStorage.setItem("manga_keys_v1",
        JSON.stringify({{ k: kk, ts: Date.now() }}));
    }} catch (e) {{}}
    if (realSid) localStorage.setItem("manga_sid", realSid);
  }} catch (e) {{}}
  return [];
}}
"""
        save_sid_js = f"""
(sid, sidBox) => {{
  try {{
    const realSid = (sid || sidBox || "").toString().trim();
    if (realSid) {{
      localStorage.setItem("manga_sid", realSid);
      let raw = localStorage.getItem("{LS_KEY}");
      let data = {{}};
      try {{ data = raw ? JSON.parse(raw) : {{}}; }} catch (e) {{ data = {{}}; }}
      data.sid = realSid;
      data.ts = Date.now();
      localStorage.setItem("{LS_KEY}", JSON.stringify(data));
      try {{
        let jraw = localStorage.getItem("{JOB_KEY}");
        let job = jraw ? JSON.parse(jraw) : {{}};
        job.sid = realSid;
        job.ts = Date.now();
        localStorage.setItem("{JOB_KEY}", JSON.stringify(job));
      }} catch (e2) {{}}
    }}
  }} catch (e) {{}}
  return [];
}}
"""
        
        save_job_js = f"""
(sid, sidBox, btnLabel, logText) => {{
  try {{ if (window.__mangaUpdateChip) window.__mangaUpdateChip(logText, btnLabel); }} catch (e) {{}}
  try {{ if (window.__mangaUpdateProg) window.__mangaUpdateProg(logText, btnLabel); }} catch (e) {{}}
  try {{
    const JOB = "{JOB_KEY}";
    let prev = {{}};
    try {{ prev = JSON.parse(localStorage.getItem(JOB) || "{{}}"); }} catch (e) {{ prev = {{}}; }}
    const realSid = (sid || sidBox || "").toString().trim();
    const log = (logText || "").toString();
    const btn = (btnLabel || "").toString();
    const running = btn.indexOf("متوقف") >= 0 || btn.indexOf("⏹") >= 0;
    const prevSid = (prev.sid || "").trim();
    const prevLog = (prev.log || "").toString();
    const prevRunning = !!prev.running;

    if (prevRunning && prevSid && realSid && realSid !== prevSid) {{
      return [];
    }}
    if ((!log || log.indexOf("— لاگ بعد") === 0) && prevLog && prevLog.indexOf("— لاگ بعد") !== 0) {{
      return [];
    }}
    const done = (log || prevLog || "").indexOf("تمام شد") >= 0
      || (log || prevLog || "").indexOf("✅") >= 0
      || (log || prevLog || "").indexOf("موفق") >= 0;
    if (prevRunning && !running && !done && prevLog && log && prevLog.length >= log.length) {{
      if (log.length > prevLog.length + 10 && (!realSid || realSid === prevSid)) {{
        prev.log = log;
        prev.ts = Date.now();
        localStorage.setItem(JOB, JSON.stringify(prev));
      }} else {{
        prev.running = false;
        prev.btn = btn || prev.btn;
        prev.ts = Date.now();
        localStorage.setItem(JOB, JSON.stringify(prev));
      }}
      return [];
    }}

    let keepLog = log;
    if (prevLog && log && prevLog.length > log.length + 40) {{
      keepLog = prevLog;
    }}
    if (prevLog && (!log || log.indexOf("— لاگ بعد") === 0)) {{
      keepLog = prevLog;
    }}

    const job = {{
      sid: realSid || prevSid || "",
      log: keepLog || prevLog || "",
      btn: (running || prevRunning) ? (running ? btn : (prev.btn || btn)) : (btn || prev.btn || ""),
      running: running || (prevRunning && (!realSid || realSid === prevSid) && !btn),
      ts: Date.now()
    }};
    const done2 = (keepLog || "").indexOf("تمام شد") >= 0
      || (keepLog || "").indexOf("✅") >= 0;
    if (done2) {{
      job.running = false;
      job.btn = "🚀  شروع ترجمه";
    }} else if (!running && btn.indexOf("شروع") >= 0 && prevRunning && keepLog === prevLog) {{
      job.running = true;
      job.btn = prev.btn || "⏹  متوقف ترجمه";
      job.sid = prevSid || job.sid;
    }}
    localStorage.setItem(JOB, JSON.stringify(job));
    if (job.sid) localStorage.setItem("manga_sid", job.sid);
  }} catch (e) {{}}
  return [];
}}
"""

        load_form_js = f"""
() => {{
  try {{ window.__mangaLoadJsRan = (window.__mangaLoadJsRan || 0) + 1; }} catch (e) {{}}
  try {{
    let raw = localStorage.getItem("{LS_KEY}");
    if (!raw) {{
      raw = localStorage.getItem("manga_autotranslate_form_v1");
      if (raw) {{
        try {{ localStorage.setItem("{LS_KEY}", raw); }} catch (e) {{}}
      }}
    }}
    try {{
      const pk = JSON.parse(localStorage.getItem("manga_keys_v1") || "null");
      if (pk && pk.k) {{
        if (raw) {{
          try {{
            const dk = JSON.parse(raw) || {{}};
            if (!dk.keys) {{ dk.keys = pk.k; raw = JSON.stringify(dk); }}
          }} catch (e) {{}}
        }} else {{
          raw = JSON.stringify({{ keys: pk.k }});
        }}
      }}
    }} catch (e) {{}}
    try {{
      if (raw) {{
        let dj = {{}};
        try {{ dj = JSON.parse(raw) || {{}}; }} catch (e) {{ dj = {{}}; }}
        const gv = (id) => {{
          try {{
            const root = document.getElementById(id);
            if (!root) return "";
            const el = root.querySelector("input, textarea") || root;
            return String((el && el.value) || "").trim();
          }} catch (e) {{ return ""; }}
        }};
        let ch = false;
        const ck = gv("manga_api_keys");
        if (ck && ck !== String(dj.keys || "")) {{ dj.keys = ck; ch = true;
          try {{ localStorage.setItem("manga_keys_v1",
            JSON.stringify({{ k: ck, ts: Date.now() }})); }} catch (e) {{}}
        }}
        const cm = gv("manga_model");
        if (cm && cm !== String(dj.model || "")) {{ dj.model = cm; ch = true; }}
        if (ch) {{
          dj.ts = Date.now();
          const nj = JSON.stringify(dj);
          try {{ localStorage.setItem("{LS_KEY}", nj); }} catch (e) {{}}
          raw = nj;
        }}
      }}
    }} catch (e) {{}}
    const sidOnly = (localStorage.getItem("manga_sid") || "").trim();
    let job = {{}};
    try {{ job = JSON.parse(localStorage.getItem("{JOB_KEY}") || "{{}}"); }} catch (e) {{ job = {{}}; }}
    const jobSid = (job.sid || "").trim();
    const bestSid = sidOnly || jobSid || "";

    if (!raw) {{
      if (bestSid) {{
        return [JSON.stringify({{
          sid: bestSid,
          ts: Date.now(),
          _jobLog: job.log || "",
          _jobBtn: job.btn || "",
          _jobRunning: !!job.running
        }})];
      }}
      return [""];
    }}
    const d = JSON.parse(raw);
    if (!d) {{
      if (bestSid) {{
        return [JSON.stringify({{
          sid: bestSid,
          ts: Date.now(),
          _jobLog: job.log || "",
          _jobBtn: job.btn || "",
          _jobRunning: !!job.running
        }})];
      }}
      try {{
        const pk = JSON.parse(localStorage.getItem("manga_keys_v1") || "null");
        if (pk && pk.k) return [JSON.stringify({{ keys: pk.k }})];
      }} catch (e) {{}}
      return [""];
    }}
    try {{ d.ts = Date.now(); localStorage.setItem("{LS_KEY}", JSON.stringify(d)); }} catch (e) {{}}
    if (bestSid) d.sid = bestSid;
    d._jobLog = job.log || "";
    d._jobBtn = job.btn || "";
    d._jobRunning = !!job.running;
    return [JSON.stringify(d)];
  }} catch (e) {{
    return [""];
  }}
}}
"""

        client_restore_js = f"""
() => {{
  const KEY = "{LS_KEY}";
  const JOB = "{JOB_KEY}";

  if (!window.__mangaInputGuard) {{
    window.__mangaInputGuard = true;
    try {{
      const markDirty = (e) => {{
        try {{
          const t = e.target;
          if (!(t && t.closest)) return;
          if (t.closest("#manga_api_keys")) window.__mangaKeysDirty = true;
          if (t.closest("#manga_model")) window.__mangaModelDirty = true;
        }} catch (err) {{}}
      }};
      document.addEventListener("input", markDirty, true);
      document.addEventListener("paste", markDirty, true);
    }} catch (e) {{}}
  }}

  const setVal = (el, val) => {{
    if (!el || val === undefined || val === null) return;
    const s = String(val);
    try {{
      const proto = el.tagName === "TEXTAREA"
        ? (window.HTMLTextAreaElement && window.HTMLTextAreaElement.prototype)
        : (window.HTMLInputElement && window.HTMLInputElement.prototype);
      const desc = proto && Object.getOwnPropertyDescriptor(proto, "value");
      if (desc && desc.set) desc.set.call(el, s);
      else el.value = s;
    }} catch (e) {{ el.value = s; }}
    el.dispatchEvent(new Event("input", {{ bubbles: true }}));
    el.dispatchEvent(new Event("change", {{ bubbles: true }}));
  }};

  const findLogEl = () => {{
    return document.querySelector("#manga_live_log textarea")
      || document.querySelector('[id*="manga_live_log"] textarea')
      || (() => {{
          const areas = Array.from(document.querySelectorAll("textarea"));
          return areas.sort((a,b) => (b.rows||0)-(a.rows||0))[0] || null;
        }})();
  }};

  const findSidEl = () => {{
    return document.querySelector("#manga_sid textarea")
      || document.querySelector("#manga_sid input")
      || document.querySelector('[id*="manga_sid"] textarea')
      || document.querySelector('[id*="manga_sid"] input');
  }};

  const byId = (id) => {{
    const root = document.getElementById(id);
    if (!root) return null;
    return root.querySelector("input, textarea, select") || root;
  }};

  const apply = () => {{
    try {{
      let job = {{}};
      try {{ job = JSON.parse(localStorage.getItem(JOB) || "{{}}"); }} catch (e) {{ job = {{}}; }}
      const sidOnly = (localStorage.getItem("manga_sid") || job.sid || "").trim();
      const jobLog = (job.log || "").toString();

      if (sidOnly) {{
        const sidEl = findSidEl();
        if (sidEl) setVal(sidEl, sidOnly);
      }}

      const jobDone = (jobLog || "").indexOf("تمام شد") >= 0 || (jobLog || "").indexOf("✅") >= 0;
      if (jobDone && job.running) {{
        try {{
          job.running = false;
          job.btn = "🚀  شروع ترجمه";
          localStorage.setItem(JOB, JSON.stringify(job));
        }} catch (e) {{}}
      }}
      try {{ if (window.__mangaUpdateProg) window.__mangaUpdateProg(jobLog, job.btn || ""); }} catch (e) {{}}

      if (jobLog && jobLog.indexOf("— لاگ بعد") !== 0) {{
        const logEl = findLogEl();
        if (logEl) {{
          const cur = (logEl.value || "").trim();
          if (!cur || cur.indexOf("— لاگ بعد") === 0 || jobLog.length >= cur.length) {{
            setVal(logEl, jobLog);
            try {{ logEl.scrollTop = logEl.scrollHeight; }} catch (e) {{}}
          }}
        }}
      }}

      let raw = localStorage.getItem(KEY) || localStorage.getItem("manga_autotranslate_form_v1");
      if (raw) {{
        const d = JSON.parse(raw);
        if (d) {{
          let curProv = "";
          try {{
            const pe = document.querySelector("#manga_provider_row input, #manga_provider_row select, #manga_provider_row textarea");
            curProv = String((pe && pe.value) || "").trim();
          }} catch (e) {{ curProv = ""; }}
          const sameProv = !d.prov || !curProv
            || String(d.prov).trim() === curProv;
          if (sameProv) {{
            if (d.keys && !window.__mangaKeysDirty) {{
              const k = byId("manga_api_keys") || document.querySelector('input[type="password"]');
              if (k) setVal(k, d.keys);
            }}
            if (d.model && !window.__mangaModelDirty) {{
              const mRaw = String(d.model || "");
              const mClean = mRaw.replace(/[\\'\\"\\[\\]{{}}()<>]+/g, "")
                                 .replace(/\\s+/g, " ").trim();
              if (mClean) {{
                const m = byId("manga_model");
                if (m) setVal(m, mClean);
                if (mClean !== mRaw) {{
                  try {{ d.model = mClean; localStorage.setItem(KEY, JSON.stringify(d)); }} catch (e) {{}}
                }}
              }}
            }}
          }}
        }} else {{
          try {{
            const pk2 = JSON.parse(localStorage.getItem("manga_keys_v1") || "null");
            if (pk2 && pk2.k && !window.__mangaKeysDirty) {{
              const k = byId("manga_api_keys")
                || document.querySelector('input[type="password"]');
              if (k) setVal(k, pk2.k);
            }}
          }} catch (e) {{}}
        }}
      }}

      try {{
        const cmRaw = (localStorage.getItem("manga_custom_models") || "").trim();
        if (cmRaw && cmRaw.charAt(0) === "[") {{
          const cmEl = byId("manga_cm_restore");
          if (cmEl && (cmEl.value || "") !== cmRaw) setVal(cmEl, cmRaw);
        }}
      }} catch (e) {{}}
    }} catch (e) {{ console.warn("manga restore", e); }}
  }};

  apply();
  [100, 300, 600, 1000, 2000, 3500, 5000, 8000, 12000].forEach((t) => setTimeout(apply, t));

  try {{
    const saveFromDom = () => {{
      try {{
        const logEl = findLogEl();
        if (!logEl) return;
        const log = logEl.value || "";
        if (!log || log.indexOf("— لاگ بعد") === 0) return;
        let job = {{}};
        try {{ job = JSON.parse(localStorage.getItem(JOB) || "{{}}"); }} catch (e) {{ job = {{}}; }}
        if (job.running && job.sid && job.log && job.log.length > log.length + 30) return;
        if (job.running && job.log && (!log || log.indexOf("— لاگ بعد") === 0)) return;
        const sidLs = (localStorage.getItem("manga_sid") || "").trim();
        const sid = (job.running && job.sid) ? job.sid : (sidLs || job.sid || "");
        const runRoot = document.getElementById("runbtn");
        const btn = runRoot ? (runRoot.querySelector("button") || runRoot) : null;
        const btnT = btn ? (btn.textContent || "") : "";
        const runningNow = btnT.indexOf("متوقف") >= 0 || btnT.indexOf("⏹") >= 0;
        if (job.running && !runningNow && job.log && log.length <= job.log.length + 5) {{
          return;
        }}
        if (job.log && job.log.length > log.length + 50) return;
        job.sid = sid;
        job.log = (job.log && job.log.length > log.length) ? job.log : log;
        job.ts = Date.now();
        if (btnT) {{
          job.btn = btnT;
          job.running = runningNow || !!job.running;
        }}
        localStorage.setItem(JOB, JSON.stringify(job));
        if (sid) localStorage.setItem("manga_sid", sid);
      }} catch (e) {{}}
    }};
    const obs = new MutationObserver(() => saveFromDom());
    const startObs = () => {{
      const root = document.getElementById("manga_live_log") || document.body;
      if (root) obs.observe(root, {{ childList: true, subtree: true, characterData: true }});
    }};
    startObs();
    setTimeout(startObs, 800);
    setInterval(saveFromDom, 2000);
  }} catch (e) {{}}

  const syncSidHolder = () => {{
    try {{
      let job = {{}};
      try {{ job = JSON.parse(localStorage.getItem(JOB) || "{{}}"); }} catch (e) {{ job = {{}}; }}
      const sid = (localStorage.getItem("manga_sid") || job.sid || "").trim();
      if (!sid) return;
      const el = document.querySelector("#manga_sid_holder textarea")
        || document.querySelector("#manga_sid_holder input")
        || document.querySelector('[id*="manga_sid_holder"] textarea')
        || document.querySelector('[id*="manga_sid_holder"] input');
      if (!el) return;
      if ((el.value || "").trim() === sid) return;
      setVal(el, sid);
    }} catch (e) {{}}
  }};
  syncSidHolder();
  setInterval(syncSidHolder, 1000);
  [200, 500, 1000, 2000, 4000].forEach((t) => setTimeout(syncSidHolder, t));

  try {{
    const attachFollow = () => {{
      const ta = findLogEl();
      if (!ta || ta._mangaFollowBound) return;
      ta._mangaFollowBound = true;
      ta._mangaFollow = true;
      ta._mangaLogLen = (ta.value || "").length;
      const atBottom = () => {{
        try {{ return ta.scrollTop + ta.clientHeight >= ta.scrollHeight - 28; }}
        catch (e) {{ return true; }}
      }};
      ta.addEventListener("scroll", () => {{ ta._mangaFollow = atBottom(); }}, {{passive: true}});
      ta.addEventListener("wheel", () => {{ ta._mangaFollow = atBottom(); }}, {{passive: true}});
      ta.addEventListener("touchmove", () => {{ ta._mangaFollow = false; }}, {{passive: true}});
      ta.addEventListener("keydown", (ev) => {{
        const k = ev.key || "";
        if (k === "ArrowUp" || k === "PageUp" || k === "Home") ta._mangaFollow = false;
        if (k === "ArrowDown" || k === "PageDown" || k === "End") ta._mangaFollow = true;
      }});
      setInterval(() => {{
        const len = (ta.value || "").length;
        if (len !== ta._mangaLogLen) {{
          const reset = len < ta._mangaLogLen;
          ta._mangaLogLen = len;
          if (ta._mangaFollow || reset) {{
            try {{ ta.scrollTop = ta.scrollHeight; }} catch (e) {{}}
          }}
        }}
      }}, 300);
    }};
    attachFollow();
    [1200, 4000].forEach((t) => setTimeout(attachFollow, t));
  }} catch (e) {{}}

  try {{
    const attachEye = () => {{
      const kb = document.getElementById("manga_api_keys");
      if (!kb) return;
      const inp = kb.querySelector("input");
      if (!inp || inp.dataset.mangaEyeBound) return;
      inp.dataset.mangaEyeBound = "1";
      const host = inp.closest(".input-container")
        || inp.closest(".wrap") || inp.parentElement;
      if (!host) return;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "manga-eye";
      btn.setAttribute("aria-label", "نمایش / مخفی کردن کلید");
      btn.title = "نمایش / مخفی کردن کلید";
      const paint = () => {{
        inp.type = window.__mangaKeysShown ? "text" : "password";
        btn.textContent = window.__mangaKeysShown ? "🙈" : "👁";
        btn.classList.toggle("on", !!window.__mangaKeysShown);
      }};
      btn.addEventListener("click", (ev) => {{
        ev.preventDefault();
        ev.stopPropagation();
        window.__mangaKeysShown = !window.__mangaKeysShown;
        paint();
      }});
      host.appendChild(btn);
      paint();
    }};
    attachEye();
    [300, 800, 1500, 3000, 5000].forEach((t) => setTimeout(attachEye, t));
    if (!window.__mangaEyeObs) {{
      let pend = false;
      window.__mangaEyeObs = new MutationObserver(() => {{
        if (pend) return;
        pend = true;
        requestAnimationFrame(() => {{ pend = false; attachEye(); }});
      }});
      try {{
        window.__mangaEyeObs.observe(document.body,
          {{ childList: true, subtree: true }});
      }} catch (e) {{}}
    }}
  }} catch (e) {{}}

  try {{
    const attachTokTip = () => {{
      const root = document.getElementById("manga_token_btn");
      const el = root ? (root.tagName === "BUTTON" ? root
        : root.querySelector("button")) : null;
      if (el && !el.dataset.mangaTokTip) {{
        el.dataset.mangaTokTip = "1";
        el.title = "دریافت توکن — سایتِ همان انتخاب (Gemini → aistudio؛ سرویسِ دلخواه → سایتِ خودش)";
        el.setAttribute("aria-label", el.title);
      }}
    }};
    attachTokTip();
    [300, 1500, 5000].forEach((t) => setTimeout(attachTokTip, t));
  }} catch (e) {{}}

  return [];
}}
"""

        def _do_test_key(provider_v, api_keys_v, model_v, api_base_v,
                         models_v=None):
            if not str(api_keys_v or "").strip():
                api_keys_v = os.environ.get("GEMINI_API_KEY", "").strip()
            try:
                from manga import test_api_keys, format_key_test_text
            except Exception as e:
                return gr.update(value=f"خطا در تست: {e}", visible=True)
            prov = str(provider_v or "").strip()
            if prov == "auto":
                lines = []
                _cands = [("Gemini", "gemini", "", str(api_keys_v or ""),
                           _model_str(model_v))]
                for m in (models_v or []):
                    if isinstance(m, dict) and str(m.get("name") or "").strip():
                        _cands.append((str(m.get("name")).strip(), "custom",
                                       str(m.get("api_base") or ""),
                                       str(m.get("api_key") or ""),
                                       str(m.get("model") or "")))
                for _lb, _cp, _cb, _ck, _cm in _cands:
                    try:
                        _r = test_api_keys(_ck, _cp, _cb, model=_cm)
                        lines.append(f"—— {_lb} ——\n" + format_key_test_text(_r))
                    except Exception as _e:
                        lines.append(f"—— {_lb} ——\nخطا: {_e}")
                return gr.update(value="\n\n".join(lines), visible=True)
            _nm = resolve_ai_named(models_v, prov,
                                   str(api_keys_v or ""), _model_str(model_v))
            if _nm is not None:
                prov, api_base_v, api_keys_v, model_v = _nm
            try:
                res = test_api_keys(api_keys_v or "", prov or "gemini",
                                    api_base_v or "", model=model_v or "")
                txt = format_key_test_text(res)
                return gr.update(value=txt, visible=True)
            except Exception as e:
                return gr.update(value=f"خطا در تست: {e}", visible=True)

        def run_translation(sid, sid_box_v, inp_path_v, upload, provider_v, api_keys_v, model_v,
                            ocr_lang_v,
                            out_fmt_v, quality_v, font_up,
                            workers_v, bubbles_v, timeout_v,
                            batchw_v, maxre_v, reqdelay_v, temp_v, top_p_v, readord_v,
                            clean_method_v, device_v, two_pass_v,
                            fake_test_v, clean_only_v, web_debug_v, prompt_mode_v, prompt_body_v,
                            api_base_v,
                            thinking_v, safety_v, max_tokens_v, max_tokens_custom_v,
                            models_v,
                            glossary_text_v, story_brief_v,
                            *tone_args):
            _t_prep = time.time()
            if not str(api_keys_v or "").strip():
                api_keys_v = os.environ.get("GEMINI_API_KEY", "").strip()
            ocr_lang_v = _ocr_lang_norm(ocr_lang_v)
            sid = (sid or sid_box_v or "").strip()
            sid = _find_active_sid(sid) or sid
            if not sid:
                sid = _new_sid()
            try:
                _web_touch(sid)
            except Exception:
                pass

            job = _get_job(sid)
            n_slots = len(tone_slots)
            tone_files = list(tone_args[:n_slots])
            tone_enables = list(tone_args[n_slots:n_slots * 2])

            def _pack(btn, log, dl=None, view=None, group=None, viewer=None, html="",
                      dl_dbg=None, view_dbg=None, dbg_row=None, html_dbg="",
                      modal=None):
                return (
                    sid,
                    gr.update(value=sid),
                    gr.update(value=btn),
                    gr.update(value=log),
                    dl if dl is not None else gr.update(),
                    gr.update(visible=False),
                    group if group is not None else gr.update(),
                    viewer if viewer is not None else gr.update(),
                    html if html is not None else gr.update(),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(),
                    modal if modal is not None else gr.update(visible=False),
                )

            with job["lock"]:
                running_now = _job_running(job)
            if running_now:
                _kill_job(sid)
                msg = job.get("log") or "⏹ ترجمه متوقف شد.\n(پروسه manga.py بسته شد)"
                return _pack("🚀  شروع ترجمه", msg)

            up_files = upload if isinstance(upload, (list, tuple)) else (
                [upload] if upload else [])
            up_files = [u for u in up_files if u and os.path.isfile(u)]
            src = (inp_path_v or "").strip()
            multi_base = ""
            _batch_no_stitch = False
            if up_files:
                if len(up_files) == 1:
                    try:
                        _sdir1 = os.path.join(OUT_DIR, sid[:12],
                                              "input_batch", "single")
                        os.makedirs(_sdir1, exist_ok=True)
                        _dst1 = os.path.join(
                            _sdir1, os.path.basename(up_files[0]))
                        shutil.copyfile(up_files[0], _dst1)
                        src = _dst1
                    except Exception:
                        src = up_files[0]
                else:
                    batch_dir = os.path.join(OUT_DIR, sid[:12], "input_batch")
                    shutil.rmtree(batch_dir, ignore_errors=True)
                    os.makedirs(batch_dir, exist_ok=True)
                    for bi, bf in enumerate(sorted(up_files, key=natural_key), 1):
                        ext_b = os.path.splitext(bf)[1].lower() or ".bin"
                        try:
                            shutil.copyfile(bf, os.path.join(
                                batch_dir, f"file_{bi:03d}{ext_b}"))
                        except Exception:
                            shutil.copyfile(bf, os.path.join(
                                batch_dir, f"file_{bi:03d}" + ext_b.replace(".", "_")))
                    _bf_sorted = sorted(os.listdir(batch_dir))
                    src = ",".join(
                        os.path.join(batch_dir, _bn) for _bn in _bf_sorted)
                    _batch_no_stitch = True
                    _mb = smart_output_base(up_files[0]) or "batch"
                    multi_base = re.sub(r'[\\/:*?"<>|]+', "_", _mb)[:60] \
                        + f"_{len(up_files)}files"

            if "data:image/" in src:
                try:
                    src = _stage_data_urls(
                        src, os.path.join(OUT_DIR, sid[:12], "input_b64"))
                except Exception:
                    pass

            if not src:
                return _pack("🚀  شروع ترجمه",
                             "❌ ورودی خالی است — فایل آپلود کنید یا URL بدهید.")

            try:
                if any(not os.path.isfile(os.path.join(FONT_DIR, _fb[1]))
                       for _fb in FONT_BUNDLES):
                    download_fonts(log=lambda *_a: None)
            except Exception:
                pass

            font_v = font_up or find_font()
            if not font_v or not os.path.isfile(font_v):
                return _pack("🚀  شروع ترجمه",
                             "❌ فونت فارسی روی سرور نیست — یک .ttf آپلود کنید.")

            prov_s = str(provider_v or "").strip()
            _models_now = [m for m in (models_v or [])
                           if isinstance(m, dict)
                           and str(m.get("name") or "").strip()]
            _auto_log_lines = []
            _named = resolve_ai_named(_models_now, prov_s,
                                      str(api_keys_v or ""), _model_str(model_v))
            if _named is not None:
                prov_s, api_base_v, api_keys_v, model_v = _named
                provider_v = prov_s
                _auto_log_lines.append(
                    f"🎯 مدلِ انتخابیِ شما از «لیست مدل‌ها» استفاده میشود "
                    f"(provider={prov_s}، model={str(model_v or '')[:40]}) — فقط همین.")
            elif prov_s == "auto":
                _ap, _ab, _ak, _am, _auto_log_lines = resolve_ai_auto(
                    _models_now, str(api_keys_v or ""), _model_str(model_v))
                if not _ap:
                    return _pack(
                        "🚀  شروع ترجمه",
                        "❌ حالتِ auto: هیچ مدلِ در دسترسی نبود:\n"
                        + "\n".join(_auto_log_lines)
                        + "\n   یک کلیدِ Gemini وارد کنید یا مدلِ سفارشیِ خود را "
                          "به «لیست مدل‌ها» اضافه کنید.")
                prov_s, api_base_v, api_keys_v, model_v = _ap, _ab, _ak, _am
                provider_v = prov_s
            elif prov_s and prov_s not in ("gemini", "custom"):
                prov_s, provider_v = "gemini", "gemini"
            if prov_s == "custom":
                _ab = normalize_api_base(str(api_base_v or ""))
                if not _ab:
                    return _pack("🚀  شروع ترجمه",
                                 "❌ provider «custom» به دامنهٔ API معتبر نیاز دارد.\n"
                                 "   مثال: https://api.example.com/v1\n"
                                 "   (https:// اگر جا افتاده باشد خودکار اضافه می‌شود.)")
                if not _model_str(model_v).strip():
                    return _pack("🚀  شروع ترجمه",
                                 "❌ provider «custom» به نام مدل نیاز دارد (مثال: gpt-4o-mini).")
                api_base_v = _ab

            out_fmt_v = str(out_fmt_v or "PDF")
            if out_fmt_v not in ("PDF", "ZIP", "HTML", "PSD"):
                out_fmt_v = "PDF"
            ext = {"PDF": ".pdf", "ZIP": ".zip", "HTML": ".html",
                   "PSD": ".psd"}[out_fmt_v]
            base = multi_base or smart_output_base(str(src))
            user_out_dir = os.path.join(OUT_DIR, sid[:12])
            os.makedirs(user_out_dir, exist_ok=True)
            _prev_src = ""
            with job["lock"]:
                _prev_src = str(job.get("src") or "")
            if _web_host():
                if _prev_src and _prev_src != str(src):
                    try:
                        for _n in os.listdir(user_out_dir):
                            if _n == "input_batch":
                                continue
                            _p = os.path.join(user_out_dir, _n)
                            if os.path.isdir(_p):
                                shutil.rmtree(_p, ignore_errors=True)
                            else:
                                try:
                                    os.remove(_p)
                                except Exception:
                                    pass
                    except Exception:
                        pass
                else:
                    try:
                        for _n in os.listdir(user_out_dir):
                            _p = os.path.join(user_out_dir, _n)
                            if os.path.isfile(_p) and _n.lower().endswith(
                                    (".pdf", ".zip", ".html", ".psd")):
                                try:
                                    os.remove(_p)
                                except Exception:
                                    pass
                    except Exception:
                        pass
            out_v = os.path.join(user_out_dir, base + ext)

            try:
                _run_sids = set()
                for _jsid, _jb in list(live_jobs.items()):
                    try:
                        if _job_running(_jb):
                            _run_sids.add(str(_jsid)[:12])
                    except Exception:
                        pass
                for _sn in os.listdir(OUT_DIR):
                    _sd = os.path.join(OUT_DIR, _sn)
                    if not os.path.isdir(_sd) or _sn == sid[:12]:
                        continue
                    if _sn in _run_sids:
                        continue
                    for _cn in os.listdir(_sd):
                        if not _cn.endswith(".cache"):
                            continue
                        _cp = os.path.join(_sd, _cn)
                        try:
                            if (time.time() - os.path.getmtime(_cp)) < 900:
                                continue
                        except Exception:
                            pass
                        print(f"[*] GC کش: {_sn}/{_cn} (سشن غیرفعال)")
                        shutil.rmtree(_cp, ignore_errors=True)
            except Exception:
                pass

            _retranslate = False
            if not clean_only_v:
                _instr_sig = str(prompt_body_v or "").strip()
                if _instr_sig and not is_custom_instruction(_instr_sig):
                    _instr_sig = ""
                _mt_mode_q = str(max_tokens_v or "auto").strip().lower()
                if _mt_mode_q not in ("auto", "8192", "16384", "32768",
                                      "65536", "custom"):
                    _mt_mode_q = "auto"
                if _mt_mode_q == "custom":
                    try:
                        _mtc_q = int(max_tokens_custom_v or 4096)
                    except Exception:
                        _mtc_q = 4096
                    _mt_eff_q = max(1024, _mtc_q)
                elif _mt_mode_q == "auto":
                    _mt_eff_q = None
                else:
                    _mt_eff_q = int(_mt_mode_q)
                _sig_cur = _trans_sig_of(
                    prov_s, _model_str(model_v), str(api_base_v or ""),
                    sanitize_prompt_mode(prompt_mode_v), _instr_sig,
                    bool(fake_test_v),
                    (temp_v if temp_v not in (None, "") else 0.7),
                    (top_p_v if top_p_v not in (None, "") else 0.9),
                    bool(thinking_v if thinking_v is not None else True),
                    bool(safety_v),
                    _mt_eff_q,
                    brief=bool(story_brief_v),
                    glossary_sig=_glossary_text_sig(glossary_text_v))
                _cache_dir_q = _cache_dir_for(out_v)
                _sig_prev = ""
                _fake_prev = None
                try:
                    with open(os.path.join(_cache_dir_q, "state.json"),
                              encoding="utf-8") as _fh:
                        _st_j = json.load(_fh) or {}
                    _sig_prev = str(_st_j.get("trans_sig") or "")
                    _fake_prev = _st_j.get("fake")
                except Exception:
                    pass
                _has_progress = False
                try:
                    _has_progress = (
                        os.path.isfile(os.path.join(_cache_dir_q, "trans.json"))
                        or any(_fn.endswith(".json") for _fn in os.listdir(
                            os.path.join(_cache_dir_q, "extract"))
                            if os.path.isfile(os.path.join(
                                _cache_dir_q, "extract", _fn)))
                        or any(
                            (_n == "out" or _n.startswith("out_"))
                            and os.listdir(os.path.join(_cache_dir_q, _n))
                            for _n in os.listdir(_cache_dir_q)))
                except Exception:
                    _has_progress = False
                _ask_mode = _ASK_ANSWER.pop(sid, None) or ""
                if (_has_progress and _sig_prev and _sig_cur
                        and _sig_prev != _sig_cur):
                    if (_fake_prev is not None
                            and bool(_fake_prev) != bool(fake_test_v)):
                        _retranslate = True
                    elif _ask_mode == "fresh":
                        _retranslate = True
                    elif _ask_mode != "continue":
                        return _pack(
                            "🚀  شروع ترجمه",
                            TX("app.ask_log",
                               "⏸ مدل یا پرامپتِ ترجمه با دفعهٔ قبل فرق دارد — "
                               "اول انتخاب کن: همین‌جا ادامه بده یا از اول "
                               "ترجمه کن؟"),
                            modal=gr.update(visible=True))

            cmd = [sys.executable, "-u", MANGA_PY, "-i", str(src), "-o", out_v,
                   "--font", font_v,
                   "--provider", provider_v,
                   "--workers", str(int(workers_v)),
                   "--bubbles-per-request", str(int(bubbles_v)),
                   "--api-timeout", str(int(timeout_v)),
                   "--quality", str(int(quality_v)),
                   "--batch-workers", str(int(batchw_v)),
                   "--max-retries", str(int(maxre_v)),
                   "--request-delay", str(float(reqdelay_v)),
                   "--temperature", str(float(temp_v if temp_v not in (None, "") else 0.7)),
                   "--top-p", str(float(top_p_v if top_p_v not in (None, "") else 0.9)),
                   "--reading-order", str(readord_v)]
            if prov_s == "custom" and str(api_base_v or "").strip():
                cmd += ["--api-base", str(api_base_v).strip()]
            cmd += font_args()
            active_tones = ["normal"]
            for si, slot in enumerate(tone_slots):
                fp = tone_files[si] if si < len(tone_files) else None
                en = tone_enables[si] if si < len(tone_enables) else True
                if not en:
                    continue
                if not fp:
                    bundle = next((b for b in FONT_BUNDLES if b[0] == slot), None)
                    if bundle:
                        srv = os.path.join(FONT_DIR, bundle[1])
                        if os.path.isfile(srv):
                            fp = srv
                if fp and os.path.isfile(fp):
                    _cli = {"free_text": "free"}
                    cmd += ["--font-" + _cli.get(slot, slot.replace("_", "-")), fp]
                    if slot not in active_tones:
                        active_tones.append(slot)
            if active_tones:
                cmd += ["--active-tones", ",".join(active_tones)]
            klist = [k.strip() for k in (api_keys_v or "").replace(";", ",").split(",") if k.strip()]
            if klist:
                cmd += ["--api-key", ",".join(klist)]
            if ocr_lang_v and str(ocr_lang_v).strip() and str(ocr_lang_v).strip() != "en":
                cmd += ["--ocr-lang"] + [p for p in str(ocr_lang_v).split() if p]
            if model_v and _model_str(model_v):
                cmd += ["--model", _model_str(model_v)]
            _cm_v = str(clean_method_v or "lama-manga").strip()
            if _cm_v not in ("lama-manga", "lama-big", "opencv"):
                _cm_v = "lama-manga"
            cmd += ["--clean-method", _cm_v]
            _dv_v = str(device_v or "auto").strip().lower()
            if _dv_v not in ("auto", "cpu", "gpu"):
                _dv_v = "auto"
            if _dv_v != "auto":
                cmd += ["--device", _dv_v]
            if _batch_no_stitch:
                cmd += ["--stitch-max-height", "0"]
            if not two_pass_v:
                cmd += ["--no-two-pass-ocr"]
            if fake_test_v:
                cmd += ["--fake-translate"]
            if clean_only_v:
                cmd += ["--clean-only"]
            if _retranslate:
                cmd += ["--translate-retranslate"]
            if web_debug_v:
                cmd += ["--debug"]
            cmd += [("--deep-thinking"
                     if (thinking_v is None or bool(thinking_v))
                     else "--no-deep-thinking")]
            if safety_v:
                cmd += ["--safety-settings"]
            _mt_mode_c = str(max_tokens_v or "auto").strip().lower()
            if _mt_mode_c not in ("auto", "8192", "16384", "32768",
                                  "65536", "custom"):
                _mt_mode_c = "auto"
            cmd += ["--max-tokens", _mt_mode_c]
            if _mt_mode_c == "custom":
                try:
                    _mtc_c = int(max_tokens_custom_v or 4096)
                except Exception:
                    _mtc_c = 4096
                cmd += ["--max-tokens-custom", str(max(1024, _mtc_c))]
            instr_text = str(prompt_body_v or "").strip()
            if is_custom_instruction(instr_text):
                instr_path = os.path.join(user_out_dir, "instruction_user.txt")
                with open(instr_path, "w", encoding="utf-8") as _inf:
                    _inf.write(instr_text + "\n")
                cmd += ["--instruction", instr_path]
            cmd += ["--prompt-mode", sanitize_prompt_mode(prompt_mode_v)]
            _glos_txt = str(glossary_text_v or "").strip()
            try:
                _glos_dir = os.path.join(WORK_DIR, "glossary")
                os.makedirs(_glos_dir, exist_ok=True)
                _glos_path = os.path.join(_glos_dir, "glossary_user.txt")
                _learned = os.path.join(_glos_dir, "glossary.json")
                _merged: dict = {}
                try:
                    if os.path.isfile(_learned):
                        with open(_learned, encoding="utf-8") as _lf:
                            _ld = json.load(_lf) or {}
                        for _k, _v in _ld.items():
                            _k2, _v2 = str(_k).strip(), str(_v).strip()
                            if _k2 and _v2:
                                _merged[_k2] = _v2
                except Exception:
                    _merged = {}
                for _ln in _glos_txt.splitlines():
                    _ln = _ln.strip()
                    if not _ln or _ln.startswith("#"):
                        continue
                    for _sep in ("=", ":", "\t"):
                        if _sep in _ln:
                            _ks, _vs = _ln.split(_sep, 1)
                            _ks, _vs = _ks.strip(), _vs.strip()
                            if _ks and _vs:
                                _merged[_ks] = _vs
                            break
                if _merged:
                    with open(_glos_path, "w", encoding="utf-8") as _gf:
                        for _k in sorted(_merged):
                            _gf.write(f"{_k}={_merged[_k]}\n")
                    cmd += ["--glossary", _glos_path]
                    print(f"[*] واژه‌نامه: {len(_merged)} معادل فعال")
                else:
                    try:
                        if os.path.isfile(_glos_path):
                            os.remove(_glos_path)
                    except Exception:
                        pass
            except Exception as _ge:
                print(f"[!] واژه‌نامه آماده نشد ({_ge})")
            if story_brief_v:
                cmd += ["--brief"]
            t0 = time.time()
            try:
                print(f"[TIME] app-prep={time.time() - _t_prep:.1f}s",
                      flush=True)
            except Exception:
                pass
            with job["lock"]:
                _prev_src = str(job.get("src") or "").strip()
                _prev_sig = str(job.get("src_sig") or "")
                _sig = _src_signature(src)
                _same_src = (bool(_prev_src)
                             and _prev_src == str(src or "").strip()
                             and _prev_sig == _sig)
                _keep_log = _same_src and bool((job.get("log") or "").strip()
                                               or (job.get("buf") or []))
                _old_log = ""
                _old_buf = []
                if _keep_log:
                    _old_log = str(job.get("log") or "").rstrip() + "\n"
                    _old_buf = list(job.get("buf") or [])
                else:
                    try:
                        _lf = os.path.join(SESS_DIR, f"{sid}.log")
                        if os.path.isfile(_lf):
                            os.remove(_lf)
                    except Exception:
                        pass
                job["result_visible"] = False
                job["download_path"] = None
                job["download_debug"] = None
                job["html_state"] = ""
                job["html_debug"] = ""
                job["reader_path"] = None
                job["reader_debug_path"] = None
                job["buf"] = _old_buf
                job["t0"] = t0
                job["returncode"] = None
                job["done_event"] = False
                job["out_v"] = out_v
                job["src"] = src
                job["src_sig"] = _sig
                job["running"] = True
                job["log"] = _old_log + ("\n".join(_auto_log_lines) + "\n"
                              if _auto_log_lines else "") + "▶ در حال شروع…"
                job["ts"] = time.time()
            _append_job_logfile(
                sid, f"═══ Manga-AutoTranslate v{APP_VER} — شروعِ کارِ جدید — "
                     f"{time.strftime('%Y-%m-%d %H:%M:%S')} ═══")
            if _auto_log_lines:
                _append_job_logfile(sid, "\n".join(_auto_log_lines))

            live_dir = os.path.join(user_out_dir, "live")
            shutil.rmtree(live_dir, ignore_errors=True)
            os.makedirs(live_dir, exist_ok=True)
            _dbg_on = bool(web_debug_v)
            live_dbg_dir = ""
            if _dbg_on:
                live_dbg_dir = os.path.join(user_out_dir, "live_debug")
                shutil.rmtree(live_dbg_dir, ignore_errors=True)
                os.makedirs(live_dbg_dir, exist_ok=True)
            _live_run_tok = str(int(time.time() * 1000))
            try:
                _write_live_reader(live_dir, dbg_dir=live_dbg_dir,
                                   run=_live_run_tok)
            except Exception as _e:
                print(f"[!] نوشتن live_reader.html ناموفق: {_e}")
            with job["lock"]:
                job["live_dir"] = live_dir
                job["live_dbg_dir"] = live_dbg_dir or None
                job["live_files"] = []
                job["live_run"] = _live_run_tok
                _old_slicer = job.get("live_slicer")
            if _old_slicer:
                try:
                    _old_slicer["stop"] = True
                except Exception:
                    pass
            try:
                _start_live_slicer(live_dir, job)
            except Exception as _e:
                print(f"[!] برشکارِ وبِ live ناموفق: {_e}")

            _env = os.environ.copy()
            _env["PYTHONUNBUFFERED"] = "1"
            _env["PYTHONIOENCODING"] = "utf-8"
            _env.pop("MANGA_SPEED_TEST", None)
            _env["MANGA_LIVE_DIR"] = live_dir
            if _dbg_on:
                _env["MANGA_LIVE_DEBUG_DIR"] = live_dbg_dir
            try:
                proc = subprocess.Popen(
                    cmd, cwd=HERE, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    env=_env,
                    bufsize=0,
                    start_new_session=True,
                )
            except Exception as e:
                with job["lock"]:
                    job["running"] = False
                    job["log"] = f"❌ اجرا نشد: {e}"
                _append_job_logfile(sid, f"❌ اجرا نشد: {e}")
                return _pack("🚀  شروع ترجمه", job["log"])

            with job["lock"]:
                job["proc"] = proc
                job["running"] = True
                job["ts"] = time.time()
                job["log"] = _old_log + (("\n".join(_auto_log_lines) + "\n")
                              if _auto_log_lines else "") \
                    + "▶ شروع شد — لاگ زنده به‌زودی…\n(اگر صفحه را رفرش کنید لاگ از همین جلسه برمی‌گردد)"
            _persist_job_meta(sid)
            _start_job_reader(sid, proc, t0)

            return _pack(
                "⏹  متوقف ترجمه", job["log"],
                dl=gr.update(visible=False),
                view=gr.update(visible=False),
                group=gr.update(visible=False),
                dl_dbg=gr.update(visible=False),
                view_dbg=gr.update(visible=False),
                dbg_row=gr.update(visible=False),
            )

        def _on_provider_change(p, models, bank, cur_base, cur_key, cur_model):
            bank = dict(bank or {})
            v = str(p or "").strip()
            on_auto = (v == "auto")
            is_custom = (v == "custom")
            mine = v in _cm_names(models)
            last = str(bank.get("_last") or "").strip()
            if last in ("gemini", "custom") and last != v:
                bank[last] = {"base": str(cur_base or ""),
                              "key": str(cur_key or ""),
                              "model": _model_str(cur_model)}
            bank["_last"] = v
            saved = bank.get(v) if v in ("gemini", "custom") else {}
            saved = saved if isinstance(saved, dict) else {}
            nb = str(saved.get("base") or "")
            nk = str(saved.get("key") or "")
            nm = _model_str(saved.get("model"))
            if not is_custom:
                nb = ""
            if on_auto or mine:
                nk, nm = "", ""
            info = _cm_info_html(models, v) if mine else ""
            row_vis = not on_auto and not mine
            if v == "gemini":
                mdl_upd = gr.update(visible=True,
                                    value=(nm or _gemini_default_models_str()),
                                    label="مدل (ها)")
            else:
                mdl_upd = gr.update(visible=row_vis, value=nm,
                                    label="مدل (ها)")
            key_upd = gr.update(visible=row_vis, value=nk)
            if not nk and str(cur_key or "").strip():
                key_upd = gr.update(visible=row_vis)
            return (gr.update(visible=is_custom, value=nb),
                    gr.update(visible=row_vis),
                    key_upd,
                    mdl_upd,
                    gr.update(visible=is_custom),
                    gr.update(visible=is_custom),
                    gr.update(visible=mine, value=info),
                    gr.update(visible=mine),
                    bank,
                    gr.update(visible=mine),
                    gr.update(visible=False),
                    gr.update(visible=(v == "gemini")))

        def _cm_edit_start(prov, models):
            nm = str(prov or "").strip()
            m = next((x for x in (models or [])
                      if str(x.get("name") or "").strip() == nm), None)
            if not m:
                return (gr.update(),) * 9
            return (gr.update(visible=True,
                              value=str(m.get("api_base") or "")),
                    gr.update(visible=True),
                    gr.update(visible=True,
                              value=str(m.get("api_key") or "")),
                    gr.update(visible=True,
                              value=str(m.get("model") or ""),
                              label="مدل — شناسهٔ مدل را دستی بنویس | خالی = پیش‌فرض"),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=True),
                    gr.update(visible=False),
                    gr.update(visible=False))

        def _cm_save_edits(prov, models, base, key, mdl):
            nm = str(prov or "").strip()
            new_models = [dict(x) for x in (models or [])]
            idx = next((i for i, x in enumerate(new_models)
                        if str(x.get("name") or "").strip() == nm), -1)
            if idx < 0 or not nm:
                return (gr.update(),) * 15
            entry = {"name": nm,
                     "api_base": str(base or "").strip(),
                     "api_key": str(key or "").strip(),
                     "model": _model_str(mdl)}
            new_models[idx] = entry
            _link = entry["api_base"] or "Gemini رسمی (بدونِ دامنهٔ سفارشی)"
            _mdl = f" — مدلِ هوش: {entry['model']}" if entry["model"] else ""
            msg = (f"✅ ویرایشِ «{nm}» ذخیره شد — لینک: {_link}{_mdl}"
                   + (" (روی دیسک)" if not _web_host()
                      else " (در مرورگرِ شما)"))
            return (*_cm_pack(new_models, nm),
                    gr.update(visible=True,
                              value=_cm_info_html(new_models, nm)),
                    gr.update(visible=False),
                    gr.update(visible=True),
                    gr.update(visible=False, value=""),
                    gr.update(visible=False),
                    gr.update(visible=False, value=""),
                    gr.update(visible=False, value=""),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(value=msg, visible=True),
                    gr.update(visible=False))

        try:
            provider.change(
                _on_provider_change,
                inputs=[provider, custom_models_state, fields_bank,
                        api_base, api_keys, model],
                outputs=[api_base, api_row, api_keys, model,
                         add_model_btn, cm_hint_md, cm_info_md,
                         cm_del_btn, fields_bank,
                         cm_edit_btn, cm_save_btn, model_ref_btn],
                api_name="toggle_custom_base",
            )
        except Exception:
            pass
        try:
            provider.change(
                fn=None,
                inputs=[provider],
                outputs=None,
                js="""(p) => {
  try {
    const b = document.getElementById('manga_model_ref');
    if (b) b.style.display = (String(p || '').trim() === 'gemini') ? '' : 'none';
  } catch (e) {}
}""",
            )
        except Exception:
            pass

        try:
            mt_ibtn.click(
                fn=None,
                inputs=None,
                outputs=None,
                queue=False,
                js="""() => {
  try {
    let fieldText = '';
    try {
      const el = document.querySelector('#manga_inp_path textarea')
              || document.querySelector('[id*="manga_inp_path"] textarea')
              || document.querySelector('#manga_inp_path input');
      if (el) fieldText = String(el.value || '').slice(0, 4000);
    } catch (e) {}
    if (window.pywebview && window.pywebview.api
        && window.pywebview.api.openBrowser) {
      try { window.pywebview.api.openBrowser(fieldText); } catch (e) {}
      return;
    }
    const toUrl = (t) => {
      t = String(t || '').trim();
      if (!t) return 'https://www.google.com';
      if (/^https?:/i.test(t)) return t;
      if (!/\\s/.test(t) &&
          /^[A-Za-z0-9_-]+(\\.[A-Za-z0-9_-]+)+([\\/?#].*)?$/.test(t))
        return 'https://' + t;
      return 'https://www.google.com/search?q=' + encodeURIComponent(t);
    };
    const first = String(fieldText || '').split(/[\\n,]/)[0] || '';
    window.open(toUrl(first), '_blank');
  } catch (e) {
    try { alert(String(e)); } catch (e2) {}
  }
}""",
            )
        except Exception:
            pass

        try:
            token_btn.click(
                fn=None,
                inputs=[provider],
                outputs=None,
                js="""(p) => {
  try {
    const GEM = 'https://aistudio.google.com/docs/api-key';
    const gv = (id) => {
      try {
        const root = document.getElementById(id);
        if (!root) return "";
        const el = root.querySelector("input, textarea") || root;
        return String((el.value || "")).trim();
      } catch (e) { return ""; }
    };
    const norm = (u) => { try { return new URL(u); } catch (e) {
      try { return new URL('https://' + u); } catch (e2) { return null; } } };
    const provInp = (typeof p === 'string' && p.trim())
      ? p.trim() : gv("manga_provider_row");
    let models = [];
    try {
      models = JSON.parse(gv("manga_cm_json") || "[]") || [];
    } catch (e) { models = []; }
    if (!Array.isArray(models) || !models.length) {
      try {
        models = JSON.parse(
          localStorage.getItem("manga_custom_models") || "[]") || [];
      } catch (e) { models = []; }
    }
    if (!Array.isArray(models)) models = [];
    let url = '';
    if (provInp === 'gemini' || provInp === 'auto' || provInp === '') {
      url = GEM;
    } else if (provInp === 'custom') {
      const u = norm(gv("manga_api_base"));
      url = u ? u.origin : GEM;
    } else {
      const m = models.find(
        (x) => x && String(x.name || '').trim() === provInp);
      const b = m ? String(m.api_base || '').trim() : '';
      const u = b ? norm(b) : null;
      url = u ? u.origin : GEM;
    }
    if (url) window.open(url, '_blank', 'noopener');
  } catch (e) {}
}""",
            )
        except Exception:
            pass

        def _refresh_model_list(provider_v, api_keys_v, api_base_v, model_v):
            try:
                from manga import list_provider_models
            except Exception as e:
                raise gr.Error(f"خطا در بارگذاری: {str(e)[:80]}")

            def _merge_models(cur, fetched):
                out = []
                for m in re.split(r"[\s,;\n]+", str(cur or "")):
                    m = m.strip()
                    if m and m not in out:
                        out.append(m)
                for m in (fetched or []):
                    m = str(m or "").strip()
                    if m and m not in out:
                        out.append(m)
                return out
            prov = str(provider_v or "").strip()
            if prov in ("", "auto"):
                raise gr.Error("روی «auto» مدلی وارد نمیشود — یک سرویس انتخاب کنید.")
            _nm = None
            try:
                _nm = resolve_ai_named(custom_models_state.value, prov,
                                       str(api_keys_v or ""),
                                       _model_str(model_v))
            except Exception:
                pass
            if _nm is not None:
                _p, _b, _k, _m = _nm
                prov, api_base_v, api_keys_v = _p, _b, _k
            models, err = list_provider_models(
                prov, str(api_keys_v or ""), str(api_base_v or ""))
            if not models:
                if prov == "gemini":
                    offline = _gemini_offline_models()
                    _why = f" — {str(err or '')[:60]}" if err else ""
                    _merged = _merge_models(model_v, offline)
                    return gr.update(
                        value=_models_join(_merged),
                        label=(f"مدل (ها) — اتصال برقرار نشد{_why}؛ فهرستِ "
                               f"آفلاینِ برنامه به مدل‌هایِ موجودِ شما "
                               f"اضافه شد (مدل‌های شما اول‌اند)"))
                raise gr.Error(err or "مدلی پیدا نشد — کلید/لینک را با «تست کلیدها / لینک» چک کنید.")

            _probe_note = ""
            if prov == "gemini":
                _pm = None
                try:
                    from manga import gemini_style_probe_many as _pm
                except Exception:
                    _pm = None
                if _pm is not None:
                    try:
                        _good, _res = _pm(models, str(api_keys_v or ""))
                    except Exception:
                        _good, _res = [], {}
                    if _good:
                        _n_all = len(models)
                        _bk = [m for m, r in (_res or {}).items()
                               if (r or {}).get("verdict") == "bookish"]
                        _er = [m for m, r in (_res or {}).items()
                               if (r or {}).get("verdict") == "error"]
                        models = _good
                        _probe_note = (f" — سنجشِ زنده: {len(_good)} مدلِ سالم "
                                       f"(محاوره‌ای ✓) از {_n_all}")
                        if _bk or _er:
                            _probe_note += (f"؛ حذف: {len(_bk)} کتابی، "
                                           f"{len(_er)} بی‌پاسخ (پولی/سهمیه)")
                    elif _res:
                        _n_err = sum(1 for r in (_res or {}).values()
                                     if (r or {}).get("verdict") == "error")
                        _n_run = len(_res)
                        if _n_err >= _n_run and _n_run:
                            _probe_note = (" — سنجشِ زندهٔ سبک در همین لحظه "
                                           "جواب نداد (شبکه/سهمیه)؛ فهرستِ خام")
                        else:
                            offline = _gemini_offline_models()
                            _merged = _merge_models(model_v, offline)
                            return gr.update(
                                value=_models_join(_merged),
                                label=(f"مدل (ها) — هیچ مدلی جوابِ سالمِ محاوره‌ای "
                                       f"نداد؛ فهرستِ آفلاینِ برنامه به "
                                       f"مدل‌هایِ موجودِ شما اضافه شد"))
            _merged = _merge_models(model_v, models)
            _kept = len(_merged) - len([m for m in models if m in _merged])
            return gr.update(
                value=_models_join(_merged),
                label=(f"مدل (ها) — {len(models)} مدلِ زنده پیدا شد{_probe_note}؛ "
                       f"مدل‌هایِ خودتان اول ماندند"
                       + (f" (+{_kept})" if _kept else "")
                       + " (چند مدل = فال‌بکِ خودکار)"))

        try:
            model_ref_btn.click(
                _refresh_model_list,
                inputs=[provider, api_keys, api_base, model],
                outputs=[model],
                api_name="refresh_models", show_progress="full")
        except Exception:
            pass

        def _cm_pack(models, prov_cur=None):
            models = list(models or [])
            save_custom_models(models)
            _ch = _ai_choices(models)
            _cur = str(prov_cur if prov_cur is not None else "").strip()
            _val = _cur if _cur in _ch else ("auto" if "auto" in _ch
                                             else "gemini")
            return (models,
                    json.dumps(models, ensure_ascii=False),
                    gr.update(choices=_ch, value=_val),
                    gr.update(visible=_val in _cm_names(models)))

        def _cm_add_box(raw, models, prov_cur):
            try:
                it = json.loads(raw) if raw else {}
            except Exception:
                it = {}
            name = str((it or {}).get("name") or "").strip() \
                if isinstance(it, dict) else ""
            if not name:
                return (*_cm_pack(models, prov_cur), gr.update())
            entry = {"name": name,
                     "api_base": str(it.get("api_base") or "").strip(),
                     "api_key": str(it.get("api_key") or "").strip(),
                     "model": _model_str(it.get("model"))}
            models = [m for m in (models or [])
                      if str(m.get("name") or "") != name]
            models.append(entry)
            _link = entry["api_base"] or "Gemini رسمی (بدونِ دامنهٔ سفارشی)"
            _mdl = f" — مدلِ هوش: {entry['model']}" if entry["model"] else ""
            return (*_cm_pack(models, prov_cur),
                    gr.update(value=(f"✅ مدلِ «{name}» ذخیره شد — لینک: {_link}"
                                     f"{_mdl}"
                                     + (" (روی دیسک)" if not _web_host()
                                        else " (در مرورگرِ شما)")),
                              visible=True))

        def _cm_del_selected(prov, models):
            nm = str(prov or "").strip()
            models = [m for m in (models or [])
                      if str(m.get("name") or "") != nm] if nm \
                else list(models or [])
            return _cm_pack(models, None)

        def _cm_restore(raw, models, prov_cur):
            try:
                data = json.loads(raw) if raw else []
            except Exception:
                data = []
            if not isinstance(data, list) or not data:
                return _cm_pack(models, prov_cur)
            merged = list(models or [])
            for it in data:
                if not isinstance(it, dict):
                    continue
                name = str(it.get("name") or "").strip()
                if not name or any(str(m.get("name") or "") == name
                                   for m in merged):
                    continue
                merged.append({"name": name,
                               "api_base": str(it.get("api_base") or ""),
                               "api_key": str(it.get("api_key") or ""),
                               "model": _model_str(it.get("model"))})
            return _cm_pack(merged, prov_cur)

        _cm_add_js = """
(prov) => {
  try {
    const gv = (id) => {
      try {
        const root = document.getElementById(id);
        if (!root) return "";
        const el = root.querySelector("input, textarea") || root;
        return String((el.value || "")).trim();
      } catch (e) { return ""; }
    };
    const onCustom = String(prov || "").trim() === "custom";
    const base = onCustom ? gv("manga_api_base") : "";
    const key = gv("manga_api_keys");
    const mdl = gv("manga_model");
    if (!base && !mdl && !key) {
      try { alert("اول «مدل» و «کلیدهای API» را پر کنید، بعد «+ افزودن به لیست مدل‌ها» را بزنید."); } catch (e) {}
      return [];
    }
    let nm = "";
    try { nm = String(window.prompt("نامِ این مدل در لیست (خالی = نامِ خودِ مدل):", mdl) || "").trim(); } catch (e) { nm = ""; }
    if (!nm) nm = mdl;
    if (!nm) {
      try { alert("نامِ مدل خالی ماند — اول فیلدِ «مدل» را پر کن یا یک نام بنویس."); } catch (e) {}
      return [];
    }
    let list = [];
    try { list = JSON.parse(localStorage.getItem("manga_custom_models") || "[]") || []; } catch (e) { list = []; }
    if (!Array.isArray(list)) list = [];
    list = list.filter((m) => m && m.name !== nm);
    list.push({ name: nm, api_base: base, api_key: key, model: mdl });
    try { localStorage.setItem("manga_custom_models", JSON.stringify(list)); } catch (e) {}
    try {
      const box = document.getElementById("manga_cm_add_box");
      const el = box ? (box.querySelector("textarea") || box.querySelector("input") || box) : null;
      if (el) {
        const s = JSON.stringify({ name: nm, api_base: base, api_key: key, model: mdl });
        const proto = el.tagName === "TEXTAREA"
          ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
        const desc = proto && Object.getOwnPropertyDescriptor(proto, "value");
        if (desc && desc.set) desc.set.call(el, s); else el.value = s;
        el.dispatchEvent(new Event("input", { bubbles: true }));
        el.dispatchEvent(new Event("change", { bubbles: true }));
      }
    } catch (e) {}
  } catch (e) {}
  return [];
}
"""

        try:
            add_model_btn.click(
                fn=None, inputs=[provider], outputs=None, js=_cm_add_js)
        except Exception:
            pass
        try:
            cm_add_box.change(
                _cm_add_box,
                inputs=[cm_add_box, custom_models_state, provider],
                outputs=[custom_models_state, cm_json_box, provider,
                         cm_del_btn, backup_status],
                api_name="cm_add")
        except Exception:
            pass
        try:
            cm_del_btn.click(
                _cm_del_selected,
                inputs=[provider, custom_models_state],
                outputs=[custom_models_state, cm_json_box, provider,
                         cm_del_btn],
                api_name="cm_del_sel")
        except Exception:
            pass
        try:
            cm_edit_btn.click(
                _cm_edit_start,
                inputs=[provider, custom_models_state],
                outputs=[api_base, api_row, api_keys, model,
                         add_model_btn, cm_edit_btn, cm_save_btn,
                         cm_hint_md, model_ref_btn],
                api_name="cm_edit", show_progress="hidden")
        except Exception:
            pass
        try:
            cm_save_btn.click(
                _cm_save_edits,
                inputs=[provider, custom_models_state, api_base, api_keys,
                        model],
                outputs=[custom_models_state, cm_json_box, provider,
                         cm_del_btn, cm_info_md, cm_save_btn, cm_edit_btn,
                         api_base, api_row, api_keys, model,
                         add_model_btn, cm_hint_md, backup_status,
                         model_ref_btn],
                api_name="cm_save_edits", show_progress="hidden")
        except Exception:
            pass
        try:
            cm_json_box.change(
                fn=None, inputs=[cm_json_box], outputs=[],
                js="""(js) => {
  try {
    if (js && js.trim().charAt(0) === '[')
      localStorage.setItem('manga_custom_models', js);
  } catch (e) {}
  try {
    let list = [];
    try { list = JSON.parse(js || '[]') || []; } catch (e) { list = []; }
    if (!Array.isArray(list)) list = [];
    const names = list.map((m) => String((m && m.name) || '').trim())
                      .filter(Boolean);
    const inp = document.querySelector('#manga_provider_row input, #manga_provider_row select');
    if (inp) {
      const cur = String(inp.value || '').trim();
      const valid = ['auto', 'gemini', 'custom'].concat(names);
      if (cur && valid.indexOf(cur) < 0) {
        const fb = names.length ? 'auto' : 'gemini';
        try {
          inp.focus();
          const d = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype, 'value');
          if (d && d.set) d.set.call(inp, fb); else inp.value = fb;
          inp.dispatchEvent(new Event('input', {bubbles: true}));
          inp.dispatchEvent(new KeyboardEvent('keydown',
            {key: 'Enter', bubbles: true}));
          inp.dispatchEvent(new Event('change', {bubbles: true}));
          inp.blur();
        } catch (e2) {}
      }
    }
  } catch (e) {}
  return [];
}""")
            cm_restore_box.change(
                _cm_restore,
                inputs=[cm_restore_box, custom_models_state, provider],
                outputs=[custom_models_state, cm_json_box, provider,
                         cm_del_btn],
                api_name="cm_restore")
        except Exception:
            pass

        _BACKUP_FIELDS = [
            ("provider", provider), ("api_base", api_base),
            ("api_keys", api_keys), ("model", model),
            ("ocr_lang", ocr_lang), ("out_fmt", out_fmt),
            ("quality", quality), ("workers", workers),
            ("bubbles", bubbles), ("timeout", timeout),
            ("batchw", batchw), ("maxre", maxre),
            ("reqdelay", reqdelay), ("temp", temp), ("top_p", top_p), ("readord", readord),
            ("clean_method", clean_method), ("two_pass", two_pass),
            ("fake_test", fake_test), ("clean_only", clean_only),
            ("web_debug", web_debug), ("prompt_mode", prompt_mode),
            ("prompt_body", prompt_preview_body),
            ("deep_thinking", deep_thinking),
            ("safety_settings", safety_settings),
            ("max_tokens", max_tokens),
            ("max_tokens_custom", max_tokens_custom),
        ]

        def _do_backup(*args):
            try:
                import datetime as _dt
                n = len(_BACKUP_FIELDS)
                settings = {}
                for (k, _), v in zip(_BACKUP_FIELDS, args[:n]):
                    if k == "ocr_lang":
                        v = _ocr_lang_norm(v)
                    settings[k] = (v if isinstance(v, (int, float, bool))
                                   else str(v or ""))
                if "model" in settings:
                    settings["model"] = _model_str(settings.get("model"))
                models = list(args[n] or [])
                payload = {
                    "_type": "manga_autotranslate_backup",
                    "app_ver": APP_VER,
                    "exported_at": _dt.datetime.now().isoformat(timespec="seconds"),
                    "custom_models": models,
                    "settings": settings,
                }
                payload["_dl"] = time.time_ns()
                if _web_host():
                    return (gr.update(visible=False),
                            gr.update(value=("✅ پشتیبان ساخته شد و دانلودش فقط در "
                                             "همین مرورگر شروع شد: "
                                             f"{len(models)} مدل + "
                                             f"{len(settings)} تنظیم.\n"
                                             "🛡 روی میزبانِ اشتراکی هیچ فایلی "
                                             "ذخیره نمیشود و لینکِ این بکاپ "
                                             "در مرورگرِ دیگری کار نمیکند."),
                                      visible=True),
                            json.dumps(payload, ensure_ascii=False, indent=2))
                ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
                path = os.path.join(WORK_DIR, f"manga_backup_{ts}.json")
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
                return (gr.update(value=path, visible=True),
                        gr.update(value=f"✅ پشتیبان ساخته شد و دانلودِ خودکارش "
                                        f"شروع شد: {len(models)} مدل + "
                                        f"{len(settings)} تنظیم."
                                        f"\n(اگر مرورگرتان دانلود را بلاک کرد، "
                                        f"از کارتِ «فایلِ پشتیبان» همین‌جا "
                                        f"دستیش کنید.)",
                                  visible=True),
                        "")
            except Exception as e:
                return (gr.update(),
                        gr.update(value=f"❌ پشتیبان ناموفق: {e}", visible=True),
                        "")

        def _do_import(file_info, models_cur, prov_cur, bank_cur):
            n = len(_BACKUP_FIELDS)
            ups = [gr.update()] * n
            bank_up = gr.update()
            try:
                path = (file_info or "").strip() if isinstance(file_info, str) \
                    else (file_info.get("name") if isinstance(file_info, dict) else "")
                if isinstance(file_info, str):
                    path = file_info
                elif isinstance(file_info, dict):
                    path = file_info.get("name") or ""
                if not path or not os.path.isfile(path):
                    return (*ups, gr.update(), gr.update(), gr.update(),
                            gr.update(), bank_up,
                            gr.update(value="❌ فایل پشتیبان انتخاب نشده.",
                                      visible=True))
                with open(path, encoding="utf-8") as f:
                    payload = json.load(f)
                if not isinstance(payload, dict) \
                        or payload.get("_type") != "manga_autotranslate_backup":
                    return (*ups, gr.update(), gr.update(), gr.update(),
                            gr.update(), bank_up,
                            gr.update(value="❌ این فایلِ پشتیبانِ این اپ نیست.",
                                      visible=True))
                st = payload.get("settings") or {}
                for i, (k, _comp) in enumerate(_BACKUP_FIELDS):
                    if k in st and st[k] is not None:
                        ups[i] = gr.update(value=st[k])
                merged = []
                for it in (payload.get("custom_models") or []):
                    if isinstance(it, dict) and str(it.get("name") or "").strip():
                        merged.append({
                            "name": str(it.get("name") or "").strip(),
                            "api_base": str(it.get("api_base") or "").strip(),
                            "api_key": str(it.get("api_key") or "").strip(),
                            "model": str(it.get("model") or "").strip(),
                        })
                save_custom_models(merged)
                _ch = _ai_choices(merged)
                _imp = str(st.get("provider") or "").strip()
                _old = str(prov_cur or "").strip()
                _newv = _imp if _imp in _ch else (
                    _old if _old in _ch
                    else ("auto" if "auto" in _ch else "gemini"))
                try:
                    _bank = dict(bank_cur or {}) if isinstance(bank_cur, dict) else {}
                except Exception:
                    _bank = {}
                _bank["_last"] = _newv
                if _newv in ("gemini", "custom"):
                    _bank[_newv] = {"base": str(st.get("api_base") or ""),
                                    "key": str(st.get("api_keys") or ""),
                                    "model": _model_str(st.get("model"))}
                bank_up = _bank
                return (*ups, merged,
                        json.dumps(merged, ensure_ascii=False),
                        gr.update(choices=_ch, value=_newv),
                        gr.update(visible=_newv in _cm_names(merged)),
                        bank_up,
                        gr.update(value=f"✅ بازیابیِ کامل شد: {len(merged)} مدل + "
                                        f"{len(st)} تنظیم (از فایلِ بکاپ).",
                                  visible=True))
            except Exception as e:
                return (*ups, gr.update(), gr.update(), gr.update(),
                        gr.update(), bank_up,
                        gr.update(value=f"❌ بازیابی ناموفق: {e}", visible=True))

        try:
            _backup_inputs = [c for _, c in _BACKUP_FIELDS] + [custom_models_state]
            _BK_BLOB_JS = """(v) => {
  try {
    if (!v || typeof v !== "string" || !v.trim()
        || v.trim().charAt(0) !== '{') return [];
    let name = "manga_backup.json";
    try {
      const j = JSON.parse(v);
      const t = String(j.exported_at || "").replace(/[^0-9]/g, "");
      if (t.length >= 14)
        name = "manga_backup_" + t.slice(0, 8) + "_" + t.slice(8, 14) + ".json";
    } catch (e) {}
    const blob = new Blob([v], {type: "application/json"});
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(function () {
      try { URL.revokeObjectURL(url); } catch (e) {}
    }, 5000);
  } catch (e) {}
  return [];
}"""
            backup_btn.click(
                _do_backup, inputs=_backup_inputs,
                outputs=[backup_out, backup_status, backup_json],
                api_name="backup_settings")
            backup_json.change(
                fn=None, inputs=[backup_json], outputs=[],
                js=_BK_BLOB_JS)
            backup_out.change(
                fn=None, inputs=[backup_out], outputs=[],
                js="""(v) => {
  try {
    let url = null, name = "manga_backup.json";
    if (v && typeof v === "object") {
      url = v.url || null;
      name = v.orig_name || name;
    } else if (typeof v === "string" && v) {
      url = v;
    }
    if (url) {
      const a = document.createElement("a");
      a.href = url;
      a.download = name || "manga_backup.json";
      document.body.appendChild(a);
      a.click();
      a.remove();
    }
  } catch (e) {}
  return [];
}""",
            )
            import_file.upload(
                _do_import,
                inputs=[import_file, custom_models_state, provider,
                        fields_bank],
                outputs=[c for _, c in _BACKUP_FIELDS]
                        + [custom_models_state, cm_json_box, provider,
                           cm_del_btn, fields_bank, backup_status],
                api_name="import_settings")
        except Exception:
            pass

        def _prompt_preview_update(mode_v, prov_v, mdl_v):
            try:
                return gr.update(value=resolve_prompt_preview(mode_v, prov_v, mdl_v, None))
            except Exception as e:
                return gr.update(value=f"خطا در پیش‌نمایش پرامپت: {e}")
        try:
            _pp_inputs = [prompt_mode, provider, model]
            for _pp_comp in (prompt_mode, provider, model):
                _pp_comp.change(
                    _prompt_preview_update, inputs=_pp_inputs,
                    outputs=[prompt_preview_body],
                    api_name=f"prompt_preview_{id(_pp_comp)}",
                )
        except Exception:
            pass

        _click_kw = dict(
            inputs=[session_id, sid_box, inp_path, inp_upload, provider, api_keys, model,
                    ocr_lang,
                    out_fmt, quality, font_upload,
                    workers, bubbles, timeout,
                    batchw, maxre, reqdelay, temp, top_p, readord,
                    clean_method, device, two_pass,
                    fake_test, clean_only, web_debug, prompt_mode, prompt_preview_body,
                    api_base,
                    deep_thinking, safety_settings, max_tokens, max_tokens_custom,
                    custom_models_state,
                    glossary_text, story_brief,
                ] + tone_uploads + tone_enables,
            outputs=[session_id, sid_box, run_btn, log_box, dl_btn, btn_view, result_group, viewer_html, html_state,
                     dl_btn_debug, btn_view_debug, debug_row, html_debug_state,
                     ask_group],
            concurrency_limit=8,
        )
        _hide_test_js = """
            () => {
                setTimeout(() => {
                    const el = document.getElementById('manga_test_key_out');
                    if (el) {
                        el.style.display = 'none';
                    }
                }, 60000);
            }
            """
        try:
            _test_evt = test_key_btn.click(
                _do_test_key,
                inputs=[provider, api_keys, model, api_base,
                        custom_models_state],
                outputs=[test_key_out],
            )
            try:
                _test_evt.then(fn=None, inputs=None, outputs=None, js=_hide_test_js)
            except Exception:
                pass
        except Exception:
            pass
        try:
            _ev = None
            try:
                _ev = run_btn.click(run_translation,
                                       show_progress="hidden", **_click_kw)
            except TypeError:
                try:
                    run_btn.click(run_translation,
                                  show_progress=False,
                                  **_click_kw)
                except TypeError:
                    run_btn.click(run_translation, **_click_kw)
        except Exception:
            pass

        def _ask_wrap(_mode):
            def _w(*_a):
                try:
                    _sid_a = ""
                    if len(_a) >= 2:
                        _sid_a = (str(_a[0] or "").strip()
                                  or str(_a[1] or "").strip())
                    if _sid_a:
                        try:
                            _sid_a = _find_active_sid(_sid_a) or _sid_a
                        except Exception:
                            pass
                        _ASK_ANSWER[_sid_a] = _mode
                except Exception:
                    pass
                return run_translation(*_a)
            return _w

        try:
            ask_continue_btn.click(_ask_wrap("continue"), **_click_kw)
        except Exception:
            pass
        try:
            ask_fresh_btn.click(_ask_wrap("fresh"), **_click_kw)
        except Exception:
            pass
        try:
            ask_cancel_btn.click(lambda: gr.update(visible=False),
                                 inputs=None, outputs=[ask_group])
        except Exception:
            pass

        _save_inputs = [
            session_id, sid_box, inp_path, provider, api_keys, model, out_fmt, quality,
            workers, bubbles, timeout, batchw, maxre, reqdelay, temp, top_p, readord,
            clean_method, device, two_pass, fake_test, clean_only,
            deep_thinking, safety_settings, max_tokens, max_tokens_custom,
            glossary_text, story_brief,
        ]

        try:
            run_btn.click(fn=None, inputs=_save_inputs, outputs=[], js=save_form_js)
        except Exception:
            pass
        try:
            
            run_btn.click(
                fn=None,
                inputs=[session_id, sid_box, run_btn, log_box],
                outputs=[],
                js=save_job_js,
            )
        except Exception:
            pass
        try:
            sid_box.change(fn=None, inputs=[session_id, sid_box], outputs=[], js=save_sid_js)
        except Exception:
            pass

        for _comp in (api_keys, provider, model, out_fmt, inp_path, glossary_text):
            try:
                _comp.change(fn=None, inputs=_save_inputs, outputs=[], js=save_form_js)
            except Exception:
                try:
                    _comp.blur(fn=None, inputs=_save_inputs, outputs=[], js=save_form_js)
                except Exception:
                    pass
        for _comp in (quality, workers, bubbles, timeout, batchw, maxre, reqdelay, temp, top_p, readord,
                      clean_method, device, two_pass, fake_test, clean_only,
                      deep_thinking, safety_settings, max_tokens, max_tokens_custom,
                      story_brief):
            try:
                _comp.change(fn=None, inputs=_save_inputs, outputs=[], js=save_form_js)
            except Exception:
                pass

        def _apply_browser_restore(raw_json):
            data = {}
            if raw_json:
                try:
                    data = json.loads(raw_json) if isinstance(raw_json, str) else {}
                except Exception:
                    data = {}

            preferred = (data.get("sid") or "").strip()
            
            if preferred:
                sid = _find_active_sid(preferred) or preferred
            else:
                sid = ""
            if not sid:
                _ks = str(data.get("keys") or "").strip()
                if _ks:
                    _outs = [gr.update()] * 35
                    _outs[12] = gr.update(value=_ks)
                    return tuple(_outs)
                return (gr.update(),) * 35
            job = _get_job(sid)
            meta = _load_job_meta(sid) if sid else {}
            
            client_log = (data.get("_jobLog") or "").strip()
            client_running = bool(data.get("_jobRunning"))

            with job["lock"]:
                mem_log = job.get("log") or ""
                meta_log = meta.get("log") or ""
                default_log = "— لاگ بعد از شروع ترجمه اینجا می‌آید —"

                candidates = []
                if mem_log and mem_log != default_log and not mem_log.startswith("—"):
                    candidates.append(mem_log)
                if meta_log and meta_log != default_log:
                    candidates.append(meta_log)
                if client_log and client_log != default_log and not client_log.startswith("—"):
                    candidates.append(client_log)

                if candidates:
                    
                    job["log"] = max(candidates, key=len)

                if meta.get("download_path") and not job.get("download_path"):
                    job["download_path"] = meta.get("download_path")
                if meta.get("result_visible"):
                    job["result_visible"] = True
                if meta.get("html_state") and not job.get("html_state"):
                    job["html_state"] = meta.get("html_state")
                if meta.get("reader_path") and not job.get("reader_path"):
                    job["reader_path"] = meta.get("reader_path")
                if meta.get("out_v") and not job.get("out_v"):
                    job["out_v"] = meta.get("out_v")
                still_running = _job_running(job)
                if not still_running and (meta.get("running") or client_running):
                    
                    if still_running is False and meta.get("running"):
                        cur = job.get("log") or ""
                        if "اتصال به جلسه قطع شد" not in cur:
                            job["log"] = (cur or client_log or meta_log or "") + (
                                "\n\n⚠ اتصال به پروسه روی سرور قطع است. "
                                "اگر ترجمه تمام شده از خروجی استفاده کنید؛ وگرنه دوباره Start بزنید."
                            )
                log = job.get("log") or client_log or default_log
                vis = bool(job.get("result_visible"))
                dl = job.get("download_path")
                html = job.get("html_state") or ""
            
            if still_running:
                btn = "⏹  متوقف ترجمه"
            else:
                btn = "🚀  شروع ترجمه"

            def u_str(key):
                if key not in data:
                    return gr.update()
                v = data.get(key)
                if v is None:
                    return gr.update()
                if key == "model":
                    _ms = _model_str(v)
                    return gr.update(value=_ms) if _ms else gr.update()
                s = str(v).strip()
                if s.lower() in ("null", "undefined"):
                    return gr.update()
                return gr.update(value=s)

            def u_num(key):
                if key not in data:
                    return gr.update()
                v = data.get(key)
                if v is None or v == "":
                    return gr.update()
                try:
                    return gr.update(value=float(v))
                except Exception:
                    return gr.update()

            def u_bool(key, default=None):
                if key not in data:
                    return gr.update()
                v = data.get(key)
                if v is None:
                    return gr.update()
                return gr.update(value=bool(v))

            def u_cleanm():
                if "cleanm" in data:
                    v = str(data.get("cleanm") or "").strip()
                    if v in ("lama-manga", "lama-big", "opencv"):
                        return gr.update(value=v)
                    if v:
                        return gr.update(value="lama-manga")
                    return gr.update()
                if data.get("cpu"):
                    return gr.update(value="opencv")
                if data.get("lama"):
                    return gr.update(value="lama-big")
                return gr.update(value="lama-manga")

            def u_dev():
                v = str(data.get("device") or "").strip().lower()
                if v not in ("auto", "cpu", "gpu"):
                    v = "auto"
                return gr.update(value=v)

            _MT_OK = ("auto", "8192", "16384", "32768", "65536", "custom")

            def u_max_tokens():
                v = str(data.get("max_tokens") or "").strip().lower()
                if v not in _MT_OK:
                    v = "auto"
                return gr.update(value=v)

            def u_max_tokens_custom():
                v = str(data.get("max_tokens") or "auto").strip().lower()
                if v not in _MT_OK:
                    v = "auto"
                if "max_tokens_custom" not in data:
                    return gr.update(visible=(v == "custom"))
                try:
                    n = int(float(data.get("max_tokens_custom") or 4096))
                except Exception:
                    n = 4096
                return gr.update(value=n, visible=(v == "custom"))

            return (
                sid,
                gr.update(value=sid),
                gr.update(value=btn),
                gr.update(value=log),
                gr.update(value=dl, label=_dl_label(dl), visible=vis) if vis else gr.update(),
                gr.update(visible=False),
                gr.update(visible=vis),
                gr.update(visible=False),
                html if vis else gr.update(),
                u_str("inp"),
                u_str("prov"),
                gr.update(),
                gr.update(),
                u_str("fmt"),
                u_num("qual"),
                u_num("workers"),
                u_num("bubbles"),
                u_num("timeout"),
                u_num("batchw"),
                u_num("maxre"),
                u_num("reqdelay"),
                u_num("temp"),
                u_num("top_p"),
                u_str("readord"),
                u_cleanm(),
                u_dev(),
                u_bool("twopass"),
                u_bool("fake_test"),
                u_bool("clean_only"),
                u_bool("deep_thinking"),
                u_bool("safety_settings"),
                u_max_tokens(),
                u_max_tokens_custom(),
                u_str("glossary_text"),
                u_bool("story_brief"),
            )

        _restore_outputs = [
            session_id, sid_box, run_btn, log_box, dl_btn, btn_view, result_group, viewer_html, html_state,
            inp_path, provider, api_keys, model, out_fmt, quality,
            workers, bubbles, timeout, batchw, maxre, reqdelay, temp, top_p, readord,
            clean_method, device, two_pass, fake_test, clean_only,
            deep_thinking, safety_settings, max_tokens, max_tokens_custom,
            glossary_text, story_brief,
        ]

        hidden_restore_tb = gr.Textbox(visible=False, elem_id="manga_hidden_restore", container=False)
        try:
            demo.load(
                fn=None,
                inputs=None,
                outputs=[hidden_restore_tb],
                js=load_form_js,
            )
        except Exception:
            pass
        try:
            hidden_restore_tb.change(
                _apply_browser_restore,
                inputs=[hidden_restore_tb],
                outputs=_restore_outputs,
            )
        except Exception:
            pass

        try:
            demo.load(None, None, None, js=client_restore_js)
        except Exception:
            try:
                demo.load(fn=None, inputs=None, outputs=None, js=client_restore_js)
            except Exception:
                pass
        try:
            demo.load(None, None, None, js=_REFRESH_FAB_JS)
        except Exception:
            pass

        try:
            def _on_load_fallback(sid, sid_box_v):
                preferred = (sid or sid_box_v or "").strip()
                if not preferred:
                    return (gr.update(),) * 13
                sid = _find_active_sid(preferred) or preferred
                job = _get_job(sid)
                meta = _load_job_meta(sid)
                with job["lock"]:
                    mem_log = job.get("log") or ""
                    meta_log = meta.get("log") or ""
                    if (not mem_log or mem_log.startswith("—")) and meta_log:
                        job["log"] = meta_log
                    elif meta_log and len(meta_log) > len(mem_log):
                        job["log"] = meta_log
                    if meta.get("download_path"):
                        job["download_path"] = meta.get("download_path")
                    if meta.get("download_debug"):
                        job["download_debug"] = meta.get("download_debug")
                    if meta.get("result_visible"):
                        job["result_visible"] = True
                    if meta.get("reader_path"):
                        job["reader_path"] = meta.get("reader_path")
                    if meta.get("reader_debug_path"):
                        job["reader_debug_path"] = meta.get("reader_debug_path")
                    still_running = _job_running(job)
                    log = job.get("log") or ""
                    vis = bool(job.get("result_visible"))
                    dl = job.get("download_path")
                    dl_dbg = job.get("download_debug")
                    has_dbg = bool(dl_dbg or job.get("reader_debug_path") or meta.get("has_debug"))
                    want_dbg = bool(job.get("want_debug") or meta.get("want_debug") or has_dbg)
                    show_dbg = bool(want_dbg and (vis or still_running))
                    html = job.get("html_state") or ""
                if not log or log.startswith("—"):
                    return (sid, gr.update(value=sid)) + (gr.update(),) * 11
                btn = "⏹  متوقف ترجمه" if still_running else "🚀  شروع ترجمه"
                _dbg_sz = ""
                try:
                    if dl_dbg and os.path.isfile(dl_dbg):
                        _dbg_sz = f" ({human_size(os.path.getsize(dl_dbg))})"
                except Exception:
                    pass
                return (
                    sid,
                    gr.update(value=sid),
                    gr.update(value=btn),
                    gr.update(value=log),
                    gr.update(value=dl, label=_dl_label(dl), visible=vis) if vis else gr.update(),
                    gr.update(visible=False),
                    gr.update(visible=vis),
                    gr.update(visible=False),
                    html if vis else gr.update(),
                    gr.update(value=dl_dbg,
                              label=str(TX("app.download_debug", "⬇ دانلود دیباگ")) + _dbg_sz,
                              visible=bool(show_dbg and dl_dbg and vis)),
                    gr.update(visible=False),
                    gr.update(visible=bool(show_dbg and dl_dbg and vis)),
                    gr.update(),
                )

            demo.load(
                _on_load_fallback,
                inputs=[session_id, sid_box],
                outputs=[session_id, sid_box, run_btn, log_box, dl_btn, btn_view, result_group, viewer_html, html_state,
                     dl_btn_debug, btn_view_debug, debug_row, html_debug_state],
            )
        except Exception:
            pass

        def _poll_job_status(sid, sid_box_v, run_btn_v="", log_box_v=""):
            preferred = (sid or sid_box_v or "").strip()
            sid = _find_active_sid(preferred) or preferred
            empty = (gr.update(),) * 15
            if not sid:
                return empty
            try:
                _web_touch(sid)
            except Exception:
                pass
            job = _get_job(sid)
            meta = _load_job_meta(sid)
            with job["lock"]:
                mem_log = job.get("log") or ""
                meta_log = meta.get("log") or ""
                if meta_log and (
                        len(meta_log) > len(mem_log) or not mem_log
                        or mem_log.startswith("—")):
                    job["log"] = meta_log
                if meta.get("result_visible") and not job.get("result_visible"):
                    job["result_visible"] = True
                if meta.get("download_path") and not job.get("download_path"):
                    job["download_path"] = meta.get("download_path")
                if meta.get("download_debug") and not job.get("download_debug"):
                    job["download_debug"] = meta.get("download_debug")
                if meta.get("reader_path") and not job.get("reader_path"):
                    job["reader_path"] = meta.get("reader_path")
                if meta.get("reader_debug_path") and not job.get("reader_debug_path"):
                    job["reader_debug_path"] = meta.get("reader_debug_path")
                
                running = _job_running(job)
                log = job.get("log") or ""
                _last_pushed = job.get("_last_poll_log")
                _force_log = bool(job.get("_log_force_push"))
                if _force_log:
                    job["_log_force_push"] = False
                _cl = str(log_box_v or "")
                _stale_client = (len(_cl) < len(log)
                                 and _cl[:400] == log[:400])
                log_changed = bool(log) and (
                    log != _last_pushed or _force_log or _stale_client)
                if log_changed:
                    job["_last_poll_log"] = log
                vis = bool(job.get("result_visible"))
                live_cnt = 0
                try:
                    _ld = job.get("live_dir")
                    if _ld and os.path.isdir(_ld):
                        live_cnt = sum(
                            1 for f in os.listdir(_ld)
                            if f.lower().endswith(".jpg") and f.startswith("live_"))
                except Exception:
                    pass
                dl = job.get("download_path")
                dl_dbg = job.get("download_debug")
                has_dbg = bool(dl_dbg or job.get("reader_debug_path") or meta.get("has_debug"))
                want_dbg = bool(job.get("want_debug") or meta.get("want_debug") or has_dbg)
            default_log = "— لاگ بعد از شروع ترجمه اینجا می‌آید —"
            if not running and not vis and (not log or log.strip() == default_log):
                _bt = str(run_btn_v or "")
                if ("متوقف" in _bt) or ("⏹" in _bt):
                    return (sid, gr.update(value=sid), gr.update(value=sid),
                            gr.update(value="🚀  شروع ترجمه")) + empty[4:]
                return empty
            btn = "⏹  متوقف ترجمه" if running else "🚀  شروع ترجمه"
            show_card = bool(vis or (running and live_cnt > 0))
            _dbg_sz = ""
            try:
                if dl_dbg and os.path.isfile(dl_dbg):
                    _dbg_sz = f" ({human_size(os.path.getsize(dl_dbg))})"
            except Exception:
                pass
            return (
                sid,
                gr.update(value=sid),
                gr.update(value=sid),
                gr.update(value=btn),
                gr.update(value=log) if (log and log_changed) else gr.update(),
                gr.update(value=dl, label=_dl_label(dl), visible=vis) if vis else gr.update(),
                gr.update(visible=False),
                gr.update(visible=show_card),
                gr.update(),
                gr.update(),
                gr.update(value=dl_dbg,
                          label=str(TX("app.download_debug", "⬇ دانلود دیباگ")) + _dbg_sz,
                          visible=bool(dl_dbg and vis)),
                gr.update(visible=False),
                gr.update(visible=bool(dl_dbg and vis)),
                gr.update(),
                gr.update(),
            )

        _poll_outputs = [session_id, sid_box, sid_holder, run_btn, log_box, dl_btn, btn_view, result_group, viewer_html, html_state,
                         dl_btn_debug, btn_view_debug, debug_row, html_debug_state, prog_html]

        def _scan_live_dir(live_dir):
            try:
                fs = [f for f in os.listdir(live_dir)
                      if f.lower().endswith(".jpg") and f.startswith("live_")
                      and not f.lower().endswith("_base.jpg")]
            except Exception:
                return []
            fs.sort()
            return [os.path.join(live_dir, f) for f in fs]

        def _dbg_sibling(live_dir: str) -> str:
            try:
                base = os.path.dirname(os.path.abspath(live_dir))
                cand = os.path.join(base, "live_debug")
                if os.path.isdir(cand):
                    return cand
            except Exception:
                pass
            return ""

        def _live_total_of(d: str) -> int:
            try:
                with open(os.path.join(d, "total.txt"), encoding="utf-8") as f:
                    return int(f.read().strip() or 0)
            except Exception:
                return 0

        def _write_live_reader(live_dir: str, dbg_dir: str = "",
                               run: str = "") -> str:
            import gradio as _gr
            gv = getattr(_gr, "__version__", "4")
            try:
                major = int(str(gv).split(".")[0] or 4)
            except Exception:
                major = 4
            prefix = "/gradio_api/file=" if major >= 5 else "/file="
            d = str(live_dir).replace(os.sep, "/")
            if not d.endswith("/"):
                d += "/"
            dbg_q = ""
            if dbg_dir:
                dbg_q = str(dbg_dir).replace(os.sep, "/")
                if not dbg_q.endswith("/"):
                    dbg_q += "/"
            run_tok = str(run or "").strip() or str(int(time.time() * 1000))
            _uit_head = _ui_t_head()
            html = (_LIVE_READER_TMPL
                    .replace("</style></head>", "</style>" + _uit_head + "</head>")
                    .replace("__PREFIX__", prefix)
                    .replace("__DIR__", urllib.parse.quote(d, safe="/"))
                    .replace("__DBGDIR__", urllib.parse.quote(dbg_q, safe="/"))
                    .replace("__RUN__", run_tok))
            path = os.path.join(live_dir, "live_reader.html")
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            return path

        def _start_live_slicer(live_dir: str, job: dict) -> None:
            try:
                from PIL import Image as _PILImage
            except Exception:
                return
            state = {"stop": False}

            def _slice_one(path: str, st_mtime_ms: int) -> None:
                try:
                    slot = os.path.basename(path)[5:-4]
                    mark = os.path.join(live_dir, "w_%s.json" % slot)
                    try:
                        with open(mark, encoding="utf-8") as f:
                            old = json.load(f) or {}
                        if int(old.get("src") or 0) == st_mtime_ms:
                            return
                    except Exception:
                        pass
                    with _PILImage.open(path) as im:
                        im = im.convert("RGB")
                        w, h = im.size
                        n = 0
                        if h > 2000:
                            n = (h + 1999) // 2000
                            for k in range(n):
                                chk = im.crop(
                                    (0, k * 2000, w, min(h, (k + 1) * 2000)))
                                fp = os.path.join(
                                    live_dir, "w_%s_%d.jpg" % (slot, k + 1))
                                tmp = fp + ".tmp"
                                chk.save(tmp, format="JPEG", quality=82,
                                         optimize=True, progressive=True)
                                os.replace(tmp, fp)
                    try:
                        if int(os.path.getmtime(path) * 1000) != st_mtime_ms:
                            return
                    except OSError:
                        return
                    tmpm = mark + ".tmp"
                    with open(tmpm, "w", encoding="utf-8") as f:
                        json.dump({"n": n, "src": st_mtime_ms}, f)
                    os.replace(tmpm, mark)
                except Exception:
                    pass

            def _worker():
                seen = {}
                idle = 0.0
                while not state.get("stop") and os.path.isdir(live_dir):
                    changed = False
                    try:
                        for f in os.listdir(live_dir):
                            if not (f.startswith("live_")
                                    and f.endswith(".jpg")):
                                continue
                            if f.endswith("_base.jpg"):
                                continue
                            p = os.path.join(live_dir, f)
                            try:
                                mt = os.path.getmtime(p)
                            except OSError:
                                continue
                            if seen.get(f) == mt:
                                continue
                            seen[f] = mt
                            changed = True
                            _slice_one(p, int(mt * 1000))
                    except Exception:
                        pass
                    idle = (0.0 if changed else idle + 0.25)
                    time.sleep(0.25 if idle < 300 else 2.0)

            threading.Thread(target=_worker, daemon=True,
                             name="manga-live-slicer").start()
            with job["lock"]:
                job["live_slicer"] = state

        def _on_sid_reconnect(sid_v):
            sid = (sid_v or "").strip()
            if not sid:
                return
            try:
                sid = _find_active_sid(sid) or sid
            except Exception:
                pass
            job = live_jobs.get(sid)
            if job is not None:
                with job["lock"]:
                    job["_live_force_push"] = True
                    job["_log_force_push"] = True
        try:
            sid_holder.change(_on_sid_reconnect, inputs=[sid_holder], outputs=None,
                              queue=False)
        except Exception:
            try:
                sid_box.change(_on_sid_reconnect, inputs=[sid_box], outputs=None,
                               queue=False)
            except Exception:
                pass

        def _poll_live_gallery(sid_v, sid_box_v):
            pref = (sid_v or sid_box_v or "").strip()
            job = live_jobs.get(pref)
            if job is None:
                return gr.update(), gr.update(), gr.update()
            live_dir = job.get("live_dir")
            files = _scan_live_dir(live_dir) if live_dir else []
            dbg_dir = job.get("live_dbg_dir")
            dbg_files = _scan_live_dir(dbg_dir) if dbg_dir else []
            with job["lock"]:
                prev = list(job.get("live_files") or [])
                prev_dbg = list(job.get("live_dbg_files") or [])
                running = bool(job.get("running")) and (
                    job.get("proc") is None or job["proc"].poll() is None)
                if files != prev or dbg_files != prev_dbg:
                    job["live_files"] = files
                    job["live_dbg_files"] = dbg_files
                    job["_live_was_running"] = running
                    job["ts"] = time.time()
                _pushed = job.get("_live_last_push") or ()
                _now_push = (running, tuple(files), tuple(dbg_files))
                job["_live_last_push"] = _now_push
                _force = bool(job.get("_live_force_push"))
                if _force:
                    job["_live_force_push"] = False
                need_push = _force or (_pushed != _now_push) \
                    or not job.get("_live_pushed_once")
                job["_live_pushed_once"] = True
            if not need_push:
                return gr.update(), gr.update(), gr.update()
            if not running:
                tot_end = _live_total_of(live_dir) if live_dir else 0
                n_end = len(files)
                if n_end > 0 or tot_end > 0:
                    if tot_end > 0:
                        lbl_end = "📖 نمایش (%d/%d صفحه)" % (n_end, tot_end)
                    elif n_end > 1:
                        lbl_end = "📖 نمایش (%d صفحه)" % n_end
                    else:
                        lbl_end = "📖 نمایش (۱ صفحه)"
                    return (gr.update(value=lbl_end, visible=True),
                            gr.update(),
                            gr.update(visible=False))
                return (gr.update(visible=False), gr.update(), gr.update())
            tot = _live_total_of(live_dir) if live_dir else 0
            if tot > 0:
                label = "📖 نمایش (%d/%d صفحه)" % (len(files), tot)
            elif len(files) > 1:
                label = "📖 نمایش (%d صفحه)" % len(files)
            else:
                label = "📖 نمایش (۱ صفحه)"
            return (gr.update(value=label, visible=True),
                    gr.update(visible=True),
                    gr.update(visible=False))
        try:
            _timer = gr.Timer(1.0, active=True)
            _tick_evt = _timer.tick(
                _poll_job_status,
                inputs=[sid_holder, sid_box, run_btn, log_box],
                outputs=_poll_outputs,
                queue=False,
                concurrency_limit=1,
            )
            try:
                
                _tick_evt.then(
                    fn=None,
                    inputs=[session_id, sid_box, run_btn, log_box],
                    outputs=[],
                    js=save_job_js,
                    queue=False,
                )
            except Exception:
                pass
        except Exception:
            try:
                demo.load(_poll_job_status, inputs=[session_id, sid_box, run_btn, log_box], outputs=_poll_outputs)
            except Exception:
                pass

        try:
            _timer_g = gr.Timer(1.5, active=True)
            _timer_g.tick(
                _poll_live_gallery,
                inputs=[sid_holder, sid_box],
                outputs=[live_btn, result_group, btn_view_debug],
                queue=False,
                concurrency_limit=1,
            )
        except Exception:
            pass

        def _cleanup_old_jobs():
            _file_ttl = _web_file_ttl() if _web_host() else JOB_TTL
            while True:
                try:
                    now = time.time()
                    dead = []
                    for sid, job in list(live_jobs.items()):
                        try:
                            with job["lock"]:
                                alive = job.get("proc") is not None and job["proc"].poll() is None
                                ts = job.get("ts") or 0
                            _seen = _web_last_seen_of(sid[:12])
                            if _seen > ts:
                                ts = _seen
                            if not alive and (now - ts) > _file_ttl:
                                dead.append(sid)
                                out_sub = os.path.join(OUT_DIR, sid[:12])
                                if os.path.isdir(out_sub):
                                    shutil.rmtree(out_sub, ignore_errors=True)
                        except Exception:
                            dead.append(sid)
                    for sid in dead:
                        live_jobs.pop(sid, None)

                    if os.path.isdir(OUT_DIR):
                        _busy12 = set()
                        for _jsid, _jb in list(live_jobs.items()):
                            try:
                                if _job_running(_jb):
                                    _busy12.add(str(_jsid)[:12])
                            except Exception:
                                pass
                        for name in os.listdir(OUT_DIR):
                            p = os.path.join(OUT_DIR, name)
                            if not os.path.isdir(p):
                                continue
                            if name in _busy12:
                                continue
                            if len(name) == 12 and all(c in "0123456789abcdef" for c in name.lower()):
                                try:
                                    mtime = os.path.getmtime(p)
                                    for root, dirs, files in os.walk(p):
                                        for f in files:
                                            try:
                                                mtime = max(mtime, os.path.getmtime(os.path.join(root, f)))
                                            except Exception:
                                                pass
                                    _seen = _web_last_seen_of(name)
                                    if _seen > mtime:
                                        mtime = _seen
                                    if (now - mtime) > _file_ttl:
                                        shutil.rmtree(p, ignore_errors=True)
                                        with _web_seen_lock:
                                            _WEB_LAST_SEEN.pop(name, None)
                                        try:
                                            print(f"[🧹 وب] پوشهٔ خروجیِ کهنه پاک شد: "
                                                  f"{name} (بیش از "
                                                  f"{int(_file_ttl // 60)} دقیقه از "
                                                  f"آخرین حضور)")
                                        except Exception:
                                            pass
                                except Exception:
                                    pass

                    old_sess = os.path.join(WORK_DIR, "sessions")
                    if os.path.isdir(old_sess):
                        for name in os.listdir(old_sess):
                            if name == "web_last_seen.json":
                                continue
                            fp = os.path.join(old_sess, name)
                            try:
                                if (now - os.path.getmtime(fp)) > _file_ttl:
                                    if os.path.isfile(fp):
                                        os.remove(fp)
                                    elif os.path.isdir(fp):
                                        shutil.rmtree(fp, ignore_errors=True)
                            except Exception:
                                pass
                except Exception:
                    pass
                time.sleep(60)

        def _sid_box_sync(sid_v, sid_box_v):
            preferred = (sid_v or sid_box_v or "").strip()
            if not preferred:
                return (gr.update(),) * 15
            return _poll_job_status(preferred, preferred)

        try:
            sid_box.change(
                _sid_box_sync,
                inputs=[session_id, sid_box],
                outputs=_poll_outputs,
            )
        except Exception:
            pass

        _direct_restore_js = f"""
() => {{
  try {{
    const job = JSON.parse(localStorage.getItem("{JOB_KEY}") || "{{}}");
    const sid = (localStorage.getItem("manga_sid") || job.sid || "").trim();
    const log = (job.log || "").toString();
    const running = !!job.running;
    const btn = running ? "⏹  متوقف ترجمه" : "🚀  شروع ترجمه";
    return [sid, sid, sid, btn, log];
  }} catch (e) {{
    return ["", "", "", "🚀  شروع ترجمه", ""];
  }}
}}
"""

        def _apply_direct_restore(sid, sid2, btn, log):
            sid = (sid or sid2 or "").strip()
            log = (log or "").strip()
            btn = (btn or "").strip() or "🚀  شروع ترجمه"
            if not sid and not log:
                return gr.update(), gr.update(), gr.update(), gr.update(), gr.update()
            server_log = ""
            still = False
            if sid:
                job = _get_job(sid)
                meta = _load_job_meta(sid)
                with job["lock"]:
                    if meta.get("log") and (
                        not job.get("log")
                        or len(meta.get("log") or "") > len(job.get("log") or "")
                    ):
                        job["log"] = meta["log"]
                    still = _job_running(job)
                    server_log = job.get("log") or ""
            client_wants_run = ("متوقف" in btn) or ("⏹" in btn)
            if still:
                btn = "⏹  متوقف ترجمه"
            elif client_wants_run and not still:
                
                if server_log or log:
                    tail = "\n\n⚠ بعد از رفرش اتصال به پروسه قطع شد. اگر کار تمام نشده دوباره Start بزنید."
                    base = server_log if len(server_log) >= len(log) else log
                    if "اتصال به پروسه قطع شد" not in base:
                        log = base + tail
                    else:
                        log = base
                btn = "🚀  شروع ترجمه"
            final_log = server_log if (server_log and len(server_log) >= len(log or "")) else (log or server_log)
            return (
                sid if sid else gr.update(),
                gr.update(value=sid) if sid else gr.update(),
                gr.update(value=sid) if sid else gr.update(),  
                gr.update(value=btn),
                gr.update(value=final_log) if final_log else gr.update(),
            )

        try:
            demo.load(
                fn=None,
                js=_direct_restore_js,
                outputs=[session_id, sid_box, sid_holder, run_btn, log_box],
            )
        except Exception:
            try:
                demo.load(
                    _apply_direct_restore,
                    inputs=None,
                    outputs=[session_id, sid_box, sid_holder, run_btn, log_box],
                    js=_direct_restore_js,
                )
            except Exception:
                pass

        def _hydrate_after_js(sid, holder):
            preferred = (sid or holder or "").strip()
            if not preferred:
                return (gr.update(),) * 15
            return _poll_job_status(preferred, preferred)

        try:
            demo.load(
                _hydrate_after_js,
                inputs=[sid_holder, sid_box],
                outputs=_poll_outputs,
            )
        except Exception:
            pass

        if _web_host():
            try:
                _web_seen_load()
            except Exception:
                pass
            threading.Thread(target=_cleanup_old_jobs, daemon=True).start()

        def _reader_file_url(path: str) -> str:
            if not path or not os.path.isfile(path):
                return ""
            import gradio as _gr
            gv = getattr(_gr, "__version__", "4")
            major = int(str(gv).split(".")[0] or 4)
            prefix = "/gradio_api/file=" if major >= 5 else "/file="
            return prefix + str(path).replace(os.sep, "/")

        reader_url_box = gr.Textbox(value="", visible=False, elem_id="manga_reader_url")

        open_live_js = """
(url) => {
  const u = (url || "").toString().trim();
  const isDesk = (new URLSearchParams(location.search)).get('desktop') === '1'
                 || !!(window.pywebview);
  if (!u) {
    if (!isDesk) { alert("هنوز صفحه‌ای آماده نشده — چند لحظه بعد دوباره بزن."); }
    return [];
  }
  if (isDesk) { window.location.href = u; return []; }
  window.__mangaCloseReader = () => {
    try {
      const ov = document.getElementById('mangaReaderOverlay');
      if (ov && ov.parentNode) ov.parentNode.removeChild(ov);
    } catch (e) {}
  };
  try { window.__mangaCloseReader(); } catch (e) {}
  const ov = document.createElement('div');
  ov.id = 'mangaReaderOverlay';
  ov.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;'
    + 'width:100vw;height:100vh;margin:0;padding:0;z-index:2147483630;'
    + 'background:#000;';;
  const fr = document.createElement('iframe');
  fr.title = 'نمایش';
  fr.allow = 'fullscreen';
  fr.style.cssText = 'position:absolute;top:0;left:0;width:100%;'
    + 'height:100%;border:0;display:block;background:#000;';
  let injected = false;
  fr.addEventListener('load', () => {
    try {
      const d = fr.contentDocument;
      if (!d) return;
      if (d.getElementById('mangaOvClose')) { injected = true; return; }
      const bar = d.querySelector('.bar') || d.body;
      if (!bar) return;
      const b = d.createElement('button');
      b.type = 'button';
      b.id = 'mangaOvClose';
      b.className = 'zbtn';
      b.textContent = '✕';
      b.title = 'بازگشت به صفحهٔ اصلی';
      b.setAttribute('aria-label', 'بازگشت به صفحهٔ اصلی');
      b.style.cssText = 'background:#2a1215;border-color:#ff4a3d;'
        + 'color:#ff8d84;font-weight:700;flex:none;';
      b.addEventListener('click', (ev) => {
        ev.preventDefault();
        ev.stopPropagation();
        try { parent.__mangaCloseReader(); } catch (e) {}
      });
      bar.appendChild(b);
      d.addEventListener('keydown', (ev) => {
        if (ev.key === 'Escape') {
          try { parent.__mangaCloseReader(); } catch (e) {}
        }
      }, true);
      injected = true;
    } catch (e) { injected = false; }
  });
  fr.src = u;
  ov.appendChild(fr);
  const x = document.createElement('button');
  x.type = 'button';
  x.textContent = '✕';
  x.title = 'بازگشت به صفحهٔ اصلی';
  x.setAttribute('aria-label', 'بازگشت به صفحهٔ اصلی');
  x.style.cssText = 'position:absolute;top:10px;left:10px;z-index:3;'
    + 'width:42px;height:42px;border-radius:21px;'
    + 'border:1px solid rgba(255,74,61,.55);background:rgba(20,10,10,.85);'
    + 'color:#ff8d84;font-size:19px;font-weight:700;line-height:1;'
    + 'cursor:pointer;backdrop-filter:blur(6px);display:flex;'
    + 'align-items:center;justify-content:center;';
  x.addEventListener('click', window.__mangaCloseReader);
  setTimeout(() => { if (!injected) { try { ov.appendChild(x); } catch (e) {} } }, 2500);
  document.body.appendChild(ov);
  return [];
}
"""

        def _open_live_viewer(sid, sid_box_v):
            preferred = (sid or sid_box_v or "").strip()
            sid2 = _find_active_sid(preferred) or preferred
            job = _get_job(sid2) if sid2 else None
            url = ""
            if job:
                with job["lock"]:
                    d = job.get("live_dir")
                    rt = job.get("live_run") or ""
                    _sl = job.get("live_slicer")
                if d and os.path.isdir(d):
                    if not _sl:
                        try:
                            _start_live_slicer(d, job)
                        except Exception:
                            pass
                    try:
                        path = os.path.join(d, "live_reader.html")
                        if not os.path.isfile(path):
                            rt = str(int(time.time() * 1000))
                            _write_live_reader(d, dbg_dir=_dbg_sibling(d), run=rt)
                            with job["lock"]:
                                job["live_run"] = rt
                        url = _reader_file_url(path)
                        if rt:
                            url += ("&" if "?" in url else "?") + "v=" + rt
                    except Exception:
                        url = ""
            return url

        try:
            live_btn.click(
                fn=_open_live_viewer,
                inputs=[session_id, sid_box],
                outputs=[reader_url_box],
            ).then(
                fn=None,
                inputs=[reader_url_box],
                outputs=[],
                js=open_live_js,
            )
        except Exception:
            pass

        try:
            demo.load(None, None, None, js=_dark_js_src())
        except Exception:
            try:
                demo.load(js=_dark_js_src())
            except Exception:
                pass

        try:
            demo.load(None, None, None, js=_browser_extract_js())
        except Exception:
            try:
                demo.load(js=_browser_extract_js())
            except Exception:
                pass

        try:
            demo.load(None, None, None, js=_prov_keys_js())
        except Exception:
            try:
                demo.load(js=_prov_keys_js())
            except Exception:
                pass

        _qtip_texts = {
            "manga_cb_twopass": TX("app.two_pass_info",
                                   "پاسِ اول بلوکها را مییابد، پاسِ دوم متنِ داخلشان را دقیق بازمیخواند — پیش‌فرض روشن"),
            "manga_cb_thinking": TX("app.thinking_info",
                                    "سطح High — برای جمینای و OpenAI-سازگارها؛ پیش‌فرض روشن"),
            "manga_cb_faketest": TX("app.fake_test_info",
                                    "به‌جای API، متنِ الکی داخل حباب‌ها رندر میشود — چکِ استخراج/پاکسازی/رندر بدون کلید"),
            "manga_cb_cleanup": TX("app.cleanup_mode_info",
                                   "فقط پاکسازی متن (inpaint) بدون ترجمه — کلید API لازم نیست"),
            "manga_cb_debug": TX("app.web_debug_info",
                                 "مربعِ رنگی دور هر بلوک + خروجیِ دیباگ جدا (مثلاً PDF → *_debug.pdf)"),
            "manga_cb_safety": TX("app.safety_info",
                                  "فیلترهای گوگل BLOCK_NONE میشوند (ضدِ سانسور) — پیش‌فرض خاموش"),
            "manga_max_tokens": TX("app.max_tokens_info",
                                   "خودکار = سرویس‌دهنده خودش مدیریت میکند؛ چپترِ طولانیِ ناتمام؟ عدد را بالا ببرید"),
            "manga_max_tokens_custom": TX("app.max_tokens_custom_info",
                                          "عددِ دلخواه سقفِ توکنِ خروجی — حداقل ۱۰۲۴"),
            "manga_inp_path": TX("app.url_info",
                                 "چند لینک = هر لینک در یک خط (اینتر) — کاما هم کار می‌کند. «آدرس فصلِ ۲۰ > آدرس فصلِ ۲۴» بازهٔ کاملِ فصلها، «…/1 > 14.jpg» از اول تا آخر، «…/1 < 14.jpg» از آخر به اول، «…/*.jpg» هرچه پیدا کند — همه با هم ترجمه می‌شوند."),
            "manga_provider": TX("app.ai_menu_info",
                                 "«auto» (با مدلِ اضافهشده) خودش بینِ Gemini و مدل‌های شما اولینِ در دسترس را انتخاب میکند. مدلِ مشخص = فقط همان. «custom» = فیلدهای همین صفحه. حذفِ مدل = انتخابش در منو + ✖ِ کنارِ منو. «+ افزودن» مدلِ فعلی را در لیست ثبت میکند؛ در منو میآید و در بکاپ ذخیره میشود."),
            "manga_api_base": TX("app.api_base_info",
                                 "۴ فرمت خودکار شناخته می‌شود: …/chat/completions | …/responses | …/messages (Anthropic) | …:generateContent (Google) — لینک کامل endpoint را هم می‌شود چسباند؛ https:// اگر جا افتاده باشد خودکار اضافه می‌شود."),
            "manga_api_keys": TX("app.api_keys_info",
                                 "چند کلید با کاما = چرخش خودکار. کلید فقط در localStorage مرورگر شما می‌ماند — نه روی سرور. با 👁 دیده میشود. از aistudio.google.com (Gemini) یا سرویس دلخواه خودتان بگیرید."),
            "manga_model": TX("app.model_info",
                              "چند مدل با کاما = فال‌بکِ خودکار (مثال: gemini-3.5-flash-lite,gemini-3.8-flash). ↻ همهٔ مدلهایِ رایگان را داخلِ فیلد می‌نویسد. خالی = پیش‌فرض."),
            "manga_ocr_lang": TX("app.ocr_lang_info",
                                 "زبانهای حباب‌ها را تیک بزن (مثلاً فقط ژاپنی، یا ژاپنی+انگلیسی، یا همه). مانهوای فارسی/انگلیسی → فقط انگلیسی کافی است."),
            "manga_quality": TX("app.quality_info",
                                "کیفیت فشرده‌سازی تصویر خروجی — ۹۰ به بالا = بدون افتِ محسوس"),
            "manga_font_upload": TX("app.font_info",
                                    "فونت اصلی (.ttf/.otf) — خالی = فونت سرور. هر فونت لحن را جدا آپلود کن؛ با سوییچِ کنار هر لحن فعال/غیرفعالش کن."),
            "manga_sl_workers": TX("app.ocr_workers_info",
                                   "تعداد ورکرِ موازی OCR — فقط حالت تک‌عکس"),
            "manga_sl_bubbles": TX("app.bubbles_info",
                                   "چند حباب در هر درخواست ترجمه به AI فرستاده شود"),
            "manga_sl_batchw": TX("app.batch_info",
                                  "بستهٔ ترجمهٔ موازی — هر بسته با کلید جدا"),
            "manga_sl_timeout": TX("app.timeout_info",
                                   "حداکثر انتظار برای پاسخ هر درخواست (ثانیه)"),
            "manga_sl_maxre": TX("app.max_retry_info",
                                 "حداکثر تلاش مجدد برای هر ترجمه"),
            "manga_sl_delay": TX("app.delay_info",
                                 "تأخیر بین درخواست‌ها (ثانیه) — ضدِ محدودیتِ نرخ"),
            "manga_sl_temp": TX("app.temperature_info",
                                "خلاقیت — ۰.۳ تحت‌اللفظی، ۰.۷+ محاوره‌ای و روان"),
            "manga_sl_topp": TX("app.topp_info",
                                "تنوع واژگان — ۰.۹ بهترین تعادل"),
            "manga_readord": TX("app.order_info",
                                "ترتیب خواندن حباب‌ها در صفحه — rtl برای مانگای راست‌به‌چپ"),
            "manga_clean_method": TX("app.cleanup_info",
                                     "lama-manga = سبک و سریع | big-lama = دقیقتر و سنگینتر | opencv = فوری بدون مدل (فقط حبابهای ساده)"),
            "manga_device": TX("app.device_info",
                               "دستگاه پردازش استخراج و پاکسازی — فقط وقتی سرور GPU دارد نمایش داده میشود"),
            "manga_prompt_mode": TX("app.prompt_mode_info",
                                    "حرفه‌ای = فرآیند تفکر سه‌گانه برای Flash و Pro | سبک = برای Flash Lite و مدلهای سبکِ غیر Gemini"),
            "manga_prompt_body": TX("app.prompt_info",
                                    "همین متن بهعنوان قوانین ترجمه به مدل فرستاده میشود — خالی = پرامپت خودکارِ بر اساس سبک و مدل"),
        }
        try:
            _qtip_json = json.dumps(_qtip_texts, ensure_ascii=False)
        except Exception:
            _qtip_json = "{}"
        _prog_res_json = json.dumps(
            [[p, k, u] for p, k, u in _WEB_PROG_COUNT_RES], ensure_ascii=False)
        _prog_phases_json = json.dumps(
            [list(x) for x in _WEB_PROG_PHASES], ensure_ascii=False)
        _prog_js = """() => {
window.__mangaUpdateProg = function(logText, btnLabel) {
  try {
    const host = document.getElementById('manga_prog_row');
    if (!host) return;
    const log = (logText || '').toString();
    if (!log || log.indexOf('— لاگ بعد') === 0) {
      if (host.__mp) { host.innerHTML = ''; host.__mp = ''; }
      return;
    }
    const running = !!(btnLabel && (btnLabel.indexOf('متوقف') >= 0 || btnLabel.indexOf('⏹') >= 0));
    const RES = __PROG_RES__.map(r => [new RegExp(r[0]), r[1], r[2]]);
    const PHASES = __PROG_PHASES__;
    const tail = log.split('\\n').slice(-400);
    const marks = {};
    let extDoneIdx = null, readyIdx = null, readyPage = 0, termIdx = -1, termPhase = '';
    tail.forEach((ln, idx) => {
      for (const [rx, kind, unit] of RES) {
        const m = rx.exec(ln);
        if (m) marks[kind] = [idx, parseInt(m[1], 10), parseInt(m[2], 10), unit];
      }
      if (extDoneIdx === null && ln.indexOf('صفحه کامل شد') >= 0) extDoneIdx = idx;
      const rm = /(\\d{1,4})\\s+آماده شد/.exec(ln);
      if (rm) { readyIdx = idx; readyPage = parseInt(rm[1], 10); }
      for (const [k, v] of PHASES) {
        if (ln.indexOf(k) >= 0 && (v === 'تمام شد' || v === 'خطا' || v === 'لغو شد')) {
          termIdx = idx; termPhase = v;
        }
      }
    });
    let events = [];
    for (const kind in marks) {
      const [idx, cur, tot, unit] = marks[kind];
      if (kind === 'استخراج متن' && extDoneIdx !== null && idx < extDoneIdx) continue;
      events.push([idx, kind, cur, tot, unit]);
    }
    if (readyIdx !== null) events.push([readyIdx, 'رندر و ذخیره', readyPage + 1, 0, 'صفحهٔ']);
    if (termIdx >= 0) events.push([termIdx, termPhase, readyPage, 0, '']);
    let ph = '', cur = 0, tot = 0, unit = '';
    if (events.length) {
      events.sort((a, b) => a[0] - b[0]);
      const e = events[events.length - 1];
      ph = e[1]; cur = e[2]; tot = e[3]; unit = e[4];
    } else {
      for (let i = tail.length - 1; i >= 0; i--) {
        let hit = false;
        for (const [k, v] of PHASES) {
          if (tail[i].indexOf(k) >= 0) { ph = v; hit = true; break; }
        }
        if (hit) break;
      }
      cur = readyPage;
    }
    const done = !running && (log.indexOf('✅') >= 0 || log.indexOf('تمام شد') >= 0);
    if (!running && !done && !ph) {
      if (host.__mp) { host.innerHTML = ''; host.__mp = ''; }
      return;
    }
    let cls = '', pct = 0, now = 0;
    if (done) { cls = ' done'; pct = 100; now = tot; }
    else if (!running && ph === 'خطا') {
      cls = ' err';
      pct = tot > 0 ? Math.min(100, Math.floor(cur * 100 / tot)) : 0;
      now = cur;
    } else {
      now = tot > 0 ? Math.min(cur, tot) : cur;
      pct = tot > 0 ? Math.floor(now * 100 / tot) : 0;
    }
    let txt;
    if (done) {
      txt = '✅ تمام شد — ' + (tot > 0 ? tot : cur) + ' صفحه'
        + (tot > 0 ? ' (' + tot + '/' + tot + ')' : '');
    } else if (!running && ph === 'خطا') {
      txt = '❌ خطا — آخرین صفحهٔ آماده: ' + cur + (tot > 0 ? ' از ' + tot : '');
    } else if (ph) {
      if (tot > 0) {
        if (unit === 'صفحهٔ') txt = '📊 ' + ph + ' — صفحهٔ ' + now + ' از ' + tot + ' (' + pct + '٪)';
        else txt = '📊 ' + ph + ' — ' + now + ' از ' + tot + (unit ? ' ' + unit : '') + ' (' + pct + '٪)';
      } else txt = '📊 ' + ph + '…';
    } else txt = '📊 در حال شروع…';
    const html = '<div class="mprog"><div class="mprog-track">'
      + '<div class="mprog-fill' + cls + '" style="width:' + pct + '%"></div></div>'
      + '<div class="mprog-txt">' + txt + '</div></div>';
    if (host.__mp === html) return;
    host.__mp = html;
    host.innerHTML = html;
  } catch (e) {}
};
try { window.__mangaUpdateProg('', ''); } catch (e) {}
}
""".replace("__PROG_RES__", _prog_res_json).replace("__PROG_PHASES__", _prog_phases_json)
        try:
            demo.load(None, None, None, js=_prog_js)
        except Exception:
            try:
                demo.load(js=_prog_js)
            except Exception:
                pass
        _qtips_js = """
() => {
  const T = __QTIP_JSON__;
  const hideAll = () => {
    document.querySelectorAll('div.k3tip').forEach((el) => {
      if (el.__t) clearTimeout(el.__t);
      el.remove();
    });
  };
  const show = (btn, text) => {
    hideAll();
    const tip = document.createElement('div');
    tip.className = 'k3tip';
    tip.textContent = text;
    document.body.appendChild(tip);
    const r = btn.getBoundingClientRect();
    let x = r.left + (r.width / 2) - (tip.offsetWidth / 2);
    x = Math.max(8, Math.min(x, window.innerWidth - tip.offsetWidth - 8));
    let y = r.bottom + 8;
    if (y + tip.offsetHeight > window.innerHeight - 8)
      y = Math.max(8, r.top - tip.offsetHeight - 8);
    tip.style.left = x + 'px';
    tip.style.top = y + 'px';
    tip.__src = btn;
    tip.__t = setTimeout(() => tip.remove(), 10000);
  };
  const attach = () => {
    for (const id in T) {
      const root = document.getElementById(id);
      if (!root || root.querySelector('button.k3q')) continue;
      const lab = root.querySelector('label')
        || root.querySelector('div.container > span')
        || root.querySelector('span.label-wrap')
        || root;
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'k3q';
      btn.textContent = '؟';
      btn.title = '?';
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        const cur = document.querySelector('div.k3tip');
        if (cur && cur.__src === btn) {
          if (cur.__t) clearTimeout(cur.__t);
          cur.remove();
          return;
        }
        show(btn, T[id]);
      });
      lab.appendChild(btn);
    }
  };
  attach();
  const mo = new MutationObserver(() => {
    try { attach(); } catch (err) {}
  });
  mo.observe(document.body, { childList: true, subtree: true });
  document.addEventListener('click', (e) => {
    try {
      if (!e.target || !e.target.closest) return;
      if (e.target.closest('button.k3q')) return;
      hideAll();
    } catch (err) {}
  }, true);
}
""".replace("__QTIP_JSON__", _qtip_json)
        try:
            demo.load(None, None, None, js=_qtips_js)
        except Exception:
            try:
                demo.load(js=_qtips_js)
            except Exception:
                pass

        gr.Markdown(
            "<div style='text-align:center; opacity:.45; margin-top:16px'>"
            f"مانگا مترجم PRO v{APP_VER} · RT-DETR + Gemini/… + LaMa-Manga · اجرا روی CPU</div>"
        )

        gr.HTML(
            """
<div class="credit">
  <a href="https://t.me/amir_wolf512" target="_blank" rel="noopener"
     title="کانال تلگرام سازنده">
    <svg viewBox="0 0 24 24"><path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71L12.6 16.3l-1.99 1.93c-.23.23-.42.42-.83.42z"/></svg>
    سازنده
  </a>
  <a href="https://github.com/amirwolf5122/Manga-AutoTranslate" target="_blank" rel="noopener"
     title="سورس پروژه در گیت‌هاب">
    <img class="gh-avatar" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACQAAAAkCAYAAADhAJiYAAALoklEQVR42rWYa5Bcx13Ff9197507MzvvfUmr3dVqJdkqeW2tpJhEctZ62OUIIjlJYRIeRQwx4Qu4oAguOx9CIIaqUFQgMRAnOBgIDzsJRQJUnAplJRBDDI4fshVZL6/W69G+tLszs/O8j+7mw2hlO3YcY6Cruqbmzr09p/t/+txzWvAWm7XWvsFvSCnFWxn3f/RQq9WyzWaTMIww2tButzBYpBB4iQSJhEcqmSKbzbxqaCGE+D8FdP/9D9j62hrVapVLly5RrVWoNxpUKhWazRZKKZRSJJMp8tkeejI9bNu6jX379jM2voXegT7yuRzOmwD2I2+440Mfts1mk7V6nVazSaw1sY6J4xhrLX19fdRqVayGUqkXIQQzs7NoLNl0hq2jI+wcHWPH1m309vdxw63vEm8J0O23/6JdXV2l3qgThiEIEEi01sRxDIAxhmKhQBDFCKVIJVPUKzWSAorCJR9DBvCLOdbSLjKTx8+mcFI+9/7uveJNA3rn1EEbRyFCCJTjIIRAa00YRlhrEEIiBWgB1hgSGpx2hG13SCmHfCZDb38v/eMjbN+9m+3X7SCT76Gx1iCdSpPP5fGTaXKF4mv+3/nBC/v2v9Naa3A9DyEEcRwThuFlIAopHYSlWxLlUAhigmab4vAgYzt3sHPPBFt2bGdwZJhCPk+jViPl+fTksmhrWFxYIIpjStk0q8vztti7QbwhIKXUlXJEUYTWGgApHAQCKQSRgM1eip5akxVP8sHf+Qh73349A/19JFyXMIpQrosxhmQyxfzcPIUgwDqCXKlIdaXK9HPPklKvrY585ZepA4csQBzHBEGA0RopJUoqpOh+xkIwkcwz0IyZVjG/9smPccvNh1DWIiyEYUS72SJotrDGonWMn/TRVuNYgelEDAwMki0U6S/18vWH/8a+LqADh2+yAq6Q1hiDEAKJRAoHRykiYdmayjBuXZ7Tde7+vY9x/XWTLK1UCKKQThSBkijXIY7j7mRcl1w+h6dcMtkssYmxxlLcOMzxJ05w592/xWfu+2P7GkD1epMwDNFaI6Ui5adxlIcQEiUEsRRkHY+pTB/Hy9P80l2/wr69kzi+T211GQeBCSKklAgpEUJgsSS8BFIpVqurOJ5Lo9mkVqvgOi5tKwg1fO+JJ169Qldt32nrtTXiWGO0QQCO4yDlZbxSoHXMTYUBnpyZZvzQO3jfkXfRbLVZnL/I4tlTuI6D47lYbbHaYG33FQKGdrvNU//2LS4tLpBMpgmaLcKoweHDN7J3zx7m5xY4/8K0vQLIGIOJNVEQo5TCGkOr1equlpC0dcxkKodsBVzoUdzzm3fSiTSdIGLxzEm2DQ8ThwGRjpHWEnZCpFTYKMZ1EizPzTGxZYT506doN5sIR1Gr1sj05Ji6cT/li3PMzc29vELWWqy1dDptsKJ7WQgEEBpDr3S5Nlnk25U57vnE3YxtHkHHEbZeYffevWyeuIZOvY6OYywWKQWOUgghqFcr+FJw9cFj7LhuJ83qMpmeNDqMiOOAqal9JFNJYt0VW2f79p3WXiZwGIbEcYzjOBhjiYUBY7ghv5En58rsv+3Hedu1Ezx34gTzZ8/SaAc8c3aa0c0jRJ0AsVKhVCyS6kkTdAISbpJnn36KC7MzfP34cVQQsmV0M7l8L8rzWF5e5Bvf+CYHDkxRyOV5qTxnnb6BPi6+VMZzPbTWBEHQ5Y6xdNBcl8xhgg7lguRXDx/gP7/zX3zhTz7HC2fPUMhmOffCBXbsexu/ftdHGE6nCTsB1coql5YvMT07y32f/BSnn3yam257DwemDnH/Zx/gnqFhJvbs5plnTvDQ3/09W7dtxnEcrDHID9/xIeI4uuJjwjAEa4mx5IRiIlngsZUFfu72nyHbk6F30xDDW0cR7YAbDxzkmpFNlMKI7dvHgYhaZQmCFqMjGwgbNUZyJQ7t3s3Bt+/nF375g/zs+3+S4fFxojDkob/4a6yx9Pb1USyWuiW79rprSKfTBJ0IIQSO0xXv2Bp2pkvMNRvITX3ccvAgmXyBnkaTY8eOMDW6Fen5HLn3E/RvG2agvw+LRimJclywivfe+l52DI0SaY11HB790pcpbhxgcHCIh+//MzpPnSGfyzC5a5JEIsHq6ipOqVikVCwyMzNLOp0mkUhgsLgIBt0UJ+oLHHn/+7qmy8LSwjyedNjzEwfJ9pfw0ykcz8MYCdJDCDCmK7BWukwcPMi5s6fwpMOp8xfYtWWcZ08+zTcf+ReuH9jIxeYq41u3oXXcFWLfT5PJZNFak06nu/wRAkdIktKho2PmFhaYPj+NjjWFnhS+MlSaDbxcBqUkOgzR1hDHAVEUIxC4roub8Ig7HTYNjXD6zDmKuRzN0HDnnXfx/FwZXMm2Qolz0y/AZa1WR48e+/jp58+glEOn08F1XSSSEEPaURSky5cee4xmfY29e3fRaLUoOIIUhmajgZ/qwfF8VEKh3B6Um8SagKWlZSq1Oo1mi+OPHufzD/wVEYYvfvFhhJVEwrLFS5IoFjhXWWHy2gkSvo+ampr6+Plz5xkb20wURbTbbRxH4SiHitUMSo96p82ZxUVKuSwmCij4PSRdF1Or0lxcZLk8x4lnTvL4fzzO6bPPM7+4xKbhMUqlPjLZHBPX7uIDP/0BMtkM1lrmlxaRK1UKKsFS3ufosWNsGhoijnXXoH3ta/9kn37qaSrVGmdOn2F+fgFrNbGFPs/jhnQvXz17ktE9O/jnv/wcL504CWkfIk3SwjNnznLfPzzCyVNn2b1nF3/06T9kaNPQFfe3HlDWLfWLL83y6N9+hRcvLXHbHT/PQLGfeqPJ+Pjm7h1LS8s2ikJWlpcpl8t897uPoxwPRwk6ccx4ogcRBHz5e4+zf+c2furGdzAyOYlbKhKv1alXqxz/1nf47U/9Kb9x990cPnwTKyvLjAxvxHFcEr6P4yik7Frgdc9VXatRW62ijUUIwZYtlwFNT89Yx5EopfA8l97e3le52+VqhZXlCstzi3z7+KPU5mYo9GTYsG0Lu39sL1dffRWe6/Dg5x8kv3GUyclJWs0GjuqCSGcy3R0kJYlEAmstSkoy2SzVapVqdQ0QjI2NvBxLLsxcsJ7rMTAwgDEWY7pO0XVdpJQEnQ4XZl4kl81z6vvf56P3fJTDh29mdnaao8eO8O5jR0mme5CoHxoe1zkaBAHVahXf99mwYSO1WoW+vn7xKgvruQ6Dg4PEcVcPlFI4jkO9XicIAjKZDIODA1wsXyRfLJAv9XLk3bcwMbET3091Z24MBnMFwCtjmBACz/PwPA9rLblcjtXVVU6fPk1fX+m1nnpoaFi02nUrUEjZBbO4uIi1lt7eXpRSJBIeuVyWmZlZkkkHrQPy+QJRFF4RtvUupeQH0/a6q1gv3YYNG1AKBgY2/vCs1mw2bBxHdnZ21i4sLFhrrTXGXOnWWhvHsf3zBx+wyyvzNgwjGwSBjaLIRlFktdY21rENw+BVz72yr66s2GqlYo3R9g1NPoBUgkuXlmi1WvT39xNFEca8XIZOp4NSivfceitrtSbadCOS1gZjDFJK5i+W+cwf/D76cvm5vDJaa4QQ/Pu/HucrDz+EEJIfCSjpp8XaWoNSqfeKaXqlljSbTcrlMqlUBt9Psrq6BEJjbBe4tRbPS/DihRnCqOsihJRIKa+8uDP5fNc5vk7Wd16vbFdddZVoNBpWxy9rxjoxS6USa2trlMtlfN+nXm+T9NskUwmM0WitSPg+Y1u3XuFMo1Enjg3WGpJJn41Dwxw4dLN4S4cNQRBYeXmG6xMSQmCtZWVlhaWlFaKozdiWTbiu1zV4QuEn0wi6xF6YX8BYQ61WZdeuSfG/Po6Josi+3u5Zz/zlcplO0KJYyOInfZRyEUgcz0UqhbpciDdzTiTfDCDXdYXjOK8ZbJ3Eo6OjDG0cpt2OWV5epdlsYKThpfPneeSzX0Bcbvx/tlduY621XW8X5y7a41/9R/tWx/1vBfDPJ2Nt0RQAAAAASUVORK5CYII=" width="22" height="22" alt="gh" />
    سورس
  </a>
  <button type="button" class="credit-reset" id="manga_reset_all"
          title="پاک کردنِ همهٔ تنظیماتِ ذخیره‌شده (کلیدها، مدل‌ها، فرم) و بازگشت به پیش‌فرض">
    ↺ ریست
  </button>
</div>
<div class="support" id="manga_support">
  <button type="button" class="support-toggle" id="manga_support_toggle"
          aria-expanded="false" aria-controls="manga_support_body">
    <span>حمایت مالی</span>
    <span class="support-kao">ヾ(•ω•`)o</span>
    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 15.4 5.6 9l1.4-1.4 5 5 5-5L18.4 9z"/></svg>
  </button>
  <div class="support-body" id="manga_support_body">
    <div class="support-row ton">
      <span class="support-net">TON</span>
      <span class="support-addr" data-addr="UQBScvayaxagwTfRBhlLNaqw-sZuadlnBjSvn8OJz7XZJJzT"
            title="برای کپی کلیک کنید">UQBScvayaxagwTfRBhlLNaqw-sZuadlnBjSvn8OJz7XZJJzT</span>
      <button type="button" class="support-copy"
              data-addr="UQBScvayaxagwTfRBhlLNaqw-sZuadlnBjSvn8OJz7XZJJzT">کپی</button>
    </div>
    <div class="support-row trx">
      <span class="support-net">TRX</span>
      <span class="support-addr" data-addr="TMmLTaCjaW1L2xWZmpR2EBeNyCawCzEkwa"
            title="برای کپی کلیک کنید">TMmLTaCjaW1L2xWZmpR2EBeNyCawCzEkwa</span>
      <button type="button" class="support-copy"
              data-addr="TMmLTaCjaW1L2xWZmpR2EBeNyCawCzEkwa">کپی</button>
    </div>
  </div>
</div>
"""
        )

        _support_js = """
() => {
  const copied = (btn) => {
    if (!btn) return;
    const old = btn.textContent;
    btn.textContent = 'کپی شد ✓';
    btn.classList.add('ok');
    setTimeout(() => {
      btn.textContent = old;
      btn.classList.remove('ok');
    }, 1500);
  };
  const fallbackCopy = (txt, btn) => {
    try {
      const ta = document.createElement('textarea');
      ta.value = txt;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.focus(); ta.select();
      document.execCommand('copy');
      ta.remove();
      copied(btn);
    } catch (err) {}
  };
  document.addEventListener('click', (e) => {
    try {
      const t = e.target && e.target.closest
        ? e.target.closest('.support-copy, .support-addr, .support-toggle') : null;
      if (!t) return;
      e.preventDefault();
      e.stopPropagation();
      if (t.classList.contains('support-toggle')) {
        const box = t.closest('.support');
        if (!box) return;
        const open = box.classList.toggle('open');
        t.setAttribute('aria-expanded', open ? 'true' : 'false');
        return;
      }
      const addr = t.getAttribute('data-addr');
      if (!addr) return;
      let btn = t.classList.contains('support-copy')
        ? t : (t.parentElement
               ? t.parentElement.querySelector('.support-copy') : null);
      try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(addr).then(() => copied(btn),
            () => fallbackCopy(addr, btn));
          return;
        }
      } catch (err) {}
      fallbackCopy(addr, btn);
    } catch (err) {}
  }, true);
  const tryBindReset = () => {
    const btn = document.getElementById('manga_reset_all');
    if (!btn || btn.__bound) return;
    btn.__bound = true;
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      const ok = window.confirm(
        'همهٔ تنظیماتِ ذخیره‌شده (کلیدها، مدل‌ها، فرم، واژه‌نامه، نشست) پاک شود و همه‌چیز به حالتِ پیش‌فرض برگردد؟');
      if (!ok) return;
      try {
        const kill = [];
        for (let i = 0; i < localStorage.length; i++) {
          const k = localStorage.key(i);
          if (k && (k.indexOf('manga') === 0 || k === 'mt_last_site')) kill.push(k);
        }
        kill.forEach((k) => { try { localStorage.removeItem(k); } catch (err) {} });
      } catch (err) {}
      try { sessionStorage.clear(); } catch (err) {}
      window.location.reload();
    });
  };
  tryBindReset();
  const moR = new MutationObserver(tryBindReset);
  moR.observe(document.body, { childList: true, subtree: true });
}
"""
        try:
            demo.load(None, None, None, js=_support_js)
        except Exception:
            try:
                demo.load(js=_support_js)
            except Exception:
                pass


    on_colab = ("google.colab" in sys.modules or bool(os.environ.get("COLAB_RELEASE_TAG")))
    on_codespace = _detect_codespace()
    codespace_name = (os.environ.get("CODESPACE_NAME")
                      or _hostname_codespace_name() or "")
    if on_codespace:
        print("[i] GitHub Codespaces: لینک عمومی gradio.live پایین را باز کنید.")
        if codespace_name:
            print(f"[i] پشتیبان: https://{codespace_name}-7860.app.github.dev")
    print(f"[*] فونت اصلی: {find_font() or 'پیدا نشد'}")
    launch_kw = {}
    if _gradio_major() >= 6:
        launch_kw["theme"] = gr.themes.Soft(primary_hue="indigo", neutral_hue="slate")
        launch_kw["css"] = WEB_CSS_RUNTIME
    _blocked_paths = None
    if _web_host():
        _blocked_paths = [str(CUSTOM_MODELS_PATH), str(CFG_PATH), str(HIST_PATH)]
        print("[🛡] میزبانِ وبِ عمومی: فایلهایِ حساسِ workspace از /file= بسته شدند.")
    _launch_kw = dict(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("MANGA_APP_PORT", "7860")),
        share=on_colab or on_codespace or (not has_display()),
        inline=on_colab,
        show_error=True,
        allowed_paths=[str(WORK_DIR), str(OUT_DIR), str(UPLOAD_DIR), str(FONT_DIR)],
        blocked_paths=_blocked_paths,
    )
    _launch_kw.update(launch_kw)
    try:
        demo.queue(max_size=64).launch(**_launch_kw)
    except ValueError as _ve:
        if "localhost" not in str(_ve).lower():
            raise
        print("[!] پروکسیِ سیستم چکِ لوکال‌هاست را سد کرد — تلاشِ دوباره…")
        _no_proxy_localhost()
        demo.queue(max_size=64).launch(**_launch_kw)

def main():
    ensure_dirs()
    args = sys.argv[1:]

    if not any(a in ("--web", "-h", "--help") for a in args):
        auto_update_on_start(log=print)

    if not manga_py_ok() and not any(a in ("--web", "-h", "--help") for a in args):
        print(MANGA_MIXED_MSG)
        if os.name == "nt":
            try:
                import tkinter as tk
                from tkinter import messagebox
                r = tk.Tk(); r.withdraw()
                messagebox.showerror(APP_NAME, MANGA_MIXED_MSG)
            except Exception:
                pass
        sys.exit(1)

    if args and args[0] == "--":
        run_cli(args[1:])
        return
    if "--cli" in args and "-i" not in args and "--input" not in args:
        run_cli([])
        return
    if any(a in ("-i", "--input", "-h", "--help") for a in args):
        run_cli(args)
        return
    if "--web" in args:
        run_web()
        return
    if "--desktop" in args:
        run_desktop()
        return

    on_colab = "google.colab" in sys.modules or bool(os.environ.get("COLAB_RELEASE_TAG"))
    headless = (not has_display()) or bool(os.environ.get("SSH_CONNECTION")) or on_colab
    if headless:
        print("[*] محیط بدون دسکتاپ → رابط وب")
        try:
            run_web()
        except KeyboardInterrupt:
            pass
        return

    try:
        run_desktop()
    except Exception as e:
        print(f"[!] دسکتاپ ممکن نشد ({e}) → رابط وب")
        run_web()

if __name__ == "__main__":
    main()
