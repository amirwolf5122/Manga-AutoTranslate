document.addEventListener('DOMContentLoaded', function () {
  const tog = document.getElementById('tog')
  const togtxt = document.getElementById('togtxt')
  const statusEl = document.getElementById('status')
  const verEl = document.getElementById('ver')
  try {
    verEl.textContent = 'نسخهٔ ' + chrome.runtime.getManifest().version
  } catch (err) { verEl.textContent = '' }

  let busy = false

  function setState(en, rec, count) {
    tog.checked = !!en
    togtxt.textContent = en ? 'روشن' : 'خاموش'
    if (!en) statusEl.textContent = ''
    else if (rec) statusEl.textContent = '● ضبط فعال' + (typeof count === 'number' ? ' — ' + count + ' عکس' : '')
    else statusEl.textContent = 'فعال — دکمهٔ «ضبط» پایین صفحه'
  }

  function refresh() {
    try {
      chrome.runtime.sendMessage({ type: 'MT_STATE' }, function (r) {
        if (chrome.runtime.lastError || !r) return
        setState(r.en, r.rec, r.count)
      })
    } catch (err) {}
  }

  function sendTab(msg) {
    return new Promise(function (resolve) {
      try {
        chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
          const tab = tabs && tabs[0]
          if (!tab || tab.id == null) { resolve(false); return }
          try {
            chrome.tabs.sendMessage(tab.id, msg, function (r) {
              resolve(!chrome.runtime.lastError && !!r)
            })
          } catch (err) { resolve(false) }
        })
      } catch (err) { resolve(false) }
    })
  }

  function bgCmd(type) {
    return new Promise(function (resolve) {
      try {
        chrome.runtime.sendMessage({ type: type }, function (r) {
          resolve(!!r && !!r.ok)
        })
      } catch (err) { resolve(false) }
    })
  }

  tog.addEventListener('change', function () {
    if (busy) { tog.checked = !tog.checked; return }
    busy = true
    const want = tog.checked
    const done = function () {
      setState(want, false, 0)
      busy = false
      setTimeout(refresh, 600)
    }
    sendTab({ type: want ? 'MT_POPUP_ENABLE' : 'MT_POPUP_DISABLE' }).then(function (ok) {
      if (ok) { done(); return }
      bgCmd(want ? 'MT_ENABLE' : 'MT_DISABLE').then(function () {
        if (!want) statusEl.textContent = 'افزونه خاموش شد'
        done()
      })
    })
  })

  try {
    chrome.storage.onChanged.addListener(function (changes, area) {
      if (area !== 'session') return
      if (!changes.mtRec && !changes.mtEn) return
      refresh()
    })
  } catch (err) {}

  refresh()
})
