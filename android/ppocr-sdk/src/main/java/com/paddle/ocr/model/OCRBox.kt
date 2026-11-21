
package com.paddle.ocr.model

import android.graphics.PointF

data class OCRBox(
    val points: List<PointF>,
) {
    init {
        require(points.size == 4) { "OCRBox must have exactly 4 points, got ${points.size}" }
    }
}
