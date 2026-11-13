# BUILD-STRIP-START
class _MangaTranslatorBody_80:
# BUILD-STRIP-END
    @staticmethod
    def _is_rate_or_model_quota_error(err: Exception) -> bool:

        msg = str(err)
        low = msg.lower()

        if any(x in low for x in (
            "deadline", "timeout", "timed out", "bad file descriptor",
            "ssl:", "wrong_version", "connection reset", "broken pipe",
        )):
            return False
        if any(x in msg for x in (
            "RESOURCE_EXHAUSTED", "429", "RateLimit", "rateLimit",
            "PerMinute", "PerModel", "PerHour",
        )):
            return True
        if any(x in low for x in (
            "rate limit", "quota", "resource exhausted",
            "too many requests", "exceeded your current quota",
            "high demand", "try again later",
        )):
            if MangaTranslator._is_daily_quota_error(err):
                return False
            return True
        return False

    TONE_NAMES = [
        "normal", "shout", "comedy_shout", "whisper",
        "sun_thought", "thought", "free_text", "system",
        "monster", "cry", "fear", "broadcast", "letter",
        "narrator", "square_thought", "black",
    ]

    def _get_system_instruction(self) -> str:
        try:
            _jp = bool(self._ocr_lang_flags()[2])
        except Exception:
            _jp = False
        _with_schema = getattr(self, "provider_type", "openai") != "gemini"
        return mt_system_instruction(japanese=_jp, with_schema=_with_schema)

    @staticmethod
    def _is_watermark_text(text: str) -> bool:

        t = (text or "").lower()
        toks = re.findall(r"[a-z0-9]+", t)
        if not toks:
            return False
        token_set = set(toks)
        compact = "".join(toks)
        grams = {tuple(toks[i:i + n]) for n in (2, 3) for i in range(len(toks) - n + 1)}
        for w in WATERMARK_PATTERNS:
            parts = tuple(w.split())
            if not parts:
                continue
            if len(parts) == 1:
                if parts[0] not in token_set and not (
                        len(parts[0]) >= 8 and parts[0] in compact):
                    continue
                if len(text or "") <= 32 or len(toks) <= 4:
                    return True
                if "_" in (text or "") and parts[0] in compact:
                    return True
                if re.search(r"(?i)(\.(?:com|net|org|io|gg)|www\.|@)", text):
                    return True
            else:
                if parts in grams:
                    return True
        return bool(PROMO_RE.search(text) or DOMAIN_RE.search(text))

    @staticmethod
    def _cleanup_translation(t: str) -> str:

        if not t:
            return t

        t = t.replace("?", "؟")

        t = t.replace("\\n", "\n").replace("\\r", "").replace("\\t", " ")

        t = re.sub(r"(?i)([a-z])\1{1,}", "", t)
        t = re.sub(r"(?i)([!؟])\s*[a-z]{1,3}\s*", r"\1", t)
        t = re.sub(r"(?i)(?<=[(\u0600-\u06FF)])\s*[a-z]{1,2}\s*$", "", t)

        t = re.sub(
            r"[\u2e80-\u303f\u3040-\u30ff\u3100-\u312f\u3130-\u318f"
            r"\u31f0-\u31ff\u3400-\u4dbf\u4e00-\u9fff\ua960-\ua97f"
            r"\uac00-\ud7af\uf900-\ufaff\uff00-\uffef]+",
            "", t,
        )
        t = re.sub(r"[^\S\n]{2,}", " ", t)
        t = re.sub(r" *\n *", "\n", t)
        t = re.sub(r"\s+([؟!.,،])", r"\1", t)
        return t.strip()

    @staticmethod
    def _mt_norm(text: str) -> str:
        return re.sub(r"[^\w]", "", (text or "").lower())

    @staticmethod
    def _mt_pages_payload(regions: List[TextRegion]):
        groups: List[Tuple[str, List[TextRegion]]] = []
        by_key: dict = {}
        for r in regions:
            pi = getattr(r, "page_index", -1)
            pf = (getattr(r, "page_file", "") or "").strip()
            if pi is not None and pi >= 0:
                key = ("p", int(pi))
            elif pf:
                key = ("f", pf)
            else:
                key = ("u",)
            if key not in by_key:
                fname = pf or "page_01.png"
                _taken = {g[0] for g in groups}
                _base, _ext = os.path.splitext(fname)
                _n = 2
                while fname in _taken:
                    fname = f"{_base}_{_n}{_ext}"
                    _n += 1
                by_key[key] = (fname, [])
                groups.append((fname, by_key[key][1]))
            by_key[key][1].append(r)
        pages = [{"filename": fname,
                  "dialogues": [r.source_text or "" for r in rs]}
                 for fname, rs in groups]
        region_page = {id(r): fname for fname, rs in groups for r in rs}
        return pages, region_page

    _CENSOR_CORES = {
        "censored", "redacted", "blocked", "omitted", "skipped",
        "unavailable", "contentremoved", "contentblocked", "filtered",
        "sanctioned", "suppressed",
        "سانسور", "سانسورشد", "سانسورشده", "سانسورشدهاست",
        "متنسانسورشده", "حذفشد",
    }

    _CENSOR_RETRY_NOTE = ("\r\n\r\nRETRY NOTE: A previous attempt returned "
                          "placeholders or refusals such as '[CENSORED]' for "
                          "some of these blocks. Those blocks are raw comic OCR "
                          "and may look garbled or broken — that is NEVER a "
                          "reason to refuse. Translate EVERY single block with "
                          "your best interpretation of the intended dialogue. "
                          "Placeholders and refusals are strictly forbidden.")

    _STYLE_RETRY_NOTE = ("\r\n\r\nSTYLE RETRY NOTE: A previous attempt for "
                         "this chapter came back formal/bookish Persian "
                         "(\u0645\u06cc\u200c\u0628\u0627\u0634\u062f, "
                         "\u0622\u06cc\u0627, \u0628\u0646\u0627\u0628\u0631\u0627\u06cc\u0646\u061b). "
                         "That register is WRONG for spoken comic dialogue. "
                         "Rewrite the blocks below in natural, spoken, "
                         "colloquial Persian — the way people actually talk "
                         "(\u0645\u06cc\u200c\u062e\u0648\u0645, \u0645\u06cc\u200c\u062a\u0648\u0646\u0645, "
                         "\u0628\u0631\u06cc\u0645, \u0646\u0645\u06cc\u200c\u062f\u0648\u0646\u0645). "
                         "Formal/bookish wording is strictly forbidden.")

    @classmethod
    def _is_censored_translation(cls, fa: str) -> bool:
        if not fa:
            return False
        t = str(fa).strip()
        if not t:
            return False
        core = re.sub(
            r"[\s\u200c\[\](){}<>«»*~`'\"\u201c\u201d\u2018\u2019"
            r"\-–—_.!?؟:;,،/\\|+#^%$@]+",
            "", t).lower()
        if not core:
            return len(t) <= 12
        if core in cls._CENSOR_CORES:
            return True
        if len(core) <= 48:
            if core.startswith(("imsorry", "iamsorry", "sosorry",
                                "icant", "icannot", "iamunableto",
                                "imunableto", "cannottranslate",
                                "canttranslate", "unabletotranslate",
                                "cannotassist", "cantassist",
                                "cannothelp", "noiwillnot",
                                "asani", "asaani",
                                "نمیتوانم", "نمی‌توانم",
                                "قادرنیستم", "قادرنمیباشم",
                                "ترجمهناممکن", "ترجمهنشد", )):
                return True
            if "translatethis" not in core and (
                    "cannottranslate" in core or "canttranslate" in core
                    or "unabletotranslate" in core
                    or "refuseto" in core or "cannotassist" in core):
                return True
        return False

    def _apply_mt_pages(self, pages, regions: List[TextRegion],
                        region_page: Optional[dict] = None) -> int:
        if not pages or not regions:
            return 0
        applied = 0
        _censored = 0
        done: set = set()
        for pg in pages:
            if not isinstance(pg, dict):
                continue
            fname = str(pg.get("filename") or "")
            trans = [it for it in (pg.get("translations") or [])
                     if isinstance(it, dict)]
            page_regions = [r for r in regions
                            if id(r) not in done
                            and (not region_page
                                 or region_page.get(id(r)) == fname)]
            if not page_regions and region_page:
                page_regions = [r for r in regions if id(r) not in done]
            used_items: set = set()
            for i, it in enumerate(trans):
                en = str(it.get("en_text") or "")
                fa = (it.get("fa_text") or "")
                if not isinstance(fa, str) or not fa.strip():
                    continue
                if self._is_censored_translation(fa) \
                        and "censor" not in en.lower():
                    _censored += 1
                    used_items.add(i)
                    continue
                reg = None
                if en:
                    reg = next((r for r in page_regions
                                if id(r) not in done
                                and (r.source_text or "") == en), None)
                    if reg is None:
                        _ne = self._mt_norm(en)
                        if _ne:
                            reg = next((r for r in page_regions
                                        if id(r) not in done
                                        and self._mt_norm(r.source_text) == _ne),
                                       None)
                if reg is not None:
                    reg.translated_text = self._cleanup_translation(fa)
                    done.add(id(reg))
                    used_items.add(i)
                    applied += 1
            left_regs = [r for r in page_regions if id(r) not in done]
            left_items = [i for i in range(len(trans)) if i not in used_items]
            for r, i in zip(left_regs, left_items):
                fa = trans[i].get("fa_text")
                if isinstance(fa, str) and fa.strip():
                    _src_hint = str(trans[i].get("en_text") or "") \
                        + (r.source_text or "")
                    if self._is_censored_translation(fa) \
                            and "censor" not in _src_hint.lower():
                        _censored += 1
                        continue
                    r.translated_text = self._cleanup_translation(fa)
                    done.add(id(r))
                    applied += 1
        if _censored:
            print(f"    [!] {_censored} پاسخِ جای‌نگهدار ([CENSORED]/انکار) "
                  f"رد شد — دوباره پرسیده میشود", flush=True)
        return applied

    _MT_PAGE_BLOCK_RE = re.compile(
        r'\{\s*"filename"\s*:\s*"[^"]+"\s*,\s*"translations"\s*:\s*\[.*?\]\s*\}',
        re.S,
    )

    @classmethod
    def _salvage_stream_pages(cls, text: str, on_pages) -> None:
        if not text or on_pages is None:
            return
        blocks = cls._MT_PAGE_BLOCK_RE.findall(text)
        if not blocks:
            return
        pages = []
        for b in blocks:
            try:
                pages.append(json.loads(b))
            except Exception:
                continue
        if pages:
            try:
                on_pages(pages)
            except Exception:
                pass

    def _parse_translation_response(self, text: str, regions: List[TextRegion],
                                    region_page: Optional[dict] = None) -> bool:

        text = text.strip()

        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        try:
            results = json.loads(text)
        except json.JSONDecodeError:

            m = re.search(r"\[[\s\S]*\]", text)
            if not m:
                raise
            results = json.loads(m.group(0))

        if isinstance(results, dict):
            for key in ("translations", "results", "data"):
                if isinstance(results.get(key), list):
                    results = results[key]
                    break
        if not isinstance(results, list):
            raise ValueError("پاسخ مدل آرایه نیست.")

        _mt_pages = [it for it in results
                     if isinstance(it, dict)
                     and isinstance(it.get("translations"), list)
                     and ("filename" in it)]
        if _mt_pages:
            applied = self._apply_mt_pages(_mt_pages, regions, region_page)
            if applied > 0:
                return True

        return False

    def _recreate_api_client(self) -> None:

        if not self._api_keys:
            return
        key = self._api_keys[self._key_index % len(self._api_keys)]
        try:
            self._apply_api_key(key)
        except Exception as e:
            print(f"    [!] بازسازی کلاینت ناموفق: {e}")

    def _call_ai_with_timeout(self, fn, *, label: str = "AI",
                              timeout: float = None) -> str:

        timeout = (float(timeout) if timeout
                   else float(getattr(self, "api_timeout", 45.0) or 45.0))
        if timeout <= 0:
            return fn()
        ex = ThreadPoolExecutor(max_workers=1)
        fut = ex.submit(fn)
        try:
            return fut.result(timeout=timeout)
        except FuturesTimeout:
            try:
                fut.cancel()
            except Exception:
                pass
            try:
                ex.shutdown(wait=False, cancel_futures=True)
            except TypeError:
                ex.shutdown(wait=False)
            self._recreate_api_client()
            raise TimeoutError(
                f"{label} بیش از {timeout:.0f}ثانیه طول کشید (timeout) → مدل بعدی"
            )
        except Exception:
            try:
                ex.shutdown(wait=False, cancel_futures=True)
            except TypeError:
                ex.shutdown(wait=False)
            raise
        else:
            try:
                ex.shutdown(wait=False, cancel_futures=True)
            except TypeError:
                ex.shutdown(wait=False)

    def _translate_with_gemini(self, user_prompt: str, system_instruction: str,
                               *, structured: bool = True,
                               timeout: float = None,
                               on_item=None) -> str:
        _g_temp = self.translation_temperature if structured else 0.2
        _g_top_p = self.translation_top_p
        if (structured and "gemini-3.6-flash" in (self._thread_model() or "")
                and _g_temp == 0.7 and _g_top_p == 0.9):
            _g_temp, _g_top_p = 0.4, 0.7
        config_args = dict(
            system_instruction=system_instruction,
            temperature=_g_temp,
        )
        if structured:
            config_args["top_p"] = _g_top_p
            if getattr(self, "_sbn_ok", True):
                try:
                    _sbn = []
                    for _cat in ("HARM_CATEGORY_HARASSMENT",
                                 "HARM_CATEGORY_HATE_SPEECH",
                                 "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                                 "HARM_CATEGORY_DANGEROUS_CONTENT"):
                        _sbn.append(genai_types.SafetySetting(
                            category=genai_types.HarmCategory[_cat],
                            threshold=genai_types.HarmBlockThreshold.BLOCK_NONE,
                        ))
                    config_args["safety_settings"] = _sbn
                except Exception:
                    pass
            config_args["response_mime_type"] = "application/json"
            config_args["response_schema"] = json.loads(MT_RESPONSE_SCHEMA_TEXT)
        else:
            config_args["max_output_tokens"] = 768
        config = genai_types.GenerateContentConfig(**config_args)
        client = self._thread_client()
        model = self._thread_model()
        self._pace_before_gemini_call()

        def _do():
            if on_item is not None:
                _parts: list = []
                try:
                    for _chunk in client.models.generate_content_stream(
                            model=model, contents=user_prompt, config=config):
                        _t = None
                        try:
                            _t = _chunk.text
                        except Exception:
                            _t = None
                        if not _t:
                            continue
                        _parts.append(_t)
                        try:
                            self._salvage_stream_pages(
                                "".join(_parts), on_item)
                        except Exception:
                            pass
                except Exception:
                    if not _parts:
                        response = client.models.generate_content(
                            model=model, contents=user_prompt, config=config,
                        )
                        _t = getattr(response, "text", None)
                        if _t:
                            _parts.append(_t)
                text = "".join(_parts)
            else:
                response = client.models.generate_content(
                    model=model, contents=user_prompt, config=config,
                )
                text = response.text
            if not text or not text.strip():
                raise RuntimeError("پاسخ خالی از Gemini دریافت شد.")
            return text

        return self._call_ai_with_timeout(
            _do, label=f"Gemini/{model}", timeout=timeout
        )

    def _translate_with_openai(self, user_prompt: str, system_instruction: str,
                               *, structured: bool = True,
                               timeout: float = None,
                               on_item=None) -> str:
        model = self._thread_model()
        client = self._thread_openai()
        mlow = model.lower()
        _eff_t = float(timeout) if timeout and float(timeout) > 0 else 0.0
        try:
            _eff_t = max(_eff_t,
                         float(getattr(self, "api_timeout", 45.0) or 45.0))
        except Exception:
            pass
        kwargs = dict(
            model=model,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.translation_temperature if structured else 0.2,
            timeout=(_eff_t if _eff_t > 0
                     else float(getattr(self, "api_timeout", 10.0) or 10.0)),
        )
        if structured:
            kwargs["top_p"] = self.translation_top_p

        if re.search(r"(?:^|/)(?:o[134](?:-|$)|gpt-5(?:-|$))", mlow):
            kwargs.pop("temperature", None)
            kwargs.pop("top_p", None)

        def _do():
            resp = client.chat.completions.create(**kwargs)
            text = resp.choices[0].message.content
            if not text or not text.strip():
                raise RuntimeError(f"پاسخ خالی از {self.provider} دریافت شد.")
            return text

        if structured:
            def _do_stream():
                parts: list = []
                skw = dict(kwargs)
                skw["stream"] = True
                stream = client.chat.completions.create(**skw)
                for ev in stream:
                    piece = ""
                    try:
                        ch = (getattr(ev, "choices", None) or [None])[0]
                        if ch is not None:
                            piece = getattr(getattr(ch, "delta", None),
                                            "content", None) or ""
                    except Exception:
                        piece = ""
                    if not piece:
                        continue
                    parts.append(piece)
                    if on_item is not None:
                        try:
                            self._salvage_stream_pages("".join(parts), on_item)
                        except Exception:
                            pass
                text = "".join(parts)
                if not text.strip():
                    raise RuntimeError(
                        f"پاسخ خالی از {self.provider} دریافت شد.")
                return text

            try:
                return self._call_ai_with_timeout(
                    _do_stream, label=f"{self.provider}/{model}",
                    timeout=(_eff_t if _eff_t > 0 else None))
            except Exception as _se:
                _ss = str(_se).lower()
                _stream_broken = (
                    "stream" in _ss and ("support" in _ss or "invalid" in _ss
                                         or "unrecognized" in _ss
                                         or "not allowed" in _ss)
                ) or "does not support" in _ss or "not supported" in _ss
                if not _stream_broken:
                    raise
                print(f"    [!] استریم روی {model} ممکن نشد — مسیرِ عادی.")

        return self._call_ai_with_timeout(
            _do, label=f"{self.provider}/{model}",
            timeout=(_eff_t if _eff_t > 0 else None)
        )

    def _raw_api_post_text(self, url: str, headers: dict, payload: dict,
                           label: str) -> str:
        import urllib.request as _ureq
        import urllib.error as _uerr

        key = self._current_api_key()
        hdrs = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
        }
        hdrs.update(headers or {})
        if key and "Authorization" not in hdrs:
            hdrs["Authorization"] = "Bearer " + key
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        timeout_s = float(getattr(self, "api_timeout", 30.0) or 30.0)

        def _do():
            req = _ureq.Request(url, data=data, method="POST", headers=hdrs)
            try:
                with _ureq.urlopen(req, timeout=timeout_s) as resp:
                    raw = (resp.read() or b"").decode("utf-8", "ignore")
            except _uerr.HTTPError as e:
                body = ""
                try:
                    body = (e.read() or b"").decode("utf-8", "ignore")[:600]
                except Exception:
                    pass
                ok, msg = explain_api_http_error(e.code, body)
                if not ok:
                    raise RuntimeError(
                        msg + (f" — {' '.join(body.split())[:150]}"
                               if body and "HTTP" in msg else "")) from e
                raise RuntimeError(msg) from e
            try:
                return json.loads(raw)
            except Exception:
                raise RuntimeError(
                    f"پاسخ JSON نیست از {label}: {raw[:200]}")

        obj = self._call_ai_with_timeout(_do, label=label)
        return obj

    def _translate_with_openai_responses(self, user_prompt: str,
                                         system_instruction: str,
                                         *, structured: bool = True) -> str:
        model = self._thread_model()
        url = (self.api_base or "").rstrip("/") + "/responses"
        payload = {
            "model": model,
            "input": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt},
            ],
        }
        data = self._raw_api_post_text(url, {}, payload,
                                       label=f"{self.provider}-responses/{model}")
        text = ""
        if isinstance(data, dict):
            text = str(data.get("output_text") or "")
            if not text.strip():
                parts = []
                for item in (data.get("output") or []):
                    if not isinstance(item, dict):
                        continue
                    for c in (item.get("content") or []):
                        if isinstance(c, dict) and c.get("text"):
                            parts.append(str(c["text"]))
                text = "".join(parts)
            if not text.strip():
                ch = data.get("choices")
                if isinstance(ch, list) and ch:
                    msg = (ch[0] or {}).get("message") or {}
                    text = str(msg.get("content") or "")
        if not text or not text.strip():
            raise RuntimeError(f"پاسخ خالی از {self.provider} (responses) دریافت شد.")
        return text

    def _translate_with_anthropic(self, user_prompt: str,
                                  system_instruction: str,
                                  *, structured: bool = True) -> str:
        model = self._thread_model()
        base = (self.api_base or "").rstrip("/")
        if not base.endswith("/v1"):
            base += "/v1"
        url = base + "/messages"
        key = self._current_api_key()
        payload = {
            "model": model,
            "max_tokens": 4096,
            "system": system_instruction,
            "messages": [{"role": "user", "content": user_prompt}],
            "temperature": self.translation_temperature if structured else 0.2,
            **({"top_p": self.translation_top_p} if structured else {}),
        }
        headers = {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "Authorization": "Bearer " + key,
        }
        data = self._raw_api_post_text(url, headers, payload,
                                       label=f"{self.provider}-anthropic/{model}")
        text = ""
        if isinstance(data, dict):
            parts = []
            for c in (data.get("content") or []):
                if isinstance(c, dict) and c.get("text"):
                    parts.append(str(c["text"]))
            text = "".join(parts)
        if not text or not text.strip():
            raise RuntimeError(f"پاسخ خالی از {self.provider} (messages) دریافت شد.")
        return text

    def _translate_with_google_endpoint(self, user_prompt: str,
                                        system_instruction: str,
                                        *, structured: bool = True) -> str:
        import urllib.parse as _uparse
        model = self._thread_model()
        base = (self.api_base or "").rstrip("/")
        url = f"{base}/models/{_uparse.quote(model)}:generateContent"
        key = self._current_api_key()
        payload = {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": self.translation_temperature if structured else 0.2,
                **({"topP": self.translation_top_p} if structured else {}),
            },
        }
        headers = {
            "x-goog-api-key": key,
            "Authorization": "Bearer " + key,
        }
        data = self._raw_api_post_text(url, headers, payload,
                                       label=f"{self.provider}-google/{model}")
        text = ""
        if isinstance(data, dict):
            parts = []
            for cand in (data.get("candidates") or []):
                if not isinstance(cand, dict):
                    continue
                cont = cand.get("content") or {}
                for p in (cont.get("parts") or []):
                    if isinstance(p, dict) and p.get("text"):
                        parts.append(str(p["text"]))
            text = "".join(parts)
        if not text or not text.strip():
            raise RuntimeError(f"پاسخ خالی از {self.provider} (generateContent) دریافت شد.")
        return text

    def _translate_via_provider(self, user_prompt: str,
                                system_instruction: str,
                                *, structured: bool = True,
                                timeout: float = None,
                                on_item=None) -> str:
        if self.provider_type == "gemini":
            return self._translate_with_gemini(
                user_prompt, system_instruction, structured=structured,
                timeout=timeout, on_item=on_item)
        if self.provider_type == "openai-responses":
            return self._translate_with_openai_responses(
                user_prompt, system_instruction, structured=structured)
        if self.provider_type == "anthropic":
            return self._translate_with_anthropic(
                user_prompt, system_instruction, structured=structured)
        if self.provider_type == "google-endpoint":
            return self._translate_with_google_endpoint(
                user_prompt, system_instruction, structured=structured)
        return self._translate_with_openai(
            user_prompt, system_instruction, structured=structured,
            timeout=timeout, on_item=on_item)

    @staticmethod
    def _fix_ocr_text(text: str) -> str:

        if not text:
            return text
        t = text

        t = re.sub(r"[ \t\f\v]+", " ", t).strip()
        t = re.sub(r"\s*\n\s*", "\n", t)

        replacements = [
            (r"\bMUDI[:]?YING\b", "MODIFYING"),
            (r"\bMODIEYING\b", "MODIFYING"),
            (r"\bMODIFYlNG\b", "MODIFYING"),
            (r"\bRECONSTRUC(?:TION)?\b", "RECONSTRUCTION"),
            (r"\bRECONSTRUC\b", "RECONSTRUCTION"),
            (r"\bPROCES\b", "PROCESS"),
            (r"\bPARALYZE[D]?\b", "PARALYZED"),
            (r"\bMANA\b", "MANA"),
            (r"\bAND\s+YE\b", "AND YET"),
            (r"\bNDYE\b", "AND YET"),
            (r"\bONL\b", "ONLY"),
            (r"\bMYE\b", "MY"),
            (r"\bUNSCATHED\b", "UNSCATHED"),
            (r"\bUNFORESEEN\b", "UNFORESEEN"),
            (r"\bOVERCONSUMPTION\b", "OVERCONSUMPTION"),
            (r"\bRECONSTRUCTION\s+PROCES\b", "RECONSTRUCTION PROCESS"),
            (r"\bBODY\s+RECONSTRUCTION\b", "BODY RECONSTRUCTION"),
        ]
        for pat, rep in replacements:
            t = re.sub(pat, rep, t, flags=re.IGNORECASE)

        t = re.sub(r"([A-Za-z])[:;|]([A-Za-z])", r"\1\2", t)

        def _strip_trailing_number(s: str, pat: str) -> str:
            m = re.search(pat, s, flags=re.I)
            if not m:
                return s
            prefix = s[:m.start()]

            if re.search(
                r"(?:lv|iv|1v|l1|i1|lvl|level|ch|chapter|ep|episode|vol|no|score|hp|mp|power|rank)\s*[.:\-–]?\s*$",
                prefix[-10:], flags=re.I,
            ):
                return s
            return (prefix + s[m.end():]).strip()

        t = _strip_trailing_number(t, r"\s*[QOIl]?\d{3,}\s*$")
        t = _strip_trailing_number(t, r"\s+\d{3,}\s*$")
        return t.strip()

    def _style_ref_samples(self):
        try:
            store = getattr(self, "_chapter_style_samples", None) or []
            out = []
            for src, fa in store:
                src = str(src or "").strip()
                fa = str(fa or "").strip()
                if not src or not fa or fa == src:
                    continue
                if fa.startswith("[") and fa.endswith("]"):
                    continue
                out.append((src, fa))
                if len(out) >= 10:
                    break
            return out
        except Exception:
            return []

    def _note_style_samples(self, regions) -> None:
        try:
            store = getattr(self, "_chapter_style_samples", None)
            if store is None:
                store = self._chapter_style_samples = []
            seen = set((s, f) for s, f in store)
            for r in regions or []:
                try:
                    src = str(getattr(r, "source_text", "") or "").strip()
                    fa = str(getattr(r, "translated_text", "") or "").strip()
                except Exception:
                    continue
                if not src or not fa or fa == src:
                    continue
                if fa.startswith("[") and fa.endswith("]"):
                    continue
                if len(fa) < 4 or len(fa) > 200 or len(src) > 200:
                    continue
                if self._fa_style_verdict(fa) == "bookish":
                    continue
                key = (src, fa)
                if key in seen:
                    continue
                seen.add(key)
                store.append((src, fa))
            if len(store) > 24:
                del store[:len(store) - 24]
        except Exception:
            pass

    @staticmethod
    def _fa_style_verdict(text: str) -> str:
        try:
            verdict, _bk, _cs = _gemini_probe_score(str(text or ""))
            return verdict
        except Exception:
            try:
                norm = str(text or "").replace("\u200c", "").replace("\u200f", "")
                _b = sum(1 for m in ("می‌باشد", "می‌باشند", "آیا", "بنابراین",
                                     "می‌گردد", "می‌بایست", "خواهد بود")
                         if m.replace("\u200c", "") in norm)
                _c = sum(1 for m in ("می‌خوام", "می‌تونم", "بریم", "بذار",
                                     "نمی‌دونم", "خب", "وای")
                         if m.replace("\u200c", "") in norm)
                return "bookish" if (_b >= 2 or (_b and not _c)) else "ok"
            except Exception:
                return "ok"

    def _style_retry_bookish(self, regions) -> bool:
        if getattr(self, "_style_retried", False):
            return False
        done = [r for r in (regions or [])
                if str(getattr(r, "translated_text", "") or "").strip()]
        if not done:
            return False
        bad = []
        for r in done:
            try:
                if self._fa_style_verdict(r.translated_text) == "bookish":
                    bad.append(r)
            except Exception:
                pass
        _need = max(2, int(round(len(done) * 0.25)))
        if not bad or len(bad) < _need:
            return False
        self._style_retried = True
        self._style_retry_mode = True
        for r in bad:
            try:
                r.translated_text = ""
            except Exception:
                pass
        print(f"    [!] سبک: {len(bad)}/{len(done)} ترجمه کتابی آمد — "
              f"دوباره با لنگرِ محاوره‌ای پرسیده میشوند.")
        return True

    def translate_regions(self, regions: List[TextRegion]) -> None:
        _raise_if_stop()
        if not regions:
            return

        if getattr(self, "clean_only", False):
            print("    [*] Clean-only mode — no API request.")
            return

        if not getattr(self, "_extraction_done", True) \
                and not getattr(self, "fake_translate", False):
            print("[!!] رگرسیونِ دو-فازی: مترجم در وسطِ فازِ استخراج صدا "
                  "زده شد — گزارشِ باگ (باید بعد از «استخراجِ همهٔ صفحهها "
                  "کامل شد» بیاید).", file=sys.stderr)

        _n_empty = sum(1 for _r in regions
                       if not (_r.source_text or "").strip())
        if _n_empty:
            print(f"    [*] {_n_empty} ناحیه بدون متنِ OCR → فقط پاکسازی")
            regions = [r for r in regions if (r.source_text or "").strip()]
        if not regions:
            return

        _keep = [r for r in regions if source_has_letters(r.source_text)]
        _drop = len(regions) - len(_keep)
        if _drop:
            print(f"    [*] {_drop} ناحیه فقط عدد/علامت → دست‌نخورده (نه ترجمه، نه پاکسازی)")
            regions = _keep
        if not regions:
            return

        if getattr(self, "fake_translate", False):

            samples = [
                "این یک متن آزمایشی فارسی است.",
                "سلام! این حباب تستی است تا خروجی تصویر را چک کنی.",
                "جملهٔ کوتاه.",
                "این متن کمی بلندتر است تا شکستن خطوط داخل حباب هم آزمایش شود و مطمئن شویم رندر فارسی درست کار می‌کند.",
                "داد تستی!! حباب انرژی!!",
                "زمزمهٔ آرام تستی…",
                "این فکر تستی است و داخل حباب ابری رندر می‌شود.",
                "متن تستی برای حباب گفت‌وگوی عادی.",
            ]
            styles = ["normal", "normal", "normal", "normal", "shout", "whisper", "thought", "normal"]
            for i, r in enumerate(regions):
                r.source_text = self._fix_ocr_text(uncensor_swears(r.source_text or ""))
                r.translated_text = samples[i % len(samples)]
                r.bubble_style = styles[i % len(styles)]
            return

        self._pick_random_api_key(reason="ترجمه صفحه")
        self._cascade_full_cycles = 0
        self._same_model_timeout_retries = 0
        if self._model_cascade:
            good = (getattr(self, "_last_good_model", "") or "").strip()
            if good and good in self._model_cascade:
                idx = self._model_cascade.index(good)
            else:
                idx = 0
                for i, m in enumerate(self._model_cascade):

                    if "3." in m or "flash-latest" in m.lower() or "lite" in m.lower():
                        idx = i
                        break
            local = self._model_cascade[idx: idx + 6]
            if len(local) < 3:
                local = self._model_cascade[:6]
            tls = getattr(self, "_tls", None)
            if tls is not None:
                tls.local_cascade = local
                tls.local_index = 0
            self._set_thread_model(local[0], 0)

        for r in regions:
            r.source_text = self._fix_ocr_text(uncensor_swears(r.source_text or ""))

        def _make_batches(items: List[TextRegion]):

            if getattr(self, "chapter_one_request", False):
                return [list(items)]

            max_items = max(1, int(getattr(self, "bubbles_per_request", 6) or 6))
            max_chars = 2200
            batches: List[List[TextRegion]] = []
            cur: List[TextRegion] = []
            cur_chars = 0
            for r in items:
                tlen = len(r.source_text or "")
                if cur and (len(cur) >= max_items or cur_chars + tlen > max_chars):
                    batches.append(cur)
                    cur = []
                    cur_chars = 0
                cur.append(r)
                cur_chars += tlen
            if cur:
                batches.append(cur)
            return batches

        self._note_style_samples(regions)
        pending = list(regions)
        import concurrent.futures as _cf
        for round_i in range(1, 4):
            if not pending:
                break
            batches = _make_batches(pending)
            if len(batches) > 1 or round_i > 1:
                print(
                    f"    [*] دور {round_i}: {len(pending)} دیالوگ → {len(batches)} بسته"
                )
            workers = max(1, min(
                int(getattr(self, "batch_workers", 3) or 1), len(batches)))
            if getattr(self, "chapter_one_request", False):
                workers = 1
            if workers > 1:
                keys = list(self._api_keys)
                jobs = [(bi, b) for bi, b in enumerate(batches, 1)]
                with _cf.ThreadPoolExecutor(max_workers=workers) as ex:
                    def _run(job):
                        bi, batch = job
                        if keys:
                            self._apply_api_key(keys[(bi - 1) % len(keys)])
                        print(f"    [*] بسته {bi}/{len(batches)}: {len(batch)} دیالوگ (موازی)")
                        try:
                            self._translate_regions_batch(batch)
                        except Exception as e:
                            print(f"    [!] بسته {bi} ناموفق: {str(e)[:80]}")
                    list(ex.map(_run, jobs))
            else:
                for bi, batch in enumerate(batches, 1):
                    if len(batches) > 1:
                        print(f"    [*] بسته {bi}/{len(batches)}: {len(batch)} دیالوگ")
                    self._translate_regions_batch(batch)
                    if bi < len(batches):
                        time.sleep(1.0)

            pending = [r for r in regions if not (r.translated_text or "").strip()]
            self._note_style_samples(regions)
            try:
                if self._style_retry_bookish(regions):
                    pending = [r for r in regions
                               if not (r.translated_text or "").strip()]
            except Exception:
                pass
            if not pending:
                break
            if round_i < 3:
                wait_s = min(2.5 * round_i, 5.0)
                print(
                    f"    [!] {len(pending)} دیالوگ هنوز بدون ترجمه — "
                    f"صبر {wait_s:.0f}ثانیه و تلاش مجدد..."
                )
                time.sleep(wait_s)

                if self._api_keys and len(self._api_keys) > 1:
                    self._pick_random_api_key(reason=f"دور {round_i + 1}")
                if self._model_cascade and len(self._model_cascade) > 1:
                    self._switch_to_next_model(reason=f"دور {round_i + 1}")

        if any(not (r.translated_text or "").strip() for r in regions):
            try:
                if self._force_translate_missing(regions):
                    print("    [✓] نجاتِ نهایی در translate_regions انجام شد.")
            except Exception as _e:
                print(f"    [!] نجاتِ نهایی: {str(_e)[:80]}")
        still = sum(1 for r in regions if not (r.translated_text or "").strip())
        if still:
            print(f"    [!] در نهایت {still} دیالوگ بدون ترجمه ماند.")

    def _translate_regions_batch(self, regions: List[TextRegion]) -> None:
        if not regions:
            return

        system_instruction = self._get_system_instruction()
        source_text = "\n".join(r.source_text or "" for r in regions)
        delay = 0.4
        last_err = None
        work_regions = [r for r in regions if not (r.translated_text or "").strip()]
        if not work_regions:
            return

        _pctx: dict = {}
        _attempt_cell = [0]

        def _make_prompt():
            _pm = resolve_prompt_mode(
                getattr(self, "prompt_mode", "professional"),
                getattr(self, "provider", "gemini"),
                getattr(self, "model_name", ""),
            )
            rules = (getattr(self, "custom_instruction", "") or "").strip() \
                or PROMPT_PRESETS[_pm]
            pages, _rpage = self._mt_pages_payload(work_regions)
            _pctx["region_page"] = _rpage
            try:
                _jp = bool(self._ocr_lang_flags()[2])
            except Exception:
                _jp = False
            _sref = self._style_ref_samples()
            _out = mt_user_prompt(rules, pages, _jp, style_ref=_sref)
            if _attempt_cell[0] > 1:
                _out += self._CENSOR_RETRY_NOTE
            if getattr(self, "_style_retry_mode", False):
                _out += self._STYLE_RETRY_NOTE
            return _out

        for attempt in range(1, self.max_retries + 1):
            _attempt_cell[0] = attempt
            try:
                user_prompt = _make_prompt()

                if self.provider_type == "gemini" and self._is_bad_translate_model(self.model_name):
                    print(f"    [!] رد مدل نامناسب ترجمه: {self.model_name}")
                    if self._note_model_fail():
                        self._reset_model_cascade(reason="۳ بار مدل نامناسب")
                        self._recreate_api_client()
                        time.sleep(0.3)
                        continue
                    if self._drop_current_model_and_switch(reason="bad model"):
                        continue
                    if self._switch_to_next_model(reason="bad model"):
                        continue
                    print("    [!] مدل مناسب در cascade نماند.")
                    break

                _on_item = None
                _applied_pages: set = set()
                _want_stream = self.provider_type in ("gemini", "openai")
                if _want_stream:
                    def _on_pages(pages) -> None:
                        _new = [p for p in pages
                                if str(p.get("filename")) not in _applied_pages]
                        if not _new:
                            return
                        for p in _new:
                            _applied_pages.add(str(p.get("filename")))
                        self._apply_mt_pages(
                            _new, work_regions, _pctx.get("region_page"))
                        try:
                            self._note_style_samples(work_regions)
                        except Exception:
                            pass
                        _done = sum(1 for r in work_regions
                                    if (r.translated_text or "").strip())
                        print(f"    ← استریم: {_done}/{len(work_regions)} "
                              f"دیالوگ…", flush=True)
                    _on_item = _on_pages

                _chars = sum(len(r.source_text or "") for r in work_regions)
                _tout = min(
                    1800.0,
                    max(
                        float(getattr(self, "api_timeout", 45.0) or 45.0),
                        60.0 + 1.5 * len(work_regions) + _chars / 40.0,
                    ),
                )

                with self._api_lock:
                    if self.provider_type == "gemini":
                        text = self._translate_with_gemini(
                            user_prompt, system_instruction,
                            timeout=_tout, on_item=_on_item)
                    else:
                        text = self._translate_via_provider(
                            user_prompt, system_instruction,
                            timeout=_tout, on_item=_on_item)

                self._parse_translation_response(
                    text, work_regions, _pctx.get("region_page"))
                try:
                    self._note_style_samples(regions)
                except Exception:
                    pass
                self._note_model_ok()

                for r in work_regions:
                    if not (getattr(r, "bubble_style", None) or "").strip():
                        r.bubble_style = "normal"

                missing = [r for r in work_regions if not (r.translated_text or "").strip()]
                if missing and attempt < self.max_retries:
                    print(f"    [!] {len(missing)} حباب بدون ترجمه؛ تلاش مجدد...")
                    work_regions = missing
                    continue

                self._daily_fail_streak = 0
                self._daily_fail_model = ""
                self._rate_key_streak = 0
                self._cascade_full_cycles = 0
                if not missing:
                    self._last_good_model = self._thread_model()
                self._same_model_timeout_retries = 0
                status = f"{len(missing)} حباب بدون ترجمه ماند" if missing else "پاسخ کامل دریافت شد"
                print(f"[فاز ۳ - ترجمه با {self.provider}/{self._thread_model()}] {status}.")
                for r in regions:
                    if r.translated_text:
                        st = (getattr(r, "bubble_style", None) or "").strip()
                        extra = f" ({st})" if st else ""
                        print(f"    ← بالن[{r.id}]{extra}: {r.translated_text}")
                try:
                    self._force_translate_missing(regions)
                except Exception as _e:
                    print(f"    [!] نجاتِ نهایی: {str(_e)[:80]}")
                if self.request_delay > 0:
                    time.sleep(self.request_delay)
                return

            except Exception as e:
                last_err = e
                err_str = str(e).lower()
                _es = str(e)
                if ("BLOCK_NONE" in _es or "safety_settings" in _es.lower()
                        or ("blocked" in err_str and "safety" in err_str)):
                    self._sbn_ok = False

                is_timeout = (
                    isinstance(e, TimeoutError)
                    or isinstance(e, FuturesTimeout)
                    or "timeout" in err_str
                    or "timed out" in err_str
                    or "deadline_exceeded" in err_str
                    or "deadline expired" in err_str
                    or "504" in str(e)
                )
                is_conn_dead = (
                    "bad file descriptor" in err_str
                    or "wrong_version_number" in err_str
                    or "ssl:" in err_str
                    or "connection reset" in err_str
                    or "connection aborted" in err_str
                    or "broken pipe" in err_str
                )
                if is_timeout or is_conn_dead:
                    tag = "تایم‌اوت/اتصال" if is_conn_dead else "تایم‌اوت"
                    print(f"    [!] {tag} روی {self.provider}/{self.model_name}")
                    self._recreate_api_client()

                    _still = [r for r in work_regions
                              if not (r.translated_text or "").strip()]
                    if _still and len(_still) < len(work_regions):
                        work_regions = _still
                    same_retries = int(getattr(self, "_same_model_timeout_retries", 0) or 0)
                    try:
                        _mt_max = min(10, max(1, int(
                            os.environ.get("MANGA_TIMEOUT_RETRIES", "3") or 3)))
                    except Exception:
                        _mt_max = 3
                    try:
                        _mt_wait = max(0.5, float(
                            os.environ.get("MANGA_TIMEOUT_WAIT", "2.0") or 2.0))
                    except Exception:
                        _mt_wait = 2.0
                    if same_retries < _mt_max:
                        self._same_model_timeout_retries = same_retries + 1
                        _ws = min(_mt_wait * (2 ** same_retries), 30.0)
                        print(f"    [*] AutoRetry مرجع "
                              f"{same_retries + 1}/{_mt_max} روی "
                              f"{self.model_name} — صبر {_ws:.0f}ثانیه و "
                              f"تلاش دوباره…")
                        time.sleep(_ws)
                        continue
                    self._same_model_timeout_retries = 0
                    if self._switch_to_next_model(reason="timeout"):
                        self._recreate_api_client()
                        time.sleep(0.2)
                        continue

                    if not hasattr(self, "_cascade_full_cycles"):
                        self._cascade_full_cycles = 0
                    self._cascade_full_cycles += 1
                    if self._cascade_full_cycles <= 1:
                        self._reset_model_cascade(reason="timeout→ریست مدل‌ها")
                        self._recreate_api_client()
                        time.sleep(0.2)
                        continue
                    self._cascade_full_cycles = 0
                    if self._switch_to_next_key(reason="after full cascade", cycle=True):
                        self._reset_model_cascade(reason="کلید جدید")
                        self._recreate_api_client()
                        time.sleep(0.2)
                        continue
                    if attempt < self.max_retries:
                        time.sleep(0.25)
                        continue

                if self.provider_type == "gemini" and _HAS_GEMINI:

                    if self._is_banned_or_invalid_key_error(e):
                        if self._remove_current_key_and_switch(reason=str(e)[:120]):
                            continue
                        if not self._api_keys:
                            raise GeminiQuotaExhausted("همه کلیدها نامعتبر/بن شدند.") from e

                    if self._is_daily_quota_error(e):
                        if self._daily_fail_model == self.model_name:
                            self._daily_fail_streak += 1
                        else:
                            self._daily_fail_model = self.model_name
                            self._daily_fail_streak = 1
                        print(f"    [!] محدودیت روی {self.model_name} "
                              f"(کلید {self._key_index + 1}/{len(self._api_keys)}, "
                              f"streak={self._daily_fail_streak})")

                        if self._daily_fail_streak >= 2:
                            self._daily_fail_streak = 0
                            self._daily_fail_model = ""
                            if self._drop_current_model_and_switch(reason="سهمیه/محدودیت مدل"):
                                continue
                            if self._switch_to_next_model(reason="سهمیه مدل"):
                                continue
                        if self._switch_to_next_key(reason="سهمیه"):
                            continue
                        if self._switch_to_next_model(reason="سهمیه همه کلیدها"):
                            self._daily_fail_streak = 0
                            if self._api_keys:
                                self._key_index = 0
                                self._apply_api_key(self._api_keys[0])
                            continue
                        raise GeminiQuotaExhausted(
                            "سهمیه همه کلیدها و مدل‌ها تموم شده."
                        ) from e

                    if self._is_rate_or_model_quota_error(e):
                        print(f"    [!] محدودیت مدل/نرخ روی {self.model_name} "
                              f"(کلید {self._key_index + 1}/{len(self._api_keys)})")
                        if self._is_daily_quota_error(e):
                            self._daily_dead[(self.model_name,
                                              self._current_api_key())] = True
                            tried = {k for (m, k) in self._daily_dead
                                     if m == self.model_name}
                            if len(tried) < len(self._api_keys) \
                                    and self._switch_to_next_key(
                                        reason="سهمیهٔ روزانه", cycle=True):
                                self._recreate_api_client()
                                time.sleep(0.3)
                                continue
                            if self._drop_current_model_and_switch(
                                    reason="سهمیهٔ روزانهٔ این مدل"):
                                continue
                        if len(set(self._model_cascade or [])) > 1 \
                                and self._switch_to_next_model(
                                    reason="rate→تعویض فوری مدل"):
                            self._recreate_api_client()
                            time.sleep(0.2)
                            continue
                        _rd = self._mark_key_cooldown(e)
                        wait_s = (min(max(_rd, 2.0 + attempt), 60.0) if _rd
                                  else min(2.0 + attempt, 6.0))
                        print(f"    [*] صبر {wait_s:.0f} ثانیه برای بازیابی سهمیه...")
                        time.sleep(wait_s)
                        if self._switch_to_next_key(reason="rate مدل",
                                                    cycle=True):
                            self._recreate_api_client()
                            time.sleep(0.3)
                            continue
                        if self._switch_to_next_model(reason="quota/rate مدل"):
                            self._recreate_api_client()
                            time.sleep(0.5)
                            continue
                        if not hasattr(self, "_cascade_full_cycles"):
                            self._cascade_full_cycles = 0
                        self._cascade_full_cycles += 1
                        if self._cascade_full_cycles <= 1:
                            self._reset_model_cascade(reason="rate→ریست مدل‌ها")
                            self._recreate_api_client()
                            time.sleep(1.0)
                            continue
                        self._cascade_full_cycles = 0
                        if self._switch_to_next_key(reason="after full cascade", cycle=True):
                            self._reset_model_cascade(reason="کلید جدید")
                            self._recreate_api_client()
                            time.sleep(1.5)
                            continue
                        if attempt < self.max_retries:
                            time.sleep(2.0)
                            continue

                    if self._is_model_permanently_gone(e):
                        msg_l = str(e).lower()

                        is_404 = "404" in str(e) or "not_found" in msg_l or "not found" in msg_l
                        core = self.model_name.lower().replace("models/", "")
                        is_core_flash = any(
                            core == x or core.startswith(x)
                            for x in (
                                "gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.1-flash",
                                "gemini-flash-latest", "gemini-flash-lite-latest",
                                "gemini-3.5-flash-lite", "gemini-3.1-flash-lite",
                            )
                        )
                        suggested = self._extract_suggested_model(e)
                        if suggested:
                            print(f"    [!] مدل «{self.model_name}» دیگر در دسترس نیست → "
                                  f"پیشنهاد API: {suggested}")
                            self._note_model_fail()

                            dead = self.model_name
                            cascade = [x for x in (self._model_cascade or []) if x != dead]
                            if suggested not in cascade:
                                cascade.insert(0, suggested)
                            else:
                                cascade = [suggested] + [x for x in cascade if x != suggested]
                            self._model_cascade = cascade
                            self._model_index = 0
                            self.model_name = suggested
                            self._set_thread_model(suggested, 0)
                            self._recreate_api_client()
                            time.sleep(0.5)
                            continue
                        if is_404 and is_core_flash:
                            print(f"    [!] 404 روی {self.model_name} با این کلید → کلید بعدی "
                                  f"(مدل اصلی حذف نمی‌شود)")
                            if self._switch_to_next_key(reason="404 key", cycle=True):
                                self._recreate_api_client()
                                time.sleep(0.8)
                                continue
                            print(f"    [!] همه کلیدها روی {self.model_name} 404 → مدل بعدی")
                            if self._drop_current_model_and_switch(reason="404 all keys"):
                                self._recreate_api_client()
                                time.sleep(0.5)
                                continue
                            if self._switch_to_next_model(reason="404 all keys"):
                                self._recreate_api_client()
                                continue
                        else:
                            if self._note_model_fail():
                                self._reset_model_cascade(reason="۳ بار ناموجودِ مدل")
                                self._recreate_api_client()
                                time.sleep(0.3)
                                continue
                            print(f"    [!] مدل «{self.model_name}» ناسازگار → بعدی")
                            if self._drop_current_model_and_switch(reason=str(e)[:80]):
                                time.sleep(0.5)
                                continue
                            if self._switch_to_next_model(reason="gone"):
                                time.sleep(0.3)
                                continue

                    if self._is_model_unavailable_error(e):
                        if self._note_model_fail():
                            self._reset_model_cascade(reason="۳ بار UNAVAILABLE")
                            self._recreate_api_client()
                            time.sleep(0.3)
                            continue
                        if self._switch_to_next_model(reason="UNAVAILABLE"):
                            time.sleep(0.2)
                            continue
                        if self._switch_to_next_key(reason="model unavailable", cycle=False):
                            time.sleep(0.3)
                            continue

                if self._is_rate_or_model_quota_error(e) or any(
                    x in err_str for x in ("rate limit", "429", "quota", "insufficient_quota")
                ):
                    print(f"    [!] محدودیت نرخ/سهمیه ({self.provider}/{self.model_name})...")
                    if self._is_daily_quota_error(e):
                        self._daily_dead[(self.model_name,
                                          self._current_api_key())] = True
                        tried = {k for (m, k) in self._daily_dead
                                 if m == self.model_name}
                        if len(tried) < len(self._api_keys) \
                                and self._switch_to_next_key(
                                    reason="سهمیهٔ روزانه", cycle=True):
                            self._recreate_api_client()
                            time.sleep(0.3)
                            continue
                        if self._drop_current_model_and_switch(
                                reason="سهمیهٔ روزانهٔ این مدل"):
                            continue
                    if len(set(self._model_cascade or [])) > 1 \
                            and self._switch_to_next_model(
                                reason="rate→تعویض فوری مدل"):
                        self._recreate_api_client()
                        time.sleep(0.2)
                        continue
                    if self._switch_to_next_key(reason="rate/quota", cycle=True):
                        self._recreate_api_client()
                        time.sleep(0.3)
                        continue
                    _rd = self._mark_key_cooldown(e)
                    wait_s = (min(max(_rd, 3.0 + attempt), 60.0) if _rd
                              else min(3.0 + attempt, 8.0))
                    print(f"    [*] صبر {wait_s:.0f} ثانیه برای بازیابی سهمیه...")
                    time.sleep(wait_s)
                    if self._switch_to_next_model(reason="rate/quota"):
                        time.sleep(0.5)
                        continue
                if self._is_banned_or_invalid_key_error(e) or any(
                    x in err_str for x in ("invalid api key", "authentication", "incorrect api key")
                ):
                    print(f"    [!] کلید نامعتبر ({self.provider})...")
                    if self._remove_current_key_and_switch(reason=str(e)[:100]):
                        continue

                if ("403" in err_str or "forbidden" in err_str.lower()
                        or "does not have permission" in err_str.lower()):
                    print(f"    [!] دسترسی رد شد (403) — {self.provider}/{self.model_name}")
                    if self._switch_to_next_model(reason="403 permission"):
                        time.sleep(0.3)
                        continue
                    if self._switch_to_next_key(reason="403 permission", cycle=True):
                        time.sleep(0.5)
                        continue
                    print("    [X] هیچ کلید/مدلی به Gemini دسترسی ندارد (403). "
                          "احتمالاً شبکهٔ شما به سرویس گوگل مسدود است — VPN/پروکسی روشن کنید.")
                    return

                print(f"    [!] تلاش {attempt}/{self.max_retries} ناموفق: {last_err}")
                if attempt < self.max_retries:
                    time.sleep(delay)
                    delay = min(delay * 1.5, 3.0)

        print(f"    [!] {self.max_retries} تلاش ناموفق — ریست کامل و تلاش نهایی...")
        try:
            print("    [*] صبر ۲ ثانیه قبل از تلاش نهایی...")
            time.sleep(2.0)
            self._reset_model_cascade(reason="تلاش نهایی")
            if self._api_keys and len(self._api_keys) > 1:
                self._pick_random_api_key(reason="تلاش نهایی")
            else:
                self._recreate_api_client()
            work_regions = [r for r in work_regions if not (r.translated_text or "").strip()]
            if not work_regions:
                return
            try:
                self._note_style_samples(regions)
            except Exception:
                pass
            user_prompt = _make_prompt()
            with self._api_lock:
                if self.provider_type == "gemini":
                    text_final = self._translate_with_gemini(user_prompt, system_instruction)
                else:
                    text_final = self._translate_via_provider(user_prompt, system_instruction)
            self._parse_translation_response(text_final, work_regions)
            for r in work_regions:
                if not (getattr(r, "bubble_style", None) or "").strip():
                    r.bubble_style = "normal"
                fa = (r.translated_text or "").strip()
                if fa:
                    print(f"    ← بالن[{r.id}] (نهایی): {fa[:70]}{'…' if len(fa) > 70 else ''}")
            got = sum(
                1 for r in work_regions
                if str(getattr(r, "translated_text", "") or "").strip()
            )
            if got:
                self._last_good_model = self.model_name
                self._note_model_ok(self.model_name)
                print(f"[فاز ۳ - نهایی {self.model_name}] {got} بالن نجات یافت.")
                return
        except Exception as e:
            print(f"    [!] تلاش نهایی هم شکست: {e}")
        print(f"    [!] ترجمه‌ی این بخش بعد از {self.max_retries}+1 تلاش ناموفق موند.")
        try:
            if self._force_translate_missing(regions):
                print("    [✓] حبابهای خالی نجات یافتند (189).")
        except Exception as _e:
            print(f"    [!] نجاتِ نهایی: {str(_e)[:80]}")

    def _force_translate_missing(self, regions: List[TextRegion]) -> int:
        missing = [r for r in regions
                   if not str(getattr(r, "translated_text", "") or "").strip()
                   and str(getattr(r, "source_text", "") or "").strip()]
        if not missing:
            return 0
        print(f"    {len(missing)} حبابِ بدونِ ترجمه — نجاتِ تکآیتمی…")
        sys_inst = self._get_system_instruction()
        _sref = self._style_ref_samples()[:3]
        _anchor = ""
        if _sref:
            _ex = "\n".join(
                '  "' + str(_s)[:90] + '" -> "' + str(_f)[:90] + '"'
                for _s, _f in _sref)
            _anchor = ("\nStyle of this chapter (match its tone, register and "
                       "phrasing exactly — do NOT sound formal or bookish):\n"
                       + _ex + "\n")
        fixed = 0
        for r in missing:
            src = (r.source_text or "").strip()
            val = ""
            p1 = ("Translate this one manga dialogue into natural spoken Persian. "
                  "It is raw OCR output from a comic page, so it may contain "
                  "errors or look garbled — never refuse it and never write "
                  "placeholders such as [CENSORED]; translate the most likely "
                  "intended dialogue instead. "
                  "Answer with ONLY the Persian translation — no notes, no quotes."
                  "\n" + _anchor + "\n" + src)
            for _t in range(2):
                try:
                    with self._api_lock:
                        if self.provider_type == "gemini":
                            val = self._translate_with_gemini(
                                p1, sys_inst, structured=False) or ""
                        else:
                            val = self._translate_via_provider(
                                p1, sys_inst, structured=False) or ""
                    val = (val or "").strip()
                    val = re.sub(r"^```(?:json)?\s*|\s*```$", "", val).strip()
                    val = val.strip('"').strip().strip('"').strip()
                    if val and self._is_censored_translation(val) \
                            and "censor" not in src.lower():
                        print(f"    [!] نجاتِ تک‌آیتمیِ بالن[{r.id}]: پاسخِ "
                              f"جای‌نگهدار رد شد — تلاش مجدد")
                        val = ""
                    if val:
                        break
                    time.sleep(0.4)
                except Exception as e:
                    print(f"    [!] نجاتِ تکآیتمیِ بالن[{r.id}]: {str(e)[:80]}")
                    time.sleep(0.4)
            if not val:
                try:
                    _rules = (getattr(self, "custom_instruction", "") or "").strip() \
                        or PROMPT_PRESETS[resolve_prompt_mode(
                            getattr(self, "prompt_mode", "professional"),
                            getattr(self, "provider", "gemini"),
                            getattr(self, "model_name", ""))]
                    try:
                        _jp = bool(self._ocr_lang_flags()[2])
                    except Exception:
                        _jp = False
                    p2 = mt_user_prompt(
                        _rules,
                        [{"filename": "rescue_%d.png" % r.id, "dialogues": [src]}],
                        _jp)
                    with self._api_lock:
                        if self.provider_type == "gemini":
                            t2 = self._translate_with_gemini(p2, sys_inst)
                        else:
                            t2 = self._translate_via_provider(p2, sys_inst)
                    self._parse_translation_response(t2, [r])
                    val = (r.translated_text or "").strip()
                except Exception as e:
                    print(f"    [!] نجاتِ JSONِ بالن[{r.id}]: {str(e)[:80]}")
            if not val:
                print(f"    [!] بالن[{r.id}] مدل جواب نداد — بیترجمه میماند تا دورِ بعد دوباره پرسیده شود.")
                continue
            fixed += 1
            print(f"    ← نجاتِ 189[{r.id}]: {val[:60]}")
            r.translated_text = val
        return fixed

    @staticmethod
    def _shape_farsi(text: str) -> str:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)

    _FA_PROBE_CACHE: Optional[str] = None
    _FONT_COVER_CACHE: Dict[str, bool] = {}
