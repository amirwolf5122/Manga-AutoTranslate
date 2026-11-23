(function () {
  'use strict'
  function ping() {
    let ok = false
    const onMsg = function (ev) {
      if (ev.source === window && ev.data && ev.data.MT_EV === 'pong') ok = true
    }
    window.addEventListener('message', onMsg)
    window.postMessage({ MT_CMD: 'ping' }, '*')
    setTimeout(function () {
      window.removeEventListener('message', onMsg)
      if (!ok) {
        try {
          chrome.runtime.sendMessage({ type: 'MT_PAGE_INJECT' }).catch(function () {})
        } catch (err) {}
      }
    }, 700)
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { ping() }, { once: true })
  } else {
    ping()
  }
})()
