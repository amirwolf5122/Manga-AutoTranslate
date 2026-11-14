# BUILD-STRIP-START
class _MangaTranslatorBody_90:
# BUILD-STRIP-END
    @staticmethod
    def _fa_probe_text() -> str:
        if MangaTranslator._FA_PROBE_CACHE is not None:
            return MangaTranslator._FA_PROBE_CACHE
        letters = "ابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهیآأإئءؤئةی"
        parts: List[str] = []
        for _L in letters:
            parts += [_L, _L + _L, "ب" + _L + "ب", "ب" + _L, _L + "ب"]
        sample = " ".join(parts) + " ۰۱۲۳۴۵۶۷۸۹ 0123456789 .,!?…:;()«»-"
        try:
            shaped = get_display(arabic_reshaper.reshape(sample))
        except Exception:
            shaped = sample
        txt = "".join(sorted({c for c in shaped
                              if not c.isspace() and c != "\u200c"}))
        txt += "\uFEF5\uFEF6\uFEF7\uFEF8\uFEFB\uFEFC"
        MangaTranslator._FA_PROBE_CACHE = txt
        return txt

    @staticmethod
    def _font_covers(path: str) -> bool:
        if not path or not os.path.isfile(path):
            return False
        key = os.path.abspath(path)
        cached = MangaTranslator._FONT_COVER_CACHE.get(key)
        if cached is not None:
            return cached
        ok = True
        try:
            f = ImageFont.truetype(path, 32)

            def _rb(ch: str) -> bytes:
                im = Image.new("L", (96, 96), 0)
                ImageDraw.Draw(im).text((24, 24), ch, font=f, fill=255)
                return im.tobytes()

            refs = {_rb("\uE0FA"), _rb("\uE0F9"), _rb("\uE0EF")}
            for _ch in MangaTranslator._fa_probe_text():
                b = _rb(_ch)
                if not any(b) or b in refs:
                    ok = False
                    break
        except Exception:
            ok = True
        MangaTranslator._FONT_COVER_CACHE[key] = ok
        return ok

    def _warn_font(self, key: str, msg: str) -> None:
        seen = getattr(self, "_font_warned", None)
        if seen is None:
            seen = set()
            self._font_warned = seen
        if key not in seen:
            seen.add(key)
            print(msg)

    def _cover_fallback_font(self, exclude: str) -> str:
        cands: List[str] = []
        d = os.path.dirname(os.path.abspath(exclude or self.font_path or ""))
        try:
            if os.path.isdir(d):
                cands += [os.path.join(d, f) for f in sorted(os.listdir(d))
                          if f.lower().endswith((".ttf", ".otf"))]
        except Exception:
            pass
        cands += [
            "/system/fonts/NotoNaskhArabic-Regular.ttf",
            "/system/fonts/NotoNaskhArabicUI-Regular.ttf",
            "/system/fonts/NotoSansArabic-Regular.ttf",
            "/system/fonts/NotoSansArabicUI-Regular.ttf",
            "/system/fonts/DroidSansArabic.ttf",
            "/system/fonts/NotoNaskhArabic-Bold.ttf",
        ]
        ex = os.path.abspath(exclude) if exclude else ""
        for c in cands:
            if os.path.isfile(c) and os.path.abspath(c) != ex and self._font_covers(c):
                return c
        return ""

    def _load_font(self, size: int, style: str = "") -> ImageFont.FreeTypeFont:
        path = self.font_path
        if style:
            cand = (getattr(self, "font_by_style", None) or {}).get(style) or path
            if cand and os.path.isfile(cand):
                if self._font_covers(cand):
                    path = cand
                else:
                    self._warn_font(
                        "style:" + style,
                        f"[!] فونت لحن «{style}» ({os.path.basename(cand)}) گلیف‌های "
                        f"فارسی را کامل ندارد (به‌جای حرف مربع می‌افتاد) → فونت اصلی.")
        if not self._font_covers(path):
            alt = self._cover_fallback_font(path)
            if alt:
                self._warn_font(
                    "main:" + str(path),
                    f"[!] فونت اصلی ({os.path.basename(str(path))}) حروف فارسی را کامل "
                    f"ندارد → {os.path.basename(alt)}")
                path = alt
        return ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.BASIC)

    @staticmethod
    def _stroke_width_for(size: int) -> int:

        if size <= 14:
            return 1
        if size <= 22:
            return 2
        return max(2, size // 16)

    def _max_font_for_region(self, region: "TextRegion") -> int:

        polys = list(getattr(region, "ocr_polys", None) or []) or list(getattr(region, "boxes", None) or [])
        if not polys:
            return 48
        try:
            ang = float(getattr(region, "angle", 0.0) or 0.0)
        except (TypeError, ValueError):
            ang = 0.0
        a = np.deg2rad(ang)
        ca, sa = np.cos(-a), np.sin(-a)
        hs: List[float] = []
        for p in polys:
            try:
                pts = np.asarray(p, dtype=np.float32).reshape(-1, 2)
            except Exception:
                continue
            if pts.shape[0] < 2:
                continue
            rot = np.empty_like(pts)
            rot[:, 0] = pts[:, 0] * ca - pts[:, 1] * sa
            rot[:, 1] = pts[:, 0] * sa + pts[:, 1] * ca
            hs.append(float(rot[:, 1].max() - rot[:, 1].min()))
        if not hs:
            return 48
        h_line = float(np.median(hs))
        if h_line <= 2:
            return 48

        return int(np.clip(round(h_line * 1.2), 12, 48))

    def _wrap_and_fit(
        self, draw: ImageDraw.ImageDraw, text: str, max_w: int, max_h: int,
        style: str = "", max_size: int = 48,
    ) -> Tuple[ImageFont.FreeTypeFont, List[str], int]:

        words = text.split()
        if not words:
            words = [""]
        _segments = [s.strip() for s in str(text).split("\n")]
        _segments = [s for s in _segments if s] or [str(text).strip() or " "]

        def wrap_at(size: int, line_gap: int):
            font = self._load_font(size, style=style)
            sw = self._stroke_width_for(size)

            usable_w = max(8, max_w - 2 * sw)
            lines: List[str] = []
            for seg in _segments:
                seg_words = seg.split()
                if not seg_words:
                    lines.append("")
                    continue
                current = ""
                for word in seg_words:
                    candidate = f"{current} {word}".strip()
                    w = draw.textbbox(
                        (0, 0), self._shape_farsi(candidate), font=font, stroke_width=sw
                    )[2]
                    if w <= usable_w or not current:
                        current = candidate
                    else:
                        lines.append(current)
                        current = word
                if current:
                    lines.append(current)

            bb = font.getbbox("آیگچ", stroke_width=sw)
            glyph_h = bb[3] - bb[1]
            line_h = glyph_h + line_gap
            total_h = line_h * len(lines) if lines else line_h

            total_h += 2 * sw
            widest = max(
                (
                    draw.textbbox(
                        (0, 0), self._shape_farsi(l), font=font, stroke_width=sw
                    )[2]
                    for l in lines
                ),
                default=0,
            )
            return font, lines, sw, total_h, widest, line_h

        n_words = len(words)
        short_text = n_words <= 2 and sum(len(w) for w in words) <= 12
        min_size = 14 if short_text else 11
        max_size = max(min_size, min(48, int(max_size or 48)))

        smallest_attempt = None

        for line_gap in (4, 2, 1, 0):
            for size in range(max_size, min_size - 1, -1):
                font, lines, sw, total_h, widest, line_h = wrap_at(size, line_gap)
                smallest_attempt = (font, lines, sw, line_h)
                if total_h <= max_h and widest <= max_w:
                    return font, lines, sw

        for size in range(min_size - 1, 5, -1):
            font, lines, sw, total_h, widest, line_h = wrap_at(size, 0)
            smallest_attempt = (font, lines, sw, line_h)
            if total_h <= max_h and widest <= max_w:
                return font, lines, sw

        if smallest_attempt is None:
            font = self._load_font(11, style=style)
            sw = self._stroke_width_for(11)
            return font, [" ".join(words)], sw
        return smallest_attempt[0], smallest_attempt[1], smallest_attempt[2]

    @staticmethod
    def _pick_text_and_stroke(
        cleaned: np.ndarray, original: np.ndarray, region: TextRegion
    ) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
        h_img, w_img = original.shape[:2]
        x, y, w, h = region.rect
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(w_img, x + w), min(h_img, y + h)

        poly_mask = np.zeros((h_img, w_img), dtype=np.uint8)
        for poly in region.boxes:
            cv2.fillPoly(poly_mask, [poly], 255)

        local_mask = poly_mask[y0:y1, x0:x1]
        local_orig = original[y0:y1, x0:x1]
        local_clean = cleaned[y0:y1, x0:x1] if cleaned is not None else local_orig

        if local_orig.size == 0:
            return (15, 15, 15), (255, 255, 255)

        if local_clean.size > 0:
            bg_gray = float(np.median(cv2.cvtColor(local_clean, cv2.COLOR_BGR2GRAY)))
        else:
            bg_gray = 128.0

        orig_gray = cv2.cvtColor(local_orig, cv2.COLOR_BGR2GRAY).astype(np.float32)
        if bg_gray < 128:
            ink_m = (orig_gray > bg_gray + 20) & (local_mask > 0)
        else:
            ink_m = (orig_gray < bg_gray - 20) & (local_mask > 0)

        ink_pixels = local_orig[ink_m]

        if len(ink_pixels) >= 8:
            bgr = np.median(ink_pixels, axis=0)
            r, g, b = int(bgr[2]), int(bgr[1]), int(bgr[0])

            mx, mn = max(r, g, b), min(r, g, b)
            saturation = mx - mn
            lum = 0.299 * r + 0.587 * g + 0.114 * b

            if saturation < 25:
                if bg_gray >= 140:
                    text_rgb = (18, 18, 18)
                    stroke_rgb = (255, 255, 255)
                else:
                    text_rgb = (245, 245, 245)
                    stroke_rgb = (10, 10, 10)
            else:
                text_rgb = (r, g, b)
                if lum >= 140:
                    stroke_rgb = (20, 20, 20)
                else:
                    stroke_rgb = (255, 255, 255)
        else:
            if bg_gray >= 140:
                text_rgb, stroke_rgb = (18, 18, 18), (255, 255, 255)
            else:
                text_rgb, stroke_rgb = (245, 245, 245), (10, 10, 10)

        return text_rgb, stroke_rgb

    def render_translations(self, image: np.ndarray, regions: List[TextRegion],
                            original_image: np.ndarray) -> np.ndarray:
        pil_img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)

        for region in regions:
            if not region.translated_text:
                continue

            try:
                self._render_one_region(pil_img, draw, image, original_image, region)
            except Exception as e:
                print(f"  [!] رندر ناحیه {region.id} خطا داد ({e}) → فال‌بک…")
                _done = False
                try:
                    import gc as _gc
                    _gc.collect()
                    self._render_one_region(pil_img, draw, image, original_image, region)
                    _done = True
                    print(f"  [+] ناحیه {region.id} در تلاشِ دوم رندر شد.")
                except Exception:
                    pass
                if not _done:
                    try:
                        self._render_one_region_fallback(
                            pil_img, draw, image, original_image, region)
                        _done = True
                        print(f"  [+] ناحیه {region.id} با رندرِ فال‌بک رندر شد.")
                    except Exception as _eb:
                        print(f"  [!] فال‌بکِ ناحیه {region.id} هم مرد ({_eb})")
                if not _done:
                    try:
                        self._restore_region_pixels(
                            pil_img, image, original_image, region)
                        print(f"  [+] ناحیه {region.id} به پیکسلهایِ اصلی برگشت (حبابِ سیاه ساخته نشد).")
                    except Exception as _ec:
                        print(f"  [!] بازگردانیِ ناحیه {region.id} ناموفق ({_ec})")
                continue

        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    def _render_one_region_fallback(self, pil_img, draw, image,
                                    original_image, region) -> None:
        txt = str(getattr(region, "translated_text", "") or "").strip()
        if not txt:
            return
        try:
            x, y, w, h = region.rect
            x, y, w, h = int(x), int(y), int(w), int(h)
        except Exception:
            return
        try:
            text_rgb, stroke_rgb = self._pick_text_and_stroke(
                image, original_image, region)
        except Exception:
            text_rgb, stroke_rgb = (255, 255, 255), (0, 0, 0)
        sw = 0
        try:
            font = self._load_font(
                max(10, min(48, max(12, h // 3))),
                (getattr(region, "bubble_style", None) or ""))
        except Exception:
            font = self._load_font(18)
        try:
            raw_lines = [s for s in txt.splitlines() if s.strip()] or [txt]
        except Exception:
            raw_lines = [txt]
        max_w = max(20, w - 8)
        lines = []
        for _ln in raw_lines:
            try:
                _sh = self._shape_farsi(_ln.strip())
            except Exception:
                _sh = _ln.strip()
            try:
                _lw = draw.textbbox((0, 0), _sh, font=font,
                                    stroke_width=sw)[2]
            except Exception:
                _lw = 0
            if _lw <= max_w or not _sh:
                lines.append(_sh)
                continue
            _cur = ""
            for _wd in _sh.split(" "):
                _cand = (_cur + " " + _wd).strip()
                try:
                    _cw = draw.textbbox((0, 0), _cand, font=font,
                                        stroke_width=sw)[2]
                except Exception:
                    _cw = 0
                if _cur and _cw > max_w:
                    lines.append(_cur)
                    _cur = _wd
                else:
                    _cur = _cand
            if _cur:
                lines.append(_cur)
        if not lines:
            lines = [txt]
        try:
            _lh = font.getbbox("آیگ", stroke_width=sw)[3] + 6
        except Exception:
            _lh = (getattr(font, "size", 16) or 16) + 8
        total_h = _lh * len(lines)
        _ty = max(0, y + max(0, (h - total_h) // 2))
        for _ln in lines:
            try:
                _tw = draw.textbbox((0, 0), _ln, font=font,
                                    stroke_width=sw)[2]
            except Exception:
                _tw = 0
            _tx = max(0, x + max(0, (w - _tw) // 2))
            draw.text((_tx, _ty), _ln, font=font,
                      fill=tuple(text_rgb)[:3],
                      stroke_width=sw,
                      stroke_fill=tuple(stroke_rgb)[:3])
            _ty += _lh

    def _restore_region_pixels(self, pil_img, image, original_image,
                               region) -> None:
        try:
            x, y, w, h = region.rect
            x, y, w, h = int(x), int(y), int(w), int(h)
        except Exception:
            return
        H, W = original_image.shape[:2]
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(W, x + w), min(H, y + h)
        if x1 - x0 < 2 or y1 - y0 < 2:
            return
        _crop = original_image[y0:y1, x0:x1]
        _rgb = cv2.cvtColor(_crop, cv2.COLOR_BGR2RGB)
        pil_img.paste(Image.fromarray(_rgb), (x0, y0))

    def _rescue_reread_blocked(self, region, text: str,
                               regions, polys=None) -> bool:
        try:
            rx, ry, rw, rh = [float(v) for v in region.rect]
            rb = (rx, ry, rx + rw, ry + rh)

            def _n(s) -> str:
                return re.sub(r"[^0-9a-z\u0600-\u06ff\u3040-\u30ff"
                              r"\u3400-\u9fff\uac00-\ud7af]+",
                              "", str(s or "").lower())
            _nt = _n(text)
            _pl = list(polys or [])
            for o in regions:
                if o is region:
                    continue
                if not (getattr(o, "source_text", "") or "").strip():
                    continue
                try:
                    ox, oy, ow, oh = [float(v) for v in o.rect]
                except Exception:
                    continue
                ob = (ox, oy, ox + ow, oy + oh)
                _ix = max(0.0, min(rb[2], ob[2]) - max(rb[0], ob[0]))
                _iy = max(0.0, min(rb[3], ob[3]) - max(rb[1], ob[1]))
                if _ix * _iy <= 0.0:
                    continue
                if _nt and len(_nt) >= 5 and _nt in _n(o.source_text):
                    return True
                if _pl:
                    _ta = _ca = 0.0
                    for p in _pl:
                        try:
                            pp = np.asarray(p, np.float32).reshape(-1, 2)
                            bx0 = float(pp[:, 0].min())
                            by0 = float(pp[:, 1].min())
                            bx1 = float(pp[:, 0].max())
                            by1 = float(pp[:, 1].max())
                            pa = max(1.0, (bx1 - bx0) * (by1 - by0))
                            pin = 0.0
                            for op in (getattr(o, "ocr_polys", None) or []):
                                try:
                                    qq = np.asarray(op, np.float32).reshape(-1, 2)
                                    qx0 = float(qq[:, 0].min())
                                    qy0 = float(qq[:, 1].min())
                                    qx1 = float(qq[:, 0].max())
                                    qy1 = float(qq[:, 1].max())
                                    iw = max(0.0, min(bx1, qx1) - max(bx0, qx0))
                                    ih = max(0.0, min(by1, qy1) - max(by0, qy0))
                                    if iw * ih > 0:
                                        pin = max(pin, (iw * ih) / pa)
                                except Exception:
                                    continue
                            iw2 = max(0.0, min(bx1, ob[2]) - max(bx0, ob[0]))
                            ih2 = max(0.0, min(by1, ob[3]) - max(by0, ob[1]))
                            if iw2 * ih2 > 0:
                                pin = max(pin, (iw2 * ih2) / pa)
                            _ta += pa
                            _ca += pa * min(1.0, pin)
                        except Exception:
                            continue
                    if _ta > 0.0 and _ca / _ta >= 0.55:
                        return True
            return False
        except Exception:
            return False

    def _rescue_empty_ocr(self, image: np.ndarray,
                               regions: List[TextRegion]) -> None:
        _resc = 0
        for _r in regions:
            if (_r.source_text or "").strip() \
                    or not getattr(_r, "ocr_empty", False):
                continue
            try:
                _rx, _ry, _rw, _rh = [
                    int(v) for v in _r.rect]
                _oc = self._ocr_crop(
                    image, (_rx, _ry,
                            _rx + _rw, _ry + _rh), page_cache={})
                _t2 = (_oc[0] or "").strip()
                _p2 = list(_oc[1] or []) if len(_oc) > 1 else []
            except Exception:
                _t2, _p2 = "", []
            if not _t2:
                try:
                    _crop = image[
                        max(0, _ry):_ry + _rh,
                        max(0, _rx):_rx + _rw]
                    if _crop.size:
                        _res2 = None
                        try:
                            _res2 = self.ocr.ocr(
                                cv2.bitwise_not(_crop))
                        except Exception:
                            _res2 = None
                        _txts = []
                        if _res2:
                            for _ln in (_res2[0] or []):
                                try:
                                    _tv = _ln[1]
                                    if isinstance(_tv, (tuple, list)):
                                        _tv = _tv[0]
                                    if str(_tv).strip():
                                        _txts.append(
                                            str(_tv).strip())
                                except Exception:
                                    continue
                        _t2 = " ".join(_txts).strip()
                except Exception:
                    pass
            _lt = sum(1 for _c in _t2
                         if _c.isascii() and _c.isalpha())
            if _t2 and _lt >= 2 and \
                    _lt * 2 >= len(_t2.replace(" ", "")):
                if self._rescue_reread_blocked(
                        _r, _t2, regions, polys=(_p2 or None)):
                    if self.debug:
                        try:
                            print(f"    [🔍نجات] نجاتِ ناحیه {_r.id} رد شد "
                                  f"(بازخوانیِ متنِ ناحیهٔ همپوشان): "
                                  f"{_t2[:36]!r}")
                        except Exception:
                            pass
                    continue
                _r.source_text = _t2
                if _p2:
                    _r.ocr_polys = _p2
                _r.ocr_empty = False
                _resc += 1
                try:
                    print(f"    [+] نجاتِ OCR ناحیه {_r.id}: {_t2[:48]!r}")
                except Exception:
                    pass
            elif _t2 and self.debug:
                try:
                    print(f"    [🔍نجات] نجاتِ ناحیه {_r.id} رد شد "
                          f"(نویز، نه متن): {_t2[:32]!r}")
                except Exception:
                    pass
        if _resc:
            print(f"    [+] {_resc} ناحیه با نجاتِ OCR متن گرفت → ترجمه میشوند")

    def _draw_debug_regions(self, image: np.ndarray,
                            regions: List[TextRegion],
                            det_quads: Optional[list] = None) -> np.ndarray:
      vis = image.copy()

      colors = {
        "dialogue": (0, 0, 255),
        "promo": (0, 165, 255),
        "sfx": (255, 255, 0),
        "junk": (128, 128, 128),
    }

      for r in regions:
        x, y, w, h = r.rect
        color = colors.get(r.kind, (0, 0, 255))

        cv2.rectangle(vis, (x, y), (x + w, y + h), color, 2)

        cx = x + w // 2
        cv2.circle(vis, (cx, y + h // 2), 3, (0, 255, 255), -1)

        label = f"[{r.id}] {r.kind[:3].upper()}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        cv2.rectangle(vis, (x, y - th - 6), (x + tw + 4, y), color, -1)
        cv2.putText(vis, label, (x + 2, y - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)

        short = (r.source_text or "")[:28]
        if short:
            cv2.putText(vis, short, (x, y + h + 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 200, 0), 1, cv2.LINE_AA)
        try:
            _ct = f"({x},{y} {w}x{h})"
            (_cw, _ch), _ = cv2.getTextSize(_ct, cv2.FONT_HERSHEY_SIMPLEX,
                                            0.38, 1)
            _cy = y + h + 34
            cv2.rectangle(vis, (x, _cy), (x + _cw + 4, _cy + _ch + 6),
                          (30, 30, 30), -1)
            cv2.putText(vis, _ct, (x + 2, _cy + _ch + 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 255),
                        1, cv2.LINE_AA)
        except Exception:
            pass

        ai = (r.translated_text or "").strip()
        if ai:

            ai_show = ai if all(ord(c) < 128 for c in ai[:20]) else f"AI[{r.id}] OK"
            cv2.putText(vis, ai_show[:32], (x, y + h + 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 128, 0), 1, cv2.LINE_AA)
            st = (getattr(r, "bubble_style", None) or "").strip()
            if st:
                cv2.putText(vis, st, (x + 2, y + 14),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1, cv2.LINE_AA)

      try:
        _dq = list(det_quads) if det_quads is not None else []
        for _q in _dq:
          _pts = np.asarray(_q, dtype=np.int32).reshape(-1, 1, 2)
          cv2.polylines(vis, [_pts], True, (255, 0, 0), 2, cv2.LINE_AA)
      except Exception:
        pass

      _det_raw0 = None
      for _r0 in regions:
        _v0 = getattr(_r0, "det_raw", None)
        if _v0:
          _det_raw0 = _v0
          break
      if _det_raw0:
        try:
          _v_h, _v_w = vis.shape[:2]
          for _di, (_dbox, _dcls) in enumerate(_det_raw0):
            try:
              _dx1 = max(0, int(_dbox[0]))
              _dy1 = max(0, int(_dbox[1]))
              _dx2 = max(_dx1 + 1, min(int(_dbox[2]), _v_w - 1))
              _dy2 = max(_dy1 + 1, min(int(_dbox[3]), _v_h - 1))
              cv2.rectangle(vis, (_dx1, _dy1), (_dx2, _dy2),
                            (0, 255, 0), 3)
              cv2.putText(vis, f"D{_di:02d} {_dcls}".strip(),
                          (_dx1 + 4, min(_v_h - 2, _dy1 + 26)),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                          (0, 255, 0), 2, cv2.LINE_AA)
            except Exception:
              continue
        except Exception:
          pass

      try:
        _ovl = {"size": [int(vis.shape[1]), int(vis.shape[0])],
                "det": [], "pdet": [], "rec": []}
        for _dbox, _dcls in (_det_raw0 or []):
          _ovl["det"].append([int(_dbox[0]), int(_dbox[1]),
                              int(_dbox[2]), int(_dbox[3]),
                              str(_dcls or "")])
        for _q in (list(det_quads) if det_quads is not None else []):
          _qq = np.asarray(_q, dtype=np.float32).reshape(-1, 2)
          _ovl["pdet"].append([[round(float(_x), 1), round(float(_y), 1)]
                               for _x, _y in _qq])
        def _pdet_iou(a2, b2) -> float:
            try:
                ax1, ay1 = float(a2[:, 0].min()), float(a2[:, 1].min())
                ax2, ay2 = float(a2[:, 0].max()), float(a2[:, 1].max())
                bx1, by1 = float(b2[:, 0].min()), float(b2[:, 1].min())
                bx2, by2 = float(b2[:, 0].max()), float(b2[:, 1].max())
                _iw = max(0.0, min(ax2, bx2) - max(ax1, bx1))
                _ih = max(0.0, min(ay2, by2) - max(ay1, by1))
                _inter = _iw * _ih
                _un = (ax2 - ax1) * (ay2 - ay1) \
                    + (bx2 - bx1) * (by2 - by1) - _inter
                return _inter / max(1e-6, _un)
            except Exception:
                return 0.0
        for _r in (regions or []):
            for _p in (getattr(_r, "ocr_polys", None) or []):
                try:
                    _qq2 = np.asarray(_p, dtype=np.float32).reshape(-1, 2)
                except Exception:
                    continue
                if _qq2.shape[0] < 3 or _qq2.size < 6:
                    continue
                _dup = False
                for _e in _ovl["pdet"]:
                    try:
                        _ee = np.asarray(_e, dtype=np.float32).reshape(-1, 2)
                        if _pdet_iou(_qq2, _ee) >= 0.55:
                            _dup = True
                            break
                    except Exception:
                        continue
                if _dup:
                    continue
                _ovl["pdet"].append(
                    [[round(float(_x), 1), round(float(_y), 1)]
                     for _x, _y in _qq2])
        for _r in (regions or []):
          try:
            _ovl["rec"].append([
              int(_r.rect[0]), int(_r.rect[1]),
              int(_r.rect[2]), int(_r.rect[3]),
              str(getattr(_r, "kind", "") or ""),
              (str(getattr(_r, "source_text", "") or ""))[:80],
              (str(getattr(_r, "translated_text", "") or ""))[:80]])
          except Exception:
            continue
        _vis2 = vis.view(_DebugPageVis)
        _vis2.ovl = _ovl
        _vis2.base = image
        return _vis2
      except Exception:
        return vis

    @staticmethod
    def _skew_from_quads(core_bgr: np.ndarray, quads, ox: int, oy: int, inset: int) -> float:

        try:
            g = cv2.cvtColor(core_bgr, cv2.COLOR_BGR2GRAY)
            med = float(np.median(g))
            ink = (g < max(60, med - 45)).astype(np.uint8) * 255
            h_c, w_c = ink.shape[:2]
            zone = np.zeros_like(ink)
            got = False
            for p in list(quads or []):
                pts = np.asarray(p, dtype=np.float32).reshape(-1, 2).copy()
                pts[:, 0] -= ox + inset
                pts[:, 1] -= oy + inset
                cv2.fillPoly(zone, [pts.astype(np.int32)], 255)
                got = True
            if not got:
                return 0.0
            zone = cv2.dilate(zone, np.ones((5, 5), np.uint8), iterations=1)
            ink = cv2.bitwise_and(ink, zone)
            ink = cv2.dilate(ink, np.ones((3, 3), np.uint8), iterations=1)
            n, lab, st, cents = cv2.connectedComponentsWithStats(ink, connectivity=8)
            pts_list = []
            for i in range(1, n):
                a = int(st[i, cv2.CC_STAT_AREA])
                if a < 60:
                    continue
                pts_list.append(cents[i])
            if len(pts_list) < 3:
                return 0.0
            data = np.asarray(pts_list, dtype=np.float32)
            _, eig, _ = cv2.PCACompute2(data, mean=None)
            v = eig[0]
            a = float(np.degrees(np.arctan2(float(v[1]), float(v[0]))))
            if a > 90:
                a -= 180.0
            elif a < -90:
                a += 180.0
            if abs(a) > 45:
                return 0.0
            return a
        except Exception:
            return 0.0

    @staticmethod
    def _pdf_to_images(pdf_path: str, dest_dir: str) -> List[str]:
        import fitz
        os.makedirs(dest_dir, exist_ok=True)
        doc = fitz.open(pdf_path)
        zoom = 200 / 72
        matrix = fitz.Matrix(zoom, zoom)
        files = []
        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=matrix)
            out_file = os.path.join(dest_dir, f"page_{i + 1:03d}.png")
            pix.save(out_file)
            files.append(out_file)
        doc.close()
        return files

    def _save_as_pdf(self, image_paths_in_order: List[str], out_path: str) -> None:
        images = []
        for p in image_paths_in_order:
            im = Image.open(p).convert("RGB")

            if im.size[0] < 8 or im.size[1] < 8:
                print(f"    [!] رد تصویر خیلی کوچک در PDF: {os.path.basename(p)} {im.size}")
                continue
            images.append(im)
        if not images:
            raise ValueError("هیچ تصویری برای ساخت PDF وجود نداره.")
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

        q = max(92, int(np.clip(int(getattr(self, "img_quality", 90) or 90), 40, 100)))
        images[0].save(
            out_path,
            save_all=True,
            append_images=images[1:],
            resolution=150.0,
            quality=q,
            optimize=True,
        )

    @staticmethod
    def _save_as_zip(folder: str, out_path: str) -> None:
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_STORED) as zf:
            for name in sorted(os.listdir(folder), key=MangaTranslator._natural_sort_key):
                zf.write(os.path.join(folder, name), arcname=name)

    def _save_as_psd(self, image_paths_in_order: List[str], out_path: str) -> None:

        try:
            from pytoshop.user.nested_layers import Image as PsdLayer
            from pytoshop.user.nested_layers import nested_layers_to_psd
            from pytoshop import enums as psd_enums
            from pytoshop.image_data import ImageData
        except ImportError:
            print("[*] نصب pytoshop برای خروجی PSD ...")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "-q", "pytoshop"],
            )
            from pytoshop.user.nested_layers import Image as PsdLayer
            from pytoshop.user.nested_layers import nested_layers_to_psd
            from pytoshop import enums as psd_enums
            from pytoshop.image_data import ImageData

        pages: List[np.ndarray] = []
        for p in image_paths_in_order:
            im = cv2.imread(p, cv2.IMREAD_UNCHANGED)
            if im is None:
                print(f"    [!] رد تصویر در PSD: {os.path.basename(p)}")
                continue
            if im.ndim == 2:
                im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
            elif im.shape[2] == 4:
                bgr = im[:, :, :3].astype(np.float32)
                a = im[:, :, 3:4].astype(np.float32) / 255.0
                im = (bgr * a + 255.0 * (1.0 - a)).astype(np.uint8)
            elif im.shape[2] > 4:
                im = im[:, :, :3]
            pages.append(im)
        if not pages:
            raise ValueError("هیچ تصویری برای ساخت PSD وجود ندارد.")

        max_h = max(im.shape[0] for im in pages)
        max_w = max(im.shape[1] for im in pages)
        use_psb = max_h > 30000 or max_w > 30000
        version = psd_enums.Version.version_2 if use_psb else psd_enums.Version.version_1

        def _place_on_canvas(bgr: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:

            h, w = bgr.shape[:2]
            canvas = np.zeros((max_h, max_w, 3), dtype=np.uint8)
            alpha = np.zeros((max_h, max_w), dtype=np.uint8)
            x0 = max(0, (max_w - w) // 2)
            canvas[:h, x0:x0 + w] = bgr
            alpha[:h, x0:x0 + w] = 255
            rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
            return rgb, alpha

        def _to_layer(name: str, bgr: np.ndarray) -> "PsdLayer":
            rgb, alpha = _place_on_canvas(bgr)
            return PsdLayer(
                name=name[:250],
                channels={
                    -1: np.ascontiguousarray(alpha),
                    0: np.ascontiguousarray(rgb[:, :, 0]),
                    1: np.ascontiguousarray(rgb[:, :, 1]),
                    2: np.ascontiguousarray(rgb[:, :, 2]),
                },
                opacity=255,
                visible=True,
            )

        layers = [_to_layer(f"page_{i + 1:03d}", im) for i, im in enumerate(pages)]
        layers = list(reversed(layers))

        print(
            f"[*] ساخت PSD: {len(pages)} لایه | بوم {max_w}×{max_h}"
            f"{' | PSB' if use_psb else ''} ..."
        )
        psd = nested_layers_to_psd(
            layers,
            color_mode=psd_enums.ColorMode.rgb,
            version=version,
            compression=psd_enums.Compression.raw,
        )

        preview_bgr = pages[0]
        preview_rgb, _ = _place_on_canvas(preview_bgr)
        comp = np.stack(
            [
                np.ascontiguousarray(preview_rgb[:, :, 0]),
                np.ascontiguousarray(preview_rgb[:, :, 1]),
                np.ascontiguousarray(preview_rgb[:, :, 2]),
            ],
            axis=0,
        )

        nch = int(getattr(psd, "num_channels", 3) or 3)
        if nch >= 4:
            alpha = np.zeros((max_h, max_w), dtype=np.uint8)
            h0, w0 = preview_bgr.shape[:2]
            x0 = max(0, (max_w - w0) // 2)
            alpha[:h0, x0:x0 + w0] = 255
            comp = np.concatenate([comp, alpha[None, ...]], axis=0)
        psd.image_data = ImageData(
            channels=comp,
            compression=psd_enums.Compression.raw,
        )

        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with open(out_path, "wb") as f:
            psd.write(f)
        size_mb = os.path.getsize(out_path) / (1024 * 1024)
        print(f"  - PSD ذخیره شد ({size_mb:.1f} MB): {out_path}")
        print("  - پیش‌نمایش ترکیبی = صفحه ۱ (برای IrfanView/ویندوز)")

    def _write_image(self, image: np.ndarray, path: str) -> None:
        ext = os.path.splitext(path)[1].lower()

        out_image = image
        try:
            _pp = os.environ.get("MANGA_PROBE_REPAIR", "")
            if _pp and getattr(self, "_probe_repair_pts", None):
                for (_px, _py) in self._probe_repair_pts:
                    print(f"  [PROBE] write @{_px},{_py} "
                          f"val={image[_py, _px]} shape={image.shape} "
                          f"path={os.path.basename(path)}", flush=True)
        except Exception:
            pass
        if os.environ.get("MANGA_DEBUG_LEFTOVER") == "1":
            try:
                cv2.imwrite("/tmp/ct38/write_input_debug.png", out_image)
            except Exception:
                pass
        if out_image is None or out_image.size == 0:
            raise ValueError(f"تصویر خالی برای ذخیره: {path}")
        if out_image.dtype != np.uint8:
            out_image = np.clip(out_image, 0, 255).astype(np.uint8)
        out_image = np.ascontiguousarray(out_image)

        if self.max_output_width and self.max_output_width > 0:
            target_w = int(self.max_output_width)
            if out_image.shape[1] != target_w:
                scale = target_w / float(out_image.shape[1])
                new_h = max(1, int(round(out_image.shape[0] * scale)))
                interp = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC
                out_image = cv2.resize(out_image, (target_w, new_h), interpolation=interp)
                out_image = np.ascontiguousarray(out_image)
        if os.environ.get("MANGA_DEBUG_LEFTOVER") == "1":
            import traceback as _tbw
            print(f"    [dbg-write] path={path} shape={out_image.shape} "
                  f"q={int(np.clip(int(self.img_quality), 40, 100))}")
            _tbw.print_stack(limit=6)

        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        _q_user = int(self.img_quality)
        q = int(np.clip(_q_user, 40, 100))
        if _q_user == 90:
            q = 85
        rgb = cv2.cvtColor(out_image, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(rgb)

        if ext == ".webp":

            pil.save(
                path, format="WEBP", quality=q, method=6,
                exact=False,
            )
        elif ext in (".jpg", ".jpeg"):

            sub = 0 if q >= 90 else 2
            pil.save(
                path, format="JPEG", quality=q, optimize=True,
                progressive=True, subsampling=sub,
            )
        elif ext == ".png":

            pil.save(path, format="PNG", optimize=True, compress_level=9)
        else:
            cv2.imwrite(path, out_image)

        if ext in (".webp", ".jpg", ".jpeg"):
            try:
                if os.path.getsize(path) > 1572864:
                    q2 = max(72, q - 7)
                    tmp = path + ".tmp"
                    if ext == ".webp":
                        pil.save(tmp, format="WEBP", quality=q2,
                                 method=6, exact=False)
                    else:
                        pil.save(
                            tmp, format="JPEG", quality=q2, optimize=True,
                            progressive=True,
                            subsampling=(0 if q2 >= 90 else 2),
                        )
                    if (os.path.isfile(tmp)
                            and os.path.getsize(tmp) < os.path.getsize(path)):
                        os.replace(tmp, path)
                    elif os.path.isfile(tmp):
                        os.remove(tmp)
            except Exception:
                pass

    @staticmethod
    def _save_as_html(image_paths: List[str], out_path: str, title: str = "مانهوا ترجمه شده") -> None:
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

        css = """
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { background: #0a0a0b; }
.strip {
  max-width: 900px;
  margin: 0 auto;
  background: #000;
}
.strip img {
  width: 100%;
  height: auto;
  display: block;
  vertical-align: top;
}
"""

        parts = [
            "<!DOCTYPE html>",
            '<html lang="fa" dir="rtl">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            '<meta name="color-scheme" content="dark">',
            '<meta name="theme-color" content="#0a0a0b">',
            f"<title>{title}</title>",
            "<style>",
            css.strip(),
            "</style>",
            "</head>",
            "<body>",
            '<div class="strip">',
        ]

        for i, p in enumerate(image_paths, 1):
            with open(p, "rb") as f:
                data = f.read()
            ext = os.path.splitext(p)[1].lower().lstrip(".")
            mime = {
                "jpg": "image/jpeg",
                "jpeg": "image/jpeg",
                "png": "image/png",
                "webp": "image/webp",
            }.get(ext, "image/jpeg")
            b64 = base64.b64encode(data).decode("ascii")
            parts.append(
                f'<img src="data:{mime};base64,{b64}" alt="" '
                f'loading="{"eager" if i <= 2 else "lazy"}" decoding="async">'
            )

        parts.append("</div>")
        parts.append("</body></html>")

        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(parts))

    @staticmethod
    def _cleanup_previous_artifacts(output_path: str, keep_outputs: bool = False) -> None:
        abs_out = os.path.abspath(output_path)
        parent = os.path.dirname(abs_out) or "."
        current_base = os.path.basename(abs_out)
        current_cache = MangaTranslator._cache_dir_for(abs_out)
        current_stem = os.path.splitext(current_base)[0]

        if not os.path.isdir(parent):
            return

        series_prefix = current_stem
        for marker in ("-chapter-", "_chapter_", "-ch-", "_ch-"):
            if marker in current_stem.lower():
                idx = current_stem.lower().index(marker)
                series_prefix = current_stem[:idx]
                break
        if len(series_prefix) < 3:
            series_prefix = current_stem[: max(4, len(current_stem) // 2)]

        removed = 0
        for name in os.listdir(parent):
            path = os.path.join(parent, name)

            if name.endswith(".cache") and os.path.isdir(path):
                if os.path.abspath(path) != os.path.abspath(current_cache):
                    print(f"[*] پاک کردن کش قدیمی: {name}")
                    shutil.rmtree(path, ignore_errors=True)
                    removed += 1
                continue

            if keep_outputs:
                continue

            low = name.lower()
            if not low.endswith((".pdf", ".html", ".zip", ".psd")):
                continue
            if os.path.abspath(path) == abs_out:
                continue
            if not os.path.isfile(path):
                continue

            stem = os.path.splitext(name)[0]
            if series_prefix and series_prefix.lower() in stem.lower():
                try:
                    print(f"[*] پاک کردن خروجی قدیمی: {name}")
                    os.remove(path)
                    removed += 1
                except OSError as e:
                    print(f"    [!] نتوانست پاک شود ({name}): {e}")

        if removed:
            print(f"[*] {removed} مورد قدیمی پاک شد.")
        else:
            print("[*] مورد قدیمی برای پاک کردن پیدا نشد.")

    @staticmethod
    def _extract_title_skips_from_path(path_or_url: str) -> List[str]:
        from urllib.parse import urlparse, unquote

        raw = path_or_url.strip()
        if MangaTranslator._is_url(raw):
            path = unquote(urlparse(raw).path)
        else:
            path = raw

        parts = [p for p in re.split(r"[/\\]+", path) if p]
        skip: List[str] = []
        noise = {
            "comics", "comic", "manga", "manhwa", "reader", "en", "chapter",
            "chapters", "series", "title", "www", "http", "https", "cdn",
            "asurascans", "asura", "mgeko", "webtoon", "page", "pages",
        }

        candidates = []
        for p in parts:
            pl = p.lower()
            if re.fullmatch(r"\d+", pl):
                continue
            if pl in noise:
                continue
            if pl.endswith((".jpg", ".png", ".webp", ".jpeg", ".html", ".pdf")):
                continue

            cleaned = re.sub(r"^[a-z]{0,4}\d+-", "", pl)
            cleaned = re.sub(r"-[a-f0-9]{6,}$", "", cleaned)
            if cleaned and cleaned not in noise:
                candidates.append(cleaned)
            if pl not in candidates and pl not in noise:
                candidates.append(pl)

        for c in candidates:

            compact = re.sub(r"[^a-z0-9]", "", c)
            if len(compact) >= 5:
                skip.append(compact)
            tokens = [t for t in re.split(r"[-_]+", c) if t and t not in noise and not t.isdigit()]
            if len(tokens) >= 2:

                for n in range(2, min(len(tokens), 4) + 1):
                    for i in range(0, len(tokens) - n + 1):
                        chunk = "".join(tokens[i:i + n])
                        if len(chunk) >= 5:
                            skip.append(chunk)

                full = "".join(tokens)
                if len(full) >= 5:
                    skip.append(full)

        seen = set()
        out = []
        for s in skip:
            if s not in seen:
                seen.add(s)
                out.append(s)
        return out
