# مترجم خودکار مانگا / مانهوا (فارسی)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/amirwolf5122/Manga-AutoTranslate/blob/main/Manga_Translator_Colab.ipynb)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

ابزاری برای **ترجمهٔ خودکار صفحات مانگا و مانهوا به فارسی**.

متن را با OCR می‌خواند، متن اصلی را از داخل حباب پاک می‌کند، با **مدل‌های AI** (Gemini / OpenAI / DeepSeek / …) به فارسی محاوره‌ای ترجمه می‌کند و ترجمه را دوباره داخل همان حباب می‌نویسد.

---

## چی کار می‌کند؟ (خلاصهٔ فرآیند)

1. **ورودی** را می‌گیرد: پوشه تصویر، یک تصویر، ZIP، PDF یا URL مستقیم/صفحهٔ فصل
2. **OCR** با PaddleOCR متن هر حباب را استخراج می‌کند (انگلیسی / کره‌ای / ژاپنی)
3. متن‌های تبلیغاتی، واترمارک و SFX را جدا می‌کند تا ترجمه نشوند
4. فحش‌های سانسور‌شده (`fu*ck`، `sh*t` و …) را کامل می‌کند
5. با مدل انتخابی به فارسی محاوره‌ای و خیابونی ترجمه می‌کند
6. متن اصلی را با **LaMa** (اگر GPU باشد) یا **OpenCV inpaint** پاک می‌کند
7. متن فارسی را با فونت انتخابی داخل حباب می‌نویسد
8. خروجی را به صورت **PDF / ZIP / پوشه تصویر / HTML** ذخیره می‌کند

---

## ویژگی‌ها

| ویژگی | توضیح |
|--------|--------|
| **OCR** | PaddleOCR — پشتیبانی از `en` / `ko` / `ja` |
| **چند ارائه‌دهنده AI** | Gemini، OpenAI/ChatGPT، DeepSeek، Groq، xAI/Grok، Together، OpenRouter، Ollama |
| **Fallback مدل (Gemini)** | اگر مدل در دسترس نبود، فوری مدل بعدی را امتحان می‌کند |
| **چند کلید API** | جابه‌جایی خودکار روی سهمیه / خطا |
| **پاک‌سازی متن** | LaMa (GPU) یا OpenCV inpaint (CPU) |
| **رندر فارسی** | reshaper + bidi + یک فونت TTF فارسی |
| **ورودی** | پوشه، تصویر، ZIP، PDF، URL تصویر یا صفحهٔ فصل |
| **خروجی** | پوشه تصویر / ZIP / PDF / HTML |
| **عرض ثابت** | همه صفحات به عرض یکسان (پیش‌فرض ۹۰۰px) |
| **Resume / کش** | اگر اجرا قطع شود از کش ادامه می‌دهد |
| **Chunking** | صفحات خیلی بلند را تکه‌تکه OCR می‌کند |

---

## ارائه‌دهنده‌های پشتیبانی‌شده

| `--provider` | پیش‌فرض مدل | متغیر محیطی کلید |
|--------------|-------------|------------------|
| `gemini` | `gemini-flash-latest` | `GEMINI_API_KEY` |
| `openai` / `chatgpt` | `gpt-4o-mini` | `OPENAI_API_KEY` |
| `deepseek` | `deepseek-chat` | `DEEPSEEK_API_KEY` |
| `groq` | `llama-3.3-70b-versatile` | `GROQ_API_KEY` |
| `xai` / `grok` | `grok-2-latest` | `XAI_API_KEY` |
| `together` | `meta-llama/Llama-3.3-70B-Instruct-Turbo` | `TOGETHER_API_KEY` |
| `openrouter` | `google/gemini-2.0-flash-001` | `OPENROUTER_API_KEY` |
| `ollama` | `llama3.2` | (اختیاری) |

برای هر provider می‌توانی با `--model` مدل دیگری بگذاری و با `--api-base` آدرس پایه را عوض کنی.

---

## پارامترهای مهم

| پارامتر | توضیح | پیش‌فرض |
|--------|--------|---------|
| `-i` / `--input` | پوشه، تصویر، ZIP، PDF یا URL | **اجباری** |
| `-o` / `--output` | مسیر خروجی (`.pdf` / `.zip` / `.html` / پوشه) | **اجباری** |
| `--font` | مسیر فونت TTF فارسی | **اجباری** |
| `--provider` | ارائه‌دهنده AI (جدول بالا) | `gemini` |
| `--api-key` | کلید API (قابل تکرار یا با کاما) | یا env مربوطه |
| `--api-base` | آدرس پایه API (اختیاری) | پیش‌فرض provider |
| `--model` | نام مدل | پیش‌فرض provider |
| `--ocr-lang` | زبان OCR (`en` / `ko en` / `ja en`) | `en` |
| `--reading-order` | ترتیب خواندن حباب‌ها: `rtl` یا `ltr` | `rtl` |
| `--max-width` | عرض ثابت خروجی (پیکسل) | `900` |
| `--img-format` | فرمت تصاویر خروجی: `webp` / `png` / `jpg` | `jpg` |
| `--quality` | کیفیت فشرده‌سازی ۱–۱۰۰ | `80` |
| `--gpu` / `--cpu` | اجبار GPU یا CPU | تشخیص خودکار |
| `--no-resume` | نادیده گرفتن کش و پردازش دوباره | — |
| `--keep-old` | کش و خروجی فصل‌های قبلی را پاک نکن | — |
| `--temperature` | دمای مدل (بالاتر = محاوره‌ای‌تر) | `0.85` |
| `--max-retries` | حداکثر تلاش ترجمه در صورت خطا | `4` |
| `--request-delay` | تأخیر بین درخواست‌های API (ثانیه) | `0` |
| `--workers` | تعداد تیکه‌های موازی OCR | `1` |
| `--max-chunk-height` | حداکثر ارتفاع هر تکه OCR (پیکسل) | `3600` |
| `--min-confidence` | حداقل اطمینان OCR برای قبول متن | `0.12` |
| `--mask-padding` | حاشیه ثابت دور حروف هنگام پاک‌سازی | `3` |
| `--pad-ratio` | حاشیه نسبی دور حروف | `0.06` |
| `--inpaint-radius` | شعاع inpaint برای حالت OpenCV | `3` |
| `--no-two-pass-ocr` | غیرفعال کردن پاس دوم OCR (سریع‌تر، دقت کمتر) | — |

---

## توضیح جزئی‌تر پارامترها

### ورودی و خروجی
- **`--input`**: می‌تواند پوشهٔ تصاویر، یک فایل تصویر، ZIP، PDF، لینک مستقیم تصویر، یا لینک صفحهٔ فصل (مثل Asura Scans) باشد.
- **`--output`**: اگر `.pdf` بگذاری خروجی یک PDF می‌شود؛ `.zip` → آرشیو تصاویر؛ `.html` → صفحهٔ وب؛ بدون پسوند → پوشهٔ تصاویر.

### فونت
- **`--font`**: فقط **یک** فونت برای همهٔ متن‌ها استفاده می‌شود.
- پیشنهاد: `Vazirmatn-Regular.ttf` (خوانا و پایدار).

### مدل و API
- **`--provider`**: تعیین می‌کند از کدام سرویس استفاده شود.
- **`--model`**: اگر ندهی، مدل پیش‌فرض همان provider استفاده می‌شود.
- **Gemini**: اگر مدل ۵۰۳/UNAVAILABLE بدهد، **فوری** مدل بعدی در زنجیره امتحان می‌شود:
  ```
  gemini-2.5-flash → gemini-flash-latest → gemini-2.5-flash-lite → …
  ```
- چند کلید API را با کاما یا چند بار `--api-key` بده؛ روی سهمیه/خطا خودکار جابه‌جا می‌شود.
- متغیرهای محیطی هم پشتیبانی می‌شوند (`GEMINI_API_KEY`، `OPENAI_API_KEY`، `DEEPSEEK_API_KEY` و …).

### OCR
- صفحهٔ اسکنلیشن انگلیسی → `--ocr-lang en`
- اسکن خام کره‌ای → `--ocr-lang ko en`
- اسکن خام ژاپنی → `--ocr-lang ja en`
- **`--no-two-pass-ocr`**: پاس دوم (CLAHE/invert) را خاموش می‌کند → سریع‌تر ولی ممکن است متن‌های کم‌کنتراست را از دست بدهد.

### پاک‌سازی
- اگر GPU و LaMa در دسترس باشد → inpaint با کیفیت بالاتر
- در غیر این صورت → OpenCV inpaint (دو پاس)


---

## چهار روش اجرا

### ۱) Google Colab (پیشنهادی)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/amirwolf5122/Manga-AutoTranslate/blob/main/Manga_Translator_Colab.ipynb)

1. Runtime را روی **GPU (T4)** بگذار  
2. همه سلول‌ها را با **Run all** اجرا کن

### ۲) GitHub Actions

1. ریپو را [Fork](https://github.com/amirwolf5122/Manga-AutoTranslate/fork) کن  
2. در Settings → Secrets کلید موردنظر را بگذار (`GEMINI_API_KEY` یا `OPENAI_API_KEY` و …)  
3. از تب Actions ورک‌فلو را Run کن  
4. خروجی را از Artifacts دانلود کن  

> Runnerهای GitHub GPU ندارند؛ روی CPU کندتر است.

### ۳) GitHub Codespaces

```bash
bash run.sh
```

### ۴) اجرای لوکال

```bash
git clone https://github.com/amirwolf5122/Manga-AutoTranslate.git
cd Manga-AutoTranslate
python -m venv .venv
source .venv/bin/activate   # ویندوز: .venv\Scripts\activate
bash run.sh                 # ویندوز: run.bat
```

---

## محدودیت‌ها

- عنوان‌ها و لوگوهای خیلی بزرگ که با نقاشی قاطی شده‌اند ممکن است کاملاً پاک نشوند.
- کیفیت ترجمه به مدل انتخابی و کیفیت OCR بستگی دارد.
- روی CPU، inpaint ساده‌تر است و ممکن است لکه بماند.
- واترمارک‌های نصفه‌کاره گاهی به‌اشتباه دیالوگ تشخیص داده می‌شوند.
- بعضی مدل‌های OpenAI-compatible ممکن است فرمت JSON را دقیق رعایت نکنند؛ در این صورت با `--max-retries` بیشتر امتحان کن.

---

## ساختار پروژه

```text
Manga-AutoTranslate/
├── manga_translator.py   # اسکریپت اصلی
├── run.sh                # رانر تعاملی لینوکس/مک
├── run.bat               # رانر تعاملی ویندوز
├── requirements.txt
├── README.md
└── fonts/                # فونت فارسی (دانلود جداگانه)
```

---

## حمایت مالی
ヾ(•ω•`)o


Ton:`UQBScvayaxagwTfRBhlLNaqw-sZuadlnBjSvn8OJz7XZJJzT`

-

TRX:`TMmLTaCjaW1L2xWZmpR2EBeNyCawCzEkwa`

---
## لایسنس

MIT — آزاد برای استفاده شخصی و غیرتجاری.

حقوق مانگا/مانهوا متعلق به ناشر و خالق اثر است؛ این ابزار فقط برای مطالعهٔ شخصی است.
