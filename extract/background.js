let restored = false
let restorePromise = null
const REC = { on: false, urls: [], keys: [], seen: new Set() }
const EN = { on: false }
let flushTimer = null
const pendingNet = []
const selfFetch = new Set()

let dnrKey = ''
let dnrTimer = null
const DNR_RULE_ID = 9901

async function removeRefererRule() {
  dnrKey = ''
  try { await chrome.declarativeNetRequest.updateSessionRules({ removeRuleIds: [DNR_RULE_ID] }) } catch (err) {}
}

async function ensureRefererRule(url, ref) {
  try {
    if (!chrome.declarativeNetRequest || !chrome.declarativeNetRequest.updateSessionRules) return
    let host = ''
    try { host = new URL(url).hostname } catch (err) { return }
    if (!host) return
    const key = host + '|' + (ref || '')
    if (key === dnrKey) {
      if (dnrTimer) clearTimeout(dnrTimer)
      dnrTimer = setTimeout(removeRefererRule, 120000)
      return
    }
    await removeRefererRule()
    if (ref) {
      await chrome.declarativeNetRequest.updateSessionRules({
        addRules: [{
          id: DNR_RULE_ID,
          priority: 1,
          condition: { requestDomains: [host], resourceTypes: ['xmlhttprequest'] },
          action: {
            type: 'modifyHeaders',
            setRequestHeaders: [{ header: 'referer', value: ref }]
          }
        }]
      })
    }
    dnrKey = key
    if (dnrTimer) clearTimeout(dnrTimer)
    dnrTimer = setTimeout(removeRefererRule, 120000)
  } catch (err) {}
}

async function ensurePageHook() {
  try {
    await chrome.scripting.unregisterContentScripts({ ids: ['mt-page-hook'] })
  } catch (err) {}
  try {
    await chrome.scripting.registerContentScripts([{
      id: 'mt-page-hook',
      js: ['page-hook.js'],
      matches: ['http://*/*', 'https://*/*'],
      runAt: 'document_start',
      world: 'MAIN',
      allFrames: false
    }])
  } catch (err) {}
}
ensurePageHook()
try {
  chrome.runtime.onInstalled.addListener(function () { ensurePageHook() })
} catch (err) {}

function ensureRestore() {
  if (!restorePromise) {
    restorePromise = (async function () {
      try { await chrome.storage.session.setAccessLevel({ accessLevel: 'TRUSTED_AND_UNTRUSTED_CONTEXTS' }) } catch (err) {}
      try {
        const saved = await chrome.storage.session.get(['mtRec', 'mtEn'])
        if (saved && saved.mtRec && saved.mtRec.on) {
          REC.on = true
          REC.urls = saved.mtRec.urls || []
          REC.keys = saved.mtRec.keys || []
          REC.seen = new Set(REC.keys)
        }
        if (saved && saved.mtEn && saved.mtEn.on) EN.on = true
      } catch (err) {}
      restored = true
      const list = pendingNet.splice(0)
      for (const d of list) handleNet(d)
    })()
  }
  return restorePromise
}
ensureRestore()

function clearRec(on) {
  REC.on = !!on
  if (on) {
    REC.urls = []
    REC.keys = []
    REC.seen = new Set()
  }
}

function serialize() {
  return { on: REC.on, urls: REC.urls, keys: REC.keys }
}

function persist() {
  if (flushTimer) return
  flushTimer = setTimeout(async () => {
    flushTimer = null
    try { await chrome.storage.session.set({ mtRec: serialize() }) } catch (err) {}
  }, 300)
}

function persistNow() {
  if (flushTimer) { clearTimeout(flushTimer); flushTimer = null }
  chrome.storage.session.set({ mtRec: serialize() }).catch(() => {})
}

function persistEn() {
  chrome.storage.session.set({ mtEn: { on: EN.on } }).catch(() => {})
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
  if (/(pubadx|adservice|adserver|doubleclick|adnxs|propellerads?|onclck|adcash|adsterra|hilltopads?|clickadu|sovrn|taboola|outbrain|zedo|buysellads?|sharethrough|smartadserver|openx|rubicon|criteo|pubmatic|media\.net|jumpg-assets)/i.test(b)) return true
  return false
}

function keyOf(u) {
  const s = String(u)
  const b = s.split(/[?#]/)[0]
  if (!/\.(jpe?g|png|webp|avif|bmp|tiff?)$/i.test(b)) return s.split('#')[0]
  return b.replace(/[-_]\d{2,4}x\d{2,4}\./i, '.')
}

function handleNet(details) {
  if (!REC.on) return
  if (selfFetch.has(details.url)) return
  if (details.initiator && String(details.initiator).indexOf('chrome-extension://') === 0) return
  if (details.documentUrl && String(details.documentUrl).indexOf('chrome-extension://') === 0) return
  let ct = ''
  let cl = 0
  const headers = details.responseHeaders || []
  for (const h of headers) {
    const n = (h.name || '').toLowerCase()
    if (n === 'content-type') ct = h.value || ''
    if (n === 'content-length') cl = parseInt(h.value, 10) || 0
  }
  if (!/^image\//i.test(ct)) return
  if (/^image\/gif/i.test(ct)) return
  if (/\.gif([?#]|$)/i.test(details.url)) return
  if (cl > 0 && cl < 15000) return
  const dec = decodeProxy(details.url)
  if (junk(dec)) return
  const k = keyOf(dec)
  if (REC.seen.has(k)) return
  REC.seen.add(k)
  REC.keys.push(k)
  REC.urls.push({ u: details.url, d: dec, s: cl, r: details.documentUrl || details.initiator || '' })
  persist()
}

chrome.webRequest.onResponseStarted.addListener(function (details) {
  if (!restored) { pendingNet.push(details); return }
  handleNet(details)
}, { urls: ['<all_urls>'] }, ['responseHeaders'])

async function fetchBytes(url, ref) {
  selfFetch.add(url)
  setTimeout(function () { selfFetch.delete(url) }, 30000)
  await ensureRefererRule(url, ref)
  const mk = function (cred) {
    const o = { credentials: cred }
    if (ref) { o.referrer = ref; o.referrerPolicy = 'unsafe-url' }
    return o
  }
  let res = await fetch(url, mk('omit')).catch(() => null)
  if (!res || !res.ok) res = await fetch(url, mk('include')).catch(() => null)
  if (!res || !res.ok) return { err: 'http ' + (res ? res.status : 0) }
  const buf = await res.arrayBuffer()
  const u8 = new Uint8Array(buf)
  let b64 = ''
  const CH = 32768
  for (let i = 0; i < u8.length; i += CH) {
    b64 += String.fromCharCode.apply(null, u8.subarray(i, i + CH))
  }
  return { b64: btoa(b64), ct: res.headers.get('content-type') || '', size: u8.length }
}

function saveFile(blobUrl, filename) {
  return new Promise(function (resolve) {
    if (!chrome.downloads || !chrome.downloads.download) { resolve({ err: 'noapi' }); return }
    chrome.downloads.download({
      url: blobUrl,
      filename: filename,
      saveAs: false,
      conflictAction: 'uniquify'
    }).then(function (id) {
      let done = false
      const finish = function (r) {
        if (done) return
        done = true
        clearTimeout(timer)
        try { chrome.downloads.onChanged.removeListener(watch) } catch (err) {}
        resolve(r)
      }
      const timer = setTimeout(function () { finish({ id: id, path: '' }) }, 150000)
      const watch = function (delta) {
        if (!delta || delta.id !== id) return
        const st = delta.state && delta.state.current
        if (st === 'complete') {
          chrome.downloads.search({ id: id }).then(function (items) {
            finish({ id: id, path: (items && items[0] && items[0].filename) || '' })
          }).catch(function () { finish({ id: id, path: '' }) })
        } else if (st === 'interrupted') {
          finish({ err: 'interrupted' })
        }
      }
      chrome.downloads.onChanged.addListener(watch)
    }).catch(function (err) {
      resolve({ err: String((err && err.message) || err) })
    })
  })
}

chrome.runtime.onMessage.addListener(function (msg, sender, sendResponse) {
  const type = msg && msg.type
  if (type === 'MT_WHOAMI') {
    sendResponse({ tab: sender && sender.tab ? sender.tab.id : -1 })
    return
  }
  if (type === 'MT_ENABLE') {
    ensureRestore().then(function () {
      EN.on = true
      persistEn()
      sendResponse({ ok: true })
    })
    return true
  }
  if (type === 'MT_DISABLE') {
    ensureRestore().then(function () {
      EN.on = false
      REC.on = false
      persistEn()
      persistNow()
      removeRefererRule()
      sendResponse({ ok: true })
    })
    return true
  }
  if (type === 'MT_START') {
    ensureRestore().then(function () {
      EN.on = true
      clearRec(true)
      persistEn()
      persistNow()
      sendResponse({ ok: true })
    })
    return true
  }
  if (type === 'MT_STOP') {
    ensureRestore().then(function () {
      REC.on = false
      persistNow()
      removeRefererRule()
      sendResponse({ ok: true })
    })
    return true
  }
  if (type === 'MT_STATE') {
    ensureRestore().then(function () {
      sendResponse({ rec: REC.on, count: REC.on ? REC.urls.length : 0, en: EN.on })
    })
    return true
  }
  if (type === 'MT_GET') {
    ensureRestore().then(function () {
      const urls = []
      const keys = new Set()
      for (const it of REC.urls) {
        if (keys.has(it.d)) continue
        keys.add(it.d)
        urls.push(it)
      }
      sendResponse({ items: urls })
    })
    return true
  }
  if (type === 'MT_FETCH') {
    const ref = msg.ref || (sender && sender.tab && sender.tab.url) || ''
    fetchBytes(msg.url, ref).then(sendResponse).catch(function (err) { sendResponse({ err: String(err) }) })
    return true
  }
  if (type === 'MT_PAGE_INJECT') {
    if (sender && sender.tab) {
      chrome.scripting.executeScript({ target: { tabId: sender.tab.id }, world: 'MAIN', files: ['page-hook.js'] })
        .then(function () { sendResponse({ ok: true }) })
        .catch(function (err) { sendResponse({ err: String(err) }) })
    } else {
      sendResponse({ err: 'no tab' })
    }
    return true
  }
  if (type === 'MT_DL') {
    saveFile(msg.blobUrl, msg.filename).then(sendResponse).catch(function (err) { sendResponse({ err: String(err) }) })
    return true
  }
})
