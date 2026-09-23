# -*- coding: utf-8 -*-

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


try:
    from manga_app import (  # noqa: F401
        APP_NAME, APP_VER, PROVIDERS, WEB_CSS,
    )
except Exception:
    APP_NAME, APP_VER, PROVIDERS = "مانگا مترجم", "1.7", [
        "gemini", "openai", "chatgpt", "deepseek", "groq",
        "xai", "grok", "together", "openrouter", "ollama"]
    WEB_CSS = "body{background:#060607;color:#e8e6e1;font-family:sans-serif}"

import manga

LOCK = threading.Lock()
JOBS = {}


def _bubbles_html():
    rows = "".join(
        '<label style="display:inline-flex;align-items:center;gap:8px;'
        'background:#08080a;border:1px solid #1f1f24;border-radius:10px;'
        'padding:10px 13px;margin:3px 0;font-size:.95rem;min-height:44px">'
        '<input type="radio" name="ocr_lang" value="%s" %s>'
        '<span style="color:#97948c">%s</span></label>'
        % (val, "checked" if val == "en" else "", lbl)
        for lbl, val in [
            ("انگلیسی", "en"),
            ("کره‌ای (+ انگلیسی)", "ko en"),
            ("ژاپنی (+ انگلیسی)", "ja en"),
            ("چینی (+ انگلیسی)", "zh en"),
            ("چندزبانه (کره‌ای/ژاپنی/چینی/انگلیسی)", "ko ja zh en"),
        ]
    )
    return rows


PAGE = """<!DOCTYPE html><html lang="fa" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>مانگا مترجم</title>
<style>%(css)s</style></head>
<body class="gradio-container">
<div class="nav"><div class="nav-left">
  <div class="stamp">漫</div>
  <div class="nav-brand">مانگا مترجم <span class="nav-sub">ترجمه خودکار مانهوا — نسخه گوشی</span></div>
</div></div>

<div class="stepcard">
 <div class="steptitle"><span class="stepnum">۱</span> ورودی — فایل یا لینک</div>
 <input type="file" id="f" accept=".pdf,.zip,.cbz,image/*" style="width:100%%;background:#08080a;color:#e8e6e1;border:1px solid #1f1f24;border-radius:10px;padding:10px">
 <input type="url" id="url" placeholder="یا URL تصویر/مانهوا" style="width:100%%;margin-top:8px;background:#08080a;color:#e8e6e1;border:1px solid #1f1f24;border-radius:10px;padding:12px">
</div>

<div class="stepcard">
 <div class="steptitle"><span class="stepnum">۲</span> مترجم هوش مصنوعی</div>
 <div style="display:flex;gap:8px;flex-wrap:wrap">
  <select id="provider" style="flex:1;background:#08080a;color:#e8e6e1;border:1px solid #1f1f24;border-radius:10px;padding:12px">%(providers)s</select>
  <input id="keys" type="password" placeholder="کلیدهای API (با کاما)" style="flex:2;background:#08080a;color:#e8e6e1;border:1px solid #1f1f24;border-radius:10px;padding:12px">
 </div>
 <div style="margin-top:10px;font-size:.85rem;color:#97948c">زبان متن مانگا (OCR):</div>
 <div id="langs" style="display:flex;flex-wrap:wrap">%(langs)s</div>
</div>

<div class="stepcard">
 <div class="steptitle"><span class="stepnum">۳</span> خروجی</div>
 <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
  <select id="fmt" style="background:#08080a;color:#e8e6e1;border:1px solid #1f1f24;border-radius:10px;padding:12px">
   <option>PDF</option><option>ZIP</option><option>HTML</option>
  </select>
  <label style="display:inline-flex;align-items:center;gap:8px;color:#97948c">
   <input type="checkbox" id="dbg"> حالت دیباگ (مربع رنگی دور هر حباب)</label>
  <label style="display:inline-flex;align-items:center;gap:8px;color:#97948c">
   <input type="checkbox" id="fake" checked> بدون ترجمه (تست موتور)</label>
 </div>
</div>

<button id="run" class="primary" style="width:100%%;padding:15px;border-radius:14px;border:none;font-size:1.1rem;font-weight:700;background:linear-gradient(160deg,#ff4a3d,#c9271c);color:#fff">▶ شروع ترجمه</button>

<pre id="log" style="background:#08080a;color:#e8e6e1;border:1px solid #1f1f24;border-radius:12px;padding:14px;white-space:pre-wrap;max-height:38vh;overflow:auto;direction:ltr;text-align:left;font-size:12px"></pre>
<div id="out"></div>
<div class="credit"><a href="https://github.com/amirwolf512k/Manga-AutoTranslate">سورس — amirwolf512k</a></div>

<script>
async function start(){
  const run=document.getElementById('run'); run.disabled=true; run.textContent='⏳ در حال ارسال…';
  const fd=new FormData();
  const f=document.getElementById('f').files[0];
  if(f) fd.append('file', f);
  fd.append('url', document.getElementById('url').value);
  fd.append('provider', document.getElementById('provider').value);
  fd.append('keys', document.getElementById('keys').value);
  const lang=document.querySelector('input[name=ocr_lang]:checked');
  fd.append('ocr_lang', lang? lang.value : 'en');
  fd.append('fmt', document.getElementById('fmt').value);
  fd.append('debug', document.getElementById('dbg').checked);
  fd.append('fake', document.getElementById('fake').checked);
  const r=await fetch('/api/start',{method:'POST',body:fd});
  const j=await r.json();
  poll(j.sid);
  run.textContent='▶ شروع ترجمه'; run.disabled=false;
}
function poll(sid){
  fetch('/api/status?sid='+sid).then(r=>r.json()).then(j=>{
    document.getElementById('log').textContent=j.log||'';
    const out=document.getElementById('out');
    if(j.done){
      let h='';
      if(j.images) for(const u of j.images) h+='<img src="'+u+'" style="width:100%%;margin:6px 0;border-radius:10px">';
      if(j.debug_images) h+='<div style="color:#97948c;margin-top:8px">🔍 دیباگ:</div>';
      if(j.debug_images) for(const u of j.debug_images) h+='<img src="'+u+'" style="width:100%%;margin:6px 0;border-radius:10px;outline:1px solid #1f1f24">';
      if(j.download) h+='<a href="'+j.download+'" download style="color:#ff4a3d">⬇ دانلود خروجی</a>';
      out.innerHTML=h;
    } else setTimeout(()=>poll(sid), 1500);
  }).catch(()=>setTimeout(()=>poll(sid),2000));
}
document.getElementById('run').onclick=start;
</script></body></html>"""


def _providers_html():
    return "".join('<option>%s</option>' % p for p in PROVIDERS)


def _save_upload(handler, dest):
    ctype = handler.headers.get("Content-Type", "")
    if "multipart/form-data" not in ctype:
        return None
    m = re.search(r'boundary=(.+)', ctype)
    if not m:
        return None
    boundary = m.group(1).encode()
    length = int(handler.headers.get("Content-Length", "0"))
    body = handler.rfile.read(length)
    fields = {}
    parts = body.split(b"--" + boundary)
    for part in parts:
        if b"\r\n\r\n" not in part:
            continue
        head, _, data = part.partition(b"\r\n\r\n")
        data = data.rsplit(b"\r\n", 1)[0]
        mh = head.decode("utf-8", "replace")
        nm = re.search(r'name="([^"]+)"', mh)
        fn = re.search(r'filename="([^"]*)"', mh)
        if not nm:
            continue
        if fn and fn.group(1):
            safe = os.path.basename(fn.group(1).replace("\\", "/"))
            path = os.path.join(dest, safe or "upload.bin")
            with open(path, "wb") as f:
                f.write(data)
            fields[nm.group(1)] = path
        else:
            fields[nm.group(1)] = data.decode("utf-8", "replace")
    return fields


def _run_job(sid, cfg):
    job = JOBS[sid]
    log = job["log"]
    try:
        log("▶ شروع…")
        os.makedirs(cfg["out"], exist_ok=True)
        import io as _io
        import contextlib
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            tr = manga.MangaTranslator(
                input_path=cfg["src"], output_dir=cfg["out"],
                provider=cfg["provider"], api_key=cfg["keys"],
                font_path=manga.find_font() or "Vazirmatn-Bold.ttf",
                ocr_langs=cfg["langs"], debug=cfg["debug"], gpu=False,
                fake_translate=cfg["fake"], no_resume=True,
            )
            tr.process()
        txt = buf.getvalue()
        log(txt[-8000:] if txt else "(بدون خروجی)")
        imgs, dbg_imgs, dl = [], [], None
        for root, _dirs, files in os.walk(cfg["out"]):
            for f in sorted(files):
                p = os.path.join(root, f)
                if f.startswith("page") and f.lower().endswith((".jpg", ".png", ".webp")):
                    (dbg_imgs if "debug" in f.lower() else imgs).append("/file?sid=%s&p=%s" % (sid, p))
                elif f.lower().endswith((".pdf", ".zip", ".html")):
                    dl = "/file?sid=%s&p=%s" % (sid, p)
        with LOCK:
            job["images"] = imgs
            job["debug_images"] = dbg_imgs
            job["download"] = dl
            job["done"] = True
        log("✅ تمام شد")
    except Exception:
        log("❌ خطا:\n" + traceback.format_exc()[-3000:])
        with LOCK:
            job["done"] = True


class Handler(BaseHTTPRequestHandler):
    server_version = "MangaApp/1.5"

    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            html = PAGE % dict(css=WEB_CSS, providers=_providers_html(),
                               langs=_bubbles_html())
            self._send(200, html.encode())
        elif self.path.startswith("/api/status"):
            sid = self.path.split("sid=")[-1].split("&")[0]
            with LOCK:
                job = JOBS.get(sid, {})
                self._send(200, json.dumps({
                    "log": job.get("log_txt", "…"),
                    "done": job.get("done", False),
                    "images": job.get("images", []),
                    "debug_images": job.get("debug_images", []),
                    "download": job.get("download"),
                }, ensure_ascii=False).encode())
        elif self.path.startswith("/file?"):
            q = dict(p.split("=", 1) for p in self.path.split("?")[1].split("&") if "=" in p)
            p = q.get("p", "").replace("%2F", "/")
            sid = q.get("sid", "")
            p = re.sub(r"[^\w\-./ \\:\u0600-\u06FF]", "_", p)
            if os.path.isfile(p) and sid in JOBS:
                ctype = ("image/jpeg" if p.lower().endswith((".jpg", ".jpeg"))
                         else "application/pdf" if p.lower().endswith(".pdf")
                         else "application/zip" if p.lower().endswith(".zip")
                         else "application/octet-stream")
                with open(p, "rb") as f:
                    self._send(200, f.read(), ctype)
            else:
                self._send(404, b"not found", "text/plain")
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self):
        if self.path != "/api/start":
            return self._send(404, b"not found", "text/plain")
        work = os.path.join(os.environ.get("MANGA_FILES_DIR", os.getcwd()), "work", "input")
        os.makedirs(work, exist_ok=True)
        fields = _save_upload(self, work) or {}
        sid = str(int(time.time() * 1000))
        src = fields.get("file") or fields.get("url") or ""
        cfg = {
            "src": src,
            "out": os.path.join(os.environ.get("MANGA_FILES_DIR", os.getcwd()), "work", "out", sid),
            "provider": fields.get("provider", "gemini"),
            "keys": ",".join(k for k in (fields.get("keys") or "").split(",") if k.strip()),
            "langs": [x for x in (fields.get("ocr_lang") or "en").split()],
            "debug": fields.get("debug") == "true",
            "fake": fields.get("fake") == "true",
        }
        with LOCK:
            job = JOBS[sid] = {"done": False, "log_txt": "در صف…", "images": [],
                               "debug_images": [], "download": None}

        def log(msg):
            with LOCK:
                job["log_txt"] = str(job.get("log_txt", "")) + "\n" + str(msg)

        threading.Thread(target=_run_job, args=(sid, cfg), daemon=True).start()
        self._send(200, json.dumps({"sid": sid}).encode(), "application/json")


def serve_forever(files_dir, port=8080):
    os.environ["MANGA_FILES_DIR"] = files_dir
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    httpd.serve_forever()
