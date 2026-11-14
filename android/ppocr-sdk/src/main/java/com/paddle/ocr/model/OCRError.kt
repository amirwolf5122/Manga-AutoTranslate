
package com.paddle.ocr.model

sealed class OCRError(message: String, cause: Throwable? = null) : Exception(message, cause) {
    class ModelNotFound(modelPath: String, cause: Throwable? = null) : OCRError("Model not found: $modelPath", cause)
    class ModelLoadFailed(modelName: String, cause: Throwable) : OCRError("Failed to load $modelName model", cause)
    class ConfigParseFailed(path: String, cause: Throwable? = null) : OCRError("Failed to parse config: $path", cause)
    class InvalidImage : OCRError("Input image is empty or invalid")
    class InferenceFailed(stage: String, cause: Throwable) : OCRError("Inference failed at stage '$stage'", cause)
    class DecodeError(message: String, cause: Throwable? = null) : OCRError(message, cause)
}
