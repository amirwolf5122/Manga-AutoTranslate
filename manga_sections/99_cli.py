# BUILD-STRIP-START
# BUILD-STRIP-END
def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="مترجم خودکار مانگا/مانهوا به فارسی — پشتیبانی از Gemini / OpenAI / DeepSeek / Groq / xAI / Ollama و ..."
    )
    p.add_argument("-i", "--input", required=True)
    p.add_argument("-o", "--output", required=True,
                   help="مسیر خروجی: فایل کامل یا فقط پسوند (.pdf / .zip / .html / .psd) — خروجیِ پوشه‌ای حذف شد")
    p.add_argument(
        "--provider",
        default="gemini",
        choices=list(PROVIDER_PRESETS.keys()),
        help="ارائه‌دهنده AI: gemini | openai | deepseek | groq | xai | together | openrouter | ollama "
             "(نام‌های قدیمی chatgpt و grok هم پذیرفته می‌شوند: همان openai و xai)"
    )
    p.add_argument("--api-key", action="append", default=None,
                   help="کلید API. چندبار یا با کاما. env متناظر هم خوانده می‌شود")
    p.add_argument("--api-base", default=None,
                   help="آدرس پایه API (اختیاری)")
    p.add_argument("--font", required=True,
                   help="فونت پیش‌فرض فارسی / بالن عادی (کودک) و fallback")
    p.add_argument("--font-normal", default=None, help="بالن عادی گرد — کودک")
    p.add_argument("--font-shout", default=None, help="داد خشم دندانه — افسانه")
    p.add_argument("--font-comedy-shout", default=None, help="داد کمدی — کروش")
    p.add_argument("--font-whisper", default=None, help="زمزمه موج‌دار — دست‌نویس")
    p.add_argument("--font-sun-thought", default=None, help="تفکر خورشیدی — مهر")
    p.add_argument("--font-thought", default=None, help="تفکر ابری — مروارید")
    p.add_argument("--font-free", default=None, help="متن بیرون بالن — ارامکو/هوما/تهران")
    p.add_argument("--font-free-text", default=None,
                   help="نام مستعار --font-free (سازگاری با اپ قدیمی)")
    p.add_argument("--font-system", default=None, help="UI سیستم — اصفهان/فرناز")
    p.add_argument("--font-monster", default=None, help="صدای هیولا — کردی")
    p.add_argument("--font-cry", default=None, help="گریه — موج/هاله")
    p.add_argument("--font-fear", default=None, help="ترس — صحرا")
    p.add_argument("--font-broadcast", default=None, help="بی‌سیم/تلویزیون/موبایل — اکبر/اسمان/مثلث")
    p.add_argument("--font-letter", default=None, help="نامه/طومار — آندالوس/فورات")
    p.add_argument("--font-narrator", default=None, help="راوی مستطیل — الهام")
    p.add_argument("--font-square-thought", default=None, help="فکر مربعی — یکان")
    p.add_argument("--font-black", default=None, help="دارک تیره — اتابای/فرزیانی/زنگار")

    p.add_argument("--font-explosion", default=None, help="[قدیمی] → shout")
    p.add_argument("--font-sfx", default=None, help="[قدیمی] → comedy_shout")
    p.add_argument("--ocr-lang", nargs="+", default=["en"],
                   help="زبان‌های OCR. en | ko en | ja en")
    p.add_argument("--model", default=None,
                   help="نام مدل. اگر ندهی از پیش‌فرض provider استفاده می‌شود")
    p.add_argument("--reading-order", choices=["rtl", "ltr"], default="rtl")
    p.add_argument("--gpu", dest="gpu", action="store_true", default=None,
                   help="اجبار به GPU برای OCR و LaMa ONNX")
    p.add_argument("--cpu", dest="gpu", action="store_false",
                   help="اجبار به CPU (OpenCV inpaint)")
    p.add_argument("--lama", action="store_true", default=False,
                   help="حتی روی CPU هم پاک‌سازی big-lama.pt را فعال کن (کندتر، تمیزتر)")
    p.add_argument("--clean-method", dest="clean_method",
                   choices=["lama-manga", "lama-big", "opencv"], default=None,
                   help="روش پاکسازی: lama-manga (پیش‌فرض) | lama-big | opencv")
    p.add_argument("--no-resume", action="store_true")
    p.add_argument("--keep-old", action="store_true")
    p.add_argument("--request-delay", type=float, default=0.0)
    p.add_argument("--bubbles-per-request", type=int, default=15,
                   help="چند حباب در هر درخواست ترجمه (پیش‌فرض ۱۵ — تا این تعداد "
                        "متن جمع نشود درخواست API زده نمی‌شود)")
    p.add_argument("--min-translate-batch", type=int, default=15,
                   help="حداقل تعداد دیالوگ قبل از ارسال ترجمه (پیش‌فرض ۱۵؛ "
                        "دیالوگ‌های چند صفحه با هم بافر می‌شوند)")
    p.add_argument("--batch-workers", type=int, default=3,
                   help="تعداد بستهٔ ترجمهٔ موازی (پیش‌فرض ۳ — هر بسته کلید جدا می‌گیرد)")
    p.add_argument("--api-timeout", type=float, default=30.0,
                   help="سقف انتظار پاسخ AI به ثانیه (پیش‌فرض ۳۰). بعد از تایم‌اوت کلید/مدل بعدی")
    p.add_argument("--max-retries", type=int, default=8,
                   help="حداکثر تلاش ترجمه؛ برای پیمایش cascade همه مدل‌ها (پیش‌فرض ۱۲)")
    p.add_argument("--det-confidence", type=float, default=0.16,
                   help="آستانه اطمینان تشخیص حباب RT-DETR (پیش‌فرض 0.16 — "
                        "تگ‌های چرخیده/نیمه‌شفاف نمرهٔ پایین می‌گیرند؛ OCR جعبه‌های "
                        "اضافی را خودش فیلتر می‌کند)")
    p.add_argument("--max-chunk-height", type=int, default=3500,
                   help="حداکثر ارتفاع هر تکه OCR داخل یک تصویر (پیکسل)")
    p.add_argument("--stitch-max-height", type=int, default=None,
                   help="پیش‌فرضِ خودکار: ۸۰۰۰ برای ورودیِ فصل/آرشیو/zip؛ ورودیِ چند-لینکِ مستقیم اصلاً برش نمی‌خورد "
                        "(هر صفحه مثل حالتِ تکی). ۰ = بدون برش مجدد ارتفاع (ترمیم مرز متن همچنان فعال است). "
                        "عدد دیگر = هدف تقریبی ارتفاع نوار؛ برای حفظ متن و حباب ممکن است خروجی بلندتر شود")
    p.add_argument("--no-seam-repair", action="store_true",
                   help="با ارتفاع برش ۰، ترمیم خودکار متن مشترک بین دو تصویر را هم خاموش کن (ممکن است متن نصف شود)")
    p.add_argument("--stitch-short-threshold", type=int, default=0,
                   help="تنظیم قدیمی: اگر از --stitch-max-height بزرگ‌تر باشد، "
                        "هدف ارتفاع را افزایش می‌دهد؛ معمولاً ۰ بگذارید")
    p.add_argument("--no-stitch-keep-first", action="store_true",
                   help="صفحهٔ اول را هم داخل نوارها بگذار (پیش‌فرض: فقط اگر مرز آن امن باشد جدا می‌ماند)")
    p.add_argument("--img-format", choices=["webp", "png", "jpg"], default="jpg",
                   help="فرمت صفحات خروجی (پیش‌فرض jpg — حجم کمتر، کیفیت مشابه)")
    p.add_argument("--quality", type=int, default=90,
                   help="کیفیت JPEG/WebP (پیش‌فرض ۹۰). با encode بهینه حجم کمتر می‌شود بدون افت محسوس")
    p.add_argument("--max-width", type=int, default=0,
                   help="سقف سخت عرض خروجی (۰=خاموش). عرض‌های نزدیک خودکار یکی می‌شوند "
                        "(مثلاً 700/800/900→800، 1700/1800/1900→1800)")
    p.add_argument("--min-confidence", type=float, default=0.12)
    p.add_argument("--workers", type=int, default=3,
                   help="تعداد worker موازی OCR/ترجمه (پیش‌فرض ۳)")
    p.add_argument("--mask-padding", type=int, default=3)
    p.add_argument("--pad-ratio", type=float, default=0.06)
    p.add_argument("--inpaint-radius", type=int, default=3)
    p.add_argument("--mag-ratio", type=float, default=1.35)
    p.add_argument("--no-two-pass-ocr", action="store_true")
    p.add_argument("--fake-translate", action="store_true",
                   help="حالت تست: به‌جای API، متن فارسی الکی داخل حباب‌ها رندر می‌شود "
                        "(برای چک کردن استخراج/پاکسازی/رندر بدون کلید API)")
    p.add_argument("--clean-only", action="store_true",
                   help="فقط پاکسازی متن (inpaint) بدون ترجمه و بدون رندر فارسی — "
                        "برای تست تشخیص حباب/پاکسازی؛ کلید API لازم نیست")
    p.add_argument("--translate-retranslate", action="store_true",
                   help="با عوض‌شدنِ مدل/پرامپت: ترجمه‌ها از نو ساخته شوند "
                        "(پیش‌فرض: ادامه — حباب‌های ترجمه‌شده از کش می‌مانند؛ "
                        "استخراج/پاکسازی در هر دو حالت از کش می‌مانند)")
    p.add_argument("--no-brief", action="store_true",
                   help=argparse.SUPPRESS)
    p.add_argument("--clean-sfx", action="store_true",
                   help="پاکسازی افکت‌های صوتی و متنِ استایل‌دارِ بیرونِ حباب "
                        "(HAA، SFX کره‌ای، پلاک اسم…) — پیش‌فرض خاموش (SFX هنر "
                        "حساب می‌شود)؛ env متناظر: MANGA_CLEAN_SFX=1")
    p.add_argument("--no-style-fonts", action="store_true",
                   help="فونت جداگانهٔ هر لحن حباب خاموش شود → همه با فونت اصلی رندر می‌شوند")
    p.add_argument("--active-tones", default=None,
                   help="فقط این لحن‌ها فعال بمانند (با کاما): مثلاً normal,whisper,shout "
                        "— بقیهٔ لحن‌ها از دستور ترجمه حذف و به normal برمی‌گردند")
    p.add_argument("--instruction", default=None,
                   help="فایل متنی دستور مترجم (System Instruction) — محتوای این فایل جایگزین "
                        "کامل متن دستور داخل کد می‌شود")
    p.add_argument("--prompt-mode", default=None,
                   choices=["professional", "lite", "auto"],
                   help="سبک پرامپت وقتی --instruction داده نشده: professional "
                        "(پیشفرض — حرفهای انگلیسی؛ مدلهای Lite خودکار سبکِ "
                        "lite میگیرند)، lite (سبک انگلیسی). مقدارِ کهنهٔ auto "
                        "= همان رفتارِ خودکارِ professional/lite")
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--top-p", type=float, default=0.9)
    p.add_argument(
        "--debug",
        action="store_true",
        help="حالت دیباگ: مربع رنگی دور هر بلوک؛ خروجی دیباگ هم فرمت اصلی را می‌گیرد (مثلاً PDF → *_debug.pdf)",
    )
    return p

def main():
    try:
        print(f"[TIME] imports={_time_t0.time() - _T0_IMPORT:.1f}s",
              flush=True)
    except Exception:
        pass
    args = build_arg_parser().parse_args()

    if str(os.environ.get("MANGA_SPEED_TEST", "") or "").strip() == "1":
        try:
            speed_lab_env({})
        except Exception:
            pass
        speed_test_run(src=args.input,
                       langs=tuple(args.ocr_lang or ["en"]),
                       per_mode=60.0)
        return

    provider = (args.provider or "gemini").lower().strip()
    if provider not in PROVIDER_PRESETS:
        print(f"خطا: provider ناشناخته «{provider}»", file=sys.stderr)
        sys.exit(1)

    keys: List[str] = []
    if args.api_key:
        for item in args.api_key:
            keys.extend(k.strip() for k in item.replace(";", ",").split(",") if k.strip())

    env_name = PROVIDER_PRESETS[provider].get("env_key", "")
    if env_name:
        env_val = os.environ.get(env_name, "")
        if env_val:
            keys.extend(k.strip() for k in env_val.replace(";", ",").split(",") if k.strip())

    for fallback_env in ("GEMINI_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY", "API_KEY"):
        if fallback_env != env_name:
            v = os.environ.get(fallback_env, "")
            if v:
                keys.extend(k.strip() for k in v.replace(";", ",").split(",") if k.strip())

    if provider == "custom":
        if not getattr(args, "api_base", None):
            args.api_base = os.environ.get("CUSTOM_BASE_URL", "").strip() or None
        if not getattr(args, "model", None):
            args.model = os.environ.get("CUSTOM_MODEL", "").strip() or None

        if (not args.api_base or not args.model) and sys.stdin.isatty() \
                and not getattr(args, "fake_translate", False) \
                and not getattr(args, "clean_only", False):
            args.api_base, args.model = _prompt_custom_endpoint(
                args.api_base or "", args.model or "")

        _ab = normalize_api_base(args.api_base or "")
        if not _ab:
            print("خطا: برای provider «custom» دامنهٔ API معتبر لازم است.",
                  file=sys.stderr)
            print("  نمونهٔ درست:  --api-base https://api.example.com/v1",
                  file=sys.stderr)
            print("  (https:// اگر جا افتاده باشد خودکار اضافه می‌شود؛ "
                  "یا env CUSTOM_BASE_URL را تنظیم کن.)",
                  file=sys.stderr)
            sys.exit(1)
        args.api_base = _ab
        if not args.model:
            print("خطا: برای provider «custom» نام مدل لازم است — "
                  "--model را بده (مثال: --model gpt-4o-mini) "
                  "یا env CUSTOM_MODEL را تنظیم کن.",
                  file=sys.stderr)
            sys.exit(1)
        print(f"[*] ارائه‌دهندهٔ سفارشی: base={args.api_base} | model={args.model}")

    seen = set()
    unique_keys = []
    for k in keys:
        if k not in seen:
            seen.add(k)
            unique_keys.append(k)

    if not unique_keys and provider not in ("ollama", "custom") \
            and not getattr(args, "fake_translate", False) \
            and not getattr(args, "clean_only", False):
        print(
            f"خطا: حداقل یک کلید API لازم است (--api-key یا env: {env_name}).",
            file=sys.stderr,
        )
        sys.exit(1)

    output_path = MangaTranslator._auto_output_path(args.input, args.output)
    if output_path != args.output:
        print(f"[*] نام خروجی خودکار: {output_path}")

    translator = MangaTranslator(
        api_key=unique_keys or ["ollama"],
        provider=provider,
        ocr_langs=args.ocr_lang,
        model_name=args.model,
        api_base=args.api_base,
        font_path=args.font,
        reading_order=args.reading_order,
        gpu=args.gpu,
        force_lama=bool(getattr(args, "lama", False)),
        clean_method=(getattr(args, "clean_method", None)
                      or ("lama-big" if getattr(args, "lama", False)
                          else ("opencv" if args.gpu is False else "lama-manga"))),
        max_retries=args.max_retries,
        det_confidence=getattr(args, "det_confidence", 0.28),
        request_delay=args.request_delay,
        bubbles_per_request=max(1, int(getattr(args, "bubbles_per_request", 15) or 15)),
        api_timeout=getattr(args, "api_timeout", 10.0),
        max_chunk_height=args.max_chunk_height,
        img_format=args.img_format,
        img_quality=args.quality,
        min_confidence=args.min_confidence,
        max_workers=args.workers,
        mask_padding=args.mask_padding,
        pad_ratio=args.pad_ratio,
        inpaint_radius=args.inpaint_radius,
        mag_ratio=args.mag_ratio,
        two_pass_ocr=not args.no_two_pass_ocr,
        translation_temperature=args.temperature,
        translation_top_p=getattr(args, "top_p", 0.9),
        max_output_width=(args.max_width or None),
        stitch_max_height=(8000 if getattr(args, "stitch_max_height", None) is None
                           else int(args.stitch_max_height)),
        stitch_short_threshold=args.stitch_short_threshold,
        stitch_keep_first=not args.no_stitch_keep_first,
        stitch_explicit=(getattr(args, "stitch_max_height", None) is not None),
        repair_page_seams=not bool(getattr(args, "no_seam_repair", False)),
        debug=bool(getattr(args, "debug", False)),
        fake_translate=bool(getattr(args, "fake_translate", False)),
        clean_only=bool(getattr(args, "clean_only", False)),
        translate_retranslate=bool(getattr(args, "translate_retranslate", False)),
        clean_sfx=bool(getattr(args, "clean_sfx", False)),
        style_fonts=not getattr(args, "no_style_fonts", False),
        instruction_text=(
            open(args.instruction, encoding="utf-8").read()
            if getattr(args, "instruction", None) and os.path.isfile(args.instruction) else None
        ),
        prompt_mode=getattr(args, "prompt_mode", None),
    )
    if getattr(args, "lama", False):
        translator.use_lama = True
        print("[*] --lama → پاک‌سازی باکیفیت LaMa ONNX فعال (کندتر از OpenCV).")
    translator.batch_workers = max(1, int(getattr(args, "batch_workers", 3) or 3))
    translator.min_translate_batch = max(1, int(getattr(args, "min_translate_batch", 15) or 15))

    if not getattr(args, "font_free", None) and getattr(args, "font_free_text", None):
        args.font_free = args.font_free_text

    _font_map = (
        ("normal", "font_normal"),
        ("shout", "font_shout"),
        ("comedy_shout", "font_comedy_shout"),
        ("whisper", "font_whisper"),
        ("sun_thought", "font_sun_thought"),
        ("thought", "font_thought"),
        ("free_text", "font_free"),
        ("system", "font_system"),
        ("monster", "font_monster"),
        ("cry", "font_cry"),
        ("fear", "font_fear"),
        ("broadcast", "font_broadcast"),
        ("letter", "font_letter"),
        ("narrator", "font_narrator"),
        ("square_thought", "font_square_thought"),
        ("black", "font_black"),

        ("explosion", "font_explosion"),
        ("sfx", "font_sfx"),
    )
    if translator.style_fonts:
        for _style, _attr in _font_map:
            pth = getattr(args, _attr, None)
            if pth and os.path.isfile(pth):
                translator.font_by_style[_style] = pth
                print(f"[*] فونت tone «{_style}»: {os.path.basename(pth)}")
    if not translator.style_fonts:
        translator.font_by_style = {k: translator.font_path for k in translator.font_by_style}
        print("[*] فونت جداگانهٔ لحن‌ها خاموش است → همهٔ حباب‌ها با فونت اصلی رندر می‌شوند.")

    if getattr(args, "font_normal", None) and os.path.isfile(args.font_normal):
        translator.font_path = args.font_normal
        translator.font_by_style["normal"] = args.font_normal

    if translator.font_by_style.get("explosion") and translator.font_by_style.get("shout") == args.font:
        if getattr(args, "font_explosion", None) and os.path.isfile(args.font_explosion):
            translator.font_by_style["shout"] = args.font_explosion
    if translator.font_by_style.get("sfx") and translator.font_by_style.get("comedy_shout") == args.font:
        if getattr(args, "font_sfx", None) and os.path.isfile(args.font_sfx):
            translator.font_by_style["comedy_shout"] = args.font_sfx

    _at = (getattr(args, "active_tones", None) or "").strip()
    if _at:
        translator.active_tones = {t.strip().lower() for t in _at.split(",") if t.strip()}
    else:
        _main_fp = os.path.abspath(translator.font_path or "")
        auto_tones = {s for s, p in translator.font_by_style.items()
                      if p and os.path.abspath(p) != _main_fp}
        auto_tones.add("normal")
        if "explosion" in auto_tones:
            auto_tones.add("shout")
        if "sfx" in auto_tones:
            auto_tones.add("comedy_shout")
        translator.active_tones = auto_tones
        dropped = sorted(set(translator.TONE_NAMES) - auto_tones)
        if dropped and args.debug:
            print("[*] برای این لحن‌ها فونت جدا تخصیص نیافته → از دستور ترجمه حذف شدند: "
                  + ", ".join(dropped))

    try:
        translator.run(
            args.input,
            output_path,
            resume=not args.no_resume,
            clean_old=not args.keep_old,
        )
    finally:
        try:
            _live_seq_flush()
        except Exception:
            pass

if __name__ == "__main__":
    main()
