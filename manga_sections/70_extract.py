# BUILD-STRIP-START
class _MangaTranslatorBody_70:
# BUILD-STRIP-END
    @staticmethod
    def _estimate_skew_angle(crop_bgr: np.ndarray) -> float:

        try:
            g = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
            med = float(np.median(g))
            ink = (g < max(60, med - 45)).astype(np.uint8) * 255
            ink = cv2.dilate(ink, np.ones((3, 3), np.uint8), iterations=2)
            n, lab, st, _ = cv2.connectedComponentsWithStats(ink, connectivity=8)
            crop_area = float(max(1, crop_bgr.shape[0] * crop_bgr.shape[1]))
            angs: List[float] = []
            for i in range(1, n):
                a = int(st[i, cv2.CC_STAT_AREA])
                bw = int(st[i, cv2.CC_STAT_WIDTH])
                bh = int(st[i, cv2.CC_STAT_HEIGHT])
                if a < 150 or max(bw, bh) < 40:
                    continue

                if max(bw, bh) < 2.0 * max(1, min(bw, bh)):
                    continue
                if a > 0.5 * crop_area:
                    continue
                pts = np.column_stack(np.where(lab == i))[:, ::-1].astype(np.float32)
                rect = cv2.minAreaRect(pts)
                box = cv2.boxPoints(rect)
                best_a, best_len = 0.0, 0.0
                for k in range(4):
                    p0, p1 = box[k], box[(k + 1) % 4]
                    dx, dy = float(p1[0] - p0[0]), float(p1[1] - p0[1])
                    ln = float(np.hypot(dx, dy))
                    if ln > best_len:
                        best_len = ln
                        if dx < 0.0:
                            dx, dy = -dx, -dy
                        best_a = float(np.degrees(np.arctan2(dy, dx)))
                if best_a > 90:
                    best_a -= 180.0
                elif best_a < -90:
                    best_a += 180.0
                if abs(best_a) <= 45:
                    angs.append(best_a)
            if not angs:
                return 0.0
            return float(np.median(angs))
        except Exception:
            return 0.0

    _SYSTEM_KEYWORDS = (
        "system", "info", "information", "quest", "mission", "level", "status",
        "window", "menu", "alert", "notice", "warning", "shop", "store",
        "skill", "inventory", "reward", "daily", "weekly", "tutorial",
        "settings", "objective", "complete", "completed", "failed", "bonus",
        "achievement", "notification", "loading", "confirm", "cancel",
        "accept", "decline", "points", "exp", "time left", "countdown",
        "timer", "update", "guild", "dungeon", "penalty", "runaway",
        "システム", "情報", "インフォ", "クエスト", "ミッション", "レベル",
        "ステータス", "警告", "注意", "通知", "ショップ", "商店", "アイテム",
        "報酬", "デイリー", "ウィークリー", "達成", "実績", "完了", "失敗",
        "確認", "キャンセル", "設定", "スキル", "経験値", "所持", "メニュー",
        "討伐", "侵入", "準備",
        "시스템", "정보", "퀘스트", "미션", "레벨", "상태", "경고", "알림",
        "상점", "아이템", "보상", "일일", "주간", "업적", "완료", "실패",
        "확인", "취소", "설정", "스킬", "경험치", "메뉴", "공지",
        "系统", "信息", "任务", "等级", "状态", "警告", "提醒", "通知", "商店",
        "道具", "奖励", "日常", "每周", "成就", "完成", "失败", "确认", "取消",
        "设置", "技能", "经验", "公告", "菜单", "副本", "公会",
    )

    @staticmethod
    def _system_window_score(text: str, line_texts, line_polys, rect) -> int:
        try:
            t = str(text or "").strip()
            if not t:
                return 0
            lines = [str(l or "").strip() for l in (line_texts or [])
                     if str(l or "").strip()]
            if not lines:
                lines = [p for p in re.split(r"[\n]+", t) if p.strip()]
            n = len(lines)
            if n <= 0:
                return 0
            score = 0
            if re.search(r"[\[\u3010][^\]\u3011\n]{1,48}[\]\u3011]", t):
                score += 3
            kw = MangaTranslator._sys_keyword_hits(lines)
            if kw >= 1:
                score += 2
            if kw >= 3:
                score += 1
            colons = sum(l.count(":") + l.count("\uff1a") + l.count("\uff1d")
                         for l in lines)
            if colons >= 2:
                score += 2
            lens = [len(l) for l in lines]
            if n >= 3 and max(lens) - min(lens) <= max(6, int(0.35 * max(lens))):
                score += 2
            if line_polys and len(line_polys) >= 3:
                try:
                    tops, hts = [], []
                    for _p in line_polys:
                        _a = np.asarray(_p, dtype=np.float32).reshape(-1, 2)
                        tops.append(float(_a[:, 1].min()))
                        hts.append(max(1.0, float(_a[:, 1].max() - _a[:, 1].min())))
                    tops.sort()
                    gaps = [tops[i2 + 1] - tops[i2] for i2 in range(len(tops) - 1)]
                    hmed = float(np.median(hts))
                    if hmed > 1 and gaps and float(np.median(gaps)) >= hmed * 1.35:
                        score += 2
                except Exception:
                    pass
            if n >= 4 and max(lens) <= 42:
                score += 1
            if n >= 3 and not any(re.search(r"[\u3002\uff0e\uff01!?\u2026]$", l)
                                  for l in lines):
                score += 1
            try:
                w_ = int(rect[2]) - int(rect[0])
                h_ = int(rect[3]) - int(rect[1])
                if w_ > 0 and h_ > 0 and (w_ / float(h_)) >= 2.2 and n >= 3:
                    score += 1
            except Exception:
                pass
            return score
        except Exception:
            return 0

    @staticmethod
    def _sys_keyword_hits(lines) -> int:
        n = 0
        for l in (lines or []):
            ll = str(l or "").strip().lower()
            if not ll:
                continue
            for k in MangaTranslator._SYSTEM_KEYWORDS:
                try:
                    if k.isascii():
                        if re.search(r"(?<![a-z0-9])" + re.escape(k)
                                     + r"(?![a-z0-9])", ll):
                            n += 1
                            break
                    elif k in ll:
                        n += 1
                        break
                except Exception:
                    continue
        return n

    @staticmethod
    def _is_label_block(line_texts) -> bool:
        try:
            lines = [str(l or "").strip() for l in (line_texts or [])
                     if str(l or "").strip()]
            n = len(lines)
            if not (2 <= n <= 12):
                return False
            lens = [len(l) for l in lines]
            if max(lens) > 46 or (sum(lens) / float(n)) > 30.0:
                return False
            if any(re.search(r"[?!…\u3002\uff01\uff1f]$", l) for l in lines):
                return False
            colon_lines = sum(1 for l in lines if re.search(r"[:\uff1a\uff1d=]", l))
            has_bracket = any(
                re.search(r"[\[\u3010][^\]\u3011]{1,48}[\]\u3011]", l)
                for l in lines)
            if colon_lines >= 2 or has_bracket:
                return True
            if len(lines) >= 3 and all(len(l.split()) <= 4 for l in lines):
                kw = MangaTranslator._sys_keyword_hits(lines)
                if kw >= 1 and colon_lines >= 1:
                    return True
            return False
        except Exception:
            return False

    @staticmethod
    def _system_window_strong(text: str, line_texts) -> bool:
        try:
            t = str(text or "")
            if re.search(r"[\[\u3010][^\]\u3011\n]{1,48}[\]\u3011]", t):
                return True
            lines = [str(l or "").strip().lower() for l in (line_texts or [])
                     if str(l or "").strip()]
            if not lines:
                lines = [p.strip().lower() for p in re.split(r"[\n]+", t) if p.strip()]
            if MangaTranslator._sys_keyword_hits(lines) >= 1:
                return True
            colons = sum(l.count(":") + l.count("\uff1a") + l.count("\uff1d")
                         for l in lines)
            if colons >= 2:
                return True
            return False
        except Exception:
            return False

    @staticmethod
    def _cluster_ocr_lines(polys, texts, y_tol_factor: float = 0.65):
        try:
            items = []
            for _i, _p in enumerate(list(polys or [])):
                _t = str((list(texts or []) + [""] * (len(polys or []) ))[_i] or "").strip()
                if not _t:
                    continue
                _a = np.asarray(_p, dtype=np.float32).reshape(-1, 2)
                items.append([float(_a[:, 1].min()), float(_a[:, 1].max()),
                              float(_a[:, 0].min()), float(_a[:, 0].max()), _t])
            if not items:
                return []
            _hs = sorted(it[1] - it[0] for it in items)
            _hmed = max(1.0, float(np.median(_hs)))
            items.sort(key=lambda it: ((it[0] + it[1]) / 2.0, it[2]))
            lines: List[dict] = []
            for it in items:
                _cy = (it[0] + it[1]) / 2.0
                _hit = None
                for ln in lines:
                    _lcy = (ln["y0"] + ln["y1"]) / 2.0
                    if abs(_cy - _lcy) <= max(_hmed * y_tol_factor,
                                              (ln["y1"] - ln["y0"]) * 0.6):
                        _hit = ln
                        break
                if _hit is None:
                    lines.append({"y0": it[0], "y1": it[1], "x0": it[2],
                                  "x1": it[3], "words": [it]})
                else:
                    _hit["y0"] = min(_hit["y0"], it[0])
                    _hit["y1"] = max(_hit["y1"], it[1])
                    _hit["x0"] = min(_hit["x0"], it[2])
                    _hit["x1"] = max(_hit["x1"], it[3])
                    _hit["words"].append(it)
            out = []
            for ln in lines:
                ln["words"].sort(key=lambda w2: w2[2])
                _txt = " ".join(w2[4] for w2 in ln["words"]).strip()
                out.append((ln["x0"], ln["y0"], ln["x1"], ln["y1"], _txt))
            out.sort(key=lambda t2: t2[1])
            return out
        except Exception:
            return []

    def _ocr_pool_workers(self, n_tasks: int) -> int:
        try:
            if n_tasks is None or int(n_tasks) <= 1:
                return 1
            if not isinstance(getattr(self, "ocr", None), RapidOCRBackend):
                return 1
        except Exception:
            return 1
        try:
            w = int(os.environ.get("MANGA_OCR_WORKERS", "0") or 0)
        except Exception:
            w = 0
        if w <= 0:
            try:
                w = max(1, min(4, int(_physical_core_count()) // 2))
            except Exception:
                w = 1
        try:
            return max(1, min(int(w), int(n_tasks)))
        except Exception:
            return 1

    def _ocr_crop(self, image_bgr: np.ndarray, rect,
                  block_rects: Optional[List[Tuple[int, int, int, int]]] = None,
                  page_cache: Optional[dict] = None) \
            -> Tuple[str, List[np.ndarray]]:

        x1, y1, x2, y2 = [int(v) for v in rect]
        h, w = image_bgr.shape[:2]
        try:
            _ck = (x1, y1, x2, y2, w, h,
                      tuple(map(tuple, block_rects)) if block_rects else None)
            _cc = page_cache if page_cache is not None \
                else getattr(self, "_ocr_crop_cache", None)
            if _cc is not None and _ck in _cc:
                return _cc[_ck]
        except Exception:
            pass
        _rv = self._ocr_crop_run(image_bgr, rect, block_rects)
        try:
            if page_cache is not None:
                if len(page_cache) < 512:
                    page_cache[_ck] = _rv
            else:
                if getattr(self, "_ocr_crop_cache", None) is None:
                    self._ocr_crop_cache = {}
                if len(self._ocr_crop_cache) < 512:
                    self._ocr_crop_cache[_ck] = _rv
        except Exception:
            pass
        return _rv

    def _rec_fast_single_line(self, crop0: np.ndarray, base_scale: float,
                              ox: int, oy: int, block_rects, own_area: float):
        _rf = getattr(self.ocr, "rec_only", None)
        if not callable(_rf):
            return None
        ch, cw = crop0.shape[:2]
        if ch < 10 or cw < 20:
            return None
        try:
            g = cv2.cvtColor(crop0, cv2.COLOR_BGR2GRAY)
        except Exception:
            return None
        med = float(np.median(g))
        if med >= 120:
            ink = (g < max(60.0, med - 45.0))
        elif med <= 108:
            ink = (g > min(200.0, med + 45.0))
        else:
            return None
        rows = ink.mean(axis=1)
        on = rows > 0.03
        bands = []
        _s = None
        _gap = 0
        for _i, _v in enumerate(on):
            if _v:
                if _s is None:
                    _s = _i
                _gap = 0
            elif _s is not None:
                _gap += 1
                if _gap >= 3:
                    bands.append((_s, _i - _gap))
                    _s = None
        if _s is not None:
            bands.append((_s, len(on) - 1))
        bands = [(_a, _b) for (_a, _b) in bands if _b - _a >= 5]
        if len(bands) != 1:
            return None
        by1, by2 = bands[0]
        if by2 - by1 + 1 < 7:
            return None
        cols = ink[by1:by2 + 1].mean(axis=0)
        cx = np.flatnonzero(cols > 0.02)
        if len(cx) < 8:
            return None
        bx1, bx2 = int(cx[0]), int(cx[-1])
        if bx2 - bx1 + 1 < 16:
            return None
        if bx1 <= 1 or bx2 >= cw - 2:
            try:
                _bandcols = ink[by1:by2 + 1].mean(axis=0)
                _core = _bandcols[bx1:bx2 + 1]
                _core_med = float(np.median(_core[_core > 0.02])) \
                    if (_core > 0.02).any() else 0.0
                _bad = False
                if bx1 <= 1:
                    _ed = float(_bandcols[0:min(3, cw)].mean())
                    if _core_med > 0 and _ed > 0.55 * _core_med:
                        _bad = True
                if not _bad and bx2 >= cw - 2:
                    _ed = float(_bandcols[max(0, cw - 3):cw].mean())
                    if _core_med > 0 and _ed > 0.55 * _core_med:
                        _bad = True
                if _bad:
                    return None
            except Exception:
                return None
        _tot = float(ink.sum())
        if _tot <= 0 or float(ink[by1:by2 + 1].sum()) / _tot < 0.88:
            return None
        ry1, ry2 = max(0, by1 - 4), min(ch, by2 + 5)
        rx1, rx2 = max(0, bx1 - 6), min(cw, bx2 + 7)
        lc = crop0[ry1:ry2, rx1:rx2]
        if lc is None or lc.size == 0:
            return None
        if base_scale > 1.01:
            lc = cv2.resize(lc, None, fx=base_scale, fy=base_scale,
                            interpolation=cv2.INTER_CUBIC)
        rr = _rf(lc)
        if rr is None:
            return None
        txt = str(rr[0]).strip()
        cf = float(rr[1])
        if not txt or cf < 0.85:
            return None
        _lt = sum(1 for _c in txt if _c.isascii() and _c.isalpha())
        if _lt < 2:
            return None
        if _lt * 2 < len(txt.replace(" ", "")):
            return None
        _bb = (float(ox + rx1), float(oy + ry1),
               float(ox + rx2), float(oy + ry2))
        try:
            if _line_is_foreign(_bb, block_rects, max(1.0, float(own_area))):
                return None
        except Exception:
            return None
        _p = np.array(
            [[ox + bx1, oy + by1], [ox + bx2 + 1, oy + by1],
             [ox + bx2 + 1, oy + by2 + 1], [ox + bx1, oy + by2 + 1]],
            dtype=np.float32)
        if getattr(self, "debug", False):
            print(f"    [⚡] تک‌خطی بدونِ det: {txt[:44]!r} "
                  f"(conf={cf:.2f}, {bx2 - bx1 + 1}x{by2 - by1 + 1}px)")
        return (txt, [_p.astype(np.int32)], [0.0], [txt], [-1])

    def _ocr_crop_run(self, image_bgr: np.ndarray, rect,
                      block_rects: Optional[List[Tuple[int, int, int, int]]] = None) \
            -> Tuple[str, List[np.ndarray]]:
        x1, y1, x2, y2 = [int(v) for v in rect]
        h, w = image_bgr.shape[:2]
        pad = 8
        x1, y1 = max(0, x1 - pad), max(0, y1 - pad)
        x2, y2 = min(w, x2 + pad), min(h, y2 + pad)
        if x2 - x1 < 8 or y2 - y1 < 8:
            return "", [], [], []
        crop0 = image_bgr[y1:y2, x1:x2]
        ch0, cw0 = crop0.shape[:2]

        try:
            _sk = self._estimate_skew_angle(crop0)
        except Exception:
            _sk = 0.0
        _tilted0 = abs(_sk) >= 8.0
        if _tilted0:
            pad2 = min(120, int(abs(np.sin(np.radians(_sk))) * max(x2 - x1, y2 - y1)) + 16)
            nx1, ny1 = max(0, int(rect[0]) - pad2), max(0, int(rect[1]) - pad2)
            nx2, ny2 = min(w, int(rect[2]) + pad2), min(h, int(rect[3]) + pad2)
            if (nx2 - nx1) > (x2 - x1) or (ny2 - ny1) > (y2 - y1):
                x1, y1, x2, y2 = nx1, ny1, nx2, ny2
                crop0 = image_bgr[y1:y2, x1:x2]
                ch0, cw0 = crop0.shape[:2]

        def _run(crop_bgr, scale: float, apply_offset: bool = True,
                 ang_corr: float = 0.0, origin=None):
            if scale > 1.01:
                crop_bgr = cv2.resize(
                    crop_bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC
                )
            try:
                _oc = self.ocr
                if _on_android() and getattr(_oc, "_mobile", None) \
                        is not None:
                    results = _oc.ocr(crop_bgr, crop_mode=True)
                else:
                    results = _oc.ocr(crop_bgr)
            except Exception as _e:
                if getattr(self, "debug", False):
                    print(f"    [!] OCRِ برش خطا داد: {str(_e)[:140]}")
                return "", [], 0.0, []
            if not results or not results[0]:
                return "", [], 0.0, []
            lines, polys, confs, entries = [], [], [], []
            for line in results[0]:
                try:
                    if not (isinstance(line, (list, tuple)) and len(line) >= 2):
                        continue
                    pair = line[1]
                    eng_ang = 0.0
                    if isinstance(pair, (list, tuple)):
                        text = str(pair[0]).strip()
                        conf = float(pair[1]) if len(pair) > 1 else 1.0
                        if len(pair) > 2:
                            try:
                                eng_ang = float(pair[2])
                                if eng_ang > 180.0:
                                    eng_ang -= 360.0
                                if abs(eng_ang) > 45.0:
                                    eng_ang = 0.0
                            except (TypeError, ValueError):
                                eng_ang = 0.0
                    else:
                        text, conf = str(pair).strip(), 1.0
                    if not text or conf < self.min_confidence:
                        continue
                    if self._is_non_english_script(text):
                        continue
                    lines.append(text)
                    confs.append(conf)
                    box0 = line[0] if len(line) >= 1 else None
                    _blk_id = -1
                    if isinstance(pair, (list, tuple)) and len(pair) > 3:
                        try:
                            _blk_id = int(pair[3])
                        except (TypeError, ValueError):
                            _blk_id = -1

                    entry_poly = None
                    if box0 is not None and isinstance(box0, (list, tuple, np.ndarray)) and len(box0) >= 3:
                        poly = np.array(line[0], dtype=np.float32).reshape(-1, 2)
                        if poly.min() >= -8 and poly.max() < 100000:
                            if scale > 1.01:
                                poly = poly / scale
                            if apply_offset:
                                _ox, _oy = origin if origin is not None else (x1, y1)
                                poly = poly + np.array([_ox, _oy], dtype=np.float32)
                            polys.append(poly.astype(np.int32))
                            entry_poly = poly.astype(np.float32)
                    entries.append((text, conf, entry_poly,
                                    float(eng_ang) + float(ang_corr),
                                    int(_blk_id)))
                except Exception:
                    continue
            joined = " ".join(lines).strip()
            avg_conf = float(np.mean(confs)) if confs else 0.0
            return joined, polys, avg_conf, entries

        _sc_cjk = _on_android()

        def _score(txt: str, conf: float) -> float:
            if not txt:
                return -1.0
            latin = sum(1 for c in txt if c.isascii() and c.isalpha())
            if _sc_cjk:
                _cjk = sum(
                    1 for c in txt
                    if (0x3040 <= ord(c) <= 0x30FF)
                    or (0x3400 <= ord(c) <= 0x9FFF)
                    or (0xAC00 <= ord(c) <= 0xD7AF))
                return (max(latin, _cjk) * 2.0 + conf * 3.0
                        + min(len(txt), 24) * 0.15)

            return latin * 2.0 + conf * 3.0 + min(len(txt), 24) * 0.15

        candidates = []

        m = max(ch0, cw0)
        if m < 200:
            base_scale = 2.4
        elif m < 360:
            base_scale = 1.8
        elif m < 600:
            base_scale = 1.35
        else:
            base_scale = 1.0

        inset = int(min(ch0, cw0) * 0.06)
        if min(ch0, cw0) >= 160 and ch0 > 2 * inset + 20 and cw0 > 2 * inset + 20:
            core = crop0[inset:ch0 - inset, inset:cw0 - inset]
        else:
            core = crop0

        if not _tilted0 and not os.environ.get("MANGA_REC_FAST_OFF"):
            try:
                _fast = self._rec_fast_single_line(
                    crop0, base_scale, x1, y1, block_rects,
                    (x2 - x1) * (y2 - y1))
                if _fast is not None:
                    return _fast
            except Exception:
                pass

        variants = []
        variants.append(("raw", core, base_scale))
        _clahe_skip = False
        try:
            _gc = cv2.cvtColor(core, cv2.COLOR_BGR2GRAY)
            _p10 = float(np.percentile(_gc, 10))
            _p90 = float(np.percentile(_gc, 90))
            _clahe_skip = (_p90 - _p10) >= 120.0
        except Exception:
            _clahe_skip = False
        if not _clahe_skip:
            try:
                lab = cv2.cvtColor(core, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                l2 = cv2.createCLAHE(2.5, (8, 8)).apply(l)
                enh = cv2.cvtColor(cv2.merge((l2, a, b)), cv2.COLOR_LAB2BGR)
                variants.append(("clahe", enh, base_scale))
            except Exception:
                pass
        try:
            g = cv2.cvtColor(core, cv2.COLOR_BGR2GRAY)
            _, bw = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            if float(np.mean(bw)) < 127:
                bw = cv2.bitwise_not(bw)
            bw = cv2.cvtColor(bw, cv2.COLOR_GRAY2BGR)
            variants.append(("otsu", bw, min(base_scale + 0.25, 2.2)))

            if float(np.median(g)) < 110:
                inv = cv2.cvtColor(cv2.bitwise_not(g), cv2.COLOR_GRAY2BGR)
                variants.append(("inv", inv, min(base_scale + 0.4, 2.6)))
        except Exception:
            pass

        def _bb_of(poly):
            if poly is None:
                return None
            p = np.asarray(poly, dtype=np.float32).reshape(-1, 2)
            return (float(p[:, 0].min()), float(p[:, 1].min()),
                    float(p[:, 0].max()), float(p[:, 1].max()))

        def _overlap_frac(a, b):
            ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
            iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
            inter = ix * iy
            if inter <= 0:
                return 0.0
            aa = max(1e-6, (a[2] - a[0]) * (a[3] - a[1]))
            ab = max(1e-6, (b[2] - b[0]) * (b[3] - b[1]))
            return inter / min(aa, ab)

        merged: List[List] = []
        best = ("", [], -1.0, [], [], [])
        inset_used = inset if core is not crop0 else 0
        early_stop = False

        _ink_rows = None
        try:
            _g2 = cv2.cvtColor(core, cv2.COLOR_BGR2GRAY)
            _med2 = float(np.median(_g2))
            _rowink = ((_g2 < max(60.0, _med2 - 45.0)).mean(axis=1))
            _rows = np.flatnonzero(_rowink > 0.02)
            if len(_rows) >= 4:
                _ink_rows = (int(_rows[0]), int(_rows[-1]))
        except Exception:
            _ink_rows = None

        _vi = -1
        for name, crop_v, sc in variants:
            _vi += 1
            txt, polys, conf, entries = _run(crop_v, sc)
            if inset_used and entries:
                polys = [p + inset_used for p in polys]
                for e in entries:
                    if e[2] is not None:
                        e[2][:, 0] += inset_used
                        e[2][:, 1] += inset_used
            _own = max(1.0, float((x2 - x1) * (y2 - y1)))
            if entries:
                try:
                    _rhas3 = source_has_letters(
                        " ".join(str(_e[0]) for _e in entries))
                except Exception:
                    _rhas3 = None
                _keep = []
                _fix = False
                for _e in entries:
                    _bb = _bb_of(_e[2]) if _e[2] is not None else None
                    if _bb is not None and _line_is_foreign(
                            _bb, block_rects, _own):
                        if self.debug:
                            print(f"    [🔍مالکیت] خطِ ناحیهٔ مجاور حذف شد: "
                                  f"{str(_e[0])[:36]!r}")
                        continue
                    _j = _latin_junk_line(_e[0], _rhas3) \
                        if _latin_lang(self) else False
                    if _j:
                        if isinstance(_j, str):
                            _e = (_j,) + tuple(_e[1:])
                            _fix = True
                        else:
                            if self.debug:
                                print(f"    [🔍مالکیت] خطِ آشغالِ لاتین حذف شد: "
                                      f"{str(_e[0])[:36]!r}")
                            continue
                    _keep.append(_e)
                if _fix or len(_keep) != len(entries):
                    entries = _keep
                    txt = " ".join(e[0] for e in entries).strip()
                    polys = [np.asarray(e[2], dtype=np.int32)
                             for e in entries if e[2] is not None]
                    conf = (float(np.mean([e[1] for e in entries]))
                            if entries else 0.0)
            _poly_angs = [float(e[3]) if len(e) > 3 else 0.0
                          for e in entries if e[2] is not None]
            for e in entries:
                text, e_conf, e_poly = e[0], e[1], e[2]
                e_ang = float(e[3]) if len(e) > 3 else 0.0
                bb = _bb_of(e_poly)
                hit = None
                if bb is not None:
                    for m_item in merged:
                        mb = _bb_of(m_item[2])
                        if mb is not None and _overlap_frac(bb, mb) > 0.35:
                            hit = m_item
                            break
                if hit is None:
                    merged.append([text, e_conf, e_poly, e_ang,
                                   (e[4] if len(e) > 4 else -1)])
                elif e_conf > hit[1]:
                    hit[0], hit[1], hit[3] = text, e_conf, e_ang
                    if len(hit) > 4:
                        hit[4] = (e[4] if len(e) > 4 else -1)

            scv = _score(txt, conf)
            if scv > best[2]:
                best = (txt, polys, scv, _poly_angs,
                        [e[0] for e in entries if e[2] is not None],
                        [(e[4] if len(e) > 4 else -1)
                         for e in entries if e[2] is not None])

            _latin_n = len(re.sub(r"[^A-Za-z]", "", txt or ""))
            if os.environ.get("MANGA_DBG") and _vi == 0:
                print(f"    [DBG] vi0 name={name} conf={conf:.3f} "
                      f"latin={_latin_n} entries={len(entries)} "
                      f"tilt={_tilted0} ink={_ink_rows}", flush=True)
            if (_vi == 0 and not _tilted0 and entries
                    and conf >= 0.80
                    and (_latin_n >= 3
                         or sum(1 for _ch in (txt or "")
                                if 0x3040 <= ord(_ch) <= 0x30FF
                                or 0x3400 <= ord(_ch) <= 0x9FFF
                                or 0xAC00 <= ord(_ch) <= 0xD7AF) >= 2)):
                if os.environ.get("MANGA_DBG"):
                    print(f"    [DBG] gate-pass vi={_vi} conf={conf:.2f} "
                          f"latin={_latin_n} entries={len(entries)} "
                          f"ink={_ink_rows}", flush=True)
                _cover_ok = True
                if _ink_rows is not None and merged:
                    _ys = [_bb_of(m[2]) for m in merged
                              if m[2] is not None]
                    _ys = [b for b in _ys if b is not None]
                    if _ys:
                        _fy0 = min(b[1] for b in _ys)
                        _fy1 = max(b[3] for b in _ys)
                        _span = max(1.0, float(
                            _ink_rows[1] - _ink_rows[0]))
                        _cov = (_fy1 - _fy0) / _span
                        _cover_ok = _cov >= 0.60
                if _cover_ok:
                    early_stop = True
                    break

            if ((not _tilted0)
                    and ((conf >= 0.86 and _latin_n >= 8)
                         or (conf >= 0.78 and _latin_n >= 20))):
                early_stop = True
                break

            if (not _tilted0) and conf >= 0.80:
                _cjk = 0
                for _ch in (txt or ""):
                    _o = ord(_ch)
                    if (0x3040 <= _o <= 0x30FF or 0x3400 <= _o <= 0x9FFF
                            or 0xAC00 <= _o <= 0xD7AF):
                        _cjk += 1
                if _cjk >= 3:
                    early_stop = True
                    break

        try:
            if merged and not _tilted0:
                _mx, _mn = max(ch0, cw0), min(ch0, cw0)
                if _mx >= 260 and _mx / max(1, _mn) >= 1.5:
                    _bxs = [_bb_of(m[2]) for m in merged
                               if m[2] is not None]
                    _bxs = [b for b in _bxs if b is not None]
                    if 2 <= len(_bxs) <= 30:
                        _dims = [max(2.0, min(b[2] - b[0], b[3] - b[1]))
                                    for b in _bxs]
                        _med = float(np.median(_dims))
                        _vert = sum(
                            1 for b in _bxs
                            if (b[3] - b[1]) > (b[2] - b[0])
                        ) > len(_bxs) / 2
                        _sb = sorted(_bxs, key=(
                            (lambda b: b[0]) if _vert
                            else (lambda b: b[1])))
                        _maxgap = 0.0
                        for _i in range(len(_sb) - 1):
                            _g = (
                                (_sb[_i + 1][0] - _sb[_i][2])
                                if _vert else
                                (_sb[_i + 1][1] - _sb[_i][3]))
                            if _g > _maxgap:
                                _maxgap = _g
                        if _maxgap > 2.0 * _med:
                            _halves = []
                            if ch0 >= cw0:
                                _oh = max(60, int(ch0 * 0.58))
                                if 60 <= _oh < ch0:
                                    _halves = [
                                        ("half-top", crop0[0:_oh], 0, 0),
                                        ("half-bot", crop0[ch0 - _oh:],
                                         0, ch0 - _oh)]
                            else:
                                _ow = max(60, int(cw0 * 0.58))
                                if 60 <= _ow < cw0:
                                    _halves = [
                                        ("half-left", crop0[:, 0:_ow],
                                         0, 0),
                                        ("half-right",
                                         crop0[:, cw0 - _ow:],
                                         cw0 - _ow, 0)]
                            if _halves and self.debug:
                                print(f"    [🔍شکاف] شکافِ خط {_maxgap:.0f}px "
                                      f"(میانه {_med:.0f}px) → OCRِ نیمهها")
                            for _hn, _hc, _hox, _hoy in _halves:
                                try:
                                    _t2, _p2, _c2, _e2 = _run(
                                        _hc, base_scale,
                                        origin=(x1 + _hox, y1 + _hoy))
                                except Exception:
                                    continue
                                for _e3 in (_e2 or []):
                                    _bb2 = (_bb_of(_e3[2])
                                            if _e3[2] is not None else None)
                                    if _bb2 is None:
                                        continue
                                    if _line_is_foreign(
                                            _bb2, block_rects, _own):
                                        continue
                                    try:
                                        _rhas = source_has_letters(
                                            " ".join(
                                                [str(_m2[0]) for _m2 in merged]
                                                + [str(_e5[0]) for _e5 in (_e2 or [])]))
                                    except Exception:
                                        _rhas = None
                                    _j2 = _latin_junk_line(_e3[0], _rhas) \
                                        if _latin_lang(self) else False
                                    if _j2:
                                        if isinstance(_j2, str):
                                            _e3 = (_j2,) + tuple(_e3[1:])
                                        else:
                                            continue
                                    _hit2 = None
                                    for _m in merged:
                                        _bm = _bb_of(_m[2])
                                        if _bm is not None and \
                                                _overlap_frac(_bb2, _bm) > 0.35:
                                            _hit2 = _m
                                            break
                                    if _hit2 is None:
                                        merged.append(
                                            [_e3[0], float(_e3[1]), _e3[2],
                                             float(_e3[3]) if len(_e3) > 3 else 0.0,
                                             (int(_e3[4]) if len(_e3) > 4 else -1)])
                                        if self.debug:
                                            print(f"    [🔍شکاف] خطِ بازیابی‌شده از "
                                                  f"{_hn}: {str(_e3[0])[:36]!r}")
        except Exception:
            pass

        try:
            if merged and not _tilted0:
                _dbg = bool(os.environ.get("MANGA_R90_DBG"))
                _edge = 3 + int(inset_used or 0)
                for _side in (0, 1):
                    if _side == 0:
                        _clip = [m for m in merged if m[2] is not None
                                   and _bb_of(m[2])[0] <= x1 + _edge]
                    else:
                        _clip = [m for m in merged if m[2] is not None
                                   and _bb_of(m[2])[2] >= x2 - _edge]
                    if not _clip:
                        continue
                    _ext = min(110, int((x2 - x1) * 0.35))
                    if _ext < 12:
                        continue
                    if _side == 0:
                        _nb = max(0, x1 - _ext)
                        if block_rects:
                            for (_bx1, _by1, _bx2, _by2) in block_rects:
                                try:
                                    if (_bx1 < x1 and _bx2 > _nb
                                            and _by1 < y2 and _by2 > y1):
                                        _nb = max(_nb,
                                                    min(x1 - 2, _bx2 + 6))
                                except Exception:
                                    continue
                        if _nb >= x1 - 4:
                            continue
                        _crop = image_bgr[y1:y2, _nb:x2]
                        _org = (_nb, y1)
                    else:
                        _nb = min(w, x2 + _ext)
                        if block_rects:
                            for (_bx1, _by1, _bx2, _by2) in block_rects:
                                try:
                                    if (_bx2 > x2 and _bx1 < _nb
                                            and _by1 < y2 and _by2 > y1):
                                        _nb = min(_nb,
                                                    max(x2 + 2, _bx1 - 6))
                                except Exception:
                                    continue
                        if _nb <= x2 + 4:
                            continue
                        _crop = image_bgr[y1:y2, x1:_nb]
                        _org = (x1, y1)
                    if _crop.size == 0 or _crop.shape[0] < 12 \
                            or _crop.shape[1] < 12:
                        continue
                    _ylo = min(_bb_of(m[2])[1] for m in _clip) - 10
                    _yhi = max(_bb_of(m[2])[3] for m in _clip) + 10
                    if _dbg:
                        print(f"    [r90] crop=({x1},{y1},{x2},{y2}) side="
                              f"{'L' if _side == 0 else 'R'} → تاِ {_nb} | "
                              f"بریده: {[m[0] for m in _clip]}", flush=True)
                    _txtE, _polE, _confE, _entE = _run(
                        _crop, base_scale, apply_offset=True, origin=_org)
                    for _e6 in (_entE or []):
                        _tE = str(_e6[0] or "").strip()
                        _pE = _e6[2] if len(_e6) > 2 else None
                        if not _tE or _pE is None:
                            continue
                        _bE = _bb_of(_pE)
                        if _bE is None or (_bE[3] - _bE[1]) < 8:
                            continue
                        if _line_is_foreign(_bE, block_rects, _own):
                            continue
                        try:
                            _rhasE = source_has_letters(
                                " ".join(
                                    [str(_m2[0]) for _m2 in merged]
                                    + [_tE]))
                        except Exception:
                            _rhasE = None
                        _jE = _latin_junk_line(_tE, _rhasE) \
                            if _latin_lang(self) else False
                        if _jE:
                            if isinstance(_jE, str):
                                _tE = _jE
                            else:
                                continue
                        _oyE = min(_yhi, _bE[3]) - max(_ylo, _bE[1])
                        if _oyE <= 0.3 * max(1.0, _bE[3] - _bE[1]):
                            continue
                        if _side == 0 and _bE[0] >= x1 - 2:
                            continue
                        if _side == 1 and _bE[2] <= x2 + 2:
                            continue
                        _hitE = None
                        for _m3 in merged:
                            _bM = _bb_of(_m3[2]) if _m3[2] is not None else None
                            if _bM is not None and _overlap_frac(_bE, _bM) > 0.40:
                                _hitE = _m3
                                break
                        if _hitE is None:
                            merged.append([_tE, float(_e6[1]), _pE,
                                           float(_e6[3]) if len(_e6) > 3 else 0.0,
                                           (int(_e6[4]) if len(_e6) > 4 else -1)])
                            if _dbg:
                                print(f"    [r90]   + «{_tE}» "
                                      f"x[{_bE[0]:.0f}-{_bE[2]:.0f}] "
                                      f"y[{_bE[1]:.0f}-{_bE[3]:.0f}]", flush=True)
                        elif _hitE in _clip and (
                                len(_tE) >= len(_hitE[0] or "")):
                            if _dbg:
                                print(f"    [r90]   ~ «{_hitE[0]}» → «{_tE}»",
                                      flush=True)
                            _hitE[0] = _tE
                            _hitE[1] = float(_e6[1])
                            _hitE[2] = _pE
                            if len(_e6) > 3:
                                _hitE[3] = float(_e6[3])
                            if len(_hitE) > 4 and len(_e6) > 4:
                                _hitE[4] = int(_e6[4])
                        elif _dbg and _hitE is not None:
                            print(f"    [r90]   . نگهِ «{_hitE[0]}» "
                                  f"(جدید: «{_tE}»)", flush=True)
        except Exception:
            pass

        if merged:
            _allow_en, _allow_ko, _allow_ja, _allow_zh = self._ocr_lang_flags()
            if _allow_ja and len(merged) > 1:
                _hts0 = []
                for m_item in merged:
                    mb = _bb_of(m_item[2])
                    if mb is not None:
                        _hts0.append(mb[3] - mb[1])
                _hmax0 = max(_hts0) if _hts0 else 0.0
                if _hmax0 > 0:
                    _kana_re = re.compile(r"^[\u3040-\u30FFー・]+$")
                    _kept = [
                        m for m in merged
                        if not (
                            _kana_re.match((m[0] or "").replace(" ", "").replace("　", ""))
                            and _bb_of(m[2]) is not None
                            and (_bb_of(m[2])[3] - _bb_of(m[2])[1]) < _hmax0 * 0.62
                        )
                    ]
                    if _kept:
                        merged = _kept
            if _on_android() and len(merged) >= 3:
                try:
                    _bbsF = [_bb_of(m[2]) for m in merged]
                    _vF = [b for b in _bbsF if b is not None]
                    if len(_vF) >= 3:
                        _medhF = float(np.median(
                            [b[3] - b[1] for b in _vF]))
                        _medwF = float(np.median(
                            [b[2] - b[0] for b in _vF]))
                        _tallF = sum(
                            1 for b in _vF
                            if (b[3] - b[1]) > 1.4 * (b[2] - b[0]))
                        _wideF = len(_vF) - _tallF
                        _keepF = None
                        if _tallF * 20 >= len(_vF) * 11:
                            _keepF = [
                                m for m, b in zip(merged, _bbsF)
                                if b is None or not (
                                    (b[2] - b[0]) > max(
                                        1.7 * _medwF, _medwF + 28.0)
                                    and (b[2] - b[0]) > 1.6 * (b[3] - b[1]))
                            ]
                        elif _wideF * 20 >= len(_vF) * 11:
                            _keepF = [
                                m for m, b in zip(merged, _bbsF)
                                if b is None or not (
                                    (b[3] - b[1]) > max(
                                        1.7 * _medhF, _medhF + 28.0)
                                    and (b[3] - b[1]) > 1.6 * (b[2] - b[0]))
                            ]
                        if (_keepF is not None and len(_keepF) >= 2
                                and len(_keepF) < len(merged)):
                            merged = _keepF
                except Exception:
                    pass
            hts = []
            for m_item in merged:
                mb = _bb_of(m_item[2])
                if mb is not None:
                    hts.append(mb[3] - mb[1])
            if _on_android():
                _bbsS = [_bb_of(m[2]) for m in merged]
                _vS = [b for b in _bbsS if b is not None]
                if _vS:
                    _medhS = float(np.median(
                        [b[3] - b[1] for b in _vS]))
                    _tallS = sum(
                        1 for b in _vS
                        if (b[3] - b[1]) > 1.4 * (b[2] - b[0]))
                    _rtlS = (
                        getattr(self, "reading_order", "rtl") == "rtl")
                    if len(_vS) >= 2 and _tallS * 2 >= len(_vS):
                        if _rtlS:
                            merged.sort(key=lambda m_item: (
                                (-(_bb_of(m_item[2])[0])
                                 if m_item[2] is not None else 0.0),
                                (_bb_of(m_item[2])[1]
                                 if m_item[2] is not None else 0.0)))
                        else:
                            merged.sort(key=lambda m_item: (
                                (_bb_of(m_item[2])[0]
                                 if m_item[2] is not None else 0.0),
                                (_bb_of(m_item[2])[1]
                                 if m_item[2] is not None else 0.0)))
                    else:
                        _rh = max(8.0, _medhS * 0.75)
                        merged.sort(key=lambda m_item: (
                            ((_bb_of(m_item[2])[1]
                              if m_item[2] is not None else 0.0) // _rh),
                            (_bb_of(m_item[2])[0]
                             if m_item[2] is not None else 0.0)))
            else:
                row_h = max(8.0, (float(np.median(hts)) if hts else 8.0) * 0.75)
                merged.sort(key=lambda m_item: (
                    ((_bb_of(m_item[2])[1] if m_item[2] is not None else 0.0) // row_h),
                    (_bb_of(m_item[2])[0] if m_item[2] is not None else 0.0),
                ))
            try:
                _cg = MangaTranslator._column_line_groups(
                    list(range(len(merged))),
                    [_bb_of(m_item[2]) for m_item in merged],
                    rtl=(getattr(self, "reading_order", "rtl") == "rtl"))
            except Exception:
                _cg = None
            if _cg and len(_cg) > 1:
                _parts = []
                for _g3 in _cg:
                    _gs = sorted(_g3, key=lambda _k: (
                        (_bb_of(merged[_k][2])[1]
                         if merged[_k][2] is not None else 0.0),
                        (_bb_of(merged[_k][2])[0]
                         if merged[_k][2] is not None else 0.0)))
                    _tg = " ".join(
                        str(merged[_k][0] or "").strip() for _k in _gs
                    ).strip()
                    if _tg:
                        _parts.append(_tg)
                u_txt = "\n".join(_parts)
            else:
                u_txt = " ".join(m_item[0] for m_item in merged).strip()
            u_txt = u_txt.strip()
            u_conf = float(np.mean([m_item[1] for m_item in merged])) if merged else 0.0
            u_polys = [
                np.rint(np.asarray(m_item[2], dtype=np.float32)).astype(np.int32)
                for m_item in merged if m_item[2] is not None
            ]
            u_angs = [float(m_item[3]) if len(m_item) > 3 else 0.0
                      for m_item in merged if m_item[2] is not None]
            u_texts = [str(m_item[0] or "") for m_item in merged if m_item[2] is not None]
            u_blks = [int(m_item[4]) if len(m_item) > 4 else -1
                      for m_item in merged if m_item[2] is not None]
            scv = _score(u_txt, u_conf)
            if scv >= best[2]:
                best = (u_txt, u_polys, scv, u_angs, u_texts, u_blks)

        best_txt = best[0] or ""
        latin_n = len(re.sub(r"[^A-Za-z]", "", best_txt))

        skew = self._skew_from_quads(core, best[1], x1, y1, inset_used)
        if skew == 0.0:
            skew = _sk if _sk != 0.0 else self._estimate_skew_angle(core)
        if (not early_stop) and skew != 0.0 and 4.0 <= abs(skew) <= 40.0 and (latin_n < 3 or abs(skew) >= 5.0):
            try:
                hc, wc = core.shape[:2]
                M = cv2.getRotationMatrix2D((wc / 2.0, hc / 2.0), skew, 1.0)
                nw = int(round(wc * abs(np.cos(np.radians(skew))) +
                               hc * abs(np.sin(np.radians(skew))))) + 4
                nh = int(round(wc * abs(np.sin(np.radians(skew))) +
                               hc * abs(np.cos(np.radians(skew))))) + 4
                M[0, 2] += nw / 2.0 - wc / 2.0
                M[1, 2] += nh / 2.0 - hc / 2.0
                desk = cv2.warpAffine(
                    core, M, (nw, nh),
                    flags=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_CONSTANT,
                    borderValue=(255, 255, 255),
                )
                txt, polys, conf, _entries = _run(desk, base_scale,
                                                  apply_offset=False,
                                                  ang_corr=float(skew))
                if txt and polys:
                    M_inv = cv2.getRotationMatrix2D((wc / 2.0, hc / 2.0), -skew, 1.0)
                    M_inv[0, 2] += wc / 2.0 - nw / 2.0
                    M_inv[1, 2] += hc / 2.0 - nh / 2.0
                    off = np.array([x1, y1], dtype=np.float32)
                    back_polys = []
                    for p in polys:
                        pp = p.astype(np.float32).reshape(-1, 2)
                        ones = np.hstack([pp, np.ones((pp.shape[0], 1), dtype=np.float32)])
                        backp = (M_inv @ ones.T).T + off[None, :]
                        back_polys.append(np.rint(backp).astype(np.int32))
                    if inset_used:
                        for pp in back_polys:
                            pp[:, 0] += inset_used
                            pp[:, 1] += inset_used
                    scv = _score(txt, conf)
                    latin_d = len(re.sub(r"[^A-Za-z]", "", txt or ""))
                    if scv > best[2] and latin_d >= latin_n:
                        _desk_angs = []
                        for _bp in back_polys:
                            try:
                                _desk_angs.append(float(
                                    MangaTranslator._poly_long_side_angle(_bp)))
                            except Exception:
                                _desk_angs.append(0.0)
                        _desk_texts = [str(e[0] or "") for e in _entries
                                       if e[2] is not None]
                        _desk_blks = [(int(e[4]) if len(e) > 4 else -1)
                                      for e in _entries if e[2] is not None]
                        best = (txt, back_polys, scv, _desk_angs, _desk_texts,
                                _desk_blks)
            except Exception:
                pass

        try:
            _latin_b = len(re.sub(r"[^A-Za-z]", "", best[0] or ""))
            _tall = False
            if merged:
                _hb = []
                for m_item in merged:
                    mb = _bb_of(m_item[2])
                    if mb is not None:
                        _hb.append((mb[3] - mb[1], mb[2] - mb[0]))
                if _hb:
                    _mh = float(np.median([b[0] for b in _hb]))
                    _mw = float(np.median([b[1] for b in _hb]))
                    _tall = _mh > max(1.3 * _mw, 1.15 * cw0)
            _need = (
                cw0 >= 40 and ch0 >= 1.2 * cw0
                and ((not merged) or _tall
                     or (_latin_b < 4 and bool(merged))))
            if _need and merged:
                _cjk_b = sum(
                    1 for _ch in (best[0] or "")
                    if 0x3040 <= ord(_ch) <= 0x30FF
                    or 0x3400 <= ord(_ch) <= 0x9FFF
                    or 0xAC00 <= ord(_ch) <= 0xD7AF)
                if _cjk_b >= 2:
                    _need = False
            if _need:
                for _rotk in (cv2.ROTATE_90_CLOCKWISE,
                                 cv2.ROTATE_90_COUNTERCLOCKWISE):
                    try:
                        _rot_img = cv2.rotate(crop0, _rotk)
                        _rt, _rp, _rc, _re = _run(
                            _rot_img, base_scale, apply_offset=False)
                        if not _re:
                            continue
                        _keep2 = []
                        try:
                            _rhas2 = source_has_letters(
                                " ".join(str(_e[0])
                                          for _e in (_re or [])))
                        except Exception:
                            _rhas2 = None
                        for _e4 in (_re or []):
                            if _e4[2] is None:
                                continue
                            _j3 = _latin_junk_line(_e4[0], _rhas2) \
                                if _latin_lang(self) else False
                            if _j3:
                                if isinstance(_j3, str):
                                    _e4 = (_j3,) + tuple(_e4[1:])
                                else:
                                    continue
                            _keep2.append(_e4)
                        if not _keep2:
                            continue
                        _back = []
                        for _e4 in _keep2:
                            _pp = np.asarray(_e4[2], np.float32).reshape(-1, 2)
                            if _rotk == cv2.ROTATE_90_CLOCKWISE:
                                _bx = _pp[:, 1].copy()
                                _by = (ch0 - 1.0) - _pp[:, 0]
                            else:
                                _bx = (cw0 - 1.0) - _pp[:, 1]
                                _by = _pp[:, 0].copy()
                            _bp2 = np.stack(
                                [_bx + x1, _by + y1], axis=1)
                            if inset_used:
                                _bp2 += float(inset_used)
                            _back.append(np.rint(_bp2).astype(np.int32))
                        _btxt = " ".join(str(e[0]) for e in _keep2).strip()
                        _bconf = float(np.mean([e[1] for e in _keep2]))
                        _scv = _score(_btxt, _bconf)
                        _bl = len(re.sub(r"[^A-Za-z]", "", _btxt))
                        if _scv > best[2] and _bl >= _latin_b:
                            _bangs = []
                            for _bp2 in _back:
                                try:
                                    _bangs.append(float(
                                        MangaTranslator._poly_long_side_angle(_bp2)))
                                except Exception:
                                    _bangs.append(0.0)
                            best = (_btxt, _back, _scv, _bangs,
                                    [str(e[0]) for e in _keep2],
                                    [(int(e[4]) if len(e) > 4 else -1)
                                     for e in _keep2])
                            if self.debug:
                                print(f"    [🔍چرخش] نجاتِ ±۹۰°: "
                                      f"{_btxt[:60]!r}")
                            break
                    except Exception:
                        continue
        except Exception:
            pass

        return (best[0], best[1], (best[3] if len(best) > 3 else []),
                (best[4] if len(best) > 4 else []),
                (best[5] if len(best) > 5 else []))

    @staticmethod
    def _drop_contained_boxes(boxes: List[dict], contain_thresh: float = 0.72) -> List[dict]:

        if len(boxes) < 2:
            return boxes

        def _area(r):
            return max(0, int(r[2]) - int(r[0])) * max(0, int(r[3]) - int(r[1]))

        def _iou(a, b):
            ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
            iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
            inter = ix * iy
            if inter <= 0:
                return 0.0
            ua = _area(a) + _area(b) - inter
            return inter / float(ua) if ua > 0 else 0.0

        def _contain(big, small):
            ix = max(0, min(big[2], small[2]) - max(big[0], small[0]))
            iy = max(0, min(big[3], small[3]) - max(big[1], small[1]))
            a_s = _area(small)
            return (ix * iy) / a_s if a_s > 0 else 0.0

        n_all = len(boxes)
        is_group = [False] * n_all
        if n_all >= 3:
            for i in range(n_all):
                members = [j for j in range(n_all) if j != i
                           and _contain(boxes[i]["rect"], boxes[j]["rect"]) >= 0.82]
                disjoint: List[int] = []
                for j in members:
                    if all(_iou(boxes[j]["rect"], boxes[k]["rect"]) < 0.10
                           for k in disjoint):
                        disjoint.append(j)
                if len(disjoint) >= 2:
                    is_group[i] = True
        boxes = [b for i, b in enumerate(boxes) if not is_group[i]]

        priority = {"text_bubble": 2, "text_free": 1, "bubble": 0}
        boxes = sorted(
            boxes,
            key=lambda x: (priority.get(x.get("class_name", ""), 0),
                           float(x.get("confidence", 0.0)),
                           _area(x["rect"])),
            reverse=True,
        )
        kept: List[dict] = []
        for b in boxes:
            rb = b["rect"]
            ab = _area(rb)
            if ab < 1:
                continue
            dup = False
            for k in kept:
                rk = k["rect"]

                ix = max(0, min(rb[2], rk[2]) - max(rb[0], rk[0]))
                iy = max(0, min(rb[3], rk[3]) - max(rb[1], rk[1]))
                inter = ix * iy
                smaller = min(ab, _area(rk))
                if smaller > 0 and inter / smaller >= contain_thresh:
                    dup = True
                    break

                if _iou(rb, rk) >= 0.45:
                    dup = True
                    break
            if not dup:
                kept.append(b)
        return kept

    @staticmethod
    def _split_adjacent_balloons(image_bgr: np.ndarray, rect,
                                 min_area_frac: float = 0.16) -> List[list]:

        try:
            x1, y1, x2, y2 = [int(v) for v in rect[:4]]
            h_img, w_img = image_bgr.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w_img, x2), min(h_img, y2)
            full = [x1, y1, x2, y2]
            if x2 - x1 < 48 or y2 - y1 < 48:
                return [full]
            crop = image_bgr[y1:y2, x1:x2]
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            if float(np.mean(bw)) < 127:
                bw = 255 - bw
            k = min(9, max(3, min(bw.shape) // 80))
            bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
            n, _lab, st, _ = cv2.connectedComponentsWithStats(bw, connectivity=8)
            box_area = float((x2 - x1) * (y2 - y1))
            comps: List[list] = []
            for i in range(1, n):
                area = float(st[i, cv2.CC_STAT_AREA])
                cw_, ch_ = int(st[i, cv2.CC_STAT_WIDTH]), int(st[i, cv2.CC_STAT_HEIGHT])
                if area >= box_area * min_area_frac and cw_ >= 32 and ch_ >= 32:
                    comps.append([int(st[i, cv2.CC_STAT_LEFT]), int(st[i, cv2.CC_STAT_TOP]),
                                  cw_, ch_, area])
            if len(comps) < 2:
                return [full]
            comps.sort(key=lambda c: -c[4])
            comps = comps[:4]
            if sum(c[4] for c in comps) < box_area * 0.50:
                return [full]
            subs: List[list] = []
            for cx, cy, cw_, ch_, _a in comps:
                sx1, sy1 = max(x1, x1 + cx), max(y1, y1 + cy)
                sx2, sy2 = min(x2, x1 + cx + cw_), min(y2, y1 + cy + ch_)
                if sx2 - sx1 >= 28 and sy2 - sy1 >= 28:
                    subs.append([sx1, sy1, sx2, sy2])
            if len(subs) < 2:
                return [full]
            ded = MangaTranslator._drop_contained_boxes(
                [{"rect": r} for r in subs], contain_thresh=0.85)
            subs = [d["rect"] for d in ded]
            return subs if len(subs) >= 2 else [full]
        except Exception:
            try:
                return [[int(v) for v in rect[:4]]]
            except Exception:
                return [rect]

    def _ocr_guard_line_boxes(self, crop: np.ndarray):
        try:
            try:
                _res = self.ocr.ocr(crop, crop_mode=True)
            except TypeError:
                _res = self.ocr.ocr(crop)
            boxes = []
            for _pg in (_res or []):
                for _it in (_pg or []):
                    try:
                        boxes.append(np.asarray(
                            _it[0], dtype=np.float32).reshape(-1, 2))
                    except Exception:
                        continue
        except Exception:
            return []
        out = []
        for _p in (boxes or []):
            try:
                _pp = np.asarray(_p, dtype=np.float32).reshape(-1, 2)
                if _pp.shape[0] < 4:
                    continue
                _w = float(_pp[:, 0].max() - _pp[:, 0].min())
                _h = float(_pp[:, 1].max() - _pp[:, 1].min())
                if _w >= 12.0 and _h >= 6.0:
                    out.append((float(_pp[:, 0].min()),
                                float(_pp[:, 1].min()),
                                float(_pp[:, 0].max()),
                                float(_pp[:, 1].max()), _h))
            except Exception:
                continue
        return out

    def _split_cuts_text(self, image: np.ndarray, full_rect, parts) -> bool:
        try:
            _ocr = getattr(self, "ocr", None)
            if _ocr is None:
                return False
            x1, y1, x2, y2 = [int(v) for v in full_rect[:4]]
            _pad = 6
            _cx1 = max(0, x1 - _pad)
            _cy1 = max(0, y1 - _pad)
            _cx2 = min(int(image.shape[1]), x2 + _pad)
            _cy2 = min(int(image.shape[0]), y2 + _pad)
            if _cx2 - _cx1 < 24 or _cy2 - _cy1 < 24:
                return False
            crop = image[_cy1:_cy2, _cx1:_cx2]
            if crop is None or crop.size == 0:
                return False
            lines = self._ocr_guard_line_boxes(crop)
            if not lines:
                return False
            _bx0, _by0 = float(x1 - _cx1), float(y1 - _cy1)
            _bx1, _by1 = float(x2 - _cx1), float(y2 - _cy1)
            _good = []
            for _L in lines:
                _lx0, _ly0, _lx1, _ly1, _lh = _L
                _mxc = (_lx0 + _lx1) * 0.5
                _myc = (_ly0 + _ly1) * 0.5
                if _bx0 - 2 <= _mxc <= _bx1 + 2 and _by0 - 2 <= _myc <= _by1 + 2:
                    _good.append(_L)
            if not _good:
                return False
            _parts = sorted(
                [[int(v) for v in p[:4]] for p in parts],
                key=lambda p: (p[0], p[1]))
            for _a, _b in zip(_parts, _parts[1:]):
                _ovx = min(_a[2], _b[2]) - max(_a[0], _b[0])
                _ovy = min(_a[3], _b[3]) - max(_a[1], _b[1])
                _wa = max(1, _a[2] - _a[0])
                _ha = max(1, _a[3] - _a[1])
                _side = (_ovy >= 0.5 * min(_ha, max(1, _b[3] - _b[1])))
                _stack = (_ovx >= 0.5 * min(_wa, max(1, _b[2] - _b[0])))
                if not _side and not _stack:
                    continue
                if _side:
                    _lo = max(_a[0], _b[0])
                    _hi = min(_a[2], _b[2])
                    if _hi <= _lo:
                        _lo, _hi = min(_a[2], _b[2]), max(_a[0], _b[0])
                    for _lx0, _ly0, _lx1, _ly1, _lh in _good:
                        _tol = min(24.0, max(4.0, 0.12 * max(1.0, _lh)))
                        if (_lo - _lx0) >= _tol and (_lx1 - _hi) >= _tol:
                            return True
                if _stack:
                    _lo = max(_a[1], _b[1])
                    _hi = min(_a[3], _b[3])
                    if _hi <= _lo:
                        _lo, _hi = min(_a[3], _b[3]), max(_a[1], _b[1])
                    for _lx0, _ly0, _lx1, _ly1, _lh in _good:
                        _tol = min(24.0, max(4.0, 0.12 * max(1.0, _lh)))
                        if (_lo - _ly0) >= _tol and (_ly1 - _hi) >= _tol:
                            return True
            return False
        except Exception:
            return False

    @staticmethod
    def _merge_overlapping_regions(regions: List[TextRegion],
                                   iou_thresh: float = 0.35,
                                   contain_thresh: float = 0.65) -> List[TextRegion]:

        if len(regions) < 2:
            return regions

        def _line_min_dims(r):
            out = []
            for p in (getattr(r, "ocr_polys", None) or []):
                try:
                    pp = np.asarray(p, dtype=np.float32).reshape(-1, 2)
                    w = float(pp[:, 0].max() - pp[:, 0].min())
                    h = float(pp[:, 1].max() - pp[:, 1].min())
                    d = min(w, h)
                    if d > 2.0:
                        out.append(d)
                except Exception:
                    continue
            return out

        def _incoherent_lines(a, b):
            ha = _line_min_dims(a)
            hb = _line_min_dims(b)
            if len(ha) < 2 or len(hb) < 2:
                return False
            ma, mb = float(np.median(ha)), float(np.median(hb))
            if ma <= 0 or mb <= 0:
                return False
            return (max(ma, mb) / min(ma, mb)) >= 1.35

        def rect_xyxy(r: TextRegion):
            x, y, w, h = r.rect
            return [x, y, x + w, y + h]

        def area(xyxy):
            return max(0, xyxy[2] - xyxy[0]) * max(0, xyxy[3] - xyxy[1])

        def iou(a, b):
            ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
            iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
            inter = ix * iy
            if inter <= 0:
                return 0.0
            ua = area(a) + area(b) - inter
            return inter / float(ua) if ua > 0 else 0.0

        def contain_ratio(inner, outer):
            ix = max(0, min(inner[2], outer[2]) - max(inner[0], outer[0]))
            iy = max(0, min(inner[3], outer[3]) - max(inner[1], outer[1]))
            inter = ix * iy
            ai = area(inner)
            return inter / float(ai) if ai > 0 else 0.0

        def _det_box(r):
            try:
                bs = getattr(r, "boxes", None) or []
                if not bs:
                    return None
                p = np.asarray(bs[0], dtype=np.float32).reshape(-1, 2)
                if p.size < 8:
                    return None
                return [float(p[:, 0].min()), float(p[:, 1].min()),
                        float(p[:, 0].max()), float(p[:, 1].max())]
            except Exception:
                return None

        ordered = sorted(
            regions,
            key=lambda r: (len((r.source_text or "").strip()), r.rect[2] * r.rect[3]),
            reverse=True,
        )
        used = [False] * len(ordered)
        merged: List[TextRegion] = []
        n_merged = 0
        for i, a in enumerate(ordered):
            if used[i]:
                continue
            cur = a
            used[i] = True
            ca = rect_xyxy(cur)
            _cur_det = [d for d in [_det_box(cur)] if d]
            changed = True
            while changed:
                changed = False
                for j, b in enumerate(ordered):
                    if used[j]:
                        continue
                    cb = rect_xyxy(b)
                    _db = _det_box(b)
                    if _cur_det and _db:
                        if not any(
                                iou(cd, _db) >= iou_thresh
                                or contain_ratio(_db, cd) >= contain_thresh
                                or contain_ratio(cd, _db) >= contain_thresh
                                for cd in _cur_det):
                            continue
                    ov = iou(ca, cb)
                    cont_ab = contain_ratio(cb, ca)
                    cont_ba = contain_ratio(ca, cb)
                    if ov < iou_thresh and cont_ab < contain_thresh and cont_ba < contain_thresh:
                        continue

                    nx0 = min(ca[0], cb[0]); ny0 = min(ca[1], cb[1])
                    nx1 = max(ca[2], cb[2]); ny1 = max(ca[3], cb[3])
                    ta = (cur.source_text or "").strip()
                    tb = (b.source_text or "").strip()
                    if not ta:
                        joined = tb
                    elif not tb:
                        joined = ta
                    elif tb.lower() in ta.lower():
                        joined = ta
                    elif ta.lower() in tb.lower():
                        joined = tb
                    elif _incoherent_lines(cur, b):
                        continue
                    else:

                        if ca[1] <= cb[1]:
                            joined = (ta + " " + tb).strip()
                        else:
                            joined = (tb + " " + ta).strip()
                        joined = re.sub(r"\s{2,}", " ", joined)
                    _aa = float(cur.angle or 0.0)
                    _ba = float(b.angle or 0.0)
                    if abs(_aa) < 3.0:
                        _ang = _ba
                    elif abs(_ba) < 3.0:
                        _ang = _aa
                    elif (_aa > 0.0) == (_ba > 0.0):
                        _ang = (_aa + _ba) / 2.0
                    else:
                        _ang = _aa if abs(_aa) >= abs(_ba) else _ba
                    cur = TextRegion(
                        id=cur.id,
                        boxes=list(cur.boxes or []) + list(b.boxes or []),
                        source_text=joined,
                        rect=(nx0, ny0, nx1 - nx0, ny1 - ny0),
                        angle=_ang,
                        kind=cur.kind if cur.kind == "dialogue" else b.kind,
                        ocr_polys=list(getattr(cur, "ocr_polys", None) or [])
                        + list(getattr(b, "ocr_polys", None) or []),
                    )
                    ca = [nx0, ny0, nx1, ny1]
                    if _db is not None:
                        _cur_det.append(_db)
                    used[j] = True
                    n_merged += 1
                    changed = True
            merged.append(cur)
        return merged

    @staticmethod
    def _poly_long_side_angle(pts) -> float:
        try:
            pts = np.asarray(pts, dtype=np.float32).reshape(-1, 2)
        except Exception:
            return 0.0
        if pts.shape[0] < 2:
            return 0.0
        try:
            box = cv2.boxPoints(cv2.minAreaRect(pts.astype(np.float32)))
        except Exception:
            return 0.0
        best_a, best_len = 0.0, 0.0
        for k in range(4):
            p0, p1 = box[k], box[(k + 1) % 4]
            dx, dy = float(p1[0] - p0[0]), float(p1[1] - p0[1])
            ln = float(np.hypot(dx, dy))
            if ln > best_len:
                best_len = ln
                if dx < 0.0:
                    dx, dy = -dx, -dy
                best_a = float(np.degrees(np.arctan2(dy, dx)))
        if abs(best_a) > 45:
            return 0.0
        return best_a

    @staticmethod
    def _ocr_poly_mask(shape_hw, polys, off_x: float = 0.0,
                       off_y: float = 0.0) -> Optional[np.ndarray]:
        try:
            m = np.zeros((int(shape_hw[0]), int(shape_hw[1])), np.uint8)
            drew = 0
            for p in polys or []:
                try:
                    pp = np.asarray(p, dtype=np.float32).reshape(-1, 2)
                    pp = pp - np.array([off_x, off_y], np.float32)
                    cv2.fillPoly(m, [np.round(pp).astype(np.int32)], 255)
                    drew += 1
                except Exception:
                    continue
            if not drew:
                return None
            m = cv2.dilate(m, np.ones((3, 3), np.uint8), iterations=3)
            if int((m > 0).sum()) < 60:
                return None
            return m
        except Exception:
            return None

    @staticmethod
    def _ink_slant_angle(crop_bgr, poly_mask=None) -> float:
        return MangaTranslator._ink_slant_measure(crop_bgr, poly_mask)[0]

    @staticmethod
    def _ink_slant_support(crop_bgr, angle_deg: float,
                           poly_mask=None) -> Optional[float]:
        try:
            if crop_bgr is None or getattr(crop_bgr, "size", 0) == 0:
                return None
            h_c, w_c = crop_bgr.shape[:2]
            if w_c < 40 or h_c < 14:
                return None
            g = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
            med = float(np.median(g))
            _dark = (g < max(60.0, med - 45.0))
            _bright = (g > min(195.0, max(med + 45.0, 150.0)))
            if poly_mask is not None:
                _keep = (poly_mask > 0)
                _dark = _dark & _keep
                _bright = _bright & _keep
            _fd = float(_dark.mean())
            _fb = float(_bright.mean())
            _cands = []
            if 0.010 <= _fd <= 0.45:
                _cands.append(_dark)
            if 0.010 <= _fb <= 0.45:
                _cands.append(_bright)
            if not _cands:
                if 0.45 < _fd <= 0.60:
                    _cands.append(_dark)
                elif 0.010 <= _fb <= 0.60:
                    _cands.append(_bright)
                else:
                    return None
            _cands.sort(key=lambda _b: float(_b.mean()))

            def _sup(ink: np.ndarray) -> Optional[float]:
                try:
                    ys_, xs_ = np.nonzero(ink)
                    if len(ys_) < 60:
                        return None
                    ys_f = ys_.astype(np.float64)
                    xs_f = xs_.astype(np.float64)

                    def _score(theta_deg: float) -> float:
                        t = float(np.tan(np.radians(theta_deg)))
                        rows = ys_f - t * xs_f
                        idx = (rows - rows.min()).astype(np.int32)
                        hist = np.bincount(idx)
                        hf = hist.astype(np.float64)
                        return float(np.dot(hf, hf))

                    s0 = max(1.0, _score(0.0))
                    sa = _score(float(angle_deg))
                    return sa / s0
                except Exception:
                    return None

            for _ink_b in _cands:
                _r = _sup(_ink_b)
                if _r is not None:
                    return _r
            return None
        except Exception:
            return None

    def _ink_slant_measure(crop_bgr, poly_mask=None) -> Tuple[float, bool]:
        try:
            if crop_bgr is None or getattr(crop_bgr, "size", 0) == 0:
                return 0.0, False
            h_c, w_c = crop_bgr.shape[:2]
            if w_c < 40 or h_c < 14:
                return 0.0, False
            g = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
            med = float(np.median(g))
            _dark = (g < max(60.0, med - 45.0))
            _bright = (g > min(195.0, max(med + 45.0, 150.0)))
            if poly_mask is not None:
                _keep = (poly_mask > 0)
                _dark = _dark & _keep
                _bright = _bright & _keep
            _fd = float(_dark.mean())
            _fb = float(_bright.mean())
            _cands = []
            if 0.010 <= _fd <= 0.45:
                _cands.append(_dark.astype(np.uint8))
            if 0.010 <= _fb <= 0.45:
                _cands.append(_bright.astype(np.uint8))
            if not _cands:
                if 0.45 < _fd <= 0.60:
                    _cands.append(_dark.astype(np.uint8))
                elif 0.010 <= _fb <= 0.60:
                    _cands.append(_bright.astype(np.uint8))
                else:
                    return 0.0, False
            _cands.sort(key=lambda _b: float(_b.mean()))
            for _ink_b in _cands:
                _res = MangaTranslator._ink_slant_core(_ink_b, h_c, w_c)
                if _res is not None:
                    return _res
            return 0.0, False
        except Exception:
            return 0.0, False

    @staticmethod
    def _ink_slant_core(ink, h_c: int, w_c: int) -> Optional[Tuple[float, bool]]:
        try:
            if float(ink.mean()) < 0.010 or float(ink.mean()) > 0.60:
                return None
            n, lab, st, _cents = cv2.connectedComponentsWithStats(ink, connectivity=8)
            crop_area = float(max(1.0, h_c * w_c))
            clean = np.zeros_like(ink)
            comp_ang: List[float] = []
            for i in range(1, n):
                a_ = int(st[i, cv2.CC_STAT_AREA])
                if a_ < 12 or a_ > 0.08 * crop_area:
                    continue
                x_c = int(st[i, cv2.CC_STAT_LEFT])
                y_c = int(st[i, cv2.CC_STAT_TOP])
                bw_ = int(st[i, cv2.CC_STAT_WIDTH])
                bh_ = int(st[i, cv2.CC_STAT_HEIGHT])
                touches = ((x_c <= 0) + (y_c <= 0)
                           + (x_c + bw_ >= w_c) + (y_c + bh_ >= h_c))
                aspect = max(bw_, bh_) / max(1.0, float(min(bw_, bh_)))
                if a_ < 0.25 * float(max(1, bw_ * bh_)):
                    continue
                if touches >= 2 or (touches >= 1 and aspect > 3.0):
                    continue
                if touches == 1:
                    border_span = 0.0
                    if x_c <= 0 or x_c + bw_ >= w_c:
                        border_span = bh_ / float(h_c)
                    else:
                        border_span = bw_ / float(w_c)
                    if border_span > 0.45 or aspect > 1.9:
                        continue
                clean[lab == i] = 1
                try:
                    _pc = np.column_stack(np.nonzero(lab == i))[:, ::-1].astype(np.float32)
                    _ca = MangaTranslator._poly_long_side_angle(_pc)
                    if abs(_ca) >= 3.0:
                        comp_ang.append(_ca)
                except Exception:
                    pass
            if float(clean.mean()) < 0.008:
                return None
            ys_, xs_ = np.nonzero(clean)
            if len(ys_) < 60:
                return None
            ys_f = ys_.astype(np.float64)
            xs_f = xs_.astype(np.float64)

            def _score(theta_deg: float) -> float:
                t = float(np.tan(np.radians(theta_deg)))
                rows = ys_f - t * xs_f
                idx = (rows - rows.min()).astype(np.int32)
                hist = np.bincount(idx)
                hf = hist.astype(np.float64)
                return float(np.dot(hf, hf))

            best_t, best_s = 0.0, -1.0
            for td in range(-45, 46, 3):
                s_ = _score(float(td))
                if s_ > best_s:
                    best_s, best_t = s_, float(td)
            for td in np.arange(best_t - 3.0, best_t + 3.01, 0.5):
                s_ = _score(float(td))
                if s_ > best_s:
                    best_s, best_t = s_, float(td)
            try:
                if best_s < 1.12 * max(1.0, _score(0.0)):
                    return (0.0, True)
            except Exception:
                pass
            a = float(best_t)
            if abs(a) > 45.0:
                return None
            if abs(a) < 5.0:
                return (0.0, True)
            if len(comp_ang) >= 3:
                _med = float(np.median(comp_ang))
                if abs(_med) >= 5.0 and (_med > 0.0) != (a > 0.0):
                    return (_med, True)
            return (a, True)
        except Exception:
            return None

    @staticmethod
    def _polys_vertical(polys) -> bool:
        tall = wide = 0
        for p in list(polys or []):
            try:
                pp = np.asarray(p, dtype=np.float32).reshape(-1, 2)
            except Exception:
                continue
            if pp.shape[0] < 3:
                continue
            pw_ = float(pp[:, 0].max() - pp[:, 0].min())
            ph_ = float(pp[:, 1].max() - pp[:, 1].min())
            if ph_ >= 1.3 * pw_ and ph_ >= 18.0:
                tall += 1
            elif pw_ >= 1.3 * ph_ and pw_ >= 18.0:
                wide += 1
        return tall > wide

    @staticmethod
    def _ink_bitmap_polar(crop_bgr, poly_mask=None):
        try:
            if crop_bgr is None or getattr(crop_bgr, "size", 0) == 0:
                return None
            h_c, w_c = crop_bgr.shape[:2]
            g = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
            med = float(np.median(g))
            _dark = (g < max(60.0, med - 45.0))
            _bright = (g > min(195.0, max(med + 45.0, 150.0)))
            if poly_mask is not None:
                _keep = (poly_mask > 0)
                _dark = _dark & _keep
                _bright = _bright & _keep
            _cands = []
            _fd = float(_dark.mean())
            _fb = float(_bright.mean())
            if 0.010 <= _fd <= 0.45:
                _cands.append(_dark)
            if 0.010 <= _fb <= 0.45:
                _cands.append(_bright)
            if not _cands:
                if 0.45 < _fd <= 0.60:
                    _cands.append(_dark)
                elif 0.010 <= _fb <= 0.60:
                    _cands.append(_bright)
                else:
                    return None
            _cands.sort(key=lambda _b: float(_b.mean()))
            for _ink in _cands:
                n_, lab_, st_, _c = cv2.connectedComponentsWithStats(
                    _ink.astype(np.uint8), connectivity=8)
                clean = np.zeros(_ink.shape, np.uint8)
                for i in range(1, n_):
                    a_ = int(st_[i, cv2.CC_STAT_AREA])
                    if a_ < 12:
                        continue
                    x_c = int(st_[i, cv2.CC_STAT_LEFT])
                    y_c = int(st_[i, cv2.CC_STAT_TOP])
                    bw_ = int(st_[i, cv2.CC_STAT_WIDTH])
                    bh_ = int(st_[i, cv2.CC_STAT_HEIGHT])
                    touches = ((x_c <= 0) + (y_c <= 0)
                               + (x_c + bw_ >= w_c) + (y_c + bh_ >= h_c))
                    if touches >= 2:
                        continue
                    clean[lab_ == i] = 1
                if int(clean.sum()) >= 80:
                    return clean
            return None
        except Exception:
            return None

    @staticmethod
    def _curve_path_from_ink(original_image, region):
        try:
            polys_raw = list(getattr(region, "ocr_polys", None) or [])
            if not polys_raw or original_image is None:
                return None
            polys = []
            for p in polys_raw:
                try:
                    pp = np.asarray(p, dtype=np.float32).reshape(-1, 2)
                except Exception:
                    continue
                if pp.shape[0] >= 3:
                    polys.append(pp)
            if not polys:
                return None
            try:
                _lines = MangaTranslator._group_polys_to_lines(polys_raw)
            except Exception:
                _lines = []
            if _lines and len(_lines) != 1:
                return None
            try:
                if MangaTranslator._polys_vertical(polys_raw):
                    return None
            except Exception:
                pass
            _pts_all = np.concatenate(polys, axis=0)
            _cx0 = float(_pts_all[:, 0].min()) - 4.0
            _cy0 = float(_pts_all[:, 1].min()) - 4.0
            _cx1 = float(_pts_all[:, 0].max()) + 4.0
            _cy1 = float(_pts_all[:, 1].max()) + 4.0
            _ix0 = max(0, int(_cx0))
            _iy0 = max(0, int(_cy0))
            _ix1 = min(int(original_image.shape[1]), int(np.ceil(_cx1)))
            _iy1 = min(int(original_image.shape[0]), int(np.ceil(_cy1)))
            if _ix1 - _ix0 < 64 or _iy1 - _iy0 < 12:
                return None
            _mask = MangaTranslator._ocr_poly_mask(
                (_iy1 - _iy0, _ix1 - _ix0), polys_raw, _ix0, _iy0)
            ink = MangaTranslator._ink_bitmap_polar(
                original_image[_iy0:_iy1, _ix0:_ix1], _mask)
            if ink is None:
                return None
            ys_, xs_ = np.nonzero(ink)
            if len(ys_) < 80:
                return None
            pts = np.stack([xs_, ys_], 1).astype(np.float64)
            cen = pts.mean(axis=0)
            c = pts - cen
            cov = np.cov(c.T)
            ev_, evec = np.linalg.eigh(cov)
            main = evec[:, int(np.argmax(ev_))]
            ang = float(np.degrees(np.arctan2(main[1], main[0])))
            if ang > 90.0:
                ang -= 180.0
            if ang < -90.0:
                ang += 180.0
            if abs(ang) > 60.0:
                return None
            ca, sa = float(np.cos(np.radians(-ang))), float(np.sin(np.radians(-ang)))
            rx = c[:, 0] * ca - c[:, 1] * sa
            ry = c[:, 0] * sa + c[:, 1] * ca
            x0, x1 = float(rx.min()), float(rx.max())
            span = x1 - x0
            if span < 64.0:
                return None
            nb = int(np.clip(round(span / 3.0), 10, 64))
            cols = []
            chs = []
            for i in range(nb):
                lo = x0 + span * i / nb
                hi = x0 + span * (i + 1) / nb
                sel = (rx >= lo) & (rx < hi)
                if sel.sum() >= 4:
                    _yy = ry[sel]
                    cols.append(((lo + hi) / 2.0, float(_yy.mean())))
                    chs.append(float(_yy.max() - _yy.min()))
            if len(cols) < 8 or not chs:
                return None
            cxs = np.array([p[0] for p in cols])
            cys = np.array([p[1] for p in cols])
            try:
                _rs = ink.sum(axis=1)
                _bands = []
                _inr = False
                _bs = 0
                for _yy in range(ink.shape[0]):
                    if _rs[_yy] > 0:
                        if not _inr:
                            _inr = True
                            _bs = _yy
                    else:
                        if _inr:
                            _inr = False
                            _bands.append((_bs, _yy))
                if _inr:
                    _bands.append((_bs, ink.shape[0]))
                if len(_bands) >= 2:
                    _bh = [b - a for (a, b) in _bands]
                    _bg = [_bands[k + 1][0] - _bands[k][1]
                           for k in range(len(_bands) - 1)]
                    if _bh and _bg and max(_bg) >= 0.20 * max(_bh):
                        return None
            except Exception:
                pass
            _cha = np.asarray(chs, dtype=np.float64)
            _med_ch = float(np.median(_cha))
            if _med_ch <= 0.0:
                return None
            if _med_ch > 0.70 * float(_iy1 - _iy0):
                return None
            _full = _cha >= 0.60 * _med_ch
            if int(_full.sum()) < 8:
                return None
            _fch = _cha[_full]
            if float(_fch.std()) > 0.28 * float(np.median(_fch)):
                return None
            cxs = cxs[_full]
            cys = cys[_full]
            _n_ch = len(chs)
            _edge = max(2, int(round(_n_ch * 0.20)))
            _pool = chs[:_edge] + chs[-_edge:] \
                + [float(np.percentile(chs, 25))]
            ch_med = float(np.median(chs))
            row_h = float(np.clip(np.median(_pool), 7.0, ch_med))
            lh = ch_med
            if lh < 8.0:
                return None
            if len(cys) >= 5:
                _sm = cys.copy()
                for i in range(len(cys)):
                    lo_i = max(0, i - 1)
                    hi_i = min(len(cys), i + 2)
                    _sm[i] = float(np.median(cys[lo_i:hi_i]))
                cys = _sm
            A = np.stack([cxs ** 2, cxs, np.ones_like(cxs)], 1)
            coef, *_ = np.linalg.lstsq(A, cys, rcond=None)
            qa, qb, qc = [float(k) for k in coef]
            chord = cys[0] + (cys[-1] - cys[0]) * (cxs - cxs[0]) / max(1e-9, cxs[-1] - cxs[0])
            fit = qa * cxs ** 2 + qb * cxs + qc
            sag = float(np.max(np.abs(fit - chord)))
            d_ang = float(np.degrees(np.arctan(2.0 * qa * cxs[-1] + qb))
                          - np.degrees(np.arctan(2.0 * qa * cxs[0] + qb)))
            if sag < max(3.5, 0.12 * row_h):
                return None
            if abs(d_ang) < 12.0 or abs(d_ang) > 75.0:
                return None
            fit_at_ink = qa * rx ** 2 + qb * rx + qc
            resid = ry - fit_at_ink
            resid_std = float(np.std(resid))
            frac_near = float(np.mean(np.abs(resid) <= 0.70 * lh))
            if resid_std > 0.55 * lh or frac_near < 0.82:
                return None
            try:
                for q in polys:
                    _ql = np.asarray(q, dtype=np.float64) \
                        - np.array([_ix0, _iy0], np.float64)
                    _qr = (_ql[:, 0] - cen[0]) * ca \
                        - (_ql[:, 1] - cen[1]) * sa
                    _p_span = float(_qr.max() - _qr.min())
                    if _p_span < 0.55 * span:
                        continue
                    _t_l = float(np.degrees(np.arctan(
                        2.0 * qa * float(_qr.min()) + qb)))
                    _t_r = float(np.degrees(np.arctan(
                        2.0 * qa * float(_qr.max()) + qb)))
                    if abs(_t_r - _t_l) > 60.0:
                        return None
            except Exception:
                pass
            for q in polys:
                try:
                    _pa = float(MangaTranslator._poly_long_side_angle(q))
                    _ql = np.asarray(q, dtype=np.float64) \
                        - np.array([_ix0, _iy0], np.float64)
                    _qr = (_ql[:, 0] - cen[0]) * ca \
                        - (_ql[:, 1] - cen[1]) * sa
                    _p_span = float(_qr.max() - _qr.min())
                    if _p_span >= 0.55 * span:
                        if abs(_pa - ang) > 16.0:
                            return None
                        continue
                    _p_cx = float((_ql[:, 0].min() + _ql[:, 0].max()) / 2.0)
                    _p_cy = float((_ql[:, 1].min() + _ql[:, 1].max()) / 2.0)
                    _prx = (_p_cx - cen[0]) * ca - (_p_cy - cen[1]) * sa
                    _tan = float(np.degrees(np.arctan(2.0 * qa * _prx + qb)))
                    if abs(_tan) > 60.0:
                        return None
                    if abs(_pa - ang - _tan) > 16.0:
                        return None
                except Exception:
                    continue
            n_s = 24
            ts = np.linspace(cxs[0], cxs[-1], n_s)
            fy = qa * ts ** 2 + qb * ts + qc
            ca2, sa2 = float(np.cos(np.radians(ang))), float(np.sin(np.radians(ang)))
            px = ts * ca2 - fy * sa2 + cen[0] + float(_ix0)
            py = ts * sa2 + fy * ca2 + cen[1] + float(_iy0)
            path = np.stack([px, py], 1)
            if float(np.hypot(*(path[-1] - path[0]))) < 0.5 * span:
                return None
            return {
                "path": [[round(float(p[0]), 2), round(float(p[1]), 2)]
                         for p in path],
                "lh": round(row_h, 2),
                "lh_band": round(lh, 2),
                "sag": round(sag, 2),
                "d_ang": round(d_ang, 2),
                "angle": round(ang, 2),
                "arc_len": round(float(np.sum(
                    np.hypot(np.diff(path[:, 0]), np.diff(path[:, 1])))), 2),
            }
        except Exception:
            return None

    @staticmethod
    def _add_watermark_regions(image, regions):
        try:
            import re as _re
            ocr_engine = None
            try:
                from rapidocr_onnxruntime import RapidOCR as _R
                ocr_engine = _R()
            except Exception:
                return regions
            res, _ = ocr_engine(image)
            if not res:
                return regions
            _wm_pat = _re.compile(
                r"(www\.|https?://|[a-z0-9-]+\.(?:com|net|org|io|xyz)"
                r"(?:/[A-Za-z0-9._/-]*)?|patreon\b|chapter\s*\d+\s*"
                r".{0,30}?page\s*\d+)", _re.I)
            existing = []
            for _r in (regions or []):
                try:
                    existing.append(tuple(int(v) for v in _r.rect[:4]))
                except Exception:
                    pass
            out = list(regions or [])
            for box, txt, conf in res:
                try:
                    t = str(txt or "").strip()
                    if not t or float(conf) < 0.60:
                        continue
                    if not _wm_pat.search(t):
                        continue
                    xs = [p[0] for p in box]
                    ys = [p[1] for p in box]
                    x0, y0 = int(min(xs)), int(min(ys))
                    x1, y1 = int(max(xs)), int(max(ys))
                    if (x1 - x0) < 12 or (y1 - y0) < 6:
                        continue
                    _ov = False
                    for (_ex, _ey, _ew, _eh) in existing:
                        if not (x1 < _ex or x0 > _ex + _ew
                                or y1 < _ey or y0 > _ey + _eh):
                            _ov = True
                            break
                    if _ov:
                        continue
                    _nr = TextRegion(
                        id=-1,
                        boxes=[np.asarray(box, dtype=np.int32)],
                        source_text=t,
                        translated_text="",
                        rect=(x0, y0,
                              max(1, x1 - x0), max(1, y1 - y0)),
                        det_class="text",
                        kind="promo",
                        bubble_style="free_text",
                        ocr_polys=[np.asarray(box, dtype=np.int32)])
                    out.append(_nr)
                except Exception:
                    continue
            return out
        except Exception:
            return regions

    @staticmethod
    def _polys_dense(polys) -> bool:
        tall = wide = 0
        _pl: List[np.ndarray] = []
        for p in list(polys or []):
            try:
                pp = np.asarray(p, dtype=np.float32).reshape(-1, 2)
            except Exception:
                continue
            if pp.shape[0] < 3:
                continue
            _pl.append(pp)
            pw_ = float(pp[:, 0].max() - pp[:, 0].min())
            ph_ = float(pp[:, 1].max() - pp[:, 1].min())
            if ph_ >= 1.3 * pw_ and ph_ >= 18.0:
                tall += 1
            elif pw_ >= 1.3 * ph_ and pw_ >= 18.0:
                wide += 1
        if tall > 0 or wide < 2 or len(_pl) < 2:
            return False
        try:
            _all = np.concatenate(_pl, axis=0)
            _ua = max(1.0, float(_all[:, 0].max() - _all[:, 0].min())
                      * float(_all[:, 1].max() - _all[:, 1].min()))
            _sa = 0.0
            for _q in _pl:
                _sa += 0.5 * abs(float(np.dot(
                    _q[:, 0], np.roll(_q[:, 1], -1))
                    - np.dot(_q[:, 1], np.roll(_q[:, 0], -1))))
            return (_sa / _ua) >= 0.34
        except Exception:
            return False

    @staticmethod
    def _text_block_box(polys, rect, vert: bool):
        try:
            _pl = []
            for p in list(polys or []):
                try:
                    pp = np.asarray(p, dtype=np.float32).reshape(-1, 2)
                except Exception:
                    continue
                if pp.shape[0] >= 3:
                    _pl.append(pp)
            if not _pl:
                return None
            _all = np.concatenate(_pl, axis=0)
            ux0 = float(_all[:, 0].min())
            ux1 = float(_all[:, 0].max())
            uy0 = float(_all[:, 1].min())
            uy1 = float(_all[:, 1].max())
            _ws = [float(p[:, 0].max() - p[:, 0].min()) for p in _pl]
            _hs = [float(p[:, 1].max() - p[:, 1].min()) for p in _pl]
            if vert:
                _mw = float(np.median(_ws)) if _ws else 30.0
                pad_x = max(6.0, 0.55 * _mw)
                pad_y = max(4.0, 0.30 * _mw)
            else:
                _mh = float(np.median(_hs)) if _hs else 20.0
                pad_y = max(6.0, 0.55 * _mh)
                pad_x = max(4.0, 0.35 * _mh)
            ux0 -= pad_x
            ux1 += pad_x
            uy0 -= pad_y
            uy1 += pad_y
            if rect:
                rx, ry, rw, rh = [float(v) for v in rect]
                if not vert:
                    _capw = 0.18 * max(4.0, rw)
                    _caph = 0.30 * max(4.0, rh)
                    _near_t = 0.0 <= uy0 - ry <= _caph
                    _near_b = 0.0 <= (ry + rh) - uy1 <= _caph
                    _near_l = 0.0 <= ux0 - rx <= _capw
                    _near_r = 0.0 <= (rx + rw) - ux1 <= _capw
                    if _near_t and _near_b:
                        uy0, uy1 = ry, ry + rh
                    if _near_l and _near_r:
                        ux0, ux1 = rx, rx + rw
                ux0 = max(ux0, rx)
                uy0 = max(uy0, ry)
                ux1 = min(ux1, rx + max(4.0, rw))
                uy1 = min(uy1, ry + max(4.0, rh))
            bx0, by0 = int(np.floor(ux0)), int(np.floor(uy0))
            bx1, by1 = int(np.ceil(ux1)), int(np.ceil(uy1))
            if bx1 - bx0 >= 8 and by1 - by0 >= 8:
                return (bx0, by0, bx1 - bx0, by1 - by0)
        except Exception:
            return None
        return None

    @staticmethod
    def _estimate_angle_from_polys(polys) -> float:
        angs: List[float] = []
        for p in list(polys or []):
            angs.append(MangaTranslator._poly_long_side_angle(p))
        if not angs:
            return 0.0
        return float(np.median(angs))

    def _split_mixed_column_regions(self, regions: List["TextRegion"]) -> List["TextRegion"]:
        out: List["TextRegion"] = []
        for r in regions:
            try:
                if getattr(r, "sys_span", None) or getattr(r, "sys_split", False):
                    out.append(r)
                    continue
                if abs(float(getattr(r, "angle", 0.0) or 0.0)) >= 8.0:
                    out.append(r)
                    continue
                if getattr(r, "kind", "dialogue") in (
                        "system", "promo", "junk", "sfx", "free_text"):
                    out.append(r)
                    continue
                polys = [p for p in (r.ocr_polys or [])
                         if p is not None and len(np.asarray(p).reshape(-1, 2)) >= 3]
                txt = (r.source_text or "").strip()
                if len(polys) < 4 or "\n" not in txt:
                    out.append(r)
                    continue
                parts = [p.strip() for p in txt.split("\n") if p.strip()]
                if len(parts) < 2:
                    out.append(r)
                    continue
                bbs = []
                for p in polys:
                    pp = np.asarray(p, dtype=np.float32).reshape(-1, 2)
                    bbs.append((float(pp[:, 0].min()), float(pp[:, 1].min()),
                                float(pp[:, 0].max()), float(pp[:, 1].max())))
                groups = MangaTranslator._column_line_groups(
                    list(range(len(polys))), bbs,
                    rtl=(getattr(self, "reading_order", "rtl") == "rtl"))
                if not groups or len(groups) < 2 or len(groups) != len(parts):
                    out.append(r)
                    continue
                med_h = float(np.median([bbs[i][3] - bbs[i][1]
                                         for i in range(len(polys))]))
                spans = sorted(
                    [(min(bbs[i][0] for i in g), max(bbs[i][2] for i in g))
                     for g in groups], key=lambda s: s[0])
                _ok = True
                for _a in range(len(spans) - 1):
                    if spans[_a][1] - spans[_a + 1][0] > max(10.0, 0.45 * med_h):
                        _ok = False
                        break
                if not _ok:
                    out.append(r)
                    continue
                if self.debug:
                    try:
                        print("    [*]ناحیهٔ چندستونی → "
                              f"{len(groups)} ناحیهٔ جدا: "
                              + " | ".join(p[:30] for p in parts))
                    except Exception:
                        pass
                for gi, g in enumerate(groups):
                    xs0 = int(min(bbs[i][0] for i in g)) - 3
                    ys0 = int(min(bbs[i][1] for i in g)) - 3
                    xs1 = int(max(bbs[i][2] for i in g)) + 3
                    ys1 = int(max(bbs[i][3] for i in g)) + 3
                    nx0, ny0 = max(0, xs0), max(0, ys0)
                    out.append(TextRegion(
                        id=-1,
                        boxes=[np.array([[nx0, ny0], [max(nx0 + 1, xs1), ny0],
                                         [max(nx0 + 1, xs1), max(ny0 + 1, ys1)],
                                         [nx0, max(ny0 + 1, ys1)]],
                                        dtype=np.int32)],
                        source_text=parts[gi],
                        rect=(nx0, ny0, max(1, xs1 - nx0), max(1, ys1 - ny0)),
                        angle=float(getattr(r, "angle", 0.0) or 0.0),
                        kind=getattr(r, "kind", "dialogue"),
                        bubble_style=getattr(r, "bubble_style", "normal"),
                        det_class=getattr(r, "det_class", "") or "",
                        ocr_polys=[np.asarray(polys[i], dtype=np.int32)
                                   for i in g],
                    ))
            except Exception:
                out.append(r)
        return out

    def _extract_regions_from_bubbles(self, image: np.ndarray,
                                       page_cache: Optional[dict] = None
                                       ) -> Tuple[List[TextRegion], list]:

        if self.det is None:
            return [], []
        boxes = self.det.detect(image)
        if not boxes:
            return [], []
        n0 = len(boxes)
        _raw_det_dbg = []
        if self.debug:
            try:
                _raw_det_dbg = [
                    ([int(v) for v in _b["rect"][:4]],
                     str(_b.get("class_name") or ""))
                    for _b in boxes]
            except Exception:
                _raw_det_dbg = []
        boxes = self._drop_contained_boxes(boxes, contain_thresh=0.72)
        if len(boxes) < n0 and self.debug:
            print(f"    [*] {n0 - len(boxes)} باکس تودرتو/تکراری حذف شد (از {n0})")

        expanded: List[dict] = []
        split_groups: List[Tuple[List[int], list]] = []
        for b in boxes:
            try:
                parts = MangaTranslator._split_adjacent_balloons(image, b["rect"])
            except Exception:
                parts = [b["rect"]]
            if len(parts) > 1:
                try:
                    if self._split_cuts_text(image, b["rect"], parts):
                        print(f"    [*] برشِ باکس {b['rect']} به {len(parts)} "
                              f"حباب لغو شد — خطِ متن از مرز میگذشت (باکس کامل حفظ شد)")
                        parts = [[int(v) for v in b["rect"][:4]]]
                except Exception:
                    pass
            if len(parts) > 1:
                print(f"    [*] باکس {b['rect']} شامل {len(parts)} حباب چسبیده → جدا شدند")
                idxs: List[int] = []
                for p in parts:
                    idxs.append(len(expanded))
                    nb = dict(b)
                    nb["rect"] = p
                    expanded.append(nb)
                split_groups.append((idxs, [int(v) for v in b["rect"][:4]]))
            else:
                expanded.append(b)
        boxes = expanded
        try:
            page_boxes = [
                (int(b["rect"][0]), int(b["rect"][1]),
                 int(b["rect"][2]), int(b["rect"][3]),
                 str(b.get("class_name") or ""))
                for b in boxes
            ]
        except Exception:
            page_boxes = []

        regions: List[TextRegion] = []
        h, w = image.shape[:2]
        page_area = float(max(1, min(h, RTDetrV2ONNXDetector.TILE_HEIGHT) * w))
        cand: List[Tuple[int, dict, int, int, int, int, int, int]] = []
        for i, b in enumerate(boxes):
            x1, y1, x2, y2 = b["rect"]
            x1, y1 = max(0, int(x1)), max(0, int(y1))
            x2, y2 = min(w, int(x2)), min(h, int(y2))
            bw, bh = x2 - x1, y2 - y1
            if bw < 16 or bh < 16:
                if self.debug:
                    print(f"    [*] باکسِ ریزِ detector حذف شد: ({x1},{y1},{bw}x{bh})")
                continue

            if bw * bh < page_area * 0.0008 and max(bw, bh) < 60:
                if self.debug:
                    print(f"    [*] باکسِ خیلی کوچک حذف شد: ({x1},{y1},{bw}x{bh})")
                continue
            cand.append((i, b, x1, y1, x2, y2, bw, bh))
        ocr_results: List[Tuple[str, List[np.ndarray], List[float]]] = [
            ("", [], [], [], [])] * len(cand)
        if cand:
            _all_rects = [(t[2], t[3], t[4], t[5]) for t in cand]

            def _ocr_one(k: int):
                _t = cand[k]
                _blk = [_all_rects[j]
                          for j in range(len(_all_rects)) if j != k]
                return self._ocr_crop(
                    image, [_t[2], _t[3], _t[4], _t[5]],
                    block_rects=_blk, page_cache=page_cache)

            n_workers = max(1, min(int(getattr(self, "max_workers", 3) or 1), len(cand)))
            _ocr_ts = isinstance(self.ocr, RapidOCRBackend)
            if n_workers > 1 and _ocr_ts:
                if self.debug and not getattr(self, "_par_note", False):
                    self._par_note = True
                    print(f"    [*] استخراجِ موازی: {len(cand)} ناحیه × "
                          f"{n_workers} کارگر (cpu={os.cpu_count()})")
                with ThreadPoolExecutor(max_workers=n_workers) as ex:
                    ocr_results = list(ex.map(_ocr_one, range(len(cand))))
            else:
                ocr_results = [_ocr_one(k) for k in range(len(cand))]

        for _k in range(len(cand)):
            _t = cand[_k]
            ocr_results[_k] = _clamp_lines_to_det(
                ocr_results[_k], (_t[2], _t[3], _t[4], _t[5]),
                _all_rects)

        if split_groups:
            for idxs, full_rect in split_groups:
                try:
                    any_text = any(
                        str(ocr_results[j][0] or "").strip()
                        for j in idxs if 0 <= j < len(ocr_results)
                    )
                except Exception:
                    any_text = True
                if any_text:
                    continue
                full_txt, full_polys, full_angs, _full_lts, _full_blks = \
                    _clamp_lines_to_det(
                        self._ocr_crop(
                            image, full_rect,
                            block_rects=[(cand[j][2], cand[j][3], cand[j][4],
                                          cand[j][5])
                                         for j in range(len(cand))
                                         if j not in idxs],
                            page_cache=page_cache),
                        full_rect,
                        [(cand[j][2], cand[j][3], cand[j][4], cand[j][5])
                         for j in range(len(cand)) if j not in idxs])
                if not str(full_txt or "").strip():
                    continue
                if self.debug:
                    print(f"    [*] اجزای شکسته خالی بودند → OCR باکس کامل {full_rect}")
                fx1, fy1, fx2, fy2 = full_rect
                cand.append((len(cand), {
                    "class_name": "text_bubble", "confidence": 0.40,
                    "rect": full_rect, "shape_type": "round", "mask_poly": None,
                }, fx1, fy1, fx2, fy2, fx2 - fx1, fy2 - fy1))
                ocr_results.append((full_txt, full_polys, full_angs,
                                    _full_lts, _full_blks))

        if cand:
            for _k in range(len(cand)):
                try:
                    if str(ocr_results[_k][0] or "").strip():
                        continue
                    _tk = cand[_k]
                    _blk = [(_all_rects[j] if j < len(_all_rects)
                             else (cand[j][2], cand[j][3],
                                   cand[j][4], cand[j][5]))
                            for j in range(len(cand)) if j != _k]
                    _hits = self._rec_rescue_missed_quads(
                        image, (_tk[2], _tk[3], _tk[4], _tk[5]),
                        _blk, ocr_results[_k][1] or [])
                    if not _hits:
                        continue
                    _txt, _polys, _angs, _lts, _blks = ocr_results[_k]
                    for _ht, _hp, _hc in _hits:
                        _polys = list(_polys or []) + [_hp]
                        _lts = list(_lts or []) + [_ht]
                        _blks = list(_blks or []) + [-1]
                        _angs = list(_angs or []) + [
                            float(MangaTranslator._poly_long_side_angle(_hp))]
                    _nt = " ".join(str(_t or "").strip()
                                   for _t in _lts if str(_t or "").strip())
                    ocr_results[_k] = (_nt, _polys, _angs, _lts, _blks)
                    print(f"    [✓] نجاتِ rec: ناحیهٔ {_tk[0]} — "
                          f"{len(_hits)} کوار دوباره خوانده شد "
                          f"→ «{_nt[:60]}»")
                except Exception:
                    continue

        for (i, b, x1, y1, x2, y2, bw, bh), (text, line_polys, line_angs,
                                             line_texts, line_blks) in zip(
                cand, ocr_results):
            if not text:
                _gink = 0.0
                try:
                    _gx1, _gy1 = max(0, int(x1)), max(0, int(y1))
                    _gx2 = min(image.shape[1], int(x2))
                    _gy2 = min(image.shape[0], int(y2))
                    if _gx2 - _gx1 >= 12 and _gy2 - _gy1 >= 12:
                        _gcrop = image[_gy1:_gy2, _gx1:_gx2]
                        _gg = cv2.cvtColor(_gcrop, cv2.COLOR_BGR2GRAY)
                        _gmed = float(np.median(_gg))
                        _gink = float((_gg < max(60.0, _gmed - 45.0)).mean())
                except Exception:
                    _gink = 0.0
                if line_polys and 0.008 <= _gink <= 0.50:
                    try:
                        _dupe = None
                        for _j in range(len(cand)):
                            if _j == i:
                                continue
                            _jt = ""
                            if _j < len(ocr_results):
                                _jt = str(
                                    (ocr_results[_j][0] if ocr_results[_j]
                                     else "") or "").strip()
                            if not _jt:
                                continue
                            _jc = cand[_j]
                            _jx1, _jy1 = float(_jc[2]), float(_jc[3])
                            _jx2, _jy2 = float(_jc[4]), float(_jc[5])
                            _ix3 = max(0.0, min(x2, _jx2) - max(x1, _jx1))
                            _iy3 = max(0.0, min(y2, _jy2) - max(y1, _jy1))
                            _inter = _ix3 * _iy3
                            if _inter <= 0:
                                continue
                            _aA = max(1e-6, float((x2 - x1) * (y2 - y1)))
                            _aB = max(1e-6, (_jx2 - _jx1) * (_jy2 - _jy1))
                            _iom = _inter / min(_aA, _aB)
                            if _iom >= 0.28:
                                _dupe = (_j, _iom)
                                break
                        if _dupe is not None:
                            if self.debug:
                                print(f"    [*] Region [{i}] باکسِ تکراریِ "
                                      f"حبابِ متن‌دار (هم‌پوشانیِ "
                                      f"{_dupe[1]*100:.0f}% با کاندیدِ "
                                      f"{_dupe[0]}) → حذف شد")
                            continue
                    except Exception:
                        pass
                    _dots = False
                    try:
                        _gx1, _gy1 = max(0, int(x1)), max(0, int(y1))
                        _gx2 = min(image.shape[1], int(x2))
                        _gy2 = min(image.shape[0], int(y2))
                        _gc2 = image[_gy1:_gy2, _gx1:_gx2]
                        _gg2 = cv2.cvtColor(_gc2, cv2.COLOR_BGR2GRAY)
                        _gm2 = float(np.median(_gg2))
                        _mk2 = ((_gg2 < max(60.0, _gm2 - 45.0))
                                .astype(np.uint8))
                        _nl2, _l2, _st2, _c2 = cv2.connectedComponentsWithStats(
                            _mk2, connectivity=8)
                        _ncomp2 = 0
                        _maxh2 = 0.0
                        for _ci2 in range(1, _nl2):
                            _a2 = float(_st2[_ci2, cv2.CC_STAT_AREA])
                            if _a2 < 6:
                                continue
                            _w2 = float(_st2[_ci2, cv2.CC_STAT_WIDTH])
                            _h2 = float(_st2[_ci2, cv2.CC_STAT_HEIGHT])
                            if _w2 * _h2 > 0 and \
                                    _a2 / (_w2 * _h2) < 0.22:
                                continue
                            _ncomp2 += 1
                            _maxh2 = max(_maxh2, _h2)
                        if _ncomp2 <= 10 and \
                                _maxh2 < 0.18 * max(1, _gy2 - _gy1):
                            _dots = True
                    except Exception:
                        _dots = False
                    if _dots:
                        if self.debug:
                            print(f"    [*] Region [{i}] جوهرِ نقطه/نمادِ "
                                  f"ریز است → دست‌نخورده")
                        continue
                    _epoly = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]],
                                      dtype=np.int32)
                    regions.append(TextRegion(
                        id=i,
                        boxes=[_epoly],
                        source_text="",
                        rect=(x1, y1, bw, bh),
                        angle=0.0,
                        kind="dialogue",
                        ocr_polys=[],
                        det_class=b.get("class_name", "") or "",
                    ))
                    regions[-1].ocr_empty = True
                    if self.debug:
                        print(f"    [!] Region [{i}] had no OCR text but has "
                              f"text-like ink → cleaning only")
                continue

            if self._is_non_english_script(text):
                continue

            try:
                _sys_score = MangaTranslator._system_window_score(
                    text, line_texts, line_polys, (x1, y1, x2, y2))
                _sys_strong = MangaTranslator._system_window_strong(
                    text, line_texts)
            except Exception:
                _sys_score, _sys_strong = 0, False
            _lbl_block = MangaTranslator._is_label_block(line_texts or [])
            _sys_ok = _sys_strong and (
                _sys_score >= 5
                or (len(line_polys) <= 1
                    and len(str(text or '').strip()) <= 28)
                or _lbl_block)
            _sys_can_split = (
                _sys_ok
                and len(line_polys) >= 2
                and len(line_texts or []) == len(line_polys)
                and (_lbl_block or _sys_score >= 6))
            if os.environ.get("MANGA_SYS_DEBUG"):
                try:
                    print(f"    [SYSDBG] text={str(text)[:60]!r} score={_sys_score} "
                          f"strong={_sys_strong} nlp={len(line_polys)} "
                          f"nlt={len(line_texts or [])} lbl={_lbl_block} "
                          f"ok={_sys_ok} cansplit={_sys_can_split}")
                except Exception:
                    pass
            if _sys_can_split:
                _lines = MangaTranslator._cluster_ocr_lines(
                    line_polys, line_texts or [])
                _made = 0
                for (_qx1, _qy1, _qx2, _qy2, _lt) in _lines:
                    _lt = _lt.strip()
                    if not _lt:
                        continue
                    _lx1 = int(max(0, np.floor(_qx1)) - 4)
                    _ly1 = int(max(0, np.floor(_qy1)) - 3)
                    _lx2 = int(min(w - 1, np.ceil(_qx2)) + 4)
                    _ly2 = int(min(h - 1, np.ceil(_qy2)) + 3)
                    if _lx2 - _lx1 < 12 or _ly2 - _ly1 < 8:
                        continue
                    _lpoly = np.array(
                        [[_lx1, _ly1], [_lx2, _ly1], [_lx2, _ly2], [_lx1, _ly2]],
                        dtype=np.int32)
                    _sr = TextRegion(
                        id=len(regions),
                        boxes=[_lpoly],
                        source_text=_lt,
                        rect=(_lx1, _ly1, _lx2 - _lx1, _ly2 - _ly1),
                        angle=0.0,
                        kind="dialogue",
                        bubble_style="system",
                        ocr_polys=[_lpoly],
                        det_class=b.get("class_name", "") or "",
                    )
                    _sr.style_locked = True
                    _sr.sys_split = True
                    _sr.cover_rect = (x1, y1, x2, y2)
                    regions.append(_sr)
                    _made += 1
                if _made:
                    if self.debug:
                        print(f"    [*] پنجرهٔ سیستم → {_made} خط جداگانه")
                    continue

            kind = self._classify_text(text)

            if kind == "dialogue":
                if MangaTranslator._is_watermark_text(text):
                    _scrub = MangaTranslator._strip_watermark_tokens(text)
                    if _scrub and self._classify_text(_scrub) == "dialogue":
                        text = _scrub
                    else:
                        kind = "promo"

            if kind == "junk":
                if not MangaTranslator._is_watermark_text(text):
                    latin = re.sub(r"[^A-Za-z]", "", text)
                    if len(latin) >= 3 and any(c in "AEIOUaeiou" for c in latin):
                        kind = "dialogue"
            poly = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype=np.int32)
            eng_angs = []
            for _a in (line_angs or []):
                try:
                    _af = float(_a)
                except (TypeError, ValueError):
                    continue
                if _af > 180.0:
                    _af -= 360.0
                if abs(_af) > 45.0:
                    continue
                if abs(_af) >= 1.0:
                    eng_angs.append(_af)
            ang_src = "ink"
            poly_ang = self._estimate_angle_from_polys(line_polys)
            if abs(poly_ang) >= 3.0:
                ang_ = poly_ang
                ang_src = "poly"
            elif eng_angs:
                ang_ = float(np.median(eng_angs))
                ang_src = "engine"
            else:
                ang_ = poly_ang
            _is_vert = self._polys_vertical(line_polys)
            if abs(ang_) < 5.0:
                try:
                    if _is_vert:
                        _tx1, _ty1 = float(x1), float(y1)
                        _tx2, _ty2 = float(x2), float(y2)
                    else:
                        _tx1 = _ty1 = None
                        if line_polys:
                            try:
                                _pts_all = np.concatenate(
                                    [np.asarray(p).reshape(-1, 2) for p in line_polys])
                                _tx1, _ty1 = float(_pts_all[:, 0].min()), float(_pts_all[:, 1].min())
                                _tx2, _ty2 = float(_pts_all[:, 0].max()), float(_pts_all[:, 1].max())
                            except Exception:
                                _tx1 = _ty1 = None
                        if _tx1 is None:
                            _tx1, _ty1, _tx2, _ty2 = float(x1), float(y1), float(x2), float(y2)
                    _iy1, _iy2 = max(0, int(_ty1)), min(image.shape[0], int(_ty2) + 1)
                    _ix1, _ix2 = max(0, int(_tx1)), min(image.shape[1], int(_tx2) + 1)
                    if _ix2 - _ix1 >= 40 and _iy2 - _iy1 >= 14:
                        _lmk = MangaTranslator._ocr_poly_mask(
                            (_iy2 - _iy1, _ix2 - _ix1), line_polys,
                            _ix1, _iy1)
                        a_ink2 = MangaTranslator._ink_slant_angle(
                            image[_iy1:_iy2, _ix1:_ix2], _lmk)
                        _thr_ink = 7.0 if _is_vert else 5.0
                        if abs(a_ink2) >= _thr_ink and abs(a_ink2) > abs(ang_) + 1.0:
                            ang_ = a_ink2
                            ang_src = "ink"
                except Exception:
                    pass
            rx1, ry1, rw_, rh_ = x1, y1, bw, bh
            if line_polys and abs(ang_) >= 8.0:
                try:
                    _rx_pts = []
                    for _p in line_polys:
                        try:
                            _pp = np.asarray(_p,
                                                dtype=np.float32).reshape(-1, 2)
                            _qx1 = float(_pp[:, 0].min())
                            _qy1 = float(_pp[:, 1].min())
                            _qx2 = float(_pp[:, 0].max())
                            _qy2 = float(_pp[:, 1].max())
                            _qa = max(1.0, (_qx2 - _qx1) * (_qy2 - _qy1))
                            _ix = max(0.0, min(_qx2, float(x2))
                                         - max(_qx1, float(x1)))
                            _iy = max(0.0, min(_qy2, float(y2))
                                         - max(_qy1, float(y1)))
                            if (_ix * _iy) / _qa >= 0.60:
                                _rx_pts.append(_pp)
                        except Exception:
                            _rx_pts.append(
                                np.asarray(_p).reshape(-1, 2))
                    if not _rx_pts:
                        _rx_pts = [np.asarray(p).reshape(-1, 2)
                                      for p in line_polys]
                    pts = np.concatenate(_rx_pts)
                    px1, py1 = int(pts[:, 0].min()), int(pts[:, 1].min())
                    px2, py2 = int(pts[:, 0].max()) + 1, int(pts[:, 1].max()) + 1
                    rx1, ry1 = min(rx1, px1), min(ry1, py1)
                    rw_ = max(x1 + bw, px2) - rx1
                    rh_ = max(y1 + bh, py2) - ry1
                except Exception:
                    rx1, ry1, rw_, rh_ = x1, y1, bw, bh
            regions.append(TextRegion(
                id=i,
                boxes=[poly],
                source_text=text,
                rect=(rx1, ry1, rw_, rh_),
                angle=ang_,
                kind=kind,
                ocr_polys=line_polys,
                det_class=b.get("class_name", "") or "",
            ))
            regions[-1].angle_src = ang_src
            if _raw_det_dbg:
                regions[-1].det_raw = _raw_det_dbg
            if _sys_ok:
                regions[-1].bubble_style = "system"
                regions[-1].style_locked = True
                if self.debug:
                    print(f"    [*] برچسب/پنجرهٔ سیستم (تک‌قطعه) → فونت سیستم")

        try:
            _sreg = [r for r in regions if getattr(r, "sys_split", False)]
            if len(_sreg) > 1:
                def _riou(_a, _b):
                    ax, ay, aw, ah = _a.rect
                    bx, by, bw2, bh2 = _b.rect
                    ix = max(0, min(ax + aw, bx + bw2) - max(ax, bx))
                    iy = max(0, min(ay + ah, by + bh2) - max(ay, by))
                    inter = ix * iy
                    if inter <= 0:
                        return 0.0
                    return inter / float(min(aw * ah, bw2 * bh2) or 1)
                _keep = []
                for _r in sorted(_sreg, key=lambda r: -(len(r.source_text or "")
                                                        * 1000 + r.rect[2] * r.rect[3])):
                    if any(_riou(_r, _k) >= 0.45 for _k in _keep):
                        continue
                    _keep.append(_r)
                if len(_keep) < len(_sreg):
                    _drop_ids = {id(r) for r in _sreg if r not in _keep}
                    regions = [r for r in regions if id(r) not in _drop_ids]
                    if self.debug:
                        print(f"    [*] {len(_drop_ids)} خط تکراری پنجرهٔ سیستم حذف شد")
        except Exception:
            pass

        try:
            _sys_groups: Dict[Tuple[int, int], List[TextRegion]] = {}
            for _r in regions:
                if not getattr(_r, "sys_split", False):
                    continue
                _cr = getattr(_r, "cover_rect", None)
                _key = (int(_cr[0]), int(_cr[1])) if _cr else (
                    int(_r.rect[0]), int(_r.rect[1]))
                _sys_groups.setdefault(_key, []).append(_r)
            for _grp in _sys_groups.values():
                if not _grp:
                    continue
                _cr = getattr(_grp[0], "cover_rect", None)
                if _cr:
                    _pw = max(1, int(_cr[2]) - int(_cr[0]))
                    _inset = max(6, int(0.03 * _pw))
                    _sx0 = min(int(_cr[0]) + _inset,
                               min(int(r_.rect[0]) for r_ in _grp))
                    _sx1 = max(int(_cr[2]) - _inset,
                               max(int(r_.rect[0] + r_.rect[2]) for r_ in _grp))
                else:
                    _sx0 = min(int(r_.rect[0]) for r_ in _grp)
                    _sx1 = max(int(r_.rect[0] + r_.rect[2]) for r_ in _grp)
                for r_ in _grp:
                    r_.sys_span = (max(0, _sx0), _sx1)
        except Exception:
            pass

        before = len(regions)
        regions = self._split_mixed_column_regions(regions)
        regions = self._merge_overlapping_regions(regions, iou_thresh=0.35, contain_thresh=0.65)
        if self.debug:
            print(f"    [*] RT-DETR: {n0} خام → {before} OCR → {len(regions)} نهایی")
        try:
            regions = self._rescue_orphan_lines(image, regions,
                                                page_cache=page_cache)
        except Exception:
            pass
        return regions, page_boxes

    @staticmethod
    def _dedup_duplicate_text_regions(
            regions: List["TextRegion"]) -> List["TextRegion"]:
        if not regions or len(regions) < 2:
            return regions

        def _norm(t) -> str:
            try:
                return re.sub(r"[\W_]+", "", str(t or "").lower())
            except Exception:
                return str(t or "").lower()

        def _sim(a: str, b: str) -> float:
            if a == b:
                return 1.0
            try:
                import difflib as _dl
                return _dl.SequenceMatcher(None, a, b).ratio()
            except Exception:
                return 0.0

        def _xyxy(r):
            try:
                x, y, w, h = [float(v) for v in r.rect]
                return (x, y, x + w, y + h)
            except Exception:
                return (0.0, 0.0, 0.0, 0.0)

        def _inter(a, b):
            ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
            iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
            return max(0.0, ix) * max(0.0, iy)

        def _area(a):
            return max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])

        infos = []
        for r in regions:
            try:
                n = _norm(getattr(r, "source_text", ""))
            except Exception:
                n = ""
            if not n:
                continue
            try:
                npol = len(getattr(r, "ocr_polys", None) or [])
            except Exception:
                npol = 0
            infos.append((r, n, _xyxy(r), _area(_xyxy(r)), npol))
        if len(infos) < 2:
            return regions

        drop_ids: set = set()
        n_eq = n_sub = 0
        for i in range(len(infos)):
            ra, na, ba, aa, pa = infos[i]
            if id(ra) in drop_ids:
                continue
            for j in range(i + 1, len(infos)):
                rb, nb, bb, ab, pb = infos[j]
                if id(rb) in drop_ids:
                    continue
                if getattr(rb, "kind", "") != getattr(ra, "kind", ""):
                    continue
                try:
                    if getattr(ra, "sys_split", False) \
                            and getattr(rb, "sys_split", False) \
                            and getattr(ra, "cover_rect", None) is not None \
                            and getattr(ra, "cover_rect", None) \
                            == getattr(rb, "cover_rect", None):
                        continue
                except Exception:
                    pass
                inter = _inter(ba, bb)
                if inter <= 0.0:
                    continue
                amin = min(aa, ab) or 1.0
                ov_min = inter / amin
                cont_ba = inter / (ab or 1.0)
                cont_ab = inter / (aa or 1.0)
                _kill = None
                _same_txt = (na == nb) or (
                    len(na) >= 6 and len(nb) >= 6
                    and sorted(na) == sorted(nb))
                if not _same_txt and len(na) >= 6 and len(nb) >= 6:
                    _same_txt = _sim(na, nb) >= 0.62
                if _same_txt:
                    if ov_min >= 0.18 or max(cont_ba, cont_ab) >= 0.45:
                        _kill = ra if (pa, aa) <= (pb, ab) else rb
                        n_eq += 1
                elif nb in na and cont_ba >= 0.60:
                    _kill = rb
                    n_sub += 1
                elif na in nb and cont_ab >= 0.60:
                    _kill = ra
                    n_sub += 1
                if _kill is not None:
                    drop_ids.add(id(_kill))
        if not drop_ids:
            return regions
        out = [r for r in regions if id(r) not in drop_ids]
        try:
            print(f"    [*] {len(drop_ids)} ناحیهٔ هممتنِ همپوشان حذف شد "
                  f"(ضدِ رندرِ دوباره — {n_eq} یکسان / {n_sub} بخشی)",
                  flush=True)
        except Exception:
            pass
        return out

    def _rescue_orphan_lines(self, image: np.ndarray,
                             regions: List["TextRegion"],
                             page_cache: Optional[dict] = None) -> List["TextRegion"]:
        if os.environ.get("MANGA_ORPHAN_RESCUE", "1") == "0":
            return regions
        try:
            h_img, w_img = image.shape[:2]
        except Exception:
            return regions
        if self.ocr is None:
            return regions
        parents = [r for r in regions
                   if (getattr(r, "source_text", "") or "").strip()
                   and getattr(r, "kind", "") == "dialogue"]
        if not parents:
            return regions
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        except Exception:
            return regions
        covered = []
        for r in regions:
            try:
                rx, ry, rw_, rh_ = [int(v) for v in r.rect]
                covered.append((rx - 12, ry - 12, rx + rw_ + 12, ry + rh_ + 12))
            except Exception:
                continue
        _next_id = 900000
        try:
            _next_id = 900000 + max(
                (int(getattr(r, "id", 0) or 0) for r in regions), default=0)
        except Exception:
            pass
        rescued: List[TextRegion] = []
        _seen_bands: List[Tuple[int, int, int, int]] = []
        _orphan_budget = max(12, 2 * len(parents))
        for r in parents:
            try:
                x, y, rw_, rh_ = [int(v) for v in r.rect]
            except Exception:
                continue
            _lhs = []
            for _p in (getattr(r, "ocr_polys", None) or []):
                try:
                    _pp = np.asarray(_p, dtype=np.float32).reshape(-1, 2)
                    _lhs.append(float(_pp[:, 1].max() - _pp[:, 1].min()))
                except Exception:
                    continue
            lh = float(np.median(_lhs)) if _lhs else float(rh_)
            lh = float(np.clip(lh, 12.0, 140.0))
            gap = max(4, int(round(lh * 0.12)))
            reach = int(round(lh * 2.2))
            for _b0, _b1 in ((y + rh_ + gap, y + rh_ + gap + reach),
                             (y - gap - reach, y - gap)):
                _b0 = max(0, int(_b0))
                _b1 = min(h_img, int(_b1))
                if _b1 - _b0 < int(lh * 0.6):
                    continue
                _x0 = max(0, x - int(rw_ * 0.25))
                _x1 = min(w_img, x + rw_ + int(rw_ * 0.25))
                if _x1 - _x0 < 40:
                    continue
                band = gray[_b0:_b1, _x0:_x1]
                if band.size == 0:
                    continue
                med = float(np.median(band))
                if med >= 128.0:
                    ink = (band < med - 60.0)
                else:
                    ink = (band > med + 60.0)
                _dens = float(ink.mean())
                if _dens < 0.004 or _dens > 0.55:
                    continue
                _rows = ink.sum(axis=1).astype(np.float32)
                _row_thr = max(12.0, 0.08 * (_x1 - _x0))
                _runs: List[Tuple[int, int]] = []
                _in_run = False
                _rs = 0
                for _i in range(len(_rows)):
                    if _rows[_i] >= _row_thr:
                        if not _in_run:
                            _rs = _i
                            _in_run = True
                    else:
                        if _in_run:
                            _runs.append((_rs, _i))
                            _in_run = False
                if _in_run:
                    _runs.append((_rs, len(_rows)))
                for (_r0, _r1) in _runs:
                    _rhh = _r1 - _r0
                    if _rhh < 8 or _rhh > max(30, int(lh * 2.5)):
                        continue
                    _soft_thr = _row_thr * 0.30
                    _ext_max = max(4, int(lh * 0.5))
                    _e0 = 0
                    while (_r0 - _e0 - 1 >= 0 and _e0 < _ext_max
                           and _rows[_r0 - _e0 - 1] >= _soft_thr):
                        _e0 += 1
                    _e1 = 0
                    while (_r1 + _e1 < len(_rows) and _e1 < _ext_max
                           and _rows[_r1 + _e1] >= _soft_thr):
                        _e1 += 1
                    _r0 -= _e0
                    _r1 += _e1
                    _rhh = _r1 - _r0
                    if _rhh > max(30, int(lh * 2.8)):
                        continue
                    _sub = ink[_r0:_r1, :]
                    if float(_sub.mean()) > 0.55:
                        continue
                    try:
                        _nlab, _labs, _stat, _cent = \
                            cv2.connectedComponentsWithStats(
                                _sub.astype(np.uint8), connectivity=8)
                        _letters = 0
                        _bots: List[int] = []
                        for _li in range(1, _nlab):
                            _sx, _sy, _sw, _sh, _sa = \
                                _stat[_li]
                            if _sa < 8:
                                continue
                            if not (3 <= _sh <= max(12.0, lh * 1.6)):
                                continue
                            if _sw <= max(14.0, lh * 1.2):
                                _letters += 1
                                _bots.append(int(_sy + _sh))
                            elif _sw <= max(30.0, lh * 3.5):
                                _letters += 2
                                _bots.append(int(_sy + _sh))
                        if _letters < 5:
                            continue
                        if len(_bots) >= 5:
                            _bstd = float(np.std(_bots))
                            if _bstd > max(6.0, 0.45 * lh):
                                continue
                    except Exception:
                        pass
                    try:
                        _ys, _xs = np.nonzero(_sub)
                    except Exception:
                        continue
                    _ix0, _ix1 = int(_xs.min()), int(_xs.max())
                    if (_ix1 - _ix0) < 30:
                        continue
                    gx0 = max(0, _x0 + _ix0)
                    gy0 = max(0, _b0 + _r0 - 3)
                    gx1 = min(w_img, _x0 + _ix1 + 1)
                    gy1 = min(h_img, _b0 + _r1 + 3)
                    if gx1 - gx0 < 30 or gy1 - gy0 < 8:
                        continue
                    _clipped_edge = (_r0 <= 0 or _r1 >= len(_rows))
                    if not _clipped_edge \
                            and (gy1 - gy0) < max(12, int(round(lh * 0.45))):
                        continue
                    if (gy1 - gy0) < 12:
                        continue
                    _ga = float(max(1, (gx1 - gx0) * (gy1 - gy0)))
                    if any(not (gx1 < c[0] or gx0 > c[2]
                                or gy1 < c[1] or gy0 > c[3])
                           and (min(gx1, c[2]) - max(gx0, c[0]))
                               * (min(gy1, c[3]) - max(gy0, c[1]))
                               >= 0.70 * _ga
                           for c in covered):
                        continue
                    if any(not (gx1 < s[0] or gx0 > s[2]
                                or gy1 < s[1] or gy0 > s[3])
                           and (min(gx1, s[2]) - max(gx0, s[0]))
                               * (min(gy1, s[3]) - max(gy0, s[1]))
                               >= 0.70 * _ga
                           for s in _seen_bands):
                        continue
                    _seen_bands.append((gx0, gy0, gx1, gy1))
                    try:
                        _inkys, _inkxs = np.nonzero(
                            ink[_r0:_r1, :])
                        if _inkys.size >= 12:
                            _gx = _inkxs.astype(np.int32) + _x0
                            _gy = _inkys.astype(np.int32) + _b0
                            _inany = np.zeros(
                                _gx.shape, bool)
                            for _rp in regions:
                                for _rpoly in (
                                        getattr(_rp, "ocr_polys", None)
                                        or []):
                                    try:
                                        _pp3 = np.asarray(
                                            _rpoly,
                                            np.float32).reshape(-1, 2)
                                        _bxa = int(_pp3[:, 0].min())
                                        _bya = int(_pp3[:, 1].min())
                                        _bxb = int(
                                            _pp3[:, 0].max()) + 1
                                        _byb = int(
                                            _pp3[:, 1].max()) + 1
                                        _selb = (
                                            (_gx >= _bxa)
                                            & (_gx < _bxb)
                                            & (_gy >= _bya)
                                            & (_gy < _byb))
                                        if not _selb.any():
                                            continue
                                        _bw = max(
                                            1, _bxb - _bxa)
                                        _bh = max(
                                            1, _byb - _bya)
                                        _pm = np.zeros(
                                            (_bh, _bw), np.uint8)
                                        cv2.fillPoly(
                                            _pm,
                                            [np.rint(
                                                _pp3
                                                - [_bxa,
                                                   _bya]).astype(
                                                np.int32)], 255)
                                        _inany[_selb] |= (
                                            _pm[
                                                _gy[_selb]
                                                - _bya,
                                                _gx[_selb]
                                                - _bxa] > 0)
                                    except Exception:
                                        continue
                                if float(
                                        _inany.mean()) >= 0.55:
                                    break
                            if float(_inany.mean()) >= 0.55:
                                continue
                    except Exception:
                        pass
                    if _orphan_budget <= 0:
                        continue
                    try:
                        _oc = self._ocr_crop(
                            image, (max(0, gx0 - 6), max(0, gy0 - 6),
                                    min(w_img, gx1 + 6), min(h_img, gy1 + 6)),
                            page_cache=page_cache)
                        _orphan_budget -= 1
                        _txt = (_oc[0] or "").strip()
                        _polys = list(_oc[1] or []) if len(_oc) > 1 else []
                    except Exception:
                        _txt, _polys = "", []
                    _lt = sum(1 for _c in _txt
                              if _c.isascii() and _c.isalpha())
                    if not _txt or _lt < 6 \
                            or _lt * 2 < len(_txt.replace(" ", "")):
                        continue
                    try:
                        _ta = 0.0
                        _ca = 0.0
                        for _p2 in _polys:
                            try:
                                _pp2 = np.asarray(
                                    _p2, np.float32).reshape(-1, 2)
                                _pbx0 = float(_pp2[:, 0].min())
                                _pby0 = float(_pp2[:, 1].min())
                                _pbx1 = float(_pp2[:, 0].max())
                                _pby1 = float(_pp2[:, 1].max())
                                _pba = max(1.0, (_pbx1 - _pbx0)
                                           * (_pby1 - _pby0))
                                _pin = 0.0
                                for _c in covered:
                                    _ix = max(
                                        0.0, min(_pbx1, _c[2])
                                        - max(_pbx0, _c[0]))
                                    _iy = max(
                                        0.0, min(_pby1, _c[3])
                                        - max(_pby0, _c[1]))
                                    _pin = max(_pin, (_ix * _iy)
                                               / _pba)
                                _ta += _pba
                                _ca += _pba * min(1.0, _pin)
                            except Exception:
                                continue
                        if _ta > 0.0 and \
                                _ca / _ta >= 0.55:
                            if self.debug:
                                print(f"    [🔍یتیم] یتیمِ بازخوانیِ "
                                      f"متنِ پوشیدهشده رد شد: "
                                      f"{_txt[:44]!r}", flush=True)
                            continue
                    except Exception:
                        pass
                    _boxes = []
                    _polys_ok: List[np.ndarray] = []
                    for _p in (_polys or []):
                        try:
                            _pp = np.asarray(_p, dtype=np.float32).reshape(-1, 2)
                            if (_pp[:, 1].max() - _pp[:, 1].min()) >= 3.0 \
                                    or (_pp[:, 0].max() - _pp[:, 0].min()) >= 3.0:
                                _polys_ok.append(_p)
                                _boxes.append(_pp.astype(np.int32))
                        except Exception:
                            continue
                    _polys = _polys_ok
                    try:
                        if _polys:
                            _pb_all = np.concatenate([
                                np.asarray(_p, dtype=np.float32).reshape(-1, 2)
                                for _p in _polys])
                            _px0 = int(_pb_all[:, 0].min()) - 2
                            _py0 = int(_pb_all[:, 1].min()) - 2
                            _px1 = int(_pb_all[:, 0].max()) + 3
                            _py1 = int(_pb_all[:, 1].max()) + 3
                            if (_px1 - _px0) >= 12 and (_py1 - _py0) >= 8 \
                                    and (_px1 - _px0) * (_py1 - _py0) \
                                    < (gx1 - gx0) * (gy1 - gy0) * 0.9:
                                gx0, gy0 = max(0, _px0), max(0, _py0)
                                gx1 = min(w_img, _px1)
                                gy1 = min(h_img, _py1)
                    except Exception:
                        pass
                    nr = TextRegion(
                        id=_next_id, boxes=_boxes or [np.array(
                            [[gx0, gy0], [gx1, gy0], [gx1, gy1], [gx0, gy1]],
                            dtype=np.int32)],
                        source_text=_txt,
                        rect=(gx0, gy0, gx1 - gx0, gy1 - gy0),
                        kind="dialogue",
                        bubble_style=str(getattr(r, "bubble_style", "normal")
                                         or "normal"),
                        det_class=str(getattr(r, "det_class", "") or ""),
                        ocr_polys=_polys)
                    _next_id += 1
                    rescued.append(nr)
                    covered.append((gx0 - 12, gy0 - 12, gx1 + 12, gy1 + 12))
                    if self.debug:
                        print(f"    [+] نجاتِ خطِ یتیم زیر/بالای "
                              f"({x},{y},{x + rw_},{y + rh_}): {_txt[:56]!r}")
        if rescued:
            regions = list(regions) + rescued
            print(f"    [+] {len(rescued)} خطِ یتیم (همسایهٔ نواحیِ متن) "
                  f"نجات یافت → ترجمه و پاکسازی میشوند")
        return regions

    def _verify_angle_signs(self, image: np.ndarray,
                            regions: List["TextRegion"]) -> None:
        for r in regions:
            ang = float(getattr(r, "angle", 0.0) or 0.0)
            if abs(ang) > 45.0:
                r.angle = 0.0
                continue
            if abs(ang) < 6.0:
                _is_vert = self._polys_vertical(getattr(r, "ocr_polys", None))
                try:
                    _px = getattr(r, "ocr_polys", None) or []
                    _vx1 = _vy1 = None
                    if _px and not _is_vert:
                        try:
                            _vp = np.concatenate(
                                [np.asarray(p).reshape(-1, 2) for p in _px])
                            _vx1, _vy1 = float(_vp[:, 0].min()), float(_vp[:, 1].min())
                            _vx2, _vy2 = float(_vp[:, 0].max()), float(_vp[:, 1].max())
                        except Exception:
                            _vx1 = _vy1 = None
                    if _vx1 is None:
                        _vx, _vy, _vw, _vh = [int(v) for v in r.rect]
                        _vx1, _vy1 = float(_vx), float(_vy)
                        _vx2, _vy2 = float(_vx + _vw), float(_vy + _vh)
                    _uy1 = max(0, int(_vy1))
                    _ux1 = max(0, int(_vx1))
                    _ux2 = min(int(image.shape[1]), int(_vx2) + 1)
                    _uy2 = min(int(image.shape[0]), int(_vy2) + 1)
                    if _ux2 - _ux1 >= 40 and _uy2 - _uy1 >= 14:
                        _umk = MangaTranslator._ocr_poly_mask(
                            (_uy2 - _uy1, _ux2 - _ux1), _px,
                            _ux1, _uy1)
                        _ai = MangaTranslator._ink_slant_angle(
                            image[_uy1:_uy2, _ux1:_ux2], _umk)
                        if abs(_ai) >= (7.0 if _is_vert else 6.0):
                            _keep_poly = False
                            try:
                                if not _is_vert and _px:
                                    _pangs = []
                                    for _q in _px:
                                        try:
                                            _va = float(
                                                MangaTranslator._poly_long_side_angle(_q))
                                        except Exception:
                                            _va = 0.0
                                        if abs(_va) >= 3.0:
                                            _pangs.append(_va)
                                    if (_pangs
                                            and len(_pangs) >= max(1, len(_px) - 1)
                                            and float(np.median(_pangs)) * _ai < 0.0):
                                        _sup_ai = MangaTranslator._ink_slant_support(
                                            image[_uy1:_uy2, _ux1:_ux2], _ai, _umk)
                                        if _sup_ai is None or _sup_ai < 1.10:
                                            _keep_poly = True
                            except Exception:
                                _keep_poly = False
                            if _keep_poly:
                                print(f"    [!] وتوی بازیابیِ کجی [{r.id}]: "
                                      f"{ang:+.1f}° ماند — پالیهایِ OCR زاویهٔ "
                                      f"{_ai:+.1f}° را تایید نمیکنند")
                            else:
                                print(f"    [!] بازیابی کجی [{r.id}]: {ang:+.1f}° → "
                                      f"{_ai:+.1f}° (جوهر؛ موتور از دست داده بود)")
                                r.angle = _ai
                except Exception:
                    pass
                continue
            try:
                x1 = y1 = None
                polys = list(getattr(r, "ocr_polys", None) or [])
                if polys:
                    try:
                        _pa = np.concatenate(
                            [np.asarray(p).reshape(-1, 2) for p in polys])
                        x1, y1 = float(_pa[:, 0].min()), float(_pa[:, 1].min())
                        x2, y2 = float(_pa[:, 0].max()), float(_pa[:, 1].max())
                    except Exception:
                        x1 = y1 = None
                if x1 is None:
                    x, y, w_, h_ = [int(v) for v in r.rect]
                    x1, y1 = max(0, x), max(0, y)
                    x2 = min(int(image.shape[1]), x + max(8, w_))
                    y2 = min(int(image.shape[0]), y + max(8, h_))
                x1, y1 = max(0, int(x1)), max(0, int(y1))
                x2 = min(int(image.shape[1]), int(x2) + 1)
                y2 = min(int(image.shape[0]), int(y2) + 1)
                if x2 - x1 < 40 or y2 - y1 < 14:
                    continue
                _vmk = MangaTranslator._ocr_poly_mask(
                    (y2 - y1, x2 - x1), polys, x1, y1)
                _a_ink, _a_ok = MangaTranslator._ink_slant_measure(
                    image[y1:y2, x1:x2], _vmk)
                if os.environ.get("MANGA_DBG_VERIFY"):
                    print(f"    [dbg-verify] {r.id} ang={ang:+.1f} "
                          f"bbox=({x1},{y1},{x2},{y2}) ok={_a_ok} a={_a_ink:+.1f}")
                if not _a_ok:
                    continue
                if abs(_a_ink) >= 6.0 and (_a_ink > 0.0) != (ang > 0.0):
                    if abs(abs(_a_ink) - abs(ang)) > 15.0:
                        print(f"    [!] وتوی کجیِ ناسازگار [{r.id}]: "
                              f"{ang:+.1f}° ← جوهر {_a_ink:+.1f}° "
                              "(پرشِ فاحش) → 0.0°")
                        r.angle = 0.0
                        r.angle_flat_veto = True
                    else:
                        print(f"    [!] اصلاح علامتِ چرخش [{r.id}]: {ang:+.1f}° → "
                              f"{_a_ink:+.1f}° (راستی‌آزمایی جوهر)")
                        r.angle = _a_ink
                elif abs(_a_ink) < 6.0:
                    _sup = MangaTranslator._ink_slant_support(
                        image[y1:y2, x1:x2], ang, _vmk)
                    if _sup is not None and _sup >= 1.10:
                        if os.environ.get("MANGA_DBG_VERIFY"):
                            print(f"    [dbg-verify] {r.id} ang={ang:+.1f}° "
                                  f"تأییدِ جوهر (پشتیبانی={_sup:.2f}) — "
                                  f"وتو نشد")
                        continue
                    print(f"    [!] حذف کجیِ کاذب [{r.id}]: {ang:+.1f}° → 0.0° "
                          f"(جوهرِ واقعیِ خط مسطح است)")
                    r.angle = 0.0
                    r.angle_flat_veto = True
            except Exception:
                continue

    def _discover_sfx_regions(self, image: np.ndarray,
                              regions: List["TextRegion"]) -> List["TextRegion"]:
        try:
            out = self._discover_free_text_regions(image, regions,
                                                   relaxed=True)
        except Exception:
            return []
        return self._merge_sfx_fragments(image, out)

    def _merge_sfx_fragments(self, image: np.ndarray,
                             regions: List["TextRegion"]) -> List["TextRegion"]:
        if not regions:
            return regions
        try:
            h, w = image.shape[:2]
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            med = cv2.medianBlur(gray, 31)
            ink = (np.abs(gray.astype(np.int16) - med.astype(np.int16))
                   > 52).astype(np.uint8) * 255
        except Exception:
            ink = None
        try:
            rs = sorted(regions, key=lambda r: (r.rect[1], r.rect[0]))
            merged: List["TextRegion"] = []
            for r in rs:
                placed = False
                try:
                    x, y, w_, h_ = [int(v) for v in r.rect]
                except Exception:
                    merged.append(r)
                    continue
                for m in merged:
                    try:
                        mx, my, mw, mh = [int(v) for v in m.rect]
                    except Exception:
                        continue
                    if (x - 70 < mx + mw and mx - 70 < x + w_
                            and y - 70 < my + mh and my - 70 < y + h_):
                        nx0, ny0 = min(mx, x), min(my, y)
                        nx1, ny1 = max(mx + mw, x + w_), max(my + mh, y + h_)
                        m.rect = (nx0, ny0, nx1 - nx0, ny1 - ny0)
                        try:
                            m.boxes = list(m.boxes or []) + list(r.boxes or [])
                            m.ocr_polys = (list(m.ocr_polys or [])
                                           + list(r.ocr_polys or []))
                        except Exception:
                            pass
                        try:
                            _t1 = (m.source_text or "").strip()
                            _t2 = (r.source_text or "").strip()
                            if _t2 and _t2 not in _t1:
                                m.source_text = (_t1 + " " + _t2).strip()
                        except Exception:
                            pass
                        placed = True
                        break
                if not placed:
                    merged.append(r)
            if ink is not None:
                for m in merged:
                    try:
                        mx, my, mw, mh = [int(v) for v in m.rect]
                        for _ in range(3):
                            ex0, ey0 = max(0, mx - 80), max(0, my - 80)
                            ex1 = min(w, mx + mw + 80)
                            ey1 = min(h, my + mh + 80)
                            sub = ink[ey0:ey1, ex0:ex1]
                            ys, xs = np.nonzero(sub)
                            if len(xs) < 20:
                                break
                            nx0, ny0 = ex0 + int(xs.min()), ey0 + int(ys.min())
                            nx1 = ex0 + int(xs.max()) + 1
                            ny1 = ey0 + int(ys.max()) + 1
                            if (nx0 == mx and ny0 == my
                                    and nx1 == mx + mw and ny1 == my + mh):
                                break
                            mx, my, mw, mh = nx0, ny0, nx1 - nx0, ny1 - ny0
                        m.rect = (mx, my, mw, mh)
                    except Exception:
                        pass
            return merged
        except Exception:
            return regions

    def _dbg_collect_det_quads(self, image: np.ndarray,
                               regions: List[TextRegion],
                               bubbles: list) -> list:

        _fn = getattr(self.ocr, "det_only", None)
        if not callable(_fn):
            return []
        _bubbles = list(bubbles or [])
        if not _bubbles:
            return []
        try:
            _h, _w = image.shape[:2]
        except Exception:
            return []
        _quads: List[np.ndarray] = []
        _t = time.time()

        def _dbg_one_bubble(_b) -> List[np.ndarray]:
            _out: List[np.ndarray] = []
            try:
                _bx1, _by1, _bx2, _by2 = [int(v) for v in _b[:4]]
                _pad = 8
                _x1 = max(0, _bx1 - _pad)
                _y1 = max(0, _by1 - _pad)
                _x2 = min(_w, _bx2 + _pad)
                _y2 = min(_h, _by2 + _pad)
                if _x2 - _x1 < 8 or _y2 - _y1 < 8:
                    return _out
                _crop = image[_y1:_y2, _x1:_x2]
                if _crop is None or _crop.size == 0:
                    return _out
                _m = max(_crop.shape[:2])
                if _m < 200:
                    _sc = 2.4
                elif _m < 360:
                    _sc = 1.8
                elif _m < 600:
                    _sc = 1.35
                else:
                    _sc = 1.0
                _passes = [(_crop, 1.0)]
                if _sc > 1.01:
                    _passes.append(
                        (cv2.resize(_crop, None, fx=_sc, fy=_sc,
                                    interpolation=cv2.INTER_CUBIC), _sc))
                for _cimg, _cs in _passes:
                    for _q in (_fn(_cimg) or []):
                        try:
                            _qf = np.asarray(
                                _q, dtype=np.float32).reshape(-1, 2).copy()
                            if _cs > 1.01:
                                _qf = _qf / _cs
                            _qf[:, 0] += _x1
                            _qf[:, 1] += _y1
                        except Exception:
                            continue
                        try:
                            _qx1 = float(np.min(_qf[:, 0]))
                            _qy1 = float(np.min(_qf[:, 1]))
                            _qx2 = float(np.max(_qf[:, 0]))
                            _qy2 = float(np.max(_qf[:, 1]))
                            _qa = max(1e-6, (_qx2 - _qx1) * (_qy2 - _qy1))
                            _ix = max(0.0, min(_qx2, float(_bx2))
                                      - max(_qx1, float(_bx1)))
                            _iy = max(0.0, min(_qy2, float(_by2))
                                      - max(_qy1, float(_by1)))
                            if (_ix * _iy) / _qa < 0.5:
                                continue
                        except Exception:
                            continue
                        _out.append(_qf)
            except Exception:
                pass
            return _out

        try:
            _nw = max(1, min(4, int(getattr(self, "max_workers", 2) or 2),
                             len(_bubbles)))
            if _nw > 1:
                with ThreadPoolExecutor(max_workers=_nw) as _ex:
                    _per = list(_ex.map(_dbg_one_bubble, _bubbles))
                for _lst in _per:
                    _quads.extend(_lst)
            else:
                for _b in _bubbles:
                    _quads.extend(_dbg_one_bubble(_b))
        except Exception:
            for _b in _bubbles:
                _quads.extend(_dbg_one_bubble(_b))
        try:
            _keep: List[np.ndarray] = []
            _bb = []
            for _q in _quads:
                _bx1_ = float(np.min(_q[:, 0])); _by1_ = float(np.min(_q[:, 1]))
                _bx2_ = float(np.max(_q[:, 0])); _by2_ = float(np.max(_q[:, 1]))
                _dup = False
                for _kb in _bb:
                    _ix = max(0.0, min(_bx2_, _kb[2]) - max(_bx1_, _kb[0]))
                    _iy = max(0.0, min(_by2_, _kb[3]) - max(_by1_, _kb[1]))
                    _inter = _ix * _iy
                    if _inter <= 0:
                        continue
                    _aq = max(1e-6, (_bx2_ - _bx1_) * (_by2_ - _by1_))
                    _bq = max(1e-6, (_kb[2] - _kb[0]) * (_kb[3] - _kb[1]))
                    _iov = _inter / min(_aq, _bq)
                    if _iov >= 0.6:
                        _dup = True
                        break
                if not _dup:
                    _keep.append(_q)
                    _bb.append((_bx1_, _by1_, _bx2_, _by2_))
            _quads = _keep
        except Exception:
            pass
        try:
            _cov = []
            for _r in (regions or []):
                try:
                    _rx, _ry, _rw, _rh = [int(v) for v in _r.rect]
                    _cov.append((_rx, _ry,
                                    _rx + _rw, _ry + _rh))
                except Exception:
                    pass
                for _p in (getattr(_r, "ocr_polys", None) or []):
                    try:
                        _pp = np.asarray(_p, dtype=np.float32).reshape(-1, 2)
                        _cov.append((float(np.min(_pp[:, 0])),
                                        float(np.min(_pp[:, 1])),
                                        float(np.max(_pp[:, 0])),
                                        float(np.max(_pp[:, 1]))))
                    except Exception:
                        continue
            _miss = []
            for _q in _quads:
                try:
                    _qx1_ = float(np.min(_q[:, 0])); _qy1_ = float(np.min(_q[:, 1]))
                    _qx2_ = float(np.max(_q[:, 0])); _qy2_ = float(np.max(_q[:, 1]))
                except Exception:
                    continue
                _hit = False
                for _cb in _cov:
                    _ix = max(0.0, min(_qx2_, _cb[2]) - max(_qx1_, _cb[0]))
                    _iy = max(0.0, min(_qy2_, _cb[3]) - max(_qy1_, _cb[1]))
                    if _ix * _iy <= 0:
                        continue
                    _aq = max(1e-6, (_qx2_ - _qx1_) * (_qy2_ - _qy1_))
                    if (_ix * _iy) / _aq >= 0.35:
                        _hit = True
                        break
                if not _hit:
                    _miss.append((int(_qx1_), int(_qy1_),
                                     int(_qx2_ - _qx1_), int(_qy2_ - _qy1_)))
            if _quads or _miss:
                _ms = ""
                if _miss:
                    _ms = (" | " + str(len(_miss)) + " خط: det دید ولی "
                              "rec/فیلتر نگرفت → " +
                              ", ".join(f"({a},{b} {c}x{d})"
                                        for a, b, c, d in _miss[:8]))
                print(f"    [🔍det] دیباگِ det (آبی): {len(_quads)} جعبهٔ خام"
                      f" در {time.time() - _t:.1f}s{_ms}")
        except Exception:
            pass
        return _quads

    def _rec_rescue_missed_quads(self, image: np.ndarray, rect,
                                 block_rects, cur_polys):
        out: List[Tuple[str, np.ndarray, float]] = []
        try:
            _fn_det = getattr(self.ocr, "det_only", None)
            _fn_rec = getattr(self.ocr, "rec_only", None)
            if not callable(_fn_det) or not callable(_fn_rec):
                return out
            h_img, w_img = image.shape[:2]
            x1, y1, x2, y2 = [int(v) for v in rect[:4]]
            _pad = 8
            _cx1 = max(0, x1 - _pad)
            _cy1 = max(0, y1 - _pad)
            _cx2 = min(w_img, x2 + _pad)
            _cy2 = min(h_img, y2 + _pad)
            if _cx2 - _cx1 < 12 or _cy2 - _cy1 < 12:
                return out
            crop = image[_cy1:_cy2, _cx1:_cx2]
            quads = _fn_det(crop) or []
            if not quads:
                return out
            _own = max(1.0, float((x2 - x1) * (y2 - y1)))
            _cov = []
            for _p in (cur_polys or []):
                try:
                    _pp = np.asarray(_p, dtype=np.float32).reshape(-1, 2)
                    _cov.append((float(_pp[:, 0].min()), float(_pp[:, 1].min()),
                                 float(_pp[:, 0].max()), float(_pp[:, 1].max())))
                except Exception:
                    continue
            for _q in quads:
                try:
                    _qf = np.asarray(_q, dtype=np.float32).reshape(-1, 2).copy()
                    _qf[:, 0] += _cx1
                    _qf[:, 1] += _cy1
                    _qx1 = float(np.min(_qf[:, 0])); _qy1 = float(np.min(_qf[:, 1]))
                    _qx2 = float(np.max(_qf[:, 0])); _qy2 = float(np.max(_qf[:, 1]))
                    _qa = max(1e-6, (_qx2 - _qx1) * (_qy2 - _qy1))
                    _ix = max(0.0, min(_qx2, float(x2)) - max(_qx1, float(x1)))
                    _iy = max(0.0, min(_qy2, float(y2)) - max(_qy1, float(y1)))
                    if (_ix * _iy) / _qa < 0.5:
                        continue
                    _foreign = False
                    for _r in (block_rects or []):
                        try:
                            _ox1, _oy1, _ox2, _oy2 = [float(v) for v in _r[:4]]
                            _oa = max(1.0, (_ox2 - _ox1) * (_oy2 - _oy1))
                            if _oa >= _own:
                                continue
                            _jx = max(0.0, min(_qx2, _ox2) - max(_qx1, _ox1))
                            _jy = max(0.0, min(_qy2, _oy2) - max(_qy1, _oy1))
                            if (_jx * _jy) / _qa >= 0.6:
                                _foreign = True
                                break
                        except Exception:
                            continue
                    if _foreign:
                        continue
                    _hit = False
                    for _cb in _cov:
                        _hx = max(0.0, min(_qx2, _cb[2]) - max(_qx1, _cb[0]))
                        _hy = max(0.0, min(_qy2, _cb[3]) - max(_qy1, _cb[1]))
                        if (_hx * _hy) / _qa >= 0.4:
                            _hit = True
                            break
                    if _hit:
                        continue
                    _pts = _qf.astype(np.float32)
                    _rect = cv2.minAreaRect(_pts)
                    (_rc, _rs, _ra) = _rect
                    if _ra < -45.0:
                        _ra += 90.0
                    elif _ra > 45.0:
                        _ra -= 90.0
                    _rw = max(8.0, _rs[0] if abs(_ra) < 45.0 else _rs[1])
                    _rh = max(8.0, _rs[1] if abs(_ra) < 45.0 else _rs[0])
                except Exception:
                    continue
                try:
                    _poly4 = MangaTranslator._order_quad_pts(_qf)
                    if _poly4 is None:
                        continue
                    _M = cv2.getPerspectiveTransform(
                        _poly4,
                        np.array([[0, 0], [_rw - 1, 0],
                                  [_rw - 1, _rh - 1], [0, _rh - 1]],
                                 dtype=np.float32))
                    strip = cv2.warpPerspective(
                        image, _M, (int(_rw), int(_rh)),
                        flags=cv2.INTER_CUBIC, borderValue=(255, 255, 255))
                    best = None
                    _tries = [strip]
                    if _rh < 56:
                        _tries.append(cv2.resize(
                            strip, None, fx=2.0, fy=2.0,
                            interpolation=cv2.INTER_CUBIC))
                    for _st in _tries:
                        _rr = _fn_rec(_st)
                        if _rr is None:
                            continue
                        _t, _s = _rr
                        if not _t or _s < 0.5:
                            continue
                        if best is None or _s > best[1]:
                            best = (_t, _s)
                        if _s >= 0.8:
                            break
                    if best is None:
                        continue
                    _t, _s = best
                    if self._is_non_english_script(_t):
                        continue
                    if _latin_lang(self) and _latin_junk_line(_t, True):
                        continue
                    if not _t.strip():
                        continue
                    out.append((_t.strip(), _poly4.astype(np.int32), float(_s)))
                except Exception:
                    continue
            return out
        except Exception:
            return out

    @staticmethod
    def _order_quad_pts(pts):
        try:
            p = np.asarray(pts, dtype=np.float32).reshape(-1, 2)
            if p.shape[0] != 4:
                return None
            _s = p.sum(axis=1)
            tl = p[int(np.argmin(_s))]
            br = p[int(np.argmax(_s))]
            _d = p[:, 1] - p[:, 0]
            tr = p[int(np.argmin(_d))]
            bl = p[int(np.argmax(_d))]
            return np.array([tl, tr, br, bl], dtype=np.float32)
        except Exception:
            return None

    def extract_regions_phase(self, image: np.ndarray
            ) -> Tuple[List[TextRegion], Optional[np.ndarray], dict]:
        _page_cache: dict = {}
        h, w = image.shape[:2]
        _t_ext = time.time()
        if _android_gate("MANGA_PHASE_PRINTS"):
            print("[*] استخراج متن…", flush=True)
        unique_regions: List[TextRegion] = []
        page_boxes: list = []

        _raise_if_stop()
        if self.det is not None:
            unique_regions, page_boxes = self._extract_regions_from_bubbles(
                image, page_cache=_page_cache)
        else:
            print("    [!] detector-v4-s در دسترس نیست → ناحیهٔ متنی پیدا نشد")
        _raise_if_stop()

        _raise_if_stop()
        try:
            unique_regions = MangaTranslator._add_watermark_regions(
                image, unique_regions)
        except Exception:
            pass

        _nt_n = 0
        for _r in unique_regions:
            _t = (_r.source_text or "").strip()
            if _t and not source_has_letters(_t):
                _r.no_touch = True
                _nt_n += 1
            else:
                _r.no_touch = False
        if _nt_n:
            print(f"[*] {_nt_n} ناحیهٔ فقط عدد/نماد → دست‌نخورده "
                  f"(نه ترجمه، نه پاکسازی)")

        if unique_regions and getattr(self, "clean_sfx", False):
            _raise_if_stop()
            try:
                _sfx = self._discover_sfx_regions(image, unique_regions)
                if _sfx:
                    unique_regions.extend(_sfx)
            except Exception:
                pass
        _raise_if_stop()
        if unique_regions:
            self._verify_angle_signs(image, unique_regions)

        if self.reading_order == "rtl":
            unique_regions.sort(key=lambda r: (r.rect[1] // 80, -(r.rect[0] + r.rect[2])))
        else:
            unique_regions.sort(key=lambda r: (r.rect[1] // 80, r.rect[0]))
        for idx, r in enumerate(unique_regions):
            r.id = idx

        dbg = None
        det_quads: list = []
        if self.debug:
            try:
                det_quads = self._dbg_collect_det_quads(
                    image, unique_regions, page_boxes) or []
            except Exception:
                det_quads = []
        if self.debug and unique_regions:
            dbg = self._draw_debug_regions(image, unique_regions, det_quads)
            try:
                _vh, _vw = image.shape[:2]
                _ob = getattr(self, "_ocr_backend_name", "") or "?"
                print(f"    [🔍] دیباگِ استخراج — {len(unique_regions)} ناحیه | "
                      f"تصویر {_vw}×{_vh} | ترتیب: {self.reading_order} | OCR: {_ob}")
                for r in unique_regions:
                    try:
                        x, y, rw, rh = [int(v) for v in r.rect]
                        polys = getattr(r, "ocr_polys", None) or []
                        _lys = []
                        for _p in polys:
                            try:
                                _pa = np.asarray(_p, dtype=np.float32).reshape(-1, 2)
                                _lys.append((float(_pa[:, 1].min()),
                                             float(_pa[:, 1].max())))
                            except Exception:
                                pass
                        _lys.sort()
                        _hs = [int(_b - _a) for _a, _b in _lys]
                        _gs = [int(_lys[_i + 1][0] - _lys[_i][1])
                               for _i in range(len(_lys) - 1)]
                        _txt = (r.source_text or "").replace("\n", " ⏎ ")
                        print(f"      #{r.id:02d} {r.kind}/{r.bubble_style} | "
                              f"rect=({x},{y},{rw},{rh}) | "
                              f"زاویه={float(getattr(r, 'angle', 0.0) or 0.0):+.1f}° | "
                              f"خط={len(_lys)} بلندی={_hs} فاصله={_gs}")
                        if _txt:
                            print(f"          متن: {_txt[:200]}"
                                  f"{'…' if len(_txt) > 200 else ''}")
                    except Exception:
                        continue
            except Exception:
                pass

        try:
            _ads = self._scan_watermark_banners(image, unique_regions)
            if _ads:
                print(f"[*] {len(_ads)} بنرِ تبلیغ شناسایی شد")
                unique_regions = list(unique_regions) + _ads
        except Exception:
            pass

        _ob2 = getattr(self, "_ocr_backend_name", "") or "?"
        _dt = time.time() - _t_ext
        if unique_regions:
            print(f"[+] متن استخراج شد: {len(unique_regions)} ناحیه | "
                  f"زمانِ استخراج: {_dt:.1f} ثانیه | موتور: {_ob2}")
        else:
            print("[!] هیچ متن/حبابی یافت نشد.")
        page_ctx = {"boxes": page_boxes, "quads": det_quads}
        return unique_regions, dbg, page_ctx

    def _scan_watermark_banners(self, image: np.ndarray,
                                regions: List[TextRegion]) -> List[TextRegion]:
        found: List[TextRegion] = []
        try:
            h, w = image.shape[:2]
        except Exception:
            return found
        if getattr(self, "ocr", None) is None:
            return found
        try:
            _tile = 2200
            _ovl = 120
            _exist = []
            for r in (regions or []):
                try:
                    _exist.append([int(v) for v in r.rect])
                except Exception:
                    continue
            _kb = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 5))
            _kd = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 5))
            _found_rects: list = []
            _cands: list = []
            _cand_n = 0
            _ty0 = 0
            while _ty0 < h:
                _y1 = min(h, _ty0 + _tile)
                tile = image[_ty0:_y1]
                _tnext = _y1 if _y1 >= h else _y1 - _ovl
                g = cv2.cvtColor(tile, cv2.COLOR_BGR2GRAY)
                _med = cv2.medianBlur(g, 21)
                _stk = (np.abs(g.astype(np.int16)
                               - _med.astype(np.int16)) > 42)
                _blob = cv2.morphologyEx((_stk * 255).astype(np.uint8),
                                         cv2.MORPH_CLOSE, _kb)
                _blob = cv2.dilate(_blob, _kd)
                n, lab, st, _ = cv2.connectedComponentsWithStats(_blob, 8)
                for i in range(1, n):
                    bx = int(st[i, cv2.CC_STAT_LEFT])
                    by = int(st[i, cv2.CC_STAT_TOP])
                    bw_ = int(st[i, cv2.CC_STAT_WIDTH])
                    bh_ = int(st[i, cv2.CC_STAT_HEIGHT])
                    if bw_ < 60 or bh_ < 12 or bh_ > 170 or bw_ > 1000:
                        continue
                    if bw_ < 2.2 * bh_:
                        continue
                    _fill = float(st[i, cv2.CC_STAT_AREA]) / float(bw_ * bh_)
                    if _fill < 0.06 or _fill > 0.95:
                        continue
                    if bw_ >= 60 and bh_ >= 12:
                        _sub = _stk[by:by + bh_, bx:bx + bw_]
                        _sr = float(_sub.mean()) if _sub.size else 0.0
                        if _sr < 0.025 or _sr > 0.60:
                            continue
                    else:
                        continue
                    X0, X1 = bx, bx + bw_
                    Y0, Y1 = by + _ty0, by + bh_ + _ty0
                    _skip = False
                    for (rx, ry, rw, rh) in _exist:
                        if not (X1 < rx or X0 > rx + rw
                                or Y1 < ry or Y0 > ry + rh):
                            _skip = True
                            break
                    if _skip:
                        continue
                    _dup = False
                    for (fx0, fy0, fx1, fy1) in _found_rects:
                        ix0, iy0 = max(X0, fx0), max(Y0, fy0)
                        ix1, iy1 = min(X1, fx1), min(Y1, fy1)
                        if ix1 - ix0 > 0.5 * min(X1 - X0, fx1 - fx0) \
                                and iy1 - iy0 > 0.5 * min(Y1 - Y0, fy1 - fy0):
                            _dup = True
                            break
                    if _dup:
                        continue
                    cx0, cy0 = max(0, X0 - 8), max(0, Y0 - 8)
                    cx1, cy1 = min(w, X1 + 8), min(h, Y1 + 8)
                    if cx1 - cx0 < 30 or cy1 - cy0 < 12:
                        continue
                    _edge = 0 if min(int(X0), w - int(X1)) <= 40 else 1
                    _cands.append((
                        int(_ty0),
                        _edge,
                        -float(_sr),
                        -float(_fill),
                        cx0, cy0, cx1, cy1))
                _ty0 = _tnext
            try:
                _max_calls = int(os.environ.get(
                    "MANGA_BANNER_OCR_MAX", "0") or 0)
            except Exception:
                _max_calls = 0
            if _max_calls <= 0:
                _nt = max(1, int((h + _tile - 1) // max(1, _tile - _ovl)))
                _max_calls = min(40, 24 + 6 * max(0, _nt - 2))
            _buckets: dict = {}
            for _c3 in _cands:
                _buckets.setdefault(_c3[0], []).append(_c3)
            for _b in _buckets.values():
                _b.sort(key=lambda t: (t[1], t[2], t[3]))
            _ordered: list = []
            while any(_buckets.values()):
                for _tk in sorted(_buckets):
                    if _buckets[_tk]:
                        _ordered.append(_buckets[_tk].pop(0))
            if self.debug:
                try:
                    _top = ", ".join(
                        f"({c[4]},{c[5]},edge{c[1]},s{-c[2]:.2f})"
                        for c in _ordered[:12])
                    print(f"  [🔍] جارویِ بنر: {len(_cands)} کاندید | "
                          f"بودجه {_max_calls} | ترتیبِ گردشی: {_top}")
                except Exception:
                    pass
            _ocr_calls = 0
            _stop_all = False
            try:
                _empty_max = int(os.environ.get(
                    "MANGA_BANNER_EARLY_STOP", "8") or 0)
            except Exception:
                _empty_max = 8
            _empty_streak = 0
            try:
                _tlimit = float(os.environ.get(
                    "MANGA_BANNER_TLIMIT", "0") or 0)
            except Exception:
                _tlimit = 0.0
            if _tlimit <= 0:
                try:
                    if _on_android():
                        _tlimit = 0.0
                    else:
                        _nt2 = max(1, int((h + _tile - 1)
                                           // max(1, _tile - _ovl)))
                        _tlimit = max(8.0, 3.0 * _nt2)
                except Exception:
                    _tlimit = 8.0
            _t = time.time()
            _wm_pw = self._ocr_pool_workers(len(_ordered))
            _wm_i = 0

            def _wm_scan_one(_c):
                (_s0, _s1, _s2, _s3, cx0, cy0, cx1, cy1) = _c
                out = {"calls": 0, "empty": 0, "nonempty": False,
                       "txt": "", "found": False}
                try:
                    crop = image[cy0:cy1, cx0:cx1]
                    if crop.size == 0:
                        return out
                    _pad_h = max(0, 48 - crop.shape[0])
                    _pad_w = max(0, 160 - crop.shape[1])
                    if _pad_h or _pad_w:
                        crop = cv2.copyMakeBorder(
                            crop, _pad_h // 2, _pad_h - _pad_h // 2,
                            _pad_w // 2, _pad_w - _pad_w // 2,
                            cv2.BORDER_REPLICATE)
                    _txt = ""
                    for _zm in (3, 2):
                        _zm_empty = True
                        _big = cv2.resize(
                            crop, (crop.shape[1] * _zm,
                                   crop.shape[0] * _zm),
                            interpolation=cv2.INTER_CUBIC)
                        for _var in (0, 1):
                            _try = _big
                            if _var == 1:
                                try:
                                    _lab2 = cv2.cvtColor(_big,
                                                         cv2.COLOR_BGR2LAB)
                                    _clahe = cv2.createCLAHE(
                                        2.2, (8, 8))
                                    _l2 = _clahe.apply(_lab2[..., 0])
                                    _try = cv2.cvtColor(
                                        cv2.merge([_l2, _l2, _l2]),
                                        cv2.COLOR_BGR2GRAY)
                                    _try = cv2.cvtColor(
                                        _try, cv2.COLOR_GRAY2BGR)
                                except Exception:
                                    _try = _big
                            try:
                                _res = self.ocr.ocr(_try)
                            except Exception:
                                _res = None
                            out["calls"] += 1
                            _txts = []
                            if _res:
                                for _ln in (_res[0] or []):
                                    try:
                                        _tv = _ln[1]
                                        if isinstance(_tv, (tuple, list)):
                                            _tv = _tv[0]
                                        if str(_tv).strip():
                                            _txts.append(str(_tv).strip())
                                    except Exception:
                                        continue
                            _txt = " ".join(_txts)
                            if _txt:
                                out["nonempty"] = True
                                _zm_empty = False
                            else:
                                out["empty"] += 1
                            if self._is_watermark_text(_txt):
                                break
                            if _txt:
                                break
                        if _zm_empty and _zm == 3:
                            break
                    if _txt and self._is_watermark_text(_txt):
                        out["found"] = True
                        out["txt"] = _txt
                except Exception:
                    pass
                return out

            _wm_results: list = []
            while _wm_i < len(_ordered):
                if _tlimit > 0 and time.time() - _t > _tlimit:
                    if self.debug:
                        try:
                            print(f"  [🔍] جارویِ بنر: سقفِ زمانیِ "
                                  f"{_tlimit:.0f}s — {_ocr_calls} "
                                  f"فراخوانی از {len(_ordered)} کاندید",
                                  flush=True)
                        except Exception:
                            pass
                    break
                if _stop_all:
                    if self.debug:
                        try:
                            print("  [🔍] جارویِ بنر: توقفِ زودهنگام — "
                                  f"{_empty_streak} فراخوانیِ خالیِ پیاپی "
                                  f"(اکاندی‌هایِ بعدی هم بافتِ هنرند)",
                                  flush=True)
                        except Exception:
                            pass
                    break
                if _ocr_calls >= _max_calls:
                    if self.debug:
                        try:
                            print(f"  [🔍] جارویِ بنر: بودجهٔ OCR تمام شد "
                                  f"({_max_calls} فراخوانی) — "
                                  f"{len(_cands)} کاندید")
                        except Exception:
                            pass
                    break
                _batch = _ordered[_wm_i:_wm_i + max(1, _wm_pw)]
                _wm_i += len(_batch)
                if _wm_pw > 1:
                    try:
                        with ThreadPoolExecutor(max_workers=_wm_pw) as _wmx:
                            _wm_res = list(_wmx.map(_wm_scan_one, _batch))
                    except Exception:
                        _wm_res = [_wm_scan_one(_c) for _c in _batch]
                else:
                    _wm_res = [_wm_scan_one(_c) for _c in _batch]
                for (_c2, _r) in zip(_batch, _wm_res):
                    (_s0, _s1, _s2, _s3, cx0, cy0, cx1, cy1) = _c2
                    _ocr_calls += int(_r.get("calls", 0))
                    _txt = str(_r.get("txt", "") or "")
                    if _r.get("nonempty"):
                        _empty_streak = 0
                    else:
                        _empty_streak += int(_r.get("empty", 0))
                        if (_empty_max > 0
                                and _empty_streak >= _empty_max):
                            _stop_all = True
                    if _r.get("found"):
                        _tr = TextRegion(
                            id=10000 + len(found),
                            boxes=[np.array([[cx0, cy0], [cx1, cy0],
                                             [cx1, cy1], [cx0, cy1]],
                                            dtype=np.float32)],
                            source_text=_txt,
                            rect=(cx0, cy0, cx1 - cx0, cy1 - cy0),
                            kind="promo")
                        found.append(_tr)
                        _found_rects.append((cx0, cy0, cx1, cy1))
                        try:
                            _max_calls = min(
                                _max_calls,
                                _ocr_calls + max(6,
                                                 (_max_calls - _ocr_calls) // 3))
                        except Exception:
                            pass
                        if self.debug:
                            try:
                                print(f"  [🔍] بنرِ تبلیغ: rect={_tr.rect} "
                                      f"متن: {_txt[:60]}")
                            except Exception:
                                pass
            if self.debug:
                try:
                    print(f"  [🔍] جارویِ بنر: {len(found)} تبلیغ شناسایی شد")
                except Exception:
                    pass
        except Exception:
            import traceback as _tb
            if self.debug:
                try:
                    print("  [🔍] جارویِ بنر: خطا —")
                    _tb.print_exc()
                except Exception:
                    pass
            return found
        return found

    def finish_page_phase(self, image: np.ndarray, regions: List[TextRegion],
                          skip_translate: bool = False,
                          precleaned: Optional[np.ndarray] = None,
                          final: bool = False,
                          det_quads: Optional[list] = None,
                          page_boxes: Optional[list] = None,
                          ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        _raise_if_stop()
        if not regions:
            return image.copy(), None

        page_debug: Optional[np.ndarray] = None

        dialogue_regions = [r for r in regions if r.kind == "dialogue"]
        promo_regions = [r for r in regions if r.kind == "promo"]
        sfx_regions = [r for r in regions if r.kind == "sfx"]
        junk_regions = [r for r in regions if r.kind == "junk"]
        raw_image_copy = image.copy()

        if getattr(self, "clean_only", False):
            clean_targets = [r for r in regions
                             if r.kind in ("dialogue", "junk", "promo")]
            if _android_gate("MANGA_CLEAN_TEXTFREE"):
                _tf = [r for r in regions if r.kind == "text_free"]
                if _tf:
                    clean_targets = clean_targets + _tf
                    if self.debug:
                        try:
                            print(f"  [*]text_free: +{len(_tf)} "
                                  f"ناحیه به پاکسازی اضافه شد "
                                  f"(متنِ واقعی — نه تبلیغ)", flush=True)
                        except Exception:
                            pass
            if self.debug and regions:
                page_debug = self._draw_debug_regions(image, regions, det_quads)
                try:
                    _kc = {}
                    for _r in regions:
                        if _r.kind not in ("dialogue", "junk"):
                            _kc[_r.kind] = _kc.get(_r.kind, 0) + 1
                    if _kc:
                        print(f"  [*]{len(regions) - len(clean_targets)}"
                              f" ناحیه رد شد (تبلیغ/SFX دست‌نخورده): {_kc}")
                except Exception:
                    pass
            if clean_targets:
                if precleaned is not None:
                    final_image = precleaned
                else:
                    if _android_gate("MANGA_PHASE_PRINTS"):
                        print("[*] پاکسازی متن…", flush=True)
                    _t0 = time.time()
                    final_image = self.clean_image(image, clean_targets,
                                                   page_boxes=page_boxes)
                    print(f"[+] پاکسازی: {time.time() - _t0:.1f} ثانیه با {self._clean_label()}")
            else:
                final_image = precleaned.copy() if precleaned is not None else image.copy()
            return final_image, page_debug

        if (not skip_translate and dialogue_regions
                and not getattr(self, "clean_only", False)):
            self._rescue_empty_ocr(image, dialogue_regions)

        if skip_translate:
            pass
        elif dialogue_regions:
            print(f"[*] ترجمه: {len(dialogue_regions)} حباب…")
            self.translate_regions(dialogue_regions)

        if (final and not getattr(self, "clean_only", False)
                and not getattr(self, "fake_translate", False)
                and getattr(self, "_extraction_done", True)):
            for _g_round in range(1, 4):
                if stop_requested():
                    break
                _g_missing = [r for r in dialogue_regions
                              if not (r.translated_text or "").strip()
                              and (r.source_text or "").strip()
                              and source_has_letters(r.source_text)
                              and not getattr(r, "ocr_empty", False)]
                if not _g_missing:
                    break
                print(f"دورِ {_g_round}/۳: {_g_missing.__len__()} حباب هنوز ترجمه نشده — "
                      "تا ترجمهٔ کامل صبر میشود، انگلیسی نشان داده نمیشود…")
                try:
                    self.translate_regions(_g_missing)
                except (GeminiQuotaExhausted, JobCancelled):
                    raise
                except Exception as _g_err:
                    print(f"    دورِ {_g_round} خطا: {str(_g_err)[:80]}")
                    time.sleep(0.6)

        translated_regions = [r for r in dialogue_regions if r.translated_text]
        _fb: List[TextRegion] = []
        if final and precleaned is not None:
            for _r2 in dialogue_regions:
                if (_r2.translated_text or "").strip() \
                        or not (_r2.source_text or "").strip() \
                        or not source_has_letters(_r2.source_text) \
                        or getattr(_r2, "ocr_empty", False):
                    continue
                _c = copy.copy(_r2)
                _c.translated_text = _r2.source_text
                _fb.append(_c)
            if _fb:
                print(f"  {len(_fb)} حباب بدونِ ترجمه ولی پاکشده → "
                      "متنِ مبدأ رندر شد (ضدِ حبابِ خالی)")
                if self.debug:
                    for _c in _fb:
                        try:
                            print(f"    حباب[{_c.id}] rect="
                                  f"{tuple(int(v) for v in _c.rect)} → "
                                  f"متنِ مبدأ: {(_c.translated_text or '')[:60]}")
                        except Exception:
                            pass
        _oe = [r for r in dialogue_regions
                  if not r.translated_text
                  and getattr(r, "ocr_empty", False)]
        _ocr_empty_regions = _oe
        if _oe:
            for _r in _oe:
                try:
                    print(f"  [!] ناحیهٔ {_r.id} بدونِ متنِ OCR → فقط پاکسازی (rect={tuple(int(v) for v in _r.rect)}) — متنِ قبلی نمیماند")
                except Exception:
                    pass
        _clean_regions = (translated_regions + _ocr_empty_regions)
        if getattr(self, "clean_sfx", False) and sfx_regions:
            _clean_regions = _clean_regions + sfx_regions
        if _android_gate("MANGA_CLEAN_TEXTFREE"):
            _tf_free = [r for r in regions if r.kind == "text_free"]
            if _tf_free:
                _clean_regions = _clean_regions + _tf_free
        missing_n = sum(1 for r in dialogue_regions
                        if not r.translated_text
                        and not getattr(r, "ocr_empty", False)
                        and (r.source_text or "").strip()
                        and source_has_letters(r.source_text))
        if missing_n and final:
            print(f"[!] {missing_n} حباب ترجمه نشد")
        if self.debug:
            if promo_regions:
                print(f"  [*] {len(promo_regions)} تبلیغ → دست‌نخورده «ازش رد شه»")
            if sfx_regions:
                _sfx = "پاک شدند" if getattr(self, "clean_sfx", False) else "دست‌نخورده"
                print(f"  [*] {len(sfx_regions)} SFX → {_sfx}")
            if junk_regions:
                print(f"  [*] {len(junk_regions)} junk → دست‌نخورده")

        if self.debug and regions:
            page_debug = self._draw_debug_regions(image, regions, det_quads)

        if _clean_regions or _fb:
            if precleaned is not None:
                cleaned_image = precleaned
            else:
                if _android_gate("MANGA_PHASE_PRINTS"):
                    print("[*] پاکسازی متن…", flush=True)
                _t0 = time.time()
                cleaned_image = self.clean_image(image, _clean_regions,
                                                 page_boxes=page_boxes)
                print(f"[+] پاکسازی: {time.time() - _t0:.1f} ثانیه با {self._clean_label()}")
            final_image = self.render_translations(
                cleaned_image,
                (translated_regions + _fb) if _fb else translated_regions,
                raw_image_copy)
            if not self.debug:
                for _r in translated_regions:
                    _txt = (_r.translated_text or "").strip().replace("\n", " / ")
                    if _txt:
                        print(f"    {_txt[:150]}")
        else:
            final_image = precleaned.copy() if precleaned is not None else image.copy()
        if (not final and precleaned is not None
                and not getattr(self, "clean_only", False)):
            _wait_regions = [r for r in dialogue_regions
                             if not (r.translated_text or "").strip()
                             and not getattr(r, "ocr_empty", False)
                             and (r.source_text or "").strip()]
            if _wait_regions:
                try:
                    final_image = self._draw_loading_marks(
                        final_image, _wait_regions)
                except Exception as _lg_err:
                    if self.debug:
                        try:
                            print(f"    نشانِ لودینگ: {str(_lg_err)[:80]}")
                        except Exception:
                            pass
        return final_image, page_debug

    def _draw_loading_marks(self, image: np.ndarray,
                                 regions: List[TextRegion]) -> np.ndarray:
        img = image
        if img is None or img.size == 0 or not regions:
            return img
        h, w = img.shape[:2]
        _spin = int((time.time() * 90.0) % 360.0)
        for r in regions:
            try:
                _rx, _ry, _rw, _rh = r.rect
                x0, y0 = max(0, int(_rx)), max(0, int(_ry))
                x1 = min(w - 1, int(_rx + _rw) - 1)
                y1 = min(h - 1, int(_ry + _rh) - 1)
                bw, bh = x1 - x0, y1 - y0
                if bw < 26 or bh < 26:
                    continue
                cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
                rad = int(min(bw, bh) * 0.17)
                rad = max(8, min(rad, 44))
                th = max(2, rad // 5)
                col = (150, 150, 150)
                cv2.ellipse(img, (cx, cy), (rad, rad), _spin % 360,
                            0, 250, col, th, cv2.LINE_AA)
                _d = max(2, th - 1)
                _dy = min(cy + rad + th * 3, y1 - _d - 1)
                if _dy > cy:
                    for _k in (-1, 0, 1):
                        _px = cx + _k * (rad // 2 + _d * 2)
                        if x0 + _d < _px < x1 - _d:
                            cv2.circle(img, (_px, _dy), _d, col, -1, cv2.LINE_AA)
            except Exception:
                continue
        return img

    def process_core(self, image: np.ndarray) -> np.ndarray:
        _t_all = time.time()
        _t = time.time()
        regions, dbg, page_ctx = self.extract_regions_phase(image)
        _t_ext = time.time() - _t
        if dbg is not None:
            self._last_debug_image = dbg
        else:
            self._last_debug_image = None
        if not regions:
            try:
                print(f"[TIME] extract={_t_ext:.1f}s | "
                      f"total={time.time() - _t_all:.1f}s (بدونِ متن)",
                      flush=True)
            except Exception:
                pass
            return image
        _t = time.time()
        try:
            self._classify_balloon_tones(image, regions)
        except Exception:
            pass
        _t_tone = time.time() - _t
        _t = time.time()
        final_image, _ = self.finish_page_phase(
            image, regions, final=True,
            det_quads=page_ctx.get("quads"),
            page_boxes=page_ctx.get("boxes"))
        _t_fin = time.time() - _t
        try:
            print(f"[TIME] extract={_t_ext:.1f}s tone={_t_tone:.1f}s "
                  f"translate+clean+render={_t_fin:.1f}s "
                  f"total={time.time() - _t_all:.1f}s", flush=True)
        except Exception:
            pass
        return final_image

    def _classify_balloon_tones(self, image: np.ndarray,
                                regions: List[TextRegion]) -> None:
        clf = getattr(self, "_tone_clf", None)
        if clf is None:
            clf = BalloonToneClassifier()
            self._tone_clf = clf
        h, w = image.shape[:2]
        for r in regions:
            if getattr(r, "style_locked", False):
                continue
            try:
                x0, y0, x1, y1 = r.rect
                x0, y0 = max(0, int(x0)), max(0, int(y0))
                x1, y1 = min(w, int(x1)), min(h, int(y1))
                if x1 - x0 < 10 or y1 - y0 < 10:
                    continue
                pad = 8
                px0 = max(0, x0 - pad)
                py0 = max(0, y0 - pad)
                px1 = min(w, x1 + pad)
                py1 = min(h, y1 + pad)
                crop = image[py0:py1, px0:px1]
                tone = clf.classify(crop)
                if tone and tone in BalloonToneClassifier.TONES:
                    r.bubble_style = tone
            except Exception:
                continue

    @staticmethod
    def _is_mostly_blank(image: np.ndarray, std_thresh: float = 12.0, unique_thresh: int = 24) -> bool:
        if image is None or image.size == 0:
            return True
        h, w = image.shape[:2]
        if h < 40 or w < 40:
            return True
        y0, y1 = int(h * 0.15), int(h * 0.85)
        x0, x1 = int(w * 0.1), int(w * 0.9)
        crop = image[y0:y1, x0:x1]
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
        if float(np.std(gray)) < std_thresh:
            return True
        hist = cv2.calcHist([gray], [0], None, [64], [0, 256]).flatten()
        if int(np.count_nonzero(hist > (gray.size * 0.002))) < unique_thresh and float(np.std(gray)) < 22:
            return True
        return False

    @staticmethod
    def _is_url(s: str) -> bool:
        return s.lower().startswith("http://") or s.lower().startswith("https://")

    @staticmethod
    def _cluster_widths(widths: List[int], abs_tol: int = 180, rel_tol: float = 0.18) -> Dict[int, int]:
        if not widths:
            return {}
        indexed = sorted(enumerate(widths), key=lambda t: t[1])
        clusters: List[List[Tuple[int, int]]] = []
        for idx, w in indexed:
            if not clusters:
                clusters.append([(idx, w)])
                continue
            cur = clusters[-1]
            vals = [x[1] for x in cur]
            med = int(np.median(vals))

            last_w = cur[-1][1]
            tol = max(abs_tol, int(med * rel_tol), int(last_w * rel_tol))
            if abs(w - med) <= tol or abs(w - last_w) <= tol:
                cur.append((idx, w))
            else:
                clusters.append([(idx, w)])
        mapping: Dict[int, int] = {}
        for cur in clusters:
            vals = [x[1] for x in cur]
            med = float(np.median(vals))

            target = int(round(med / 100.0) * 100)
            if target < 1:
                target = max(1, int(round(med)))
            for idx, _ in cur:
                mapping[idx] = target
        return mapping

    def _normalize_page_width(self, im: np.ndarray, target_w: Optional[int] = None) -> np.ndarray:
        if im is None or im.size == 0:
            return im
        if target_w is None:
            target_w = self.max_output_width
        if not target_w or target_w <= 0:
            return im
        h, w = im.shape[:2]
        if w == target_w:
            return im
        cap = self.max_output_width
        if cap and cap > 0 and target_w > cap:
            target_w = cap
        scale = target_w / float(w)
        new_w = int(target_w)
        new_h = max(1, int(round(h * scale)))

        if scale < 0.95:
            interp = cv2.INTER_AREA
        elif scale > 1.05:
            interp = cv2.INTER_CUBIC
        else:
            interp = cv2.INTER_LINEAR
        out = cv2.resize(im, (new_w, new_h), interpolation=interp)
        return np.ascontiguousarray(out)

    def _find_safe_cut_y_smart(
        self,
        strip: np.ndarray,
        target_y: int,
        min_y: int,
        max_y: int,
        search_radius: int = 900,
        protected_ranges: Optional[List[Tuple[int, int]]] = None,
        spans_ready: bool = False,
    ) -> Optional[int]:
        if strip is None or strip.size == 0 or self.det is None:
            return None
        try:
            ih, iw = strip.shape[:2]
            clearance = max(12, int(round(iw * 0.02)))
            edge_margin = max(14, int(round(iw * 0.02)))
            y0 = max(int(min_y), int(target_y) - int(search_radius),
                     clearance + edge_margin)
            y1 = min(int(max_y), int(target_y) + int(search_radius),
                     ih - clearance - edge_margin)
            if y1 < y0:
                return None
            spans: List[Tuple[int, int]] = []
            if spans_ready:
                for top, bottom in (protected_ranges or []):
                    t, b = int(top), int(bottom)
                    if b > t:
                        spans.append((max(0, t), min(ih, b)))
            else:
                probe_half = max(250, int(round((y1 - y0) * 0.25)),
                                 clearance + edge_margin)
                wy0 = max(0, y0 - probe_half)
                wy1 = min(ih, y1 + probe_half)
                if wy1 - wy0 < 100:
                    return None
                band = strip[wy0:wy1]
                boxes = self.det.detect(band, fast=True)
                for box in boxes:
                    _, by1, _, by2 = box["rect"]
                    top = max(0, wy0 + int(by1) - edge_margin)
                    bot = min(ih, wy0 + int(by2) + 1 + edge_margin)
                    if bot > top:
                        spans.append((top, bot))
                for top, bottom in (protected_ranges or []):
                    spans.append((max(0, int(top) - edge_margin),
                                  min(ih, int(bottom) + 1 + edge_margin)))
            spans.sort()
            merged: List[Tuple[int, int]] = []
            for top, bot in spans:
                if merged and top <= merged[-1][1]:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], bot))
                else:
                    merged.append((top, bot))

            def _hit_text(_y: int) -> bool:
                return any(top <= _y <= bottom for top, bottom in merged)

            if y0 <= int(target_y) <= y1 and not _hit_text(int(target_y)):
                return int(target_y)
            pad = max(14, int(round(iw * 0.015)))
            cands: List[int] = []
            if merged:
                first_top = merged[0][0] - pad
                if y0 <= first_top <= y1:
                    cands.append(first_top)
                for j in range(len(merged) - 1):
                    gap = merged[j + 1][0] - merged[j][1]
                    if gap >= 2 * pad:
                        mid = merged[j][1] + gap // 2
                        if y0 <= mid <= y1:
                            cands.append(mid)
                last_bot = merged[-1][1] + pad
                if y0 <= last_bot <= y1:
                    cands.append(last_bot)
            cands = [c for c in cands if not _hit_text(c)]
            if cands:
                return min(cands, key=lambda y: abs(y - target_y))
            _t = int(target_y)
            for _d in range(1, max(y1 - _t, _t - y0) + 1):
                _yy = _t - _d
                if y0 <= _yy <= y1 and not _hit_text(_yy):
                    return _yy
                _yy = _t + _d
                if y0 <= _yy <= y1 and not _hit_text(_yy):
                    return _yy
            return None
        except Exception:
            return None

    def _repair_page_seams(self, image_files: List[str], work_dir: str) -> List[str]:

        if len(image_files) < 2 or not getattr(self, "repair_page_seams", True):
            return image_files
        if self.det is None:
            print("[!] ترمیم مرز متن انجام نشد: مدل تشخیص حباب در دسترس نیست.")
            return image_files

        os.makedirs(work_dir, exist_ok=True)
        result: List[str] = []
        group: List[np.ndarray] = []
        group_path = image_files[0]
        group_height = 0
        joined_count = 0

        def emit_group() -> None:
            if len(group) == 1:
                result.append(group_path)
                return

            width = group[0].shape[1]
            scale = (self.max_output_width / float(width)
                     if self.max_output_width else 1.0)
            fmt = (getattr(self, "img_format", None) or "webp").lstrip(".").lower()
            limit = {"webp": 16383, "jpg": 65500, "jpeg": 65500}.get(fmt)
            if limit and max(round(width * scale), round(group_height * scale)) > limit:
                raise RuntimeError("تصاویرِ دارای متن مشترک برای فرمت خروجی بیش از حد بلند شدند؛ "
                                   "--stitch-max-height 3600 یا --img-format png را انتخاب کنید. "
                                   "از وسط متن برش زده نشد.")
            path = os.path.join(work_dir, f"joined_{len(result) + 1:03d}.png")
            if not cv2.imwrite(path, np.vstack(group)):
                raise RuntimeError(f"ذخیرهٔ تصاویر متصل‌شده ناموفق بود: {path}")
            result.append(path)

        for path in image_files:
            image = MangaTranslator._imread_any(path)
            if image is None:
                raise RuntimeError(f"خواندن تصویر برای ترمیم مرز متن ناموفق بود: {path}")
            if not group:
                group = [image]
                group_height = len(image)
                continue
            previous = group[-1]
            width = min(previous.shape[1], image.shape[1])
            if self.max_output_width and self.max_output_width > 0:
                width = min(width, self.max_output_width)
            left = self._normalize_page_width(previous, target_w=width)
            right = self._normalize_page_width(image, target_w=width)
            context = max(320, int(round(width * 0.75)))
            tail, head = left[-context:], right[:context]
            preview = np.vstack([tail, head])
            seam = len(tail)
            try:
                boxes = self.det.detect(preview)
            except Exception as exc:
                raise RuntimeError("تشخیص متن در مرز دو تصویر ناموفق بود؛ "
                                   "برای جلوگیری از OCR متن نصفه، پردازش متوقف شد.") from exc
            crossing = any(box["rect"][1] <= seam - 8 and box["rect"][3] >= seam + 8
                           for box in boxes)
            if crossing:
                image = self._normalize_page_width(image, target_w=group[0].shape[1])
                if image.shape[1] != group[0].shape[1]:
                    raise RuntimeError("عرض تصاویر متصل‌شده یکسان نیست؛ ابتدا عرض ورودی‌ها را یکسان کنید.")
                if group_height + len(image) > 32000:
                    raise RuntimeError("زنجیرهٔ تصاویر دارای متن مشترک بیش از حد بلند شد؛ "
                                       "--stitch-max-height 3600 را فعال کنید.")
                group.append(image)
                group_height += len(image)
                joined_count += 1
                print(f"[*] متن/حباب روی مرز {os.path.basename(path)} ادامه دارد؛ "
                      "دو بخش پیش از OCR متصل شدند.")
            else:
                emit_group()
                group, group_path, group_height = [image], path, len(image)
        emit_group()
        if joined_count:
            print(f"[*] ترمیم خودکار مرز متن: {len(image_files)} تصویر → {len(result)} تصویر؛ "
                  "بدون برش مجدد ارتفاع.")
        return result

    def _stitch_pages_for_efficiency(self, image_files: List[str], work_dir: str) -> List[str]:

        if not image_files:
            return image_files
        if self.stitch_max_height <= 0:
            return self._repair_page_seams(image_files, work_dir)

        work_h = int(self.stitch_max_height)

        soft_h = int(getattr(self, "stitch_short_threshold", 0) or 0)
        if soft_h > work_h:
            work_h = soft_h
        lookahead = max(512, min(2000, work_h // 2))

        os.makedirs(work_dir, exist_ok=True)
        result: List[str] = []
        start_idx = 0

        if self.det is None and (len(image_files) > 1 or not self.stitch_keep_first):
            raise RuntimeError("برش امن به detector-v4-s نیاز دارد؛ مدل تشخیص بارگذاری نشده است. "
                               "برای حفظ فایل‌های اصلی --stitch-max-height 0 را بزنید.")

        keep_first = bool(self.stitch_keep_first)
        current_protected: List[Tuple[int, int]] = []
        if keep_first and len(image_files) > 1:

            first = MangaTranslator._imread_any(image_files[0])
            second = MangaTranslator._imread_any(image_files[1])
            if first is None or second is None:
                print("[!] خواندن دو تصویر اول برای بررسیِ مرز امن نشد؛ "
                      "صفحهٔ اول جدا نگه داشته می‌شود و ادامه می‌دهیم.")
            else:
                seam_w = min(first.shape[1], second.shape[1])
                if self.max_output_width and self.max_output_width > 0:
                    seam_w = min(seam_w, self.max_output_width)
                first = self._normalize_page_width(first, target_w=seam_w)
                second = self._normalize_page_width(second, target_w=seam_w)
                context = max(320, int(round(seam_w * 0.75)))
                tail, head = first[-context:], second[:context]
                preview = np.vstack([tail, head])
                seam_y = len(tail)
                padding = max(14, int(round(seam_w * 0.02)))
                try:
                    protected = [
                        (box["rect"][1] - padding, box["rect"][3] + padding)
                        for box in self.det.detect(preview)
                    ]
                except Exception as exc:
                    raise RuntimeError("بررسی مرز صفحهٔ اول ناموفق بود؛ برای جلوگیری از قطع متن "
                                       "صفحه جدا نشد.") from exc
                keep_first = self._find_safe_cut_y_smart(
                    preview, seam_y, seam_y, seam_y, protected_ranges=protected,
                    spans_ready=True,
                ) is not None
                if not keep_first:
                    current_protected = [
                        (top + len(first) - seam_y, bottom + len(first) - seam_y)
                        for top, bottom in protected
                    ]
                    print("[*] مرز صفحهٔ اول امن نیست؛ برای حفظ متنِ ادامه‌دار به صفحهٔ بعد چسبانده می‌شود.")
                del first, second, tail, head, preview

        if keep_first:
            ext_s = "." + (getattr(self, "img_format", None) or "webp").lstrip(".")
            if ext_s == ".jpeg":
                ext_s = ".jpg"
            first_out = os.path.join(work_dir, f"strip_000_cover{ext_s}")
            shutil.copy2(image_files[0], first_out)
            result.append(first_out)
            start_idx = 1
            if start_idx >= len(image_files):
                return result

        sample_widths = []
        for f in image_files[start_idx:start_idx + min(8, len(image_files) - start_idx)]:
            im = MangaTranslator._imread_any(f)
            if im is None:
                raise RuntimeError(f"خواندن تصویر ناموفق بود؛ صفحه حذف نشد: {f}")
            sample_widths.append(im.shape[1])
        sample_widths.sort()
        target_w = sample_widths[len(sample_widths) // 2]
        if current_protected:

            scale = target_w / float(seam_w)
            current_protected = [
                (int(np.floor(top * scale)) - 2, int(np.ceil(bottom * scale)) + 2)
                for top, bottom in current_protected
            ]

        strip_i = 0
        current_pages: List[np.ndarray] = []
        current_h = 0
        min_strip = max(1, int(work_h * 0.65))
        scan_from = 0

        _page_spans: List[List[int]] = []
        _life = [0, 0]
        _pre_boxes: Dict[int, Tuple[float, List[Tuple[int, int]], bool]] = {}
        _pre_lock = threading.Lock()
        _pre_pages = list(range(start_idx, len(image_files)))

        def _pre_detect_page(_idx: int) -> None:
            try:
                _im = cv2.imread(image_files[_idx])
                if _im is None:
                    with _pre_lock:
                        _pre_boxes[_idx] = (0.0, [], True)
                    return
                _pw = float(_im.shape[1])
                _blank = False
                try:
                    _g = (cv2.cvtColor(_im, cv2.COLOR_BGR2GRAY)
                          if _im.ndim == 3 else _im)
                    if int(_g.min()) >= 205:
                        _blank = True
                except Exception:
                    pass
                _bx: List[Tuple[int, int]] = []
                if not _blank:
                    try:
                        for _box in self.det.detect(_im, fast=True):
                            _r = _box.get("rect")
                            if not _r:
                                continue
                            _bx.append((int(_r[1]), int(_r[3])))
                    except Exception:
                        _bx = []
                with _pre_lock:
                    _pre_boxes[_idx] = (_pw, _bx, _blank)
            except Exception:
                with _pre_lock:
                    _pre_boxes.setdefault(_idx, (0.0, [], True))

        _pre_threads: List[threading.Thread] = []
        if _pre_pages and self.det is not None:
            try:
                from collections import deque as _deque
                _dq = _deque(_pre_pages)
                _pre_total = len(_pre_pages)
                _pre_prog = {"جلو": 0, "عقب": 0}
                _pre_step = max(3, _pre_total // 6)
                _pre_t0 = time.time()
                _pre_done_flag = {"d": False}
                try:
                    _n_pre = 2 if _on_android() else max(2, min(4, (os.cpu_count() or 2)))
                except Exception:
                    _n_pre = 2
                _n_pre = max(1, min(_n_pre, len(_pre_pages)))

                def _pre_worker(_from_right: bool) -> None:
                    _tag = "عقب" if _from_right else "جلو"
                    while True:
                        try:
                            _idx = _dq.pop() if _from_right else _dq.popleft()
                        except IndexError:
                            return
                        _pre_detect_page(_idx)
                        _show = _fin = False
                        with _pre_lock:
                            _pre_prog[_tag] += 1
                            _show = (_pre_total >= 6
                                     and _pre_prog[_tag] % _pre_step == 0)
                            if (not _pre_done_flag["d"]
                                    and (_pre_prog["جلو"] + _pre_prog["عقب"])
                                    >= _pre_total):
                                _pre_done_flag["d"] = True
                                _fin = True
                        if _show:
                            print(f"    [برش {_tag}] صفحهٔ {_idx + 1} از "
                                  f"{_pre_total} کش شد")
                        if _fin:
                            print(f"[✓] برش امن دوطرفه: هر {_pre_total} صفحه "
                                  f"از دو طرف کش شد "
                                  f"({time.time() - _pre_t0:.1f}s)")

                for _k in range(_n_pre):
                    _t = threading.Thread(
                        target=_pre_worker, args=(bool(_k % 2),), daemon=True)
                    _t.start()
                    _pre_threads.append(_t)
                print(f"[*] برش امن دوطرفه (RT-DETR / detector-v4-s): {_n_pre} کارگر تشخیص "
                      f"— یکی از صفحهٔ اول به آخر، یکی از آخر به اول")
            except Exception:
                _pre_threads = []

        def _pre_wait(_idx: int, _timeout: float = 120.0) -> bool:
            _t0 = time.time()
            while time.time() < _t0 + _timeout:
                with _pre_lock:
                    if _idx in _pre_boxes:
                        return True
                if _pre_threads and not any(_t.is_alive() for _t in _pre_threads):
                    break
                time.sleep(0.04)
            with _pre_lock:
                return _idx in _pre_boxes
        print(
            f"[*] چسباندن streaming + برش امن: هدف={work_h}px | "
            f"نگاه به جلو={lookahead}px | ارتفاع هدف است، نه برش اجباری"
        )

        def _stack_pages(pages: List[np.ndarray]) -> np.ndarray:
            return np.vstack(pages) if len(pages) > 1 else pages[0]

        def _emit_array(arr: np.ndarray, label: str = "") -> None:
            nonlocal strip_i
            if arr is None or arr.size == 0:
                return
            ext_s = "." + (getattr(self, "img_format", None) or "webp").lstrip(".")
            if ext_s == ".jpeg":
                ext_s = ".jpg"
            out_path = os.path.join(work_dir, f"strip_{strip_i + 1:03d}{ext_s}")
            scale = (self.max_output_width / float(arr.shape[1])
                     if getattr(self, "max_output_width", 0) else 1.0)
            encoded_size = [max(1, int(round(d * scale))) for d in arr.shape[:2]]
            codec_limit = {".webp": 16383, ".jpg": 65500}.get(ext_s)
            if codec_limit and max(encoded_size) > codec_limit:
                raise RuntimeError("نوار امن برای این فرمت بیش از حد بزرگ است؛ "
                                   "با --img-format png دوباره اجرا کنید. "
                                   "برای رعایت محدودیت فرمت از وسط متن برش زده نشد.")
            self._write_image(arr, out_path)
            result.append(out_path)
            print(f"    [+] نوار {strip_i + 1}: {label} ({arr.shape[0]}px)")
            strip_i += 1

        def _cut_and_emit(final: bool = False) -> None:
            nonlocal current_pages, current_h, current_protected, scan_from
            if not current_pages or (not final and current_h < work_h + lookahead):
                return

            strip = _stack_pages(current_pages)
            ih = int(strip.shape[0])
            protected = list(current_protected)
            padding = max(14, int(round(target_w * 0.02)))

            def _scan_window(_top: int, _limit: int) -> List[Tuple[int, int]]:
                _bottom = min(_limit, _top + 1680)
                try:
                    if _page_spans and _pre_threads:
                        _ih_now = int(strip.shape[0])
                        _end_cur = _life[0] - _life[1]
                        _out_c: List[Tuple[int, int]] = []
                        _have_all = True
                        for _j in range(len(_page_spans)):
                            _pid, _y0 = _page_spans[_j]
                            _seg_a = _y0 - _life[1]
                            _y0n = _page_spans[_j + 1][1] \
                                if _j + 1 < len(_page_spans) else _life[0]
                            _seg_b = _y0n - _life[1]
                            if _seg_b <= _top or _seg_a >= _bottom:
                                continue
                            if not _pre_wait(_pid):
                                _have_all = False
                                break
                            with _pre_lock:
                                _ent = _pre_boxes.get(_pid)
                            if _ent is None or _ent[0] <= 0:
                                _have_all = False
                                break
                            _pw, _bx, _blank = _ent
                            if _blank:
                                continue
                            _sc = target_w / _pw
                            _base = _seg_a
                            for (_by1, _by2) in _bx:
                                _sy1 = _base + int(_by1 * _sc)
                                _sy2 = _base + int(_by2 * _sc)
                                if _sy2 < _top or _sy1 > _bottom:
                                    continue
                                _out_c.append((_sy1, _sy2))
                        if _have_all:
                            return [(_sy1 - padding, _sy2 + padding)
                                    for (_sy1, _sy2) in _out_c]
                except Exception:
                    pass
                _win = strip[_top:_bottom]
                try:
                    _g = (cv2.cvtColor(_win, cv2.COLOR_BGR2GRAY)
                          if _win.ndim == 3 else _win)
                    if int(_g.min()) >= 205:
                        return []
                except Exception:
                    pass
                _out: List[Tuple[int, int]] = []
                try:
                    for box in self.det.detect(_win, fast=True):
                        _, y1, _, y2 = box["rect"]
                        _out.append((_top + y1 - padding, _top + y2 + padding))
                except Exception as exc:
                    raise RuntimeError("تشخیص detector-v4-s برای برش امن ناموفق بود؛ "
                                       "برش اجباری انجام نشد.") from exc
                return _out

            def _scan_band(_band_top: int, _band_bot: int) -> None:
                nonlocal scan_from
                _s_lo = max(0, _band_top - 520)
                _s_hi = min(ih, _band_bot + 480)
                if _s_hi <= scan_from or _s_hi - _s_lo < 100:
                    return
                _win_starts = list(range(max(scan_from - 520, _s_lo), _s_hi, 1160))
                if not _win_starts:
                    return
                if _win_starts[-1] + 1680 < _s_hi:
                    _win_starts.append(max(_win_starts[-1] + 1160,
                                           _s_hi - 1680))
                _scan_tw = 1
                try:
                    if len(_win_starts) > 1:
                        _scan_tw = (2 if _on_android()
                                    else max(2, min(3, (os.cpu_count() or 2) // 2)))
                except Exception:
                    _scan_tw = 1
                _scan_tw = max(1, min(_scan_tw, len(_win_starts)))
                if _scan_tw > 1:
                    with ThreadPoolExecutor(max_workers=_scan_tw) as _sex:
                        for _res in _sex.map(
                                lambda _t: _scan_window(_t, _s_hi), _win_starts):
                            protected.extend(_res)
                else:
                    for _t in _win_starts:
                        protected.extend(_scan_window(_t, _s_hi))
                scan_from = max(scan_from, _s_hi)

            offset = 0
            while ih - offset >= work_h + min_strip:
                max_cut = ih - max(min_strip, lookahead if not final else 0)
                _band_lo = offset + max(0, int(work_h) - 1000)
                _band_hi = offset + int(work_h)
                _band_mid = (_band_lo + _band_hi) // 2
                cut_y = None
                if min(_band_hi, max_cut) >= _band_lo:
                    _scan_band(_band_lo, min(_band_hi, max_cut))
                    cut_y = self._find_safe_cut_y_smart(
                        strip, _band_mid, _band_lo, min(_band_hi, max_cut),
                        search_radius=max(250, (_band_hi - _band_lo) // 2),
                        protected_ranges=protected,
                        spans_ready=True,
                    )
                if cut_y is None:
                    _fb_hi = min(_band_lo, max_cut)
                    _fb_lo = offset + max(120, int(work_h) // 3)
                    if _fb_hi - _fb_lo >= 200:
                        _scan_band(_fb_lo, _fb_hi)
                        cut_y = self._find_safe_cut_y_smart(
                            strip, _fb_hi, _fb_lo, _fb_hi,
                            search_radius=max(200, _fb_hi - _fb_lo),
                            protected_ranges=protected,
                            spans_ready=True,
                        )
                if cut_y is None:
                    break
                _emit_array(strip[offset:cut_y], f"برش بررسی‌شده y={cut_y}")
                offset = cut_y

            current_h = ih - offset
            current_protected = [(max(0, top - offset), bottom - offset)
                                 for top, bottom in current_protected if bottom >= offset]
            scan_from = max(0, scan_from - offset)
            _life[1] += offset
            while len(_page_spans) > 1 and (_page_spans[1][1] - _life[1]) <= 0:
                _page_spans.pop(0)
            if final:
                label = ("پایان فصل" if current_h <= work_h + min_strip
                         else "بزرگ‌تر از هدف: محل برش امن پیدا نشد")
                _emit_array(strip[offset:], label)
                current_pages, current_h = [], 0
            else:

                current_pages = [strip[offset:].copy()]
                if current_h > max(32000, work_h * 8):
                    raise RuntimeError("نوار بدون محل برش امن بیش از حد بلند شد؛ "
                                       "برای جلوگیری از قطع متن، پردازش متوقف شد.")

        for _abs_i, f in enumerate(image_files[start_idx:], start=start_idx):
            im = MangaTranslator._imread_any(f)
            if im is None:
                raise RuntimeError(f"خواندن تصویر ناموفق بود؛ صفحه حذف نشد: {f}")
            h, w = im.shape[:2]
            if (target_w > 0
                    and abs(w - target_w) > max(180, int(target_w * 0.18))):
                if current_pages:
                    _cut_and_emit(final=True)
                    current_protected = []
                    scan_from = 0
                    _page_spans.clear()
                    _life[0] = 0
                    _life[1] = 0
                print(f"[*] عرضِ {w}px با گروهِ {target_w}px فرق دارد → "
                      f"نوارِ جدا؛ استخراجِ دقیقاً تک-حالتی (بدونِ له‌شدن)")
                target_w = w
            if w != target_w and target_w > 0:

                new_h = max(1, int(round(h * (target_w / float(w)))))
                interp = cv2.INTER_AREA if target_w < w else cv2.INTER_CUBIC
                im = cv2.resize(im, (target_w, new_h), interpolation=interp)
                h, w = im.shape[:2]
            current_pages.append(im)
            _page_spans.append([_abs_i, _life[0]])
            _life[0] += h
            current_h += h
            _cut_and_emit()

        _cut_and_emit(final=True)

        print(
            f"[*] چسباندن صفحات: {len(image_files)} صفحه → {len(result)} نوار "
            f"(هدف={work_h}px / نگاه به جلو={lookahead}px"
            f"{'، صفحهٔ اول جدا (مرز امن)' if keep_first else ''})"
        )
        return result if result else image_files
