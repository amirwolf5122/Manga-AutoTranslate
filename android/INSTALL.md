# نصب دستی اپ اندروید مانگا مترجم

## روش ۱ — دانلود از Releases (پیشنهادی)

1. به صفحه [Releases](https://github.com/amirwolf5121/Manga-AutoTranslate/releases) برو
2. آخرین نسخه → فایل `manga-translator-*.apk` را دانلود کن
3. فایل را باز کن؛ اگر پیام «نصب از منابع ناشناس» آمد، اجازه بده
4. نصب تمام — بازش کن

> نسخه debug است؛ موقع نصب اندروید هشدار Play Protect می‌دهد → «نصب مجدد/به هر حال نصب» را بزن.

## روش ۲ — بیلد خودتان از سورس

نیازمندی‌ها: JDK 21، Python 3.10، Android SDK (platform 35)، Gradle 8.10.2

```bash
cd android
echo "sdk.dir=/path/to/android-sdk" > local.properties
gradle :app:assembleDebug -PchaquopyBuildPython="$(command -v python3.10)"
# خروجی: app/build/outputs/apk/debug/app-debug.apk
```

یا از GitHub Actions استفاده کن: تب **Actions** → **Build Android APK** → **Run workflow**
— خروجی را در همان صفحه می‌گیری (artifact) و اگر Release بسازی، APK خودکار به آن چسبانده می‌شود.

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
