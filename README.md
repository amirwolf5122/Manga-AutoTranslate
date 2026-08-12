# مترجم خودکار مانگا / مانهوا (فارسی)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/amirwolf5122/Manga-AutoTranslate/blob/main/Manga_Translator_Colab.ipynb)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

ابزاری برای **ترجمهٔ خودکار صفحات مانگا و مانهوا به فارسی**:

متن را با OCR می‌خواند، متن اصلی را از داخل حباب پاک می‌کند، با **Gemini API** به فارسی محاوره‌ای ترجمه می‌کند و ترجمه را دوباره داخل همان حباب می‌نویسد.

---

## نمونه خروجی

| قبل | بعد |
|:---:|:---:|
| ![before](examples/before.png) | ![after](examples/after.png) |

---

## ویژگی‌ها

- **OCR** با PaddleOCR (پشتیبانی از انگلیسی / ژاپنی / کره‌ای و …)
- **ترجمه** با Google Gemini (چند API key با جابه‌جایی خودکار هنگام اتمام سهمیه)
- **پاک‌سازی هوشمند** متن قدیمی:
  - حباب سفید یکدست
  - پنل‌های رنگی / تیره (UI)
  - عنوان و لوگوی بزرگ روی پس‌زمینهٔ پیچیده
- **رندر فارسی** با reshaper + bidi و فونت فارسی (مثل Vazirmatn)
- ورودی: پوشه تصویر، یک تصویر، ZIP، PDF یا لینک صفحه
- خروجی: پوشه تصویر / ZIP / PDF
- عرض ثابت خروجی (پیش‌فرض **۹۰۰px**)
- ادامه از کش (`resume`) اگر اجرا قطع شود

---

## چهار روش اجرا

### ۱) Google Colab (پیشنهادی — بدون نصب روی سیستم)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/amirwolf5122/Manga-AutoTranslate/blob/main/Manga_Translator_Colab.ipynb)

1. یک Runtime با **GPU** بسازید:  
   `Runtime → Change runtime type → GPU (T4)`
2. همه سلول‌ها را با **Run all** اجرا کنید.

---
### ۲) اجرا با GitHub Actions (بدون نصب)

#### قدم اول — Fork
یک نسخه [fork](https://github.com/amirwolf5122/Manga-AutoTranslate/fork) جدا از ریپو بساز.

#### قدم دوم — گذاشتن کلید Gemini (مهم)
1. برو به ریپوی **fork** خودت  
2. **Settings** → **Secrets and variables** → **Actions**  
3. روی **New repository secret** بزن  
4. این مقادیر را وارد کن:
   - **Name:** `GEMINI_API_KEY`
   - **Secret:** کلید(های) Gemini — اگر چند تا داری با کاما جدا کن  
     مثال: `key1,key2,key3`
5. **Add secret** را بزن

> اگر Secret را نسازی، workflow با خطای «Secret با نام GEMINI_API_KEY تنظیم نشده» متوقف می‌شود.

#### قدم سوم — اجرای workflow
1. برو به تب **Actions**
2. workflow مربوط به ترجمه را انتخاب کن
3. روی **Run workflow** بزن
4. فقط این فیلدها را پر کن:
   - لینک / مسیر ورودی
   - زبان OCR (اختیاری)
   - مدل Gemini (اختیاری)
   - ترتیب خواندن (rtl / ltr)
   - فرمت خروجی (pdf / html / zip)
5. بعد از اتمام، از قسمت **Artifacts** فایل ترجمه‌شده را دانلود کن  
   (اسم artifact همان نام فصل است، نه `translated-manga`)

**نکات:**
- چون runnerهای GitHub GPU ندارند، پردازش روی CPU انجام می‌شود و نسبت به Colab کندتر است.
- برای فصل‌های خیلی بزرگ ممکن است به timeout برخورد کنید (حداکثر ۶ ساعت).
- کلید API در لاگ و صفحه Inputs دیده نمی‌شود (امن است).

---

### ۳) اجرا با GitHub Codespaces (محیط ابری کامل)

1. روی دکمه سبز **Code** کلیک کن → تب **Codespaces** → **Create codespace on main**
2. بعد از آماده شدن محیط، در ترمینال این دستور را بزن:

```bash
bash run.sh
```

یا برای ویندوز داخل Codespaces:

```bash
./run.bat
```

**مزایا:**
- محیط کامل لینوکسی آماده (مثل لوکال)
- نیازی به نصب چیزی روی سیستم خودت نیست
- می‌تونی فایل‌ها را مستقیم آپلود کنی یا از لینک استفاده کنی
- امکان استفاده از GPU در بعضی پلن‌ها وجود دارد

**نکته:** بعد از اتمام کار، Codespace را Stop کن تا منابع مصرف نشود.

---

### ۴) اجرای دستی (لوکال)

```bash
git clone https://github.com/amirwolf5122/Manga-AutoTranslate.git
cd Manga-AutoTranslate

python -m venv .venv
source .venv/bin/activate          # لینوکس / مک
# .venv\Scripts\activate           # ویندوز
```

```bash
# لینوکس / مک:
bash run.sh

# ویندوز:
run.bat
```

---

## پارامترهای مهم

| پارامتر | توضیح | پیش‌فرض |
|--------|--------|---------|
| `-i / --input` | پوشه، تصویر، ZIP، PDF یا URL | اجباری |
| `-o / --output` | مسیر خروجی (`.pdf` / `.zip` / پوشه) | اجباری |
| `--font` | مسیر فونت TTF فارسی | اجباری |
| `--api-key` | کلید Gemini (قابل تکرار یا با کاما) | یا `GEMINI_API_KEY` |
| `--ocr-lang` | زبان OCR (`en` / `ko en` / `ja en`) | `en` |
| `--reading-order` | `rtl` یا `ltr` | `rtl` |
| `--model` | مدل Gemini | `gemini-flash-latest` |
| `--max-width` | عرض ثابت خروجی (پیکسل) | `900` |
| `--img-format` | `webp` / `png` / `jpg` | `webp` |
| `--quality` | کیفیت فشرده‌سازی ۱–۱۰۰ | `80` |
| `--gpu` / `--cpu` | اجبار GPU یا CPU | تشخیص خودکار |
| `--no-resume` | نادیده گرفتن کش و پردازش دوباره | — |

---

## نکات OCR

- اگر صفحه از قبل **اسکنلیشن انگلیسی** است → `--ocr-lang en`
- اسکن خام **کره‌ای** → `--ocr-lang ko en`
- اسکن خام **ژاپنی** → `--ocr-lang ja en`

---

## محدودیت‌ها

- عنوان‌ها و لوگوهای خیلی بزرگ که با نقاشی قاطی شده‌اند ممکن است کاملاً پاک نشوند.
- کیفیت ترجمه به مدل Gemini و کیفیت OCR بستگی دارد.
- برای پس‌زمینه‌های بسیار شلوغ، inpaint ساده گاهی کافی نیست.

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

## لایسنس

MIT — آزاد برای استفاده شخصی و غیرتجاری.

حقوق مانگا/مانهوا متعلق به ناشر و خالق اثر است؛ این ابزار فقط برای مطالعهٔ شخصی است.
