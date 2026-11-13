# BUILD-STRIP-START
class _MangaTranslatorBody_95:
# BUILD-STRIP-END
    def _cache_jsonable(v):
        import numpy as _np
        if isinstance(v, _np.ndarray):
            return {"__nd": v.tolist(), "dt": str(v.dtype)}
        if isinstance(v, (_np.floating, _np.integer)):
            return float(v)
        if isinstance(v, (list, tuple)):
            return [MangaTranslator._cache_jsonable(x) for x in v]
        if isinstance(v, dict):
            return {str(k): MangaTranslator._cache_jsonable(x)
                    for k, x in v.items()}
        if isinstance(v, (str, int, float, bool)) or v is None:
            return v
        return None

    @staticmethod
    def _region_to_cache(r) -> dict:
        d = {}
        try:
            for k, v in vars(r).items():
                j = MangaTranslator._cache_jsonable(v)
                if j is None and v is not None:
                    continue
                d[k] = j
        except Exception:
            return {}
        return d

    @staticmethod
    def _region_from_cache(d):
        import numpy as _np

        def _und(v):
            def _one(x):
                a = _np.asarray(x["__nd"])
                try:
                    if x.get("dt"):
                        a = a.astype(_np.dtype(str(x["dt"])))
                except Exception:
                    pass
                return a
            if isinstance(v, dict) and "__nd" in v:
                return _one(v)
            if isinstance(v, list) and v and all(
                    isinstance(x, dict) and "__nd" in x for x in v):
                return [_one(x) for x in v]
            return v
        r = TextRegion(id=int(d.get("id", 0) or 0), boxes=[])
        for k, v in d.items():
            try:
                setattr(r, k, _und(v))
            except Exception:
                continue
        def _isarrlist(v):
            return isinstance(v, list) and (
                not v or all(hasattr(x, "shape") for x in v))
        if not _isarrlist(getattr(r, "boxes", None)):
            try:
                r.boxes = [_np.asarray(_und(b), dtype=_np.int32)
                           for b in (d.get("boxes") or [])]
            except Exception:
                r.boxes = []
        if not _isarrlist(getattr(r, "ocr_polys", None)):
            try:
                r.ocr_polys = [_np.asarray(_und(p), dtype=_np.float32)
                               for p in (d.get("ocr_polys") or [])]
            except Exception:
                r.ocr_polys = []
        try:
            if isinstance(getattr(r, "rect", None), list):
                r.rect = tuple(r.rect)
        except Exception:
            pass
        return r

    @staticmethod
    def _cache_dir_for(output_path: str) -> str:
        _p = str(output_path or "")
        root, ext = os.path.splitext(_p)
        if ext.lower() in (".pdf", ".zip", ".html", ".psd",
                           ".webp", ".png", ".jpg", ".jpeg"):
            return root + ".cache"
        return _p + ".cache"

    @staticmethod
    def _trans_sig_of(provider: str, model: str, api_base: str,
                      prompt_mode: str, instruction: str,
                      fake: bool, temperature: float, top_p: float) -> str:
        import hashlib as _hl
        try:
            prov = str(provider or "").strip().lower()
            mdl = str(model or "").strip()
            ab = (str(api_base or "").strip().lower()
                  if prov == "custom" else "")
            pm = str(prompt_mode or "professional").strip().lower() or "professional"
            instr = str(instruction or "").strip()
            parts = [
                "t1", prov, mdl, ab, pm,
                (_hl.sha256(instr.encode("utf-8", "ignore")).hexdigest()[:12]
                 if instr else "-"),
                "fake" if fake else "real",
                "%.2f" % float(temperature if temperature is not None else 0.7),
                "%.2f" % float(top_p if top_p is not None else 0.9),
            ]
            return _hl.sha256("|".join(parts).encode("utf-8", "ignore")).hexdigest()[:16]
        except Exception:
            return ""

    def run(self, input_path: str, output_path: str, resume: bool = True,
            clean_old: bool = True) -> None:
        self._extraction_done = False
        self._independent_pages = False
        _t_run = time.time()
        try:
            self.preload_lama_async()
        except Exception:
            pass
        if clean_old:
            self._cleanup_previous_artifacts(output_path, keep_outputs=False)

        cache_dir = MangaTranslator._cache_dir_for(output_path)
        if not resume:
            shutil.rmtree(cache_dir, ignore_errors=True)

        src_dir = os.path.join(cache_dir, "src")

        def _same_dl(_p: str, _c: bytes) -> bool:
            try:
                if not os.path.isfile(_p) or os.path.getsize(_p) != len(_c):
                    return False
                with open(_p, "rb") as _fh:
                    _old = _fh.read(4096)
                return _old == _c[:len(_old)]
            except Exception:
                return False

        cache_tag = "_safe_v3" if (self.stitch_max_height > 0 or getattr(self, "repair_page_seams", True)) else ""
        def _clean_style_tag() -> str:
            import hashlib as _hl
            try:
                parts = [
                    str(getattr(self, "clean_method", "") or "").strip().lower(),
                    1 if getattr(self, "force_lama", False) else 0,
                    1 if getattr(self, "clean_sfx", False) else 0,
                    int(getattr(self, "mask_padding", 3) or 0),
                    round(float(getattr(self, "pad_ratio", 0.06) or 0), 4),
                    int(getattr(self, "inpaint_radius", 3) or 0),
                    round(float(getattr(self, "mag_ratio", 1.35) or 0), 4),
                    str(getattr(self, "img_format", "jpg") or "jpg").lower(),
                    int(getattr(self, "img_quality", 90) or 90),
                    int(getattr(self, "max_width", 0) or 0),
                ]
                return _hl.sha256(
                    "|".join(str(p) for p in parts).encode()).hexdigest()[:8]
            except Exception:
                return ""
        style_tag = _clean_style_tag()
        out_dir = os.path.join(cache_dir, "out" + cache_tag
                               + (("_style-" + style_tag) if style_tag else "")
                               + ("_cleanonly" if getattr(self, "clean_only", False)
                                  else ""))
        def _clean_img_tag() -> str:
            import hashlib as _hl
            try:
                parts = [
                    str(getattr(self, "clean_method", "") or "").strip().lower(),
                    1 if getattr(self, "force_lama", False) else 0,
                    1 if getattr(self, "clean_sfx", False) else 0,
                    int(getattr(self, "mask_padding", 3) or 0),
                    round(float(getattr(self, "pad_ratio", 0.06) or 0), 4),
                    int(getattr(self, "inpaint_radius", 3) or 0),
                    round(float(getattr(self, "mag_ratio", 1.35) or 0), 4),
                    1 if getattr(self, "clean_only", False) else 0,
                    1 if _android_gate("MANGA_CLEAN_TEXTFREE") else 0,
                ]
                return _hl.sha256(
                    "|".join(str(p) for p in parts).encode()).hexdigest()[:8]
            except Exception:
                return ""
        clean_cache_dir = os.path.join(
            cache_dir, "clean" + cache_tag + "_c-" + (_clean_img_tag() or "x"))
        os.makedirs(src_dir, exist_ok=True)
        os.makedirs(out_dir, exist_ok=True)

        try:
            for _nm in os.listdir(cache_dir):
                if not ((_nm == "out" or _nm.startswith("out_")
                         or _nm.startswith("dbgspill"))
                        and os.path.isdir(os.path.join(cache_dir, _nm))):
                    continue
                if _nm in (os.path.basename(out_dir), "out"):
                    continue
                shutil.rmtree(os.path.join(cache_dir, _nm),
                              ignore_errors=True)
        except Exception:
            pass

        try:
            _gc_root = os.path.dirname(os.path.abspath(output_path))
            _cur_cache = os.path.abspath(cache_dir)
            for _nm in os.listdir(_gc_root):
                if _nm.endswith(".cache"):
                    _p = os.path.abspath(os.path.join(_gc_root, _nm))
                    if _p != _cur_cache and os.path.isdir(_p):
                        shutil.rmtree(_p, ignore_errors=True)
        except Exception:
            pass

        try:
            with open(os.path.join(cache_dir, "last_out.json"), "w",
                      encoding="utf-8") as _fh:
                json.dump({"dir": os.path.basename(out_dir),
                           "clean_only": bool(getattr(self, "clean_only",
                                                      False)),
                           "ts": int(time.time())}, _fh)
        except Exception:
            pass

        title_skips = self._extract_title_skips_from_path(input_path)
        self._title_skip_patterns = title_skips
        MangaTranslator._title_skip_patterns = title_skips
        MangaTranslator._title_skip_enabled = False

        _local_fix_files: Optional[List[str]] = None
        if (not self._is_url(input_path) and "*" not in input_path
                and ("," in input_path or "\n" in input_path.strip())):
            def _local_img(s: str) -> Optional[str]:
                s = (s or "").strip()
                if s.lower().startswith("file://"):
                    s = s[7:]
                if (s and os.path.isfile(s)
                        and os.path.splitext(s)[1].lower() in IMAGE_EXTS):
                    return s
                return None
            _parts = [p for p in re.split(r"[,\n\r\t]+", input_path) if p.strip()]
            _loc = [_local_img(p) for p in _parts]
            if _parts and all(_loc):
                _local_fix_files = _loc
                self._independent_pages = True

        if _local_fix_files is not None:
            image_files = _local_fix_files
            print(f"[*] {len(image_files)} فایل محلی انتخاب شد — بدون دانلود.")
        elif (self._is_url(input_path) or "," in input_path
                or "*" in input_path or "\n" in input_path.strip()):
            urls = self._expand_input_urls(input_path)

            if not urls:
                print("[!] هیچ لینک معتبری پیدا نشد.", file=sys.stderr)
                return

            _probe_urls = [u for u in urls
                           if not (u.lower().startswith("file://")
                                   or self._is_direct_image_url(u))]
            _probe_image = set()
            if _probe_urls and len(urls) > 1:
                try:
                    from concurrent.futures import ThreadPoolExecutor as _TPE

                    def _probe(u: str) -> tuple:
                        try:
                            import requests as _rq
                            h = dict(headers) if headers else {
                                "User-Agent": "Mozilla/5.0"}
                            r = _rq.head(u, headers=h, timeout=8,
                                         allow_redirects=True)
                            ct = (r.headers.get("Content-Type") or "").lower()
                            if not ct.startswith("image/"):
                                h["Range"] = "bytes=0-255"
                                r2 = _rq.get(u, headers=h, timeout=8, stream=True)
                                ct = (r2.headers.get("Content-Type") or "").lower()
                                r2.close()
                            return (u, ct.startswith("image/"))
                        except Exception:
                            return (u, False)

                    with _TPE(max_workers=min(8, len(_probe_urls))) as _ex:
                        for _u, _ok in _ex.map(_probe, _probe_urls):
                            if _ok:
                                _probe_image.add(_u)
                    if _probe_image:
                        print(f"[*] {len(_probe_image)} لینک با چکِ Content-Type "
                              f"«تصویر مستقیم» شناخته شد.")
                except Exception:
                    pass
            all_direct = all(
                self._is_direct_image_url(u) or u in _probe_image for u in urls)
            if len(urls) == 1:
                print(f"[*] دانلود تصاویر از لینک: {urls[0]}")
                image_files = self._download_images_from_url(urls[0], src_dir)
                self._independent_pages = True
            elif all_direct:
                print(f"[*] {len(urls)} تصویر مستقیم — دانلود یک‌جا به عنوان یک فصل...")
                self._independent_pages = True
                os.makedirs(src_dir, exist_ok=True)
                image_files = []
                import requests as _req
                headers = {
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                }
                for i, u in enumerate(urls, 1):
                    try:
                        _lp = u[7:] if u.lower().startswith("file://") else u
                        if (os.path.isfile(_lp)
                                and os.path.splitext(_lp)[1].lower() in IMAGE_EXTS):
                            _ub = os.path.splitext(os.path.basename(_lp))[0]
                            _ub = re.sub(r'[\\/:*?"<>|]+', "_", _ub).strip("._ ")[:80]
                            _lext = os.path.splitext(_lp)[1].lower()
                            out_file = os.path.join(src_dir, f"{_ub or f'page_{i:03d}'}{_lext}")
                            _kk = 2
                            while (os.path.exists(out_file)
                                   and os.path.getsize(out_file) != os.path.getsize(_lp)):
                                out_file = os.path.join(src_dir, f"{_ub or f'page_{i:03d}'}-{_kk}{_lext}")
                                _kk += 1
                            if not os.path.exists(out_file):
                                shutil.copyfile(_lp, out_file)
                            image_files.append(out_file)
                            print(f"    [+] {i}/{len(urls)} فایل محلی کپی شد")
                            continue
                        if (re.match(r"^[A-Za-z]:[\\/]", u)
                                or u.startswith("\\\\")
                                or (u.startswith("/")
                                    and not u.lower().startswith("//"))):
                            print(f"    [!] فایلِ محلی پیدا نشد: {_lp[:140]}",
                                  file=sys.stderr)
                            continue
                        u = self._normalize_image_url(u)
                        _ub0 = os.path.splitext(os.path.basename(u.split("?")[0]))[0]
                        _ub0 = re.sub(r'[\\/:*?"<>|]+', "_", _ub0).strip("._ ")[:80]
                        if not re.search(r"\d", _ub0):
                            _ub0 = f"page_{i:03d}"
                        _hit0 = None
                        for _e0 in (".jpg", ".jpeg", ".png", ".webp"):
                            _c0 = os.path.join(src_dir, (_ub0 or f"page_{i:03d}") + _e0)
                            if os.path.isfile(_c0) and os.path.getsize(_c0) > 0:
                                _hit0 = _c0
                                break
                        if _hit0 is not None:
                            image_files.append(_hit0)
                            print(f"    [+] {i}/{len(urls)} از کشِ دانلود")
                            continue
                        r = _req.get(u, headers=headers, timeout=60)
                        r.raise_for_status()
                        content = r.content
                        ext = os.path.splitext(u.split("?")[0])[1].lower() or ".jpg"
                        if ext not in IMAGE_EXTS:
                            if content[:3] == b"\xff\xd8\xff":
                                ext = ".jpg"
                            elif content[:8] == b"\x89PNG\r\n\x1a\n":
                                ext = ".png"
                            elif content[:4] == b"RIFF":
                                ext = ".webp"
                            else:
                                ext = ".jpg"
                        test_img, _reblob = MangaTranslator._decode_image_bytes(content)
                        if test_img is None:
                            print(f"    [!] تصویر نامعتبر: {u[:90]}")
                            continue
                        if _reblob is not None:
                            content, ext = _reblob, ".jpg"
                        _ub = os.path.splitext(os.path.basename(u.split("?")[0]))[0]
                        _ub = re.sub(r'[\\/:*?"<>|]+', "_", _ub).strip("._ ")[:80]
                        if not re.search(r"\d", _ub):
                            _ub = f"page_{i:03d}"
                        out_file = os.path.join(src_dir, f"{_ub or f'page_{i:03d}'}{ext}")
                        _kk = 2
                        while (os.path.exists(out_file)
                               and not _same_dl(out_file, content)):
                            out_file = os.path.join(src_dir, f"{_ub or f'page_{i:03d}'}-{_kk}{ext}")
                            _kk += 1
                        if not os.path.exists(out_file):
                            with open(out_file, "wb") as f:
                                f.write(content)
                        image_files.append(out_file)
                        print(f"    [+] {i}/{len(urls)} ذخیره شد")
                    except Exception as e:
                        print(f"    [!] دانلود ناموفق ({u[:80]}…): {e}")
                if not image_files:
                    print("[!] هیچ تصویری دانلود نشد.", file=sys.stderr)
                    return
            else:
                print(f"[*] {len(urls)} لینک فصل — اول دانلودِ همهٔ تصاویر، "
                      f"بعد استخراج/پاکسازی/ترجمهٔ یک‌جا…")
                os.makedirs(src_dir, exist_ok=True)
                image_files = []
                _seen_ch: set = set()
                for i, url in enumerate(urls, 1):
                    if stop_requested():
                        raise JobCancelled("لغو توسط کاربر")
                    print(f"\n{'='*60}")
                    print(f"[دانلود {i}/{len(urls)}] {url}")
                    print(f"{'='*60}")
                    try:
                        files_i = self._download_images_from_url(
                            url, src_dir, shared_seen=_seen_ch)
                    except Exception as e:
                        print(f"[!] دانلود لینک {i} ناموفق: {str(e)[:120]}")
                        files_i = []
                    if not files_i:
                        print(f"[!] لینک {i}: هیچ تصویری دانلود نشد — رد شد.")
                        continue
                    for j, fsrc in enumerate(files_i, 1):
                        _nb = f"{i:02d}_{j:03d}_" + os.path.splitext(os.path.basename(fsrc))[0]
                        _nb = re.sub(r'[\\/:*?"<>|]+', "_", _nb).strip("._ ")[:100] \
                            or f"link{i:02d}_page_{j:03d}"
                        _ext = os.path.splitext(fsrc)[1].lower() or ".jpg"
                        out_file = os.path.join(src_dir, f"{_nb}{_ext}")
                        try:
                            _fsrc_t = os.path.getmtime(fsrc)
                        except Exception:
                            _fsrc_t = 0.0
                        _dup_ok = False
                        try:
                            if (os.path.exists(out_file)
                                    and os.path.abspath(out_file) != os.path.abspath(fsrc)
                                    and os.path.getsize(out_file) == os.path.getsize(fsrc)):
                                with open(out_file, "rb") as _fa, open(fsrc, "rb") as _fb:
                                    _dup_ok = (_fa.read(4096) == _fb.read(4096))
                        except Exception:
                            _dup_ok = False
                        if _dup_ok:
                            if _fsrc_t >= _t_run:
                                try:
                                    os.remove(fsrc)
                                except Exception:
                                    pass
                            image_files.append(out_file)
                            continue
                        _k = 2
                        while (os.path.exists(out_file)
                               and os.path.abspath(out_file) != os.path.abspath(fsrc)):
                            out_file = os.path.join(src_dir, f"{_nb}-{_k}{_ext}")
                            _k += 1
                        try:
                            if os.path.abspath(out_file) != os.path.abspath(fsrc):
                                shutil.move(fsrc, out_file)
                        except Exception:
                            out_file = fsrc
                        image_files.append(out_file)
                    print(f"    [+] لینک {i}: {len(files_i)} تصویر آماده "
                          f"(مجموع: {len(image_files)})")
                if not image_files:
                    print("[!] هیچ تصویری دانلود نشد.", file=sys.stderr)
                    return
                image_files.sort(key=MangaTranslator._natural_sort_key)
                self._independent_pages = True
                print(f"[✓] دانلودِ همهٔ {len(urls)} لینک تمام شد: "
                      f"{len(image_files)} تصویر → شروعِ استخراج/پاکسازی/ترجمه…")
        elif input_path.lower().endswith(".zip"):
            print(f"[*] استخراج فایل zip: {input_path}")
            image_files = self._extract_zip(input_path, src_dir)
        elif input_path.lower().endswith(".pdf"):
            print(f"[*] استخراج صفحات از PDF: {input_path}")
            image_files = self._pdf_to_images(input_path, src_dir)
        elif os.path.isdir(input_path):
            image_files = sorted(
                (f for f in glob.glob(os.path.join(input_path, "*"))
                 if os.path.splitext(f)[1].lower() in IMAGE_EXTS),
                key=MangaTranslator._natural_sort_key,
            )
        elif os.path.isfile(input_path) and os.path.splitext(input_path)[1].lower() in IMAGE_EXTS:
            image_files = [input_path]
        else:
            raise ValueError(f"نوع ورودی پشتیبانی نمی‌شه: {input_path}")

        if not image_files:
            print("[!] هیچ تصویری برای پردازش پیدا نشد.", file=sys.stderr)
            return

        _norm_files: List[str] = []
        for _f in image_files:
            _nf = MangaTranslator._normalize_input_image_file(_f, src_dir)
            if _nf != _f:
                print(f"    [~] {os.path.basename(_f)} کدکِ گوشی نداشت → "
                      f"به JPG تبدیل شد: {os.path.basename(_nf)}")
            _norm_files.append(_nf)
        image_files = _norm_files

        if len(image_files) >= 1:
            widths: List[int] = []
            valid_files: List[str] = []
            for f in image_files:
                im0 = cv2.imread(f)
                if im0 is None:
                    continue
                widths.append(int(im0.shape[1]))
                valid_files.append(f)
                del im0
            if valid_files:
                _indep_keep_w = (
                    getattr(self, "_independent_pages", False)
                    and int(getattr(self, "stitch_max_height", 0) or 0) <= 0)
                if _indep_keep_w:
                    wmap = {i: widths[i] for i in range(len(valid_files))}
                else:
                    wmap = self._cluster_widths(widths, abs_tol=180, rel_tol=0.18)
                cap = self.max_output_width if self.max_output_width and self.max_output_width > 0 else 0
                if cap:
                    for i in list(wmap.keys()):
                        if wmap[i] > cap:
                            wmap[i] = cap
                norm_dir = os.path.join(cache_dir, "normalized")
                os.makedirs(norm_dir, exist_ok=True)
                _norm_map_path = os.path.join(norm_dir, "map.json")
                _norm_map: Dict[str, str] = {}
                try:
                    with open(_norm_map_path, encoding="utf-8") as _fh:
                        _norm_map = {str(k): str(v) for k, v in
                                     (json.load(_fh) or {}).items()}
                except Exception:
                    _norm_map = {}
                normalized_files = []
                changed = 0
                _reused_norm = 0
                _norm_dirty = False
                cluster_summary: Dict[int, int] = {}
                for i, f in enumerate(valid_files):
                    _key_n = None
                    try:
                        _key_n = f"{os.path.basename(f)}|{os.path.getsize(f)}"
                    except Exception:
                        _key_n = None
                    if _key_n and _key_n in _norm_map:
                        _cand_n = os.path.join(norm_dir, _norm_map[_key_n])
                        if os.path.isfile(_cand_n):
                            normalized_files.append(_cand_n)
                            _reused_norm += 1
                            continue
                    im = cv2.imread(f)
                    if im is None:
                        continue
                    orig_w = im.shape[1]
                    tw = wmap.get(i, orig_w)
                    cluster_summary[tw] = cluster_summary.get(tw, 0) + 1
                    im = self._normalize_page_width(im, target_w=tw)
                    if im.shape[1] != orig_w:
                        changed += 1
                    ext_n = "." + (getattr(self, "img_format", None) or "webp").lstrip(".")
                    if ext_n == ".jpeg":
                        ext_n = ".jpg"
                    _nb = os.path.splitext(os.path.basename(f))[0]
                    _nb = re.sub(r'[\\/:*?"<>|]+', "_", _nb).strip() or f"page_{i+1:03d}"
                    out_n = os.path.join(norm_dir, f"{_nb}{ext_n}")
                    _k = 2
                    while os.path.exists(out_n):
                        out_n = os.path.join(norm_dir, f"{_nb}-{_k}{ext_n}")
                        _k += 1
                    self._write_image(im, out_n)
                    if _key_n:
                        _norm_map[_key_n] = os.path.basename(out_n)
                        _norm_dirty = True
                    normalized_files.append(out_n)
                if _norm_dirty:
                    try:
                        with open(_norm_map_path, "w", encoding="utf-8") as _fh:
                            json.dump(_norm_map, _fh, ensure_ascii=False)
                    except Exception:
                        pass
                if normalized_files:
                    image_files = normalized_files
                    groups = ", ".join(f"{w}px×{c}" for w, c in sorted(cluster_summary.items()))
                    print(
                        f"[*] نرمال‌سازی عرض هوشمند: {changed}/{len(normalized_files)} صفحه تغییر کرد | "
                        f"خوشه‌ها: {groups}"
                        + (f" (سقف={cap}px)" if cap else "")
                        + (f" | {_reused_norm} صفحه از کشِ نرمال‌سازی"
                           if _reused_norm else "")
                    )

        _indep_no_stitch = (
            getattr(self, "_independent_pages", False)
            and int(getattr(self, "stitch_max_height", 0) or 0) <= 0
            and not getattr(self, "stitch_explicit", False))
        if _indep_no_stitch and len(image_files) > 1:
            print(f"[*] حالت صفحات مستقل: {len(image_files)} صفحه هرکدام جدا مثل حالت تکی "
                  f"پردازش می‌شوند — بدون چسباندن/برشِ نوار (ریسایزِ گروهی هم نیست).")
        if (len(image_files) > 1 and not _indep_no_stitch
                and (self.stitch_max_height > 0 or getattr(self, "repair_page_seams", True))):
            stitch_dir = os.path.join(cache_dir, "stitched")
            image_files = self._stitch_pages_for_efficiency(image_files, stitch_dir)

        try:
            _live_total_write(len(image_files))
        except Exception:
            pass

        extract_dir = os.path.join(cache_dir, "extract")

        def _files_fingerprint(files):
            import hashlib as _hl
            try:
                h = _hl.sha256()
                h.update(("ver=" + str(APP_VER) + "\n").encode("utf-8", "ignore"))
                try:
                    h.update(("langs=" + ",".join(sorted(str(x) for x in (
                        getattr(self, "ocr_langs", None) or []))) + "\n"
                    ).encode("utf-8", "ignore"))
                except Exception:
                    pass
                h.update(("detconf=%.3f\n" % float(
                    getattr(self, "det_confidence", 0.16) or 0.16)).encode())
                h.update(("twopass=%d\n" % (
                    1 if getattr(self, "two_pass_ocr", True) else 0)).encode())
                for f in sorted(files, key=lambda x: os.path.basename(x).lower()):
                    try:
                        st = os.stat(f)
                        h.update(("%s|%d|" % (
                            os.path.basename(f), st.st_size)
                        ).encode("utf-8", "ignore"))
                        with open(f, "rb") as _fh:
                            h.update(_fh.read(524288))
                        h.update(b"\n")
                    except Exception:
                        h.update((os.path.basename(f) + "|?\n"
                        ).encode("utf-8", "ignore"))
                return h.hexdigest()[:16]
            except Exception:
                return ""

        _fp_new = _files_fingerprint(image_files)
        _fp_path = os.path.join(cache_dir, "input.json")
        _fp_old = ""
        try:
            with open(_fp_path, encoding="utf-8") as _fh:
                _fp_old = str(json.load(_fh).get("fp") or "")
        except Exception:
            _fp_old = ""
        if _fp_new and _fp_old and _fp_new != _fp_old:
            print("[*] ورودی/تنظیمات تغییر کرد — استخراج از اول.")
            shutil.rmtree(os.path.join(cache_dir, "extract"),
                          ignore_errors=True)
            try:
                for _n in os.listdir(cache_dir):
                    if (_n == "out" or _n.startswith("out_")
                            or _n.startswith("clean")):
                        shutil.rmtree(os.path.join(cache_dir, _n),
                                      ignore_errors=True)
            except Exception:
                pass
            try:
                os.remove(os.path.join(cache_dir, "trans.json"))
            except Exception:
                pass
        if _fp_new:
            try:
                with open(_fp_path, "w", encoding="utf-8") as _fh:
                    json.dump({"fp": _fp_new}, _fh)
            except Exception:
                pass

        _sig_cur = MangaTranslator._trans_sig_of(
            provider=getattr(self, "provider", ""),
            model=getattr(self, "model_name_raw",
                          getattr(self, "model_name", "")),
            api_base=getattr(self, "api_base", ""),
            prompt_mode=getattr(self, "prompt_mode", "professional"),
            instruction=(getattr(self, "custom_instruction", "") or ""),
            fake=bool(getattr(self, "fake_translate", False)),
            temperature=float(getattr(self, "translation_temperature", 0.7) or 0.7),
            top_p=float(getattr(self, "translation_top_p", 0.9) or 0.9),
        )
        _state_path = os.path.join(cache_dir, "state.json")
        _sig_prev = ""
        _fake_prev = None
        try:
            with open(_state_path, encoding="utf-8") as _fh:
                _st_j = json.load(_fh) or {}
            _sig_prev = str(_st_j.get("trans_sig") or "")
            _fake_prev = _st_j.get("fake")
            if _fake_prev is not None:
                _fake_prev = bool(_fake_prev)
        except Exception:
            pass
        _trans_store_path = os.path.join(cache_dir, "trans.json")
        _trans_store: Dict[str, dict] = {"sig": _sig_cur, "items": {}}
        _trans_store_lock = threading.Lock()
        _fake_toggled = (_fake_prev is not None
                         and _fake_prev != bool(getattr(self, "fake_translate", False)))
        _fresh_translate = (bool(getattr(self, "translate_retranslate", False))
                            or _fake_toggled)
        if _fake_toggled:
            print("[*] حالتِ تست عوض شد — ترجمه‌ها با حالتِ تازه از نو "
                  "ساخته میشوند (استخراج/پاکسازی از کش می‌ماند).")
        if _fresh_translate:
            if not _fake_toggled:
                print("[*] «از اول ترجمه کن» — ترجمه‌های قبلی پاک و همهٔ "
                      "حباب‌ها از نو ترجمه میشوند (استخراج/پاکسازی از کش "
                      "می‌ماند).")
            try:
                os.remove(_trans_store_path)
            except Exception:
                pass
            try:
                for _n in os.listdir(cache_dir):
                    if ((_n == "out" or _n.startswith("out_"))
                            and not _n.endswith("_cleanonly")):
                        shutil.rmtree(os.path.join(cache_dir, _n),
                                      ignore_errors=True)
            except Exception:
                pass
        elif _sig_prev and _sig_cur and _sig_prev != _sig_cur:
            print("[*] مدل/پرامپتِ ترجمه عوض شد — حالتِ ادامه: حباب‌های "
                  "ترجمه‌شده سرِ جایشان می‌مانند و فقط مانده‌ها با مدلِ "
                  "جدید ترجمه میشوند.")
        _trans_apply = False
        if resume and os.path.isfile(_trans_store_path):
            try:
                with open(_trans_store_path, encoding="utf-8") as _fh:
                    _ts_j = json.load(_fh) or {}
                _ts_items = _ts_j.get("items") or {}
                if _ts_items:
                    _trans_store["items"] = {str(k): dict(v) for k, v in
                                             _ts_items.items()}
                    _trans_apply = True
                    print(f"[*] {len(_trans_store['items'])} ترجمهٔ ذخیرهشده "
                          f"از کش برگشت (ادامه از همان‌جا).")
            except Exception:
                pass
        if (_sig_cur and not getattr(self, "clean_only", False)):
            try:
                with open(_state_path, "w", encoding="utf-8") as _fh:
                    json.dump({"trans_sig": _sig_cur,
                               "fake": bool(getattr(self, "fake_translate", False)),
                               "ts": int(time.time())}, _fh)
            except Exception:
                pass

        def _tkey(page_i: int, idx: int, src: str) -> str:
            import hashlib as _hl
            _h = _hl.sha256((src or "").encode("utf-8", "ignore")).hexdigest()[:10]
            return f"p{page_i}_i{idx}_{_h}"

        def _trans_store_save(regions) -> None:
            try:
                _upd = {}
                for _r in (regions or []):
                    _k = getattr(_r, "_tkey", None)
                    _t = (getattr(_r, "translated_text", "") or "").strip()
                    if not _k or not _t:
                        continue
                    _upd[_k] = {"t": _t,
                                "s": (getattr(_r, "bubble_style", "") or "")}
                if not _upd:
                    return
                with _trans_store_lock:
                    _trans_store["items"].update(_upd)
                    _items = dict(_trans_store["items"])
                    with open(_trans_store_path, "w", encoding="utf-8") as _fh:
                        json.dump({"sig": _sig_cur, "items": _items}, _fh,
                                  ensure_ascii=False)
            except Exception:
                pass

        processed_files = []
        skipped = 0
        page_ext = "." + (self.img_format or "webp").lstrip(".")
        if page_ext == ".jpeg":
            page_ext = ".jpg"

        pending = []
        _src_of_page: Dict[int, str] = {}
        for page_i, f in enumerate(image_files):
            _src_of_page[page_i] = f
            out_file = os.path.join(out_dir, os.path.splitext(os.path.basename(f))[0] + page_ext)
            if resume and os.path.isfile(out_file):
                processed_files.append(out_file)
                skipped += 1
                try:
                    _live_page_dump(out_file, key=out_file, slot=page_i + 1)
                except Exception:
                    pass
                continue
            pending.append((page_i, f, out_file))

        if skipped:
            print(f"[*] {skipped} صفحه از کش (resume).")

        try:
            self.preload_lama_async()
        except Exception:
            pass
        try:
            print(f"[TIME] startup={time.time() - _t_run:.1f}s "
                  f"(اماده‌سازی تا اولین صفحه)", flush=True)
        except Exception:
            pass

        def _extract_one(item):
            page_i, f, out_file = item
            _raise_if_stop()
            _t_ext = time.time()
            if page_i == 0:
                MangaTranslator._title_skip_enabled = True
            _ex_cache = os.path.join(extract_dir, f"page_{page_i:04d}.json")
            _ex_size = -1
            try:
                _ex_size = os.path.getsize(f)
            except Exception:
                _ex_size = -1
            if resume and os.path.isfile(_ex_cache):
                try:
                    with open(_ex_cache, encoding="utf-8") as _fh:
                        _cdata = json.load(_fh)
                    if int(_cdata.get("src_size") or -2) == _ex_size:
                        image = MangaTranslator._imread_any(f)
                        if image is not None:
                            regions = [
                                MangaTranslator._region_from_cache(d)
                                for d in (_cdata.get("regions") or [])
                            ]
                            _dbg = None
                            _ovl = _cdata.get("ovl")
                            if _ovl:
                                try:
                                    _dbg = image.view(_DebugPageVis)
                                    _dbg.ovl = _ovl
                                    _dbg.base = image
                                except Exception:
                                    _dbg = None
                            _ctx_put(page_i, {
                                "boxes": _ctx_boxes_from_regions(regions),
                                "quads": _ctx_quads_from_ovl(_ovl),
                            })
                            _n_hit = 0
                            if _trans_apply and regions:
                                for _ii, _r in enumerate(regions):
                                    if getattr(_r, "kind", "") != "dialogue":
                                        continue
                                    _src_t = (_r.source_text or "").strip()
                                    if not _src_t:
                                        continue
                                    _it = _trans_store["items"].get(
                                        _tkey(page_i, _ii, _src_t))
                                    if not _it:
                                        continue
                                    try:
                                        _r.translated_text = str(_it.get("t") or "")
                                        if _it.get("s"):
                                            _r.bubble_style = str(_it["s"])
                                        _n_hit += 1
                                    except Exception:
                                        continue
                            _hit_note = (f" + {_n_hit} حباب از کشِ ترجمه"
                                         if _n_hit else "")
                            print(f"[*] {os.path.basename(f)} — از کشِ "
                                  f"استخراج (ادامه){_hit_note}")
                            return page_i, out_file, image, regions, _dbg
                except Exception:
                    pass
            try:
                image = MangaTranslator._imread_any(f)
                if image is None:
                    raise ValueError(f"تصویر قابل خواندن نیست: {f}")
                basename = os.path.basename(f)
                if self._is_mostly_blank(image):
                    print(f"[!] رد شد (صفحه خالی): {basename}")
                    return page_i, out_file, None, None, None
                print(f"[*] {basename}")
                regions, dbg, page_ctx = self.extract_regions_phase(image)
                _ctx_put(page_i, page_ctx)
                try:
                    _ovl_w = getattr(dbg, "ovl", None)
                    _cdata_w = {
                        "src_size": _ex_size,
                        "regions": [MangaTranslator._region_to_cache(r)
                                    for r in (regions or [])],
                        "ovl": (MangaTranslator._cache_jsonable(_ovl_w)
                                if _ovl_w is not None else None),
                    }
                    os.makedirs(extract_dir, exist_ok=True)
                    with open(_ex_cache, "w", encoding="utf-8") as _fh:
                        json.dump(_cdata_w, _fh, ensure_ascii=False)
                except Exception:
                    pass
                try:
                    print(f"[TIME] page#{page_i + 1} "
                          f"load+extract={time.time() - _t_ext:.1f}s",
                          flush=True)
                except Exception:
                    pass
                return page_i, out_file, image, regions, dbg
            except GeminiQuotaExhausted:
                raise
            except Exception as e:
                print(f"    [!] خطا در استخراج {os.path.basename(f)}: {e}", file=sys.stderr)
                return page_i, out_file, None, None, None
            finally:
                if page_i == 0:
                    MangaTranslator._title_skip_enabled = False

        def _finish_one(page_i, out_file, image, regions, dbg):
            if image is None:
                return page_i, out_file, None, dbg
            if not regions:
                return page_i, out_file, image, dbg
            _t_fin = time.time()
            _pctx1 = _ctx_get(page_i)
            try:
                result, page_debug = self.finish_page_phase(
                    image, regions, final=True,
                    det_quads=_pctx1.get("quads"),
                    page_boxes=_pctx1.get("boxes"))
                try:
                    print(f"[TIME] page#{page_i + 1} "
                          f"clean+render={time.time() - _t_fin:.1f}s",
                          flush=True)
                except Exception:
                    pass
                dbg_out = page_debug if page_debug is not None else dbg
                return page_i, out_file, result, dbg_out
            except GeminiQuotaExhausted:
                raise
            except Exception as e:
                print(f"    [!] خطا در تکمیل {os.path.basename(out_file)}: {e}", file=sys.stderr)
                return page_i, out_file, None, dbg

        results_by_i = {}

        min_batch = max(1, int(getattr(self, "min_translate_batch", 15) or 15))

        min_batch = max(min_batch, max(1, int(getattr(self, "bubbles_per_request", 15) or 15)))

        extracted_map: Dict[int, tuple] = {}
        self._page_ctx_store: Dict[int, dict] = {}
        _page_ctx_lock = threading.Lock()

        def _ctx_get(p: int) -> dict:
            try:
                with _page_ctx_lock:
                    return self._page_ctx_store.get(p) or {}
            except Exception:
                return {}

        def _ctx_put(p: int, ctx: dict) -> None:
            try:
                with _page_ctx_lock:
                    self._page_ctx_store[p] = ctx or {}
            except Exception:
                pass

        def _ref_img(v):
            if v is None:
                return None
            if isinstance(v, np.ndarray):
                return v
            try:
                return MangaTranslator._imread_any(str(v))
            except Exception:
                return None

        def _dbg_spill_dir() -> str:
            return os.path.join(cache_dir, "dbgspill" + cache_tag)

        def _dbg_spill(dbg, page_i: int):
            try:
                if dbg is None:
                    return None
                if isinstance(dbg, np.ndarray):
                    _ovl = getattr(dbg, "ovl", None)
                    _d = _dbg_spill_dir()
                    os.makedirs(_d, exist_ok=True)
                    _p = os.path.join(_d, "page_%04d.png" % page_i)
                    import cv2
                    cv2.imwrite(_p, np.asarray(dbg))
                    return {"ovl": _ovl, "burn": _p}
                return dbg
            except Exception:
                return dbg

        def _dbg_view(dbg, image: Optional[np.ndarray]):
            try:
                if dbg is None:
                    return None
                if isinstance(dbg, np.ndarray):
                    return dbg
                _ovl = (dbg or {}).get("ovl")
                _burn = (dbg or {}).get("burn")
                _img = None
                if _burn and os.path.isfile(_burn):
                    _img = MangaTranslator._imread_any(str(_burn))
                if _img is None:
                    return None
                _v = _img.view(_DebugPageVis)
                _v.ovl = _ovl
                _v.base = image
                return _v
            except Exception:
                return None

        def _map_spill_page(page_i: int) -> None:
            try:
                with _clean_cond:
                    _e = extracted_map.get(page_i)
                    if _e is None:
                        return
                    _of, _im, _pc, _regs, _dbg = _e
                    _im2 = _im
                    if isinstance(_im2, np.ndarray):
                        _f = _src_of_page.get(page_i)
                        if _f and os.path.isfile(_f):
                            _im2 = str(_f)
                    _pc2 = _pc
                    if isinstance(_pc2, np.ndarray):
                        _ccp = os.path.join(clean_cache_dir,
                                            "page_%04d.png" % page_i)
                        try:
                            os.makedirs(clean_cache_dir, exist_ok=True)
                            import cv2
                            cv2.imwrite(_ccp, _pc2)
                            if os.path.isfile(_ccp):
                                _pc2 = _ccp
                        except Exception:
                            _pc2 = _pc
                    _dbg2 = _dbg_spill(_dbg, page_i)
                    if (_im2 is not _im) or (_pc2 is not _pc) \
                            or (_dbg2 is not _dbg):
                        extracted_map[page_i] = (_of, _im2, _pc2, _regs, _dbg2)
            except Exception:
                pass

        def _ctx_quads_from_ovl(ovl) -> list:
            out = []
            try:
                for _q in ((ovl or {}).get("pdet") or []):
                    try:
                        out.append(np.asarray(_q, dtype=np.float32)
                                   .reshape(-1, 2))
                    except Exception:
                        continue
            except Exception:
                return []
            return out

        def _ctx_boxes_from_regions(regs) -> list:
            out = []
            for _r0 in (regs or []):
                try:
                    if str(getattr(_r0, "det_class", "") or "") \
                            in ("bubble", "text_bubble"):
                        _x0, _y0 = int(_r0.rect[0]), int(_r0.rect[1])
                        out.append((_x0, _y0, _x0 + int(_r0.rect[2]),
                                    _y0 + int(_r0.rect[3]),
                                    str(getattr(_r0, "det_class", ""))))
                except Exception:
                    continue
            return out

        dialogue_buffer: List[TextRegion] = []
        global_id = 0
        pending_by_page: Dict[int, int] = {}
        page_of_region: Dict[int, int] = {}
        finished_pages: set = set()
        results_by_i: Dict[int, tuple] = {}

        def _account_chunk(chunk: List[TextRegion]) -> None:
            for r in chunk:
                pi = page_of_region.get(r.id)
                if pi is None:
                    continue
                left = pending_by_page.get(pi, 0) - 1
                if left <= 0:
                    pending_by_page.pop(pi, None)
                else:
                    pending_by_page[pi] = left

        def _finish_page_now(page_i: int) -> None:
            _raise_if_stop()
            if page_i in finished_pages:
                return
            try:
                _wait_clean(page_i)
            except Exception:
                pass
            entry = extracted_map.get(page_i)
            if entry is None:
                return
            out_file, image, precleaned, regions, dbg = entry
            image = _ref_img(image)
            precleaned = _ref_img(precleaned)
            dbg = _dbg_spill(dbg, page_i)
            _pctx = _ctx_get(page_i)
            finished_pages.add(page_i)

            extracted_map[page_i] = (out_file, None, None, regions, dbg)
            try:
                if image is None:
                    results_by_i[page_i] = (out_file, None, dbg)
                    return
                if not regions:
                    try:
                        self._write_image(image, out_file)
                        _live_page_dump(out_file, key=out_file,
                                        slot=page_i + 1)
                    except Exception:
                        pass
                    results_by_i[page_i] = (out_file, True, dbg)
                    return
                _t_fin = time.time()
                result, page_debug = self.finish_page_phase(
                    image, regions, skip_translate=True, precleaned=precleaned,
                    final=True,
                    det_quads=_pctx.get("quads"),
                    page_boxes=_pctx.get("boxes"))
                try:
                    _trans_store_save(regions)
                except Exception:
                    pass
                try:
                    print(f"[TIME] page#{page_i + 1} "
                          f"clean+render={time.time() - _t_fin:.1f}s",
                          flush=True)
                except Exception:
                    pass
                dbg_out = page_debug if page_debug is not None else dbg
                _dbg_view_now = dbg_out if isinstance(dbg_out, np.ndarray) \
                    else _dbg_view(dbg_out, image)
                try:
                    self._write_image(result, out_file)
                    results_by_i[page_i] = (out_file, True,
                                            _dbg_spill(dbg_out, page_i))
                    _live_page_dump(out_file, key=out_file, slot=page_i + 1)
                    if self.debug and _dbg_view_now is not None:
                        _live_dump(_dbg_view_now, dbg=True, slot=page_i + 1)
                except Exception as _werr:
                    print(f"  [!] ذخیرهٔ تصویر #{page_i + 1} ناموفق: {_werr}")
                    results_by_i[page_i] = (out_file, None,
                                            _dbg_spill(dbg_out, page_i))
                del result
            except GeminiQuotaExhausted as e:
                print(f"\n[!] {e}")
                results_by_i[page_i] = (out_file, None, dbg)
            except Exception as e:
                print(f"    [!] خطا در تکمیل {os.path.basename(out_file)}: {e}", file=sys.stderr)
                results_by_i[page_i] = (out_file, None, dbg)

        def _finish_ready_pages() -> None:
            with _qd_lock:
                _inflight = set(_qd_inflight)
            for page_i in sorted(extracted_map.keys()):
                if page_i in finished_pages:
                    continue
                if page_i in _inflight:
                    continue
                if pending_by_page.get(page_i, 0) > 0:
                    continue
                if not _clean_ready(page_i):
                    continue
                _finish_page_now(page_i)

        _prev_counts: Dict[int, int] = {}
        _prev_state = {"t": 0.0}
        _prev_lock = threading.Lock()

        def _preview_ready_pages(force: bool = False) -> None:
            now = time.time()
            if not force:
                if now - _prev_state["t"] < 2.0:
                    return
            with _prev_lock:
                if not force and time.time() - _prev_state["t"] < 2.0:
                    return
                _prev_state["t"] = time.time()
            for page_i in sorted(extracted_map.keys()):
                if page_i in finished_pages:
                    continue
                entry = extracted_map.get(page_i)
                if entry is None:
                    continue
                out_file, image, precleaned, regions, dbg = entry
                image = _ref_img(image)
                precleaned = _ref_img(precleaned)
                if image is None or not regions or precleaned is None:
                    continue
                if pending_by_page.get(page_i, 0) <= 0:
                    continue
                n_tr = sum(1 for r in regions
                           if r.kind == "dialogue"
                           and (r.translated_text or "").strip())
                if n_tr <= 0 or n_tr <= _prev_counts.get(page_i, 0):
                    continue
                try:
                    _pctxv = _ctx_get(page_i)
                    result, _pd = self.finish_page_phase(
                        image, regions, skip_translate=True, precleaned=precleaned,
                        page_boxes=_pctxv.get("boxes"))
                    self._write_image(result, out_file)
                    _live_page_dump(out_file, key=out_file, slot=page_i + 1)
                    _prev_counts[page_i] = n_tr
                    del result
                except Exception as _perr:
                    print(f"    [!] پیش‌نمایش صفحهٔ {page_i + 1}: {str(_perr)[:80]}")

        def _flush_translate_buffer(force: bool = False) -> None:
            nonlocal dialogue_buffer
            if not dialogue_buffer:
                return
            if not force and len(dialogue_buffer) < min_batch:
                return
            n = len(dialogue_buffer)
            dialogue_buffer.sort(key=lambda r: page_of_region.get(r.id, 0))
            _groups = [dialogue_buffer]
            dialogue_buffer = []
            print(f"[*] ترجمهٔ {n} دیالوگ در «یک» درخواست (سبکِ مرجع)…")
            for _g in _groups:
                _translate_chunk_bg(_g)

        def _queue_dialogues(regions: List[TextRegion], page_i: int) -> None:
            nonlocal global_id, dialogue_buffer
            if not regions:
                return
            queued = 0
            for _ri, r in enumerate(regions):
                if r.kind != "dialogue":
                    continue
                if not (r.source_text or "").strip():
                    continue
                if not source_has_letters(r.source_text):
                    continue
                try:
                    r._tkey = _tkey(page_i, _ri, r.source_text)
                except Exception:
                    pass
                if (r.translated_text or "").strip():
                    continue
                r.id = global_id
                page_of_region[global_id] = page_i
                r.page_index = page_i
                _pf = _src_of_page.get(page_i)
                r.page_file = (os.path.basename(_pf) if _pf
                               else f"page_{page_i + 1:02d}.png")
                global_id += 1
                dialogue_buffer.append(r)
                queued += 1
            if queued:
                pending_by_page[page_i] = pending_by_page.get(page_i, 0) + queued

        if getattr(self, "clean_only", False):
            print("[*] Clean-only mode — API is not called.")
            min_batch = 15
        else:
            print(
                f"[*] سبکِ مرجع: اول استخراجِ دوطرفهٔ همهٔ {len(pending)} صفحه "
                f"+ پاکسازیٔ یکطرفهٔ بالا→پایین همزمان؛ بعد از اتمامِ "
                f"کاملِ استخراج: پاکسازیٔ دوطرفه + ترجمهٔ همه در «یک» "
                f"درخواست (هیچ متنی زودتر از اتمامِ استخراج به مترجم نمیرود)."
            )

        quota_flag = {"dead": False}
        trans_futures: list = []
        _tr_prog = {"n": 0}
        _tr_prog239_lock = threading.Lock()

        def _translate_chunk_bg(chunk: List[TextRegion]) -> None:
            if not chunk:
                return

            def _job():
                try:
                    if stop_requested():
                        raise JobCancelled("لغو توسط کاربر")
                    self.translate_regions(chunk)
                except GeminiQuotaExhausted as e:
                    print(f"\n[!] {e}")
                    quota_flag["dead"] = True
                except JobCancelled:
                    _account_chunk(chunk)
                    raise
                except Exception as e:
                    print(f"    [!] خطای ترجمه در پس‌زمینه: {e}", file=sys.stderr)
                finally:
                    try:
                        _trans_store_save(chunk)
                    except Exception:
                        pass
                    _account_chunk(chunk)
                    try:
                        with _tr_prog239_lock:
                            _tr_prog["n"] += len(chunk)
                            _n = _tr_prog["n"]
                            _t = max(int(global_id or 0), _n)
                        print(f"[*] ترجمه: {_n}/{_t} ناحیه",
                              flush=True)
                    except Exception:
                        pass

            trans_futures.append(trans_pool.submit(_job))

        trans_pool = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="translate")

        clean_pool = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="clean")
        clean_pool2 = None
        clean_all_futs: list = []
        clean_started: set = set()
        clean_claimed: set = set()
        clean_counted: set = set()
        clean_done_ev: Dict[int, threading.Event] = {}
        pending_clean: set = set()
        extraction_done = {"v": False}
        _clean_cond = threading.Condition()


        def _clean_regions_for_page(page_i: int) -> Optional[List[TextRegion]]:
            entry = extracted_map.get(page_i)
            if entry is None:
                return None
            _of, im, _pc, regions, _dbg = entry
            if im is None or not regions:
                return None
            regs = [r for r in regions
                    if r.kind == "dialogue"
                    and (((r.source_text or "").strip()
                          or (r.translated_text or "").strip())
                         or getattr(r, "ocr_empty", False))]
            if _android_gate("MANGA_CLEAN_TEXTFREE"):
                regs = regs + [r for r in regions if r.kind == "text_free"]
            if getattr(self, "clean_only", False):
                regs = regs + [r for r in regions if r.kind == "promo"]
            if getattr(self, "clean_sfx", False):
                regs = regs + [r for r in regions if r.kind == "sfx"]
            if getattr(self, "clean_only", False):
                _have = {id(x) for x in regs}
                regs = regs + [r for r in regions
                               if r.kind == "junk" and id(r) not in _have]
            return regs or None

        def _clean_one_page(_p: int) -> bool:
            _did = False
            try:
                if stop_requested():
                    return False
                with _clean_cond:
                    if _p in finished_pages:
                        return False
                    _e = extracted_map.get(_p)
                    if _e is None:
                        return False
                    _of, im, _pc, regions, _dbg = _e
                    if im is None:
                        return False
                    if _pc is not None:
                        return True
                    if _p in clean_claimed:
                        return False
                    clean_claimed.add(_p)
                _did = True
                im = _ref_img(im)
                if im is None:
                    return False
                _cc_path = os.path.join(clean_cache_dir,
                                        "page_%04d.png" % _p)
                if resume and os.path.isfile(_cc_path):
                    _pc_disk = MangaTranslator._imread_any(_cc_path)
                    if (_pc_disk is not None
                            and im is not None
                            and _pc_disk.shape[:2] == im.shape[:2]):
                        with _clean_cond:
                            if _p in finished_pages:
                                return True
                            _cur = extracted_map.get(_p) or _e
                            extracted_map[_p] = (_cur[0], _cur[1], _cc_path,
                                                 _cur[3], _cur[4])
                        try:
                            print(f"[*] صفحهٔ {_p + 1} — پاکسازی از "
                                  f"کشِ دیسک (بدونِ LaMa)", flush=True)
                        except Exception:
                            pass
                        return True
                regs = _clean_regions_for_page(_p)
                if not regs:
                    return True
                if _android_gate("MANGA_PHASE_PRINTS"):
                    print(f"[*] پاکسازی متنِ صفحهٔ {_p + 1}…",
                          flush=True)
                _t0 = time.time()
                _pctxc = _ctx_get(_p)
                _pcn = self.clean_image(im, regs,
                                        page_boxes=_pctxc.get("boxes"))
                _cc_wrote = False
                try:
                    import cv2 as _cv2
                    os.makedirs(clean_cache_dir, exist_ok=True)
                    _cv2.imwrite(_cc_path, _pcn)
                    _cc_wrote = os.path.isfile(_cc_path)
                except Exception:
                    _cc_wrote = False
                with _clean_cond:
                    if _p in finished_pages:
                        return True
                    _cur = extracted_map.get(_p) or _e
                    extracted_map[_p] = (_cur[0], _cur[1],
                                         (_cc_path if _cc_wrote else _pcn),
                                         _cur[3], _cur[4])
                del _pcn
                try:
                    print(f"[TIME] page#{_p + 1} "
                          f"clean={time.time() - _t0:.1f}s",
                          flush=True)
                except Exception:
                    pass
                return True
            except GeminiQuotaExhausted as e:
                print(f"\n[!] {e}")
                quota_flag["dead"] = True
            except Exception as e:
                print(f"    [!] پاکسازیِ صفحهٔ {_p + 1} ناموفق: "
                      f"{str(e)[:120]}")
                if getattr(self, "debug", False):
                    try:
                        import traceback as _tb
                        _tb.print_exc()
                    except Exception:
                        pass
            finally:
                if _did:
                    with _clean_cond:
                        clean_claimed.discard(_p)
                        if _p not in clean_counted:
                            clean_counted.add(_p)
                            _cn = len(clean_counted)
                            _ctot = len(pending)
                        else:
                            _cn = None
                    if _cn is not None:
                        try:
                            print(f"[*] پاکسازی متن: {_cn}/{_ctot} صفحه",
                                  flush=True)
                        except Exception:
                            pass
            return _did

        def _clean_done_mark(_p: int) -> None:
            _ev = clean_done_ev.get(_p)
            if _ev is not None:
                _ev.set()

        def _clean_pages_bg(pages: List[int]) -> None:
            for _p in dict.fromkeys(pages):
                with _clean_cond:
                    if (_p in clean_started or _p in finished_pages
                            or extraction_done["v"]):
                        continue
                    clean_started.add(_p)
                    if _p not in clean_done_ev:
                        clean_done_ev[_p] = threading.Event()
                    pending_clean.add(_p)
                    _clean_cond.notify_all()

        def _clean_sched_job() -> None:
            while True:
                if stop_requested() or quota_flag["dead"]:
                    return
                with _clean_cond:
                    cand = None
                    while True:
                        cand = [p for p in pending_clean
                                if p in extracted_map
                                and p not in finished_pages]
                        if cand:
                            break
                        if extraction_done["v"]:
                            return
                        _clean_cond.wait(timeout=0.5)
                    pi = min(cand)
                    pending_clean.discard(pi)
                if _clean_one_page(pi):
                    _clean_done_mark(pi)

        clean_all_futs.append(clean_pool.submit(_clean_sched_job))

        def _wait_clean(page_i: int) -> None:
            with _clean_cond:
                _ev = clean_done_ev.get(page_i)
            if _ev is not None:
                _ev.wait(timeout=1800)

        def _clean_ready(page_i: int) -> bool:
            with _clean_cond:
                _ev = clean_done_ev.get(page_i)
            return _ev is None or _ev.is_set()

        def _clean_seq_job(seq) -> None:
            for _p in seq:
                if stop_requested() or quota_flag["dead"]:
                    _clean_done_mark(_p)
                    continue
                with _clean_cond:
                    if _p in finished_pages:
                        _clean_done_mark(_p)
                        continue
                    pending_clean.discard(_p)
                if _clean_one_page(_p):
                    _clean_done_mark(_p)

        def _dispatch_chunk_clean(chunk: List[TextRegion]) -> None:
            _pgs = sorted({page_of_region.get(r.id) for r in chunk
                           if page_of_region.get(r.id) is not None})
            if _pgs:
                _clean_pages_bg(_pgs)

        _ext_lock = threading.Lock()
        _ext_fwd = {"v": 0}
        _ext_bwd = {"v": len(pending) - 1}
        _ext_quota = {"v": False}
        _ext_err = {"exc": None}
        _qd_lock = threading.Lock()
        _qd_inflight: set = set()

        _ext_prog = {"n": 0}

        def _ext_prog_tick() -> None:
            try:
                with _ext_lock:
                    _ext_prog["n"] += 1
                    _n = _ext_prog["n"]
                print(f"[*] استخراج متن: {_n}/{len(pending)} صفحه",
                      flush=True)
            except Exception:
                pass

        def _claim_ext(role: str):
            with _ext_lock:
                f, b = _ext_fwd["v"], _ext_bwd["v"]
                if f > b:
                    return None
                if role == "fwd":
                    it = pending[f]
                    _ext_fwd["v"] = f + 1
                else:
                    it = pending[b]
                    _ext_bwd["v"] = b - 1
                return it

        def _ext_worker(role: str) -> None:
            while True:
                if stop_requested():
                    return
                if quota_flag["dead"] or _ext_quota["v"]:
                    return
                item = _claim_ext(role)
                if item is None:
                    return
                try:
                    page_i, out_file, image, regions, dbg = _extract_one(item)
                except GeminiQuotaExhausted as e:
                    print(f"\n[!] {e}")
                    _ext_quota["v"] = True
                    return
                except JobCancelled as e:
                    _ext_err["exc"] = e
                    return
                except Exception as e:
                    print(f"    [!] خطای کارگرِ استخراج({role}): {e}",
                          file=sys.stderr)
                    _ext_prog_tick()
                    continue
                _ext_prog_tick()
                with _qd_lock:
                    _qd_inflight.add(page_i)
                extracted_map[page_i] = (out_file, image, None, regions, dbg)
                try:
                    if image is not None and regions:
                        try:
                            self._rescue_empty_ocr(image, regions)
                            with _qd_lock:
                                _queue_dialogues(regions, page_i)
                        except GeminiQuotaExhausted as e:
                            print(f"\n[!] {e}")
                            _ext_quota["v"] = True
                            return
                        _clean_pages_bg([page_i])
                finally:
                    with _qd_lock:
                        _qd_inflight.discard(page_i)
                try:
                    _finish_ready_pages()
                    _preview_ready_pages()
                except JobCancelled as e:
                    _ext_err["exc"] = e
                    return
                except Exception:
                    pass
                _map_spill_page(page_i)

        print(f"[*] استخراج دوطرفه: صفحهٔ ۱→{max(0, len(pending))} و "
              f"صفحهٔ {max(0, len(pending))}→۱ همزمان (دیدار در وسط).")
        _t_fwd = threading.Thread(target=_ext_worker, args=("fwd",),
                                  daemon=True, name="extract-fwd")
        _t_bwd = threading.Thread(target=_ext_worker, args=("bwd",),
                                  daemon=True, name="extract-bwd")
        _t_fwd.start()
        _t_bwd.start()
        _t_fwd.join()
        _t_bwd.join()

        extraction_done["v"] = True
        with _clean_cond:
            _clean_cond.notify_all()

        if _ext_err["exc"] is not None:
            trans_pool.shutdown(wait=False)
            clean_pool.shutdown(wait=False)
            raise _ext_err["exc"]

        with _clean_cond:
            _backlog = sorted(pending_clean)
        if _backlog:
            _mid = (len(_backlog) + 1) // 2
            _top_seq, _bot_seq = _backlog[:_mid], _backlog[_mid:]
            print(f"[*] پاکسازی دوطرفه: {len(_top_seq)} صفحه از بالا→پایین، "
                  f"{len(_bot_seq)} صفحه از پایین→بالا…")
            clean_all_futs.append(clean_pool.submit(
                _clean_seq_job, list(_top_seq)))
            clean_pool2 = ThreadPoolExecutor(
                max_workers=1, thread_name_prefix="clean2")
            clean_all_futs.append(clean_pool2.submit(
                _clean_seq_job, list(reversed(_bot_seq))))

        if stop_requested():
            trans_pool.shutdown(wait=False)
            raise JobCancelled("لغو توسط کاربر")

        self._extraction_done = True
        _n_dlg_total = int(len(dialogue_buffer))
        if not getattr(self, "clean_only", False):
            print(
                f"[✓] استخراجِ همهٔ {len(pending)} صفحه کامل شد — "
                f"{_n_dlg_total} دیالوگ جمع شد؛ حالا ترجمهٔ همه در «یک» "
                "درخواست (سبکِ مرجع) شروع میشود…"
            )
        else:
            print(f"[✓] استخراجِ همهٔ {len(pending)} صفحه کامل شد "
                  f"(حالتِ فقط-پاکسازی).")
        if dialogue_buffer and not getattr(self, "clean_only", False):
            _flush_translate_buffer(force=True)
        _t_trw = time.time()
        import concurrent.futures as _cfw
        _seen_f: dict = {}
        for _f in trans_futures:
            _seen_f[id(_f)] = _f
        for _f in list(clean_all_futs):
            _seen_f[id(_f)] = _f
        _futures = list(_seen_f.values())
        while _futures:
            if stop_requested():
                break
            _done, _futures = _cfw.wait(
                _futures, timeout=2.0,
                return_when=_cfw.FIRST_COMPLETED)
            if not _done:
                _finish_ready_pages()
                _preview_ready_pages()
                continue
            for _f in _done:
                try:
                    _f.result()
                except Exception:
                    pass
            _finish_ready_pages()
            _preview_ready_pages(force=True)
        try:
            print(f"[TIME] translate_wait={time.time() - _t_trw:.1f}s",
                  flush=True)
        except Exception:
            pass
        if stop_requested():
            trans_pool.shutdown(wait=False)
            raise JobCancelled("لغو توسط کاربر")

        def _collect_empty_dialogues() -> List[TextRegion]:
            _out: List[TextRegion] = []
            for _p in sorted(extracted_map.keys()):
                _entry = extracted_map.get(_p)
                if _entry is None:
                    continue
                _of, _im, _pc, _regs, _dbg = _entry
                for _r in (_regs or []):
                    if getattr(_r, "kind", "") != "dialogue":
                        continue
                    if not (_r.source_text or "").strip():
                        continue
                    if getattr(_r, "ocr_empty", False):
                        continue
                    if not source_has_letters(_r.source_text):
                        continue
                    if (_r.translated_text or "").strip():
                        continue
                    _out.append(_r)
            return _out

        def _rerender_page_after_empty(page_i: int) -> None:
            try:
                _raise_if_stop()
            except Exception:
                return
            _entry = extracted_map.get(page_i)
            if _entry is None:
                return
            _of, _im, _pc, _regs, _dbg = _entry
            if not _regs:
                return
            _f = _src_of_page.get(page_i)
            if not _f or not os.path.isfile(_f):
                return
            _img = MangaTranslator._imread_any(_f)
            if _img is None:
                return
            try:
                _pctxr = _ctx_get(page_i)
                _res, _pd = self.finish_page_phase(
                    _img, _regs, skip_translate=True,
                    precleaned=None, final=True,
                    det_quads=_pctxr.get("quads"),
                    page_boxes=_pctxr.get("boxes"))
                self._write_image(_res, _of)
                try:
                    _live_page_dump(_of, key=_of, slot=page_i + 1)
                except Exception:
                    pass
                del _res
                print(f"  [✓] صفحهٔ {page_i + 1} با ترجمهٔ پسگیری‌شده دوباره "
                      f"رندر شد")
            except GeminiQuotaExhausted:
                raise
            except Exception as _e:
                print(f"    [!] رندرِ دوبارهٔ صفحهٔ {page_i + 1} ناموفق: "
                      f"{str(_e)[:90]}")

        if (not getattr(self, "clean_only", False)
                and not getattr(self, "fake_translate", False)):
            _empty_ids_before: Dict[int, int] = {}
            for _r in _collect_empty_dialogues():
                _pg = page_of_region.get(getattr(_r, "id", -1), -1)
                if _pg is not None and _pg >= 0:
                    _empty_ids_before[getattr(_r, "id", -1)] = int(_pg)
            for _er_round in range(1, 4):
                if stop_requested() or quota_flag["dead"]:
                    break
                _empties = _collect_empty_dialogues()
                if not _empties:
                    break
                print(f"[*] پسگیریِ خالیهایِ AI: {_empties.__len__()} حباب "
                      f"بیترجمه در یک درخواستِ دوباره (دورِ {_er_round}/۳)…")
                _empties.sort(key=lambda _r: page_of_region.get(
                    getattr(_r, "id", -1), 0))
                try:
                    self.translate_regions(_empties)
                except (GeminiQuotaExhausted, JobCancelled):
                    raise
                except Exception as _e:
                    print(f"    [!] دوبارهترجمهٔ خالیها ناموفق: "
                          f"{str(_e)[:90]}")
                _trans_store_save(_empties)
                _still = _collect_empty_dialogues()
                if len(_still) >= len(_empties):
                    print(f"[!] دوبارهترجمه پیشرفت نکرد ({len(_still)} حباب "
                          f"همچنان خالی) — قانونِ ۱۹۲: متنِ مبدأ میماند")
                    break
            _refilled_pages = sorted({
                _pg for _rid, _pg in _empty_ids_before.items()
                if _pg in finished_pages
                and any((_r_ref.translated_text or "").strip()
                        for _pg_one in (_pg,)
                        for _r_ref in ((extracted_map.get(_pg_one)
                                        or (None,) * 5)[3] or [])
                        if getattr(_r_ref, "id", None) == _rid)})
            for _p in _refilled_pages:
                _rerender_page_after_empty(int(_p))

        _finish_ready_pages()
        for page_i in sorted(extracted_map.keys()):
            _finish_page_now(page_i)
        try:
            trans_pool.shutdown(wait=True)
        except Exception:
            pass
        try:
            clean_pool.shutdown(wait=True)
        except Exception:
            pass
        try:
            if clean_pool2 is not None:
                clean_pool2.shutdown(wait=True)
        except Exception:
            pass

        _t_save = time.time()
        print("[*] ذخیرهٔ نهایی خروجی‌ها...", flush=True)
        debug_files = []
        for page_i in sorted(results_by_i.keys()):
            out_file, result, dbg = results_by_i[page_i]
            if result is None:
                continue
            if result is True:
                processed_files.append(out_file)
            else:
                self._write_image(result, out_file)
                _live_page_dump(out_file, key=out_file,
                                slot=page_i + 1)
                processed_files.append(out_file)
            results_by_i[page_i] = (out_file, None, None)
            if self.debug and dbg is not None:
                try:
                    _bs_img = _ref_img(_src_of_page.get(page_i))
                    dbg = _dbg_view(dbg, _bs_img)
                except Exception:
                    dbg = dbg if isinstance(dbg, np.ndarray) else None
                if dbg is not None:
                    try:
                        _live_dump(dbg, dbg=True, slot=page_i + 1)
                    except Exception:
                        pass
            if self.debug and dbg is not None:
                debug_dir = os.path.join(cache_dir, "debug" + cache_tag)
                os.makedirs(debug_dir, exist_ok=True)
                dbg_ext = "." + (getattr(self, "img_format", None) or "webp").lstrip(".")
                if dbg_ext == ".jpeg":
                    dbg_ext = ".jpg"
                dbg_name = os.path.splitext(os.path.basename(out_file))[0] + "_debug" + dbg_ext
                dbg_path = os.path.join(debug_dir, dbg_name)
                self._write_image(dbg, dbg_path)
                debug_files.append(dbg_path)
                print(f"  [*] DEBUG صفحه ذخیره شد: {dbg_path}")
                try:
                    _ov = getattr(dbg, "ovl", None)
                    _bs = getattr(dbg, "base", None)
                    if _ov is not None and _bs is not None:
                        _base_name = (os.path.splitext(
                            os.path.basename(out_file))[0]
                            + "_base" + dbg_ext)
                        self._write_image(_bs,
                                          os.path.join(debug_dir,
                                                       _base_name))
                        import json as _json
                        with open(os.path.splitext(dbg_path)[0] + ".json",
                                  "w", encoding="utf-8") as f:
                            _json.dump(_ov, f, ensure_ascii=False)
                except Exception:
                    pass

        if not processed_files:
            print("[!] هیچ خروجی‌ای تولید نشد.", file=sys.stderr)
            return

        out_ext = os.path.splitext(output_path)[1].lower()
        if out_ext == ".pdf":
            self._save_as_pdf(processed_files, output_path)
            print(f"[✓] PDF نهایی ذخیره شد در: {output_path}")

            if self.debug and debug_files:
                dbg_pdf = os.path.splitext(output_path)[0] + "_debug.pdf"
                try:
                    self._save_as_pdf(debug_files, dbg_pdf)
                    print(f"[✓] PDF دیباگ ذخیره شد در: {dbg_pdf}")
                except Exception as e:
                    print(f"  [!] ساخت PDF دیباگ ناموفق: {e}")
        elif out_ext == ".zip":
            self._save_as_zip(out_dir, output_path)
            print(f"[✓] فایل zip نهایی ذخیره شد در: {output_path}")
            if self.debug and debug_files:
                dbg_zip = os.path.splitext(output_path)[0] + "_debug.zip"
                try:
                    dbg_dir = os.path.join(cache_dir, "debug" + cache_tag)
                    self._save_as_zip(dbg_dir, dbg_zip)
                    print(f"[✓] ZIP دیباگ ذخیره شد در: {dbg_zip}")
                except Exception as e:
                    print(f"  [!] ساخت ZIP دیباگ ناموفق: {e}")
        elif out_ext == ".html":
            self._save_as_html(processed_files, output_path)
            print(f"[✓] HTML نهایی (با تصاویر base64) ذخیره شد در: {output_path}")
            if self.debug and debug_files:
                dbg_html = os.path.splitext(output_path)[0] + "_debug.html"
                try:
                    self._save_as_html(debug_files, dbg_html)
                    print(f"[✓] HTML دیباگ ذخیره شد در: {dbg_html}")
                except Exception as e:
                    print(f"  [!] ساخت HTML دیباگ ناموفق: {e}")
        elif out_ext == ".psd":
            self._save_as_psd(processed_files, output_path)
            print(f"[✓] PSD نهایی ذخیره شد در: {output_path}")
            if self.debug and debug_files:
                dbg_psd = os.path.splitext(output_path)[0] + "_debug.psd"
                try:
                    self._save_as_psd(debug_files, dbg_psd)
                    print(f"[✓] PSD دیباگ ذخیره شد در: {dbg_psd}")
                except Exception as e:
                    print(f"  [!] ساخت PSD دیباگ ناموفق: {e}")
        elif len(processed_files) == 1 and out_ext in IMAGE_EXTS:
            img = cv2.imread(processed_files[0])
            self._write_image(img, output_path)
            print(f"[✓] ذخیره شد در: {output_path}")
        else:
            if out_ext != ".pdf":
                output_path = os.path.splitext(output_path)[0] + ".pdf"
            self._save_as_pdf(processed_files, output_path)
            print(f"[✓] PDF نهایی ذخیره شد در: {output_path}")
        try:
            print(f"[TIME] save={time.time() - _t_save:.1f}s | "
                  f"total={time.time() - _t_run:.1f}s", flush=True)
        except Exception:
            pass
        try:
            _live_seq_flush()
        except Exception:
            pass

    def _render_one_region(self, pil_img, draw, image, original_image, region) -> None:
        x, y, w, h = region.rect
        try:
            _polys = [np.asarray(p, dtype=np.float32).reshape(-1, 2)
                      for p in (getattr(region, "ocr_polys", None) or [])
                      if np.asarray(p).size >= 6]
            if _polys:
                _pts = np.concatenate(_polys, axis=0)
                px0, py0 = float(_pts[:, 0].min()), float(_pts[:, 1].min())
                px1, py1 = float(_pts[:, 0].max()), float(_pts[:, 1].max())
                if (px1 - px0) >= 10 and (py1 - py0) >= 8:
                    _off = max(abs((px0 + px1) / 2 - (x + w / 2)) / max(1.0, w),
                               abs((py0 + py1) / 2 - (y + h / 2)) / max(1.0, h))
                    if _off > 0.35:
                        _padx = max(6, int(0.06 * (px1 - px0)))
                        _pady = max(5, int(0.08 * (py1 - py0)))
                        x = max(0, int(px0 - _padx))
                        y = max(0, int(py0 - _pady))
                        w = int(px1 - px0 + 2 * _padx)
                        h = int(py1 - py0 + 2 * _pady)
        except Exception:
            pass

        try:
            _rpolys = list(getattr(region, "ocr_polys", None) or [])
            if _rpolys:
                _rvert = self._polys_vertical(_rpolys)
                _rdense = (not _rvert) and MangaTranslator._polys_dense(_rpolys)
                if _rvert or _rdense:
                    _rbb = MangaTranslator._text_block_box(
                        _rpolys, region.rect, vert=_rvert)
                    if _rbb is not None:
                        x, y, w, h = (int(_rbb[0]), int(_rbb[1]),
                                      int(_rbb[2]), int(_rbb[3]))
        except Exception:
            pass

        short = len((region.translated_text or "").split()) <= 2
        if short and (w < 90 or h < 50):

            expand = max(4, int(min(w, h) * 0.12))
            x = max(0, x - expand // 2)
            y = max(0, y - expand // 2)
            w = w + expand
            h = h + expand

        pad = max(3, int(min(w, h) * (0.05 if short else 0.08)))
        box_w = max(14, w - 2 * pad)
        box_h = max(14, h - 2 * pad)

        style = (getattr(region, "bubble_style", None) or "").strip().lower()

        max_font = self._max_font_for_region(region)

        try:
            _hs = []
            for _p in (getattr(region, "ocr_polys", None) or []):
                _pts = np.asarray(_p, dtype=np.float32).reshape(-1, 2)
                if _pts.shape[0] < 3:
                    continue
                _r = cv2.minAreaRect(_pts)
                _hs.append(float(min(_r[1][0], _r[1][1])))
            if _hs:
                _orig_h = float(np.median(_hs))
                if _orig_h >= 9.0:
                    max_font = max(10, min(int(max_font),
                                           int(round(_orig_h * 0.80))))
        except Exception:
            pass

        font, lines, sw = self._wrap_and_fit(
            draw, region.translated_text, box_w, box_h, style=style, max_size=max_font
        )
        text_rgb, stroke_rgb = self._pick_text_and_stroke(image, original_image, region)

        try:
            angle = float(getattr(region, "angle", 0.0) or 0.0)
        except (TypeError, ValueError):
            angle = 0.0
        if angle != angle or angle in (float("inf"), float("-inf")):
            angle = 0.0
        if abs(angle) > 45.0:
            angle = 0.0

        if not bool(getattr(region, "angle_flat_veto", False)):
            try:
                _angs = []
                for _p in (getattr(region, "ocr_polys", None) or []):
                    _a = self._poly_long_side_angle(_p)
                    if abs(_a) >= 1.0:
                        _angs.append(float(_a))
                if len(_angs) >= 2:
                    _med = float(np.median(_angs))
                    _spread = float(np.max(np.abs(np.asarray(_angs) - _med)))
                    if _spread <= 5.0 and abs(_med) >= 3.0:
                        angle = _med
            except Exception:
                pass

        try:
            if abs(angle) >= 3.0 and original_image is not None:
                _vpts = None
                for _p in (getattr(region, "ocr_polys", None) or []):
                    try:
                        _pp = np.asarray(_p, dtype=np.float32).reshape(-1, 2)
                    except Exception:
                        continue
                    if _pp.size == 0:
                        continue
                    _vpts = _pp if _vpts is None else np.concatenate([_vpts, _pp], axis=0)
                if _vpts is None:
                    _vpts = np.array([[x, y], [x + w, y],
                                      [x + w, y + h], [x, y + h]], dtype=np.float32)
                _vx0 = max(0, int(_vpts[:, 0].min()) - 2)
                _vy0 = max(0, int(_vpts[:, 1].min()) - 2)
                _vx1 = min(int(original_image.shape[1]), int(_vpts[:, 0].max()) + 3)
                _vy1 = min(int(original_image.shape[0]), int(_vpts[:, 1].max()) + 3)
                _polys_agree = False
                try:
                    _pa = [float(self._poly_long_side_angle(_p))
                           for _p in (getattr(region, "ocr_polys", None) or [])]
                    _pa = [a for a in _pa if abs(a) >= 1.0]
                    if len(_pa) >= 2 \
                            and float(np.std(_pa)) <= 2.5 \
                            and abs(float(np.mean(_pa)) - angle) <= 3.0:
                        _polys_agree = True
                except Exception:
                    _polys_agree = False
                if (not _polys_agree) \
                        and _vx1 - _vx0 >= 40 and _vy1 - _vy0 >= 14:
                    _rmk = MangaTranslator._ocr_poly_mask(
                        (_vy1 - _vy0, _vx1 - _vx0),
                        getattr(region, "ocr_polys", None) or [],
                        _vx0, _vy0)
                    _a_ink, _a_ok = MangaTranslator._ink_slant_measure(
                        original_image[_vy0:_vy1, _vx0:_vx1], _rmk)
                    if _a_ok and abs(_a_ink) < 6.0:
                        _supr = MangaTranslator._ink_slant_support(
                            original_image[_vy0:_vy1, _vx0:_vx1],
                            angle, _rmk)
                        if _supr is not None and _supr >= 1.10:
                            pass
                        else:
                            print(f"    [!] حذف کجیِ کاذب در رندر [{region.id}]: "
                                  f"{angle:+.1f}° → 0.0° (جوهرِ مسطح)")
                            angle = 0.0
                    elif (abs(_a_ink) >= 6.0 and abs(_a_ink) <= 45.0
                            and (_a_ink > 0.0) != (angle > 0.0)):
                        if abs(abs(_a_ink) - abs(angle)) > 15.0:
                            print(f"    [!] وتوی کجیِ ناسازگار در رندر [{region.id}]: "
                                  f"{angle:+.1f}° ← جوهر {_a_ink:+.1f}° → 0.0°")
                            angle = 0.0
                        else:
                            print(f"    [!] اصلاح جهتِ چرخش در رندر [{region.id}]: "
                                  f"{angle:+.1f}° → {_a_ink:+.1f}°")
                            angle = _a_ink
        except Exception:
            pass
        if abs(angle) > 45.0:
            angle = 0.0

        if original_image is not None:
            try:
                _arc = MangaTranslator._curve_path_from_ink(
                    original_image, region)
            except Exception:
                _arc = None
            if os.environ.get("MANGA_DEBUG_ROT"):
                try:
                    _np_ = len(getattr(region, "ocr_polys", None) or [])
                    _nl_ = len(MangaTranslator._group_polys_to_lines(
                        getattr(region, "ocr_polys", None) or []))
                    print(f"    [dbg-arc-chk] r{region.id} polys={_np_} "
                          f"lines={_nl_} arc={'YES' if _arc else 'no'}")
                except Exception:
                    pass
            if _arc is not None:
                try:
                    if os.environ.get("MANGA_DEBUG_ROT"):
                        print(f"    [dbg-arc] r{region.id} "
                              f"sag={_arc['sag']} d_ang={_arc['d_ang']} "
                              f"lh={_arc['lh']} ang={_arc['angle']} "
                              f"arc_len={_arc['arc_len']}")
                    if self._render_arc_text(
                            pil_img, draw, region, _arc,
                            text_rgb, stroke_rgb, style, max_font):
                        return
                except Exception:
                    pass

        if abs(angle) < 3:
            bb = font.getbbox("آیگچ", stroke_width=sw)
            glyph_h = bb[3] - bb[1]
            _dbg_pos = bool(os.environ.get("MANGA_DEBUG_POS"))

            n = max(1, len(lines))

            _olines = None
            try:
                _olines = MangaTranslator._group_polys_to_lines(
                    getattr(region, "ocr_polys", None) or [])
            except Exception:
                _olines = None
            _align_ok = False
            if (_olines and len(_olines) == n):
                try:
                    _omh = float(np.median([b[3] - b[1] for b in _olines]))
                    if _omh >= 8.0:
                        _align_ok = True
                except Exception:
                    _align_ok = False
            if _align_ok:
                line_h = glyph_h + 1
                if line_h * n + 2 * sw > box_h:
                    line_h = max(4, (box_h - 2 * sw) // n)
                _cy_off = (float(bb[1]) + float(bb[3])) / 2.0
                _y_top = y + 1
                _y_bot = y + pad + box_h - max(4, line_h)
                if _dbg_pos:
                    print(f"    [pos] r{region.id} ALIGN font={getattr(font,'size','?')} "
                          f"n={n} olines={len(_olines)} bb=({bb[1]:.0f},{bb[3]:.0f}) "
                          f"line_h={line_h} y={y} pad={pad} box_h={box_h}")
                for i, line in enumerate(lines):
                    shaped = self._shape_farsi(line)
                    line_w = draw.textbbox(
                        (0, 0), shaped, font=font, stroke_width=sw)[2]
                    line_x = x + pad + max(0, (box_w - line_w) // 2)
                    _bx0, _by0, _bx1, _by1 = _olines[i]
                    _cy = (_by0 + _by1) / 2.0
                    line_y = int(round(_cy - _cy_off))
                    if _y_bot >= _y_top:
                        line_y = max(_y_top, min(line_y, _y_bot))
                    draw.text(
                        (line_x, line_y),
                        shaped,
                        font=font,
                        fill=text_rgb,
                        stroke_width=sw,
                        stroke_fill=stroke_rgb,
                    )
            else:
                line_h = glyph_h + 1
                if line_h * n + 2 * sw > box_h:
                    line_h = max(4, (box_h - 2 * sw) // n)
                total_h = line_h * n
                start_y = y + pad + max(0, (box_h - total_h) // 2)

                start_y = max(start_y, y + 1)
                if _dbg_pos:
                    print(f"    [pos] r{region.id} BLOCK font={getattr(font,'size','?')} "
                          f"n={n} olines={len(_olines) if _olines else 0} "
                          f"bb=({bb[1]:.0f},{bb[3]:.0f}) line_h={line_h} "
                          f"y={y} pad={pad} box_h={box_h} start_y={start_y}")

                bottom_limit = y + pad + box_h

                for i, line in enumerate(lines):
                    shaped = self._shape_farsi(line)
                    line_w = draw.textbbox((0, 0), shaped, font=font, stroke_width=sw)[2]
                    line_x = x + pad + max(0, (box_w - line_w) // 2)
                    line_y = start_y + i * line_h

                    draw.text(
                        (line_x, line_y),
                        shaped,
                        font=font,
                        fill=text_rgb,
                        stroke_width=sw,
                        stroke_fill=stroke_rgb,
                    )
        else:

            try:
                _pln = MangaTranslator._group_polys_to_lines(
                    getattr(region, "ocr_polys", None) or [])
                if os.environ.get("MANGA_DEBUG_ROT"):
                    _pang = [round(self._poly_long_side_angle(p), 1)
                             for p in (getattr(region, "ocr_polys", None) or [])]
                    print(f"    [dbg-lines] r{region.id} "
                          f"polys={len(_pang)} pangs={_pang} "
                          f"lines={len(_pln)}")
                if _pln and len(_pln) >= 2:
                    _allp = [np.asarray(p, dtype=np.float32).reshape(-1, 2)
                             for p in (getattr(region, "ocr_polys", None) or [])
                             if np.asarray(p).size >= 6]
                    _ln_ang = []
                    for _lb in _pln:
                        _cx0, _cy0, _cx1, _cy1 = _lb
                        _cxs = (_cx0 + _cx1) / 2.0
                        _cys = (_cy0 + _cy1) / 2.0
                        _pw = max(8.0, float(_cx1 - _cx0))
                        _ph = max(8.0, float(_cy1 - _cy0))
                        _aa = []
                        for _pp in _allp:
                            _px = float(_pp[:, 0].mean())
                            _py = float(_pp[:, 1].mean())
                            if abs(_px - _cxs) <= _pw * 0.75 \
                                    and abs(_py - _cys) <= _ph * 0.9:
                                _va = float(self._poly_long_side_angle(_pp))
                                if abs(_va) >= 1.0:
                                    _aa.append(_va)
                        _ln_ang.append(float(np.median(_aa)) if _aa else 0.0)
                    _spr = float(np.max(_ln_ang) - np.min(_ln_ang))
                    if os.environ.get("MANGA_DEBUG_ROT"):
                        print(f"    [dbg-curve] r{region.id} "
                              f"lines={len(_pln)} "
                              f"angs={[round(a, 1) for a in _ln_ang]} "
                              f"spr={_spr:.1f}")
                    if _spr >= 8.0 and all(abs(a) <= 45.0 for a in _ln_ang):
                        self._render_curved_lines(
                            pil_img, draw, region, _pln, _ln_ang,
                            text_rgb, stroke_rgb, style, max_font)
                        return
            except Exception:
                pass

            rx, ry, rw_box, rh_box = x, y, w, h
            try:
                _rpoly = [np.asarray(p, dtype=np.float32).reshape(-1, 2)
                          for p in (getattr(region, "ocr_polys", None) or [])
                          if np.asarray(p).size >= 6]
                if _rpoly:
                    _rpt = np.concatenate(_rpoly, axis=0)
                    _qx0 = float(_rpt[:, 0].min()) - 3.0
                    _qy0 = float(_rpt[:, 1].min()) - 3.0
                    _qx1 = float(_rpt[:, 0].max()) + 3.0
                    _qy1 = float(_rpt[:, 1].max()) + 3.0
                    if (_qx1 - _qx0) >= 24 and (_qy1 - _qy0) >= 14:
                        rx = max(0, int(_qx0))
                        ry = max(0, int(_qy0))
                        rw_box = int(_qx1 - _qx0)
                        rh_box = int(_qy1 - _qy0)
            except Exception:
                pass

            th = np.radians(abs(angle))
            c_, s_ = float(np.cos(th)), float(np.sin(th))
            denom = c_ * c_ - s_ * s_
            fit_w, fit_h = rw_box, rh_box
            if denom > 0.05:
                _t_w = (rw_box * c_ - rh_box * s_) / denom
                _t_h = (rh_box * c_ - rw_box * s_) / denom
                _b_w = (w * c_ - h * s_) / denom
                _b_h = (h * c_ - w * s_) / denom
                if 24 < _t_w <= (rw_box + rh_box) * 0.95 \
                        and 10 < _t_h <= (rw_box + rh_box) * 0.95:
                    fit_w, fit_h = int(_t_w * 0.94), int(_t_h * 0.94)
                if 24 < _b_w <= (w + h) * 0.95 \
                        and 10 < _b_h <= (w + h) * 0.95:
                    fit_w = max(fit_w, int(_b_w * 0.94))
                    fit_h = max(fit_h, int(_b_h * 0.94))
            font, lines, sw = self._wrap_and_fit(
                draw, region.translated_text, fit_w, fit_h, style=style, max_size=max_font
            )
            if os.environ.get("MANGA_DEBUG_ROT"):
                print(f"    [dbg-rot] {getattr(region, 'id', '?')} "
                      f"rect=({x},{y},{w},{h}) text-box=({rx},{ry},"
                      f"{rw_box},{rh_box}) angle={angle:.1f} "
                      f"fit=({fit_w},{fit_h}) lines={len(lines)} "
                      f"font={getattr(font, 'size', '?')}")

            line_h = font.getbbox("آی", stroke_width=sw)[3] + 6
            tmp_h = line_h * len(lines) + 10
            tmp_w = 0
            for line in lines:
                shaped = self._shape_farsi(line)
                lw = draw.textbbox((0, 0), shaped, font=font, stroke_width=sw)[2]
                tmp_w = max(tmp_w, lw)
            tmp_w += 14

            tmp = Image.new("RGBA", (tmp_w, tmp_h), (0, 0, 0, 0))
            tmp_draw = ImageDraw.Draw(tmp)

            for i, line in enumerate(lines):
                shaped = self._shape_farsi(line)
                line_w = tmp_draw.textbbox((0, 0), shaped, font=font, stroke_width=sw)[2]
                tx = (tmp_w - line_w) // 2
                ty = 15 + i * line_h
                tmp_draw.text(
                    (tx, ty),
                    shaped,
                    font=font,
                    fill=text_rgb + (255,),
                    stroke_width=sw,
                    stroke_fill=stroke_rgb + (255,),
                )

            rotated = tmp.rotate(-angle, expand=True, resample=Image.BICUBIC)

            max_rw = max(24, int(w * 1.04))
            max_rh = max(24, int(h * 1.04))
            rw0, rh0 = rotated.size
            scale_fit = min(1.0, max_rw / max(1, rw0), max_rh / max(1, rh0))
            if scale_fit < 0.99:
                rotated = rotated.resize(
                    (max(8, int(rw0 * scale_fit)), max(8, int(rh0 * scale_fit))),
                    Image.LANCZOS,
                )
            cx = rx + rw_box // 2
            cy = ry + rh_box // 2
            rw, rh = rotated.size
            paste_x = int(cx - rw / 2)
            paste_y = int(cy - rh / 2)

            pil_img.paste(rotated, (paste_x, paste_y), rotated)

    def _render_curved_lines(self, pil_img, draw, region, line_boxes,
                             line_angles, text_rgb, stroke_rgb,
                             style, max_font) -> None:
        txt = str(getattr(region, "translated_text", "") or "").strip()
        if not txt or not line_boxes:
            return
        try:
            n = len(line_boxes)
            words = txt.split()
            if not words:
                return
            widths = [max(14.0, float(b[2] - b[0])) for b in line_boxes]
            heights = [max(7.0, float(b[3] - b[1])) for b in line_boxes]
            med_h = float(np.median(heights))
            fsize = int(np.clip(round(med_h * 0.92), 10,
                                max(11, int(max_font or 48))))
            sw = self._stroke_width_for(fsize)
            if n == 1:
                chunks = [" ".join(words)]
            elif len(words) <= n:
                chunks = [words[i] if i < len(words) else ""
                          for i in range(n)]
            else:
                total_w = sum(widths)
                chunks = []
                wi = 0
                for li in range(n):
                    if li == n - 1:
                        chunks.append(" ".join(words[wi:]))
                        break
                    _share = (widths[li] / total_w) * (len(words))
                    _take = max(1, int(round(_share)))
                    _take = min(_take, len(words) - wi - (n - li - 1))
                    if _take <= 0 or wi >= len(words):
                        chunks.append("")
                        continue
                    chunks.append(" ".join(words[wi:wi + _take]))
                    wi += _take
                while len(chunks) < n:
                    chunks.append("")
            for li, chunk in enumerate(chunks):
                if not chunk:
                    continue
                _lb = line_boxes[li]
                _ang = float(line_angles[li]) if li < len(line_angles) else 0.0
                if abs(_ang) > 45.0:
                    _ang = 0.0
                _f = self._load_font(fsize, style=style)
                _sh = self._shape_farsi(chunk)
                _lw = draw.textbbox((0, 0), _sh, font=_f,
                                    stroke_width=sw)[2]
                _fit = max(14.0, widths[li] * 1.12)
                _tries = 0
                while _lw > _fit and fsize - _tries > 10 and _tries < 6:
                    _tries += 1
                    _f = self._load_font(fsize - _tries, style=style)
                    _lw = draw.textbbox((0, 0), _sh, font=_f,
                                        stroke_width=sw)[2]
                _fsize = fsize - _tries
                _sw2 = self._stroke_width_for(_fsize)
                _lh = max(10, int(_fsize * 1.35))
                _tmp_w = max(24, _lw + 12)
                _tmp = Image.new("RGBA", (_tmp_w, _lh + 8), (0, 0, 0, 0))
                _td = ImageDraw.Draw(_tmp)
                _tx = (_tmp_w - _lw) // 2
                _td.text((_tx, 2), _sh, font=_f,
                         fill=tuple(text_rgb)[:3] + (255,),
                         stroke_width=_sw2,
                         stroke_fill=tuple(stroke_rgb)[:3] + (255,))
                _rot = _tmp.rotate(-_ang, expand=True,
                                   resample=Image.BICUBIC)
                _cx = (_lb[0] + _lb[2]) / 2.0
                _cy = (_lb[1] + _lb[3]) / 2.0
                _rw, _rh = _rot.size
                pil_img.paste(_rot, (int(_cx - _rw / 2),
                                     int(_cy - _rh / 2)), _rot)
        except Exception:
            return

    def _render_arc_text(self, pil_img, draw, region, curve, text_rgb,
                         stroke_rgb, style, max_font) -> bool:
        try:
            txt = str(getattr(region, "translated_text", "") or "").strip()
            path_pts = curve.get("path") if isinstance(curve, dict) else None
            if not txt or not path_pts or len(path_pts) < 6:
                return False
            path = np.asarray(path_pts, dtype=np.float64).reshape(-1, 2)
            if path.shape[0] < 6:
                return False
            segs = np.diff(path, axis=0)
            seg_len = np.hypot(segs[:, 0], segs[:, 1])
            if float(seg_len.sum()) < 36.0:
                return False
            cum = np.concatenate([[0.0], np.cumsum(seg_len)])
            arc_len = float(cum[-1])
            tang = segs / np.maximum(seg_len, 1e-6)[:, None]
            lh_src = max(8.0, float(curve.get("lh", 12.0)))
            lh_band = max(8.0, float(curve.get("lh_band", lh_src)))
            try:
                _rh = int(region.rect[3])
            except Exception:
                _rh = int(lh_src * 4)
            _single_src = lh_band <= lh_src * 1.40 + 2.0
            if _single_src:
                try:
                    _step = float(np.median(seg_len))
                    _max_ext = 0.18 * arc_len
                    _img_w, _img_h = pil_img.size
                    _pre = []
                    _p = path[0].copy()
                    _t = -tang[0]
                    _acc = 0.0
                    while _acc < _max_ext:
                        _p = _p + _t * _step
                        if _p[0] < 2 or _p[1] < 2 \
                                or _p[0] > _img_w - 3 or _p[1] > _img_h - 3:
                            break
                        _pre.append(_p.copy())
                        _acc += _step
                    _post = []
                    _p = path[-1].copy()
                    _t = tang[-1]
                    _acc = 0.0
                    while _acc < _max_ext:
                        _p = _p + _t * _step
                        if _p[0] < 2 or _p[1] < 2 \
                                or _p[0] > _img_w - 3 or _p[1] > _img_h - 3:
                            break
                        _post.append(_p.copy())
                        _acc += _step
                    if _pre or _post:
                        _pre_a = np.asarray(_pre[::-1], dtype=np.float64) \
                            .reshape(-1, 2)
                        _post_a = np.asarray(_post, dtype=np.float64) \
                            .reshape(-1, 2)
                        path = np.concatenate([_pre_a, path, _post_a], axis=0)
                        segs = np.diff(path, axis=0)
                        seg_len = np.hypot(segs[:, 0], segs[:, 1])
                        cum = np.concatenate([[0.0], np.cumsum(seg_len)])
                        arc_len = float(cum[-1])
                        tang = segs / np.maximum(seg_len, 1e-6)[:, None]
                except Exception:
                    path = np.asarray(path_pts, dtype=np.float64).reshape(-1, 2)
                    segs = np.diff(path, axis=0)
                    seg_len = np.hypot(segs[:, 0], segs[:, 1])
                    cum = np.concatenate([[0.0], np.cumsum(seg_len)])
                    arc_len = float(cum[-1])
                    tang = segs / np.maximum(seg_len, 1e-6)[:, None]
            fit_w = int(arc_len * (0.97 if _single_src else 0.94))
            fit_h = int(max(lh_src * 1.35, min(_rh * 1.05, lh_src * 5.0)))
            font = lines = sw = None
            _ms = min(int(max_font or 48), max(10, int(round(lh_src * 0.95))))
            while _ms >= 10:
                _f, _l, _s = self._wrap_and_fit(
                    draw, txt, fit_w, fit_h, style=style, max_size=_ms)
                if _l:
                    _bb = _f.getbbox("آیگچ", stroke_width=_s)
                    _lh_t = max(8, _bb[3] - _bb[1]) + 3
                    font, lines, sw = _f, _l, _s
                    _k_max = 4 if _single_src else 5
                    if len(_l) <= _k_max \
                            and _lh_t * len(_l) <= max(_rh * 1.35, lh_src * 1.6):
                        break
                _ms -= 2
            _k_max = 4 if _single_src else 5
            if font is None or not lines or len(lines) > _k_max:
                return False
            bb = font.getbbox("آیگچ", stroke_width=sw)
            glyph_h = max(8, bb[3] - bb[1])
            line_h = glyph_h + 3
            K = len(lines)
            _fs0 = int(getattr(font, "size", 12))
            if os.environ.get("MANGA_DEBUG_ROT"):
                print(f"    [dbg-arc-render] r{getattr(region, 'id', '?')} "
                      f"rows={K} arc_len={arc_len:.0f} lh_src={lh_src:.0f} "
                      f"font={getattr(font, 'size', '?')} sag={curve.get('sag')} "
                      f"d_ang={curve.get('d_ang')}")
            for i, line in enumerate(lines):
                if not line.strip():
                    continue
                off = ((K - 1) / 2.0 - i) * line_h
                row_path = np.empty_like(path)
                for j in range(len(path)):
                    tj = tang[min(j, len(tang) - 1)]
                    nx_, ny_ = tj[1], -tj[0]
                    row_path[j, 0] = path[j, 0] + nx_ * off
                    row_path[j, 1] = path[j, 1] + ny_ * off
                row_segs = np.diff(row_path, axis=0)
                row_len = np.hypot(row_segs[:, 0], row_segs[:, 1])
                row_cum = np.concatenate([[0.0], np.cumsum(row_len)])
                row_total = float(row_cum[-1])
                row_tang = row_segs / np.maximum(row_len, 1e-6)[:, None]
                _f = font
                _sw_r = sw
                words = [self._shape_farsi(wd) for wd in line.split()]
                words = [wd for wd in words if wd]
                if not words:
                    continue
                space_w = float(_f.getlength(" ") if hasattr(_f, "getlength")
                                else _f.getbbox(" ")[2])
                wwidths = [float(draw.textbbox((0, 0), wd, font=_f,
                                               stroke_width=_sw_r)[2])
                           for wd in words]
                total = sum(wwidths) + space_w * (len(words) - 1)
                _tries = 0
                while total > row_total * 0.97 and _fs0 - _tries > 9 and _tries < 8:
                    _tries += 1
                    _f = self._load_font(_fs0 - _tries, style=style)
                    _sw_r = self._stroke_width_for(_fs0 - _tries)
                    wwidths = [float(draw.textbbox((0, 0), wd, font=_f,
                                                   stroke_width=_sw_r)[2])
                               for wd in words]
                    space_w = float(_f.getlength(" ") if hasattr(_f, "getlength")
                                    else _f.getbbox(" ")[2])
                    total = sum(wwidths) + space_w * (len(words) - 1)
                if total > row_total * 1.25:
                    continue
                cursor = (row_total + total) / 2.0
                _place = []
                for wi, wd in enumerate(words):
                    wwd = wwidths[wi]
                    cursor -= wwd / 2.0
                    s = float(np.clip(cursor, 0.0, row_total))
                    k = int(np.searchsorted(row_cum, s, side="right")) - 1
                    k = int(np.clip(k, 0, len(row_tang) - 1))
                    t_seg = float((s - row_cum[k]) / max(1e-6, row_len[k]))
                    cx_ = row_path[k, 0] + row_tang[k, 0] * t_seg * row_len[k]
                    cy_ = row_path[k, 1] + row_tang[k, 1] * t_seg * row_len[k]
                    ang_w = float(np.degrees(np.arctan2(row_tang[k, 1],
                                                        row_tang[k, 0])))
                    if abs(ang_w) > 75.0:
                        ang_w = 0.0
                    _wb = draw.textbbox((0, 0), wd, font=_f,
                                        stroke_width=_sw_r)
                    tw = int(_wb[2] - _wb[0]) + 2 * _sw_r + 8
                    th = int(_wb[3] - _wb[1]) + 2 * _sw_r + 8
                    tile = Image.new("RGBA", (max(8, tw), max(8, th)),
                                     (0, 0, 0, 0))
                    td = ImageDraw.Draw(tile)
                    td.text((-_wb[0] + _sw_r + 4, -_wb[1] + _sw_r + 4), wd,
                            font=_f,
                            fill=tuple(text_rgb)[:3] + (255,),
                            stroke_width=_sw_r,
                            stroke_fill=tuple(stroke_rgb)[:3] + (255,))
                    rot = tile.rotate(-ang_w, expand=True,
                                      resample=Image.BICUBIC)
                    _place.append((rot, cx_, cy_))
                    cursor -= (wwd / 2.0 + space_w)
                try:
                    _iw, _ih = pil_img.size
                    _xs0 = [cx_ - rot.size[0] / 2 for rot, cx_, cy_ in _place]
                    _xs1 = [cx_ + rot.size[0] / 2 for rot, cx_, cy_ in _place]
                    _ys0 = [cy_ - rot.size[1] / 2 for rot, cx_, cy_ in _place]
                    _ys1 = [cy_ + rot.size[1] / 2 for rot, cx_, cy_ in _place]
                    _dx = 0.0
                    if min(_xs0) < 0.0:
                        _dx = -min(_xs0)
                    elif max(_xs1) > float(_iw):
                        _dx = float(_iw) - max(_xs1)
                    _dy = 0.0
                    if min(_ys0) < 0.0:
                        _dy = -min(_ys0)
                    elif max(_ys1) > float(_ih):
                        _dy = float(_ih) - max(_ys1)
                    for rot, cx_, cy_ in _place:
                        rw_, rh_ = rot.size
                        pil_img.paste(
                            rot,
                            (int(cx_ - rw_ / 2 + _dx), int(cy_ - rh_ / 2 + _dy)),
                            rot)
                except Exception:
                    for rot, cx_, cy_ in _place:
                        rw_, rh_ = rot.size
                        pil_img.paste(rot, (int(cx_ - rw_ / 2),
                                            int(cy_ - rh_ / 2)), rot)
            return True
        except Exception:
            if os.environ.get("MANGA_DEBUG_ROT"):
                import traceback
                traceback.print_exc()
            return False
