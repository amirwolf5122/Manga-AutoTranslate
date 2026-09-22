package com.amirwolf.mangatranslator

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.graphics.BitmapFactory
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Bundle
import android.os.Environment
import android.provider.OpenableColumns
import android.os.Handler
import android.os.Looper
import android.text.InputType
import android.util.TypedValue
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
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

/** اپ بومی مانگا مترجم — UI از manga_app.py، طرح دقیق مثل وب گرادیو. */
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

    private lateinit var bridge: com.chaquo.python.PyObject
    private lateinit var formBox: LinearLayout
    private lateinit var logBox: TextView
    private lateinit var resultsBox: LinearLayout
    private lateinit var runBtn: Button
    private lateinit var loadingRow: LinearLayout
    private val values = HashMap<String, Any?>()
    private val fieldViews = HashMap<String, View>()
    private val pickedFiles = HashMap<String, String>()
    private var pickerField: String? = null
    private var logFollow = true  // لاگ خودکار تا پایین می‌آید تا کاربر بالا بکشد
    private val ui = Handler(Looper.getMainLooper())
    private val prefs by lazy { getSharedPreferences("manga_settings", MODE_PRIVATE) }

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

    private fun saveVal(id: String, v: Any?) {
        values[id] = v
        prefs.edit().putString(id, v?.toString() ?: "").apply()
    }

    private fun savedOr(id: String, dflt: Any?): Any? =
        prefs.getString(id, null) ?: dflt

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.decorView.setBackgroundColor(BG)
        window.navigationBarColor = BG
        window.statusBarColor = BG

        if (!Python.isStarted()) Python.start(AndroidPlatform(this))

        // اجازه حافظه فقط برای اندروید ۹ و قدیمی‌تر — اندروید ۱۰+ با MediaStore بی‌اجازه است
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
            topMargin = dp(14); bottomMargin = dp(8)
        })

        // لاگ + نتایج داخل آکاردئون «🚩 لاگ زنده» مثل وب
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
            // وقتی روی لاگ می‌کشی، ScrollView بیرونی بouce اسکرول را نمی‌دزدد
            setOnTouchListener { v, ev ->
                v.parent.requestDisallowInterceptTouchEvent(true)
                if (ev.action == android.view.MotionEvent.ACTION_UP ||
                    ev.action == android.view.MotionEvent.ACTION_CANCEL) {
                    // اگر کاربر پایین لاگ است، دوباره دنبال‌کردن ادامه پیدا می‌کند
                    logFollow = !logBox.canScrollVertically(1)
                }
                false
            }
            text = "— لاگ بعد از شروع ترجمه اینجا می‌آید —"
        }
        logContent.addView(logBox, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, dp(230)).apply { topMargin = dp(4) })
        resultsBox = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        logContent.addView(resultsBox)
        logCard.addView(logContent)
        root.addView(logCard, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply {
            topMargin = dp(10)
        })

        root.addView(footer())

        // لودینگ اول — تا فرم آماده شود (موتور + دانلود فونت)
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
        })
        root.addView(loadingRow, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))

        runBtn.setOnClickListener { onStartJob() }

        Thread {
            try {
                clearOldCaches()
                copyBundledSources()
                val launcher = Python.getInstance().getModule("launcher")
                launcher.callAttr("main", filesDir.absolutePath)
                // لایه پایدار — آپدیت ریپو نمی‌تواند فیکس‌های Ollama/سلامت را پاک کند
                bridge = Python.getInstance().getModule("native_bridge")
                // چک سلامت موتور: اگر manga.py / manga_app.py خراب باشد، کامل بگو چه چیزی خراب است
                var healthReport = ""
                try {
                    val h = JSONObject(bridge.callAttr("health").toString())
                    if (!h.optBoolean("ok")) healthReport = h.optString("report", "")
                } catch (_: Exception) {
                }
                val st = launcher.callAttr("status").toString()
                ui.post {
                    logBox.text = if (healthReport.isNotBlank())
                        healthReport + "\n\n—— وضعیت فایل‌ها —\n" + st
                    else st
                }
                ui.post { buildForm() }
            } catch (e: PyException) {
                ui.post {
                    logBox.text = "❌ خطای موتور:\n" + e.message
                    Toast.makeText(this, "خطای موتور پایتون", Toast.LENGTH_LONG).show()
                }
            }
        }.start()
    }


    /** کپی manga.py / manga_app.py از assets/engine به files/updates.
     *  آپدیت آنلاین از release «files» کلاً حذف شده است؛ موتور فقط از APK می‌آید.
     *  یک‌بار (با مهر .engine_offline_v1) فایل‌های موتورِ قبلی روی دیسد پاک
     *  می‌شوند تا دقیقاً نسخه‌ی همراه این APK جای‌گزین شود — حتی اگر نسخه
     *  قبلی از آپدیت شبکه APP_VER بالاتری داشته باشد. */
    private fun copyBundledSources() {
        try {
            val upd = File(filesDir, "updates").apply { mkdirs() }
            val marker = File(upd, ".engine_offline_v1")
            if (!marker.exists()) {
                upd.listFiles()?.forEach { f ->
                    if (f.name.endsWith(".py") || f.name.startsWith(".ver_")) f.delete()
                }
                marker.writeText("1")
                android.util.Log.i("MangaApp", "engine reset → bundled copy (no net updates)")
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
                val broken = dst.exists() && dst.length() < 1000L
                val newer = verCmp(assetVer, diskVer) > 0
                if (!dst.exists() || broken || newer) {
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

    // ---------- ساخت فرم بومی از manifest ----------
    private fun buildForm() {
        loadingRow.visibility = View.GONE
        try {
            val mf = JSONObject(bridge.callAttr("manifest").toString())
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

                // مثل وب: ۳ بخش اول باز، آکاردئون‌ها (فونت‌ها/پیشرفته) بسته
                val openDefault = step <= 3
                contentBox.visibility = if (openDefault) View.VISIBLE else View.GONE
                arrow.text = if (openDefault) "▾" else "▸"

                val fields = sec.getJSONArray("fields")
                for (i in 0 until fields.length()) addField(contentBox, fields.getJSONObject(i))
                formBox.addView(card, lp)
            }
        } catch (e: Exception) {
            loadingRow.visibility = View.GONE
            logBox.text = "❌ ساخت فرم:\n" + (e.message ?: e.toString())
        }
    }

    /** کش‌های اجراهای قبلی: خروجی‌های work و کپی فایل‌های ورودی —
     *  تنظیمات و فونت‌ها دست‌نخورده می‌مانند. */
    private fun clearOldCaches() {
        try {
            File(filesDir, "work").deleteRecursively()
            cacheDir.listFiles()?.forEach {
                if (it.name.startsWith("pick_")) it.delete()
            }
        } catch (e: Exception) {
            android.util.Log.e("MangaApp", "clearOldCaches", e)
        }
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

        when (type) {
            "text", "password", "number" -> {
                card.addView(label(lbl))
                val lines = f.optInt("lines", 1)
                val et = EditText(this).apply {
                    if (lines > 1) {
                        // فیلد چندخطی (System Instruction، واژه‌نامه …)
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
                    if (lines < 2 && type == "password") inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
                    if (lines < 2 && type == "number") inputType = InputType.TYPE_CLASS_NUMBER
                    val saved = savedOr(id, dflt)
                    if (saved is String) {
                        // pref خالی نسخه قبلی = هیچ — دیفالت (مثل instruction از manga.py)
                        setText(saved.ifBlank { dflt?.toString() ?: "" })
                    }
                    addTextChangedListener(object : android.text.TextWatcher {
                        override fun afterTextChanged(s: android.text.Editable?) {
                            prefs.edit().putString(id, s?.toString() ?: "").apply()
                        }
                        override fun beforeTextChanged(p0: CharSequence?, p1: Int, p2: Int, p3: Int) {}
                        override fun onTextChanged(p0: CharSequence?, p1: Int, p2: Int, p3: Int) {}
                    })
                }
                card.addView(et)
                infoView()?.let { card.addView(it) }
                fieldViews[id] = et
            }
            "select" -> {
                card.addView(label(lbl))
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
                val btn = Button(this).apply {
                    text = items.getOrNull(selected)?.first ?: "— انتخاب —"
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
                            btn.text = items[w].first
                        }.show()
                }
                if (selected >= 0) values[id] = items[selected].second
                card.addView(btn)
                infoView()?.let { card.addView(it) }
                fieldViews[id] = btn
            }
            "radio" -> {
                card.addView(label(lbl))
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
                card.addView(listCol)
                infoView()?.let { card.addView(it) }
                fieldViews[id] = listCol
            }
            "bool" -> {
                val sw = SwitchCompat(this).apply {
                    text = lbl
                    setTextColor(TXT); textSize = 13f
                    setPadding(dp(4), dp(8), dp(4), dp(8))
                    isChecked = (savedOr(id, dflt) as? Boolean) ?: (dflt == true)
                    thumbTintList = android.content.res.ColorStateList.valueOf(ACC)
                    trackTintList = android.content.res.ColorStateList(
                        arrayOf(intArrayOf(android.R.attr.state_checked), intArrayOf()),
                        intArrayOf(ACC, LINE))
                    setOnCheckedChangeListener { _, c -> saveVal(id, c) }
                }
                card.addView(sw)
                infoView()?.let { card.addView(it) }
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

                val row = LinearLayout(this).apply {
                    orientation = LinearLayout.HORIZONTAL
                    gravity = Gravity.CENTER_VERTICAL
                }
                row.addView(label(lbl), LinearLayout.LayoutParams(0,
                    ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
                val valBox = TextView(this).apply {
                    text = fmt(apply((savedV ?: dfltV).toFloat()))
                    setTextColor(TXT); textSize = 13f; typeface = Typeface.DEFAULT_BOLD
                    background = rounded(CARD2, 8, 1)
                    setPadding(dp(10), dp(4), dp(10), dp(4))
                }
                row.addView(valBox)
                card.addView(row)
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
                card.addView(sl)
                infoView()?.let { card.addView(it) }
                fieldViews[id] = sl
            }
            "file" -> {
                card.addView(label(lbl))
                val nameView = TextView(this).apply {
                    text = "فایلی انتخاب نشده"
                    setTextColor(MUT); textSize = 11f; setPadding(dp(12), dp(2), dp(12), dp(2))
                }
                val btn = Button(this).apply {
                    text = "⬆  آپلود فایل — کلیک کن"
                    setTextColor(MUT); textSize = 13f
                    background = dashed()
                    gravity = Gravity.CENTER
                    setPadding(dp(12), dp(18), dp(12), dp(18))
                    stateListAnimator = null
                }
                btn.setOnClickListener {
                    pickerField = id
                    startActivityForResult(
                        Intent.createChooser(Intent(Intent.ACTION_GET_CONTENT).apply {
                            addCategory(Intent.CATEGORY_OPENABLE)
                            setType("*/*")
                        }, "انتخاب فایل"), REQ_FILE)
                }
                card.addView(btn)
                card.addView(nameView)
                fieldViews[id] = nameView
                fieldViews[id + "_btn"] = btn
                // بازیابی انتخاب قبلی (مثلاً فونت لحن) بعد از بستن اپ
                val prev = prefs.getString(id + "_path", null)
                if (prev != null && File(prev).isFile()) {
                    pickedFiles[id] = prev
                    nameView.text = "✔ ${File(prev).name}"
                    (fieldViews[id + "_btn"] as? Button)?.text = "✓ ${File(prev).name}"
                }
            }
            "header" -> card.addView(TextView(this).apply {
                text = lbl; setTextColor(ACC); textSize = 12.5f
                typeface = Typeface.DEFAULT_BOLD; setPadding(0, dp(10), 0, dp(2))
            })
        }
    }

    // ---------- جمع‌کردن مقادیر و اجرا ----------
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
        map.put("src", firstNonEmpty(o, "inp_path", "url")
            ?: pickedFiles["inp_upload"] ?: pickedFiles.values.firstOrNull() ?: "")
        map.put("file", pickedFiles["inp_upload"] ?: "")
        map.put("provider", firstNonEmpty(o, "provider") ?: "gemini")
        map.put("keys", firstNonEmpty(o, "manga_api_keys", "api_keys", "keys") ?: "")
        map.put("model", firstNonEmpty(o, "manga_model", "model") ?: "")
        map.put("ocr_lang", firstNonEmpty(o, "manga_ocr_lang", "ocr_lang") ?: "en")
        map.put("fmt", firstNonEmpty(o, "out_fmt", "fmt") ?: "PDF")
        map.put("quality", optInt(o, "quality", 92))
        map.put("debug", optBool(o, "web_debug", "debug"))
        map.put("fake", optBool(o, "fake_test", "fake"))
        map.put("clean_only", optBool(o, "clean_only"))
        map.put("use_lama", optBool(o, "use_lama"))
        map.put("force_cpu", optBool(o, "force_cpu"))
        map.put("two_pass", optBoolD(o, true, "two_pass"))
        map.put("readord", firstNonEmpty(o, "readord") ?: "rtl")
        map.put("glossary", firstNonEmpty(o, "glossary_text", "glossary") ?: "")
        map.put("instruction", firstNonEmpty(o, "instruction_text", "instruction") ?: "")
        map.put("story_brief", optBoolD(o, true, "story_brief"))
        // تنظیمات پیشرفته — اگر فیلدش در manifest نبود، دیفالت خود موتور می‌ماند
        for (k in listOf("workers", "bubbles", "batchw", "timeout", "maxre", "reqdelay", "temp", "api_base")) {
            if (o.has(k) && !o.isNull(k)) map.put(k, o.get(k))
        }
        // فونت‌ها: هر فیلد file/bool باقی‌مانده (فونت اصلی + لحن‌ها از manga_app.py)
        for ((id, v) in values) {
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
            logBox.post {
                try {
                    val l = logBox.layout ?: return@post
                    val bottom = l.getLineBottom(l.lineCount - 1) - logBox.height + dp(8)
                    logBox.scrollTo(0, bottom.coerceAtLeast(0))
                } catch (e: Exception) {
                }
            }
        }
    }

    private fun onStartJob() {
        try {
            val p = collect()
            if ((p.optString("src") ?: "").isBlank()) {
                Toast.makeText(this, "فایل یا لینک ورودی بده", Toast.LENGTH_SHORT).show()
                return
            }
            runBtn.isEnabled = false
            runBtn.text = "⏳ در حال اجرا…"
            resultsBox.removeAllViews()
            val r = JSONObject(bridge.callAttr("start_job", p.toString(), filesDir.absolutePath).toString())
            if (r.optBoolean("ok")) pollLoop()
            else {
                logBox.text = "❌ " + r.optString("error", "خطا")
                runBtn.isEnabled = true; runBtn.text = "🚀  شروع ترجمه"
            }
        } catch (e: Exception) {
            logBox.text = "❌ " + (e.message ?: e.toString())
            runBtn.isEnabled = true
        }
    }

    private fun pollLoop() {
        ui.postDelayed({
            try {
                val st = JSONObject(bridge.callAttr("poll").toString())
                setLog(st.optString("log", ""))
                if (st.optBoolean("done")) {
                    runBtn.isEnabled = true
                    runBtn.text = "🚀  شروع ترجمه"
                    showResults(st)
                } else pollLoop()
            } catch (e: Exception) {
                logBox.text = "❌ poll: " + (e.message ?: e.toString())
                runBtn.isEnabled = true
            }
        }, 1500)
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
        val outFile = st.optString("out_file", "")
        val hasOutFile = outFile.isNotBlank() && File(outFile).isFile()

        // ⚠ درخواست کاربر: اگر واقعاً تصویری ساخته نشده، دکمهٔ آن اصلاً نشان داده نشود
        if (images.isNotEmpty()) {
            resultsBox.addView(resBtn("📖  نمایش (${images.size} صفحه)", true) {
                viewer(images)
            })
        }
        if (hasOutFile) {
            resultsBox.addView(resBtn("⬇  دانلود خروجی", false) { saveToDownloads(outFile) })
        }
        if (debug.isNotEmpty()) {
            resultsBox.addView(resBtn("🔍  نمایش دیباگ (${debug.size})", false) { viewer(debug) })
            resultsBox.addView(resBtn("⬇  دانلود دیباگ (${debug.size})", false) {
                saveManyToDownloads(debug, "debug")
            })
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

    /** نمایشگر تمام‌صفحهٔ عمودی — همهٔ صفحه‌ها به‌ترتیب از بالا به پایین چیده
     *  می‌شوند و با کشیدن انگشت به پایین خوانده می‌شوند (بدون دکمهٔ قبلی/بعدی
     *  و بدون ناوبری چپ/راست — درخواست کاربر).
     *  دبل‌تپ = زوم ×2.5، پینچ = زوم آزاد (تا ×4)، تک‌تپ = نمایش/مخفی شماره صفحه.
     *  دیکود در بک‌گراند + کش LRU + درصدهای بزرگ با inSampleSize (بدون OOM). */
    private fun viewer(paths: List<String>, start: Int = 0) {
        if (paths.isEmpty()) return
        val screenW = resources.displayMetrics.widthPixels
        val bmpCache = object : android.util.LruCache<String, android.graphics.Bitmap>(
            ((Runtime.getRuntime().maxMemory() / 6L).toInt()).coerceAtLeast(12 * 1024 * 1024)) {
            override fun sizeOf(key: String, b: android.graphics.Bitmap): Int = b.byteCount
        }
        val decoder = java.util.concurrent.Executors.newSingleThreadExecutor()

        val pill = TextView(this).apply {
            setTextColor(Color.WHITE); textSize = 13f; typeface = Typeface.DEFAULT_BOLD
            background = rounded(Color.parseColor("#88000000"), 999)
            setPadding(dp(14), dp(6), dp(14), dp(6))
        }
        val close = TextView(this).apply {
            text = "✕"; setTextColor(Color.WHITE); textSize = 15f
            gravity = Gravity.CENTER
            background = rounded(Color.parseColor("#88000000"), 999)
        }
        val recycler = androidx.recyclerview.widget.RecyclerView(this)
        recycler.setBackgroundColor(Color.BLACK)
        recycler.layoutManager = androidx.recyclerview.widget.LinearLayoutManager(this)
        recycler.setItemViewCacheSize(4)

        val hideRun = Runnable { pill.visibility = View.GONE; close.visibility = View.GONE }
        val showChrome: () -> Unit = {
            pill.visibility = View.VISIBLE; close.visibility = View.VISIBLE
            ui.removeCallbacks(hideRun); ui.postDelayed(hideRun, 2400)
        }
        val toggleChrome: () -> Unit = {
            if (pill.visibility == View.VISIBLE) {
                ui.removeCallbacks(hideRun)
                pill.visibility = View.GONE; close.visibility = View.GONE
            } else showChrome()
        }

        val adapter = object : androidx.recyclerview.widget.RecyclerView.Adapter<ReaderHolder>() {
            override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ReaderHolder =
                ReaderHolder(this@MainActivity, recycler, screenW, bmpCache, decoder, toggleChrome)

            override fun getItemCount(): Int = paths.size

            override fun onBindViewHolder(holder: ReaderHolder, position: Int) =
                holder.bind(paths[position])

            override fun onViewRecycled(holder: ReaderHolder) {
                holder.recycle()
            }
        }
        recycler.adapter = adapter
        val lm = recycler.layoutManager as androidx.recyclerview.widget.LinearLayoutManager
        recycler.addOnScrollListener(
            object : androidx.recyclerview.widget.RecyclerView.OnScrollListener() {
                override fun onScrolled(rv: androidx.recyclerview.widget.RecyclerView,
                                        dx: Int, dy: Int) {
                    val pos = lm.findFirstVisibleItemPosition()
                    if (pos >= 0 && pos < paths.size) {
                        pill.text = "صفحه ${pos + 1} از ${paths.size}"
                    }
                }
            })

        val root = android.widget.FrameLayout(this).apply { setBackgroundColor(Color.BLACK) }
        root.addView(recycler, ViewGroup.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.MATCH_PARENT))
        root.addView(pill, android.widget.FrameLayout.LayoutParams(
            ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT,
            Gravity.TOP or Gravity.CENTER_HORIZONTAL).apply { topMargin = dp(14) })
        root.addView(close, android.widget.FrameLayout.LayoutParams(
            dp(34), dp(34), Gravity.TOP or Gravity.END).apply {
            topMargin = dp(10); marginEnd = dp(10) })

        val dlg = Dialog(this, android.R.style.Theme_Black_NoTitleBar_Fullscreen)
        dlg.setContentView(root)
        dlg.window?.setBackgroundDrawable(ColorDrawable(Color.BLACK))
        dlg.window?.setLayout(ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.MATCH_PARENT)
        close.setOnClickListener { dlg.dismiss() }
        dlg.setOnDismissListener {
            ui.removeCallbacks(hideRun)
            decoder.shutdownNow()
        }
        val s0 = start.coerceIn(0, paths.size - 1)
        pill.text = "صفحه ${s0 + 1} از ${paths.size}"
        recycler.post { lm.scrollToPosition(s0) }
        dlg.show()
        showChrome()
        if (!prefs.getBoolean("viewer_hint_v2", false)) {
            prefs.edit().putBoolean("viewer_hint_v2", true).apply()
            Toast.makeText(this,
                "صفحه‌ها به‌ترتیب زیر هم چیده شدن • برای زوم دبل‌تپ بزن یا پینچ کن",
                Toast.LENGTH_LONG).show()
        }
    }

    /** یک ردیف لیست عمودی — HorizontalScrollView (پن افقی در زوم) + PageView.
     *  زوم به‌صورت «تغییر اندازهٔ خود ویو» انجام می‌شود تا اسکرول عمودی لیست
     *  همیشه طبیعی بماند (الگوی خوانندهٔ وب‌تون). */
    private inner class ReaderHolder(
        ctx: android.content.Context,
        private val list: androidx.recyclerview.widget.RecyclerView,
        private val screenW: Int,
        private val cache: android.util.LruCache<String, android.graphics.Bitmap>,
        private val decoder: java.util.concurrent.Executor,
        private val onTap: () -> Unit,
    ) : androidx.recyclerview.widget.RecyclerView.ViewHolder(
        android.widget.HorizontalScrollView(ctx).apply {
            isFillViewport = false
            isHorizontalScrollBarEnabled = false
            setBackgroundColor(Color.BLACK)
        }) {

        val page = PageView(ctx)
        private var ratio = 1.4f   // ارتفاع/عرض تخمینی تا رسیدن بیت‌مپ
        private var zoom = 1f      // ۱ = به‌اندازهٔ عرض صفحه

        init {
            itemView.layoutParams = androidx.recyclerview.widget.RecyclerView.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
            (itemView as android.widget.HorizontalScrollView).addView(page)
        }

        fun bind(path: String) {
            page.tag = path
            page.onTap = { onTap() }
            val b = cache.get(path)
            if (b != null) {
                page.setImageBitmap(b)
                ratio = b.height.toFloat() / b.width.toFloat()
                zoom = 1f
                page.post { applySize() }
            } else {
                page.setImageBitmap(null)
                ratio = 1.4f
                zoom = 1f
                page.post { applySize() }
                decoder.execute {
                    val o = BitmapFactory.Options().apply { inJustDecodeBounds = true }
                    BitmapFactory.decodeFile(path, o)
                    var sample = 1
                    var m = maxOf(o.outWidth, o.outHeight)
                    while (m / sample >= 2560) sample *= 2
                    val bmp = BitmapFactory.decodeFile(path,
                        BitmapFactory.Options().apply { inSampleSize = sample })
                    if (bmp != null) cache.put(path, bmp)
                    page.post {
                        if (page.tag == path && bmp != null) {
                            page.setImageBitmap(bmp)
                            ratio = bmp.height.toFloat() / bmp.width.toFloat()
                            applySize()
                        }
                    }
                }
            }
        }

        fun recycle() {
            page.tag = null
            page.setImageBitmap(null)
        }

        private fun applySize() {
            val w = (screenW * zoom).toInt().coerceAtLeast(1)
            val h = (w * ratio).toInt().coerceAtLeast(1)
            page.layoutParams = ViewGroup.LayoutParams(w, h)
        }

        /** ImageView صفحه — همهٔ لمس‌ها را می‌گیرد و خودش توزیع می‌کند:
         *  اسکرول عمودی → لیست، پن افقی در زوم → HorizontalScrollView،
         *  پینچ/دبل‌تپ → تغییر zoom (اندازهٔ ویو). */
        inner class PageView(ctx: android.content.Context) :
            androidx.appcompat.widget.AppCompatImageView(ctx) {

            var onTap: (() -> Unit)? = null

            private val scaleDet = android.view.ScaleGestureDetector(ctx,
                object : android.view.ScaleGestureDetector.SimpleOnScaleGestureListener() {
                    override fun onScale(d: android.view.ScaleGestureDetector): Boolean {
                        zoom = (zoom * d.scaleFactor).coerceIn(1f, 4f)
                        applySize()
                        return true
                    }
                })

            private val gest = android.view.GestureDetector(ctx,
                object : android.view.GestureDetector.SimpleOnGestureListener() {
                    override fun onDown(e: android.view.MotionEvent): Boolean = true

                    override fun onScroll(e1: android.view.MotionEvent?,
                                          e2: android.view.MotionEvent,
                                          dx: Float, dy: Float): Boolean {
                        // افقی: فقط وقتی زوم‌شده محدودهٔ پن وجود دارد
                        (itemView as android.widget.HorizontalScrollView)
                            .scrollBy((-dx).toInt(), 0)
                        // عمودی: همیشه لیست جلو می‌رود (خواندن از بالا به پایین)
                        list.scrollBy(0, dy.toInt())
                        return true
                    }

                    override fun onSingleTapConfirmed(e: android.view.MotionEvent): Boolean {
                        onTap?.invoke(); return true
                    }

                    override fun onDoubleTap(e: android.view.MotionEvent): Boolean {
                        zoom = if (zoom > 1.2f) 1f else 2.5f
                        applySize()
                        return true
                    }

                    override fun onFling(e1: android.view.MotionEvent?,
                                         e2: android.view.MotionEvent,
                                         vx: Float, vy: Float): Boolean {
                        list.fling(0, vy.toInt())
                        return true
                    }
                })

            init {
                scaleType = ImageView.ScaleType.FIT_CENTER
                adjustViewBounds = false
            }

            override fun onTouchEvent(e: android.view.MotionEvent): Boolean {
                scaleDet.onTouchEvent(e)
                if (!scaleDet.isInProgress) gest.onTouchEvent(e)
                if (scaleDet.isInProgress) {
                    parent?.requestDisallowInterceptTouchEvent(true)
                }
                return true
            }
        }
    }

    private fun stampNow(): String =
        java.text.SimpleDateFormat("yyyyMMdd_HHmmss", java.util.Locale.US)
            .format(java.util.Date())

    private fun canWritePublic(): Boolean =
        Build.VERSION.SDK_INT >= 29 ||
            checkSelfPermission(android.Manifest.permission.WRITE_EXTERNAL_STORAGE) ==
            PackageManager.PERMISSION_GRANTED

    /** ذخیره یک فایل در Download/manga —
     *  اندروید ۱۰+ : MediaStore.Downloads با RELATIVE_PATH (بدون هیچ اجازه‌ای —
     *  راه درست Scoped Storage؛ خطای «دسترسی حافظه نداره» همین بود)؛
     *  اندروید ۹−  : File API با اجازه WRITE_EXTERNAL_STORAGE (در شروع اپ خواسته می‌شود). */
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
            val ok = saveAnyToDownloads(path, null, "manga_${stampNow()}.$ext")
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

    /** ذخیره خودکار خروجی هر اجرا در Download/manga — فایل نهایی (PDF/ZIP/…) + تک‌تک صفحات.
     *  چون خروجی داخلی اپ در هر اجرای جدید پاک می‌شود، این کار تضمین می‌کند نسخه
     *  ترجمه‌شده همیشه در حافظه عمومی بماند. */
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
                    if (saveAnyToDownloads(outFile, null,
                            "manga_${stampNow()}." + f.extension.ifBlank { "bin" })) n++
                }
                val sub = "pages_${stampNow()}"
                for (p in images) if (saveAnyToDownloads(p, sub, null)) n++
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

override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == REQ_FILE && resultCode == Activity.RESULT_OK && data?.data != null) {
            val uri = data.data!!
            val fid0 = pickerField ?: ""
            // اول نام واقعی فایل را از provider بپرس (مرورگر/فایل‌منیجر معمولاً DisplayName می‌دهد)
            var name = queryDisplayName(uri)
            if (name.isNullOrBlank()) name = uri.lastPathSegment ?: "input.bin"
            name = name.substringAfterLast('/')
            // گالری اندروید گاهی نام بدون پسوند می‌دهد (مثل «image:1000223081»)
            // → موتور ورودی بی‌پسوند را قبول نمی‌کند؛ پسوند را از MIME بساز
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
            // کاراکترهای غیرمجاز نام فایل (مثل «:» در image:1000223081)
            name = name.replace(Regex("[\\\\/:*?\"<>|]"), "_")
            val dest = File(cacheDir, "pick_" + System.currentTimeMillis() + "_" + name)
            contentResolver.openInputStream(uri)?.use { input ->
                dest.outputStream().use { output -> input.copyTo(output) }
            }
            // فقط همان فیلدی که دکمه‌اش زده شده — فونت/لحن دیگر روی src اثر نمی‌گذارد
            val fid = pickerField ?: return
            pickedFiles[fid] = dest.absolutePath
            saveVal(fid + "_path", dest.absolutePath)
            (fieldViews[fid] as? TextView)?.text = "✔ ${dest.name}"
            if (fid.startsWith("up_") || fid == "font_upload") {
                (fieldViews[fid + "_btn"] as? Button)?.text = "✓ ${dest.name}"
            }
            saveVal("last_file_name", dest.name)
        }
    }

    /** نام واقعی فایل از provider (ستون DISPLAY_NAME) — null اگر ممکن نشد. */
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
    }
}
