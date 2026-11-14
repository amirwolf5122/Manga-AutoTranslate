
package com.paddle.ocr.engine

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import com.paddle.ocr.EngineConfig
import com.paddle.ocr.model.OCRError
import java.nio.FloatBuffer

class ORTSessionManager(
    private val context: Context,
    private val config: EngineConfig,
) {
    private var env: OrtEnvironment? = null
    private var detSession: OrtSession? = null
    private var recSession: OrtSession? = null
    private var clsSession: OrtSession? = null
    private var detInputName: String = "x"
    private var recInputName: String = "x"
    private var clsInputName: String = "x"
    var coldLoadTimeMs: Long = 0
        private set

    fun hasCls(): Boolean = clsSession != null

    fun loadClsModel(clsAssetPath: String) {
        val ortEnv = env
            ?: throw OCRError.ModelLoadFailed("cls", Exception("Environment not initialized"))
        val clsBytes = readModelAsset(clsAssetPath)
        val opts = OrtSession.SessionOptions().apply {
            setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT)
            setIntraOpNumThreads(config.numThreads)
        }
        try {
            clsSession = try {
                ortEnv.createSession(clsBytes, opts)
            } catch (t: Throwable) {
                throw OCRError.ModelLoadFailed("cls", t)
            }
            clsInputName = try {
                clsSession!!.inputNames.iterator().next()
            } catch (t: Throwable) {
                throw OCRError.ModelLoadFailed("cls", t)
            }
        } finally {
            opts.close()
        }
    }

    fun loadRecModel(recAssetPath: String) {
        val ortEnv = env
            ?: throw OCRError.ModelLoadFailed("recognition", Exception("Environment not initialized"))
        val recBytes = readModelAsset(recAssetPath)
        val opts = OrtSession.SessionOptions().apply {
            setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT)
            setIntraOpNumThreads(config.numThreads)
        }
        var fresh: OrtSession? = null
        try {
            fresh = try {
                ortEnv.createSession(recBytes, opts)
            } catch (t: Throwable) {
                throw OCRError.ModelLoadFailed("recognition", t)
            }
            val freshInputName = try {
                fresh!!.inputNames.iterator().next()
            } catch (t: Throwable) {
                throw OCRError.ModelLoadFailed("recognition", t)
            }
            val old = recSession
            recSession = fresh
            recInputName = freshInputName
            fresh = null
            old?.close()
        } finally {
            if (fresh != null) {
                try { fresh.close() } catch (_: Throwable) {}
            }
            opts.close()
        }
    }

    fun runClassification(input: FloatArray, shape: LongArray): Pair<FloatArray, LongArray> {
        val session = clsSession
            ?: throw OCRError.ModelLoadFailed("cls", Exception("Session not initialized"))
        val ortEnv = env
            ?: throw OCRError.ModelLoadFailed("cls", Exception("Environment not initialized"))
        return runSession(ortEnv, session, clsInputName, input, shape, "cls")
    }

    fun loadModels(detAssetPath: String, recAssetPath: String) {
        val loadStart = System.currentTimeMillis()
        env = OrtEnvironment.getEnvironment()
        val opts = OrtSession.SessionOptions().apply {
            setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT)
            setIntraOpNumThreads(config.numThreads)
        }
        try {
            val ortEnv = env ?: throw OCRError.ModelLoadFailed("OCR", Exception("Environment not initialized"))
            val detBytes = readModelAsset(detAssetPath)
            val recBytes = readModelAsset(recAssetPath)
            try {
                detSession = ortEnv.createSession(detBytes, opts)
            } catch (t: Throwable) {
                throw OCRError.ModelLoadFailed("detection", t)
            }
            try {
                recSession = ortEnv.createSession(recBytes, opts)
            } catch (t: Throwable) {
                detSession?.close()
                detSession = null
                throw OCRError.ModelLoadFailed("recognition", t)
            }

            detInputName = try {
                detSession!!.inputNames.iterator().next()
            } catch (t: Throwable) {
                throw OCRError.ModelLoadFailed("detection", t)
            }
            recInputName = try {
                recSession!!.inputNames.iterator().next()
            } catch (t: Throwable) {
                throw OCRError.ModelLoadFailed("recognition", t)
            }
            coldLoadTimeMs = System.currentTimeMillis() - loadStart
        } finally {
            opts.close()
        }
    }

    fun runDetection(input: FloatArray, shape: LongArray): Pair<FloatArray, LongArray> {
        val session = detSession
            ?: throw OCRError.ModelLoadFailed("detection", Exception("Session not initialized"))
        val ortEnv = env
            ?: throw OCRError.ModelLoadFailed("detection", Exception("Environment not initialized"))
        return runSession(ortEnv, session, detInputName, input, shape, "detection")
    }

    fun runRecognition(input: FloatArray, shape: LongArray): Pair<FloatArray, LongArray> {
        val session = recSession
            ?: throw OCRError.ModelLoadFailed("recognition", Exception("Session not initialized"))
        val ortEnv = env
            ?: throw OCRError.ModelLoadFailed("recognition", Exception("Environment not initialized"))
        return runSession(ortEnv, session, recInputName, input, shape, "recognition")
    }

    fun release() {
        try {
            detSession?.close()
        } finally {
            detSession = null
            try {
                recSession?.close()
            } finally {
                recSession = null
                try {
                    clsSession?.close()
                } finally {
                    clsSession = null
                    env = null
                }
            }
        }
    }

    private fun readModelAsset(assetPath: String): ByteArray {
        return try {
            com.paddle.ocr.util.ModelSource.bytes(context, assetPath)
        } catch (t: Throwable) {
            throw OCRError.ModelNotFound(assetPath, t)
        }
    }

    private fun runSession(
        ortEnv: OrtEnvironment,
        session: OrtSession,
        inputName: String,
        input: FloatArray,
        shape: LongArray,
        modelName: String,
    ): Pair<FloatArray, LongArray> {
        val tensor = try {
            OnnxTensor.createTensor(ortEnv, FloatBuffer.wrap(input), shape)
        } catch (t: Throwable) {
            throw OCRError.InferenceFailed(modelName, t)
        }
        val result = try {
            try {
                session.run(mapOf(inputName to tensor))
            } catch (t: Throwable) {
                throw OCRError.InferenceFailed(modelName, t)
            }
        } finally {
            tensor.close()
        }

        return try {
            try {
                val outputName = session.outputNames.iterator().next()
                val ortValue = result.get(outputName)
                    .orElseThrow { Exception("No output tensor found") }
                val outputTensor = ortValue as? OnnxTensor
                    ?: throw Exception("Output is not an ONNX tensor")
                Pair(copyFloatBuffer(outputTensor.floatBuffer), outputTensor.info.shape)
            } catch (t: Throwable) {
                throw OCRError.InferenceFailed(modelName, t)
            }
        } finally {
            result.close()
        }
    }

    private fun copyFloatBuffer(buffer: FloatBuffer): FloatArray {
        val duplicate = buffer.duplicate()
        duplicate.rewind()
        val output = FloatArray(duplicate.remaining())
        duplicate.get(output)
        return output
    }
}
