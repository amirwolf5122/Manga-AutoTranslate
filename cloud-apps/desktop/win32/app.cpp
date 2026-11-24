#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <objbase.h>
#include <stdio.h>
#include <cmath>
#include <cstdint>
#include <set>
#include <string>
#include <vector>
#include "WebView2.h"

static const WCHAR APP_URL[] =
    L"https://amirwolf512-manga-autotranslate.hf.space/";
static const WCHAR BROWSER_HOME[] = L"https://www.google.com";
static const WCHAR APP_TITLE[] =
    L"\u0645\u0627\u0646\u06AF\u0627 \u06A9\u0644\u0648\u062F";

#define ID_BTN_GO      101
#define ID_BTN_BACK    102
#define ID_BTN_FWD     103
#define ID_BTN_EXTRACT 104
#define ID_BTN_CLOSE   105
#define ID_EDIT_URL    106
#define ID_LBL_STATUS  107
#define ID_BTN_GLOBE   108
#define ID_BTN_WV2DL   109
#define ID_BTN_SYSBR   110
#define ID_BTN_RETRY   111
#define ID_MITEM_LINK  201
#define ID_MITEM_DL    202

#define WM_APP_CREATCTL (WM_APP + 1)
#define WM_APP_BRREADY  (WM_APP + 2)
#define WM_APP_MENU_SHOW  (WM_APP + 3)
#define WM_APP_DO_EXTRACT (WM_APP + 4)
#define WM_APP_FILL_DONE  (WM_APP + 5)
#define WM_APP_NAV_FILL   (WM_APP + 6)
#define WM_APP_DL_STEP    (WM_APP + 7)
#define WM_APP_UP_START   (WM_APP + 8)
#define WM_APP_UP_POLL    (WM_APP + 9)
#define WM_APP_UP_FINISH  (WM_APP + 10)
#define WM_APP_DL_FAIL    (WM_APP + 11)
#define WM_APP_DL_EMPTY   (WM_APP + 12)
#define WM_APP_SHOW_FOLDERS (WM_APP + 13)

#define BR_BAR_H     52
#define PROG_H        3
#define FAB_SIZE    52

#define TIMER_PROGRESS 1
#define TIMER_RECOUNT  2
#define TIMER_SMOKE_BR 3
#define TIMER_READER   4

static HWND g_hwnd = NULL;
static HWND g_hwndBr = NULL;
static HINSTANCE g_hInst = NULL;

static ICoreWebView2Environment *g_env = NULL;
static ICoreWebView2Controller *g_appCtl = NULL;
static ICoreWebView2 *g_webApp = NULL;
static ICoreWebView2Controller *g_brCtl = NULL;
static ICoreWebView2 *g_webBr = NULL;
static BOOL g_brPending = FALSE;
static BOOL g_smokeBrowser = FALSE;
static std::wstring g_brTarget;
static std::wstring g_fillUrl;
static int g_fillCount = 0;
static std::wstring g_lastSite;

static HWND g_editUrl = NULL;
static HWND g_btnGo = NULL;
static HWND g_btnBack = NULL;
static HWND g_btnFwd = NULL;
static HWND g_btnExtract = NULL;
static HWND g_lblStatus = NULL;
static HWND g_hwndMenu = NULL;
static HWND g_btnGlobe = NULL;
static HFONT g_font = NULL;
static HFONT g_fontBold = NULL;
static HFONT g_fontFail = NULL;
static HWND g_lblFailTitle = NULL;
static HWND g_lblFailBody = NULL;
static HWND g_btnWv2Dl = NULL;
static HWND g_btnSysBr = NULL;
static HWND g_btnRetry = NULL;
static BOOL g_failMode = FALSE;
static BOOL g_readerMode = FALSE;
static BOOL g_recording = FALSE;
static std::vector<std::wstring> g_recNet;
static std::set<std::wstring> g_recNetSeen;
static std::vector<std::wstring> g_foundStore;
static std::vector<std::wstring> g_domOrder;
static std::set<std::wstring> g_foundSeen;
static std::vector<std::wstring> g_selUrls;
static int g_netShown = -1;
static std::vector<std::wstring> g_dlUrls;
static std::vector<std::wstring> g_dlData;
static int g_dlSlotIdx[3] = {-1, -1, -1};
static size_t g_dlNext = 0;
static int g_dlDone = 0;
static int g_dlOk = 0;
static int g_dlBad = 0;
static int g_upPolls = 0;
static int g_upFired = 0;
static int g_upNextIdx = 0;
static HBRUSH g_barBrush = NULL;
static HBRUSH g_urlBrush = NULL;
static HBRUSH g_brBarBrush = NULL;
static RECT g_urlRing = {0, 0, 0, 0};

static int g_progress = 0;
static BOOL g_loading = FALSE;
static int g_doneTicks = 0;

static const COLORREF CLR_BAR    = RGB(16, 19, 27);
static const COLORREF CLR_URLBG  = RGB(26, 31, 43);
static const COLORREF CLR_URLBR  = RGB(39, 48, 67);
static const COLORREF CLR_TXT    = RGB(231, 235, 243);
static const COLORREF CLR_MUT    = RGB(138, 147, 168);
static const COLORREF CLR_BTN    = RGB(32, 38, 51);
static const COLORREF CLR_BTN_DN = RGB(45, 54, 73);
static const COLORREF CLR_ACC    = RGB(232, 89, 12);
static const COLORREF CLR_ACC_DN = RGB(160, 60, 8);
static const COLORREF CLR_FAB    = RGB(31, 36, 49);
static const COLORREF CLR_FAB_DN = RGB(45, 52, 70);
static const COLORREF CLR_BRBAR  = RGB(13, 13, 16);
static const COLORREF CLR_BRBRD  = RGB(31, 31, 36);
static const COLORREF CLR_NAV    = RGB(45, 54, 73);
static const COLORREF CLR_NAV_DN = RGB(60, 72, 97);
static const COLORREF CLR_EXTR   = RGB(228, 60, 47);
static const COLORREF CLR_EXTR_DN = RGB(178, 42, 33);
static const COLORREF CLR_CNT    = RGB(151, 148, 140);

static const wchar_t *MT_COLLECT_JS =
L"(function(){"
L"try{"
L"if(/(^|\\.)mangaplus\\.shueisha\\.co\\.jp$/i.test(location.host)&&location.pathname.indexOf('/viewer/')===0)return [location.href];"
L"}catch(e){}"
L"function abs(u){try{var a=document.createElement('a');a.href=u;return a.href}catch(e){return null}}"
L"function qsz(u){"
L"var m=String(u).match(/[?&](?:type|size|w|h|width|height)=(f?)(\\d{1,4})(?:[_x](\\d{1,4}))?/i);"
L"if(!m)return 0;"
L"var a=parseInt(m[2],10)||0;"
L"var b=parseInt(m[3]||'0',10)||0;"
L"if(a>0&&b>0)return Math.max(a,b);"
L"if(m[1]&&a>0)return a;"
L"return 0}"
L"function junk(u){"
L"if(!u)return 1;"
L"if(u.indexOf('data:')===0)return 1;"
L"if(u.indexOf('blob:')===0)return 1;"
L"if(!/^https?:/i.test(u))return 1;"
L"var b=String(u).split(/[?#]/)[0];"
L"if(/\\.(svg|ico|gif)$/i.test(b))return 1;"
L"if(/[-_]\\d{2,4}x\\d{2,4}\\.(jpe?g|png|webp)$/i.test(b))return 1;"
L"var q=qsz(u);"
L"if(q>0&&q<=400)return 1;"
L"if(/(logo|icon|avatar|banner|sprite|favicon|badge|flag|button|emoji|thumb(nail)?s?|placeholder|blank|spacer|transparen|loading|spinner|pixel|profile|rating|share|follow|comment|credits)/i.test(b))return 1;"
L"if(/(?:^|[^a-z0-9])ads?[._\\/-]/i.test(b))return 1;"
L"return 0}"
L"var seen={},picked=[];"
L"function add(u){"
L"try{"
L"if(!u)return;"
L"u=abs(String(u).trim());"
L"if(!u)return;"
L"if(junk(u))return;"
L"try{if(u===location.href)return}catch(e){}"
L"var k=keyOf(u);"
L"if(Object.prototype.hasOwnProperty.call(seen,k))return;"
L"seen[k]=1;picked.push(u)"
L"}catch(e){}}"
L"function domPass(){"
L"var els2=document.querySelectorAll('img,source,a[href],[style*=\"url(\"]');"
L"for(var i=0;i<els2.length;i++){"
L"var el=els2[i],tg=el.tagName;"
L"if(tg==='A'){"
L"try{var h=el.getAttribute('href')||'';"
L"if(/^https?:/i.test(h)&&/\\.(jpe?g|png|webp|avif|bmp)([?#]|$)/i.test(h))add(h)}catch(e){}"
L"continue}"
L"if(tg!=='IMG'&&tg!=='SOURCE'){"
L"try{var mm=String(el.getAttribute('style')||'').match(/url\\((['\"]?)([^'\")]+)\\1\\)/i);"
L"if(mm&&mm[2])add(mm[2])}catch(e){}"
L"continue}"
L"var ok=false,nw=0,nh=0;"
L"try{ok=!!el.complete&&el.naturalWidth>0;nw=el.naturalWidth||0;nh=el.naturalHeight||0}catch(e){}"
L"var u='';"
L"try{u=el.currentSrc||el.src||''}catch(e){}"
L"if(u&&u.indexOf('data:')===0)u='';"
L"if(u&&ok&&nw&&nh&&Math.max(nw,nh)<300)u='';"
L"if(u)add(u);"
L"var dts=['data-src','data-lazy-src','data-original','data-original-src','data-orig-src','data-lazy','data-url','data-image','data-echo','data-cfsrc','data-hi-res-src','data-full-src','data-full_image','data-large-src','data-file','data-path','data-actualsrc'];"
L"for(var j=0;j<dts.length;j++){"
L"try{var v=el.getAttribute(dts[j]);if(v&&v.length>4)add(v)}catch(e){}}"
L"try{var ss=el.getAttribute('srcset')||el.getAttribute('data-srcset');"
L"if(ss){var parts=ss.split(','),best='',bw=0;"
L"for(var k=0;k<parts.length;k++){"
L"var tk=parts[k].trim().split(/\\s+/);"
L"var u0=tk[0]||'';"
L"var w0=parseInt(String(tk[1]||'').replace(/[^0-9]/g,''),10)||0;"
L"if(u0&&w0>=bw){bw=w0;best=u0}}"
L"if(best)add(best)}}catch(e){}"
L"}"
L"}"
L"function resPass(){"
L"var rs=[];"
L"try{rs=performance.getEntriesByType('resource')}catch(e){}"
L"for(var i=0;i<rs.length;i++){"
L"var en=rs[i]||{};"
L"var t=String(en.initiatorType||'');"
L"if(t!=='img'&&t!=='css'&&t!=='link'&&t!=='other'&&t!=='svg'&&t!=='embed'&&t!=='fetch'&&t!=='xmlhttprequest')continue;"
L"var n=String(en.name||'');"
L"if(!n)continue;"
L"var b=n.split(/[?#]/)[0];"
L"var ext=/\\.(jpe?g|png|webp|avif|bmp|tiff?)$/i.test(b);"
L"if(!ext){"
L"if(/\\.(jpe?g|png|webp|avif|bmp|tiff?)([?#]|$)/i.test(n)){add(n);continue}"
L"if(t==='fetch'||t==='xmlhttprequest')continue;"
L"if(!/(^|\\/)(pages?|images?|img|media|manga|manhwa|webtoon|chapters?|episodes?|comic|uploads|wp-content|cdn)(\\/|[_\\-.]|$)/i.test(b))continue"
L"}"
L"add(n)"
L"}"
L"}"
L"domPass();resPass();"
L"if(picked.length)return picked;"
L"var all=[],good=[],idx=0;"
L"var els=document.querySelectorAll('img,source');"
L"for(var i=0;i<els.length;i++){"
L"var el=els[i];"
L"var cs=null;"
L"try{cs=el.currentSrc||el.src||null}catch(e){}"
L"var cands=[cs,el.getAttribute('data-src'),el.getAttribute('data-lazy-src'),el.getAttribute('data-original'),el.getAttribute('data-original-src'),el.getAttribute('data-orig-src'),el.getAttribute('data-lazy'),el.getAttribute('data-url'),el.getAttribute('data-image'),el.getAttribute('data-echo')];"
L"var ss=el.getAttribute('srcset')||el.getAttribute('data-srcset');"
L"if(ss){"
L"var parts=ss.split(','),best='',bw=0;"
L"for(var k=0;k<parts.length;k++){"
L"var tk=parts[k].trim().split(/\\s+/);"
L"var u0=tk[0]||'';"
L"var w0=parseInt(String(tk[1]||'').replace(/[^0-9]/g,''),10)||0;"
L"if(u0&&w0>=bw){bw=w0;best=u0}}"
L"if(best)cands.push(best)}"
L"if(el.tagName==='SOURCE'&&el.parentNode){"
L"var pe=el.parentNode.querySelector('img');"
L"if(pe&&pe.src)cands.push(pe.src)}"
L"var pick=null,pj=1;"
L"for(var j=0;j<cands.length;j++){"
L"var u=cands[j];"
L"if(!u)continue;"
L"u=abs(String(u).trim());"
L"if(!u||u.indexOf('data:')===0)continue;"
L"try{if(u===location.href)continue}catch(e){}"
L"if(!pick)pick=u;"
L"if(!junk(u)){pick=u;pj=0;break}"
L"}"
L"if(!pick)continue;"
L"var nw=0,nh=0;"
L"try{nw=el.naturalWidth||0;nh=el.naturalHeight||0}catch(e){}"
L"if(nw&&nh&&Math.max(nw,nh)<300)continue;"
L"all.push([pick,idx]);"
L"if(!pj)good.push([pick,idx]);"
L"idx++"
L"}"
L"function keyOf(u){"
L"var s=String(u);"
L"var b=s.split(/[?#]/)[0];"
L"if(!/\\.(jpe?g|png|webp|avif|bmp|tiff?)$/i.test(b))return s.split('#')[0];"
L"return b.replace(/[-_]\\d{2,4}x\\d{2,4}\\./i,'.')}"
L"function dedupe(list){"
L"var by={},order=[];"
L"for(var i=0;i<list.length;i++){"
L"var it=list[i],k=keyOf(it[0]);"
L"if(Object.prototype.hasOwnProperty.call(by,k)){"
L"var o=by[k];"
L"if(qsz(it[0])>qsz(o[0]))by[k]=it"
L"}else{by[k]=it;order.push(k)}}"
L"var out=[];"
L"for(var j=0;j<order.length;j++)out.push(by[order[j]][0]);"
L"return out}"
L"var res=dedupe(good);"
L"if(!res.length)res=dedupe(all);"
L"return res;"
L"})()";

static const wchar_t *MT_NET_HOOK_JS =
L"(function(){try{"
L"if(window.__mtNetHook)return;window.__mtNetHook=1;"
L"function post(u){try{"
L"if(!u)return;u=String(u);"
L"if(u.indexOf('data:')===0)return;"
L"if(!/^https?:/i.test(u))return;"
L"if(window.__mtWv2&&window.__mtWv2.postMessage)"
L"window.__mtWv2.postMessage('MTIMG '+u)"
L"}catch(e){}}"
L"var _f=window.fetch;"
L"if(typeof _f==='function'&&!window.__mtFH){"
L"window.__mtFH=1;"
L"window.fetch=function(){"
L"var p;try{p=_f.apply(this,arguments)}catch(e){throw e}"
L"try{"
L"var a0=arguments[0];var u0='';"
L"if(a0){if(typeof a0==='string')u0=a0;"
L"else if(a0.url)u0=String(a0.url)}"
L"p.then(function(r){try{"
L"var ct=(r.headers&&r.headers.get('content-type'))||'';"
L"if(/^image\\//i.test(String(ct).trim()))post(u0)"
L"}catch(e){}}).catch(function(){})"
L"}catch(e){}"
L"return p}}"
L"var _o=XMLHttpRequest.prototype.open,_s=XMLHttpRequest.prototype.send;"
L"XMLHttpRequest.prototype.open=function(m,u){"
L"try{this.__mtU=String(u||'')}catch(e){}"
L"return _o.apply(this,arguments)};"
L"XMLHttpRequest.prototype.send=function(){"
L"try{var x=this;"
L"x.addEventListener('loadend',function(){try{"
L"var ct='';try{ct=x.getResponseHeader('content-type')||''}catch(e){}"
L"var ru='';try{ru=x.responseURL||x.__mtU||''}catch(e){}"
L"if(/^image\\//i.test(String(ct).trim()))post(ru)"
L"}catch(e){}})}"
L"catch(e){}"
L"return _s.apply(this,arguments)}"
L"}catch(e){}})()";

static const wchar_t *MT_PRELOAD_JS =
L"(function(){try{var _a=window.alert;window.alert=function(m){"
L"try{var s=String(m);"
L"var f=s.match(/^__MT_FILLED__(\\d+)__MT_FILLED2__$/);"
L"if(f){_a(f[1]+' \\u0644\\u06cc\\u0646\\u06a9 \\u0639\\u06a9\\u0633 \\u062f\\u0631 \\u0641\\u06cc\\u0644\\u062f\\u0650 \\u0648\\u0631\\u0648\\u062f\\u06cc \\u0646\\u0634\\u0633\\u062a \\u2014 \\u00ab\\u0634\\u0631\\u0648\\u0639 \\u062a\\u0631\\u062c\\u0645\\u0647\\u00bb \\u0631\\u0627 \\u0628\\u0632\\u0646');return;}"
L"if(s==='__MT_NOLINKS__'){_a('\\u0639\\u06a9\\u0633\\u06cc \\u067e\\u06cc\\u062f\\u0627 \\u0646\\u0634\\u062f');return;}"
L"if(s==='__MT_COPIED__'){_a('\\u06a9\\u067e\\u06cc \\u0634\\u062f');return;}"
L"if(s==='__MT_COPY2__'){_a('\\u0644\\u06cc\\u0646\\u06a9\\u200c\\u0647\\u0627 \\u06a9\\u067e\\u06cc \\u0634\\u062f \\u2014 \\u062f\\u0631 \\u0641\\u06cc\\u0644\\u062f\\u0650 \\u0648\\u0631\\u0648\\u062f\\u06cc \\u0628\\u0686\\u0633\\u067e\\u0627\\u0646');return;}"
L"if(s==='__MT_NOURL__'){_a('\\u0627\\u0648\\u0644 \\u0622\\u062f\\u0631\\u0633 \\u0633\\u0627\\u06cc\\u062a \\u0645\\u0627\\u0646\\u0647\\u0648\\u0627 \\u0631\\u0627 \\u0628\\u0646\\u0648\\u06cc\\u0633');return;}"
L"}catch(e){}_a(m)};}catch(e){}})();";

static const wchar_t *MT_GETFIELD_JS =
L"(function(){try{"
L"var el=document.querySelector('#manga_inp_path textarea')"
L"||document.querySelector('[id*=\"manga_inp_path\"] textarea')"
L"||document.querySelector('#manga_inp_path input');"
L"var v=el?String(el.value||''):'';"
L"var p=v.split(/\\n|,/).map(function(x){return x.trim()})"
L".filter(function(x){return x.length>0});"
L"if(!p.length)return '';"
L"var n=0;for(var i=0;i<p.length;i++){var t=p[i];"
L"if(t.indexOf('http://')===0||t.indexOf('https://')===0)n++}"
L"if(n>1)return '__MT_MANY__';"
L"var t=p[0];"
L"if(/\\.(jpe?g|png|webp|gif|avif|bmp)([?#]|$)/i.test(t))"
L"return '__MT_MANY__';"
L"return t;"
L"}catch(e){return ''}})()";

static std::wstring g_logNear;
static std::wstring g_logMain;
static std::wstring g_dirNear;
static std::wstring g_dirMain;

static const wchar_t MT_READER_WATCH_JS[] =
    L"(function(){try{return document.getElementById('mangaReaderOverlay')"
    L"?'1':'0'}catch(e){return '0'}})()";

static const wchar_t MT_READER_REFRESH_JS[] =
    L"(function(){try{var o=document.getElementById('mangaReaderOverlay');"
    L"if(!o)return '0';var f=o.querySelector('iframe');if(!f)return '0';"
    L"try{if(f.contentWindow&&f.contentWindow.location)"
    L"f.contentWindow.location.reload();return '1'}"
    L"catch(e){f.src=f.src;return '1'}}catch(e){return '0'}})()";

static std::wstring MtDlOneJs(const std::wstring &quotedUrl) {
    return std::wstring(L"(function(){try{var u=") + quotedUrl
        + L";if(!u)return '';"
          L"return fetch(u,{credentials:'include'})"
          L".then(function(r){if(!r.ok)return '';return r.blob()})"
          L".then(function(b){if(!b)return '';"
          L"return new Promise(function(res){try{"
          L"var f=new FileReader();"
          L"f.onload=function(){res(String(f.result||''))};"
          L"f.onerror=function(){res('')};f.readAsDataURL(b)}"
          L"catch(e){res('')}})})"
          L".catch(function(){return ''})}catch(e){return ''}})()";
}

static std::wstring MtUpOneJs(int idx, const std::wstring &quotedDataUrl) {
    wchar_t ib[32];
    swprintf(ib, 32, L"%d", idx);
    return std::wstring(
        L"(function(){try{"
        L"window.__mtUp=window.__mtUp||{ok:0,paths:[]};"
        L"var i=") + std::wstring(ib)
        + L";var d=" + quotedDataUrl + L";"
          L"fetch(d).then(function(r){return r.blob()})"
          L".then(function(b){"
          L"var mt=String(d.slice(5,d.indexOf(';'))||'image/jpeg');"
          L"var ex=mt.split('/')[1]||'jpg';if(ex==='jpeg')ex='jpg';"
          L"if(!/^[a-z0-9]{2,5}$/.test(ex))ex='jpg';"
          L"var fd=new FormData();"
          L"fd.append('files',b,'page_'+(i+1)+'.'+ex);"
          L"return fetch('gradio_api/upload',{method:'POST',body:fd})"
          L".then(function(r){if(r.status===404)"
          L"return fetch('upload',{method:'POST',body:fd});"
          L"return r})})"
          L".then(function(r){return r.ok?r.json():[]})"
          L".then(function(a){if(a&&a[0])"
          L"window.__mtUp.paths[i]=String(a[0])})"
          L".catch(function(){})"
          L".then(function(){window.__mtUp.ok++});"
          L"return 1}catch(e){return 0}})()";
}

static std::wstring MtUpPollJs(int total) {
    wchar_t tb[32];
    swprintf(tb, 32, L"%d", total);
    return std::wstring(
        L"(function(){try{"
        L"var u=window.__mtUp||{ok:0};"
        L"var t=") + std::wstring(tb) + L";"
        L"return new Promise(function(res){"
        L"setTimeout(function(){res(u.ok+'/'+t)},400)})"
        L"}catch(e){return '0/1'}})()";
}

static const wchar_t MT_UP_FILL_JS[] =
    L"(function(){try{"
    L"var u=window.__mtUp;if(!u)return 0;"
    L"var p=(u.paths||[]).filter(Boolean);"
    L"if(!p.length)return 0;"
    L"if(window.__mtFillLinks){"
    L"window.__mtFillLinks(p.join('\\n'));"
    L"alert('__MT_FILLED__'+p.length+'__MT_FILLED2__')}"
    L"return 1}catch(e){return 0}})()";

static void MtWriteLog(const std::wstring &path, const char *line) {
    if (path.empty() || line == NULL)
        return;
    FILE *f = _wfopen(path.c_str(), L"a");
    if (f == NULL)
        return;
    SYSTEMTIME st;
    GetLocalTime(&st);
    fprintf(f, "%04u-%02u-%02u %02u:%02u:%02u %s\n",
            (unsigned)st.wYear, (unsigned)st.wMonth, (unsigned)st.wDay,
            (unsigned)st.wHour, (unsigned)st.wMinute, (unsigned)st.wSecond,
            line);
    fclose(f);
}

static void MtLog(const char *line) {
    MtWriteLog(g_logNear, line);
    MtWriteLog(g_logMain, line);
}

static void MtLogHr(const char *what, HRESULT hr) {
    char b[120];
    sprintf(b, "%s hr=%08lX", what, (unsigned long)hr);
    MtLog(b);
}

static void MtInitLogPath(void) {
    WCHAR base[MAX_PATH];
    WCHAR exe[MAX_PATH];
    DWORD n = GetModuleFileNameW(NULL, exe, MAX_PATH);
    if (n > 0 && n < MAX_PATH) {
        std::wstring dir(exe);
        size_t cut = dir.find_last_of(L"\\/");
        if (cut != std::wstring::npos) {
            g_dirNear = dir.substr(0, cut);
            g_logNear = g_dirNear + L"\\run.log";
        }
    }
    if (GetEnvironmentVariableW(L"LOCALAPPDATA", base, MAX_PATH) > 0) {
        g_dirMain = std::wstring(base) + L"\\MangaCloud";
        CreateDirectoryW(g_dirMain.c_str(), NULL);
        g_logMain = g_dirMain + L"\\run.log";
    }
}

static void MtDarkTitleBar(HWND hwnd) {
    if (hwnd == NULL)
        return;
    HMODULE dwm = LoadLibraryW(L"dwmapi.dll");
    if (dwm == NULL)
        return;
    typedef HRESULT (WINAPI *MtDwmSetFn)(HWND, DWORD, const void *, DWORD);
    MtDwmSetFn set = (MtDwmSetFn)(void *)(uintptr_t)GetProcAddress(
        dwm, "DwmSetWindowAttribute");
    if (set == NULL)
        return;
    BOOL dark = TRUE;
    if (FAILED(set(hwnd, 20, &dark, sizeof(dark))))
        set(hwnd, 19, &dark, sizeof(dark));
}

typedef BOOL (WINAPI *MtMiniDumpFn)(HANDLE, DWORD, HANDLE, DWORD,
                                    const void *, const void *, const void *);
typedef struct MtMiniDumpExcInfo {
    DWORD ThreadId;
    EXCEPTION_POINTERS *ExceptionPointers;
    BOOL ClientPointers;
} MtMiniDumpExcInfo;

static BOOL g_inCrash = FALSE;

static int g_dumpCount = 0;

static void MtWriteMinidump(EXCEPTION_POINTERS *ep) {
    if (g_dumpCount >= 8)
        return;
    HMODULE db = LoadLibraryW(L"dbghelp.dll");
    if (db == NULL)
        return;
    g_dumpCount++;
    MtMiniDumpFn fn = (MtMiniDumpFn)(void *)(uintptr_t)GetProcAddress(
        db, "MiniDumpWriteDump");
    if (fn == NULL)
        return;
    const wchar_t *names[2] = {NULL, NULL};
    std::wstring nearDump, mainDump;
    if (!g_dirNear.empty()) {
        nearDump = g_dirNear + L"\\MangaCloud-crash.dmp";
        names[0] = nearDump.c_str();
    }
    if (!g_dirMain.empty()) {
        mainDump = g_dirMain + L"\\MangaCloud-crash.dmp";
        names[1] = mainDump.c_str();
    }
    for (int i = 0; i < 2; i++) {
        if (names[i] == NULL)
            continue;
        HANDLE h = CreateFileW(names[i], GENERIC_WRITE, 0, NULL,
                               CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
        if (h == INVALID_HANDLE_VALUE)
            continue;
        MtMiniDumpExcInfo mei;
        mei.ThreadId = GetCurrentThreadId();
        mei.ExceptionPointers = ep;
        mei.ClientPointers = FALSE;
        fn(GetCurrentProcess(), GetCurrentProcessId(), h,
           0  , &mei, NULL, NULL);
        CloseHandle(h);
    }
}

static LONG WINAPI MtCrashFilter(EXCEPTION_POINTERS *ep) {
    if (g_inCrash)
        return EXCEPTION_CONTINUE_SEARCH;
    g_inCrash = TRUE;
    char b[256];
    unsigned long code = 0;
    void *addr = NULL;
    ULONG_PTR rw = 99, target = 0;
    if (ep != NULL && ep->ExceptionRecord != NULL) {
        code = (unsigned long)ep->ExceptionRecord->ExceptionCode;
        addr = ep->ExceptionRecord->ExceptionAddress;
        if (ep->ExceptionRecord->ExceptionInformation != NULL
                && ep->ExceptionRecord->NumberParameters >= 2) {
            rw = (ULONG_PTR)ep->ExceptionRecord->ExceptionInformation[0];
            target = (ULONG_PTR)ep->ExceptionRecord->ExceptionInformation[1];
        }
    }
    HMODULE img = GetModuleHandleW(NULL);
    sprintf(b, "CRASH code=%08lX addr=%p imgbase=%p type=%lu target=0x%llX",
            code, addr, (void *)img, (unsigned long)rw,
            (unsigned long long)target);
    MtLog(b);
    if (addr != NULL && img != NULL) {
        char b2[96];
        sprintf(b2, "CRASH offset=+%llX",
                (unsigned long long)((uintptr_t)addr - (uintptr_t)img));
        MtLog(b2);
    }
    {
        void *fr[24];
        USHORT n = CaptureStackBackTrace(0, 24, fr, NULL);
        for (USHORT i = 0; i < n; i++) {
            char b3[96];
            if (img != NULL
                    && (uintptr_t)fr[i] >= (uintptr_t)img
                    && (uintptr_t)fr[i] < (uintptr_t)img + 0x4000000u) {
                sprintf(b3, "stack[%u] +0x%llX", (unsigned)i,
                        (unsigned long long)((uintptr_t)fr[i]
                                             - (uintptr_t)img));
            } else {
                sprintf(b3, "stack[%u] %p", (unsigned)i, fr[i]);
            }
            MtLog(b3);
        }
    }
    MtWriteMinidump(ep);
    return EXCEPTION_CONTINUE_SEARCH;
}

typedef BOOL (WINAPI *MtSymInitFn)(HANDLE, PCSTR, BOOL);
typedef BOOL (WINAPI *MtSymFromAddrFn)(HANDLE, DWORD64, DWORD64 *, void *);
static MtSymInitFn g_symInit = NULL;
static MtSymFromAddrFn g_symFromAddr = NULL;
static BOOL g_symTried = FALSE;

static void MtSymName(void *addr, char *out, size_t outsz) {
    if (out == NULL || outsz == 0)
        return;
    out[0] = 0;
    if (!g_symTried) {
        g_symTried = TRUE;
        HMODULE db = LoadLibraryW(L"dbghelp.dll");
        if (db != NULL) {
            g_symInit = (MtSymInitFn)(void *)(uintptr_t)GetProcAddress(
                db, "SymInitialize");
            g_symFromAddr = (MtSymFromAddrFn)(void *)(uintptr_t)
                GetProcAddress(db, "SymFromAddr");
        }
        if (g_symInit != NULL)
            g_symInit(GetCurrentProcess(), NULL, TRUE);
    }
    if (g_symFromAddr == NULL)
        return;
    struct { ULONG SizeOfStruct; ULONG TypeIndex; ULONG64 Reserved[2];
             ULONG Index; ULONG Size; ULONG64 ModBase; ULONG Flags;
             ULONG64 Value; ULONG64 Address; ULONG Register;
             ULONG Scope; ULONG Tag; ULONG NameLen; ULONG MaxNameLen;
             char Name[128]; } si;
    si.SizeOfStruct = 88;
    si.MaxNameLen = 128;
    DWORD64 disp = 0;
    if (g_symFromAddr(GetCurrentProcess(), (DWORD64)(uintptr_t)addr,
                      &disp, &si)) {
        _snprintf(out, outsz - 1, "%s+0x%llX",
                  si.Name, (unsigned long long)disp);
        out[outsz - 1] = 0;
    }
}

static int MtSehLog(const char *who, EXCEPTION_POINTERS *ep) {
    char b[200];
    unsigned long code = 0;
    void *addr = NULL;
    unsigned long rw = 99;
    unsigned long long target = 0;
    if (ep != NULL && ep->ExceptionRecord != NULL) {
        code = (unsigned long)ep->ExceptionRecord->ExceptionCode;
        addr = ep->ExceptionRecord->ExceptionAddress;
        if (ep->ExceptionRecord->ExceptionInformation != NULL
                && ep->ExceptionRecord->NumberParameters >= 2) {
            rw = (unsigned long)ep->ExceptionRecord->ExceptionInformation[0];
            target = (unsigned long long)
                ep->ExceptionRecord->ExceptionInformation[1];
        }
    }
    char sym[160];
    MtSymName(addr, sym, sizeof(sym));
    sprintf(b, "SEH-CAUGHT %s code=%08lX addr=%p type=%lu target=0x%llX%s%s",
            who, code, addr, rw, target,
            sym[0] ? " sym=" : "", sym);
    MtLog(b);
    {
        char bg[160];
        sprintf(bg,
                "SEH-STATE webApp=%p appCtl=%p webBr=%p brCtl=%p "
                "hwnd=%p hwndBr=%p brPending=%d",
                (void *)g_webApp, (void *)g_appCtl, (void *)g_webBr,
                (void *)g_brCtl, (void *)g_hwnd, (void *)g_hwndBr,
                (int)g_brPending);
        MtLog(bg);
    }
    {
        HMODULE img = GetModuleHandleW(NULL);
        if (addr != NULL && img != NULL) {
            char b2[96];
            sprintf(b2, "SEH offset=+%llX",
                    (unsigned long long)((uintptr_t)addr - (uintptr_t)img));
            MtLog(b2);
        }
        void *fr[24];
        USHORT n = CaptureStackBackTrace(0, 24, fr, NULL);
        for (USHORT i = 0; i < n; i++) {
            char b3[96];
            if (img != NULL
                    && (uintptr_t)fr[i] >= (uintptr_t)img
                    && (uintptr_t)fr[i] < (uintptr_t)img + 0x4000000u) {
                sprintf(b3, "seh-stack[%u] +0x%llX", (unsigned)i,
                        (unsigned long long)((uintptr_t)fr[i]
                                             - (uintptr_t)img));
            } else {
                sprintf(b3, "seh-stack[%u] %p", (unsigned)i, fr[i]);
            }
            MtLog(b3);
        }
    }
    MtWriteMinidump(ep);
    return EXCEPTION_EXECUTE_HANDLER;
}

static void MtUnescape(const wchar_t *src, size_t len, std::wstring &out) {
    for (size_t i = 0; i < len; i++) {
        wchar_t c = src[i];
        if (c == L'\\' && i + 1 < len) {
            wchar_t e = src[++i];
            if (e == L'"') out += L'"';
            else if (e == L'\\') out += L'\\';
            else if (e == L'/') out += L'/';
            else if (e == L'n') out += L'\n';
            else if (e == L'r') out += L'\r';
            else if (e == L't') out += L'\t';
            else if (e == L'b') out += L'\b';
            else if (e == L'f') out += L'\f';
            else if (e == L'u' && i + 4 < len) {
                unsigned v = 0;
                for (int k = 1; k <= 4; k++) {
                    wchar_t h = src[++i];
                    v <<= 4;
                    if (h >= L'0' && h <= L'9') v |= (unsigned)(h - L'0');
                    else if (h >= L'a' && h <= L'f') v |= (unsigned)(h - L'a' + 10);
                    else if (h >= L'A' && h <= L'F') v |= (unsigned)(h - L'A' + 10);
                }
                out += (wchar_t)v;
            } else {
                out += e;
            }
        } else {
            out += c;
        }
    }
}

static bool MtParseStringArray(const wchar_t *s, std::vector<std::wstring> &out) {
    if (s == NULL)
        return false;
    while (*s == L' ' || *s == L'\t' || *s == L'\r' || *s == L'\n')
        s++;
    if (*s != L'[')
        return false;
    s++;
    while (*s == L' ' || *s == L'\t')
        s++;
    if (*s == L']')
        return true;
    for (;;) {
        while (*s == L' ' || *s == L'\t' || *s == L',')
            s++;
        if (*s != L'"')
            return false;
        s++;
        const wchar_t *start = s;
        while (*s && *s != L'"') {
            if (*s == L'\\' && *(s + 1))
                s++;
            s++;
        }
        if (*s != L'"')
            return false;
        std::wstring u;
        MtUnescape(start, (size_t)(s - start), u);
        if (!u.empty())
            out.push_back(u);
        s++;
        while (*s == L' ' || *s == L'\t')
            s++;
        if (*s == L',')
            continue;
        if (*s == L']')
            return true;
        return false;
    }
}

static bool MtParseMaybeWrapped(const wchar_t *s,
                                 std::vector<std::wstring> &out) {
    if (s == NULL)
        return false;
    while (*s == L' ' || *s == L'\t' || *s == L'\r' || *s == L'\n')
        s++;
    if (wcsncmp(s, L"null", 4) == 0)
        return true;
    if (MtParseStringArray(s, out))
        return true;
    if (*s == L'"') {
        s++;
        const wchar_t *start = s;
        while (*s && *s != L'"') {
            if (*s == L'\\' && *(s + 1))
                s++;
            s++;
        }
        if (*s != L'"')
            return false;
        std::wstring inner;
        MtUnescape(start, (size_t)(s - start), inner);
        return MtParseStringArray(inner.c_str(), out);
    }
    return false;
}

static std::wstring MtParseJsonString(const wchar_t *s) {
    std::wstring out;
    if (s == NULL)
        return out;
    while (*s == L' ' || *s == L'\t' || *s == L'\r' || *s == L'\n')
        s++;
    if (wcsncmp(s, L"null", 4) == 0)
        return out;
    if (*s != L'"')
        return out;
    s++;
    const wchar_t *start = s;
    while (*s && *s != L'"') {
        if (*s == L'\\' && *(s + 1))
            s++;
        s++;
    }
    if (*s != L'"')
        return out;
    MtUnescape(start, (size_t)(s - start), out);
    size_t a = out.find_first_not_of(L" \t\r\n");
    if (a == std::wstring::npos)
        return std::wstring();
    size_t b = out.find_last_not_of(L" \t\r\n");
    return out.substr(a, b - a + 1);
}

static std::string MtUrlEncode(const std::wstring &in) {
    std::string out;
    int need = WideCharToMultiByte(CP_UTF8, 0, in.c_str(), (int)in.size(),
                                   NULL, 0, NULL, FALSE);
    if (need <= 0)
        return out;
    std::vector<char> buf((size_t)need + 1, 0);
    WideCharToMultiByte(CP_UTF8, 0, in.c_str(), (int)in.size(),
                        &buf[0], need, NULL, FALSE);
    static const char *hex = "0123456789ABCDEF";
    for (size_t i = 0; i < (size_t)need; i++) {
        unsigned char c = (unsigned char)buf[i];
        if ((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') ||
            (c >= '0' && c <= '9') ||
            c == '-' || c == '_' || c == '.' || c == '!' || c == '~' ||
            c == '*' || c == '\'' || c == '(' || c == ')') {
            out += (char)c;
        } else {
            out += '%';
            out += hex[c >> 4];
            out += hex[c & 15];
        }
    }
    return out;
}

static std::wstring MtWideFromAscii(const std::string &s) {
    std::wstring w;
    w.reserve(s.size());
    for (size_t i = 0; i < s.size(); i++)
        w += (wchar_t)(unsigned char)s[i];
    return w;
}

static std::wstring MtJsQuote(const std::wstring &s) {
    std::wstring o = L"\"";
    for (size_t i = 0; i < s.size(); i++) {
        wchar_t c = s[i];
        if (c == L'"') o += L"\\\"";
        else if (c == L'\\') o += L"\\\\";
        else if (c == L'\n') o += L"\\n";
        else if (c == L'\r') o += L"\\r";
        else if (c == L'\t') o += L"\\t";
        else if (c < 0x20) {
            wchar_t b[8];
            swprintf(b, 8, L"\\u%04x", (unsigned)c);
            o += b;
        } else {
            o += c;
        }
    }
    o += L"\"";
    return o;
}

static std::wstring MtSearchOrUrl(const std::wstring &s) {
    if (_wcsnicmp(s.c_str(), L"http://", 7) == 0
            || _wcsnicmp(s.c_str(), L"https://", 8) == 0)
        return s;
    BOOL domain = (s.find(L' ') == std::wstring::npos)
                  && (s.find(L'\t') == std::wstring::npos);
    int dots = 0;
    for (size_t i = 0; domain && i < s.size(); i++) {
        wchar_t c = s[i];
        if (c == L'.') {
            dots++;
        } else if (!((c >= L'a' && c <= L'z') ||
                     (c >= L'A' && c <= L'Z') ||
                     (c >= L'0' && c <= L'9') ||
                     c == L'-' || c == L'_' || c == L':' ||
                     c == L'/' || c == L'?' || c == L'#' ||
                     c == L'~' || c == L'.')) {
            domain = FALSE;
        }
    }
    if (domain && dots > 0)
        return std::wstring(L"https://") + s;
    return std::wstring(L"https://www.google.com/search?q=")
           + MtWideFromAscii(MtUrlEncode(s));
}

static BOOL MtHasI(const std::wstring &hay, const wchar_t *needle) {
    if (needle == NULL || *needle == 0)
        return TRUE;
    size_t nl = wcslen(needle);
    if (hay.size() < nl)
        return FALSE;
    for (size_t i = 0; i + nl <= hay.size(); i++) {
        size_t k = 0;
        while (k < nl) {
            wchar_t a = hay[i + k];
            wchar_t b = needle[k];
            if (a >= L'A' && a <= L'Z') a = a - L'A' + L'a';
            if (b >= L'A' && b <= L'Z') b = b - L'A' + L'a';
            if (a != b)
                break;
            k++;
        }
        if (k == nl)
            return TRUE;
    }
    return FALSE;
}

static std::wstring MtUrlBase(const std::wstring &u) {
    size_t h = u.find_first_of(L"#?");
    return (h == std::wstring::npos) ? u : u.substr(0, h);
}

static BOOL MtEndsWithI(const std::wstring &b, const wchar_t *ext) {
    size_t el = wcslen(ext);
    if (b.size() < el)
        return FALSE;
    return _wcsicmp(b.c_str() + (b.size() - el), ext) == 0;
}

static BOOL MtDimTag(const std::wstring &b) {
    for (size_t i = 1; i + 6 < b.size(); i++) {
        if (b[i - 1] != L'-' && b[i - 1] != L'_')
            continue;
        size_t p = i;
        int d1 = 0;
        while (p < b.size() && b[p] >= L'0' && b[p] <= L'9' && d1 < 4) {
            p++; d1++;
        }
        if (d1 < 2 || p >= b.size() || b[p] != L'x')
            continue;
        p++;
        int d2 = 0;
        while (p < b.size() && b[p] >= L'0' && b[p] <= L'9' && d2 < 4) {
            p++; d2++;
        }
        if (d2 < 2)
            continue;
        if (p < b.size() && (b[p] == L'.' || b[p] == L'/' || b[p] == L'\\'
                             || b[p] == L'-' || b[p] == L'_'))
            return TRUE;
    }
    return FALSE;
}

static int MtQuerySize(const std::wstring &u) {
    static const wchar_t *names[] = {
        L"type=", L"size=", L"w=", L"h=", L"width=", L"height=", NULL };
    for (int ni = 0; names[ni]; ni++) {
        size_t nl = wcslen(names[ni]) - 1;
        for (size_t i = 0; i + nl < u.size(); i++) {
            if (u[i] != L'?' && u[i] != L'&')
                continue;
            size_t nvStart = i + 1;
            if (_wcsnicmp(u.c_str() + nvStart, names[ni], nl + 1) != 0)
                continue;
            size_t p = nvStart + nl + 1;
            BOOL fFlag = FALSE;
            if (p < u.size() && (u[p] == L'f' || u[p] == L'F')) {
                fFlag = TRUE;
                p++;
            }
            int d1 = 0;
            long v1 = 0;
            while (p < u.size() && u[p] >= L'0' && u[p] <= L'9' && d1 < 4) {
                v1 = v1 * 10 + (u[p] - L'0');
                p++; d1++;
            }
            if (d1 == 0)
                continue;
            long v2 = 0;
            int d2 = 0;
            if (p < u.size() && (u[p] == L'_' || u[p] == L'x'
                                 || u[p] == L'X')) {
                size_t q2 = p + 1;
                while (q2 < u.size() && u[q2] >= L'0' && u[q2] <= L'9'
                       && d2 < 4) {
                    v2 = v2 * 10 + (u[q2] - L'0');
                    q2++; d2++;
                }
            }
            if (d2 > 0)
                return (int)((v1 > v2) ? v1 : v2);
            if (fFlag && d1 > 0)
                return (int)v1;
        }
    }
    return 0;
}

static BOOL MtJunkUrl(const std::wstring &uRaw) {
    if (uRaw.empty())
        return TRUE;
    if (_wcsnicmp(uRaw.c_str(), L"data:", 5) == 0)
        return TRUE;
    if (_wcsnicmp(uRaw.c_str(), L"blob:", 5) == 0)
        return FALSE;
    if (_wcsnicmp(uRaw.c_str(), L"http://", 7) != 0
            && _wcsnicmp(uRaw.c_str(), L"https://", 8) != 0)
        return TRUE;
    std::wstring b = MtUrlBase(uRaw);
    static const wchar_t *badExt[] = {
        L".svg", L".ico", L".gif", L".css", L".js", L".mjs", L".json",
        L".html", L".htm", L".xml", L".txt", L".pdf", L".zip", L".rar",
        L".7z", L".gz", L".mp4", L".webm", L".mp3", L".m4a", L".ogg",
        L".wav", L".woff", L".woff2", L".ttf", L".otf", L".eot", L".map",
        NULL };
    for (int i = 0; badExt[i]; i++)
        if (MtEndsWithI(b, badExt[i]))
            return TRUE;
    if (MtDimTag(b))
        return TRUE;
    if (MtHasI(b, L"login") || MtHasI(b, L"signin")
            || MtHasI(b, L"signup") || MtHasI(b, L"register")
            || MtHasI(b, L"servicelogin") || MtHasI(b, L"oauth"))
        return TRUE;
    int q = MtQuerySize(uRaw);
    if (q > 0 && q <= 400)
        return TRUE;
    static const wchar_t *junkWords[] = {
        L"logo", L"icon", L"avatar", L"banner", L"sprite", L"favicon",
        L"badge", L"flag", L"button", L"emoji", L"thumb", L"thumbnail",
        L"thumbnails", L"placeholder", L"blank", L"spacer", L"transparen",
        L"loading", L"spinner", L"pixel", L"profile", L"rating", L"share",
        L"follow", L"comment", L"credits", NULL };
    for (int i = 0; junkWords[i]; i++)
        if (MtHasI(b, junkWords[i]))
            return TRUE;
    static const wchar_t *junkDirs[] = {
        L"/covers/", L"/cover/", L"/thumbs/", L"/thumb/", L"/thumbnails/",
        L"/avatars/", L"/avatar/", L"/banners/", L"/banner/",
        L"/creatives/", L"/gifs/", L"/decorations/", L"/emojis/",
        L"/smileys/", L"/stickers/", NULL };
    for (int i = 0; junkDirs[i]; i++)
        if (MtHasI(b, junkDirs[i]))
            return TRUE;
    static const wchar_t *adHosts[] = {
        L"pubadx", L"adservice", L"adserver", L"doubleclick", L"adnxs",
        L"propellerads", L"onclck", L"adcash", L"adsterra", L"hilltopads",
        L"clickadu", L"sovrn", L"taboola", L"outbrain", L"zedo",
        L"buysellads", L"sharethrough", L"smartadserver", L"openx",
        L"rubicon", L"criteo", L"pubmatic", L"media.net", NULL };
    for (int i = 0; adHosts[i]; i++)
        if (MtHasI(b, adHosts[i]))
            return TRUE;
    return FALSE;
}

static int MtRecCount(void) {
    std::set<std::wstring> all;
    all.insert(g_recNet.begin(), g_recNet.end());
    all.insert(g_foundStore.begin(), g_foundStore.end());
    return (int)all.size();
}

static void MtFoundAdd(const std::wstring &u) {
    try {
        if (u.empty())
            return;
        if (!g_foundSeen.insert(u).second)
            return;
        g_foundStore.push_back(u);
    } catch (...) {
    }
}

static void MtRecAdd(const std::wstring &u) {
    try {
        if (u.empty())
            return;
        if (!g_recNetSeen.insert(u).second)
            return;
        g_recNet.push_back(u);
    } catch (...) {
    }
}

static void MtResetRecordUi(void);
static BOOL MtIsMangaPlusUrl(const std::wstring &u);
static void MtFillFieldAndClose(const std::vector<std::wstring> &links);
static void MtStartDownload(const std::vector<std::wstring> &urls);
static void MtShowFolderOverlay(void);
static void MtOnExtractBtn(void);
static void MtShowExtractMenu(void);
static void LayoutApp(void);
static void LayoutBrowser(void);
static void MtCloseExtractMenu(void);
static void MtFireUploadBatch(void);
static void Wv2Recount(void);
static void MtOpenBrowserUi(void);
static void MtShowBrowser(void);

#if defined(_MSC_VER)
#define MT_HAS_SEH 1
#else
#define MT_HAS_SEH 0
#endif

template <typename IFACE>
struct MtHandlerBase : public IFACE {
    volatile LONG m_ref;
    MtHandlerBase() : m_ref(1) {}
    virtual HRESULT STDMETHODCALLTYPE QueryInterface(REFIID riid, void **ppv) {
        if (ppv == NULL)
            return E_POINTER;
#if defined(_MSC_VER)
        if (riid == IID_IUnknown || riid == __uuidof(IFACE)) {
            *ppv = static_cast<IFACE *>(this);
            InterlockedIncrement(&m_ref);
            return S_OK;
        }
        *ppv = NULL;
        return E_NOINTERFACE;
#else
        *ppv = static_cast<IFACE *>(this);
        InterlockedIncrement(&m_ref);
        return S_OK;
#endif
    }
    virtual ULONG STDMETHODCALLTYPE AddRef() {
        return (ULONG)InterlockedIncrement(&m_ref);
    }
    virtual ULONG STDMETHODCALLTYPE Release() {
        return (ULONG)InterlockedDecrement(&m_ref);
    }
};

struct MtExecHandler : MtHandlerBase<ICoreWebView2ExecuteScriptCompletedHandler> {
    int mode;
    explicit MtExecHandler(int m) : mode(m) {}
    virtual HRESULT STDMETHODCALLTYPE Invoke(HRESULT errorCode,
                                             LPCWSTR resultObjectAsJson) {
#if MT_HAS_SEH
        __try {
            return MtExecImpl(mode, errorCode, resultObjectAsJson);
        } __except (MtSehLog("exec", GetExceptionInformation())) {
            return S_OK;
        }
#else
        return MtExecImpl(mode, errorCode, resultObjectAsJson);
#endif
    }
    static HRESULT MtExecImpl(int mode, HRESULT errorCode,
                              LPCWSTR resultObjectAsJson);
};

static MtExecHandler g_execExtract(0);
static MtExecHandler g_execCount(2);
static MtExecHandler g_execGetUrl(3);
static MtExecHandler g_execFill(4);
static MtExecHandler g_execReaderWatch(5);
static MtExecHandler g_execDlList(9);
static MtExecHandler g_execDlStep(10);
static MtExecHandler g_execDlStepB(13);
static MtExecHandler g_execDlStepC(14);
static MtExecHandler g_execUpPoll(12);
static MtExecHandler g_execNoop(11);
static MtExecHandler g_execCollectStore(15);

struct MtNoopScriptHandler
        : MtHandlerBase<
            ICoreWebView2AddScriptToExecuteOnDocumentCreatedCompletedHandler> {
    virtual HRESULT STDMETHODCALLTYPE Invoke(HRESULT errorCode, LPCWSTR id) {
#if MT_HAS_SEH
        __try {
            return NoopImpl(errorCode, id);
        } __except (MtSehLog("noopScript", GetExceptionInformation())) {
            return S_OK;
        }
#else
        return NoopImpl(errorCode, id);
#endif
    }
    static HRESULT NoopImpl(HRESULT errorCode, LPCWSTR id) {
        (void)errorCode; (void)id;
        return S_OK;
    }
};
static MtNoopScriptHandler g_noopScript;

static void MtSetStatusCount(int n) {
    std::wstring s;
    if (n > 0) {
        s = std::to_wstring(n);
        s += L" \u0639\u06A9\u0633 \u0622\u0645\u0627\u062F\u0647";
    } else {
        s = L"\u2014";
    }
    SetWindowTextW(g_lblStatus, s.c_str());
}

struct MtNavStartHandler : MtHandlerBase<ICoreWebView2NavigationStartingEventHandler> {
    virtual HRESULT STDMETHODCALLTYPE Invoke(ICoreWebView2 *sender,
                                             ICoreWebView2NavigationStartingEventArgs *args) {
#if MT_HAS_SEH
        __try {
            return NavStartImpl(sender, args);
        } __except (MtSehLog("navStart", GetExceptionInformation())) {
            return S_OK;
        }
#else
        return NavStartImpl(sender, args);
#endif
    }
    static HRESULT NavStartImpl(ICoreWebView2 *sender,
                                ICoreWebView2NavigationStartingEventArgs *args);
};

struct MtNavDoneHandler : MtHandlerBase<ICoreWebView2NavigationCompletedEventHandler> {
    virtual HRESULT STDMETHODCALLTYPE Invoke(ICoreWebView2 *sender,
                                             ICoreWebView2NavigationCompletedEventArgs *args) {
#if MT_HAS_SEH
        __try {
            return NavDoneImpl(sender, args);
        } __except (MtSehLog("navDone", GetExceptionInformation())) {
            return S_OK;
        }
#else
        return NavDoneImpl(sender, args);
#endif
    }
    static HRESULT NavDoneImpl(ICoreWebView2 *sender,
                               ICoreWebView2NavigationCompletedEventArgs *args);
};

struct MtSrcChangedHandler : MtHandlerBase<ICoreWebView2SourceChangedEventHandler> {
    virtual HRESULT STDMETHODCALLTYPE Invoke(ICoreWebView2 *sender,
                                             ICoreWebView2SourceChangedEventArgs *args) {
#if MT_HAS_SEH
        __try {
            return SrcChangedImpl(sender, args);
        } __except (MtSehLog("srcChanged", GetExceptionInformation())) {
            return S_OK;
        }
#else
        return SrcChangedImpl(sender, args);
#endif
    }
    static HRESULT SrcChangedImpl(ICoreWebView2 *sender,
                                  ICoreWebView2SourceChangedEventArgs *args);
};

static MtNavStartHandler g_navStartHandler;
static MtNavDoneHandler g_navDoneHandler;
static MtSrcChangedHandler g_srcHandler;

struct MtResReqHandler
        : MtHandlerBase<ICoreWebView2WebResourceRequestedEventHandler> {
    virtual HRESULT STDMETHODCALLTYPE Invoke(
            ICoreWebView2 *sender,
            ICoreWebView2WebResourceRequestedEventArgs *args) {
#if MT_HAS_SEH
        __try {
            return Impl(sender, args);
        } __except (MtSehLog("resReq", GetExceptionInformation())) {
            return S_OK;
        }
#else
        return Impl(sender, args);
#endif
    }
    static HRESULT Impl(ICoreWebView2 *sender,
                        ICoreWebView2WebResourceRequestedEventArgs *args);
};

struct MtMsgHandler
        : MtHandlerBase<ICoreWebView2WebMessageReceivedEventHandler> {
    virtual HRESULT STDMETHODCALLTYPE Invoke(
            ICoreWebView2 *sender,
            ICoreWebView2WebMessageReceivedEventArgs *args) {
#if MT_HAS_SEH
        __try {
            return Impl(sender, args);
        } __except (MtSehLog("webMsg", GetExceptionInformation())) {
            return S_OK;
        }
#else
        return Impl(sender, args);
#endif
    }
    static HRESULT Impl(ICoreWebView2 *sender,
                        ICoreWebView2WebMessageReceivedEventArgs *args);
};

static MtResReqHandler g_resReqHandler;
static MtMsgHandler g_msgHandler;
static EventRegistrationToken g_evTokResReq;
static EventRegistrationToken g_evTokMsg;

HRESULT MtResReqHandler::Impl(
        ICoreWebView2 *sender,
        ICoreWebView2WebResourceRequestedEventArgs *args) {
    (void)sender;
    if (!g_recording || args == NULL)
        return S_OK;
    try {
        ICoreWebView2WebResourceRequest *req = NULL;
        if (FAILED(args->get_Request(&req)) || req == NULL)
            return S_OK;
        LPWSTR uri = NULL;
        BOOL img = FALSE;
        if (SUCCEEDED(req->get_Uri(&uri)) && uri != NULL) {
            std::wstring u(uri);
            CoTaskMemFree(uri);
            std::wstring b = MtUrlBase(u);
            if (MtEndsWithI(b, L".jpg") || MtEndsWithI(b, L".jpeg")
                    || MtEndsWithI(b, L".png") || MtEndsWithI(b, L".webp")
                    || MtEndsWithI(b, L".avif") || MtEndsWithI(b, L".bmp")
                    || MtEndsWithI(b, L".tiff") || MtEndsWithI(b, L".tif"))
                img = TRUE;
            if (!img) {
                ICoreWebView2HttpRequestHeaders *hdrs = NULL;
                if (SUCCEEDED(req->get_Headers(&hdrs)) && hdrs != NULL) {
                    LPWSTR v = NULL;
                    if (SUCCEEDED(hdrs->GetHeader(L"sec-fetch-dest", &v))
                            && v != NULL) {
                        if (_wcsicmp(v, L"image") == 0)
                            img = TRUE;
                        CoTaskMemFree(v);
                    }
                    if (!img) {
                        LPWSTR acc = NULL;
                        if (SUCCEEDED(hdrs->GetHeader(L"accept", &acc))
                                && acc != NULL) {
                            std::wstring a(acc);
                            CoTaskMemFree(acc);
                            for (size_t i = 0; i < a.size(); i++) {
                                wchar_t c = a[i];
                                if (c >= L'A' && c <= L'Z')
                                    a[i] = c - L'A' + L'a';
                            }
                            if (a.find(L"image/") != std::wstring::npos
                                    && a.find(L"text/html")
                                       == std::wstring::npos)
                                img = TRUE;
                        }
                    }
                    hdrs->Release();
                }
            }

            if (!img) {
                std::wstring f = u;
                size_t h = f.find(L'#');
                if (h != std::wstring::npos)
                    f = f.substr(0, h);
                if (MtEndsWithI(f, L".jpg") || MtEndsWithI(f, L".jpeg")
                        || MtEndsWithI(f, L".png") || MtEndsWithI(f, L".webp")
                        || MtEndsWithI(f, L".avif") || MtEndsWithI(f, L".bmp")
                        || MtEndsWithI(f, L".tiff") || MtEndsWithI(f, L".tif"))
                    img = TRUE;
            }
            if (img && !MtJunkUrl(u))
                MtRecAdd(u);
        }
        req->Release();
    } catch (...) {
    }
    return S_OK;
}

HRESULT MtMsgHandler::Impl(
        ICoreWebView2 *sender,
        ICoreWebView2WebMessageReceivedEventArgs *args) {
    (void)sender;
    try {
        if (args == NULL)
            return S_OK;
        LPWSTR msg = NULL;
        if (FAILED(args->TryGetWebMessageAsString(&msg))
                || msg == NULL)
            return S_OK;
        std::vector<std::wstring> links;
        std::wstring m(msg);
        CoTaskMemFree(msg);

        if (m.compare(0, 6, L"MTIMG ") == 0) {
            std::wstring u = m.size() > 6 ? m.substr(6) : L"";
            if (g_recording && !u.empty() && !MtJunkUrl(u))
                MtRecAdd(u);
            return S_OK;
        }
        MtParseMaybeWrapped(m.c_str(), links);
        if (links.empty())
            return S_OK;
        g_selUrls = links;
        MtLog("webMsg: folder selection received");
        PostMessage(g_hwnd, WM_APP_MENU_SHOW, 0, 0);
    } catch (...) {
    }
    return S_OK;
}

HRESULT MtNavStartHandler::NavStartImpl(
        ICoreWebView2 *sender, ICoreWebView2NavigationStartingEventArgs *args) {
    (void)sender; (void)args;
    g_loading = TRUE;
    g_progress = 8;
    g_doneTicks = 0;
    SetTimer(g_hwnd, TIMER_PROGRESS, 40, NULL);
    if (g_hwndBr != NULL)
        InvalidateRect(g_hwndBr, NULL, FALSE);
    return S_OK;
}

HRESULT MtNavDoneHandler::NavDoneImpl(
        ICoreWebView2 *sender, ICoreWebView2NavigationCompletedEventArgs *args) {
    (void)args;
    g_loading = FALSE;
    g_progress = 100;
    g_doneTicks = 8;
    if (g_hwndBr != NULL)
        InvalidateRect(g_hwndBr, NULL, FALSE);
    if (sender == g_webBr)
        Wv2Recount();
    return S_OK;
}

HRESULT MtSrcChangedHandler::SrcChangedImpl(
        ICoreWebView2 *sender, ICoreWebView2SourceChangedEventArgs *args) {
    (void)args;
    if (sender == g_webBr && sender != NULL) {
        LPWSTR uri = NULL;
        if (SUCCEEDED(sender->get_Source(&uri)) && uri != NULL) {
            SetWindowTextW(g_editUrl, uri);
            g_lastSite = uri;
            CoTaskMemFree(uri);
        }
    }
    return S_OK;
}

static void Wv2Recount(void) {
    if (g_webBr == NULL)
        return;
    g_webBr->ExecuteScript(MT_COLLECT_JS, &g_execCount);
}

struct MtCtlHandler : MtHandlerBase<ICoreWebView2CreateCoreWebView2ControllerCompletedHandler> {
    BOOL browser;
    explicit MtCtlHandler(BOOL b) : browser(b) {}
    virtual HRESULT STDMETHODCALLTYPE Invoke(HRESULT errorCode,
                                             ICoreWebView2Controller *controller) {
#if MT_HAS_SEH
        __try {
            return InvokeImpl(errorCode, controller);
        } __except (MtSehLog(browser ? "ctl(br)" : "ctl(app)",
                             GetExceptionInformation())) {
            return S_OK;
        }
#else
        return InvokeImpl(errorCode, controller);
#endif
    }
    HRESULT InvokeImpl(HRESULT errorCode,
                       ICoreWebView2Controller *controller) {
        if (FAILED(errorCode) || controller == NULL) {
            char lb[96];
            sprintf(lb, "controller(%s) failed hr=%08lX",
                    browser ? "browser" : "app", (unsigned long)errorCode);
            MtLog(lb);
            if (!browser) {
                g_failMode = TRUE;
            } else {
                g_brPending = FALSE;
            }
            if (browser)
                LayoutBrowser();
            else
                LayoutApp();
            return S_OK;
        }
        controller->AddRef();
        ICoreWebView2 *wv = NULL;
        HRESULT hr = controller->get_CoreWebView2(&wv);
        MtLogHr(browser ? "br: get_CoreWebView2" : "app: get_CoreWebView2", hr);
        if (FAILED(hr) || wv == NULL) {
            if (!browser)
                g_failMode = TRUE;
            else
                g_brPending = FALSE;
            if (browser)
                LayoutBrowser();
            else
                LayoutApp();
            return S_OK;
        }
        if (browser) {
            g_brCtl = controller;
            g_webBr = wv;
            wv->add_NavigationStarting(&g_navStartHandler, &g_evTokBrNav);
            wv->add_NavigationCompleted(&g_navDoneHandler, &g_evTokBrDone);
            wv->add_SourceChanged(&g_srcHandler, &g_evTokBrSrc);
            wv->AddScriptToExecuteOnDocumentCreated(
                L"try{window.__mtWv2=(window.chrome"
                L"&&window.chrome.webview)||null}catch(e){}",
                &g_noopScript);
            wv->add_WebMessageReceived(&g_msgHandler, &g_evTokMsg);
            ICoreWebView2_2 *wv2 = NULL;
            if (SUCCEEDED(wv->QueryInterface(__uuidof(ICoreWebView2_2),
                                             (void **)&wv2))
                    && wv2 != NULL) {
                HRESULT hrF = wv2->AddWebResourceRequestedFilter(
                    L"*", COREWEBVIEW2_WEB_RESOURCE_CONTEXT_ALL);
                MtLogHr("resReq filter", hrF);
                if (SUCCEEDED(hrF))
                    wv2->add_WebResourceRequested(&g_resReqHandler,
                                                  &g_evTokResReq);
                wv2->Release();
            } else {
                MtLog("ICoreWebView2_2 not available");
            }
            MtLog("br webview created");
            PostMessage(g_hwnd, WM_APP_BRREADY, 0, 0);
            return S_OK;
        }
        g_appCtl = controller;
        g_webApp = wv;
        wv->AddScriptToExecuteOnDocumentCreated(MT_PRELOAD_JS,
                                                &g_noopScript);
        wv->add_NavigationStarting(&g_navStartHandler, &g_evTokAppNav);
        wv->add_NavigationCompleted(&g_navDoneHandler, &g_evTokAppDone);
        wv->Navigate(APP_URL);
        MtLog("app webview created — navigating");
        LayoutApp();
        if (g_smokeBrowser)
            SetTimer(g_hwnd, TIMER_SMOKE_BR, 8000, NULL);
        return S_OK;
    }
    EventRegistrationToken g_evTokAppNav, g_evTokAppDone;
    EventRegistrationToken g_evTokBrNav, g_evTokBrDone, g_evTokBrSrc;
};

static MtCtlHandler g_ctlApp(FALSE);
static MtCtlHandler g_ctlBr(TRUE);

static void MtOpenBrowserUi(void) {
    if (g_hwndBr != NULL && g_webBr != NULL) {
        MtShowBrowser();
        return;
    }
    if (g_brPending)
        return;
    if (g_env == NULL || g_hwnd == NULL)
        return;
    if (g_hwndBr == NULL) {
        int sw = GetSystemMetrics(SM_CXSCREEN);
        int sh = GetSystemMetrics(SM_CYSCREEN);
        int ww = sw < 1120 ? (sw > 40 ? sw - 40 : sw) : 1080;
        int wh = sh < 800 ? (sh > 80 ? sh - 80 : sh) : 720;
        int x = sw > ww ? (sw - ww) / 2 : 0;
        int y = sh > wh ? (sh - wh) / 2 : 0;
        g_hwndBr = CreateWindowExW(0, L"MangaCloudBrWnd",
            L"\u0645\u0631\u0648\u0631\u06AF\u0631 \u062F\u0627\u062E\u0644\u06CC"
            L" \u2014 \u0627\u0633\u062A\u062E\u0631\u0627\u062C \u0639\u06A9\u0633"
            L" \u0645\u0627\u0646\u0647\u0648\u0627",
            WS_OVERLAPPEDWINDOW, x, y, ww, wh,
            g_hwnd, NULL, g_hInst, NULL);
        if (g_hwndBr == NULL) {
            MtLog("browser window create failed");
            return;
        }
        MtDarkTitleBar(g_hwndBr);
        LayoutBrowser();
    }
    g_brPending = TRUE;
    if (g_webApp != NULL) {
        g_brTarget.clear();
        g_webApp->ExecuteScript(MT_GETFIELD_JS, &g_execGetUrl);
    } else {
        g_brTarget = g_lastSite.empty() ? BROWSER_HOME : g_lastSite;
    }
    if (g_hwndBr == NULL) {
        MtLog("lazy: creating browser window");
    }
    MtLog("lazy: creating browser controller (separate top-level window)");
    HRESULT hr = g_env->CreateCoreWebView2Controller(g_hwndBr, &g_ctlBr);
    MtLogHr("lazy: create br", hr);
    if (FAILED(hr)) {
        g_brPending = FALSE;
        LayoutBrowser();
    }
}

static BOOL g_inBrShow = FALSE;
static void MtShowBrowser(void) {
    if (g_hwndBr == NULL)
        return;
    MtLog("brShow: begin");
    if (g_brCtl != NULL)
        g_brCtl->put_IsVisible(TRUE);
    if (g_btnGlobe != NULL)
        ShowWindow(g_btnGlobe, SW_HIDE);
    MtLog("brShow: ctl visible");
    g_inBrShow = TRUE;
    ShowWindow(g_hwndBr, SW_SHOW);
    if (IsIconic(g_hwndBr))
        ShowWindow(g_hwndBr, SW_RESTORE);
    SetWindowPos(g_hwndBr, HWND_TOP, 0, 0, 0, 0,
                 SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE);
    SetForegroundWindow(g_hwndBr);
    g_inBrShow = FALSE;
    MtLog("brShow: window shown");
    LayoutBrowser();
    if (g_editUrl != NULL)
        SetFocus(g_hwndBr);
}

static void MtHideBrowser(void) {
    MtCloseExtractMenu();
    if (g_hwndBr == NULL)
        return;
    ShowWindow(g_hwndBr, SW_HIDE);
    if (g_brCtl != NULL)
        g_brCtl->put_IsVisible(FALSE);
    if (!g_failMode && g_webApp != NULL && g_btnGlobe != NULL
            && !g_readerMode)
        ShowWindow(g_btnGlobe, SW_SHOW);
    SetForegroundWindow(g_hwnd);
}

struct MtEnvHandler : MtHandlerBase<ICoreWebView2CreateCoreWebView2EnvironmentCompletedHandler> {
    virtual HRESULT STDMETHODCALLTYPE Invoke(HRESULT errorCode,
                                             ICoreWebView2Environment *environment) {
#if MT_HAS_SEH
        __try {
            return InvokeImpl(errorCode, environment);
        } __except (MtSehLog("env", GetExceptionInformation())) {
            return S_OK;
        }
#else
        return InvokeImpl(errorCode, environment);
#endif
    }
    HRESULT InvokeImpl(HRESULT errorCode,
                       ICoreWebView2Environment *environment) {
        if (FAILED(errorCode) || environment == NULL) {
            char lb[80];
            sprintf(lb, "environment failed hr=%08lX",
                    (unsigned long)errorCode);
            g_failMode = TRUE;
            MtLog(lb);
            LayoutApp();
            return S_OK;
        }
        MtLog("environment created");
        g_env = environment;
        g_env->AddRef();
        PostMessage(g_hwnd, WM_APP_CREATCTL, 0, 0);
        return S_OK;
    }
};

static MtEnvHandler g_envHandler;

static void TryStartEnv(void) {
    LPWSTR ver = NULL;
    HRESULT hv = GetAvailableCoreWebView2BrowserVersionString(NULL, &ver);
    if (FAILED(hv) || ver == NULL) {
        MtLog("WebView2 runtime NOT found");
        g_failMode = TRUE;
        LayoutApp();
        return;
    }
    {
        std::wstring v = L"wv2 runtime: ";
        v += ver;
        std::string a;
        int need = WideCharToMultiByte(CP_UTF8, 0, v.c_str(), (int)v.size(),
                                       NULL, 0, NULL, FALSE);
        if (need > 0) {
            a.resize((size_t)need);
            WideCharToMultiByte(CP_UTF8, 0, v.c_str(), (int)v.size(),
                                &a[0], need, NULL, FALSE);
            MtLog(a.c_str());
        }
    }
    CoTaskMemFree(ver);

    WCHAR base[MAX_PATH];
    WCHAR udf[MAX_PATH + 32];
    PCWSTR userDataFolder = NULL;
    if (GetEnvironmentVariableW(L"LOCALAPPDATA", base, MAX_PATH) > 0) {
        wsprintfW(udf, L"%s\\MangaCloud", base);
        userDataFolder = udf;
    }
    HRESULT hr = CreateCoreWebView2EnvironmentWithOptions(
        NULL, userDataFolder, NULL, &g_envHandler);
    MtLogHr("createEnv", hr);
    if (FAILED(hr)) {
        g_failMode = TRUE;
        LayoutApp();
        return;
    }
    MtLog("createEnv accepted");
}

static void LayoutApp(void) {
    RECT rc;
    GetClientRect(g_hwnd, &rc);
    int w = rc.right;
    int h = rc.bottom;
    if (w <= 0 || h <= 0)
        return;

    BOOL fail = g_failMode;
    BOOL brVis = (g_hwndBr != NULL && IsWindowVisible(g_hwndBr));

    ShowWindow(g_btnGlobe,
               (!fail && g_webApp != NULL && !brVis && !g_readerMode)
               ? SW_SHOW : SW_HIDE);
    ShowWindow(g_lblFailTitle, fail ? SW_SHOW : SW_HIDE);
    ShowWindow(g_lblFailBody, fail ? SW_SHOW : SW_HIDE);
    ShowWindow(g_btnWv2Dl, fail ? SW_SHOW : SW_HIDE);
    ShowWindow(g_btnSysBr, fail ? SW_SHOW : SW_HIDE);
    ShowWindow(g_btnRetry, fail ? SW_SHOW : SW_HIDE);

    if (fail) {
        int bw = w - 48;
        if (bw > 260)
            bw = 260;
        int by = h - 3 * 44 - 2 * 10 - 18;
        if (by < 190)
            by = 190;
        MoveWindow(g_lblFailTitle, 24, 24, w - 48, 40, TRUE);
        MoveWindow(g_lblFailBody, 24, 78, w - 48,
                   (by > 120 ? by - 120 : 60), TRUE);
        MoveWindow(g_btnWv2Dl, w - 24 - bw, by, bw, 44, TRUE);
        MoveWindow(g_btnSysBr, w - 24 - bw, by + 54, bw, 44, TRUE);
        MoveWindow(g_btnRetry, w - 24 - bw, by + 108, bw, 44, TRUE);
    } else {
        MoveWindow(g_btnGlobe, 14, h - 14 - FAB_SIZE, FAB_SIZE, FAB_SIZE, TRUE);
        SetWindowPos(g_btnGlobe, HWND_TOP, 0, 0, 0, 0,
                     SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE);
    }

    if (g_appCtl != NULL) {
        if (!fail) {
            RECT a = {0, 0, w, h};
            g_appCtl->put_Bounds(a);
            g_appCtl->put_IsVisible(TRUE);
        } else {
            g_appCtl->put_IsVisible(FALSE);
        }
    }
    InvalidateRect(g_hwnd, NULL, FALSE);
}

static void LayoutBrowser(void) {
    if (g_hwndBr == NULL)
        return;
    RECT rc;
    GetClientRect(g_hwndBr, &rc);
    int w = rc.right;
    int h = rc.bottom;
    if (w <= 0 || h <= 0)
        return;

    int m = 10, gap = 8;
    int bh = 34, by = (BR_BAR_H - bh) / 2;
    int bwNav = 42, bwGo = 64;
    int bwExt = (w < 700) ? 100 : 118;
    int bwCnt = (w < 1000) ? 0 : 110;

    int xR = w - m;
    MoveWindow(g_btnFwd, xR - bwNav, by, bwNav, bh, TRUE);
    xR -= bwNav + gap;
    MoveWindow(g_btnBack, xR - bwNav, by, bwNav, bh, TRUE);
    xR -= bwNav + gap;
    int urlR = xR - 2;

    int xL = m;
    if (bwCnt > 0) {
        MoveWindow(g_lblStatus, xL, by, bwCnt, bh, TRUE);
        xL += bwCnt + gap;
    } else {
        MoveWindow(g_lblStatus, xL, by, 0, 0, TRUE);
    }
    MoveWindow(g_btnExtract, xL, by, bwExt, bh, TRUE);
    xL += bwExt + gap;
    MoveWindow(g_btnGo, xL, by, bwGo, bh, TRUE);
    xL += bwGo + gap;
    int urlL = xL + 2;

    if (urlR > urlL + 60)
        MoveWindow(g_editUrl, urlL, by + 1, urlR - urlL, bh - 2, TRUE);
    g_urlRing.left = urlL;
    g_urlRing.top = by + 1;
    g_urlRing.right = urlR;
    g_urlRing.bottom = by + bh - 1;

    if (g_brCtl != NULL) {
        int top = BR_BAR_H + 1;
        int ih = h - top;
        if (ih < 1)
            ih = 1;
        RECT b = {0, top, w, top + ih};
        g_brCtl->put_Bounds(b);
    }
    InvalidateRect(g_hwndBr, NULL, FALSE);
}

static void OnGo(void) {
    int n = GetWindowTextLengthW(g_editUrl);
    if (n <= 0)
        return;
    std::wstring buf((size_t)n + 1, L'\0');
    GetWindowTextW(g_editUrl, &buf[0], n + 1);
    size_t a = buf.find_first_not_of(L" \t");
    if (a == std::wstring::npos)
        return;
    size_t b = buf.find_last_not_of(L" \t");
    std::wstring s = buf.substr(a, b - a + 1);
    std::wstring url = MtSearchOrUrl(s);
    if (g_webBr != NULL)
        g_webBr->Navigate(url.c_str());
}

static WNDPROC g_editProc = NULL;
static LRESULT MtEditProcInner(HWND h, UINT m, WPARAM w, LPARAM l) {
    if (m == WM_KEYDOWN && w == VK_RETURN) {
        OnGo();
        return 0;
    }

    if (m == WM_CHAR && w == 1) {
        SendMessageW(h, EM_SETSEL, 0, -1);
        return 0;
    }
    return CallWindowProcW(g_editProc, h, m, w, l);
}
static LRESULT CALLBACK MtEditProc(HWND h, UINT m, WPARAM w, LPARAM l) {
#if MT_HAS_SEH
    __try {
        return MtEditProcInner(h, m, w, l);
    } __except (MtSehLog("editProc", GetExceptionInformation())) {
        return 0;
    }
#else
    return MtEditProcInner(h, m, w, l);
#endif
}

static void MtDrawPill(HDC hdc, const RECT &rc, COLORREF bg,
                       const wchar_t *txt, HFONT f) {
    HBRUSH b = CreateSolidBrush(bg);
    HPEN pen = CreatePen(PS_SOLID, 1, bg);
    HGDIOBJ ob = SelectObject(hdc, pen);
    HGDIOBJ obb = SelectObject(hdc, b);
    int rh = rc.bottom - rc.top;
    int rx = rh / 2;
    if (rx > 18)
        rx = 18;
    RoundRect(hdc, rc.left, rc.top, rc.right, rc.bottom, rx * 2, rx * 2);
    SelectObject(hdc, ob);
    SelectObject(hdc, obb);
    DeleteObject(pen);
    DeleteObject(b);
    SetBkMode(hdc, TRANSPARENT);
    SetTextColor(hdc, RGB(255, 255, 255));
    HGDIOBJ of = SelectObject(hdc, f ? f : g_font);
    RECT r = rc;
    DrawTextW(hdc, txt, -1, &r,
              DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_END_ELLIPSIS);
    SelectObject(hdc, of);
}

static HPEN MtRoundPen(COLORREF c, int w) {
    LOGBRUSH lb;
    lb.lbStyle = BS_SOLID;
    lb.lbColor = c;
    lb.lbHatch = 0;
    return ExtCreatePen(PS_GEOMETRIC | PS_SOLID | PS_ENDCAP_ROUND
                        | PS_JOIN_ROUND, w, &lb, 0, NULL);
}

static void MtDrawRounded(HDC hdc, const RECT &rc, COLORREF bg,
                          COLORREF border, int rx) {
    HBRUSH b = CreateSolidBrush(bg);
    HPEN pen = CreatePen(PS_SOLID, 1, border);
    HGDIOBJ ob = SelectObject(hdc, pen);
    HGDIOBJ obb = SelectObject(hdc, b);
    RoundRect(hdc, rc.left, rc.top, rc.right, rc.bottom, rx * 2, rx * 2);
    SelectObject(hdc, ob);
    SelectObject(hdc, obb);
    DeleteObject(pen);
    DeleteObject(b);
}

static void MtDrawImageIcon(HDC hdc, int x, int cy) {
    HPEN pen = MtRoundPen(RGB(255, 255, 255), 2);
    HGDIOBJ ob = SelectObject(hdc, pen);
    HGDIOBJ onb = SelectObject(hdc, GetStockObject(NULL_BRUSH));
    RoundRect(hdc, x, cy - 7, x + 18, cy + 7, 4, 4);
    MoveToEx(hdc, x + 3, cy + 4, NULL);
    LineTo(hdc, x + 7, cy - 2);
    LineTo(hdc, x + 10, cy + 1);
    LineTo(hdc, x + 13, cy - 3);
    LineTo(hdc, x + 15, cy + 4);
    SelectObject(hdc, onb);
    SelectObject(hdc, ob);
    DeleteObject(pen);
    HBRUSH wb = CreateSolidBrush(RGB(255, 255, 255));
    HGDIOBJ ow = SelectObject(hdc, wb);
    Ellipse(hdc, x + 11, cy - 4, x + 15, cy);
    SelectObject(hdc, ow);
    DeleteObject(wb);
}

static void MtDrawDlIcon(HDC hdc, int x, int cy) {
    HPEN pen = MtRoundPen(RGB(255, 255, 255), 3);
    HGDIOBJ ob = SelectObject(hdc, pen);
    MoveToEx(hdc, x + 7, cy - 8, NULL);
    LineTo(hdc, x + 7, cy + 3);
    MoveToEx(hdc, x + 2, cy - 2, NULL);
    LineTo(hdc, x + 7, cy + 4);
    LineTo(hdc, x + 12, cy - 2);
    SelectObject(hdc, ob);
    DeleteObject(pen);
    HPEN pen2 = MtRoundPen(RGB(255, 255, 255), 2);
    HGDIOBJ ob2 = SelectObject(hdc, pen2);
    MoveToEx(hdc, x + 0, cy + 8, NULL);
    LineTo(hdc, x + 14, cy + 8);
    SelectObject(hdc, ob2);
    DeleteObject(pen2);
}

static void MtDrawBtn(HDC hdc, const RECT &rc, COLORREF bg,
                      COLORREF border, const wchar_t *txt, HFONT f,
                      int iconKind) {
    if (bg == CLR_EXTR) {
        HRGN rgn = CreateRoundRectRgn(rc.left, rc.top, rc.right + 1,
                                      rc.bottom + 1, 24, 24);
        SelectClipRgn(hdc, rgn);
        int hgt = rc.bottom - rc.top;
        for (int i = 0; i < hgt; i++) {
            int t = hgt > 0 ? (i * 100) / hgt : 0;
            HBRUSH sb = CreateSolidBrush(RGB(255 - 54 * t / 100,
                                             74 - 35 * t / 100,
                                             61 - 33 * t / 100));
            RECT sr = {rc.left, rc.top + i, rc.right, rc.top + i + 1};
            FillRect(hdc, &sr, sb);
            DeleteObject(sb);
        }
        SelectClipRgn(hdc, NULL);
        DeleteObject(rgn);
    } else {
        MtDrawRounded(hdc, rc, bg, border, 12);
    }
    SetBkMode(hdc, TRANSPARENT);
    SetTextColor(hdc, RGB(255, 255, 255));
    int cy = (rc.top + rc.bottom) / 2;
    if (iconKind == 0) {
        RECT r = rc;
        HGDIOBJ of = SelectObject(hdc, f ? f : g_font);
        DrawTextW(hdc, txt, -1, &r,
                  DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_END_ELLIPSIS);
        SelectObject(hdc, of);
        return;
    }
    int iconW = iconKind == 2 ? 16 : 20;
    int x = rc.left + 11;
    if (iconKind == 1)
        MtDrawImageIcon(hdc, x, cy);
    else if (iconKind == 2)
        MtDrawDlIcon(hdc, x, cy);
    RECT r = rc;
    r.left += 11 + iconW + 4;
    r.right -= 8;
    HGDIOBJ of = SelectObject(hdc, f ? f : g_font);
    DrawTextW(hdc, txt, -1, &r,
              DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_END_ELLIPSIS);
    SelectObject(hdc, of);
}

static void MtDrawGlobe(HDC hdc, const RECT &rc, BOOL pressed) {
    int cx = (rc.left + rc.right) / 2;
    int cy = (rc.top + rc.bottom) / 2;
    int r = (rc.right - rc.left) / 2 - 2;
    if (r < 8)
        return;
    HBRUSH bg = CreateSolidBrush(pressed ? CLR_FAB_DN : CLR_FAB);
    HPEN ring = CreatePen(PS_SOLID, 3, CLR_ACC);
    HGDIOBJ ob = SelectObject(hdc, ring);
    HGDIOBJ obb = SelectObject(hdc, bg);
    Ellipse(hdc, cx - r, cy - r, cx + r, cy + r);
    SelectObject(hdc, ob);
    SelectObject(hdc, obb);
    DeleteObject(ring);
    DeleteObject(bg);
    HPEN gp = CreatePen(PS_SOLID, 2, RGB(255, 255, 255));
    HGDIOBJ og = SelectObject(hdc, gp);
    HGDIOBJ onb = SelectObject(hdc, GetStockObject(NULL_BRUSH));
    int gr = r - 7;
    if (gr < 4)
        gr = 4;
    Ellipse(hdc, cx - gr, cy - gr, cx + gr, cy + gr);
    Ellipse(hdc, cx - gr * 55 / 100, cy - gr, cx + gr * 55 / 100, cy + gr);
    MoveToEx(hdc, cx - gr, cy, NULL);
    LineTo(hdc, cx + gr, cy);
    MoveToEx(hdc, cx - gr * 55 / 100, cy - gr, NULL);
    LineTo(hdc, cx - gr * 55 / 100, cy + gr);
    SelectObject(hdc, og);
    SelectObject(hdc, onb);
    DeleteObject(gp);
}

static void MtDrawRefresh(HDC hdc, const RECT &rc, BOOL pressed) {
    int cx = (rc.left + rc.right) / 2;
    int cy = (rc.top + rc.bottom) / 2;
    int r = (rc.right - rc.left) / 2 - 2;
    if (r < 8)
        return;
    HBRUSH bg = CreateSolidBrush(pressed ? CLR_FAB_DN : CLR_FAB);
    HPEN ring = CreatePen(PS_SOLID, 3, CLR_ACC);
    HGDIOBJ ob = SelectObject(hdc, ring);
    HGDIOBJ obb = SelectObject(hdc, bg);
    Ellipse(hdc, cx - r, cy - r, cx + r, cy + r);
    SelectObject(hdc, ob);
    SelectObject(hdc, obb);
    DeleteObject(ring);
    DeleteObject(bg);
    SetBkMode(hdc, TRANSPARENT);
    SetTextColor(hdc, RGB(255, 255, 255));
    HGDIOBJ of = SelectObject(hdc, g_fontFail);
    RECT tr = rc;
    DrawTextW(hdc, L"\u21BB", -1, &tr,
              DT_CENTER | DT_VCENTER | DT_SINGLELINE);
    SelectObject(hdc, of);
}

static const wchar_t MT_FAIL_BODY[] =
    L"\u0645\u0648\u062A\u0648\u0631\u0650 \u0648\u0628\u0650 \u0648\u06CC\u0646\u062F\u0648\u0632 (WebView2) \u0631\u0648\u06CC \u0627\u06CC\u0646 \u0633\u06CC\u0633\u062A\u0645 \u067E\u06CC\u062F\u0627 \u0646\u0634\u062F \u06CC\u0627 \u0627\u062C\u0631\u0627 \u0646\u0634\u062F \u2014 \u0628\u062F\u0648\u0646\u0650 \u0622\u0646 \u0635\u0641\u062D\u0647\u0650 \u0627\u067E \u0628\u0627\u0632 \u0646\u0645\u06CC\u0634\u0648\u062F.\n\n"
    L"1) \u00AB\u062F\u0627\u0646\u0644\u0648\u062F WebView2\u00BB \u0631\u0627 \u0628\u0632\u0646 \u2014 \u0635\u0641\u062D\u0647\u0654 \u0631\u0633\u0645\u06CC\u0650 \u0645\u0627\u06CC\u06A9\u0631\u0648\u0633\u0627\u0641\u062A \u062F\u0631 \u0645\u0631\u0648\u0631\u06AF\u0631 \u0628\u0627\u0632 \u0645\u06CC\u0634\u0648\u062F\u061B \u0646\u0635\u0628\u200C\u06A9\u0646\u0646\u062F\u0647 \u0631\u0627 \u062F\u0627\u0646\u0644\u0648\u062F \u0648 \u0627\u062C\u0631\u0627 \u06A9\u0646 (\u0627\u06CC\u0646\u062A\u0631\u0646\u062A \u0644\u0627\u0632\u0645 \u0627\u0633\u062A).\n"
    L"2) \u0628\u0639\u062F \u0627\u0632 \u067E\u0627\u06CC\u0627\u0646\u0650 \u0646\u0635\u0628\u060C \u00AB\u062A\u0644\u0627\u0634 \u062F\u0648\u0628\u0627\u0631\u0647\u00BB \u0631\u0627 \u0628\u0632\u0646.\n\n"
    L"\u06CC\u0627 \u0647\u0645\u06CC\u0646 \u062D\u0627\u0644\u0627 \u00AB\u0628\u0627\u0632 \u06A9\u0631\u062F\u0646 \u0627\u067E \u062F\u0631 \u0645\u0631\u0648\u0631\u06AF\u0631\u00BB \u0631\u0627 \u0628\u0632\u0646 \u2014 \u0647\u0645\u0647\u0654 \u0627\u0645\u06A9\u0627\u0646\u0627\u062A \u0647\u0645\u0627\u0646\u0627\u0633\u062A.";

static void ShowFailScreen(const char *logReason) {
    g_failMode = TRUE;
    if (logReason != NULL)
        MtLog(logReason);
    LayoutApp();
}

static LRESULT MtOnCtlColor(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    if (msg == WM_CTLCOLOREDIT) {
        HDC hdc = (HDC)wp;
        SetTextColor(hdc, CLR_TXT);
        SetBkColor(hdc, CLR_URLBG);
        return (LRESULT)g_urlBrush;
    }
    if (msg == WM_CTLCOLORBTN) {
        HDC hdc = (HDC)wp;
        if (hwnd == g_hwndBr || hwnd == g_hwndMenu) {
            SetBkColor(hdc, CLR_BRBAR);
            return (LRESULT)g_brBarBrush;
        }
        SetBkColor(hdc, CLR_BAR);
        return (LRESULT)g_barBrush;
    }
    if (msg == WM_CTLCOLORSTATIC) {
        HDC hdc = (HDC)wp;
        HWND h = (HWND)lp;
        if (h == g_lblStatus) {
            SetTextColor(hdc, CLR_CNT);
            SetBkColor(hdc, CLR_BRBAR);
        } else if (h == g_lblFailTitle || h == g_lblFailBody) {
            SetTextColor(hdc, CLR_TXT);
            SetBkColor(hdc, CLR_BAR);
        } else {
            SetTextColor(hdc, CLR_MUT);
            SetBkColor(hdc, CLR_BAR);
        }
        return (LRESULT)g_barBrush;
    }
    return 0;
}

static LRESULT MtOnDrawItem(WPARAM wp, LPARAM lp) {
    (void)wp;
    DRAWITEMSTRUCT *d = (DRAWITEMSTRUCT *)lp;
    if (d == NULL || d->CtlType != ODT_BUTTON)
        return 0;
    if (d->CtlID == ID_BTN_GLOBE) {
        if (g_readerMode)
            MtDrawRefresh(d->hDC, d->rcItem,
                          (d->itemState & ODS_SELECTED) != 0);
        else
            MtDrawGlobe(d->hDC, d->rcItem,
                        (d->itemState & ODS_SELECTED) != 0);
        return TRUE;
    }
    BOOL down = (d->itemState & ODS_SELECTED) != 0;
    if (d->CtlID == ID_MITEM_LINK || d->CtlID == ID_MITEM_DL) {
        wchar_t txt[128];
        GetWindowTextW(d->hwndItem, txt, 127);
        HFONT f = (HFONT)SendMessageW(d->hwndItem, WM_GETFONT, 0, 0);
        COLORREF bg = down ? CLR_NAV_DN : CLR_URLBG;
        MtDrawBtn(d->hDC, d->rcItem, bg, bg, txt, f,
                  d->CtlID == ID_MITEM_LINK ? 1 : 2);
        return TRUE;
    }
    if (d->CtlID == ID_BTN_BACK || d->CtlID == ID_BTN_FWD) {
        wchar_t txt[8];
        GetWindowTextW(d->hwndItem, txt, 7);
        COLORREF bg = down ? CLR_NAV_DN : CLR_NAV;
        MtDrawBtn(d->hDC, d->rcItem, bg, bg, txt, g_fontBold, 0);
        return TRUE;
    }
    if (d->CtlID == ID_BTN_GO) {
        wchar_t txt[128];
        GetWindowTextW(d->hwndItem, txt, 127);
        HFONT f = (HFONT)SendMessageW(d->hwndItem, WM_GETFONT, 0, 0);
        COLORREF bg = down ? CLR_NAV_DN : CLR_NAV;
        MtDrawBtn(d->hDC, d->rcItem, bg, bg, txt, f, 0);
        return TRUE;
    }
    if (d->CtlID == ID_BTN_EXTRACT) {
        wchar_t txt[128];
        GetWindowTextW(d->hwndItem, txt, 127);
        HFONT f = (HFONT)SendMessageW(d->hwndItem, WM_GETFONT, 0, 0);
        COLORREF bg = down ? CLR_EXTR_DN : CLR_EXTR;
        MtDrawBtn(d->hDC, d->rcItem, bg, bg, txt, f, 1);
        return TRUE;
    }
    COLORREF bg;
    if (d->CtlID == ID_BTN_WV2DL) {
        bg = down ? CLR_ACC_DN : CLR_ACC;
    } else {
        bg = down ? CLR_BTN_DN : CLR_BTN;
    }
    wchar_t txt[128];
    GetWindowTextW(d->hwndItem, txt, 127);
    HFONT f = (HFONT)SendMessageW(d->hwndItem, WM_GETFONT, 0, 0);
    MtDrawPill(d->hDC, d->rcItem, bg, txt, f ? f : g_font);
    return TRUE;
}

static WNDPROC g_brBtnProc = NULL;
static LRESULT MtBrBtnProcInner(HWND h, UINT m, WPARAM w, LPARAM l) {
    if (m == WM_SETFOCUS || m == WM_KILLFOCUS) {
        InvalidateRect(h, NULL, FALSE);
        return 0;
    }
    return CallWindowProcW(g_brBtnProc, h, m, w, l);
}
static LRESULT CALLBACK MtBrBtnProc(HWND h, UINT m, WPARAM w, LPARAM l) {
#if MT_HAS_SEH
    __try {
        return MtBrBtnProcInner(h, m, w, l);
    } __except (MtSehLog("brBtn", GetExceptionInformation())) {
        return 0;
    }
#else
    return MtBrBtnProcInner(h, m, w, l);
#endif
}

static LRESULT MenuWndProcInner(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    switch (msg) {
    case WM_CREATE: {
        HINSTANCE hInst = (HINSTANCE)GetWindowLongPtrW(hwnd,
                                                       GWLP_HINSTANCE);
        HWND b1 = CreateWindowExW(0, L"BUTTON",
            L"\u0627\u0633\u062A\u062E\u0631\u0627\u062C \u0628\u0627 \u0644\u06CC\u0646\u06A9",
            WS_CHILD | WS_VISIBLE | BS_OWNERDRAW,
            10, 10, 226, 40, hwnd, (HMENU)(INT_PTR)ID_MITEM_LINK,
            hInst, NULL);
        HWND b2 = CreateWindowExW(0, L"BUTTON",
            L"\u0627\u0633\u062A\u062E\u0631\u0627\u062C \u0628\u0627 \u062F\u0627\u0646\u0644\u0648\u062F",
            WS_CHILD | WS_VISIBLE | BS_OWNERDRAW,
            10, 56, 226, 40, hwnd, (HMENU)(INT_PTR)ID_MITEM_DL,
            hInst, NULL);
        SendMessageW(b1, WM_SETFONT, (WPARAM)g_fontBold, TRUE);
        SendMessageW(b2, WM_SETFONT, (WPARAM)g_fontBold, TRUE);
        return 0;
    }
    case WM_COMMAND: {
        int id = LOWORD(wp);
        if (HIWORD(wp) == 0
                && (id == ID_MITEM_LINK || id == ID_MITEM_DL)) {
            DestroyWindow(hwnd);
            PostMessage(g_hwnd, WM_APP_DO_EXTRACT,
                        (WPARAM)(id == ID_MITEM_LINK ? 1 : 2), 0);
            return 0;
        }
        break;
    }
    case WM_CTLCOLOREDIT:
    case WM_CTLCOLORSTATIC:
    case WM_CTLCOLORBTN:
        return MtOnCtlColor(hwnd, msg, wp, lp);
    case WM_DRAWITEM:
        return MtOnDrawItem(wp, lp);
    case WM_KILLFOCUS:

        if (wp != 0 && IsChild(hwnd, (HWND)wp))
            return 0;
        DestroyWindow(hwnd);
        return 0;
    case WM_ACTIVATE:
        if (LOWORD(wp) == WA_INACTIVE) {
            DestroyWindow(hwnd);
            return 0;
        }
        break;
    case WM_PAINT: {
        PAINTSTRUCT ps;
        HDC hdc = BeginPaint(hwnd, &ps);
        RECT rc;
        GetClientRect(hwnd, &rc);
        HBRUSH bb = CreateSolidBrush(CLR_BRBAR);
        FillRect(hdc, &rc, bb);
        DeleteObject(bb);
        HPEN bp = CreatePen(PS_SOLID, 1, CLR_URLBR);
        HGDIOBJ obp = SelectObject(hdc, bp);
        HGDIOBJ onb = SelectObject(hdc, GetStockObject(NULL_BRUSH));
        RECT fr = {0, 0, rc.right - 1, rc.bottom - 1};
        RoundRect(hdc, fr.left, fr.top, fr.right, fr.bottom, 16, 16);
        SelectObject(hdc, obp);
        SelectObject(hdc, onb);
        DeleteObject(bp);
        EndPaint(hwnd, &ps);
        return 0;
    }
    case WM_DESTROY:
        if (g_hwndMenu == hwnd)
            g_hwndMenu = NULL;
        return 0;
    }
    return DefWindowProcW(hwnd, msg, wp, lp);
}

static LRESULT CALLBACK MenuWndProc(HWND hwnd, UINT msg, WPARAM wp,
                                    LPARAM lp) {
#if MT_HAS_SEH
    __try {
        return MenuWndProcInner(hwnd, msg, wp, lp);
    } __except (MtSehLog("menuWnd", GetExceptionInformation())) {
        return 0;
    }
#else
    return MenuWndProcInner(hwnd, msg, wp, lp);
#endif
}

static void MtCloseExtractMenu(void) {
    if (g_hwndMenu != NULL && IsWindow(g_hwndMenu)) {
        HWND m = g_hwndMenu;
        g_hwndMenu = NULL;
        DestroyWindow(m);
    }
}

static void MtShowExtractMenu(void) {
    if (g_hwndMenu != NULL && IsWindow(g_hwndMenu)) {
        MtCloseExtractMenu();
        return;
    }
    if (g_btnExtract == NULL || g_hwndBr == NULL)
        return;
    RECT rc;
    GetWindowRect(g_btnExtract, &rc);
    int mw = 246, mh = 106;
    int x = rc.right - mw;
    int y = rc.bottom + 6;
    RECT dr;
    SystemParametersInfoW(SPI_GETWORKAREA, 0, &dr, 0);
    if (x < dr.left)
        x = dr.left;
    if (x + mw > dr.right)
        x = dr.right - mw;
    if (y + mh > dr.bottom)
        y = rc.top - mh - 6;
    g_hwndMenu = CreateWindowExW(WS_EX_TOOLWINDOW,
        L"MangaCloudMenuWnd", L"", WS_POPUP,
        x, y, mw, mh, g_hwndBr, NULL, g_hInst, NULL);
    if (g_hwndMenu == NULL)
        return;
    ShowWindow(g_hwndMenu, SW_SHOW);
    SetForegroundWindow(g_hwndMenu);
    SetFocus(g_hwndMenu);
}

static void MtBrCreateControls(HWND hwnd) {
    HINSTANCE hInst = (HINSTANCE)GetWindowLongPtrW(hwnd, GWLP_HINSTANCE);
    g_editUrl = CreateWindowExW(0, L"EDIT", L"",
        WS_CHILD | WS_VISIBLE | ES_AUTOHSCROLL | ES_LEFT,
        0, 9, 400, 28, hwnd,
        (HMENU)(INT_PTR)ID_EDIT_URL, hInst, NULL);
    g_btnGo = CreateWindowExW(0, L"BUTTON",
        L"\u0628\u0631\u0648",
        WS_CHILD | WS_VISIBLE | BS_OWNERDRAW,
        0, 0, 64, 34, hwnd, (HMENU)(INT_PTR)ID_BTN_GO, hInst, NULL);
    g_btnFwd = CreateWindowExW(0, L"BUTTON", L"\u2192",
        WS_CHILD | WS_VISIBLE | BS_OWNERDRAW,
        0, 0, 42, 34, hwnd, (HMENU)(INT_PTR)ID_BTN_FWD, hInst, NULL);
    g_btnBack = CreateWindowExW(0, L"BUTTON", L"\u2190",
        WS_CHILD | WS_VISIBLE | BS_OWNERDRAW,
        0, 0, 42, 34, hwnd, (HMENU)(INT_PTR)ID_BTN_BACK, hInst, NULL);
    g_lblStatus = CreateWindowExW(0, L"STATIC",
        L"\u2026",
        WS_CHILD | WS_VISIBLE | SS_RIGHT | SS_CENTERIMAGE | SS_ENDELLIPSIS,
        0, 0, 110, 34, hwnd, (HMENU)(INT_PTR)ID_LBL_STATUS, hInst, NULL);
    g_btnExtract = CreateWindowExW(0, L"BUTTON",
        L"\u25B6 \u0634\u0631\u0648\u0639 \u0636\u0628\u0637",
        WS_CHILD | WS_VISIBLE | BS_OWNERDRAW,
        0, 0, 118, 34, hwnd, (HMENU)(INT_PTR)ID_BTN_EXTRACT, hInst, NULL);

    SendMessageW(g_editUrl, WM_SETFONT, (WPARAM)g_font, TRUE);
    g_editProc = (WNDPROC)SetWindowLongPtrW(g_editUrl, GWLP_WNDPROC,
                                            (LONG_PTR)MtEditProc);
    SendMessageW(g_btnGo, WM_SETFONT, (WPARAM)g_fontBold, TRUE);
    SendMessageW(g_btnFwd, WM_SETFONT, (WPARAM)g_fontBold, TRUE);
    SendMessageW(g_btnBack, WM_SETFONT, (WPARAM)g_fontBold, TRUE);
    SendMessageW(g_btnExtract, WM_SETFONT, (WPARAM)g_fontBold, TRUE);
    SendMessageW(g_lblStatus, WM_SETFONT, (WPARAM)g_font, TRUE);
    HWND brBtns[4] = {g_btnGo, g_btnFwd, g_btnBack, g_btnExtract};
    for (int i = 0; i < 4; i++) {
        if (brBtns[i] == NULL)
            continue;
        if (g_brBtnProc == NULL)
            g_brBtnProc = (WNDPROC)GetWindowLongPtrW(brBtns[i],
                                                     GWLP_WNDPROC);
        SetWindowLongPtrW(brBtns[i], GWLP_WNDPROC,
                          (LONG_PTR)MtBrBtnProc);
    }
    MtLog("br controls created");
}

static LRESULT BrWndProcInner(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    switch (msg) {
    case WM_CREATE:
        MtBrCreateControls(hwnd);
        return 0;
    case WM_CLOSE:

        MtResetRecordUi();
        g_recNet.clear();
        g_recNetSeen.clear();
        g_foundStore.clear();
        g_foundSeen.clear();
        g_domOrder.clear();
        g_selUrls.clear();
        MtHideBrowser();
        return 0;
    case WM_COMMAND: {
        int id = LOWORD(wp);
        int code = HIWORD(wp);
        if (code == 0) {
            if (id == ID_BTN_GO) {
                OnGo();
                return 0;
            }
            if (id == ID_BTN_BACK) {
                if (g_webBr != NULL)
                    g_webBr->GoBack();
                return 0;
            }
            if (id == ID_BTN_FWD) {
                if (g_webBr != NULL)
                    g_webBr->GoForward();
                return 0;
            }
            if (id == ID_BTN_EXTRACT) {
                MtOnExtractBtn();
                return 0;
            }
        }
        break;
    }
    case WM_CTLCOLOREDIT:
    case WM_CTLCOLORSTATIC:
    case WM_CTLCOLORBTN:
        return MtOnCtlColor(hwnd, msg, wp, lp);
    case WM_DRAWITEM:
        return MtOnDrawItem(wp, lp);
    case WM_MOVE:
        if (g_brCtl != NULL)
            g_brCtl->NotifyParentWindowPositionChanged();
        return 0;
    case WM_SIZE:
        if (!g_inBrShow)
            LayoutBrowser();
        return 0;
    case WM_GETMINMAXINFO: {
        MINMAXINFO *mmi = (MINMAXINFO *)lp;
        if (mmi != NULL) {
            mmi->ptMinTrackSize.x = 480;
            mmi->ptMinTrackSize.y = 360;
        }
        return 0;
    }
    case WM_PAINT: {
        PAINTSTRUCT ps;
        HDC hdc = BeginPaint(hwnd, &ps);
        RECT rc;
        GetClientRect(hwnd, &rc);
        HBRUSH bb = CreateSolidBrush(CLR_BRBAR);
        RECT barRc = {0, 0, rc.right, BR_BAR_H};
        FillRect(hdc, &barRc, bb);
        DeleteObject(bb);
        HPEN bp = CreatePen(PS_SOLID, 1, CLR_BRBRD);
        HGDIOBJ obp = SelectObject(hdc, bp);
        MoveToEx(hdc, 0, BR_BAR_H, NULL);
        LineTo(hdc, rc.right, BR_BAR_H);
        SelectObject(hdc, obp);
        DeleteObject(bp);
        FillRect(hdc, &ps.rcPaint, g_barBrush);
        if (g_urlRing.right > g_urlRing.left) {
            HPEN pen = CreatePen(PS_SOLID, 1, CLR_URLBR);
            HGDIOBJ ob = SelectObject(hdc, pen);
            HGDIOBJ obb = SelectObject(hdc, GetStockObject(NULL_BRUSH));
            int rr = (g_urlRing.bottom - g_urlRing.top) / 2;
            if (rr < 8)
                rr = 8;
            RoundRect(hdc, g_urlRing.left - 1, g_urlRing.top - 1,
                      g_urlRing.right + 1, g_urlRing.bottom + 1,
                      rr * 2, rr * 2);
            SelectObject(hdc, ob);
            SelectObject(hdc, obb);
            DeleteObject(pen);
        }
        if (g_progress > 0 && rc.right > 0) {
            RECT pr = {0, BR_BAR_H + 1,
                       (rc.right * g_progress) / 100,
                       BR_BAR_H + 1 + PROG_H};
            HBRUSH b = CreateSolidBrush(CLR_EXTR);
            FillRect(hdc, &pr, b);
            DeleteObject(b);
        }
        EndPaint(hwnd, &ps);
        return 0;
    }
    case WM_DESTROY:
        return 0;
    default:
        return DefWindowProcW(hwnd, msg, wp, lp);
    }
    return DefWindowProcW(hwnd, msg, wp, lp);
}

static LRESULT CALLBACK BrWndProc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
#if MT_HAS_SEH
    __try {
        return BrWndProcInner(hwnd, msg, wp, lp);
    } __except (MtSehLog("brWnd", GetExceptionInformation())) {
        return 0;
    }
#else
    return BrWndProcInner(hwnd, msg, wp, lp);
#endif
}

static LRESULT WndProcInner(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    switch (msg) {
    case WM_APP_CREATCTL: {
        if (g_env != NULL && g_webApp == NULL && g_appCtl == NULL) {
            MtLog("creating app controller (on main window)");
            HRESULT hr = g_env->CreateCoreWebView2Controller(hwnd, &g_ctlApp);
            MtLogHr("create ctl(app)", hr);
            if (FAILED(hr)) {
                g_failMode = TRUE;
                LayoutApp();
            }
        }
        return 0;
    }
    case WM_APP_BRREADY: {
        if (g_brPending) {
            char bb[160];
            g_brPending = FALSE;
            sprintf(bb,
                    "BRREADY: webBr=%p brCtl=%p hwndBr=%p tgtLen=%u",
                    (void *)g_webBr, (void *)g_brCtl, (void *)g_hwndBr,
                    (unsigned)g_brTarget.size());
            MtLog(bb);
            MtShowBrowser();
            if (g_webBr != NULL && !g_brTarget.empty()) {
                MtLog("BRREADY: navigate target");
                g_webBr->Navigate(g_brTarget.c_str());
                g_brTarget.clear();
            }
            LayoutBrowser();
            MtLog("BRREADY: done");
        }
        return 0;
    }
    case WM_APP_MENU_SHOW: {
        if (!g_selUrls.empty() && g_lblStatus != NULL)
            SetWindowTextW(g_lblStatus,
                (std::to_wstring(g_selUrls.size())
                 + L" \u0639\u06A9\u0633 \u0627\u0646\u062A\u062E\u0627\u0628"
                   L" \u0634\u062F").c_str());
        MtShowExtractMenu();
        return 0;
    }
    case WM_APP_DO_EXTRACT: {
        int choice = (int)wp;
        MtCloseExtractMenu();
        if (!g_selUrls.empty()) {

            if (g_selUrls.size() == 1 && MtIsMangaPlusUrl(g_selUrls[0]))
                choice = 1;
            if (choice == 1)
                MtFillFieldAndClose(g_selUrls);
            else
                MtStartDownload(g_selUrls);
        } else if (g_webBr != NULL) {
            if (choice == 1)
                g_webBr->ExecuteScript(MT_COLLECT_JS, &g_execExtract);
            else
                g_webBr->ExecuteScript(MT_COLLECT_JS, &g_execDlList);
        }
        return 0;
    }
    case WM_APP_FILL_DONE: {
        MtHideBrowser();
        if (wp == 1 && g_fillCount > 0) {
            wchar_t mb[96];
            swprintf(mb, 96,
                L"%d \u0644\u06CC\u0646\u06A9 \u0639\u06A9\u0633 \u062F\u0631"
                L" \u0641\u06CC\u0644\u062F\u0650 \u0648\u0631\u0648\u062F\u06CC"
                L" \u0646\u0634\u0633\u062A \u2014 \u00AB\u0634\u0631\u0648\u0639"
                L" \u062A\u0631\u062C\u0645\u0647\u00BB \u0631\u0627 \u0628\u0632\u0646",
                g_fillCount);
            MessageBoxW(g_hwnd, mb,
                L"\u0645\u0627\u0646\u06AF\u0627 \u06A9\u0644\u0648\u062F",
                MB_OK | MB_ICONINFORMATION | MB_RTLREADING | MB_RIGHT);
        }
        return 0;
    }
    case WM_APP_NAV_FILL: {
        if (g_webApp != NULL && !g_fillUrl.empty())
            g_webApp->Navigate(g_fillUrl.c_str());
        return 0;
    }
    case WM_APP_DL_STEP: {
        int slot = (int)wp;
        if (slot >= 0 && slot < 3 && g_webBr != NULL
                && g_dlNext < g_dlUrls.size()) {
            g_dlSlotIdx[slot] = (int)g_dlNext;
            g_webBr->ExecuteScript(
                MtDlOneJs(MtJsQuote(g_dlUrls[g_dlNext])).c_str(),
                slot == 0 ? &g_execDlStep
                : (slot == 1 ? &g_execDlStepB : &g_execDlStepC));
            g_dlNext++;
        }
        return 0;
    }
    case WM_APP_UP_START: {
        if (g_dlOk > 0 && g_webApp != NULL) {
            g_upPolls = 0;
            g_upFired = 0;
            g_upNextIdx = 0;
            g_webApp->ExecuteScript(
                L"(function(){try{window.__mtUp={ok:0,paths:[]}}"
                L"catch(e){}})()",
                &g_execNoop);
            SetWindowTextW(g_lblStatus,
                L"\u2B06 \u062F\u0631 \u062D\u0627\u0644\u0650 "
                L"\u0622\u067E\u0644\u0648\u062F \u0628\u0647 "
                L"\u0633\u0631\u0648\u0631\u2026");
            MtFireUploadBatch();
            g_webApp->ExecuteScript(MtUpPollJs(g_dlOk).c_str(),
                                    &g_execUpPoll);
        }
        return 0;
    }
    case WM_APP_UP_POLL: {
        int ok = (int)wp;
        if (g_webApp == NULL)
            return 0;
        if (ok >= g_dlOk || g_upPolls >= 1500) {
            PostMessage(g_hwnd, WM_APP_UP_FINISH, 0, 0);
        } else {
            if (ok >= g_upFired)
                MtFireUploadBatch();
            g_webApp->ExecuteScript(MtUpPollJs(g_dlOk).c_str(),
                                    &g_execUpPoll);
        }
        return 0;
    }
    case WM_APP_UP_FINISH: {
        if (g_webApp != NULL)
            g_webApp->ExecuteScript(MT_UP_FILL_JS, &g_execNoop);
        MtResetRecordUi();
        MtHideBrowser();
        return 0;
    }
    case WM_APP_DL_FAIL: {
        MessageBoxW(g_hwnd,
            L"\u0647\u06CC\u0686 \u0639\u06A9\u0633\u06CC \u062F\u0627"
            L"\u0646\u0644\u0648\u062F \u0646\u0634\u062F",
            L"\u0645\u0627\u0646\u06AF\u0627 \u06A9\u0644\u0648\u062F",
            MB_OK | MB_ICONINFORMATION | MB_RTLREADING | MB_RIGHT);
        MtResetRecordUi();
        MtHideBrowser();
        return 0;
    }
    case WM_APP_DL_EMPTY: {
        MessageBoxW(g_hwnd,
            L"\u0639\u06A9\u0633\u06CC \u067E\u06CC\u062F\u0627 \u0646\u0634\u062F \u2014 "
            L"\u0627\u0648\u0644 \u0641\u0635\u0644 \u0631\u0627 \u0628\u0627\u0632 \u06A9\u0646 "
            L"\u0648 \u062A\u0627 \u0622\u062E\u0631\u0650 \u0635\u0641\u062D\u0647 "
            L"\u0627\u0633\u06A9\u0631\u0648\u0644 \u06A9\u0646",
            L"\u0645\u0627\u0646\u06AF\u0627 \u06A9\u0644\u0648\u062F",
            MB_OK | MB_ICONINFORMATION | MB_RTLREADING | MB_RIGHT);
        return 0;
    }
    case WM_APP_SHOW_FOLDERS: {
        MtShowFolderOverlay();
        return 0;
    }
    case WM_COMMAND: {
        int id = LOWORD(wp);
        int code = HIWORD(wp);
        if (code == 0) {
            if (id == ID_BTN_GLOBE) {
                if (g_readerMode) {
                    if (g_webApp != NULL)
                        g_webApp->ExecuteScript(MT_READER_REFRESH_JS,
                                                &g_execNoop);
                } else {
                    MtOpenBrowserUi();
                }
                return 0;
            }
            if (id == ID_BTN_WV2DL) {
                MtLog("open WebView2 download page");
                ShellExecuteW(NULL, L"open",
                    L"https://developer.microsoft.com/microsoft-edge/webview2/",
                    NULL, NULL, SW_SHOWNORMAL);
                return 0;
            }
            if (id == ID_BTN_SYSBR) {
                ShellExecuteW(NULL, L"open", APP_URL,
                              NULL, NULL, SW_SHOWNORMAL);
                return 0;
            }
            if (id == ID_BTN_RETRY) {
                MtLog("retry pressed");
                g_failMode = FALSE;
                LayoutApp();
                TryStartEnv();
                return 0;
            }
        }
        break;
    }
    case WM_CTLCOLOREDIT:
    case WM_CTLCOLORSTATIC:
    case WM_CTLCOLORBTN:
        return MtOnCtlColor(hwnd, msg, wp, lp);
    case WM_DRAWITEM:
        return MtOnDrawItem(wp, lp);
    case WM_TIMER: {
        if (wp == TIMER_PROGRESS) {
            if (g_loading) {
                g_progress += (g_progress < 70) ? 5
                             : (g_progress < 90) ? 3 : 1;
                if (g_progress > 96)
                    g_progress = 96;
            } else if (g_doneTicks > 0) {
                g_doneTicks--;
                if (g_doneTicks == 0) {
                    g_progress = 0;
                    KillTimer(hwnd, TIMER_PROGRESS);
                }
            } else {
                g_progress = 0;
                KillTimer(hwnd, TIMER_PROGRESS);
            }
            if (g_hwndBr != NULL && IsWindowVisible(g_hwndBr))
                InvalidateRect(g_hwndBr, NULL, FALSE);
            return 0;
        }
        if (wp == TIMER_RECOUNT) {
            if (!g_failMode && g_btnGlobe != NULL && g_webApp != NULL) {
                SetWindowPos(g_btnGlobe, HWND_TOP, 0, 0, 0, 0,
                             SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE);
            }
            if (g_webBr != NULL && g_hwndBr != NULL
                    && IsWindowVisible(g_hwndBr)) {
                if (g_recording && g_lblStatus != NULL) {
                    int n = MtRecCount();
                    if (n != g_netShown) {
                        g_netShown = n;
                        SetWindowTextW(g_lblStatus,
                            (L"\u25CF " + std::to_wstring(n)
                             + L" \u0639\u06A9\u0633 \u0636\u0628\u0637"
                               L" \u0634\u062F").c_str());
                    }
                }
                if (!g_loading)
                    Wv2Recount();
            }
            return 0;
        }
        if (wp == TIMER_SMOKE_BR) {
            KillTimer(hwnd, TIMER_SMOKE_BR);
            MtLog("smoke: auto globe click — opening browser window");
            MtOpenBrowserUi();
            return 0;
        }
        if (wp == TIMER_READER) {
            if (!g_failMode && g_webApp != NULL)
                g_webApp->ExecuteScript(MT_READER_WATCH_JS,
                                        &g_execReaderWatch);
            return 0;
        }
        break;
    }
    case WM_MOVE:
        if (g_appCtl != NULL)
            g_appCtl->NotifyParentWindowPositionChanged();
        return 0;
    case WM_SIZE:
        LayoutApp();
        return 0;
    case WM_GETMINMAXINFO: {
        MINMAXINFO *mmi = (MINMAXINFO *)lp;
        if (mmi != NULL) {
            mmi->ptMinTrackSize.x = 520;
            mmi->ptMinTrackSize.y = 380;
        }
        return 0;
    }
    case WM_PAINT: {
        PAINTSTRUCT ps;
        HDC hdc = BeginPaint(hwnd, &ps);
        RECT rc;
        GetClientRect(hwnd, &rc);
        FillRect(hdc, &rc, g_barBrush);
        EndPaint(hwnd, &ps);
        return 0;
    }
    case WM_DESTROY:
        KillTimer(hwnd, TIMER_PROGRESS);
        KillTimer(hwnd, TIMER_RECOUNT);
        KillTimer(hwnd, TIMER_READER);
        if (g_hwndBr != NULL) {
            DestroyWindow(g_hwndBr);
            g_hwndBr = NULL;
        }
        PostQuitMessage(0);
        return 0;
    default:
        return DefWindowProcW(hwnd, msg, wp, lp);
    }
    return DefWindowProcW(hwnd, msg, wp, lp);
}

static LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
#if MT_HAS_SEH
    __try {
        return WndProcInner(hwnd, msg, wp, lp);
    } __except (MtSehLog("mainWnd", GetExceptionInformation())) {
        return 0;
    }
#else
    return WndProcInner(hwnd, msg, wp, lp);
#endif
}

static BOOL MtIsMangaPlusUrl(const std::wstring &u) {
    std::wstring s;
    s.reserve(u.size());
    for (size_t i = 0; i < u.size(); i++) {
        WCHAR c = u[i];
        if (c >= L'A' && c <= L'Z')
            c = c - L'A' + L'a';
        s += c;
    }
    size_t p = s.find(L"://");
    if (p == std::wstring::npos)
        return FALSE;
    std::wstring rest = s.substr(p + 3);
    size_t cut = rest.find(L'/');
    std::wstring host = (cut == std::wstring::npos)
        ? rest : rest.substr(0, cut);
    if (host != L"mangaplus.shueisha.co.jp"
            && host != L"www.mangaplus.shueisha.co.jp")
        return FALSE;
    return rest.compare(0, 8, L"/viewer/") == 0;
}

static void MtFireUploadBatch(void) {
    if (g_webApp == NULL)
        return;
    int firedNow = 0;
    while (g_upFired < g_dlOk && firedNow < 4) {
        while (g_upNextIdx < (int)g_dlData.size()
                && g_dlData[g_upNextIdx].empty())
            g_upNextIdx++;
        if (g_upNextIdx >= (int)g_dlData.size())
            break;
        g_webApp->ExecuteScript(
            MtUpOneJs(g_upFired,
                      MtJsQuote(g_dlData[g_upNextIdx])).c_str(),
            &g_execNoop);
        g_upFired++;
        g_upNextIdx++;
        firedNow++;
    }
}

static void MtFillFieldAndClose(const std::vector<std::wstring> &links) {
    std::wstring payload;
    for (size_t i = 0; i < links.size(); i++) {
        if (i)
            payload += L'\n';
        payload += links[i];
    }
    g_fillCount = (int)links.size();
    g_fillUrl = std::wstring(APP_URL) + L"#imgs="
                + MtWideFromAscii(MtUrlEncode(payload));
    if (g_webApp != NULL) {
        std::wstring js = L"(function(){try{if(window.__mtFillLinks){"
                          L"window.__mtFillLinks(" + MtJsQuote(payload) + L");"
                          L"return 1}return 0}"
                          L"catch(e){return 0}})()";
        g_webApp->ExecuteScript(js.c_str(), &g_execFill);
    }
    MtResetRecordUi();
}

static void MtResetRecordUi(void) {
    g_recording = FALSE;
    g_netShown = -1;
    if (g_btnExtract != NULL)
        SetWindowTextW(g_btnExtract,
            L"\u25B6 \u0634\u0631\u0648\u0639 \u0636\u0628\u0637");
}

static void MtOnExtractBtn(void) {
    MtCloseExtractMenu();
    if (g_webBr == NULL || g_btnExtract == NULL)
        return;
    if (!g_recording) {
        g_recording = TRUE;
        g_recNet.clear();
        g_recNetSeen.clear();
        g_foundStore.clear();
        g_foundSeen.clear();
        g_domOrder.clear();
        g_selUrls.clear();
        g_netShown = -1;
        SetWindowTextW(g_btnExtract, L"\U0001F5BC \u0627\u0633\u062A\u062E\u0631\u0627\u062C");
        if (g_lblStatus != NULL)
            SetWindowTextW(g_lblStatus, L"\u062F\u0631 \u062D\u0627\u0644 \u0636\u0628\u0637\u2026 \u0635\u0641\u062D\u0647 \u0641\u0635\u0644 \u0631\u0627 \u0648\u0631\u0642 \u0628\u0632\u0646");
        MtLog("recording started");
        g_webBr->AddScriptToExecuteOnDocumentCreated(MT_NET_HOOK_JS,
                                                      &g_noopScript);
        g_webBr->Reload();
        return;
    }
    if (g_lblStatus != NULL)
        SetWindowTextW(g_lblStatus, L"\u2026 \u062F\u0631 \u062D\u0627\u0644 \u0622\u0645\u0627\u062F\u0647\u200C\u0633\u0627\u0632\u06CC");
    if (MtIsMangaPlusUrl(g_lastSite)) {

        std::vector<std::wstring> one;
        one.push_back(g_lastSite);
        g_selUrls = one;
        if (g_lblStatus != NULL)
            SetWindowTextW(g_lblStatus,
                L"\u0641\u0635\u0644\u0650 \u0645\u0627\u0646\u06AF\u0627\u067E\u0644\u0627\u0633 \u2014 "
                L"\u0631\u0648\u0634\u0650 \u0627\u0633\u062A\u062E\u0631\u0627\u062C "
                L"\u0631\u0627 \u0627\u0646\u062A\u062E\u0627\u0628 \u06A9\u0646");
        PostMessage(g_hwnd, WM_APP_MENU_SHOW, 0, 0);
        return;
    }
    g_webBr->ExecuteScript(MT_COLLECT_JS, &g_execCollectStore);
}

static const wchar_t *MT_FOLDER_OVERLAY_JS =
L"(function(){"
L"try{"
L"var URLS=__MT_URLS__;"
L"var old=document.getElementById('mtFoldOv');"
L"if(old&&old.parentNode)old.parentNode.removeChild(old);"
L"function folderOf(u){"
L"if(String(u).indexOf('blob:')===0)return 'blob:';"
L"try{var a=document.createElement('a');a.href=u;"
L"var p=a.pathname||'/';var c=p.lastIndexOf('/');"
L"p=c>=0?p.slice(0,c+1):'/';"
L"return a.protocol+'//'+a.hostname+p;"
L"}catch(e){return String(u).split('#')[0].split('?')[0]}}"
L"function shortF(f){"
L"if(f==='blob:')return '\u062F\u0631\u0648\u0646 \u0635\u0641\u062D\u0647 (\u0631\u0645\u0632\u06AF\u0634\u0627\u06CC\u06CC\u200C\u0634\u062F\u0647)';"
L"f=String(f).replace(/^https?:\\/\\//,'');"
L"if(f.length>46)f=f.slice(0,20)+'\u2026'+f.slice(-24);"
L"return f}"
L"var folders={},order=[],rank={};"
L"for(var i=0;i<URLS.length;i++){"
L"rank[URLS[i]]=i+1;"
L"var f=folderOf(URLS[i]);"
L"if(!folders[f]){folders[f]=[];order.push(f)}"
L"folders[f].push(URLS[i])}"
L"order.sort(function(a,b){return folders[b].length-folders[a].length});"
L"var picks={};"
L"for(var j=0;j<order.length;j++)picks[order[j]]={};"
L"function addAll(fk){var a=folders[fk];"
L"for(var k=0;k<a.length;k++)picks[fk][a[k]]=1}"
L"var anyDef=false;"
L"for(var j2=0;j2<order.length;j2++){"
L"if(folders[order[j2]].length>=2){addAll(order[j2]);anyDef=true}}"
L"if(!anyDef&&order.length)addAll(order[0]);"
L"function mk(t){return document.createElement(t)}"
L"function imgSafe(u){return String(u).split(String.fromCharCode(39)).join('%27').split('\"').join('%22')}"
L"function showFull(u){"
L"var old=document.getElementById('mtFullOv');"
L"if(old&&old.parentNode)old.parentNode.removeChild(old);"
L"var fv=mk('div');fv.id='mtFullOv';"
L"fv.style.position='fixed';fv.style.top='0';fv.style.left='0';"
L"fv.style.right='0';fv.style.bottom='0';"
L"fv.style.zIndex='2147483647';"
L"fv.style.background='rgba(4,6,10,.96)';"
L"fv.style.display='flex';fv.style.alignItems='center';"
L"fv.style.justifyContent='center';"
L"var wrap=mk('div');"
L"wrap.style.position='relative';wrap.style.maxWidth='96vw';"
L"wrap.style.maxHeight='92vh';wrap.style.display='flex';"
L"wrap.style.alignItems='center';wrap.style.justifyContent='center';"
L"var im=mk('img');"
L"im.style.maxWidth='96vw';im.style.maxHeight='92vh';"
L"im.style.objectFit='contain';"
L"im.style.borderRadius='10px';"
L"im.style.boxShadow='0 24px 70px rgba(0,0,0,.85)';"
L"im.style.background='#10141c';"
L"var ld=mk('div');"
L"ld.textContent='\u2026 \u062F\u0631 \u062D\u0627\u0644 \u0628\u0627\u0631\u06AF\u0630\u0627\u0631\u06CC';"
L"ld.style.position='absolute';ld.style.top='10px';"
L"ld.style.left='0';ld.style.right='0';ld.style.textAlign='center';"
L"ld.style.color='#8a93a8';ld.style.fontSize='12.5px';"
L"var errm=mk('div');"
L"errm.style.display='none';errm.style.color='#ffb4ad';"
L"errm.style.fontSize='12.5px';errm.style.textAlign='center';"
L"errm.style.maxWidth='82vw';errm.style.padding='10px';"
L"errm.style.direction='rtl';"
L"var x=mk('button');x.type='button';x.textContent='\u2715';"
L"x.style.position='fixed';x.style.top='14px';x.style.left='14px';"
L"x.style.width='42px';x.style.height='42px';"
L"x.style.borderRadius='12px';x.style.border='1px solid #2a3242';"
L"x.style.background='rgba(23,27,36,.92)';x.style.color='#e7ebf3';"
L"x.style.fontSize='17px';x.style.fontWeight='700';"
L"x.style.cursor='pointer';x.style.fontFamily='Tahoma,Arial,sans-serif';"
L"var tip=mk('div');"
L"tip.textContent='\u0628\u0631\u0627\u06CC \u0628\u0633\u062A\u0646 \u0627\u06CC\u0646\u062C\u0627 \u06A9\u0644\u06CC\u06A9 \u06A9\u0646';"
L"tip.style.position='fixed';tip.style.bottom='12px';"
L"tip.style.left='0';tip.style.right='0';"
L"tip.style.textAlign='center';tip.style.color='#8a93a8';"
L"tip.style.fontSize='11.5px';tip.style.zIndex='2147483647';"
L"tip.style.fontFamily='Tahoma,Arial,sans-serif';"
L"var bornAt=Date.now();var stg=0;"
L"function closeFv(){try{if(fv.parentNode)fv.parentNode.removeChild(fv)}catch(e){}}"
L"function failMsg(){ld.style.display='none';"
L"try{im.style.display='none'}catch(e){}"
L"errm.textContent='\u062A\u0635\u0648\u06CC\u0631 \u0628\u0627\u0631\u06AF\u0630\u0627\u0631\u06CC \u0646\u0634\u062F \u2014 \u0633\u0627\u06CC\u062A \u0627\u062C\u0627\u0632\u0647\u0654 \u0646\u0645\u0627\u06CC\u0634 \u0645\u0633\u062A\u0642\u06CC\u0645 \u0646\u0645\u06CC\u062F\u0647\u062F';"
L"errm.style.display=''}"
L"im.onload=function(){ld.style.display='none';errm.style.display='none'};"
L"im.onerror=function(){"
L"stg++;"
L"if(stg===1){"
L"ld.textContent='\u2026 \u062A\u0644\u0627\u0634 \u0645\u062C\u062F\u062F';"
L"try{im.referrerPolicy='no-referrer'}catch(e){}"
L"try{im.src=String(u)}catch(e){failMsg()}"
L"return}"
L"if(stg===2){"
L"ld.textContent='\u2026 \u062A\u0644\u0627\u0634 \u0645\u062C\u062F\u062F';"
L"try{"
L"fetch(String(u),{credentials:'include'}).then(function(r){"
L"return r.ok?r.blob():null}).then(function(b){"
L"if(!b)throw 0;"
L"var ur=URL.createObjectURL(b);"
L"im.onload=function(){ld.style.display='none';"
L"try{URL.revokeObjectURL(ur)}catch(e){}};"
L"im.onerror=failMsg;"
L"im.src=ur}).catch(failMsg)"
L"}catch(e){failMsg()}"
L"return}"
L"failMsg()};"
L"fv.onclick=function(){"
L"if(Date.now()-bornAt<350)return;"
L"closeFv()};"
L"x.onclick=function(ev){ev.stopPropagation();closeFv()};"
L"im.onclick=function(ev){ev.stopPropagation()};"
L"wrap.appendChild(im);wrap.appendChild(ld);wrap.appendChild(errm);"
L"fv.appendChild(wrap);fv.appendChild(x);fv.appendChild(tip);"
L"(document.body||document.documentElement).appendChild(fv);"
L"im.src=String(u)}"
L"function armHold(el,u){"
L"var ht=null;"
L"function kill(){if(ht){clearTimeout(ht);ht=null}}"
L"function fire(){kill();"
L"try{el.__held=1}catch(e){}"
L"showFull(u)}"
L"function down(){kill();ht=setTimeout(fire,320)}"
L"try{"
L"el.style.webkitUserSelect='none';el.style.userSelect='none';"
L"el.style.webkitTouchCallout='none';"
L"try{el.style.touchAction='pan-y'}catch(e2){}"
L"el.addEventListener('pointerdown',function(ev){"
L"try{if(ev.button!=null&&ev.button!==0)return}catch(e){}"
L"try{ev.stopPropagation()}catch(e){}"
L"down()});"
L"if(!window.PointerEvent){"
L"el.addEventListener('mousedown',function(ev){"
L"try{if(ev.button!==0)return}catch(e){}"
L"down()});"
L"el.addEventListener('touchstart',function(){down()},{passive:true})}"
L"var ks=['pointerup','pointerleave','pointercancel','mouseup','mouseleave','touchend','touchcancel'];"
L"for(var k=0;k<ks.length;k++)el.addEventListener(ks[k],kill);"
L"el.addEventListener('contextmenu',function(ev){"
L"try{ev.preventDefault()}catch(e){}"
L"try{ev.stopPropagation()}catch(e){}"
L"fire()});"
L"el.addEventListener('dragstart',function(ev){"
L"try{ev.preventDefault()}catch(e){}});"
L"}catch(e){}}"
L"function thumb(el,u){try{"
L"el.style.position='relative';el.style.overflow='hidden';"
L"var tim=mk('img');tim.loading='lazy';tim.decoding='async';"
L"tim.style.position='absolute';tim.style.top='0';tim.style.left='0';"
L"tim.style.width='100%';tim.style.height='100%';"
L"tim.style.objectFit='cover';tim.style.borderRadius='10px';"
L"tim.style.background='#232b3b';tim.style.display='block';"
L"tim.onerror=function(){try{"
L"if(!tim.__r){tim.__r=1;tim.referrerPolicy='no-referrer';tim.src=u}"
L"}catch(e){}};"
L"try{tim.src=String(u)}catch(e){}"
L"el.appendChild(tim)}catch(e){}}"
L"var ov=mk('div');ov.id='mtFoldOv';"
L"ov.style.position='fixed';ov.style.top='0';ov.style.left='0';"
L"ov.style.right='0';ov.style.bottom='0';"
L"ov.style.zIndex='2147483645';"
L"ov.style.background='rgba(0,0,0,.55)';"
L"ov.style.fontFamily='Tahoma,Arial,sans-serif';"
L"ov.style.display='flex';ov.style.alignItems='center';"
L"ov.style.justifyContent='center';ov.style.direction='rtl';"
L"var box=mk('div');"
L"box.style.background='linear-gradient(180deg,#171b24,#10141c)';"
L"box.style.border='1px solid #2a3242';"
L"box.style.borderRadius='18px';box.style.padding='16px';"
L"box.style.boxShadow='0 24px 60px rgba(0,0,0,.7)';"
L"box.style.display='flex';box.style.flexDirection='column';"
L"box.style.gap='12px';box.style.width='min(640px,94vw)';"
L"box.style.maxHeight='80vh';box.style.boxSizing='border-box';"
L"var h=mk('div');"
L"h.style.display='flex';h.style.alignItems='center';h.style.gap='8px';"
L"var tt=mk('div');tt.style.flex='1';tt.style.minWidth='0';"
L"var t1=mk('div');"
L"t1.textContent='\u067E\u0648\u0634\u0647\u200C\u0647\u0627\u06CC \u0639\u06A9\u0633 ('+order.length+')';"
L"t1.style.fontWeight='800';t1.style.fontSize='15px';"
L"t1.style.color='#e7ebf3';"
L"var t2=mk('div');"
L"t2.textContent='\u06A9\u0644\u06CC\u06A9 = \u0627\u0646\u062A\u062E\u0627\u0628 \u2022 \u0646\u06AF\u0647\u200C\u062F\u0627\u0634\u062A\u0646 \u0631\u0648\u06CC \u0639\u06A9\u0633 = \u067E\u06CC\u0634\u200C\u0646\u0645\u0627\u06CC\u0634 \u06A9\u0627\u0645\u0644';"
L"t2.style.fontSize='11.5px';t2.style.color='#8a93a8';"
L"t2.style.marginTop='2px';"
L"tt.appendChild(t1);tt.appendChild(t2);h.appendChild(tt);"
L"function mkBtn(txt){var b=mk('button');b.type='button';"
L"b.textContent=txt;b.style.border='0';b.style.background='#2d3649';"
L"b.style.color='#c8ceda';b.style.fontFamily='inherit';"
L"b.style.fontSize='11.5px';b.style.fontWeight='700';"
L"b.style.borderRadius='10px';b.style.padding='5px 10px';"
L"b.style.cursor='pointer';return b}"
L"var allB=mkBtn('\u0647\u0645\u0647'),nonB=mkBtn('\u0647\u06CC\u0686');"
L"allB.style.marginLeft='6px';"
L"h.appendChild(allB);h.appendChild(nonB);"
L"box.appendChild(h);"
L"var listEl=mk('div');"
L"listEl.style.overflow='auto';listEl.style.display='flex';"
L"listEl.style.flexDirection='column';listEl.style.gap='8px';"
L"listEl.style.paddingTop='10px';listEl.style.minWidth='0';"
L"box.appendChild(listEl);"
L"var rows=[];"
L"for(var fi=0;fi<order.length;fi++){"
L"(function(idx){"
L"var fk=order[idx];var arr=folders[fk];"
L"var row=mk('div');"
L"row.style.background='#1a1f2b';row.style.border='2px solid #232b3b';"
L"row.style.borderRadius='14px';row.style.padding='10px 12px';"
L"row.style.display='flex';row.style.flexDirection='column';"
L"row.style.gap='8px';row.style.cursor='pointer';"
L"row.style.boxSizing='border-box';"
L"var top=mk('div');"
L"top.style.display='flex';top.style.alignItems='center';"
L"top.style.gap='10px';"
L"var cb=mk('input');cb.type='checkbox';"
L"cb.style.width='17px';cb.style.height='17px';"
L"cb.style.accentColor='#ff4a3d';cb.style.flex='none';"
L"var name=mk('div');"
L"name.textContent=String.fromCharCode(0x200E)+shortF(fk);"
L"name.style.flex='1';name.style.minWidth='0';"
L"name.style.direction='ltr';name.style.textAlign='left';"
L"name.style.color='#e7ebf3';name.style.fontSize='12.5px';"
L"name.style.wordBreak='break-all';name.style.lineHeight='1.6';"
L"var cnt=mk('div');cnt.style.background='#2d3649';"
L"cnt.style.borderRadius='10px';cnt.style.color='#fff';"
L"cnt.style.fontSize='11.5px';cnt.style.fontWeight='700';"
L"cnt.style.padding='3px 10px';cnt.style.flex='none';"
L"var exp=mkBtn('\u067E\u06CC\u0634\u200C\u0646\u0645\u0627\u06CC\u0634');exp.style.flex='none';"
L"top.appendChild(cb);top.appendChild(name);"
L"top.appendChild(cnt);top.appendChild(exp);"
L"row.appendChild(top);"
L"var strip=mk('div');"
L"strip.style.display='flex';strip.style.gap='6px';"
L"strip.style.overflow='hidden';"
L"for(var s=0;s<arr.length&&s<4;s++){"
L"(function(si){"
L"var d=mk('div');"
L"d.style.width='58px';d.style.height='58px';d.style.flex='none';"
L"d.style.borderRadius='10px';"
L"d.style.background='#232b3b';"
L"d.style.border='1px solid #2a3242';"
L"thumb(d,arr[si]);"
L"armHold(d,arr[si]);"
L"strip.appendChild(d)"
L"})(s)}"
L"row.appendChild(strip);"
L"var grid=mk('div');"
L"grid.style.display='none';"
L"grid.style.gridTemplateColumns='repeat(auto-fill,minmax(86px,1fr))';"
L"grid.style.gap='6px';"
L"var cells=[];"
L"for(var g=0;g<arr.length;g++){"
L"(function(gi){"
L"var dd=mk('div');"
L"dd.style.width='100%';dd.style.aspectRatio='2/3';"
L"dd.style.borderRadius='10px';"
L"dd.style.background='#232b3b';"
L"thumb(dd,arr[gi]);"
L"dd.style.border='2px solid transparent';dd.style.opacity='0.35';"
L"dd.style.cursor='pointer';dd.style.position='relative';"
L"dd.style.boxSizing='border-box';"
L"var no=mk('span');no.textContent=String(rank[arr[gi]]||(gi+1));"
L"no.style.position='absolute';no.style.bottom='3px';"
L"no.style.left='3px';no.style.background='rgba(0,0,0,.65)';"
L"no.style.color='#fff';no.style.fontSize='10px';"
L"no.style.borderRadius='6px';no.style.padding='1px 5px';"
L"dd.appendChild(no);"
L"dd.onclick=function(ev){ev.stopPropagation();"
L"if(dd.__held){dd.__held=0;return}"
L"if(picks[fk][arr[gi]]){delete picks[fk][arr[gi]]}"
L"else{picks[fk][arr[gi]]=1}"
L"refreshAll()};"
L"armHold(dd,arr[gi]);"
L"grid.appendChild(dd);cells.push(dd)}"
L")(g)}"
L"row.appendChild(grid);"
L"exp.onclick=function(ev){ev.stopPropagation();"
L"var open=grid.style.display==='none';"
L"grid.style.display=open?'grid':'none';"
L"strip.style.display=open?'none':'flex';"
L"exp.textContent=open?'\u0628\u0633\u062A\u0646':'\u067E\u06CC\u0634\u200C\u0646\u0645\u0627\u06CC\u0634'};"
L"cb.onclick=function(ev){ev.stopPropagation()};"
L"cb.onchange=function(){picks[fk]={};"
L"if(cb.checked)addAll(fk);refreshAll()};"
L"row.onclick=function(){cb.checked=!cb.checked;"
L"if(cb.onchange)cb.onchange()};"
L"listEl.appendChild(row);"
L"rows.push({fk:fk,cb:cb,cnt:cnt,row:row,cells:cells,arr:arr})"
L"})(fi)}"
L"function refreshAll(){"
L"for(var r=0;r<rows.length;r++){"
L"var rw=rows[r];var n=0;var a=rw.arr;"
L"for(var z=0;z<a.length;z++)if(picks[rw.fk][a[z]])n++;"
L"rw.cb.checked=n>0;"
L"rw.row.style.borderColor=(n>0)?'#ff4a3d':'#232b3b';"
L"rw.cnt.textContent=(n===a.length)?(a.length+' \u0639\u06A9\u0633'):(n+'/'+a.length);"
L"for(var z2=0;z2<a.length&&z2<rw.cells.length;z2++){"
L"var on=!!picks[rw.fk][a[z2]];"
L"rw.cells[z2].style.opacity=on?'1':'0.35';"
L"rw.cells[z2].style.borderColor=on?'#ff4a3d':'transparent'}}}"
L"refreshAll();"
L"var btns=mk('div');"
L"btns.style.display='flex';btns.style.gap='8px';"
L"var okB=mk('button');okB.type='button';okB.textContent='\u0627\u062F\u0627\u0645\u0647';"
L"okB.style.border='0';okB.style.cursor='pointer';"
L"okB.style.fontWeight='700';okB.style.fontSize='13px';"
L"okB.style.color='#fff';okB.style.borderRadius='10px';"
L"okB.style.padding='10px 18px';okB.style.fontFamily='inherit';"
L"okB.style.background='linear-gradient(135deg,#ff4a3d,#c9271c)';"
L"okB.style.flex='1';"
L"var noB=mk('button');noB.type='button';noB.textContent='\u0627\u0646\u0635\u0631\u0627\u0641';"
L"noB.style.border='0';noB.style.cursor='pointer';"
L"noB.style.fontWeight='700';noB.style.fontSize='13px';"
L"noB.style.color='#c8ceda';noB.style.borderRadius='10px';"
L"noB.style.padding='10px 18px';noB.style.fontFamily='inherit';"
L"noB.style.background='#2d3649';"
L"btns.appendChild(noB);btns.appendChild(okB);"
L"box.appendChild(btns);"
L"ov.appendChild(box);"
L"(document.body||document.documentElement).appendChild(ov);"
L"function closeOv(){try{if(ov.parentNode)"
L"ov.parentNode.removeChild(ov)}catch(e){}}"
L"allB.onclick=function(ev){ev.stopPropagation();"
L"for(var q=0;q<order.length;q++){picks[order[q]]={};"
L"addAll(order[q])}"
L"refreshAll()};"
L"nonB.onclick=function(ev){ev.stopPropagation();"
L"for(var q2=0;q2<order.length;q2++)picks[order[q2]]={};"
L"refreshAll()};"
L"okB.onclick=function(){"
L"/* \u0627\u0646\u062A\u062E\u0627\u0628 \u0628\u0647 \u062A\u0631\u062A\u06CC\u0628\u0650 \u0633\u0646\u062F \u2014 \u0639\u06A9\u0633 \u06F1\u060C \u06F2\u060C \u2026 */"
L"var sel=[];"
L"for(var q3=0;q3<URLS.length;q3++){"
L"var u2=URLS[q3];"
L"var f2=folderOf(u2);"
L"if(picks[f2]&&picks[f2][u2])sel.push(u2)}"
L"if(!sel.length){try{alert('\u0647\u06CC\u0686 \u0639\u06A9\u0633\u06CC \u0627\u0646\u062A\u062E\u0627\u0628 \u0646\u0634\u062F')}catch(e){}return}"
L"var sent=false;"
L"try{if(window.__mtWv2&&window.__mtWv2.postMessage){"
L"window.__mtWv2.postMessage(JSON.stringify(sel));sent=true}}catch(e2){}"
L"if(!sent){try{alert('\u0627\u06CC\u0646 \u0635\u0641\u062D\u0647 \u0627\u062C\u0627\u0632\u0647\u0654 \u06AF\u0641\u062A\u06AF\u0648 \u0628\u0627 \u0627\u067E \u0631\u0627 \u0646\u0645\u06CC\u200C\u062F\u0647\u062F')}"
L"catch(e3){}return}"
L"closeOv()};"
L"noB.onclick=closeOv;"
L"ov.onclick=function(ev){if(ev.target===ov)closeOv()};"
L"}catch(e){try{if(window.__mtWv2&&window.__mtWv2.postMessage)"
L"window.__mtWv2.postMessage('[]')}catch(e2){}}"
L"})()";

static std::wstring MtFolderOverlayJs(
        const std::vector<std::wstring> &urls) {
    std::wstring arr = L"[";
    for (size_t i = 0; i < urls.size(); i++) {
        if (i)
            arr += L",";
        arr += MtJsQuote(urls[i]);
    }
    arr += L"]";
    std::wstring js = MT_FOLDER_OVERLAY_JS;
    const std::wstring ph = L"__MT_URLS__";
    size_t p = js.find(ph);
    if (p != std::wstring::npos)
        js.replace(p, ph.size(), arr);
    return js;
}

static void MtShowFolderOverlay(void) {
    if (g_webBr == NULL)
        return;
    std::vector<std::wstring> all;
    {
        std::set<std::wstring> seen;

        for (size_t i = 0; i < g_domOrder.size(); i++)
            if (seen.insert(g_domOrder[i]).second)
                all.push_back(g_domOrder[i]);
        for (size_t i = 0; i < g_recNet.size(); i++)
            if (seen.insert(g_recNet[i]).second)
                all.push_back(g_recNet[i]);
        for (size_t i = 0; i < g_foundStore.size(); i++)
            if (seen.insert(g_foundStore[i]).second)
                all.push_back(g_foundStore[i]);
    }
    if (all.empty()) {
        MessageBoxW(g_hwnd,
            L"\u0647\u06CC\u0686 \u0639\u06A9\u0633\u06CC \u0636\u0628\u0637 \u0646\u0634\u062F \u2014 \u0627\u0648\u0644 \u00AB\u0634\u0631\u0648\u0639 \u0636\u0628\u0637\u00BB \u0631\u0627 \u0628\u0632\u0646\u060C \u0635\u0641\u062D\u0647 \u0641\u0635\u0644 \u0631\u0627 \u0628\u0627\u0632 \u06A9\u0646 \u0648 \u0648\u0631\u0642 \u0628\u0632\u0646",
            L"\u0645\u0627\u0646\u06AF\u0627 \u06A9\u0644\u0648\u062F",
            MB_OK | MB_ICONINFORMATION | MB_RTLREADING | MB_RIGHT);
        if (g_lblStatus != NULL)
            SetWindowTextW(g_lblStatus, L"\u2014");
        return;
    }
    std::wstring js = MtFolderOverlayJs(all);
    g_webBr->ExecuteScript(js.c_str(), &g_execNoop);
    MtLog("folder overlay injected");
}

static void MtStartDownload(const std::vector<std::wstring> &urls) {
    g_dlUrls = urls;
    g_dlData.assign(urls.size(), L"");
    g_dlNext = 0;
    g_dlDone = 0;
    g_dlOk = 0;
    g_dlBad = 0;
    g_dlSlotIdx[0] = -1;
    g_dlSlotIdx[1] = -1;
    g_dlSlotIdx[2] = -1;
    if (g_lblStatus != NULL)
        SetWindowTextW(g_lblStatus, L"\u2B07 0/\u2026");
    for (int s = 0; s < 3 && g_webBr != NULL; s++) {
        if (g_dlNext >= g_dlUrls.size())
            break;
        g_dlSlotIdx[s] = (int)g_dlNext;
        g_webBr->ExecuteScript(
            MtDlOneJs(MtJsQuote(g_dlUrls[g_dlNext])).c_str(),
            s == 0 ? &g_execDlStep
            : (s == 1 ? &g_execDlStepB : &g_execDlStepC));
        g_dlNext++;
    }
}

HRESULT MtExecHandler::MtExecImpl(int mode, HRESULT errorCode,
                                  LPCWSTR resultObjectAsJson) {
    if (FAILED(errorCode)) {
        if (mode == 4 && !g_fillUrl.empty()) {
            PostMessage(g_hwnd, WM_APP_NAV_FILL, 0, 0);
            PostMessage(g_hwnd, WM_APP_FILL_DONE, 0, 0);
        }
        if (mode == 3) {
            g_brTarget = g_lastSite.empty() ? BROWSER_HOME : g_lastSite;
            MtShowBrowser();
            if (g_webBr != NULL && !g_brTarget.empty()) {
                g_webBr->Navigate(g_brTarget.c_str());
                g_brTarget.clear();
            }
        }
        return S_OK;
    }
    if (mode == 2) {
        std::vector<std::wstring> links;
        MtParseMaybeWrapped(resultObjectAsJson, links);
        if (g_recording) {
            for (size_t i = 0; i < links.size(); i++)
                MtFoundAdd(links[i]);
            int n = MtRecCount();
            if (g_lblStatus != NULL)
                SetWindowTextW(g_lblStatus,
                    (L"\u25CF " + std::to_wstring(n)
                     + L" \u0639\u06A9\u0633 \u0636\u0628\u0637"
                       L" \u0634\u062F").c_str());
        } else {
            MtSetStatusCount((int)links.size());
        }
        return S_OK;
    }
    if (mode == 3) {
        std::wstring u = MtParseJsonString(resultObjectAsJson);
        std::wstring target;
        if (u.empty() || u == L"__MT_MANY__") {
            target = g_lastSite.empty() ? BROWSER_HOME : g_lastSite;
        } else if (_wcsnicmp(u.c_str(), L"http", 4) == 0) {
            target = u;
        } else {
            target = MtSearchOrUrl(u);
        }
        MtLog("field read: target decided");
        if (g_webBr != NULL) {
            MtLog("field read: show + navigate");
            MtShowBrowser();
            g_webBr->Navigate(target.c_str());
        } else {
            g_brTarget = target;
        }
        return S_OK;
    }
    if (mode == 4) {
        const wchar_t *s = resultObjectAsJson ? resultObjectAsJson : L"0";
        if (wcsstr(s, L"1") != NULL) {
            PostMessage(g_hwnd, WM_APP_FILL_DONE, 1, 0);
        } else if (!g_fillUrl.empty()) {
            PostMessage(g_hwnd, WM_APP_NAV_FILL, 0, 0);
            PostMessage(g_hwnd, WM_APP_FILL_DONE, 0, 0);
        }
        return S_OK;
    }
    if (mode == 5) {
        const wchar_t *s = resultObjectAsJson ? resultObjectAsJson : L"";
        BOOL on = (wcsstr(s, L"1") != NULL);
        if (on != g_readerMode) {
            g_readerMode = on;
            if (g_btnGlobe != NULL) {
                BOOL brVis0 = (g_hwndBr != NULL && IsWindowVisible(g_hwndBr));
                ShowWindow(g_btnGlobe,
                           (!on && !g_failMode && g_webApp != NULL && !brVis0)
                           ? SW_SHOW : SW_HIDE);
            }
        }
        return S_OK;
    }
    if (mode == 9) {
        std::vector<std::wstring> links;
        if (!MtParseMaybeWrapped(resultObjectAsJson, links)
                || links.empty()) {
            PostMessage(g_hwnd, WM_APP_DL_EMPTY, 0, 0);
            return S_OK;
        }
        g_selUrls = links;
        if (links.size() == 1 && MtIsMangaPlusUrl(links[0])) {
            PostMessage(g_hwnd, WM_APP_DO_EXTRACT, 1, 0);
            return S_OK;
        }
        PostMessage(g_hwnd, WM_APP_DO_EXTRACT, 2, 0);
        return S_OK;
    }
    if (mode == 15) {
        std::vector<std::wstring> links;
        MtParseMaybeWrapped(resultObjectAsJson, links);

        g_domOrder = links;
        for (size_t i = 0; i < links.size(); i++)
            MtFoundAdd(links[i]);
        PostMessage(g_hwnd, WM_APP_SHOW_FOLDERS, 0, 0);
        return S_OK;
    }
    if (mode == 10 || mode == 13 || mode == 14) {
        int slot = mode - 10;
        int idx = g_dlSlotIdx[slot];
        if (idx >= 0 && idx < (int)g_dlData.size()) {
            std::wstring d = MtParseJsonString(
                resultObjectAsJson ? resultObjectAsJson : L"");
            if (d.size() > 32 && d.compare(0, 5, L"data:") == 0) {
                g_dlData[idx] = d;
                g_dlOk++;
            } else {
                g_dlBad++;
            }
            g_dlDone++;
        }
        wchar_t sb[64];
        swprintf(sb, 64, L"\u2B07 %d/%d", g_dlDone, (int)g_dlUrls.size());
        if (g_lblStatus != NULL)
            SetWindowTextW(g_lblStatus, sb);
        if (g_dlNext < g_dlUrls.size()) {
            PostMessage(g_hwnd, WM_APP_DL_STEP, (WPARAM)slot, 0);
            return S_OK;
        }
        if ((size_t)g_dlDone < g_dlUrls.size())
            return S_OK;
        if (g_dlOk > 0 && g_webApp != NULL) {
            PostMessage(g_hwnd, WM_APP_UP_START, 0, 0);
        } else {
            PostMessage(g_hwnd, WM_APP_DL_FAIL, 0, 0);
        }
        return S_OK;
    }
    if (mode == 12) {
        std::wstring s = MtParseJsonString(
            resultObjectAsJson ? resultObjectAsJson : L"");
        int ok = _wtoi(s.c_str());
        size_t slash = s.find(L'/');
        int total = (slash != std::wstring::npos)
            ? _wtoi(s.c_str() + slash + 1) : 1;
        if (total <= 0)
            total = 1;
        g_upPolls++;
        wchar_t sb[64];
        swprintf(sb, 64, L"\u2B06 %d/%d", ok, g_dlOk);
        if (g_lblStatus != NULL)
            SetWindowTextW(g_lblStatus, sb);
        PostMessage(g_hwnd, WM_APP_UP_POLL, (WPARAM)ok, (LPARAM)total);
        return S_OK;
    }
    if (mode != 0 || g_webApp == NULL)
        return S_OK;
    std::vector<std::wstring> links;
    if (!MtParseMaybeWrapped(resultObjectAsJson, links) || links.empty()) {
        PostMessage(g_hwnd, WM_APP_DL_EMPTY, 0, 0);
        return S_OK;
    }
    g_selUrls = links;
    PostMessage(g_hwnd, WM_APP_DO_EXTRACT, 1, 0);
    return S_OK;
}

int WINAPI WinMain(HINSTANCE hInst, HINSTANCE hPrev, LPSTR cmdLine, int nCmdShow) {
    typedef BOOL(WINAPI *SetDpiCtxFn)(HANDLE value);

    (void)hPrev; (void)cmdLine;

    MtInitLogPath();
    SetUnhandledExceptionFilter(MtCrashFilter);
    MtLog("WinMain — MangaCloud v1.14.387 (DOM-order extraction + fixed collect JS + robust hold preview)");
    {
        WCHAR mv[16];
        DWORD mn = GetEnvironmentVariableW(L"MANGA_SMOKE", mv, 15);
        if (mn > 0 && mn < 15 && mv[0] == L'2')
            g_smokeBrowser = TRUE;
    }

    g_hInst = hInst;

    HMODULE user32 = GetModuleHandleW(L"user32.dll");
    if (user32 != NULL) {
        SetDpiCtxFn setCtx =
            (SetDpiCtxFn)(void *)(uintptr_t)GetProcAddress(user32, "SetProcessDpiAwarenessContext");
        if (setCtx != NULL)
            setCtx((HANDLE)(INT_PTR)-4);
    }
    CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);

    g_barBrush = CreateSolidBrush(CLR_BAR);
    g_urlBrush = CreateSolidBrush(CLR_URLBG);
    g_brBarBrush = CreateSolidBrush(CLR_BRBAR);
    g_font = CreateFontW(-15, 0, 0, 0, FW_NORMAL, 0, 0, 0,
                         DEFAULT_CHARSET, OUT_DEFAULT_PRECIS,
                         CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY,
                         DEFAULT_PITCH | FF_DONTCARE, L"Segoe UI");
    g_fontFail = CreateFontW(-21, 0, 0, 0, FW_BOLD, 0, 0, 0,
                             DEFAULT_CHARSET, OUT_DEFAULT_PRECIS,
                             CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY,
                             DEFAULT_PITCH | FF_DONTCARE, L"Segoe UI");
    g_fontBold = CreateFontW(-16, 0, 0, 0, FW_BOLD, 0, 0, 0,
                             DEFAULT_CHARSET, OUT_DEFAULT_PRECIS,
                             CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY,
                             DEFAULT_PITCH | FF_DONTCARE, L"Segoe UI");

    WNDCLASSEXW wc;
    ZeroMemory(&wc, sizeof(wc));
    wc.cbSize = sizeof(wc);
    wc.style = CS_HREDRAW | CS_VREDRAW;
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hInst;
    wc.hIcon = LoadIconW(hInst, MAKEINTRESOURCEW(1));
    wc.hIconSm = wc.hIcon;
    wc.hCursor = LoadCursorW(NULL, (LPCWSTR)IDC_ARROW);
    wc.hbrBackground = g_barBrush;
    wc.lpszClassName = L"MangaCloudWnd";
    RegisterClassExW(&wc);

    WNDCLASSEXW bc;
    ZeroMemory(&bc, sizeof(bc));
    bc.cbSize = sizeof(bc);
    bc.style = CS_HREDRAW | CS_VREDRAW;
    bc.lpfnWndProc = BrWndProc;
    bc.hInstance = hInst;
    bc.hIcon = LoadIconW(hInst, MAKEINTRESOURCEW(1));
    bc.hIconSm = bc.hIcon;
    bc.hCursor = LoadCursorW(NULL, (LPCWSTR)IDC_ARROW);
    bc.hbrBackground = g_barBrush;
    bc.lpszClassName = L"MangaCloudBrWnd";
    RegisterClassExW(&bc);

    WNDCLASSEXW mc;
    ZeroMemory(&mc, sizeof(mc));
    mc.cbSize = sizeof(mc);
    mc.style = CS_HREDRAW | CS_VREDRAW;
    mc.lpfnWndProc = MenuWndProc;
    mc.hInstance = hInst;
    mc.hCursor = LoadCursorW(NULL, (LPCWSTR)IDC_ARROW);
    mc.hbrBackground = g_brBarBrush;
    mc.lpszClassName = L"MangaCloudMenuWnd";
    RegisterClassExW(&mc);

    int sw = GetSystemMetrics(SM_CXSCREEN);
    int sh = GetSystemMetrics(SM_CYSCREEN);
    int ww = sw < 1320 ? (sw > 40 ? sw - 40 : sw) : 1280;
    int wh = sh < 900 ? (sh > 80 ? sh - 80 : sh) : 820;
    int x = sw > ww ? (sw - ww) / 2 : 0;
    int y = sh > wh ? (sh - wh) / 2 : 0;

    g_hwnd = CreateWindowExW(0, L"MangaCloudWnd", APP_TITLE,
                             WS_OVERLAPPEDWINDOW, x, y, ww, wh,
                             NULL, NULL, hInst, NULL);
    if (g_hwnd == NULL) {
        MtLog("CreateWindow failed");
        if (GetEnvironmentVariableW(L"MANGA_SMOKE", NULL, 0) == 0) {
            MessageBoxW(NULL,
                L"\u067E\u0646\u062C\u0631\u0647 \u0633\u0627\u062E\u062A\u0647 \u0646\u0634\u062F \u2014 \u0645\u0633\u06CC\u0631 \u0627\u067E \u062F\u0631 \u0645\u0631\u0648\u0631\u06AF\u0631 \u0628\u0627\u0632 \u0645\u06CC\u200C\u0634\u0648\u062F.",
                L"\u0645\u0627\u0646\u06AF\u0627 \u06A9\u0644\u0648\u062F",
                MB_OK | MB_ICONERROR | MB_RTLREADING | MB_RIGHT);
        }
        ShellExecuteW(NULL, L"open", APP_URL, NULL, NULL, SW_SHOWNORMAL);
        return 1;
    }
    MtDarkTitleBar(g_hwnd);

    g_btnGlobe = CreateWindowExW(0, L"BUTTON",
        L"\u0645\u0631\u0648\u0631\u06AF\u0631 \u062F\u0627\u062E\u0644\u06CC",
        WS_CHILD | WS_VISIBLE | BS_OWNERDRAW,
        14, 14, FAB_SIZE, FAB_SIZE, g_hwnd,
        (HMENU)(INT_PTR)ID_BTN_GLOBE, hInst, NULL);
    SetWindowRgn(g_btnGlobe, CreateEllipticRgn(0, 0, FAB_SIZE, FAB_SIZE),
                 TRUE);

    g_lblFailTitle = CreateWindowExW(0, L"STATIC",
        L"\u0648\u0627\u0628\u0633\u062A\u06AF\u06CC\u0650 \u0648\u0628 \u0622\u0645\u0627\u062F\u0647 \u0646\u06CC\u0633\u062A",
        WS_CHILD | SS_RIGHT | SS_CENTERIMAGE,
        0, 0, 400, 40, g_hwnd, (HMENU)(INT_PTR)ID_LBL_STATUS,
        hInst, NULL);
    g_lblFailBody = CreateWindowExW(0, L"STATIC", MT_FAIL_BODY,
        WS_CHILD | SS_RIGHT,
        0, 0, 500, 200, g_hwnd, (HMENU)(INT_PTR)ID_LBL_STATUS,
        hInst, NULL);
    g_btnWv2Dl = CreateWindowExW(0, L"BUTTON",
        L"\u2B07 \u062F\u0627\u0646\u0644\u0648\u062F WebView2",
        WS_CHILD | BS_OWNERDRAW,
        0, 0, 260, 44, g_hwnd, (HMENU)(INT_PTR)ID_BTN_WV2DL, hInst, NULL);
    g_btnSysBr = CreateWindowExW(0, L"BUTTON",
        L"\U0001F310 \u0628\u0627\u0632 \u06A9\u0631\u062F\u0646 \u0627\u067E \u062F\u0631 \u0645\u0631\u0648\u0631\u06AF\u0631",
        WS_CHILD | BS_OWNERDRAW,
        0, 0, 260, 44, g_hwnd, (HMENU)(INT_PTR)ID_BTN_SYSBR, hInst, NULL);
    g_btnRetry = CreateWindowExW(0, L"BUTTON",
        L"\u21BB \u062A\u0644\u0627\u0634 \u062F\u0648\u0628\u0627\u0631\u0647",
        WS_CHILD | BS_OWNERDRAW,
        0, 0, 260, 44, g_hwnd, (HMENU)(INT_PTR)ID_BTN_RETRY, hInst, NULL);
    SendMessageW(g_lblFailTitle, WM_SETFONT, (WPARAM)g_fontFail, TRUE);
    SendMessageW(g_lblFailBody, WM_SETFONT, (WPARAM)g_font, TRUE);
    SendMessageW(g_btnWv2Dl, WM_SETFONT, (WPARAM)g_fontBold, TRUE);
    SendMessageW(g_btnSysBr, WM_SETFONT, (WPARAM)g_fontBold, TRUE);
    SendMessageW(g_btnRetry, WM_SETFONT, (WPARAM)g_fontBold, TRUE);

    ShowWindow(g_hwnd, nCmdShow);
    UpdateWindow(g_hwnd);
    LayoutApp();
    SetTimer(g_hwnd, TIMER_RECOUNT, 3000, NULL);
    SetTimer(g_hwnd, TIMER_READER, 900, NULL);

    TryStartEnv();

    MSG msg;
    while (GetMessageW(&msg, NULL, 0, 0) > 0) {
#if MT_HAS_SEH
        __try {
            TranslateMessage(&msg);
            DispatchMessageW(&msg);
        } __except (MtSehLog("dispatch", GetExceptionInformation())) {
            MtLog("dispatch: exception swallowed — continuing");
        }
#else
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
#endif
    }
    MtLog("exit");
    return (int)msg.wParam;
}
