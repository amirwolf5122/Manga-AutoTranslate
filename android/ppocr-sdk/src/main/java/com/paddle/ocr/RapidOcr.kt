
package com.paddle.ocr

import android.content.Context
import android.graphics.Bitmap
import com.paddle.ocr.engine.OCREngineResult
import com.paddle.ocr.engine.RapidOcrEngine
import com.paddle.ocr.engine.RapidOcrParams
import com.paddle.ocr.model.OCRError
import com.paddle.ocr.model.OCRRunResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class RapidOcr private constructor(
    private val engine: RapidOcrEngine,
) {
    val coldLoadTimeMs: Long get() = engine.coldLoadTimeMs

    companion object {

        suspend fun create(
            context: Context,
            engineConfig: EngineConfig = EngineConfig(),
            detModelAssetPath: String,
            clsModelAssetPath: String,
            recModelAssetPath: String,
            recDictAssetPath: String,
            params: RapidOcrParams = RapidOcrParams(),
        ): RapidOcr {
            val appContext = context.applicationContext
            return withContext(Dispatchers.IO) {
                val engine = RapidOcrEngine(
                    context = appContext,
                    engineConfig = engineConfig,
                    detModelAsset = detModelAssetPath,
                    clsModelAsset = clsModelAssetPath,
                    recModelAsset = recModelAssetPath,
                    recDictAsset = recDictAssetPath,
                    params = params,
                )
                RapidOcr(engine)
            }
        }
    }

    suspend fun recognize(bitmap: Bitmap): OCRRunResult {
        if (bitmap.width == 0 || bitmap.height == 0) {
            throw OCRError.InvalidImage()
        }
        return recognizeResult { engine.run(bitmap) }
    }

    suspend fun recognize(imageBytes: ByteArray): OCRRunResult {
        if (imageBytes.isEmpty()) {
            throw OCRError.InvalidImage()
        }
        return recognizeResult { engine.run(imageBytes) }
    }

    suspend fun setLanguageVariant(recModelAssetPath: String, recDictAssetPath: String) {
        withContext(Dispatchers.IO) {
            engine.setLanguageVariant(recModelAssetPath, recDictAssetPath)
        }
    }

    private suspend fun recognizeResult(runEngine: () -> OCREngineResult): OCRRunResult {
        return withContext(Dispatchers.IO) {
            val result = runEngine()
            OCRRunResult(
                results = result.results,
                detectionTimeMs = result.detectionTimeMs,
                recognitionTimeMs = result.recognitionTimeMs,
                totalTimeMs = result.totalTimeMs,
                lineCount = result.lineCount,
                detPreprocessMs = result.detPreprocessMs,
                detInferenceMs = result.detInferenceMs,
                detPostprocessMs = result.detPostprocessMs,
                recPreprocessMs = result.recPreprocessMs,
                recInferenceMs = result.recInferenceMs,
                recPostprocessMs = result.recPostprocessMs,
                pipelineOverheadMs = result.pipelineOverheadMs,
                coldLoadTimeMs = result.coldLoadTimeMs,
                detInputShape = result.detInputShape,
                recInputShapes = result.recInputShapes,
                perLineRecMs = result.perLineRecMs,
            )
        }
    }

    suspend fun release() {
        withContext(Dispatchers.IO) {
            engine.release()
        }
    }
}
