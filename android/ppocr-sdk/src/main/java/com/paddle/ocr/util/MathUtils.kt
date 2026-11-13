
package com.paddle.ocr.util

import kotlin.math.floor

object MathUtils {

    fun roundHalfToEven(value: Double): Int {
        val floored = floor(value)
        val diff = value - floored
        return when {
            diff < 0.5 -> floored.toInt()
            diff > 0.5 -> floored.toInt() + 1
            floored.toInt() % 2 == 0 -> floored.toInt()
            else -> floored.toInt() + 1
        }
    }
}
