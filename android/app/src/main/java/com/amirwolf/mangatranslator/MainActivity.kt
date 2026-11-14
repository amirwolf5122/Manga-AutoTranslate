package com.amirwolf.mangatranslator

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Bundle
import android.os.Environment
import android.os.ParcelFileDescriptor
import android.provider.OpenableColumns
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.text.InputType
import android.util.TypedValue
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.GridLayout
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.RadioButton
import android.widget.RadioGroup
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.SwitchCompat
import com.chaquo.python.PyException
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import com.google.android.material.slider.Slider
import org.json.JSONObject
import android.app.Dialog
import android.content.ContentValues
import android.content.pm.PackageManager
import android.graphics.drawable.ColorDrawable
import android.os.Build
import android.provider.MediaStore

import java.io.File

class MainActivity : AppCompatActivity() {

    private val BG = Color.parseColor("#060607")
    private val CARD = Color.parseColor("#0d0d10")
    private val CARD2 = Color.parseColor("#08080a")
    private val SURF2 = Color.parseColor("#121216")
    private val LINE = Color.parseColor("#1f1f24")
    private val TXT = Color.parseColor("#e8e6e1")
    private val MUT = Color.parseColor("#97948c")
    private val ACC = Color.parseColor("#ff4a3d")
    private val ACC2 = Color.parseColor("#c9271c")
    private val IMG_EXT = setOf("jpg", "jpeg", "png", "webp")

    private lateinit var bridge: com.chaquo.python.PyObject
    private lateinit var formBox: LinearLayout
    private lateinit var logBox: TextView
    private lateinit var resultsBox: LinearLayout
    private lateinit var liveBox: LinearLayout
    private lateinit var runBtn: Button
    private val liveImages = mutableListOf<String>()
    private val liveDbgImages = mutableListOf<String>()
    private var liveBtn: Button? = null
    private var livePush: ((Int) -> Unit)? = null
    private var liveTotal = 0
    private var liveDbgTotal = 0
    private var shownLiveTotal = 0
    private var shownLiveDbgTotal = 0
    @Volatile private var liveDone = false
    private var jobRunning = false
    private var cancelPending = false
    private lateinit var loadingRow: LinearLayout
    private val values = HashMap<String, Any?>()
    private val fieldViews = HashMap<String, View>()
    private val pickedFiles = HashMap<String, String>()
    private var pickerField: String? = null
    private var logFollow = true
    private val ui = Handler(Looper.getMainLooper())
    private val prefs by lazy { getSharedPreferences("manga_settings", MODE_PRIVATE) }
    private var wakeLock: android.os.PowerManager.WakeLock? = null

    private var providerBtn: Button? = null
    private var providerFieldId: String = "provider"
    private var cmDelBtn: Button? = null
    private var cmAddBtn: Button? = null
    private var cmEditBtn: Button? = null
    private var cmSaveBtn: Button? = null
    private var cmEditing: Boolean = false
    private var cmHintTv: TextView? = null
    private var cmInfoTv: TextView? = null
    private var modelFieldRoot: LinearLayout? = null
    private var modelLabelTv: TextView? = null
    private var modelRefBtn: Button? = null
    private var backupStatusView: TextView? = null
    private var manifestAppVer: String = ""
    private var formReady: Boolean = false
    private val selectMaps = HashMap<String, List<Pair<String, String>>>()

    private fun cmLoad(): MutableList<JSONObject> {
        val out = mutableListOf<JSONObject>()
        try {
            val s = prefs.getString("manga_custom_models", null)
            if (!s.isNullOrBlank()) {
                val arr = org.json.JSONArray(s)
                for (i in 0 until arr.length()) {
                    val o = arr.optJSONObject(i) ?: continue
                    val nm = o.optString("name").trim()
                    if (nm.isEmpty()) continue
                    out.add(JSONObject().apply {
                        put("name", nm)
                        put("api_base", o.optString("api_base").trim())
                        put("api_key", o.optString("api_key").trim())
                        put("model", o.optString("model").trim())
                    })
                }
            }
        } catch (_: Exception) {
        }
        return out
    }

    private fun cmSave(list: List<JSONObject>) {
        try {
            val arr = org.json.JSONArray()
            for (m in list) arr.put(m)
            prefs.edit().putString("manga_custom_models", arr.toString()).apply()
        } catch (_: Exception) {
        }
    }

    private fun cmJson(): String {
        val arr = org.json.JSONArray()
        for (m in cmLoad()) arr.put(m)
        return arr.toString()
    }

    private fun installedVersionName(): String = try {
        packageManager.getPackageInfo(packageName, 0).versionName ?: ""
    } catch (_: Exception) {
        ""
    }

    private fun dp(v: Int): Int =
        TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, v.toFloat(), resources.displayMetrics).toInt()

    private fun rounded(color: Int, radiusDp: Int, stroke: Int = 0, strokeColor: Int = LINE): GradientDrawable {
        val d = GradientDrawable()
        d.setColor(color)
        d.cornerRadius = dp(radiusDp).toFloat()
        if (stroke > 0) d.setStroke(dp(stroke), strokeColor)
        return d
    }

    private fun dashed(): GradientDrawable {
        val d = GradientDrawable()
        d.setColor(CARD2)
        d.cornerRadius = dp(12).toFloat()
        d.setStroke(dp(1) * 2, MUT, dp(6).toFloat(), dp(4).toFloat())
        return d
    }

    private fun gradBtn(): GradientDrawable {
        val d = GradientDrawable(GradientDrawable.Orientation.TL_BR, intArrayOf(ACC, ACC2))
        d.cornerRadius = dp(14).toFloat()
        return d
    }

    private fun label(t: String): TextView = TextView(this).apply {
        text = t; setTextColor(MUT); textSize = 13f; setPadding(0, dp(8), 0, dp(4))
    }

    private val modeGridIds = listOf(
        "manga_cb_twopass", "manga_cb_thinking", "manga_cb_faketest",
        "manga_cb_cleanup", "manga_cb_debug", "manga_cb_safety")

    private val modeTips = mapOf(
        "manga_cb_twopass" to "پاسِ اول بلوکها را مییابد، پاسِ دوم متنِ داخلشان را دقیق بازمیخواند — پیش‌فرض روشن",
        "manga_cb_thinking" to "سطح High — برای جمینای و OpenAI-سازگارها؛ پیش‌فرض روشن",
        "manga_cb_faketest" to "به‌جای API، متنِ الکی داخل حباب‌ها رندر میشود — چکِ استخراج/پاکسازی/رندر بدون کلید",
        "manga_cb_cleanup" to "فقط پاکسازی متن (inpaint) بدون ترجمه — کلید API لازم نیست",
        "manga_cb_debug" to "مربعِ رنگی دور هر بلوک + خروجیِ دیباگ جدا (مثلاً PDF → *_debug.pdf)",
        "manga_cb_safety" to "فیلترهای گوگل BLOCK_NONE میشوند (ضدِ سانسور) — پیش‌فرض خاموش",
        "manga_max_tokens" to "خودکار = سرویس‌دهنده خودش مدیریت میکند؛ چپترِ طولانیِ ناتمام؟ عدد را بالا ببرید")

    private var activeTip: TextView? = null
    private var activeTipRun: Runnable? = null

    private fun hideTip() {
        activeTipRun?.let { ui.removeCallbacks(it) }
        activeTipRun = null
        activeTip?.let { t -> (t.parent as? ViewGroup)?.removeView(t) }
        activeTip = null
    }

    private fun showTip(anchor: View, text: String) {
        hideTip()
        val root = findViewById<ViewGroup>(android.R.id.content) ?: return
        val tv = TextView(this).apply {
            this.text = text
            setTextColor(TXT); textSize = 12.5f
            background = rounded(Color.parseColor("#15151b"), 12, 1)
            setPadding(dp(12), dp(10), dp(12), dp(10))
        }
        val lp = FrameLayout.LayoutParams(
            ViewGroup.LayoutParams.WRAP_CONTENT,
            ViewGroup.LayoutParams.WRAP_CONTENT)
        root.addView(tv, lp)
        tv.measure(View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED),
            View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED))
        val ar = IntArray(2)
        anchor.getLocationInWindow(ar)
        val sw = resources.displayMetrics.widthPixels
        val sh = resources.displayMetrics.heightPixels
        var x = ar[0] + anchor.width / 2 - tv.measuredWidth / 2
        x = Math.max(dp(8), Math.min(x, sw - tv.measuredWidth - dp(8)))
        var y = ar[1] + anchor.height + dp(10)
        if (y + tv.measuredHeight > sh - dp(24))
            y = Math.max(dp(8), ar[1] - tv.measuredHeight - dp(10))
        lp.leftMargin = x
        lp.topMargin = y
        tv.layoutParams = lp
        activeTip = tv
        val r = Runnable { hideTip() }
        activeTipRun = r
        ui.postDelayed(r, 10000)
    }

    private fun tipButton(text: String): Button = Button(this).apply {
        this.text = "؟"
        setTextColor(MUT); textSize = 10f
        background = rounded(Color.parseColor("#15151b"), 9, 1)
        setPadding(0, 0, 0, 0)
        stateListAnimator = null
        minWidth = 0; minimumWidth = 0
        minHeight = 0; minimumHeight = 0
        setOnClickListener { v -> showTip(v, text) }
    }

    private fun addModeCell(grid: LinearLayout, f: JSONObject, idx: Int) {
        val id = f.optString("id")
        val lbl = f.optString("label", "")
        val tip = modeTips[id] ?: ""
        val dfltRaw = f.opt("default")
        val dflt: Any? = if (dfltRaw is JSONObject) dfltRaw.opt("default") else dfltRaw
        if (idx % 3 == 0) {
            grid.addView(LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                layoutDirection = View.LAYOUT_DIRECTION_RTL
            }, LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT).apply { bottomMargin = dp(6) })
        }
        val row = grid.getChildAt(grid.childCount - 1) as LinearLayout
        val cell = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = rounded(CARD2, 10, 1)
            setPadding(dp(6), dp(6), dp(6), dp(7))
        }
        val topRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            layoutDirection = View.LAYOUT_DIRECTION_RTL
        }
        val sw = SwitchCompat(this).apply {
            setPadding(0, 0, 0, 0)
            val svB = savedOr(id, dflt)
            isChecked = when (svB) {
                is Boolean -> svB
                is String -> svB.equals("true", true)
                else -> (dflt == true)
            }
            thumbTintList = android.content.res.ColorStateList.valueOf(ACC)
            trackTintList = android.content.res.ColorStateList(
                arrayOf(intArrayOf(android.R.attr.state_checked), intArrayOf()),
                intArrayOf(ACC, LINE))
            setOnCheckedChangeListener { _, c -> saveVal(id, c) }
        }
        topRow.addView(sw, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.WRAP_CONTENT,
            ViewGroup.LayoutParams.WRAP_CONTENT))
        topRow.addView(View(this), LinearLayout.LayoutParams(0, 1, 1f))
        if (tip.isNotEmpty()) {
            topRow.addView(tipButton(tip), LinearLayout.LayoutParams(
                dp(17), dp(17)).apply { marginStart = dp(4) })
        }
        cell.addView(topRow)
        cell.addView(TextView(this).apply {
            text = lbl; setTextColor(TXT); textSize = 11.5f
            gravity = Gravity.CENTER
            setPadding(0, dp(4), 0, 0)
        })
        row.addView(cell, LinearLayout.LayoutParams(0,
            ViewGroup.LayoutParams.WRAP_CONTENT, 1f).apply {
            marginStart = dp(5)
        })
        fieldViews[id] = sw
    }

    private fun saveVal(id: String, v: Any?) {
        values[id] = v
        prefs.edit().putString(id, v?.toString() ?: "").apply()
        notifyDeps(id)
    }

    private val depListeners = HashMap<String, MutableList<() -> Unit>>()

    private fun notifyDeps(id: String) {
        depListeners[id]?.forEach { try { it() } catch (_: Exception) {} }
    }

    private fun savedOr(id: String, dflt: Any?): Any? {
        val s = prefs.getString(id, null)
        if (s != null) {

            if (s.equals("null", true) || s.equals("undefined", true)) return null
            return s
        }
        if (dflt === org.json.JSONObject.NULL) return null
        return dflt
    }

    private fun acquireKeepAwake() {

        try {
            window.addFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
            val pm = getSystemService(POWER_SERVICE) as android.os.PowerManager
            if (wakeLock == null) {
                wakeLock = pm.newWakeLock(android.os.PowerManager.PARTIAL_WAKE_LOCK,
                    "MangaApp:translation")
            }
            wakeLock?.takeIf { !it.isHeld }?.acquire(4 * 60 * 60 * 1000L)
            startTranslationForeground()
        } catch (_: Exception) {
        }
    }

    private fun releaseKeepAwake() {
        stopTranslationForeground()
        try {
            window.clearFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
            wakeLock?.takeIf { it.isHeld }?.release()
        } catch (_: Exception) {
        }
        wakeLock = null
    }

    private fun startTranslationForeground() {
        try {
            if (Build.VERSION.SDK_INT >= 33 &&
                checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS)
                != android.content.pm.PackageManager.PERMISSION_GRANTED &&
                !prefs.getBoolean("notif_asked", false)) {
                prefs.edit().putBoolean("notif_asked", true).apply()
                try {
                    requestPermissions(
                        arrayOf(android.Manifest.permission.POST_NOTIFICATIONS), 4150)
                } catch (_: Exception) {
                }
            }
            val i = Intent(this, TranslationService::class.java)
            if (Build.VERSION.SDK_INT >= 26) startForegroundService(i)
            else startService(i)
        } catch (_: Exception) {
        }
    }

    private fun stopTranslationForeground() {
        try {
            stopService(Intent(this, TranslationService::class.java))
        } catch (_: Exception) {
        }
    }

    private fun maybeAskBatteryExemption() {
        if (prefs.getBoolean("battery_asked", false)) return
        prefs.edit().putBoolean("battery_asked", true).apply()
        try {
            val pm = getSystemService(POWER_SERVICE) as android.os.PowerManager
            if (Build.VERSION.SDK_INT >= 23 &&
                !pm.isIgnoringBatteryOptimizations(packageName)) {
                @Suppress("BatteryLife")
                val i = Intent(
                    android.provider.Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS)
                    .setData(Uri.parse("package:$packageName"))
                startActivity(i)
            }
        } catch (_: Exception) {
        }
    }

    private var pythonStartError: String? = null

    override fun onResume() {
        super.onResume()

        val pending = try { prefs.getString("pending_apk", null) } catch (_: Exception) { null }
        if (!pending.isNullOrEmpty()) {
            val f = java.io.File(pending)
            if (f.exists() && (Build.VERSION.SDK_INT < 26 ||
                        packageManager.canRequestPackageInstalls())) {
                prefs.edit().remove("pending_apk").apply()
                launchInstall(f)
            }
        }
        if (updRow == null &&
            System.currentTimeMillis() - lastUpdCheckAt > 30 * 60_000L) {
            Thread { checkAppUpdate() }.start()
        }
    }

    override fun onDestroy() {
        if (isFinishing && jobRunning) {
            TranslationService.hardStopAndExit()
        }
        super.onDestroy()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        installCrashLogger()
        window.decorView.setBackgroundColor(BG)
        window.navigationBarColor = BG
        window.statusBarColor = BG

        pythonStartError = try {
            if (!Python.isStarted()) Python.start(AndroidPlatform(this))
            null
        } catch (t: Throwable) {
            android.util.Log.e("MainActivity", "Python.start failed", t)
            (t.message ?: t.toString())
        }

        cleanupPagesDirs()

        Thread { resetLogsOnStart() }.start()
        deleteAllMangaLogsOnStart()

        if (Build.VERSION.SDK_INT < 29 &&
            checkSelfPermission(android.Manifest.permission.WRITE_EXTERNAL_STORAGE) !=
            PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(android.Manifest.permission.WRITE_EXTERNAL_STORAGE),
                REQ_STORAGE)
        }

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(BG)
            layoutDirection = View.LAYOUT_DIRECTION_RTL
            setPadding(dp(14), dp(10), dp(14), dp(20))
        }
        setContentView(ScrollView(this).apply { addView(root) })

        root.addView(header())
        root.addView(chips())

        formBox = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        root.addView(formBox)

        runBtn = Button(this).apply {
            text = "🚀  شروع ترجمه"
            setTextColor(Color.WHITE); textSize = 17f; typeface = Typeface.DEFAULT_BOLD
            background = gradBtn(); setPadding(0, dp(14), 0, dp(14))
            stateListAnimator = null
        }
        root.addView(runBtn, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply {
            topMargin = dp(14); bottomMargin = dp(6)
        })

        val logCard = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = rounded(CARD, 18, 1)
            setPadding(dp(16), dp(12), dp(16), dp(14))
        }
        val logArrow = TextView(this).apply {
            text = "▾"; setTextColor(MUT); textSize = 16f; setPadding(dp(8), 0, dp(8), 0)
        }
        val logContent = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        val logTitle = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(0, dp(2), 0, dp(8))
        }
        logTitle.addView(TextView(this).apply {
            text = "🚩"; textSize = 15f
        }, LinearLayout.LayoutParams(dp(27), dp(27)))
        logTitle.addView(TextView(this).apply {
            text = "لاگ زنده"
            setTextColor(TXT); textSize = 15.5f; typeface = Typeface.DEFAULT_BOLD
            setPadding(dp(9), 0, 0, 0)
        })
        val logSpacer = View(this)
        logTitle.addView(logSpacer, LinearLayout.LayoutParams(0, 1, 1f))
        logTitle.addView(TextView(this).apply {
            text = "📋"
            textSize = 14f
            setPadding(dp(6), 0, dp(6), 0)
            setOnClickListener {
                val cb = getSystemService(CLIPBOARD_SERVICE) as android.content.ClipboardManager
                cb.setPrimaryClip(android.content.ClipData.newPlainText("log", logBox.text))
                Toast.makeText(this@MainActivity, "لاگ کپی شد", Toast.LENGTH_SHORT).show()
            }
        })
        logTitle.addView(logArrow)
        logTitle.setOnClickListener {
            val open = logContent.visibility == View.VISIBLE
            logContent.visibility = if (open) View.GONE else View.VISIBLE
            logArrow.text = if (open) "▸" else "▾"
        }
        logCard.addView(logTitle)
        logBox = TextView(this).apply {
            setTextColor(TXT); textSize = 11f; typeface = Typeface.MONOSPACE
            background = rounded(CARD2, 12, 1)
            setPadding(dp(12), dp(10), dp(12), dp(10))
            movementMethod = android.text.method.ScrollingMovementMethod()
            isVerticalScrollBarEnabled = true
            setOnTouchListener { v, ev ->
                v.parent.requestDisallowInterceptTouchEvent(true)
                if (ev.action == android.view.MotionEvent.ACTION_UP ||
                    ev.action == android.view.MotionEvent.ACTION_CANCEL) {
                    logFollow = !logBox.canScrollVertically(1)
                }
                false
            }
            text = "— لاگ بعد از شروع ترجمه اینجا می‌آید —"
        }
        logContent.addView(logBox, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, dp(230)).apply { topMargin = dp(4) })
        liveBox = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        logContent.addView(liveBox)
        resultsBox = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        logContent.addView(resultsBox)
        logCard.addView(logContent)
        root.addView(logCard, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply {
            topMargin = dp(10)
        })

        root.addView(footer())

        loadingRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
            setPadding(0, dp(10), 0, dp(4))
        }
        loadingRow.addView(android.widget.ProgressBar(this).apply {
            indeterminateTintList = android.content.res.ColorStateList.valueOf(ACC)
        }, LinearLayout.LayoutParams(dp(26), dp(26)))
        loadingRow.addView(TextView(this).apply {
            text = "  در حال آماده‌سازی موتور و دانلود فونت‌ها…"
            setTextColor(MUT); textSize = 12.5f
            tag = "loading_text"
        })
        root.addView(loadingRow, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))

        runBtn.setOnClickListener { onStartJob() }

        Thread { checkAppUpdateWithRetry() }.start()

        Thread {
            try {
                try {
                    val fl = java.io.File(filesDir, "fault_log.txt")
                    if (fl.isFile && fl.length() > 0) {
                        val d = fl.readText().trim()
                        fl.delete()
                        if (d.isNotEmpty()) appendCrashLog(
                            "—— سیگ‌فالتِ پایتون (faulthandler) ——\nزمان: " +
                            nowStr() + "\n" + d.take(4000))
                    }
                } catch (_: Exception) { }
                var crashRep = ""
                try {
                    val cl = java.io.File(filesDir, "crash_log.txt")
                    if (cl.isFile) {
                        val seen = prefs.getLong("crashlog_seen", -1L)
                        if (cl.lastModified() != seen) {
                            crashRep = cl.readText().take(4000)
                            prefs.edit().putLong("crashlog_seen",
                                cl.lastModified()).apply()
                        }
                    }
                } catch (_: Exception) {
                }
                pythonStartError?.let { throw RuntimeException("Python.start: $it") }
                clearOldCaches()
                copyBundledSources()
                val launcher = Python.getInstance().getModule("launcher")
                launcher.callAttr("main", filesDir.absolutePath)
                bridge = Python.getInstance().getModule("native_bridge")
                var healthReport = ""
                try {
                    val h = JSONObject(bridge.callAttr("health").toString())
                    if (!h.optBoolean("ok")) healthReport = h.optString("report", "")
                } catch (_: Exception) {
                }
                val st = launcher.callAttr("status").toString()
                val pre = StringBuilder()
                if (crashRep.isNotBlank()) {
                    pre.append("💥 گزارشِ کرشِ قبلی (این متن را برایِ سازنده بفرست):\n")
                    pre.append(crashRep).append("\n\n")
                    pre.append("مسیرِ فایل: Android/data/").append(packageName)
                        .append("/files/crash_log.txt\n\n")
                }
                ui.post {
                    setLog(pre.toString() + if (healthReport.isNotBlank())
                        healthReport + "\n\n—— وضعیت فایل‌ها —\n" + st
                    else st)
                }
                ui.post { buildForm() }
            } catch (e: PyException) {
                ui.post {
                    loadingRow.visibility = View.GONE
                    setLog("❌ خطای موتور:\n" + e.message)
                    Toast.makeText(this, "خطای موتور پایتون", Toast.LENGTH_LONG).show()
                }
            } catch (e: Throwable) {
                ui.post {
                    loadingRow.visibility = View.GONE
                    val sw = java.io.StringWriter()
                    e.printStackTrace(java.io.PrintWriter(sw))
                    setLog("❌ خطای غیرمنتظره در آماده‌سازی:\n" + sw.toString().take(2500))
                    Toast.makeText(this, "خطای غیرمنتظره", Toast.LENGTH_LONG).show()
                }
            }
        }.start()

        ui.postDelayed({
            if (loadingRow.visibility == View.VISIBLE) {
                val tv = loadingRow.findViewWithTag<TextView>("loading_text")
                tv?.text = "  ⏳ بیشتر از حد انتظار طول کشیده (دانلود فونت‌ها/بررسی آپدیت). چند لحظه دیگر صبر کن؛ اگر اپ بسته شد دوباره بازش کن — این بار سریع لود می‌شود."
            }
        }, 120_000)
    }

    private val UPD_MIRRORS = listOf(
        "https://raw.githubusercontent.com/amirwolf5122/Manga-AutoTranslate/main/",
        "https://gh-proxy.com/raw.githubusercontent.com/amirwolf5122/Manga-AutoTranslate/main/",
        "https://cdn.jsdelivr.net/gh/amirwolf5122/Manga-AutoTranslate@main/"
    )
    private var updRow: LinearLayout? = null
    private var updState = "idle"
    private var updVerName = ""
    private var updVerCode = 0
    private var updStatus: TextView? = null
    private var updBar: android.widget.ProgressBar? = null
    private var updBtn: Button? = null
    private var updThread: Thread? = null

    private fun updApkName(): String = "update_" + updVerCode + ".apk"

    private fun updPartFile(): java.io.File {
        val dir = (getExternalFilesDir(null) ?: filesDir)
        return java.io.File(dir, updApkName() + ".part")
    }

    private fun updDstFile(): java.io.File {
        val dir = (getExternalFilesDir(null) ?: filesDir)
        return java.io.File(dir, updApkName())
    }

    private fun updExpectedSize(): Long =
        prefs.getLong("apk_size_" + updVerCode, 0L)

    private fun fetchUrl(url: String, timeoutMs: Int = 15000): ByteArray {
        val c = java.net.URL(url).openConnection() as java.net.HttpURLConnection
        c.connectTimeout = timeoutMs
        c.readTimeout = timeoutMs
        c.instanceFollowRedirects = true
        c.setRequestProperty("User-Agent", "Mozilla/5.0")
        try {
            if (c.responseCode / 100 != 2) throw RuntimeException("HTTP " + c.responseCode)
            return c.inputStream.use { it.readBytes() }
        } finally {
            c.disconnect()
        }
    }

    private fun fetchMirror(path: String): ByteArray {
        var last: Exception? = null
        val bust = "?t=" + System.currentTimeMillis()
        for (m in UPD_MIRRORS) {
            try {
                return fetchUrl(m + path + bust)
            } catch (e: Exception) {
                last = e
            }
        }
        throw last ?: RuntimeException("همهٔ منابع ناموفق")
    }

    private fun nowStr(): String =
        java.text.SimpleDateFormat("yyyy-MM-dd HH:mm:ss", java.util.Locale.US)
            .format(java.util.Date())

    private fun devLine(): String {
        val abis = try { (Build.SUPPORTED_ABIS ?: arrayOf<String>())
            .take(2).joinToString(",") } catch (_: Exception) { "?" }
        return (Build.MANUFACTURER ?: "?") + " " + (Build.MODEL ?: "?") +
                " | android " + (Build.VERSION.RELEASE ?: "?") +
                " | abi " + abis
    }

    private fun appendCrashLog(txt: String) {
        try {
            val f = java.io.File(filesDir, "crash_log.txt")
            var cur = try { if (f.isFile) f.readText() else "" }
                      catch (_: Exception) { "" }
            cur += txt + "\n"
            if (cur.length > 48000) cur = cur.substring(cur.length - 48000)
            f.writeText(cur)
            try {
                val dir = getExternalFilesDir(null)
                if (dir != null) java.io.File(dir, "crash_log.txt").writeText(cur)
            } catch (_: Exception) { }
        } catch (_: Exception) { }
    }

    private fun installedVersionCode(): Int = try {
        @Suppress("DEPRECATION")
        packageManager.getPackageInfo(packageName, 0).versionCode
    } catch (_: Exception) {
        0
    }

    private fun checkAppUpdate(): Boolean {
        lastUpdCheckAt = System.currentTimeMillis()
        try {
            val vc = installedVersionCode()
            val verTxt = String(fetchMirror("VERSION")).trim()
            var remote = 0
            var rname = ""
            var apk64 = ""
            var apkv7 = ""
            var apkUni = ""
            for (ln in verTxt.lines()) {
                val pp = ln.split("=", limit = 2)
                if (pp.size != 2) continue
                when (pp[0].trim()) {
                    "versionCode" -> remote = pp[1].trim().toIntOrNull() ?: 0
                    "versionName" -> rname = pp[1].trim()
                    "apkArm64" -> apk64 = pp[1].trim()
                    "apkArmv7a" -> apkv7 = pp[1].trim()
                    "apkUniversal" -> apkUni = pp[1].trim()
                }
            }
            if (remote <= vc || remote <= 0) return true
            val has64 = (Build.SUPPORTED_ABIS ?: arrayOf<String>())
                .any { it.contains("arm64") }
            val base = when {
                has64 && apk64.isNotEmpty() -> apk64
                !has64 && apkv7.isNotEmpty() -> apkv7
                else -> apkUni.ifEmpty { apk64 }
            }
            val baseUrl = base.ifEmpty {
                "https://github.com/amirwolf5122/Manga-AutoTranslate" +
                        "/releases/download/apk/" +
                        (if (has64) "MangaTranslator-arm64.apk"
                         else "MangaTranslator-universal.apk")
            }
            if (baseUrl.isEmpty()) return true
            prefs.edit().putString("apk_url_" + remote, baseUrl).apply()
            ui.post {
                updVerName = rname
                updVerCode = remote
                val dst = updDstFile()
                val exp = updExpectedSize()
                val okFile = dst.isFile && dst.length() > 1_000_000L &&
                        (exp <= 0L || dst.length() == exp)
                if (!okFile && dst.isFile) dst.delete()
                cleanOldUpdateApks(remote)
                showUpdateRow()
            }
            return true
        } catch (_: Exception) {
            return false
        }
    }

    @Volatile
    private var lastUpdCheckAt: Long = 0L

    private fun checkAppUpdateWithRetry() {
        var attempt = 0
        while (attempt < 3) {
            if (checkAppUpdate()) return
            if (isFinishing || isDestroyed) return
            attempt += 1
            try {
                Thread.sleep(if (attempt == 1) 20_000L else 40_000L)
            } catch (_: InterruptedException) {
                return
            }
        }
    }

    private fun showUpdateRow() {
        if (updRow != null) {
            updateUpdRowUi()
            return
        }
        val row = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = rounded(Color.parseColor("#1d2b1d"), 14, 1,
                Color.parseColor("#3f7f3f"))
            setPadding(dp(14), dp(8), dp(14), dp(8))
        }
        val l1 = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        val status = TextView(this).apply {
            setTextColor(TXT); textSize = 14f
        }
        l1.addView(status, LinearLayout.LayoutParams(
            0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        val btn = Button(this).apply {
            setTextColor(Color.WHITE); textSize = 14f
            typeface = Typeface.DEFAULT_BOLD
            background = gradBtn()
            setPadding(dp(18), dp(6), dp(18), dp(6))
        }
        l1.addView(btn)
        row.addView(l1, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT))
        val bar = android.widget.ProgressBar(
            this, null, android.R.attr.progressBarStyleHorizontal).apply {
            max = 1000
            progress = 0
            visibility = View.GONE
        }
        row.addView(bar, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT).apply { topMargin = dp(6) })
        (runBtn.parent as? ViewGroup)?.addView(
            row,
            LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT).apply { topMargin = dp(8) })
        updRow = row
        updStatus = status
        updBar = bar
        updBtn = btn
        btn.setOnClickListener { onUpdButton() }
        updateUpdRowUi()
    }

    private fun updateUpdRowUi() {
        val st = updStatus ?: return
        val btn = updBtn
        val bar = updBar
        val dst = updDstFile()
        val exp = updExpectedSize()
        val okFile = dst.isFile && dst.length() > 1_000_000L &&
                (exp <= 0L || dst.length() == exp)
        when (updState) {
            "dl" -> {
                st.text = "⏳ دانلودِ آپدیتِ v" + updVerName + " …"
                btn?.visibility = View.GONE
                bar?.visibility = View.VISIBLE
            }
            "fail" -> {
                val part = updPartFile()
                val pct = if (exp > 0)
                    (part.length() * 100 / exp).toInt().coerceIn(0, 99) else 0
                st.text = ("⚠ اینترنت قطع شد — v" + updVerName +
                        (" (٪" + pct + " گرفته شده)") +
                        " — دوباره بزن تا از همان‌جا ادامه بدهد")
                btn?.visibility = View.VISIBLE
                btn?.text = "ادامه"
                bar?.visibility = View.GONE
            }
            else -> {
                bar?.visibility = View.GONE
                btn?.visibility = View.VISIBLE
                if (okFile) {
                    st.text = "🔄 آپدیتِ جدید v" + updVerName + " — آمادهٔ نصب"
                    btn?.text = "نصب"
                } else {
                    st.text = "🔄 آپدیتِ جدید v" + updVerName +
                            " — فایلِ نصبی دانلود شود؟"
                    btn?.text = "⬇ دانلود و نصب"
                }
            }
        }
    }

    private fun onUpdButton() {
        if (updState == "dl") return
        val dst = updDstFile()
        val exp = updExpectedSize()
        val okFile = dst.isFile && dst.length() > 1_000_000L &&
                (exp <= 0L || dst.length() == exp)
        if (okFile) {
            installUpdate(dst)
            return
        }
        val url = prefs.getString("apk_url_" + updVerCode, null)
        if (url.isNullOrEmpty()) return
        updState = "dl"
        updateUpdRowUi()
        updThread = Thread { downloadApkResumable(url) }.apply { start() }
    }

    private fun fmtMB(b: Long): String =
        String.format(java.util.Locale.US, "%.1f", b / 1048576.0)

    private fun downloadApkResumable(url: String) {
        val dst = updDstFile()
        val part = updPartFile()
        var lastEx: Exception? = null
        var ok = false
        for (u in listOf(url, "https://gh-proxy.com/" + url)) {
            try {
                var done = false
                while (!done) {
                    val already = if (part.isFile) part.length() else 0L
                    val c = java.net.URL(u).openConnection()
                        as java.net.HttpURLConnection
                    c.connectTimeout = 15000
                    c.readTimeout = 30000
                    c.instanceFollowRedirects = true
                    c.setRequestProperty("User-Agent", "Mozilla/5.0")
                    if (already > 0L)
                        c.setRequestProperty("Range", "bytes=" + already + "-")
                    try {
                        c.connect()
                        if (c.responseCode / 100 != 2)
                            throw RuntimeException("HTTP " + c.responseCode)
                        val total: Long = if (c.responseCode == 206) {
                            val cr = c.getHeaderField("Content-Range") ?: ""
                            val mm = Regex("/(\\d+)\\s*$").find(cr)
                            mm?.groupValues?.get(1)?.toLongOrNull()
                                ?: (already +
                                    (c.getHeaderField("Content-Length")
                                        ?.toLongOrNull() ?: 0L))
                        } else {
                            c.getHeaderField("Content-Length")?.toLongOrNull()
                                ?: 0L
                        }
                        if (total > 0L) {
                            if (updExpectedSize() != total)
                                prefs.edit().putLong(
                                    "apk_size_" + updVerCode, total).apply()
                            if (already > total) {
                                part.delete()
                                continue
                            }
                        }
                        if (total > 0L && already == total && already > 1_000_000L) {
                            done = true
                            break
                        }
                        c.inputStream.use { ins ->
                            java.io.FileOutputStream(part, true).use { fo ->
                                val buf = ByteArray(65536)
                                var lastUi = 0L
                                while (true) {
                                    if (Thread.currentThread().isInterrupted)
                                        throw RuntimeException("لغو")
                                    val n = ins.read(buf)
                                    if (n < 0) break
                                    fo.write(buf, 0, n)
                                    val now = SystemClock.elapsedRealtime()
                                    if (now - lastUi > 400) {
                                        lastUi = now
                                        val got = part.length()
                                        val pct = if (total > 0)
                                            (got * 1000 / total).toInt()
                                                .coerceIn(0, 999) else -1
                                        ui.post {
                                            updBar?.let { bb ->
                                                if (pct >= 0) {
                                                    bb.isIndeterminate = false
                                                    bb.progress = pct
                                                } else bb.isIndeterminate = true
                                            }
                                            updStatus?.text =
                                                ("⏳ دانلودِ v" + updVerName +
                                                        " — " +
                                                        (if (pct >= 0)
                                                            "٪" + (pct / 10)
                                                        else "") +
                                                        " (" + fmtMB(got) +
                                                        (if (total > 0)
                                                            "/" + fmtMB(total)
                                                        else "") + " MB)")
                                        }
                                    }
                                }
                            }
                        }
                        val fsize = part.length()
                        if (total > 0L && fsize < total)
                            throw RuntimeException("ناتمام: " + fsize + "/" + total)
                        if (fsize < 1_000_000L)
                            throw RuntimeException("APK ناقص: " + fsize)
                        ok = true
                        done = true
                    } finally {
                        c.disconnect()
                    }
                }
                break
            } catch (e: Exception) {
                lastEx = e
            }
        }
        ui.post {
            if (ok) {
                val old = if (dst.isFile) dst else null
                old?.delete()
                if (!part.renameTo(dst)) {
                    part.copyTo(dst, overwrite = true)
                    part.delete()
                }
                updState = "idle"
                updateUpdRowUi()
                installUpdate(dst)
            } else {
                updState = "fail"
                updateUpdRowUi()
            }
        }
    }

    private fun installUpdate(apk: java.io.File) {
        try {
            if (Build.VERSION.SDK_INT >= 26 &&
                !packageManager.canRequestPackageInstalls()) {
                prefs.edit().putString("pending_apk", apk.absolutePath).apply()
                startActivity(
                    Intent(
                        android.provider.Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                        Uri.parse("package:" + packageName)))
                Toast.makeText(this, "اجازهٔ «نصب از منابع ناشناس» را بده و برگرد",
                    Toast.LENGTH_LONG).show()
                return
            }
            launchInstall(apk)
        } catch (e: Exception) {
            Toast.makeText(this, "نصب ممکن نشد: " + e.message, Toast.LENGTH_LONG).show()
        }
    }

    private fun launchInstall(apk: java.io.File) {
        val uri = androidx.core.content.FileProvider.getUriForFile(
            this, packageName + ".files", apk)
        val i = Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(uri, "application/vnd.android.package-archive")
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or
                    Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        try {
            startActivity(i)
        } catch (e: Exception) {
            Toast.makeText(this, "نصب‌کننده پیدا نشد: " + e.message,
                Toast.LENGTH_LONG).show()
        }
    }

    private fun copyBundledSources() {
        try {
            val upd = File(filesDir, "updates").apply { mkdirs() }
            val marker = File(upd, ".engine_offline_v3")
            val apkBuild = try {
                @Suppress("DEPRECATION")
                packageManager.getPackageInfo(packageName, 0).versionCode.toString()
            } catch (_: Exception) { "0" }
            if (!marker.exists() || marker.readText().trim() != apkBuild) {
                upd.listFiles()?.forEach { f ->
                    if (f.name.endsWith(".py") || f.name.startsWith(".ver_") ||
                        f.name.endsWith(".new")) f.delete()
                }
                marker.writeText(apkBuild)
                android.util.Log.i("MangaApp", "engine reset → bundled copy (apk build $apkBuild)")
            }
            val names = assets.list("engine") ?: return
            for (name in names) {
                if (!name.endsWith(".py")) continue
                val dst = File(upd, name)
                val assetVer = verOf {
                    assets.open("engine/" + name).use { i ->
                        val b = ByteArray(8192)
                        val n = i.read(b)
                        String(b, 0, if (n > 0) n else 0, Charsets.UTF_8)
                    }
                }
                val diskVer = verOf { if (dst.exists()) dst.readText() else "" }
                val stampVer = try {
                    val sv = File(upd, ".ver_" + name)
                    if (sv.exists()) sv.readText().trim() else "0"
                } catch (_: Exception) { "0" }
                val broken = dst.exists() && dst.length() < 1000L
                val effDisk = if (verCmp(stampVer, diskVer) > 0) stampVer else diskVer
                val cmp = verCmp(assetVer, effDisk)
                val differs = dst.exists() && !broken && md5Of(dst) != md5Of(assets, "engine/" + name)
                if (!dst.exists() || broken || cmp > 0 || (cmp == 0 && differs)) {
                    assets.open("engine/" + name).use { i ->
                        java.io.FileOutputStream(dst).use { o -> i.copyTo(o) }
                    }
                    File(upd, ".ver_" + name).writeText(assetVer)
                    android.util.Log.i("MangaApp", "bundled source copied: " + name)
                }
            }
        } catch (e: Exception) {
            android.util.Log.e("MangaApp", "copyBundledSources failed", e)
        }
    }

    private fun verOf(src: () -> String): String = try {
        Regex("""APP_VER\s*=\s*"([^"]+)"""").find(src())?.groupValues?.get(1) ?: "0"

    } catch (e: Exception) { "0" }

    private fun md5Of(f: File): String = try {
        val md = java.security.MessageDigest.getInstance("MD5")
        f.inputStream().use { i ->
            val b = ByteArray(65536)
            while (true) {
                val n = i.read(b)
                if (n <= 0) break
                md.update(b, 0, n)
            }
        }
        md.digest().joinToString("") { "%02x".format(it) }
    } catch (_: Exception) { "" }

    private fun md5Of(am: android.content.res.AssetManager, path: String): String = try {
        val md = java.security.MessageDigest.getInstance("MD5")
        am.open(path).use { i ->
            val b = ByteArray(65536)
            while (true) {
                val n = i.read(b)
                if (n <= 0) break
                md.update(b, 0, n)
            }
        }
        md.digest().joinToString("") { "%02x".format(it) }
    } catch (_: Exception) { "" }

    private fun verCmp(a: String, b: String): Int {
        val pa = a.split(".").map { it.toIntOrNull() ?: 0 }.toMutableList()
        val pb = b.split(".").map { it.toIntOrNull() ?: 0 }.toMutableList()
        while (pa.size < pb.size) pa.add(0)
        while (pb.size < pa.size) pb.add(0)
        for (i in pa.indices) {
            if (pa[i] != pb[i]) return if (pa[i] > pb[i]) 1 else -1
        }
        return 0
    }

    private fun header(): View {
        val row = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            layoutDirection = View.LAYOUT_DIRECTION_LTR
            gravity = Gravity.CENTER_VERTICAL
            background = rounded(Color.parseColor("#101014"), 18, 1)
            setPadding(dp(16), dp(14), dp(16), dp(14))
        }
        val col = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            layoutDirection = View.LAYOUT_DIRECTION_RTL
            gravity = Gravity.RIGHT
            setPadding(0, 0, dp(12), 0)
        }
        col.addView(TextView(this).apply {
            text = "مانگا مترجم"
            setTextColor(TXT); textSize = 19f; typeface = Typeface.DEFAULT_BOLD
            gravity = Gravity.RIGHT
        })
        col.addView(TextView(this).apply {
            text = "ترجمه خودکار مانهوا — اپ اندروید"
            setTextColor(MUT); textSize = 11f; gravity = Gravity.RIGHT
        })
        val stamp = TextView(this).apply {
            text = "漫"
            setTextColor(Color.WHITE); textSize = 26f; typeface = Typeface.DEFAULT_BOLD
            gravity = Gravity.CENTER
            background = gradBtn().apply { cornerRadius = dp(10).toFloat() }
        }
        row.addView(stamp, LinearLayout.LayoutParams(dp(46), dp(46)))
        val spacer = View(this)
        row.addView(spacer, LinearLayout.LayoutParams(0, 1, 1f))
        row.addView(col)
        return row.apply { (layoutParams as? LinearLayout.LayoutParams)?.bottomMargin = dp(8) }
    }

    private fun chips(): View {
        val row = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
            setPadding(0, dp(6), 0, dp(4))
        }
        for (c in listOf("CPU", "Gemini · ChatGPT · Groq", "LaMa-Manga")) {
            row.addView(TextView(this).apply {
                text = c
                setTextColor(MUT); textSize = 10f
                typeface = Typeface.MONOSPACE
                background = rounded(SURF2, 999, 1)
                setPadding(dp(10), dp(4), dp(10), dp(4))
            }, LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT).apply { setMargins(dp(3), 0, dp(3), 0) })
        }
        return row
    }

    private fun footer(): View {
        val box = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding(0, dp(16), 0, dp(8))
        }
        val row = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
        }
        fun pill(txt: String, icon: Int, url: String): View {
            val wrap = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
                background = rounded(SURF2, 999, 1)
                setPadding(dp(12), dp(6), dp(14), dp(6))
                setOnClickListener {
                    if (url.isNotBlank()) {
                        try {
                            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                        } catch (e: Exception) {
                            Toast.makeText(this@MainActivity, "مرورگر باز نشد",
                                Toast.LENGTH_SHORT).show()
                        }
                    }
                }
            }
            wrap.addView(ImageView(this).apply {
                setImageResource(icon)
                setColorFilter(MUT)
            }, LinearLayout.LayoutParams(dp(13), dp(13)))
            wrap.addView(TextView(this).apply {
                text = txt
                setTextColor(MUT); textSize = 11f
                setPadding(dp(6), 0, 0, 0)
            })
            return wrap
        }
        row.addView(pill("سازنده", R.drawable.ic_telegram, "https://t.me/amir_wolf512"),
            LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT).apply { setMargins(dp(4), 0, dp(4), 0) })
        row.addView(pill("سورس", R.drawable.ic_github,
                "https://github.com/amirwolf5122/Manga-AutoTranslate"),
            LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT).apply { setMargins(dp(4), 0, dp(4), 0) })
        row.addView(pill("ریست", android.R.drawable.ic_menu_revert, "").apply {
            setOnClickListener {
                android.app.AlertDialog.Builder(this@MainActivity)
                    .setTitle("ریست کامل تنظیمات؟")
                    .setMessage("همه کلیدها و تنظیمات به حالت اول برمی‌گردند (فونت‌ها حذف نمی‌شوند).")
                    .setPositiveButton("ریست") { _, _ ->
                        prefs.edit().clear().commit()
                        values.clear()
                        pickedFiles.clear()
                        recreate()
                    }
                    .setNegativeButton("بی‌خیال", null)
                    .show()
            }
        }, LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT,
            ViewGroup.LayoutParams.WRAP_CONTENT).apply { setMargins(dp(4), 0, dp(4), 0) })
        box.addView(row)
        box.addView(TextView(this).apply {
            text = "مانگا مترجم PRO · RT-DETR + Gemini · LaMa-Manga · اجرا روی CPU"
            setTextColor(MUT); textSize = 10f
            gravity = Gravity.CENTER
            setPadding(0, dp(8), 0, 0)
        })
        return box
    }

    private fun buildForm() {
        loadingRow.visibility = View.GONE
        try {
            val mf = JSONObject(bridge.callAttr("manifest").toString())
            manifestAppVer = mf.optString("app_ver", "")
            val sections = mf.getJSONArray("sections")
            var step = 0
            for (s in 0 until sections.length()) {
                val sec = sections.getJSONObject(s)
                val card = LinearLayout(this).apply {
                    orientation = LinearLayout.VERTICAL
                    background = rounded(CARD, 18, 1)
                    setPadding(dp(16), dp(12), dp(16), dp(14))
                }
                val lp = LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
                lp.topMargin = dp(10)

                step += 1
                val title = sec.optString("title").replace(Regex("^[۱۲۳۴۵۶ ۰-۹]+\\s*"), "")
                val contentBox = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
                val arrow = TextView(this).apply {
                    text = "▾"; setTextColor(MUT); textSize = 16f; setPadding(dp(8), 0, dp(8), 0)
                }
                val titleRow = LinearLayout(this).apply {
                    orientation = LinearLayout.HORIZONTAL
                    gravity = Gravity.CENTER_VERTICAL
                    setPadding(0, dp(2), 0, dp(8))
                }
                titleRow.addView(TextView(this).apply {
                    text = if (sec.optString("title").contains("تنظیمات")) "⚙" else step.toString()
                    setTextColor(Color.WHITE); textSize = 14f; typeface = Typeface.DEFAULT_BOLD
                    gravity = Gravity.CENTER
                    background = gradBtn().apply { cornerRadius = dp(8).toFloat() }
                }, LinearLayout.LayoutParams(dp(27), dp(27)))
                titleRow.addView(TextView(this).apply {
                    text = title
                    setTextColor(TXT); textSize = 15.5f; typeface = Typeface.DEFAULT_BOLD
                    setPadding(dp(9), 0, 0, 0)
                })
                val spacer = View(this)
                titleRow.addView(spacer, LinearLayout.LayoutParams(0, 1, 1f))
                titleRow.addView(arrow)
                titleRow.setOnClickListener {
                    val open = contentBox.visibility == View.VISIBLE
                    contentBox.visibility = if (open) View.GONE else View.VISIBLE
                    arrow.text = if (open) "▸" else "▾"
                }
                card.addView(titleRow)
                card.addView(contentBox)

                val openDefault = step <= 3
                contentBox.visibility = if (openDefault) View.VISIBLE else View.GONE
                arrow.text = if (openDefault) "▾" else "▸"

                val fields = sec.getJSONArray("fields")
                if (title.contains("بکاپ") || title.contains("پشتیبان")) {
                    addBackupSection(contentBox)
                } else {
                    var modeGrid: LinearLayout? = null
                    var modeCells = 0
                    for (i in 0 until fields.length()) {
                        val f = fields.getJSONObject(i)
                        if (modeGridIds.contains(f.optString("id"))) {
                            if (modeGrid == null) {
                                modeGrid = LinearLayout(this).apply {
                                    orientation = LinearLayout.VERTICAL
                                    layoutDirection = View.LAYOUT_DIRECTION_RTL
                                }
                                contentBox.addView(modeGrid, LinearLayout.LayoutParams(
                                    ViewGroup.LayoutParams.MATCH_PARENT,
                                    ViewGroup.LayoutParams.WRAP_CONTENT).apply {
                                    topMargin = dp(2); bottomMargin = dp(6)
                                })
                            }
                            addModeCell(modeGrid!!, f, modeCells)
                            modeCells++
                            continue
                        }
                        addField(contentBox, f)
                    }
                    flushPendingTest(contentBox)
                }
                formBox.addView(card, lp)
            }
            formReady = true
            refreshProviderBtn()
        } catch (e: Exception) {
            loadingRow.visibility = View.GONE
            setLog("❌ ساخت فرم:\n" + (e.message ?: e.toString()))
        }
    }

    private fun installCrashLogger() {
        val prev = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { t, e ->
            try {
                val sw = java.io.StringWriter()
                e.printStackTrace(java.io.PrintWriter(sw))
                appendCrashLog("—— کرشِ Java ——\nزمان: " + nowStr() +
                        "\nدستگاه: " + devLine() +
                        "\nthread: " + t.name + "\n" + sw.toString())
            } catch (_: Exception) {
            }
            prev?.uncaughtException(t, e)
        }
    }

    private fun cleanOldUpdateApks(keepVerCode: Int) {
        try {
            val dirs = listOfNotNull(getExternalFilesDir(null), filesDir)
            for (d in dirs) {
                val fs = d.listFiles() ?: continue
                for (f in fs) {
                    val n = f.name
                    val vc = when {
                        n.startsWith("update_") && n.endsWith(".apk.part") ->
                            n.removePrefix("update_")
                                .removeSuffix(".apk.part").toIntOrNull()
                        n.startsWith("update_") && n.endsWith(".apk") ->
                            n.removePrefix("update_")
                                .removeSuffix(".apk").toIntOrNull()
                        else -> null
                    }
                    if (vc != null && vc != keepVerCode) f.delete()
                }
            }
            for (k in prefs.all.keys.toList()) {
                val m = Regex("^(apk_url_|apk_size_)(\\d+)$").find(k)
                if (m != null &&
                    (m.groupValues[2].toIntOrNull() ?: 0) != keepVerCode) {
                    prefs.edit().remove(k).apply()
                }
            }
        } catch (e: Exception) {
            android.util.Log.e("MangaApp", "cleanOldUpdateApks", e)
        }
    }

    private fun clearOldCaches() {
        try {
            File(filesDir, "work").deleteRecursively()
            cacheDir.listFiles()?.forEach {
                if (it.name.startsWith("pick_")) it.delete()
            }
            cleanOldUpdateApks(installedVersionCode())
        } catch (e: Exception) {
            android.util.Log.e("MangaApp", "clearOldCaches", e)
        }
    }

    private fun providerItems(): List<Pair<String, String>> {
        val out = ArrayList<Pair<String, String>>()
        val models = cmLoad()
        if (models.isNotEmpty()) out.add("auto" to "auto")
        out.add("gemini" to "gemini")
        for (m in models) {
            val nm = m.optString("name").trim()
            if (nm.isNotEmpty() && out.none { it.second == nm }) out.add(nm to nm)
        }
        out.add("custom" to "custom")
        return out
    }

    private fun refreshProviderBtn() {
        val btn = providerBtn ?: return
        cmEditing = false
        val id = providerFieldId
        val items = providerItems()
        var cur = (values[id] ?: prefs.getString(id, null))?.toString()?.trim() ?: ""
        if (cur.isEmpty() || items.none { it.second == cur }) {
            cur = if (cmLoad().isNotEmpty()) "auto" else "gemini"
        }
        bankFields(cur)
        values[id] = cur
        prefs.edit().putString(id, cur).apply()
        val nm = items.firstOrNull { it.second == cur }?.first ?: cur
        btn.text = "$nm  ▾"
        refreshCmDelBtn()
        applyProviderGate()
    }

    private fun addProviderField(row: LinearLayout, lbl: String, info: String, id: String) {
        providerFieldId = id
        val prow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        val btn = Button(this).apply {
            setTextColor(TXT); textSize = 14f
            background = rounded(CARD2, 10, 1)
            gravity = Gravity.START or Gravity.CENTER_VERTICAL
            setPadding(dp(12), dp(11), dp(12), dp(11))
            stateListAnimator = null
        }
        providerBtn = btn
        btn.setOnClickListener {
            val items = providerItems()
            AlertDialog.Builder(this)
                .setTitle(lbl)
                .setItems(items.map { it.first }.toTypedArray()) { _, w ->
                    saveVal(id, items[w].second)
                    refreshProviderBtn()
                }.show()
        }
        prow.addView(btn, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        val tok = Button(this).apply {
            text = "↗"
            setTextColor(Color.parseColor("#ffd28a")); textSize = 13f
            background = rounded(Color.TRANSPARENT, 999, 1,
                Color.parseColor("#66ffd28a"))
            setPadding(dp(10), dp(2), dp(10), dp(2))
            stateListAnimator = null
            minWidth = 0
            minimumWidth = 0
        }
        tok.setOnClickListener { openTokenSite() }
        prow.addView(tok, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.WRAP_CONTENT,
            ViewGroup.LayoutParams.WRAP_CONTENT).apply { marginStart = dp(6) })
        val del = Button(this).apply {
            text = "✖"
            setTextColor(Color.parseColor("#ff7b7b")); textSize = 13f
            background = rounded(Color.TRANSPARENT, 999, 1,
                Color.parseColor("#66ff5a5a"))
            setPadding(dp(10), dp(2), dp(10), dp(2))
            stateListAnimator = null
            minWidth = 0
            minimumWidth = 0
        }
        del.setOnClickListener {
            val cur = (values[id] ?: prefs.getString(id, null))?.toString()?.trim() ?: ""
            if (cur.isEmpty()) return@setOnClickListener
            val newList = cmLoad().filter { it.optString("name") != cur }
            cmSave(newList)
            saveVal(id, if (newList.isNotEmpty()) "auto" else "gemini")
            refreshProviderBtn()
            Toast.makeText(this@MainActivity,
                "مدلِ «$cur» از لیست و منو حذف شد", Toast.LENGTH_SHORT).show()
        }
        cmDelBtn = del
        prow.addView(del, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.WRAP_CONTENT,
            ViewGroup.LayoutParams.WRAP_CONTENT).apply { marginStart = dp(6) })
        row.addView(prow, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT))
        if (info.isNotEmpty()) row.addView(TextView(this).apply {
            text = info; setTextColor(MUT); textSize = 11f
            setPadding(dp(2), dp(3), dp(2), dp(4))
        })
        val infoTv = TextView(this).apply {
            setTextColor(MUT); textSize = 11f
            setPadding(dp(2), dp(3), dp(2), dp(4))
            visibility = View.GONE
        }
        cmInfoTv = infoTv
        row.addView(infoTv)
        refreshProviderBtn()
        fieldViews[id] = btn

        val addBtn = Button(this).apply {
            text = "+ افزودن به لیست مدل‌ها"
            setTextColor(Color.WHITE); textSize = 13.5f
            typeface = Typeface.DEFAULT_BOLD
            background = rounded(Color.parseColor("#101014"), 14, 1,
                Color.parseColor("#3a3a45"))
            setPadding(dp(12), dp(11), dp(12), dp(11))
            stateListAnimator = null
        }
        addBtn.setOnClickListener { onAddModel() }
        cmAddBtn = addBtn
        row.addView(addBtn, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT).apply { topMargin = dp(6) })
        val editBtn = Button(this).apply {
            text = "✎ ویرایش این مدل"
            setTextColor(Color.WHITE); textSize = 13.5f
            typeface = Typeface.DEFAULT_BOLD
            background = rounded(Color.parseColor("#101014"), 14, 1,
                Color.parseColor("#3a3a45"))
            setPadding(dp(12), dp(11), dp(12), dp(11))
            stateListAnimator = null
            visibility = View.GONE
        }
        editBtn.setOnClickListener { onEditModel() }
        cmEditBtn = editBtn
        row.addView(editBtn, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT).apply { topMargin = dp(6) })
        val saveBtn = Button(this).apply {
            text = "💾 ذخیرهٔ ویرایش"
            setTextColor(Color.WHITE); textSize = 13.5f
            typeface = Typeface.DEFAULT_BOLD
            background = rounded(Color.parseColor("#b3261e"), 14, 0)
            setPadding(dp(12), dp(11), dp(12), dp(11))
            stateListAnimator = null
            visibility = View.GONE
        }
        saveBtn.setOnClickListener { onSaveModelEdits() }
        cmSaveBtn = saveBtn
        row.addView(saveBtn, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT).apply { topMargin = dp(6) })
        val hintTv = TextView(this).apply {
            text = ("«+ افزودن» مدلِ فعلیِ صفحه (دامنه/کلید/مدل) را با یک نام در "
                    + "«لیست مدل‌ها» ثبت میکند؛ در حافظهٔ دستگاه میماند، در "
                    + "منوی انتخابِ AI میآید و در بکاپ هم ذخیره میشود. حذفِ "
                    + "مدل = انتخابش در منو و زدنِ ✖ِ کنارِ منو. ویرایشِ مدلِ "
                    + "ذخیرهشده = انتخابش در منو، «✎ ویرایش» و بعد «💾 ذخیرهٔ "
                    + "ویرایش». کلید در فیلد مخفی است — با 👁 دیده میشود. رویِ "
                    + "«auto» "
                    + "فیلدها قفل میشوند — خودش بینِ مدلها انتخاب میکند.")
            setTextColor(MUT); textSize = 11f
            setPadding(dp(2), dp(3), dp(2), dp(4))
        }
        cmHintTv = hintTv
        row.addView(hintTv)
    }

    private fun refreshCmDelBtn() {
        val btn = cmDelBtn ?: return
        val cur = (values[providerFieldId]
            ?: prefs.getString(providerFieldId, null))?.toString()?.trim() ?: ""
        val mine = cmLoad().any { it.optString("name") == cur }
        btn.visibility = if (mine) View.VISIBLE else View.GONE
    }

    private fun openTokenSite() {
        val gem = "https://aistudio.google.com/docs/api-key"
        val cur = (values[providerFieldId]
            ?: prefs.getString(providerFieldId, null))?.toString()?.trim() ?: ""
        var url = gem
        try {
            if (cur == "custom") {
                val b = fieldText("manga_api_base", "api_base").trim()
                url = originOf(b) ?: gem
            } else if (cur.isNotEmpty() && cur != "gemini" && cur != "auto") {
                val m = cmLoad().firstOrNull { it.optString("name") == cur }
                val b = m?.optString("api_base")?.trim() ?: ""
                url = originOf(b) ?: gem
            }
        } catch (e: Exception) {
            url = gem
        }
        try {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
        } catch (e: Exception) {
            Toast.makeText(this, "مرورگر باز نشد — $url",
                Toast.LENGTH_LONG).show()
        }
    }

    private fun originOf(raw: String): String? {
        var s = raw.trim()
        if (s.isEmpty()) return null
        if (!s.startsWith("http://") && !s.startsWith("https://")) s = "https://$s"
        return try {
            val u = java.net.URI(s)
            val sch = u.scheme ?: "https"
            val host = u.host ?: return null
            val dfltPort = if (sch == "https") 443 else 80
            val port = if (u.port > 0 && u.port != dfltPort) ":${u.port}" else ""
            if (host.isBlank()) null else "$sch://$host$port"
        } catch (e: Exception) {
            null
        }
    }

    private fun applyProviderGate() {
        val cur = (values[providerFieldId]
            ?: prefs.getString(providerFieldId, null))?.toString()?.trim() ?: ""
        val onAuto = cur == "auto"
        val isCustom = cur == "custom"
        val mine = cmLoad().any { it.optString("name") == cur }
        val editing = cmEditing && mine
        modelFieldRoot?.visibility =
            if (onAuto || (mine && !editing)) View.GONE else View.VISIBLE
        modelRefBtn?.visibility = if (cur == "gemini") View.VISIBLE else View.GONE
        modelLabelTv?.text = if (cur == "gemini")
            "مدل — Gemini: ↻ فهرستِ مدل‌ها (آفلاین آماده؛ زنده با کلید) | خالی = پیش‌فرض"
        else
            "مدل — شناسهٔ مدل را دستی بنویس | خالی = پیش‌فرض"
        for (id in arrayOf("manga_api_base", "api_base")) {
            val v = fieldViews[id]
            if (v is EditText) {
                (v.parent as? View)?.visibility =
                    if (isCustom || editing) View.VISIBLE else View.GONE
                v.isEnabled = !onAuto
                v.alpha = 1f
            }
        }
        for (id in arrayOf("manga_api_keys", "api_keys", "manga_model", "model")) {
            val v = fieldViews[id]
            if (v is EditText) {
                (v.parent as? View)?.visibility =
                    if (onAuto || (mine && !editing)) View.GONE else View.VISIBLE
                v.isEnabled = !onAuto
                v.alpha = 1f
            }
        }
        cmAddBtn?.visibility = if (isCustom) View.VISIBLE else View.GONE
        cmEditBtn?.visibility = if (mine && !cmEditing) View.VISIBLE else View.GONE
        cmSaveBtn?.visibility = if (editing) View.VISIBLE else View.GONE
        cmHintTv?.visibility = if (isCustom) View.VISIBLE else View.GONE
        refreshCmInfo(cur, mine)
    }

    private fun fetchModelList(et: EditText) {
        val keys = fieldText("manga_api_keys", "api_keys", "keys")
        if (keys.isBlank()) {
            Toast.makeText(this,
                "کلید خالی است — فهرستِ آفلاینِ داخلِ برنامه می‌آید؛ برای فهرستِ زنده کلید API را وارد کن",
                Toast.LENGTH_LONG).show()
        }
        Toast.makeText(this, "در حال گرفتن فهرست مدل‌ها…", Toast.LENGTH_SHORT).show()
        Thread {
            var offline = false
            var models: List<String> = emptyList()
            var err = ""
            var probe = ""
            try {
                val payload = JSONObject().apply {
                    put("provider", "gemini")
                    put("keys", keys)
                    put("api_base", "")
                }
                val r = JSONObject(
                    bridge.callAttr("list_models", payload.toString()).toString())
                if (r.optBoolean("ok")) {
                    val arr = r.optJSONArray("models")
                    offline = r.optBoolean("offline")
                    probe = r.optString("probe")
                    models = (0 until (arr?.length() ?: 0))
                        .mapNotNull { arr?.optString(it) }.filter { it.isNotBlank() }
                } else {
                    err = r.optString("error")
                }
            } catch (e: Exception) {
                err = e.message ?: e.toString()
            }
            val list = models
            val error = err
            val probeNote = probe
            runOnUiThread {
                if (list.isEmpty()) {
                    Toast.makeText(this@MainActivity,
                        "فهرستِ مدلها نیامد" +
                            (if (error.isNotBlank()) " — $error" else "") +
                            " — کلید را با «تست کلیدها / لینک» چک کن یا مدل را دستی بنویس",
                        Toast.LENGTH_LONG).show()
                    return@runOnUiThread
                }
                val picked = LinkedHashSet<String>()
                val curSet = et.text.toString().split(",")
                    .map { it.trim() }.filter { it.isNotBlank() }
                curSet.forEach { if (list.contains(it)) picked.add(it) }
                val names = list.map { m ->
                    (if (picked.contains(m)) "✓ " else "") + m
                }.toTypedArray()
                AlertDialog.Builder(this)
                    .setTitle("مدلها (${list.size})" +
                        (if (offline) " — آفلاین (اتصال/کلید برقرار نشد)" else "") +
                        (if (probeNote.isNotBlank()) " — $probeNote" else "") +
                        " — یکی یا چند مدل (فال‌بکِ خودکار)")
                    .setMultiChoiceItems(names, list.map { picked.contains(it) }.toBooleanArray()) { _, w, isChecked ->
                        val m = list[w]
                        if (isChecked) picked.add(m) else picked.remove(m)
                    }
                    .setPositiveButton("باشه") { _, _ ->
                        et.setText(picked.joinToString(","))
                    }
                    .setNegativeButton("بی‌خیال", null)
                    .show()
            }
        }.start()
    }

    private fun onEditModel() {
        val cur = (values[providerFieldId]
            ?: prefs.getString(providerFieldId, null))?.toString()?.trim() ?: ""
        val m = cmLoad().firstOrNull { it.optString("name") == cur } ?: return
        cmEditing = true
        setFieldFor(arrayOf("manga_api_base", "api_base"), m.optString("api_base"))
        setFieldFor(arrayOf("manga_api_keys", "api_keys"), m.optString("api_key"))
        setFieldFor(arrayOf("manga_model", "model"), m.optString("model"))
        applyProviderGate()
        Toast.makeText(this,
            "ویرایشِ «$cur» — بعد از تغییرها «💾 ذخیرهٔ ویرایش» را بزن",
            Toast.LENGTH_SHORT).show()
    }

    private fun onSaveModelEdits() {
        val cur = (values[providerFieldId]
            ?: prefs.getString(providerFieldId, null))?.toString()?.trim() ?: ""
        if (cur.isEmpty()) return
        val list = cmLoad()
        val idx = list.indexOfFirst { it.optString("name") == cur }
        if (idx < 0) return
        val base = fieldText("manga_api_base", "api_base")
        val key = fieldText("manga_api_keys", "api_keys", "keys")
        val mdl = fieldText("manga_model", "model")
        list[idx] = JSONObject().apply {
            put("name", cur)
            put("api_base", base)
            put("api_key", key)
            put("model", mdl)
        }
        cmSave(list)
        cmEditing = false
        setFieldFor(arrayOf("manga_api_base", "api_base"), "")
        setFieldFor(arrayOf("manga_api_keys", "api_keys"), "")
        setFieldFor(arrayOf("manga_model", "model"), "")
        refreshProviderBtn()
        val linkTxt = if (base.isNotBlank()) " — لینک: $base"
                      else " — لینک: Gemini رسمی"
        Toast.makeText(this, "✅ ویرایشِ «$cur» ذخیره شد$linkTxt",
            Toast.LENGTH_LONG).show()
    }

    private fun fieldText(vararg ids: String): String {
        for (fid in ids) {
            val v = fieldViews[fid]
            if (v is EditText && v.text.isNotBlank()) return v.text.toString().trim()
        }
        for (fid in ids) {
            val s = prefs.getString(fid, null)
            if (!s.isNullOrBlank() && !s.equals("null", true) && !s.equals("undefined", true)) {
                return s.trim()
            }
        }
        return ""
    }

    private fun fieldTextStrict(vararg ids: String): String {
        for (fid in ids) {
            val v = fieldViews[fid]
            if (v is EditText) return v.text.toString().trim()
        }
        return ""
    }

    private fun setFieldFor(ids: Array<String>, value: String) {
        for (fid in ids) {
            val v = fieldViews[fid]
            if (v is EditText) {
                if (v.text.toString() != value) v.setText(value)
                return
            }
        }
    }

    private fun maskKey(k: String): String {
        val s = k.trim()
        if (s.isEmpty()) return ""
        return if (s.length <= 10) s.take(2) + "…" + s.takeLast(2)
        else s.take(6) + "…" + s.takeLast(4)
    }

    private fun bankFields(newProv: String) {
        if (!formReady) return
        val last = prefs.getString("fld_last", "")?.trim() ?: ""
        if (last == newProv) return
        if (last == "gemini" || last == "custom") {
            val o = JSONObject()
            o.put("base", fieldTextStrict("manga_api_base", "api_base"))
            o.put("key", fieldTextStrict("manga_api_keys", "api_keys"))
            o.put("model", fieldTextStrict("manga_model", "model"))
            prefs.edit().putString("fld_$last", o.toString()).apply()
        }
        prefs.edit().putString("fld_last", newProv).apply()
        if (newProv == "gemini" || newProv == "custom") {
            val raw = prefs.getString("fld_$newProv", null)
            if (raw.isNullOrBlank()) return
            val o = try { JSONObject(raw) } catch (e: Exception) { return }
            setFieldFor(arrayOf("manga_api_base", "api_base"), o.optString("base"))
            setFieldFor(arrayOf("manga_api_keys", "api_keys"), o.optString("key"))
            setFieldFor(arrayOf("manga_model", "model"), o.optString("model"))
        }
    }

    private fun refreshCmInfo(cur: String, mine: Boolean) {
        val tv = cmInfoTv ?: return
        if (!mine) { tv.visibility = View.GONE; return }
        val m = cmLoad().firstOrNull { it.optString("name") == cur }
        if (m == null) { tv.visibility = View.GONE; return }
        val base = m.optString("api_base").trim()
        val mdl = m.optString("model").trim()
        val key = maskKey(m.optString("api_key"))
        val sb = StringBuilder("مدلِ ذخیره‌شدهٔ «").append(cur).append("» — لینک: ")
        sb.append(if (base.isNotEmpty()) base else "Gemini رسمی")
        if (mdl.isNotEmpty()) sb.append(" — مدلِ هوش: ").append(mdl)
        if (key.isNotEmpty()) sb.append(" — کلید: ").append(key)
        tv.text = sb.toString()
        tv.visibility = View.VISIBLE
    }

    private fun onAddModel() {
        val base = fieldText("manga_api_base", "api_base")
        val key = fieldText("manga_api_keys", "api_keys", "keys")
        val mdl = fieldText("manga_model", "model")
        if (mdl.isBlank() && base.isBlank()) {
            Toast.makeText(this,
                "اول «مدل» (و برای custom «دامنهٔ API») را پر کن، بعد «+ افزودن» را بزن",
                Toast.LENGTH_LONG).show()
            return
        }
        val input = EditText(this).apply {
            setText(if (mdl.isNotBlank()) mdl else "")
            setTextColor(TXT)
            setHintTextColor(MUT)
            hint = "نامِ مدل (مثلاً Kk)"
            textSize = 14f
            background = rounded(CARD2, 10, 1)
            setPadding(dp(12), dp(11), dp(12), dp(11))
        }
        val wrap = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(8), dp(20), dp(0))
            addView(TextView(this@MainActivity).apply {
                text = "نامِ این مدل در لیست (خالی بگذاری = نامِ خودِ مدل):"
                setTextColor(MUT); textSize = 12f
                setPadding(dp(4), 0, dp(4), dp(6))
            })
            addView(input)
        }
        AlertDialog.Builder(this)
            .setTitle("افزودن به لیست مدل‌ها")
            .setView(wrap)
            .setPositiveButton("افزودن") { _, _ ->
                var nm = input.text.toString().trim()
                if (nm.isEmpty()) nm = mdl
                if (nm.isEmpty()) {
                    Toast.makeText(this, "نامِ مدل خالی ماند — نام بده یا «مدل» را پر کن",
                        Toast.LENGTH_LONG).show()
                    return@setPositiveButton
                }
                val list = cmLoad()
                list.removeAll { it.optString("name") == nm }
                list.add(JSONObject().apply {
                    put("name", nm)
                    put("api_base", base)
                    put("api_key", key)
                    put("model", mdl)
                })
                cmSave(list)
                refreshProviderBtn()
                val linkTxt = if (base.isNotBlank()) " — لینک: $base" else ""
                Toast.makeText(this, "✔ مدلِ «$nm» ذخیره شد$linkTxt",
                    Toast.LENGTH_LONG).show()
            }
            .setNegativeButton("بی‌خیال", null)
            .show()
    }

    private fun backupKeys(): List<String> = listOf(
        "provider", "api_base", "api_keys", "model", "ocr_lang", "out_fmt",
        "quality", "workers", "bubbles", "timeout", "batchw", "maxre",
        "reqdelay", "temp", "top_p", "readord", "clean_method", "two_pass",
        "fake_test", "clean_only", "web_debug", "prompt_mode",
        "prompt_body", "thinking", "safety", "max_tokens", "max_tokens_custom")

    private fun settingIds(k: String): List<String> = when (k) {
        "prompt_body" -> listOf("prompt_preview_body", "manga_prompt_body", "prompt_body")
        "two_pass" -> listOf("manga_cb_twopass", "two_pass", "manga_two_pass")
        "thinking", "deep_thinking" -> listOf("manga_cb_thinking", "thinking", "manga_deep_thinking")
        "safety", "safety_settings" -> listOf("manga_cb_safety", "safety", "manga_safety_settings")
        "fake_test" -> listOf("manga_cb_faketest", "fake_test", "manga_fake_test")
        "clean_only" -> listOf("manga_cb_cleanup", "clean_only", "manga_clean_only")
        "web_debug" -> listOf("manga_cb_debug", "web_debug", "manga_web_debug")
        "max_tokens" -> listOf("manga_max_tokens", "max_tokens")
        "max_tokens_custom" -> listOf("manga_max_tokens_custom", "max_tokens_custom")
        else -> listOf(k, "manga_$k")
    }

    private fun readSetting(k: String): Any? {
        for (kid in settingIds(k)) {
            val view = fieldViews[kid]
            when (view) {
                is EditText -> return view.text.toString()
                is SwitchCompat -> return view.isChecked
                is com.google.android.material.slider.Slider ->
                    return if (view.stepSize % 1.0 != 0.0) view.value.toDouble()
                    else view.value.toInt()
            }
        }
        for (kid in settingIds(k)) {
            (values[kid])?.let { return it.toString() }
        }
        for (kid in settingIds(k)) {
            prefs.getString(kid, null)?.let { if (!it.equals("null", true)) return it }
        }
        return ""
    }

    private fun setBackupStatus(t: String, err: Boolean = false) {
        val st = backupStatusView ?: return
        st.text = t
        st.setTextColor(if (err) Color.parseColor("#ff6b6b") else TXT)
        st.visibility = View.VISIBLE
    }

    private fun doBackup() {
        Thread {
            var cacheFile: File? = null
            try {
                val settings = JSONObject()
                for (k in backupKeys()) {
                    val v = readSetting(k)
                    when (v) {
                        null -> settings.put(k, "")
                        is Boolean -> settings.put(k, v)
                        is Number -> settings.put(k, v)
                        else -> settings.put(k, v.toString())
                    }
                }
                val arr = org.json.JSONArray()
                for (m in cmLoad()) arr.put(m)
                val payload = JSONObject()
                payload.put("_type", "manga_autotranslate_backup")
                payload.put("app_ver", manifestAppVer.ifBlank { installedVersionName() })
                payload.put("exported_at",
                    java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", java.util.Locale.US)
                        .format(java.util.Date()))
                payload.put("custom_models", arr)
                payload.put("settings", settings)
                val f = File(cacheDir, "manga_backup_${stampNow()}.json")
                cacheFile = f
                f.writeText(payload.toString(2))
                val ok = saveAnyToDownloads(f.absolutePath, null, f.name)
                ui.post {
                    if (ok) {
                        setBackupStatus("✅ بکاپ ذخیره شد: Download/manga/${f.name} "
                                + "(${arr.length()} مدل + ${settings.length()} تنظیم)")
                        Toast.makeText(this,
                            "✔ بکاپ ذخیره شد: Download/manga/${f.name}",
                            Toast.LENGTH_LONG).show()
                    } else {
                        setBackupStatus("❌ ذخیرهٔ بکاپ ناموفق بود", true)
                        Toast.makeText(this, "❌ ذخیرهٔ بکاپ ناموفق بود",
                            Toast.LENGTH_LONG).show()
                    }
                }
            } catch (e: Exception) {
                ui.post { setBackupStatus("❌ پشتیبان ناموفق: ${e.message}", true) }
            } finally {
                try { cacheFile?.delete() } catch (_: Exception) {}
            }
        }.start()
    }

    private fun applySetting(k: String, v: Any?) {
        if (v == null || v === JSONObject.NULL) return
        var s = v.toString()
        if (k == "prompt_body") {
            s = s.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\r\n", "\n")
        }
        var view: View? = null
        for (kid in settingIds(k)) {
            view = fieldViews[kid]
            if (view != null) break
        }
        when (view) {
            is EditText -> view.setText(s)
            is SwitchCompat -> {
                view.isChecked = (v is Boolean && v) || s.equals("true", true) || s == "1"
            }
            is com.google.android.material.slider.Slider -> {
                val fv = s.toDoubleOrNull() ?: return
                view.value = fv.toFloat().coerceIn(view.valueFrom, view.valueTo)
            }
            is Button -> {
                values[k] = s
                prefs.edit().putString(k, s).apply()
                val items = selectMaps[k]
                val nm = items?.firstOrNull { it.second == s }?.first ?: s
                view.text = "$nm  ▾"
                if (k == providerFieldId) refreshProviderBtn()
            }
            is ViewGroup -> {
                values[k] = s
                prefs.edit().putString(k, s).apply()
                fun walk(vg: ViewGroup) {
                    for (i in 0 until vg.childCount) {
                        val c = vg.getChildAt(i)
                        if (c is RadioButton) c.isChecked = (c.text.toString() == s)
                        else if (c is ViewGroup) walk(c)
                    }
                }
                walk(view)
            }
            else -> {
                values[k] = s
                prefs.edit().putString(k, s).apply()
            }
        }
    }

    private fun doImport(path: String) {
        try {
            val payload = JSONObject(File(path).readText())
            if (payload.optString("_type") != "manga_autotranslate_backup") {
                setBackupStatus("❌ این فایلِ پشتیبانِ این اپ نیست.", true)
                Toast.makeText(this, "❌ این فایلِ پشتیبانِ این اپ نیست",
                    Toast.LENGTH_LONG).show()
                return
            }
            val st = payload.optJSONObject("settings") ?: JSONObject()
            var n = 0
            for (k in backupKeys()) {
                if (st.has(k) && !st.isNull(k)) {
                    applySetting(k, st.get(k))
                    n++
                }
            }
            val arr = payload.optJSONArray("custom_models")
            val list = mutableListOf<JSONObject>()
            if (arr != null) {
                for (i in 0 until arr.length()) {
                    val o = arr.optJSONObject(i) ?: continue
                    val nm = o.optString("name").trim()
                    if (nm.isEmpty()) continue
                    list.add(JSONObject().apply {
                        put("name", nm)
                        put("api_base", o.optString("api_base").trim())
                        put("api_key", o.optString("api_key").trim())
                        put("model", o.optString("model").trim())
                    })
                }
            }
            cmSave(list)
            refreshProviderBtn()
            setBackupStatus("✅ بازیابیِ کامل شد: ${list.size} مدل + $n تنظیم (از فایلِ بکاپ).")
            Toast.makeText(this,
                "✅ بازیابی کامل شد: ${list.size} مدل + $n تنظیم", Toast.LENGTH_LONG).show()
        } catch (e: Exception) {
            setBackupStatus("❌ بازیابی ناموفق: ${e.message}", true)
            Toast.makeText(this, "❌ بازیابی ناموفق: ${e.message}", Toast.LENGTH_LONG).show()
        }
    }

    private fun addBackupSection(box: LinearLayout) {
        box.addView(TextView(this).apply {
            text = ("«گرفتن بکاپ» همه‌چیز (لیستِ مدلها + تمامِ تنظیمات) را با یکِ "
                    + "کلیک در Download/manga ذخیره میکند — بدونِ کلیکِ دوم. "
                    + "«Import» دکمهای هماندازهٔ خودش است (بدونِ باکسِ بزرگ) — فایلِ "
                    + "بکاپ را انتخاب کن تا همه‌چیز کامل برگردد.")
            setTextColor(MUT); textSize = 11.5f
            setPadding(dp(2), dp(2), dp(2), dp(6))
        })
        val backupBtn = Button(this).apply {
            text = "⬇️  گرفتن بکاپ (ذخیرهٔ خودکار JSON)"
            setTextColor(Color.WHITE); textSize = 13.5f; typeface = Typeface.DEFAULT_BOLD
            background = gradBtn()
            setPadding(0, dp(11), 0, dp(11))
            stateListAnimator = null
        }
        backupBtn.setOnClickListener {
            if (!canWritePublic()) {
                requestPermissions(arrayOf(
                    android.Manifest.permission.WRITE_EXTERNAL_STORAGE), REQ_STORAGE)
                Toast.makeText(this, "اول اجازهٔ حافظه را بده، بعد دوباره بزن",
                    Toast.LENGTH_LONG).show()
                return@setOnClickListener
            }
            doBackup()
        }
        box.addView(backupBtn, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT).apply { topMargin = dp(4) })
        val importBtn = Button(this).apply {
            text = "⬆️  Import — بازیابی از فایلِ بکاپ"
            setTextColor(TXT); textSize = 13.5f; typeface = Typeface.DEFAULT_BOLD
            background = rounded(Color.parseColor("#101014"), 14, 1,
                Color.parseColor("#3a3a45"))
            setPadding(0, dp(11), 0, dp(11))
            stateListAnimator = null
        }
        importBtn.setOnClickListener {
            pickerField = "__import_backup__"
            val intent = Intent(Intent.ACTION_GET_CONTENT).apply {
                addCategory(Intent.CATEGORY_OPENABLE)
                type = "*/*"
                putExtra(Intent.EXTRA_MIME_TYPES, arrayOf(
                    "application/json", "text/plain", "application/octet-stream"))
            }
            startActivityForResult(
                Intent.createChooser(intent, "انتخاب فایلِ بکاپ (JSON)"), REQ_IMPORT)
        }
        box.addView(importBtn, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT).apply { topMargin = dp(8) })
        val st = TextView(this).apply {
            setTextColor(MUT); textSize = 12f
            setPadding(dp(2), dp(6), dp(2), dp(2))
            visibility = View.GONE
        }
        backupStatusView = st
        box.addView(st)
    }

    private fun addField(card: LinearLayout, f: JSONObject) {
        val id = f.optString("id")
        val type = f.optString("type")
        val lbl = f.optString("label", "")
        val info = f.optString("info", "")
        val dfltRaw = f.opt("default")
        val dflt: Any? = if (dfltRaw is JSONObject) dfltRaw.opt("default") else dfltRaw

        fun infoView(): TextView? = if (info.isNotEmpty()) TextView(this).apply {
            text = info; setTextColor(MUT); textSize = 11f
            setPadding(dp(2), dp(3), dp(2), dp(4))
        } else null

        val row = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        card.addView(row)
        if (lbl.isNotEmpty() && type != "bool" && type != "slider") row.addView(label(lbl))
        val visIf = f.optJSONObject("visible_if")
        if (visIf != null) {
            val depId = visIf.optString("field")
            val depVal = visIf.optString("equals")
            fun applyVis() {
                val cur = (values[depId] ?: prefs.getString(depId, null))?.toString() ?: ""
                row.visibility =
                    if (cur.equals(depVal, ignoreCase = true)) View.VISIBLE else View.GONE
            }
            applyVis()
            if (depId.isNotBlank()) {
                depListeners.getOrPut(depId) { mutableListOf() }.add { applyVis() }
            }
        }

        when (type) {
            "text", "password", "number" -> {
                                val lines = f.optInt("lines", 1)
                val isSecret = f.optBoolean("password") || type == "password"
                val et = EditText(this).apply {
                    if (lines > 1) {
                        setSingleLine(false)
                        inputType = InputType.TYPE_CLASS_TEXT or
                            InputType.TYPE_TEXT_FLAG_MULTI_LINE or
                            InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS
                        minLines = lines.coerceIn(2, 10)
                        maxLines = 14
                        gravity = Gravity.TOP or Gravity.START
                        setHorizontallyScrolling(false)
                        ellipsize = null
                    } else {
                        setSingleLine(true)
                    }
                    setTextColor(TXT); setHintTextColor(MUT); textSize = 14f
                    background = rounded(CARD2, 10, 1)
                    setPadding(dp(12), dp(11), dp(12), dp(11))
                    if (lines < 2 && (type == "password" || isSecret)) inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
                    if (lines < 2 && type == "number")
                        inputType = InputType.TYPE_CLASS_NUMBER or
                                InputType.TYPE_NUMBER_FLAG_DECIMAL
                    val dfltStr: String = when {
                        dflt == null || dflt === org.json.JSONObject.NULL -> ""
                        else -> {
                            val s = dflt.toString()
                            if (s.equals("null", true) || s.equals("undefined", true)) "" else s
                        }
                    }
                    val saved = savedOr(id, dflt)
                    if (saved is String) {
                        setText(saved.ifBlank { dfltStr })
                    }
                    addTextChangedListener(object : android.text.TextWatcher {
                        override fun afterTextChanged(s: android.text.Editable?) {
                            prefs.edit().putString(id, s?.toString() ?: "").apply()
                        }
                        override fun beforeTextChanged(p0: CharSequence?, p1: Int, p2: Int, p3: Int) {}
                        override fun onTextChanged(p0: CharSequence?, p1: Int, p2: Int, p3: Int) {}
                    })
                }
                f.optJSONObject("value_if")?.let { vi ->
                    val depId = vi.optString("field")
                    val vals = vi.optJSONObject("values")
                    if (depId.isNotBlank() && vals != null && vals.length() > 0) {
                        fun applyValIf(initial: Boolean) {
                            val cur = (values[depId] ?: prefs.getString(depId, null))
                                ?.toString() ?: ""
                            if (!vals.has(cur)) return
                            val mapped = vals.optString(cur)
                            if (mapped.isEmpty()) return
                            val curText = et.text.toString()
                            if (curText == mapped) return
                            if (initial) {
                                var isPreset = false
                                for (k in vals.keys()) {
                                    if (vals.optString(k) == curText) { isPreset = true; break }
                                }
                                if (!(curText.isBlank() || isPreset)) return
                            }
                            et.setText(mapped)
                        }
                        applyValIf(true)
                        depListeners.getOrPut(depId) { mutableListOf() }
                            .add { applyValIf(false) }
                    }
                }
                if (isSecret && lines < 2) {
                    et.transformationMethod =
                        android.text.method.PasswordTransformationMethod.getInstance()
                    val keyRow = LinearLayout(this).apply {
                        orientation = LinearLayout.HORIZONTAL
                        gravity = Gravity.CENTER_VERTICAL
                    }
                    keyRow.addView(et, LinearLayout.LayoutParams(
                        0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
                    val eyeBtn = Button(this).apply {
                        text = "👁"
                        setTextColor(Color.parseColor("#b9b6ad")); textSize = 14f
                        background = rounded(Color.parseColor("#1c1c22"), 10, 1,
                            Color.parseColor("#33333c"))
                        setPadding(dp(10), dp(6), dp(10), dp(6))
                        stateListAnimator = null
                        minWidth = 0; minimumWidth = 0
                    }
                    eyeBtn.setOnClickListener {
                        val hidden = et.transformationMethod != null
                        et.transformationMethod =
                            if (hidden) null
                            else android.text.method.PasswordTransformationMethod.getInstance()
                        eyeBtn.text = if (hidden) "🙈" else "👁"
                        try { et.setSelection(et.text.length) } catch (e: Exception) {}
                    }
                    keyRow.addView(eyeBtn, LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.WRAP_CONTENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT).apply { marginStart = dp(6) })
                    row.addView(keyRow)
                } else if (type == "number" && f.optDouble("step", 0.0) > 0.0) {
                    val stepN = f.optDouble("step", 0.05)
                    val minN = if (f.has("min")) f.optDouble("min", 0.0) else 0.0
                    val maxN = if (f.has("max")) f.optDouble("max", 1.0) else 1.0
                    fun fmtN(v: Double): String {
                        val r = Math.round(v * 100.0) / 100.0
                        return if (r == Math.floor(r)) r.toInt().toString()
                        else String.format(java.util.Locale.US, "%.2f", r)
                            .trimEnd('0').trimEnd('.')
                    }
                    fun curNum(): Double = et.text.toString().trim().toDoubleOrNull()
                        ?: ((dflt as? Number)?.toDouble()
                            ?: dflt?.toString()?.toDoubleOrNull() ?: minN)
                    if (et.text.isBlank()) {
                        et.setText(fmtN(curNum().coerceIn(minN, maxN)))
                    }
                    val numRow = LinearLayout(this).apply {
                        orientation = LinearLayout.HORIZONTAL
                        gravity = Gravity.CENTER_VERTICAL
                    }
                    numRow.addView(et, LinearLayout.LayoutParams(
                        0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
                    fun mkStepBtn(lblTxt: String, delta: Double) = Button(this).apply {
                        text = lblTxt
                        setTextColor(Color.WHITE); textSize = 17f
                        background = rounded(CARD2, 10, 1, ACC)
                        setPadding(dp(16), dp(10), dp(16), dp(10))
                        stateListAnimator = null
                        minWidth = 0; minimumWidth = 0
                        setOnClickListener {
                            val v = Math.round(
                                (curNum() + delta).coerceIn(minN, maxN) * 100.0) / 100.0
                            et.setText(fmtN(v))
                        }
                    }
                    numRow.addView(mkStepBtn("−", -stepN), LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.WRAP_CONTENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT).apply { marginStart = dp(6) })
                    numRow.addView(mkStepBtn("+", stepN), LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.WRAP_CONTENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT).apply { marginStart = dp(6) })
                    row.addView(numRow)
                } else {
                    row.addView(et)
                }
                infoView()?.let { row.addView(it) }
                fieldViews[id] = et
                if (id.lowercase().contains("key")) {

                    val testBtn = Button(this).apply {
                        text = "تست کلیدها / لینک"
                        setTextColor(Color.WHITE); textSize = 13.5f
                        typeface = Typeface.DEFAULT_BOLD
                        background = rounded(Color.parseColor("#101014"), 14, 1,
                                             Color.parseColor("#3a3a45"))
                        setPadding(dp(12), dp(11), dp(12), dp(11))
                        stateListAnimator = null
                    }
                    val testLbl = TextView(this).apply {
                        setTextColor(MUT); textSize = 12f
                        setPadding(dp(2), dp(4), dp(2), dp(2))
                        visibility = View.GONE
                    }
                    testBtn.setOnClickListener {
                        testLbl.text = "در حال تست…"
                        testLbl.setTextColor(MUT)
                        testLbl.visibility = View.VISIBLE
                        testBtn.isEnabled = false
                        Thread {
                            var res: JSONObject? = null
                            var err: String? = null
                            fun settingVal(vararg ids: String): String {
                                for (fid in ids) {
                                    val v = fieldViews[fid]
                                    if (v is EditText && v.text.isNotBlank()) return v.text.toString()
                                }
                                for (fid in ids) {
                                    val s = prefs.getString(fid, null)
                                    if (!s.isNullOrBlank()) return s
                                }
                                return ""
                            }
                            try {
                                val p = JSONObject()
                                val prov = settingVal("provider", "manga_provider")
                                    .ifBlank { "auto" }
                                val keyVal = settingVal("manga_api_keys", "api_keys", "keys")
                                val baseVal = settingVal("manga_api_base", "api_base")
                                val modelVal = settingVal("manga_model", "model")
                                if (prov == "auto" || (prov != "gemini" && prov != "custom")) {
                                    val cm = cmLoad()
                                    val cands = mutableListOf<Array<String>>()
                                    if (prov == "auto") {
                                        cands.add(arrayOf("gemini", "gemini", "", keyVal, modelVal))
                                        for (m in cm) {
                                            cands.add(arrayOf(
                                                m.optString("name").ifBlank { "مدل" },
                                                if (m.optString("api_base").isBlank()) "gemini" else "custom",
                                                m.optString("api_base"),
                                                m.optString("api_key").ifBlank { keyVal },
                                                m.optString("model").ifBlank { modelVal }))
                                        }
                                    } else {
                                        val hit = cm.firstOrNull {
                                            it.optString("name") == prov
                                        }
                                        if (hit != null) {
                                            cands.add(arrayOf(prov,
                                                if (hit.optString("api_base").isBlank()) "gemini" else "custom",
                                                hit.optString("api_base"),
                                                hit.optString("api_key").ifBlank { keyVal },
                                                hit.optString("model").ifBlank { modelVal }))
                                        } else {
                                            cands.add(arrayOf(prov, "gemini", baseVal, keyVal, modelVal))
                                        }
                                    }
                                    val lines = mutableListOf<String>()
                                    var hitIdx = -1
                                    for ((idx, c) in cands.withIndex()) {
                                        try {
                                            val q = JSONObject()
                                            q.put("keys", c[3])
                                            q.put("provider", c[1])
                                            q.put("api_base", c[2])
                                            q.put("model", c[4])
                                            val r = JSONObject(bridge.callAttr(
                                                "test_keys", q.toString()).toString())
                                            val txt = r.optString("text")
                                                .takeIf { it.isNotBlank() && !it.equals("null", true) }
                                            if (txt != null && txt.contains("✔")) {
                                                lines.add("✔ ${c[0]}: در دسترس است")
                                                hitIdx = idx
                                                break
                                            }
                                            val er = r.optString("error")
                                                .takeIf { it.isNotBlank() && !it.equals("null", true) }
                                            lines.add("✘ ${c[0]}: " +
                                                    (er?.take(80) ?: (txt?.take(80) ?: "در دسترس نیست")))
                                        } catch (e: Exception) {
                                            lines.add("✘ ${c[0]}: ${e.message?.take(80) ?: "خطا"}")
                                        }
                                    }
                                    if (hitIdx >= 0) {
                                        lines.add("→ «${cands[hitIdx][0]}» استفاده میشود")
                                    } else if (prov == "auto") {
                                        lines.add("❌ هیچ‌کدام از مدلها در دسترس نبود")
                                    }
                                    res = JSONObject().put("text", lines.joinToString("\n"))
                                } else {
                                    p.put("keys", keyVal)
                                    p.put("provider", prov)
                                    p.put("api_base", baseVal)
                                    p.put("model", modelVal)
                                    res = JSONObject(bridge.callAttr("test_keys", p.toString()).toString())
                                }
                            } catch (e: Exception) {
                                err = e.message ?: e.toString()
                            }
                            runOnUiThread {
                                testBtn.isEnabled = true
                                val okTxt = res?.optString("text")?.takeIf {
                                    it.isNotBlank() && !it.equals("null", true)
                                }
                                val errTxt = res?.optString("error")?.takeIf {
                                    it.isNotBlank() && !it.equals("null", true)
                                }
                                val msg = okTxt
                                    ?: ("خطا: " + (errTxt
                                        ?: (err ?: "خطا")))
                                testLbl.text = msg
                                testLbl.setTextColor(if (okTxt != null) TXT else Color.parseColor("#c62828"))
                                testLbl.visibility = View.VISIBLE

                                testLbl.postDelayed({ testLbl.visibility = View.GONE }, 60000)
                            }
                        }.start()
                    }
                    pendingTestBtn = testBtn
                    pendingTestLbl = testLbl
                }
                if (id.equals("manga_model", true) || id.equals("model", true)) {
                    flushPendingTest(card)
                }
            }
            "select" -> {
                if (id == "provider" || id == "manga_provider") {
                    addProviderField(row, lbl, info, id)
                    return
                }
                if (id.equals("manga_model", true) || id.equals("model", true)) {
                    modelLabelTv = if (lbl.isNotEmpty() && row.childCount > 0 &&
                        row.getChildAt(row.childCount - 1) is TextView)
                        row.getChildAt(row.childCount - 1) as TextView else null
                    val mrow = LinearLayout(this).apply {
                        orientation = LinearLayout.HORIZONTAL
                        gravity = Gravity.CENTER_VERTICAL
                    }
                    val et = EditText(this).apply {
                        setSingleLine(true)
                        setTextColor(TXT); setHintTextColor(MUT); textSize = 14f
                        background = rounded(CARD2, 10, 1)
                        setPadding(dp(12), dp(11), dp(12), dp(11))
                        hint = "چند مدل با کاما = فال‌بکِ خودکار | خالی = پیش‌فرض"
                        val dfltStr: String = when {
                            dflt == null || dflt === org.json.JSONObject.NULL -> ""
                            else -> {
                                val s = dflt.toString()
                                if (s.equals("null", true) || s.equals("undefined", true)) "" else s
                            }
                        }
                        val saved = savedOr(id, dflt)
                        if (saved is String) setText(saved.ifBlank { dfltStr })
                        addTextChangedListener(object : android.text.TextWatcher {
                            override fun afterTextChanged(s: android.text.Editable?) {
                                values[id] = s?.toString() ?: ""
                                prefs.edit().putString(id, s?.toString() ?: "").apply()
                            }
                            override fun beforeTextChanged(p0: CharSequence?, p1: Int, p2: Int, p3: Int) {}
                            override fun onTextChanged(p0: CharSequence?, p1: Int, p2: Int, p3: Int) {}
                        })
                    }
                    mrow.addView(et, LinearLayout.LayoutParams(
                        0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
                    val ref = Button(this).apply {
                        text = "↻"
                        setTextColor(TXT); textSize = 15f
                        background = rounded(CARD2, 10, 1)
                        setPadding(dp(14), dp(9), dp(14), dp(9))
                        stateListAnimator = null
                        minWidth = 0; minimumWidth = 0
                    }
                    ref.setOnClickListener { fetchModelList(et) }
                    mrow.addView(ref, LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.WRAP_CONTENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT).apply { marginStart = dp(6) })
                    row.addView(mrow)
                    infoView()?.let { row.addView(it) }
                    fieldViews[id] = et
                    modelRefBtn = ref
                    modelFieldRoot = row
                    flushPendingTest(card)
                    return
                }
                                val items = ArrayList<Pair<String, String>>()
                f.optJSONArray("choices")?.let { ch ->
                    for (i in 0 until ch.length()) {
                        val c = ch.optJSONArray(i)
                        if (c != null && c.length() >= 2) items.add(Pair(c.optString(0), c.optString(1)))
                        else items.add(Pair(ch.optString(i), ch.optString(i)))
                    }
                }
                val saved = savedOr(id, dflt)?.toString()
                var selected = items.indexOfFirst { it.second == saved }
                if (selected < 0) selected = items.indexOfFirst { it.second == dflt?.toString() }
                fun selText(name: String?): String =
                    (name ?: "— انتخاب —") + "  ▾"
                val btn = Button(this).apply {
                    text = selText(items.getOrNull(selected)?.first)
                    setTextColor(TXT); textSize = 14f
                    background = rounded(CARD2, 10, 1)
                    gravity = Gravity.START or Gravity.CENTER_VERTICAL
                    setPadding(dp(12), dp(11), dp(12), dp(11))
                    stateListAnimator = null
                }
                btn.setOnClickListener {
                    AlertDialog.Builder(this)
                        .setTitle(lbl)
                        .setItems(items.map { it.first }.toTypedArray()) { _, w ->
                            saveVal(id, items[w].second)
                            btn.text = selText(items[w].first)
                        }.show()
                }
                if (selected >= 0) values[id] = items[selected].second
                val tipTxt = modeTips[id]
                if (tipTxt != null) {
                    val hrow = LinearLayout(this).apply {
                        orientation = LinearLayout.HORIZONTAL
                        gravity = Gravity.CENTER_VERTICAL
                        layoutDirection = View.LAYOUT_DIRECTION_RTL
                    }
                    hrow.addView(btn, LinearLayout.LayoutParams(0,
                        ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
                    hrow.addView(tipButton(tipTxt), LinearLayout.LayoutParams(
                        dp(17), dp(17)).apply { marginStart = dp(6) })
                    row.addView(hrow)
                } else {
                    row.addView(btn)
                }
                infoView()?.let { row.addView(it) }
                fieldViews[id] = btn
                selectMaps[id] = items
            }
            "radio" -> {
                                val choices = f.optJSONArray("choices")!!
                val saved = savedOr(id, dflt)?.toString()
                val items = ArrayList<Triple<String, String, RadioButton>>()
                for (i in 0 until choices.length()) {
                    val c = choices.optJSONArray(i)
                    val name = if (c != null) c.optString(0) else choices.optString(i)
                    val value = if (c != null) c.optString(1) else choices.optString(i)
                    items.add(Triple(name, value, RadioButton(this)))
                }

                fun syncRows() {
                    for ((_, v, rb) in items) {
                        rb.isChecked = v == (values[id]?.toString() ?: "")
                        (rb.parent as? LinearLayout)?.background =
                            if (rb.isChecked) rounded(Color.parseColor("#1a1114"), 12, 2, ACC)
                            else rounded(CARD2, 12, 1)
                    }
                }

                fun makeRow(name: String, value: String): LinearLayout {
                    val rb = items.first { it.second == value }.third
                    rb.apply {
                        text = name
                        setTextColor(TXT); textSize = 13f
                        isClickable = false
                        buttonTintList = android.content.res.ColorStateList.valueOf(ACC)
                    }
                    val row = LinearLayout(this@MainActivity).apply {
                        orientation = LinearLayout.HORIZONTAL
                        gravity = Gravity.CENTER_VERTICAL
                        setPadding(dp(12), dp(9), dp(12), dp(9))
                        setOnClickListener {
                            saveVal(id, value)
                            syncRows()
                        }
                    }
                    row.addView(rb)
                    return row
                }

                val listCol = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
                val twoCol = choices.length() > 3
                if (twoCol) {
                    val cols = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
                    val colA = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
                    val colB = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
                    items.forEachIndexed { i, (name, value, _) ->
                        val row = makeRow(name, value)
                        val target = if (i % 2 == 0) colA else colB
                        target.addView(row, LinearLayout.LayoutParams(
                            ViewGroup.LayoutParams.MATCH_PARENT,
                            ViewGroup.LayoutParams.WRAP_CONTENT).apply {
                            setMargins(0, 0, 0, dp(6))
                            if (target === colB) marginStart = dp(6)
                        })
                    }
                    colA.layoutParams = LinearLayout.LayoutParams(0,
                        ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
                    colB.layoutParams = LinearLayout.LayoutParams(0,
                        ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
                    cols.addView(colA); cols.addView(colB)
                    listCol.addView(cols)
                } else {
                    for ((name, value, _) in items) {
                        listCol.addView(makeRow(name, value), LinearLayout.LayoutParams(
                            ViewGroup.LayoutParams.MATCH_PARENT,
                            ViewGroup.LayoutParams.WRAP_CONTENT).apply {
                            setMargins(0, 0, 0, dp(6))
                        })
                    }
                }
                if (values[id] == null) {
                    val v = saved ?: dflt?.toString()
                    val match = items.firstOrNull { it.second == v }
                    if (match != null) saveVal(id, match.second)
                    else if (items.isNotEmpty()) saveVal(id, items[0].second)
                }
                syncRows()
                row.addView(listCol)
                infoView()?.let { row.addView(it) }
                fieldViews[id] = listCol
            }
            "bool" -> {
                val sw = SwitchCompat(this).apply {
                    text = lbl
                    setTextColor(TXT); textSize = 13f
                    setPadding(dp(4), dp(8), dp(4), dp(8))
                    val _svB = savedOr(id, dflt)
                    isChecked = when (_svB) {
                        is Boolean -> _svB
                        is String -> _svB.equals("true", true)
                        else -> (dflt == true)
                    }
                    thumbTintList = android.content.res.ColorStateList.valueOf(ACC)
                    trackTintList = android.content.res.ColorStateList(
                        arrayOf(intArrayOf(android.R.attr.state_checked), intArrayOf()),
                        intArrayOf(ACC, LINE))
                    setOnCheckedChangeListener { _, c -> saveVal(id, c) }
                }
                row.addView(sw)
                infoView()?.let { row.addView(it) }
                fieldViews[id] = sw
            }
            "slider" -> {
                val stepAny = f.opt("step")
                val step = when (stepAny) {
                    is Double -> stepAny
                    is Number -> stepAny.toDouble()
                    else -> 1.0
                }
                val isFloat = step % 1.0 != 0.0
                val minV = f.optDouble("min", 0.0)
                val maxV = f.optDouble("max", 100.0)
                val savedV = savedOr(id, null)?.toString()?.toDoubleOrNull()
                val dfltV = (dflt as? Number)?.toDouble()
                    ?: dflt?.toString()?.toDoubleOrNull() ?: (minV + maxV) / 2
                fun fmt(v: Float): String =
                    if (isFloat) String.format("%.2f", v).trimEnd('0').trimEnd('.')
                    else v.toInt().toString()
                fun apply(v: Float): Float = v.coerceIn(minV.toFloat(), maxV.toFloat())
                    .let { x -> Math.round(x / step.toFloat()) * step.toFloat() }

                val headRow = LinearLayout(this).apply {
                    orientation = LinearLayout.HORIZONTAL
                    gravity = Gravity.CENTER_VERTICAL
                }
                if (lbl.isNotEmpty()) headRow.addView(label(lbl), LinearLayout.LayoutParams(0,
                    ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
                val valBox = TextView(this).apply {
                    text = fmt(apply((savedV ?: dfltV).toFloat()))
                    setTextColor(TXT); textSize = 13f; typeface = Typeface.DEFAULT_BOLD
                    background = rounded(CARD2, 8, 1)
                    setPadding(dp(10), dp(4), dp(10), dp(4))
                }
                headRow.addView(valBox)
                row.addView(headRow)
                val sl = Slider(this).apply {
                    valueFrom = minV.toFloat()
                    valueTo = maxV.toFloat()
                    stepSize = step.toFloat()
                    value = apply((savedV ?: dfltV).toFloat())
                    tag = step.toString()
                    addOnChangeListener { _, v, _ -> valBox.text = fmt(v) }
                    addOnChangeListener { _, vv, fromUser ->
                        if (fromUser) saveVal(id, if (isFloat) vv.toDouble() else vv.toInt())
                    }
                }
                row.addView(sl, LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT))
                infoView()?.let { row.addView(it) }
                fieldViews[id] = sl
            }
            "file" -> {
                val isFontField = id.startsWith("up_") || id == "font_upload"
                val nameView = TextView(this).apply {
                    text = "فایلی انتخاب نشده"
                    setTextColor(MUT); textSize = 11f; setPadding(dp(12), dp(2), dp(12), dp(2))
                }
                val clearBtn = Button(this).apply {
                    text = "✕  لغو"
                    setTextColor(Color.WHITE); textSize = 12f
                    background = rounded(Color.parseColor("#3a1210"), 10, 1, ACC)
                    setPadding(dp(10), dp(11), dp(10), dp(11))
                    stateListAnimator = null
                    visibility = View.GONE
                }
                val btn = Button(this).apply {
                    text = if (isFontField) "⬆  آپلود فونت — کلیک کن"
                           else "⬆  آپلود فایل‌ها (چندتایی) — کلیک کن"
                    setTextColor(MUT); textSize = 13f
                    background = dashed()
                    gravity = Gravity.CENTER
                    setPadding(dp(12), dp(18), dp(12), dp(18))
                    stateListAnimator = null
                }
                btn.setOnClickListener {
                    pickerField = id
                    val intent = Intent(Intent.ACTION_GET_CONTENT).apply {
                        addCategory(Intent.CATEGORY_OPENABLE)
                        setType("*/*")

                        if (!isFontField) putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true)
                    }
                    startActivityForResult(
                        Intent.createChooser(intent,
                            if (isFontField) "انتخاب فونت" else "انتخاب فایل (می‌توانی چندتا بزنی)"),
                        REQ_FILE)
                }

                clearBtn.setOnClickListener {
                    pickedFiles.remove(id)
                    prefs.edit().remove(id + "_path").apply()
                    nameView.text = "فایلی انتخاب نشده"
                    btn.text = if (isFontField) "⬆  آپلود فونت — کلیک کن"
                               else "⬆  آپلود فایل‌ها (چندتایی) — کلیک کن"
                    clearBtn.visibility = View.GONE
                    Toast.makeText(this, "انتخاب فایل لغو شد", Toast.LENGTH_SHORT).show()
                }

                btn.layoutParams = LinearLayout.LayoutParams(
                    0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
                val fileRow = LinearLayout(this).apply {
                    orientation = LinearLayout.HORIZONTAL
                    gravity = Gravity.CENTER_VERTICAL
                }
                fileRow.addView(btn)
                fileRow.addView(clearBtn, LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.WRAP_CONTENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT).apply {
                    marginStart = dp(6)
                })
                row.addView(fileRow)
                row.addView(nameView)
                fieldViews[id] = nameView
                fieldViews[id + "_btn"] = btn
                fieldViews[id + "_clear"] = clearBtn
                val prev = prefs.getString(id + "_path", null)
                if (prev != null && !prev.equals("null", true)) {
                    val kept = prev.split(",").map { it.trim() }
                        .filter { it.isNotBlank() && File(it).isFile() }
                    if (kept.isNotEmpty()) {
                        pickedFiles[id] = kept.joinToString(",")
                        nameView.text = if (kept.size == 1) "✔ ${File(kept[0]).name}"
                                        else "✔ ${kept.size} فایل انتخاب شد"
                        btn.text = if (kept.size == 1) "✓ ${File(kept[0]).name}"
                                   else "✓ ${kept.size} فایل — برای تغییر دوباره کلیک کن"
                        clearBtn.visibility = View.VISIBLE
                    }
                }
            }
            "header" -> row.addView(TextView(this).apply {
                text = lbl; setTextColor(ACC); textSize = 12.5f
                typeface = Typeface.DEFAULT_BOLD; setPadding(0, dp(10), 0, dp(2))
            })
        }
    }

    private fun collect(): JSONObject {
        val o = JSONObject()
        for ((id, v) in fieldViews) {
            when (v) {
                is EditText -> o.put(id, v.text.toString())
                is SwitchCompat -> o.put(id, v.isChecked)
                is Slider -> {
                    val step = (v.tag as? String)?.toDoubleOrNull() ?: 1.0
                    o.put(id, if (step % 1.0 != 0.0) v.value.toDouble() else v.value.toInt())
                }
                else -> if (values[id] != null) o.put(id, values[id].toString())
            }
        }
        for ((id, path) in pickedFiles) o.put(id + "_file", path)
        val map = JSONObject()
        val urlVal = (firstNonEmpty(o, "inp_path", "url") ?: "")
            .takeIf { it.isNotBlank() && !it.equals("null", true) && !it.equals("undefined", true) }
        map.put("src", urlVal
            ?: pickedFiles["inp_upload"] ?: "")
        map.put("file", pickedFiles["inp_upload"] ?: "")
        map.put("provider", firstNonEmpty(o, "provider") ?: "gemini")
        map.put("custom_models", cmJson())
        map.put("keys", firstNonEmpty(o, "manga_api_keys", "api_keys", "keys") ?: "")
        map.put("model", firstNonEmpty(o, "manga_model", "model") ?: "")
        map.put("api_base", firstNonEmpty(o, "manga_api_base", "api_base") ?: "")
        map.put("ocr_lang", firstNonEmpty(o, "manga_ocr_lang", "ocr_lang") ?: "en")
        map.put("ocr_engine", firstNonEmpty(o, "ocr_engine")
            ?: prefs.getString("ocr_engine", null) ?: "")
        map.put("fmt", firstNonEmpty(o, "out_fmt", "fmt") ?: "PDF")
        map.put("quality", optInt(o, "quality", 92))
        map.put("debug", optBool(o, "web_debug", "debug"))
        map.put("fake", optBool(o, "fake_test", "fake"))
        map.put("clean_only", optBool(o, "clean_only"))
        map.put("clean_method", firstNonEmpty(o, "clean_method") ?: "lama-manga")
        map.put("two_pass", optBoolD(o, true, "two_pass"))
        map.put("thinking", optBoolD(o, true, "manga_cb_thinking", "thinking", "deep_thinking"))
        map.put("safety", optBool(o, "manga_cb_safety", "safety", "safety_settings"))
        map.put("max_tokens", firstNonEmpty(o, "manga_max_tokens", "max_tokens") ?: "auto")
        val mtcS = firstNonEmpty(o, "manga_max_tokens_custom", "max_tokens_custom")
        map.put("max_tokens_custom", ((mtcS?.toIntOrNull() ?: 4096)).coerceAtLeast(1024))
        map.put("readord", firstNonEmpty(o, "readord") ?: "rtl")
        map.put("instruction", firstNonEmpty(o, "instruction_text", "instruction") ?: "")
        map.put("prompt_mode", firstNonEmpty(o, "prompt_mode") ?: "professional")
        map.put("prompt_body", firstNonEmpty(o, "prompt_preview_body", "prompt_body") ?: "")

        for (k in listOf("workers", "bubbles", "batchw", "timeout", "maxre", "reqdelay", "temp", "top_p")) {
            if (o.has(k) && !o.isNull(k)) map.put(k, o.get(k))
        }
        for ((id, v) in values) {
            if (v == null) continue
            if (id !in o.keysIteratorAsList()) {
                o.put(id, v.toString())
            }
        }
        for (k in o.keysIteratorAsList()) {
            when {
                k.startsWith("up_") || k == "font_upload" -> map.put(k, o.opt(k))
                k.startsWith("en_") -> map.put(k, o.optBoolean(k, true))
            }
        }
        for ((id, path) in pickedFiles) {
            if (id.startsWith("up_") || id == "font_upload") {
                map.put(id + "_file", path)
            }
        }
        return map
    }

    private fun JSONObject.keysIteratorAsList(): List<String> {
        val out = ArrayList<String>()
        val it = keys()
        while (it.hasNext()) out.add(it.next())
        return out
    }

    private fun firstNonEmpty(o: JSONObject, vararg keys: String): String? {
        for (k in keys) {
            if (o.has(k) && !o.isNull(k)) {
                val s = o.optString(k, "")
                if (s.isNotBlank()) return s
            }
        }
        return null
    }

    private fun optBool(o: JSONObject, vararg keys: String): Boolean =
        keys.firstOrNull { o.has(it) && o.optBoolean(it, false) } != null

    private fun optBoolD(o: JSONObject, d: Boolean, vararg keys: String): Boolean {
        for (k in keys) {
            if (o.has(k) && !o.isNull(k)) return o.optBoolean(k, d)
        }
        return d
    }

    private fun optInt(o: JSONObject, key: String, d: Int): Int = o.optInt(key, d)

    private fun setLog(t: String) {
        logBox.text = t
        if (logFollow) {
            logBox.post { scrollLogToBottom() }
            logBox.postDelayed({ scrollLogToBottom() }, 90)
        }
    }

    private fun scrollLogToBottom() {
        try {
            val l = logBox.layout ?: return
            val bottom = l.getLineBottom(l.lineCount - 1) - logBox.height + dp(8)
            logBox.scrollTo(0, bottom.coerceAtLeast(0))
        } catch (e: Exception) {
        }
    }

    private fun onCancelJob() {

        if (cancelPending) return
        cancelPending = true
        runBtn.isEnabled = false
        runBtn.text = "⏳ در حال توقف…"
        runBtn.background = rounded(Color.parseColor("#241009"), 14, 2, MUT)
        setLog(logBox.text.toString() + "\n⏹ درخواست لغو ثبت شد — توقف فوری…")
        Thread {
            try {
                bridge.callAttr("cancel")
            } catch (_: Exception) {
            }
        }.start()
        Toast.makeText(this, "درخواست لغو ثبت شد — در حال توقف فوری…",
            Toast.LENGTH_SHORT).show()
    }

    private fun onStartJob() {

        if (jobRunning) {
            onCancelJob()
            return
        }
        val p: JSONObject
        try {
            p = collect()
            if ((p.optString("src") ?: "").isBlank() ||
                (p.optString("src") ?: "").equals("null", true)) {
                Toast.makeText(this, "فایل یا لینک ورودی بده", Toast.LENGTH_SHORT).show()
                return
            }
        } catch (e: Exception) {
            setLog("❌ " + (e.message ?: e.toString()))
            finishJobUi()
            return
        }
        Thread {
            var ask = false
            try {
                val r = JSONObject(bridge.callAttr(
                    "trans_sig_check", p.toString(),
                    filesDir.absolutePath).toString())
                ask = r.optBoolean("ask", false)
            } catch (_: Exception) {
            }
            ui.post {
                if (ask) askRetranslate(p) else beginJob(p)
            }
        }.start()
    }

    private fun askRetranslate(p: JSONObject) {
        try {
            AlertDialog.Builder(this)
                .setTitle("مدل یا پرامپتِ ترجمه عوض شده")
                .setMessage("دفعهٔ قبل با مدل/پرامپتِ دیگری روی همین ورودی کار شده است.\nادامه بده یا از اول ترجمه کن؟\n(استخراج و پاکسازی در هر دو حالت از کش می‌ماند)")
                .setPositiveButton("از اول ترجمه کن") { _, _ ->
                    p.put("retranslate", true)
                    beginJob(p)
                }
                .setNegativeButton("ادامه بده") { _, _ ->
                    p.put("retranslate", false)
                    beginJob(p)
                }
                .setNeutralButton("بی‌خیال", null)
                .show()
        } catch (_: Exception) {
            beginJob(p)
        }
    }

    private fun beginJob(p: JSONObject) {
        try {
            maybeAskBatteryExemption()
            jobRunning = true
            cancelPending = false
            logFollow = true
            Thread { deleteAllMangaLogsInDownloads() }.start()

            runBtn.isEnabled = true
            runBtn.text = "⏹  لغو ترجمه"
            runBtn.setTextColor(Color.WHITE)
            runBtn.background = rounded(Color.parseColor("#3a1210"), 14, 2, ACC)
            acquireKeepAwake()
            resultsBox.removeAllViews()
            liveBox.removeAllViews()
            liveBtn = null
            liveImages.clear()
            liveDbgImages.clear()
            liveTotal = 0
            liveDbgTotal = 0
            shownLiveTotal = 0
            shownLiveDbgTotal = 0
            livePush = null
            liveDone = false
            Thread {
                var res: JSONObject? = null
                var err: String? = null
                try {
                    res = JSONObject(bridge.callAttr("start_job", p.toString(),
                        filesDir.absolutePath).toString())
                } catch (e: Exception) {
                    err = e.message ?: e.toString()
                }
                ui.post {
                    try {
                        val r = res
                        if (r != null && r.optBoolean("ok")) {

                            if (cancelPending) {
                                Thread { try { bridge.callAttr("cancel") } catch (_: Exception) {} }.start()
                            }
                            pollLoop()
                        } else {
                            setLog("❌ " + (r?.optString("error", "")?.takeIf {
                                it.isNotBlank() && !it.equals("null", true)
                            }
                                ?: err ?: "خطا"))
                            finishJobUi()
                        }
                    } catch (e: Exception) {
                        setLog("❌ " + (e.message ?: e.toString()))
                        finishJobUi()
                    }
                }
            }.start()
        } catch (e: Exception) {
            setLog("❌ " + (e.message ?: e.toString()))
            finishJobUi()
        }
    }

    private val pollExec = java.util.concurrent.Executors.newSingleThreadExecutor()
    private var lastLogTxt = ""

    private fun finishJobUi() {
        jobRunning = false
        cancelPending = false
        runBtn.isEnabled = true
        runBtn.text = "🚀  شروع ترجمه"
        runBtn.setTextColor(Color.WHITE)
        runBtn.background = gradBtn()
        releaseKeepAwake()
    }

    private fun pollLoop() {
        pollExec.execute {
            var st: JSONObject? = null
            var err: String? = null
            try {
                st = JSONObject(bridge.callAttr("poll").toString())
            } catch (e: Exception) {
                err = e.message ?: e.toString()
            }
            ui.post {
                try {
                    val s = st
                    if (s == null) {
                        setLog("❌ poll: $err")
                        rescueOutputs()
                        finishJobUi()
                        return@post
                    }
                    val lg = s.optString("log", "")
                    if (lg != lastLogTxt) {
                        lastLogTxt = lg
                        setLog(lg)
                    }
                    if (s.optInt("live_total", 0) > 0) liveTotal = s.optInt("live_total")
                    if (s.optInt("live_total_dbg", 0) > 0) liveDbgTotal = s.optInt("live_total_dbg")
                    TranslationService.updateProgress(
                        s.optInt("prog_now", 0), s.optInt("prog_total", 0),
                        s.optString("prog_phase", ""))
                    s.optJSONArray("live_images")?.let { a ->
                        val live = mutableListOf<String>()
                        for (i in 0 until a.length()) live.add(a.optString(i))
                        val liveDbg = mutableListOf<String>()
                        s.optJSONArray("live_debug_images")?.let { b ->
                            for (i in 0 until b.length()) liveDbg.add(b.optString(i))
                        }
                        updateLiveResults(live, liveDbg)
                    }
                    if (s.optBoolean("cancel_requested") && !s.optBoolean("done") &&
                        !cancelPending) {
                        cancelPending = true
                        runBtn.isEnabled = false
                        runBtn.text = "⏳ در حال توقف…"
                    }
                    if (s.optBoolean("done")) {
                        if (s.optBoolean("cancelled")) {
                            setLog(lg + "\n\n⏹ ترجمه لغو شد.")
                        }
                        finishJobUi()
                        liveDone = true
                        livePush?.invoke(0)
                        liveBox.removeAllViews()
                        liveBtn = null
                        showResults(s)
                        autoSaveLog()

                    } else ui.postDelayed({ pollLoop() }, 800)
                } catch (e: Exception) {
                    setLog("❌ poll: " + (e.message ?: e.toString()))
                    rescueOutputs()
                    finishJobUi()
                }
            }
        }
    }

    private fun pdfToImages(pdfPath: String, tag: String, maxPages: Int = 40,
                            maxDim: Int = 3400): List<String> {
        val out = mutableListOf<String>()
        try {
            val dir = java.io.File(cacheDir, "pdfview_$tag")
            dir.deleteRecursively()
            dir.mkdirs()
            try {
                val tok = java.security.MessageDigest.getInstance("MD5")
                    .digest((pdfPath + "#" + java.io.File(pdfPath).lastModified())
                        .toByteArray(Charsets.UTF_8))
                    .joinToString("") { "%02x".format(it) }
                java.io.File(dir, "run.txt").writeText(tok)
            } catch (_: Exception) {}
            val pfd = ParcelFileDescriptor.open(java.io.File(pdfPath),
                ParcelFileDescriptor.MODE_READ_ONLY)
            val renderer = android.graphics.pdf.PdfRenderer(pfd)
            try {
                val n = minOf(renderer.pageCount, maxPages)
                for (i in 0 until n) {
                    if (isFinishing || isDestroyed) break
                    val pg = renderer.openPage(i)
                    try {
                        val pw = pg.width.coerceAtLeast(1)
                        val ph = pg.height.coerceAtLeast(1)
                        val sc = (maxDim.toFloat() /
                                maxOf(pw, ph).toFloat()).coerceIn(0.05f, 3.0f)
                        val w = (pw * sc).toInt().coerceAtLeast(48)
                        val h = (ph * sc).toInt().coerceAtLeast(48)
                        val bmp = Bitmap.createBitmap(w, h,
                            Bitmap.Config.ARGB_8888)
                        bmp.eraseColor(Color.WHITE)
                        pg.render(bmp, null, null,
                            android.graphics.pdf.PdfRenderer.Page
                                .RENDER_MODE_FOR_DISPLAY)
                        val f = java.io.File(dir, "pg_%03d.png".format(i))
                        java.io.FileOutputStream(f).use { fo ->
                            bmp.compress(Bitmap.CompressFormat.PNG, 92, fo)
                        }
                        bmp.recycle()
                        out.add(f.absolutePath)
                    } finally {
                        pg.close()
                    }
                }
            } finally {
                try { renderer.close() } catch (_: Exception) {}
                try { pfd.close() } catch (_: Exception) {}
            }
        } catch (e: Exception) {
            android.util.Log.w("MangaView", "pdfToImages failed", e)
        }
        return out
    }

    private fun resBtn(text: String, primary: Boolean, onClick: () -> Unit): Button =
        Button(this).apply {
            this.text = text
            setTextColor(if (primary) Color.WHITE else TXT)
            textSize = 13.5f
            typeface = Typeface.DEFAULT_BOLD
            background = if (primary) gradBtn() else rounded(SURF2, 12, 1)
            setPadding(0, dp(11), 0, dp(11))
            stateListAnimator = null
            setOnClickListener { onClick() }
        }

    private fun showResults(st: JSONObject) {
        resultsBox.removeAllViews()
        val images = mutableListOf<String>()
        val debug = mutableListOf<String>()
        st.optJSONArray("images")?.let { a -> for (i in 0 until a.length()) images.add(a.optString(i)) }
        st.optJSONArray("debug_images")?.let { a -> for (i in 0 until a.length()) debug.add(a.optString(i)) }
        if (images.isEmpty()) {
            File(filesDir, "work/out/live").listFiles()?.let { fs ->
                for (f in fs) if (f.isFile && IMG_EXT.contains(f.extension.lowercase())) {
                    images.add(f.absolutePath)
                }
            }
        }
        val outFile = st.optString("out_file", "")
        val hasOutFile = outFile.isNotBlank() && File(outFile).isFile()

        val dbgFile = st.optString("debug_out_file", "")
        val hasDbgFile = dbgFile.isNotBlank() && File(dbgFile).isFile()

        if (images.isNotEmpty()) {
            resultsBox.addView(resBtn("📖  نمایش (${images.size} صفحه)", true) {
                viewer(images, live = true, dbgPaths = debug, total = images.size)
            })
        }
        if (images.isEmpty() && hasOutFile &&
            outFile.lowercase().endsWith(".pdf")) {
            resultsBox.addView(resBtn("📖  نمایش خروجی (PDF)", true) {
                Thread {
                    val imgs = pdfToImages(outFile, "main")
                    val dbgImgs = if (debug.isNotEmpty()) debug
                                  else if (hasDbgFile) pdfToImages(dbgFile, "dbg")
                                  else emptyList()
                    ui.post {
                        if (imgs.isNotEmpty()) {
                            viewer(imgs, dbgPaths = dbgImgs,
                                   total = imgs.size)
                        } else {
                            Toast.makeText(this,
                                "نمایش PDF ممکن نشد — از «دانلود خروجی» استفاده کن",
                                Toast.LENGTH_LONG).show()
                        }
                    }
                }.start()
            })
        }
        if (hasOutFile) {
            resultsBox.addView(resBtn("⬇  دانلود خروجی", false) { saveToDownloads(outFile) })
        }
        if (debug.isNotEmpty()) {
            if (hasDbgFile) {
                resultsBox.addView(resBtn("⬇  دانلود دیباگ (یک فایل)", false) {
                    saveToDownloads(dbgFile)
                })
            } else {
                resultsBox.addView(resBtn("⬇  دانلود دیباگ (${debug.size})", false) {
                    saveManyToDownloads(debug, "debug")
                })
            }
        }
        if (images.isEmpty() && debug.isEmpty() && !hasOutFile) {
            val tv = TextView(this).apply {
                text = "برای این اجرا خروجی تصویری ساخته نشد — دلیلش در لاگ بالا آمده."
                setTextColor(MUT); textSize = 12.5f
                gravity = Gravity.CENTER
                setPadding(dp(6), dp(4), dp(6), dp(4))
            }
            resultsBox.addView(tv)
        }

        for (i in 0 until resultsBox.childCount) {
            val lp = resultsBox.getChildAt(i).layoutParams as LinearLayout.LayoutParams
            lp.topMargin = dp(7)
        }
        autoSaveOutputs(images, outFile)
    }

    private fun updateLiveResults(live: List<String>, liveDbg: List<String>) {
        if (live.size == liveImages.size && liveDbg.size == liveDbgImages.size &&
            liveTotal == shownLiveTotal && liveDbgTotal == shownLiveDbgTotal) return
        synchronized(liveImages) {
            liveImages.clear()
            liveImages.addAll(live)
        }
        synchronized(liveDbgImages) {
            liveDbgImages.clear()
            liveDbgImages.addAll(liveDbg)
        }
        if (liveImages.isEmpty() && liveDbgImages.isEmpty() && liveTotal <= 0) return
        shownLiveTotal = liveTotal
        shownLiveDbgTotal = liveDbgTotal
        resultsBox.removeAllViews()
        if (liveImages.isNotEmpty() || liveTotal > 0) {
            var lbl = if (liveTotal > 0) "📖  نمایش (${liveImages.size}/$liveTotal صفحه)"
                      else "📖  نمایش (${liveImages.size} صفحه)"
            if (liveDbgImages.isNotEmpty()) lbl += " · 🔍${liveDbgImages.size}"
            resultsBox.addView(resBtn(lbl, true) {
                viewer(liveImages, live = true, dbgPaths = liveDbgImages,
                       total = maxOf(liveTotal, liveImages.size))
            })
        }
        for (i in 0 until resultsBox.childCount) {
            val lp = resultsBox.getChildAt(i).layoutParams as LinearLayout.LayoutParams
            lp.topMargin = dp(7)
        }
        livePush?.invoke(0)
    }

    private fun rescueOutputs() {
        try {
            val outRoot = File(filesDir, "work/out")
            if (!outRoot.isDirectory) return
            val found = mutableListOf<String>()
            File(outRoot, "live").listFiles()?.let { fs ->
                for (f in fs) if (f.isFile && IMG_EXT.contains(f.extension.lowercase())) {
                    found.add(f.absolutePath)
                }
            }
            if (found.isEmpty()) {
                val skipDirs = setOf("src", "normalized", "stitched")
                outRoot.walkTopDown().forEach { f ->
                    if (!f.isFile) return@forEach
                    if (f.extension.lowercase() !in IMG_EXT) return@forEach
                    if (f.name.contains("debug", ignoreCase = true)) return@forEach
                    val top = f.relativeTo(outRoot).path.replace('\\', '/')
                        .substringBefore('/')
                    if (top in skipDirs) return@forEach
                    found.add(f.absolutePath)
                }
                found.sortWith(compareBy({ it.length }, { it }))
            }
            if (found.isEmpty()) return
            resultsBox.removeAllViews()
            resultsBox.addView(resBtn("📖  نمایش (${found.size} صفحه)", true) {
                viewer(found)
            })
            outRoot.listFiles()?.firstOrNull {
                it.isFile && it.extension.lowercase() == "pdf"
            }?.let {
                resultsBox.addView(resBtn("⬇  دانلود خروجی", false) {
                    saveToDownloads(it.absolutePath)
                })
            }
            val tv = TextView(this).apply {
                text = "پاسخ موتور قطع شد — این صفحه‌ها از پوشهٔ خروجی بازیابی شدند."
                setTextColor(MUT); textSize = 12f
                gravity = Gravity.CENTER
                setPadding(dp(6), dp(4), dp(6), dp(4))
            }
            resultsBox.addView(tv)
        } catch (_: Exception) {}
    }

    private fun viewer(pathsRaw: List<String>, live: Boolean = false,
                       dbg: Boolean = false, dbgPaths: List<String> = emptyList(),
                       total: Int = 0) {
        if (pathsRaw.isEmpty() && total <= 0) return
        val paths: MutableList<String> = java.util.Collections.synchronizedList(
            mutableListOf<String>().apply { addAll(pathsRaw) })
        val dpaths: MutableList<String> = java.util.Collections.synchronizedList(
            mutableListOf<String>().apply { addAll(dbgPaths) })
        if (paths.isEmpty() && dpaths.isEmpty() && total <= 0) return
        val runTok: String = try {
            val dir = File(paths[0]).parentFile
            val rf = File(dir, "run.txt")
            val rt = if (dir != null && rf.isFile)
                rf.readText().trim().filter { it.isLetterOrDigit() }.take(32) else ""
            if (rt.isNotEmpty()) rt
            else {
                val f0 = File(paths[0])
                val src = (dir?.canonicalPath ?: "?") + "#" + f0.name +
                    "#" + f0.lastModified()
                val dg = java.security.MessageDigest.getInstance("MD5")
                    .digest(src.toByteArray(Charsets.UTF_8))
                "f" + dg.joinToString("") { "%02x".format(it) }.substring(0, 15)
            }
        } catch (_: Exception) { stampNow() }

        val imgRx = Regex("/i/(\\d+)(?:\\?.*)?$")
        val dbgRx = Regex("/d/(\\d+)/?$")
        val dbgBaseRx = Regex("/db/(\\d+)/?$")
        val dbgJsonRx = Regex("/dj/(\\d+)/?$")
        val mimeMap = mapOf(
            "png" to "image/png", "jpg" to "image/jpeg", "jpeg" to "image/jpeg",
            "webp" to "image/webp", "bmp" to "image/bmp", "gif" to "image/gif")

        var uiT: org.json.JSONObject? = null
        try {
            val udir = File(paths[0]).parentFile
            val ufile = if (udir != null) java.io.File(udir, "ui_texts.json") else null
            if (ufile != null && ufile.isFile)
                uiT = org.json.JSONObject(ufile.readText().trim())
        } catch (_: Exception) { }
        fun ut(k: String, d: String): String = try {
            val v = uiT?.optString(k, d)
            if (v.isNullOrEmpty()) d else v
        } catch (_: Exception) { d }

        val wv = android.webkit.WebView(this)
        wv.setBackgroundColor(Color.BLACK)
        wv.settings.javaScriptEnabled = true
        wv.settings.domStorageEnabled = true
        wv.settings.useWideViewPort = true
        wv.settings.loadWithOverviewMode = true
        wv.settings.builtInZoomControls = false
        wv.settings.displayZoomControls = false
        wv.settings.allowFileAccess = false
        wv.settings.mediaPlaybackRequiresUserGesture = true

        val title = try {
            val base = File(paths[0]).parentFile?.name?.takeIf { it.isNotBlank() }
                ?: ut("rdr.title_default", "مانهوا")
            val pfx = when {
                dbg && live -> ut("rdr.live_dbg", "🔍 زنده · ")
                dbg -> ut("rdr.live_dbg2", "🔍 ")
                live -> ut("rdr.live", "زنده · ")
                else -> ""
            }
            "$pfx$base"
        } catch (_: Exception) { "مانهوا" }

        val assetHtml = try {
            assets.open("reader.html").bufferedReader().use { it.readText() }
        } catch (_: Exception) { "" }
        if (assetHtml.isBlank()) {
            Toast.makeText(this, ut("rdr.toast_no_reader", "خواننده در دسترس نیست"), Toast.LENGTH_LONG).show()
            return
        }
        val imgs = paths.indices.joinToString("") {
            "<img src=\"i/$it\" loading=\"lazy\" decoding=\"async\" alt=\"\" draggable=\"false\">"
        } + (paths.size until maxOf(paths.size, total)).joinToString("") {
            "<div class=\"ph\"><span class=\"sp\"></span>" + ut("rdr.translating", "در حال ترجمه…") + "</div>"
        }
        var html = assetHtml
            .replace("__TITLE__", title)
            .replace("__IMGS__", imgs)
            .replace("data-act=\"close\"", "data-act=\"close\" hidden")
        html = html.replace(
            "data-ndbg=\"0\"",
            "data-ndbg=\"${dpaths.size}\" data-run=\"$runTok\"")
        try {
            val uj = uiT?.toString()
            if (!uj.isNullOrBlank() && html.contains("</head>"))
                html = html.replaceFirst(
                    "</head>",
                    "<script>window.UI_T=" + uj + ";</script></head>")
        } catch (_: Exception) { }

        wv.loadDataWithBaseURL("https://localhost/$runTok/", html, "text/html", "utf-8", null)

        wv.webViewClient = object : android.webkit.WebViewClient() {
            override fun shouldInterceptRequest(
                view: android.webkit.WebView,
                request: android.webkit.WebResourceRequest,
            ): android.webkit.WebResourceResponse? {
                val dm = dbgRx.find(request.url.toString())
                if (dm != null) {
                    val di = dm.groupValues[1].toIntOrNull() ?: return null
                    if (di < 0 || di >= dpaths.size) return null
                    val df = File(dpaths[di])
                    if (!df.isFile) return null
                    return try {
                        android.webkit.WebResourceResponse(
                            mimeMap[df.extension.lowercase()] ?: "image/png", null,
                            df.inputStream())
                    } catch (_: Exception) { null }
                }
                val bm = dbgBaseRx.find(request.url.toString())
                if (bm != null) {
                    val bi = bm.groupValues[1].toIntOrNull() ?: return null
                    if (bi < 0 || bi >= dpaths.size) return null
                    val df = File(dpaths[bi])
                    val bf = File(df.parentFile ?: File("."),
                        df.nameWithoutExtension.removeSuffix("_debug")
                            + "_base." + df.extension)
                    if (!bf.isFile) return null
                    return try {
                        android.webkit.WebResourceResponse(
                            mimeMap[bf.extension.lowercase()] ?: "image/jpeg", null,
                            bf.inputStream())
                    } catch (_: Exception) { null }
                }
                val jm = dbgJsonRx.find(request.url.toString())
                if (jm != null) {
                    val ji = jm.groupValues[1].toIntOrNull() ?: return null
                    if (ji < 0 || ji >= dpaths.size) return null
                    val df = File(dpaths[ji])
                    val jf = File(df.parentFile ?: File("."),
                        df.nameWithoutExtension + ".json")
                    if (!jf.isFile) return null
                    return try {
                        android.webkit.WebResourceResponse(
                            "application/json", "utf-8", jf.inputStream())
                    } catch (_: Exception) { null }
                }
                if (request.url.toString().contains("/mtimes")) {
                    var mtf: java.io.File? = null
                    try {
                        synchronized(paths) {
                            if (paths.isNotEmpty()) mtf = java.io.File(
                                java.io.File(paths[0]).parentFile, "mtimes.txt")
                        }
                    } catch (_: Exception) {
                    }
                    if (mtf != null && mtf!!.isFile) {
                        return try {
                            android.webkit.WebResourceResponse(
                                "text/plain", "utf-8", mtf!!.inputStream())
                        } catch (_: Exception) {
                            null
                        }
                    }
                    return null
                }
                val m = imgRx.find(request.url.toString()) ?: return null
                val idx = m.groupValues[1].toIntOrNull() ?: return null
                if (idx < 0 || idx >= paths.size) return null
                val f = File(paths[idx])
                if (!f.isFile) return null
                return try {
                    android.webkit.WebResourceResponse(
                        mimeMap[f.extension.lowercase()] ?: "image/png", null,
                        f.inputStream())
                } catch (_: Exception) { null }
            }
        }

        val close = TextView(this).apply {
            text = "✕"; setTextColor(Color.WHITE); textSize = 15f
            gravity = Gravity.CENTER
            background = rounded(Color.parseColor("#88000000"), 999)
        }
        val root = android.widget.FrameLayout(this).apply { setBackgroundColor(Color.BLACK) }
        root.addView(wv, ViewGroup.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))
        root.addView(close, android.widget.FrameLayout.LayoutParams(
            dp(34), dp(34), Gravity.TOP or Gravity.END).apply {
            topMargin = dp(10); marginEnd = dp(10) })

        val dlg = Dialog(this, android.R.style.Theme_Black_NoTitleBar_Fullscreen)
        dlg.setContentView(root)
        dlg.window?.setBackgroundDrawable(ColorDrawable(Color.BLACK))
        dlg.window?.setLayout(ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.MATCH_PARENT)
        close.setOnClickListener { dlg.dismiss() }
        wv.webChromeClient = object : android.webkit.WebChromeClient() {
            override fun onCloseWindow(window: android.webkit.WebView?) {
                dlg.dismiss()
            }
        }
        dlg.setOnDismissListener {
            wv.stopLoading()
            (wv.parent as? ViewGroup)?.removeView(wv)
            wv.destroy()
            if (live) livePush = null
        }
        dlg.show()
        if (live) {
            livePush = { _ ->
                try {
                    val curLive: List<String>
                    val curDbg: List<String>
                    synchronized(liveImages) { curLive = liveImages.toList() }
                    synchronized(liveDbgImages) { curDbg = liveDbgImages.toList() }
                    synchronized(paths) {
                        if (paths.size < curLive.size)
                            for (i in paths.size until curLive.size) paths.add(curLive[i])
                    }
                    synchronized(dpaths) {
                        if (dpaths.size < curDbg.size)
                            for (i in dpaths.size until curDbg.size) dpaths.add(curDbg[i])
                    }
                    wv.evaluateJavascript(
                        "window.__mangaLive && window.__mangaLive(${paths.size}, " +
                            "${liveTotal}, ${dpaths.size}, ${liveDone})", null)
                } catch (_: Exception) {}
            }
            livePush?.invoke(0)
        }
        if (!prefs.getBoolean("viewer_hint_v3", false)) {
            prefs.edit().putBoolean("viewer_hint_v3", true).apply()
            Toast.makeText(this,
                "نمایشگر مثل نسخهٔ وب شد • پینچ یا دبل‌تپ = زوم • دکمه‌های بالای صفحه: بزرگ/کوچک/پهنا",
                Toast.LENGTH_LONG).show()
        }
    }

    private fun stampNow(): String =
        java.text.SimpleDateFormat("yyyyMMdd_HHmmss", java.util.Locale.US)
            .format(java.util.Date())

    private fun canWritePublic(): Boolean =
        Build.VERSION.SDK_INT >= 29 ||
            checkSelfPermission(android.Manifest.permission.WRITE_EXTERNAL_STORAGE) ==
            PackageManager.PERMISSION_GRANTED

    @Suppress("NewApi")
    private fun saveAnyToDownloads(path: String, subDir: String?, niceName: String?): Boolean {
        return try {
            val f = File(path)
            if (!f.isFile) return false
            val name = niceName ?: f.name
            val rel = if (subDir.isNullOrBlank()) "Download/manga/"
                      else "Download/manga/$subDir/"
            if (Build.VERSION.SDK_INT >= 29) {
                val mime = when (f.extension.lowercase()) {
                    "jpg", "jpeg" -> "image/jpeg"
                    "png" -> "image/png"
                    "webp" -> "image/webp"
                    "pdf" -> "application/pdf"
                    "zip" -> "application/zip"
                    "psd" -> "image/vnd.adobe.photoshop"
                    "html" -> "text/html"
                    else -> "application/octet-stream"
                }
                val cv = ContentValues().apply {
                    put(MediaStore.MediaColumns.DISPLAY_NAME, name)
                    put(MediaStore.MediaColumns.MIME_TYPE, mime)
                    put(MediaStore.MediaColumns.RELATIVE_PATH, rel)
                    put(MediaStore.MediaColumns.IS_PENDING, 1)
                }
                val uri = contentResolver.insert(
                    MediaStore.Downloads.EXTERNAL_CONTENT_URI, cv) ?: return false
                try {
                    contentResolver.openOutputStream(uri)?.use { o ->
                        f.inputStream().use { it.copyTo(o) }
                    } ?: return false
                    contentResolver.update(uri, ContentValues().apply {
                        put(MediaStore.MediaColumns.IS_PENDING, 0)
                    }, null, null)
                } catch (e: Exception) {
                    try { contentResolver.delete(uri, null, null) } catch (_: Exception) {}
                    throw e
                }
                true
            } else {
                val dir = File(Environment.getExternalStoragePublicDirectory(
                    Environment.DIRECTORY_DOWNLOADS),
                    if (subDir.isNullOrBlank()) "manga" else "manga/$subDir")
                dir.mkdirs()
                f.copyTo(File(dir, name), overwrite = true)
                true
            }
        } catch (e: Exception) {
            android.util.Log.e("MangaApp", "saveAnyToDownloads", e)
            false
        }
    }

    private fun saveToDownloads(path: String) {
        if (!canWritePublic()) {
            requestPermissions(arrayOf(android.Manifest.permission.WRITE_EXTERNAL_STORAGE),
                REQ_STORAGE)
            Toast.makeText(this, "اول اجازه حافظه را بده، بعد دوباره بزن",
                Toast.LENGTH_LONG).show()
            return
        }
        val f = File(path)
        val ext = f.extension.ifBlank { "bin" }
        Thread {
            val nice = if (f.nameWithoutExtension.isBlank() ||
                        f.name.startsWith("output.")) "manga_${stampNow()}.$ext" else null
            val ok = saveAnyToDownloads(path, null, nice)
            ui.post {
                Toast.makeText(this,
                    if (ok) "✔ ذخیره شد: Download/manga" else "❌ ذخیره نشد: ${f.name}",
                    Toast.LENGTH_LONG).show()
            }
        }.start()
    }

    private fun saveManyToDownloads(paths: List<String>, subPrefix: String) {
        if (!canWritePublic()) {
            requestPermissions(arrayOf(android.Manifest.permission.WRITE_EXTERNAL_STORAGE),
                REQ_STORAGE)
            Toast.makeText(this, "اول اجازه حافظه را بده، بعد دوباره بزن",
                Toast.LENGTH_LONG).show()
            return
        }
        Thread {
            val sub = subPrefix + "_" + stampNow()
            var n = 0
            for (p in paths) if (saveAnyToDownloads(p, sub, null)) n++
            ui.post {
                Toast.makeText(this,
                    if (n > 0) "✔ $n فایل ذخیره شد: Download/manga/$sub" else "❌ ذخیره نشد",
                    Toast.LENGTH_LONG).show()
            }
        }.start()
    }

    private fun logFile(): File = File(filesDir, "manga.log")

    private fun logOldFile(): File = File(filesDir, "manga_old.log")

    private var pendingTestBtn: Button? = null
    private var pendingTestLbl: TextView? = null

    private fun flushPendingTest(card: LinearLayout?) {
        val btn = pendingTestBtn ?: return
        val lbl = pendingTestLbl ?: return
        val ctx = this
        if (card == null) {
            pendingTestBtn = null; pendingTestLbl = null
            return
        }
        val wrap = LinearLayout(ctx).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(2), dp(4), dp(2), dp(2))
        }
        wrap.addView(btn, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT))
        wrap.addView(lbl)
        card.addView(wrap)
        pendingTestBtn = null
        pendingTestLbl = null
    }

    private fun normMangaLogName(dn: String): String? {
        val s = dn.lowercase().trim()
        if (!s.startsWith("manga")) return null
        if (!s.contains(".log") && !s.endsWith(".txt")) return null
        val noDup = s.replace(Regex(" \\(\\d+\\)"), "")
        return if (noDup.startsWith("manga_old")) "manga_old.log" else "manga.log"
    }

    private fun isMangaLogName(dn: String): Boolean = normMangaLogName(dn) != null

    private fun writeLogEntry(uri: Uri, src: File): Boolean {
        var ok = false
        try {
            contentResolver.openOutputStream(uri, "wt")?.use { o ->
                src.inputStream().use { it.copyTo(o) }
                ok = true
            }
        } catch (_: Exception) {
            ok = false
        }
        if (!ok) {
            try { contentResolver.delete(uri, null, null) } catch (_: Exception) {}
            return false
        }
        try {
            contentResolver.update(uri, ContentValues().apply {
                put(MediaStore.MediaColumns.IS_PENDING, 0)
            }, null, null)
        } catch (_: Exception) {
        }
        return true
    }

    private fun deleteAllLogKindRows(kind: String) {
        try {
            val proj = arrayOf(MediaStore.MediaColumns._ID,
                MediaStore.MediaColumns.DISPLAY_NAME,
                MediaStore.MediaColumns.RELATIVE_PATH)
            contentResolver.query(MediaStore.Downloads.EXTERNAL_CONTENT_URI,
                proj, MediaStore.MediaColumns.DISPLAY_NAME + " LIKE ?",
                arrayOf("manga%"), null)?.use { c ->
                    val doomed = ArrayList<Uri>()
                    while (c.moveToNext()) {
                        val id = c.getLong(0)
                        val dn = c.getString(1) ?: continue
                        val rp = try { c.getString(2) ?: "" }
                                catch (_: Exception) { "" }
                        if (rp != "Download/manga/" && rp != "Download/") continue
                        if (normMangaLogName(dn) == kind) {
                            doomed.add(android.content.ContentUris
                                .withAppendedId(
                                    MediaStore.Downloads.EXTERNAL_CONTENT_URI,
                                    id))
                        }
                    }
                    for (u in doomed) try {
                        contentResolver.delete(u, null, null)
                    } catch (_: Exception) {}
                }
        } catch (_: Exception) {
        }
    }

    private fun insertLogEntry(name: String, src: File): Boolean {
        val kind = normMangaLogName(name)
        if (kind != null && Build.VERSION.SDK_INT >= 29) {
            deleteAllLogKindRows(kind)
        }
        val fname = if (name.endsWith(".txt")) name else "$name.txt"
        val uri = contentResolver.insert(
            MediaStore.Downloads.EXTERNAL_CONTENT_URI,
            ContentValues().apply {
                put(MediaStore.MediaColumns.DISPLAY_NAME, fname)
                put(MediaStore.MediaColumns.MIME_TYPE, "text/plain")
                put(MediaStore.MediaColumns.RELATIVE_PATH, "Download/manga/")
                put(MediaStore.MediaColumns.IS_PENDING, 1)
            }) ?: return false
        val ok = writeLogEntry(uri, src)
        if (!ok) {
            try { contentResolver.delete(uri, null, null) }
            catch (_: Exception) {}
        }
        return ok
    }

    private fun upsertLogInDownloads(name: String, src: File): Boolean {
        if (!src.isFile) return false
        val kind = normMangaLogName(name) ?: return false
        if (Build.VERSION.SDK_INT < 29) {
            return try {
                val dir = File(Environment.getExternalStoragePublicDirectory(
                    Environment.DIRECTORY_DOWNLOADS), "manga")
                dir.mkdirs()
                for (f in dir.listFiles() ?: emptyArray()) {
                    if (!f.isFile) continue
                    if (normMangaLogName(f.name) == kind && f.name != name) {
                        try { f.delete() } catch (_: Exception) {}
                    }
                }
                src.copyTo(File(dir, name), overwrite = true)
                true
            } catch (e: Exception) {
                android.util.Log.e("MangaApp", "upsertLogInDownloads", e)
                false
            }
        }
        return try {
            val proj = arrayOf(MediaStore.MediaColumns._ID,
                MediaStore.MediaColumns.DISPLAY_NAME,
                MediaStore.MediaColumns.RELATIVE_PATH)
            data class Row(val id: Long, val dn: String, val rp: String)
            val rows = ArrayList<Row>()
            contentResolver.query(MediaStore.Downloads.EXTERNAL_CONTENT_URI,
                proj, MediaStore.MediaColumns.DISPLAY_NAME + " LIKE ?",
                arrayOf("manga%"), null)?.use { c ->
                    while (c.moveToNext()) {
                        val id = c.getLong(0)
                        val dn = c.getString(1) ?: continue
                        val rp = try {
                            c.getString(2) ?: ""
                        } catch (_: Exception) {
                            ""
                        }
                        rows.add(Row(id, dn, rp))
                    }
                }
            val mine = rows.filter {
                it.rp == "Download/manga/" && normMangaLogName(it.dn) != null
            }
            fun dupNum(dn: String): Int {
                val m = Regex("\\((\\d+)\\)").find(dn) ?: return 0
                return m.groupValues[1].toIntOrNull() ?: 0
            }
            val canon = if (name.endsWith(".txt")) name else "$name.txt"
            val cands = mine.filter { normMangaLogName(it.dn) == kind }
            val main = cands.firstOrNull {
                it.dn.equals(name, ignoreCase = true)
                        || it.dn.equals(canon, ignoreCase = true)
            } ?: cands.sortedByDescending { it.id }
                    .sortedBy { dupNum(it.dn) }
                    .firstOrNull()
            val mainDn: String = main?.dn ?: ""
            var mainUri: Uri? = null
            if (main != null) {
                mainUri = android.content.ContentUris.withAppendedId(
                    MediaStore.Downloads.EXTERNAL_CONTENT_URI, main.id)
            }
            val doomed = ArrayList<Uri>()
            for (r in mine) {
                if (normMangaLogName(r.dn) != kind) continue
                val u = android.content.ContentUris.withAppendedId(
                    MediaStore.Downloads.EXTERNAL_CONTENT_URI, r.id)
                if (u == mainUri) continue
                doomed.add(u)
            }
            var allDeleted = true
            for (u in doomed) try {
                contentResolver.delete(u, null, null)
            } catch (_: Exception) {
                allDeleted = false
            }
            var ok = false
            val target = mainUri
            if (target != null) {
                ok = writeLogEntry(target, src)
                if (!ok) {
                    try { contentResolver.delete(target, null, null) } catch (_: Exception) {}
                }
                if (ok && allDeleted && !mainDn.equals(canon, ignoreCase = true)) {
                    try {
                        contentResolver.update(target, ContentValues().apply {
                            put(MediaStore.MediaColumns.DISPLAY_NAME, canon)
                        }, null, null)
                    } catch (_: Exception) {
                    }
                }
            }
            if (!ok) ok = insertLogEntry(name, src)
            ok
        } catch (e: Exception) {
            android.util.Log.e("MangaApp", "upsertLogInDownloads", e)
            false
        }
    }

    private fun autoSaveLog(manual: Boolean = false) {
        Thread {
            synchronized(this@MainActivity) {
                val cur = upsertLogInDownloads("manga.log", logFile())
                val old = upsertLogInDownloads("manga_old.log", logOldFile())
                cleanupLogDuplicates()
                Thread {
                    try { Thread.sleep(2500) } catch (_: Exception) {}
                    synchronized(this@MainActivity) {
                        cleanupLogDuplicates()
                    }
                }.start()
                ui.post {
                    if (cur || old) {
                        if (manual) Toast.makeText(this,
                            "✔ ذخیره شد: Download/manga/manga.log",
                            Toast.LENGTH_SHORT).show()
                        else Toast.makeText(this,
                            "📋 لاگ کامل ذخیره شد: Download/manga/manga.log",
                            Toast.LENGTH_SHORT).show()
                    } else if (manual) Toast.makeText(this,
                        "❌ لاگی موجود نیست — اول یک ترجمه اجرا کن",
                        Toast.LENGTH_LONG).show()
                }
            }
        }.start()
    }

    private fun deleteAllMangaLogsOnStart() {
        deleteAllMangaLogsInDownloads()
        try { logFile().delete() } catch (_: Exception) {}
        try { logOldFile().delete() } catch (_: Exception) {}
    }

    private fun deleteAllMangaLogsInDownloads() {
        try {
            if (Build.VERSION.SDK_INT >= 29) {
                val proj = arrayOf(MediaStore.MediaColumns._ID,
                    MediaStore.MediaColumns.DISPLAY_NAME,
                    MediaStore.MediaColumns.RELATIVE_PATH)
                val doomed = ArrayList<Uri>()
                contentResolver.query(MediaStore.Downloads.EXTERNAL_CONTENT_URI,
                    proj, MediaStore.MediaColumns.DISPLAY_NAME + " LIKE ?",
                    arrayOf("manga%"), null)?.use { c ->
                    while (c.moveToNext()) {
                        val id = c.getLong(0)
                        val dn = c.getString(1) ?: continue
                        val rp = try { c.getString(2) ?: "" }
                                catch (_: Exception) { "" }
                        if (rp != "Download/manga/" && rp != "Download/") continue
                        if (normMangaLogName(dn) == null) continue
                        doomed.add(android.content.ContentUris.withAppendedId(
                            MediaStore.Downloads.EXTERNAL_CONTENT_URI, id))
                    }
                }
                for (u in doomed) try {
                    contentResolver.delete(u, null, null)
                } catch (_: Exception) {}
            } else {
                val dir = File(Environment.getExternalStoragePublicDirectory(
                    Environment.DIRECTORY_DOWNLOADS), "manga")
                for (f in dir.listFiles() ?: emptyArray()) {
                    if (!f.isFile) continue
                    if (normMangaLogName(f.name) != null) {
                        try { f.delete() } catch (_: Exception) {}
                    }
                }
            }
        } catch (_: Exception) {
        }
    }

    private fun cleanupLogDuplicates() {
        try {
            if (Build.VERSION.SDK_INT >= 29) {
                data class RowL(val id: Long, val uri: Uri,
                                val dn: String, val rp: String)
                val rows = ArrayList<RowL>()
                contentResolver.query(MediaStore.Downloads.EXTERNAL_CONTENT_URI,
                    arrayOf(MediaStore.MediaColumns._ID,
                        MediaStore.MediaColumns.DISPLAY_NAME,
                        MediaStore.MediaColumns.RELATIVE_PATH),
                    MediaStore.MediaColumns.DISPLAY_NAME + " LIKE ?",
                    arrayOf("manga%"), null)?.use { c ->
                        while (c.moveToNext()) {
                            val id = c.getLong(0)
                            val dn = c.getString(1) ?: continue
                            val rp = try { c.getString(2) ?: "" }
                                    catch (_: Exception) { "" }
                            if (rp != "Download/manga/" && rp != "Download/") continue
                            rows.add(RowL(id, android.content.ContentUris
                                .withAppendedId(
                                    MediaStore.Downloads.EXTERNAL_CONTENT_URI,
                                    id), dn, rp))
                        }
                    }
                for (kind in listOf("manga.log", "manga_old.log")) {
                    val mine = rows.filter {
                        normMangaLogName(it.dn) == kind
                    }
                    if (mine.isEmpty()) continue
                    val canon = "$kind.txt"
                    val main = mine.firstOrNull {
                        (it.dn.equals(kind, ignoreCase = true)
                                || it.dn.equals(canon, ignoreCase = true))
                                && it.rp == "Download/manga/"
                    } ?: mine.firstOrNull {
                        it.dn.equals(kind, ignoreCase = true)
                                || it.dn.equals(canon, ignoreCase = true)
                    } ?: mine.sortedByDescending { it.id }.first()
                    for (r in mine) {
                        if (r.id == main.id) continue
                        try { contentResolver.delete(r.uri, null, null)
                        } catch (_: Exception) {}
                    }
                    if (!main.dn.equals(canon, ignoreCase = true)) {
                        try {
                            contentResolver.update(main.uri,
                                ContentValues().apply {
                                    put(MediaStore.MediaColumns.DISPLAY_NAME,
                                        canon)
                                }, null, null)
                        } catch (_: Exception) {}
                    }
                }
            } else {
                val dir = File(Environment.getExternalStoragePublicDirectory(
                    Environment.DIRECTORY_DOWNLOADS), "manga")
                for (f in dir.listFiles() ?: emptyArray()) {
                    if (!f.isFile) continue
                    val k = normMangaLogName(f.name) ?: continue
                    if (!f.name.equals(k, ignoreCase = true)) {
                        try { f.delete() } catch (_: Exception) {}
                    }
                }
            }
        } catch (_: Exception) {
        }
    }

    private fun isLogFamilyName(dn: String): Boolean {
        val s = dn.lowercase().trim()
        if (s.endsWith(".log.txt")) return true
        if (normMangaLogName(s) != null) return true
        return false
    }

    private fun resetLogsOnStart() {
        try {
            if (Build.VERSION.SDK_INT >= 29) {
                val proj = arrayOf(MediaStore.MediaColumns._ID,
                    MediaStore.MediaColumns.DISPLAY_NAME,
                    MediaStore.MediaColumns.RELATIVE_PATH)
                val doomed = ArrayList<Uri>()
                contentResolver.query(MediaStore.Downloads.EXTERNAL_CONTENT_URI,
                    proj, null, null, null)?.use { c ->
                    while (c.moveToNext()) {
                        val id = c.getLong(0)
                        val dn = c.getString(1) ?: continue
                        val rp = try { c.getString(2) ?: "" }
                                catch (_: Exception) { "" }
                        if (rp != "Download/manga/" && rp != "Download/") continue
                        if (!isLogFamilyName(dn)) continue
                        doomed.add(android.content.ContentUris
                            .withAppendedId(
                                MediaStore.Downloads.EXTERNAL_CONTENT_URI, id))
                    }
                }
                for (u in doomed) {
                    try { contentResolver.delete(u, null, null) }
                    catch (_: Exception) {}
                }
            } else {
                for (dir in listOf("manga", "")) {
                    val base = File(Environment.getExternalStoragePublicDirectory(
                        Environment.DIRECTORY_DOWNLOADS), dir)
                    for (f in base.listFiles() ?: emptyArray()) {
                        if (!f.isFile) continue
                        if (!isLogFamilyName(f.name)) continue
                        try { f.delete() } catch (_: Exception) {}
                    }
                }
            }
            val empty = File(filesDir, "_empty_log_tmp")
            try {
                empty.writeText("")
            } catch (_: Exception) {
            }
            if (empty.isFile) {
                try { upsertLogInDownloads("manga.log", empty) }
                catch (_: Exception) {}
                try { upsertLogInDownloads("manga_old.log", empty) }
                catch (_: Exception) {}
                try { empty.delete() } catch (_: Exception) {}
            }
            try {
                val f = logFile()
                if (f.exists()) f.writeText("") else f.writeText("")
                val o = logOldFile()
                if (o.exists()) o.writeText("") else o.writeText("")
            } catch (_: Exception) {
            }
        } catch (_: Exception) {
        }
    }

    private fun autoSaveOutputs(images: List<String>, outFile: String) {
        if (outFile.isBlank() && images.isEmpty()) return
        if (!canWritePublic()) {
            requestPermissions(arrayOf(android.Manifest.permission.WRITE_EXTERNAL_STORAGE),
                REQ_STORAGE)
            Toast.makeText(this,
                "خروجی در Download/manga ذخیره نشد — اجازه حافظه لازم است",
                Toast.LENGTH_LONG).show()
            return
        }
        Thread {
            try {
                var n = 0
                val f = File(outFile)
                if (f.isFile) {
                    val nice = if (f.nameWithoutExtension.isBlank() ||
                                f.name.startsWith("output."))
                        "manga_${stampNow()}." + f.extension.ifBlank { "bin" } else null
                    if (saveAnyToDownloads(outFile, null, nice)) n++
                }
                ui.post {
                    if (n > 0) Toast.makeText(this,
                        "📥 $n فایل ذخیره شد در Download/manga", Toast.LENGTH_LONG).show()
                }
            } catch (e: Exception) {
                ui.post {
                    Toast.makeText(this, "ذخیره خودکار نشد: ${e.message}",
                        Toast.LENGTH_LONG).show()
                }
            }
        }.start()
    }

    private fun cleanupPagesDirs() {
        Thread {
            var n = 0
            try {
                if (Build.VERSION.SDK_INT >= 29) {
                    val sel = "${MediaStore.MediaColumns.RELATIVE_PATH} LIKE ? ESCAPE '\\'"
                    val args = arrayOf("Download/manga/pages\\_%")
                    val proj = arrayOf(MediaStore.MediaColumns._ID)
                    contentResolver.query(
                        MediaStore.Downloads.EXTERNAL_CONTENT_URI, proj, sel, args, null
                    )?.use { c ->
                        val idCol = c.getColumnIndexOrThrow(MediaStore.MediaColumns._ID)
                        val ids = mutableListOf<Long>()
                        while (c.moveToNext()) ids.add(c.getLong(idCol))
                        for (id in ids) {
                            val uri = android.content.ContentUris.withAppendedId(
                                MediaStore.Downloads.EXTERNAL_CONTENT_URI, id)
                            try {
                                if (contentResolver.delete(uri, null, null) > 0) n++
                            } catch (_: Exception) {}
                        }
                    }
                } else if (canWritePublic()) {
                    val base = File(Environment.getExternalStoragePublicDirectory(
                        Environment.DIRECTORY_DOWNLOADS), "manga")
                    val kids = base.listFiles() ?: emptyArray()
                    for (d in kids) {
                        if (d.isDirectory && d.name.startsWith("pages_")) {
                            try { if (d.deleteRecursively()) n++ } catch (_: Exception) {}
                        }
                    }
                }
            } catch (e: Exception) {
                android.util.Log.e("MangaApp", "cleanupPagesDirs", e)
            }
            try {
                val baseF = File(Environment.getExternalStoragePublicDirectory(
                    Environment.DIRECTORY_DOWNLOADS), "manga")
                for (d in baseF.listFiles() ?: emptyArray()) {
                    if (d.isDirectory && d.name.startsWith("pages_")) {
                        try {
                            val kids = d.listFiles()
                            if (kids == null || kids.isEmpty()) {
                                if (d.delete()) n++
                            } else if (d.deleteRecursively()) n++
                        } catch (_: Exception) {
                        }
                    }
                }
            } catch (_: Exception) {
            }
            if (n > 0) {
                android.util.Log.i("MangaApp", "cleanupPagesDirs: $n items removed")
                ui.post {
                    Toast.makeText(this,
                        "🧹 $n مورد از پوشه‌های pages_ قدیمی پاک شد",
                        Toast.LENGTH_SHORT).show()
                }
            }
        }.start()
    }

override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == REQ_IMPORT && resultCode == Activity.RESULT_OK &&
            data != null && data.data != null) {
            val uri = data.data!!
            val dst = File(cacheDir, "import_" + System.currentTimeMillis() + ".json")
            try {
                contentResolver.openInputStream(uri)?.use { i ->
                    dst.outputStream().use { o -> i.copyTo(o) }
                }
            } catch (_: Exception) {
            }
            if (dst.isFile && dst.length() > 0) {
                doImport(dst.absolutePath)
                try { dst.delete() } catch (_: Exception) {}
            } else {
                setBackupStatus("❌ خواندنِ فایلِ بکاپ ناموفق بود.", true)
                Toast.makeText(this, "❌ خواندنِ فایل ناموفق بود", Toast.LENGTH_LONG).show()
            }
            return
        }
        if (requestCode == REQ_FILE && resultCode == Activity.RESULT_OK && data != null) {

            val uris = mutableListOf<Uri>()
            data.data?.let { uris.add(it) }
            data.clipData?.let { cd ->
                for (i in 0 until cd.itemCount) {
                    try { cd.getItemAt(i).uri?.let { u -> if (!uris.contains(u)) uris.add(u) } }
                    catch (_: Exception) {}
                }
            }
            if (uris.isEmpty()) return
            val fid0 = pickerField ?: return
            val isFontField = fid0.startsWith("up_") || fid0 == "font_upload"
            val copied = mutableListOf<String>()
            for (uri in uris) {
                var name = queryDisplayName(uri)
                if (name.isNullOrBlank()) name = uri.lastPathSegment ?: "input.bin"
                name = name.substringAfterLast('/')
                if (!name.contains('.')) {
                    val mime = try { contentResolver.getType(uri) } catch (_: Exception) { null }
                    val ext = when {
                        mime?.startsWith("image/") == true ->
                            "." + mime.removePrefix("image/").substringBefore('+')
                                .replace("jpeg", "jpg")
                        mime == "application/pdf" -> ".pdf"
                        mime == "application/zip" || mime == "application/x-zip-compressed" -> ".zip"
                        mime?.startsWith("font/") == true || mime == "application/x-font-ttf" -> ".ttf"
                        fid0.contains("font") -> ".ttf"
                        else -> ".png"
                    }
                    name += ext
                }
                name = name.replace(Regex("[\\\\/:*?\"<>|,]"), "_")
                val dest = File(cacheDir, "pick_" + System.currentTimeMillis() + "_" + name)
                try {
                    contentResolver.openInputStream(uri)?.use { input ->
                        dest.outputStream().use { output -> input.copyTo(output) }
                    }
                } catch (_: Exception) {}
                if (dest.isFile && dest.length() > 0) copied.add(dest.absolutePath)
                if (isFontField) break

            }
            if (copied.isEmpty()) return
            val fid = pickerField ?: return
            pickedFiles[fid] = copied.joinToString(",")
            saveVal(fid + "_path", pickedFiles[fid] ?: "")
            (fieldViews[fid] as? TextView)?.text =
                if (copied.size == 1) "✔ ${File(copied[0]).name}"
                else "✔ ${copied.size} فایل انتخاب شد"
            if (isFontField) {
                (fieldViews[fid + "_btn"] as? Button)?.text =
                    "✓ ${File(copied[0]).name}"
            } else {
                (fieldViews[fid + "_btn"] as? Button)?.text =
                    if (copied.size == 1) "✓ ${File(copied[0]).name}"
                    else "✓ ${copied.size} فایل — برای تغییر دوباره کلیک کن"
            }
            (fieldViews[fid + "_clear"] as? Button)?.visibility = View.VISIBLE
            saveVal("last_file_name", File(copied[0]).name)
        }
    }

    private fun queryDisplayName(uri: Uri): String? {
        return try {
            contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)
                ?.use { c -> if (c.moveToFirst()) c.getString(0) else null }
        } catch (_: Exception) {
            null
        }
    }

    companion object {
        const val REQ_FILE = 1001
        const val REQ_STORAGE = 1002
        const val REQ_IMPORT = 1003
    }
}
