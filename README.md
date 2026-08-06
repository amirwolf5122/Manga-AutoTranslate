# مترجم خودکار مانگا / مانهوا (فارسی)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/amirwolf5122//Manga-AutoTranslate/blob/main/Manga_Translator_Colab.ipynb)
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

## سه روش اجرا

### ۱) Google Colab (پیشنهادی — بدون نصب روی سیستم)


[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/amirwolf5122//Manga-AutoTranslate/blob/main/Manga_Translator_Colab.ipynb)

1. یک Runtime با **GPU** بسازید:  
   `Runtime → Change runtime type → GPU (T4)`
2. [نوت‌بوک Colab](https://colab.research.google.com/github/amirwolf5122/Manga-AutoTranslate/blob/main/Manga_Translator_Colab.ipynb) را باز کنید یا سلول‌ها را یکی‌یکی اجرا کنید!

---

### ۲) اجرا با GitHub Actions (بدون نصب)

#### نحوه استفاده:

1. برو به تب **Actions**
2. یکی از سه workflow بالا را انتخاب کن
3. روی **Run workflow** بزن
4. فیلدهای لازم را پر کن (لینک یا فایل + کلید Gemini)
5. بعد از اتمام، از قسمت **Artifacts** فایل ترجمه‌شده را دانلود کن

**نکات:**
- فونت اختیاری است؛ اگر نزنید خودش Vazirmatn را استفاده می‌کند.
- چون runnerهای GitHub GPU ندارند، پردازش روی CPU انجام می‌شود و نسبت به Colab کندتر است.
- برای فصل‌های خیلی بزرگ ممکن است به timeout برخورد کنید (حداکثر ۶ ساعت).

---
 ### ۳) اجرای دستی (لوکال)
```bash
git clone https://github.com/YOUR_USER/manga-translator-fa.git
cd manga-translator-fa

python -m venv .venv
source .venv/bin/activate   # ویندوز: .venv\Scripts\activate

pip install -r requirements.txt

# فونت فارسی
mkdir -p fonts
# Vazirmatn را از https://github.com/rastikerdar/vazirmatn دانلود کنید
```

```bash
python manga_translator.py \
  -i ./pages \
  -o ./output_fa.pdf \
  --font fonts/Vazirmatn-Bold.ttf \
  --ocr-lang en \
  --api-key "$GEMINI_API_KEY"
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
├── requirements.txt
├── README.md
├── examples/             # قبل / بعد
│   ├── before.png
│   └── after.png
└── fonts/                # فونت فارسی (دانلود جداگانه)
```

---

## لایسنس

MIT — آزاد برای استفاده شخصی و غیرتجاری.  
حقوق مانگا/مانهوا متعلق به ناشر و خالق اثر است؛ این ابزار فقط برای مطالعهٔ شخصی است.
