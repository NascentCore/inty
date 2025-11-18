package com.ai.intellimate.notifications

import ai.sxwl.android.common.event.EventBus
import ai.sxwl.android.common.event.EventSubscriber
import ai.sxwl.android.common.event.PushNotificationEvent
import ai.sxwl.android.firebase.DirectBootStorage
import ai.sxwl.android.firebase.DirectBootUtils
import ai.sxwl.android.firebase.FCMConstants
import ai.sxwl.android.firebase.FCMService
import ai.sxwl.android.utils.AppUtils
import ai.sxwl.android.utils.LogUtils
import android.annotation.SuppressLint
import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.ai.intellimate.MainActivity
import com.ai.intellimate.chat.ChatActivity
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

/**
 * 推送通知管理器
 *
 * 负责处理所有推送通知相关的业务逻辑：
 * - 显示推送通知
 * - 处理通知点击导航
 * - 处理 Direct Boot 模式下的待处理消息
 * - 订阅 FCM 事件
 */
class PushNotificationManager private constructor(private val application: Application) {

    companion object {
        @Volatile private var INSTANCE: PushNotificationManager? = null

        /** 获取 PushNotificationManager 实例 */
        fun getInstance(context: Application): PushNotificationManager {
            return INSTANCE
                ?: synchronized(this) {
                    INSTANCE
                        ?: PushNotificationManager(context.applicationContext as Application).also {
                            INSTANCE = it
                        }
                }
        }
    }

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    /** 初始化推送通知管理器 订阅 FCM 事件并处理 Direct Boot 待处理消息 */
    fun initialize() {
        // 立即创建通知渠道，避免 Firebase 在应用启动时使用未创建的渠道
        createNotificationChannelIfNeeded()
        subscribeToPushNotificationEvents()
        handleDirectBootPendingMessages()
    }

    /** 订阅 FCM 推送通知事件 */
    private fun subscribeToPushNotificationEvents() {
        EventBus.subscribe(
            PushNotificationEvent.ShowNotification::class,
            object : EventSubscriber<PushNotificationEvent.ShowNotification> {
                override fun onEvent(event: PushNotificationEvent.ShowNotification) {
                    showNotification(event.title, event.body, event.data)
                }
            },
        )
    }

    /** 处理 Direct Boot 模式下保存的待处理消息 在用户解锁后（应用启动时）调用 */
    private fun handleDirectBootPendingMessages() {
        // 检查用户是否已解锁
        if (!DirectBootUtils.isUserUnlocked(application)) {
            LogUtils.d("PushNotificationManager", "用户未解锁，跳过处理 Direct Boot 待处理消息")
            return
        }

        // 异步处理，避免阻塞应用启动
        scope.launch {
            try {
                // 初始化 Direct Boot 存储（用户已解锁，可以访问）
                DirectBootStorage.initialize(application)

                // 调试：打印存储状态（仅在调试模式下）
                if (AppUtils.isAppDebug()) {
                    DirectBootStorage.debugPrintStatus(application)
                }

                // 获取待处理的消息
                val pendingMessages = DirectBootStorage.getPendingMessages(application)
                val messageCount = pendingMessages.size

                if (messageCount > 0) {
                    LogUtils.i(
                        "PushNotificationManager",
                        "发现 $messageCount 条 Direct Boot 模式下保存的待处理消息，开始处理",
                    )

                    // 处理每条消息
                    pendingMessages.forEach { message ->
                        try {
                            handlePendingMessage(message)
                        } catch (e: Exception) {
                            LogUtils.e(
                                "PushNotificationManager",
                                "处理待处理消息失败: messageId=${message.messageId}",
                                e,
                            )
                        }
                    }

                    // 清除已处理的消息
                    DirectBootStorage.clearPendingMessages(application)
                    LogUtils.i("PushNotificationManager", "Direct Boot 待处理消息处理完成，已清除")
                } else {
                    LogUtils.d("PushNotificationManager", "没有 Direct Boot 待处理消息")
                }
            } catch (e: Exception) {
                LogUtils.e("PushNotificationManager", "处理 Direct Boot 待处理消息失败", e)
            }
        }
    }

    /** 处理单条待处理消息 */
    private fun handlePendingMessage(message: DirectBootStorage.PendingMessage) {
        // 如果有标题和内容，显示通知
        if (!message.title.isNullOrEmpty() && !message.body.isNullOrEmpty()) {
            // 构建通知数据
            val data = mutableMapOf<String, String>()
            message.type?.let { data[FCMConstants.DATA_KEY_TYPE] = it }
            message.agentId?.let { data[FCMConstants.DATA_KEY_AGENT_ID] = it }

            // 显示通知，使用特定的通知 ID 和时间戳
            showNotification(
                title = message.title ?: "",
                body = message.body ?: "",
                data = data,
                notificationId = message.messageId.hashCode(),
                timestamp = message.timestamp,
                iconResId = android.R.drawable.ic_dialog_info,
            )
        } else {
            LogUtils.d(
                "PushNotificationManager",
                "待处理消息缺少标题或内容，跳过显示通知: messageId=${message.messageId}",
            )
        }
    }

    /**
     * 显示推送通知
     *
     * @param title 通知标题
     * @param body 通知内容
     * @param data 消息数据（用于点击通知后的跳转）
     * @param notificationId 通知 ID（默认使用时间戳）
     * @param timestamp 时间戳（可选）
     * @param iconResId 图标资源 ID（可选，默认使用应用配置的图标）
     */
    @SuppressLint("MissingPermission")
    fun showNotification(
        title: String,
        body: String,
        data: Map<String, String>,
        notificationId: Int = System.currentTimeMillis().toInt(),
        timestamp: Long? = null,
        iconResId: Int? = null,
    ) {
        try {
            // 确保通知渠道已创建
            createNotificationChannelIfNeeded()

            // 获取通知图标资源 ID
            val finalIconResId = iconResId ?: getNotificationIconResId()

            // 构建通知
            val builder =
                NotificationCompat.Builder(application, FCMService.NOTIFICATION_CHANNEL_ID)
                    .setSmallIcon(finalIconResId)
                    .setContentTitle(title)
                    .setContentText(body)
                    .setPriority(NotificationCompat.PRIORITY_DEFAULT)
                    .setAutoCancel(true)
                    .setDefaults(NotificationCompat.DEFAULT_ALL)

            // 设置时间戳（如果有）
            timestamp?.let { builder.setWhen(it) }

            // 创建点击通知后的 Intent
            val intent = createNotificationIntent(data)
            val pendingIntent = createPendingIntent(intent)
            builder.setContentIntent(pendingIntent)

            // 显示通知
            val notificationManager = NotificationManagerCompat.from(application)
            if (notificationManager.areNotificationsEnabled()) {
                notificationManager.notify(notificationId, builder.build())
                LogUtils.d("PushNotificationManager", "通知已显示: $title")
            } else {
                LogUtils.w("PushNotificationManager", "通知权限未授予，无法显示通知")
            }
        } catch (e: Exception) {
            LogUtils.e("PushNotificationManager", "显示通知失败", e)
        }
    }

    /** 创建通知点击后的 Intent */
    private fun createNotificationIntent(data: Map<String, String>): Intent {
        val messageType = data[FCMConstants.DATA_KEY_TYPE]
        val agentId = data[FCMConstants.DATA_KEY_AGENT_ID]

        // 添加详细日志，便于调试跳转问题
        LogUtils.d(
            "PushNotificationManager",
            "创建通知 Intent - 消息类型: $messageType, agent_id: $agentId, 所有数据: $data",
        )

        return when (messageType) {
            FCMConstants.TYPE_AGENT_MESSAGE -> {
                // Agent 消息：跳转到聊天页面
                if (!agentId.isNullOrEmpty()) {
                    LogUtils.d("PushNotificationManager", "跳转到 ChatActivity - agent_id: $agentId")
                    ChatActivity.notifyIntent(application, agentId)
                } else {
                    LogUtils.w(
                        "PushNotificationManager",
                        "消息类型为 agent_message 但缺少 agent_id，跳转到主页面。消息类型: $messageType, 数据: $data",
                    )
                    createMainActivityIntent()
                }
            }

            FCMConstants.TYPE_SYSTEM,
            null -> {
                // 系统通知或其他：跳转到主页面
                LogUtils.d("PushNotificationManager", "系统通知或消息类型为空，跳转到主页面。消息类型: $messageType")
                createMainActivityIntent()
            }

            else -> {
                LogUtils.w(
                    "PushNotificationManager",
                    "未知消息类型: $messageType，跳转到主页面。期望类型: ${FCMConstants.TYPE_AGENT_MESSAGE} 或 ${FCMConstants.TYPE_SYSTEM}，所有数据: $data",
                )
                createMainActivityIntent()
            }
        }
    }

    /** 创建 PendingIntent */
    private fun createPendingIntent(intent: Intent): PendingIntent {
        val flags =
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
            } else {
                PendingIntent.FLAG_UPDATE_CURRENT
            }
        return PendingIntent.getActivity(application, 0, intent, flags)
    }

    /** 创建跳转到主页面的 Intent */
    private fun createMainActivityIntent(): Intent {
        return Intent(application, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
    }

    /** 获取通知图标资源 ID */
    private fun getNotificationIconResId(): Int {
        return try {
            val appInfo =
                application.packageManager.getApplicationInfo(
                    application.packageName,
                    android.content.pm.PackageManager.GET_META_DATA,
                )
            val iconResId =
                appInfo.metaData?.getInt(
                    "com.google.firebase.messaging.default_notification_icon",
                    0,
                )

            if (iconResId != null && iconResId != 0) {
                iconResId
            } else {
                appInfo.icon
            }
        } catch (e: Exception) {
            LogUtils.w("PushNotificationManager", "获取通知图标失败，使用系统默认图标", e)
            android.R.drawable.ic_dialog_info
        }
    }

    /** 创建通知渠道（Android 8.0+ 必需） */
    private fun createNotificationChannelIfNeeded() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val notificationManager = application.getSystemService(NotificationManager::class.java)

            if (
                notificationManager.getNotificationChannel(FCMService.NOTIFICATION_CHANNEL_ID) ==
                    null
            ) {
                val channel =
                    NotificationChannel(
                            FCMService.NOTIFICATION_CHANNEL_ID,
                            "Push Notifications",
                            NotificationManager.IMPORTANCE_DEFAULT,
                        )
                        .apply {
                            description = "Receive push notifications and messages"
                            enableVibration(true)
                            vibrationPattern = longArrayOf(0, 250, 250, 250)
                            enableLights(true)
                        }

                notificationManager.createNotificationChannel(channel)
                LogUtils.d("PushNotificationManager", "通知渠道已创建")
            }
        }
    }
}
