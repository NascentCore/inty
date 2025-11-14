package com.example.fcmtokengetter

import android.app.NotificationManager
import android.content.Context
import android.util.Log
import androidx.core.app.NotificationCompat
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import kotlin.random.Random

/**
 * FCM 消息服务，用于监听 token 刷新和处理推送消息
 */
class FCMTokenService : FirebaseMessagingService() {

    override fun onCreate() {
        super.onCreate()
        // 确保通知渠道已创建
        NotificationChannels.ensureDefaultChannel(this)
    }

    override fun onNewToken(token: String) {
        super.onNewToken(token)
        Log.i(TAG, "FCM Token 已刷新: $token")
        // 注意：这里只是记录日志，实际应用中应该自动重新注册到服务器
        // 可以通过 SharedPreferences 保存配置，然后调用 TokenService.registerTokenToServer
    }

    override fun onMessageReceived(remoteMessage: RemoteMessage) {
        super.onMessageReceived(remoteMessage)
        Log.i(TAG, "收到 FCM 消息: ${remoteMessage.messageId}")
        
        // 确保通知渠道已创建
        NotificationChannels.ensureDefaultChannel(this)
        
        // 获取通知内容
        val title = remoteMessage.notification?.title ?: "FCM 通知"
        val body = remoteMessage.notification?.body ?: "收到新消息"
        
        // 创建并显示通知
        val notification = NotificationCompat.Builder(this, NotificationChannels.CHANNEL_DEFAULT)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle(title)
            .setContentText(body)
            .setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .build()
        
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.notify(Random.nextInt(), notification)
        
        Log.i(TAG, "通知已显示: title=$title, body=$body")
    }

    companion object {
        private const val TAG = "FCMTokenService"
    }
}

