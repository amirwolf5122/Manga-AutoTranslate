package com.amirwolf.mangatranslator

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder

class TranslationService : Service() {

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        current = this
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        try {
            goForeground()
        } catch (_: Exception) {
            try {
                stopSelf()
            } catch (_: Exception) {
            }
        }
        return START_NOT_STICKY
    }

    override fun onTaskRemoved(rootIntent: Intent?) {
        TranslationService.hardStopAndExit()
        try {
            stopForeground(true)
        } catch (_: Exception) {
        }
        try {
            stopSelf()
        } catch (_: Exception) {
        }
        if (current === this) current = null
        super.onTaskRemoved(rootIntent)
    }

    override fun onDestroy() {
        if (current === this) current = null
        super.onDestroy()
    }

    private fun goForeground() {
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= 26) {
            nm.createNotificationChannel(
                NotificationChannel(
                    CH_ID, "ترجمه در جریان",
                    NotificationManager.IMPORTANCE_LOW
                )
            )
        }
        startFg(buildNotif(0, 0, ""))
    }

    private fun startFg(n: Notification) {
        if (Build.VERSION.SDK_INT >= 29) {
            startForeground(
                NOTIF_ID, n,
                ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
            )
        } else {
            @Suppress("DEPRECATION")
            startForeground(NOTIF_ID, n)
        }
    }

    private fun buildNotif(done: Int, total: Int, phase: String): Notification {
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= 26) {
            nm.createNotificationChannel(
                NotificationChannel(
                    CH_ID, "ترجمه در جریان",
                    NotificationManager.IMPORTANCE_LOW
                )
            )
        }
        val ph = phase.ifBlank { "در حال ترجمه…" }
        val pct = if (total > 0 && done > 0) done * 100 / total else 0
        val txt = if (total > 0 && done > 0)
            "$ph — صفحهٔ $done از $total (٪$pct)" else ph
        val b = if (Build.VERSION.SDK_INT >= 26) {
            Notification.Builder(this, CH_ID)
        } else {
            @Suppress("DEPRECATION") Notification.Builder(this)
        }
        b.setContentTitle("مانگا مترجم")
            .setContentText(txt)
            .setSmallIcon(R.drawable.ic_notif)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
        if (total > 0) {
            b.setProgress(total, done.coerceIn(0, total), false)
        } else {
            b.setProgress(0, 0, true)
        }
        return b.build()
    }

    private fun notifyProgress(done: Int, total: Int, phase: String) {
        try {
            val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            nm.notify(NOTIF_ID, buildNotif(done, total, phase))
        } catch (_: Exception) {
        }
    }

    companion object {
        private const val CH_ID = "translation"
        private const val NOTIF_ID = 4150

        @Volatile
        var current: TranslationService? = null
            private set

        @JvmStatic
        fun updateProgress(done: Int, total: Int, phase: String) {
            try {
                current?.notifyProgress(done, total, phase)
            } catch (_: Exception) {
            }
        }

        @Volatile
        private var hardStopDone = false

        @JvmStatic
        fun hardStopAndExit() {
            if (hardStopDone) return
            hardStopDone = true
            Thread {
                try {
                    if (com.chaquo.python.Python.isStarted()) {
                        com.chaquo.python.Python.getInstance()
                            .getModule("native_bridge").callAttr("cancel")
                    }
                } catch (_: Exception) {
                }
                try {
                    Thread.sleep(1200)
                } catch (_: Exception) {
                }
                try {
                    android.os.Process.killProcess(android.os.Process.myPid())
                } catch (_: Exception) {
                }
                try {
                    java.lang.System.exit(0)
                } catch (_: Exception) {
                }
            }.start()
        }
    }
}
