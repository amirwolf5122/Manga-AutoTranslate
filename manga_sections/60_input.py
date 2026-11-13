# BUILD-STRIP-START
class _MangaTranslatorBody_60:
# BUILD-STRIP-END
    @staticmethod
    def _url_exists(url: str, headers: dict) -> bool:
        import requests
        try:
            r = requests.head(url, headers=headers, timeout=12, allow_redirects=True)
            if r.status_code == 200:
                ct = (r.headers.get("Content-Type") or "").lower()

                if ct.startswith("text/html"):
                    pass
                else:
                    return True
        except Exception:
            pass
        try:

            h = dict(headers)
            h["Range"] = "bytes=0-1023"
            r = requests.get(url, headers=h, timeout=15, allow_redirects=True, stream=True)
            ok = r.status_code in (200, 206)
            ct = (r.headers.get("Content-Type") or "").lower()
            r.close()
            if not ok:
                return False
            if ct.startswith("text/html"):
                return False
            return True
        except Exception:
            return False

    @staticmethod
    def _is_direct_image_url(url: str) -> bool:
        u = (url or "").strip()
        low = u.lower()
        path = low.split("?")[0]
        exts = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif")
        if any(path.endswith(e) for e in exts):
            return True
        if re.search(r"\.(jpe?g|png|webp|bmp|gif)(/|$)", path):
            return True
        if "gstatic.com/images" in low and "q=tbn:" in low:
            return True
        return False

    @staticmethod
    def _expand_input_urls(input_str: str) -> List[str]:
        import requests

        parts = [p.strip() for p in re.split(r"[,\n\r\t]+", input_str) if p.strip()]
        if not parts:
            return []

        expanded: List[str] = []
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

        _range_re = re.compile(
            r"^(?P<base>.+?)(?P<a>\d+)\s*(?P<op>[><])\s*(?P<b>\d+)"
            r"(?P<ext>\.[A-Za-z0-9]{2,5})?(?P<q>\?.*)?$"
        )

        for part in parts:
            _rm = _range_re.match(part)
            if _rm and "*" not in part:
                base = _rm.group("base")
                a = int(_rm.group("a"))
                b = int(_rm.group("b"))
                op = _rm.group("op")
                ext = _rm.group("ext") or ".jpg"
                q = _rm.group("q") or ""
                lo, hi = min(a, b), max(a, b)
                if hi - lo > 2000:
                    print(f"[!] بازه خیلی بزرگ نادیده گرفته شد: {part[:80]}")
                    continue
                nums = range(lo, hi + 1) if op == ">" else range(hi, lo - 1, -1)
                _found = [f"{base}{n}{ext}{q}" for n in nums]
                print(f"[*] بازهٔ لینک: {lo} {'→' if op == '>' else '←'} {hi} "
                      f"({len(_found)} صفحه)")
                expanded.extend(_found)
                continue

            if "*" not in part:
                expanded.append(part)
                continue

            m = re.search(r"(.*?)(\d*)\*(\d*)(.*)", part)
            if not m:
                print(f"[!] الگوی * قابل تشخیص نیست: {part}")
                expanded.append(part)
                continue

            prefix = m.group(1)
            suffix = m.group(4)

            is_page_glob = MangaTranslator._is_direct_image_url(suffix if suffix.startswith(".") else suffix + "x") or (
                suffix.lower().lstrip(".").split("?")[0] in ("jpg", "jpeg", "png", "webp", "bmp", "gif")
                or any(suffix.lower().endswith(e) for e in (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"))
            )

            label = "صفحه" if is_page_glob else "فصل"
            print(f"[*] در حال پیدا کردن {label}های موجود برای الگو: {part}")

            found = []
            consecutive_fail = 0
            max_fail = 5
            max_n = 500

            for n in range(1, max_n + 1):
                candidate = f"{prefix}{n}{suffix}"
                if MangaTranslator._url_exists(candidate, headers):
                    found.append(candidate)
                    consecutive_fail = 0
                    print(f"    [+] {label} {n} پیدا شد")
                else:
                    consecutive_fail += 1
                if consecutive_fail >= max_fail:
                    break

            if found:
                print(f"[*] مجموعاً {len(found)} {label} پیدا شد.")
                expanded.extend(found)
            else:
                print(f"[!] هیچ موردی با الگو پیدا نشد: {part}")

        seen = set()
        unique = []
        for u in expanded:
            if u not in seen:
                seen.add(u)
                unique.append(u)
        return unique
    @staticmethod
    def _normalize_image_url(url: str) -> str:
        if "github.com/" in url and "/blob/" in url:
            url = url.replace("github.com/", "raw.githubusercontent.com/").replace("/blob/", "/")
        return url

    @staticmethod
    def _is_junk_image_url(u: str) -> bool:
        low = u.lower()
        junk_parts = (
            "logo", "loading", "spinner", "placeholder", "avatar", "icon",
            "credits", "credit-", "watermark", "banner", "ads/", "/ad.",
            "radio", "vline", "favicon", "sprite", "emoji", "badge",
            "/static/", "data:image", ".svg", "tracking", "pixel",
            "1x1", "blank.", "transparent", "spacer",
        )
        if any(p in low for p in junk_parts):
            return True
        path = low.split("?")[0]
        if path.endswith((".js", ".css", ".html", ".php", ".json", ".xml")):
            return True
        return False

    @staticmethod
    def _extract_src_candidates(img_tag) -> List[str]:
        attrs = (
            "src", "data-src", "data-original", "data-lazy-src", "data-lazy",
            "data-url", "data-image", "data-full", "data-srcset", "srcset",
            "data-pagespeed-lazy-src", "data-orig-src",
        )
        found = []
        for a in attrs:
            val = img_tag.get(a)
            if not val:
                continue
            if "srcset" in a:
                for part in val.split(","):
                    part = part.strip().split()[0] if part.strip() else ""
                    if part:
                        found.append(part)
            else:
                found.append(val)
        return found

    @staticmethod
    def _natural_sort_key(path: str):
        name = os.path.basename(path)
        return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", name)]

    @staticmethod
    def _try_extend_sequential(urls: List[str], headers: dict, max_extra: int = 80) -> List[str]:
        import requests

        if len(urls) < 2:
            return urls

        pattern = re.compile(
            r"^(?P<prefix>.+/)(?P<num>\d+)(?P<suffix>\.(?:jpe?g|png|webp|gif))(?:\?.*)?$",
            re.I,
        )
        parsed = []
        for u in urls:
            m = pattern.match(u.split("?")[0])
            if m:
                parsed.append((int(m.group("num")), m.group("prefix"), m.group("suffix"), u))

        if len(parsed) < 2:
            return urls

        parsed.sort(key=lambda x: x[0])
        nums = [p[0] for p in parsed]
        if nums[-1] - nums[0] + 1 > len(nums) * 2:
            return urls

        prefix, suffix = parsed[0][1], parsed[0][2]
        if not all(p[1] == prefix and p[2].lower() == suffix.lower() for p in parsed):
            return urls

        end = max(nums)
        existing = set(nums)
        extra = []
        consecutive_fail = 0
        for n in range(end + 1, end + 1 + max_extra):
            if n in existing:
                consecutive_fail = 0
                continue
            candidate = f"{prefix}{n}{suffix}"
            try:
                r = requests.head(candidate, headers=headers, timeout=12, allow_redirects=True)
                if r.status_code == 200 and (r.headers.get("Content-Type") or "").startswith("image/"):
                    extra.append(candidate)
                    consecutive_fail = 0
                else:
                    consecutive_fail += 1
            except Exception:
                consecutive_fail += 1
            if consecutive_fail >= 3:
                break

        if extra:
            print(f"    [+] {len(extra)} تصویر اضافی با الگوی شماره‌ای پیدا شد.")
            return urls + extra
        return urls

    @staticmethod
    def _content_signature(content: bytes) -> str:
        try:
            head = bytes(content[:16])
        except Exception:
            return "؟"
        if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
            return "webp"
        if head[4:8] == b"ftyp":
            brand = head[8:12].decode("ascii", "ignore").strip() or "؟"
            _bl = brand.lower()
            if _bl in ("avif", "avis"):
                return "avif"
            if _bl in ("heic", "heix", "heim", "hevc", "mif1", "msf1"):
                return f"heic({brand})"
            return f"mp4({brand})"
        if head[:3] == b"\xff\xd8\xff":
            return "jpeg"
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            return "png"
        if head[:3] == b"GIF":
            return "gif"
        if head[:2] == b"BM":
            return "bmp"
        _low = head.lstrip().lower()
        if _low.startswith((b"<!doctype", b"<html", b"<body")):
            return "html"
        if head[:5] == b"<?xml":
            return "xml"
        if _low.startswith((b"{", b"[")):
            return "json"
        _txt = "".join(chr(b) if 32 <= b < 127 else "." for b in head[:12])
        return f"ناشناس[{_txt}]"

    @staticmethod
    def _android_decode_bytes(content: bytes) -> Optional[bytes]:
        src = None
        try:
            from android.graphics import (
                BitmapFactory, Bitmap, Canvas, Color,
            )
            from java.io import ByteArrayOutputStream
        except Exception:
            return None
        try:
            src = BitmapFactory.decodeByteArray(content, 0, len(content))
            if src is None:
                return None
            bm = src
            try:
                _alpha = bool(bm.hasAlpha())
            except Exception:
                _alpha = False
            if _alpha:
                base = Bitmap.createBitmap(
                    bm.getWidth(), bm.getHeight(), Bitmap.Config.ARGB_8888)
                _cv = Canvas(base)
                _cv.drawColor(Color.WHITE)
                _cv.drawBitmap(bm, 0.0, 0.0, None)
                bm = base
            baos = ByteArrayOutputStream()
            ok = bool(bm.compress(Bitmap.CompressFormat.JPEG, 92, baos))
            if not ok:
                return None
            raw = baos.toByteArray()
            out = bytes(raw) if not isinstance(raw, bytes) else raw
            return out or None
        except Exception:
            return None
        finally:
            try:
                if src is not None:
                    src.recycle()
            except Exception:
                pass

    @staticmethod
    def _webp_avif_magic(content: bytes) -> bool:
        try:
            if content is None or len(content) < 16:
                return False
            if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
                return True
            if content[4:8] == b"ftyp":
                return True
        except Exception:
            pass
        return False

    @staticmethod
    def _decode_image_bytes(content: bytes):
        _prefer_pillow = (_on_android()
                          and MangaTranslator._webp_avif_magic(content))
        if not _prefer_pillow:
            arr = np.frombuffer(content, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is not None:
                return img, None
        _rgb = None
        try:
            from io import BytesIO
            from PIL import Image
            with Image.open(BytesIO(content)) as _im:
                _im.load()
                _rgb = np.asarray(_im.convert("RGB"), dtype=np.uint8)
        except Exception:
            _rgb = None
        if _rgb is None:
            _jpg = MangaTranslator._android_decode_bytes(content)
            if _jpg:
                _img2 = cv2.imdecode(
                    np.frombuffer(_jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                if _img2 is not None:
                    return _img2, _jpg
            return None, None
        img = cv2.cvtColor(_rgb, cv2.COLOR_RGB2BGR)
        ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
        if not ok:
            return None, None
        return img, buf.tobytes()

    @staticmethod
    def _imread_any(path: str):
        if _on_android():
            try:
                with open(path, "rb") as _fmg:
                    if MangaTranslator._webp_avif_magic(_fmg.read(16)):
                        with open(path, "rb") as _f:
                            img, _rb = MangaTranslator._decode_image_bytes(
                                _f.read())
                        if img is not None:
                            return img
            except Exception:
                pass
        try:
            img = cv2.imread(path, cv2.IMREAD_COLOR)
        except Exception:
            img = None
        if img is not None:
            return img
        try:
            with open(path, "rb") as f:
                img, _reblob = MangaTranslator._decode_image_bytes(f.read())
        except Exception:
            return None
        return img

    @staticmethod
    def _normalize_input_image_file(path: str, dest_dir: Optional[str] = None) -> str:
        _ext_norm = os.path.splitext(path)[1].lower()
        _force_chain = (_on_android() and _ext_norm in (
            ".webp", ".avif", ".heif", ".heic"))
        if not _force_chain and _on_android():
            try:
                with open(path, "rb") as _fmg:
                    _force_chain = MangaTranslator._webp_avif_magic(
                        _fmg.read(16))
            except Exception:
                pass
        if not _force_chain:
            try:
                if cv2.imread(path, cv2.IMREAD_COLOR) is not None:
                    return path
            except Exception:
                pass
        try:
            with open(path, "rb") as f:
                content = f.read()
        except Exception:
            return path
        img, jpg = MangaTranslator._decode_image_bytes(content)
        if img is None:
            return path
        out_dir = dest_dir or os.path.dirname(path) or "."
        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception:
            out_dir = os.path.dirname(path) or "."
        stem = os.path.splitext(os.path.basename(path))[0].strip() or "page"
        stem = re.sub(r'[\\/:*?"<>|]+', "_", stem)[:80]
        out_file = os.path.join(out_dir, f"{stem}.jpg")
        _k = 2
        while os.path.exists(out_file):
            out_file = os.path.join(out_dir, f"{stem}-{_k}.jpg")
            _k += 1
        try:
            if jpg:
                with open(out_file, "wb") as f:
                    f.write(jpg)
            else:
                ok, buf = cv2.imencode(
                    ".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
                if not ok:
                    return path
                with open(out_file, "wb") as f:
                    f.write(buf.tobytes())
        except Exception:
            return path
        return out_file

    @staticmethod
    def _download_images_from_url(url: str, dest_dir: str,
                                  shared_seen: Optional[set] = None) -> List[str]:
        import requests
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin, urlparse

        _t_dl = time.time()
        os.makedirs(dest_dir, exist_ok=True)
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": url,
        }
        url = MangaTranslator._normalize_image_url(url)

        use_numeric_sort = False

        def _predict_stem(_u: str, _idx: int) -> str:
            _b = os.path.splitext(os.path.basename(urlparse(_u).path))[0]
            _b = re.sub(r'[\\/:*?"<>|]+', "_", _b).strip("._ ")[:80]
            if (not use_numeric_sort) and _b:
                return f"{_idx:03d}_{_b}"
            return _b or f"page_{_idx:03d}"

        def _cached_page(_u: str, _idx: int) -> Optional[str]:
            try:
                _stem_p = _predict_stem(_u, _idx)
                for _e in (".jpg", ".jpeg", ".png", ".webp"):
                    _c = os.path.join(dest_dir, _stem_p + _e)
                    if os.path.isfile(_c) and os.path.getsize(_c) > 0:
                        return _c
            except Exception:
                return None
            return None

        try:
            if os.path.splitext(urlparse(url).path)[1].lower() in IMAGE_EXTS:
                _pre = _cached_page(url, 1)
                if _pre:
                    print("    1 تصویر از کشِ دانلود (بدونِ شبکه).")
                    return [_pre]
        except Exception:
            pass

        def _save_bytes(content: bytes, index: int, hint_url: str = "") -> Optional[str]:
            ext = os.path.splitext(urlparse(hint_url or url).path)[1].lower()
            if ext not in IMAGE_EXTS:
                if content[:3] == b"\xff\xd8\xff":
                    ext = ".jpg"
                elif content[:8] == b"\x89PNG\r\n\x1a\n":
                    ext = ".png"
                elif content[:4] == b"RIFF" and content[8:12] == b"WEBP":
                    ext = ".webp"
                else:
                    ext = ".jpg"

            img, _reblob = MangaTranslator._decode_image_bytes(content)
            if img is None:
                return None
            if _reblob is not None:
                content, ext = _reblob, ".jpg"
            h, w = img.shape[:2]
            if min(h, w) < 80 or max(h, w) < 200:
                return None

            _base = os.path.splitext(os.path.basename(urlparse(hint_url or url).path))[0]
            _base = re.sub(r'[\\/:*?"<>|]+', "_", _base).strip("._ ")[:80]
            _stem = _base or f"page_{index:03d}"
            if (not use_numeric_sort) and _base:
                _stem = f"{index:03d}_{_base}"
            out_file = os.path.join(dest_dir, f"{_stem}{ext}")
            _n = 1
            while os.path.isfile(out_file):
                _same = False
                try:
                    _same = (os.path.getsize(out_file) == len(content))
                    if _same:
                        with open(out_file, "rb") as _fold:
                            _old_head = _fold.read(4096)
                        _same = (_old_head == content[:len(_old_head)])
                except Exception:
                    _same = False
                if _same:
                    return out_file
                _n += 1
                out_file = os.path.join(dest_dir, f"{_stem}-{_n}{ext}")
            with open(out_file, "wb") as f:
                f.write(content)
            return out_file

        path_ext = os.path.splitext(urlparse(url).path)[1].lower()
        resp = requests.get(url, headers=headers, timeout=60, stream=True)
        resp.raise_for_status()
        content_type = (resp.headers.get("Content-Type") or "").lower()
        is_direct_image = (
            path_ext in IMAGE_EXTS
            or content_type.startswith("image/")
        )

        if is_direct_image:
            content = resp.content
            saved_path = _save_bytes(content, 1, url)
            if saved_path:
                print(f"    1 تصویر مستقیم از لینک دانلود شد.")
                return [saved_path]
            _last = content
            try:
                _alt = dict(headers)
                _alt["Accept"] = "image/jpeg,image/png,image/webp,*/*;q=0.8"
                _alt.pop("Referer", None)
                _r2 = requests.get(url, headers=_alt, timeout=60)
                _r2.raise_for_status()
                if _r2.content:
                    _last = _r2.content
                    saved_path = _save_bytes(_last, 1, url)
                    if saved_path:
                        print("    1 تصویر مستقیم از لینک دانلود شد (تلاشِ دوم).")
                        return [saved_path]
            except Exception:
                pass
            _sig = MangaTranslator._content_signature(_last)
            _msg = (f"محتوای لینک تصویر معتبر نبود: {url} "
                    f"[HTTP {resp.status_code}، نوع: {content_type or 'نامشخص'}، "
                    f"{len(_last)} بایت، امضا: {_sig}]")
            print(f"[!] {_msg}")
            raise ValueError(_msg)

        soup = BeautifulSoup(resp.content, "html.parser")
        img_urls, seen = [], set()
        raw_html = resp.text if hasattr(resp, "text") else resp.content.decode("utf-8", errors="ignore")

        json_page_urls = []
        for m in re.finditer(
            r"https?://[^\"'\\s<>]+?\.(?:jpe?g|png|webp)(?:\?[^\"'\\s<>]*)?",
            raw_html,
            flags=re.I,
        ):
            cand = m.group(0).rstrip("\\").replace("\\/", "/")
            low = cand.lower()
            if any(k in low for k in ("/chapter", "/chapters/", "/comic/", "/manga/", "/pages/", "/sv2/")):
                if not MangaTranslator._is_junk_image_url(cand):
                    json_page_urls.append(MangaTranslator._normalize_image_url(cand))

        if json_page_urls:
            for u in json_page_urls:
                key = u.split("?")[0].lower()
                if key in seen:
                    continue
                seen.add(key)
                img_urls.append(u)
            print(f"    [*] {len(img_urls)} صفحه از JSON/HTML به ترتیب پیدا شد.")

        for img in soup.find_all("img"):
            for src in MangaTranslator._extract_src_candidates(img):
                if not src or src.startswith("data:"):
                    continue
                full_url = MangaTranslator._normalize_image_url(urljoin(url, src))
                key = full_url.split("?")[0].lower()
                if key in seen:
                    continue
                if MangaTranslator._is_junk_image_url(full_url):
                    continue
                seen.add(key)
                img_urls.append(full_url)

        for a in soup.find_all("a", href=True):
            href = a["href"]
            low = href.lower().split("?")[0]
            if any(low.endswith(e) for e in (".jpg", ".jpeg", ".png", ".webp")):
                full_url = MangaTranslator._normalize_image_url(urljoin(url, href))
                key = full_url.split("?")[0].lower()
                if key not in seen and not MangaTranslator._is_junk_image_url(full_url):
                    seen.add(key)
                    img_urls.append(full_url)

        if not img_urls:
            print("    [!] هیچ تگ تصویری معتبری در صفحه پیدا نشد.")
            return []

        img_urls = MangaTranslator._try_extend_sequential(img_urls, headers)

        deduped = []
        seen_u = set()
        for u in img_urls:
            key = u.split("?")[0].lower()
            if key in seen_u:
                continue
            seen_u.add(key)
            deduped.append(u)
        img_urls = deduped

        numbered = []
        for u in img_urls:
            m = re.search(r"/(\d+)\.(?:jpe?g|png|webp)(?:\?|$)", u.lower())
            if m:
                numbered.append(True)
            else:
                numbered.append(False)
        use_numeric_sort = sum(numbered) >= max(3, int(len(img_urls) * 0.6))

        if use_numeric_sort:
            def _page_sort_key(u: str):
                low = u.lower().split("?")[0]
                if any(k in low for k in ("/chapter", "/chapters/", "/comic/", "/manga/", "/pages/")):
                    pri = 0
                elif re.search(r"/\d+\.(jpe?g|png|webp)$", low):
                    pri = 1
                else:
                    pri = 2
                m = re.search(r"/(\d+)\.(?:jpe?g|png|webp)$", low)
                num = int(m.group(1)) if m else 10**9
                return (pri, num, low)

            img_urls = sorted(img_urls, key=_page_sort_key)
            print(f"    [*] مرتب‌سازی عددی صفحات ({len(img_urls)} تصویر).")
        else:
            print(f"    [*] ترتیب HTML حفظ شد ({len(img_urls)} تصویر، بدون شماره ترتیبی).")

        if shared_seen is not None and img_urls:
            _b = len(img_urls)
            img_urls = [u for u in img_urls
                        if u.split("?")[0].lower() not in shared_seen]
            if _b > len(img_urls):
                print(f"    [*] {_b - len(img_urls)} تصویر مشترک با فصلِ "
                      f"قبلی (کاور/بنرِ سری) رد شد.")
            for u in img_urls:
                shared_seen.add(u.split("?")[0].lower())

        _sess = requests.Session()
        try:
            _ad = requests.adapters.HTTPAdapter(
                pool_connections=8, pool_maxsize=8, max_retries=1)
            _sess.mount("https://", _ad)
            _sess.mount("http://", _ad)
        except Exception:
            pass

        def _fetch_page(_u: str) -> Optional[bytes]:
            try:
                _r = _sess.get(_u, headers=headers, timeout=60)
                if _r.status_code != 200:
                    print(f"    [!] رد شد ({_u[:90]}…): HTTP {_r.status_code}")
                    return None
                return _r.content
            except Exception as e:
                print(f"    [!] رد شد ({_u[:90]}…): {e}")
                return None

        _dl_workers = max(2, min(
            8, len(img_urls),
            int(os.environ.get("MANGA_DL_WORKERS") or 6)))
        _reused: list = []
        _fetch_list: list = []
        for _i, _u in enumerate(img_urls, 1):
            _hit = _cached_page(_u, _i)
            _reused.append(_hit)
            if _hit is None:
                _fetch_list.append(_u)
        if len(_fetch_list) < len(img_urls):
            print(f"    [*] {len(img_urls) - len(_fetch_list)} صفحه از کشِ "
                  f"دانلود (بدونِ شبکه) — {len(_fetch_list)} صفحه می‌ماند.")
        _dl_map = {}
        if _fetch_list:
            with ThreadPoolExecutor(max_workers=_dl_workers) as _dex:
                for _u, _c in zip(_fetch_list,
                                  _dex.map(_fetch_page, _fetch_list)):
                    _dl_map[_u] = _c
        saved = []
        for _i, img_url in enumerate(img_urls, 1):
            if _reused[_i - 1]:
                saved.append(_reused[_i - 1])
                continue
            _content = _dl_map.get(img_url)
            if not _content:
                continue
            path = _save_bytes(_content, _i, img_url)
            if path:
                saved.append(path)

        print(f"    {len(saved)} تصویر از {url} دانلود شد "
              f"({time.time() - _t_dl:.1f}s).")
        return saved

    @staticmethod
    def _auto_output_path(input_path: str, output_spec: str) -> str:
        spec = (output_spec or "").strip()
        is_ext_only = (
            spec.startswith(".")
            and "/" not in spec
            and "\\" not in spec
            and re.fullmatch(r"\.(pdf|zip|html|psd)", spec, re.I) is not None
        )
        if not is_ext_only:
            return output_spec

        ext = spec.lower()
        raw_in = (input_path or "").strip()
        raw_in = re.split(r"[,\n\r\t]+", raw_in)[0].strip()
        if MangaTranslator._is_url(raw_in):
            from urllib.parse import urlparse, unquote
            path = unquote(urlparse(raw_in).path).strip("/")
            parts = [p for p in path.split("/") if p and p != "*"]
            base = "chapter"
            if parts:
                while parts and (
                    parts[-1].startswith("*")
                    or re.search(r"(?i)\.(jpe?g|png|webp|gif|bmp)(\?.*)?$", parts[-1])
                ):
                    parts.pop()

                if parts and re.fullmatch(r"\d+", parts[-1] or ""):
                    parts.pop()
                slug = parts[-1] if parts else "chapter"
                if re.search(r"(?i)^chapter[-_]?\d+$", slug) or re.search(
                    r"(?i)chapter[-_]?\d+", slug
                ):
                    series = parts[-2] if len(parts) >= 2 else ""
                    base = f"{series}-{slug}" if series else slug
                elif "chapter" in [p.lower() for p in parts]:
                    low_parts = [p.lower() for p in parts]
                    try:
                        idx = low_parts.index("chapter")
                        name = parts[idx - 1] if idx > 0 else "chapter"
                        num = parts[idx + 1] if idx + 1 < len(parts) else ""
                        num = re.sub(r"[^\w\-]", "", num.split("?")[0])
                        base = f"{name}-{num}" if num else name
                    except ValueError:
                        base = slug
                else:
                    base = slug
            base = re.sub(r"\*+", "", base)
            base = re.sub(r"(?i)\.(jpe?g|png|webp|gif|bmp)$", "", base)
            base = re.sub(r"[^\w\-.]+", "-", base)
            base = re.sub(r"-{2,}", "-", base).strip("-._")
            if not base:
                base = "chapter"
        else:
            raw = raw_in.rstrip("/\\")
            base = os.path.splitext(os.path.basename(raw))[0] or "output"
            base = re.sub(r"\*+", "", base)
            base = re.sub(r"[^\w\-.]+", "-", base).strip("-._") or "output"

        return base + ext

    @staticmethod
    def _extract_zip(zip_path: str, dest_dir: str) -> List[str]:
        os.makedirs(dest_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(dest_dir)
        files = []
        for root, _, names in os.walk(dest_dir):
            for name in names:
                if os.path.splitext(name)[1].lower() in IMAGE_EXTS:
                    files.append(os.path.join(root, name))
        return sorted(files, key=MangaTranslator._natural_sort_key)
