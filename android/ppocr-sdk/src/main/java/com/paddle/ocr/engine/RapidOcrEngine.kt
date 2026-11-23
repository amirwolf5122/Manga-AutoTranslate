
package com.paddle.ocr.engine

import android.content.Context
import android.graphics.Bitmap
import com.paddle.ocr.EngineConfig
import com.paddle.ocr.PaddleOCRConfig
import com.paddle.ocr.model.ModelConfig
import com.paddle.ocr.model.OCRError
import com.paddle.ocr.model.OCRResult
import com.paddle.ocr.postprocess.BoxSorter
import com.paddle.ocr.postprocess.CTCDecoder
import com.paddle.ocr.postprocess.QuadTextCrop
import com.paddle.ocr.preprocess.RecPreprocessor
import com.paddle.ocr.util.BitmapUtils
import org.opencv.core.Core
import org.opencv.core.CvType
import org.opencv.core.Mat
import org.opencv.core.Scalar
import org.opencv.core.Size
import org.opencv.imgproc.Imgproc

data class RapidOcrParams(
    val maxSideLen: Int = 960,
    val detThresh: Float = 0.3f,
    val boxScoreThresh: Float = 0.5f,
    val unclipRatio: Float = 1.6f,
    val doAngle: Boolean = true,
    val angleScoreThresh: Float = 0.9f,
    val recBatchSize: Int = 1,
    val recScoreThresh: Float = 0.0f,
) {
    internal fun toPaddleConfig(): PaddleOCRConfig = PaddleOCRConfig(
        detLimitSideLen = maxSideLen,
        detLimitType = "max",
        detThresh = detThresh,
        detBoxThresh = boxScoreThresh,
        detUnclipRatio = unclipRatio,
        detUseDilation = true,
        recBatchSize = recBatchSize,
        recScoreThresh = recScoreThresh,
    )
}

class RapidOcrEngine(
    context: Context,
    engineConfig: EngineConfig,
    detModelAsset: String,
    clsModelAsset: String,
    recModelAsset: String,
    recDictAsset: String,
    private val params: RapidOcrParams = RapidOcrParams(),
) {
    private val appContext: Context = context.applicationContext
    private val ortManager = ORTSessionManager(appContext, engineConfig)
    private val detectionEngine: DetectionEngine
    private val recLock = Any()

    @Volatile
    private var characters: List<String> = emptyList()

    @Volatile
    private var recAssetPath: String = recModelAsset

    val coldLoadTimeMs: Long get() = ortManager.coldLoadTimeMs

    init {
        try {
            ortManager.loadModels(detModelAsset, recModelAsset)
            if (clsModelAsset.isNotBlank()) {
                ortManager.loadClsModel(clsModelAsset)
            }
            characters = loadDict(appContext, recDictAsset)
        } catch (t: Throwable) {
            ortManager.release()
            throw t
        }
        detectionEngine = DetectionEngine(ortManager, params.toPaddleConfig())
    }

    fun setLanguageVariant(recModelAsset: String, recDictAsset: String) =
        synchronized(recLock) {
            if (recModelAsset == recAssetPath) return
            ortManager.loadRecModel(recModelAsset)
            characters = loadDict(appContext, recDictAsset)
            recAssetPath = recModelAsset
        }

    fun run(bitmap: Bitmap): OCREngineResult {
        val srcMat = BitmapUtils.bitmapToBGRMat(bitmap)
        return runWithOwnedMat(srcMat)
    }

    fun run(imageBytes: ByteArray): OCREngineResult {
        val srcMat = BitmapUtils.imdecodeBGR(imageBytes)
        if (srcMat.empty()) {
            srcMat.release()
            throw OCRError.InvalidImage()
        }
        return runWithOwnedMat(srcMat)
    }

    private fun runWithOwnedMat(srcMat: Mat): OCREngineResult =
        try {
            run(srcMat)
        } finally {
            srcMat.release()
        }

    private fun run(srcMat: Mat): OCREngineResult {
        val totalStart = System.currentTimeMillis()
        val detResult = detectionEngine.detect(srcMat)
        val boxes = detResult.boxes

        if (boxes.isEmpty()) {
            return OCREngineResult(
                results = emptyList(),
                detectionTimeMs = detResult.timeMs,
                recognitionTimeMs = 0,
                totalTimeMs = System.currentTimeMillis() - totalStart,
                lineCount = 0,
                detPreprocessMs = detResult.preprocessMs,
                detInferenceMs = detResult.inferenceMs,
                detPostprocessMs = detResult.postprocessMs,
                detInputShape = detResult.inputShape,
                coldLoadTimeMs = ortManager.coldLoadTimeMs,
            )
        }

        val sortedBoxes = BoxSorter.sortInReadingOrder(boxes)
        val crops = mutableListOf<Mat>()
        val cropBoxIndices = mutableListOf<Int>()
        try {
            for ((idx, box) in sortedBoxes.withIndex()) {
                val crop = QuadTextCrop.crop(srcMat, box)
                if (crop.rows() > 0 && crop.cols() > 0) {
                    crops.add(crop)
                    cropBoxIndices.add(idx)
                } else {
                    crop.release()
                }
            }

            if (params.doAngle && ortManager.hasCls() && crops.isNotEmpty()) {
                try {
                    val flags = classifyAngles(crops)
                    for (i in crops.indices) {
                        if (flags[i]) {
                            val rotated = Mat()
                            Core.flip(crops[i], rotated, -1)
                            crops[i].release()
                            crops[i] = rotated
                        }
                    }
                } catch (_: OCRError) {
                }
            }

            var recPreMs = 0L
            var recInfMs = 0L
            var recPostMs = 0L
            val recShapes = mutableListOf<List<Int>>()
            val allResults = mutableListOf<OCRResult>()
            val batchSize = params.recBatchSize.coerceAtLeast(1)
            var i = 0
            synchronized(recLock) {
                while (i < crops.size) {
                    val batchEnd = minOf(i + batchSize, crops.size)
                    val batch = crops.subList(i, batchEnd)
                    if (batch.isNotEmpty()) {
                        val preStart = System.currentTimeMillis()
                        val pre = RecPreprocessor.preprocessBatch(batch)
                        recPreMs += System.currentTimeMillis() - preStart
                        val infStart = System.currentTimeMillis()
                        val (outData, outShape) = ortManager.runRecognition(pre.tensorData, pre.shape)
                        val postStart = System.currentTimeMillis()
                        val decoded = CTCDecoder.decode(outData, outShape, characters)
                        recPostMs += System.currentTimeMillis() - postStart
                        recInfMs += postStart - infStart
                        recShapes.add(pre.shape.map { it.toInt() })
                        for (j in decoded.indices) {
                            val (text, confidence) = decoded[j]
                            if (confidence >= params.recScoreThresh) {
                                allResults.add(
                                    OCRResult(
                                        box = sortedBoxes[cropBoxIndices[i + j]],
                                        text = text,
                                        confidence = confidence,
                                    )
                                )
                            }
                        }
                    }
                    i = batchEnd
                }
            }

            val totalElapsed = System.currentTimeMillis() - totalStart
            return OCREngineResult(
                results = allResults,
                detectionTimeMs = detResult.timeMs,
                recognitionTimeMs = recInfMs + recPostMs,
                totalTimeMs = totalElapsed,
                lineCount = allResults.size,
                detPreprocessMs = detResult.preprocessMs,
                detInferenceMs = detResult.inferenceMs,
                detPostprocessMs = detResult.postprocessMs,
                recPreprocessMs = recPreMs,
                recInferenceMs = recInfMs,
                recPostprocessMs = recPostMs,
                pipelineOverheadMs = totalElapsed - detResult.timeMs - recInfMs - recPostMs,
                coldLoadTimeMs = ortManager.coldLoadTimeMs,
                detInputShape = detResult.inputShape,
                recInputShapes = recShapes,
            )
        } finally {
            crops.forEach { it.release() }
        }
    }

    private fun classifyAngles(crops: List<Mat>): BooleanArray {
        val clsW = 192
        val clsH = 48
        val n = crops.size
        val tensor = FloatArray(n * 3 * clsH * clsW)
        for (i in 0 until n) {
            val resized = Mat()
            Imgproc.resize(crops[i], resized, Size(clsW.toDouble(), clsH.toDouble()))
            val floatMat = Mat(clsH, clsW, CvType.CV_32FC3)
            resized.convertTo(floatMat, CvType.CV_32F)
            resized.release()
            Core.divide(floatMat, Scalar(127.5, 127.5, 127.5), floatMat)
            Core.subtract(floatMat, Scalar(1.0, 1.0, 1.0), floatMat)
            val channels = mutableListOf<Mat>()
            Core.split(floatMat, channels)
            val channelSize = clsH * clsW
            for (c in 0..2) {
                val buf = FloatArray(channelSize)
                channels[c].get(0, 0, buf)
                System.arraycopy(buf, 0, tensor, (i * 3 + c) * channelSize, channelSize)
                channels[c].release()
            }
            floatMat.release()
        }
        val (outData, outShape) = ortManager.runClassification(
            tensor, longArrayOf(n.toLong(), 3, clsH.toLong(), clsW.toLong()),
        )
        val flags = BooleanArray(n)
        if (outData.size < n * 2) return flags
        for (b in 0 until n) {
            val s0 = outData[b * 2]
            val s1 = outData[b * 2 + 1]
            flags[b] = s1 > s0 && s1 >= params.angleScoreThresh
        }
        return flags
    }

    fun release() {
        synchronized(recLock) {
            ortManager.release()
        }
    }

    private fun loadDict(context: Context, dictAsset: String): List<String> {
        val content = try {
            com.paddle.ocr.util.ModelSource.text(context, dictAsset)
        } catch (t: Throwable) {
            throw OCRError.ConfigParseFailed(dictAsset, t)
        }
        return ModelConfig.fromDictText(content, dictAsset).characterList
    }
}
