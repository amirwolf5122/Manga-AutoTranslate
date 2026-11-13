

package com.paddle.ocr.util

interface OcrProgressSink {
    fun onProgress(line: String)
}
