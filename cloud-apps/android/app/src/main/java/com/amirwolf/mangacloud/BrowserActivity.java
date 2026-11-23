package com.amirwolf.mangacloud;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.inputmethod.EditorInfo;
import android.webkit.CookieManager;
import android.webkit.JsResult;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONArray;

public class BrowserActivity extends Activity {

    public static final String EXTRA_URL = "url";
    public static final String EXTRA_LINKS = "links";
    public static final String EXTRA_DL_DIR = "dl_dir";
    public static final String EXTRA_DL_COUNT = "dl_count";

    public static String lastSite = "";

    private static final String UA_STR =
            "Mozilla/5.0 (Linux; Android 10; Pixel 7) " +
            "AppleWebKit/537.36 (KHTML, like Gecko) " +
            "Chrome/120.0.0.0 Mobile Safari/537.36";

    private static final String EXTRACT_JS =
        "(function(){ var W=window; if(!W.__MT_FOUND){W.__MT_FOUND={};W.__MT_ORDER=[];} if(!W.__MT_BLOBS){W.__MT_BLOBS={};} if(typeof W.__MT_T0!=='number'){W.__MT_T0=0;} function abs(u){try{var a=document.createElement('a');a.href=u;return a.href}catch(e){return null}} function qsz(u){ try{ var m=String(u).match(/[?&](?:type|size|w|h|width|height)=(f?)(\\d{1,4})(?:[_x](\\d{1,4}))?/i); if(!m)return 0; var a=parseInt(m[2],10)||0; var b=parseInt(m[3]||'0',10)||0; if(a>0&&b>0)return Math.max(a,b); if(m[1]&&a>0)return a; return 0 }catch(e){return 0}} function junk(u){ if(!u)return 1; u=String(u); if(u.indexOf('data:')===0)return 1; if(u.indexOf('blob:')===0)return 1; if(!/^https?:/i.test(u))return 1; var b=u.split(/[?#]/)[0]; if(/\\.(svg|ico|gif|css|js|mjs|json|html?|xml|txt|pdf|zip|rar|7z|gz|mp4|webm|mp3|m4a|ogg|wav|woff2?|ttf|otf|eot|map)$/i.test(b))return 1; if(/[-_]\\d{2,4}x\\d{2,4}\\.(jpe?g|png|webp|avif)$/i.test(b))return 1; if(/\\/\\d{2,4}x\\d{2,4}\\//i.test(b))return 1; if(/(login|signin|signup|register|servicelogin|oauth)/i.test(b))return 1; var q=qsz(u); if(q>0&&q<=400)return 1; if(/(logo|icon|avatar|banner|sprite|favicon|badge|flag|button|emoji|thumb(nail)?s?|placeholder|blank|spacer|transparen|loading|spinner|pixel|profile|rating|share|follow|comment|credits)/i.test(b))return 1; if(/(?:^|[^a-z0-9])ads?[._\\/-]/i.test(b))return 1; if(/\\/(covers?|thumbs?|thumbnails?|avatars?|banners?|creatives?|gifs?|decorations?|emojis?|smileys?|stickers?)\\//i.test(b))return 1; if(/(default|anon|guest|blank)[-_]?(pp|avatar|user|profile|image)/i.test(b))return 1; if(/(pubadx|adservice|adserver|doubleclick|adnxs|propellerads?|onclck|adcash|adsterra|hilltopads?|clickadu|sovrn|taboola|outbrain|zedo|buysellads?|sharethrough|smartadserver|openx|rubicon|criteo|pubmatic|media\\.net|jumpg-assets)/i.test(b))return 1; return 0} function keyOf(u){ var s=String(u); var b=s.split(/[?#]/)[0]; if(!/\\.(jpe?g|png|webp|avif|bmp|tiff?)$/i.test(b))return s.split('#')[0]; return b.replace(/[-_]\\d{2,4}x\\d{2,4}\\./i,'.')} function bkey(u){return String(u).split('#')[0]} function hold(k,b){ try{ if(!b||W.__MT_BLOBS[k])return; var n=0;for(var p in W.__MT_BLOBS)n++; if(n<120)W.__MT_BLOBS[k]=b }catch(e){}} function capb(u){ try{ if(!u)return; u=String(u).trim(); if(u.indexOf('blob:')!==0)return; var k=bkey(u); if(Object.prototype.hasOwnProperty.call(W.__MT_FOUND,k))return; W.__MT_FOUND[k]=u; W.__MT_ORDER.push(u); try{fetch(u).then(function(r){return r.ok?r.blob():null}).then(function(b){if(b)hold(k,b)}).catch(function(){})}catch(e2){} }catch(e){}} function cap(u){ try{ if(!u)return; u=String(u).trim(); if(u.indexOf('data:')===0)return; if(u.indexOf('blob:')===0){capb(u);return} if(!/^https?:/i.test(u))return; u=abs(u); if(!u||junk(u))return; try{if(u===location.href)return}catch(e){} var k=keyOf(u); if(Object.prototype.hasOwnProperty.call(W.__MT_FOUND,k))return; W.__MT_FOUND[k]=u; W.__MT_ORDER.push(u) }catch(e){}} function bestSrcset(ss){ try{ var parts=String(ss).split(','),best='',bw=-1; for(var k=0;k<parts.length;k++){ var tk=parts[k].trim().split(/\\s+/); var u0=tk[0]||''; var w0=parseInt(String(tk[1]||'').replace(/[^0-9]/g,''),10)||0; if(u0&&w0>=bw){bw=w0;best=u0}} return best }catch(e){return ''}} var DATA_ATTS=['data-src','data-lazy-src','data-original','data-original-src','data-orig-src','data-lazy','data-url','data-image','data-echo','data-asurl','data-cfsrc','data-hi-res-src','data-full-src','data-full_image','data-large-src','data-file','data-path','data-actualsrc']; function nowT(){try{return performance.now()}catch(e){return 0}} function grabEl(el){ try{ if(!el||el.nodeType!==1)return; var tg=el.tagName; if(tg!=='IMG'&&tg!=='SOURCE')return; el.__MT_SEEN=nowT(); var u=''; try{u=el.currentSrc||el.getAttribute('src')||''}catch(e){} u=String(u||''); if(u.indexOf('blob:')===0){capb(u)} else if(tg==='SOURCE'&&u&&u.indexOf('data:')!==0){cap(u)} else if(u&&u.indexOf('data:')!==0){ var done=function(){try{var c=el.currentSrc||el.src||'';if(c&&c.indexOf('http')===0)cap(c)}catch(e){}}; try{ if(el.complete&&el.naturalWidth>0){ if(Math.max(el.naturalWidth||0,el.naturalHeight||0)>=300)done(); }else{ el.addEventListener('load',function(){ try{if(Math.max(el.naturalWidth||0,el.naturalHeight||0)>=300)done()}catch(e){} },{once:true}); } }catch(e){} } try{ var ss=el.getAttribute('srcset')||el.getAttribute('data-srcset'); if(ss){var bs=bestSrcset(ss);if(bs)cap(bs)} }catch(e){} for(var j=0;j<DATA_ATTS.length;j++){ try{var v=el.getAttribute(DATA_ATTS[j]);if(v&&v.length>4)cap(v)}catch(e){} } }catch(e){}} function grabTree(n){ try{ if(!n||n.nodeType!==1)return; if(n.tagName==='IMG'||n.tagName==='SOURCE'){grabEl(n);return} if(n.querySelectorAll){ var q=n.querySelectorAll('img,source'); for(var i=0;i<q.length;i++)grabEl(q[i]) } }catch(e){}} if(!W.__MT_WATCH){ W.__MT_WATCH=1; try{ if(!W.__mtCO){W.__mtCO=1; var _co=URL.createObjectURL; URL.createObjectURL=function(){ var u=''; try{u=_co.apply(this,arguments)}catch(e){return _co.apply(this,arguments)} try{ var b=arguments[0]; if(b&&(typeof Blob!=='undefined')&&b instanceof Blob&&String(b.type||'').indexOf('image/')===0&&(b.size||0)>12000){hold(String(u).split('#')[0],b)} }catch(e2){} return u }; } var ex=document.querySelectorAll('img,source'); for(var i2=0;i2<ex.length;i2++){try{ex[i2].__MT_SEEN=nowT()}catch(e){}} }catch(e){} try{ var obs=new MutationObserver(function(ms){ for(var i3=0;i3<ms.length;i3++){ var m=ms[i3]; try{ if(m.type==='attributes'){grabEl(m.target);continue} var ns=m.addedNodes; for(var j2=0;j2<ns.length;j2++)grabTree(ns[j2]) }catch(e){}} }); obs.observe(document.documentElement||document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['src','srcset']}) }catch(e){} try{ if(!W.__mtPO){W.__mtPO=1; var po=new PerformanceObserver(function(list){ try{ var es=list.getEntries(); for(var i=0;i<es.length;i++){ var en=es[i]||{};var n=String(en.name||''); if(!n)continue; var b=n.split(/[?#]/)[0]; var t=String(en.initiatorType||''); if(/\\.(jpe?g|png|webp|avif|bmp|tiff?)$/i.test(b)||t==='img'||/\\.(jpe?g|png|webp|avif|bmp|tiff?)([?#]|$)/i.test(n)){cap(n)} } }catch(e){}}); po.observe({entryTypes:['resource'],buffered:true}) }}catch(e){} try{ var _f=W.fetch; if(typeof _f==='function'&&!W.__mtFH){W.__mtFH=1; W.fetch=function(){var p;try{p=_f.apply(this,arguments)}catch(e){throw e} try{var a0=arguments[0];var u0=''; if(a0){if(typeof a0==='string')u0=a0;else if(a0.url)u0=String(a0.url)} p.then(function(r){try{var ct=(r.headers&&r.headers.get('content-type'))||''; if(/^image\\//i.test(String(ct).trim()))cap(u0)}catch(e){}}).catch(function(){}) }catch(e){}return p}} var _o=XMLHttpRequest.prototype.open,_s=XMLHttpRequest.prototype.send; XMLHttpRequest.prototype.open=function(m,u){try{this.__mtU=String(u||'')}catch(e){}return _o.apply(this,arguments)}; XMLHttpRequest.prototype.send=function(){try{var x=this; x.addEventListener('loadend',function(){try{var ct=''; try{ct=x.getResponseHeader('content-type')||''}catch(e){} var ru='';try{ru=x.responseURL||x.__mtU||''}catch(e){} if(/^image\\//i.test(String(ct).trim()))cap(ru)}catch(e){}})}catch(e){} return _s.apply(this,arguments)} }catch(e){} } function scanDoc(doc){ try{ var els=doc.querySelectorAll('img'); for(var i=0;i<els.length;i++){ var el=els[i]; try{ var t0=W.__MT_T0||0; if(el.__MT_SEEN&&el.__MT_SEEN<t0)continue; el.__MT_SEEN=nowT(); }catch(e){} var nw=0,nh=0,loaded=false; try{loaded=!!el.complete&&el.naturalWidth>0;nw=el.naturalWidth||0;nh=el.naturalHeight||0}catch(e){} var u=''; try{u=el.currentSrc||el.src||''}catch(e){} if(u&&u.indexOf('data:')===0)u=''; if(u&&u.indexOf('blob:')===0){ if(loaded&&nw&&nh&&Math.max(nw,nh)>=300)capb(u); u=''; } if(u&&loaded&&nw&&nh&&Math.max(nw,nh)<300)u=''; if(u)cap(u); try{ var ss=el.getAttribute('srcset')||el.getAttribute('data-srcset'); if(ss){var bs=bestSrcset(ss);if(bs)cap(bs)} }catch(e){} for(var j=0;j<DATA_ATTS.length;j++){ try{ var v=el.getAttribute(DATA_ATTS[j]); if(v&&v.length>4)cap(v) }catch(e){}} } }catch(e){} try{ var sos=doc.querySelectorAll('source'); for(var i4=0;i4<sos.length;i4++){ var so=sos[i4]; try{ var t02=W.__MT_T0||0; if(so.__MT_SEEN&&so.__MT_SEEN<t02)continue; so.__MT_SEEN=nowT(); var s2=so.getAttribute('srcset')||so.getAttribute('data-srcset')||so.getAttribute('src'); if(s2){var b2=bestSrcset(s2);if(!b2)b2=s2;if(b2)cap(b2)} }catch(e){}} }catch(e){} try{ var as=doc.querySelectorAll('a[href]'); for(var i5=0;i5<as.length;i5++){ var h=as[i5].getAttribute('href')||''; if(/^https?:/i.test(h)&&/\\.(jpe?g|png|webp|avif|bmp)([?#]|$)/i.test(h))cap(h)} }catch(e){} try{ var st=doc.querySelectorAll('[style*=\"url(\"]'); for(var i6=0;i6<st.length;i6++){ var mm=String(st[i6].getAttribute('style')||'').match(/url\\((['\"]?)([^'\")]+)\\1\\)/i); if(mm&&mm[2])cap(mm[2])} }catch(e){}} function scanAll(){ try{scanDoc(document)}catch(e){} try{ var fs=document.querySelectorAll('iframe'); for(var i=0;i<fs.length;i++){ try{var d=fs[i].contentDocument;if(d)scanDoc(d)}catch(e){}} }catch(e){} try{ var of=window.frames; for(var j=0;j<of.length;j++){ try{var d2=of[j].document;if(d2)scanDoc(d2)}catch(e){}} }catch(e){}} function perfPass(){ try{ var rs=performance.getEntriesByType('resource'); var tp=W.__MT_T0||0; for(var i=0;i<rs.length;i++){ var en=rs[i]||{}; var n=String(en.name||''); if(!n)continue; try{if(en.startTime<tp)continue}catch(e){} var b=n.split(/[?#]/)[0]; var t=String(en.initiatorType||''); if(/\\.(jpe?g|png|webp|avif|bmp|tiff?)$/i.test(b)){cap(n);continue} if(/\\.(jpe?g|png|webp|avif|bmp|tiff?)([?#]|$)/i.test(n)){cap(n);continue} if(t==='img'){if(n.indexOf('blob:')===0){capb(n)}else{cap(n)}} } }catch(e){}} function scriptPass(){ try{ if(W.__MT_ORDER.length)return; var sc=document.querySelectorAll('script'); var re=/https?:\\\\?\\/\\\\?\\/[^\"'\\s\\\\<>()[\\]]+?\\.(?:jpe?g|png|webp|avif|bmp)(?:\\?[^\"'\\\\\\s<>()[\\]]*)?/gi; var m,guard=0; for(var i=0;i<sc.length&&guard<800;i++){ var txt=''; try{txt=sc[i].textContent||''}catch(e){continue} if(!txt||txt.length<10)continue; re.lastIndex=0; while((m=re.exec(txt))&&guard<800){ guard++; try{cap(m[0].replace(/\\\\\\//g,'/'))}catch(e){}}} }catch(e){}} scanAll(); perfPass(); scriptPass(); try{return W.__MT_ORDER.slice(0,400)}catch(e){return []} })()";

    private static final String SCROLL_JS =
        "(function(){try{if(window.__MT_SCROLLING)return;window.__MT_SCROLLING=1;window.__MT_SCROLL_DONE=0;var step=Math.max(500,Math.floor(window.innerHeight*0.85));var y=0,n=0,stable=0,lastH=0;function H(){try{return Math.max(document.body?document.body.scrollHeight:0,document.documentElement?document.documentElement.scrollHeight:0)}catch(e){return 0}}lastH=H();function tick(){try{y+=step;window.scrollTo(0,y);n++;var h=H();if(h===lastH)stable++;else{stable=0;lastH=h}var atBottom=(y+window.innerHeight>=h-8);if((atBottom&&stable>=3)||n>200){try{window.scrollTo(0,0)}catch(e){}window.__MT_SCROLL_DONE=1;return}setTimeout(tick,280)}catch(e){window.__MT_SCROLL_DONE=1}}tick()}catch(e){try{window.__MT_SCROLL_DONE=1}catch(e2){}}})()";

    private static final String CLEAR_STORE_JS =
            "(function(){try{window.__MT_FOUND={};window.__MT_ORDER=[];"
                    + "window.__MT_BLOBS={};"
                    + "try{window.__MT_T0=(window.performance&&performance.now)"
                    + "?performance.now():0}catch(e){window.__MT_T0=0}}"
                    + "catch(e){}})()";

    private WebView web;
    private EditText urlBox;
    private TextView extractBtn;
    private TextView countLbl;
    private ProgressBar progress;
    private java.io.File dlDir = null;
    private int dlDone = 0;
    private int dlOk = 0;
    private int dlSeq = 0;
    private final java.util.HashMap<Integer, StringBuilder> dlParts =
            new java.util.HashMap<>();
    private final java.util.LinkedHashSet<String> foundStore =
            new java.util.LinkedHashSet<>();
    private final java.util.LinkedHashSet<String> netLog =
            new java.util.LinkedHashSet<>();
    private String chapterKeyNow = "";
    private boolean recording = false;

    private static final java.util.regex.Pattern RE_IMG_EXT =
            java.util.regex.Pattern.compile(
                    "\\.(jpe?g|png|webp|avif|bmp|tiff?)$",
                    java.util.regex.Pattern.CASE_INSENSITIVE);
    private static final java.util.regex.Pattern RE_IMG_EXT_FULL =
            java.util.regex.Pattern.compile(
                    "\\.(jpe?g|png|webp|avif|bmp|tiff?)([&#]|$)",
                    java.util.regex.Pattern.CASE_INSENSITIVE);
    private static final java.util.regex.Pattern RE_BAD_EXT =
            java.util.regex.Pattern.compile(
                    "\\.(svg|ico|gif|css|js|mjs|json|html?|xml|txt|pdf|zip|rar|7z|gz|"
                            + "mp4|webm|mp3|m4a|ogg|wav|woff2?|ttf|otf|eot|map)$",
                    java.util.regex.Pattern.CASE_INSENSITIVE);
    private static final java.util.regex.Pattern RE_DIM_TAG =
            java.util.regex.Pattern.compile(
                    "[-_]\\d{2,4}x\\d{2,4}\\.\\w{2,5}$",
                    java.util.regex.Pattern.CASE_INSENSITIVE);
    private static final java.util.regex.Pattern RE_JUNK_WORDS =
            java.util.regex.Pattern.compile(
                    "(logo|icon|avatar|banner|sprite|favicon|badge|flag|button|emoji|"
                            + "thumb(nail)?s?|placeholder|blank|spacer|transparen|loading|spinner|"
                            + "pixel|profile|rating|share|follow|comment|credits)",
                    java.util.regex.Pattern.CASE_INSENSITIVE);
    private static final java.util.regex.Pattern RE_AD_WORD =
            java.util.regex.Pattern.compile(
                    "(?:^|[^a-z0-9])ads?[._/-]",
                    java.util.regex.Pattern.CASE_INSENSITIVE);
    private static final java.util.regex.Pattern RE_JUNK_DIR =
            java.util.regex.Pattern.compile(
                    "/(covers?|thumbs?|thumbnails?|avatars?|banners?|creatives?|gifs?|"
                            + "decorations?|emojis?|smileys?|stickers?)/",
                    java.util.regex.Pattern.CASE_INSENSITIVE);
    private static final java.util.regex.Pattern RE_AD_HOST =
            java.util.regex.Pattern.compile(
                    "(pubadx|adservice|adserver|doubleclick|adnxs|propellerads?|onclck|"
                            + "adcash|adsterra|hilltopads?|clickadu|sovrn|taboola|outbrain|zedo|"
                            + "buysellads?|sharethrough|smartadserver|openx|rubicon|criteo|"
                            + "pubmatic|media\\.net)",
                    java.util.regex.Pattern.CASE_INSENSITIVE);
    private static final java.util.regex.Pattern RE_QSZ =
            java.util.regex.Pattern.compile(
                    "[?&](?:type|size|w|h|width|height)=(f?)(\\d{1,4})(?:[_x](\\d{1,4}))?",
                    java.util.regex.Pattern.CASE_INSENSITIVE);

    private static boolean junkUrl(String u) {
        String b = u;
        int h1 = b.indexOf('#');
        if (h1 >= 0) b = b.substring(0, h1);
        int h2 = b.indexOf('?');
        if (h2 >= 0) b = b.substring(0, h2);
        if (RE_BAD_EXT.matcher(b).find()) return true;
        if (RE_DIM_TAG.matcher(b).find()) return true;
        if (RE_JUNK_WORDS.matcher(b).find()) return true;
        if (RE_AD_WORD.matcher(b).find()) return true;
        if (RE_JUNK_DIR.matcher(b).find()) return true;
        if (RE_AD_HOST.matcher(b).find()) return true;
        java.util.regex.Matcher m = RE_QSZ.matcher(u);
        if (!m.find()) return false;
        int a = 0;
        int bb = 0;
        try { a = Integer.parseInt(m.group(2)); } catch (Exception ignored) {}
        try { bb = m.group(3) != null ? Integer.parseInt(m.group(3)) : 0; }
        catch (Exception ignored) {}
        if (a > 0 && bb > 0) return Math.max(a, bb) <= 400;
        if (a > 0 && "f".equals(m.group(1))) return a <= 400;
        return false;
    }

    private static String folderOf(String u) {
        if (u.startsWith("blob:")) return "blob:";
        try {
            java.net.URI p = new java.net.URI(u);
            String path = p.getPath() == null ? "" : p.getPath();
            int cut = path.lastIndexOf('/');
            path = cut >= 0 ? path.substring(0, cut + 1) : "/";
            String scheme = p.getScheme() == null ? "https" : p.getScheme();
            String host = p.getHost() == null ? "" : p.getHost();
            return scheme + "://" + host + path;
        } catch (Exception e) {
            String b = u;
            int h1 = b.indexOf('#');
            if (h1 >= 0) b = b.substring(0, h1);
            int h2 = b.indexOf('?');
            if (h2 >= 0) b = b.substring(0, h2);
            return b;
        }
    }

    private static String shortFolder(String f) {
        if ("blob:".equals(f)) return "درون صفحه (رمزگشایی‌شده)";
        String s = f;
        if (s.startsWith("https://")) s = s.substring(8);
        else if (s.startsWith("http://")) s = s.substring(7);
        if (s.length() > 46)
            s = s.substring(0, 20) + "…" + s.substring(s.length() - 24);
        return s;
    }

    private int snapshotCount() {
        java.util.HashSet<String> keys = new java.util.HashSet<>();
        synchronized (netLog) { keys.addAll(netLog); }
        keys.addAll(foundStore);
        return keys.size();
    }

    private final Handler recountHandler = new Handler();
    private final Runnable recountTick = new Runnable() {
        @Override public void run() {
            try { recountAsync(); } catch (Exception ignored) {}
            recountHandler.postDelayed(this, 3000);
        }
    };

    private static JSONArray parseLinksRaw(String raw) {
        String s = raw == null ? "" : raw.trim();
        if (s.isEmpty()) return null;
        try {
            Object v = new org.json.JSONTokener(s).nextValue();
            if (v instanceof JSONArray) return (JSONArray) v;
            if (v instanceof String) {
                Object inner = new org.json.JSONTokener((String) v).nextValue();
                if (inner instanceof JSONArray) return (JSONArray) inner;
            }
        } catch (Exception ignored) {}
        return null;
    }

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.parseColor("#0b0e14"));

        LinearLayout top = new LinearLayout(this);
        top.setOrientation(LinearLayout.HORIZONTAL);
        top.setGravity(Gravity.CENTER_VERTICAL);
        top.setBackgroundColor(Color.parseColor("#10131b"));
        top.setPadding(dp(10), dp(8), dp(10), dp(8));

        TextView closeBtn = new TextView(this);
        closeBtn.setText("✕");
        closeBtn.setTextColor(Color.parseColor("#c8ceda"));
        closeBtn.setTextSize(16);
        closeBtn.setPadding(dp(12), dp(6), dp(12), dp(6));
        closeBtn.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { finish(); }
        });

        TextView reloadBtn = new TextView(this);
        reloadBtn.setText("↻");
        reloadBtn.setTextColor(Color.parseColor("#e7ebf3"));
        reloadBtn.setTextSize(17);
        reloadBtn.setPadding(dp(12), dp(6), dp(12), dp(6));
        GradientDrawable rlBg = new GradientDrawable();
        rlBg.setColor(Color.parseColor("#2d3649"));
        rlBg.setCornerRadius(dp(12));
        reloadBtn.setBackground(rlBg);
        reloadBtn.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                try { web.reload(); } catch (Exception ignored) {}
            }
        });

        urlBox = new EditText(this);
        urlBox.setTextColor(Color.parseColor("#e7ebf3"));
        urlBox.setHintTextColor(Color.parseColor("#67718a"));
        urlBox.setHint("آدرس سایت مانهوا…");
        urlBox.setTextSize(13);
        urlBox.setSingleLine(true);
        urlBox.setImeOptions(EditorInfo.IME_ACTION_GO);
        GradientDrawable urlBg = new GradientDrawable();
        urlBg.setColor(Color.parseColor("#1a1f2b"));
        urlBg.setCornerRadius(dp(20));
        urlBg.setStroke(1, Color.parseColor("#273043"));
        urlBox.setBackground(urlBg);
        urlBox.setPadding(dp(16), dp(12), dp(16), dp(12));
        urlBox.setOnEditorActionListener((v, action, ev) -> {
            if (action == EditorInfo.IME_ACTION_GO) { goUrl(); return true; }
            return false;
        });

        TextView goBtn = new TextView(this);
        goBtn.setText("برو");
        goBtn.setTextColor(Color.WHITE);
        goBtn.setTextSize(13);
        goBtn.setTypeface(Typeface.DEFAULT_BOLD);
        goBtn.setPadding(dp(16), dp(8), dp(16), dp(8));
        GradientDrawable goBg = new GradientDrawable();
        goBg.setColor(Color.parseColor("#e8590c"));
        goBg.setCornerRadius(dp(16));
        goBtn.setBackground(goBg);
        goBtn.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { goUrl(); }
        });

        top.addView(closeBtn, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT));
        top.addView(reloadBtn, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT));
        LinearLayout.LayoutParams urlLp = new LinearLayout.LayoutParams(
                0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        urlLp.setMargins(dp(6), 0, dp(6), 0);
        top.addView(urlBox, urlLp);
        top.addView(goBtn, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT));
        root.addView(top, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT));

        progress = new ProgressBar(this, null,
                android.R.attr.progressBarStyleHorizontal);
        progress.setMax(100);
        progress.setProgress(0);
        try {
            progress.setProgressTintList(android.content.res.ColorStateList.valueOf(
                    Color.parseColor("#e8590c")));
        } catch (Exception ignored) {}
        root.addView(progress, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(3)));

        web = new WebView(this);
        setupWebView();
        root.addView(web, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));

        LinearLayout bottom = new LinearLayout(this);
        bottom.setOrientation(LinearLayout.HORIZONTAL);
        bottom.setGravity(Gravity.CENTER_VERTICAL);
        bottom.setBackgroundColor(Color.parseColor("#10131b"));
        bottom.setPadding(dp(10), dp(8), dp(10), dp(8));

        countLbl = new TextView(this);
        countLbl.setText("اول فصل را باز کن، بعد «شروع ضبط» را بزن");
        countLbl.setTextColor(Color.parseColor("#8a93a8"));
        countLbl.setTextSize(12);
        countLbl.setPadding(dp(4), 0, dp(4), 0);

        extractBtn = new TextView(this);
        extractBtn.setText("▶ شروع ضبط");
        extractBtn.setTextColor(Color.WHITE);
        extractBtn.setTextSize(14);
        extractBtn.setTypeface(Typeface.DEFAULT_BOLD);
        extractBtn.setPadding(dp(20), dp(12), dp(20), dp(12));
        GradientDrawable exBg = new GradientDrawable();
        exBg.setColor(Color.parseColor("#e8590c"));
        exBg.setCornerRadius(dp(22));
        extractBtn.setBackground(exBg);
        extractBtn.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                if (!recording) startRecording(); else showExtractChoice();
            }
        });

        bottom.addView(countLbl, new LinearLayout.LayoutParams(
                0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        bottom.addView(extractBtn, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT));
        root.addView(bottom, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT));

        setContentView(root);

        String startUrl = getIntent() != null && getIntent().getStringExtra(EXTRA_URL) != null
                ? getIntent().getStringExtra(EXTRA_URL).trim() : "";
        if (startUrl.startsWith("http")) {
            urlBox.setText(startUrl);
            web.loadUrl(startUrl);
            recountAsync();
        } else {
            String home = lastSite.startsWith("http") ? lastSite
                    : "https://www.google.com";
            web.loadUrl(home);
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    private void setupWebView() {
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        s.setBuiltInZoomControls(true);
        s.setDisplayZoomControls(false);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            s.setMixedContentMode(WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE);
        }
        s.setUserAgentString(UA_STR);
        try {
            CookieManager cm = CookieManager.getInstance();
            cm.setAcceptCookie(true);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                cm.setAcceptThirdPartyCookies(web, true);
            }
        } catch (Exception ignored) {}

        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return false;
            }

            @Override
            public android.webkit.WebResourceResponse shouldInterceptRequest(
                    WebView view, WebResourceRequest request) {
                try {
                    if (recording && request != null && request.getUrl() != null) {
                        String u = request.getUrl().toString();
                        if (u.startsWith("http")) {
                            String dest = "";
                            String accept = "";
                            java.util.Map<String, String> hdrs =
                                    request.getRequestHeaders();
                            if (hdrs != null) {
                                for (java.util.Map.Entry<String, String> e :
                                        hdrs.entrySet()) {
                                    String lk = e.getKey() == null
                                            ? "" : e.getKey().toLowerCase();
                                    if (lk.equals("sec-fetch-dest"))
                                        dest = e.getValue() == null
                                                ? "" : e.getValue().toLowerCase();
                                    else if (lk.equals("accept"))
                                        accept = e.getValue() == null
                                                ? "" : e.getValue().toLowerCase();
                                }
                            }
                            String b = u;
                            int h1 = b.indexOf('#');
                            if (h1 >= 0) b = b.substring(0, h1);
                            int h2 = b.indexOf('?');
                            if (h2 >= 0) b = b.substring(0, h2);
                            boolean extImg = RE_IMG_EXT.matcher(b).find()
                                    || RE_IMG_EXT_FULL.matcher(u).find();
                            if (dest.equals("image")
                                    || (accept.contains("image/")
                                        && !accept.contains("text/html"))
                                    || extImg) {
                                if (!junkUrl(u)) {
                                    synchronized (netLog) { netLog.add(u); }
                                }
                            }
                        }
                    }
                } catch (Exception ignored) {}
                return null;
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                try {
                    if (url != null && url.startsWith("http")) lastSite = url;
                    urlBox.setText(url != null ? url : "");
                } catch (Exception ignored) {}
                recountAsync();
            }

            @Override
            public void doUpdateVisitedHistory(WebView view, String url, boolean isReload) {
                super.doUpdateVisitedHistory(view, url, isReload);
                try {
                    if (url != null && url.startsWith("http")) lastSite = url;
                    urlBox.setText(url != null ? url : "");
                } catch (Exception ignored) {}
                recountAsync();
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int newProgress) {
                progress.setProgress(newProgress);
                progress.setVisibility(newProgress >= 100 ? View.GONE : View.VISIBLE);
            }

            @Override
            public boolean onJsAlert(WebView view, String url, String message,
                                     JsResult result) {
                try {
                    Toast.makeText(BrowserActivity.this,
                            message != null ? message : "", Toast.LENGTH_SHORT).show();
                } catch (Exception ignored) {}
                result.confirm();
                return true;
            }
        });
        try {
            web.addJavascriptInterface(new Object() {
                @android.webkit.JavascriptInterface
                public void recv(final int idx, final int total,
                                 final String dataUrl, final String srcUrl) {
                    onDlItem(idx, total, dataUrl, srcUrl);
                }

                @android.webkit.JavascriptInterface
                public void chunk(final int idx, final int ci, final int cn,
                                  final String piece) {
                    onDlChunk(idx, ci, cn, piece);
                }

                @android.webkit.JavascriptInterface
                public void commit(final int idx, final int total,
                                   final String srcUrl) {
                    onDlCommit(idx, total, srcUrl);
                }

                @android.webkit.JavascriptInterface
                public void done(final int total) {
                    onDlDone(total);
                }

                @android.webkit.JavascriptInterface
                public void prev(final String dataUrl) {
                    onPreviewData(dataUrl == null ? "" : dataUrl);
                }

                @android.webkit.JavascriptInterface
                public void th(final String srcUrl, final String dataUrl) {
                    onThumbData(srcUrl == null ? "" : srcUrl,
                            dataUrl == null ? "" : dataUrl);
                }
            }, "MtDl");
        } catch (Exception ignored) {
        }
    }

    private static String smartUrl(String input) {
        String u = input == null ? "" : input.trim();
        if (u.isEmpty()) return null;
        if (u.startsWith("http://") || u.startsWith("https://")) return u;
        boolean domain = u.indexOf(' ') < 0 && u.indexOf('\t') < 0;
        int dots = 0;
        for (int i = 0; domain && i < u.length(); i++) {
            char c = u.charAt(i);
            if (c == '.') { dots++; continue; }
            boolean ok = (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')
                    || (c >= '0' && c <= '9')
                    || c == '-' || c == '_' || c == ':' || c == '/'
                    || c == '?' || c == '#' || c == '~';
            if (!ok) domain = false;
        }
        if (domain && dots > 0) return "https://" + u;
        try {
            return "https://www.google.com/search?q="
                    + java.net.URLEncoder.encode(u, "UTF-8");
        } catch (Exception e) {
            return "https://www.google.com/search?q=" + u;
        }
    }

    private void goUrl() {
        String u = smartUrl(urlBox.getText().toString());
        if (u == null) return;
        urlBox.setText(u);
        web.loadUrl(u);
    }

    private static String chapterKey(String raw) {
        String u = raw == null ? "" : raw.trim();
        if (!u.startsWith("http")) return u;
        try {
            java.net.URI p = new java.net.URI(u);
            String host = p.getHost() == null ? "" : p.getHost();
            String path = p.getPath() == null ? "" : p.getPath();
            while (path.endsWith("/")) path = path.substring(0, path.length() - 1);
            java.util.List<String> list = new java.util.ArrayList<>();
            if (!path.isEmpty()) {
                for (String s : path.substring(1).split("/")) {
                    if (!s.isEmpty()) list.add(s);
                }
            }
            int strips = 0;
            while (list.size() >= 2 && strips < 2) {
                String last = list.get(list.size() - 1);
                if (!last.matches("\\d{1,4}")) break;
                String parent = list.get(list.size() - 2);
                boolean parentNumeric = parent.matches("\\d+");
                boolean parentChapMark =
                        parent.matches(".*(ch|chap|chapter|episode|ep|sec|part)[-_]?\\d.*");
                if (parentNumeric || parentChapMark) {
                    list.remove(list.size() - 1);
                    strips++;
                } else break;
            }
            String q = p.getRawQuery() == null ? "" : p.getRawQuery();
            java.util.List<String> kept = new java.util.ArrayList<>();
            if (!q.isEmpty()) {
                for (String kv : q.split("&")) {
                    if (kv.trim().isEmpty()) continue;
                    String key = kv.contains("=")
                            ? kv.substring(0, kv.indexOf('=')) : kv;
                    if (!key.toLowerCase().matches("page|pg|pagina")) kept.add(kv);
                }
            }
            java.util.Collections.sort(kept);
            StringBuilder sb = new StringBuilder(host);
            for (String s : list) sb.append('/').append(s);
            if (!kept.isEmpty()) {
                sb.append('?');
                for (int i = 0; i < kept.size(); i++) {
                    if (i > 0) sb.append('&');
                    sb.append(kept.get(i));
                }
            }
            return sb.toString();
        } catch (Exception e) {
            String b = u;
            int h1 = b.indexOf('#');
            if (h1 >= 0) b = b.substring(0, h1);
            int h2 = b.indexOf('?');
            if (h2 >= 0) b = b.substring(0, h2);
            return b;
        }
    }

    private void syncChapterKey() {
        try {
            String cur;
            try { cur = web.getUrl(); } catch (Exception e) { cur = null; }
            String k = chapterKey(cur);
            if (!k.equals(chapterKeyNow)) {
                chapterKeyNow = k;
                foundStore.clear();
                synchronized (netLog) { netLog.clear(); }
                try { web.evaluateJavascript(CLEAR_STORE_JS, null); }
                catch (Exception ignored) {}
            }
        } catch (Exception ignored) {}
    }

    private int mergeFound(JSONArray arr) {
        if (arr != null) {
            for (int i = 0; i < arr.length(); i++) {
                String u = arr.optString(i);
                if (u != null && !u.trim().isEmpty()) foundStore.add(u);
            }
        }
        return foundStore.size();
    }

    private JSONArray storeSnapshot() {
        JSONArray arr = new JSONArray();
        java.util.HashSet<String> seen = new java.util.HashSet<>();
        for (String u : foundStore) if (seen.add(u)) arr.put(u);
        synchronized (netLog) {
            for (String u : netLog) if (seen.add(u)) arr.put(u);
        }
        return arr;
    }

    private void startRecording() {
        String cur;
        try { cur = web.getUrl() != null ? web.getUrl() : ""; }
        catch (Exception e) { cur = ""; }
        if (cur.isEmpty() || cur.equals("about:blank")) {
            Toast.makeText(this, "اول یک سایت را باز کن",
                    Toast.LENGTH_SHORT).show();
            return;
        }
        recording = true;
        foundStore.clear();
        synchronized (netLog) { netLog.clear(); }
        chapterKeyNow = chapterKey(cur);
        try { web.evaluateJavascript(CLEAR_STORE_JS, null); }
        catch (Exception ignored) {}
        extractBtn.setText("🖼 استخراج");
        countLbl.setText("در حال ضبط… صفحه فصل را ورق بزن");
        try { web.reload(); } catch (Exception ignored) {}
    }

    private void recountAsync() {
        if (!recording) return;
        try {
            syncChapterKey();
            web.evaluateJavascript(EXTRACT_JS, value -> {
                try {
                    JSONArray arr = parseLinksRaw(value);
                    runOnUiThread(() -> {
                        mergeFound(arr);
                        final int n = snapshotCount();
                        countLbl.setText(n > 0
                                ? "● " + n + " عکس ضبط شد"
                                : "در حال ضبط… صفحه فصل را ورق بزن");
                    });
                } catch (Exception ignored) {}
            });
        } catch (Exception ignored) {}
    }

    private interface ArrCallback {
        void onResult(JSONArray arr);
    }

    private void startAutoScroll(final Runnable done) {
        try {
            web.evaluateJavascript(SCROLL_JS, null);
        } catch (Exception ignored) {}
        final Handler h = new Handler();
        final long t0 = System.currentTimeMillis();
        final Runnable[] tick = new Runnable[1];
        tick[0] = () -> {
            try {
                web.evaluateJavascript("(window.__MT_SCROLL_DONE===1)?1:0", v -> {
                    boolean finished = "1".equals(v)
                            || System.currentTimeMillis() - t0 > 60000;
                    if (finished) {
                        h.postDelayed(done, 700);
                    } else {
                        h.postDelayed(tick[0], 800);
                    }
                });
            } catch (Exception e) {
                done.run();
            }
        };
        h.postDelayed(tick[0], 900);
    }

    private static boolean hasBlobs(JSONArray arr) {
        if (arr == null) return false;
        try {
            for (int i = 0; i < arr.length(); i++) {
                if (arr.optString(i).startsWith("blob:")) return true;
            }
        } catch (Exception ignored) {}
        return false;
    }

    private void rankByDom(final java.util.List<String> urls,
                           final java.util.function.Consumer<java.util.List<String>> then) {
        if (urls.isEmpty()) { then.accept(urls); return; }
        try {
            StringBuilder sb = new StringBuilder("[");
            for (int i = 0; i < urls.size(); i++) {
                if (i > 0) sb.append(',');
                sb.append(org.json.JSONObject.quote(urls.get(i)));
            }
            sb.append(']');
            final String knownJson = sb.toString();
            StringBuilder js = new StringBuilder("(function(){");
            js.append("try{");
            js.append("var KNOWN=").append(knownJson).append(";");
            js.append("function keyOf(u){var s=String(u);var b=s.split(/[?#]/)[0];")
                    .append("if(!/\\.(jpe?g|png|webp|avif|bmp|tiff?)$/i.test(b))return s.split('#')[0];")
                    .append("return b.replace(/[-_]\\d{2,4}x\\d{2,4}\\./i,'.')}");
            js.append("function ukey(u){return String(u).indexOf('blob:')===0?")
                    .append("String(u).split('#')[0]:keyOf(u)}");
            js.append("var byKey={};");
            js.append("for(var i=0;i<KNOWN.length;i++)byKey[ukey(KNOWN[i])]=KNOWN[i];");
            js.append("var out=[],seen={};");
            js.append("function radd(u){");
            js.append("try{");
            js.append("if(!u)return;");
            js.append("u=String(u).trim();");
            js.append("if(u.indexOf('data:')===0)return;");
            js.append("if(u.indexOf('blob:')!==0){")
                    .append("try{var a=document.createElement('a');a.href=u;u=a.href}catch(e){}}");
            js.append("var k=ukey(u);");
            js.append("if(!k||seen[k])return;");
            js.append("if(!Object.prototype.hasOwnProperty.call(byKey,k))return;");
            js.append("seen[k]=1;out.push(byKey[k])");
            js.append("}catch(e){}}");
            js.append("var DTS=['data-src','data-lazy-src','data-original','data-original-src',")
                    .append("'data-orig-src','data-lazy','data-url','data-image','data-echo','data-cfsrc',")
                    .append("'data-hi-res-src','data-full-src','data-full_image','data-large-src',")
                    .append("'data-file','data-path','data-actualsrc'];");
            js.append("function best(ss){try{var p=String(ss).split(','),b='',w=0;")
                    .append("for(var k=0;k<p.length;k++){var tk=p[k].trim().split(/\\s+/);")
                    .append("var u0=tk[0]||'';var w0=parseInt(String(tk[1]||'').replace(/[^0-9]/g,''),10)||0;")
                    .append("if(u0&&w0>=w){w=w0;b=u0}}return b}catch(e){return ''}}");
            js.append("var els=[];");
            js.append("try{els=document.querySelectorAll('img,source,a[href],[style*=\"url(\"]')}catch(e){}");
            js.append("for(var j=0;j<els.length;j++){");
            js.append("var el=els[j],tg=el.tagName;");
            js.append("if(tg==='A'){radd(el.getAttribute('href')||'');continue}");
            js.append("if(tg!=='IMG'&&tg!=='SOURCE'){");
            js.append("try{var mm=String(el.getAttribute('style')||'')")
                    .append(".match(/url\\((['\"]?)([^'\")]+)\\1\\)/i);if(mm&&mm[2])radd(mm[2])}catch(e){}");
            js.append("continue}");
            js.append("try{radd(el.currentSrc||el.src||'')}catch(e){}");
            js.append("try{var ss=el.getAttribute('srcset')||el.getAttribute('data-srcset');")
                    .append("if(ss){var bs=best(ss);if(bs)radd(bs)}}catch(e){}");
            js.append("for(var d=0;d<DTS.length;d++){");
            js.append("try{var v=el.getAttribute(DTS[d]);if(v&&v.length>4)radd(v)}catch(e){}}");
            js.append("}");
            js.append("return out");
            js.append("}catch(e){return []}");
            js.append("})()");
            web.evaluateJavascript(js.toString(), raw -> {
                java.util.ArrayList<String> ranked = new java.util.ArrayList<>();
                try {
                    JSONArray arr = parseLinksRaw(raw);
                    if (arr != null) {
                        for (int i = 0; i < arr.length(); i++)
                            ranked.add(arr.optString(i));
                    }
                } catch (Exception ignored) {
                }
                if (ranked.isEmpty()) { then.accept(urls); return; }
                java.util.HashSet<String> seen = new java.util.HashSet<>();
                java.util.ArrayList<String> out = new java.util.ArrayList<>(urls.size());
                for (String u : ranked) if (seen.add(u)) out.add(u);
                for (String u : urls) if (seen.add(u)) out.add(u);
                then.accept(out);
            });
        } catch (Exception e) {
            then.accept(urls);
        }
    }

    private void finishWithDomOrder(final JSONArray snap, final ArrCallback then) {
        try {
            final java.util.ArrayList<String> urls = new java.util.ArrayList<>();
            for (int i = 0; i < snap.length(); i++) {
                String u = snap.optString(i);
                if (u != null && !u.trim().isEmpty()) urls.add(u);
            }
            rankByDom(urls, ranked -> {
                JSONArray out = new JSONArray();
                for (String u : ranked) out.put(u);
                then.onResult(out);
            });
        } catch (Exception e) {
            then.onResult(snap);
        }
    }

    private void extractWithScroll(final ArrCallback then) {
        try {
            syncChapterKey();
            web.evaluateJavascript(EXTRACT_JS, value -> runOnUiThread(() -> {
                final JSONArray arr = parseLinksRaw(value);
                mergeFound(arr);
                final JSONArray snapshot = storeSnapshot();
                if (snapshot.length() > 0 && !hasBlobs(snapshot)) {
                    finishWithDomOrder(snapshot, then);
                    return;
                }
                countLbl.setText("… در حال آماده‌سازی صفحه (اسکرول خودکار)");
                startAutoScroll(() -> {
                    try {
                        syncChapterKey();
                        web.evaluateJavascript(EXTRACT_JS, v2 -> runOnUiThread(() -> {
                            JSONArray arr2 = parseLinksRaw(v2);
                            mergeFound(arr2);
                            finishWithDomOrder(storeSnapshot(), then);
                        }));
                    } catch (Exception e) {
                        runOnUiThread(() -> finishWithDomOrder(storeSnapshot(), then));
                    }
                });
            }));
        } catch (Exception e) {
            runOnUiThread(() -> then.onResult(null));
        }
    }

    private static boolean isMangaPlusViewer(String u) {
        if (u == null) return false;
        try {
            java.net.URL p = new java.net.URL(u);
            String h = p.getHost() == null ? "" : p.getHost().toLowerCase();
            if (!h.equals("mangaplus.shueisha.co.jp")
                    && !h.equals("www.mangaplus.shueisha.co.jp"))
                return false;
            return p.getPath() != null && p.getPath().startsWith("/viewer/");
        } catch (Exception e) {
            return false;
        }
    }

    private static String sniffMime(byte[] d) {
        if (d == null || d.length < 12) return null;
        if ((d[0] & 0xFF) == 0xFF && (d[1] & 0xFF) == 0xD8) return "image/jpeg";
        if ((d[0] & 0xFF) == 0x89 && d[1] == 0x50) return "image/png";
        if (d[0] == 'R' && d[1] == 'I' && d[2] == 'F' && d[8] == 'W') return "image/webp";
        if (d[0] == 'G' && d[1] == 'I' && d[2] == 'F') return "image/gif";
        return null;
    }

    private String httpFetchDataUrl(String u) {
        try {
            java.net.HttpURLConnection c =
                    (java.net.HttpURLConnection) new java.net.URL(u).openConnection();
            c.setConnectTimeout(15000);
            c.setReadTimeout(40000);
            c.setRequestProperty("User-Agent", UA_STR);
            try {
                String ck = CookieManager.getInstance().getCookie(u);
                if (ck != null && !ck.isEmpty()) c.setRequestProperty("Cookie", ck);
            } catch (Exception ignored) {
            }
            try {
                String ref = web.getUrl();
                if (ref != null && ref.startsWith("http"))
                    c.setRequestProperty("Referer", ref);
            } catch (Exception ignored) {
            }
            int code = c.getResponseCode();
            if (code < 200 || code >= 300) {
                c.disconnect();
                return "";
            }
            java.io.ByteArrayOutputStream bo = new java.io.ByteArrayOutputStream();
            try (java.io.InputStream in = c.getInputStream()) {
                byte[] buf = new byte[16384];
                int n;
                while ((n = in.read(buf)) > 0) bo.write(buf, 0, n);
            }
            byte[] data = bo.toByteArray();
            String mime = c.getContentType();
            c.disconnect();
            if (data.length == 0) return "";
            if (mime == null || !mime.toLowerCase().startsWith("image/"))
                mime = sniffMime(data);
            if (mime == null) return "";
            if (mime.contains(";")) mime = mime.split(";")[0].trim();
            return "data:" + mime + ";base64,"
                    + android.util.Base64.encodeToString(data,
                            android.util.Base64.NO_WRAP);
        } catch (Exception e) {
            return "";
        }
    }

    private void onDlItem(final int idx, final int total, String dataUrl,
                          final String srcUrl) {
        try {
            if (dlDir == null) return;
            String d = dataUrl == null ? "" : dataUrl.trim();
            if (d.isEmpty() || !d.startsWith("data:image/"))
                d = httpFetchDataUrl(srcUrl);
            if (d.startsWith("data:image/") && !d.startsWith("data:image/svg")) {
                int ci = d.indexOf(',');
                if (ci > 0) {
                    String head = d.substring(0, ci).toLowerCase();
                    byte[] data = android.util.Base64.decode(
                            d.substring(ci + 1), android.util.Base64.NO_WRAP);
                    if (data != null && data.length > 0) {
                        int maxDim = 0;
                        try {
                            android.graphics.BitmapFactory.Options o =
                                    new android.graphics.BitmapFactory.Options();
                            o.inJustDecodeBounds = true;
                            android.graphics.BitmapFactory.decodeByteArray(
                                    data, 0, data.length, o);
                            maxDim = Math.max(o.outWidth, o.outHeight);
                        } catch (Exception ignored) {}
                        String headStr = "";
                        try {
                            headStr = new String(
                                    java.util.Arrays.copyOfRange(
                                            data, 0, Math.min(600, data.length)),
                                    "ISO-8859-1");
                        } catch (Exception ignored) {}
                        boolean small =
                                (maxDim >= 1 && maxDim < 300)
                                || (maxDim <= 0 && data.length < 4096)
                                || headStr.toLowerCase().contains("<svg");
                        if (!small) {
                            String ext = ".jpg";
                            java.util.regex.Matcher m = java.util.regex.Pattern
                                    .compile("data:image/(jpe?g|png|webp|bmp)")
                                    .matcher(head);
                            if (m.find())
                                ext = "." + ("jpeg".equals(m.group(1))
                                        ? "jpg" : m.group(1));
                            int seq = ++dlSeq;
                            java.io.File f = new java.io.File(dlDir,
                                    "page_" + String.format(java.util.Locale.US,
                                            "%03d", seq) + ext);
                            try (java.io.FileOutputStream fo =
                                         new java.io.FileOutputStream(f)) {
                                fo.write(data);
                            }
                            dlOk++;
                        }
                    }
                }
            }
            dlDone++;
            final int done = dlDone;
            final int ok = dlOk;
            runOnUiThread(() -> countLbl.setText(
                    "⬇ " + done + "/" + total + (ok > 0 ? " — " + ok + " ✓" : "")));
        } catch (Exception ignored) {
        }
    }

    private void onDlChunk(final int idx, final int ci, final int cn,
                           final String piece) {
        try {
            if (ci == 0) dlParts.remove(idx);
            StringBuilder sb = dlParts.get(idx);
            if (sb == null) {
                sb = new StringBuilder();
                dlParts.put(idx, sb);
            }
            sb.append(piece == null ? "" : piece);
            if (sb.length() > 40 * 1024 * 1024) {
                sb.setLength(0);
                sb.append("!!OVERSIZE");
            }
        } catch (Exception ignored) {
        }
    }

    private void onDlCommit(final int idx, final int total,
                             final String srcUrl) {
        String dataUrl = "";
        try {
            StringBuilder sb = dlParts.remove(idx);
            if (sb != null) {
                dataUrl = sb.toString();
                if (dataUrl.startsWith("!!OVERSIZE")) dataUrl = "";
            }
        } catch (Exception e) {
            dataUrl = "";
        }
        onDlItem(idx, total, dataUrl, srcUrl);
    }

    private void onDlDone(final int total) {
        runOnUiThread(() -> {
            try {
                int cnt = 0;
                if (dlDir != null && dlDir.isDirectory()) {
                    java.io.File[] fs = dlDir.listFiles();
                    cnt = fs == null ? 0 : fs.length;
                }
                if (cnt > 0) {
                    Intent out = new Intent();
                    out.putExtra(EXTRA_DL_DIR, dlDir.getAbsolutePath());
                    out.putExtra(EXTRA_DL_COUNT, cnt);
                    setResult(RESULT_OK, out);
                    Toast.makeText(BrowserActivity.this,
                            "✅ " + cnt + " عکس دانلود شد",
                            Toast.LENGTH_SHORT).show();
                } else {
                    Toast.makeText(BrowserActivity.this,
                            "هیچ عکسی دانلود نشد", Toast.LENGTH_LONG).show();
                }
                finish();
            } catch (Exception ignored) {
            }
        });
    }

    private void startDownloadAll(java.util.List<String> urls) {
        try {
            dlDir = new java.io.File(getCacheDir(),
                    "mt_dl_" + System.currentTimeMillis());
            dlDir.mkdirs();
            dlDone = 0;
            dlOk = 0;
            dlSeq = 0;
            dlParts.clear();
        } catch (Exception e) {
            Toast.makeText(this, "خطا در آماده‌سازی دانلود: " + e.getMessage(),
                    Toast.LENGTH_LONG).show();
            return;
        }
        org.json.JSONArray arr = new org.json.JSONArray(urls);
        StringBuilder js = new StringBuilder();
        js.append("(function(){try{var urls=").append(arr.toString()).append(";");
        js.append("function afix(b){return new Promise(function(res){")
           .append("try{")
           .append("if(!b||String(b.type||'').indexOf('avif')<0){res(b);return}")
           .append("createImageBitmap(b).then(function(bp){")
           .append("try{var c=document.createElement('canvas');")
           .append("c.width=bp.width||1;c.height=bp.height||1;")
           .append("c.getContext('2d').drawImage(bp,0,0);")
           .append("if(c.toBlob){c.toBlob(function(j){res(j||b)},'image/jpeg',0.92);return}")
           .append("res(b)}")
           .append("catch(e){res(b)}})")
           .append(".catch(function(){res(b)})")
           .append("}catch(e){res(b)}})}");
        js.append("function toData(u){")
           .append("try{var k=String(u).split('#')[0];")
           .append("if(window.__MT_BLOBS&&window.__MT_BLOBS[k]&&window.__MT_BLOBS[k].size){")
           .append("var bb=window.__MT_BLOBS[k];")
           .append("return afix(bb).then(function(nb){")
           .append("return new Promise(function(res){")
           .append("try{var f=new FileReader();")
           .append("f.onload=function(){res(String(f.result||''))};")
           .append("f.onerror=function(){res('')};")
           .append("f.readAsDataURL(nb)}")
           .append("catch(e){res('')}})})}}catch(e){}")
           .append("function fgo(o){return fetch(u,o)")
           .append(".then(function(r){if(!r.ok)return '';return r.blob()})}")
           .append("return fgo()")
           .append(".then(function(b){if(b)return b;return fgo({credentials:'include'})})")
           .append(".then(function(b){if(!b)return '';return afix(b)})")
           .append(".then(function(b){if(!b)return '';return new Promise(function(res){")
           .append("try{var f=new FileReader();")
           .append("f.onload=function(){res(String(f.result||''))};")
           .append("f.onerror=function(){res('')};f.readAsDataURL(b)}")
           .append("catch(e){res('')}})})")
           .append(".then(function(d){if(d&&d.indexOf('data:image')===0)return d;")
           .append("if(String(u).indexOf('blob:')!==0)return '';")
           .append("return new Promise(function(res2){")
           .append("try{var im=null;")
           .append("try{var cs=document.querySelectorAll('img');var kk=String(u).split('#')[0];")
           .append("for(var q=0;q<cs.length;q++){var ss='';")
           .append("try{ss=cs[q].currentSrc||cs[q].src||''}catch(e5){}")
           .append("if(ss&&ss.split('#')[0]===kk){im=cs[q];break}}}catch(e7){}")
           .append("if(im&&im.complete&&im.naturalWidth>0){")
           .append("try{var cv2=document.createElement('canvas');")
           .append("cv2.width=im.naturalWidth;cv2.height=im.naturalHeight;")
           .append("cv2.getContext('2d').drawImage(im,0,0);")
           .append("res2(cv2.toDataURL('image/jpeg',0.92)||'');return}")
           .append("catch(e6){}}")
           .append("im=new Image();")
           .append("im.onload=function(){try{var cv=document.createElement('canvas');")
           .append("cv.width=im.naturalWidth||1;cv.height=im.naturalHeight||1;")
           .append("var ctx=cv.getContext('2d');ctx.drawImage(im,0,0);")
           .append("res2(cv.toDataURL('image/jpeg',0.92)||'')}catch(e3){res2('')}};")
           .append("im.onerror=function(){res2('')};im.src=u}")
           .append("catch(e4){res2('')}})})}");
        js.append("var CH=262144;");
        js.append("function send(idx,total,u,d){")
           .append("try{d=String(d||'');")
           .append("if(d.length<=CH){try{window.MtDl.recv(idx,total,d,u)}catch(e){}return}")
           .append("var n=Math.ceil(d.length/CH);")
           .append("for(var c=0;c<n;c++){")
           .append("try{window.MtDl.chunk(idx,c,n,d.substr(c*CH,CH))}catch(e){}}")
           .append("try{window.MtDl.commit(idx,total,u)}catch(e){}}")
           .append("catch(e){try{window.MtDl.recv(idx,total,'',u)}catch(e2){}}}");
        js.append("var i=0,pending=0;function step(){")
           .append("if(i>=urls.length){if(pending<=0){try{window.MtDl.done(urls.length)}catch(e){}}return}")
           .append("var idx=i;var u=urls[i];i++;pending++;")
           .append("toData(u).then(function(d){")
           .append("send(idx,urls.length,u,d);pending--;step()})")
           .append(".catch(function(){")
           .append("send(idx,urls.length,u,'');pending--;step()})};");
        js.append("step();step();step();");
        js.append("}catch(e){try{window.MtDl.done(0)}catch(e2){}}})()");
        try {
            web.evaluateJavascript(js.toString(), null);
        } catch (Exception e) {
            Toast.makeText(this, "خطا در شروع دانلود: " + e.getMessage(),
                    Toast.LENGTH_LONG).show();
        }
    }

    private void showExtractChoice() {
        String curUrl;
        try { curUrl = web.getUrl() != null ? web.getUrl() : ""; }
        catch (Exception e) { curUrl = ""; }
        final String cur = curUrl;
        extractBtn.setText("… در حال آماده‌سازی");
        extractWithScroll(arr -> {
            extractBtn.setText("🖼 استخراج");
            try {
                java.util.ArrayList<String> all = new java.util.ArrayList<>();
                if (arr != null) {
                    for (int i = 0; i < arr.length(); i++) {
                        String u = arr.optString(i);
                        if (u != null && !u.trim().isEmpty()) all.add(u);
                    }
                }
                if (all.isEmpty()) {
                    if (!cur.isEmpty() && isMangaPlusViewer(cur)) {
                        showLinkDownloadChoice(
                                java.util.Collections.singletonList(cur), true);
                        return;
                    }
                    countLbl.setText("هیچ عکسی ضبط نشد — فصل را باز کن و ورق بزن");
                    Toast.makeText(BrowserActivity.this,
                            "هیچ عکسی ضبط نشد — صفحه فصل را باز کن و ورق بزن",
                            Toast.LENGTH_LONG).show();
                    return;
                }
                showFolderDialog(all);
            } catch (final Exception e) {
                Toast.makeText(BrowserActivity.this,
                        "خطا در استخراج: " + e.getMessage(),
                        Toast.LENGTH_LONG).show();
            }
        });
    }

    private void showLinkDownloadChoice(final java.util.List<String> sel) {
        showLinkDownloadChoice(sel, false);
    }

    private void showLinkDownloadChoice(final java.util.List<String> sel,
                                        final boolean mpMode) {
        try {
            showLinkDownloadChoiceImpl(sel, mpMode);
        } catch (Exception e) {
            android.app.AlertDialog.Builder b =
                    new android.app.AlertDialog.Builder(this);
            b.setTitle(mpMode ? "فصلِ مانگاپلاس"
                    : "استخراج (" + sel.size() + " عکس)");
            b.setItems(new String[]{"استخراج با لینک", "استخراج با دانلود"},
                    (dialog, which) -> {
                        if (mpMode || which == 0) finishWithLinks(sel);
                        else downloadSelected(sel);
                    });
            b.setNegativeButton("انصراف", null);
            b.show();
        }
    }

    private void showLinkDownloadChoiceImpl(final java.util.List<String> sel,
                                            final boolean mpMode) {
        final android.app.Dialog dlg = new android.app.Dialog(this);
        dlg.requestWindowFeature(android.view.Window.FEATURE_NO_TITLE);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(16), dp(16), dp(16), dp(14));
        GradientDrawable rootBg = new GradientDrawable(
                GradientDrawable.Orientation.TOP_BOTTOM,
                new int[]{Color.parseColor("#171b24"), Color.parseColor("#10141c")});
        rootBg.setCornerRadius(dp(18));
        rootBg.setStroke(dp(1), Color.parseColor("#2a3242"));
        root.setBackground(rootBg);

        TextView title = new TextView(this);
        title.setText(mpMode ? "فصلِ مانگاپلاس"
                : "استخراج (" + sel.size() + " عکس)");
        title.setTextColor(Color.parseColor("#e7ebf3"));
        title.setTextSize(15);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        root.addView(title);

        TextView sub = new TextView(this);
        sub.setText(mpMode
                ? "موتور خودش عکس‌ها را از API رسمی می‌گیرد و رمزگشایی می‌کند"
                : "روشِ استخراج را انتخاب کن");
        sub.setTextColor(Color.parseColor("#8a93a8"));
        sub.setTextSize(11.5f);
        android.widget.LinearLayout.LayoutParams subLp =
                new android.widget.LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT);
        subLp.topMargin = dp(2);
        subLp.bottomMargin = dp(10);
        root.addView(sub, subLp);

        final String[][] items = mpMode ? new String[][]{
                {"🖼", "استخراج با لینک",
                        "لینکِ فصل در فیلدِ ورودی می‌نشیند"},
                {"⬇", "استخراج با دانلود",
                        "همان لینک — موتور عکس‌ها را می‌گیرد"}} : new String[][]{
                {"🖼", "استخراج با لینک",
                        "فقط لینک‌ها در فیلدِ ورودی می‌نشینند"},
                {"⬇", "استخراج با دانلود",
                        "عکس‌ها همین‌جا دانلود و به سرور می‌روند"}};
        for (int i = 0; i < items.length; i++) {
            final int idx = i;
            LinearLayout card = new LinearLayout(this);
            card.setOrientation(LinearLayout.HORIZONTAL);
            card.setGravity(Gravity.CENTER_VERTICAL);
            card.setPadding(dp(14), dp(12), dp(14), dp(12));
            GradientDrawable cardBg = new GradientDrawable();
            cardBg.setColor(Color.parseColor("#1a1f2b"));
            cardBg.setCornerRadius(dp(14));
            cardBg.setStroke(dp(1), Color.parseColor("#232b3b"));
            card.setBackground(cardBg);

            TextView ico = new TextView(this);
            ico.setText(items[i][0]);
            ico.setTextSize(22);
            ico.setPadding(0, 0, dp(12), 0);
            card.addView(ico, new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.WRAP_CONTENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT));

            LinearLayout txts = new LinearLayout(this);
            txts.setOrientation(LinearLayout.VERTICAL);
            TextView t1 = new TextView(this);
            t1.setText(items[i][1]);
            t1.setTextColor(Color.parseColor("#e7ebf3"));
            t1.setTextSize(14);
            t1.setTypeface(Typeface.DEFAULT_BOLD);
            TextView t2 = new TextView(this);
            t2.setText(items[i][2]);
            t2.setTextColor(Color.parseColor("#8a93a8"));
            t2.setTextSize(11.5f);
            txts.addView(t1);
            txts.addView(t2);
            card.addView(txts, new LinearLayout.LayoutParams(
                    0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));

            card.setOnClickListener(v -> {
                try { dlg.dismiss(); } catch (Exception ignored) {}
                if (mpMode || idx == 0) finishWithLinks(sel);
                else downloadSelected(sel);
            });
            LinearLayout.LayoutParams cardLp = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT);
            cardLp.bottomMargin = dp(8);
            root.addView(card, cardLp);
        }

        TextView cancel = new TextView(this);
        cancel.setText("انصراف");
        cancel.setTextColor(Color.parseColor("#c8ceda"));
        cancel.setTextSize(13);
        cancel.setTypeface(Typeface.DEFAULT_BOLD);
        cancel.setGravity(Gravity.CENTER);
        cancel.setPadding(dp(10), dp(11), dp(10), dp(11));
        GradientDrawable cBg = new GradientDrawable();
        cBg.setColor(Color.parseColor("#2d3649"));
        cBg.setCornerRadius(dp(12));
        cancel.setBackground(cBg);
        cancel.setOnClickListener(v -> {
            try { dlg.dismiss(); } catch (Exception ignored) {}
        });
        root.addView(cancel, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT));

        dlg.setContentView(root);
        dlg.show();
        android.view.Window w = dlg.getWindow();
        if (w != null) {
            w.setBackgroundDrawable(new android.graphics.drawable.ColorDrawable(
                    Color.TRANSPARENT));
            w.setLayout(Math.min(
                    getResources().getDisplayMetrics().widthPixels - dp(32),
                    dp(440)), ViewGroup.LayoutParams.WRAP_CONTENT);
        }
    }

    private static final android.util.LruCache<String, android.graphics.Bitmap>
            THUMB_CACHE = new android.util.LruCache<String,
            android.graphics.Bitmap>(24 * 1024 * 1024) {
        @Override
        protected int sizeOf(String k, android.graphics.Bitmap v) {
            try {
                return v.getByteCount();
            } catch (Exception e) {
                return 1;
            }
        }
    };
    private static final java.util.Set<String> THUMB_FAILED =
            java.util.Collections.synchronizedSet(
                    new java.util.HashSet<String>());
    private static final java.util.concurrent.ExecutorService THUMB_POOL =
            java.util.concurrent.Executors.newFixedThreadPool(3);
    private static final java.util.Map<String, java.util.List<android.widget.ImageView>> THUMB_VIEWS =
            new java.util.concurrent.ConcurrentHashMap<>();

    private void loadThumb(final android.widget.ImageView iv, final String u) {
        try {
            iv.setTag(u);
            try {
                THUMB_VIEWS.computeIfAbsent(u,
                        k -> java.util.Collections.synchronizedList(
                                new java.util.ArrayList<>())).add(iv);
            } catch (Exception ignored) {
            }
            android.graphics.Bitmap b = THUMB_CACHE.get(u);
            if (b != null) {
                iv.setImageBitmap(b);
                iv.setVisibility(View.VISIBLE);
                return;
            }
            if (u.startsWith("blob:")) {
                loadThumbViaJs(u);
                return;
            }
            if (THUMB_FAILED.contains(u)) {
                iv.setVisibility(View.INVISIBLE);
                return;
            }
            iv.setImageDrawable(null);
            THUMB_POOL.execute(() -> {
                android.graphics.Bitmap bmp = null;
                try {
                    java.net.HttpURLConnection c =
                            (java.net.HttpURLConnection) new java.net.URL(u)
                                    .openConnection();
                    c.setConnectTimeout(9000);
                    c.setReadTimeout(16000);
                    c.setRequestProperty("User-Agent", UA_STR);
                    try {
                        String ck = CookieManager.getInstance().getCookie(u);
                        if (ck != null && !ck.isEmpty())
                            c.setRequestProperty("Cookie", ck);
                    } catch (Exception ignored) {
                    }
                    try {
                        String ref = null;
                        try {
                            ref = web.getUrl();
                        } catch (Exception ignored0) {
                        }
                        if (ref != null && ref.startsWith("http"))
                            c.setRequestProperty("Referer", ref);
                    } catch (Exception ignored) {
                    }
                    int code = c.getResponseCode();
                    if (code >= 200 && code < 300) {
                        java.io.ByteArrayOutputStream bo =
                                new java.io.ByteArrayOutputStream();
                        try (java.io.InputStream in = c.getInputStream()) {
                            byte[] buf = new byte[16384];
                            int n;
                            while ((n = in.read(buf)) > 0) bo.write(buf, 0, n);
                        }
                        byte[] data = bo.toByteArray();
                        c.disconnect();
                        if (data.length > 0 && data.length < 25 * 1024 * 1024) {
                            android.graphics.BitmapFactory.Options o =
                                    new android.graphics.BitmapFactory.Options();
                            o.inJustDecodeBounds = true;
                            android.graphics.BitmapFactory.decodeByteArray(
                                    data, 0, data.length, o);
                            int maxDim = Math.max(o.outWidth, o.outHeight);
                            int sc = 1;
                            while (maxDim / sc > 260) sc *= 2;
                            android.graphics.BitmapFactory.Options o2 =
                                    new android.graphics.BitmapFactory.Options();
                            o2.inSampleSize = sc;
                            bmp = android.graphics.BitmapFactory.decodeByteArray(
                                    data, 0, data.length, o2);
                        }
                    } else {
                        c.disconnect();
                    }
                } catch (Exception ignored) {
                }
                if (bmp == null) {
                    THUMB_FAILED.add(u);
                    runOnUiThread(() -> {
                        try {
                            if (u.equals(iv.getTag()))
                                iv.setVisibility(View.INVISIBLE);
                        } catch (Exception ignored) {
                        }
                    });
                    return;
                }
                final android.graphics.Bitmap b2 = bmp;
                THUMB_CACHE.put(u, b2);
                runOnUiThread(() -> {
                    try {
                        if (u.equals(iv.getTag())) {
                            iv.setImageBitmap(b2);
                            iv.setVisibility(View.VISIBLE);
                        }
                    } catch (Exception ignored) {
                    }
                });
            });
        } catch (Exception ignored) {
        }
    }

    private void loadThumbViaJs(final String u) {
        try {
            final String q = org.json.JSONObject.quote(u);
            final StringBuilder js = new StringBuilder("(function(){");
            js.append("try{");
            js.append("var U=").append(q).append(";");
            js.append("function done(d){try{window.MtDl.th(U,d||'')}catch(e){}}");
            js.append("function finish(b){");
            js.append("if(!b){done('');return}");
            js.append("try{");
            js.append("var fr=new FileReader();");
            js.append("fr.onload=function(){");
            js.append("try{");
            js.append("var s=String(fr.result||'');");
            js.append("var img=new Image();");
            js.append("img.onload=function(){");
            js.append("try{");
            js.append("var cv=document.createElement('canvas');");
            js.append("var mw=img.width||1,mh=img.height||1;");
            js.append("var sc=Math.min(1,240/Math.max(mw,mh));");
            js.append("cv.width=Math.max(1,Math.round(mw*sc));");
            js.append("cv.height=Math.max(1,Math.round(mh*sc));");
            js.append("cv.getContext('2d').drawImage(img,0,0,cv.width,cv.height);");
            js.append("done(cv.toDataURL('image/jpeg',0.72))");
            js.append("}catch(e){done(s)}");
            js.append("};");
            js.append("img.onerror=function(){done(s)};");
            js.append("img.src=s");
            js.append("}catch(e){done(s)}");
            js.append("};");
            js.append("fr.onerror=function(){done('')};");
            js.append("fr.readAsDataURL(b)");
            js.append("}catch(e){done('')}");
            js.append("}");
            js.append("var mb=null;");
            js.append("try{mb=window.__MT_BLOBS[String(U).split('#')[0]]}catch(e){}");
            js.append("if(mb&&mb!==1){finish(mb);return}");
            js.append("try{");
            js.append("fetch(U).then(function(r){return r.ok?r.blob():null})");
            js.append(".then(function(b){finish(b)})");
            js.append(".catch(function(){done('')})");
            js.append("}catch(e){done('')}");
            js.append("}catch(e){try{window.MtDl.th(U,'')}catch(e2){}}");
            js.append("})()");
            web.evaluateJavascript(js.toString(), null);
        } catch (Exception e) {
            onThumbData(u, "");
        }
    }

    private void onThumbData(final String u, final String dataUrl) {
        if (dataUrl.length() < 64) {
            THUMB_FAILED.add(u);
            return;
        }
        THUMB_POOL.execute(() -> {
            android.graphics.Bitmap bmp = null;
            try {
                String b64 = dataUrl.substring(dataUrl.indexOf(',') + 1);
                byte[] bytes = android.util.Base64.decode(
                        b64, android.util.Base64.DEFAULT);
                if (bytes.length > 0) {
                    android.graphics.BitmapFactory.Options o =
                            new android.graphics.BitmapFactory.Options();
                    o.inJustDecodeBounds = true;
                    android.graphics.BitmapFactory.decodeByteArray(
                            bytes, 0, bytes.length, o);
                    int sc = 1;
                    int maxDim = Math.max(o.outWidth, o.outHeight);
                    while (maxDim / sc > 260) sc *= 2;
                    android.graphics.BitmapFactory.Options o2 =
                            new android.graphics.BitmapFactory.Options();
                    o2.inSampleSize = sc;
                    bmp = android.graphics.BitmapFactory.decodeByteArray(
                            bytes, 0, bytes.length, o2);
                }
            } catch (Exception ignored) {
            }
            if (bmp == null) {
                THUMB_FAILED.add(u);
                return;
            }
            THUMB_CACHE.put(u, bmp);
            final android.graphics.Bitmap b2 = bmp;
            runOnUiThread(() -> {
                try {
                    java.util.List<android.widget.ImageView> lst =
                            THUMB_VIEWS.get(u);
                    if (lst != null) {
                        synchronized (lst) {
                            for (int i = 0; i < lst.size(); i++) {
                                try {
                                    android.widget.ImageView iv2 = lst.get(i);
                                    if (iv2 != null && u.equals(iv2.getTag())) {
                                        iv2.setImageBitmap(b2);
                                        iv2.setVisibility(View.VISIBLE);
                                    }
                                } catch (Exception ignored) {
                                }
                            }
                        }
                    }
                } catch (Exception ignored) {
                }
            });
        });
    }

    private android.widget.ImageView previewIv = null;
    private String previewTag = null;
    private TextView previewLd = null;
    private TextView previewErr = null;

    private void showFullPreview(final String u) {
        try {
            final android.app.Dialog dlg = new android.app.Dialog(this);
            dlg.requestWindowFeature(android.view.Window.FEATURE_NO_TITLE);
            android.widget.FrameLayout root = new android.widget.FrameLayout(this);
            root.setBackgroundColor(Color.parseColor("#F204060A"));
            final android.widget.ImageView iv = new android.widget.ImageView(this);
            iv.setScaleType(android.widget.ImageView.ScaleType.FIT_CENTER);
            root.addView(iv, new android.widget.FrameLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.MATCH_PARENT));
            final TextView ld = new TextView(this);
            ld.setText("… در حال بارگذاری");
            ld.setTextColor(Color.parseColor("#8a93a8"));
            ld.setTextSize(12.5f);
            ld.setGravity(Gravity.CENTER);
            root.addView(ld, new android.widget.FrameLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT,
                    Gravity.TOP | Gravity.CENTER_HORIZONTAL));
            final TextView errm = new TextView(this);
            errm.setText("تصویر بارگذاری نشد — سایت اجازه‌ی نمایش مستقیم نمی‌دهد");
            errm.setTextColor(Color.parseColor("#ffb4ad"));
            errm.setTextSize(12.5f);
            errm.setGravity(Gravity.CENTER);
            errm.setPadding(dp(24), 0, dp(24), 0);
            errm.setVisibility(View.GONE);
            root.addView(errm, new android.widget.FrameLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT,
                    Gravity.CENTER));
            TextView tip = new TextView(this);
            tip.setText("برای بستن لمس کن");
            tip.setTextColor(Color.parseColor("#8a93a8"));
            tip.setTextSize(11.5f);
            tip.setGravity(Gravity.CENTER);
            android.widget.FrameLayout.LayoutParams tipLp =
                    new android.widget.FrameLayout.LayoutParams(
                            ViewGroup.LayoutParams.MATCH_PARENT,
                            ViewGroup.LayoutParams.WRAP_CONTENT,
                            Gravity.BOTTOM | Gravity.CENTER_HORIZONTAL);
            tipLp.bottomMargin = dp(14);
            root.addView(tip, tipLp);
            root.setOnClickListener(v -> {
                previewIv = null;
                previewLd = null;
                previewErr = null;
                try { dlg.dismiss(); } catch (Exception ignored) {}
            });
            dlg.setContentView(root);
            if (dlg.getWindow() != null) {
                dlg.getWindow().setBackgroundDrawable(
                        new android.graphics.drawable.ColorDrawable(
                                Color.TRANSPARENT));
                dlg.getWindow().setLayout(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.MATCH_PARENT);
            }
            final String tag = "full:" + u;
            iv.setTag(tag);
            previewIv = iv;
            previewTag = tag;
            previewLd = ld;
            previewErr = errm;
            dlg.show();
            if (u.startsWith("blob:")) {
                loadPreviewViaJs(u);
            } else {
                loadFullInto(iv, u);
            }
        } catch (Exception ignored) {
        }
    }

    private void loadPreviewViaJs(final String u) {
        try {
            final String q = org.json.JSONObject.quote(u);
            final StringBuilder js = new StringBuilder("(function(){");
            js.append("try{");
            js.append("var U=").append(q).append(";");
            js.append("function done(d){try{window.MtDl.prev(d||'')}catch(e){}}");
            js.append("function finish(b){");
            js.append("if(!b){done('');return}");
            js.append("try{");
            js.append("var fr=new FileReader();");
            js.append("fr.onload=function(){");
            js.append("try{");
            js.append("var s=String(fr.result||'');");
            js.append("var big=s.length>=2500000||s.indexOf('data:image/avif')===0;");
            js.append("if(!big){done(s);return}");
            js.append("var img=new Image();");
            js.append("img.onload=function(){");
            js.append("try{");
            js.append("var cv=document.createElement('canvas');");
            js.append("var mw=img.width||1,mh=img.height||1;");
            js.append("var sc=Math.min(1,1800/Math.max(mw,mh));");
            js.append("cv.width=Math.max(1,Math.round(mw*sc));");
            js.append("cv.height=Math.max(1,Math.round(mh*sc));");
            js.append("cv.getContext('2d').drawImage(img,0,0,cv.width,cv.height);");
            js.append("done(cv.toDataURL('image/jpeg',0.88))");
            js.append("}catch(e){done(s)}");
            js.append("};");
            js.append("img.onerror=function(){done(s)};");
            js.append("img.src=s");
            js.append("}catch(e){done(s)}");
            js.append("};");
            js.append("fr.onerror=function(){done('')};");
            js.append("fr.readAsDataURL(b)");
            js.append("}catch(e){done('')}");
            js.append("}");
            js.append("var mb=null;");
            js.append("try{mb=window.__MT_BLOBS[String(U).split('#')[0]]}catch(e){}");
            js.append("if(mb&&mb!==1){finish(mb);return}");
            js.append("try{");
            js.append("fetch(U,{credentials:'include'})");
            js.append(".then(function(r){return r.ok?r.blob():null})");
            js.append(".then(function(b){finish(b)})");
            js.append(".catch(function(){done('')})");
            js.append("}catch(e){done('')}");
            js.append("}catch(e){try{window.MtDl.prev('')}catch(e2){}}");
            js.append("})()");
            web.evaluateJavascript(js.toString(), null);
        } catch (Exception e) {
            onPreviewData("");
        }
    }

    private void onPreviewData(final String dataUrl) {
        runOnUiThread(() -> {
            final android.widget.ImageView iv = previewIv;
            final String tag = previewTag;
            final TextView ld = previewLd;
            final TextView errm = previewErr;
            if (iv == null || tag == null || !tag.equals(iv.getTag())) return;
            if (dataUrl.length() < 64) {
                if (ld != null) ld.setVisibility(View.GONE);
                if (errm != null) errm.setVisibility(View.VISIBLE);
                return;
            }
            THUMB_POOL.execute(() -> {
                android.graphics.Bitmap bmp = null;
                try {
                    String b64 = dataUrl.substring(dataUrl.indexOf(',') + 1);
                    byte[] bytes = android.util.Base64.decode(
                            b64, android.util.Base64.DEFAULT);
                    if (bytes.length > 0) {
                        android.graphics.BitmapFactory.Options o =
                                new android.graphics.BitmapFactory.Options();
                        o.inJustDecodeBounds = true;
                        android.graphics.BitmapFactory.decodeByteArray(
                                bytes, 0, bytes.length, o);
                        int sc = 1;
                        int maxDim = Math.max(o.outWidth, o.outHeight);
                        while (maxDim / sc > 2200) sc *= 2;
                        android.graphics.BitmapFactory.Options o2 =
                                new android.graphics.BitmapFactory.Options();
                        o2.inSampleSize = sc;
                        bmp = android.graphics.BitmapFactory.decodeByteArray(
                                bytes, 0, bytes.length, o2);
                    }
                } catch (Exception ignored) {
                }
                final android.graphics.Bitmap b = bmp;
                runOnUiThread(() -> {
                    try {
                        if (ld != null) ld.setVisibility(View.GONE);
                        if (b != null) {
                            if (errm != null) errm.setVisibility(View.GONE);
                            iv.setImageBitmap(b);
                        } else {
                            if (errm != null) errm.setVisibility(View.VISIBLE);
                        }
                    } catch (Exception ignored) {
                    }
                });
            });
        });
    }

    private void loadFullInto(final android.widget.ImageView iv, final String u) {
        try {
            final String tag = "full:" + u;
            iv.setTag(tag);
            THUMB_POOL.execute(() -> {
                android.graphics.Bitmap bmp = null;
                try {
                    java.net.HttpURLConnection c =
                            (java.net.HttpURLConnection)
                                    new java.net.URL(u).openConnection();
                    c.setConnectTimeout(12000);
                    c.setReadTimeout(25000);
                    c.setRequestProperty("User-Agent",
                            "Mozilla/5.0 (Linux; Android 10; Pixel 7) "
                            + "AppleWebKit/537.36 (KHTML, like Gecko) "
                            + "Chrome/120.0.0.0 Mobile Safari/537.36");
                    try {
                        String ck = android.webkit.CookieManager
                                .getInstance().getCookie(u);
                        if (ck != null && !ck.isEmpty())
                            c.setRequestProperty("Cookie", ck);
                    } catch (Exception ignored) {}
                    try {
                        String ref = null;
                        try { ref = web.getUrl(); } catch (Exception ignored) {}
                        if (ref != null && ref.startsWith("http"))
                            c.setRequestProperty("Referer", ref);
                    } catch (Exception ignored) {}
                    int code = c.getResponseCode();
                    if (code >= 200 && code < 300) {
                        java.io.ByteArrayOutputStream bo =
                                new java.io.ByteArrayOutputStream();
                        java.io.InputStream in = c.getInputStream();
                        byte[] buf = new byte[16384];
                        int n;
                        while ((n = in.read(buf)) > 0) bo.write(buf, 0, n);
                        in.close();
                        byte[] data = bo.toByteArray();
                        c.disconnect();
                        if (data.length > 0 && data.length < 30 * 1024 * 1024) {
                            android.graphics.BitmapFactory.Options o =
                                    new android.graphics.BitmapFactory.Options();
                            o.inJustDecodeBounds = true;
                            android.graphics.BitmapFactory.decodeByteArray(
                                    data, 0, data.length, o);
                            int sc = 1;
                            int maxDim = Math.max(o.outWidth, o.outHeight);
                            while (maxDim / sc > 1600) sc *= 2;
                            android.graphics.BitmapFactory.Options o2 =
                                    new android.graphics.BitmapFactory.Options();
                            o2.inSampleSize = sc;
                            bmp = android.graphics.BitmapFactory.decodeByteArray(
                                    data, 0, data.length, o2);
                        }
                    } else {
                        c.disconnect();
                    }
                } catch (Exception ignored) {
                }
                final android.graphics.Bitmap b = bmp;
                runOnUiThread(() -> {
                    try {
                        if (!tag.equals(iv.getTag())) return;
                        if (b != null) {
                            if (previewIv == iv && previewLd != null)
                                previewLd.setVisibility(View.GONE);
                            iv.setImageBitmap(b);
                        } else {
                            if (previewIv == iv) loadPreviewViaJs(u);
                        }
                    } catch (Exception ignored) {
                    }
                });
            });
        } catch (Exception ignored) {
        }
    }

    private void showFolderDialog(final java.util.List<String> all) {
        try {
            showFolderDialogImpl(all);
        } catch (Exception e) {
            showFolderDialogFallback(all);
        }
    }

    private static String hostOfKey(String u) {
        if (u.startsWith("blob:")) return "blob:";
        try {
            java.net.URI p = new java.net.URI(u);
            String scheme = p.getScheme() == null ? "https" : p.getScheme();
            String host = p.getHost() == null ? "" : p.getHost();
            return scheme + "://" + host;
        } catch (Exception e) {
            String s = u;
            int h = s.indexOf('#');
            if (h >= 0) s = s.substring(0, h);
            int q = s.indexOf('?');
            if (q >= 0) s = s.substring(0, q);
            return s;
        }
    }

    private java.util.LinkedHashMap<String, java.util.List<String>> buildFolders(
            final java.util.List<String> all) {
        java.util.LinkedHashMap<String, java.util.List<String>> folders =
                new java.util.LinkedHashMap<>();
        for (String u : all) {
            String f = folderOf(u);
            if (!folders.containsKey(f))
                folders.put(f, new java.util.ArrayList<>());
            folders.get(f).add(u);
        }
        if (folders.size() > Math.max(8, all.size() * 6 / 10)) {
            java.util.LinkedHashMap<String, java.util.List<String>> byHost =
                    new java.util.LinkedHashMap<>();
            for (String u : all) {
                String h = hostOfKey(u);
                if (!byHost.containsKey(h))
                    byHost.put(h, new java.util.ArrayList<>());
                byHost.get(h).add(u);
            }
            folders = byHost;
        }
        return folders;
    }

    private void showFolderDialogFallback(final java.util.List<String> all) {
        java.util.LinkedHashMap<String, java.util.List<String>> folders =
                buildFolders(all);
        java.util.List<java.util.Map.Entry<String, java.util.List<String>>> entries =
                new java.util.ArrayList<>(folders.entrySet());
        entries.sort((a, b) -> Integer.compare(b.getValue().size(), a.getValue().size()));
        int nf = entries.size();
        CharSequence[] labels = new CharSequence[nf];
        boolean[] checked = new boolean[nf];
        for (int i = 0; i < nf; i++) {
            labels[i] = "\u200E" + shortFolder(entries.get(i).getKey())
                    + "  —  " + entries.get(i).getValue().size() + " عکس";
            checked[i] = entries.get(i).getValue().size() >= 2;
        }
        boolean anyChecked = false;
        for (boolean c : checked) if (c) { anyChecked = true; break; }
        if (!anyChecked && nf > 0) checked[0] = true;
        final boolean[] checkedF = checked;
        android.app.AlertDialog.Builder b = new android.app.AlertDialog.Builder(this);
        b.setTitle("پوشه‌های عکس (" + nf + ") — انتخاب کن");
        b.setMultiChoiceItems(labels, checkedF,
                (dialog, which, isChecked) -> checkedF[which] = isChecked);
        b.setPositiveButton("ادامه", (dialog, which) -> {
            java.util.ArrayList<String> sel = new java.util.ArrayList<>();
            java.util.HashSet<String> checkedKeys = new java.util.HashSet<>();
            for (int i = 0; i < nf; i++)
                if (checkedF[i]) checkedKeys.add(entries.get(i).getKey());
            for (String u : all)
                if (checkedKeys.contains(folderOf(u)) ||
                        checkedKeys.contains(hostOfKey(u))) sel.add(u);
            if (sel.isEmpty()) {
                Toast.makeText(this, "هیچ پوشه‌ای انتخاب نشد",
                        Toast.LENGTH_SHORT).show();
                return;
            }
            showLinkDownloadChoice(sel);
        });
        b.setNegativeButton("انصراف", null);
        b.show();
    }

    private void showFolderDialogImpl(final java.util.List<String> all) {
        java.util.LinkedHashMap<String, java.util.List<String>> folders =
                buildFolders(all);
        java.util.HashMap<String, Integer> rankOf = new java.util.HashMap<>();
        for (int i = 0; i < all.size(); i++) rankOf.put(all.get(i), i + 1);
        java.util.List<java.util.Map.Entry<String, java.util.List<String>>> entries =
                new java.util.ArrayList<>(folders.entrySet());
        entries.sort((a, b) -> Integer.compare(b.getValue().size(), a.getValue().size()));
        final java.util.List<String> order = new java.util.ArrayList<>();
        for (java.util.Map.Entry<String, java.util.List<String>> e : entries)
            order.add(e.getKey());

        final java.util.HashMap<String, java.util.LinkedHashSet<String>> picks =
                new java.util.HashMap<>();
        final java.util.HashMap<String, java.util.List<View>> grids =
                new java.util.HashMap<>();
        final java.util.HashMap<String, TextView> cntViews = new java.util.HashMap<>();
        final java.util.HashMap<String, android.widget.CheckBox> cbViews =
                new java.util.HashMap<>();
        final java.util.HashMap<String, GradientDrawable> rowBgs =
                new java.util.HashMap<>();

        final android.app.Dialog dlg = new android.app.Dialog(this);
        dlg.requestWindowFeature(android.view.Window.FEATURE_NO_TITLE);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(16), dp(16), dp(16), dp(12));
        GradientDrawable rootBg = new GradientDrawable(
                GradientDrawable.Orientation.TOP_BOTTOM,
                new int[]{Color.parseColor("#171b24"), Color.parseColor("#10141c")});
        rootBg.setCornerRadius(dp(18));
        rootBg.setStroke(dp(1), Color.parseColor("#2a3242"));
        root.setBackground(rootBg);

        LinearLayout head = new LinearLayout(this);
        head.setOrientation(LinearLayout.HORIZONTAL);
        head.setGravity(Gravity.CENTER_VERTICAL);
        LinearLayout headTxt = new LinearLayout(this);
        headTxt.setOrientation(LinearLayout.VERTICAL);
        TextView t1 = new TextView(this);
        t1.setText("پوشه‌های عکس (" + order.size() + ")");
        t1.setTextColor(Color.parseColor("#e7ebf3"));
        t1.setTextSize(15);
        t1.setTypeface(Typeface.DEFAULT_BOLD);
        TextView t2 = new TextView(this);
        t2.setText("کلیک = انتخاب • نگه‌داشتن روی عکس = پیش‌نمایش کامل");
        t2.setTextColor(Color.parseColor("#8a93a8"));
        t2.setTextSize(11.5f);
        headTxt.addView(t1);
        headTxt.addView(t2);
        head.addView(headTxt, new LinearLayout.LayoutParams(
                0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        TextView allBtn = makeMiniBtn("همه");
        TextView noneBtn = makeMiniBtn("هیچ");
        head.addView(allBtn, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT));
        android.widget.LinearLayout.LayoutParams nbLp =
                new android.widget.LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.WRAP_CONTENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT);
        nbLp.leftMargin = dp(6);
        head.addView(noneBtn, nbLp);
        root.addView(head);

        android.widget.ScrollView scroll = new android.widget.ScrollView(this);
        scroll.setVerticalScrollBarEnabled(false);
        LinearLayout list = new LinearLayout(this);
        list.setOrientation(LinearLayout.VERTICAL);
        final int topPad = dp(10);
        list.setPadding(0, topPad, 0, 0);
        scroll.addView(list, new android.view.ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT));
        root.addView(scroll, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));

        int screenW = getResources().getDisplayMetrics().widthPixels;
        int cell = dp(76);
        int cols = Math.max(3, Math.min(8,
                (Math.min(screenW - dp(120), dp(560))) / (cell + dp(6))));

        boolean anyDefault = false;
        for (String fk : order) {
            if (folders.get(fk).size() >= 2) anyDefault = true;
        }
        for (int oi = 0; oi < order.size(); oi++) {
            String fk = order.get(oi);
            picks.put(fk, new java.util.LinkedHashSet<>());
            if (folders.get(fk).size() >= 2
                    || (!anyDefault && oi == 0)) {
                picks.get(fk).addAll(folders.get(fk));
            }
        }

        final Runnable refresh = () -> {
            for (String fk : order) {
                java.util.LinkedHashSet<String> p = picks.get(fk);
                java.util.List<String> arr = folders.get(fk);
                android.widget.CheckBox cb = cbViews.get(fk);
                TextView cnt = cntViews.get(fk);
                GradientDrawable rbg = rowBgs.get(fk);
                if (p == null || arr == null) continue;
                boolean on = !p.isEmpty();
                if (cb != null) cb.setChecked(on);
                if (cnt != null)
                    cnt.setText(p.size() == arr.size()
                            ? arr.size() + " عکس"
                            : p.size() + "/" + arr.size());
                if (rbg != null) rbg.setStroke(dp(2), Color.parseColor(
                        on ? "#e8590c" : "#232b3b"));
                java.util.List<View> cells = grids.get(fk);
                if (cells != null) {
                    for (int i = 0; i < arr.size() && i < cells.size(); i++) {
                        View c = cells.get(i);
                        boolean sel = p.contains(arr.get(i));
                        c.setAlpha(sel ? 1f : 0.35f);
                    }
                }
            }
        };

        for (final String fk : order) {
            final java.util.List<String> arr = folders.get(fk);

            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.VERTICAL);
            row.setPadding(dp(12), dp(10), dp(12), dp(10));
            GradientDrawable rowBg = new GradientDrawable();
            rowBg.setColor(Color.parseColor("#1a1f2b"));
            rowBg.setCornerRadius(dp(14));
            rowBg.setStroke(dp(2), Color.parseColor("#232b3b"));
            row.setBackground(rowBg);
            rowBgs.put(fk, rowBg);
            LinearLayout.LayoutParams rowLp = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT);
            rowLp.bottomMargin = dp(8);
            row.setLayoutParams(rowLp);

            LinearLayout topRow = new LinearLayout(this);
            topRow.setOrientation(LinearLayout.HORIZONTAL);
            topRow.setGravity(Gravity.CENTER_VERTICAL);
            final android.widget.CheckBox cb = new android.widget.CheckBox(this);
            try {
                cb.setButtonTintList(android.content.res.ColorStateList.valueOf(
                        Color.parseColor("#e8590c")));
            } catch (Exception ignored) {
            }
            cbViews.put(fk, cb);
            TextView name = new TextView(this);
            name.setText("\u200E" + shortFolder(fk));
            name.setTextColor(Color.parseColor("#e7ebf3"));
            name.setTextSize(12.5f);
            name.setGravity(Gravity.LEFT);
            LinearLayout.LayoutParams nameLp = new LinearLayout.LayoutParams(
                    0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
            nameLp.leftMargin = dp(8);
            nameLp.rightMargin = dp(8);
            topRow.addView(cb);
            topRow.addView(name, nameLp);
            TextView cnt = new TextView(this);
            cnt.setTextColor(Color.WHITE);
            cnt.setTextSize(11.5f);
            cnt.setTypeface(Typeface.DEFAULT_BOLD);
            GradientDrawable cntBg = new GradientDrawable();
            cntBg.setColor(Color.parseColor("#2d3649"));
            cntBg.setCornerRadius(dp(10));
            cnt.setBackground(cntBg);
            cnt.setPadding(dp(10), dp(3), dp(10), dp(3));
            cntViews.put(fk, cnt);
            topRow.addView(cnt, new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.WRAP_CONTENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT));
            TextView exp = makeMiniBtn("پیش‌نمایش");
            android.widget.LinearLayout.LayoutParams expLp =
                    new android.widget.LinearLayout.LayoutParams(
                            ViewGroup.LayoutParams.WRAP_CONTENT,
                            ViewGroup.LayoutParams.WRAP_CONTENT);
            expLp.leftMargin = dp(8);
            topRow.addView(exp, expLp);
            row.addView(topRow);

            LinearLayout strip = new LinearLayout(this);
            strip.setOrientation(LinearLayout.HORIZONTAL);
            android.widget.LinearLayout.LayoutParams stripLp =
                    new android.widget.LinearLayout.LayoutParams(
                            ViewGroup.LayoutParams.MATCH_PARENT,
                            ViewGroup.LayoutParams.WRAP_CONTENT);
            stripLp.topMargin = dp(8);
            strip.setLayoutParams(stripLp);
            for (int s = 0; s < arr.size() && s < 4; s++) {
                android.widget.ImageView iv = new android.widget.ImageView(this);
                iv.setScaleType(android.widget.ImageView.ScaleType.CENTER_CROP);
                GradientDrawable ivBg = new GradientDrawable();
                ivBg.setColor(Color.parseColor("#232b3b"));
                ivBg.setCornerRadius(dp(10));
                ivBg.setStroke(dp(1), Color.parseColor("#2a3242"));
                iv.setBackground(ivBg);
                iv.setClipToOutline(true);
                LinearLayout.LayoutParams ivLp = new LinearLayout.LayoutParams(
                        dp(58), dp(58));
                if (s > 0) ivLp.leftMargin = dp(6);
                strip.addView(iv, ivLp);
                loadThumb(iv, arr.get(s));
                final String su = arr.get(s);
                iv.setOnLongClickListener(v -> {
                    showFullPreview(su);
                    return true;
                });
            }
            row.addView(strip);

            final android.widget.GridLayout grid = new android.widget.GridLayout(this);
            grid.setColumnCount(cols);
            grid.setAlpha(1f);
            grid.setVisibility(View.GONE);
            android.widget.LinearLayout.LayoutParams gridLp =
                    new android.widget.LinearLayout.LayoutParams(
                            ViewGroup.LayoutParams.MATCH_PARENT,
                            ViewGroup.LayoutParams.WRAP_CONTENT);
            gridLp.topMargin = dp(8);
            grid.setLayoutParams(gridLp);
            java.util.List<View> cells = new java.util.ArrayList<>();
            for (int g = 0; g < arr.size(); g++) {
                final String u = arr.get(g);
                final android.widget.FrameLayout cellBox =
                        new android.widget.FrameLayout(this);
                android.widget.GridLayout.LayoutParams clp =
                        new android.widget.GridLayout.LayoutParams();
                clp.width = cell;
                clp.height = cell * 3 / 2;
                android.widget.GridLayout.Spec colSpec =
                        android.widget.GridLayout.spec(g % cols);
                android.widget.GridLayout.Spec rowSpec =
                        android.widget.GridLayout.spec(g / cols);
                clp.columnSpec = colSpec;
                clp.rowSpec = rowSpec;
                int mm = dp(3);
                clp.setMargins(mm, mm, mm, mm);
                cellBox.setLayoutParams(clp);

                android.widget.ImageView iv = new android.widget.ImageView(this);
                iv.setScaleType(android.widget.ImageView.ScaleType.CENTER_CROP);
                GradientDrawable ivBg = new GradientDrawable();
                ivBg.setColor(Color.parseColor("#232b3b"));
                ivBg.setCornerRadius(dp(10));
                iv.setBackground(ivBg);
                iv.setClipToOutline(true);
                cellBox.addView(iv, new android.widget.FrameLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.MATCH_PARENT));
                loadThumb(iv, u);

                TextView no = new TextView(this);
                Integer rk = rankOf.get(u);
                no.setText(String.valueOf(rk != null ? rk : (g + 1)));
                no.setTextColor(Color.WHITE);
                no.setTextSize(10);
                no.setBackgroundColor(Color.parseColor("#a6000000"));
                no.setPadding(dp(5), dp(1), dp(5), dp(1));
                android.widget.FrameLayout.LayoutParams noLp =
                        new android.widget.FrameLayout.LayoutParams(
                                ViewGroup.LayoutParams.WRAP_CONTENT,
                                ViewGroup.LayoutParams.WRAP_CONTENT,
                                Gravity.BOTTOM | Gravity.START);
                noLp.leftMargin = dp(3);
                noLp.bottomMargin = dp(3);
                cellBox.addView(no, noLp);

                cellBox.setOnClickListener(v -> {
                    try {
                        java.util.LinkedHashSet<String> pp = picks.get(fk);
                        if (pp == null) return;
                        if (pp.contains(u)) pp.remove(u);
                        else pp.add(u);
                        refresh.run();
                    } catch (Exception ignored) {
                    }
                });
                cellBox.setOnLongClickListener(v -> {
                    showFullPreview(u);
                    return true;
                });
                grid.addView(cellBox);
                cells.add(cellBox);
            }
            grids.put(fk, cells);
            row.addView(grid);

            exp.setOnClickListener(v -> {
                try {
                    boolean open = grid.getVisibility() != View.VISIBLE;
                    grid.setVisibility(open ? View.VISIBLE : View.GONE);
                    strip.setVisibility(open ? View.GONE : View.VISIBLE);
                    exp.setText(open ? "بستن" : "پیش‌نمایش");
                } catch (Exception ignored) {
                }
            });
            View.OnClickListener rowClick = v -> {
                try {
                    java.util.LinkedHashSet<String> pp = picks.get(fk);
                    if (pp == null) return;
                    boolean turnOn = pp.isEmpty();
                    pp.clear();
                    if (turnOn) pp.addAll(arr);
                    refresh.run();
                } catch (Exception ignored) {
                }
            };
            row.setOnClickListener(rowClick);
            cb.setOnClickListener(v -> {
                try {
                    java.util.LinkedHashSet<String> pp = picks.get(fk);
                    if (pp == null) return;
                    pp.clear();
                    if (cb.isChecked()) pp.addAll(arr);
                    refresh.run();
                } catch (Exception ignored) {
                }
            });
            list.addView(row);
        }

        refresh.run();

        LinearLayout btns = new LinearLayout(this);
        btns.setOrientation(LinearLayout.HORIZONTAL);
        btns.setGravity(Gravity.CENTER_VERTICAL);
        android.widget.LinearLayout.LayoutParams btnsLp =
                new android.widget.LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT);
        btnsLp.topMargin = dp(4);
        btns.setLayoutParams(btnsLp);
        TextView okBtn = new TextView(this);
        okBtn.setText("ادامه");
        okBtn.setTextColor(Color.WHITE);
        okBtn.setTextSize(13.5f);
        okBtn.setTypeface(Typeface.DEFAULT_BOLD);
        okBtn.setGravity(Gravity.CENTER);
        okBtn.setPadding(dp(24), dp(11), dp(24), dp(11));
        GradientDrawable okBg = new GradientDrawable(
                GradientDrawable.Orientation.TL_BR,
                new int[]{Color.parseColor("#ff4a3d"), Color.parseColor("#c9271c")});
        okBg.setCornerRadius(dp(12));
        okBtn.setBackground(okBg);
        TextView noBtn = new TextView(this);
        noBtn.setText("انصراف");
        noBtn.setTextColor(Color.parseColor("#c8ceda"));
        noBtn.setTextSize(13.5f);
        noBtn.setTypeface(Typeface.DEFAULT_BOLD);
        noBtn.setGravity(Gravity.CENTER);
        noBtn.setPadding(dp(24), dp(11), dp(24), dp(11));
        GradientDrawable noBg = new GradientDrawable();
        noBg.setColor(Color.parseColor("#2d3649"));
        noBg.setCornerRadius(dp(12));
        noBtn.setBackground(noBg);
        btns.addView(noBtn, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT));
        LinearLayout.LayoutParams okLp = new LinearLayout.LayoutParams(
                0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        okLp.leftMargin = dp(8);
        btns.addView(okBtn, okLp);
        root.addView(btns);

        allBtn.setOnClickListener(v -> {
            for (String fk : order) {
                picks.get(fk).clear();
                picks.get(fk).addAll(folders.get(fk));
            }
            refresh.run();
        });
        noneBtn.setOnClickListener(v -> {
            for (String fk : order) picks.get(fk).clear();
            refresh.run();
        });
        okBtn.setOnClickListener(v -> {
            java.util.ArrayList<String> sel = new java.util.ArrayList<>();
            for (String u : all) {
                String fk = folderOf(u);
                java.util.HashSet<String> p = picks.get(fk);
                if (p != null && p.contains(u)) sel.add(u);
            }
            if (sel.isEmpty()) {
                Toast.makeText(this, "هیچ عکسی انتخاب نشد",
                        Toast.LENGTH_SHORT).show();
                return;
            }
            try {
                dlg.dismiss();
            } catch (Exception ignored) {
            }
            showLinkDownloadChoice(sel);
        });
        noBtn.setOnClickListener(v -> {
            try {
                dlg.dismiss();
            } catch (Exception ignored) {
            }
        });

        dlg.setContentView(root);
        dlg.show();
        android.view.Window w = dlg.getWindow();
        if (w != null) {
            w.setBackgroundDrawable(new android.graphics.drawable.ColorDrawable(
                    Color.TRANSPARENT));
            int dw = Math.min(screenW - dp(24), dp(600));
            w.setLayout(dw, (int) (getResources().getDisplayMetrics().heightPixels
                    * 0.82));
        }
    }

    private TextView makeMiniBtn(String txt) {
        TextView b = new TextView(this);
        b.setText(txt);
        b.setTextColor(Color.parseColor("#c8ceda"));
        b.setTextSize(11.5f);
        b.setTypeface(Typeface.DEFAULT_BOLD);
        b.setPadding(dp(10), dp(5), dp(10), dp(5));
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(Color.parseColor("#2d3649"));
        bg.setCornerRadius(dp(10));
        b.setBackground(bg);
        return b;
    }

    private void finishWithLinks(final java.util.List<String> sel) {
        try {
            for (String u : sel) {
                if (u.startsWith("blob:")) {
                    countLbl.setText(sel.size() + " عکس — در حال دانلود…");
                    Toast.makeText(BrowserActivity.this,
                            "این سایت عکس‌ها را داخل مرورگر رمزگشایی می‌کند "
                                    + "(" + sel.size() + " صفحه) — "
                                    + "به‌جای لینک، خودکار دانلود می‌کنم",
                            Toast.LENGTH_LONG).show();
                    downloadSelected(sel);
                    return;
                }
            }
            java.util.List<String> out = sel;
            if (out.size() > 400) {
                out = new java.util.ArrayList<>(out.subList(0, 400));
                Toast.makeText(BrowserActivity.this,
                        "برای پایداری فقط ۴۰۰ لینکِ اول منتقل شد",
                        Toast.LENGTH_SHORT).show();
            }
            StringBuilder links = new StringBuilder();
            for (int i = 0; i < out.size(); i++) {
                if (i > 0) links.append('\n');
                links.append(out.get(i));
            }
            Intent res = new Intent();
            res.putExtra(EXTRA_LINKS, links.toString());
            setResult(RESULT_OK, res);
            Toast.makeText(BrowserActivity.this,
                    "✅ " + sel.size() + " لینک عکس گرفته شد",
                    Toast.LENGTH_SHORT).show();
            finish();
        } catch (final Exception e) {
            Toast.makeText(BrowserActivity.this,
                    "خطا در استخراج: " + e.getMessage(),
                    Toast.LENGTH_LONG).show();
        }
    }

    private void downloadSelected(final java.util.List<String> sel) {
        extractBtn.setText("… در حال دانلود");
        countLbl.setText("⬇ 0/" + sel.size());
        startDownloadAll(sel);
    }

    @SuppressWarnings("deprecation")
    @Override
    public void onBackPressed() {
        try {
            if (web.canGoBack()) web.goBack(); else finish();
        } catch (Exception e) {
            finish();
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        recountHandler.removeCallbacks(recountTick);
        recountHandler.postDelayed(recountTick, 1200);
    }

    @Override
    protected void onPause() {
        recountHandler.removeCallbacks(recountTick);
        super.onPause();
    }

    @Override
    protected void onDestroy() {
        try { web.destroy(); } catch (Exception ignored) {}
        super.onDestroy();
    }

    private int dp(int v) {
        return (int) (v * getResources().getDisplayMetrics().density + 0.5f);
    }
}
