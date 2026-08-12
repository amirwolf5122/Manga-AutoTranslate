@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ========================================
echo  مترجم خودکار مانگا / مانهوا (فارسی)
echo ========================================
echo.

echo ۰) بررسی و نصب وابستگی‌ها...

(
echo numpy==1.26.4
echo opencv-python-headless==4.8.1.78
echo opencv-python==4.8.1.78
echo opencv-contrib-python==4.8.1.78
) > constraints.txt

set NEED_INSTALL=0

python -c "import numpy; exit(0 if numpy.__version__ == '1.26.4' else 1)" 2>nul
if errorlevel 1 set NEED_INSTALL=1

python -c "import cv2" 2>nul
if errorlevel 1 set NEED_INSTALL=1

python -c "import paddle" 2>nul
if errorlevel 1 set NEED_INSTALL=1

python -c "import paddleocr" 2>nul
if errorlevel 1 set NEED_INSTALL=1

python -c "import pymupdf" 2>nul
if errorlevel 1 set NEED_INSTALL=1

if !NEED_INSTALL! equ 1 (
    echo برخی پکیج‌ها نصب نیستند یا نسخه اشتباه دارند. در حال نصب دقیق...
    pip install --upgrade pip setuptools wheel
    pip install --no-cache-dir --constraint constraints.txt numpy==1.26.4
    pip install --no-cache-dir --constraint constraints.txt opencv-python-headless==4.8.1.78
    pip install --no-cache-dir --no-deps --constraint constraints.txt paddlepaddle==2.6.2 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
    pip install --no-cache-dir --no-deps --constraint constraints.txt paddleocr==2.7.0.3
    pip install --no-cache-dir --constraint constraints.txt pymupdf
    pip install --no-cache-dir --constraint constraints.txt --ignore-installed attrdict cython fire lxml openpyxl pdf2docx premailer python-docx visualdl
    pip install --no-cache-dir --constraint constraints.txt Pillow pyclipper lmdb scikit-image shapely python-bidi arabic-reshaper rapidfuzz imageio matplotlib tqdm requests beautifulsoup4 google-genai decorator imgaug opt-einsum astor pyyaml simple-lama-inpainting
    
    echo نصب وابستگی‌ها تمام شد.
) else (
    echo همه پکیج‌های اصلی درست نصب هستند.
)
echo.
where python >nul 2>&1
if errorlevel 1 (
    echo خطا: Python پیدا نشد. لطفاً اول نصبش کنید.
    pause
    exit /b 1
)
echo ۳) کلید Gemini API
echo کلید رایگان‌تون رو از https://aistudio.google.com/api-keys بگیرید.
echo کلیدها رو یکی‌یکی وارد کنید (خالی بذارید تا تموم بشه):
echo.

set "API_KEYS="
set i=1

:key_loop
set /p "k=کلید !i! (Enter = پایان): "
if "!k!"=="" goto key_done
if defined API_KEYS (
    set "API_KEYS=!API_KEYS!,!k!"
) else (
    set "API_KEYS=!k!"
)
set /a i+=1
goto key_loop

:key_done
if not defined API_KEYS (
    echo خطا: حداقل یک کلید لازم است.
    pause
    exit /b 1
)
echo !i! کلید ثبت شد.
echo.

echo زبان اصلی متن منبع رو انتخاب کنید:
echo  1) en (انگلیسی - اکثر اسکنلیشن‌ها)
echo  2) ja en (ژاپنی خام)
echo  3) ko en (کره‌ای خام)
echo  4) دستی وارد کنید
set /p "lang_choice=انتخاب [پیش‌فرض 1]: "
if "!lang_choice!"=="" set lang_choice=1

if "!lang_choice!"=="1" set OCR_LANG=en
if "!lang_choice!"=="2" set OCR_LANG=ja en
if "!lang_choice!"=="3" set OCR_LANG=ko en
if "!lang_choice!"=="4" (
    set /p "OCR_LANG=زبان OCR را وارد کنید: "
)
if not defined OCR_LANG set OCR_LANG=en
echo زبان OCR: !OCR_LANG!
echo.

echo ترتیب خواندن:
echo  1) rtl (راست به چپ - مانگا/مانهوای شرقی)
echo  2) ltr (چپ به راست - کمیک غربی)
set /p "order_choice=انتخاب [پیش‌فرض 1]: "
if "!order_choice!"=="" set order_choice=1

if "!order_choice!"=="2" (
    set READING_ORDER=ltr
) else (
    set READING_ORDER=rtl
)
echo ترتیب خواندن: !READING_ORDER!
echo.

echo ۵) ورودی رو بدید:
echo  - لینک صفحه (http/https)
echo  - مسیر فایل ZIP / PDF / پوشه تصاویر
echo  - یا فقط Enter بزنید تا مسیر فعلی رو چک کنیم
set /p "INPUT_PATH=ورودی: "
if "!INPUT_PATH!"=="" set INPUT_PATH=./pages

if not exist "!INPUT_PATH!" (
    echo !INPUT_PATH! | findstr /r "^https\?://" >nul
    if errorlevel 1 (
        echo هشدار: مسیر '!INPUT_PATH!' پیدا نشد. ادامه می‌دیم...
    )
)
echo ورودی: !INPUT_PATH!
echo.

echo فرمت خروجی:
echo  1) pdf
echo  2) html
echo  3) zip
set /p "out_choice=انتخاب [پیش‌فرض 1]: "
if "!out_choice!"=="" set out_choice=1
if "!out_choice!"=="1" set OUTPUT=.pdf
if "!out_choice!"=="2" set OUTPUT=.html
if "!out_choice!"=="3" set OUTPUT=.zip
if not defined OUTPUT set OUTPUT=.pdf
echo خروجی: !OUTPUT!
echo.

set FONT_PATH=fonts\Vazirmatn-Bold.ttf
if not exist "!FONT_PATH!" (
    echo فونت پیدا نشد. در حال دانلود Vazirmatn Bold...
    if not exist fonts mkdir fonts
    curl -L -o "!FONT_PATH!" "https://github.com/rastikerdar/vazirmatn/raw/master/fonts/ttf/Vazirmatn-Bold.ttf"
    if errorlevel 1 (
        echo دانلود فونت شکست خورد. لطفاً دستی فونت را در fonts\ بگذارید.
        pause
        exit /b 1
    )
)
echo فونت: !FONT_PATH!
echo.

echo ========================================
echo شروع ترجمه...
echo ========================================
echo.

python manga_translator.py ^
  -i "!INPUT_PATH!" ^
  -o "!OUTPUT!" ^
  --font "!FONT_PATH!" ^
  --ocr-lang !OCR_LANG! ^
  --reading-order "!READING_ORDER!" ^
  --api-key "!API_KEYS!"

echo.
echo ========================================
echo تمام شد! خروجی: !OUTPUT!
echo ========================================
pause
