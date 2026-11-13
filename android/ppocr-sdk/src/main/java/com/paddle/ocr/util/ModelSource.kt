

package com.paddle.ocr.util

import android.content.Context
import java.io.File
import java.io.FileNotFoundException

object ModelSource {

    @JvmStatic
    fun exists(context: Context, path: String): Boolean =
        try {
            context.assets.open(path).use { true }
        } catch (_: Throwable) {
            val f = File(context.filesDir, path)
            f.isFile && f.length() > 0L
        }

    @JvmStatic
    fun bytes(context: Context, path: String): ByteArray =
        try {
            context.assets.open(path).use { it.readBytes() }
        } catch (_: Throwable) {
            val f = File(context.filesDir, path)
            if (f.isFile && f.length() > 0L) {
                f.readBytes()
            } else {
                throw FileNotFoundException(
                    "model source not found: $path (assets و filesDir هر دو خالی)")
            }
        }

    @JvmStatic
    fun text(context: Context, path: String): String =
        String(bytes(context, path), Charsets.UTF_8)
}
