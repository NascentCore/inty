package com.example.fcmserverdemo

import android.app.NotificationManager
import android.content.Context
import android.util.Log
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import androidx.core.app.NotificationCompat
import kotlin.random.Random

class FCMService : FirebaseMessagingService() {
    override fun onNewToken(token: String) {
        super.onNewToken(token)
        Log.i(TAG, "FCM token: $token")
        // TODO: 上报 token 到你的服务器，以便服务端能向该设备推送
    }

    override fun onMessageReceived(message: RemoteMessage) {
        super.onMessageReceived(message)
        val title = message.notification?.title ?: message.data["title"] ?: DEFAULT_TITLE
        val body = message.notification?.body ?: message.data["body"] ?: DEFAULT_BODY

        NotificationChannels.ensureServerTaskChannel(this)

        val notification = NotificationCompat.Builder(this, NotificationChannels.CHANNEL_SERVER_TASK)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle(title)
            .setContentText(body)
            .setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .build()

        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.notify(Random.nextInt(), notification)
    }

    companion object {
        private const val TAG = "FCMService"
        private const val DEFAULT_TITLE = "任务完成"
        private const val DEFAULT_BODY = "服务器端任务已完成"
    }
}
