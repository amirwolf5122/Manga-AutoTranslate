#!/bin/bash
# Manga Auto Translate FA - Interactive Runner (Linux / macOS)
set -e

echo "========================================"
echo " مترجم خودکار مانگا / مانهوا (فارسی)"
echo "========================================"
echo ""

echo "۰) بررسی و نصب وابستگی‌ها..."

if ! ldconfig -p 2>/dev/null | grep -q "libGL.so.1"; then
    echo "نصب کتابخانه‌های سیستمی مورد نیاز OpenCV..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update -qq
        sudo apt-get install -y -qq libgl1 libglib2.0-0 libsm6 libxext6 libxrender1
    elif command -v yum &> /dev/null; then
        sudo yum install -y mesa-libGL glib2
    fi
fi

cat > constraints.txt << EOF
numpy==1.26.4
opencv-python-headless==4.8.1.78
opencv-python==4.8.1.78
opencv-contrib-python==4.8.1.78
EOF

check_pkg() {
    python3 -c "import $1" 2>/dev/null
}

NEED_INSTALL=0

if ! check_pkg numpy || ! python3 -c "import numpy; exit(0 if numpy.__version__ == '1.26.4' else 1)" 2>/dev/null; then
    NEED_INSTALL=1
fi
if ! check_pkg cv2; then
    NEED_INSTALL=1
fi
if ! check_pkg paddle; then
    NEED_INSTALL=1
fi
if ! check_pkg paddleocr; then
    NEED_INSTALL=1
fi
if ! python3 -c "import pymupdf" 2>/dev/null; then
    NEED_INSTALL=1
fi

if [ $NEED_INSTALL -eq 1 ]; then
    echo "برخی پکیج‌ها نصب نیستند یا نسخه اشتباه دارند. در حال نصب دقیق..."
    
    pip install --upgrade pip setuptools wheel
    
    pip install --no-cache-dir --constraint constraints.txt numpy==1.26.4
    pip install --no-cache-dir --constraint constraints.txt opencv-python-headless==4.8.1.78
    pip install --no-cache-dir --no-deps --constraint constraints.txt paddlepaddle==2.6.2 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
    pip install --no-cache-dir --no-deps --constraint constraints.txt paddleocr==2.7.0.3
    pip install --no-cache-dir --constraint constraints.txt pymupdf
    pip install --no-cache-dir --constraint constraints.txt --ignore-installed attrdict cython fire lxml openpyxl pdf2docx premailer python-docx visualdl
    pip install --no-cache-dir --constraint constraints.txt Pillow pyclipper lmdb scikit-image shapely python-bidi arabic-reshaper rapidfuzz imageio matplotlib tqdm requests beautifulsoup4 decorator imgaug opt-einsum astor pyyaml simple-lama-inpainting
    pip install --no-cache-dir --constraint constraints.txt torch torchvision --index-url https://download.pytorch.org/whl/cpu
    pip install --no-cache-dir --constraint constraints.txt "transformers==4.49.0" huggingface_hub sentencepiece

    echo "نصب وابستگی‌ها تمام شد."
else
    echo "همه پکیج‌های اصلی درست نصب هستند."
fi
echo ""

if ! command -v python3 &> /dev/null; then
    echo "خطا: Python3 پیدا نشد. لطفاً اول نصبش کنید."
    exit 1
fi

echo "۱) ارائه‌دهنده AI را انتخاب کنید:"
echo "  1) gemini      (Google Gemini - رایگان با سهمیه)"
echo "  2) openai      (ChatGPT / GPT)"
echo "  3) deepseek    (DeepSeek)"
echo "  4) groq        (Groq - سریع و رایگان)"
echo "  5) xai         (xAI / Grok)"
echo "  6) openrouter  (OpenRouter - دسترسی به چند مدل)"
echo "  7) ollama      (لوکال - بدون کلید)"
echo "  8) together    (Together AI)"
read -p "انتخاب [پیش‌فرض 1]: " prov_choice
prov_choice=${prov_choice:-1}
case $prov_choice in
    1) PROVIDER="gemini" ;;
    2) PROVIDER="openai" ;;
    3) PROVIDER="deepseek" ;;
    4) PROVIDER="groq" ;;
    5) PROVIDER="xai" ;;
    6) PROVIDER="openrouter" ;;
    7) PROVIDER="ollama" ;;
    8) PROVIDER="together" ;;
    *) PROVIDER="gemini" ;;
esac
echo "ارائه‌دهنده: $PROVIDER"
echo ""

# نصب پکیج مربوط به provider
case $PROVIDER in
    gemini)
        if ! python3 -c "import google.genai" 2>/dev/null; then
            echo "نصب google-genai..."
            pip install --no-cache-dir google-genai
        fi
        ;;
    ollama)
        if ! python3 -c "import openai" 2>/dev/null; then
            echo "نصب openai (برای Ollama)..."
            pip install --no-cache-dir openai
        fi
        ;;
    *)
        if ! python3 -c "import openai" 2>/dev/null; then
            echo "نصب openai..."
            pip install --no-cache-dir openai
        fi
        ;;
esac

API_KEYS=""
MODEL_ARG=""
if [ "$PROVIDER" != "ollama" ]; then
    echo "۲) کلید API برای $PROVIDER"
    case $PROVIDER in
        gemini)     echo "کلید رایگان: https://aistudio.google.com/api-keys" ;;
        openai)     echo "کلید: https://platform.openai.com/api-keys" ;;
        deepseek)   echo "کلید: https://platform.deepseek.com/api_keys" ;;
        groq)       echo "کلید: https://console.groq.com/keys" ;;
        xai)        echo "کلید: https://console.x.ai/" ;;
        openrouter) echo "کلید: https://openrouter.ai/keys" ;;
        together)   echo "کلید: https://api.together.xyz/settings/api-keys" ;;
    esac
    echo "کلیدها رو یکی‌یکی وارد کنید (خالی بذارید تا تموم بشه):"
    echo ""
    keys=()
    i=1
    while true; do
        read -s -p "کلید $i (Enter = پایان): " k
        echo ""
        if [ -z "$k" ]; then
            break
        fi
        keys+=("$k")
        ((i++))
    done
    if [ ${#keys[@]} -eq 0 ]; then
        echo "خطا: حداقل یک کلید لازم است."
        exit 1
    fi
    API_KEYS=$(IFS=,; echo "${keys[*]}")
    echo "${#keys[@]} کلید ثبت شد."
else
    echo "۲) Ollama نیاز به کلید ندارد (لوکال)."
fi
echo ""

echo "۳) مدل (Enter = پیش‌فرض provider):"
case $PROVIDER in
    gemini)     echo "  مثال: gemini-flash-latest | gemini-2.5-flash | gemini-2.5-flash-lite" ;;
    openai)     echo "  مثال: gpt-4o-mini | gpt-4o | gpt-4.1-mini" ;;
    deepseek)   echo "  مثال: deepseek-chat | deepseek-reasoner" ;;
    groq)       echo "  مثال: llama-3.3-70b-versatile | llama-3.1-8b-instant" ;;
    xai)        echo "  مثال: grok-2-latest | grok-3" ;;
    openrouter) echo "  مثال: google/gemini-2.0-flash-001 | anthropic/claude-3.5-sonnet" ;;
    ollama)     echo "  مثال: llama3.2 | qwen2.5 | mistral" ;;
    together)   echo "  مثال: meta-llama/Llama-3.3-70B-Instruct-Turbo" ;;
esac
read -p "مدل: " MODEL_NAME
if [ -n "$MODEL_NAME" ]; then
    MODEL_ARG="--model $MODEL_NAME"
fi
echo ""

echo "۴) زبان اصلی متن منبع رو انتخاب کنید:"
echo " 1) en (انگلیسی - اکثر اسکنلیشن‌ها)"
echo " 2) ja en (ژاپنی خام)"
echo " 3) ko en (کره‌ای خام)"
echo " 4) دستی وارد کنید"
read -p "انتخاب [پیش‌فرض 1]: " lang_choice
lang_choice=${lang_choice:-1}
case $lang_choice in
    1) OCR_LANG="en" ;;
    2) OCR_LANG="ja en" ;;
    3) OCR_LANG="ko en" ;;
    4) read -p "زبان OCR را وارد کنید: " OCR_LANG ;;
    *) OCR_LANG="en" ;;
esac
echo "زبان OCR: $OCR_LANG"
echo ""

echo "ترتیب خواندن:"
echo " 1) rtl (راست به چپ - مانگا/مانهوای شرقی)"
echo " 2) ltr (چپ به راست - کمیک غربی)"
read -p "انتخاب [پیش‌فرض 1]: " order_choice
order_choice=${order_choice:-1}
if [ "$order_choice" = "2" ]; then
    READING_ORDER="ltr"
else
    READING_ORDER="rtl"
fi
echo "ترتیب خواندن: $READING_ORDER"
echo ""

echo "۵) ورودی رو بدید:"
echo " - لینک صفحه (http/https)"
echo " - مسیر فایل ZIP / PDF / پوشه تصاویر"
echo " - یا فقط Enter بزنید تا مسیر فعلی رو چک کنیم"
read -p "ورودی: " INPUT_PATH
INPUT_PATH=${INPUT_PATH:-"./pages"}
if [ ! -e "$INPUT_PATH" ] && [[ ! "$INPUT_PATH" =~ ^https?:// ]]; then
    echo "هشدار: مسیر '$INPUT_PATH' پیدا نشد. ادامه می‌دیم..."
fi
echo "ورودی: $INPUT_PATH"
echo ""

echo "فرمت خروجی:"
echo " 1) pdf"
echo " 2) html"
echo " 3) zip"
read -p "انتخاب [پیش‌فرض 1]: " out_choice
out_choice=${out_choice:-1}
case $out_choice in
    1) OUTPUT=".pdf" ;;
    2) OUTPUT=".html" ;;
    3) OUTPUT=".zip" ;;
    *) OUTPUT=".pdf" ;;
esac
echo "خروجی: $OUTPUT"
echo ""

FONT_PATH="fonts/Vazirmatn-Bold.ttf"
if [ ! -f "$FONT_PATH" ]; then
    echo "فونت پیدا نشد. در حال دانلود Vazirmatn Bold..."
    mkdir -p fonts
    curl -L -o "$FONT_PATH" \
      "https://github.com/rastikerdar/vazirmatn/raw/master/fonts/ttf/Vazirmatn-Bold.ttf" || {
        echo "دانلود فونت شکست خورد. لطفاً دستی فونت را در fonts/ بگذارید."
        exit 1
    }
fi
echo "فونت: $FONT_PATH"
echo ""

echo "========================================"
echo "شروع ترجمه با $PROVIDER ..."
echo "========================================"
echo ""

CMD=(python3 manga_translator.py
  -i "$INPUT_PATH"
  -o "$OUTPUT"
  --font "$FONT_PATH"
  --ocr-lang $OCR_LANG
  --reading-order "$READING_ORDER"
  --provider "$PROVIDER"
)

if [ -n "$API_KEYS" ]; then
    CMD+=(--api-key "$API_KEYS")
fi
if [ -n "$MODEL_NAME" ]; then
    CMD+=(--model "$MODEL_NAME")
fi

"${CMD[@]}"

echo ""
echo "========================================"
echo "تمام شد! خروجی: $OUTPUT"
echo "========================================"
