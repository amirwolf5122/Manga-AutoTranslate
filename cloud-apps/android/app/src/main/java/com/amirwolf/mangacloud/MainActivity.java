package com.amirwolf.mangacloud;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.DownloadManager;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.content.ContentValues;
import android.provider.MediaStore;
import android.webkit.CookieManager;
import android.webkit.JavascriptInterface;
import android.webkit.DownloadListener;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;
import android.graphics.drawable.GradientDrawable;

public class MainActivity extends Activity {

    private static final String HOME_URL =
            "https://amirwolf512-manga-autotranslate.hf.space/";

    private WebView web;
    private LinearLayout splash;
    private TextView fab;
    private ValueCallback<Uri[]> filePathCallback;
    private static final int FILE_CHOOSER_CODE = 1001;
    private static final int REQ_BROWSER = 1004;
    private boolean pageStarted = false;
    private boolean readerMode = false;
    private final android.os.Handler uiTick = new android.os.Handler();
    private final Runnable readerWatch = new Runnable() {
        @Override public void run() {
            try { watchReader(); } catch (Exception ignored) {}
            uiTick.postDelayed(this, 900);
        }
    };

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(Color.parseColor("#0b0e14"));

        web = new WebView(this);
        root.addView(web, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT));

        TextView fab = new TextView(this);
        fab.setText("🌐");
        fab.setTextSize(20);
        fab.setGravity(Gravity.CENTER);
        fab.setTextColor(Color.WHITE);
        GradientDrawable fabBg = new GradientDrawable();
        fabBg.setShape(GradientDrawable.OVAL);
        fabBg.setColor(0xCC1f2937);
        fabBg.setStroke(dp(1), 0xFFE8590C);
        fab.setBackground(fabBg);
        fab.setElevation(dp(6));
        fab.setContentDescription("باز کردن مرورگر + استخراج عکس");
        this.fab = fab;
        fab.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                if (readerMode) refreshReader();
                else openInAppBrowser();
            }
        });
        FrameLayout.LayoutParams fabLp = new FrameLayout.LayoutParams(
                dp(48), dp(48));
        fabLp.gravity = Gravity.BOTTOM | Gravity.START;
        fabLp.setMargins(dp(14), dp(14), dp(14), dp(14));
        root.addView(fab, fabLp);

        splash = buildSplash();
        root.addView(splash, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT));

        setContentView(root);
        setupWebView();
        try {
            web.addJavascriptInterface(new Object() {
                @android.webkit.JavascriptInterface
                public void saveNamed(String dataUrl, String name) {
                    saveNamedFile(dataUrl, name);
                }
            }, "MangaCloud");
        } catch (Exception ignored) {
        }

        if (savedInstanceState != null) {
            web.restoreState(savedInstanceState);
        } else {
            web.loadUrl(HOME_URL);
        }
        uiTick.postDelayed(readerWatch, 900);
    }

    private void watchReader() {
        if (web == null) return;
        try {
            web.evaluateJavascript(
                "(function(){try{return document.getElementById('mangaReaderOverlay')?'1':'0'}catch(e){return '0'}})()",
                v -> {
                    boolean on = "\"1\"".equals(String.valueOf(v == null ? "" : v));
                    if (on != readerMode) {
                        readerMode = on;
                        if (fab != null) {
                            fab.setText("🌐");
                            fab.setTextSize(20);
                            fab.setContentDescription("باز کردن مرورگر + استخراج عکس");
                            fab.setVisibility(readerMode ? View.GONE : View.VISIBLE);
                        }
                    }
                });
        } catch (Exception ignored) {
        }
    }

    private void refreshReader() {
        try {
            web.evaluateJavascript(
                "(function(){try{var o=document.getElementById('mangaReaderOverlay');"
                + "if(!o)return;var f=o.querySelector('iframe');if(!f)return;"
                + "try{if(f.contentWindow&&f.contentWindow.location)"
                + "f.contentWindow.location.reload()}catch(e){f.src=f.src}}catch(e){}})()",
                null);
        } catch (Exception ignored) {
        }
    }

    private LinearLayout buildSplash() {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setGravity(Gravity.CENTER);
        box.setBackgroundColor(Color.parseColor("#0b0e14"));

        ProgressBar bar = new ProgressBar(this);
        box.addView(bar);

        TextView txt = new TextView(this);
        txt.setText("در حال اتصال به سرور…");
        txt.setTextColor(Color.parseColor("#c8ceda"));
        txt.setTextSize(15);
        txt.setPadding(0, 24, 0, 0);
        box.addView(txt);
        return box;
    }

    @SuppressLint("SetJavaScriptEnabled")
    private void setupWebView() {
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(true);
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        s.setSupportZoom(false);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setCacheMode(WebSettings.LOAD_DEFAULT);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            try {
                s.setForceDark(WebSettings.FORCE_DARK_OFF);
            } catch (Exception ignored) {
            }
        }

        CookieManager cm = CookieManager.getInstance();
        cm.setAcceptCookie(true);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            cm.setAcceptThirdPartyCookies(web, true);
        }

        web.setBackgroundColor(Color.parseColor("#0b0e14"));
        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri u = request.getUrl();
                String scheme = u.getScheme() == null ? "" : u.getScheme();
                if (scheme.equals("http") || scheme.equals("https")) {
                    String host = u.getHost() == null ? "" : u.getHost();
                    if (host.contains("hf.space") || host.contains("huggingface.co")
                            || host.contains("gradio.app")) {
                        return false;
                    }
                    openExternal(u);
                    return true;
                }
                if (scheme.equals("mailto") || scheme.equals("tel")
                        || scheme.equals("intent")) {
                    openExternal(u);
                    return true;
                }
                return false;
            }

            @Override
            public void onPageStarted(WebView view, String url, android.graphics.Bitmap favicon) {
                pageStarted = true;
                splash.setVisibility(View.VISIBLE);
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                splash.setVisibility(View.GONE);
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request,
                                        WebResourceError error) {
                if (request.isForMainFrame()) {
                    showOfflinePage();
                }
            }
        });

        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView view,
                                             ValueCallback<Uri[]> callback,
                                             FileChooserParams params) {
                if (filePathCallback != null) {
                    filePathCallback.onReceiveValue(null);
                }
                filePathCallback = callback;
                try {
                    Intent intent = params.createIntent();
                    startActivityForResult(intent, FILE_CHOOSER_CODE);
                } catch (ActivityNotFoundException e) {
                    filePathCallback = null;
                    return false;
                }
                return true;
            }
        });

        web.setDownloadListener(new DownloadListener() {
            @Override
            public void onDownloadStart(String url, String userAgent,
                                        String contentDisposition,
                                        String mimetype, long contentLength) {
                if (url.startsWith("data:")) {
                    saveDataUrl(url);
                    return;
                }
                if (url.startsWith("blob:")) {
                    String nm = fileNameFrom(contentDisposition, url);
                    if ("manga_download".equals(nm)) {
                        nm = "manga_backup_" + System.currentTimeMillis() + ".json";
                    }
                    final String fname = nm;
                    final String furl = url;
                    try {
                        web.evaluateJavascript(
                                "(function(u,n){try{fetch(u).then(function(r){return r.blob()})"
                                        + ".then(function(b){var f=new FileReader();f.onload=function(){"
                                        + "try{window.MangaCloud&&window.MangaCloud.saveNamed(f.result,n)}"
                                        + "catch(e){}};f.readAsDataURL(b)}).catch(function(){})}catch(e){}})('"
                                        + furl.replace("'", "\'") + "','" + fname.replace("'", "") + "')",
                                null);
                    } catch (Exception ignored) {
                    }
                    return;
                }
                try {
                    DownloadManager.Request req = new DownloadManager.Request(Uri.parse(url));
                    req.setMimeType(mimetype);
                    String cookies = CookieManager.getInstance().getCookie(url);
                    if (cookies != null) {
                        req.addRequestHeader("cookie", cookies);
                    }
                    req.addRequestHeader("User-Agent", userAgent);
                    req.setNotificationVisibility(
                            DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
                    req.setDestinationInExternalPublicDir(
                            Environment.DIRECTORY_DOWNLOADS,
                            fileNameFrom(contentDisposition, url));
                    DownloadManager dm = (DownloadManager) getSystemService(DOWNLOAD_SERVICE);
                    dm.enqueue(req);
                } catch (Exception ignored) {
                    openExternal(Uri.parse(url));
                }
            }
        });
    }

    private String fileNameFrom(String contentDisposition, String url) {
        try {
            if (contentDisposition != null) {
                String mark = "filename=";
                int i = contentDisposition.indexOf(mark);
                if (i >= 0) {
                    String nm = contentDisposition.substring(i + mark.length())
                            .replace("\"", "").replace(";", "").trim();
                    if (nm.length() > 0) return nm;
                }
            }
            String path = Uri.parse(url).getLastPathSegment();
            if (path != null && path.contains(".")) return path;
        } catch (Exception ignored) {
        }
        return "manga_download";
    }

    private void saveDataUrl(String dataUrl) {
        try {
            String[] parts = dataUrl.split(",", 2);
            if (parts.length < 2) return;
            String meta = parts[0];
            String name = "manga_download";
            if (meta.contains("name=")) {
                name = meta.substring(meta.indexOf("name=") + 5);
            }
            java.io.File dir = Environment.getExternalStoragePublicDirectory(
                    Environment.DIRECTORY_DOWNLOADS);
            if (!dir.exists()) dir.mkdirs();
            boolean b64 = meta.contains(";base64");
            java.io.File out = new java.io.File(dir, name);
            java.io.FileOutputStream fos = new java.io.FileOutputStream(out);
            if (b64) {
                fos.write(android.util.Base64.decode(parts[1],
                        android.util.Base64.DEFAULT));
            } else {
                fos.write(android.net.Uri.decode(parts[1]).getBytes("UTF-8"));
            }
            fos.close();
        } catch (Exception ignored) {
        }
    }

    private void saveNamedFile(String dataUrl, String name) {
        try {
            String[] parts = dataUrl.split(",", 2);
            if (parts.length < 2) return;
            boolean b64 = parts[0].contains(";base64");
            byte[] data;
            if (b64) {
                data = android.util.Base64.decode(parts[1],
                        android.util.Base64.DEFAULT);
            } else {
                data = android.net.Uri.decode(parts[1]).getBytes("UTF-8");
            }
            String safe = name.replaceAll("[\\/:*?\"<>|]", "_");
            if (android.os.Build.VERSION.SDK_INT >= 29) {
                ContentValues cv = new ContentValues();
                cv.put(MediaStore.Downloads.DISPLAY_NAME, safe);
                cv.put(MediaStore.Downloads.MIME_TYPE, "application/json");
                Uri uri = getContentResolver().insert(
                        MediaStore.Downloads.EXTERNAL_CONTENT_URI, cv);
                if (uri != null) {
                    try (java.io.OutputStream os =
                                 getContentResolver().openOutputStream(uri)) {
                        os.write(data);
                    }
                }
            } else {
                java.io.File dir = Environment.getExternalStoragePublicDirectory(
                        Environment.DIRECTORY_DOWNLOADS);
                if (!dir.exists()) dir.mkdirs();
                try (java.io.FileOutputStream fos =
                             new java.io.FileOutputStream(new java.io.File(dir, safe))) {
                    fos.write(data);
                }
            }
            runOnUiThread(() -> Toast.makeText(this,
                    "✅ ذخیره شد: Download/" + safe,
                    Toast.LENGTH_LONG).show());
        } catch (final Exception e) {
            runOnUiThread(() -> Toast.makeText(this,
                    "خطا در ذخیرهٔ فایل: " + e.getMessage(),
                    Toast.LENGTH_LONG).show());
        }
    }

    private void openExternal(Uri u) {
        try {
            startActivity(new Intent(Intent.ACTION_VIEW, u));
        } catch (Exception ignored) {
        }
    }

    private int dp(int v) {
        return (int) (v * getResources().getDisplayMetrics().density + 0.5f);
    }

    private void openInAppBrowser() {
        try {
            final String js = "(function(){try{"
                    + "var el=document.querySelector('#manga_inp_path textarea')"
                    + "||document.querySelector('[id*=\"manga_inp_path\"] textarea');"
                    + "var v=el?String(el.value||''):'';"
                    + "var p=v.split(/\\n|,/).map(function(x){return x.trim()})"
                    + ".filter(function(x){return x.length>0});"
                    + "if(!p.length)return '';"
                    + "var n=0;for(var i=0;i<p.length;i++){var t=p[i];"
                    + "if(t.indexOf('http://')===0||t.indexOf('https://')===0)n++}"
                    + "if(n>1)return '__MT_MANY__';"
                    + "var t=p[0];"
                    + "if(/\\.(jpe?g|png|webp|gif|avif|bmp)([?#]|$)/i.test(t))"
                    + "return '__MT_MANY__';"
                    + "return t;"
                    + "}catch(e){return ''}})()";
            web.evaluateJavascript(js, new ValueCallback<String>() {
                @Override public void onReceiveValue(String value) {
                    String initUrl = "";
                    try {
                        String v = value == null ? "" : value;
                        if (v.length() >= 2 && v.startsWith("\"")) {
                            v = v.substring(1, v.length() - 1);
                        }
                        v = v.trim();
                        if (v.equals("__MT_MANY__")) {
                            initUrl = "";
                        } else if (v.startsWith("http://")
                                || v.startsWith("https://")) {
                            initUrl = v;
                        }
                    } catch (Exception ignored) {}
                    Intent it = new Intent(MainActivity.this, BrowserActivity.class);
                    if (!initUrl.isEmpty()) it.putExtra(BrowserActivity.EXTRA_URL, initUrl);
                    startActivityForResult(it, REQ_BROWSER);
                }
            });
        } catch (Exception e) {
            try {
                startActivityForResult(
                        new Intent(this, BrowserActivity.class), REQ_BROWSER);
            } catch (Exception ignored) {}
        }
    }

    private static String sUpEndpoint = "";

    private String upEndpoint() {
        if (sUpEndpoint.isEmpty())
            sUpEndpoint = HOME_URL + "gradio_api/upload";
        return sUpEndpoint;
    }

    private String uploadFile(java.io.File f, String endpoint) throws Exception {
        String boundary = "----mtb" + System.currentTimeMillis();
        java.net.HttpURLConnection c =
                (java.net.HttpURLConnection) new java.net.URL(endpoint)
                        .openConnection();
        c.setConnectTimeout(20000);
        c.setReadTimeout(180000);
        c.setRequestMethod("POST");
        c.setDoOutput(true);
        c.setRequestProperty("Content-Type",
                "multipart/form-data; boundary=" + boundary);
        java.io.OutputStream os = c.getOutputStream();
        String head = "--" + boundary
                + "\r\nContent-Disposition: form-data; name=\"files\"; filename=\""
                + f.getName().replaceAll("[^A-Za-z0-9._-]", "_")
                + "\"\r\nContent-Type: application/octet-stream\r\n\r\n";
        os.write(head.getBytes("UTF-8"));
        try (java.io.FileInputStream fi = new java.io.FileInputStream(f)) {
            byte[] buf = new byte[16384];
            int n;
            while ((n = fi.read(buf)) > 0) os.write(buf, 0, n);
        }
        os.write(("\r\n--" + boundary + "--\r\n").getBytes("UTF-8"));
        os.flush();
        os.close();
        int code = c.getResponseCode();
        if (code == 404 || code == 405) {
            c.disconnect();
            return null;
        }
        if (code < 200 || code >= 300) {
            c.disconnect();
            throw new Exception("HTTP " + code);
        }
        java.io.ByteArrayOutputStream bo = new java.io.ByteArrayOutputStream();
        try (java.io.InputStream in = c.getInputStream()) {
            byte[] buf = new byte[8192];
            int n;
            while ((n = in.read(buf)) > 0) bo.write(buf, 0, n);
        }
        c.disconnect();
        return new String(bo.toByteArray(), "UTF-8");
    }

    private void uploadDlFiles(java.io.File dir, int count) {
        Toast.makeText(this,
                "در حال آپلودِ " + count + " عکس به سرور…",
                Toast.LENGTH_SHORT).show();
        new Thread(() -> {
            java.io.File[] fs0 = dir.listFiles();
            final java.io.File[] fs =
                    (fs0 == null) ? new java.io.File[0] : fs0;
            java.util.Arrays.sort(fs, (a, b) ->
                    a.getName().compareToIgnoreCase(b.getName()));
            final String[] paths = new String[fs.length];
            final java.util.concurrent.atomic.AtomicInteger done =
                    new java.util.concurrent.atomic.AtomicInteger();
            java.util.concurrent.ExecutorService ex =
                    java.util.concurrent.Executors.newFixedThreadPool(3);
            for (int i = 0; i < fs.length; i++) {
                final int idx = i;
                final java.io.File f = fs[i];
                ex.submit(() -> {
                    try {
                        String resp = uploadFile(f, upEndpoint());
                        if (resp == null) {
                            sUpEndpoint = HOME_URL + "upload";
                            resp = uploadFile(f, sUpEndpoint);
                        }
                        if (resp != null && !resp.isEmpty()) {
                            Object v = new org.json.JSONTokener(resp)
                                    .nextValue();
                            if (v instanceof org.json.JSONArray
                                    && ((org.json.JSONArray) v).length() > 0) {
                                paths[idx] = ((org.json.JSONArray) v)
                                        .getString(0);
                            }
                        }
                    } catch (Exception ignored) {
                    } finally {
                        done.incrementAndGet();
                    }
                    return null;
                });
            }
            ex.shutdown();
            try {
                ex.awaitTermination(30, java.util.concurrent.TimeUnit.MINUTES);
            } catch (Exception ignored) {
            }
            StringBuilder sb = new StringBuilder();
            int ok = 0;
            for (String p : paths) {
                if (p == null || p.isEmpty()) continue;
                if (ok > 0) sb.append('\n');
                sb.append(p);
                ok++;
            }
            final String text = ok > 0 ? sb.toString() : "";
            final int nOk = ok;
            runOnUiThread(() -> {
                if (!text.isEmpty()) {
                    try {
                        String payload = org.json.JSONObject.quote(text);
                        web.evaluateJavascript(
                                "window.__mtFillLinks && window.__mtFillLinks("
                                        + payload + ");", null);
                        Toast.makeText(MainActivity.this,
                                "✅ " + nOk + " عکس روی سرور آماده شد — "
                                        + "«شروع ترجمه» را بزن",
                                Toast.LENGTH_LONG).show();
                    } catch (Exception e) {
                        Toast.makeText(MainActivity.this,
                                "خطا در نشاندنِ مسیرها در فیلدِ ورودی",
                                Toast.LENGTH_LONG).show();
                    }
                } else {
                    Toast.makeText(MainActivity.this,
                            "آپلود به سرور نشد — اینترنت یا سرور را چک کن",
                            Toast.LENGTH_LONG).show();
                }
                try {
                    for (java.io.File x : fs) x.delete();
                    dir.delete();
                } catch (Exception ignored) {
                }
            });
        }).start();
    }

    private void injectLinksToPage(String links) {
        try {
            String payload = org.json.JSONObject.quote(links);
            web.evaluateJavascript(
                    "window.__mtFillLinks && window.__mtFillLinks(" + payload + ");",
                    null);
            Toast.makeText(this, "✅ لینک‌های عکس در فیلدِ ورودی نشست — «شروع ترجمه» را بزن",
                    Toast.LENGTH_LONG).show();
        } catch (Exception e) {
            try {
                android.content.ClipboardManager cb =
                        (android.content.ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
                cb.setPrimaryClip(android.content.ClipData.newPlainText("links", links));
                Toast.makeText(this, "لینک‌ها کپی شد — در فیلدِ ورودی بچسبان",
                        Toast.LENGTH_LONG).show();
            } catch (Exception ignored) {}
        }
    }

    private void showOfflinePage() {
        String html = "<html><head><meta name=\"viewport\" content=\"width=device-width,"
                + "initial-scale=1\"><style>body{background:#0b0e14;color:#c8ceda;"
                + "font-family:sans-serif;display:flex;flex-direction:column;"
                + "align-items:center;justify-content:center;height:100vh;"
                + "margin:0;text-align:center}button{margin-top:24px;"
                + "background:#2563eb;color:#fff;border:0;border-radius:12px;"
                + "padding:14px 44px;font-size:17px}</style></head><body>"
                + "<h2>اتصال برقرار نشد</h2>"
                + "<p>سرور در دسترس نیست یا اینترنت قطع است.</p>"
                + "<p>هر ۱۰ ثانیه خودکار دوباره تلاش می‌شود.</p>"
                + "<button onclick=\"location.href='"
                + HOME_URL + "'\">تلاش دوباره</button>"
                + "<script>setTimeout(function(){location.href='"
                + HOME_URL + "';},10000);</script>"
                + "</body></html>";
        web.loadDataWithBaseURL(HOME_URL, html, "text/html", "UTF-8", null);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        if (requestCode == REQ_BROWSER && resultCode == RESULT_OK && data != null) {
            String dlDir = data.getStringExtra(BrowserActivity.EXTRA_DL_DIR);
            int dlCount = data.getIntExtra(BrowserActivity.EXTRA_DL_COUNT, 0);
            if (dlDir != null && dlCount > 0) {
                uploadDlFiles(new java.io.File(dlDir), dlCount);
                return;
            }
            String links = data.getStringExtra(BrowserActivity.EXTRA_LINKS);
            if (links != null && !links.trim().isEmpty()) {
                injectLinksToPage(links.trim());
            }
            return;
        }
        if (requestCode == FILE_CHOOSER_CODE && filePathCallback != null) {
            Uri[] results = null;
            if (resultCode == RESULT_OK && data != null && data.getData() != null) {
                results = new Uri[]{data.getData()};
            } else if (resultCode == RESULT_OK && data != null && data.getClipData() != null) {
                int n = data.getClipData().getItemCount();
                results = new Uri[n];
                for (int i = 0; i < n; i++) {
                    results[i] = data.getClipData().getItemAt(i).getUri();
                }
            }
            filePathCallback.onReceiveValue(results);
            filePathCallback = null;
        } else {
            super.onActivityResult(requestCode, resultCode, data);
        }
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);
        web.saveState(outState);
    }

    @Override
    public void onBackPressed() {
        if (web.canGoBack()) {
            web.goBack();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        try {
            web.onPause();
            CookieManager.getInstance().flush();
        } catch (Exception ignored) {
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        try {
            web.onResume();
        } catch (Exception ignored) {
        }
        if (!pageStarted) {
            web.loadUrl(HOME_URL);
        }
    }

    @Override
    protected void onDestroy() {
        uiTick.removeCallbacks(readerWatch);
        try {
            web.destroy();
        } catch (Exception ignored) {
        }
        super.onDestroy();
    }
}
