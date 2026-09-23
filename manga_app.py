name: Manga CLI (ترجمه یک‌باره)

on:
  workflow_dispatch:
    inputs:
      input_url:
        description: "لینک ورودی (صفحه مانگا / ZIP / PDF / تصویر)"
        required: true
        type: string
      provider:
        description: "ارائه‌دهنده AI"
        required: false
        default: "gemini"
        type: choice
        options:
          - gemini
          - openai
          - deepseek
          - groq
          - xai
          - openrouter
          - together
      model:
        description: "نام مدل (خالی = پیش‌فرض provider)"
        required: false
        default: ""
        type: string
      ocr_lang:
        description: "زبان OCR (مثلاً en یا ko en یا ja en)"
        required: false
        default: "en"
        type: string
      reading_order:
        description: "ترتیب خواندن"
        required: false
        default: "rtl"
        type: choice
        options:
          - rtl
          - ltr
      output_format:
        description: "فرمت خروجی"
        required: false
        default: "pdf"
        type: choice
        options:
          - pdf
          - html
          - zip

jobs:
  translate:
    runs-on: ubuntu-latest
    timeout-minutes: 360
    steps:
      - name: Checkout
        uses: actions/checkout@v5

      - name: Set up Python
        uses: actions/setup-python@v6
        with:
          python-version: "3.12"

      - name: Install system dependencies
        run: |
          sudo apt-get install -y libgl1 libglib2.0-0 libsm6 libxext6 libxrender-dev

      - name: Download fonts
        run: |
          set -e
          mkdir -p fonts
          curl -fL "https://raw.githubusercontent.com/rastikerdar/vazirmatn/master/fonts/ttf/Vazirmatn-Bold.ttf" -o fonts/Vazirmatn-Bold.ttf
          curl -fL "https://raw.githubusercontent.com/rastikerdar/vazirmatn/master/fonts/ttf/Vazirmatn-Regular.ttf" -o fonts/Vazirmatn-Regular.ttf
          curl -fL "https://raw.githubusercontent.com/rastikerdar/shabnam-font/master/dist/Shabnam-Bold.ttf" -o fonts/Lalezar-Regular.ttf
          curl -fL "https://raw.githubusercontent.com/rastikerdar/gandom-font/master/dist/Gandom.ttf" -o fonts/Gandom.ttf
          curl -fL "https://raw.githubusercontent.com/rastikerdar/nahid-font/master/dist/Nahid.ttf" -o fonts/Nahid.ttf
          curl -fL "https://raw.githubusercontent.com/rastikerdar/sahel-font/master/dist/Sahel.ttf" -o fonts/Sahel.ttf
          curl -fL "https://raw.githubusercontent.com/rastikerdar/samim-font/master/dist/Samim-Bold.ttf" -o fonts/Samim-Bold.ttf
          curl -fL "https://raw.githubusercontent.com/google/fonts/main/ofl/amiri/Amiri-Regular.ttf" -o fonts/Amiri-Regular.ttf
          curl -fL "https://raw.githubusercontent.com/rastikerdar/shabnam-font/master/dist/Shabnam-Bold.ttf" -o fonts/Shabnam-Bold.ttf
          ls -la fonts/

      - name: Resolve API key
        env:
          GEMINI: ${{ secrets.GEMINI }}
          OPENAI: ${{ secrets.OPENAI }}
          DEEPSEEK: ${{ secrets.DEEPSEEK }}
          GROQ: ${{ secrets.GROQ }}
          XAI: ${{ secrets.XAI }}
          OPENROUTER: ${{ secrets.OPENROUTER }}
          TOGETHER: ${{ secrets.TOGETHER }}
          API: ${{ secrets.API }}
        run: |
          PROVIDER="${{ inputs.provider }}"
          KEY=""
          case "$PROVIDER" in
            gemini)     KEY="${GEMINI:-$API}" ;;
            openai)     KEY="${OPENAI:-$API}" ;;
            deepseek)   KEY="${DEEPSEEK:-$API}" ;;
            groq)       KEY="${GROQ:-$API}" ;;
            xai)        KEY="${XAI:-$API}" ;;
            openrouter) KEY="${OPENROUTER:-$API}" ;;
            together)   KEY="${TOGETHER:-$API}" ;;
            *)          KEY="${API}" ;;
          esac
          if [ -z "$KEY" ]; then
            echo "خطا: Secret برای provider «$PROVIDER» تنظیم نشده."
            exit 1
          fi
          echo "RESOLVED_KEY=$KEY" >> $GITHUB_ENV
          echo "PROVIDER=$PROVIDER" >> $GITHUB_ENV

      - name: Run translator
        run: |
          OUT_EXT=".${{ inputs.output_format }}"
          echo "OUT_EXT=$OUT_EXT" >> $GITHUB_ENV
          MODEL_ARG=""
          if [ -n "${{ inputs.model }}" ]; then
            MODEL_ARG="--model ${{ inputs.model }}"
          fi
          python manga.py \
            -i "${{ inputs.input_url }}" \
            -o "$OUT_EXT" \
            --font "fonts/Vazirmatn-Bold.ttf" \
            --font-normal "fonts/Vazirmatn-Bold.ttf" \
            --font-shout "fonts/Lalezar-Regular.ttf" \
            --font-comedy-shout "fonts/Gandom.ttf" \
            --font-whisper "fonts/Nahid.ttf" \
            --font-sun-thought "fonts/Samim-Bold.ttf" \
            --font-thought "fonts/Samim-Bold.ttf" \
            --font-free "fonts/Vazirmatn-Regular.ttf" \
            --font-system "fonts/Sahel.ttf" \
            --font-monster "fonts/Gandom.ttf" \
            --font-cry "fonts/Nahid.ttf" \
            --font-fear "fonts/Nahid.ttf" \
            --font-broadcast "fonts/Sahel.ttf" \
            --font-letter "fonts/Amiri-Regular.ttf" \
            --font-narrator "fonts/Shabnam-Bold.ttf" \
            --font-square-thought "fonts/Sahel.ttf" \
            --font-black "fonts/Vazirmatn-Bold.ttf" \
            --font-explosion "fonts/Lalezar-Regular.ttf" \
            --font-sfx "fonts/Gandom.ttf" \
            --ocr-lang ${{ inputs.ocr_lang }} \
            --reading-order ${{ inputs.reading_order }} \
            --provider "$PROVIDER" \
            --api-key "$RESOLVED_KEY" \
            $MODEL_ARG \
            --cpu
          RESULT=$(ls -1t *"$OUT_EXT" 2>/dev/null | head -n 1 || true)
          if [ -z "$RESULT" ]; then
            echo "هیچ فایل خروجی با پسوند $OUT_EXT پیدا نشد."
            ls -la
            exit 1
          fi
          STEM=$(basename "$RESULT" "$OUT_EXT")
          echo "RESULT_FILE=$RESULT" >> $GITHUB_ENV
          echo "RESULT_STEM=$STEM" >> $GITHUB_ENV
          echo "خروجی نهایی: $RESULT"

      - name: Upload results
        uses: actions/upload-artifact@v5
        with:
          name: ${{ env.RESULT_STEM }}
          path: |
            *.pdf
            *.html
            *.zip
          retention-days: 7
          if-no-files-found: error
