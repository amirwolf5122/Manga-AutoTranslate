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
L"var els2=document.querySelectorAll('img');"
L"for(var i=0;i<els2.length;i++){"
L"var el=els2[i],ok=false,nw=0,nh=0;"
L"try{ok=!!el.complete&&el.naturalWidth>0;nw=el.naturalWidth||0;nh=el.naturalHeight||0}catch(e){}"
L"if(!ok)continue;"
L"if(nw&&nh&&Math.max(nw,nh)<300)continue;"
L"var u='';"
L"try{u=el.currentSrc||el.src||''}catch(e){}"
L"if(u)add(u)"
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
L"if(t==='fetch'||t==='xmlhttprequest')continue;"
L"if(!/(^|\\/)(pages?|images?|img|media|manga|manhwa|webtoon|chapters?|episodes?|comic|uploads|wp-content|cdn)(\\/|[_\\-.]|$)/i.test(b))continue"
L"}"
L"add(n)"
L"}"
L"}"
L"domPass();resPass()"
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
L"var b=String(u).split(/[?#]/)[0];"
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

static void MtWriteMinidump(EXCEPTION_POINTERS *ep) {
    HMODULE db = LoadLibraryW(L"dbghelp.dll");
    if (db == NULL)
        return;
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

static void LayoutApp(void);
static void LayoutBrowser(void);
static void MtCloseExtractMenu(void);
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
    int bwExt = (w < 700) ? 84 : 104;
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
            if (g_webBr != NULL) {
                if (id == ID_MITEM_LINK)
                    g_webBr->ExecuteScript(MT_COLLECT_JS, &g_execExtract);
                else
                    g_webBr->ExecuteScript(MT_COLLECT_JS, &g_execDlList);
            }
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
        L"\u0627\u0633\u062A\u062E\u0631\u0627\u062C",
        WS_CHILD | WS_VISIBLE | BS_OWNERDRAW,
        0, 0, 104, 34, hwnd, (HMENU)(INT_PTR)ID_BTN_EXTRACT, hInst, NULL);

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
                MtShowExtractMenu();
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
                    && IsWindowVisible(g_hwndBr) && !g_loading)
                Wv2Recount();
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
    g_fillUrl = std::wstring(APP_URL) + L"#imgs="
                + MtWideFromAscii(MtUrlEncode(payload));
    if (g_webApp != NULL) {
        std::wstring js = L"(function(){try{if(window.__mtFillLinks){"
                          L"window.__mtFillLinks(" + MtJsQuote(payload) + L");"
                          L"alert('__MT_FILLED__" + std::to_wstring(links.size())
                          + L"__MT_FILLED2__');return 1}return 0}"
                          L"catch(e){return 0}})()";
        g_webApp->ExecuteScript(js.c_str(), &g_execFill);
    }
    MtHideBrowser();
}

HRESULT MtExecHandler::MtExecImpl(int mode, HRESULT errorCode,
                                  LPCWSTR resultObjectAsJson) {
    if (FAILED(errorCode)) {
        if (mode == 4 && g_webApp != NULL && !g_fillUrl.empty())
            g_webApp->Navigate(g_fillUrl.c_str());
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
        MtSetStatusCount((int)links.size());
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
        if (wcsstr(s, L"1") == NULL && g_webApp != NULL
                && !g_fillUrl.empty()) {
            g_webApp->Navigate(g_fillUrl.c_str());
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
            MessageBoxW(g_hwnd,
                L"\u0639\u06A9\u0633\u06CC \u067E\u06CC\u062F\u0627 "
                L"\u0646\u0634\u062F \u2014 \u0627\u0648\u0644 \u0641\u0635\u0644 "
                L"\u0631\u0627 \u0628\u0627\u0632 \u06A9\u0646 \u0648 \u062A\u0627 "
                L"\u0622\u062E\u0631\u0650 \u0635\u0641\u062D\u0647 \u0627\u0633"
                L"\u06A9\u0631\u0648\u0644 \u06A9\u0646",
                L"\u0645\u0627\u0646\u06AF\u0627 \u06A9\u0644\u0648\u062F",
                MB_OK | MB_ICONINFORMATION | MB_RTLREADING | MB_RIGHT);
            return S_OK;
        }
        if (links.size() == 1 && MtIsMangaPlusUrl(links[0])) {
            MtFillFieldAndClose(links);
            return S_OK;
        }
        g_dlUrls = links;
        g_dlData.assign(links.size(), L"");
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
            if (g_webBr != NULL) {
                g_dlSlotIdx[slot] = (int)g_dlNext;
                g_webBr->ExecuteScript(
                    MtDlOneJs(MtJsQuote(g_dlUrls[g_dlNext])).c_str(),
                    slot == 0 ? &g_execDlStep
                    : (slot == 1 ? &g_execDlStepB : &g_execDlStepC));
                g_dlNext++;
            }
            return S_OK;
        }
        if ((size_t)g_dlDone < g_dlUrls.size())
            return S_OK;
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
        } else {
            MessageBoxW(g_hwnd,
                L"\u0647\u06CC\u0686 \u0639\u06A9\u0633\u06CC \u062F\u0627"
                L"\u0646\u0644\u0648\u062F \u0646\u0634\u062F",
                L"\u0645\u0627\u0646\u06AF\u0627 \u06A9\u0644\u0648\u062F",
                MB_OK | MB_ICONINFORMATION | MB_RTLREADING | MB_RIGHT);
            MtHideBrowser();
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
        if (ok >= g_dlOk || g_upPolls >= 1500) {
            if (g_webApp != NULL)
                g_webApp->ExecuteScript(MT_UP_FILL_JS, &g_execNoop);
            MtHideBrowser();
        } else {
            if (ok >= g_upFired)
                MtFireUploadBatch();
            if (g_webApp != NULL)
                g_webApp->ExecuteScript(MtUpPollJs(total).c_str(),
                                        &g_execUpPoll);
        }
        return S_OK;
    }
    if (mode != 0 || g_webApp == NULL)
        return S_OK;
    std::vector<std::wstring> links;
    if (!MtParseMaybeWrapped(resultObjectAsJson, links) || links.empty()) {
        MessageBoxW(g_hwnd,
            L"\u0639\u06A9\u0633\u06CC \u067E\u06CC\u062F\u0627 \u0646\u0634\u062F \u2014 "
            L"\u0627\u0648\u0644 \u0641\u0635\u0644 \u0631\u0627 \u0628\u0627\u0632 \u06A9\u0646 "
            L"\u0648 \u062A\u0627 \u0622\u062E\u0631\u0650 \u0635\u0641\u062D\u0647 "
            L"\u0627\u0633\u06A9\u0631\u0648\u0644 \u06A9\u0646 \u062A\u0627 "
            L"\u0639\u06A9\u0633\u200C\u0647\u0627\u06CC \u062A\u0646\u0628\u0644 "
            L"\u0644\u0648\u062F \u0628\u0634\u0646",
            L"\u0645\u0627\u0646\u06AF\u0627 \u06A9\u0644\u0648\u062F",
            MB_OK | MB_ICONINFORMATION | MB_RTLREADING | MB_RIGHT);
        return S_OK;
    }
    MtFillFieldAndClose(links);
    return S_OK;
}

int WINAPI WinMain(HINSTANCE hInst, HINSTANCE hPrev, LPSTR cmdLine, int nCmdShow) {
    typedef BOOL(WINAPI *SetDpiCtxFn)(HANDLE value);

    (void)hPrev; (void)cmdLine;

    MtInitLogPath();
    SetUnhandledExceptionFilter(MtCrashFilter);
    MtLog("WinMain — MangaCloud v1.14.345 (flat toolbar, dark button corners via WM_CTLCOLORBTN, single extract button with choice menu)");
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
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }
    MtLog("exit");
    return (int)msg.wParam;
}
