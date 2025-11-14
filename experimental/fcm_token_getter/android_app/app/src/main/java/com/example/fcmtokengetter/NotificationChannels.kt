package com.example.fcmtokengetter

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.os.Build

object NotificationChannels {
    const val CHANNEL_DEFAULT = "default"

    fun ensureDefaultChannel(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_DEFAULT,
                "默认通知",
                NotificationManager.IMPORTANCE_HIGH
            )
            channel.description = "FCM 推送通知渠道"
            channel.enableLights(true)
            channel.enableVibration(true)

            val nm = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            nm.createNotificationChannel(channel)
        }
    }
}


