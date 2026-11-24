(function () {
  'use strict'
  if (window.__mtHook) return
  window.__mtHook = 1

  const net = []
  const netSeen = new Set()
  const blobs = new Map()
  let blobBytes = 0

  function clean(u) {
    try { return String(u).split('#')[0] } catch (err) { return '' }
  }

  function pushNet(u) {
    try {
      if (!u) return
      const s = clean(u)
      if (!/^https?:/i.test(s)) return
      if (netSeen.has(s)) return
      netSeen.add(s)
      net.push(s)
      while (net.length > 600) {
        const old = net.shift()
        netSeen.delete(old)
      }
    } catch (err) {}
  }

  function pushBlob(url, blob) {
    try {
      if (blobs.has(url)) return
      blobs.set(url, { blob: blob, type: blob.type || '', size: blob.size || 0 })
      blobBytes += blob.size || 0
      while (blobBytes > 220000000 && blobs.size > 1) {
        const first = blobs.keys().next().value
        const e = blobs.get(first)
        blobBytes -= (e && e.size) || 0
        blobs.delete(first)
      }
    } catch (err) {}
  }

  const origCreate = URL.createObjectURL
  URL.createObjectURL = function (b) {
    const u = origCreate.apply(URL, arguments)
    try {
      if (b instanceof Blob && /^image\//i.test(b.type || '') && (b.size || 0) > 12000) pushBlob(u, b)
    } catch (err) {}
    return u
  }

  const origFetch = window.fetch
  if (origFetch) {
    window.fetch = function () {
      const p = origFetch.apply(window, arguments)
      p.then(function (r) {
        try {
          const ct = (r.headers && r.headers.get('content-type')) || ''
          if (/^image\//i.test(ct) && r.url) pushNet(r.url)
        } catch (err) {}
      }).catch(function () {})
      return p
    }
  }

  window.addEventListener('message', function (ev) {
    if (ev.source !== window) return
    const d = ev.data
    if (!d || !d.MT_CMD) return
    if (d.MT_CMD === 'ping') {
      window.postMessage({ MT_EV: 'pong', netCount: net.length, blobCount: blobs.size }, '*')
    }
    if (d.MT_CMD === 'net') {
      window.postMessage({ MT_EV: 'net', urls: net.slice() }, '*')
    }
    if (d.MT_CMD === 'blobKeys') {
      const keys = []
      for (const [k, v] of blobs) keys.push({ url: k, type: v.type, size: v.size })
      window.postMessage({ MT_EV: 'blobKeys', keys: keys }, '*')
    }
    if (d.MT_CMD === 'pullBlobs') {
      const urls = d.urls || []
      for (const u of urls) {
        const e = blobs.get(u)
        if (!e) {
          window.postMessage({ MT_EV: 'blobData', url: u, err: 'missing' }, '*')
          continue
        }
        e.blob.arrayBuffer().then(function (buf) {
          window.postMessage({ MT_EV: 'blobData', url: u, type: e.type, buf: buf }, '*', [buf])
        }).catch(function (err) {
          window.postMessage({ MT_EV: 'blobData', url: u, err: String(err) }, '*')
        })
      }
    }
    if (d.MT_CMD === 'pageFetch') {
      const url = String(d.url || '')
      let cross = true
      try { cross = new URL(url, location.href).origin !== location.origin } catch (err) {}
      const postErr = function (e) {
        window.postMessage({ MT_EV: 'pageFetch', url: url, err: String(e) }, '*')
      }
      const attempt = function (cred, canRetry) {
        fetch(url, { credentials: cred, referrerPolicy: 'unsafe-url' }).then(async function (r) {
          if (!r.ok) {
            if (canRetry) { attempt('include', false); return }
            postErr('http ' + r.status)
            return
          }
          const buf = await r.arrayBuffer()
          window.postMessage({ MT_EV: 'pageFetch', url: url, buf: buf, ct: r.headers.get('content-type') || '' }, '*', [buf])
        }).catch(function (err) {
          if (canRetry) { attempt('include', false); return }
          postErr(err)
        })
      }
      attempt(cross ? 'omit' : 'include', cross)
    }
    if (d.MT_CMD === 'clear') {
      net.length = 0
      netSeen.clear()
      blobs.clear()
      blobBytes = 0
    }
  })
})()
