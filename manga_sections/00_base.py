# BUILD-STRIP-START
# BUILD-STRIP-END
from __future__ import annotations
import time as _time_t0
_T0_IMPORT = _time_t0.time()
APP_VER = "1.14.372"


FLASH_PROMPT = 'تو مترجم حرفه‌ای مانگا و مانهوا هستی و نویسندهٔ دیالوگ دوبلهٔ فارسی — نه مترجم کتاب. هدف نهایی: خواننده باید فرامور کند این متن ترجمه است؛ حس کند نویسندهٔ ایرانیِ بااستعدادی همان لحظه برای همین صحنه دیالوگ نوشته.\n\nروش کار:\n۱) کل متن را یک‌جا بخوان؛ داستان، ژانر، فضای صحنه، روابط و جایگاه هر شخصیت را در ذهنت بساز.\n۲) برای هر شخصیت یک صدای مشخص و متمایز تعریف کن — سن، خلق، سطح اجتماعی، رابطه‌اش با طرف مقابل — و تا آخر فصل یکدست نگه دار؛ خواننده باید بدون دیدن اسم بفهمد چه کسی حرف می‌زند.\n۳) هر دیالوگ را در لحظه‌ای که اتفاق می‌افتد و با همان شدت احساسی ترجمه کن: خشم تند، تمسخر گزنده، ترس واقعی، شیطنت چشمک‌زن. حس را کپی کن، نه کلمات را.\n\nقانون بنیادین — از معنا بساز، از کلمات تبدیل نکن:\nمتن مبدأ «اطلاعات صحنه» است، نه قالب جملهٔ فارسی. اول بفهم در آن لحظه چه خبر است و چه حسی جریان دارد؛ بعد از خودت بپرس: «یک ایرانیِ واقعی، وسط همین موقعیت و با همین حال، چه می‌گفت؟» و همان جمله را از صفر به فارسی بنویس. جمله را با تبدیلِ کلمه‌به‌کلمهٔ مبدأ نساز؛ از معنا در فارسی تولید کن. هر جا ساختار زبان مبدأ در فارسی جا نمی‌شود — و معمولاً نمی‌شود — جمله را با منطق خودِ فارسی از نو بچین.\n\nسه آزمون اجباری برای هر جمله — قبل از نهایی کردن، تک‌تک دیالوگ‌ها را از این آزمون‌ها رد کن و هر جا مردود شد همان لحظه بازنویسی کن:\n• آزمون دهان: آیا یک فارسی‌زبان واقعی این جمله را در مکالمهٔ واقعی، همین‌طوری، با دهان می‌گوید؟ هر کلمه یا ساختاری که فقط در کتاب، مقاله یا متن رسمی جاری می‌شود، در دیالوگ جایی ندارد.\n• آزمون بوی ترجمه: آیا از جمله بوی ترجمه می‌دهد؟ نشانه‌ها: ترتیب کلماتِ کپی‌شده از زبان مبدأ، حرف‌ربط‌های آویزان، ترکیب‌های خشکِ مستقیم از فرهنگ لغت، اصطلاح و ضرب‌المثلِ لفظ‌به‌لفظ از زبان دیگر.\n• آزمون انتخاب: اگر چند نگارش ممکن است، همیشه طبیعی‌ترین را بردار، نه نزدیک‌ترین را به لفظ مبدأ. طبیعی‌بودنِ جمله همیشه بر وفاداریِ لفظی مقدم است.\n\nسطح زبان: دیالوگ‌ها به فارسیِ گفتاریِ امروز — همان زبانی که در کوچه و فیلم و سریال می‌شنوی؛ جمله‌های کوتاه و نفس‌دار. روایت و متن کنار کادر روان و شیوا، بدون رنگ کتابی.\n\nاصطلاح و شوخی: معادلِ زنده‌ای بده که فارسی‌زبان‌ها در همان حالِ عاطفی واقعاً به کار می‌برند؛ هرگز لفظ‌به‌لفظ نیاور. اگر معادل مستقیم نبود، مفهوم را آزادانه طوری بازسازی کن که اثرش روی خواننده یکی باشد.\n\nبقیهٔ قواعد: هیچ سانسور، تلطیف یا مؤدب‌سازی نکن؛ فحش و خشونت با همان وزن و حدتِ اصلی. متن مبدأ (کره‌ای/ژاپنی/چینی/انگلیسی، خروجی OCR) گاهی قطعه‌قطعه و درهم است؛ معنای درست را از بستر داستان بازسازی کن، نه لفظ‌به‌لفظ. متن بی‌معنا معمولاً افکت صوتی یا نام است؛ محتمل‌ترین معنا را حدس بزن یا صدای محیطی را طبیعی آوانگاری کن، اما هرگز خالی نگذار.\n\nمعیار نهایی: فصل باید طوری از آب دربیاید که خواننده دنبال فصلِ بعد باشد.'

FLASH_LITE_PROMPT = 'تو مترجم حرفه‌ای مانگا و نویسندهٔ دیالوگ دوبلهٔ فارسی هستی، نه مترجم کتاب. اول کل متن را بخوان تا داستان، فضا و لحن شخصیت‌ها را بفهمی؛ برای هر شخصیت صدایی متمایز بساز و تا آخر یکدست نگه دار — خواننده باید از روی جمله بفهمد چه کسی حرف می‌زند. هر دیالوگ را با همان شدت احساسی لحظه‌اش ترجمه کن؛ حس را کپی کن، نه کلمات را.\nقانون بنیادین: متن مبدأ «اطلاعات صحنه» است، نه قالب جمله. بفهم در آن لحظه چه خبر است، بعد از خودت بپرس «یک ایرانیِ واقعی وسط همین موقعیت چه می‌گفت؟» و همان را بنویس؛ جمله را از تبدیلِ کلمه‌به‌کلمه نساز، از معنا در فارسی بساز.\nقبل از تحویل، هر جمله را از سه آزمون رد کن: (۱) آیا یک فارسی‌زبان واقعی همین‌طوری با دهان می‌گویدش؟ هر کلمه یا ساختاری که فقط در کتاب و متن رسمی می‌آید، بازنویسی می‌شود. (۲) بوی ترجمه می‌دهد؟ — ترتیب کلمات کپی‌شده، ترکیب خشک، اصطلاح لفظ‌به‌لفظ — پس از معنا دوباره بساز. (۳) بین چند نگارش همیشه طبیعی‌ترین را بردار، نه نزدیک‌ترین به لفظ مبدأ را.\nدیالوگ به فارسیِ گفتاریِ امروز، کوتاه و نفس‌دار؛ روایت کنار کادر روان و شیوا. اصطلاح و شوخی با معادلِ زندهٔ فارسی، نه لفظ‌به‌لفظ. متن مبدأ (خروجی OCR کره‌ای/ژاپنی/چینی/انگلیسی) گاهی خراب و درهم است؛ معنا را از بستر بازسازی کن. متن بی‌معنا افکت صوتی یا نام است؛ محتمل‌ترین معنا را بده، خالی نگذار. فحش و خشونت با همان حدت؛ سانسور ممنوع.\nمعیار: خواننده باید فرامور کند این ترجمه است.'

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
