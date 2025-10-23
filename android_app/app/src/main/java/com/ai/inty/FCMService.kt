package com.ai.inty

import ai.sxwl.android.utils.LogUtils
import android.annotation.SuppressLint
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage

/** Firebase 消息推送服务 */
class FCMService : FirebaseMessagingService() {

    override fun onMessageReceived(remoteMessage: RemoteMessage) {
        // 1. 处理数据消息（应用前后台均触发）
        if (remoteMessage.data.isNotEmpty()) {
            LogUtils.i("FCMService onMessageReceived: " + remoteMessage.data)
        }

        // 2. 处理通知消息（仅前台触发；后台时由系统自动显示）
        if (remoteMessage.notification != null) {
            val title = remoteMessage.notification!!.title
            val body = remoteMessage.notification!!.body
            if (title != null) {
                if (body != null) {
                    showNotification(title, body)
                }
            }
        }
    }

    override fun onNewToken(token: String) {
        // 将新Token发送至服务器

        //        sendTokenToServer(token)
    }

    @SuppressLint("MissingPermission")
    private fun showNotification(title: String, body: String) {
        val builder: NotificationCompat.Builder =
            NotificationCompat.Builder(this, "channel_id")
                .setSmallIcon(R.drawable.app_icon)
                .setContentTitle(title)
                .setContentText(body)
                .setPriority(NotificationCompat.PRIORITY_DEFAULT)

        // Android 8.0+ 需创建通知渠道
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel =
                NotificationChannel(
                    "channel_id",
                    "Channel Name",
                    NotificationManager.IMPORTANCE_DEFAULT,
                )
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }

        NotificationManagerCompat.from(this).notify(0, builder.build())
    }
}
