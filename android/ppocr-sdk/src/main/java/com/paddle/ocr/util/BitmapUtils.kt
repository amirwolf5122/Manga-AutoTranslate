
package com.paddle.ocr.util

import android.graphics.Bitmap
import org.opencv.android.Utils
import org.opencv.core.CvType
import org.opencv.core.Mat
import org.opencv.core.MatOfByte
import org.opencv.imgcodecs.Imgcodecs
import org.opencv.imgproc.Imgproc

object BitmapUtils {

    fun imdecodeBGR(imageBytes: ByteArray): Mat {
        val encoded = MatOfByte(*imageBytes)
        return try {
            Imgcodecs.imdecode(encoded, Imgcodecs.IMREAD_COLOR)
        } finally {
            encoded.release()
        }
    }

    fun bitmapToBGRMat(bitmap: Bitmap): Mat {
        return bitmapToMat(bitmap, Imgproc.COLOR_RGBA2BGR)
    }

    fun bitmapToRGBMat(bitmap: Bitmap): Mat {
        return bitmapToMat(bitmap, Imgproc.COLOR_RGBA2RGB)
    }

    fun bgrMatToBitmap(mat: Mat): Bitmap {
        val rgba = Mat()
        return try {
            Imgproc.cvtColor(mat, rgba, Imgproc.COLOR_BGR2RGBA)
            Bitmap.createBitmap(rgba.cols(), rgba.rows(), Bitmap.Config.ARGB_8888).also { bitmap ->
                Utils.matToBitmap(rgba, bitmap)
            }
        } finally {
            rgba.release()
        }
    }

    private fun bitmapToMat(bitmap: Bitmap, colorConversionCode: Int): Mat {
        val bmp = bitmap.copy(Bitmap.Config.ARGB_8888, false)
        val rgba = Mat(bmp.height, bmp.width, CvType.CV_8UC4)
        val dst = Mat()
        return try {
            Utils.bitmapToMat(bmp, rgba)
            Imgproc.cvtColor(rgba, dst, colorConversionCode)
            dst
        } catch (t: Throwable) {
            dst.release()
            throw t
        } finally {
            bmp.recycle()
            rgba.release()
        }
    }
}
