package com.amirwolf.mangatranslator

import android.graphics.BitmapFactory
import com.google.android.gms.tasks.Tasks
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.TextRecognizer
import com.google.mlkit.vision.text.chinese.ChineseTextRecognizerOptions
import com.google.mlkit.vision.text.japanese.JapaneseTextRecognizerOptions
import com.google.mlkit.vision.text.korean.KoreanTextRecognizerOptions
import com.google.mlkit.vision.text.latin.TextRecognizerOptions as LatinTextRecognizerOptions


object MlKitBridge {

    private var client: TextRecognizer? = null
    private var clientLang: String? = null

    @Synchronized
    private fun getClient(lang: String): TextRecognizer {
        val cur = client
        if (cur != null && clientLang == lang) return cur
        try {
            cur?.close()
        } catch (_: Exception) {
        }
        val opts = when (lang) {
            "ja" -> JapaneseTextRecognizerOptions.Builder().build()
            "ko" -> KoreanTextRecognizerOptions.Builder().build()
            "zh" -> ChineseTextRecognizerOptions.Builder().build()
            else -> LatinTextRecognizerOptions.Builder().build()
        }
        val c = TextRecognition.getClient(opts)
        client = c
        clientLang = lang
        return c
    }

    @JvmStatic
    @Synchronized
    fun recognize(png: ByteArray, lang: String): Array<String> {
        val bmp = BitmapFactory.decodeByteArray(png, 0, png.size)
            ?: return arrayOf()
        return try {
            val img = InputImage.fromBitmap(bmp, 0)
            val result = Tasks.await(getClient(lang).process(img))
            val out = ArrayList<String>()
            for (block in result.textBlocks) {
                for (line in block.lines) {
                    val t = line.text.trim()
                    if (t.isEmpty()) continue
                    val bb = line.boundingBox ?: continue
                    val conf = try {
                        val c = line.confidence
                        if (c != null && c > 0f) c else 1.0f
                    } catch (_: Exception) {
                        1.0f
                    }
                    val box = ("" + bb.left + "," + bb.top + "," +
                            bb.right + "," + bb.top + "," +
                            bb.right + "," + bb.bottom + "," +
                            bb.left + "," + bb.bottom)
                    out.add(String.format("%.4f|%s|%s", conf, box, t))
                }
            }
            out.toTypedArray()
        } catch (e: Exception) {
            throw RuntimeException("ML Kit: " + (e.message ?: e.toString()), e)
        } finally {
            try {
                bmp.recycle()
            } catch (_: Exception) {
            }
        }
    }
}
