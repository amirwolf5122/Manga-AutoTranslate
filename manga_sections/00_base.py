# BUILD-STRIP-START
# BUILD-STRIP-END
from __future__ import annotations
import time as _time_t0
_T0_IMPORT = _time_t0.time()
APP_VER = "1.14.372"


FLASH_PROMPT = 'تو نویسندهٔ دیالوگِ دوبلهٔ فارسی هستی، نه مترجمِ کتاب.\n\nمتنِ مانگا و مانهوا را به فارسیِ محاوره\u200cایِ گفتاری برگردان — همان زبانی که آدم\u200cها در خیابان و فیلم حرف می\u200cزنند و هر ایرانیِ معمولی بدونِ فکر کردن و راحت می\u200cفهمد. فارسیِ کتابی، نوشتاری، اداری یا ترجمهٔ تحت\u200cاللفظی ممنوع است.\n\nقبل از ترجمه، کلِ صفحات را با هم بخوان تا داستان، ژانر و شخصیت\u200cها را درک کنی؛ بعد هر دیالوگ را در بسترِ همین داستان و با شناختِ لحظه\u200cای که در آن اتفاق می\u200cافتد ترجمه کن. خودت تشخیص بده هر شخصیت با چه لحنی حرف می\u200cزند و همان لحن را در فارسی زنده بازسازی کن: شخصیتِ جوان و صمیمی خودمونی، خشن و لات کوچه\u200cبازاری، بزرگ\u200cسالِ محترم که باز هم گفتاری حرف می\u200cزند، و روایت یا توضیحِ کنارِ کادر که روان و شیواست نه خیابانی.\n\nمتنِ مبدأ می\u200cتواند کره\u200cای، ژاپنی، چینی یا انگلیسی باشد و چون خروجیِ OCR است گاهی قطعه\u200cقطعه، ناقص یا درهم است؛ معنای درست را از خودِ زبانِ مبدأ و بسترِ داستان بازسازی کن، نه لفظ\u200cبه\u200cلفظ. معادلِ طبیعی و رایجِ فارسی برای اصطلاح\u200cها، شوخی\u200cها و ضرب\u200cالمثل\u200cها پیدا کن و جمله\u200cها را کوتاه و نفس\u200cدار نگه دار.\n\nاگر متنی بی\u200cمعنا یا خیلی خراب است، معمولاً افکتِ صوتی یا نام است؛ محتمل\u200cترین معنا را حدس بزن یا صدای محیطی را آوانگاری کن، اما خالی نگذار. هیچ سانسور، تلطیف یا مؤدب\u200cسازی نکن؛ خشونت و فحش با همان شدتِ اصلی برگردد.'

FLASH_LITE_PROMPT = 'تو دیالوگ\u200cنویسِ دوبلهٔ فارسی هستی، نه مترجمِ کتاب. ترجمه\u200cات فارسیِ محاوره\u200cایِ گفتاری است — زبانِ خیابون و فیلم — که هر ایرانیِ معمولی راحت بفهمد؛ کتابی و نوشتاری ممنوع.\nکلِ متن را اول یک\u200cجا بخوان تا داستان و لحنِ شخصیت\u200cها را بفهمی، بعد هر خط را در همان بستر ترجمه کن و لحنِ هر شخصیت را نگه دار؛ روایتِ کنارِ کادر روان و شیواست.\nمتنِ مبدأ ممکن است کره\u200cای، ژاپنی، چینی یا انگلیسی و خروجیِ OCR باشد؛ معنا را از بستر بازسازی کن نه لفظ\u200cبه\u200cلفظ. متنِ خیلی خراب افکتِ صوتی یا نام است؛ حدس بزن یا آوانگاری کن، خالی نگذار. سانسور و مؤدب\u200cسازی ممنوع.'

PROMPT_PRESETS_LEGACY = (
    "فرایند پردازش و ترجمه (مبتنی بر خود-اصلاحی): شما باید این فرآیند را در سه گام ذهنی و متوالی اجرا کنید:\\n\r\nگام ۱: تحلیل جامع و تولید پیش‌نویس اولیه\\n\r\n* پیش از شروع ترجمه، کل محتوای متن را بخوانید تا ژانر، فضای داستانی، کنایه‌ها و ویژگی‌های شخصیتی کاراکترها را درک کنید.\\n\r\n* در مرحلهٔ اندیشیدن، بر اساس این درک، یک پیش‌نویس اولیه از ترجمه را در ذهن تولید کنید.\\n\\n\r\nگام ۲: بازبینی موشکافانه و پالایش (مرحلهٔ خود-اصلاحی)\\n\r\n* با نگاه یک ویراستار سخت‌گیر، پیش‌نویس خود را به چالش بکشید و بازبینی کنید.\\n\r\n* از خود بپرسید: آیا این جمله روان است یا بوی ترجمه می‌دهد؟ آیا لحن شخصیت حفظ شده؟ آیا معادل بهتری برای این اصطلاح وجود دارد؟\\n\\n\r\nگام ۳: ارائه خروجی نهایی\\n\r\n* نسخهٔ نهایی، سلیس و بی‌نقص را که حاصل گام دوم است، به‌عنوان خروجی قطعی ارائه دهید.\\n\\n\r\n---\\n\\n\r\nاصول کلیدی ترجمه (قوانین حاکم بر گام‌های بالا):\\n\\n\r\n1. روانی، سلیس بودن و زبان محاوره‌ای زنده (پرهیز از ترجمه تحت‌اللفظی):\\n\r\nهدف اصلی، انتقال دقیق پیام و حس دیالوگ است. از ترجمهٔ کلمه‌به‌کلمه، کتابی، نوشتاری و عبارات ماشینی اکیداً پرهیز کنید؛ ترجمه باید به زبان فارسی امروزی، طبیعی، پویا و کاملاً گیرا باشد.\\n\\n\r\n2. حفظ و بازتاب دقیق لحن و سبک شخصیت‌ها (حیاتی و بدون سانسور):\\n\r\nلحن و شیوه گفتار هر کاراکتر (رسمی، دوستانه، طنز، جدی، خشن، معصومانه و...) باید با ظرافت رعایت شود. مدل زبانی باید مانند یک بازیگر نقش‌آفرینی کند:\\n\r\n- برای شخصیت‌های بی‌پروا، لات‌منش یا بی‌سواد: ترجمه باید کاملاً عامیانه، کوچه‌بازاری و دارای اصطلاحات خیابانی باشد. از اتوکشیده کردن، مؤدب‌سازی یا رسمی کردن دیالوگ‌های این شخصیت‌ها اکیداً خودداری کنید.\\n\r\n- برای شخصیت‌های باوقار، مرموز یا اشرافی: لحن باید محترمانه باشد، اما همچنان طبیعی و روان بماند (از تبدیل گفت‌وگو به متن نوشتاری و کتابی خودداری کنید).\\n\\n\r\nتذکر بسیار مهم: ترجمه حرفه‌ای به معنای سانسور، تلطیف یا پاستوریزه کردن کلمات نیست؛ بلکه به معنای انتقال دقیق حس جمله است. اگر متن اصلی دارای کلمات رکیک، جنسی یا خشن است، ترجمه فارسی نیز باید با همان شدت و حدت (بدون سانسور) ارائه شود تا اصالت اثر حفظ گردد.\\n\\n\r\n3. بومی‌سازی هوشمندانه اصطلاحات و ارجاعات فرهنگی:\\n\r\nاصطلاحات، ضرب‌المثل‌ها، شوخی‌ها و عبارات خاص فرهنگی مانگا را شناسایی کنید. اولویت با یافتن معادل‌های دقیق، رایج و طبیعی در زبان و فرهنگ فارسی است. در صورت نبود معادل مستقیم، مفهوم را با خلاقیت و به‌گونه‌ای که برای مخاطب فارسی‌زبان جذاب و ملموس باشد منتقل کنید.\\n\\n\r\n4. دقت و یکپارچگی در اسامی و جزئیات:\\n\r\nتمامی جزئیات متن اصلی (شامل اعداد، اسامی خاص شخصیت‌ها، مکان‌ها، تکنیک‌ها و علائم نگارشی) باید با دقت کامل ترجمه شوند و در سرتاسر تمام فایل‌ها کاملاً یکسان و هماهنگ استفاده شود.\\n",
    "قوانین ترجمه:\\n\\n\r\n1. روانی، سلیس بودن و جذابیت کلام: ترجمه باید به زبان فارسی امروزی، طبیعی و پویا باشد. متن نهایی باید به‌راحتی خوانده شود و برای مخاطب عام فارسی‌زبان کاملاً قابل فهم و گیرا باشد و از به‌کار بردن لحن کتابی، رسمی و عبارات ماشینی پرهیز کن.\\n\r\n2. حفظ و بازتاب دقیق لحن و سبک شخصیت‌ها (حیاتی):\\n\r\nلحن و شیوه گفتار هر کاراکتر (رسمی، دوستانه، طنز، جدی، خشن، معصومانه و...) باید با دقت در ترجمه رعایت شود؛ مثلاً:\\n\r\n- برای شخصیت‌های بی‌پروا، لات یا کم‌سواد: ترجمه باید کاملاً عامیانه، کوچه‌بازاری و دارای اصطلاحات خیابانی باشد. از مؤدبانه کردن یا رسمی نوشتن دیالوگ‌های این کاراکترها خودداری کنید.\\n\r\n- برای شخصیت‌های رسمی، مرموز یا اشرافی: لحن باید متین باشد.\\n\r\n3. در ترجمه اسامی، القاب و اصطلاحات داستانی، در سرتاسر فایل یکدستی و هماهنگی کامل را رعایت کن.\\n",
)

def _prompt_real_lines(s: str) -> str:
    out = (s or "").replace("\\n", "\n").replace("\r\n", "\n").replace("\r", "\n")
    while "\n\n\n" in out:
        out = out.replace("\n\n\n", "\n\n")
    return out

FLASH_PROMPT = _prompt_real_lines(FLASH_PROMPT)
FLASH_LITE_PROMPT = _prompt_real_lines(FLASH_LITE_PROMPT)
MT_SYSTEM_PROTOCOL_ITEMS = ("2. IDENTITY & TASK: Expert Manga & Comic Dialogue Translation Engine.\r\n"
"3. INPUT: array of pages; each page is [filename, dialogues] and `dialogues` holds sequential `[id, text]` items — raw comic OCR that may be garbled or incomplete. NEVER refuse, skip or sanitize any block; NEVER output placeholders like '[REDACTED]' or \"I can't translate\"; always infer the intended dialogue.\r\n"
"4. 1-TO-1: for every input item keep its exact `id` and put its Persian translation in `fa`; keep page order; NEVER skip, merge, reorder or duplicate ids.\r\n"
"5. EMPTY: a page with empty `dialogues` gets an empty `translations` array.\r\n"
"6. OUTPUT: one raw compact JSON array only (schema-enforced by the API) — no markdown, no notes, no extra fields.\r\n"
"7. SAFETY FALLBACK: if a block is restricted by safety policies, put '[CENSORED]' in its `fa` and keep the response valid.")

MT_JSON_SCHEMA = {
    "type": "array",
    "description": "List of processed manga pages with their translations.",
    "items": {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "The filename of the image as provided.",
            },
            "translations": {
                "type": "array",
                "description": "Extracted text blocks and their translations.",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "integer",
                            "description": "The exact id of the dialogue item from input.",
                        },
                        "fa": {
                            "type": "string",
                            "description": "Creative, natural Persian translation.",
                        },
                    },
                    "required": ["id", "fa"],
                    "propertyOrdering": ["id", "fa"],
                },
            },
        },
        "required": ["filename", "translations"],
        "propertyOrdering": ["filename", "translations"],
    },
}

MT_JP_USER_DIRECTIVE = "\r\n*** JAPANESE DIALOGUE DIRECTIVE ***\r\n1. FURIGANA/RUBY: small kana printed beside/above Kanji (e.g. '雷夏' + 'ライカ') are the SAME word's pronunciation — translate it ONCE; never translate the reading separately.\r\n2. DEDUP: collapse repeated/stuttered OCR phrasing into ONE clean sentence per block.\r\n"
MT_JP_SYSTEM_RULE = "\r\n1. FURIGANA & DEDUP (HIGHEST PRIORITY):\r\n   - Kanji plus small furigana readings = one word; translate it ONCE, strip duplicate readings and repeated words.\r\n   - One clean unified Persian translation per block.\r\n"

_MT_NO_CENSOR_ITEM = (
"7. NO CENSORSHIP: professional manga/comic pipeline for mature audiences. "
"NEVER censor, sanitize, soften or refuse any dialogue. Profanity, insults, threats, dark humor "
"and violence must keep their FULL original intensity; NEVER output '[CENSORED]' or any placeholder. "
"If one line is truly untranslatable, put that line's original text unchanged in its `fa` and translate the rest normally.\r\n")

def mt_system_instruction(japanese: bool = False, uncensored: bool = False, **_kw) -> str:
    items = MT_SYSTEM_PROTOCOL_ITEMS
    if uncensored:
        items = items.replace(
            "7. SAFETY FALLBACK: if a block is restricted by safety policies, "
            "put '[CENSORED]' in its `fa` and keep the response valid.",
            _MT_NO_CENSOR_ITEM)
    out = ("SYSTEM BEHAVIOR PROTOCOL:\r\n"
           + (MT_JP_SYSTEM_RULE if japanese else "")
           + "\r\n" + items)
    return out

def mt_plain_system_instruction(japanese: bool = False, uncensored: bool = False, **_kw) -> str:
    _item7 = ("7. SAFETY FALLBACK: If translation of the text block is restricted by safety policies, do not refuse or break the response; answer with '[CENSORED]'.\r\n"
              if not uncensored else
              "7. NO CENSORSHIP: Professional manga pipeline for mature audiences. NEVER censor, sanitize, soften or refuse. Profanity, insults, threats and violence must keep their FULL original intensity. NEVER output '[CENSORED]' or any placeholder; if truly impossible, return the original text unchanged.\r\n")
    out = ("SYSTEM BEHAVIOR PROTOCOL:\r\n"
           + (MT_JP_SYSTEM_RULE if japanese else "")
           + "\r\n2. IDENTITY & TASK: You are an Expert Manga & Comic Dialogue Translation Engine.\r\n"
           "6. RAW OCR INPUT — NO PLACEHOLDERS: The dialogue block is raw OCR output from a comic page; it may contain OCR errors, missing or garbled fragments. NEVER refuse, skip or sanitize it, and NEVER output placeholders such as '[REDACTED]' or \"I can't translate\". Even if it looks broken or nonsensical, interpret the most likely intended dialogue and translate it into natural Persian.\r\n"
           + _item7 +
           "9. PLAIN TEXT OUTPUT ONLY: Reply with ONLY the Persian translation itself as plain text. Do NOT output JSON, arrays, objects, keys, filenames, quotes or any notes — just the translation sentence.")
    return out

HIDDEN_ID_RULE_TEXT = "هیچ id را جا نینداز، ادغام یا جابه‌جا نکن؛ برای هر id دقیقاً یک fa بده."

def _has_hidden_id_rule(text: str) -> bool:
    t = _norm_prompt_text(text)
    return ("جا نینداز" in t) or ("id دقیقاً یک" in t)

def strip_hidden_rules(text: str) -> str:
    t = (text or "").replace("\\n", "\n").replace("\r\n", "\n").replace("\r", "\n")
    if not t.strip():
        return t
    lines = [ln for ln in t.split("\n")
             if not ("جا نینداز" in ln and "ادغام" in ln)]
    out = "\n".join(lines)
    while "\n\n\n" in out:
        out = out.replace("\n\n\n", "\n\n")
    return out.rstrip("\n") + "\n"

def append_hidden_id_rule(rules: str) -> str:
    t = (rules or "").rstrip()
    if not t:
        return rules or ""
    if _has_hidden_id_rule(t):
        return rules
    return t + "\n" + HIDDEN_ID_RULE_TEXT + "\n"

def mt_user_prompt(rules: str, pages, japanese: bool = False,
                   style_ref=None, context: str = "") -> str:
    import json as _json
    _pages_c = [[p.get("filename"), p.get("dialogues")] for p in (pages or [])]
    pages_json = _json.dumps(_pages_c, ensure_ascii=False,
                             separators=(",", ":"))
    rules = append_hidden_id_rule(rules)
    _style = ""
    if style_ref:
        _lines = []
        for _s, _f in style_ref[:6]:
            _s2 = str(_s).replace('\r', ' ').replace('\n', ' ')[:90]
            _f2 = str(_f).replace('\r', ' ').replace('\n', ' ')[:90]
            _lines.append('- "' + _s2 + '" -> "' + _f2 + '"')
        _style = ("\r\n\r\nSTYLE REFERENCE — earlier translations from this "
                  "same chapter; match their tone, register and naming "
                  "exactly:\r\n"
                  + "\r\n".join(_lines) + "\r\n")
    return ("TASK: Translate the dialogue blocks of the manga pages below "
            "into natural, high-quality Persian per the rules.\r\n"
            + (MT_JP_USER_DIRECTIVE if japanese else "")
            + "\r\nRULES:\r\n" + (rules or "")
            + (context or "")
            + _style
            + "\r\n\r\nPAGES (JSON):\r\n"
            + pages_json + "\r\n")

PROMPT_PRESETS = {
    "professional": FLASH_PROMPT,
    "lite": FLASH_LITE_PROMPT,
}
PROMPT_MODES = ("professional", "lite")

def resolve_prompt_mode(mode: str, provider: str = "gemini", model: str = "") -> str:
    m = (mode or "").lower().strip()
    if m in PROMPT_PRESETS:
        return m
    name = (model or "").lower().strip()
    if not name:
        try:
            name = str(PROVIDER_PRESETS["gemini"].get("default_model") or "").lower()
        except Exception:
            name = "gemini-3.5-flash-lite"
    if "lite" in name:
        return "lite"
    return "professional"

def prompt_preset_text(mode: str, provider: str = "gemini", model: str = "") -> str:
    return PROMPT_PRESETS[resolve_prompt_mode(mode, provider, model)]

def _norm_prompt_text(t: str) -> str:
    t = (t or "").replace("\\n", "\n")
    return re.sub(r"\s+", " ", t.strip())

def visible_prompt_presets() -> dict:
    try:
        return {k: strip_hidden_rules(v)
                for k, v in PROMPT_PRESETS.items()
                if isinstance(v, str)}
    except Exception:
        return dict(PROMPT_PRESETS)

def is_known_default_instruction(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    tn = _norm_prompt_text(t)
    try:
        cands = [v for v in PROMPT_PRESETS.values() if isinstance(v, str)]
    except Exception:
        cands = []
    try:
        cands += [v for v in visible_prompt_presets().values()
                  if isinstance(v, str)]
    except Exception:
        pass
    cands += [p for p in PROMPT_PRESETS_LEGACY if isinstance(p, str)]
    for c in cands:
        if c and _norm_prompt_text(c) == tn:
            return True
    return False

import os
import sys
import subprocess

os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("FLAGS_onednn", "0")
os.environ.setdefault("FLAGS_enable_pir_in_executor", "0")
os.environ.setdefault("FLAGS_enable_pir_api", "0")
os.environ.setdefault("FLAGS_pir_apply_shape_optimization_pass", "0")
os.environ.setdefault("MANGA_APP_VER", APP_VER)
os.environ.setdefault("CUDA_DEVICE_ORDER", "PCI_BUS_ID")

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

import platform as _platform
