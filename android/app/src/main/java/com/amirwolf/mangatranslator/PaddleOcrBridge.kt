
package com.amirwolf.mangatranslator

import android.content.Context
import android.util.Log
import com.paddle.ocr.EngineConfig
import com.paddle.ocr.RapidOcr
import com.paddle.ocr.util.OpenCVUtils
import kotlinx.coroutines.runBlocking

object PaddleOcrBridge {

    private const val TAG = "PaddleOcrBridge"

    private const val DET_ASSET = "models/det/inference.onnx"
    private const val CLS_ASSET = "models/cls/inference.onnx"
    private const val REC_ASSET = "models/rec/inference.onnx"
    private const val REC_DICT_ASSET = "models/rec/dict.txt"

    private val LANG_VARIANTS: Map<String, Pair<String, String>> = mapOf(
        "ko" to ("models/rec_ko/inference.onnx" to "models/rec_ko/dict.txt"),
    )

    private val DEFAULT_VARIANT: Pair<String, String> =
        REC_ASSET to REC_DICT_ASSET

    @Volatile
    private var engine: RapidOcr? = null

    @Volatile
    private var ctx: Context? = null

    @Volatile
    private var currentVariant: String = "ch"

    private val lock = Any()

    @JvmStatic
    fun hold(context: Context) {
        if (ctx == null) ctx = context.applicationContext
    }

    @JvmStatic
    fun init(numThreads: Int): Boolean = init(numThreads, null)

    @JvmStatic
    fun init(numThreads: Int, primaryLang: String?): Boolean = synchronized(lock) {
        val context = ctx ?: run {
            Log.e(TAG, "init: MtApp هنوز Context نداده است")
            return false
        }
        try {
            OcrModelStore.ensure(context, OcrModelStore.pathsForLang(primaryLang))
        } catch (t: Throwable) {
            Log.e(TAG, "model ensure failed (lang=$primaryLang)", t)
            engine = null
            return false
        }
        if (engine != null) return true
        return try {
            OpenCVUtils.init(context)
            val threads = numThreads.coerceIn(1, 8)
            engine = runBlocking {
                RapidOcr.create(
                    context = context,
                    engineConfig = EngineConfig(numThreads = threads),
                    detModelAssetPath = DET_ASSET,
                    clsModelAssetPath = CLS_ASSET,
                    recModelAssetPath = REC_ASSET,
                    recDictAssetPath = REC_DICT_ASSET,
                )
            }
            currentVariant = "ch"
            Log.i(TAG, "RapidOCR (RapidOcrAndroidOnnx pipeline) ready — " +
                    "PP-OCRv6 det=small rec=MEDIUM, threads=$threads")
            true
        } catch (t: Throwable) {
            Log.e(TAG, "init failed", t)
            engine = null
            false
        }
    }

    @JvmStatic
    fun ready(): Boolean = engine != null

    private fun variantFor(lang: String): Pair<String, Pair<String, String>> {
        val key = lang.lowercase().trim()
        val variant = LANG_VARIANTS[key] ?: DEFAULT_VARIANT
        return if (LANG_VARIANTS.containsKey(key)) key to variant
        else "ch" to variant
    }

    @JvmStatic
    fun recognizeAuto(png: ByteArray, lang: String, w: Int, h: Int):
            Array<String>? = synchronized(lock) {
        val eng = engine ?: return null
        try {
            val (variantKey, variant) = variantFor(lang)
            if (variantKey != currentVariant) {
                try {
                    ctx?.let { OcrModelStore.ensure(it, listOf(variant.first, variant.second)) }
                } catch (t: Throwable) {
                    Log.e(TAG, "variant download failed: $variantKey", t)
                    return@synchronized arrayOf("ERR|ModelDownload|" +
                            (t.message ?: "no message").replace("|", " "))
                }
                runBlocking {
                    eng.setLanguageVariant(variant.first, variant.second)
                }
                currentVariant = variantKey
                Log.i(TAG, "rec variant → $variantKey (lang=$lang)")
            }
            val res = runBlocking { eng.recognize(png) }
            val items = res.results
            val out = ArrayList<String>(items.size + 1)
            out.add("META|$lang|${items.size}")
            for (item in items) {
                val sb = StringBuilder()
                for (p in item.box.points) {
                    if (sb.isNotEmpty()) sb.append(',')
                    sb.append(fmt(p.x)).append(',').append(fmt(p.y))
                }
                val text = item.text
                    .replace("|", " ")
                    .replace("\r", " ")
                    .replace("\n", " ")
                    .trim()
                out.add("0|" + String.format(java.util.Locale.US, "%.4f",
                        item.confidence) +
                        "|" + sb + "|" + text + "|0")
            }
            out.toTypedArray()
        } catch (t: Throwable) {
            Log.e(TAG, "recognize failed", t)
            arrayOf("ERR|" + t.javaClass.simpleName + "|" +
                    (t.message ?: "no message").replace("|", " "))
        }
    }

    @JvmStatic
    fun sdkInfo(): String =
        "RapidOCR ONNX (RapidOcrAndroidOnnx pipeline) — " +
                "PP-OCRv6 (det=small + rec=MEDIUM)"

    private fun fmt(v: Float): String =
        if (v == v.toLong().toFloat()) v.toLong().toString()
        else String.format(java.util.Locale.US, "%.2f", v)
}
