package com.example.fcmserverdemo

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.os.Build

object NotificationChannels {
    const val CHANNEL_SERVER_TASK = "server_task_updates"

    fun ensureServerTaskChannel(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_SERVER_TASK,
                "Server Task Updates",
                NotificationManager.IMPORTANCE_HIGH
            )
            channel.description = "通知服务器端任务进度与完成状态"

            val nm = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            nm.createNotificationChannel(channel)
        }
    }
}
