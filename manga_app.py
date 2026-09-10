#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import queue
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime

APP_NAME = "مانگا مترجم"
APP_VER = "1.4"
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
PROVIDERS = ["gemini", "openai", "chatgpt", "deepseek", "groq",
             "xai", "grok", "together", "openrouter", "ollama"]

DEFAULT_GEMINI_KEYS = []#",".join(["123:])


C_BG = "#060607"
C_BG2 = "#101014"
C_CARD = "#0d0d10"
C_LINE = "#1f1f24"
C_TXT = "#e8e6e1"
C_MUT = "#97948c"
C_ACC = "#ff4a3d"
ACCENT = C_ACC
C_OK = "#38c98a"
C_ERR = "#ff6a5e"



FONT_BUNDLES = [
    ("normal",       "Vazirmatn-Bold.ttf", "کودک — متن عادی حباب", [
        "https://raw.githubusercontent.com/rastikerdar/vazirmatn/master/fonts/ttf/Vazirmatn-Bold.ttf",
    ]),
    ("free_text",    "Vazirmatn-Regular.ttf", "متن بیرون حباب", [
        "https://raw.githubusercontent.com/rastikerdar/vazirmatn/master/fonts/ttf/Vazirmatn-Regular.ttf",
    ]),
    ("shout",        "Lalezar-Regular.ttf", "داد خشم", [
        "https://raw.githubusercontent.com/amirwolf5122/Manga-AutoTranslate/main/fonts/Lalezar-Regular.ttf",
        "https://raw.githubusercontent.com/rastikerdar/shabnam-font/master/dist/Shabnam-Bold.ttf",
    ]),
    ("comedy_shout", "Gandom.ttf", "داد کمدی", [
        "https://raw.githubusercontent.com/rastikerdar/gandom-font/master/dist/Gandom.ttf",
        "https://raw.githubusercontent.com/rastikerdar/shabnam-font/master/dist/Shabnam-Bold.ttf",
    ]),
    ("whisper",      "Nahid.ttf", "زمزمه دست‌نویس", [
        "https://raw.githubusercontent.com/rastikerdar/nahid-font/master/dist/Nahid.ttf",
        "https://raw.githubusercontent.com/rastikerdar/sahel-font/master/dist/Sahel.ttf",
    ]),
    ("thought",      "Samim-Bold.ttf", "تفکر ابری", [
        "https://raw.githubusercontent.com/rastikerdar/samim-font/master/dist/Samim-Bold.ttf",
    ]),
    ("system",       "Sahel-Bold.ttf", "UI سیستم/تگ", [
        "https://raw.githubusercontent.com/rastikerdar/sahel-font/master/dist/Sahel-Bold.ttf",
    ]),
    ("letter",       "Amiri-Regular.ttf", "نامه/طومار", [
        "https://raw.githubusercontent.com/google/fonts/main/ofl/amiri/Amiri-Regular.ttf",
    ]),
    ("narrator",     "Shabnam-Bold.ttf", "راوی مستطیل", [
        "https://raw.githubusercontent.com/rastikerdar/shabnam-font/master/dist/Shabnam-Bold.ttf",
    ]),
]


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
            return json.load(f)
    except Exception:
        return {}


def save_config(cfg: dict) -> None:
    try:
        with open(CFG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


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


def system_info() -> str:
    import platform
    lines = [
        f"پایتون: {platform.python_version()} — {platform.system()} {platform.release()}",
        f"هستهٔ CPU: {os.cpu_count()}",
    ]
    try:
        import onnxruntime as ort
        lines.append("ONNX Runtime: " + ort.__version__ + " | " +
                     ", ".join(ort.get_available_providers()))
    except Exception:
        lines.append("ONNX Runtime: نصب نیست")
    try:
        import torch  
        lines.append("GPU (CUDA): ✅")
    except Exception:
        lines.append("GPU (CUDA): —")
    if os.path.isdir(MODELS_DIR):
        lines.append("مدل‌های کش‌شده:")
        for f in sorted(os.listdir(MODELS_DIR)):
            p = os.path.join(MODELS_DIR, f)
            if os.path.isfile(p):
                lines.append(f"  • {f} — {human_size(os.path.getsize(p))}")
    else:
        lines.append("مدل‌های کش‌شده: — (بار اول دانلود می‌شوند)")
    fonts = os.listdir(FONT_DIR) if os.path.isdir(FONT_DIR) else []
    lines.append(f"فونت‌ها: {len(fonts)} فایل در fonts/")
    try:
        du = shutil.disk_usage(HERE)
        lines.append(f"فضای آزاد: {human_size(du.free)}")
    except Exception:
        pass
    return "\n".join(lines)



def smart_output_base(input_path: str) -> str:
    
    raw = (input_path or "").strip()
    if not raw:
        return "chapter_fa"
    is_url = raw.lower().startswith(("http://", "https://"))
    if is_url:
        from urllib.parse import urlparse, unquote
        path_u = unquote(urlparse(raw).path).strip("/")
        parts = [p for p in path_u.split("/") if p]
        base = "chapter"
        if parts:
            slug = parts[-1]
            m = re.search(
                r"(.+?-chapter[-_]?(?:\d+|\*))(?:[-_].*)?$",
                slug, flags=re.I,
            )
            if m:
                base = m.group(1)
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
                if len(parts) >= 2:
                    cand = "-".join(parts[-2:])
                    base = cand if len(cand) >= 4 else slug
                else:
                    base = slug
        base = re.sub(r"\*+", "", base)
        base = re.sub(r"[^\w\-.]+", "-", base)
        base = re.sub(r"-{2,}", "-", base).strip("-._") or "chapter"
    else:
        path_only = raw.rstrip("/\\")
        base = os.path.splitext(os.path.basename(path_only))[0] or "output"
        base = re.sub(r"[^\w\-.]+", "-", base).strip("-._") or "output"
    if not base.lower().endswith("_fa"):
        base = base + "_fa"
    return base


def append_history(entry: dict) -> None:
    try:
        with open(HIST_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def history_text() -> str:
    if not os.path.isfile(HIST_PATH):
        return "هنوز اجرایی ثبت نشده."
    rows = []
    try:
        with open(HIST_PATH, encoding="utf-8") as f:
            for line in f:
                e = json.loads(line)
                rows.append(f"{e.get('time','')}  |  "
                            f"{os.path.basename(str(e.get('input','')))[:36]:36}  |  "
                            f"{e.get('status','')}  |  {e.get('duration','')}")
    except Exception:
        return "تاریخچه خوانده نشد."
    return "\n".join(reversed(rows[-60:])) or "هنوز اجرایی ثبت نشده."


def open_path(path: str):
    try:
        if os.name == "nt":
            os.startfile(path)  
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass


def has_display() -> bool:
    if os.name == "nt" or sys.platform == "darwin":
        return True
    return bool(os.environ.get("DISPLAY"))


HELP_TEXT = f"""راهنما — {APP_NAME} v{APP_VER}

▶ اجرا (خودکار: دسکتاپ → پنجرهٔ برنامه، Colab/Codespace → وب)
  ویندوز:            دابل‌کلیک Manga.bat
  لینوکس / مک:       ./manga.sh
  مستقیم:            python manga_app.py

▶ اجبار حالت
  python manga_app.py --web       (Colab: لینک عمومی gradio.live چاپ می‌شود)
  python manga_app.py --desktop

▶ Colab — دو فایل لازم است کنار هم باشند:
  manga.py      (فایل مترجم — همان فایل اصلی)
  manga_app.py  (برنامه)
  سپس:  !python manga_app.py
  ⚠ manga_app.py را با نام manga.py ذخیره نکنید — خطای «فایل مترجم نیست» می‌گیرید.

▶ GitHub Codespaces / SSH
  لینک عمومی خودکار چاپ می‌شود (gradio.live) — نیازی به Port Forwarding نیست.
  ⚠ سرور وب به نشست ترمینال چسبیده است: با بستن ترمینال kill می‌شود.
  برای زنده‌ماندن: tmux new -s manga 'python3 manga_app.py --web'
  (detach: Ctrl+B بعد D | بازگشت: tmux attach -t manga)

▶ فونت‌ها
  بار اول خودکار در fonts/ دانلود می‌شوند (کودک، افسانه، کروش، دست‌نویس،
  مروارید، سیستم، نامه، راوی …). برای تغییر، فقط فایل .ttf را با همان نام
  در fonts/ جایگزین کنید و برنامه را دوباره باز کنید.

▶ CLI
  python manga_app.py -- -i input -o out.pdf --font fonts/Vazirmatn-Bold.ttf --api-key KEY --cpu --lama

▶ نکات
  • کلید از aistudio.google.com / platform.openai.com / openrouter.ai — چند کلید = چرخش خودکار
  • مدل‌ها بار اول دانلود و در ~/.cache کش می‌شوند
  • تنظیمات در workspace/config.json ذخیره می‌شود
"""



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

    print("\nقالب خروجی:  1) PDF   2) ZIP   3) HTML   4) پوشهٔ تصاویر")
    f = input("انتخاب [1-4] (پیش‌فرض 1): ").strip() or "1"
    ext = {"1": ".pdf", "2": ".zip", "3": ".html", "4": ""}.get(f, ".pdf")

    print("\nارائه‌دهندهٔ AI را انتخاب کنید:")
    prov_menu = [
        ("gemini", "Google Gemini - رایگان با سهمیه"),
        ("openai", "ChatGPT / GPT"),
        ("deepseek", "DeepSeek"),
        ("groq", "Groq - سریع و رایگان"),
        ("xai", "xAI / Grok"),
        ("openrouter", "OpenRouter"),
        ("ollama", "لوکال - بدون کلید"),
        ("together", "Together AI"),
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
           "--temperature", str(float(cfg.get("temperature", 0.85))),
           "--reading-order", str(cfg.get("reading_order", "rtl"))]
    cmd += font_args()
    klist = [k.strip() for k in (keys or "").replace(";", ",").split(",") if k.strip()]
    if klist:
        cmd += ["--api-key", ",".join(klist)]
    if model:
        cmd += ["--model", model]
    cmd += ["--lama", "--cpu"]

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


def run_desktop():
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, scrolledtext

    cfg = load_config()
    q: "queue.Queue[tuple]" = queue.Queue()
    proc_holder = {"p": None}

    root = tk.Tk()
    root.title(f"{APP_NAME} v{APP_VER}")
    root.geometry("1080x780")
    root.minsize(940, 660)
    root.configure(bg=C_BG)

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    dark = {
        "TFrame": {"background": C_BG},
        "TLabelframe": {"background": C_CARD, "bordercolor": C_LINE,
                        "lightcolor": C_LINE, "darkcolor": C_LINE},
        "TLabelframe.Label": {"background": C_CARD, "foreground": C_ACC},
        "TLabel": {"background": C_CARD, "foreground": C_TXT},
        "TButton": {"background": C_BG2, "foreground": C_TXT, "padding": (10, 6),
                    "bordercolor": C_LINE, "lightcolor": C_BG2, "darkcolor": C_BG2},
        "TEntry": {"fieldbackground": C_BG2, "foreground": C_TXT,
                   "insertcolor": C_TXT, "bordercolor": C_LINE,
                   "lightcolor": C_BG2, "darkcolor": C_BG2,
                   "borderwidth": 0, "relief": "flat"},
        "TCombobox": {"fieldbackground": C_BG2, "foreground": C_TXT,
                      "background": C_LINE, "arrowcolor": C_ACC,
                      "bordercolor": C_LINE, "lightcolor": C_LINE,
                      "darkcolor": C_LINE},
        "TSpinbox": {"fieldbackground": C_BG2, "foreground": C_TXT,
                     "insertcolor": C_TXT, "arrowcolor": C_ACC,
                     "bordercolor": C_LINE, "lightcolor": C_BG2, "darkcolor": C_BG2},
        "TCheckbutton": {"background": C_CARD, "foreground": C_TXT,
                         "indicatorbackground": C_BG2, "indicatorforeground": C_ACC},
        "TRadiobutton": {"background": C_CARD, "foreground": C_TXT,
                         "indicatorbackground": C_BG2, "indicatorforeground": C_ACC},
        "TNotebook": {"background": C_BG, "bordercolor": C_BG},
        "TNotebook.Tab": {"background": C_BG2, "foreground": C_MUT,
                          "padding": (18, 8)},
        "TProgressbar": {"background": C_ACC, "troughcolor": C_BG2},
        "TScrollbar": {"background": C_BG2, "troughcolor": C_BG,
                       "bordercolor": C_BG, "arrowcolor": C_MUT},
    }
    for name, kw in dark.items():
        try:
            style.configure(name, **kw)
        except tk.TclError:
            pass
    style.map("TButton",
              background=[("active", "#1c1c22"), ("pressed", "#23232a")],
              bordercolor=[("active", C_ACC)])
    style.map("TSpinbox", bordercolor=[("focus", C_ACC)])
    style.map("TEntry", bordercolor=[("focus", C_ACC)])

    style.map("TCombobox",
              fieldbackground=[("readonly", C_BG2), ("active", C_BG2),
                               ("focus", C_BG2)],
              foreground=[("readonly", C_TXT), ("active", C_TXT)],
              selectbackground=[("readonly", C_BG2), ("active", C_BG2)],
              selectforeground=[("readonly", C_TXT), ("active", C_TXT)])

    root.option_add("*TCombobox*Listbox.background", C_BG2)
    root.option_add("*TCombobox*Listbox.foreground", C_TXT)
    root.option_add("*TCombobox*Listbox.selectBackground", C_ACC)
    root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
    root.option_add("*TCombobox*Listbox.font", (None, 10))
    style.map("TNotebook.Tab", background=[("selected", C_ACC)],
              foreground=[("selected", "white")])
    style.map("TCheckbutton", background=[("active", C_CARD)])
    style.map("TRadiobutton", background=[("active", C_CARD)])
    style.configure("Accent.TButton", font=(None, 11, "bold"), foreground="white",
                    background=ACCENT, padding=(16, 8))
    style.map("Accent.TButton",
              background=[("active", "#ff6a5e"), ("disabled", "#6e2019")],
              foreground=[("disabled", "#f0b8b2")])
    style.configure("TNotebook.Tab", font=(None, 10))
    style.configure("TLabelframe.Label", font=(None, 10, "bold"))

    
    head = tk.Frame(root, bg=C_BG2, highlightthickness=0, bd=0)
    head.pack(fill="x")
    stamp = tk.Label(head, text="漫", font=(None, 15, "bold"),
                     bg=ACCENT, fg="white", width=3, pady=2)
    stamp.pack(side="right", padx=(16, 10), pady=8)
    tk.Label(head, text=APP_NAME, font=(None, 14, "bold"),
             bg=C_BG2, fg=C_TXT).pack(side="right", pady=9)
    tk.Label(head, text=f"v{APP_VER}", font=("IBM Plex Mono", 9),
             bg=C_BG2, fg=C_MUT).pack(side="left", padx=10)
    status_lbl = tk.Label(head, text="● آماده", font=(None, 10, "bold"),
                          bg=C_BG2, fg=C_OK)
    status_lbl.pack(side="left", padx=4)

    nb = ttk.Notebook(root)
    nb.pack(fill="both", expand=True, padx=10, pady=10)

    
    tab = ttk.Frame(nb)
    nb.add(tab, text="🚀 ترجمه")

    def field(parent, label):
        
        ttk.Label(parent, text=label, foreground=C_MUT).pack(fill="x", pady=(6, 2))

    
    card_io = ttk.LabelFrame(tab, text=" ورودی / خروجی ", padding=12)
    card_io.pack(fill="x", padx=10, pady=(10, 6))
    field(card_io, "فایل / پوشه / URL ورودی")
    row_in = ttk.Frame(card_io); row_in.pack(fill="x")
    inp_var = tk.StringVar(value=cfg.get("last_input", ""))
    ttk.Entry(row_in, textvariable=inp_var).pack(side="left", fill="x", expand=True)

    def pick_input():
        p = filedialog.askopenfilename(
            initialdir=UPLOAD_DIR if os.path.isdir(UPLOAD_DIR) else HERE,
            filetypes=[("مانگا", "*.pdf *.zip *.cbz *.webp *.jpg *.jpeg *.png *.html"),
                       ("همه", "*.*")])
        if p:
            inp_var.set(p)
    ttk.Button(row_in, text="📁 انتخاب", command=pick_input).pack(side="left", padx=(6, 0))

    row_out = ttk.Frame(card_io); row_out.pack(fill="x", pady=(8, 0))
    fmt_var = tk.StringVar(value=cfg.get("out_fmt", "PDF"))
    ttk.Label(row_out, text="قالب:").pack(side="right", padx=(0, 4))
    for v in ("PDF", "ZIP", "HTML", "پوشهٔ تصاویر"):
        ttk.Radiobutton(row_out, text=v, value=v, variable=fmt_var).pack(side="right", padx=4)
    quality_var = tk.IntVar(value=int(cfg.get("quality", 92)))
    ttk.Label(row_out, text="کیفیت:").pack(side="left", padx=(0, 4))
    ttk.Spinbox(row_out, from_=60, to=100, textvariable=quality_var, width=5).pack(side="left")

    
    card_ai = ttk.LabelFrame(tab, text=" حساب و مدل ", padding=12)
    card_ai.pack(fill="x", padx=10, pady=6)
    row_ai1 = ttk.Frame(card_ai); row_ai1.pack(fill="x")
    prov_var = tk.StringVar(value=cfg.get("provider", "gemini"))
    ttk.Label(row_ai1, text="ارائه‌دهنده:").pack(side="right", padx=(0, 4))
    ttk.Combobox(row_ai1, textvariable=prov_var, values=PROVIDERS,
                 state="readonly", width=12).pack(side="right", padx=(0, 16))
    model_var = tk.StringVar(value=cfg.get("model", ""))
    ttk.Label(row_ai1, text="مدل (خالی = پیش‌فرض):").pack(side="right", padx=(0, 4))
    ttk.Entry(row_ai1, textvariable=model_var, width=22).pack(side="right")
    field(card_ai, "کلید API (چند کلید = با کاما، چرخش خودکار)")
    keys_var = tk.StringVar(value=cfg.get("api_keys") or default_keys())
    keys_entry = ttk.Entry(card_ai, textvariable=keys_var, show="•")
    keys_entry.pack(fill="x")

    def _persist_api_desktop(*_a):
        try:
            cur = load_config()
            cur["api_keys"] = keys_var.get()
            cur["provider"] = prov_var.get()
            cur["model"] = model_var.get()
            save_config(cur)
        except Exception:
            pass

    _api_save_job = {"id": None}

    def _schedule_api_save(*_a):
        try:
            if _api_save_job["id"] is not None:
                root.after_cancel(_api_save_job["id"])
        except Exception:
            pass
        _api_save_job["id"] = root.after(300, _persist_api_desktop)

    keys_var.trace_add("write", _schedule_api_save)
    prov_var.trace_add("write", _schedule_api_save)
    model_var.trace_add("write", _schedule_api_save)

    
    card_font = ttk.LabelFrame(tab, text=" فونت‌های لحن ", padding=10)
    card_font.pack(fill="x", padx=10, pady=6)
    font_vars = {"main": tk.StringVar(value=cfg.get("font") or find_font())}
    row_fm = ttk.Frame(card_font); row_fm.pack(fill="x")
    ttk.Label(row_fm, text="اصلی (پیش‌فرض):", foreground=C_MUT).pack(side="right", padx=(0, 4))
    ttk.Entry(row_fm, textvariable=font_vars["main"]).pack(side="right", fill="x",
                                                           expand=True, padx=(0, 4))

    def mk_pick(var):
        def _p():
            pth = filedialog.askopenfilename(filetypes=[("فونت", "*.ttf *.otf")])
            if pth:
                var.set(pth)
        return _p
    ttk.Button(row_fm, text="…", width=3,
               command=mk_pick(font_vars["main"])).pack(side="left")

    
    SLOT_LABELS = {
        "normal": "کودک (عادی)", "shout": "افسانه (خشم)", "comedy_shout": "کروش (کمدی)",
        "whisper": "زمزمه", "thought": "تفکر", "system": "سیستم/تگ",
        "letter": "نامه/طومار", "narrator": "راوی", "free_text": "متن آزاد",
    }
    font_slots = {}
    for slot, fname, _desc, _urls in FONT_BUNDLES:
        dflt = os.path.join(FONT_DIR, fname) if os.path.isfile(os.path.join(FONT_DIR, fname)) else ""
        if dflt and not _font_persian_ok(dflt):
            dflt = ""
        font_slots[slot] = tk.StringVar(value=dflt)

    def open_font_editor():
        win = tk.Toplevel(root)
        win.title("ویرایش فونت‌های لحن")
        win.geometry("820x420")
        win.configure(bg=C_BG)
        tk.Label(win, text="مسیر هر فونت را عوض کنید یا با … انتخاب کنید",
                 bg=C_BG, fg=C_MUT).pack(anchor="e", padx=12, pady=(10, 4))
        body = tk.Frame(win, bg=C_BG)
        body.pack(fill="both", expand=True, padx=12)
        for idx, (slot, _fname, _d, _u) in enumerate(FONT_BUNDLES):
            r, c = divmod(idx, 2)
            cell = tk.Frame(body, bg=C_BG)
            cell.grid(row=r, column=(1 - c), sticky="ew", padx=4, pady=3)
            body.columnconfigure(1 - c, weight=1)
            tk.Label(cell, text=f"{SLOT_LABELS.get(slot, slot)}:",
                     bg=C_BG, fg=C_TXT).pack(side="right", padx=(0, 4))
            ttk.Entry(cell, textvariable=font_slots[slot]).pack(
                side="right", fill="x", expand=True)
            ttk.Button(cell, text="…", width=2,
                       command=mk_pick(font_slots[slot])).pack(side="left")
        ttk.Button(win, text="بستن", command=win.destroy).pack(pady=10)

    row_fd = ttk.Frame(card_font); row_fd.pack(fill="x", pady=(4, 0))

    def do_download_fonts():
        dl_btn.config(state="disabled")
        set_status("دانلود فونت…")

        def t():
            n = download_fonts(log=lambda m: q.put(("log", m)))
            q.put(("fonts_done", n))

        threading.Thread(target=t, daemon=True).start()

    dl_btn = ttk.Button(row_fd, text="⬇ دانلود فونت‌های گمشده", command=do_download_fonts)
    dl_btn.pack(side="left")
    ttk.Button(row_fd, text="✏️ ویرایش فونت‌های لحن",
               command=open_font_editor).pack(side="left", padx=6)

    
    card_opt = ttk.LabelFrame(tab, text=" گزینه‌ها ", padding=12)
    card_opt.pack(fill="x", padx=10, pady=6)
    row4 = ttk.Frame(card_opt); row4.pack(fill="x")
    lama_var = tk.BooleanVar(value=False)
    cpu_var = tk.BooleanVar(value=bool(cfg.get("force_cpu", False)))
    twopass_var = tk.BooleanVar(value=True)
    debug_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(row4, text="اجبار LaMa-Manga (خالی = خودکار)",
                    variable=lama_var).pack(side="right", padx=6)
    ttk.Checkbutton(row4, text="اجبار CPU", variable=cpu_var).pack(side="right", padx=6)
    ttk.Checkbutton(row4, text="OCR دومرحله‌ای", variable=twopass_var).pack(side="right", padx=6)
    ttk.Checkbutton(row4, text="دیباگ", variable=debug_var).pack(side="right", padx=6)
    row5 = ttk.Frame(card_opt); row5.pack(fill="x", pady=(8, 0))
    workers_var = tk.IntVar(value=int(cfg.get("workers", 2)))
    bubbles_var = tk.IntVar(value=int(cfg.get("bubbles", 6)))
    timeout_var = tk.IntVar(value=int(cfg.get("timeout", 40)))
    for lbl, var, a, b in (("ورکر OCR", workers_var, 1, 8),
                           ("حباب در هر درخواست", bubbles_var, 1, 12),
                           ("تایم‌اوت (ثانیه)", timeout_var, 10, 120)):
        ttk.Label(row5, text=lbl + ":").pack(side="right", padx=(12, 4))
        ttk.Spinbox(row5, from_=a, to=b, textvariable=var, width=5).pack(side="right")
    adv = ttk.Frame(card_opt)
    adv_open = {"v": False}
    def toggle_adv():
        adv_open["v"] = not adv_open["v"]
        if adv_open["v"]:
            adv.pack(fill="x", after=row5, pady=(6, 0))
            adv_btn.config(text="▲ بستن تنظیمات پیشرفته")
        else:
            adv.pack_forget()
            adv_btn.config(text="▼ تنظیمات پیشرفته")
    adv_btn = ttk.Button(row5, text="▼ تنظیمات پیشرفته", command=toggle_adv, width=22)
    adv_btn.pack(side="left", padx=6)
    row5b = ttk.Frame(adv); row5b.pack(fill="x", pady=(6, 0))
    batchw_var = tk.IntVar(value=int(cfg.get("batch_workers", 3)))
    maxre_var = tk.IntVar(value=int(cfg.get("max_retries", 8)))
    reqdelay_var = tk.DoubleVar(value=float(cfg.get("request_delay", 0)))
    temp_var = tk.DoubleVar(value=float(cfg.get("temperature", 0.85)))
    readord_var = tk.StringVar(value=str(cfg.get("reading_order", "rtl")))
    for lbl, var, a, b in (("بستهٔ ترجمهٔ موازی", batchw_var, 1, 8),
                           ("حداکثر تلاش", maxre_var, 1, 15),
                           ("تأخیر درخواست (ث)", reqdelay_var, 0, 5),
                           ("temperature", temp_var, 0, 1.5)):
        ttk.Label(row5b, text=lbl + ":").pack(side="right", padx=(12, 4))
        ttk.Spinbox(row5b, from_=a, to=b, textvariable=var, width=5,
                    increment=0.05 if a == 0 and b == 1.5 else 1).pack(side="right")
    ttk.Label(row5b, text="ترتیب خواندن:").pack(side="right", padx=(12, 4))
    ttk.Combobox(row5b, textvariable=readord_var, values=["rtl", "ltr"],
                 state="readonly", width=5).pack(side="right")

    # واژه‌نامه + بریف داستان
    row5c = ttk.Frame(adv); row5c.pack(fill="x", pady=(6, 0))
    brief_var = tk.BooleanVar(value=bool(cfg.get("story_brief", True)))
    ttk.Label(row5c, text="واژه‌نامهٔ اسامی (هر خط: English=فارسی):").pack(anchor="e")
    glos_txt = tk.Text(adv, height=4, font=("Consolas", 10), bg=C_CARD, fg=C_TXT)
    glos_txt.pack(fill="x", pady=(2, 4))
    glos_txt.insert("1.0", str(cfg.get("glossary_text", "") or ""))
    ttk.Checkbutton(row5c, text="بریف داستان قبل از ترجمه (لحن شخصیت‌ها حفظ شود)",
                    variable=brief_var).pack(anchor="e")

    
    row6 = ttk.Frame(tab); row6.pack(fill="x", padx=10, pady=(4, 2))
    run_btn = ttk.Button(row6, text="🚀  شروع ترجمه", style="Accent.TButton")
    run_btn.pack(side="right")
    stop_btn = ttk.Button(row6, text="⏹ توقف", state="disabled")
    stop_btn.pack(side="right", padx=6)
    read_btn = ttk.Button(row6, text="📖 خواندن", state="disabled",
                          command=lambda: open_reader())
    read_btn.pack(side="left")
    open_btn = ttk.Button(row6, text="📂 خروجی", state="disabled")
    open_btn.pack(side="left")
    out_path_holder = {"p": "", "d": ""}
    progress = ttk.Progressbar(tab, mode="indeterminate")

    
    tab_log = ttk.Frame(nb)
    row_log = ttk.Frame(tab_log); row_log.pack(fill="x", padx=10, pady=(8, 4))
    copy_btn = ttk.Button(row_log, text="📋 کپی لاگ")
    log_box = scrolledtext.ScrolledText(tab_log, height=26, font=("Consolas", 9),
                                        bg="#0a0f1c", fg="#cbd5e1",
                                        insertbackground="#e2e8f0", wrap="none",
                                        relief="flat")
    log_box.pack(fill="both", expand=True, padx=10, pady=(2, 8))
    log_newest_top = tk.BooleanVar(value=False)
    _log_count = {"n": 0}

    def on_log_key(e):
        
        if e.state & 0x0004 and e.keysym.lower() in ("c", "a"):
            return None
        return "break"
    log_box.bind("<Key>", on_log_key)

    def log_write(msg):
        log_box.config(state="normal")
        if log_newest_top.get():
            log_box.insert("1.0", msg + "\n")
        else:
            log_box.insert("end", msg + "\n")
            log_box.see("end")
        log_box.config(state="disabled")

    def toggle_log_dir():
        log_newest_top.set(not log_newest_top.get())
        dir_btn.config(text="⬆ جدید در بالا" if log_newest_top.get() else "⬇ جدید در پایین")
    dir_btn = ttk.Button(row_log, text="⬇ جدید در پایین", command=toggle_log_dir, width=14)
    dir_btn.pack(side="left", padx=6)
    ttk.Label(row_log, text="لاگ با Ctrl+C قابل کپی است", foreground=C_MUT
              ).pack(side="left", padx=8)

    def copy_log():
        txt = log_box.get("1.0", "end").strip()
        root.clipboard_clear()
        root.clipboard_append(txt)
        set_status("لاگ کپی شد")

    copy_btn.config(command=copy_log)

    
    def open_reader():
        d = out_path_holder.get("d")
        files = []
        if d and os.path.isdir(d):
            for f in sorted(os.listdir(d)):
                if f.lower().endswith((".webp", ".png", ".jpg", ".jpeg", ".bmp")):
                    files.append(os.path.join(d, f))
        p = out_path_holder.get("p")
        if not files and p and os.path.isfile(p) and \
                p.lower().endswith((".webp", ".png", ".jpg", ".jpeg")):
            files = [p]
        if not files:
            messagebox.showinfo(
                "خواندن", "فایل تصویری برای نمایش پیدا نشد.\n"
                "برای حالت خواندن، خروجی را ZIP یا «پوشهٔ تصاویر» بگیرید (PDF صفحه‌تصویری ندارد).")
            return
        win = tk.Toplevel(root)
        win.title("📖 حالت خواندن")
        win.geometry("920x860")
        win.configure(bg="#0a0f1c")

        from PIL import Image as PILImage, ImageTk

        bar = tk.Frame(win, bg="#10131c", highlightthickness=0)
        bar.pack(side="top", fill="x")
        zlbl = tk.Label(bar, text="۱۰۰٪", font=(None, 10, "bold"),
                        bg="#10131c", fg="#e8e6e1", width=7)

        cv = tk.Canvas(win, bg="#0a0f1c", highlightthickness=0)
        sb = ttk.Scrollbar(win, orient="vertical", command=cv.yview)
        inner = tk.Frame(cv, bg="#0a0f1c")
        inner.bind("<Configure>",
                   lambda e: cv.configure(scrollregion=cv.bbox("all")))
        win_id = cv.create_window((0, 0), window=inner, anchor="nw")
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        state = {"zoom": 1.0, "imgs": [], "full": False}

        def _on_mousewheel(e):
            cv.yview_scroll(int(-e.delta / 120), "units")

        def _on_zoom_wheel(e):
            if e.state & 0x0004:
                set_zoom(state["zoom"] * (1.15 if e.delta > 0 else 1 / 1.15))
            else:
                _on_mousewheel(e)

        def _sync_width(_e=None):
            if not state["full"]:
                cv.itemconfigure(win_id, width=cv.winfo_width())

        cv.bind("<Configure>", _sync_width)
        cv.bind_all("<MouseWheel>", _on_zoom_wheel)

        def set_zoom(z, center=True):
            z = max(0.15, min(4.0, z))
            if abs(z - state["zoom"]) < 1e-3:
                return
            if center:
                frac = cv.yview()[0]
            state["zoom"] = z
            zlbl.config(text=f"{int(z * 100)}٪")
            w = int(cv.winfo_width() or 880)
            target_w = int(w * z)
            for img0, lb in state["imgs"]:
                h = max(1, int(img0.height * target_w / img0.width))
                im2 = img0.resize((target_w, h), PILImage.LANCZOS)
                ph = ImageTk.PhotoImage(im2)
                lb.configure(image=ph, width=target_w, height=h)
                lb.image = ph
            if center:
                cv.update_idletasks()
                cv.yview_moveto(frac)

        def zi():
            set_zoom(state["zoom"] * 1.2)

        def zo():
            set_zoom(state["zoom"] / 1.2)

        def toggle_full(_e=None):
            state["full"] = not state["full"]
            win.attributes("-fullscreen", state["full"])
            if state["full"]:
                cv.itemconfigure(win_id, width=win.winfo_screenwidth())
            else:
                cv.itemconfigure(win_id, width=880)

        tk.Button(bar, text="✕", command=win.destroy, bd=0, padx=10,
                  bg="#10131c", fg="#ff4a3d", font=(None, 11, "bold"),
                  cursor="hand2", activebackground="#1c1c22",
                  activeforeground="#ff4a3d").pack(side="left")
        tk.Button(bar, text="🔍−", command=zo, bd=0, padx=8,
                  bg="#10131c", fg="#e8e6e1", font=(None, 10),
                  cursor="hand2", activebackground="#1c1c22").pack(side="left")
        tk.Button(bar, text="🔍+", command=zi, bd=0, padx=8,
                  bg="#10131c", fg="#e8e6e1", font=(None, 10),
                  cursor="hand2", activebackground="#1c1c22").pack(side="left")
        tk.Button(bar, text="⛶ فول‌اسکرین", command=toggle_full, bd=0, padx=8,
                  bg="#10131c", fg="#e8e6e1", font=(None, 10),
                  cursor="hand2", activebackground="#1c1c22").pack(side="left")
        tk.Label(bar, text="Ctrl+چرخ = زوم · دابل‌کلیک = فول‌اسکرین",
                 font=(None, 8), bg="#10131c", fg="#6a6a72").pack(side="right",
                                                                  padx=8)
        zlbl.pack(side="right")
        cv.bind("<Double-Button-1>", toggle_full)
        win.bind("<F11>", toggle_full)
        win.bind("<Escape>", lambda e: win.attributes("-fullscreen", False)
                 if state["full"] else win.destroy())

        for f in files:
            try:
                img0 = PILImage.open(f)
                w = 860
                h = max(1, int(img0.height * w / img0.width))
                ph = ImageTk.PhotoImage(img0.resize((w, h), PILImage.LANCZOS))
                lb = tk.Label(inner, image=ph, bg="#0a0f1c", cursor="fleur")
                lb.image = ph
                lb.pack(fill="x", pady=(0, 6))
                state["imgs"].append((img0, lb))
            except Exception:
                continue
        win.protocol("WM_DELETE_WINDOW", win.destroy)

    
    hist_var = tk.StringVar(value=history_text())
    hist_lbl = tk.Label(tab_log, textvariable=hist_var, justify="right", anchor="e",
                        bg=C_BG2, fg=C_MUT, font=("Consolas", 8))
    hist_lbl.pack(fill="x", padx=12, pady=(0, 10))

    def refresh_history():
        hist_var.set(history_text())

    def set_status(text, color=C_OK):
        status_lbl.config(text="● " + text, fg=color)

    def log_write(msg):
        log_box.config(state="normal")
        if log_newest_top.get():
            log_box.insert("1.0", msg + "\n")
        else:
            log_box.insert("end", msg + "\n")
            log_box.see("end")
        log_box.config(state="disabled")

    def toggle_log_dir():
        log_newest_top.set(not log_newest_top.get())
        dir_btn.config(text="⬆ جدید در بالا" if log_newest_top.get() else "⬇ جدید در پایین")

    def poll_queue():
        try:
            while True:
                kind, payload = q.get_nowait()
                if kind == "log":
                    log_write(payload)
                    refresh_history()
                elif kind == "status":
                    set_status(*payload)
                elif kind == "done":
                    out_path_holder["p"] = payload
                    open_btn.config(state="normal")
                    read_btn.config(state="normal")
                elif kind == "reader_dir":
                    out_path_holder["d"] = payload
                elif kind == "fonts_done":
                    dl_btn.config(state="normal")
                    font_vars["main"].set(find_font())
                    for slot, fname, _d, _u in FONT_BUNDLES:
                        pth = os.path.join(FONT_DIR, fname)
                        if os.path.isfile(pth):
                            font_slots[slot].set(pth)
                    log_write(f"🔤 فونت‌ها: {payload} فایل جدید دانلود شد.")
                elif kind == "finished":
                    run_btn.config(state="normal")
                    stop_btn.config(state="disabled")
                    progress.stop()
                    progress.pack_forget()
                    refresh_history()
        except queue.Empty:
            pass
        root.after(150, poll_queue)

    def on_stop():
        p = proc_holder.get("p")
        if p and p.poll() is None:
            p.terminate()

    def on_open():
        p = out_path_holder.get("p")
        if p:
            open_path(os.path.dirname(p) or p)

    def worker(src, out_v, cmd):
        t0 = time.time()
        proc = subprocess.Popen(
            cmd, cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
        )
        proc_holder["p"] = proc
        for line in proc.stdout:
            q.put(("log", line.rstrip()))
        proc.wait()
        dur = time.time() - t0
        dur_s = f"{int(dur // 60)}:{int(dur % 60):02d}"
        if proc.returncode != 0:
            append_history({"time": datetime.now().strftime("%m-%d %H:%M"),
                            "input": src, "status": f"❌ ({proc.returncode})",
                            "duration": dur_s})
            q.put(("log", f"❌ خطا — کد خروج {proc.returncode}"))
            q.put(("status", ("ناموفق", C_ERR)))
        else:
            target = out_v
            if os.path.isdir(out_v):
                fs = sorted(os.listdir(out_v))
                target = os.path.join(out_v, fs[0]) if fs else out_v
            size = os.path.getsize(target) if os.path.isfile(target) else 0
            append_history({"time": datetime.now().strftime("%m-%d %H:%M"),
                            "input": src, "status": "✅", "duration": dur_s})
            q.put(("log", f"✅ تمام شد ({dur_s}) — {human_size(size)}: {target}"))
            q.put(("status", ("موفق ✅", C_OK)))
            q.put(("done", target))
            
            cands = [out_v, out_v + ".cache" + os.sep + "out",
                     os.path.join(out_v + ".cache", "out")]
            rd = ""
            for c in cands:
                if os.path.isdir(c):
                    rd = c
                    break
            q.put(("reader_dir", rd))
        q.put(("finished", None))

    def on_run():
        src = inp_var.get().strip()
        if not src:
            messagebox.showwarning(APP_NAME, "ورودی را انتخاب کنید یا مسیر/URL بدهید.")
            return
        if not os.path.exists(src) and not src.lower().startswith(("http://", "https://")):
            messagebox.showerror(APP_NAME, "مسیر پیدا نشد:\n" + src)
            return
        font_v = font_vars["main"].get().strip() or find_font()
        if not font_v or not os.path.isfile(font_v):
            messagebox.showerror(APP_NAME, "فونت اصلی معتبر پیدا نشد.")
            return

        ext = {"PDF": ".pdf", "ZIP": ".zip", "HTML": ".html", "پوشهٔ تصاویر": ""}[fmt_var.get()]
        out_v = os.path.join(OUT_DIR, smart_output_base(src) + ext)

        save_config({"last_input": src, "out_fmt": fmt_var.get(),
                     "quality": quality_var.get(), "api_keys": keys_var.get(),
                     "model": model_var.get(), "font": font_v,
                     "provider": prov_var.get(),
                     "workers": workers_var.get(), "bubbles": bubbles_var.get(),
                     "timeout": timeout_var.get(), "force_cpu": cpu_var.get(),
                     "batch_workers": batchw_var.get(), "max_retries": maxre_var.get(),
                     "request_delay": reqdelay_var.get(), "temperature": temp_var.get(),
                     "reading_order": readord_var.get(),
                     "story_brief": brief_var.get(),
                     "glossary_text": glos_txt.get("1.0", "end").rstrip()})

        cmd = [sys.executable, MANGA_PY, "-i", src, "-o", out_v, "--font", font_v,
               "--provider", prov_var.get(),
               "--workers", str(workers_var.get()),
               "--bubbles-per-request", str(bubbles_var.get()),
               "--api-timeout", str(timeout_var.get()),
               "--quality", str(quality_var.get()),
               "--batch-workers", str(batchw_var.get()),
               "--max-retries", str(maxre_var.get()),
               "--request-delay", str(reqdelay_var.get()),
               "--temperature", str(temp_var.get()),
               "--reading-order", str(readord_var.get())]
        
        cli_font = {"free_text": "free"}
        for slot, var in font_slots.items():
            pv = var.get().strip()
            if pv and os.path.isfile(pv):
                cmd += ["--font-" + cli_font.get(slot, slot.replace("_", "-")), pv]
        keys = [k.strip() for k in keys_var.get().replace(";", ",").split(",") if k.strip()]
        if keys:
            cmd += ["--api-key", ",".join(keys)]
        if model_var.get().strip():
            cmd += ["--model", model_var.get().strip()]
        if lama_var.get():
            cmd += ["--lama"]
        if cpu_var.get():
            cmd += ["--cpu"]
        if not twopass_var.get():
            cmd += ["--no-two-pass-ocr"]
        if debug_var.get():
            cmd += ["--debug"]
        glos_text = glos_txt.get("1.0", "end").strip()
        if glos_text:
            glos_path = os.path.join(OUT_DIR, "glossary_user.txt")
            with open(glos_path, "w", encoding="utf-8") as _gf:
                _gf.write(glos_text + "\n")
            cmd += ["--glossary", glos_path]
        if not brief_var.get():
            cmd += ["--no-brief"]

        log_box.config(state="normal")
        log_box.delete("1.0", "end")
        log_box.config(state="disabled")
        log_write("▶ " + " ".join(cmd))
        run_btn.config(state="disabled")
        stop_btn.config(state="normal")
        open_btn.config(state="disabled")
        read_btn.config(state="disabled")
        set_status("در حال اجرا…", ACCENT)
        progress.pack(fill="x", padx=10, pady=(0, 6))
        progress.start(12)
        threading.Thread(target=worker, args=(src, out_v, cmd), daemon=True).start()

    run_btn.config(command=on_run)
    stop_btn.config(command=on_stop)
    open_btn.config(command=on_open)
    poll_queue()

    
    tab_sys = ttk.Frame(nb, padding=12)
    nb.add(tab_sys, text="🖥️ سیستم")
    sys_txt = tk.Text(tab_sys, font=("Consolas", 10), bg=C_CARD, fg=C_TXT,
                      relief="flat", height=18)
    sys_txt.pack(fill="both", expand=True)
    sys_txt.insert("1.0", system_info())
    sys_txt.config(state="disabled")

    tab_help = ttk.Frame(nb, padding=12)
    nb.add(tab_help, text="❓ راهنما")
    help_txt = tk.Text(tab_help, font=(None, 10), bg=C_CARD, fg=C_TXT,
                       relief="flat", wrap="word")
    help_txt.pack(fill="both", expand=True)
    help_txt.insert("1.0", HELP_TEXT)
    help_txt.config(state="disabled")

    nb.add(tab_log, text="📜 لاگ")

    
    import webbrowser
    import base64 as _b64
    GH_ICON_B64 = "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"
    TG_ICON_B64 = "iVBORw0KGgoAAAANSUhEUgAAABIAAAASCAYAAABWzo5XAAABzElEQVR4nJ2TPUskQRCGn11HDeSM/Gg66cxAzsBAETQQ0UQvETwXOThQ8APxF5iIkZiLoQiCifgLDAyMFA7u5M7g1GDulmE4uMBAUNFZqaVam3WVxYIZZrqrq596qyrH+ywH5IGS/mfvCVD32kYtllffB/1vTJN4FJgHLo11S1GN+JkspElsgSlgDuhQv9/yit7Av/cEaRJ3AzPABGDU7waoB07ksugV/HvF/wTMAsOBNodAM9CtZ36FRLkAvx34AkwDHytoV4AWYDGo2HcfSIKU0iTuCfDFWewOaAD+AZ+BLmBVL5Vzt8C5T0cotjTXBQ3i9WnQVDqBNmBD10saqGis+/sUCGiqSCFSTdaMdUNAL7CnQfwZsTOlzpfLa6wrAH3AuqL+B8aMdctpEvcD+0E6ZSk00A9fqBcNmSax0G0b676mSfwB+Am0Ko2vnP+eNNYJaRRiynejse5aujVN4kGh4jlIeGmdrsklYlnYR5mKLAcOgPGgezNtvkzTkkBF4I/ul0Iij4yx7ggYAEaAYxV7JxgZufBC6ctr1UZENqQSuyIZUDDWXQGi2akWRHy+Bf5ZrdMvqZSHV7WTZ9NYJ40aVrGq+emvFLmqPQIRpIZPBEo6vAAAAABJRU5ErkJggg=="
    foot = tk.Frame(root, bg=C_BG2, highlightthickness=0, bd=0)
    foot.pack(side="bottom", fill="x")
    def _open_link(url):
        webbrowser.open(url)
    def _hover(lbl, on):
        lbl.config(fg=C_ACC if on else "#c8c5bd")
    try:
        from PIL import Image as _PILImage, ImageTk as _ImageTk
        import io as _io
        _gh_img = _ImageTk.PhotoImage(_PILImage.open(_io.BytesIO(_b64.b64decode(GH_ICON_B64))))
        try:
            _tg_img = tk.PhotoImage(data=_b64.b64decode(TG_ICON_B64))
        except Exception:
            _tg_img = None
    except Exception:
        try:
            _gh_img = tk.PhotoImage(data=_b64.b64decode(GH_ICON_B64))
            _tg_img = tk.PhotoImage(data=_b64.b64decode(TG_ICON_B64))
        except Exception:
            _gh_img = _tg_img = None
    gh_lbl = tk.Label(foot, text="سورس (گیت‌هاب)", font=(None, 10),
                      bg=C_BG2, fg="#c8c5bd", cursor="hand2",
                      image=_gh_img, compound="right", padx=6)
    gh_lbl.image_ref = _gh_img
    gh_lbl.pack(side="right", padx=14, pady=6)
    gh_lbl.bind("<Button-1>", lambda e: _open_link(
        "https://github.com/amirwolf5122/Manga-AutoTranslate"))
    gh_lbl.bind("<Enter>", lambda e: _hover(gh_lbl, True))
    gh_lbl.bind("<Leave>", lambda e: _hover(gh_lbl, False))
    tg_lbl = tk.Label(foot, text="سازنده (تلگرام)", font=(None, 10),
                      bg=C_BG2, fg="#c8c5bd", cursor="hand2",
                      image=_tg_img, compound="right", padx=6)
    tg_lbl.image_ref = _tg_img
    tg_lbl.pack(side="right", padx=14, pady=6)
    tg_lbl.bind("<Button-1>", lambda e: _open_link("https://t.me/amir_wolf512"))
    tg_lbl.bind("<Enter>", lambda e: _hover(tg_lbl, True))
    tg_lbl.bind("<Leave>", lambda e: _hover(tg_lbl, False))
    tk.Label(foot, text="مانگا مترجم", font=(None, 9),
             bg=C_BG2, fg=C_MUT).pack(side="left", padx=14)

    def _on_close_desktop():
        try:
            _persist_api_desktop()
        except Exception:
            pass
        try:
            root.destroy()
        except Exception:
            pass

    root.protocol("WM_DELETE_WINDOW", _on_close_desktop)
    root.mainloop()

WEB_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;700;900&family=IBM+Plex+Mono:wght@400;500&display=swap');

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
  font-family: 'Vazirmatn', sans-serif !important;
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
  font-family: 'IBM Plex Mono', monospace; font-size: .7rem;
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
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: #060607; }
::-webkit-scrollbar-thumb { background: #232329; border-radius: 6px; }
::-webkit-scrollbar-thumb:hover { background: var(--ink-red-deep); }
::selection { background: var(--ink-red); color: #fff; }
@media (prefers-reduced-motion: reduce) {
  .nav, .stepcard { animation: none; }
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


def run_web():
    
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



    def build_reader_html(files, standalone: bool = True):
        
        import gradio as _gr
        gv = getattr(_gr, "__version__", "4")
        major = int(str(gv).split(".")[0] or 4)
        prefix = "/gradio_api/file=" if major >= 5 else "/file="
        urls = [prefix + str(p).replace(os.sep, "/") for p in files]
        if not urls:
            body = "<div style='text-align:center;opacity:.6;padding:24px'>تصویری برای نمایش پیدا نشد.</div>"
            if not standalone:
                return body
            return (
                "<!DOCTYPE html><html lang='fa' dir='rtl'><head><meta charset='utf-8'>"
                "<meta name='viewport' content='width=device-width,initial-scale=1'>"
                f"<title>خواندن</title></head><body style='background:#000;color:#999'>{body}</body></html>"
            )
        imgs = "".join(
            f'<img src="{u}" loading="lazy" decoding="async" alt="" draggable="false">'
            for u in urls
        )
        title = os.path.basename(os.path.dirname(files[0])) or "مانهوا"
        title_esc = (
            str(title).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;")
        )
        css = (
            "*{box-sizing:border-box;margin:0;padding:0}"
            "html,body{height:100%;background:#000;color:#e8e6e1;font-family:system-ui,-apple-system,sans-serif;"
            "overscroll-behavior:none;-webkit-user-select:none;user-select:none}"
            ".rdr{position:fixed;inset:0;z-index:1;background:#000;display:flex;flex-direction:column;direction:ltr}"
            ".rdr-bar{display:flex;align-items:center;flex-wrap:wrap;gap:6px;padding:8px 10px;"
            "background:rgba(12,12,14,.96);border-bottom:1px solid #232326;flex:none;backdrop-filter:blur(8px);z-index:2}"
            ".rdr-btn{background:#161619;color:#e8e6e1;border:1px solid #2a2a2e;border-radius:8px;"
            "padding:8px 12px;font-size:.95rem;cursor:pointer;font-family:inherit;"
            "min-width:40px;min-height:40px;touch-action:manipulation;-webkit-tap-highlight-color:transparent}"
            ".rdr-btn:active{background:#2a2a30}"
            ".rdr-btn.fs{background:#ff4a3d;border-color:#ff4a3d;color:#fff;font-weight:700}"
            ".rdr-title{flex:1 1 120px;color:#97948c;font-size:.8rem;white-space:nowrap;"
            "overflow:hidden;text-overflow:ellipsis;text-align:right;direction:rtl;min-width:0}"
            ".rdrS{flex:1;overflow:auto;-webkit-overflow-scrolling:touch;overscroll-behavior:contain;"
            "touch-action:pan-y;position:relative;background:#000}"
            ".rdrC{margin:0 auto;max-width:min(100%,900px);width:100%}"
            ".rdrC img{display:block;width:100%;height:auto;max-width:none;user-select:none;"
            "-webkit-user-drag:none;pointer-events:none}"
            ".rdr-progress{position:relative;height:3px;background:#1a1a1c;flex:none}"
            ".rdrB{height:100%;width:0;background:linear-gradient(90deg,#ff4a3d,#ff8a5e)}"
            ".zlv{color:#97948c;font-size:.8rem;min-width:44px;text-align:center;font-variant-numeric:tabular-nums}"
            "@media (max-width:480px){"
            ".rdr-bar{gap:4px;padding:6px 8px}"
            ".rdr-btn{padding:7px 10px;font-size:.9rem;min-width:36px}"
            ".rdr-title{font-size:.72rem;order:10;flex:1 1 100%;text-align:center}"
            "}"
        )
        js = r"""
(function(){
  const root = document.getElementById('manga_rdr');
  if (!root) return;
  const sc = root.querySelector('.rdrS');
  const c = root.querySelector('.rdrC');
  const bar = root.querySelector('.zlv');
  const prog = root.querySelector('.rdrB');
  if (!sc || !c) return;
  let z = 1;
  const MIN = 0.5, MAX = 4;
  const baseWidth = () => Math.max(200, Math.min(900, sc.clientWidth || window.innerWidth || 360));
  const applyZoom = (nz, cx, cy) => {
    nz = Math.min(MAX, Math.max(MIN, +nz || 1));
    const rect = sc.getBoundingClientRect();
    const sx = (typeof cx === 'number') ? cx : (rect.left + rect.width / 2);
    const sy = (typeof cy === 'number') ? cy : (rect.top + rect.height / 2);
    const relX = (sc.scrollLeft + (sx - rect.left)) / Math.max(0.01, z);
    const relY = (sc.scrollTop + (sy - rect.top)) / Math.max(0.01, z);
    z = nz;
    c.style.maxWidth = 'none';
    c.style.width = Math.round(baseWidth() * z) + 'px';
    c.style.marginLeft = 'auto';
    c.style.marginRight = 'auto';
    sc.scrollLeft = relX * z - (sx - rect.left);
    sc.scrollTop = relY * z - (sy - rect.top);
    if (bar) bar.textContent = Math.round(z * 100) + '%';
    root.dataset.zoom = String(z);
  };
  const setZoom = (nz) => applyZoom(nz);
  const zoomBy = (f, cx, cy) => applyZoom(z * f, cx, cy);
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
  sc.addEventListener('wheel', (e) => {
    if (!e.ctrlKey && !e.metaKey) return;
    e.preventDefault();
    zoomBy(e.deltaY < 0 ? 1.12 : 1 / 1.12, e.clientX, e.clientY);
  }, { passive: false });
  sc.addEventListener('dblclick', (e) => {
    e.preventDefault();
    if (z > 1.3) setZoom(1);
    else zoomBy(2.2, e.clientX, e.clientY);
  });
  let pinch = null, pan = null;
  const dist = (a, b) => Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
  const mid = (a, b) => ({ x: (a.clientX + b.clientX) / 2, y: (a.clientY + b.clientY) / 2 });
  sc.addEventListener('touchstart', (e) => {
    if (e.touches.length === 2) {
      e.preventDefault();
      pinch = { startDist: dist(e.touches[0], e.touches[1]), startZ: z };
      pan = null;
    } else if (e.touches.length === 1) {
      pan = { x: e.touches[0].clientX, y: e.touches[0].clientY, sl: sc.scrollLeft, st: sc.scrollTop };
    }
  }, { passive: false });
  sc.addEventListener('touchmove', (e) => {
    if (pinch && e.touches.length === 2) {
      e.preventDefault();
      const d = dist(e.touches[0], e.touches[1]);
      const m = mid(e.touches[0], e.touches[1]);
      applyZoom(pinch.startZ * (d / Math.max(1, pinch.startDist)), m.x, m.y);
    } else if (pan && e.touches.length === 1 && z > 1.05) {
      e.preventDefault();
      const t = e.touches[0];
      sc.scrollLeft = pan.sl - (t.clientX - pan.x);
      sc.scrollTop = pan.st - (t.clientY - pan.y);
    }
  }, { passive: false });
  sc.addEventListener('touchend', (e) => {
    if (e.touches.length < 2) pinch = null;
    if (e.touches.length === 0) pan = null;
  });
  sc.addEventListener('touchcancel', () => { pinch = null; pan = null; });
  sc.addEventListener('scroll', () => {
    if (!prog) return;
    const m = sc.scrollHeight - sc.clientHeight;
    prog.style.width = (m > 0 ? (sc.scrollTop / m * 100) : 0) + '%';
  }, { passive: true });
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
  setZoom(1);
})();
"""
        
        js = js.replace("sl: sc.scrollLeft", "sl: sc.scrollLeft").replace("sl: sc.scrollLeft", "sl: sc.scrollLeft")
        js = js.replace("sl: sc.scrollLeft", "sl: sc.scrollLeft")
        js = js.replace("sl: sc.scrollLeft", "sl: sc.scrollLeft")
        
        js = js.replace("sl: sc.scrollLeft", "sl: sc.scrollLeft")
        js = js.replace("sl: sc.scrollLeft", "sl: sc.scrollLeft")
        js = js.replace("pan = { x: e.touches[0].clientX, y: e.touches[0].clientY, sl: sc.scrollLeft, st: sc.scrollTop };",
                        "pan = { x: e.touches[0].clientX, y: e.touches[0].clientY, sl: sc.scrollLeft, st: sc.scrollTop };")
        
        js = js.replace("sl: sc.scrollLeft, st: sc.scrollTop", "sl: sc.scrollLeft, st: sc.scrollTop")
        js = js.replace("sl: sc.scrollLeft", "sl: sc.scrollLeft")
        
        if "sc؛" in js:
            js = js.replace("sc؛Left", "sc.scrollLeft")
        pass

        page = (
            "<!DOCTYPE html>\n"
            '<html lang="fa" dir="rtl">\n'
            "<head>\n"
            '<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=5,user-scalable=yes">\n'
            '<meta name="apple-mobile-web-app-capable" content="yes">\n'
            f"<title>{title_esc}</title>\n"
            f"<style>{css}</style>\n"
            "</head>\n"
            "<body>\n"
            '<div class="rdr" id="manga_rdr" data-zoom="1">\n'
            '  <div class="rdr-bar">\n'
            '    <button type="button" class="rdr-btn" data-act="close" title="بستن">✕</button>\n'
            f'    <div class="rdr-title">{title_esc}</div>\n'
            '    <button type="button" class="rdr-btn" data-act="zoom-out" title="دور">−</button>\n'
            '    <span class="zlv">100%</span>\n'
            '    <button type="button" class="rdr-btn" data-act="zoom-in" title="نزدیک">+</button>\n'
            '    <button type="button" class="rdr-btn" data-act="zoom-fit" title="پهنای صفحه">پهنا</button>\n'
            '    <button type="button" class="rdr-btn fs" data-act="fs" title="فول‌اسکرین">⛶</button>\n'
            "  </div>\n"
            f'  <div class="rdrS"><div class="rdrC">{imgs}</div></div>\n'
            '  <div class="rdr-progress"><div class="rdrB"></div></div>\n'
            "</div>\n"
            f"<script>\n{js}\n</script>\n"
            "</body>\n</html>\n"
        )
        return page

    g6 = _gradio_major() >= 6
    blocks_kw = {} if g6 else {"theme": gr.themes.Soft(primary_hue="indigo",
                                                       neutral_hue="slate"),
                               "css": WEB_CSS}
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
            inp_upload = gr.File(label="آپلود فایل (pdf / zip / cbz / تصویر / html)",
                                 file_count="single", type="filepath",
                                 elem_classes=["compact-upload"])
            inp_path = gr.Textbox(label="یا URL تصویر/مانهوا",
                                  placeholder="https://cdn.example.com/chapter/1/001.webp")

        
        with gr.Group(elem_classes=["stepcard"]):
            gr.HTML('<div class="steptitle"><span class="stepnum">۲</span> مترجم هوش مصنوعی</div>')
            with gr.Row():
                provider = gr.Dropdown(PROVIDERS, value="gemini",
                                       label="ارائه‌دهنده", scale=1)
                api_keys = gr.Textbox(label="کلیدهای API شما (با کاما = چرخش خودکار)",
                                      value="",
                                      type="password", scale=3,
                                      elem_id="manga_api_keys",
                                      info="کلید فقط در localStorage مرورگر شما می‌ماند — نه روی سرور و نه در config دسکتاپ.")
                model = gr.Textbox(label="مدل (خالی = پیش‌فرض)",
                                   value="",
                                   placeholder="gemini-3.8-flash", scale=2,
                                   elem_id="manga_model")
            gr.Markdown("<div class='hint'>کلید از aistudio.google.com (Gemini) یا "
                        "platform.openai.com (ChatGPT) یا console.groq.com بگیرید. "
                        "تنظیمات وب فقط در مرورگر ذخیره می‌شود.</div>")

        
        with gr.Group(elem_classes=["stepcard"]):
            gr.HTML('<div class="steptitle"><span class="stepnum">۳</span> خروجی</div>')
            with gr.Row():
                out_fmt = gr.Radio(["PDF", "ZIP", "HTML", "پوشهٔ تصاویر"],
                                   value=cfg.get("out_fmt", "PDF"), label="قالب")
                quality = gr.Slider(60, 100, value=int(cfg.get("quality", 92)),
                                    step=1, label="کیفیت تصویر")

        
        with gr.Accordion("✒️ فونت‌ها (اصلی + لحن‌ها — اختیاری، خالی = فونت سرور)", open=False):
            font_upload = gr.File(label="فونت اصلی (.ttf)",
                                  file_count="single", type="filepath",
                                  file_types=[".ttf", ".otf"],
                                  elem_classes=["compact-upload"])
            gr.Markdown("<div class='hint'>هر فونت لحن را جدا آپلود کنید؛ خالی = فونت سرور</div>")
            SLOT_LABELS = {
                "normal": "کودک (عادی)", "shout": "افسانه (خشم)",
                "comedy_shout": "کروش (کمدی)", "whisper": "زمزمه",
                "thought": "تفکر", "system": "سیستم/تگ",
                "letter": "نامه/طومار", "narrator": "راوی", "free_text": "متن آزاد",
            }
            tone_uploads = []
            tone_slots = []
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
                        tone_uploads.append(up)
                        tone_slots.append(slot)

        with gr.Accordion("⚙️ تنظیمات پیشرفته", open=False):
            with gr.Row():
                workers = _safe(gr.Slider, 1, 8, value=int(cfg.get("workers", 2)),
                                step=1, label="ورکر موازی OCR")
                bubbles = _safe(gr.Slider, 1, 12, value=int(cfg.get("bubbles", 6)),
                                step=1, label="حباب در هر درخواست ترجمه")
                batchw = _safe(gr.Slider, 1, 8, value=int(cfg.get("batch_workers", 3)),
                               step=1, label="بستهٔ ترجمهٔ موازی (کلید جدا برای هر بسته)")
            with gr.Row():
                timeout = _safe(gr.Slider, 10, 120, value=int(cfg.get("timeout", 40)),
                                step=5, label="تایم‌اوت هر درخواست (ثانیه)")
                maxre = _safe(gr.Slider, 1, 15, value=int(cfg.get("max_retries", 8)),
                              step=1, label="حداکثر تلاش ترجمه")
                reqdelay = _safe(gr.Slider, 0, 5, value=float(cfg.get("request_delay", 0)),
                                 step=0.5, label="تأخیر بین درخواست‌ها (ثانیه)")
            with gr.Row():
                temp = _safe(gr.Slider, 0, 1.5, value=float(cfg.get("temperature", 0.85)),
                             step=0.05, label="خلاقیت ترجمه (temperature)")
                readord = gr.Radio(["rtl", "ltr"], value=str(cfg.get("reading_order", "rtl")),
                                   label="ترتیب خواندن حباب‌ها")
            with gr.Row():
                use_lama = gr.Checkbox(label="اجبار LaMa-Manga (خالی = خودکار)",
                                       value=False)
                force_cpu = gr.Checkbox(label="اجبار CPU (خالی = GPU اگر بود)",
                                        value=False)
                two_pass = gr.Checkbox(label="OCR دومرحله‌ای", value=True)
            glossary_text = gr.Textbox(
                label="واژه‌نامهٔ اسامی و اصطلاحات (هر خط: English=فارسی)",
                placeholder="Raphdonia=رافدونیا\nBarbarian=باربارین",
                lines=3, value=str(cfg.get("glossary_text", "") or ""))
            story_brief = gr.Checkbox(
                label="بریف داستان قبل از ترجمه (AI یک‌بار فصل را می‌خواند تا لحن شخصیت‌ها حفظ شود)",
                value=bool(cfg.get("story_brief", True)))

        SESSION_TTL = 2 * 60 * 60
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
                        "result_visible": bool(job.get("result_visible")),
                        "returncode": job.get("returncode"),
                        "out_v": job.get("out_v"),
                        "src": str(job.get("src") or "")[:500],
                        "reader_path": job.get("reader_path"),
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
            img_dir = out_v if os.path.isdir(out_v) else os.path.join(str(out_v) + ".cache", "out")
            imgs = []
            try:
                if os.path.isdir(img_dir):
                    for f in sorted(os.listdir(img_dir), key=natural_key):
                        if f.lower().endswith((".webp", ".png", ".jpg", ".jpeg")):
                            imgs.append(os.path.join(img_dir, f))
                if not imgs and str(target).lower().endswith((".webp", ".png", ".jpg", ".jpeg")):
                    imgs = [target]
            except Exception:
                pass
            try:
                reader_html = build_reader_html(imgs, standalone=True)
            except Exception:
                reader_html = ""
            reader_path = None
            try:
                base_dir = out_v if os.path.isdir(out_v) else os.path.dirname(str(out_v))
                if not base_dir or not os.path.isdir(base_dir):
                    base_dir = os.path.join(OUT_DIR, sid[:12])
                    os.makedirs(base_dir, exist_ok=True)
                reader_path = os.path.join(base_dir, "reader.html")
                with open(reader_path, "w", encoding="utf-8") as rf:
                    rf.write(reader_html or "")
            except Exception as e:
                print(f"[!] ذخیره reader.html ناموفق: {e}")
                reader_path = None
            final_log = "\n".join(buf[-120:]) + f"\n\n✅ تمام شد ({dur_s}) — دکمه‌های نمایش و دانلود پایین فعال شدند"
            with job["lock"]:
                job["log"] = final_log
                job["download_path"] = target
                job["html_state"] = reader_html
                job["reader_path"] = reader_path
                job["result_visible"] = True
                job["ts"] = time.time()
            _persist_job_meta(sid)

        def _start_job_reader(sid: str, proc: subprocess.Popen, t0: float) -> None:
            job = _get_job(sid)

            def _fmt(buf_lines):
                el = int(time.time() - t0)
                body = "\n".join(buf_lines[-120:]) if buf_lines else "… در حال دریافت خروجی …"
                return f"⏱ {el // 60}:{el % 60:02d}\n\n{body}"

            def _reader():
                buf = list(job.get("buf") or [])
                n = 0
                partial = b""
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
                        buf.append(partial.decode("utf-8", "replace").rstrip("\r"))
                    try:
                        proc.wait(timeout=5)
                    except Exception:
                        pass
                except Exception as e:
                    with job["lock"]:
                        job["log"] = (job.get("log") or "") + f"\n⚠ reader: {e}"
                finally:
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
        sid_box = gr.Textbox(value="", visible=False, elem_id="manga_sid", label="sid")
        
        sid_holder = gr.Textbox(value="", visible=False, elem_id="manga_sid_holder", label="sid_holder")

        run_btn = gr.Button("🚀  شروع ترجمه", variant="primary", elem_id="runbtn")

        with gr.Accordion("📡 لاگ زنده", open=True):
            log_box = _safe(gr.Textbox, lines=16, max_lines=50, autoscroll=True,
                            show_label=False, interactive=True,
                            elem_id="manga_live_log",
                            value="— لاگ بعد از شروع ترجمه اینجا می‌آید —")

        html_state = gr.State("")
        with gr.Group(elem_classes=["stepcard"], visible=False) as result_group:
            gr.HTML('<div class="steptitle"><span class="stepnum">✓</span> نتیجه — نمایش یا دانلود</div>')
            with gr.Row():
                btn_view = _safe(gr.Button, "👁 نمایش", visible=False)
                dl_btn = _safe(gr.DownloadButton, label="⬇ دانلود", visible=False)
            viewer_html = gr.HTML(visible=False, elem_id="reader_wrap")

        LS_KEY = "manga_autotranslate_form_v2"
        JOB_KEY = "manga_job_v1"
        browser_form_json = gr.State("")

        save_form_js = f"""
(sid, sidBox, inp, prov, keys, model, fmt, qual, workers, bubbles, timeout, batchw, maxre, reqdelay, temp, readord, lama, cpu, twopass) => {{
  try {{
    const realSid = (sid || sidBox || "").toString().trim();
    const data = {{
      sid: realSid,
      inp: inp || "",
      prov: prov || "",
      keys: keys || "",
      model: model || "",
      fmt: fmt || "",
      qual: qual,
      workers: workers,
      bubbles: bubbles,
      timeout: timeout,
      batchw: batchw,
      maxre: maxre,
      reqdelay: reqdelay,
      temp: temp,
      readord: readord || "",
      lama: !!lama,
      cpu: !!cpu,
      twopass: twopass === null || twopass === undefined ? true : !!twopass,
      ts: Date.now()
    }};
    localStorage.setItem("{LS_KEY}", JSON.stringify(data));
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
  try {{
    let raw = localStorage.getItem("{LS_KEY}");
    if (!raw) {{
      raw = localStorage.getItem("manga_autotranslate_form_v1");
      if (raw) {{
        try {{ localStorage.setItem("{LS_KEY}", raw); }} catch (e) {{}}
      }}
    }}
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
    if (!d || !d.ts || (Date.now() - d.ts) > {SESSION_TTL * 1000}) {{
      if (bestSid) {{
        return [JSON.stringify({{
          sid: bestSid,
          ts: Date.now(),
          _jobLog: job.log || "",
          _jobBtn: job.btn || "",
          _jobRunning: !!job.running,
          keys: d && d.keys ? d.keys : undefined,
          prov: d && d.prov ? d.prov : undefined,
        }})];
      }}
      try {{ localStorage.removeItem("{LS_KEY}"); }} catch (e) {{}}
      return [""];
    }}
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
  const TTL = {SESSION_TTL * 1000};

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
      if (jobDone) {{
        const forceStart = () => {{
          const roots = [document.getElementById("runbtn"), ...Array.from(document.querySelectorAll("button"))];
          for (const r of roots) {{
            if (!r) continue;
            const el = r.tagName === "BUTTON" ? r : (r.querySelector && r.querySelector("button"));
            if (!el) continue;
            const t = (el.textContent || "");
            if (t.indexOf("متوقف") >= 0 || t.indexOf("⏹") >= 0) {{
              el.textContent = "🚀  شروع ترجمه";
            }}
          }}
        }};
        forceStart();
        setTimeout(forceStart, 500);
        setTimeout(forceStart, 1500);
        try {{
          job.running = false;
          job.btn = "🚀  شروع ترجمه";
          localStorage.setItem(JOB, JSON.stringify(job));
        }} catch (e) {{}}
      }}
      if (job.running && !jobDone) {{
        const forceBtn = () => {{
          const roots = [
            document.getElementById("runbtn"),
            ...Array.from(document.querySelectorAll("button")),
          ];
          for (const r of roots) {{
            if (!r) continue;
            const b = r.tagName === "BUTTON" ? r : r.querySelector("button");
            const el = b || (r.tagName === "BUTTON" ? r : null);
            if (!el) continue;
            const t = (el.textContent || "");
            if (t.indexOf("شروع") >= 0 || t.indexOf("🚀") >= 0 || t.indexOf("متوقف") >= 0 || t.indexOf("⏹") >= 0) {{
              el.textContent = "⏹  متوقف ترجمه";
            }}
          }}
        }};
        forceBtn();
        setTimeout(forceBtn, 400);
        setTimeout(forceBtn, 1200);
        setTimeout(forceBtn, 2500);
      }}

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
        if (d && d.ts && (Date.now() - d.ts) <= TTL) {{
          const byId = (id) => {{
            const root = document.getElementById(id);
            if (!root) return null;
            return root.querySelector("input, textarea, select") || root;
          }};
          if (d.keys) {{
            const k = byId("manga_api_keys") || document.querySelector('input[type="password"]');
            if (k) setVal(k, d.keys);
          }}
          if (d.model) {{
            const m = byId("manga_model");
            if (m) setVal(m, d.model);
          }}
        }}
      }}
    }} catch (e) {{ console.warn("manga restore", e); }}
  }};

  apply();
  [100, 300, 600, 1000, 2000, 3500, 5000].forEach((t) => setTimeout(apply, t));

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

  return [];
}}
"""


        def run_translation(sid, sid_box_v, inp_path_v, upload, provider_v, api_keys_v, model_v,
                            out_fmt_v, quality_v, font_up,
                            workers_v, bubbles_v, timeout_v,
                            batchw_v, maxre_v, reqdelay_v, temp_v, readord_v,
                            use_lama_v, force_cpu_v, two_pass_v,
                            glossary_text_v, story_brief_v,
                            *tone_files):
            sid = (sid or sid_box_v or "").strip()
            sid = _find_active_sid(sid) or sid
            if not sid:
                sid = _new_sid()

            job = _get_job(sid)

            def _pack(btn, log, dl=None, view=None, group=None, viewer=None, html=""):
                return (
                    sid,
                    gr.update(value=sid),
                    gr.update(value=btn),
                    gr.update(value=log),
                    dl if dl is not None else gr.update(),
                    view if view is not None else gr.update(),
                    group if group is not None else gr.update(),
                    viewer if viewer is not None else gr.update(),
                    html if html is not None else gr.update(),
                )

            with job["lock"]:
                running_now = _job_running(job)
            if running_now:
                _kill_job(sid)
                msg = job.get("log") or "⏹ ترجمه متوقف شد.\n(پروسه manga.py بسته شد)"
                return _pack("🚀  شروع ترجمه", msg)

            tone_map = dict(zip(tone_slots, tone_files))
            src = upload or (inp_path_v or "").strip()

            if not src:
                return _pack("🚀  شروع ترجمه",
                             "❌ ورودی خالی است — فایل آپلود کنید یا URL بدهید.")

            font_v = font_up or find_font()
            if not font_v or not os.path.isfile(font_v):
                return _pack("🚀  شروع ترجمه",
                             "❌ فونت فارسی روی سرور نیست — یک .ttf آپلود کنید.")

            ext = {"PDF": ".pdf", "ZIP": ".zip", "HTML": ".html", "پوشهٔ تصاویر": ""}[out_fmt_v]
            base = smart_output_base(str(src))
            user_out_dir = os.path.join(OUT_DIR, sid[:12])
            os.makedirs(user_out_dir, exist_ok=True)
            out_v = os.path.join(user_out_dir, base + ext)

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
                   "--temperature", str(float(temp_v)),
                   "--reading-order", str(readord_v)]
            cmd += font_args()
            for slot, fp in tone_map.items():
                if fp and os.path.isfile(fp):
                    cmd += ["--font-" + slot.replace("_", "-"), fp]
            klist = [k.strip() for k in (api_keys_v or "").replace(";", ",").split(",") if k.strip()]
            if klist:
                cmd += ["--api-key", ",".join(klist)]
            if model_v and str(model_v).strip():
                cmd += ["--model", str(model_v).strip()]
            if use_lama_v:
                cmd += ["--lama"]
            if force_cpu_v:
                cmd += ["--cpu"]
            if not two_pass_v:
                cmd += ["--no-two-pass-ocr"]
            glos_text = str(glossary_text_v or "").strip()
            if glos_text:
                glos_path = os.path.join(user_out_dir, "glossary_user.txt")
                with open(glos_path, "w", encoding="utf-8") as _gf:
                    _gf.write(glos_text + "\n")
                cmd += ["--glossary", glos_path]
            if not story_brief_v:
                cmd += ["--no-brief"]

            t0 = time.time()
            with job["lock"]:
                job["result_visible"] = False
                job["download_path"] = None
                job["html_state"] = ""
                job["buf"] = []
                job["t0"] = t0
                job["returncode"] = None
                job["done_event"] = False
                job["out_v"] = out_v
                job["src"] = src
                job["running"] = True
                job["log"] = "⏱ 0:00\n\n▶ در حال شروع…"
                job["ts"] = time.time()

            _env = os.environ.copy()
            _env["PYTHONUNBUFFERED"] = "1"
            _env["PYTHONIOENCODING"] = "utf-8"
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
                return _pack("🚀  شروع ترجمه", job["log"])

            with job["lock"]:
                job["proc"] = proc
                job["running"] = True
                job["ts"] = time.time()
                job["log"] = "⏱ 0:00\n\n▶ شروع شد — لاگ زنده به‌زودی…\n(اگر صفحه را رفرش کنید لاگ از همین جلسه برمی‌گردد)"
            _persist_job_meta(sid)
            _start_job_reader(sid, proc, t0)

            return _pack("⏹  متوقف ترجمه", job["log"])

        _click_kw = dict(
            inputs=[session_id, sid_box, inp_path, inp_upload, provider, api_keys, model,
                    out_fmt, quality, font_upload,
                    workers, bubbles, timeout,
                    batchw, maxre, reqdelay, temp, readord,
                    use_lama, force_cpu, two_pass,
                    glossary_text, story_brief] + tone_uploads,
            outputs=[session_id, sid_box, run_btn, log_box, dl_btn, btn_view, result_group, viewer_html, html_state],
            concurrency_limit=8,
        )
        try:
            run_btn.click(run_translation, show_progress="hidden", **_click_kw)
        except TypeError:
            try:
                run_btn.click(run_translation, show_progress=False, **_click_kw)
            except TypeError:
                run_btn.click(run_translation, **_click_kw)

        _save_inputs = [
            session_id, sid_box, inp_path, provider, api_keys, model, out_fmt, quality,
            workers, bubbles, timeout, batchw, maxre, reqdelay, temp, readord,
            use_lama, force_cpu, two_pass,
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

        for _comp in (api_keys, provider, model, out_fmt, inp_path):
            try:
                _comp.change(fn=None, inputs=_save_inputs, outputs=[], js=save_form_js)
            except Exception:
                try:
                    _comp.blur(fn=None, inputs=_save_inputs, outputs=[], js=save_form_js)
                except Exception:
                    pass
        for _comp in (quality, workers, bubbles, timeout, batchw, maxre, reqdelay, temp, readord,
                      use_lama, force_cpu, two_pass):
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
                return (
                    gr.update(), gr.update(), gr.update(), gr.update(),
                    gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                    gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                    gr.update(), gr.update(), gr.update(), gr.update(),
                    gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                    gr.update(), gr.update(), gr.update(),
                )
            job = _get_job(sid)
            meta = _load_job_meta(sid) if sid else {}
            
            
            client_log = (data.get("_jobLog") or "").strip()
            client_running = bool(data.get("_jobRunning"))
            client_btn = (data.get("_jobBtn") or "").strip()

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
            
            if still_running or client_running:
                btn = "⏹  متوقف ترجمه"
            else:
                btn = "🚀  شروع ترجمه"

            def u_str(key):
                if key not in data:
                    return gr.update()
                v = data.get(key)
                if v is None:
                    return gr.update()
                return gr.update(value=v)

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

            return (
                sid,
                gr.update(value=sid),
                gr.update(value=btn),
                gr.update(value=log),
                gr.update(value=dl, visible=vis) if vis else gr.update(),
                gr.update(visible=vis),
                gr.update(visible=vis),
                gr.update(visible=False),
                html if vis else gr.update(),
                u_str("inp"),
                u_str("prov"),
                u_str("keys"),
                u_str("model"),
                u_str("fmt"),
                u_num("qual"),
                u_num("workers"),
                u_num("bubbles"),
                u_num("timeout"),
                u_num("batchw"),
                u_num("maxre"),
                u_num("reqdelay"),
                u_num("temp"),
                u_str("readord"),
                u_bool("lama"),
                u_bool("cpu"),
                u_bool("twopass"),
            )

        _restore_outputs = [
            session_id, sid_box, run_btn, log_box, dl_btn, btn_view, result_group, viewer_html, html_state,
            inp_path, provider, api_keys, model, out_fmt, quality,
            workers, bubbles, timeout, batchw, maxre, reqdelay, temp, readord,
            use_lama, force_cpu, two_pass,
        ]

        try:
            demo.load(
                _apply_browser_restore,
                inputs=[browser_form_json],
                outputs=_restore_outputs,
                js=load_form_js,
            )
        except Exception:
            try:
                demo.load(
                    _apply_browser_restore,
                    inputs=[browser_form_json],
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
            def _on_load_fallback(sid, sid_box_v):
                preferred = (sid or sid_box_v or "").strip()
                if not preferred:
                    return (gr.update(), gr.update(), gr.update(), gr.update(),
                            gr.update(), gr.update(), gr.update(), gr.update(), gr.update())
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
                    if meta.get("result_visible"):
                        job["result_visible"] = True
                    if meta.get("reader_path"):
                        job["reader_path"] = meta.get("reader_path")
                    still_running = _job_running(job)
                    log = job.get("log") or ""
                    vis = bool(job.get("result_visible"))
                    dl = job.get("download_path")
                    html = job.get("html_state") or ""
                if not log or log.startswith("—"):
                    return (
                        sid, gr.update(value=sid),
                        gr.update(), gr.update(), gr.update(),
                        gr.update(), gr.update(), gr.update(), gr.update(),
                    )
                btn = "⏹  متوقف ترجمه" if still_running else "🚀  شروع ترجمه"
                return (
                    sid,
                    gr.update(value=sid),
                    gr.update(value=btn),
                    gr.update(value=log),
                    gr.update(value=dl, visible=vis) if vis else gr.update(),
                    gr.update(visible=vis),
                    gr.update(visible=vis),
                    gr.update(visible=False),
                    html if vis else gr.update(),
                )

            demo.load(
                _on_load_fallback,
                inputs=[session_id, sid_box],
                outputs=[session_id, sid_box, run_btn, log_box, dl_btn, btn_view, result_group, viewer_html, html_state],
            )
        except Exception:
            pass

        def _poll_job_status(sid, sid_box_v):
            preferred = (sid or sid_box_v or "").strip()
            sid = _find_active_sid(preferred) or preferred
            empty = (gr.update(),) * 10
            if not sid:
                return empty
            job = _get_job(sid)
            meta = _load_job_meta(sid)
            with job["lock"]:
                mem_log = job.get("log") or ""
                meta_log = meta.get("log") or ""
                if meta_log and (len(meta_log) > len(mem_log) or not mem_log or mem_log.startswith("—")):
                    job["log"] = meta_log
                if meta.get("result_visible") and not job.get("result_visible"):
                    job["result_visible"] = True
                if meta.get("download_path") and not job.get("download_path"):
                    job["download_path"] = meta.get("download_path")
                if meta.get("reader_path") and not job.get("reader_path"):
                    job["reader_path"] = meta.get("reader_path")
                running = _job_running(job)
                log = job.get("log") or ""
                vis = bool(job.get("result_visible"))
                dl = job.get("download_path")
            btn = "⏹  متوقف ترجمه" if running else "🚀  شروع ترجمه"
            return (
                sid,
                gr.update(value=sid),
                gr.update(value=sid),  
                gr.update(value=btn),
                gr.update(value=log) if log else gr.update(),
                gr.update(value=dl, visible=vis) if vis else gr.update(),
                gr.update(visible=vis),
                gr.update(visible=vis),
                gr.update(),
                gr.update(),
            )


        _poll_outputs = [session_id, sid_box, sid_holder, run_btn, log_box, dl_btn, btn_view, result_group, viewer_html, html_state]
        try:
            _timer = gr.Timer(1.0, active=True)
            _tick_evt = _timer.tick(
                _poll_job_status,
                inputs=[sid_holder, sid_box],
                outputs=_poll_outputs,
            )
            try:
                
                _tick_evt.then(
                    fn=None,
                    inputs=[session_id, sid_box, run_btn, log_box],
                    outputs=[],
                    js=save_job_js,
                )
            except Exception:
                pass
        except Exception:
            try:
                demo.load(_poll_job_status, inputs=[session_id, sid_box], outputs=_poll_outputs)
            except Exception:
                pass

        def _cleanup_old_jobs():
            while True:
                try:
                    now = time.time()
                    dead = []
                    for sid, job in list(live_jobs.items()):
                        try:
                            with job["lock"]:
                                alive = job.get("proc") is not None and job["proc"].poll() is None
                                ts = job.get("ts") or 0
                            if not alive and (now - ts) > SESSION_TTL:
                                dead.append(sid)
                                out_sub = os.path.join(OUT_DIR, sid[:12])
                                if os.path.isdir(out_sub):
                                    shutil.rmtree(out_sub, ignore_errors=True)
                        except Exception:
                            dead.append(sid)
                    for sid in dead:
                        live_jobs.pop(sid, None)

                    if os.path.isdir(OUT_DIR):
                        for name in os.listdir(OUT_DIR):
                            p = os.path.join(OUT_DIR, name)
                            if not os.path.isdir(p):
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
                                    if (now - mtime) > SESSION_TTL:
                                        shutil.rmtree(p, ignore_errors=True)
                                except Exception:
                                    pass

                    old_sess = os.path.join(WORK_DIR, "sessions")
                    if os.path.isdir(old_sess):
                        for name in os.listdir(old_sess):
                            fp = os.path.join(old_sess, name)
                            try:
                                if (now - os.path.getmtime(fp)) > SESSION_TTL:
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
                return (gr.update(), gr.update(), gr.update(), gr.update(),
                        gr.update(), gr.update(), gr.update(), gr.update(), gr.update())
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
                return (gr.update(),) * 10
            return _poll_job_status(preferred, preferred)

        try:
            demo.load(
                _hydrate_after_js,
                inputs=[sid_holder, sid_box],
                outputs=_poll_outputs,
            )
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

        def _open_viewer(sid, sid_box_v, st):
            
            preferred = (sid or sid_box_v or "").strip()
            sid = _find_active_sid(preferred) or preferred
            job = _get_job(sid) if sid else None
            path = ""
            if job:
                with job["lock"]:
                    path = job.get("reader_path") or ""
            if not path or not os.path.isfile(path):
                html = st or ""
                if job and not html:
                    with job["lock"]:
                        html = job.get("html_state") or ""
                if html and "<html" in html.lower():
                    try:
                        base = os.path.join(OUT_DIR, (sid or "tmp")[:12])
                        os.makedirs(base, exist_ok=True)
                        path = os.path.join(base, "reader.html")
                        with open(path, "w", encoding="utf-8") as f:
                            f.write(html)
                        if job:
                            with job["lock"]:
                                job["reader_path"] = path
                    except Exception:
                        path = ""
            url = _reader_file_url(path)
            return gr.update(visible=False), (st if st is not None else gr.update()), url

        reader_url_box = gr.Textbox(value="", visible=False, elem_id="manga_reader_url")

        open_reader_js = """
(sid, sidBox, htmlSt, url) => {
  const u = (url || "").toString().trim();
  if (!u) {
    alert("صفحهٔ خواندن هنوز آماده نیست.");
    return [];
  }
  const w = window.open(u, "_blank");
  if (!w) {
    window.location.href = u;
  }
  return [];
}
"""

        try:
            btn_view.click(
                fn=_open_viewer,
                inputs=[session_id, sid_box, html_state],
                outputs=[viewer_html, html_state, reader_url_box],
            ).then(
                fn=None,
                inputs=[session_id, sid_box, html_state, reader_url_box],
                outputs=[],
                js=open_reader_js,
            )
        except Exception:
            try:
                btn_view.click(
                    fn=_open_viewer,
                    inputs=[session_id, sid_box, html_state],
                    outputs=[viewer_html, html_state, reader_url_box],
                )
            except Exception:
                pass

        gr.Markdown(
            "<div style='text-align:center; opacity:.45; margin-top:16px'>"
            "مانگا مترجم PRO · RT-DETR + Gemini/… + LaMa-Manga · اجرا روی CPU</div>"
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
    <img class="gh-avatar" src="data:image/png;base64,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" width="22" height="22" alt="gh" />
    سورس
  </a>
</div>
"""
        )

    
    
    dark_js = r"""
() => {
  document.body.classList.add('dark');
  document.documentElement.classList.add('dark');
  const tryBind = () => {
    try {
      const root = document.getElementById('manga_rdr') || document.querySelector('.rdr');
      if (!root || root._bound) return;
    } catch (e) {}
  };
  try {
    new MutationObserver(tryBind).observe(document.documentElement, { childList: true, subtree: true });
  } catch (e) {}
}
"""
    try:
        demo.load(None, None, None, js=dark_js)
    except Exception:
        try:
            demo.load(js=dark_js)
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
        launch_kw["css"] = WEB_CSS
    demo.queue(max_size=4).launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("MANGA_APP_PORT", "7860")),
        share=on_colab or on_codespace or (not has_display()),
        inline=on_colab,
        show_error=True,
        allowed_paths=[str(WORK_DIR), str(OUT_DIR), str(UPLOAD_DIR), str(FONT_DIR)],
        **launch_kw,
    )



def main():
    ensure_dirs()
    args = sys.argv[1:]

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
