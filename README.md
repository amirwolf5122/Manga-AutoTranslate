# مانگا مترجم (Manga-AutoTranslate)

اپ اندروید بومی + موتور ترجمه مانگا/مانهوا — RT-DETR + Gemini + LaMa-Manga، اجرا روی CPU.

- `manga.py` — موتور ترجمه (CLI و وب)
- `manga_app.py` — رابط وب Gradio + منبع UI اپ اندروید
- `android/` — اپ اندروید بومی (Kotlin + Chaquopy) — [راهنمای نصب](android/INSTALL.md)

## اپ اندروید
APK از صفحه [Releases](https://github.com/amirwolf5121/Manga-AutoTranslate/releases) دانلود کن،
یا از تب Actions خودت بیلد بگیر. اپ هر بار اجرا `manga.py`/`manga_app.py` را از همین ریپو چک
می‌کند و با `APP_VER` بالاتر خودش آپدیت می‌شود.

## وب
```bash
python manga_app.py --web
```
