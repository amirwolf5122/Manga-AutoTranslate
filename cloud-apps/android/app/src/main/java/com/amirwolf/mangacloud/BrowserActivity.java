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
        "(function(){var OUT=[],SEEN={};function abs(u){try{var a=document.createElement('a');a.href=u;return a.href}catch(e){return null}}function qsz(u){try{var m=String(u).match(/[?&](?:type|size|w|h|width|height)=(f?)(\\d{1,4})(?:[_x](\\d{1,4}))?/i);if(!m)return 0;var a=parseInt(m[2],10)||0;var b=parseInt(m[3]||'0',10)||0;if(a>0&&b>0)return Math.max(a,b);if(m[1]&&a>0)return a;return 0}catch(e){return 0}}function junk(u){if(!u)return 1;u=String(u);if(u.indexOf('data:')===0)return 1;if(u.indexOf('blob:')===0)return 1;if(!/^https?:/i.test(u))return 1;var b=u.split(/[?#]/)[0];if(/\\.(svg|ico|gif|css|js|mjs|json|html?|xml|txt|pdf|zip|rar|7z|gz|mp4|webm|mp3|m4a|ogg|wav|woff2?|ttf|otf|eot|map)$/i.test(b))return 1;if(/[-_]\\d{2,4}x\\d{2,4}\\.(jpe?g|png|webp|avif)$/i.test(b))return 1;var q=qsz(u);if(q>0&&q<=400)return 1;if(/(logo|icon|avatar|banner|sprite|favicon|badge|flag|button|emoji|thumb(nail)?s?|placeholder|blank|spacer|transparen|loading|spinner|pixel|profile|rating|share|follow|comment|credits)/i.test(b))return 1;if(/(?:^|[^a-z0-9])ads?[._\\/-]/i.test(b))return 1;return 0}function keyOf(u){var b=String(u).split(/[?#]/)[0];return b.replace(/[-_]\\d{2,4}x\\d{2,4}\\./i,'.')}function add(u){try{if(!u)return;u=abs(String(u).trim());if(!u||junk(u))return;try{if(u===location.href)return}catch(e){}var k=keyOf(u);if(Object.prototype.hasOwnProperty.call(SEEN,k))return;SEEN[k]=1;OUT.push(u)}catch(e){}}function bestSrcset(ss){try{var parts=String(ss).split(','),best='',bw=-1;for(var k=0;k<parts.length;k++){var tk=parts[k].trim().split(/\\s+/);var u0=tk[0]||'';var w0=parseInt(String(tk[1]||'').replace(/[^0-9]/g,''),10)||0;if(u0&&w0>=bw){bw=w0;best=u0}}return best}catch(e){return ''}}var DATA_ATTS=['data-src','data-lazy-src','data-original','data-original-src','data-orig-src','data-lazy','data-url','data-image','data-echo','data-asurl','data-cfsrc','data-hi-res-src','data-full-src','data-full_image','data-large-src','data-file','data-path','data-actualsrc'];function scanDoc(doc){try{var els=doc.querySelectorAll('img');for(var i=0;i<els.length;i++){var el=els[i];var nw=0,nh=0,loaded=false;try{loaded=!!el.complete&&el.naturalWidth>0;nw=el.naturalWidth||0;nh=el.naturalHeight||0}catch(e){}var u='';try{u=el.currentSrc||el.src||''}catch(e){}if(u&&u.indexOf('data:')===0)u='';if(u&&loaded&&nw&&nh&&Math.max(nw,nh)<300)u='';if(u)add(u);try{var ss=el.getAttribute('srcset')||el.getAttribute('data-srcset');if(ss){var bs=bestSrcset(ss);if(bs)add(bs)}}catch(e){}for(var j=0;j<DATA_ATTS.length;j++){try{var v=el.getAttribute(DATA_ATTS[j]);if(v&&v.length>4)add(v)}catch(e){}}}}catch(e){}try{var sos=doc.querySelectorAll('source');for(var i2=0;i2<sos.length;i2++){var so=sos[i2];try{var s2=so.getAttribute('srcset')||so.getAttribute('data-srcset')||so.getAttribute('src');if(s2){var b2=bestSrcset(s2);if(!b2)b2=s2;if(b2)add(b2)}}catch(e){}}}catch(e){}try{var as=doc.querySelectorAll('a[href]');for(var i3=0;i3<as.length;i3++){var h=as[i3].getAttribute('href')||'';if(/^https?:/i.test(h)&&/\\.(jpe?g|png|webp|avif|bmp)([?#]|$)/i.test(h))add(h)}}catch(e){}try{var st=doc.querySelectorAll('[style*=\"url(\"]');for(var i4=0;i4<st.length;i4++){var m=String(st[i4].getAttribute('style')||'').match(/url\\((['\"]?)([^'\")]+)\\1\\)/i);if(m&&m[2])add(m[2])}}catch(e){}}function scanAll(){try{scanDoc(document)}catch(e){}try{var fs=document.querySelectorAll('iframe');for(var i=0;i<fs.length;i++){try{var d=fs[i].contentDocument;if(d)scanDoc(d)}catch(e){}}}catch(e){}try{var of=window.frames;for(var j=0;j<of.length;j++){try{var d2=of[j].document;if(d2)scanDoc(d2)}catch(e){}}}catch(e){}}function perfPass(){try{var rs=performance.getEntriesByType('resource');for(var i=0;i<rs.length;i++){var en=rs[i]||{};var n=String(en.name||'');if(!n)continue;var b=n.split(/[?#]/)[0];var t=String(en.initiatorType||'');if(/\\.(jpe?g|png|webp|avif|bmp|tiff?)$/i.test(b)){add(n);continue}if(t==='img')add(n)}}catch(e){}}function scriptPass(){try{if(OUT.length)return;var sc=document.querySelectorAll('script');var re=/https?:\\\\?\\/\\\\?\\/[^\"'\\s\\\\<>()[\\]]+?\\.(?:jpe?g|png|webp|avif|bmp)(?:\\?[^\"'\\\\\\s<>()[\\]]*)?/gi;var m,guard=0;for(var i=0;i<sc.length&&guard<800;i++){var txt='';try{txt=sc[i].textContent||''}catch(e){continue}if(!txt||txt.length<10)continue;re.lastIndex=0;while((m=re.exec(txt))&&guard<800){guard++;try{add(m[0].replace(/\\\\\\//g,'/'))}catch(e){}}}}catch(e){}}try{if(/(^|\\.)mangaplus\\.shueisha\\.co\\.jp$/i.test(location.host)&&location.pathname.indexOf('/viewer/')===0)return [location.href];}catch(e){}scanAll();perfPass();scriptPass();return OUT;})()";

    private static final String SCROLL_JS =
        "(function(){try{if(window.__MT_SCROLLING)return;window.__MT_SCROLLING=1;window.__MT_SCROLL_DONE=0;var step=Math.max(500,Math.floor(window.innerHeight*0.85));var y=0,n=0,stable=0,lastH=0;function H(){try{return Math.max(document.body?document.body.scrollHeight:0,document.documentElement?document.documentElement.scrollHeight:0)}catch(e){return 0}}lastH=H();function tick(){try{y+=step;window.scrollTo(0,y);n++;var h=H();if(h===lastH)stable++;else{stable=0;lastH=h}var atBottom=(y+window.innerHeight>=h-8);if((atBottom&&stable>=3)||n>90){try{window.scrollTo(0,0)}catch(e){}window.__MT_SCROLL_DONE=1;return}setTimeout(tick,280)}catch(e){window.__MT_SCROLL_DONE=1}}tick()}catch(e){try{window.__MT_SCROLL_DONE=1}catch(e2){}}})()";

    private WebView web;
    private EditText urlBox;
    private TextView extractBtn;
    private TextView countLbl;
    private ProgressBar progress;
    private java.io.File dlDir = null;
    private int dlDone = 0;
    private int dlOk = 0;
    private int dlSeq = 0;

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
        countLbl.setText("عکسی پیدا نشده — اول فصل را باز کن");
        countLbl.setTextColor(Color.parseColor("#8a93a8"));
        countLbl.setTextSize(12);
        countLbl.setPadding(dp(4), 0, dp(4), 0);

        extractBtn = new TextView(this);
        extractBtn.setText("🖼 استخراج");
        extractBtn.setTextColor(Color.WHITE);
        extractBtn.setTextSize(14);
        extractBtn.setTypeface(Typeface.DEFAULT_BOLD);
        extractBtn.setPadding(dp(20), dp(12), dp(20), dp(12));
        GradientDrawable exBg = new GradientDrawable();
        exBg.setColor(Color.parseColor("#e8590c"));
        exBg.setCornerRadius(dp(22));
        extractBtn.setBackground(exBg);
        extractBtn.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { showExtractChoice(); }
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
                public void done(final int total) {
                    onDlDone(total);
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

    private void recountAsync() {
        try {
            web.evaluateJavascript(EXTRACT_JS, value -> {
                try {
                    JSONArray arr = parseLinksRaw(value);
                    final int n = arr == null ? 0 : arr.length();
                    runOnUiThread(() -> countLbl.setText(n > 0
                            ? n + " عکس آماده استخراج"
                            : "عکسی پیدا نشده — اول فصل را باز کن"));
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
                            || System.currentTimeMillis() - t0 > 30000;
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

    private void extractWithScroll(final ArrCallback then) {
        try {
            web.evaluateJavascript(EXTRACT_JS, value -> runOnUiThread(() -> {
                JSONArray arr = parseLinksRaw(value);
                if (arr != null && arr.length() > 0) {
                    then.onResult(arr);
                    return;
                }
                countLbl.setText("… در حال آماده‌سازی صفحه (اسکرول خودکار)");
                startAutoScroll(() -> {
                    try {
                        web.evaluateJavascript(EXTRACT_JS, v2 -> runOnUiThread(() ->
                                then.onResult(parseLinksRaw(v2))));
                    } catch (Exception e) {
                        runOnUiThread(() -> then.onResult(null));
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

    private void extractImages() {
        String cur;
        try { cur = web.getUrl() != null ? web.getUrl() : ""; }
        catch (Exception e) { cur = ""; }
        if (cur.isEmpty() || cur.equals("about:blank")) {
            Toast.makeText(this, "اول یک سایت را باز کن",
                    Toast.LENGTH_SHORT).show();
            return;
        }
        extractBtn.setText("… در حال استخراج");
        extractWithScroll(arr -> {
            extractBtn.setText("🖼 استخراج عکس");
            try {
                if (arr == null || arr.length() == 0) {
                    countLbl.setText("عکسی پیدا نشد — صفحه فصل را باز کن");
                    Toast.makeText(BrowserActivity.this,
                            "هیچ عکسی پیدا نشد — صفحه فصل را باز کن",
                            Toast.LENGTH_LONG).show();
                    return;
                }
                StringBuilder links = new StringBuilder();
                for (int i = 0; i < arr.length(); i++) {
                    if (i > 0) links.append('\n');
                    links.append(arr.getString(i));
                }
                Intent out = new Intent();
                out.putExtra(EXTRA_LINKS, links.toString());
                setResult(RESULT_OK, out);
                Toast.makeText(BrowserActivity.this,
                        "✅ " + arr.length() + " لینک عکس گرفته شد",
                        Toast.LENGTH_SHORT).show();
                finish();
            } catch (final Exception e) {
                Toast.makeText(BrowserActivity.this,
                        "خطا در استخراج: " + e.getMessage(),
                        Toast.LENGTH_LONG).show();
            }
        });
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
            if (d.startsWith("data:image/")) {
                int ci = d.indexOf(',');
                if (ci > 0) {
                    String head = d.substring(0, ci).toLowerCase();
                    byte[] data = android.util.Base64.decode(
                            d.substring(ci + 1), android.util.Base64.NO_WRAP);
                    if (data != null && data.length > 0) {
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
            dlDone++;
            final int done = dlDone;
            final int ok = dlOk;
            runOnUiThread(() -> countLbl.setText(
                    "⬇ " + done + "/" + total + (ok > 0 ? " — " + ok + " ✓" : "")));
        } catch (Exception ignored) {
        }
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
        } catch (Exception e) {
            Toast.makeText(this, "خطا در آماده‌سازی دانلود: " + e.getMessage(),
                    Toast.LENGTH_LONG).show();
            return;
        }
        org.json.JSONArray arr = new org.json.JSONArray(urls);
        StringBuilder js = new StringBuilder();
        js.append("(function(){try{var urls=").append(arr.toString()).append(";");
        js.append("function toData(u){return fetch(u,{credentials:'include'})")
           .append(".then(function(r){if(!r.ok)return '';return r.blob()})")
           .append(".then(function(b){if(!b)return '';return new Promise(function(res){")
           .append("try{var f=new FileReader();")
           .append("f.onload=function(){res(String(f.result||''))};")
           .append("f.onerror=function(){res('')};f.readAsDataURL(b)}")
           .append("catch(e){res('')}})})}");
        js.append("var i=0,pending=0;function step(){")
           .append("if(i>=urls.length){if(pending<=0){try{window.MtDl.done(urls.length)}catch(e){}}return}")
           .append("var idx=i;var u=urls[i];i++;pending++;")
           .append("toData(u).then(function(d){")
           .append("try{window.MtDl.recv(idx,urls.length,d||'',u)}catch(e){}")
           .append("pending--;step()})")
           .append(".catch(function(){")
           .append("try{window.MtDl.recv(idx,urls.length,'',u)}catch(e){}")
           .append("pending--;step()})};");
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
        android.app.AlertDialog.Builder b = new android.app.AlertDialog.Builder(this);
        b.setTitle("روش استخراج");
        b.setItems(new String[]{"استخراج با لینک", "استخراج با دانلود"},
                (dialog, which) -> {
                    if (which == 0) extractImages(); else downloadImages();
                });
        b.setNegativeButton("انصراف", null);
        b.show();
    }

    private void downloadImages() {
        String cur;
        try { cur = web.getUrl() != null ? web.getUrl() : ""; }
        catch (Exception e) { cur = ""; }
        if (cur.isEmpty() || cur.equals("about:blank")) {
            Toast.makeText(this, "اول یک سایت را باز کن",
                    Toast.LENGTH_SHORT).show();
            return;
        }
        extractBtn.setText("… در حال دانلود");
        extractWithScroll(arr -> {
            extractBtn.setText("🖼 استخراج");
            try {
                if (arr == null || arr.length() == 0) {
                    countLbl.setText("عکسی پیدا نشد — صفحه فصل را باز کن");
                    Toast.makeText(BrowserActivity.this,
                            "هیچ عکسی پیدا نشد — صفحه فصل را باز کن",
                            Toast.LENGTH_LONG).show();
                    return;
                }
                int n = arr.length();
                if (n == 1 && isMangaPlusViewer(arr.getString(0))) {
                    Intent out = new Intent();
                    out.putExtra(EXTRA_LINKS, arr.getString(0));
                    setResult(RESULT_OK, out);
                    Toast.makeText(BrowserActivity.this,
                            "لینکِ فصلِ مانگاپلاس گرفته شد —"
                                    + " موتور خودش عکس‌ها را از"
                                    + " API رسمی می‌گیرد",
                            Toast.LENGTH_LONG).show();
                    finish();
                    return;
                }
                java.util.ArrayList<String> urls = new java.util.ArrayList<>();
                for (int i = 0; i < n; i++) urls.add(arr.getString(i));
                countLbl.setText("⬇ 0/" + n);
                startDownloadAll(urls);
            } catch (final Exception e) {
                Toast.makeText(BrowserActivity.this,
                        "خطا در دانلود: " + e.getMessage(),
                        Toast.LENGTH_LONG).show();
            }
        });
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
