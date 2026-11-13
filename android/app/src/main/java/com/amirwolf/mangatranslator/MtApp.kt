package com.amirwolf.mangatranslator

import android.app.Application
import android.content.Context

class MtApp : Application() {

    companion object {
        @Volatile
        private var appCtx: Context? = null

        @JvmStatic
        fun context(): Context? = appCtx
    }

    override fun onCreate() {
        super.onCreate()
        appCtx = applicationContext
        PaddleOcrBridge.hold(applicationContext)
    }
}
