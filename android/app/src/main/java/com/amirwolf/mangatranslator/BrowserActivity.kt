package com.amirwolf.mangatranslator

import android.annotation.SuppressLint
import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.view.inputmethod.EditorInfo
import android.webkit.CookieManager
import android.webkit.JsResult
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import org.json.JSONArray
import org.json.JSONObject

class BrowserActivity : Activity() {

    companion object {
        const val EXTRA_URL = "url"
        const val EXTRA_LINKS = "links"

        var lastSite: String = ""

        private const val EXTRACT_JS = """
(function(){
var W=window;
if(!W.__MT_FOUND){W.__MT_FOUND={};W.__MT_ORDER=[];}
if(!W.__MT_BLOBS){W.__MT_BLOBS={};}
if(typeof W.__MT_T0!=='number'){W.__MT_T0=0;}
function abs(u){try{var a=document.createElement('a');a.href=u;return a.href}catch(e){return null}}
function qsz(u){
try{
var m=String(u).match(/[?&](?:type|size|w|h|width|height)=(f?)(\d{1,4})(?:[_x](\d{1,4}))?/i);
if(!m)return 0;
var a=parseInt(m[2],10)||0;
var b=parseInt(m[3]||'0',10)||0;
if(a>0&&b>0)return Math.max(a,b);
if(m[1]&&a>0)return a;
return 0
}catch(e){return 0}}
function junk(u){
if(!u)return 1;
u=String(u);
if(u.indexOf('data:')===0)return 1;
if(u.indexOf('blob:')===0)return 1;
if(!/^https?:/i.test(u))return 1;
var b=u.split(/[?#]/)[0];
if(/\.(svg|ico|gif|css|js|mjs|json|html?|xml|txt|pdf|zip|rar|7z|gz|mp4|webm|mp3|m4a|ogg|wav|woff2?|ttf|otf|eot|map)${'$'}/i.test(b))return 1;
if(/[-_]\d{2,4}x\d{2,4}\.(jpe?g|png|webp|avif)${'$'}/i.test(b))return 1;
if(/\/\d{2,4}x\d{2,4}\//i.test(b))return 1;
if(/(login|signin|signup|register|servicelogin|oauth)/i.test(b))return 1;
var q=qsz(u);
if(q>0&&q<=400)return 1;
if(/(logo|icon|avatar|banner|sprite|favicon|badge|flag|button|emoji|thumb(nail)?s?|placeholder|blank|spacer|transparen|loading|spinner|pixel|profile|rating|share|follow|comment|credits)/i.test(b))return 1;
if(/(?:^|[^a-z0-9])ads?[._\/-]/i.test(b))return 1;
if(/\/(covers?|thumbs?|thumbnails?|avatars?|banners?|creatives?|gifs?|decorations?|emojis?|smileys?|stickers?)\//i.test(b))return 1;
if(/(default|anon|guest|blank)[-_]?(pp|avatar|user|profile|image)/i.test(b))return 1;
if(/(pubadx|adservice|adserver|doubleclick|adnxs|propellerads?|onclck|adcash|adsterra|hilltopads?|clickadu|sovrn|taboola|outbrain|zedo|buysellads?|sharethrough|smartadserver|openx|rubicon|criteo|pubmatic|media\.net|jumpg-assets)/i.test(b))return 1;
return 0}
function keyOf(u){
var s=String(u);
var b=s.split(/[?#]/)[0];
if(!/\.(jpe?g|png|webp|avif|bmp|tiff?)$/i.test(b))return s.split('#')[0];
return b.replace(/[-_]\d{2,4}x\d{2,4}\./i,'.')}
function bkey(u){return String(u).split('#')[0]}
function hold(k,b){
try{
if(!b||W.__MT_BLOBS[k])return;
var n=0;for(var p in W.__MT_BLOBS)n++;
if(n<120)W.__MT_BLOBS[k]=b
}catch(e){}}
function capb(u){
try{
if(!u)return;
u=String(u).trim();
if(u.indexOf('blob:')!==0)return;
var k=bkey(u);
if(Object.prototype.hasOwnProperty.call(W.__MT_FOUND,k))return;
W.__MT_FOUND[k]=u;
W.__MT_ORDER.push(u);
try{fetch(u).then(function(r){return r.ok?r.blob():null}).then(function(b){if(b)hold(k,b)}).catch(function(){})}catch(e2){}
}catch(e){}}
function cap(u){
try{
if(!u)return;
u=String(u).trim();
if(u.indexOf('data:')===0)return;
if(u.indexOf('blob:')===0){capb(u);return}
if(!/^https?:/i.test(u))return;
u=abs(u);
if(!u||junk(u))return;
try{if(u===location.href)return}catch(e){}
var k=keyOf(u);
if(Object.prototype.hasOwnProperty.call(W.__MT_FOUND,k))return;
W.__MT_FOUND[k]=u;
W.__MT_ORDER.push(u)
}catch(e){}}
function bestSrcset(ss){
try{
var parts=String(ss).split(','),best='',bw=-1;
for(var k=0;k<parts.length;k++){
var tk=parts[k].trim().split(/\s+/);
var u0=tk[0]||'';
var w0=parseInt(String(tk[1]||'').replace(/[^0-9]/g,''),10)||0;
if(u0&&w0>=bw){bw=w0;best=u0}}
return best
}catch(e){return ''}}
var DATA_ATTS=['data-src','data-lazy-src','data-original','data-original-src','data-orig-src','data-lazy','data-url','data-image','data-echo','data-asurl','data-cfsrc','data-hi-res-src','data-full-src','data-full_image','data-large-src','data-file','data-path','data-actualsrc'];
function nowT(){try{return performance.now()}catch(e){return 0}}
function grabEl(el){
try{
if(!el||el.nodeType!==1)return;
var tg=el.tagName;
if(tg!=='IMG'&&tg!=='SOURCE')return;
el.__MT_SEEN=nowT();
var u='';
try{u=el.currentSrc||el.getAttribute('src')||''}catch(e){}
u=String(u||'');
if(u.indexOf('blob:')===0){capb(u)}
else if(tg==='SOURCE'&&u&&u.indexOf('data:')!==0){cap(u)}
else if(u&&u.indexOf('data:')!==0){
var done=function(){try{var c=el.currentSrc||el.src||'';if(c&&c.indexOf('http')===0)cap(c)}catch(e){}};
try{
if(el.complete&&el.naturalWidth>0){
if(Math.max(el.naturalWidth||0,el.naturalHeight||0)>=300)done();
}else{
el.addEventListener('load',function(){
try{if(Math.max(el.naturalWidth||0,el.naturalHeight||0)>=300)done()}catch(e){}
},{once:true});
}
}catch(e){}
}
try{
var ss=el.getAttribute('srcset')||el.getAttribute('data-srcset');
if(ss){var bs=bestSrcset(ss);if(bs)cap(bs)}
}catch(e){}
for(var j=0;j<DATA_ATTS.length;j++){
try{var v=el.getAttribute(DATA_ATTS[j]);if(v&&v.length>4)cap(v)}catch(e){}
}
}catch(e){}}
function grabTree(n){
try{
if(!n||n.nodeType!==1)return;
if(n.tagName==='IMG'||n.tagName==='SOURCE'){grabEl(n);return}
if(n.querySelectorAll){
var q=n.querySelectorAll('img,source');
for(var i=0;i<q.length;i++)grabEl(q[i])
}
}catch(e){}}
if(!W.__MT_WATCH){
W.__MT_WATCH=1;
try{
if(!W.__mtCO){W.__mtCO=1;
var _co=URL.createObjectURL;
URL.createObjectURL=function(){
var u='';
try{u=_co.apply(this,arguments)}catch(e){return _co.apply(this,arguments)}
try{
var b=arguments[0];
if(b&&(typeof Blob!=='undefined')&&b instanceof Blob&&String(b.type||'').indexOf('image/')===0&&(b.size||0)>12000){hold(String(u).split('#')[0],b)}
}catch(e2){}
return u
};
}
}catch(e){}
try{
var ex=document.querySelectorAll('img,source');
for(var i2=0;i2<ex.length;i2++){try{ex[i2].__MT_SEEN=nowT()}catch(e){}}
}catch(e){}
try{
var obs=new MutationObserver(function(ms){
for(var i3=0;i3<ms.length;i3++){
var m=ms[i3];
try{
if(m.type==='attributes'){grabEl(m.target);continue}
var ns=m.addedNodes;
for(var j2=0;j2<ns.length;j2++)grabTree(ns[j2])
}catch(e){}}
});
obs.observe(document.documentElement||document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['src','srcset']})
}catch(e){}
try{
if(!W.__mtPO){W.__mtPO=1;
var po=new PerformanceObserver(function(list){
try{
var es=list.getEntries();
for(var i=0;i<es.length;i++){
var en=es[i]||{};var n=String(en.name||'');
if(!n)continue;
var b=n.split(/[?#]/)[0];
var t=String(en.initiatorType||'');
if(/\.(jpe?g|png|webp|avif|bmp|tiff?)$/i.test(b)||t==='img'||
/\.(jpe?g|png|webp|avif|bmp|tiff?)([?#]|${'$'})/i.test(n)){cap(n)}
}
}catch(e){}});
po.observe({entryTypes:['resource'],buffered:true})
}}catch(e){}
try{
var _f=W.fetch;
if(typeof _f==='function'&&!W.__mtFH){W.__mtFH=1;
W.fetch=function(){var p;try{p=_f.apply(this,arguments)}catch(e){throw e}
try{var a0=arguments[0];var u0='';
if(a0){if(typeof a0==='string')u0=a0;else if(a0.url)u0=String(a0.url)}
p.then(function(r){try{var ct=(r.headers&&r.headers.get('content-type'))||'';
if(/^image\//i.test(String(ct).trim()))cap(u0)}catch(e){}}).catch(function(){})
}catch(e){}return p}}
var _o=XMLHttpRequest.prototype.open,_s=XMLHttpRequest.prototype.send;
XMLHttpRequest.prototype.open=function(m,u){try{this.__mtU=String(u||'')}catch(e){}return _o.apply(this,arguments)};
XMLHttpRequest.prototype.send=function(){try{var x=this;
x.addEventListener('loadend',function(){try{var ct='';
try{ct=x.getResponseHeader('content-type')||''}catch(e){}
var ru='';try{ru=x.responseURL||x.__mtU||''}catch(e){}
if(/^image\//i.test(String(ct).trim()))cap(ru)}catch(e){}})}catch(e){}
return _s.apply(this,arguments)}
}catch(e){}
}
function scanDoc(doc){
try{
var els=doc.querySelectorAll('img');
for(var i=0;i<els.length;i++){
var el=els[i];
try{
var t0=W.__MT_T0||0;
if(el.__MT_SEEN&&el.__MT_SEEN<t0)continue;
el.__MT_SEEN=nowT();
}catch(e){}
var nw=0,nh=0,loaded=false;
try{loaded=!!el.complete&&el.naturalWidth>0;nw=el.naturalWidth||0;nh=el.naturalHeight||0}catch(e){}
var u='';
try{u=el.currentSrc||el.src||''}catch(e){}
if(u&&u.indexOf('data:')===0)u='';
if(u&&u.indexOf('blob:')===0){
if(loaded&&nw&&nh&&Math.max(nw,nh)>=300)capb(u);
u='';
}
if(u&&loaded&&nw&&nh&&Math.max(nw,nh)<300)u='';
if(u)cap(u);
try{
var ss=el.getAttribute('srcset')||el.getAttribute('data-srcset');
if(ss){var bs=bestSrcset(ss);if(bs)cap(bs)}
}catch(e){}
for(var j=0;j<DATA_ATTS.length;j++){
try{
var v=el.getAttribute(DATA_ATTS[j]);
if(v&&v.length>4)cap(v)
}catch(e){}}
}
}catch(e){}
try{
var sos=doc.querySelectorAll('source');
for(var i4=0;i4<sos.length;i4++){
var so=sos[i4];
try{
var t02=W.__MT_T0||0;
if(so.__MT_SEEN&&so.__MT_SEEN<t02)continue;
so.__MT_SEEN=nowT();
var s2=so.getAttribute('srcset')||so.getAttribute('data-srcset')||so.getAttribute('src');
if(s2){var b2=bestSrcset(s2);if(!b2)b2=s2;if(b2)cap(b2)}
}catch(e){}}
}catch(e){}
try{
var as=doc.querySelectorAll('a[href]');
for(var i5=0;i5<as.length;i5++){
var h=as[i5].getAttribute('href')||'';
if(/^https?:/i.test(h)&&/\.(jpe?g|png|webp|avif|bmp)([?#]|${'$'})/i.test(h))cap(h)}
}catch(e){}
try{
var st=doc.querySelectorAll('[style*="url("]');
for(var i6=0;i6<st.length;i6++){
var mm=String(st[i6].getAttribute('style')||'').match(/url\((['"]?)([^'")]+)\1\)/i);
if(mm&&mm[2])cap(mm[2])}
}catch(e){}}
function scanAll(){
try{scanDoc(document)}catch(e){}
try{
var fs=document.querySelectorAll('iframe');
for(var i=0;i<fs.length;i++){
try{var d=fs[i].contentDocument;if(d)scanDoc(d)}catch(e){}}
}catch(e){}
try{
var of=window.frames;
for(var j=0;j<of.length;j++){
try{var d2=of[j].document;if(d2)scanDoc(d2)}catch(e){}}
}catch(e){}}
function perfPass(){
try{
var rs=performance.getEntriesByType('resource');
var tp=W.__MT_T0||0;
for(var i=0;i<rs.length;i++){
var en=rs[i]||{};
var n=String(en.name||'');
if(!n)continue;
try{if(en.startTime<tp)continue}catch(e){}
var b=n.split(/[?#]/)[0];
var t=String(en.initiatorType||'');
if(/\.(jpe?g|png|webp|avif|bmp|tiff?)${'$'}/i.test(b)){cap(n);continue}
if(/\.(jpe?g|png|webp|avif|bmp|tiff?)([?#]|${'$'})/i.test(n)){cap(n);continue}
if(t==='img'){if(n.indexOf('blob:')===0){capb(n)}else{cap(n)}}
}
}catch(e){}}
function scriptPass(){
try{
if(W.__MT_ORDER.length)return;
var sc=document.querySelectorAll('script');
var re=/https?:\\?\/\\?\/[^"'\s\\<>()[\]]+?\.(?:jpe?g|png|webp|avif|bmp)(?:\?[^"'\\\s<>()[\]]*)?/gi;
var m,guard=0;
for(var i=0;i<sc.length&&guard<800;i++){
var txt='';
try{txt=sc[i].textContent||''}catch(e){continue}
if(!txt||txt.length<10)continue;
re.lastIndex=0;
while((m=re.exec(txt))&&guard<800){
guard++;
try{cap(m[0].replace(/\\\//g,'/'))}catch(e){}}}
}catch(e){}}
scanAll();
perfPass();
scriptPass();
try{return W.__MT_ORDER.slice(0,400)}catch(e){return []}
})()
        """

        private const val SCROLL_JS = """
(function(){
try{
if(window.__MT_SCROLLING)return;
window.__MT_SCROLLING=1;
window.__MT_SCROLL_DONE=0;
var step=Math.max(500,Math.floor(window.innerHeight*0.85));
var y=0,n=0,stable=0,lastH=0;
function H(){try{return Math.max(document.body?document.body.scrollHeight:0,document.documentElement?document.documentElement.scrollHeight:0)}catch(e){return 0}}
lastH=H();
function tick(){
try{
y+=step;
window.scrollTo(0,y);
n++;
var h=H();
if(h===lastH)stable++;else{stable=0;lastH=h}
var atBottom=(y+window.innerHeight>=h-8);
if((atBottom&&stable>=3)||n>200){
try{window.scrollTo(0,0)}catch(e){}
window.__MT_SCROLL_DONE=1;
return
}
setTimeout(tick,280)
}catch(e){window.__MT_SCROLL_DONE=1}
}
tick()
}catch(e){try{window.__MT_SCROLL_DONE=1}catch(e2){}}
})()
        """

        private const val CLEAR_STORE_JS = """
(function(){try{window.__MT_FOUND={};window.__MT_ORDER=[];window.__MT_BLOBS={};try{window.__MT_T0=(window.performance&&performance.now)?performance.now():0}catch(e){window.__MT_T0=0}}catch(e){}})()
        """

        private val THUMB_CACHE =
            object : android.util.LruCache<String, android.graphics.Bitmap>(
                24 * 1024 * 1024) {
                override fun sizeOf(k: String, v: android.graphics.Bitmap): Int {
                    return try { v.byteCount } catch (_: Exception) { 1 }
                }
            }
        private val THUMB_FAILED =
            java.util.Collections.synchronizedSet(HashSet<String>())
        private val THUMB_POOL: java.util.concurrent.ExecutorService =
            java.util.concurrent.Executors.newFixedThreadPool(3)
        private val THUMB_VIEWS =
            java.util.concurrent.ConcurrentHashMap<String, MutableList<android.widget.ImageView>>()
    }

    private val BG = Color.parseColor("#060607")
    private val CARD = Color.parseColor("#0d0d10")
    private val LINE = Color.parseColor("#1f1f24")
    private val TXT = Color.parseColor("#e8e6e1")
    private val MUT = Color.parseColor("#97948c")
    private val ACC = Color.parseColor("#ff4a3d")

    private lateinit var web: WebView
    private lateinit var urlBox: EditText
    private lateinit var extractBtn: TextView
    private lateinit var countLbl: TextView
    private lateinit var progress: ProgressBar

    private val foundStore = java.util.LinkedHashSet<String>()
    private val netLog = java.util.LinkedHashSet<String>()
    private var chapterKeyNow = ""
    private var recording = false
    private var dlDir: java.io.File? = null
    private var dlDone = 0
    private var dlOk = 0
    private val dlParts = HashMap<Int, StringBuilder>()

    private val reImgExt = Regex(
        "\\.(jpe?g|png|webp|avif|bmp|tiff?)$", RegexOption.IGNORE_CASE)
    private val reImgExtFull = Regex(
        "\\.(jpe?g|png|webp|avif|bmp|tiff?)([&#]|$)", RegexOption.IGNORE_CASE)
    private val reBadExt = Regex(
        "\\.(svg|ico|gif|css|js|mjs|json|html?|xml|txt|pdf|zip|rar|7z|gz|" +
        "mp4|webm|mp3|m4a|ogg|wav|woff2?|ttf|otf|eot|map)$",
        RegexOption.IGNORE_CASE)
    private val reDimTag = Regex(
        "[-_]\\d{2,4}x\\d{2,4}\\.\\w{2,5}$", RegexOption.IGNORE_CASE)
    private val reJunkWords = Regex(
        "(logo|icon|avatar|banner|sprite|favicon|badge|flag|button|emoji|" +
        "thumb(nail)?s?|placeholder|blank|spacer|transparen|loading|spinner|" +
        "pixel|profile|rating|share|follow|comment|credits)",
        RegexOption.IGNORE_CASE)
    private val reAdWord = Regex(
        "(?:^|[^a-z0-9])ads?[._/-]", RegexOption.IGNORE_CASE)
    private val reJunkDir = Regex(
        "/(covers?|thumbs?|thumbnails?|avatars?|banners?|creatives?|gifs?|" +
        "decorations?|emojis?|smileys?|stickers?)/", RegexOption.IGNORE_CASE)
    private val reAdHost = Regex(
        "(pubadx|adservice|adserver|doubleclick|adnxs|propellerads?|onclck|" +
        "adcash|adsterra|hilltopads?|clickadu|sovrn|taboola|outbrain|zedo|" +
        "buysellads?|sharethrough|smartadserver|openx|rubicon|criteo|" +
        "pubmatic|media\\.net)", RegexOption.IGNORE_CASE)
    private val reQsz = Regex(
        "[?&](?:type|size|w|h|width|height)=(f?)(\\d{1,4})(?:[_x](\\d{1,4}))?",
        RegexOption.IGNORE_CASE)

    private fun junkUrl(u: String): Boolean {
        val b = u.substringBefore('#').substringBefore('?')
        if (reBadExt.containsMatchIn(b)) return true
        if (reDimTag.containsMatchIn(b)) return true
        if (reJunkWords.containsMatchIn(b)) return true
        if (reAdWord.containsMatchIn(b)) return true
        if (reJunkDir.containsMatchIn(b)) return true
        if (reAdHost.containsMatchIn(b)) return true
        val m = reQsz.find(u) ?: return false
        val a = m.groupValues[2].toIntOrNull() ?: 0
        val bb = m.groupValues[3].toIntOrNull() ?: 0
        if (a > 0 && bb > 0) return maxOf(a, bb) <= 400
        if (a > 0 && m.groupValues[1] == "f") return a <= 400
        return false
    }

    private fun folderOf(u: String): String {
        if (u.startsWith("blob:")) return "blob:"
        return try {
            val p = java.net.URI(u)
            var path = p.path ?: ""
            val cut = path.lastIndexOf('/')
            path = if (cut >= 0) path.substring(0, cut + 1) else "/"
            (p.scheme ?: "https") + "://" + (p.host ?: "") + path
        } catch (_: Exception) {
            u.substringBefore('#').substringBefore('?')
        }
    }

    private fun shortFolder(f: String): String {
        if (f == "blob:") return "درون صفحه (رمزگشایی‌شده)"
        var s = f.removePrefix("https://").removePrefix("http://")
        if (s.length > 46) s = s.substring(0, 20) + "…" + s.substring(s.length - 24)
        return s
    }

    private fun snapshotCount(): Int {
        val keys = HashSet<String>()
        synchronized(netLog) { for (u in netLog) keys.add(u) }
        for (u in foundStore) keys.add(u)
        return keys.size
    }

    private val recountHandler = Handler()
    private val recountTick = object : Runnable {
        override fun run() {
            try { recountAsync() } catch (_: Exception) {}
            recountHandler.postDelayed(this, 3000)
        }
    }

    private fun parseLinksRaw(raw: String?): JSONArray? {
        var s = (raw ?: "").trim()
        if (s.isEmpty()) return null
        return try {
            val v = org.json.JSONTokener(s).nextValue()
            when (v) {
                is JSONArray -> v
                is String -> {
                    val inner = org.json.JSONTokener(v).nextValue()
                    if (inner is JSONArray) inner else null
                }
                else -> null
            }
        } catch (_: Exception) {
            null
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(BG)
        }

        val top = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setBackgroundColor(CARD)
            setPadding(12, 10, 12, 10)
        }
        val closeBtn = TextView(this).apply {
            text = "✕"
            setTextColor(TXT)
            textSize = 16f
            setPadding(14, 8, 14, 8)
            setOnClickListener { finish() }
        }
        urlBox = EditText(this).apply {
            setTextColor(TXT)
            setHintTextColor(MUT)
            hint = "آدرس سایت مانهوا…"
            textSize = 13f
            setSingleLine(true)
            imeOptions = EditorInfo.IME_ACTION_GO
            background = GradientDrawable().apply {
                setColor(Color.parseColor("#15151a"))
                cornerRadius = 22f
                setStroke(1, LINE)
            }
            setPadding(20, 16, 20, 16)
            setOnEditorActionListener { _, action, _ ->
                if (action == EditorInfo.IME_ACTION_GO) {
                    goUrl(); true
                } else false
            }
        }
        val goBtn = TextView(this).apply {
            text = "برو"
            setTextColor(Color.WHITE)
            textSize = 13f
            typeface = Typeface.DEFAULT_BOLD
            setPadding(18, 10, 18, 10)
            background = GradientDrawable().apply {
                setColor(ACC)
                cornerRadius = 18f
            }
            setOnClickListener { goUrl() }
        }
        top.addView(closeBtn, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.WRAP_CONTENT,
            ViewGroup.LayoutParams.WRAP_CONTENT))
        top.addView(urlBox, LinearLayout.LayoutParams(
            0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f).apply {
            marginStart = 6; marginEnd = 6
        })
        top.addView(goBtn, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.WRAP_CONTENT,
            ViewGroup.LayoutParams.WRAP_CONTENT))
        root.addView(top, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT))

        progress = ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply {
            max = 100
            progress = 0
            progressTintList = android.content.res.ColorStateList.valueOf(ACC)
        }
        root.addView(progress, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, dp(3)))

        web = WebView(this)
        setupWebView()
        root.addView(web, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))

        val bottom = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setBackgroundColor(CARD)
            setPadding(12, 10, 12, 10)
        }
        countLbl = TextView(this).apply {
            text = "اول فصل را باز کن، بعد «شروع ضبط» را بزن"
            setTextColor(MUT)
            textSize = 12f
            setPadding(4, 0, 4, 0)
        }
        extractBtn = TextView(this).apply {
            text = "▶ شروع ضبط"
            setTextColor(Color.WHITE)
            textSize = 14f
            typeface = Typeface.DEFAULT_BOLD
            setPadding(22, 14, 22, 14)
            background = GradientDrawable().apply {
                setColor(ACC)
                cornerRadius = 24f
            }
            setOnClickListener {
                if (!recording) startRecording() else showExtractChoice()
            }
        }
        bottom.addView(countLbl, LinearLayout.LayoutParams(
            0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        bottom.addView(extractBtn, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.WRAP_CONTENT,
            ViewGroup.LayoutParams.WRAP_CONTENT))
        root.addView(bottom, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT))

        setContentView(root)

        val startUrl = (intent?.getStringExtra(EXTRA_URL) ?: "").trim()
        if (startUrl.startsWith("http")) {
            urlBox.setText(startUrl)
            web.loadUrl(startUrl)
            recountAsync()
        } else {

            val home = if (lastSite.startsWith("http")) lastSite
                else "https://www.google.com"
            web.loadUrl(home)
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun setupWebView() {
        web.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            loadWithOverviewMode = true
            useWideViewPort = true
            builtInZoomControls = true
            displayZoomControls = false
            mixedContentMode = WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE
            userAgentString =
                "Mozilla/5.0 (Linux; Android 10; Pixel 7) " +
                "AppleWebKit/537.36 (KHTML, like Gecko) " +
                "Chrome/120.0.0.0 Mobile Safari/537.36"
        }
        try {
            CookieManager.getInstance().apply {
                setAcceptCookie(true)
                if (Build.VERSION.SDK_INT >= 21) setAcceptThirdPartyCookies(web, true)
            }
        } catch (_: Exception) {}
        web.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(
                view: WebView?, request: WebResourceRequest?): Boolean {
                return false
            }

            override fun shouldInterceptRequest(
                view: WebView?,
                request: WebResourceRequest?
            ): android.webkit.WebResourceResponse? {
                try {
                    if (recording && request != null) {
                        val u = request.url?.toString() ?: ""
                        if (u.startsWith("http")) {
                            var dest = ""
                            var accept = ""
                            val hdrs = request.requestHeaders
                            if (hdrs != null) {
                                for ((k, v) in hdrs) {
                                    val lk = k.lowercase()
                                    if (lk == "sec-fetch-dest") dest = v.lowercase()
                                    else if (lk == "accept") accept = v.lowercase()
                                }
                            }
                            val b = u.substringBefore('#').substringBefore('?')
                            val extImg = reImgExt.containsMatchIn(b) ||
                                    reImgExtFull.containsMatchIn(u)
                            if (dest == "image" ||
                                (accept.contains("image/") &&
                                        !accept.contains("text/html")) ||
                                extImg
                            ) {
                                if (!junkUrl(u)) {
                                    synchronized(netLog) { netLog.add(u) }
                                }
                            }
                        }
                    }
                } catch (_: Exception) {}
                return null
            }

            override fun onPageFinished(view: WebView?, url: String?) {
                super.onPageFinished(view, url)
                try {
                    if (url != null && url.startsWith("http")) lastSite = url
                    urlBox.setText(url ?: "")
                } catch (_: Exception) {}
                recountAsync()
            }

            override fun doUpdateVisitedHistory(view: WebView?, url: String?,
                                                isReload: Boolean) {
                super.doUpdateVisitedHistory(view, url, isReload)

                try {
                    if (url != null && url.startsWith("http")) lastSite = url
                    urlBox.setText(url ?: "")
                } catch (_: Exception) {}
                recountAsync()
            }
        }
        web.webChromeClient = object : WebChromeClient() {
            override fun onProgressChanged(view: WebView?, newProgress: Int) {
                progress.progress = newProgress
                progress.visibility =
                    if (newProgress >= 100) View.GONE else View.VISIBLE
            }

            override fun onJsAlert(
                view: WebView?, url: String?, message: String?,
                result: JsResult): Boolean {
                try {
                    Toast.makeText(this@BrowserActivity,
                        message ?: "", Toast.LENGTH_SHORT).show()
                } catch (_: Exception) {}
                result.confirm()
                return true
            }
        }
        try {
            web.addJavascriptInterface(object {
                @android.webkit.JavascriptInterface
                fun recv(idx: Int, total: Int, dataUrl: String?, srcUrl: String?) {
                    onDlItem(idx, total, dataUrl ?: "", srcUrl ?: "")
                }

                @android.webkit.JavascriptInterface
                fun chunk(idx: Int, ci: Int, cn: Int, piece: String?) {
                    onDlChunk(idx, ci, cn, piece ?: "")
                }

                @android.webkit.JavascriptInterface
                fun commit(idx: Int, total: Int, srcUrl: String?) {
                    onDlCommit(idx, total, srcUrl ?: "")
                }

                @android.webkit.JavascriptInterface
                fun done(total: Int) {
                    onDlDone(total)
                }

                @android.webkit.JavascriptInterface
                fun prev(dataUrl: String?) {
                    onPreviewData(dataUrl ?: "")
                }

                @android.webkit.JavascriptInterface
                fun th(srcUrl: String?, dataUrl: String?) {
                    onThumbData(srcUrl ?: "", dataUrl ?: "")
                }
            }, "MtDl")
        } catch (_: Exception) {}
    }

    private fun smartUrl(input: String?): String? {
        val u = input?.trim() ?: ""
        if (u.isEmpty()) return null
        if (u.startsWith("http://") || u.startsWith("https://")) return u
        var domain = u.indexOf(' ') < 0 && u.indexOf('\t') < 0
        var dots = 0
        var i = 0
        while (domain && i < u.length) {
            val c = u[i]
            if (c == '.') { dots++; i++; continue }
            val ok = (c in 'a'..'z') || (c in 'A'..'Z') || (c in '0'..'9') ||
                    c == '-' || c == '_' || c == ':' || c == '/' ||
                    c == '?' || c == '#' || c == '~'
            if (!ok) domain = false
            i++
        }
        if (domain && dots > 0) return "https://$u"
        return "https://www.google.com/search?q=" +
                java.net.URLEncoder.encode(u, "UTF-8")
    }

    private fun goUrl() {
        val u = smartUrl(urlBox.text.toString()) ?: return
        urlBox.setText(u)
        web.loadUrl(u)
    }

    private fun chapterKey(raw: String?): String {
        val u = (raw ?: "").trim()
        if (!u.startsWith("http")) return u
        return try {
            val p = java.net.URI(u)
            val host = p.host ?: ""
            var path = p.path ?: ""
            while (path.endsWith("/")) path = path.substring(0, path.length - 1)
            val list = if (path.isEmpty()) mutableListOf()
                else path.substring(1).split("/").filter { it.isNotEmpty() }.toMutableList()
            var strips = 0
            while (list.size >= 2 && strips < 2) {
                val last = list.last()
                if (!Regex("^\\d{1,4}$").matches(last)) break
                val parent = list[list.size - 2]
                val parentNumeric = Regex("^\\d+$").matches(parent)
                val parentChapMark = Regex("(ch|chap|chapter|episode|ep|sec|part)[-_]?\\d",
                    RegexOption.IGNORE_CASE).containsMatchIn(parent)
                if (parentNumeric || parentChapMark) { list.removeAt(list.size - 1); strips++ }
                else break
            }
            val q = p.rawQuery ?: ""
            val kept = q.split("&").filter { it.isNotBlank() }
                .filter { !Regex("^(page|pg|pagina)$", RegexOption.IGNORE_CASE)
                    .matches(it.substringBefore('=')) }
                .sorted()
            host + (if (list.isEmpty()) "" else "/" + list.joinToString("/")) +
                (if (kept.isEmpty()) "" else "?" + kept.joinToString("&"))
        } catch (_: Exception) {
            u.substringBefore('#').substringBefore('?')
        }
    }

    private fun syncChapterKey() {
        try {
            val cur = try { web.url } catch (_: Exception) { null }
            val k = chapterKey(cur)
            if (k != chapterKeyNow) {
                chapterKeyNow = k
                foundStore.clear()
                synchronized(netLog) { netLog.clear() }
                try { web.evaluateJavascript(CLEAR_STORE_JS, null) } catch (_: Exception) {}
            }
        } catch (_: Exception) {}
    }

    private fun mergeFound(arr: JSONArray?): Int {
        if (arr != null) {
            for (i in 0 until arr.length()) {
                val u = arr.optString(i)
                if (u.isNotBlank()) foundStore.add(u)
            }
        }
        return foundStore.size
    }

    private fun storeSnapshot(): JSONArray {
        val arr = JSONArray()
        val seen = HashSet<String>()
        for (u in foundStore) if (seen.add(u)) arr.put(u)
        synchronized(netLog) {
            for (u in netLog) if (seen.add(u)) arr.put(u)
        }
        return arr
    }

    private fun isMangaPlusViewerUrl(u: String): Boolean {
        return try {
            val p = java.net.URI(u)
            val h = (p.host ?: "").lowercase()
            (h == "mangaplus.shueisha.co.jp" ||
                    h == "www.mangaplus.shueisha.co.jp") &&
                (p.path ?: "").startsWith("/viewer/")
        } catch (_: Exception) { false }
    }

    private fun startRecording() {
        val cur = try { web.url ?: "" } catch (_: Exception) { "" }
        if (cur.isEmpty() || cur == "about:blank") {
            Toast.makeText(this, "اول یک سایت را باز کن",
                Toast.LENGTH_SHORT).show()
            return
        }
        recording = true
        foundStore.clear()
        synchronized(netLog) { netLog.clear() }
        chapterKeyNow = chapterKey(cur)
        try { web.evaluateJavascript(CLEAR_STORE_JS, null) } catch (_: Exception) {}
        extractBtn.text = "🖼 استخراج"
        countLbl.text = "در حال ضبط… صفحه فصل را ورق بزن"
        try { web.reload() } catch (_: Exception) {}
    }

    private fun showExtractChoice() {
        val cur = try { web.url ?: "" } catch (_: Exception) { "" }
        extractBtn.text = "… در حال آماده‌سازی"
        extractWithScroll { arr ->
            extractBtn.text = "🖼 استخراج"
            try {
                val all = ArrayList<String>()
                if (arr != null) {
                    for (i in 0 until arr.length()) {
                        val u = arr.optString(i)
                        if (u.isNotBlank()) all.add(u)
                    }
                }
                if (all.isEmpty()) {
                    if (cur.isNotEmpty() && isMangaPlusViewerUrl(cur)) {
                        showLinkDownloadChoice(listOf(cur), mpMode = true)
                        return@extractWithScroll
                    }
                    countLbl.text = "هیچ عکسی ضبط نشد — فصل را باز کن و ورق بزن"
                    Toast.makeText(this,
                        "هیچ عکسی ضبط نشد — صفحه فصل را باز کن و ورق بزن",
                        Toast.LENGTH_LONG).show()
                    return@extractWithScroll
                }
                showFolderDialog(all)
            } catch (e: Exception) {
                Toast.makeText(this, "خطا در استخراج: ${e.message}",
                    Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun makeMiniBtn(txt: String): TextView {
        val b = TextView(this)
        b.text = txt
        b.setTextColor(Color.parseColor("#c8ceda"))
        b.textSize = 11.5f
        b.typeface = Typeface.DEFAULT_BOLD
        b.setPadding(dp(10), dp(5), dp(10), dp(5))
        val bg = GradientDrawable()
        bg.setColor(Color.parseColor("#2d3649"))
        bg.cornerRadius = dp(10).toFloat()
        b.background = bg
        return b
    }

    private fun showLinkDownloadChoice(sel: List<String>, mpMode: Boolean = false) {
        try {
            showLinkDownloadChoiceImpl(sel, mpMode)
        } catch (e: Exception) {
            val b = android.app.AlertDialog.Builder(this)
            b.setTitle(if (mpMode) "فصلِ مانگاپلاس"
                       else "استخراج (${sel.size} عکس)")
            b.setItems(arrayOf("استخراج با لینک", "استخراج با دانلود")) { _, which ->
                if (mpMode || which == 0) finishWithLinks(sel) else downloadSelected(sel)
            }
            b.setNegativeButton("انصراف", null)
            b.show()
        }
    }

    private fun showLinkDownloadChoiceImpl(sel: List<String>, mpMode: Boolean = false) {
        val dlg = android.app.Dialog(this)
        dlg.requestWindowFeature(android.view.Window.FEATURE_NO_TITLE)
        val root = LinearLayout(this)
        root.orientation = LinearLayout.VERTICAL
        root.setPadding(dp(16), dp(16), dp(16), dp(14))
        val rootBg = GradientDrawable(
            GradientDrawable.Orientation.TOP_BOTTOM,
            intArrayOf(Color.parseColor("#171b24"), Color.parseColor("#10141c")))
        rootBg.cornerRadius = dp(18).toFloat()
        rootBg.setStroke(dp(1), Color.parseColor("#2a3242"))
        root.background = rootBg

        val title = TextView(this)
        title.text = if (mpMode) "فصلِ مانگاپلاس" else "استخراج (${sel.size} عکس)"
        title.setTextColor(Color.parseColor("#e7ebf3"))
        title.textSize = 15f
        title.typeface = Typeface.DEFAULT_BOLD
        root.addView(title)

        val sub = TextView(this)
        sub.text = if (mpMode)
            "موتور خودش عکس‌ها را از API رسمی می‌گیرد و رمزگشایی می‌کند"
        else "روشِ استخراج را انتخاب کن"
        sub.setTextColor(Color.parseColor("#8a93a8"))
        sub.textSize = 11.5f
        val subLp = LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT)
        subLp.topMargin = dp(2)
        subLp.bottomMargin = dp(10)
        root.addView(sub, subLp)

        val items = if (mpMode) arrayOf(
            Triple("🖼", "استخراج با لینک", "لینکِ فصل در فیلدِ ورودی می‌نشیند"),
            Triple("⬇", "استخراج با دانلود", "همان لینک — موتور عکس‌ها را می‌گیرد"))
        else arrayOf(
            Triple("🖼", "استخراج با لینک", "فقط لینک‌ها در فیلدِ ورودی می‌نشینند"),
            Triple("⬇", "استخراج با دانلود", "عکس‌ها همین‌جا دانلود و ذخیره می‌شوند"))
        items.forEachIndexed { idx, it ->
            val card = LinearLayout(this)
            card.orientation = LinearLayout.HORIZONTAL
            card.gravity = Gravity.CENTER_VERTICAL
            card.setPadding(dp(14), dp(12), dp(14), dp(12))
            val cardBg = GradientDrawable()
            cardBg.setColor(Color.parseColor("#1a1f2b"))
            cardBg.cornerRadius = dp(14).toFloat()
            cardBg.setStroke(dp(1), Color.parseColor("#232b3b"))
            card.background = cardBg

            val ico = TextView(this)
            ico.text = it.first
            ico.textSize = 22f
            ico.setPadding(0, 0, dp(12), 0)
            card.addView(ico, LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT))

            val txts = LinearLayout(this)
            txts.orientation = LinearLayout.VERTICAL
            val t1 = TextView(this)
            t1.text = it.second
            t1.setTextColor(Color.parseColor("#e7ebf3"))
            t1.textSize = 14f
            t1.typeface = Typeface.DEFAULT_BOLD
            val t2 = TextView(this)
            t2.text = it.third
            t2.setTextColor(Color.parseColor("#8a93a8"))
            t2.textSize = 11.5f
            txts.addView(t1)
            txts.addView(t2)
            card.addView(txts, LinearLayout.LayoutParams(
                0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))

            card.setOnClickListener {
                try { dlg.dismiss() } catch (_: Exception) {}
                if (mpMode || idx == 0) finishWithLinks(sel)
                else downloadSelected(sel)
            }
            val cardLp = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT)
            cardLp.bottomMargin = dp(8)
            root.addView(card, cardLp)
        }

        val cancel = TextView(this)
        cancel.text = "انصراف"
        cancel.setTextColor(Color.parseColor("#c8ceda"))
        cancel.textSize = 13f
        cancel.typeface = Typeface.DEFAULT_BOLD
        cancel.gravity = Gravity.CENTER
        cancel.setPadding(dp(10), dp(11), dp(10), dp(11))
        val cBg = GradientDrawable()
        cBg.setColor(Color.parseColor("#2d3649"))
        cBg.cornerRadius = dp(12).toFloat()
        cancel.background = cBg
        cancel.setOnClickListener {
            try { dlg.dismiss() } catch (_: Exception) {}
        }
        root.addView(cancel, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT))

        dlg.setContentView(root)
        dlg.show()
        dlg.window?.let { w ->
            w.setBackgroundDrawable(
                android.graphics.drawable.ColorDrawable(Color.TRANSPARENT))
            w.setLayout(Math.min(
                resources.displayMetrics.widthPixels - dp(32), dp(440)),
                ViewGroup.LayoutParams.WRAP_CONTENT)
        }
    }

    private fun showFolderDialog(all: List<String>) {
        try {
            showFolderDialogImpl(all)
        } catch (e: Exception) {
            showFolderDialogFallback(all)
        }
    }

    private fun showFolderDialogFallback(all: List<String>) {
        val (folders, keyBy) = buildFolders(all)
        val entries = folders.entries.sortedByDescending { it.value.size }
        val labels = Array(entries.size) { i ->
            "\u200E" + shortFolder(entries[i].key) +
                    "  —  " + entries[i].value.size + " عکس"
        }
        val checked = BooleanArray(entries.size) { i ->
            entries[i].value.size >= 2
        }
        if (checked.none { it } && entries.isNotEmpty()) checked[0] = true
        val b = android.app.AlertDialog.Builder(this)
        b.setTitle("پوشه‌های عکس (${entries.size}) — انتخاب کن")
        b.setMultiChoiceItems(labels, checked) { _, which, isChecked ->
            checked[which] = isChecked
        }
        b.setPositiveButton("ادامه") { _, _ ->
            val sel = ArrayList<String>()
            val checkedKeys = HashSet<String>()
            for (i in entries.indices) if (checked[i]) checkedKeys.add(entries[i].key)
            for (u in all) if (checkedKeys.contains(keyBy[u])) sel.add(u)
            if (sel.isEmpty()) {
                Toast.makeText(this, "هیچ پوشه‌ای انتخاب نشد",
                    Toast.LENGTH_SHORT).show()
                return@setPositiveButton
            }
            showLinkDownloadChoice(sel)
        }
        b.setNegativeButton("انصراف", null)
        b.show()
    }

    private fun hostOf(u: String): String {
        if (u.startsWith("blob:")) return "blob:"
        return try {
            val p = java.net.URI(u)
            (p.scheme ?: "https") + "://" + (p.host ?: "")
        } catch (_: Exception) {
            u.split("#").firstOrNull()?.split("?")?.firstOrNull() ?: u
        }
    }

    private fun buildFolders(all: List<String>):
            Pair<LinkedHashMap<String, MutableList<String>>, Map<String, String>> {
        val folders = LinkedHashMap<String, MutableList<String>>()
        for (u in all) {
            folders.getOrPut(folderOf(u)) { mutableListOf() }.add(u)
        }
        if (folders.size > maxOf(8, all.size * 6 / 10)) {
            val byHost = LinkedHashMap<String, MutableList<String>>()
            for (u in all) {
                byHost.getOrPut(hostOf(u)) { mutableListOf() }.add(u)
            }
            folders.clear()
            folders.putAll(byHost)
        }
        val keyBy = HashMap<String, String>()
        for ((k, list) in folders) for (u in list) keyBy[u] = k
        return Pair(folders, keyBy)
    }

    private fun showFolderDialogImpl(all: List<String>) {
        val (folders, _) = buildFolders(all)
        val order = folders.entries.sortedByDescending { it.value.size }
            .map { it.key }
        val rankOf = HashMap<String, Int>()
        for (i in all.indices) rankOf[all[i]] = i + 1

        val picks = HashMap<String, LinkedHashSet<String>>()
        val grids = HashMap<String, List<View>>()
        val cntViews = HashMap<String, TextView>()
        val cbViews = HashMap<String, android.widget.CheckBox>()
        val rowBgs = HashMap<String, GradientDrawable>()

        val dlg = android.app.Dialog(this)
        dlg.requestWindowFeature(android.view.Window.FEATURE_NO_TITLE)

        val root = LinearLayout(this)
        root.orientation = LinearLayout.VERTICAL
        root.setPadding(dp(16), dp(16), dp(16), dp(12))
        val rootBg = GradientDrawable(
            GradientDrawable.Orientation.TOP_BOTTOM,
            intArrayOf(Color.parseColor("#171b24"), Color.parseColor("#10141c")))
        rootBg.cornerRadius = dp(18).toFloat()
        rootBg.setStroke(dp(1), Color.parseColor("#2a3242"))
        root.background = rootBg

        val head = LinearLayout(this)
        head.orientation = LinearLayout.HORIZONTAL
        head.gravity = Gravity.CENTER_VERTICAL
        val headTxt = LinearLayout(this)
        headTxt.orientation = LinearLayout.VERTICAL
        val t1 = TextView(this)
        t1.text = "پوشه‌های عکس (${order.size})"
        t1.setTextColor(Color.parseColor("#e7ebf3"))
        t1.textSize = 15f
        t1.typeface = Typeface.DEFAULT_BOLD
        val t2 = TextView(this)
        t2.text = "کلیک = انتخاب • نگه‌داشتن روی عکس = پیش‌نمایش کامل"
        t2.setTextColor(Color.parseColor("#8a93a8"))
        t2.textSize = 11.5f
        headTxt.addView(t1)
        headTxt.addView(t2)
        head.addView(headTxt, LinearLayout.LayoutParams(
            0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        val allBtn = makeMiniBtn("همه")
        val noneBtn = makeMiniBtn("هیچ")
        head.addView(allBtn, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.WRAP_CONTENT,
            ViewGroup.LayoutParams.WRAP_CONTENT))
        val nbLp = LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.WRAP_CONTENT,
            ViewGroup.LayoutParams.WRAP_CONTENT)
        nbLp.leftMargin = dp(6)
        head.addView(noneBtn, nbLp)
        root.addView(head)

        val scroll = android.widget.ScrollView(this)
        scroll.isVerticalScrollBarEnabled = false
        val list = LinearLayout(this)
        list.orientation = LinearLayout.VERTICAL
        list.setPadding(0, dp(10), 0, 0)
        scroll.addView(list, android.view.ViewGroup.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT))
        root.addView(scroll, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))

        val screenW = resources.displayMetrics.widthPixels
        val cell = dp(76)
        val cols = Math.max(3, Math.min(8,
            (Math.min(screenW - dp(120), dp(560))) / (cell + dp(6))))

        var anyDefault = false
        for (fk in order) if (folders[fk]!!.size >= 2) anyDefault = true
        for (oi in order.indices) {
            val fk = order[oi]
            picks[fk] = LinkedHashSet()
            if (folders[fk]!!.size >= 2 || (!anyDefault && oi == 0)) {
                picks[fk]!!.addAll(folders[fk]!!)
            }
        }

        val refresh = {
            for (fk in order) {
                val p = picks[fk] ?: continue
                val arr = folders[fk] ?: continue
                val on = p.isNotEmpty()
                cbViews[fk]?.isChecked = on
                cntViews[fk]?.text = if (p.size == arr.size)
                    "${arr.size} عکس" else "${p.size}/${arr.size}"
                rowBgs[fk]?.setStroke(dp(2), Color.parseColor(
                    if (on) "#e8590c" else "#232b3b"))
                grids[fk]?.let { cells ->
                    for (i in 0 until Math.min(arr.size, cells.size)) {
                        cells[i].alpha = if (p.contains(arr[i])) 1f else 0.35f
                    }
                }
            }
        }

        for (fk in order) {
            val arr = folders[fk]!!

            val row = LinearLayout(this)
            row.orientation = LinearLayout.VERTICAL
            row.setPadding(dp(12), dp(10), dp(12), dp(10))
            val rowBg = GradientDrawable()
            rowBg.setColor(Color.parseColor("#1a1f2b"))
            rowBg.cornerRadius = dp(14).toFloat()
            rowBg.setStroke(dp(2), Color.parseColor("#232b3b"))
            row.background = rowBg
            rowBgs[fk] = rowBg
            val rowLp = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT)
            rowLp.bottomMargin = dp(8)
            row.layoutParams = rowLp

            val topRow = LinearLayout(this)
            topRow.orientation = LinearLayout.HORIZONTAL
            topRow.gravity = Gravity.CENTER_VERTICAL
            val cb = android.widget.CheckBox(this)
            try {
                cb.buttonTintList = android.content.res.ColorStateList.valueOf(
                    Color.parseColor("#e8590c"))
            } catch (_: Exception) {}
            cbViews[fk] = cb
            val name = TextView(this)
            name.text = "\u200E" + shortFolder(fk)
            name.setTextColor(Color.parseColor("#e7ebf3"))
            name.textSize = 12.5f
            name.gravity = Gravity.LEFT
            val nameLp = LinearLayout.LayoutParams(
                0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
            nameLp.leftMargin = dp(8)
            nameLp.rightMargin = dp(8)
            topRow.addView(cb)
            topRow.addView(name, nameLp)
            val cnt = TextView(this)
            cnt.setTextColor(Color.WHITE)
            cnt.textSize = 11.5f
            cnt.typeface = Typeface.DEFAULT_BOLD
            val cntBg = GradientDrawable()
            cntBg.setColor(Color.parseColor("#2d3649"))
            cntBg.cornerRadius = dp(10).toFloat()
            cnt.background = cntBg
            cnt.setPadding(dp(10), dp(3), dp(10), dp(3))
            cntViews[fk] = cnt
            topRow.addView(cnt, LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT))
            val exp = makeMiniBtn("پیش‌نمایش")
            val expLp = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT)
            expLp.leftMargin = dp(8)
            topRow.addView(exp, expLp)
            row.addView(topRow)

            val strip = LinearLayout(this)
            strip.orientation = LinearLayout.HORIZONTAL
            val stripLp = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT)
            stripLp.topMargin = dp(8)
            strip.layoutParams = stripLp
            for (s in 0 until Math.min(arr.size, 4)) {
                val iv = android.widget.ImageView(this)
                iv.scaleType = android.widget.ImageView.ScaleType.CENTER_CROP
                val ivBg = GradientDrawable()
                ivBg.setColor(Color.parseColor("#232b3b"))
                ivBg.cornerRadius = dp(10).toFloat()
                ivBg.setStroke(dp(1), Color.parseColor("#2a3242"))
                iv.background = ivBg
                iv.clipToOutline = true
                val ivLp = LinearLayout.LayoutParams(dp(58), dp(58))
                if (s > 0) ivLp.leftMargin = dp(6)
                strip.addView(iv, ivLp)
                loadThumb(iv, arr[s])
                iv.setOnLongClickListener {
                    showFullPreview(arr[s]); true
                }
            }
            row.addView(strip)

            val grid = android.widget.GridLayout(this)
            grid.columnCount = cols
            grid.visibility = View.GONE
            val gridLp = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT)
            gridLp.topMargin = dp(8)
            grid.layoutParams = gridLp
            val cells = ArrayList<View>()
            for (g in arr.indices) {
                val u = arr[g]
                val cellBox = android.widget.FrameLayout(this)
                val clp = android.widget.GridLayout.LayoutParams()
                clp.width = cell
                clp.height = cell * 3 / 2
                clp.columnSpec = android.widget.GridLayout.spec(g % cols)
                clp.rowSpec = android.widget.GridLayout.spec(g / cols)
                val mm = dp(3)
                clp.setMargins(mm, mm, mm, mm)
                cellBox.layoutParams = clp

                val iv = android.widget.ImageView(this)
                iv.scaleType = android.widget.ImageView.ScaleType.CENTER_CROP
                val ivBg = GradientDrawable()
                ivBg.setColor(Color.parseColor("#232b3b"))
                ivBg.cornerRadius = dp(10).toFloat()
                iv.background = ivBg
                iv.clipToOutline = true
                cellBox.addView(iv, android.widget.FrameLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.MATCH_PARENT))
                loadThumb(iv, u)

                val no = TextView(this)
                no.text = "${rankOf[u] ?: (g + 1)}"
                no.setTextColor(Color.WHITE)
                no.textSize = 10f
                no.setBackgroundColor(Color.parseColor("#a6000000"))
                no.setPadding(dp(5), dp(1), dp(5), dp(1))
                val noLp = android.widget.FrameLayout.LayoutParams(
                    ViewGroup.LayoutParams.WRAP_CONTENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT,
                    Gravity.BOTTOM or Gravity.START)
                noLp.leftMargin = dp(3)
                noLp.bottomMargin = dp(3)
                cellBox.addView(no, noLp)

                cellBox.setOnClickListener {
                    try {
                        val pp = picks[fk] ?: return@setOnClickListener
                        if (pp.contains(u)) pp.remove(u) else pp.add(u)
                        refresh()
                    } catch (_: Exception) {}
                }
                cellBox.setOnLongClickListener {
                    showFullPreview(u)
                    true
                }
                grid.addView(cellBox)
                cells.add(cellBox)
            }
            grids[fk] = cells
            row.addView(grid)

            exp.setOnClickListener {
                try {
                    val open = grid.visibility != View.VISIBLE
                    grid.visibility = if (open) View.VISIBLE else View.GONE
                    strip.visibility = if (open) View.GONE else View.VISIBLE
                    exp.text = if (open) "بستن" else "پیش‌نمایش"
                } catch (_: Exception) {}
            }
            row.setOnClickListener {
                try {
                    val pp = picks[fk] ?: return@setOnClickListener
                    val turnOn = pp.isEmpty()
                    pp.clear()
                    if (turnOn) pp.addAll(arr)
                    refresh()
                } catch (_: Exception) {}
            }
            cb.setOnClickListener {
                try {
                    val pp = picks[fk] ?: return@setOnClickListener
                    pp.clear()
                    if (cb.isChecked) pp.addAll(arr)
                    refresh()
                } catch (_: Exception) {}
            }
            list.addView(row)
        }

        refresh()

        val btns = LinearLayout(this)
        btns.orientation = LinearLayout.HORIZONTAL
        btns.gravity = Gravity.CENTER_VERTICAL
        val btnsLp = LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT)
        btnsLp.topMargin = dp(4)
        btns.layoutParams = btnsLp
        val okBtn = TextView(this)
        okBtn.text = "ادامه"
        okBtn.setTextColor(Color.WHITE)
        okBtn.textSize = 13.5f
        okBtn.typeface = Typeface.DEFAULT_BOLD
        okBtn.gravity = Gravity.CENTER
        okBtn.setPadding(dp(24), dp(11), dp(24), dp(11))
        val okBg = GradientDrawable(
            GradientDrawable.Orientation.TL_BR,
            intArrayOf(Color.parseColor("#ff4a3d"), Color.parseColor("#c9271c")))
        okBg.cornerRadius = dp(12).toFloat()
        okBtn.background = okBg
        val noBtn = TextView(this)
        noBtn.text = "انصراف"
        noBtn.setTextColor(Color.parseColor("#c8ceda"))
        noBtn.textSize = 13.5f
        noBtn.typeface = Typeface.DEFAULT_BOLD
        noBtn.gravity = Gravity.CENTER
        noBtn.setPadding(dp(24), dp(11), dp(24), dp(11))
        val noBg = GradientDrawable()
        noBg.setColor(Color.parseColor("#2d3649"))
        noBg.cornerRadius = dp(12).toFloat()
        noBtn.background = noBg
        btns.addView(noBtn, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.WRAP_CONTENT,
            ViewGroup.LayoutParams.WRAP_CONTENT))
        val okLp = LinearLayout.LayoutParams(
            0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
        okLp.leftMargin = dp(8)
        btns.addView(okBtn, okLp)
        root.addView(btns)

        allBtn.setOnClickListener {
            for (fk in order) {
                picks[fk]?.clear()
                picks[fk]?.addAll(folders[fk]!!)
            }
            refresh()
        }
        noneBtn.setOnClickListener {
            for (fk in order) picks[fk]?.clear()
            refresh()
        }
        okBtn.setOnClickListener {
            val sel = ArrayList<String>()
            for (u in all) {
                val fk = folderOf(u)
                if (picks[fk]?.contains(u) == true) sel.add(u)
            }
            if (sel.isEmpty()) {
                Toast.makeText(this, "هیچ عکسی انتخاب نشد",
                    Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            try { dlg.dismiss() } catch (_: Exception) {}
            showLinkDownloadChoice(sel)
        }
        noBtn.setOnClickListener {
            try { dlg.dismiss() } catch (_: Exception) {}
        }

        dlg.setContentView(root)
        dlg.show()
        dlg.window?.let { w ->
            w.setBackgroundDrawable(
                android.graphics.drawable.ColorDrawable(Color.TRANSPARENT))
            val dw = Math.min(screenW - dp(24), dp(600))
            w.setLayout(dw,
                (resources.displayMetrics.heightPixels * 0.82).toInt())
        }
    }

    private fun loadThumb(iv: android.widget.ImageView, u: String) {
        try {
            iv.tag = u
            try {
                THUMB_VIEWS.computeIfAbsent(u) {
                    java.util.Collections.synchronizedList(ArrayList())
                }.add(iv)
            } catch (_: Exception) {}
            THUMB_CACHE.get(u)?.let { b ->
                iv.setImageBitmap(b)
                iv.visibility = View.VISIBLE
                return
            }
            if (u.startsWith("blob:")) {
                loadThumbViaJs(u)
                return
            }
            if (THUMB_FAILED.contains(u)) {
                iv.visibility = View.INVISIBLE
                return
            }
            iv.setImageDrawable(null)
            THUMB_POOL.execute {
                var bmp: android.graphics.Bitmap? = null
                try {
                    val c = java.net.URL(u).openConnection() as
                            java.net.HttpURLConnection
                    c.connectTimeout = 9000
                    c.readTimeout = 16000
                    c.setRequestProperty("User-Agent",
                        "Mozilla/5.0 (Linux; Android 10; Pixel 7) " +
                        "AppleWebKit/537.36 (KHTML, like Gecko) " +
                        "Chrome/120.0.0.0 Mobile Safari/537.36")
                    try {
                        val ck = CookieManager.getInstance().getCookie(u)
                        if (!ck.isNullOrEmpty())
                            c.setRequestProperty("Cookie", ck)
                    } catch (_: Exception) {}
                    try {
                        val ref = try { web.url } catch (_: Exception) { null }
                        if (ref != null && ref.startsWith("http"))
                            c.setRequestProperty("Referer", ref)
                    } catch (_: Exception) {}
                    val code = c.responseCode
                    if (code in 200..299) {
                        val bo = java.io.ByteArrayOutputStream()
                        c.inputStream.use { ins ->
                            val buf = ByteArray(16384)
                            var n = ins.read(buf)
                            while (n > 0) {
                                bo.write(buf, 0, n)
                                n = ins.read(buf)
                            }
                        }
                        val data = bo.toByteArray()
                        c.disconnect()
                        if (data.isNotEmpty() && data.size < 25 * 1024 * 1024) {
                            val o = android.graphics.BitmapFactory.Options()
                            o.inJustDecodeBounds = true
                            android.graphics.BitmapFactory.decodeByteArray(
                                data, 0, data.size, o)
                            var sc = 1
                            val maxDim = Math.max(o.outWidth, o.outHeight)
                            while (maxDim / sc > 260) sc *= 2
                            val o2 = android.graphics.BitmapFactory.Options()
                            o2.inSampleSize = sc
                            bmp = android.graphics.BitmapFactory.decodeByteArray(
                                data, 0, data.size, o2)
                        }
                    } else {
                        c.disconnect()
                    }
                } catch (_: Exception) {}
                val b2 = bmp
                if (b2 == null) {
                    THUMB_FAILED.add(u)
                    runOnUiThread {
                        try {
                            if (u == iv.tag) iv.visibility = View.INVISIBLE
                        } catch (_: Exception) {}
                    }
                    return@execute
                }
                THUMB_CACHE.put(u, b2)
                runOnUiThread {
                    try {
                        if (u == iv.tag) {
                            iv.setImageBitmap(b2)
                            iv.visibility = View.VISIBLE
                        }
                    } catch (_: Exception) {}
                }
            }
        } catch (_: Exception) {}
    }

    private fun loadThumbViaJs(u: String) {
        try {
            val q = JSONObject.quote(u)
            val js = "(function(){" +
                "try{" +
                "var U=" + q + ";" +
                "function done(d){try{window.MtDl.th(U,d||'')}catch(e){}}" +
                "function finish(b){" +
                "if(!b){done('');return}" +
                "try{" +
                "var fr=new FileReader();" +
                "fr.onload=function(){" +
                "try{" +
                "var s=String(fr.result||'');" +
                "var img=new Image();" +
                "img.onload=function(){" +
                "try{" +
                "var cv=document.createElement('canvas');" +
                "var mw=img.width||1,mh=img.height||1;" +
                "var sc=Math.min(1,240/Math.max(mw,mh));" +
                "cv.width=Math.max(1,Math.round(mw*sc));" +
                "cv.height=Math.max(1,Math.round(mh*sc));" +
                "cv.getContext('2d').drawImage(img,0,0,cv.width,cv.height);" +
                "done(cv.toDataURL('image/jpeg',0.72))" +
                "}catch(e){done(s)}" +
                "};" +
                "img.onerror=function(){done(s)};" +
                "img.src=s" +
                "}catch(e){done(s)}" +
                "};" +
                "fr.onerror=function(){done('')};" +
                "fr.readAsDataURL(b)" +
                "}catch(e){done('')}" +
                "}" +
                "var mb=null;" +
                "try{mb=window.__MT_BLOBS[String(U).split('#')[0]]}catch(e){}" +
                "if(mb&&mb!==1){finish(mb);return}" +
                "try{" +
                "fetch(U).then(function(r){return r.ok?r.blob():null})" +
                ".then(function(b){finish(b)})" +
                ".catch(function(){done('')})" +
                "}catch(e){done('')}" +
                "}catch(e){try{window.MtDl.th(U,'')}catch(e2){}}" +
                "})()"
            web.evaluateJavascript(js, null)
        } catch (_: Exception) {
            onThumbData(u, "")
        }
    }

    private fun onThumbData(u: String, dataUrl: String) {
        if (dataUrl.length < 64) {
            THUMB_FAILED.add(u)
            return
        }
        THUMB_POOL.execute {
            var bmp: android.graphics.Bitmap? = null
            try {
                val b64 = dataUrl.substring(dataUrl.indexOf(',') + 1)
                val bytes = android.util.Base64.decode(
                    b64, android.util.Base64.DEFAULT)
                if (bytes.isNotEmpty()) {
                    val o = android.graphics.BitmapFactory.Options()
                    o.inJustDecodeBounds = true
                    android.graphics.BitmapFactory.decodeByteArray(
                        bytes, 0, bytes.size, o)
                    var sc = 1
                    val maxDim = Math.max(o.outWidth, o.outHeight)
                    while (maxDim / sc > 260) sc *= 2
                    val o2 = android.graphics.BitmapFactory.Options()
                    o2.inSampleSize = sc
                    bmp = android.graphics.BitmapFactory.decodeByteArray(
                        bytes, 0, bytes.size, o2)
                }
            } catch (_: Exception) {}
            if (bmp == null) {
                THUMB_FAILED.add(u)
                return@execute
            }
            val b2 = bmp
            THUMB_CACHE.put(u, b2)
            runOnUiThread {
                try {
                    val lst = THUMB_VIEWS[u]
                    if (lst != null) {
                        synchronized(lst) {
                            for (iv2 in lst) {
                                try {
                                    if (iv2 != null && iv2.tag == u) {
                                        iv2.setImageBitmap(b2)
                                        iv2.visibility = View.VISIBLE
                                    }
                                } catch (_: Exception) {}
                            }
                        }
                    }
                } catch (_: Exception) {}
            }
        }
    }

    private var previewIv: android.widget.ImageView? = null
    private var previewTag: String? = null
    private var previewLd: TextView? = null
    private var previewErr: TextView? = null

    private fun showFullPreview(u: String) {
        try {
            val dlg = android.app.Dialog(this)
            dlg.requestWindowFeature(android.view.Window.FEATURE_NO_TITLE)
            val root = android.widget.FrameLayout(this)
            root.setBackgroundColor(Color.parseColor("#F204060A"))
            val iv = android.widget.ImageView(this)
            iv.scaleType = android.widget.ImageView.ScaleType.FIT_CENTER
            root.addView(iv, android.widget.FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT))
            val ld = TextView(this)
            ld.text = "… در حال بارگذاری"
            ld.setTextColor(Color.parseColor("#8a93a8"))
            ld.textSize = 12.5f
            ld.gravity = Gravity.CENTER
            root.addView(ld, android.widget.FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT,
                Gravity.TOP or Gravity.CENTER_HORIZONTAL))
            val errm = TextView(this)
            errm.text = "تصویر بارگذاری نشد — سایت اجازه‌ی نمایش مستقیم نمی‌دهد"
            errm.setTextColor(Color.parseColor("#ffb4ad"))
            errm.textSize = 12.5f
            errm.gravity = Gravity.CENTER
            errm.setPadding(dp(24), 0, dp(24), 0)
            errm.visibility = View.GONE
            root.addView(errm, android.widget.FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT,
                Gravity.CENTER))
            val tip = TextView(this)
            tip.text = "برای بستن لمس کن"
            tip.setTextColor(Color.parseColor("#8a93a8"))
            tip.textSize = 11.5f
            tip.gravity = Gravity.CENTER
            root.addView(tip, android.widget.FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT,
                Gravity.BOTTOM or Gravity.CENTER_HORIZONTAL))
            val tLp = tip.layoutParams as android.widget.FrameLayout.LayoutParams
            tLp.bottomMargin = dp(14)
            tip.layoutParams = tLp
            root.setOnClickListener {
                previewIv = null
                previewLd = null
                previewErr = null
                try { dlg.dismiss() } catch (_: Exception) {}
            }
            dlg.setContentView(root)
            dlg.window?.let { w ->
                w.setBackgroundDrawable(
                    android.graphics.drawable.ColorDrawable(Color.TRANSPARENT))
                w.setLayout(ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.MATCH_PARENT)
            }
            iv.tag = "full:$u"
            previewIv = iv
            previewTag = "full:$u"
            previewLd = ld
            previewErr = errm
            dlg.show()
            if (u.startsWith("blob:")) {
                loadPreviewViaJs(u)
            } else {
                loadFullInto(iv, u)
            }
        } catch (_: Exception) {}
    }

    private fun loadPreviewViaJs(u: String) {
        try {
            val q = JSONObject.quote(u)
            val js = "(function(){" +
                "try{" +
                "var U=" + q + ";" +
                "function done(d){try{window.MtDl.prev(d||'')}catch(e){}}" +
                "function finish(b){" +
                "if(!b){done('');return}" +
                "try{" +
                "var fr=new FileReader();" +
                "fr.onload=function(){" +
                "try{" +
                "var s=String(fr.result||'');" +
                "var big=s.length>=2500000||s.indexOf('data:image/avif')===0;" +
                "if(!big){done(s);return}" +
                "var img=new Image();" +
                "img.onload=function(){" +
                "try{" +
                "var cv=document.createElement('canvas');" +
                "var mw=img.width||1,mh=img.height||1;" +
                "var sc=Math.min(1,1800/Math.max(mw,mh));" +
                "cv.width=Math.max(1,Math.round(mw*sc));" +
                "cv.height=Math.max(1,Math.round(mh*sc));" +
                "cv.getContext('2d').drawImage(img,0,0,cv.width,cv.height);" +
                "done(cv.toDataURL('image/jpeg',0.88))" +
                "}catch(e){done(s)}" +
                "};" +
                "img.onerror=function(){done(s)};" +
                "img.src=s" +
                "}catch(e){done(s)}" +
                "};" +
                "fr.onerror=function(){done('')};" +
                "fr.readAsDataURL(b)" +
                "}catch(e){done('')}" +
                "}" +
                "var mb=null;" +
                "try{mb=window.__MT_BLOBS[String(U).split('#')[0]]}catch(e){}" +
                "if(mb&&mb!==1){finish(mb);return}" +
                "try{" +
                "fetch(U,{credentials:'include'}).then(function(r){return r.ok?r.blob():null})" +
                ".then(function(b){finish(b)})" +
                ".catch(function(){done('')})" +
                "}catch(e){done('')}" +
                "}catch(e){try{window.MtDl.prev('')}catch(e2){}}" +
                "})()"
            web.evaluateJavascript(js, null)
        } catch (_: Exception) {
            onPreviewData("")
        }
    }

    private fun onPreviewData(dataUrl: String) {
        runOnUiThread {
            val iv = previewIv
            val tag = previewTag
            val ld = previewLd
            val errm = previewErr
            if (iv == null || tag == null || iv.tag != tag) return@runOnUiThread
            if (dataUrl.length < 64) {
                ld?.visibility = View.GONE
                errm?.visibility = View.VISIBLE
                return@runOnUiThread
            }
            THUMB_POOL.execute {
                var bmp: android.graphics.Bitmap? = null
                try {
                    val b64 = dataUrl.substring(dataUrl.indexOf(',') + 1)
                    val bytes = android.util.Base64.decode(
                        b64, android.util.Base64.DEFAULT)
                    if (bytes.isNotEmpty()) {
                        val o = android.graphics.BitmapFactory.Options()
                        o.inJustDecodeBounds = true
                        android.graphics.BitmapFactory.decodeByteArray(
                            bytes, 0, bytes.size, o)
                        var sc = 1
                        val maxDim = Math.max(o.outWidth, o.outHeight)
                        while (maxDim / sc > 2200) sc *= 2
                        val o2 = android.graphics.BitmapFactory.Options()
                        o2.inSampleSize = sc
                        bmp = android.graphics.BitmapFactory.decodeByteArray(
                            bytes, 0, bytes.size, o2)
                    }
                } catch (_: Exception) {}
                val b = bmp
                runOnUiThread {
                    try {
                        ld?.visibility = View.GONE
                        if (b != null) {
                            errm?.visibility = View.GONE
                            iv.setImageBitmap(b)
                        } else {
                            errm?.visibility = View.VISIBLE
                        }
                    } catch (_: Exception) {}
                }
            }
        }
    }

    private fun loadFullInto(iv: android.widget.ImageView, u: String) {
        try {
            iv.tag = "full:$u"
            THUMB_POOL.execute {
                var bmp: android.graphics.Bitmap? = null
                try {
                    val c = java.net.URL(u).openConnection() as
                            java.net.HttpURLConnection
                    c.connectTimeout = 12000
                    c.readTimeout = 25000
                    c.setRequestProperty("User-Agent",
                        "Mozilla/5.0 (Linux; Android 10; Pixel 7) " +
                        "AppleWebKit/537.36 (KHTML, like Gecko) " +
                        "Chrome/120.0.0.0 Mobile Safari/537.36")
                    try {
                        val ck = CookieManager.getInstance().getCookie(u)
                        if (!ck.isNullOrEmpty())
                            c.setRequestProperty("Cookie", ck)
                    } catch (_: Exception) {}
                    try {
                        val ref = try { web.url } catch (_: Exception) { null }
                        if (ref != null && ref.startsWith("http"))
                            c.setRequestProperty("Referer", ref)
                    } catch (_: Exception) {}
                    val code = c.responseCode
                    if (code in 200..299) {
                        val bo = java.io.ByteArrayOutputStream()
                        c.inputStream.use { ins ->
                            val buf = ByteArray(16384)
                            var n = ins.read(buf)
                            while (n > 0) {
                                bo.write(buf, 0, n)
                                n = ins.read(buf)
                            }
                        }
                        val data = bo.toByteArray()
                        c.disconnect()
                        if (data.isNotEmpty() && data.size < 30 * 1024 * 1024) {
                            val o = android.graphics.BitmapFactory.Options()
                            o.inJustDecodeBounds = true
                            android.graphics.BitmapFactory.decodeByteArray(
                                data, 0, data.size, o)
                            var sc = 1
                            val maxDim = Math.max(o.outWidth, o.outHeight)
                            while (maxDim / sc > 1600) sc *= 2
                            val o2 = android.graphics.BitmapFactory.Options()
                            o2.inSampleSize = sc
                            bmp = android.graphics.BitmapFactory.decodeByteArray(
                                data, 0, data.size, o2)
                        }
                    } else {
                        c.disconnect()
                    }
                } catch (_: Exception) {}
                val b = bmp
                runOnUiThread {
                    try {
                        if (iv.tag != "full:$u") return@runOnUiThread
                        if (b != null) {
                            if (previewIv === iv) previewLd?.visibility = View.GONE
                            iv.setImageBitmap(b)
                        } else {
                            if (previewIv === iv) loadPreviewViaJs(u)
                        }
                    } catch (_: Exception) {}
                }
            }
        } catch (_: Exception) {}
    }

    private fun finishWithLinks(sel: List<String>) {
        try {
            if (sel.any { it.startsWith("blob:") }) {
                countLbl.text = "${sel.size} عکس — در حال دانلود…"
                Toast.makeText(this,
                    "این سایت عکس‌ها را داخل مرورگر رمزگشایی می‌کند " +
                    "(${sel.size} صفحه) — به‌جای لینک، خودکار دانلود می‌کنم",
                    Toast.LENGTH_LONG).show()
                downloadSelected(sel)
                return
            }
            var outList = sel
            if (outList.size > 400) {
                outList = outList.subList(0, 400)
                Toast.makeText(this,
                    "برای پایداری فقط ۴۰۰ لینکِ اول منتقل شد",
                    Toast.LENGTH_SHORT).show()
            }
            val out = Intent()
            out.putExtra(EXTRA_LINKS, outList.joinToString("\n"))
            setResult(RESULT_OK, out)
            Toast.makeText(this,
                "✅ ${outList.size} لینک عکس گرفته شد",
                Toast.LENGTH_SHORT).show()
            finish()
        } catch (e: Exception) {
            Toast.makeText(this, "خطا در استخراج: ${e.message}",
                Toast.LENGTH_LONG).show()
        }
    }

    private fun downloadSelected(sel: List<String>) {
        extractBtn.text = "… در حال دانلود"
        countLbl.text = "⬇ 0/${sel.size}"
        startDownloadAll(sel)
    }

    private fun recountAsync() {
        if (!recording) return
        try {
            syncChapterKey()
            web.evaluateJavascript(EXTRACT_JS) { raw ->
                try {
                    val arr = parseLinksRaw(raw)
                    runOnUiThread {
                        mergeFound(arr)
                        val n = snapshotCount()
                        countLbl.text = if (n > 0) {
                            "● $n عکس ضبط شد"
                        } else {
                            "در حال ضبط… صفحه فصل را ورق بزن"
                        }
                    }
                } catch (_: Exception) {}
            }
        } catch (_: Exception) {}
    }

    private fun startAutoScroll(done: () -> Unit) {
        try {
            web.evaluateJavascript(SCROLL_JS, null)
        } catch (_: Exception) {}
        val h = Handler()
        val t0 = System.currentTimeMillis()
        val tick = object : Runnable {
            override fun run() {
                try {
                    web.evaluateJavascript(
                        "(window.__MT_SCROLL_DONE===1)?1:0") { v ->
                        val finished = "1" == v ||
                                System.currentTimeMillis() - t0 > 60000
                        if (finished) {
                            h.postDelayed({ done() }, 700)
                        } else {
                            h.postDelayed(this, 800)
                        }
                    }
                } catch (_: Exception) {
                    done()
                }
            }
        }
        h.postDelayed(tick, 900)
    }

    private fun hasBlobs(arr: JSONArray?): Boolean {
        if (arr == null) return false
        try {
            for (i in 0 until arr.length()) {
                if (arr.optString(i).startsWith("blob:")) return true
            }
        } catch (_: Exception) {}
        return false
    }

    private fun rankByDom(urls: List<String>, then: (List<String>) -> Unit) {
        if (urls.isEmpty()) { then(urls); return }
        try {
            val sb = StringBuilder("[")
            urls.forEachIndexed { i, u ->
                if (i > 0) sb.append(',')
                sb.append(JSONObject.quote(u))
            }
            sb.append(']')
            val js = "(function(){" +
                "try{" +
                "var KNOWN=" + sb + ";" +
                "function keyOf(u){var s=String(u);var b=s.split(/[?#]/)[0];" +
                "if(!/\\.(jpe?g|png|webp|avif|bmp|tiff?)$/i.test(b))return s.split('#')[0];" +
                "return b.replace(/[-_]\\d{2,4}x\\d{2,4}\\./i,'.')}" +
                "function ukey(u){return String(u).indexOf('blob:')===0?" +
                "String(u).split('#')[0]:keyOf(u)}" +
                "var byKey={};" +
                "for(var i=0;i<KNOWN.length;i++)byKey[ukey(KNOWN[i])]=KNOWN[i];" +
                "var out=[],seen={};" +
                "function radd(u){" +
                "try{" +
                "if(!u)return;" +
                "u=String(u).trim();" +
                "if(u.indexOf('data:')===0)return;" +
                "if(u.indexOf('blob:')!==0){" +
                "try{var a=document.createElement('a');a.href=u;u=a.href}catch(e){}}" +
                "var k=ukey(u);" +
                "if(!k||seen[k])return;" +
                "if(!Object.prototype.hasOwnProperty.call(byKey,k))return;" +
                "seen[k]=1;out.push(byKey[k])" +
                "}catch(e){}}" +
                "var DTS=['data-src','data-lazy-src','data-original','data-original-src'," +
                "'data-orig-src','data-lazy','data-url','data-image','data-echo','data-cfsrc'," +
                "'data-hi-res-src','data-full-src','data-full_image','data-large-src'," +
                "'data-file','data-path','data-actualsrc'];" +
                "function best(ss){try{var p=String(ss).split(','),b='',w=0;" +
                "for(var k=0;k<p.length;k++){var tk=p[k].trim().split(/\\s+/);" +
                "var u0=tk[0]||'';var w0=parseInt(String(tk[1]||'').replace(/[^0-9]/g,''),10)||0;" +
                "if(u0&&w0>=w){w=w0;b=u0}}return b}catch(e){return ''}}" +
                "var els=[];" +
                "try{els=document.querySelectorAll('img,source,a[href],[style*=\"url(\"]')}catch(e){}" +
                "for(var j=0;j<els.length;j++){" +
                "var el=els[j],tg=el.tagName;" +
                "if(tg==='A'){radd(el.getAttribute('href')||'');continue}" +
                "if(tg!=='IMG'&&tg!=='SOURCE'){" +
                "try{var mm=String(el.getAttribute('style')||'')." +
                "match(/url\\((['\"]?)([^'\")]+)\\1\\)/i);if(mm&&mm[2])radd(mm[2])}catch(e){}" +
                "continue}" +
                "try{radd(el.currentSrc||el.src||'')}catch(e){}" +
                "try{var ss=el.getAttribute('srcset')||el.getAttribute('data-srcset');" +
                "if(ss){var bs=best(ss);if(bs)radd(bs)}}catch(e){}" +
                "for(var d=0;d<DTS.length;d++){" +
                "try{var v=el.getAttribute(DTS[d]);if(v&&v.length>4)radd(v)}catch(e){}}" +
                "}" +
                "return out" +
                "}catch(e){return []}" +
                "})()"
            web.evaluateJavascript(js) { raw ->
                val ranked = ArrayList<String>()
                try {
                    val arr = parseLinksRaw(raw)
                    if (arr != null) {
                        for (i in 0 until arr.length()) ranked.add(arr.optString(i))
                    }
                } catch (_: Exception) {}
                if (ranked.isEmpty()) { then(urls); return@evaluateJavascript }
                val seen = HashSet<String>()
                val out = ArrayList<String>(urls.size)
                for (u in ranked) if (seen.add(u)) out.add(u)
                for (u in urls) if (seen.add(u)) out.add(u)
                then(out)
            }
        } catch (_: Exception) {
            then(urls)
        }
    }

    private fun finishWithDomOrder(snap: JSONArray, then: (JSONArray?) -> Unit) {
        try {
            val urls = ArrayList<String>()
            for (i in 0 until snap.length()) {
                val u = snap.optString(i)
                if (u.isNotBlank()) urls.add(u)
            }
            rankByDom(urls) { ranked ->
                val out = JSONArray()
                for (u in ranked) out.put(u)
                then(out)
            }
        } catch (_: Exception) {
            then(snap)
        }
    }

    private fun extractWithScroll(then: (JSONArray?) -> Unit) {
        try {
            syncChapterKey()
            web.evaluateJavascript(EXTRACT_JS) { raw ->
                runOnUiThread {
                    val arr = parseLinksRaw(raw)
                    mergeFound(arr)
                    val snapshot = storeSnapshot()
                    if (snapshot.length() > 0 && !hasBlobs(snapshot)) {
                        finishWithDomOrder(snapshot, then)
                        return@runOnUiThread
                    }
                    countLbl.text = "… در حال آماده‌سازی صفحه (اسکرول خودکار)"
                    startAutoScroll {
                        try {
                            syncChapterKey()
                            web.evaluateJavascript(EXTRACT_JS) { raw2 ->
                                runOnUiThread {
                                    val arr2 = parseLinksRaw(raw2)
                                    mergeFound(arr2)
                                    finishWithDomOrder(storeSnapshot(), then)
                                }
                            }
                        } catch (_: Exception) {
                            finishWithDomOrder(storeSnapshot(), then)
                        }
                    }
                }
            }
        } catch (_: Exception) {
            then(null)
        }
    }

    private fun httpFetch(u: String): ByteArray? {
        return try {
            val c = java.net.URL(u).openConnection() as java.net.HttpURLConnection
            c.connectTimeout = 15000
            c.readTimeout = 40000
            c.setRequestProperty("User-Agent",
                "Mozilla/5.0 (Linux; Android 10; Pixel 7) " +
                "AppleWebKit/537.36 (KHTML, like Gecko) " +
                "Chrome/120.0.0.0 Mobile Safari/537.36")
            try {
                val ck = CookieManager.getInstance().getCookie(u)
                if (!ck.isNullOrEmpty()) c.setRequestProperty("Cookie", ck)
            } catch (_: Exception) {}
            try {
                val ref = web.url
                if (ref != null && ref.startsWith("http"))
                    c.setRequestProperty("Referer", ref)
            } catch (_: Exception) {}
            val code = c.responseCode
            if (code < 200 || code >= 300) {
                c.disconnect()
                return null
            }
            val bo = java.io.ByteArrayOutputStream()
            c.inputStream.use { ins ->
                val buf = ByteArray(16384)
                while (true) {
                    val n = ins.read(buf)
                    if (n <= 0) break
                    bo.write(buf, 0, n)
                }
            }
            c.disconnect()
            if (bo.size() == 0) null else bo.toByteArray()
        } catch (_: Exception) {
            null
        }
    }

    private fun extOf(head: String, data: ByteArray): String {
        val m = Regex("data:image/(jpe?g|png|webp|bmp)").find(head.lowercase())
        if (m != null) {
            val g = m.groupValues[1]
            return if (g == "jpeg") ".jpg" else "." + g
        }
        if (data.size >= 3 && (data[0].toInt() and 0xFF) == 0xFF
                && (data[1].toInt() and 0xFF) == 0xD8) return ".jpg"
        if (data.size >= 4 && (data[0].toInt() and 0xFF) == 0x89
                && data[1] == 0x50.toByte()) return ".png"
        if (data.size >= 12 && data[0] == 'R'.code.toByte()
                && data[1] == 'I'.code.toByte()
                && data[8] == 'W'.code.toByte()) return ".webp"
        return ".jpg"
    }

    private fun onDlItem(idx: Int, total: Int, dataUrlIn: String, srcUrl: String) {
        try {
            val dir = dlDir ?: return
            var dataUrl = dataUrlIn.trim()
            if (dataUrl.isEmpty() || !dataUrl.startsWith("data:image/")) {
                val bytes = httpFetch(srcUrl)
                if (bytes != null) {
                    dataUrl = "data:image/jpeg;base64," +
                            android.util.Base64.encodeToString(bytes,
                                android.util.Base64.NO_WRAP)
                }
            }
            if (dataUrl.startsWith("data:image/") &&
                !dataUrl.startsWith("data:image/svg")
            ) {
                val head = dataUrl.substringBefore(",", "")
                val b64 = dataUrl.substringAfter(",", "")
                val bytes = try {
                    android.util.Base64.decode(b64, android.util.Base64.DEFAULT)
                } catch (_: Exception) {
                    null
                }
                if (bytes != null && bytes.isNotEmpty()) {
                    var maxDim = 0
                    try {
                        val o = android.graphics.BitmapFactory.Options()
                        o.inJustDecodeBounds = true
                        android.graphics.BitmapFactory.decodeByteArray(
                            bytes, 0, bytes.size, o)
                        maxDim = maxOf(o.outWidth, o.outHeight)
                    } catch (_: Exception) {}
                    var headStr = ""
                    try {
                        headStr = String(bytes.copyOfRange(
                            0, minOf(600, bytes.size)), Charsets.ISO_8859_1)
                    } catch (_: Exception) {}
                    val small =
                        (maxDim in 1..299) ||
                        (maxDim <= 0 && bytes.size < 4096) ||
                        headStr.contains("<svg", ignoreCase = true)
                    if (!small) {
                        val f = java.io.File(dir, "page_%03d%s".format(idx + 1,
                                extOf(head, bytes)))
                        java.io.FileOutputStream(f).use { it.write(bytes) }
                        dlOk++
                    }
                }
            }
            dlDone++
            val done = dlDone
            val ok = dlOk
            runOnUiThread {
                countLbl.text = "⬇ $done/$total" + (if (ok > 0) " — $ok ✓" else "")
            }
        } catch (_: Exception) {}
    }

    private fun onDlChunk(idx: Int, ci: Int, cn: Int, piece: String) {
        try {
            if (ci == 0) dlParts.remove(idx)
            val sb = dlParts.getOrPut(idx) { StringBuilder() }
            sb.append(piece)
            if (sb.length > 40 * 1024 * 1024) {
                sb.setLength(0)
                sb.append("!!OVERSIZE")
            }
        } catch (_: Exception) {}
    }

    private fun onDlCommit(idx: Int, total: Int, srcUrl: String) {
        var dataUrl = ""
        try {
            val sb = dlParts.remove(idx)
            if (sb != null) {
                dataUrl = sb.toString()
                if (dataUrl.startsWith("!!OVERSIZE")) dataUrl = ""
            }
        } catch (_: Exception) {
            dataUrl = ""
        }
        onDlItem(idx, total, dataUrl, srcUrl)
    }

    private fun onDlDone(total: Int) {
        runOnUiThread {
            try {
                val dir = dlDir
                val files = dir?.listFiles()?.sortedBy { it.name } ?: emptyList()
                if (files.isNotEmpty()) {
                    val out = android.content.Intent()
                    out.putExtra(EXTRA_LINKS, files.joinToString("\n") { it.absolutePath })
                    setResult(RESULT_OK, out)
                    Toast.makeText(this, "✅ ${files.size} عکس دانلود شد",
                        Toast.LENGTH_SHORT).show()
                } else {
                    Toast.makeText(this, "هیچ عکسی دانلود نشد",
                        Toast.LENGTH_LONG).show()
                }
                finish()
            } catch (_: Exception) {}
        }
    }

    private fun startDownloadAll(urls: List<String>) {
        try {
            val base = getExternalFilesDir(null) ?: filesDir
            dlDir = java.io.File(base, "manga_dl_" + System.currentTimeMillis())
            dlDir?.mkdirs()
            dlDone = 0
            dlOk = 0
            dlParts.clear()
        } catch (e: Exception) {
            Toast.makeText(this, "خطا در آماده‌سازی دانلود: ${e.message}",
                Toast.LENGTH_LONG).show()
            return
        }
        val arr = JSONArray(urls)
        val js = buildString {
            append("(function(){try{var urls=").append(arr.toString()).append(";")
            append("function afix(b){return new Promise(function(res){")
            append("try{")
            append("if(!b||String(b.type||'').indexOf('avif')<0){res(b);return}")
            append("createImageBitmap(b).then(function(bp){")
            append("try{var c=document.createElement('canvas');")
            append("c.width=bp.width||1;c.height=bp.height||1;")
            append("c.getContext('2d').drawImage(bp,0,0);")
            append("if(c.toBlob){c.toBlob(function(j){res(j||b)},'image/jpeg',0.92);return}")
            append("res(b)}")
            append("catch(e){res(b)}})")
            append(".catch(function(){res(b)})")
            append("}catch(e){res(b)}})}")
            append("function toData(u){")
            append("try{var k=String(u).split('#')[0];")
            append("if(window.__MT_BLOBS&&window.__MT_BLOBS[k]&&window.__MT_BLOBS[k].size){")
            append("var bb=window.__MT_BLOBS[k];")
            append("return afix(bb).then(function(nb){")
            append("return new Promise(function(res){")
            append("try{var f=new FileReader();")
            append("f.onload=function(){res(String(f.result||''))};")
            append("f.onerror=function(){res('')};")
            append("f.readAsDataURL(nb)}")
            append("catch(e){res('')}})})}}catch(e){}")
            append("function fgo(o){return fetch(u,o)")
            append(".then(function(r){if(!r.ok)return '';return r.blob()})}")
            append("return fgo()")
            append(".then(function(b){if(b)return b;return fgo({credentials:'include'})})")
            append(".then(function(b){if(!b)return '';return afix(b)})")
            append(".then(function(b){if(!b)return '';return new Promise(function(res){")
            append("try{var f=new FileReader();")
            append("f.onload=function(){res(String(f.result||''))};")
            append("f.onerror=function(){res('')};f.readAsDataURL(b)}")
            append("catch(e){res('')}})})")
            append(".then(function(d){if(d&&d.indexOf('data:image')===0)return d;")
            append("if(String(u).indexOf('blob:')!==0)return '';")
            append("return new Promise(function(res2){")
            append("try{var im=null;")
            append("try{var cs=document.querySelectorAll('img');var kk=String(u).split('#')[0];")
            append("for(var q=0;q<cs.length;q++){var ss='';")
            append("try{ss=cs[q].currentSrc||cs[q].src||''}catch(e5){}")
            append("if(ss&&ss.split('#')[0]===kk){im=cs[q];break}}}catch(e7){}")
            append("if(im&&im.complete&&im.naturalWidth>0){")
            append("try{var cv2=document.createElement('canvas');")
            append("cv2.width=im.naturalWidth;cv2.height=im.naturalHeight;")
            append("cv2.getContext('2d').drawImage(im,0,0);")
            append("res2(cv2.toDataURL('image/jpeg',0.92)||'');return}")
            append("catch(e6){}}")
            append("im=new Image();")
            append("im.onload=function(){try{var cv=document.createElement('canvas');")
            append("cv.width=im.naturalWidth||1;cv.height=im.naturalHeight||1;")
            append("var ctx=cv.getContext('2d');ctx.drawImage(im,0,0);")
            append("res2(cv.toDataURL('image/jpeg',0.92)||'')}catch(e3){res2('')}};")
            append("im.onerror=function(){res2('')};im.src=u}")
            append("catch(e4){res2('')}})})}")
            append("var CH=262144;")
            append("function send(idx,total,u,d){")
            append("try{d=String(d||'');")
            append("if(d.length<=CH){try{window.MtDl.recv(idx,total,d,u)}catch(e){}return}")
            append("var n=Math.ceil(d.length/CH);")
            append("for(var c=0;c<n;c++){")
            append("try{window.MtDl.chunk(idx,c,n,d.substr(c*CH,CH))}catch(e){}}")
            append("try{window.MtDl.commit(idx,total,u)}catch(e){}}")
            append("catch(e){try{window.MtDl.recv(idx,total,'',u)}catch(e2){}}}")
            append("var i=0;function step(){")
            append("if(i>=urls.length){try{window.MtDl.done(urls.length)}catch(e){}return}")
            append("var idx=i;var u=urls[i];i++;")
            append("toData(u).then(function(d){")
            append("send(idx,urls.length,u,d);step()})")
            append(".catch(function(){")
            append("send(idx,urls.length,u,'');step()})}")
            append("step()}catch(e){try{window.MtDl.done(0)}catch(e2){}}})()")
        }
        try {
            web.evaluateJavascript(js, null)
        } catch (e: Exception) {
            Toast.makeText(this, "خطا در شروع دانلود: ${e.message}",
                Toast.LENGTH_LONG).show()
        }
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        try {
            if (web.canGoBack()) web.goBack() else finish()
        } catch (_: Exception) {
            finish()
        }
    }

    override fun onResume() {
        super.onResume()
        recountHandler.removeCallbacks(recountTick)
        recountHandler.postDelayed(recountTick, 1200)
    }

    override fun onPause() {
        recountHandler.removeCallbacks(recountTick)
        super.onPause()
    }

    override fun onDestroy() {
        try { web.destroy() } catch (_: Exception) {}
        super.onDestroy()
    }

    private fun dp(v: Int): Int =
        (v * resources.displayMetrics.density + 0.5f).toInt()
}
