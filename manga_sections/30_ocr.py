# BUILD-STRIP-START
# BUILD-STRIP-END
def _cjk_dominant(t: str) -> bool:
    try:
        _cjk = 0
        _lat = 0
        for _c in t:
            if "\u2e80" <= _c <= "\u9fff" or "\uf900" <= _c <= "\ufaff" \
                    or "\uff00" <= _c <= "\uffef":
                _cjk += 1
            elif _c.isascii() and _c.isalpha():
                _lat += 1
        if _cjk == 0:
            return False
        return _cjk >= max(2, _lat)
    except Exception:
        return False


_MOBILE_LANG_MAP = {
    "en": "latin", "latin": "latin", "english": "latin", "fa": "latin",
    "korean": "ko", "ko": "ko",
    "japan": "ja", "ja": "ja", "japanese": "ja",
    "ch": "zh", "zh": "zh", "chinese": "zh", "ch_sim": "zh",
    "zh_hans": "zh", "zh_hant": "zh", "zh-tw": "zh", "zh_tw": "zh",
    "multi": "multi",
}

def _mobile_lang(lang):
    return _MOBILE_LANG_MAP.get(str(lang or "en").lower(), "latin")

_PAD_STATS = {"ms": 0.0, "n": 0, "lines": 0}

def _pad_stats_note(t0, nlines):
    try:
        _PAD_STATS["ms"] += (time.time() - t0) * 1000.0
        _PAD_STATS["n"] += 1
        _PAD_STATS["lines"] += int(nlines or 0)
        if _PAD_STATS["n"] % 8 == 0:
            print(f"[⚡] پدلِ اندروید: {_PAD_STATS['n']} OCR | "
                  f"مجموعِ {_PAD_STATS['ms'] / 1000.0:.1f}s | "
                  f"میانگینِ {_PAD_STATS['ms'] / max(1, _PAD_STATS['n']):.0f}ms | "
                  f"{_PAD_STATS['lines']} خط")
    except Exception:
        pass

class PaddleAndroidOCR:

    def __init__(self, lang: str = "en"):
        try:
            from java import jclass
            self._bridge = jclass(
                "com.amirwolf.mangatranslator.PaddleOcrBridge")
        except Exception as e:
            raise RuntimeError(
                "پلِ PaddleOcrBridge در APKِ نصب‌شده نیست — APKِ جدید "
                " را نصب کن: " + str(e)[:90])
        self.lang = _mobile_lang(lang)
        self.debug = True
        self._multi_pref = None
        self._multi_ko_logged = False
        try:
            from java import jclass as _jc, dynamic_proxy as _dp

            class _PyDlSink(_dp(_jc("com.paddle.ocr.util.OcrProgressSink"))):
                def onProgress(self, line):
                    try:
                        print(str(line))
                    except Exception:
                        pass

            _jc("com.amirwolf.mangatranslator.OcrModelStore"
                ).setProgressSink(_PyDlSink())
        except Exception:
            pass
        try:
            _cpu_n = os.cpu_count() or 4
        except Exception:
            _cpu_n = 4
        _intra = 4 if _cpu_n > 4 else 2
        try:
            _env_th = int(os.environ.get("MANGA_OCR_THREADS", "0") or 0)
            if _env_th > 0:
                _intra = _env_th
        except Exception:
            pass
        try:
            _ok_init = bool(self._bridge.init(_intra, str(self.lang or "en")))
        except TypeError:
            _ok_init = bool(self._bridge.init(_intra))
        if not _ok_init:
            raise RuntimeError(
                "initِ PaddleOcrBridge ناموفق بود (RapidOCR/APK/دانلودِ مدل؟)")
        try:
            _img = np.full((64, 64, 3), 255, dtype=np.uint8)
            _ok, _buf = cv2.imencode(".png", _img)
            _out = self._bridge.recognizeAuto(
                bytes(_buf.tobytes()), self.lang, 1, 1)
            if not _out or not str(_out[0]).startswith("META"):
                raise RuntimeError(
                    "خروجیِ سلف‌تستِ RapidOCRِ اندروید نامعتبر است: "
                    + str([str(x)[:80] for x in (_out or [])])[:200])
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(
                "سلف‌تستِ پلِ RapidOCRِ اندروید مردود شد: "
                + str(e)[:90])
        print(f"[+] OCR گوشی: RapidOCRِ اندروید آماده | "
              f"RapidOcrAndroidOnnx | det=PP-OCRv6_small "
              f"cls=v2.0_cls rec=PP-OCRv6_medium/{self.lang} "
              f"(دانلودی) | threads={_intra}")

    _MULTI_CONF_FLOOR = 0.72

    def _call_auto(self, buf, lang):
        try:
            return self._bridge.recognizeAuto(bytes(buf), lang, 1, 1)
        except Exception as e:
            print(f"[!] خطایِ پدلِ اندروید: {str(e)[:140]}")
            return None

    @staticmethod
    def _meta_score(out):
        texts, confs = [], []
        for item in (out or []):
            s = str(item)
            if s.startswith(("META", "ERR")):
                continue
            parts = s.split("|", 4)
            if len(parts) < 5:
                continue
            try:
                conf = float(parts[1])
            except Exception:
                continue
            txt = parts[3].strip()
            if not txt or conf < 0.25:
                continue
            texts.append(txt)
            confs.append(conf)
        return texts, (sum(confs) / len(confs) if confs else 0.0)

    def _ocr_multi(self, buf):
        if self._multi_pref == "ko":
            out_a = self._call_auto(buf, "ko")
            ta, ca = self._meta_score(out_a)
            if ta and ca >= self._MULTI_CONF_FLOOR \
                    and not str((out_a or [""])[0]).startswith("ERR"):
                return out_a
            out_b = self._call_auto(buf, "multi")
            tb, cb = self._meta_score(out_b)
            if tb and cb > ca + 0.02 \
                    and not str((out_b or [""])[0]).startswith("ERR"):
                self._multi_pref = None
                return out_b
            if ta:
                return out_a
            self._multi_pref = None
            return out_b if tb else out_a
        out1 = self._call_auto(buf, "multi")
        t1, c1 = self._meta_score(out1)
        if (t1 and c1 >= self._MULTI_CONF_FLOOR) \
                or str((out1 or [""])[0]).startswith("ERR"):
            return out1
        out2 = self._call_auto(buf, "ko")
        t2, c2 = self._meta_score(out2)
        if out2 and t2 and c2 > c1 + 0.02 \
                and not str(out2[0]).startswith("ERR"):
            if not self._multi_ko_logged:
                self._multi_ko_logged = True
                print("[*] چندزبانه: متنِ کره‌ای شناخته شد → recِ کره‌ای "
                      "(مدلِ ~۱۳.۵MB فقط بار اول دانلود شد)")
            self._multi_pref = "ko"
            return out2
        return out1 if t1 else (out2 if t2 else out1)

    def ocr(self, image_bgr, crop_mode: bool = False):
        if image_bgr is None or getattr(image_bgr, "size", 0) == 0:
            return None
        _t0 = time.time()
        try:
            _ok, _buf = cv2.imencode(
                ".png", np.ascontiguousarray(image_bgr))
            if not _ok:
                return None
            if self.lang == "multi":
                out = self._ocr_multi(_buf.tobytes())
            else:
                out = self._bridge.recognizeAuto(
                    bytes(_buf.tobytes()), self.lang, 1, 1)
        except Exception as e:
            print(f"[!] خطایِ پدلِ اندروید: {str(e)[:140]}")
            return None
        if not out:
            _pad_stats_note(_t0, 0)
            return None
        lines = []
        for item in out:
            s = str(item)
            if s.startswith("META"):
                continue
            parts = s.split("|", 4)
            if len(parts) < 5:
                continue
            try:
                conf = float(parts[1])
            except Exception:
                conf = 1.0
            txt = parts[3].strip()
            if not txt or conf < 0.25:
                continue
            try:
                nums = [float(v) for v in parts[2].split(",")]
                if len(nums) != 8:
                    continue
                box = np.asarray(nums, dtype=np.float32).reshape(4, 2)
            except Exception:
                continue
            lines.append([box, (txt, float(conf))])
        _pad_stats_note(_t0, len(lines))
        return [lines] if lines else None

def _mt_boost_crop(crop_bgr: np.ndarray):
    try:
        h, w = crop_bgr.shape[:2]
    except Exception:
        return crop_bgr, 0, 1.0
    pad = 12
    scale = 1.0
    m = min(h, w)
    if m < 96:
        scale = 3.0
    elif max(h, w) < 480:
        scale = 2.0
    out = cv2.copyMakeBorder(crop_bgr, pad, pad, pad, pad,
                             cv2.BORDER_CONSTANT, value=(255, 255, 255))
    if scale > 1.01:
        out = cv2.resize(out, None, fx=scale, fy=scale,
                         interpolation=cv2.INTER_CUBIC)
    return out, pad, scale

def _mt_map_boxes(lines, pad: float, scale: float):
    out = []
    if pad == 0 and scale == 1.0:
        return lines
    for box, pair in (lines or []):
        try:
            b = np.asarray(box, dtype=np.float32).reshape(-1, 2)
            b = (b - float(pad)) / float(scale)
            out.append([b.astype(np.float32), pair])
        except Exception:
            continue
    return out

_MT_STATS = {"n": 0, "ms": 0.0, "st1": 0, "st2": 0, "st3": 0}

def _mt_stats_note(t0: float, stage: int) -> None:
    try:
        _MT_STATS["n"] += 1
        _MT_STATS["ms"] += (time.time() - t0) * 1000.0
        _MT_STATS[f"st{stage}"] += 1
        if _MT_STATS["n"] % 20 == 0:
            n = _MT_STATS["n"]
            print(f"[⚡] پدلِ اندروید (نردبانِ مرجع): {n} کراپ | "
                  f"رسمی={_MT_STATS['st1']} | "
                  f"میانگینِ {_MT_STATS['ms'] / max(1, n):.0f}ms")
    except Exception:
        pass

class MtLadderOCR:

    _MT_MODES = ("padandroid",)

    def __init__(self, lang: str, build_onnx=None, build_pad=None):
        self._lang = lang
        self._build_onnx = None
        self._build_pad = build_pad
        self._pad = None
        self._pad_tried = False
        self._mode = "padandroid"

    def _engine_pad(self):
        if self._pad_tried:
            return self._pad
        self._pad_tried = True
        if self._build_pad is None:
            return None
        try:
            self._pad = self._build_pad()
        except Exception as e:
            print(f"[!] رپیدِ رسمیِ اندروید آماده نشد: {str(e)[:110]}")
            self._pad = None
        return self._pad

    def ocr(self, image_bgr: np.ndarray, crop_mode: bool = False):
        if image_bgr is None or getattr(image_bgr, "size", 0) == 0:
            return None
        _t0 = time.time()
        if not crop_mode:
            eng0 = self._engine_pad()
            if eng0 is None:
                _mt_stats_note(_t0, 1)
                return None
            try:
                return eng0.ocr(image_bgr)
            except Exception as e:
                print(f"[!] رپیدِ رسمیِ اندروید خطا داد: {str(e)[:110]}")
                _mt_stats_note(_t0, 1)
                return None

        eng0 = self._engine_pad()
        if eng0 is None:
            _mt_stats_note(_t0, 1)
            return None
        try:
            boosted, pad, scale = _mt_boost_crop(image_bgr)
            r0 = eng0.ocr(boosted)
            lines1 = _mt_map_boxes(r0[0], pad, scale) \
                if r0 and r0[0] else []
        except Exception as e:
            print(f"[!] رپیدِ رسمیِ اندروید خطا داد: {str(e)[:110]}")
            lines1 = []
        _mt_stats_note(_t0, 1)
        return [lines1] if lines1 else None



_MT_MODE_FA = {
    "padandroid": "رپیدِ رسمیِ اندروید",
}

_MT_PURGE_EXTRA = ("PP-OCRv6_det_small.int8.onnx",)
_PURGE_MARKER = ".onnx_loser_models_purged"

def _purge_loser_onnx_models() -> str:
    try:
        if not _android_gate("MANGA_PURGE_ONNX_MODELS"):
            return ""
        _mdir = os.path.join(
            os.environ.get("MANGA_FILES_DIR") or os.getcwd(),
            "rapidocr_models")
        if not os.path.isdir(_mdir):
            return ""
        _mk = os.path.join(_mdir, _PURGE_MARKER)
        if os.path.isfile(_mk):
            return ""
        _names = set(_RAPIDOCR_FILES) | set(_MT_PURGE_EXTRA)
        _keep = ()
        _freed = 0
        _n = 0
        for _fn in sorted(os.listdir(_mdir)):
            _fp = os.path.join(_mdir, _fn)
            if not os.path.isfile(_fp):
                continue
            if _fn in _keep:
                continue
            if _fn in _names or _fn.endswith(".part") \
                    or _fn.endswith(".part.url"):
                try:
                    _freed += os.path.getsize(_fp)
                    os.remove(_fp)
                    _n += 1
                except Exception:
                    pass
        try:
            with open(_mk, "w", encoding="utf-8") as _f:
                _f.write("purged at %s (APP_VER %s)\n"
                         % (time.strftime("%Y-%m-%d %H:%M"), APP_VER))
        except Exception:
            pass
        if _n:
            print("[🧹] %d فایلِ مدلِ بازنده (%s) از گوشی حذف شد"
                  % (_n, _fmt_mb(_freed)))
            return ("مدلهایِ بازنده حذف شد: %d فایل / %s آزاد شد — "
                    "روشِ فعال = RapidOCRِ اندروید"
                    % (_n, _fmt_mb(_freed)))
        return ""
    except Exception:
        return ""

def speed_lab_env(p: dict) -> str:
    try:
        for _k in ("MANGA_OCR_THREADS", "MANGA_XNN_THREADS",
                   "MANGA_CROP_DET_CAP", "MANGA_CROP_ENH_SCALE"):
            os.environ.pop(_k, None)

        os.environ.pop("MANGA_MOBILE_OCR_EP", None)
        _w = speed_test_load()
        _lad = "padandroid"
        os.environ["MANGA_MT_MODE"] = "padandroid"
        _ms_l = ""
        try:
            _lm = (_w or {}).get("ladder_ms") or {}
            if _lm.get(_lad):
                _ms_l = " (%.0fms/کراپ — تستِ %s)" % (float(_lm[_lad]),
                                                    str((_w or {}).get("ts") or "?"))
        except Exception:
            _ms_l = ""

        _purge = _purge_loser_onnx_models()

        for _k in ("n", "ms", "st1", "st2", "st3"):
            _MT_STATS[_k] = 0 if _k != "ms" else 0.0
        for _k in ("ms", "n", "lines"):
            _PAD_STATS[_k] = 0 if _k != "ms" else 0.0

        if _purge:
            return ("[⚡] روشِ استخراج: RapidOCRِ اندروید — "
                    "PP-OCRv6ِ دانلودی (%s)%s | v%s: %s"
                    % (_MT_MODE_FA.get(_lad, _lad), _ms_l,
                       APP_VER, _purge))
        return ("[⚡] روشِ استخراج: RapidOCRِ اندروید — "
                "PP-OCRv6ِ دانلودی (det=small + rec=MEDIUM — "
                "بدونِ باندل؛ اگ نباشد دانلود میشود — "
                "v%s)%s"
                % (APP_VER, _ms_l))
    except Exception:
        return ""


_SPEED_TEST_FILE = "speed_test.json"

def _speed_test_path() -> str:
    return os.path.join(os.environ.get("MANGA_FILES_DIR") or os.getcwd(),
                        _SPEED_TEST_FILE)

def speed_test_load():
    try:
        with open(_speed_test_path(), "r", encoding="utf-8") as _f:
            _d = json.loads(_f.read() or "{}")
        if isinstance(_d, dict) and str(_d.get("ladder") or ""):
            return _d
    except Exception:
        pass
    return None

def _speed_test_save(d: dict) -> None:
    try:
        with open(_speed_test_path(), "w", encoding="utf-8") as _f:
            json.dump(d, _f, ensure_ascii=False, indent=2)
    except Exception as _e:
        print(f"[!] ذخیرهٔ نتیجهٔ «تستِ سرعت» ناموفق: {str(_e)[:120]}")

def _speed_test_pool(page, det0, cap: int = 24):
    try:
        _boxes = []
        for _item in (det0 or []):
            try:
                if not (isinstance(_item, (list, tuple)) and _item):
                    continue
                _b = np.asarray(_item[0], dtype=np.float32).reshape(-1, 2)
                _x, _y, _w, _h = cv2.boundingRect(_b.astype(np.int32))
                if _w < 8 or _h < 8:
                    continue
                _boxes.append((_w * _h, _x, _y, _w, _h))
            except Exception:
                continue
        if not _boxes:
            return []
        _boxes.sort(key=lambda t: -t[0])
        _H, _W = page.shape[:2]
        _out = []
        for _a, _x, _y, _w, _h in _boxes[:cap]:
            _x0, _y0 = max(0, _x), max(0, _y)
            _x1, _y1 = min(_W, _x + _w), min(_H, _y + _h)
            if _x1 - _x0 < 8 or _y1 - _y0 < 8:
                continue
            _out.append(page[_y0:_y1, _x0:_x1].copy())
        return _out
    except Exception:
        return []

def _speed_test_tiles(page, cap: int = 24):
    try:
        _H, _W = page.shape[:2]
        if not _H or not _W:
            return []
        _side = 512.0
        _ny = max(1, min(6, int(round(_H / _side)) or 1))
        _nx = max(1, min(6, int(round(_W / _side)) or 1))
        while _nx * _ny > cap:
            if _nx >= _ny and _nx > 1:
                _nx -= 1
            elif _ny > 1:
                _ny -= 1
            else:
                break
        _out = []
        for _iy in range(_ny):
            for _ix in range(_nx):
                _y0, _y1 = (_H * _iy) // _ny, (_H * (_iy + 1)) // _ny
                _x0, _x1 = (_W * _ix) // _nx, (_W * (_ix + 1)) // _nx
                if _y1 - _y0 < 64 or _x1 - _x0 < 64:
                    continue
                _out.append(page[_y0:_y1, _x0:_x1].copy())
        return _out[:cap]
    except Exception:
        return []

def _speed_test_window(runner, pool, per_mode, should_stop=None):
    _n, _tsum, _err = 0, 0.0, None
    try:
        runner(pool[0])
    except Exception as _e:
        return 0, 0.0, str(_e), False
    _t0 = time.time()
    _stopped = False
    while (time.time() - _t0) < per_mode:
        for _crop in pool:
            if should_stop is not None and should_stop():
                _stopped = True
                break
            _t1 = time.time()
            try:
                runner(_crop)
            except Exception as _e:
                _err = str(_e)
                break
            _tsum += time.time() - _t1
            _n += 1
            if (time.time() - _t0) >= per_mode:
                break
        if _err or _stopped:
            break
    return _n, _tsum, _err, _stopped

def speed_test_run(src, langs=("en",), per_mode=60.0, log=print,
                   should_stop=None, backend=None):
    try:
        per_mode = max(5.0, float(per_mode or 60.0))
    except Exception:
        per_mode = 60.0
    lang = (langs[0] if langs else "en") or "en"
    _modes = tuple(MtLadderOCR._MT_MODES)
    log("[⚡] تستِ سرعتِ استخراج: %d روش (%s) × %d ثانیه"
        % (len(_modes),
           " + ".join(_MT_MODE_FA.get(_m, _m) for _m in _modes),
           int(per_mode)))
    log("[⚡] در این حالت ترجمه انجام نمیشود — فقط استخراجِ متن "
        "اندازهگیری میشود؛ لطفاً برنامه را باز نگه دار…")
    _t_all = time.time()
    try:
        page = MangaTranslator._imread_any(src)
    except Exception as _e:
        log("[!] تصویر ورودی باز نشد: %s" % str(_e)[:140])
        return None
    if page is None or getattr(page, "size", 0) == 0:
        log("[!] تصویر ورودی باز نشد (%s)" % os.path.basename(str(src or "")))
        return None
    try:
        be = backend if backend is not None else RapidOCRBackend(lang=lang)
    except Exception as _e:
        log("[!] موتورِ OCR ساخته نشد: %s" % str(_e)[:140])
        return None
    _lad0 = getattr(be, "_mobile", None)
    if not isinstance(_lad0, MtLadderOCR):
        log("[!] «تستِ سرعت» رویِ نردبانِ مرجع کار میکند — این دستگاه "
            "نردبان ندارد (PC/موتورِ دیگر). از اپِ گوشی تست کن.")
        return None

    _prev = speed_test_load() or {}
    _nnapi_pending = bool(_prev.get("nnapi_pending"))

    try:
        _padbe = be._build_paddle_android(lang)
    except Exception:
        _padbe = None

    log("[⚡] استخرِ کراپهایِ واقعی از تصویر…")
    _res0 = None
    if _padbe is not None:
        try:
            _res0 = _padbe.ocr(page, crop_mode=False)
        except Exception as _e:
            _res0 = None
            log("[!] تشخیصِ تمامصفحه خطا داد: %s" % str(_e)[:140])
    pool = _speed_test_pool(page, _res0)
    if not pool:
        pool = _speed_test_tiles(page)
        log("[⚡] تشخیصِ تمامصفحه چیزی ندید — با %d کاشیِ واقعیِ خودِ "
            "صفحه ادامه میدهیم؛ همهٔ روشها اندازهگیری میشوند." % len(pool))
    if not pool:
        log("[!] تصویر خیلی ریز/خالی است — یک صفحهٔ بزرگتر امتحان کن.")
        return None
    log("[⚡] %d کراپِ آماده — پنجرهها شروع میشوند…" % len(pool))

    _res = {"app": APP_VER,
            "ts": time.strftime("%Y-%m-%d %H:%M"),
            "per_mode": int(per_mode), "crops": len(pool),
            "ladder": str(_prev.get("ladder") or "full"),
            "ep": str(_prev.get("ep") or "auto"),
            "ladder_ms": {}, "ep_ms": {},
            "ladder_n": {}, "ep_n": {},
            "nnapi_pending": False}
    _total = len(_modes)
    _wi = 0

    for _mode in _modes:
        _wi += 1
        _need_ok = {"padandroid": _padbe is not None}[_mode]
        if not _need_ok:
            _res["ladder_ms"][_mode] = None
            log("[⚡] (%d/%d) روشِ %s (%s) → رد شد (موتورش رویِ این دستگاه آماده نیست)"
                % (_wi, _total, _MT_MODE_FA.get(_mode, _mode), _mode))
            continue
        os.environ["MANGA_MT_MODE"] = _mode
        try:
            _lad = MtLadderOCR(lang, build_pad=lambda: _padbe)
        except Exception as _e:
            _res["ladder_ms"][_mode] = None
            log("[⚡] (%d/%d) روشِ %s (%s) → نردبان ساخته نشد: %s"
                % (_wi, _total, _MT_MODE_FA.get(_mode, _mode), _mode,
                   str(_e)[:100]))
            continue
        _n, _ts, _err, _stp = _speed_test_window(
            lambda c, _l=_lad: _l.ocr(c, crop_mode=True),
            pool, per_mode, should_stop=should_stop)
        _ms = (_ts * 1000.0 / _n) if _n else None
        _res["ladder_ms"][_mode] = _ms
        _res["ladder_n"][_mode] = _n
        if _err:
            log("[⚡] (%d/%d) روشِ %s (%s) → خطا: %s"
                % (_wi, _total, _MT_MODE_FA.get(_mode, _mode), _mode,
                   str(_err)[:100]))
        elif _stp:
            log("[⚡] (%d/%d) روشِ %s (%s) → متوقف شد (%d کراپ)"
                % (_wi, _total, _MT_MODE_FA.get(_mode, _mode), _mode, _n))
            _speed_test_save(_res)
            return _res
        else:
            log("[⚡] (%d/%d) روشِ %s (%s) → %d کراپ | میانگینِ %.0fms/کراپ"
                % (_wi, _total, _MT_MODE_FA.get(_mode, _mode), _mode,
                   _n, _ms))
        _speed_test_save(_res)


    _ok_l = {k: v for k, v in _res["ladder_ms"].items() if v}
    _ok_e = {k: v for k, v in _res["ep_ms"].items() if v}
    if not _ok_l and not _ok_e:
        log("[!] هیچ پنجرهٔ سالمی تمام نشد — نتیجه‌ای ذخیره نشد.")
        return None
    _best_l = min(_ok_l, key=_ok_l.get) if _ok_l else \
        str(_prev.get("ladder") or "full")
    _best_e = min(_ok_e, key=_ok_e.get) if _ok_e else \
        str(_prev.get("ep") or "auto")
    _res["ladder"], _res["ep"] = _best_l, _best_e
    _res["seconds"] = int(time.time() - _t_all)
    _speed_test_save(_res)
    _tbl = " | ".join("%s(%s)=%.0fms" % (_MT_MODE_FA.get(k, k), k, v)
                      for k, v in sorted(_ok_l.items(), key=lambda kv: kv[1]))
    log("[⚡] جدولِ روشها (سریع → کند): %s" % (_tbl or "—"))
    log("[⚡] شتاب‌دهندهٔ جداگانه ندارد — RapidOCR رویِ CPU با "
        "EngineConfig.numThreads اجرا میشود.")
    log("[⚡] برنده: روشِ %s (%s؛ %s) → ذخیره شد (تنها روش — "
        "شتاب‌دهندهٔ جداگانه ندارد)."
        % (_MT_MODE_FA.get(_best_l, _best_l), _best_l,
           ("%.0fms/کراپ" % _ok_l[_best_l]) if _best_l in _ok_l else "—"))
    try:
        log("[⚡] کلِ تست: %d دقیقه و %d ثانیه"
            % (_res["seconds"] // 60, _res["seconds"] % 60))
    except Exception:
        pass
    return _res

def _mt_speed_report() -> str:
    try:
        _n = int(_MT_STATS.get("n") or 0)
        if _n <= 0:
            return ""
        _ms = float(_MT_STATS.get("ms") or 0.0)
        _out = ("[🧪] گزارشِ سرعتِ استخراج: %d کراپ | میانگینِ %.0fms | "
                "رسمی=%d"
                % (_n, _ms / max(1, _n), int(_MT_STATS.get("st1") or 0)))
        try:
            _pn = int(_PAD_STATS.get("n") or 0)
            if _pn > 0:
                _out += (" | رپیدِ رسمیِ تنهایی: میانگینِ %.0fms"
                         % (float(_PAD_STATS.get("ms") or 0.0) / _pn))
        except Exception:
            pass
        try:
            _lad = str(os.environ.get("MANGA_MT_MODE", "") or "").strip().lower()
            _out += " | روش=%s" % (_lad if _lad else "padandroid")
        except Exception:
            pass
        return _out
    except Exception:
        return ""

_RAPIDOCR_RECOVER_LOCK = threading.Lock()

class RapidOCRBackend:

    def __init__(self, lang: str = "en", prefer_gpu: Optional[bool] = None):
        self.lang = lang
        self._new_api = False
        self._mobile = None
        try:
            self._cjk_guard = _android_gate("MANGA_CJK_GUARD") and \
                str(lang).lower() in ("en", "latin", "english")
        except Exception:
            self._cjk_guard = False
        if _IS_ANDROID:
            self._init_mobile_engine(lang)
            return
        self._prefer_gpu = prefer_gpu
        try:
            if not _ensure_rapidocr_pkg():
                raise ImportError("rapidocr نصب نیست و نصب خودکار ناموفق بود")
            from rapidocr import RapidOCR as NewRapidOCR
            try:
                import logging as _lg

                class _QuietRapidOCR(_lg.Filter):
                    def filter(self, rec):
                        return rec.levelno >= _lg.ERROR

                for _ln in ("RapidOCR", "rapidocr"):
                    _lg.getLogger(_ln).addFilter(_QuietRapidOCR())
                    _lg.getLogger(_ln).propagate = False
            except Exception:
                pass
            _low = str(lang).lower()
            _rec_params = None
            if _low in ("korean", "ko"):
                try:
                    from rapidocr import OCRVersion as _OV, ModelType as _MT, LangRec as _LR
                    _rec_params = {
                        "Rec.lang_type": getattr(_LR, "KOREAN", _LR.KOREAN),
                        "Rec.ocr_version": _OV.PPOCRV5,
                        "Rec.model_type": _MT.MOBILE,
                    }
                except Exception as e:
                    print(f"[!] پیکربندی مدل کره‌ای RapidOCR نشد ({e}) → مدل پیش‌فرض")
            elif _low in ("japan", "ja", "japanese"):
                try:
                    from rapidocr import OCRVersion as _OV, ModelType as _MT, LangRec as _LR
                    _japan = getattr(_LR, "JAPAN", None)
                    if _japan is not None:
                        _rec_params = {
                            "Rec.lang_type": _japan,
                            "Rec.ocr_version": _OV.PPOCRV4,
                            "Rec.model_type": _MT.MOBILE,
                        }
                    else:
                        print("[!] LangRec.JAPAN در rapidocr نیست → مدل پیش‌فرض")
                except Exception as e:
                    print(f"[!] پیکربندی مدل ژاپنی RapidOCR نشد ({e}) → مدل پیش‌فرض")
            import os as _os
            _mdir = _os.path.join(
                _os.environ.get("MANGA_FILES_DIR") or _os.getcwd(),
                "rapidocr_models")
            try:
                _os.makedirs(_mdir, exist_ok=True)
            except Exception:
                _mdir = None
            _base = {"Global.model_root_dir": _mdir} if _mdir else {}
            if _mdir:
                try:
                    _det_n, _rec_n = _rapidocr_model_pair(
                        lang, small=_pc_ocr_small())
                    _ensure_rapidocr_models(_mdir,
                                            files=[_det_n, _rec_n])
                except Exception as _e:
                    print(f"[!] پیش‌دانلود مدل‌ها ناموفق: {_e}")
            _gpu_flags = {}
            if _mdir:
                try:
                    _det_n, _rec_n = _rapidocr_model_pair(
                        lang, small=_pc_ocr_small())
                    for _sec, _fn in (
                            ("Det", _det_n),
                            ("Rec", _rec_n),
                            ("Cls", "ch_ppocr_mobile_v2.0_cls_mobile.onnx")):
                        _mp = _os.path.join(_mdir, _fn)
                        if _os.path.isfile(_mp) \
                                and _os.path.getsize(_mp) > 100_000:
                            _base[f"{_sec}.model_path"] = _mp
                    if _rec_n in ("PP-OCRv6_medium_rec_onnx.onnx",
                                    "PP-OCRv5_korean_rec.onnx"):
                        _keys = ("ppocrv6_chars.txt"
                                   if _rec_n.startswith("PP-OCRv6")
                                   else "korean_chars.txt")
                        try:
                            _ensure_rapidocr_models(_mdir, files=[_keys])
                        except Exception:
                            pass
                        _kp = _os.path.join(_mdir, _keys)
                        if _os.path.isfile(_kp) \
                                and _os.path.getsize(_kp) > 100:
                            _base["Rec.rec_keys_path"] = _kp
                except Exception as _e2:
                    print(f"[!] مسیرِ صریحِ مدلِ OCR نشد ({_e2}) → auto")
            try:
                _want = bool(prefer_gpu) and (_ORT_CUDA_OK is not False)
                _ocr_head = (_best_providers_for("ocr", prefer_gpu=_want)
                               or ["CPUExecutionProvider"])[0]
                _ep_active = ""
                if _ocr_head == "CUDAExecutionProvider":
                    _cuda_ok = False
                    try:
                        _detn = ""
                        try:
                            _detn = _det_n
                        except Exception:
                            _detn = ""
                        _probe_p = _os.path.join(_mdir or "", _detn or "")
                        if _os.path.isfile(_probe_p):
                            _ps = ort.InferenceSession(
                                _probe_p,
                                providers=["CUDAExecutionProvider",
                                           "CPUExecutionProvider"])
                            _cuda_ok = (
                                _ps.get_providers()[0]
                                == "CUDAExecutionProvider")
                            _ep_active = ",".join(_ps.get_providers())
                    except Exception as _pe:
                        _cuda_ok = False
                        _ep_active = str(_pe)[:90]
                    if _cuda_ok:
                        _gpu_flags["EngineConfig.onnxruntime.use_cuda"] = True
                        _gpu_flags["EngineConfig.onnxruntime.cuda_ep_cfg.cudnn_conv_use_max_workspace"] = "1"
                        _algo_h3 = _cudnn_algo_search()
                        if _algo_h3:
                            _gpu_flags["EngineConfig.onnxruntime.cuda_ep_cfg.cudnn_conv_algo_search"] = _algo_h3
                    else:
                        print(f"[!] CUDA در عمل لود نشد ({_ep_active or 'بدونِ جزئیات'}) "
                              f"→ OCR روی CPU. راه‌حل: pip install "
                              f"'onnxruntime-gpu[cuda,cudnn]==1.26.0'")
                        _ocr_head = "CPUExecutionProvider"
                if _ocr_head == "DmlExecutionProvider":
                    _dml_ok = False
                    try:
                        _probe = []
                        for _nm in (_det_n, _rec_n):
                            try:
                                _p3 = _os.path.join(_mdir or "",
                                                      str(_nm or ""))
                            except Exception:
                                _p3 = ""
                            if _os.path.isfile(_p3) \
                                    and _os.path.getsize(_p3) > 100_000:
                                _probe.append(_p3)
                        _dml_ok = bool(_probe) and all(
                            _dml_probe_model(_p) for _p in _probe)
                    except Exception:
                        _dml_ok = False
                    if _dml_ok:
                        _gpu_flags["EngineConfig.onnxruntime.use_dml"] = True
                        self._dml_locked = True
                    else:
                        print("[!] DirectML در عمل لود نشد (درایور/DirectX را "
                              "آپدیت کن) → OCR روی CPU.")
                        _ocr_head = "CPUExecutionProvider"
                elif _ocr_head == "CoreMLExecutionProvider":
                    _gpu_flags["EngineConfig.onnxruntime.use_coreml"] = True
                if _gpu_flags:
                    _base.update(_gpu_flags)
                    print(f"[*] EPِ OCR: {_ocr_head}")
                self._ocr_ep_active = _ocr_head
            except Exception:
                _gpu_flags = {}
            try:
                import os as _os2
                _cpu_n = _os2.cpu_count() or 4
            except Exception:
                _cpu_n = 4
            try:
                _ocr_th = int(_os2.environ.get("MANGA_OCR_THREADS", "0") or 0)
            except Exception:
                _ocr_th = 0
            try:
                _env_ort_h4 = int(_os2.environ.get("MANGA_ORT_THREADS", "0") or 0)
            except Exception:
                _env_ort_h4 = 0
            _intra = None
            if _ocr_th > 0:
                _intra = max(1, _ocr_th)
            elif _env_ort_h4 > 0:
                _intra = max(1, _env_ort_h4)
            elif _on_android():
                _intra = 1 if _cpu_n <= 4 else 2
            else:
                _intra = 2
            _threads = {
                "EngineConfig.onnxruntime.intra_op_num_threads": int(_intra),
                "EngineConfig.onnxruntime.inter_op_num_threads": 1,
            }
            _det_speed = _ocr_det_resize_policy(lang) or {}
            _det_disp = ""
            if _det_speed:
                _det_disp = (f" | det={_det_speed.get('Det.limit_side_len', 736)}"
                                f"/{_det_speed.get('Det.limit_type', 'min')}")
            _intra_disp = _intra
            self.ocr_threads = int(_intra)
            if _rec_params is not None:
                _p = dict(_rec_params)
                _p.update(_base)
                _p.update(_threads)
                _p.update(_det_speed)
                try:
                    self.engine = NewRapidOCR(params=_p)
                    self._eng_params = _p
                except Exception as _eg:
                    if not _gpu_flags:
                        raise
                    print(f"[!] EPِ GPU برایِ OCR نشد ({str(_eg)[:130]}) → CPU")
                    _p2 = {k: v for k, v in _p.items() if k not in _gpu_flags}
                    self.engine = NewRapidOCR(params=_p2)
                    self._eng_params = _p2
                    self._dml_locked = False
                self._new_api = True
                _ep_disp = (f" | EP={getattr(self, '_ocr_ep_active', '')}"
                               if str(getattr(self, "_ocr_ep_active", "") or "").strip()
                               else "")
                print(f"[+] RapidOCR (ONNX, PP-OCRv5) آماده | lang={lang} | threads={_intra_disp}{_ep_disp}{_det_disp} | cls=خاموش")
                return
            _pb = dict(_base)
            _pb.update(_threads)
            _pb.update(_det_speed)
            try:
                self.engine = NewRapidOCR(params=_pb)
                self._eng_params = _pb
            except Exception as _eg:
                if not _gpu_flags:
                    raise
                print(f"[!] EPِ GPU برایِ OCR نشد ({str(_eg)[:130]}) → CPU")
                _pb2 = {k: v for k, v in _pb.items() if k not in _gpu_flags}
                self.engine = NewRapidOCR(params=_pb2)
                self._eng_params = _pb2
                self._dml_locked = False
            self._new_api = True
            _ep_disp = (f" | EP={getattr(self, '_ocr_ep_active', '')}"
                           if str(getattr(self, "_ocr_ep_active", "") or "").strip()
                           else "")
            print(f"[+] RapidOCR (ONNX, PP-OCRv5/v6) آماده | lang={lang} | threads={_intra_disp}{_ep_disp}{_det_disp} | cls=خاموش")
            return
        except Exception as e:
            import traceback as _tb
            print(f"[!] RapidOCR (API جدید) لود نشد: {e}")
            print("[!] " + _tb.format_exc()[-900:])
        if not _HAS_RAPIDOCR:
            raise ImportError("pip install rapidocr (یا rapidocr-onnxruntime)")
        self.engine = RapidOCR()
        print(f"[+] RapidOCR (ONNX, PP-OCRv3 قدیمی) آماده | lang={lang}")

    def _init_mobile_engine(self, lang: str) -> None:
        _pb = self._build_paddle_android(lang)
        if _pb is not None:
            self._mobile = _pb
            return
        print("[!] RapidOCRِ اندروید آماده نشد — استخراجِ گوشی "
              "خالی میماند (فالبکی نیست)")
        self._mobile = None

    def _build_paddle_android(self, lang: str):
        try:
            return PaddleAndroidOCR(lang)
        except Exception as e:
            print(f"[!] RapidOCRِ اندروید آماده نشد: {str(e)[:130]}")
            return None

    @staticmethod
    def _deaccent(txt: str) -> str:
        try:
            import unicodedata as _ud
            out = _ud.normalize("NFKD", txt)
            out = "".join(ch for ch in out if not _ud.combining(ch))
            return out
        except Exception:
            return txt

    def _det_dbg_engine(self):
        _e = getattr(self, "_det_dbg_eng", None)
        if _e is not None:
            return _e
        if getattr(self, "_det_dbg_tried", False):
            return None
        self._det_dbg_tried = True
        try:
            from rapidocr import RapidOCR as NewRapidOCR
            _p = {}
            for _k, _v in (getattr(self, "_eng_params", None) or {}).items():
                if not str(_k).startswith(("Global.", "Det.", "EngineConfig.")):
                    continue
                if "use_cuda" in _k or "use_dml" in _k or "use_coreml" in _k \
                        or "cuda_ep_cfg" in _k:
                    continue
                _p[_k] = _v
            self._det_dbg_eng = NewRapidOCR(params=_p)
        except Exception as _e2:
            print(f"[!] موتورِ detِ دیباگ ساخته نشد ({str(_e2)[:90]})")
            self._det_dbg_eng = None
        return self._det_dbg_eng

    def det_only(self, image_bgr: np.ndarray) -> List[np.ndarray]:
        if image_bgr is None or getattr(image_bgr, "size", 0) == 0:
            return []
        if not getattr(self, "_new_api", False):
            return []
        if getattr(self, "_mobile", None) is not None:
            return []
        eng = self._det_dbg_engine()
        if eng is None:
            return []
        try:
            out = eng(image_bgr, use_det=True, use_cls=False, use_rec=False)
        except Exception:
            return []
        boxes = getattr(out, "boxes", None)
        if boxes is None:
            return []
        quads: List[np.ndarray] = []
        try:
            for _b in np.asarray(boxes):
                try:
                    _q = np.asarray(_b, dtype=np.float32).reshape(-1, 2)
                    if _q.shape[0] >= 4 and np.ptp(_q[:, 0]) >= 2 \
                            and np.ptp(_q[:, 1]) >= 2:
                        quads.append(_q)
                except Exception:
                    continue
        except Exception:
            return []
        return quads

    def _rec_rescue_engine(self):
        _e = getattr(self, "_rec_rescue_eng", None)
        if _e is not None:
            return _e
        if getattr(self, "_rec_rescue_tried", False):
            return None
        self._rec_rescue_tried = True
        try:
            from rapidocr import RapidOCR as NewRapidOCR
            _p = {}
            for _k, _v in (getattr(self, "_eng_params", None) or {}).items():
                if not str(_k).startswith(("Global.", "Rec.", "EngineConfig.")):
                    continue
                if "use_cuda" in _k or "use_dml" in _k or "use_coreml" in _k \
                        or "cuda_ep_cfg" in _k:
                    continue
                _p[_k] = _v
            self._rec_rescue_eng = NewRapidOCR(params=_p)
        except Exception as _e2:
            print(f"[!] موتورِ recِ نجات ساخته نشد ({str(_e2)[:90]})")
            self._rec_rescue_eng = None
        return self._rec_rescue_eng

    def rec_only(self, image_bgr: np.ndarray):
        if image_bgr is None or getattr(image_bgr, "size", 0) == 0:
            return None
        if not getattr(self, "_new_api", False):
            return None
        if getattr(self, "_mobile", None) is not None:
            return None
        eng = self._rec_rescue_engine()
        if eng is None:
            return None
        try:
            out = eng(image_bgr, use_det=False, use_cls=False,
                      use_rec=True)
        except Exception:
            return None
        try:
            txts = getattr(out, "txts", None)
            scores = getattr(out, "scores", None)
            if txts is None:
                return None
            _t = " ".join(str(t) for t in (txts or [])).strip()
            _s = float(np.mean([float(s) for s in (scores or [0.0])])) \
                if scores is not None else 0.0
            if not _t:
                return None
            return _t, _s
        except Exception:
            return None

    def _engine_run_nolock(self, image_bgr):
        try:
            return self.engine(image_bgr, use_det=True, use_cls=False,
                               use_rec=True)
        except TypeError:
            return self.engine(image_bgr)

    def _engine_run(self, image_bgr):
        if getattr(self, "_dml_locked", False):
            with _DML_RUN_LOCK:
                return self._engine_run_nolock(image_bgr)
        return self._engine_run_nolock(image_bgr)

    def _dml_recover(self, err) -> bool:
        if not getattr(self, "_dml_locked", False):
            return False
        _m = str(err).lower()
        if not any(_s in _m for _s in (
                "887a0006", "80070057", "gpu will not respond",
                "device hung", "device removed", "dml", "directml")):
            return False
        with _RAPIDOCR_RECOVER_LOCK:
            if not getattr(self, "_dml_locked", False):
                return True
            try:
                from rapidocr import RapidOCR as NewRapidOCR
                _p = dict(getattr(self, "_eng_params", None) or {})
                if not _p:
                    return False
                for _k in list(_p.keys()):
                    if _k in ("EngineConfig.onnxruntime.use_cuda",
                                 "EngineConfig.onnxruntime.use_dml",
                                 "EngineConfig.onnxruntime.use_coreml") \
                            or "cuda_ep_cfg" in _k:
                        _p.pop(_k, None)
                self.engine = NewRapidOCR(params=_p)
                self._eng_params = _p
                self._dml_locked = False
                self._ocr_ep_active = "CPUExecutionProvider"
                print("[!] خطایِ GPU در OCR → موتور رویِ CPU بازساخته شد "
                      "(کیفیت حفظ شد؛ بقیهٔ صفحات بدونِ وقفه)")
                return True
            except Exception:
                return False

    def ocr(self, image_bgr: np.ndarray, crop_mode: bool = False):

        if image_bgr is None or image_bgr.size == 0:
            return None
        if self._mobile is not None:
            try:
                _out = self._mobile.ocr(image_bgr, crop_mode=crop_mode)
            except Exception as _e:
                print(f"[!] خطایِ OCRِ موبایل: {str(_e)[:150]}")
                return None
            if not _out or not _out[0]:
                return None
            _lines = []
            _ncjk = 0
            for _box, _pair in _out[0]:
                try:
                    _t = self._deaccent(str(_pair[0])).strip()
                    if not _t:
                        continue
                    if self._cjk_guard and _cjk_dominant(_t):
                        _ncjk += 1
                        continue
                    _s = float(_pair[1])
                    _lines.append([_box, (_t, _s)])
                except Exception:
                    continue
            if _ncjk:
                print(f"    [OCR] {_ncjk} خطِ پر از نویسهٔ چینی حذف شد "
                      "(گاردِ لاتین)")
            return [_lines] if _lines else None
        if self._new_api:
            for _att in range(2):
                try:
                    out = self._engine_run(image_bgr)
                    txts = getattr(out, "txts", None)
                    if not txts:
                        return None
                    boxes = getattr(out, "boxes", None)
                    scores = getattr(out, "scores", None)
                    lines = []
                    for i, t in enumerate(txts):
                        t = self._deaccent(str(t)).strip()
                        if not t:
                            continue
                        score = float(scores[i]) if scores is not None and i < len(scores) else 1.0
                        box = boxes[i] if boxes is not None and i < len(boxes) else [[0, 0], [1, 0], [1, 1], [0, 1]]
                        lines.append([np.asarray(box, dtype=np.float32), (t, score)])
                    return [lines] if lines else None
                except Exception as e:
                    msg = str(e).lower()
                    if "text detection result is empty" in msg or "detection result is empty" in msg:
                        return None
                    if _att == 0 and self._dml_recover(e):
                        continue
                    print(f"    [OCR] rapidocr جدید خطا: {e} → موتور قدیمی")
                    self._new_api = False
                    if not _HAS_RAPIDOCR:
                        return None
                    break
        try:
            result, _ = self._engine_run(image_bgr)
        except Exception as e:
            msg = str(e).lower()
            if "text detection result is empty" in msg or "detection result is empty" in msg:
                return None
            if self._dml_recover(e):
                try:
                    result, _ = self._engine_run(image_bgr)
                except Exception:
                    return None
            else:
                return None
        if not result:
            return None
        lines = []
        for item in result:
            if len(item) < 3:
                continue
            box, text, score = item[0], item[1], item[2]
            text = self._deaccent(str(text)).strip()
            if not text:
                continue
            lines.append([box, (text, float(score))])
        return [lines] if lines else None


def _dual_device_enabled() -> bool:
    try:
        _v = os.environ.get("MANGA_DUAL_DEVICE", "").strip().lower()
        if _v in ("1", "true", "yes", "on"):
            return True
        if _v in ("0", "false", "no", "off"):
            return False
    except Exception:
        pass
    return True

def _gpu_head_of(session):
    try:
        for _p in (session.get_providers() or []):
            if not str(_p).lower().startswith("cpu"):
                return str(_p)
    except Exception:
        pass
    return None

def _android_like_env() -> bool:
    try:
        if os.path.isfile("/system/build.prop"):
            return True
        if os.environ.get("ANDROID_ROOT") or os.environ.get("ANDROID_DATA"):
            return True
        if "android" in (os.uname().release or "").lower():
            return True
    except Exception:
        pass
    return False

def _on_android() -> bool:
    try:
        import java
        return True
    except Exception:
        return False

def _android_gate(env_name: str) -> bool:
    _v = str(os.environ.get(env_name, "") or "").strip().lower()
    if _v in ("1", "true", "yes", "on"):
        return True
    if _v in ("0", "false", "no", "off"):
        return False
    return bool(_on_android())

def _gate_default_on(env_name: str) -> bool:
    return str(os.environ.get(env_name, "") or "").strip().lower() \
        not in ("0", "false", "no", "off")

class PaddleOCRWrapper:

    def __init__(self, engine):
        self.engine = engine

    def ocr(self, image_bgr: np.ndarray):
        try:
            if hasattr(self.engine, "predict"):
                return self.engine.predict(image_bgr)
            return self.engine.ocr(image_bgr)
        except Exception:
            return None
