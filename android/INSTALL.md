# نصب دستی اپ اندروید مانگا مترجم

## روش ۱ — دانلود از Releases (پیشنهادی)

1. به صفحه [Releases](https://github.com/amirwolf5121/Manga-AutoTranslate/releases) برو
2. آخرین نسخه → فایل `manga-translator-*.apk` را دانلود کن
3. فایل را باز کن؛ اگر پیام «نصب از منابع ناشناس» آمد، اجازه بده
4. نصب تمام — بازش کن

> نسخه debug است؛ موقع نصب اندروید هشدار Play Protect می‌دهد → «نصب مجدد/به هر حال نصب» را بزن.

## روش ۲ — بیلد خودتان از سورس

نیازمندی‌ها: JDK 21، Python 3.10، Android SDK (platform 35)، Gradle 8.10.2

**مهم (از v1.24):** قبل از بیلد، یک‌بار اسکریپت دانلود بسته‌های پایتونی را اجرا کن —
این بسته‌ها دیگر داخل ریپو نیستند و باید موقع بیلد دانلود شوند:

```bash
python android/scripts/fetch_vendor.py          # دانلود ۱۹ بستهٔ pure-python
```

اگر این مرحله را نزنی، APK بیلد می‌شود ولی موقع ترجمه خطای import می‌گیرد.
برای چک اینکه همه حاضرند: `python android/scripts/fetch_vendor.py --check`

سپس بیلد:

```bash
cd android
echo "sdk.dir=/path/to/android-sdk" > local.properties
gradle :app:assembleDebug -PchaquopyBuildPython="$(command -v python3.10)"
# خروجی: app/build/outputs/apk/debug/app-debug.apk
```

یا از GitHub Actions استفاده کن: تب **Actions** → **Build Android APK** → **Run workflow**
— خروجی را در همان صفحه می‌گیری (artifact) و اگر Release بسازی، APK خودکار به آن چسبانده می‌شود.

### نصب دستی بسته‌ها (بدون اسکریپت)

اگر خواستی خودت دستی بریزی، معادل همان اسکریپت این دستور است (از ریشهٔ ریپو،
با Python 3.10 و ترجیحاً همین ترتیب و نسخه‌ها):

```bash
pip install --target android/app/src/main/python --no-deps --no-compile \
  openai==1.35.13 pydantic==1.10.17 rapidocr==3.9.2 huggingface_hub==0.36.0 \
  httpx==0.27.2 httpcore==1.0.9 h11==0.16.0 anyio==4.15.1 sniffio==1.3.1 \
  idna==3.20 certifi==2026.7.22 distro==1.9.0 filelock==4.0.1 fsspec==2026.9.0 \
  packaging==26.3 beautifulsoup4==4.15.0 soupsieve==2.9.2 \
  exceptiongroup==1.3.1 typing_extensions==4.16.0
```

> هشدار: `--no-deps` را حتماً نگه دار — وگرنه pip نسخه‌های جدیدتر/ناسازگار
> (مثل pydantic v2) را می‌کشد و ممکن است موتور خراب شود. بقیهٔ وابستگی‌های
> بومی (numpy/cv2/pillow/shapely/requests و…) نیازی به این دستور ندارند —
> خود گریدل از بلاک `pip` در `android/app/build.gradle.kts` نصب‌شان می‌کند.
>
> روی CI این کار خودکار انجام می‌شود (step «Fetch vendored Python packages»
> در `.github/workflows/build.yml`) — برای بیلد با Actions هیچ کاری لازم نیست.

## بسته‌های حذف‌شده از ریپو (v1.24)

این ۱۹ بسته (~۹۵۰ فایل) دیگر در گیت نیستند و موقع بیلد دانلود می‌شوند:
openai، pydantic، rapidocr، huggingface_hub، httpx، httpcore، h11، anyio،
sniffio، idna، certifi، distro، filelock، fsspec، packaging، beautifulsoup4،
soupsieve، exceptiongroup، typing_extensions.

فایل‌های خود پروژه (bridge.py، native_bridge.py، launcher.py، extract_ui.py،
app_server.py و شیم‌های onnxruntime/ و pyclipper/) همچنان داخل ریپو هستند.

## آپدیت خودکار اپ

اپ در هر اجرا `manga.py` و `manga_app.py` را از این ریپو (raw/main) چک می‌کند؛
اگر `APP_VER` داخل `manga_app.py` از نسخه نصب‌شده بالاتر باشد، خودش دانلود و جایگزین می‌کند —
بدون نصب دوباره. پس برای آپدیت موتور فقط این دو فایل را پوش کن و شماره `APP_VER` را ببر بالا.

## اگر اپ بالا نیامد (رفع مشکل دستی)

فایل‌های موتور در این مسیر هستند (بدون روت با فایل منیجر بعضی گوشی‌ها قابل دیدن نیست):
```
Android/data/com.amirwolf.mangatranslator/files/updates/
```
اگر `manga.py` یا `manga_app.py` آنجا **خالی (۰ بایت)** بودند، خودشان را حذف کن و اپ را
دوباره باز کن — از داخل APK (`assets/engine/`) سالم کپی می‌شوند. نیازی به کپی دستی نیست.

## فونت‌ها و مدل‌ها

- **فونت‌ها** (وزیرمتن، لاله‌زار و…) بار اول خودکار دانلود می‌شوند → `files/fonts/`
- **مدل‌های OCR** (~۳۱MB) بار اول موقع ترجمه دانلود می‌شوند → `files/rapidocr_models/`
- **پکیج‌های پایتون اضافی** (google-genai، openai و…) بار اول خودکار نصب می‌شوند

پس اولین اجرا کمی طول می‌کشد و به اینترنت نیاز دارد — نگران نشو، لودینگ دارد.
