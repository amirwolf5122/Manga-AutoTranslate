
package com.paddle.ocr.engine

import com.paddle.ocr.model.OCRResult

data class OCREngineResult(
    val results: List<OCRResult>,
    val detectionTimeMs: Long,
    val recognitionTimeMs: Long,
    val totalTimeMs: Long,
    val lineCount: Int,
    val detPreprocessMs: Long = 0,
    val detInferenceMs: Long = 0,
    val detPostprocessMs: Long = 0,
    val recPreprocessMs: Long = 0,
    val recInferenceMs: Long = 0,
    val recPostprocessMs: Long = 0,
    val pipelineOverheadMs: Long = 0,
    val coldLoadTimeMs: Long = 0,
    val detInputShape: List<Int> = emptyList(),
    val recInputShapes: List<List<Int>> = emptyList(),
    val perLineRecMs: List<Long> = emptyList(),
)
