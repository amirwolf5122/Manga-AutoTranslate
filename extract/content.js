(function () {
  'use strict'
  if (window.top !== window) return

  const TAB = { id: -1 }
  let recording = false
  let enabled = false
  let gathered = null
  let picked = new Set()
  let cancelFlag = false
  let selUI = null

  const DATA_ATTS = ['data-src', 'data-lazy-src', 'data-original', 'data-original-src',
    'data-orig-src', 'data-lazy', 'data-url', 'data-image', 'data-echo', 'data-asurl',
    'data-cfsrc', 'data-hi-res-src', 'data-full-src', 'data-full_image',
    'data-large-src', 'data-file', 'data-path', 'data-actualsrc']

  function bg(msg, timeout) {
    return new Promise(function (resolve, reject) {
      let settled = false
      const t = setTimeout(function () {
        if (settled) return
        settled = true
        reject(new Error('timeout'))
      }, timeout || 20000)
      try {
        chrome.runtime.sendMessage(msg, function (r) {
          if (settled) return
          settled = true
          clearTimeout(t)
          const err = chrome.runtime.lastError
          if (err) reject(new Error(err.message || 'error'))
          else resolve(r)
        })
      } catch (err) {
        clearTimeout(t)
        if (!settled) { settled = true; reject(err) }
      }
    })
  }

  function waitPage(eventName, match, timeout) {
    return new Promise(function (resolve) {
      let done = false
      const onMsg = function (ev) {
        if (ev.source !== window) return
        const d = ev.data
        if (!d || d.MT_EV !== eventName) return
        if (match && !match(d)) return
        done = true
        window.removeEventListener('message', onMsg)
        resolve(d)
      }
      window.addEventListener('message', onMsg)
      setTimeout(function () {
        if (done) return
        window.removeEventListener('message', onMsg)
        resolve(null)
      }, timeout)
    })
  }

  function decodeProxy(url) {
    try {
      let u = String(url)
      for (let i = 0; i < 3; i++) {
        const q = u.indexOf('?')
        if (q < 0) break
        if (!/[?&](url|src|img|image|target|link)=/i.test(u)) break
        const params = new URLSearchParams(u.slice(q + 1))
        let inner = ''
        for (const name of ['url', 'src', 'img', 'image', 'target', 'link']) {
          inner = inner || params.get(name) || ''
        }
        if (!inner) break
        let dec = inner
        for (let j = 0; j < 3; j++) {
          if (/%2[fF]|%3[aA]/i.test(dec)) {
            try { dec = decodeURIComponent(dec) } catch (err) { break }
          } else break
        }
        if (!/^https?:\/\//i.test(dec)) break
        u = dec
      }
      return u
    } catch (err) { return url }
  }

  function qsz(u) {
    try {
      const m = String(u).match(/[?&](?:type|size|w|h|width|height)=(f?)(\d{1,4})(?:[_x](\d{1,4}))?/i)
      if (!m) return 0
      const a = parseInt(m[2], 10) || 0
      const b = parseInt(m[3] || '0', 10) || 0
      if (a > 0 && b > 0) return Math.max(a, b)
      if (m[1] && a > 0) return a
      return 0
    } catch (err) { return 0 }
  }

  function junk(u) {
    if (!u) return true
    u = String(u)
    if (u.indexOf('data:') === 0) return true
    if (!/^https?:/i.test(u) && u.indexOf('blob:') !== 0) return true
    const b = u.split(/[?#]/)[0]
    if (/\.(svg|ico|gif|css|js|mjs|json|html?|xml|txt|pdf|zip|rar|7z|gz|mp4|webm|mp3|m4a|ogg|wav|woff2?|ttf|otf|eot|map)$/i.test(b)) return true
    if (/[-_]\d{2,4}x\d{2,4}\.(jpe?g|png|webp|avif)$/i.test(b)) return true
    if (/\/\d{2,4}x\d{2,4}\//i.test(b)) return true
    if (/(login|signin|signup|register|servicelogin|oauth)/i.test(b)) return true
    const q = qsz(u)
    if (q > 0 && q <= 400) return true
    if (/(logo|icon|avatar|banner|sprite|favicon|badge|flag|button|emoji|thumb(nail)?s?|placeholder|blank|spacer|transparen|loading|spinner|pixel|profile|rating|share|follow|comment|credits)/i.test(b)) return true
    if (/(?:^|[^a-z0-9])ads?[._\/-]/i.test(b)) return true
    if (/\/(covers?|thumbs?|thumbnails?|avatars?|banners?|creatives?|gifs?|decorations?|emojis?|smileys?|stickers?)\//i.test(b)) return true
    if (/(default|anon|guest|blank)[-_]?(pp|avatar|user|profile|image)/i.test(b)) return true
    if (/(pubadx|adservice|adserver|doubleclick|adnxs|propellerads?|onclck|adcash|adsterra|hilltopads?|clickadu|sovrn|taboola|outbrain|zedo|buysellads?|sharethrough|smartadserver|openx|rubicon|criteo|pubmatic|media\.net)/i.test(b)) return true
    return false
  }

  function keyOf(u) {
    const s = String(u)
    const b = s.split(/[?#]/)[0]
    if (!/\.(jpe?g|png|webp|avif|bmp|tiff?)$/i.test(b)) return s.split('#')[0]
    return b.replace(/[-_]\d{2,4}x\d{2,4}\./i, '.')
  }

  function absUrl(u) {
    try { const a = document.createElement('a'); a.href = u; return a.href } catch (err) { return '' }
  }

  function bestSrcset(ss) {
    try {
      const parts = String(ss).split(',')
      let best = '', bw = -1
      for (let k = 0; k < parts.length; k++) {
        const tk = parts[k].trim().split(/\s+/)
        const u0 = tk[0] || ''
        const w0 = parseInt(String(tk[1] || '').replace(/[^0-9]/g, ''), 10) || 0
        if (u0 && w0 >= bw) { bw = w0; best = u0 }
      }
      return best
    } catch (err) { return '' }
  }

  function domPass() {
    const out = []
    const add = function (u) {
      try {
        if (!u) return
        u = String(u).trim()
        if (u.indexOf('data:') === 0) return
        if (u.indexOf('blob:') === 0) { out.push(u.split('#')[0]); return }
        if (!/^https?:/i.test(u)) u = absUrl(u)
        if (u && /^https?:/i.test(u)) out.push(u)
      } catch (err) {}
    }
    let els = []
    try { els = document.querySelectorAll('img,source,a[href],[style*="url("]') } catch (err) {}
    for (let i = 0; i < els.length; i++) {
      const el = els[i]
      const tg = el.tagName
      if (tg === 'A') {
        try {
          const h = el.getAttribute('href') || ''
          if (/^https?:/i.test(h) && /\.(jpe?g|png|webp|avif|bmp)([?#]|$)/i.test(h)) add(h)
        } catch (err) {}
        continue
      }
      if (tg !== 'IMG' && tg !== 'SOURCE') {
        try {
          const mm = String(el.getAttribute('style') || '').match(/url\((['"]?)([^'")]+)\1\)/i)
          if (mm && mm[2]) add(mm[2])
        } catch (err) {}
        continue
      }
      let nw = 0, nh = 0, loaded = false
      try {
        loaded = !!(el.complete && el.naturalWidth > 0)
        nw = el.naturalWidth || 0
        nh = el.naturalHeight || 0
      } catch (err) {}
      let u = ''
      try { u = el.currentSrc || el.src || '' } catch (err) {}
      if (u && u.indexOf('data:') === 0) u = ''
      if (u && loaded && nw && nh && Math.max(nw, nh) < 300) u = ''
      if (u) add(u)
      try {
        const ss = el.getAttribute('srcset') || el.getAttribute('data-srcset')
        if (ss) { const bs = bestSrcset(ss); if (bs) add(bs) }
      } catch (err) {}
      for (let j = 0; j < DATA_ATTS.length; j++) {
        try {
          const v = el.getAttribute(DATA_ATTS[j])
          if (v && v.length > 4) add(v)
        } catch (err) {}
      }
    }
    return out
  }

  function perfPass() {
    const out = []
    try {
      const rs = performance.getEntriesByType('resource')
      for (let i = 0; i < rs.length; i++) {
        const en = rs[i] || {}
        const n = String(en.name || '')
        if (!n) continue
        const b = n.split(/[?#]/)[0]
        const t = String(en.initiatorType || '')
        if (/\.(jpe?g|png|webp|avif|bmp|tiff?)$/i.test(b)) { out.push(n); continue }
        if (t === 'img') out.push(n)
        else if (t === 'fetch' || t === 'xmlhttprequest' || t === 'other') {
          if (/\.(jpe?g|png|webp|avif|bmp|tiff?)([?#]|$)/i.test(n)) out.push(n)
        }
      }
    } catch (err) {}
    return out
  }

  function scriptScan() {
    const out = []
    try {
      const sc = document.querySelectorAll('script')
      const re = /https?:\\?\/\\?\/[^"'\s\\<>()[\]]+?\.(?:jpe?g|png|webp|avif|bmp)(?:\?[^"'\\\s<>()[\]]*)?/gi
      let m, guard = 0
      for (let i = 0; i < sc.length && guard < 800; i++) {
        let txt = ''
        try { txt = sc[i].textContent || '' } catch (err) { continue }
        if (!txt || txt.length < 10) continue
        re.lastIndex = 0
        while ((m = re.exec(txt)) && guard < 800) {
          guard++
          out.push(m[0].replace(/\\\//g, '/'))
        }
      }
    } catch (err) {}
    return out
  }

  function makeItem(fetchUrl, disp, kind, size, ref) {
    const it = { fetch: fetchUrl, show: disp, kind: kind, size: size || 0, folder: '', name: '', ext: '', num: 0, r: ref || '' }
    if (kind === 'blob') {
      it.folder = 'blob'
      it.name = 'page-image'
      return it
    }
    try {
      const u = new URL(disp)
      const segs = u.pathname.split('/').filter(Boolean)
      const base = segs.pop() || 'image'
      const m = String(base).match(/\.([a-z0-9]{2,5})$/i)
      if (m) it.ext = m[1].toLowerCase()
      if (it.ext === 'gif') return null
      it.name = base
      it.folder = u.hostname + (segs.length ? '/' + segs.join('/') : '')
    } catch (err) {
      it.folder = 'misc'
      it.name = 'image'
    }
    return it
  }

  async function hookNet() {
    try {
      const p = waitPage('net', null, 1500)
      window.postMessage({ MT_CMD: 'net' }, '*')
      const d = await p
      return d ? (d.urls || []) : []
    } catch (err) { return [] }
  }

  async function hookBlobKeys() {
    try {
      const p = waitPage('blobKeys', null, 1500)
      window.postMessage({ MT_CMD: 'blobKeys' }, '*')
      const d = await p
      return d ? (d.keys || []) : []
    } catch (err) { return [] }
  }

  async function gather() {
    let netItems = []
    try {
      const r = await bg({ type: 'MT_GET', tab: TAB.id }, 6000)
      netItems = (r && r.items) || []
    } catch (err) {}
    const netUrls = await hookNet()
    const blobKeys = await hookBlobKeys()
    const domUrls = domPass()
    const perfUrls = perfPass()
    const seen = new Set()
    const items = []
    const put = function (fetchUrl, showUrl, kind, size, ref) {
      const disp = showUrl || fetchUrl
      if (!disp) return
      const k = keyOf(disp)
      if (seen.has(k)) return
      seen.add(k)
      const it = makeItem(fetchUrl, disp, kind, size, ref)
      if (it) items.push(it)
    }
    for (let i = 0; i < domUrls.length; i++) {
      const u = domUrls[i]
      if (u.indexOf('blob:') === 0) { put(u, u, 'blob', 0, location.href); continue }
      const dec = decodeProxy(u)
      if (junk(dec)) continue
      put(u, dec, 'net', 0, location.href)
    }
    for (let i = 0; i < netItems.length; i++) put(netItems[i].u, netItems[i].d, 'net', netItems[i].s, netItems[i].r)
    for (let i = 0; i < perfUrls.length; i++) {
      const u = perfUrls[i]
      if (u.indexOf('blob:') === 0) { put(u, u, 'blob', 0, location.href); continue }
      const dec = decodeProxy(u)
      if (junk(dec)) continue
      put(u, dec, 'net', 0, location.href)
    }
    for (let i = 0; i < netUrls.length; i++) {
      const u = netUrls[i]
      if (u.indexOf('blob:') === 0) { put(u, u, 'blob', 0, location.href); continue }
      const dec = decodeProxy(u)
      if (junk(dec)) continue
      put(u, dec, 'net', 0, location.href)
    }
    if (!items.length) {
      const sc = scriptScan()
      for (let i = 0; i < sc.length; i++) {
        const dec = decodeProxy(sc[i])
        if (junk(dec)) continue
        put(sc[i], dec, 'net', 0, location.href)
      }
    }
    for (let i = 0; i < blobKeys.length; i++) put(blobKeys[i].url, blobKeys[i].url, 'blob', blobKeys[i].size)
    const blobSizes = {}
    for (let i = 0; i < blobKeys.length; i++) blobSizes[blobKeys[i].url] = blobKeys[i].size
    const netSizes = new Set()
    for (let i = 0; i < items.length; i++) {
      const it = items[i]
      if (it.kind === 'net' && it.size > 0) netSizes.add(it.size)
    }
    if (netSizes.size) {
      const kept = []
      for (let i = 0; i < items.length; i++) {
        const it = items[i]
        if (it.kind === 'blob') {
          if (!it.size) it.size = blobSizes[it.show] || 0
          if (it.size > 0 && netSizes.has(it.size)) continue
        }
        kept.push(it)
      }
      items.length = 0
      items.push.apply(items, kept)
    }
    for (let i = 0; i < items.length; i++) items[i].num = i + 1
    return items
  }

  const host = document.createElement('div')
  host.id = 'manga-autoextract'
  host.style.cssText = 'all:initial;position:fixed;top:0;left:0;right:0;bottom:0;pointer-events:none;z-index:2147483647'
  const root = host.attachShadow({ mode: 'open' })
  root.innerHTML = '<style>' +
    ':host{all:initial}' +
    '*{box-sizing:border-box;font-family:Tahoma,"Segoe UI",system-ui,sans-serif}' +
    '.mtfab{position:fixed;z-index:2147483647;bottom:calc(16px + env(safe-area-inset-bottom,0px));right:16px;height:46px;display:flex;align-items:center;gap:8px;padding:0 16px;border-radius:23px;background:#111117;border:1px solid rgba(245,158,11,.55);color:#f5f5f7;font-size:14px;font-weight:bold;cursor:pointer;box-shadow:0 4px 18px rgba(0,0,0,.45);user-select:none;-webkit-user-select:none;touch-action:none;direction:rtl;pointer-events:auto}' +
    '.mtfab:active{transform:scale(.96)}' +
    '.mtdot{width:10px;height:10px;border-radius:50%;background:#8a8a93;flex:0 0 auto}' +
    '.mtfab.mtrec .mtdot{background:#ef4444;animation:mtpulse 1.1s infinite}' +
    '@keyframes mtpulse{0%{box-shadow:0 0 0 0 rgba(239,68,68,.55)}70%{box-shadow:0 0 0 9px rgba(239,68,68,0)}100%{box-shadow:0 0 0 0 rgba(239,68,68,0)}}' +
    '.mtbadge{min-width:20px;height:20px;padding:0 6px;border-radius:10px;background:#f59e0b;color:#141417;font-size:12px;font-weight:bold;display:none;align-items:center;justify-content:center;flex:0 0 auto}' +
    '.mtmenu{position:fixed;z-index:2147483647;bottom:calc(70px + env(safe-area-inset-bottom,0px));right:16px;background:#13131a;border:1px solid #2c2c38;border-radius:12px;padding:6px;min-width:230px;display:none;flex-direction:column;gap:2px;direction:rtl;box-shadow:0 10px 30px rgba(0,0,0,.5);pointer-events:auto}' +
    '.mtmenu.mtopen{display:flex}' +
    '.mtmenu button{all:unset;box-sizing:border-box;display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:8px;color:#e8e8ec;font-size:14px;cursor:pointer;font-family:inherit;font-weight:bold}' +
    '.mtmenu button:hover{background:rgba(245,158,11,.14)}' +
    '.mtmenu button.mtdanger{color:#ef4444}' +
    '.mtmenu .mtsep{height:1px;background:#2c2c38;margin:4px 6px}' +
    '.mtpanel{position:fixed;z-index:2147483647;inset:10px;max-width:860px;margin:0 auto;background:#0f0f15;border:1px solid #2c2c38;border-radius:14px;display:none;flex-direction:column;direction:rtl;color:#e8e8ec;box-shadow:0 16px 50px rgba(0,0,0,.6);overflow:hidden;pointer-events:auto}' +
    '.mtpanel.mtopen{display:flex}' +
    '@media(min-width:700px){.mtpanel{inset:40px 24px}}' +
    '.mtphead{display:flex;align-items:center;gap:8px;padding:12px 14px;border-bottom:1px solid #23232e;flex-wrap:wrap}' +
    '.mtphead h3{margin:0;font-size:15px;color:#fff;flex:1;min-width:140px}' +
    '.mtselcnt{font-size:12px;color:#fbbf24;font-weight:bold;flex:0 0 auto;white-space:nowrap}' +
    '.mtbtn{all:unset;box-sizing:border-box;padding:8px 14px;border-radius:8px;font-size:13px;font-weight:bold;cursor:pointer;font-family:inherit;display:flex;align-items:center;gap:6px;color:#d4d4dc}' +
    '.mtbtn.mtmain{background:#f59e0b;color:#141417}' +
    '.mtbtn.mtmain:hover{background:#fbbf24}' +
    '.mtbtn.mtghost{border:1px solid #3a3a48}' +
    '.mtbtn.mtghost:hover{background:rgba(245,158,11,.1)}' +
    '.mtpbody{flex:1;overflow-y:auto;padding:8px 10px;scrollbar-width:thin;scrollbar-color:#3a3a48 transparent;min-height:0}' +
    '.mtpbody::-webkit-scrollbar{width:8px}' +
    '.mtpbody::-webkit-scrollbar-thumb{background:#3a3a48;border-radius:4px}' +
    '.mtgrp{margin:8px 0}' +
    '.mtgh{display:flex;align-items:center;gap:8px;padding:8px 10px;background:#181820;border-radius:8px;position:sticky;top:0;z-index:1}' +
    '.mtchk{width:18px;height:18px;accent-color:#f59e0b;flex:0 0 auto;cursor:pointer;margin:0}' +
    '.mtgh .mtfold{flex:1;min-width:0;font-size:11px;font-family:Consolas,monospace;color:#fbbf24;direction:ltr;text-align:left;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}' +
    '.mtgh .mtcnt{font-size:11px;color:#9a9aa5;flex:0 0 auto}' +
    '.mtgh .mtgcopy{all:unset;box-sizing:border-box;font-size:11px;font-weight:bold;color:#f59e0b;padding:3px 10px;border:1px solid rgba(245,158,11,.4);border-radius:6px;cursor:pointer;font-family:inherit;flex:0 0 auto}' +
    '.mtgh .mtgcopy:hover{background:rgba(245,158,11,.15)}' +
    '.mtrow{display:flex;align-items:center;gap:10px;padding:6px 8px;border-radius:8px;cursor:pointer}' +
    '.mtrow:hover{background:rgba(255,255,255,.05)}' +
    '.mtnum{width:30px;text-align:center;font-family:Consolas,monospace;font-size:13px;color:#f59e0b;flex:0 0 auto}' +
    '.mtthumb{width:44px;height:62px;border-radius:6px;background:#1c1c25;object-fit:cover;flex:0 0 auto}' +
    '.mtmeta{flex:1;min-width:0;display:flex;flex-direction:column;gap:2px}' +
    '.mtfn{font-size:12px;color:#e8e8ec;word-break:break-all}' +
    '.mtln{font-size:10.5px;font-family:Consolas,monospace;color:#8f8f9b;word-break:break-all;direction:ltr;text-align:left;user-select:all;-webkit-user-select:all}' +
    '.mttag{font-size:10px;background:rgba(245,158,11,.18);color:#fbbf24;border-radius:4px;padding:2px 6px;flex:0 0 auto}' +
    '.mttext{display:none;margin:10px;padding:10px;background:#0a0a0f;border:1px solid #23232e;border-radius:8px;width:calc(100% - 20px);height:34vh;min-height:160px;font-family:Consolas,monospace;font-size:11px;color:#c8c8d0;direction:ltr;text-align:left;resize:vertical;pointer-events:auto}' +
    '.mttext.mtopen{display:block}' +
    '.mtprog{position:fixed;z-index:2147483647;inset:0;background:rgba(4,4,8,.84);display:none;align-items:center;justify-content:center;direction:rtl;pointer-events:auto}' +
    '.mtprog.mtopen{display:flex}' +
    '.mtprogcard{width:min(430px,92vw);max-height:88vh;overflow-y:auto;background:#12121a;border:1px solid #2c2c38;border-radius:14px;padding:20px;display:flex;flex-direction:column;gap:14px;color:#e8e8ec}' +
    '.mtptitle{font-size:15px;font-weight:bold;color:#fff}' +
    '.mtpcur{font-size:11px;font-family:Consolas,monospace;color:#9a9aa5;direction:ltr;text-align:left;word-break:break-all;min-height:16px}' +
    '.mtbarwrap{height:10px;background:#1c1c25;border-radius:5px;overflow:hidden}' +
    '.mtbar{height:100%;width:0%;background:linear-gradient(90deg,#f59e0b,#fbbf24);border-radius:5px;transition:width .25s}' +
    '.mtpstat{font-size:13px;display:flex;justify-content:space-between;color:#c8c8d0}' +
    '.mtpstat b{color:#f59e0b}' +
    '.mtres{display:none;flex-direction:column;gap:10px}' +
    '.mtres.mtopen{display:flex}' +
    '.mtrespath{font-size:12px;font-family:Consolas,monospace;color:#fbbf24;direction:ltr;text-align:left;word-break:break-all;background:#0a0a0f;border:1px solid #23232e;border-radius:8px;padding:10px}' +
    '.mtresbtns{display:flex;gap:8px;flex-wrap:wrap}' +
    '.mtfailnote{display:none;font-size:12px;color:#fca5a5}' +
    '.mtfailnote.mtopen{display:block}' +
    '.mtview{position:fixed;z-index:2147483647;inset:0;background:rgba(0,0,0,.94);display:none;align-items:center;justify-content:center;flex-direction:column;gap:12px;direction:rtl;pointer-events:auto}' +
    '.mtview.mtopen{display:flex}' +
    '.mtview img{max-width:96vw;max-height:86vh;border-radius:6px;background:#111;display:none}' +
    '.mtview .mthint{color:#9a9aa5;font-size:12px}' +
    '.mtspin{width:34px;height:34px;border:3px solid #2c2c38;border-top-color:#f59e0b;border-radius:50%;animation:mtrot .8s linear infinite}' +
    '@keyframes mtrot{to{transform:rotate(360deg)}}' +
    '.mttoast{position:fixed;z-index:2147483647;bottom:calc(78px + env(safe-area-inset-bottom,0px));right:50%;transform:translateX(50%);background:#1b1b24;border:1px solid #343444;color:#e8e8ec;padding:10px 18px;border-radius:10px;font-size:13px;direction:rtl;display:none;max-width:88vw;text-align:center;pointer-events:auto}' +
    '.mttoast.mtopen{display:block}' +
    '</style>' +
    '<div class="mtfab" style="display:none"><span class="mtdot"></span><span class="mtlabel">استخراج</span><span class="mtbadge">0</span></div>' +
    '<div class="mtmenu">' +
    '<button data-mt="ext">استخراج</button>' +
    '<div class="mtsep"></div>' +
    '<button data-mt="stop" class="mtdanger">متوقف ضبط</button>' +
    '</div>' +
    '<div class="mtpanel">' +
    '<div class="mtphead">' +
    '<h3 class="mttitle">عکس‌های ضبط‌شده</h3>' +
    '<span class="mtselcnt"></span>' +
    '<button class="mtbtn mtghost" data-mt="selall">همه</button>' +
    '<button class="mtbtn mtghost" data-mt="selnone">هیچ</button>' +
    '<button class="mtbtn mtmain" data-mt="copyall">کپی لینک‌ها</button>' +
    '<button class="mtbtn mtghost" data-mt="dlzip">دانلود ZIP</button>' +
    '<button class="mtbtn mtghost" data-mt="showtext">نمایش متنی</button>' +
    '<button class="mtbtn mtghost" data-mt="closepanel">بستن</button>' +
    '</div>' +
    '<div class="mtpbody"></div>' +
    '<textarea class="mttext" readonly spellcheck="false"></textarea>' +
    '</div>' +
    '<div class="mtprog"><div class="mtprogcard">' +
    '<div class="mtptitle">در حال دانلود عکس‌ها</div>' +
    '<div class="mtbarwrap"><div class="mtbar"></div></div>' +
    '<div class="mtpcur"></div>' +
    '<div class="mtpstat"><span class="mtok">0 موفق</span><span class="mtfail">0 ناموفق</span></div>' +
    '<div class="mtresbtns"><button class="mtbtn mtghost" data-mt="cancel">لغو</button></div>' +
    '<div class="mtres">' +
    '<div class="mtrespath"></div>' +
    '<div class="mtfailnote"></div>' +
    '<div class="mtresbtns">' +
    '<button class="mtbtn mtmain" data-mt="copypath">کپی مسیر</button>' +
    '<button class="mtbtn mtghost" data-mt="copylinks">کپی همهٔ لینک‌ها</button>' +
    '<button class="mtbtn mtghost" data-mt="copyfails">کپی لینک‌های ناموفق</button>' +
    '<button class="mtbtn mtghost" data-mt="resclose">بستن</button>' +
    '</div>' +
    '</div>' +
    '</div></div>' +
    '<div class="mtview"><div class="mtspin"></div><img alt=""><div class="mthint">برای بستن کلیک یا لمس کن</div></div>' +
    '<div class="mttoast"></div>'
  document.documentElement.appendChild(host)

  const fab = root.querySelector('.mtfab')
  const fabLabel = root.querySelector('.mtlabel')
  const fabBadge = root.querySelector('.mtbadge')
  const menu = root.querySelector('.mtmenu')
  const panel = root.querySelector('.mtpanel')
  const panelTitle = root.querySelector('.mttitle')
  const panelSelCnt = root.querySelector('.mtselcnt')
  const panelBody = root.querySelector('.mtpbody')
  const panelText = root.querySelector('.mttext')
  const prog = root.querySelector('.mtprog')
  const progTitle = root.querySelector('.mtptitle')
  const progBar = root.querySelector('.mtbar')
  const progCur = root.querySelector('.mtpcur')
  const progOk = root.querySelector('.mtok')
  const progFail = root.querySelector('.mtfail')
  const progRes = root.querySelector('.mtres')
  const progResPath = root.querySelector('.mtrespath')
  const progFailNote = root.querySelector('.mtfailnote')
  const view = root.querySelector('.mtview')
  const viewImg = root.querySelector('.mtview img')
  const viewSpin = root.querySelector('.mtspin')
  const toastEl = root.querySelector('.mttoast')

  let toastTimer = null
  function toast(msg) {
    toastEl.textContent = msg
    toastEl.classList.add('mtopen')
    if (toastTimer) clearTimeout(toastTimer)
    toastTimer = setTimeout(function () { toastEl.classList.remove('mtopen') }, 3000)
  }

  async function copyText(t) {
    try { await navigator.clipboard.writeText(t); return true } catch (err) {}
    try {
      const ta = document.createElement('textarea')
      ta.value = t
      ta.style.cssText = 'position:fixed;left:-9999px;top:0;opacity:0'
      document.body.appendChild(ta)
      ta.focus()
      ta.select()
      const ok = document.execCommand('copy')
      ta.remove()
      return ok
    } catch (err) { return false }
  }

  function applyUI(count) {
    fab.style.display = enabled ? 'flex' : 'none'
    fab.classList.toggle('mtrec', recording)
    fabLabel.textContent = recording ? 'استخراج' : 'ضبط'
    const showBadge = recording && typeof count === 'number'
    fabBadge.style.display = showBadge ? 'flex' : 'none'
    fabBadge.textContent = String(count || 0)
    if (!recording) gathered = null
  }

  function setRec(on, count) {
    recording = !!on
    applyUI(on ? count : 0)
  }

  function closeMenu() { menu.classList.remove('mtopen') }
  function closePanel() { panel.classList.remove('mtopen') }
  function closeProg() { prog.classList.remove('mtopen') }
  function closeView() { view.classList.remove('mtopen') }

  let fabRight = 16
  try {
    const p = parseInt(localStorage.getItem('mtfabright') || '', 10)
    if (p >= 0) fabRight = p
  } catch (err) {}
  fab.style.right = fabRight + 'px'
  let dragging = false, dragMoved = false, dragStartX = 0, dragStartR = 0
  fab.addEventListener('pointerdown', function (e) {
    dragging = true
    dragMoved = false
    dragStartX = e.clientX
    dragStartR = fabRight
    try { fab.setPointerCapture(e.pointerId) } catch (err) {}
  })
  fab.addEventListener('pointermove', function (e) {
    if (!dragging) return
    const dx = e.clientX - dragStartX
    if (Math.abs(dx) > 12) dragMoved = true
    if (dragMoved) {
      fabRight = Math.min(Math.max(dragStartR - dx, 8), Math.max(window.innerWidth - 90, 8))
      fab.style.right = fabRight + 'px'
    }
  })
  fab.addEventListener('pointerup', function () {
    dragging = false
    if (dragMoved) {
      try { localStorage.setItem('mtfabright', String(fabRight)) } catch (err) {}
      return
    }
    onFabClick()
  })
  fab.addEventListener('pointercancel', function () { dragging = false })

  function onFabClick() {
    closeMenu()
    closePanel()
    if (!recording) {
      startRecording()
      return
    }
    gather().then(function (items) {
      if (!items.length) {
        toast('هیچ عکسی ضبط نشد — صفحه را اسکرول کن تا عکس‌ها لود شوند')
        return
      }
      gathered = items
      setRec(true, items.length)
      menu.classList.add('mtopen')
    })
  }

  async function startRecording() {
    try { await bg({ type: 'MT_START', tab: TAB.id }, 5000) } catch (err) {}
    enabled = true
    try { window.postMessage({ MT_CMD: 'clear' }, '*') } catch (err) {}
    setRec(true, 0)
    toast('ضبط شروع شد — صفحه بازخوانی می‌شود')
    setTimeout(function () { location.reload() }, 300)
  }

  async function stopRecording() {
    try { await bg({ type: 'MT_STOP', tab: TAB.id }, 5000) } catch (err) {}
    setRec(false, 0)
    closeMenu()
    closePanel()
    toast('ضبط متوقف شد — برای شروعِ تازه دکمهٔ ضبط را بزن')
  }

  async function enableExt() {
    try { await bg({ type: 'MT_ENABLE' }, 5000) } catch (err) {}
    enabled = true
    applyUI()
    toast('افزونه فعال شد — دکمهٔ ضبط پایین صفحه')
  }

  async function disableExt() {
    try { await bg({ type: 'MT_DISABLE' }, 5000) } catch (err) {}
    enabled = false
    setRec(false, 0)
    closeMenu()
    closePanel()
    closeProg()
    toast('افزونه خاموش شد')
  }

  menu.addEventListener('click', function (e) {
    const t = e.target && e.target.getAttribute && e.target.getAttribute('data-mt')
    if (!t) return
    closeMenu()
    if (t === 'ext' && gathered) showLinks(gathered)
    if (t === 'stop') stopRecording()
  })

  function getSel() {
    if (!gathered) return []
    const out = []
    for (let i = 0; i < gathered.length; i++) {
      if (picked.has(i)) out.push(gathered[i])
    }
    return out
  }

  function showLinks(items) {
    gathered = items
    picked = new Set()
    for (let i = 0; i < items.length; i++) picked.add(i)
    panelBody.textContent = ''
    panelText.value = items.map(function (it) { return it.show }).join('\n')
    panelText.classList.remove('mtopen')
    panelTitle.textContent = 'عکس‌های ضبط‌شده (' + items.length + ' عکس)'
    const groups = []
    const gmap = {}
    for (let i = 0; i < items.length; i++) {
      const it = items[i]
      if (!gmap[it.folder]) { gmap[it.folder] = []; groups.push(it.folder) }
      gmap[it.folder].push({ it: it, idx: i })
    }
    if (groups.length > Math.max(8, Math.floor(items.length * 0.6))) {
      const hmap = {}
      const hgroups = []
      for (let i = 0; i < items.length; i++) {
        const it = items[i]
        let h = it.folder
        if (it.folder !== 'blob' && it.folder !== 'misc') {
          h = it.folder.split('/')[0]
        }
        if (!hmap[h]) { hmap[h] = []; hgroups.push(h) }
        hmap[h].push({ it: it, idx: i })
      }
      groups.length = 0
      for (let g = 0; g < hgroups.length; g++) groups.push(hgroups[g])
      for (const k of Object.keys(gmap)) delete gmap[k]
      for (const k of Object.keys(hmap)) gmap[k] = hmap[k]
    }
    const groupRows = []
    const update = function () {
      let total = 0
      for (let g = 0; g < groupRows.length; g++) {
        const gr = groupRows[g]
        let n = 0
        for (let r = 0; r < gr.entries.length; r++) {
          const ent = gr.entries[r]
          const on = picked.has(ent.idx)
          if (ent.cb) ent.cb.checked = on
          if (on) n++
        }
        total += n
        gr.cnt.textContent = (n === gr.entries.length) ? (gr.entries.length + ' عکس') : (n + '/' + gr.entries.length)
        gr.cb.checked = n > 0 && n === gr.entries.length
        try { gr.cb.indeterminate = n > 0 && n < gr.entries.length } catch (err) {}
      }
      panelSelCnt.textContent = total + ' انتخاب‌شده'
      panelText.value = getSel().map(function (it) { return it.show }).join('\n')
    }
    for (let g = 0; g < groups.length; g++) {
      const folder = groups[g]
      const entries = gmap[folder]
      const grp = document.createElement('div')
      grp.className = 'mtgrp'
      const gh = document.createElement('div')
      gh.className = 'mtgh'
      const gcb = document.createElement('input')
      gcb.type = 'checkbox'
      gcb.className = 'mtchk'
      gcb.checked = true
      gcb.setAttribute('aria-label', 'انتخاب کل پوشه')
      gcb.addEventListener('click', function (ev) { ev.stopPropagation() })
      gcb.addEventListener('change', function () {
        for (let r = 0; r < entries.length; r++) {
          if (gcb.checked) picked.add(entries[r].idx)
          else picked.delete(entries[r].idx)
        }
        update()
      })
      const fold = document.createElement('span')
      fold.className = 'mtfold'
      fold.textContent = folder === 'blob' ? 'تصاویر درون صفحه (blob)' : folder
      const cnt = document.createElement('span')
      cnt.className = 'mtcnt'
      cnt.textContent = entries.length + ' عکس'
      const cp = document.createElement('button')
      cp.className = 'mtgcopy'
      cp.textContent = 'کپی'
      cp.addEventListener('click', function (ev) {
        ev.stopPropagation()
        const sel = []
        for (let r = 0; r < entries.length; r++) {
          if (picked.has(entries[r].idx)) sel.push(entries[r].it)
        }
        if (!sel.length) {
          toast('هیچ عکسی در این پوشه انتخاب نشده')
          return
        }
        const nb = sel.filter(function (it) { return it.kind === 'blob' }).length
        if (nb > 0) {
          toast('این عکس‌ها داخل مرورگر رمزگشایی شده‌اند (' + nb + ' عکس) — به‌جای لینک، خودکار دانلود می‌کنم')
          closePanel()
          startDownload(sel)
          return
        }
        copyText(sel.map(function (it) { return it.show }).join('\n')).then(function (ok) {
          toast(ok ? sel.length + ' لینک کپی شد' : 'کپی نشد — از حالت متنی کپی کن')
        })
      })
      gh.appendChild(gcb)
      gh.appendChild(fold)
      gh.appendChild(cnt)
      gh.appendChild(cp)
      grp.appendChild(gh)
      for (let r = 0; r < entries.length; r++) {
        const ent = entries[r]
        const it = ent.it
        const row = document.createElement('div')
        row.className = 'mtrow'
        const cb = document.createElement('input')
        cb.type = 'checkbox'
        cb.className = 'mtchk'
        cb.checked = true
        cb.setAttribute('aria-label', 'انتخاب عکس ' + it.num)
        cb.addEventListener('click', function (ev) { ev.stopPropagation() })
        cb.addEventListener('change', function () {
          if (cb.checked) picked.add(ent.idx)
          else picked.delete(ent.idx)
          update()
        })
        const num = document.createElement('span')
        num.className = 'mtnum'
        num.textContent = String(it.num)
        const th = document.createElement('img')
        th.className = 'mtthumb'
        th.loading = 'lazy'
        th.alt = ''
        th.referrerPolicy = 'no-referrer'
        th.addEventListener('error', function () {
          if (it.kind === 'blob' && !th.dataset.mtpull) {
            th.dataset.mtpull = '1'
            blobThumb(it).then(function (dd) {
              if (dd) { th.src = dd; th.style.visibility = '' }
              else th.style.visibility = 'hidden'
            })
            return
          }
          th.style.visibility = 'hidden'
        })
        th.src = it.show
        const meta = document.createElement('div')
        meta.className = 'mtmeta'
        const fn = document.createElement('div')
        fn.className = 'mtfn'
        fn.textContent = it.num + '.' + (it.ext || 'jpg') + (it.name && it.name.indexOf('.') < 0 ? ' (' + it.name + ')' : '')
        const ln = document.createElement('div')
        ln.className = 'mtln'
        ln.textContent = it.show
        meta.appendChild(fn)
        meta.appendChild(ln)
        row.appendChild(cb)
        row.appendChild(num)
        row.appendChild(th)
        row.appendChild(meta)
        if (it.kind === 'blob') {
          const tag = document.createElement('span')
          tag.className = 'mttag'
          tag.textContent = 'موقت'
          row.appendChild(tag)
        }
        row.addEventListener('click', function () { fullView(it) })
        grp.appendChild(row)
        ent.cb = cb
      }
      panelBody.appendChild(grp)
      groupRows.push({ cb: gcb, cnt: cnt, entries: entries })
    }
    selUI = {
      update: update,
      all: function () {
        picked = new Set()
        for (let i = 0; i < items.length; i++) picked.add(i)
        for (let g = 0; g < groupRows.length; g++) groupRows[g].cb.checked = true
        update()
      },
      none: function () {
        picked.clear()
        update()
      }
    }
    update()
    panel.classList.add('mtopen')
  }

  panel.addEventListener('click', function (e) {
    const t = e.target && e.target.getAttribute && e.target.getAttribute('data-mt')
    if (!t) return
    if (t === 'closepanel') closePanel()
    if (t === 'selall' && selUI) selUI.all()
    if (t === 'selnone' && selUI) selUI.none()
    if (t === 'copyall') {
      const sel = getSel()
      if (!sel.length) {
        toast('هیچ عکسی انتخاب نشد')
        return
      }
      const nb = sel.filter(function (it) { return it.kind === 'blob' }).length
      if (nb > 0) {
        toast('این سایت عکس‌ها را داخل مرورگر رمزگشایی می‌کند (' + nb + ' عکس) — به‌جای لینک، خودکار دانلود می‌کنم')
        closePanel()
        startDownload(sel)
        return
      }
      copyText(sel.map(function (it) { return it.show }).join('\n')).then(function (ok) {
        toast(ok ? sel.length + ' لینک کپی شد' : 'کپی نشد — از حالت متنی کپی کن')
      })
    }
    if (t === 'showtext') {
      panelText.classList.toggle('mtopen')
      if (panelText.classList.contains('mtopen')) {
        if (selUI) selUI.update()
        panelText.focus()
        panelText.select()
      }
    }
    if (t === 'dlzip') {
      const sel = getSel()
      if (!sel.length) {
        toast('هیچ عکسی انتخاب نشد')
        return
      }
      closePanel()
      startDownload(sel)
    }
  })

  function fullView(item) {
    viewImg.removeAttribute('src')
    viewImg.style.display = 'none'
    viewSpin.style.display = 'block'
    view.classList.add('mtopen')
    let stage = 0
    function giveUp() {
      viewSpin.style.display = 'none'
      toast('این سایت اجازهٔ نمایش مستقیم نمی‌دهد')
    }
    function toDataUrl(u8, ct) {
      let bin = ''
      const CH = 32768
      for (let i = 0; i < u8.length; i += CH) {
        bin += String.fromCharCode.apply(null, u8.subarray(i, i + CH))
      }
      return 'data:' + (ct || 'image/jpeg') + ';base64,' + btoa(bin)
    }
    viewImg.onload = function () {
      viewSpin.style.display = 'none'
      viewImg.style.display = 'block'
    }
    viewImg.onerror = function () {
      if (stage === 0) {
        stage = 1
        viewImg.referrerPolicy = 'no-referrer'
        viewImg.src = item.show
        return
      }
      if (stage === 1 && item.kind === 'blob') {
        stage = 2
        blobDataUrl(item).then(function (dd) {
          if (dd) { viewImg.src = dd; return }
          giveUp()
        })
        return
      }
      if (stage === 1 && item.kind !== 'blob') {
        stage = 2
        bg({ type: 'MT_FETCH', url: item.fetch, ref: item.r || (location.href || '') }, 60000).then(function (r) {
          if (r && r.b64) {
            viewImg.src = 'data:' + (r.ct || 'image/jpeg') + ';base64,' + r.b64
            return
          }
          return pageFetch(item.fetch).then(function (pf) {
            if (pf && pf.u8 && pf.u8.length) {
              viewImg.src = toDataUrl(pf.u8, pf.ct)
              return
            }
            giveUp()
          })
        }).catch(giveUp)
        return
      }
      giveUp()
    }
    viewImg.referrerPolicy = 'strict-origin-when-cross-origin'
    viewImg.src = item.show
  }

  view.addEventListener('click', function () { closeView() })

  function b64ToU8(b64) {
    const bin = atob(b64)
    const u8 = new Uint8Array(bin.length)
    for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i)
    return u8
  }

  const EXT_OK = ['jpg', 'jpeg', 'png', 'webp', 'avif', 'bmp', 'tiff', 'tif']

  function extFromType(ct) {
    const c = String(ct || '').toLowerCase()
    if (c.indexOf('jpeg') >= 0) return 'jpg'
    if (c.indexOf('png') >= 0) return 'png'
    if (c.indexOf('webp') >= 0) return 'webp'
    if (c.indexOf('avif') >= 0) return 'avif'
    if (c.indexOf('gif') >= 0) return 'gif'
    if (c.indexOf('bmp') >= 0) return 'bmp'
    return ''
  }

  function sniffExt(u8) {
    if (!u8 || u8.length < 12) return ''
    if (u8[0] === 0xFF && u8[1] === 0xD8 && u8[2] === 0xFF) return 'jpg'
    if (u8[0] === 0x89 && u8[1] === 0x50 && u8[2] === 0x4E && u8[3] === 0x47) return 'png'
    if (u8[0] === 0x47 && u8[1] === 0x49 && u8[2] === 0x46) return 'gif'
    if (u8[0] === 0x52 && u8[1] === 0x49 && u8[2] === 0x46 && u8[8] === 0x57 && u8[9] === 0x45 && u8[10] === 0x42 && u8[11] === 0x50) return 'webp'
    if (u8[4] === 0x66 && u8[5] === 0x74 && u8[6] === 0x79 && u8[7] === 0x70) return 'avif'
    if (u8[0] === 0x42 && u8[1] === 0x4D) return 'bmp'
    if ((u8[0] === 0x49 && u8[1] === 0x49 && u8[2] === 0x2A) || (u8[0] === 0x4D && u8[1] === 0x4D && u8[3] === 0x2A)) return 'tiff'
    if (u8[0] === 0x00 && u8[1] === 0x00 && u8[2] === 0x00 && u8[3] === 0x0C && u8[8] === 0x6A && u8[9] === 0x50) return 'jp2'
    return ''
  }

  function looksLikeJunk(u8, ct) {
    if (!u8 || !u8.length) return true
    if (u8.length < 2048) return true
    const c = String(ct || '').toLowerCase()
    if (/^text\/|json|html|xml/.test(c)) return true
    const e = sniffExt(u8)
    if (e) return false
    let texty = 0
    const n = Math.min(u8.length, 512)
    for (let i = 0; i < n; i++) {
      const b = u8[i]
      if (b === 9 || b === 10 || b === 13 || (b >= 32 && b < 127)) texty++
    }
    if (texty / n > 0.9) return true
    if (u8[0] === 0x3C || u8[0] === 0x7B) return true
    return false
  }

  function finalExt(item, ct, u8) {
    let e = String(item.ext || '').toLowerCase()
    if (e === 'jpeg') e = 'jpg'
    if (e === 'tif') e = 'tiff'
    if (EXT_OK.indexOf(e) < 0) e = ''
    if (!e) e = extFromType(ct)
    if (!e) e = sniffExt(u8)
    if (!e) e = 'jpg'
    return e
  }

  async function pageFetch(url) {
    try {
      const p = waitPage('pageFetch', function (d) { return d.url === url }, 25000)
      window.postMessage({ MT_CMD: 'pageFetch', url: url }, '*')
      const d = await p
      if (d && d.buf) return { u8: new Uint8Array(d.buf), ct: d.ct || '' }
    } catch (err) {}
    return null
  }

  async function csFetch(url) {
    try {
      let cross = true
      try { cross = new URL(url, location.href).origin !== location.origin } catch (err) {}
      const r = await fetch(url, cross ? { credentials: 'omit' } : { credentials: 'include' })
      if (!r || !r.ok) return null
      const ct = r.headers.get('content-type') || ''
      const buf = await r.arrayBuffer()
      if (!buf || !buf.byteLength) return null
      return { u8: new Uint8Array(buf), ct: ct }
    } catch (err) { return null }
  }

  function u8ToB64(u8) {
    let bin = ''
    const CH = 32768
    for (let i = 0; i < u8.length; i += CH) {
      bin += String.fromCharCode.apply(null, u8.subarray(i, i + CH))
    }
    return btoa(bin)
  }

  async function blobDataUrl(item) {
    try {
      const p = waitPage('blobData', function (d) { return d.url === item.show }, 20000)
      window.postMessage({ MT_CMD: 'pullBlobs', urls: [item.show] }, '*')
      const d = await p
      if (!d || d.buf == null) {
        if (d && d.err) return ''
        return ''
      }
      const u8 = new Uint8Array(d.buf)
      if (!u8.length || u8.length < 64) return ''
      const ct = (d.type && String(d.type).indexOf('image/') === 0) ? d.type : 'image/jpeg'
      return 'data:' + ct + ';base64,' + u8ToB64(u8)
    } catch (err) { return '' }
  }

  async function blobThumb(item) {
    try {
      const p = waitPage('blobData', function (d) { return d.url === item.show }, 20000)
      window.postMessage({ MT_CMD: 'pullBlobs', urls: [item.show] }, '*')
      const d = await p
      if (!d || !d.buf) return ''
      const u8 = new Uint8Array(d.buf)
      if (!u8.length || u8.length < 64) return ''
      const blob = new Blob([u8], { type: d.type || 'image/jpeg' })
      try {
        const bmp = await createImageBitmap(blob)
        const w = bmp.width || 96
        const h = bmp.height || 136
        const sc = Math.min(120 / w, 170 / h)
        const cv = document.createElement('canvas')
        cv.width = Math.max(1, Math.round(w * sc))
        cv.height = Math.max(1, Math.round(h * sc))
        cv.getContext('2d').drawImage(bmp, 0, 0, cv.width, cv.height)
        try { if (bmp.close) bmp.close() } catch (err2) {}
        const dd = cv.toDataURL('image/jpeg', 0.72)
        return dd && dd.indexOf('data:image') === 0 ? dd : ''
      } catch (err) {
        const ct = (d.type && String(d.type).indexOf('image/') === 0) ? d.type : 'image/jpeg'
        return 'data:' + ct + ';base64,' + u8ToB64(u8)
      }
    } catch (err) { return '' }
  }

  async function itemBytes(item) {
    if (item.kind === 'blob') {
      const p = waitPage('blobData', function (d) { return d.url === item.show }, 25000)
      window.postMessage({ MT_CMD: 'pullBlobs', urls: [item.show] }, '*')
      const d = await p
      if (d && d.buf) {
        const u8 = new Uint8Array(d.buf)
        if (!looksLikeJunk(u8, d.type || '')) return { u8: u8, ct: d.type || '' }
      }
      const pf = await pageFetch(item.show)
      if (pf && !looksLikeJunk(pf.u8, pf.ct)) return pf
      const cf = await csFetch(item.show)
      if (cf && !looksLikeJunk(cf.u8, cf.ct)) return cf
      return null
    }
    try {
      const r = await bg({ type: 'MT_FETCH', url: item.fetch, ref: item.r || (location.href || '') }, 90000)
      if (r && r.b64) {
        const u8 = b64ToU8(r.b64)
        if (!looksLikeJunk(u8, r.ct || '')) return { u8: u8, ct: r.ct || '' }
      }
    } catch (err) {}
    const pf = await pageFetch(item.fetch)
    if (pf && !looksLikeJunk(pf.u8, pf.ct)) return pf
    const cf = await csFetch(item.fetch)
    if (cf && !looksLikeJunk(cf.u8, cf.ct)) return cf
    return null
  }

  function zipName(count) {
    let hostName = 'site'
    let seg = 'images'
    try {
      hostName = (location.hostname || 'site').replace(/^www\./i, '').split('.')[0]
      const segs = location.pathname.split('/').filter(Boolean)
      if (segs.length) seg = segs[segs.length - 1]
    } catch (err) {}
    const s = String(seg).replace(/[^A-Za-z0-9._-]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 42)
    return 'manga_' + hostName + '_' + (s || 'images') + '_' + count + 'img.zip'
  }

  async function saveZip(blob, name) {
    const android = /android/i.test(navigator.userAgent)
    const fileName = android ? name : 'MangaAuto/' + name
    const url = URL.createObjectURL(blob)
    let res = null
    try { res = await bg({ type: 'MT_DL', blobUrl: url, filename: fileName }, 160000) } catch (err) { res = { err: String(err) } }
    if (!res || res.err) {
      const a = document.createElement('a')
      a.href = url
      a.download = name
      a.style.display = 'none'
      document.body.appendChild(a)
      a.click()
      setTimeout(function () { a.remove() }, 6000)
      return { path: android ? '/storage/emulated/0/Download/' + name : 'پوشهٔ دانلود مرورگر/' + name, name: name }
    }
    let p = res.path || ''
    if (!p) p = android ? '/storage/emulated/0/Download/' + name : 'Download/MangaAuto/' + name
    return { path: p, name: name }
  }

  async function avifToJpeg(u8) {
    try {
      const bmp = await createImageBitmap(new Blob([u8], { type: 'image/avif' }))
      const cv = document.createElement('canvas')
      cv.width = bmp.width || 1
      cv.height = bmp.height || 1
      cv.getContext('2d').drawImage(bmp, 0, 0)
      const b = await new Promise(function (res) { cv.toBlob(res, 'image/jpeg', 0.92) })
      if (!b) return null
      return new Uint8Array(await b.arrayBuffer())
    } catch (err) { return null }
  }

  function setProgress(i, total, item) {
    progTitle.textContent = 'در حال دانلود عکس‌ها ' + i + ' از ' + total
    progCur.textContent = item.show
    progBar.style.width = (total ? Math.round(i * 100 / total) : 0) + '%'
  }

  async function startDownload(items) {
    closeMenu()
    closePanel()
    cancelFlag = false
    progRes.classList.remove('mtopen')
    progFailNote.classList.remove('mtopen')
    progOk.textContent = '0 موفق'
    progFail.textContent = '0 ناموفق'
    progBar.style.width = '0%'
    progCur.textContent = ''
    progTitle.textContent = 'در حال دانلود عکس‌ها'
    prog.classList.add('mtopen')
    const zip = new MtZip()
    let ok = 0, fail = 0
    const failed = []
    for (let i = 0; i < items.length; i++) {
      if (cancelFlag) break
      const item = items[i]
      setProgress(i + 1, items.length, item)
      const r = await itemBytes(item)
      if (r && r.u8 && r.u8.length) {
        let ext = finalExt(item, r.ct, r.u8)
        let out = null
        if (ext === 'gif' || r.u8.length < 2048) {
          fail++
          failed.push(item.show + ' — فایل گیف یا خیلی کوچک')
        } else if (ext === 'avif') {
          const j = await avifToJpeg(r.u8)
          if (j && j.length) { out = j; ext = 'jpg' }
          else { fail++; failed.push(item.show + ' — avif تبدیل نشد') }
        } else {
          out = r.u8
        }
        if (out) { zip.add((i + 1) + '.' + ext, out); ok++ }
      } else {
        fail++
        failed.push(item.show + ' — دریافت نشد (سایت اجازه نداد)')
      }
      progOk.textContent = ok + ' موفق'
      progFail.textContent = fail + ' ناموفق'
    }
    if (cancelFlag && ok === 0) {
      closeProg()
      toast('دانلود لغو شد')
      return
    }
    if (ok === 0) {
      progTitle.textContent = 'خطا — هیچ عکسی دانلود نشد'
      progBar.style.width = '100%'
      progCur.textContent = ''
      progResPath.textContent = ''
      progResPath.style.display = 'none'
      progFailNote.textContent = 'هیچ‌کدام از ' + items.length + ' لینک قابل دریافت نبود — سایت دانلود را مسدود کرده است'
      progFailNote.classList.add('mtopen')
      progRes.classList.add('mtopen')
      progRes.setAttribute('data-path', '')
      progRes.setAttribute('data-links', items.map(function (it) { return it.show }).join('\n'))
      progRes.setAttribute('data-fails', failed.join('\n'))
      return
    }
    progTitle.textContent = 'در حال ساخت فایل ZIP'
    progCur.textContent = ok + ' عکس'
    await new Promise(function (r) { setTimeout(r, 60) })
    const blob = zip.build()
    const name = zipName(ok)
    const r = await saveZip(blob, name)
    progTitle.textContent = 'ذخیره شد'
    progBar.style.width = '100%'
    progCur.textContent = ''
    progResPath.style.display = ''
    progResPath.textContent = r.path
    if (fail > 0) {
      progFailNote.textContent = fail + ' عکس دانلود نشد و در فایل نیست'
      progFailNote.classList.add('mtopen')
    }
    progRes.classList.add('mtopen')
    progRes.setAttribute('data-path', r.path)
    progRes.setAttribute('data-links', items.map(function (it) { return it.show }).join('\n'))
    progRes.setAttribute('data-fails', failed.join('\n'))
  }

  prog.addEventListener('click', function (e) {
    const t = e.target && e.target.getAttribute && e.target.getAttribute('data-mt')
    if (!t) return
    if (t === 'cancel') {
      cancelFlag = true
      progTitle.textContent = 'در حال لغو…'
    }
    if (t === 'copypath') {
      const p = progRes.getAttribute('data-path') || ''
      copyText(p).then(function (okres) { toast(okres ? 'مسیر کپی شد' : 'کپی نشد') })
    }
    if (t === 'copylinks') {
      const l = progRes.getAttribute('data-links') || ''
      copyText(l).then(function (okres) { toast(okres ? 'لینک‌ها کپی شد' : 'کپی نشد') })
    }
    if (t === 'copyfails') {
      const f = progRes.getAttribute('data-fails') || ''
      copyText(f).then(function (okres) { toast(okres ? 'لینک‌های ناموفق کپی شد' : 'کپی نشد') })
    }
    if (t === 'resclose') closeProg()
  })

  async function refreshRecState() {
    let en = false
    let on = false
    let count = 0
    try {
      const s = await chrome.storage.session.get(['mtRec', 'mtEn'])
      const e = s && s.mtRec
      const ee = s && s.mtEn
      if (ee && ee.on) en = true
      if (e && e.on) {
        on = true
        count = (e.urls || []).length
      }
    } catch (err) {
      try {
        const r = await bg({ type: 'MT_STATE', tab: TAB.id }, 4000)
        en = !!(r && r.en)
        on = !!(r && r.rec)
        count = (r && r.count) || 0
      } catch (err2) {}
    }
    enabled = en
    recording = on
    applyUI(on ? count : 0)
  }

  async function init() {
    try {
      const who = await bg({ type: 'MT_WHOAMI' }, 5000)
      TAB.id = (who && who.tab) || -1
    } catch (err) {}
    await refreshRecState()
    try {
      chrome.storage.onChanged.addListener(function (changes, area) {
        if (area !== 'session') return
        if (!changes.mtRec && !changes.mtEn) return
        refreshRecState()
      })
    } catch (err) {}
  }

  try {
    chrome.runtime.onMessage.addListener(function (msg, sender, sendResponse) {
      if (!msg || !msg.type) return
      if (msg.type === 'MT_POPUP_ENABLE') {
        enableExt()
        sendResponse({ ok: true })
        return
      }
      if (msg.type === 'MT_POPUP_DISABLE') {
        disableExt()
        sendResponse({ ok: true })
        return
      }
      if (msg.type === 'MT_POPUP_START') {
        startRecording()
        sendResponse({ ok: true })
        return
      }
      if (msg.type === 'MT_POPUP_STOP') {
        stopRecording()
        sendResponse({ ok: true })
      }
    })
  } catch (err) {}

  init()
})()
