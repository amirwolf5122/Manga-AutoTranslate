# BUILD-STRIP-START
# BUILD-STRIP-END
class MangaTranslator:
    _LAMA_MIN_VRAM_GB = 3.5
    _ANDROID_LAMA_MIN_TOTAL_GB = 4.0
    _ANDROID_LAMA_MIN_AVAIL_GB = 0.4
    _ANDROID_LAMA_WARN_AVAIL_GB = 1.2
    _ANDROID_LAMA_STRONG_CPU_CORES = 6

    @staticmethod
    def _detect_paddle_gpu() -> bool:
        try:
            import paddle
            return bool(paddle.is_compiled_with_cuda() and paddle.device.get_device() is not None)
        except Exception:
            return False

    @staticmethod
    def _detect_torch_cuda() -> bool:
        try:
            import torch
            return bool(torch.cuda.is_available())
        except Exception:
            return False

    @staticmethod
    def _cuda_vram_gb() -> float:
        try:
            import torch
            if not torch.cuda.is_available():
                return 0.0
            props = torch.cuda.get_device_properties(0)
            return float(props.total_memory) / (1024 ** 3)
        except Exception:
            return 0.0

    @staticmethod
    def _cuda_device_name() -> str:
        try:
            import torch
            if torch.cuda.is_available():
                return torch.cuda.get_device_name(0)
        except Exception:
            pass
        return ""

    @staticmethod
    def _available_ram_gb() -> float:
        try:
            if os.name == "nt":
                import ctypes
                class _MSE(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                    ]
                st = _MSE()
                st.dwLength = ctypes.sizeof(_MSE)
                if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st)):
                    return st.ullAvailPhys / (1024 ** 3)
        except Exception:
            pass
        try:
            with open("/proc/meminfo", encoding="ascii") as f:
                for line in f:
                    if line.startswith("MemAvailable:"):
                        return int(line.split()[1]) / (1024 * 1024)
        except Exception:
            pass
        return 8.0

    def _decide_lama(self, force_gpu: Optional[bool],
                     force_lama: bool = False,
                     clean_method: str = "") -> bool:

        has_ort = ort is not None
        has_torch = _torch_available()
        has_cuda = self._detect_torch_cuda() or _ort_has_cuda()
        vram = self._cuda_vram_gb()
        name = self._cuda_device_name()

        cm = (clean_method or "").strip().lower()
        if cm == "opencv":
            print("[*] روش پاکسازی: opencv.")
            return False
        if cm == "lama-manga":
            print("[*] روش پاکسازی: lama.onnx (پیش‌فرض).")
            return True
        if cm == "lama-big":
            if not has_torch:
                has_torch = _ensure_torch_cpu()
            if not has_torch:
                print("[*] lama-big این‌جا torch ندارد → lama.onnx.")
                return True
            print("[*] روش پاکسازی: big-lama.")
            return True

        if force_gpu is False and not force_lama:
            print("[*] --cpu → پاک‌سازی OpenCV سریع.")
            return False

        if not has_ort and not has_torch:
            print("[*] نه onnxruntime هست و نه torch → OpenCV inpaint.")
            return False

        if _on_android() and not force_lama:
            if os.environ.get("MANGA_ANDROID_LAMA", "1") == "0":
                if self.debug:
                    print("[*] اندروید: پاک‌سازی سریع OpenCV (MANGA_ANDROID_LAMA=0)")
                return False
            if self.debug:
                print("[*] اندروید: پاک‌سازی LaMa پچ‌به‌پچ — سریع‌ترین EP "
                      "روی همین گوشی خودکار انتخاب می‌شود.")
            return True

        if force_gpu is True:
            print(f"[*] --gpu → big-LaMa فعال ({name or 'CUDA'}, {vram:.1f} GB).")
            return True

        if force_lama:
            print("[*] --lama → پاک‌سازی big-LaMa فعال (روی CPU کندتر ولی تمیزتر).")
            return True

        if has_cuda and (vram <= 0 or vram >= self._LAMA_MIN_VRAM_GB):
            print(f"[*] GPU مناسب ({name or 'CUDA'}, {vram:.1f} GB) → big-LaMa.")
            return True

        if has_cuda:
            print(f"[*] GPU هست ({name}, {vram:.1f} GB) ولی VRAM کم → OpenCV. "
                  f"برای اجبار: --lama یا --gpu")
            return False
        if has_torch and not _on_android():
            avail = self._available_ram_gb()
            if avail and avail < 2.2:
                print(f"[*] رم آزاد کم است ({avail:.1f}GB) → پاک‌سازی OpenCV "
                      "(بارگذاری big-lama می‌توانست پروسه را بکشد). "
                      "برای اجبار LaMa: --lama")
                return False
            print("[*] دسکتاپ/وب → پاک‌سازی پیش‌فرض با big-lama.pt "
                  "(روی CPU کندتر ولی تمیزتر). برای غیرفعال‌سازی: --cpu")
            return True

        if has_ort and not _on_android():
            print("[*] دسکتاپ → پاک‌سازی پیش‌فرض با lama.onnx + flat (سبک و سریع). "
                  "برای big-lama: --clean-method lama-big | برای OpenCV: --clean-method opencv")
            return True

        print("[*] GPU نیست → OpenCV سریع. برای LaMa روی CPU: --lama")
        return False

    def __init__(
        self,
        api_key,
        provider: str = "gemini",
        ocr_langs: List[str] = None,
        model_name: Optional[str] = None,
        api_base: Optional[str] = None,
        font_path: Optional[str] = None,
        reading_order: str = "rtl",
        gpu: Optional[bool] = None,
        force_lama: bool = False,
        clean_method: Optional[str] = None,
        group_margin: int = 5,
        inpaint_radius: int = 3,
        mask_padding: int = 3,
        pad_ratio: float = 0.06,
        min_confidence: float = 0.12,
        det_confidence: float = 0.16,
        max_retries: int = 8,
        request_delay: float = 0.0,
        bubbles_per_request: int = 12,
        api_timeout: float = 30.0,
        max_chunk_height: int = 3600,
        chunk_overlap: int = 300,
        img_format: str = "webp",
        img_quality: int = 90,
        max_workers: int = 1,
        mag_ratio: float = 1.35,
        translation_temperature: float = 0.7,
        translation_top_p: float = 0.9,
        two_pass_ocr: bool = True,
        max_output_width: Optional[int] = None,
        stitch_max_height: int = 0,
        stitch_short_threshold: int = 0,
        stitch_keep_first: bool = True,
        stitch_explicit: bool = False,
        debug: bool = False,
        fake_translate: bool = False,
        clean_only: bool = False,
        translate_retranslate: bool = False,
        style_fonts: bool = True,
        active_tones: Optional[List[str]] = None,
        instruction_text: Optional[str] = None,
        prompt_mode: Optional[str] = None,
        clean_sfx: bool = False,
        repair_page_seams: bool = True,
    ):
        self.fake_translate = bool(fake_translate)
        self.clean_only = bool(clean_only)
        self.translate_retranslate = bool(translate_retranslate)
        self.clean_sfx = bool(clean_sfx) or (
            os.environ.get("MANGA_CLEAN_SFX", "0").strip() == "1")
        self.style_fonts = bool(style_fonts)
        self.active_tones = (set(active_tones) if active_tones else None)
        _raw_instr = (instruction_text or "").strip() or ""
        if _raw_instr and is_known_default_instruction(_raw_instr):
            _raw_instr = ""
        self.custom_instruction = _raw_instr
        _pm = ((prompt_mode if prompt_mode is not None
                else os.environ.get("MANGA_PROMPT_MODE", "")) or "professional").lower().strip()
        self.prompt_mode = _pm if _pm in PROMPT_MODES else "professional"
        self.det_confidence = float(det_confidence)
        provider = (provider or "gemini").lower().strip()
        if provider not in PROVIDER_PRESETS:
            raise ValueError(
                f"ارائه‌دهندهٔ ناشناخته: «{provider}». "
                f"گزینه‌ها: {', '.join(PROVIDER_PRESETS.keys())}"
            )
        self.provider = provider
        self.provider_cfg = PROVIDER_PRESETS[provider]
        self.provider_type = self.provider_cfg["type"]

        if isinstance(api_key, str):
            keys = [k.strip() for k in api_key.replace(";", ",").split(",") if k.strip()]
        else:
            keys = [k.strip() for k in api_key if k and str(k).strip()]
        random.shuffle(keys)
        if not keys and self.provider != "ollama":
            raise ValueError(f"حداقل یک کلید API برای {provider} لازم است.")
        if not keys:
            keys = ["ollama"]
        self._api_keys: List[str] = keys
        self._key_index: int = 0
        self._ocr_lock = threading.Lock()
        self._api_lock = threading.Lock()
        self._tls = threading.local()
        self._pace_lock = threading.Lock()
        self._fire_times: List[float] = []
        self._key_cooldown_until: Dict[str, float] = {}
        self.gemini_rpm_budget = 5
        self._daily_dead: Dict[Tuple[str, str], bool] = {}

        self.model_name_raw = (model_name or "").strip()
        _user_models = parse_model_list(self.model_name_raw)
        self.model_list = _user_models
        self.model_name = (_user_models[0] if _user_models
                           else (self.provider_cfg.get("default_model")
                                 or "gemini-3.5-flash-lite")).strip()
        self._model_cascade: List[str] = []
        self._model_index: int = 0
        self._last_good_model: str = ""
        self._model_fail_counts: Dict[str, int] = {}
        self._model_ok_counts: Dict[str, int] = {}
        self._model_banned: set = set()
        _user_base = (api_base or "").strip()
        self.api_base = normalize_api_base(_user_base) if _user_base \
            else self.provider_cfg.get("base_url")
        if _user_base and self.api_base:
            _ftype, _fbase = detect_custom_api_format(self.api_base)
            if _ftype != "openai" or re.search(
                    r"/(?:chat/completions|responses|messages|completions)$",
                    self.api_base, flags=re.I):
                if provider in ("custom", "openai", "openrouter", "together",
                                "xai", "groq", "deepseek", "mistral",
                                "gemini-openai"):
                    if _ftype != self.provider_type:
                        print(f"[*] فرمت API از لینک شناخته شد: "
                              f"{CUSTOM_API_FORMAT_HINTS.get(_ftype, _ftype)}")
                    self.provider_type = _ftype
                    self.provider_cfg = dict(self.provider_cfg)
                    self.provider_cfg["type"] = _ftype
            self.api_base = _fbase if _fbase else self.api_base

        self.font_path = font_path

        self.font_by_style: Dict[str, str] = {
            "normal": font_path,
            "shout": font_path,
            "comedy_shout": font_path,
            "whisper": font_path,
            "sun_thought": font_path,
            "thought": font_path,
            "free_text": font_path,
            "system": font_path,
            "monster": font_path,
            "cry": font_path,
            "fear": font_path,
            "broadcast": font_path,
            "letter": font_path,
            "narrator": font_path,
            "square_thought": font_path,
            "black": font_path,
        }
        self.reading_order = reading_order
        self.group_margin = group_margin
        self.inpaint_radius = inpaint_radius
        self.mask_padding = mask_padding
        self.pad_ratio = pad_ratio
        self.min_confidence = min_confidence
        self.max_retries = max_retries
        self.request_delay = request_delay

        self.bubbles_per_request = max(1, int(bubbles_per_request or 15))

        self.min_translate_batch = max(1, int(getattr(self, "min_translate_batch", 15) or 15))

        self.chapter_one_request = True

        self.erase_bubble_interior = False
        self.api_timeout = float(api_timeout) if api_timeout and api_timeout > 0 else 30.0
        self._daily_fail_streak: int = 0
        self._daily_fail_model: str = ""
        self.max_chunk_height = max_chunk_height
        self.chunk_overlap = chunk_overlap
        self.img_format = img_format
        self.img_quality = img_quality
        self.max_workers = max(1, int(max_workers))
        self.mag_ratio = mag_ratio
        try:
            self.translation_temperature = min(2.0, max(0.0, float(translation_temperature)))
        except Exception:
            self.translation_temperature = 0.7
        try:
            self.translation_top_p = min(1.0, max(0.0, float(translation_top_p)))
        except Exception:
            self.translation_top_p = 0.9
        self.two_pass_ocr = bool(two_pass_ocr)
        if _on_android() and os.environ.get(
                "MANGA_ANDROID_TWO_PASS", "").strip().lower() in (
                "0", "false", "no"):
            self.two_pass_ocr = False
        self.max_output_width = max_output_width
        self.stitch_max_height = int(stitch_max_height) if stitch_max_height else 0
        self.stitch_short_threshold = int(stitch_short_threshold) if stitch_short_threshold else 0
        self.stitch_keep_first = bool(stitch_keep_first)
        self.stitch_explicit = bool(stitch_explicit)
        self._independent_pages = False
        self._extraction_done = True
        self.repair_page_seams = bool(repair_page_seams)
        self.debug = bool(debug)
        self._last_debug_image = None

        self._lama = None
        self._lama_lock = threading.Lock()
        self._lama_preload_started = False
        self._title_skip_patterns: List[str] = []
        MangaTranslator._title_skip_patterns = []
        if not hasattr(MangaTranslator, "_page_clean_lock"):
            MangaTranslator._page_clean_lock = threading.Lock()
        self.client = None
        self.openai_client = None

        if not font_path or not os.path.isfile(font_path):
            raise FileNotFoundError(
                "یک فونت معتبر فارسی (ttf) با --font مشخص کنید. "
                "پیشنهاد: فونت Vazirmatn (رایگان و متن‌باز)."
            )

        try:
            _sys_fp = (self.font_by_style or {}).get("system")
            _sys_default = (not _sys_fp
                            or not os.path.isfile(_sys_fp)
                            or os.path.abspath(str(_sys_fp))
                            == os.path.abspath(str(font_path)))
            if _sys_default:
                _dirs = []
                _dirs.append(os.path.dirname(os.path.abspath(font_path)))
                _dirs.append(os.path.join(os.getcwd(), "fonts"))
                try:
                    _dirs.append(os.path.join(
                        os.path.dirname(os.path.abspath(__file__)), "fonts"))
                except Exception:
                    pass
                for _d in _dirs:
                    if not os.path.isdir(_d):
                        continue
                    _hit = ""
                    for _prio in ("code", "mono", "system", "sahel"):
                        for _f in sorted(os.listdir(_d)):
                            _fl = _f.lower()
                            if _fl.endswith((".ttf", ".otf")) and _prio in _fl:
                                _hit = os.path.join(_d, _f)
                                break
                        if _hit:
                            break
                    if _hit:
                        self.font_by_style["system"] = _hit
                        print(f"[*] فونت سیستم: {os.path.basename(_hit)}")
                        break
        except Exception:
            pass

        if gpu is None:
            _dml = False
            try:
                _dml = (os.name == "nt") and _ort_has_dml()
            except Exception:
                _dml = False
            ocr_gpu = (self._detect_paddle_gpu() or self._detect_torch_cuda()
                       or _ort_has_cuda() or _dml)
            try:
                _nv = _nvidia_gpu_present()
            except Exception:
                _nv = False
            if ocr_gpu and _dml and not _ort_has_cuda():
                print("[*] GPU (DirectML — AMD/Intel) شناسایی شد؛ OCR و پاکسازی "
                      "روی GPU اجرا می‌شه (برای اجبار به CPU از --cpu استفاده کن).")
            elif ocr_gpu:
                print("[*] GPU شناسایی شد؛ OCR روی GPU اجرا می‌شه (برای اجبار به CPU از --cpu استفاده کن).")
            elif _nv:
                print("[*] کارتِ NVIDIA پیدا شد ولی onnxruntime فعلی بدونِ CUDA است "
                      "→ OCR روی CPU. (بارِ بعدی استارت، onnxruntime-gpu خودکار "
                      "نصب میشود؛ یا دستی: pip install 'onnxruntime-gpu[cuda,cudnn]==1.26.0')")
            else:
                _dx = False
                try:
                    _dx = _directx_gpu_present()
                except Exception:
                    _dx = False
                if _dx:
                    print("[*] GPU ویندوزی (AMD/Intel) پیدا شد ولی onnxruntime فعلی "
                          "بدونِ DirectML است → OCR روی CPU. (بارِ بعدی استارت، "
                          "onnxruntime-directml خودکار نصب میشود؛ یا دستی: "
                          "pip install onnxruntime-directml)")
                else:
                    print("[*] GPU پیدا نشد؛ OCR روی CPU اجرا می‌شه.")
        else:
            ocr_gpu = bool(gpu)
            if ocr_gpu:
                print("[*] --gpu زده شده؛ OCR روی GPU.")
            else:
                print("[*] --cpu زده شده؛ OCR روی CPU.")

        self.use_gpu = ocr_gpu

        _cm = (clean_method or "").strip().lower()
        if _cm not in ("lama-manga", "lama-big", "opencv"):
            _cm = ""
        self.clean_method = _cm
        self.use_lama = self._decide_lama(force_gpu=gpu, force_lama=force_lama,
                                          clean_method=self.clean_method)
        self._inpainter_name = "OpenCV"

        self.ocr_langs = ocr_langs or ["en"]
        lang_map = {
            "en": "en", "fa": "fa", "ko": "korean", "ja": "japan", "zh": "ch",
            "fr": "french", "de": "german", "es": "spanish", "it": "italian",
            "pt": "portuguese", "ru": "russian", "ar": "arabic",
        }
        main_lang = "en"
        for lang in self.ocr_langs:
            if str(lang).lower().strip() == "multi":
                main_lang = "multi" if _on_android() else "korean"
                break
            if lang in lang_map:
                main_lang = lang_map[lang]
                break

        device = "gpu" if ocr_gpu else "cpu"
        self.ocr = None
        self._ocr_backend_name = "none"

        avail_ram = self._available_ram_gb()
        if avail_ram < 6.0:
            if self.max_workers > 2:
                print(f"[*] RAM آزاد کم است ({avail_ram:.1f} GB) → workers={self.max_workers} به ۲ محدود شد.")
                self.max_workers = 2
        if self.max_workers <= 1:
            try:
                self.max_workers = _parallel_budget("ocr")
            except Exception:
                self.max_workers = 2
        try:
            _clean_w = _parallel_budget("clean")
        except Exception:
            _clean_w = 2
        try:
            print(f"[*] توانِ موازی: OCR تا {self.max_workers} ناحیهٔ همزمان "
                  f"| پاکسازی تا {_clean_w} خوشهٔ همزمان "
                  f"(cpu={self._cpu_core_count()}, "
                  f"ram={avail_ram:.1f}GB, "
                  f"gpu={'بله' if self.use_gpu else 'نخ'})")
        except Exception:
            pass

        use_paddle = _HAS_PADDLE and avail_ram >= 6.0
        if _HAS_PADDLE and not use_paddle:
            print(f"[*] RAM آزاد کم است ({avail_ram:.1f} GB) → PaddleOCR سنگین لود نمی‌شود؛ RapidOCR سبک استفاده می‌شود.")

        if use_paddle:
            print(f"[*] در حال بارگذاری PaddleOCR | lang={main_lang} device={device} ...")
            ocr_kwargs = dict(
                lang=main_lang,
                text_det_thresh=0.25,
                text_det_box_thresh=0.4,
                text_det_unclip_ratio=1.8,
            )
            try:
                try:
                    engine = PaddleOCR(
                        use_textline_orientation=True,
                        device=device,
                        enable_mkldnn=False,
                        **ocr_kwargs,
                    )
                except TypeError:
                    try:
                        engine = PaddleOCR(
                            use_angle_cls=True,
                            use_gpu=ocr_gpu,
                            enable_mkldnn=False,
                            **ocr_kwargs,
                        )
                    except TypeError:
                        try:
                            engine = PaddleOCR(
                                use_textline_orientation=True,
                                device=device,
                                **ocr_kwargs,
                            )
                        except TypeError:
                            engine = PaddleOCR(
                                use_angle_cls=True,
                                use_gpu=ocr_gpu,
                                **ocr_kwargs,
                            )
                self.ocr = PaddleOCRWrapper(engine)
                self._ocr_backend_name = "paddle"
                print(f"[+] PaddleOCR آماده | lang={main_lang} | device={device}")
            except Exception as e:
                print(f"[!] PaddleOCR لود نشد ({e}) → RapidOCR ONNX")

        if self.ocr is None and _on_android():
            try:
                self.ocr = RapidOCRBackend(
                    lang=main_lang, prefer_gpu=self.use_gpu)
                self._ocr_backend_name = "rapidocr"
                print("[*] اندروید: استخراجِ متن = فقط رویِ کراپهایِ "
                      "detector-v4-s (سبکِ PC)")
            except Exception as e:
                print(f"[!] موتورِ OCR گوشی لود نشد ({e})")
                raise

        try:
            _nw_env = int(os.environ.get("MANGA_OCR_WORKERS", "0") or 0)
            if _nw_env > 0:
                self.max_workers = min(8, _nw_env)
        except Exception:
            pass

        if self.ocr is None:
            try:
                self.ocr = RapidOCRBackend(lang=main_lang, prefer_gpu=self.use_gpu)
                self._ocr_backend_name = "rapidocr"
            except Exception as e:
                print(f"[!] RapidOCR هم لود نشد ({e})", file=sys.stderr)
                raise ImportError(
                    "هیچ OCR در دسترس نیست.\n"
                    "  پیشنهاد: pip install paddleocr\n"
                    "  یا: pip install rapidocr  (یا rapidocr-onnxruntime)"
                ) from e

        if self.ocr is not None and not _on_android():
            _thr = int(getattr(self.ocr, "ocr_threads", 0) or 0)
            if _thr > 0:
                try:
                    _cores = self._cpu_core_count() or (os.cpu_count() or 4)
                except Exception:
                    _cores = os.cpu_count() or 4
                _want = max(2, min(int(self.max_workers or 2),
                                      max(1, _cores // _thr)))
                if _want < int(self.max_workers or 2):
                    print(f"[*] همترازیِ OCR: workers={self.max_workers} → "
                          f"{_want} ({_want} ورکر × {_thr} نخ ≈ "
                          f"{_cores} هسته — ضدِ تشتت)")
                    self.max_workers = _want

        print(f"[*] OCR: {self._ocr_backend_name} | workers={self.max_workers}")

        self.det = None
        self.det_confidence = float(getattr(self, "det_confidence", 0.28) or 0.28)
        try:
            print("[*] بارگذاری مدل تشخیص حباب…")
            self.det = RTDetrV2ONNXDetector(
                prefer_gpu=self.use_gpu,
                conf_thresh=self.det_confidence,
                iou_thresh=0.45,
                threads=4 if _on_android() else max(1, int(self.max_workers or 2)),
                multi_scale=(not _IS_ANDROID)
                            or (self._ocr_backend_name == "rapidocr"),
            )
        except Exception as e:
            print(f"[!] RT-DETR (detector-v4-s) لود نشد ({e}) → استخراجِ متن و "
                  "برشِ امن کار نمیکند (مدلِ تشخیص الزامی است)")
            self.det = None

        if self.provider_type == "gemini":
            if not _HAS_GEMINI and _HAS_OPENAI:
                print("[!] google-genai روی این دستگاه نیست → "
                      "Gemini از مسیر سازگار openai (SDK واقعی) اجرا می‌شود")
                self.provider_cfg = PROVIDER_PRESETS["gemini-openai"]
                self.provider_type = "openai"
                self.api_base = self.provider_cfg["base_url"]
            elif not _HAS_GEMINI:
                raise ImportError(
                    "برای استفاده از Gemini باید google-genai نصب باشد:\n"
                    "  pip install google-genai"
                )

            self._key_index = 0
            if not self.clean_only and not self.fake_translate:
                self._apply_api_key(self._api_keys[0])
            else:
                self.client = None
            self._model_cascade = self._build_model_cascade(self.model_name, self.client)
            self.model_name = self._model_cascade[0]
            _nm = len(getattr(self, "model_list", []) or [])
            if _nm > 1:
                print(f"[*] مترجم: {self.model_name} (+{_nm - 1} مدلِ فال‌بک: "
                      f"{', '.join(self._model_cascade[1:_nm])})")
                if len(self._api_keys) > 1:
                    print(f"    {len(self._api_keys)} کلید (چرخش خودکار)")
            elif len(self._api_keys) > 1:
                print(f"[*] مترجم: {self.model_name} | {len(self._api_keys)} کلید")
            else:
                print(f"[*] مترجم: {self.model_name}")
        else:

            if not _HAS_OPENAI:
                raise ImportError(
                    "برای استفاده از OpenAI / DeepSeek / Groq / ... باید openai نصب باشد:\n"
                    "  pip install openai"
                )
            self._key_index = 0
            if not self.clean_only and not self.fake_translate:
                self._apply_api_key(self._api_keys[0])
            else:
                self.client = None
            self._model_cascade = ([m for m in
                                    (getattr(self, "model_list", None) or [])]
                                   or [self.model_name])
            self.model_name = self._model_cascade[0]
            if len(self._model_cascade) > 1:
                print(f"[*] مترجم: {self.model_name} "
                      f"(+{len(self._model_cascade) - 1} مدلِ فال‌بک: "
                      f"{', '.join(self._model_cascade[1:])}) ({self.provider})")
            else:
                print(f"[*] مترجم: {self.model_name} ({self.provider})")
            if len(self._api_keys) > 1:
                print(f"    {len(self._api_keys)} کلید (جابه‌جایی خودکار)")

    @staticmethod
    def _total_ram_gb() -> float:
        try:
            with open("/proc/meminfo", encoding="ascii") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        return int(line.split()[1]) / (1024 * 1024)
        except Exception:
            pass
        return 0.0

    def preload_lama_async(self):
        if getattr(self, "_lama_preload_started", False) or not self.use_lama:
            return
        self._lama_preload_started = True

        def _warm():
            try:
                _l = self._get_lama()
                if _l is not None:
                    try:
                        print("[*] LaMa پیش‌بارگذاری شد (پس‌زمینه)")
                    except Exception:
                        pass
            except Exception:
                pass

        try:
            threading.Thread(target=_warm, daemon=True,
                             name="lama-preload").start()
        except Exception:
            self._lama_preload_started = False

    def _get_lama(self, threads: int = 0, force: bool = False):
        _t_lw = time.time()
        with self._lama_lock:
            try:
                _lw = time.time() - _t_lw
                if _lw > 0.3:
                    print(f"[TIME] lama-wait={_lw:.1f}s "
                          f"(سشن در نخِ دیگر ساخته می‌شد)", flush=True)
            except Exception:
                pass
            _l = self._get_lama_locked()
            _want_sw = (threads and _l is not None and self.use_lama
                        and int(threads) != int(getattr(self, "_lama_threads", 0) or 0)
                        and isinstance(_l, LamaMangaONNX))
            if _want_sw and str(getattr(_l, "ep_used", "") or "cpu").lower() \
                    not in ("", "cpu", "none"):
                try:
                    print(f"    [~] سوئیچِ LaMa به {threads} نخ رد شد "
                          f"(EP: {getattr(_l, 'ep_used', '?')})", flush=True)
                except Exception:
                    pass
                _want_sw = False
            if _want_sw and not self._lama_switch_ok(int(threads),
                                                     force=force):
                try:
                    _av = self._available_ram_gb()
                    _old = int(getattr(self, "_lama_threads", 0) or 0)
                    _cool = (time.time() - float(
                        getattr(self, "_lama_switch_at", 0.0) or 0.0)) < 2.0
                    print(f"    [~] سوئیچِ LaMa به {threads} نخ رد شد "
                          f"(سشن: {_old} نخ، رم: {_av:.2f}GB، "
                          f"خنک‌کاری: {'بله' if _cool and not force else 'خیر'})",
                          flush=True)
                except Exception:
                    pass
                _want_sw = False
            if _want_sw:
                self._lama_switch_at = time.time()
                _new = self._build_lama_cpu(int(threads))
                if _new is not None:
                    self._lama = _new
                    self._lama_threads = int(threads)
                    try:
                        print(f"    [*] سشنِ LaMa → {threads} نخ "
                              "(پچِ کم → هسته‌های بیکار پر می‌شود)", flush=True)
                    except Exception:
                        pass
                else:
                    try:
                        _av = self._available_ram_gb()
                        print(f"    [!] ساختِ سشنِ LaMa با {threads} نخ ناموفق "
                              f"(رمِ آزاد: {_av:.2f}GB) → سشنِ قبلی حفظ شد",
                              flush=True)
                    except Exception:
                        pass
            return self._lama

    def _lama_switch_ok(self, threads: int, force: bool = False) -> bool:
        try:
            _now = time.time()
            if not force and (_now - float(
                    getattr(self, "_lama_switch_at", 0.0) or 0.0) < 2.0):
                return False
            _old = int(getattr(self, "_lama_threads", 0) or 0)
            if _old and abs(int(threads) - _old) < 2:
                return False
            if not (1 <= int(threads) <= 4):
                return False
            _av = self._available_ram_gb()
            _thr_min = 0.12 if int(threads) < _old else 0.28
            if _av and _av < _thr_min:
                return False
            return True
        except Exception:
            return False

    def _build_lama_cpu(self, threads: int):
        try:
            return LamaMangaONNX(prefer_gpu=False, threads=max(1, int(threads)))
        except Exception:
            return None

    def _get_lama_cpu_safe(self):
        _s = getattr(self, "_lama_cpu_safe", None)
        if _s is not None:
            return _s
        if getattr(self, "_lama_cpu_safe_failed", False):
            return None
        _lk = getattr(self, "_lama_cpu_safe_lock", None)
        if _lk is None:
            import threading as _th
            _lk = _th.Lock()
            self._lama_cpu_safe_lock = _lk
        with _lk:
            _s = getattr(self, "_lama_cpu_safe", None)
            if _s is not None:
                return _s
            if getattr(self, "_lama_cpu_safe_failed", False):
                return None
            try:
                _cores = int(self._cpu_core_count() or 4)
                _t = max(1, min(4, _cores))
                try:
                    _av = self._available_ram_gb()
                except Exception:
                    _av = None
                if _av and _av < 0.30:
                    self._lama_cpu_safe_failed = True
                    try:
                        print(f"    [~] سشنِ CPUِ امنِ LaMa ساخته نشد "
                              f"(رمِ آزاد: {_av:.2f}GB)", flush=True)
                    except Exception:
                        pass
                    return None
                try:
                    print(f"    [*] ساختِ سشنِ CPUِ امنِ LaMa (نجاتِ پچ)…",
                          flush=True)
                except Exception:
                    pass
                _mp = getattr(self, "_lama_model_path", None)
                _s = LamaMangaONNX(prefer_gpu=False, threads=_t,
                                   model_path=_mp) if _mp else \
                    LamaMangaONNX(prefer_gpu=False, threads=_t)
                self._lama_cpu_safe = _s
            except Exception:
                self._lama_cpu_safe_failed = True
                _s = None
            return _s

    def _force_box_gradient_fill(self, image: np.ndarray,
                                 cx0: int, cy0: int, cx1: int, cy1: int):
        try:
            _fbs = getattr(self, "_lama_force_rect_boxes", None) or []
            if not _fbs:
                return None
            for _fb in _fbs:
                _bx0, _by0 = int(_fb[0]), int(_fb[1])
                _bx1, _by1 = int(_fb[2]), int(_fb[3])
                _ix0, _iy0 = max(cx0, _bx0), max(cy0, _by0)
                _ix1, _iy1 = min(cx1, _bx1), min(cy1, _by1)
                if _ix1 - _ix0 < 24 or _iy1 - _iy0 < 24:
                    continue
                _ex0 = max(_ix0, _bx0 + 8)
                _ey0 = max(_iy0, _by0 + 8)
                _ex1 = min(_ix1, _bx1 - 7)
                _ey1 = min(_iy1, _by1 - 7)
                if _ex1 - _ex0 < 12 or _ey1 - _ey0 < 12:
                    continue
                _sub = image[_ey0:_ey1, _ex0:_ex1]
                _g = cv2.cvtColor(_sub, cv2.COLOR_BGR2GRAY)
                _blk_med = float(np.median(_g))
                _thr = min(130.0, max(60.0, _blk_med + 25.0))
                _dark = (_g < _thr).astype(np.uint8)
                _src_f = _sub.astype(np.float32)
                _k = 31
                _num = cv2.blur(_src_f * _dark[..., None], (_k, _k))
                _den = cv2.blur(_dark.astype(np.float32), (_k, _k))
                _dk_px = _src_f[_dark > 0]
                _fb_col = (np.median(_dk_px, axis=0)
                           if _dk_px.size >= 30
                           else np.array([0.0, 0.0, 0.0]))
                _fill = np.where(
                    _den[..., None] > 0.02,
                    _num / np.maximum(_den, 1e-6)[..., None],
                    _fb_col[None, None, :]).astype(np.float32)
                _out = image[cy0:cy1, cx0:cx1].copy()
                _out[_ey0 - cy0:_ey1 - cy0,
                     _ex0 - cx0:_ex1 - cx0] = np.clip(
                    np.rint(_fill), 0, 255).astype(np.uint8)
                return _out
        except Exception:
            return None
        return None

    def _get_lama_locked(self):

        if self._lama is None and self.use_lama:
            if _on_android():
                total = self._total_ram_gb()
                avail = self._available_ram_gb()
                cores = self._cpu_core_count()
                strong_cpu = cores >= self._ANDROID_LAMA_STRONG_CPU_CORES
                try:
                    import gc as _gc
                    _gc.collect()
                except Exception:
                    pass
                if total and total < self._ANDROID_LAMA_MIN_TOTAL_GB:
                    print(f"[!] LaMa فعال نشد: رم کل گوشی {total:.1f}GB است "
                          f"(حداقل {self._ANDROID_LAMA_MIN_TOTAL_GB:.0f}GB لازم است) "
                          f"→ پاک‌سازی OpenCV (سبک و سریع).")
                    self.use_lama = False
                    self._inpainter_name = "OpenCV"
                    return None
                if avail and avail < self._ANDROID_LAMA_MIN_AVAIL_GB:
                    if strong_cpu:
                        print(f"[!] رم آزاد لحظه‌ای خیلی کم است ({avail:.1f}GB) ولی CPU "
                              f"گوشی قوی است ({cores} هسته) → با این حال تلاش می‌کنیم؛ "
                              f"اندروید با کش/zram جا باز می‌کند. اگر باز کرش شد، "
                              f"اپ‌های بیکار را ببند و دوباره امتحان کن.")
                    else:
                        print(f"[!] الان رم آزاد گوشی خیلی کم است ({avail:.1f}GB) — LaMa این بار "
                              f"اجرا نشد → OpenCV. اپ‌های بیکار را ببند و دوباره امتحان کن.")
                        self.use_lama = False
                        self._inpainter_name = "OpenCV"
                        return None
                elif avail and avail < self._ANDROID_LAMA_WARN_AVAIL_GB:
                    print(f"    [!] رم آزاد کمی پایین است ({avail:.1f}GB)؛ اگر وسط کار "
                          f"کرش شد، اپ‌های بیکار را ببند یا چند لحظه بعد امتحان کن.")
                print(f"[*] رم گوشی: کل {total:.1f}GB / آزاد {avail:.1f}GB / "
                      f"{cores} هستهٔ CPU → LaMa-Manga روی CPU اجرا می‌شود "
                      f"(کندتر ولی تمیزتر از OpenCV).")
            else:
                _av = self._available_ram_gb()
                if _av and _av < 1.0:
                    print(f"[!] رم آزاد خیلی کم است ({_av:.1f}GB) → پاک‌سازی "
                          "OpenCV (بارگذاری LaMa حذف شد تا کرش نکند).")
                    self.use_lama = False
                    self._inpainter_name = "OpenCV"
                    return None
            _backend = (os.environ.get("MANGA_LAMA_BACKEND", "auto")
                        or "auto").strip().lower()
            if _backend == "auto":
                _backend = {"lama-manga": "onnx", "lama-big": "torch"}.get(
                    getattr(self, "clean_method", "") or "", "auto")
            if _backend == "onnx":
                _want_torch = False
            elif _backend == "torch":
                if not _torch_available():
                    _ensure_torch_cpu()
                _want_torch = _torch_available()
                if not _want_torch:
                    print("    [!] torch نصب نشد → lama.onnx")
            else:
                _want_torch = _torch_available()
            if _want_torch:
                try:
                    print("    [*] بارگذاری big-lama.pt (TorchScript) ...")
                    self._lama = LamaTorch(prefer_gpu=self.use_gpu)
                    self._inpainter_name = "big-LaMa"
                except Exception as e:
                    print(f"    [!] big-LaMa ناموفق ({e}) → LaMa-Manga ONNX")
            elif self._lama is None:
                print("    [*] بارگذاری lama.onnx ...")
            if self._lama is None and self.use_lama:
                try:
                    try:
                        _awa = int(self._lama_workers_auto())
                    except Exception:
                        _awa = 2
                    try:
                        _nc = int(self._cpu_core_count())
                    except Exception:
                        _nc = os.cpu_count() or 4
                    _thr = max(1, min(4, _nc // 2))
                    self._lama = LamaMangaONNX(
                        prefer_gpu=self.use_gpu,
                        threads=_thr,
                    )
                    try:
                        self._lama_model_path = getattr(
                            self._lama, "model_path", None)
                    except Exception:
                        pass
                    self._inpainter_name = "LaMa-Manga"
                except Exception as e2:
                    print(f"    [!] LaMa-Manga ناموفق ({e2}) → LaMa ONNX")
                    try:
                        self._lama = LamaONNX(
                            prefer_gpu=self.use_gpu,
                            threads=max(1, int(getattr(self, "max_workers", 2) or 2)),
                        )
                        self._inpainter_name = "LaMa"
                    except Exception as e3:
                        print(f"    [!] LaMa هم ناموفق ({e3}) → OpenCV")
                        self.use_lama = False
                        self._lama = None
                        self._inpainter_name = "OpenCV"
        if self._lama is not None and not getattr(self, "_lama_threads_seen", False):
            self._lama_threads = int(getattr(self._lama, "thr_used", 0) or 0)
            self._lama_threads_seen = True
        return self._lama

    @staticmethod
    def _cpu_core_count() -> int:
        try:
            n = os.cpu_count()
            if n:
                return int(n)
        except Exception:
            pass
        try:
            with open("/proc/cpuinfo", encoding="ascii") as f:
                return sum(1 for ln in f if ln.startswith("processor"))
        except Exception:
            pass
        return 4

    def _mask_key(self, key: str) -> str:
        if not key:
            return "(خالی)"
        if len(key) <= 10:
            return key[:3] + "..."
        return key[:6] + "..." + key[-4:]

    def _is_banned_or_invalid_key_error(self, err: Exception) -> bool:
        msg = str(err).lower()

        indicators = (
            "api key not valid",
            "api_key_invalid",
            "invalid api key",
            "api key expired",
            "api_key_service_blocked",
            "consumer_suspended",
            "has been blocked",
            "key is invalid",
            "incorrect api key",
            "authentication failed",
            "unauthenticated",
            "permission_denied",
        )

        if "401" in msg and any(x in msg for x in ("key", "auth", "credential", "token")):
            return True
        return any(ind in msg for ind in indicators)

    def _is_model_unavailable_error(self, err: Exception) -> bool:
        msg = str(err)
        low = msg.lower()
        return (
            "503" in msg
            or "UNAVAILABLE" in msg
            or "404" in msg
            or "NOT_FOUND" in msg
            or "high demand" in low
            or "try again later" in low
            or "currently experiencing" in low
            or "model not found" in low
            or "not found for api version" in low
            or "is not supported" in low
            or "no longer available" in low
            or "please update your code to use a newer model" in low
            or "developer instruction is not enabled" in low
            or "invalid_argument" in low
        )

    def _is_model_permanently_gone(self, err: Exception) -> bool:
        msg = str(err).lower()
        return (
            "404" in str(err)
            or "not_found" in msg
            or "no longer available" in msg
            or "please update your code to use a newer model" in msg
            or "model not found" in msg
            or "developer instruction is not enabled" in msg
            or "system instruction is not enabled" in msg
            or "is not supported for" in msg
            or "not enabled for models/" in msg
            or ("invalid_argument" in msg and "instruction" in msg)
            or ("invalid_argument" in msg and "not enabled" in msg)
        )

    @staticmethod
    def _static_fallback_models(primary: str) -> List[str]:
        preferred = list(GEMINI_FLASH_MODELS_OFFLINE)
        cascade = [primary] if primary else []
        for m in preferred:
            if m and m not in cascade:
                cascade.append(m)
        return cascade or preferred

    @staticmethod
    def _model_sort_key(name: str) -> tuple:
        n = name.lower().replace("models/", "")
        ver_m = re.search(r"gemini-(\d+(?:\.\d+)?)", n)
        major_minor = 0.0
        if ver_m:
            try:
                major_minor = float(ver_m.group(1))
            except ValueError:
                major_minor = 0.0

        is_lite = "lite" in n
        is_flash = "flash" in n
        is_pro = "pro" in n and "flash" not in n
        is_preview = "preview" in n
        is_latest = n.endswith("-latest") or n in (
            "gemini-flash-latest", "gemini-flash-lite-latest", "gemini-pro-latest"
        )

        if is_lite:
            type_rank = 0
        elif is_flash:
            type_rank = 1
        elif is_preview:
            type_rank = 2
        elif is_pro:
            type_rank = 3
        else:
            type_rank = 4

        if is_latest and major_minor <= 0:
            version_rank = 50.0
        else:
            version_rank = -major_minor

        age_penalty = 0 if major_minor >= 2.0 or is_latest else 10
        return (age_penalty, type_rank, version_rank, n)

    def _discover_models_from_api(self, client) -> List[str]:
        names: List[str] = []
        ban_substrings = (
            "image", "tts", "live", "audio", "embedding", "gemma",
            "robotics", "omni", "nano-banana", "imagen", "computer-use",
            "computer_use", "antigravity", "veo", "lyria", "chirp",
            "dialog", "code-execution", "aqa", "text-embedding",
            "gecko", "vision", "dream", "bard",
        )
        try:
            for m in client.models.list():
                raw = getattr(m, "name", None) or ""
                short = raw.replace("models/", "").strip()
                if not short:
                    continue
                low = short.lower()
                if any(b in low for b in ban_substrings):
                    continue
                if not low.startswith("gemini"):
                    continue
                _dg = re.match(r"gemini-(\d+)", low)
                if _dg:
                    try:
                        if int(_dg.group(1)) <= 2:
                            continue
                    except ValueError:
                        pass

                actions = getattr(m, "supported_actions", None) or []
                methods = getattr(m, "supported_generation_methods", None) or []
                ok = False
                if actions:
                    ok = "generateContent" in actions
                elif methods:
                    ok = "generateContent" in methods
                else:
                    ok = True
                if not ok:
                    continue
                names.append(short)
        except Exception as e:
            _msg = str(e).split(chr(10))[0][:120]
            print(f"    [!] کشفِ SDK مدل ناموفق: {_msg} → تلاشِ REST")

        if not names:
            names = self._discover_models_via_rest()
        if not names:
            return []

        uniq = sorted(set(names), key=self._model_sort_key)
        return uniq

    def _discover_models_via_rest(self) -> List[str]:
        import requests as _rq
        key = ""
        try:
            key = (self._current_api_key() or "").strip()
        except Exception:
            key = ""
        if not key:
            return []
        ban_substrings = (
            "image", "tts", "live", "audio", "embedding", "gemma",
            "robotics", "omni", "nano-banana", "imagen", "computer-use",
            "computer_use", "antigravity", "veo", "lyria", "chirp",
            "dialog", "code-execution", "aqa", "text-embedding",
            "gecko", "vision", "dream", "bard",
        )
        out: List[str] = []
        try:
            r = _rq.get(
                "https://generativelanguage.googleapis.com/v1beta/models",
                params={"pageSize": 1000, "key": key},
                timeout=20,
            )
            r.raise_for_status()
            data = r.json() or {}
            for m in (data.get("models") or []):
                raw = str(m.get("name") or "")
                short = raw.replace("models/", "").strip()
                if not short:
                    continue
                low = short.lower()
                if not low.startswith("gemini"):
                    continue
                if any(b in low for b in ban_substrings):
                    continue
                _dg = re.match(r"gemini-(\d+)", low)
                if _dg:
                    try:
                        if int(_dg.group(1)) <= 2:
                            continue
                    except ValueError:
                        pass
                methods = m.get("supportedGenerationMethods") or []
                if methods and "generateContent" not in methods:
                    continue
                out.append(short)
        except Exception as e:
            _msg = str(e).split(chr(10))[0][:120]
            print(f"    [!] کشفِ REST مدل هم ناموفق: {_msg}")
            return []
        if out:
            print(f"[*] {len(out)} مدل زنده از REST گوگل گرفته شد.")
        return sorted(set(out), key=self._model_sort_key)

    @staticmethod
    def _is_bad_translate_model(name: str) -> bool:
        low = (name or "").lower().replace("models/", "")
        ban = (
            "computer-use", "computer_use", "antigravity", "veo", "lyria",
            "image", "tts", "live", "audio", "embedding", "gemma", "robotics",
            "omni", "imagen", "chirp", "aqa", "dream",
            "gemini-pro-latest", "transcribe", "decision",
        )
        if any(b in low for b in ban):
            return True
        if not low.startswith("gemini"):
            return True
        _m = re.match(r"gemini-(\d+)", low)
        if _m:
            try:
                if int(_m.group(1)) <= 2:
                    return True
            except ValueError:
                return False
        return False

    @staticmethod
    def _is_bad_list_model(name: str) -> bool:
        return MangaTranslator._is_bad_translate_model(name)

    @staticmethod
    def _extract_suggested_model(err: Exception) -> Optional[str]:

        msg = str(err or "")

        m = re.search(r"use models?/([a-zA-Z0-9._\-]+)", msg, flags=re.I)
        if m:
            name = m.group(1).strip().replace("models/", "")
            if name.lower().startswith("gemini"):
                return name
        m = re.search(r"models/([a-zA-Z0-9._\-]+)", msg)
        if m:
            name = m.group(1).strip()
            if name.lower().startswith("gemini") and "no longer available" not in msg.lower():
                return name
        return None

    def _build_model_cascade(self, primary: str, client=None) -> List[str]:
        primary = (primary or "").strip().replace("models/", "")
        if primary and self._is_bad_translate_model(primary):
            primary = ""

        user_list = [m.strip().replace("models/", "") for m in
                     (getattr(self, "model_list", None) or [])
                     if str(m or "").strip()]
        user_list = [m for m in user_list if not self._is_bad_translate_model(m)]
        if primary and primary not in user_list:
            user_list.insert(0, primary)

        discovered: List[str] = []
        if client is not None:
            discovered = self._discover_models_from_api(client)

        discovered = [m for m in discovered
                      if m not in getattr(self, "_model_banned", set())]

        if discovered:
            discovered = [m for m in discovered if not self._is_bad_translate_model(m)]
            discovered = sorted(set(discovered), key=self._model_sort_key)

            try:
                _keys_txt = ""
                try:
                    _keys_txt = str(self._current_api_key() or "")
                except Exception:
                    _keys_txt = ""
                if _keys_txt and len(discovered) > 1:
                    _good, _res = gemini_style_probe_many(discovered, _keys_txt)
                    if _good:
                        _drop = [m for m in discovered if m not in _good]
                        if _drop:
                            print(
                                f"[*] سنجشِ زندهٔ سبک: {len(_good)} مدلِ سالم "
                                f"ماند؛ حذف شد: {'، '.join(_drop[:6])}"
                                + ("…" if len(_drop) > 6 else ""))
                        discovered = _good
                    elif _res:
                        print("[!] سنجشِ زنده: هیچ مدلی جوابِ سالم نداد — "
                              "چرخِ خام همان رفتارِ «خطا → مدلِ بعدی» را دارد.")
            except Exception as _pe:
                print(f"[!] سنجشِ زندهٔ سبک انجام نشد ({str(_pe)[:80]}) — "
                      "ادامه با فهرستِ خام.")

            print(
                f"[*] {len(discovered)} مدل فعال از API | "
                f"{' → '.join(discovered[:10])}{'…' if len(discovered) > 10 else ''}"
            )

            cascade: List[str] = []
            for m in user_list:
                if m in discovered and m not in cascade:
                    cascade.append(m)
                elif m not in cascade:
                    cascade.append(m)
            for m in discovered:
                if m not in cascade:
                    cascade.append(m)

            def _costly(n: str) -> bool:
                low = n.lower()
                return ("pro" in low and "flash" not in low)

            if cascade:
                head = [m for m in user_list if m in cascade]
                rest = [m for m in cascade if m not in head]
                cheap = [m for m in rest if not _costly(m)]
                costly = [m for m in rest if _costly(m)]
                cascade = head + cheap + costly
                return cascade

        print("[*] کشف API ممکن نشد / خالی → fallback محافظه‌کارانه")
        static = self._static_fallback_models(primary or "gemini-3.5-flash-lite")
        kept = [m for m in static if m not in getattr(self, "_model_banned", set())]
        out = user_list + [m for m in (kept or static) if m not in user_list]
        return out or static

    def _note_model_ok(self, name: str = "") -> None:
        try:
            name = (name or self._thread_model() or "").replace("models/", "").strip()
        except Exception:
            name = (name or "").replace("models/", "").strip()
        if not name:
            return
        self._model_ok_counts[name] = self._model_ok_counts.get(name, 0) + 1
        self._model_fail_counts.pop(name, None)

    def _note_model_fail(self, name: str = "", ban_after: int = 3) -> bool:
        try:
            name = (name or self._thread_model() or "").replace("models/", "").strip()
        except Exception:
            name = (name or "").replace("models/", "").strip()
        if not name:
            return False
        if self._model_ok_counts.get(name, 0) > 0:
            return False
        n = self._model_fail_counts.get(name, 0) + 1
        self._model_fail_counts[name] = n
        if n < ban_after:
            return False
        self._model_fail_counts.pop(name, None)
        self._model_banned.add(name)
        print(f"    [!] مدل «{name}» {ban_after} بار در دسترس نبود → بن شد؛ "
              f"دیگر امتحان نمیشود.")
        return True

    def _drop_current_model_and_switch(self, reason: str = "") -> bool:

        if not self._model_cascade:
            return False
        dead = self.model_name
        if 0 <= self._model_index < len(self._model_cascade):
            del self._model_cascade[self._model_index]

        else:
            self._model_cascade = [m for m in self._model_cascade if m != dead]
        if not self._model_cascade:
            print(f"    [!] مدل «{dead}» حذف شد ولی مدل دیگری در cascade نیست.")
            return False

        if self._model_index >= len(self._model_cascade):
            self._model_index = len(self._model_cascade) - 1
        self.model_name = self._model_cascade[self._model_index]
        self._set_thread_model(self.model_name, self._model_index)
        extra = f" ({reason})" if reason else ""
        print(f"    [!] مدل «{dead}» حذف شد → ادامه از: {self.model_name} "
              f"[{self._model_index + 1}/{len(self._model_cascade)}]{extra}")
        return True

    def _switch_to_next_model(self, reason: str = "") -> bool:

        banned = getattr(self, "_model_banned", set())
        tls = getattr(self, "_tls", None)
        local = getattr(tls, "local_cascade", None) if tls is not None else None
        if local:
            li = int(getattr(tls, "local_index", 0) or 0)
            while li + 1 < len(local) and local[li + 1] in banned:
                li += 1
            li += 1
            if li >= len(local):
                return False
            tls.local_index = li
            name = local[li]
            self._set_thread_model(name, li)
            extra = f" ({reason})" if reason else ""
            print(f"    [*] مدل بعدی: {name} [{li + 1}/{len(local)}]{extra}")
            return True
        if not self._model_cascade:
            return False
        next_idx = self._model_index
        while (next_idx + 1 < len(self._model_cascade)
               and self._model_cascade[next_idx + 1] in banned):
            next_idx += 1
        next_idx += 1
        if next_idx >= len(self._model_cascade):
            return False
        self._model_index = next_idx
        self.model_name = self._model_cascade[self._model_index]
        self._set_thread_model(self.model_name, self._model_index)
        extra = f" ({reason})" if reason else ""
        print(f"    [*] مدل بعدی: {self.model_name} "
              f"[{self._model_index + 1}/{len(self._model_cascade)}]{extra}")
        return True

    def _reset_model_cascade(self, reason: str = "") -> None:
        banned = getattr(self, "_model_banned", set())
        _head_dead = bool(self._model_cascade) \
            and self._model_cascade[0] in banned
        if not self._model_cascade or _head_dead:
            client = getattr(self, "client", None)
            try:
                client = self._thread_client()
            except Exception:
                pass
            rebuilt = self._build_model_cascade(
                getattr(self, "_last_good_model", "") or "",
                client=client,
            )
            _banned = getattr(self, "_model_banned", set())
            _static = [m for m in self._static_fallback_models("gemini-3.5-flash-lite")
                       if m not in _banned] or self._static_fallback_models("gemini-3.5-flash-lite")
            self._model_cascade = rebuilt or _static
        self._model_index = 0
        self.model_name = self._model_cascade[0]
        try:
            self._set_thread_model(self.model_name, 0)
        except Exception:
            pass
        extra = f" ({reason})" if reason else ""
        print(
            f"    [*] ریست cascade مدل → {self.model_name} "
            f"[1/{len(self._model_cascade)}]{extra}"
        )

    def _switch_to_next_key(self, reason: str = "", cycle: bool = False) -> bool:

        if not self._api_keys:
            return False
        next_idx = self._key_index + 1
        if next_idx >= len(self._api_keys):
            if cycle and len(self._api_keys) > 1:
                next_idx = 0
            else:
                return False
        self._key_index = next_idx
        key = self._api_keys[self._key_index]
        self._apply_api_key(key)

        extra = f" ({reason})" if reason else ""
        print(f"    [*] کلید API شماره {self._key_index + 1}/{len(self._api_keys)} فعال شد"
              f" | مدل فعلی: {self.model_name}{extra}.")
        return True

    def _remove_current_key_and_switch(self, reason: str = "") -> bool:
        if not self._api_keys:
            return False
        bad_key = self._api_keys[self._key_index]
        masked = self._mask_key(bad_key)
        print(f"    [!] کلید فعلی ({masked}) حذف شد. دلیل: {reason or 'نامعتبر/بن'}")
        del self._api_keys[self._key_index]
        if not self._api_keys:
            return False
        if self._key_index >= len(self._api_keys):
            self._key_index = 0
        key = self._api_keys[self._key_index]
        self._apply_api_key(key)
        print(f"    [*] کلید API شماره {self._key_index + 1}/{len(self._api_keys)} فعال شد.")
        return True

    def _apply_api_key(self, key: str) -> None:
        timeout_s = float(getattr(self, "api_timeout", 30.0) or 30.0)
        if not hasattr(self, "_client_cache"):
            self._client_cache = {}
        cache_key = (self.provider_type, key, int(timeout_s))
        if self.provider_type == "gemini":
            client = self._client_cache.get(cache_key)
            if client is None:
                try:
                    http_opts = None
                    if genai_types is not None and hasattr(genai_types, "HttpOptions"):
                        http_opts = genai_types.HttpOptions(timeout=int(timeout_s * 1000))
                    if http_opts is not None:
                        client = genai.Client(api_key=key, http_options=http_opts)
                    else:
                        client = genai.Client(
                            api_key=key,
                            http_options={"timeout": int(timeout_s * 1000)},
                        )
                except Exception:
                    client = genai.Client(api_key=key)
                self._client_cache[cache_key] = client
            self.client = client
            tls = getattr(self, "_tls", None)
            if tls is not None:
                tls.client = client
                tls.api_key = key
        else:
            oc = self._client_cache.get(cache_key)
            if oc is None:
                oc = OpenAI(
                    api_key=key,
                    base_url=self.api_base,
                    timeout=timeout_s,
                )
                self._client_cache[cache_key] = oc
            self.openai_client = oc
            tls = getattr(self, "_tls", None)
            if tls is not None:
                tls.openai_client = oc
                tls.api_key = key

    def _thread_client(self):

        tls = getattr(self, "_tls", None)
        if tls is not None and getattr(tls, "client", None) is not None:
            return tls.client
        return self.client

    def _thread_openai(self):
        tls = getattr(self, "_tls", None)
        if tls is not None and getattr(tls, "openai_client", None) is not None:
            return tls.openai_client
        return self.openai_client

    def _thread_model(self) -> str:
        tls = getattr(self, "_tls", None)
        if tls is not None and getattr(tls, "model_name", None):
            return tls.model_name
        return self.model_name

    def _set_thread_model(self, name: str, index: int | None = None) -> None:
        tls = getattr(self, "_tls", None)
        if tls is not None:
            tls.model_name = name
            if index is not None:
                tls.model_index = index
        self.model_name = name
        if index is not None:
            self._model_index = index

    def _pace_before_gemini_call(self) -> None:
        try:
            now = time.monotonic()
            wait = 0.0
            with self._pace_lock:
                hist = [t for t in self._fire_times if now - t < 60.0]
                self._fire_times = hist
                budget = self._global_min_interval()
                max_burst = max(1, int(round(60.0 / budget)))
                if len(hist) >= max_burst:
                    wait = max(0.0, budget - (now - hist[0]))
                self._fire_times.append(now + wait)
            if wait > 0:
                time.sleep(min(wait + 0.05, 30.0))
        except Exception:
            pass

    def _global_min_interval(self) -> float:
        n_keys = max(1, len(getattr(self, "_api_keys", []) or [1]))
        per_key = float(getattr(self, "gemini_rpm_budget", 8) or 8)
        return 60.0 / max(1.0, per_key * n_keys)

    @staticmethod
    def _quota_retry_delay(err: Exception) -> float:
        try:
            s = str(err)
            m = re.search(r"retryDelay['\"]?\s*[:=]\s*['\"]?(\d+(?:\.\d+)?)\s*s", s)
            if m:
                return float(m.group(1))
            m = re.search(r"[Rr]etry-[Aa]fter['\"]?\s*[:=]\s*['\"]?(\d+)", s)
            if m:
                return float(m.group(1))
            m = re.search(r"(\d+(?:\.\d+)?)\s*s(?:econds?)?\s+(?:until|before)", s)
            if m:
                return float(m.group(1))
        except Exception:
            pass
        return 0.0

    @staticmethod
    def _is_daily_quota_error(err: Exception) -> bool:
        s = str(err or "")
        return ("PerDay" in s
                or "GenerateRequestsPerDay" in s
                or "GenerateContentDaily" in s
                or "requests per day" in s.lower()
                or "daily" in s.lower() and "quota" in s.lower())

    def _current_api_key(self) -> str:
        key = getattr(self, "_tls", None) and getattr(self._tls, "api_key", None)
        if key:
            return key
        if 0 <= self._key_index < len(self._api_keys):
            return self._api_keys[self._key_index]
        return ""

    def _mark_key_cooldown(self, err: Exception) -> float:
        try:
            d = self._quota_retry_delay(err)
            if d >= 15.0:
                key = getattr(self, "_tls", None) and getattr(self._tls, "api_key", None)
                if key:
                    with self._pace_lock:
                        self._key_cooldown_until[key] = time.monotonic() + min(d + 2.0, 300.0)
                    print(f"    [*] کلید فعلی تا {d:.0f}s استراحت می‌کند (retryDelay گوگل).")
            return d
        except Exception:
            return 0.0

    def _pick_random_api_key(self, *, reason: str = "صفحه جدید") -> None:

        if not self._api_keys:
            return
        if len(self._api_keys) == 1:
            self._apply_api_key(self._api_keys[0])
            return

        now = time.monotonic()
        ok_idx = [i for i, k in enumerate(self._api_keys)
                  if now >= self._key_cooldown_until.get(k, 0.0)]
        pool = ok_idx or list(range(len(self._api_keys)))
        idx = random.choice(pool)
        key = self._api_keys[idx]
        self._key_index = idx
        self._apply_api_key(key)
        cd = "" if ok_idx else " (همه در استراحت)"
        print(f"    [*] کلید تصادفی {idx + 1}/{len(self._api_keys)} "
              f"({reason}) | {self._mask_key(key)}{cd}")

    def _ocr_lang_flags(self):

        langs = [str(x).lower().strip() for x in (getattr(self, "ocr_langs", None) or ["en"])]
        if "multi" in langs:
            return True, True, True, True
        allow_en = any(l == "en" or l.startswith("en") for l in langs)
        allow_ko = any(l == "ko" or l.startswith("ko") or l in ("korean", "hangul") for l in langs)
        allow_ja = any(l == "ja" or l.startswith("ja") or l in ("jp", "japanese") for l in langs)
        allow_zh = any(l in ("zh", "ch", "cn", "chinese") or l.startswith("zh") for l in langs)

        if langs == ["en"] or (len(langs) == 1 and langs[0].startswith("en")):
            allow_ko = allow_ja = allow_zh = False
            allow_en = True
        return allow_en, allow_ko, allow_ja, allow_zh
