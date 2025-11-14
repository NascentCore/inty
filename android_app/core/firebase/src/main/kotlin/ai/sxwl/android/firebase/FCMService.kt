package ai.sxwl.android.firebase

import ai.sxwl.android.utils.LogUtils
import android.annotation.SuppressLint
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

/**
 * Firebase Cloud Messaging 服务
 *
 * 负责接收和处理 Firebase 推送消息
 *
 * 参考文档：https://firebase.google.com/docs/cloud-messaging/get-started?hl=zh-cn&platform=android
 */
class FCMService : FirebaseMessagingService() {

    companion object {
        /**
         * 通知渠道 ID
         * 用于 Firebase Cloud Messaging 推送通知
         */
        const val NOTIFICATION_CHANNEL_ID = "fcm_default_channel"

        /**
         * Notification channel name
         */
        private const val NOTIFICATION_CHANNEL_NAME = "Push Notifications"

        /**
         * Notification channel description
         */
        private const val NOTIFICATION_CHANNEL_DESCRIPTION =
            "Receive push notifications and messages"

        /**
         * 消息类型键名
         */
        private const val DATA_KEY_TYPE = "type"

        /**
         * Agent ID 键名（用于跳转到聊天页面）
         */
        private const val DATA_KEY_AGENT_ID = "agent_id"

        /**
         * 消息类型：聊天消息
         */
        private const val TYPE_CHAT = "chat"

        /**
         * 消息类型：系统通知
         */
        private const val TYPE_SYSTEM = "system"
    }

    /**
     * 协程作用域，用于异步操作
     */
    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    /**
     * 当收到 FCM 消息时调用
     *
     * 注意：
     * - 数据消息（data message）：应用前后台均会触发此方法
     * - 通知消息（notification message）：
     *   - 应用在前台：会触发此方法，需要手动显示通知
     *   - 应用在后台：系统会自动显示通知，不会触发此方法
     * - Direct Boot 模式：在用户未解锁时，消息元数据会被保存到设备加密存储，待用户解锁后处理
     */
    override fun onMessageReceived(remoteMessage: RemoteMessage) {
        super.onMessageReceived(remoteMessage)

        LogUtils.d("FCMService", "收到 FCM 推送消息")
        LogUtils.d("FCMService", "消息 ID: ${remoteMessage.messageId}")
        LogUtils.d("FCMService", "消息来源: ${remoteMessage.from}")

        // 检查是否处于 Direct Boot 模式
        val isDirectBootMode = DirectBootUtils.isDirectBootMode(this)
        LogUtils.d("FCMService", "Direct Boot 模式: $isDirectBootMode")

        if (isDirectBootMode) {
            // Direct Boot 模式：保存消息元数据，待用户解锁后处理
            handleMessageInDirectBootMode(remoteMessage)
        } else {
            // 用户已解锁：正常处理消息
            handleMessageInNormalMode(remoteMessage)
        }
    }

    /**
     * 在 Direct Boot 模式下处理消息
     * 仅保存消息元数据到设备加密存储，不进行实际处理
     */
    private fun handleMessageInDirectBootMode(remoteMessage: RemoteMessage) {
        try {
            // 初始化 Direct Boot 存储
            DirectBootStorage.initialize(this)

            // 提取消息元数据
            val messageId = remoteMessage.messageId ?: System.currentTimeMillis().toString()
            val notification = remoteMessage.notification
            val data = remoteMessage.data

            val pendingMessage = DirectBootStorage.PendingMessage(
                messageId = messageId,
                timestamp = System.currentTimeMillis(),
                type = data["type"],
                agentId = data["agent_id"],
                title = notification?.title,
                body = notification?.body,
            )

            // 保存到 Direct Boot 存储
            val saved = DirectBootStorage.savePendingMessage(pendingMessage, this)
            if (saved) {
                LogUtils.i(
                    "FCMService",
                    "Direct Boot 模式：消息元数据已保存，待用户解锁后处理。messageId=$messageId"
                )
            } else {
                LogUtils.w("FCMService", "Direct Boot 模式：保存消息元数据失败")
            }
        } catch (e: Exception) {
            LogUtils.e("FCMService", "Direct Boot 模式：处理消息失败", e)
        }
    }

    /**
     * 在正常模式下处理消息（用户已解锁）
     */
    private fun handleMessageInNormalMode(remoteMessage: RemoteMessage) {
        LogUtils.d(
            "FCMService",
            "消息类型: ${if (remoteMessage.data.isNotEmpty()) "数据消息" else "通知消息"}"
        )

        // 1. 处理数据消息（应用前后台均会触发）
        if (remoteMessage.data.isNotEmpty()) {
            LogUtils.i("FCMService", "数据消息内容: ${remoteMessage.data}")
            handleDataMessage(remoteMessage.data)
        }

        // 2. 处理通知消息（仅在前台触发；后台时系统自动显示）
        remoteMessage.notification?.let { notification ->
            val title = notification.title
            val body = notification.body

            if (title != null && body != null) {
                LogUtils.i("FCMService", "通知消息 - 标题: $title, 内容: $body")
                showNotification(title, body, remoteMessage.data)
            } else {
                LogUtils.w("FCMService", "通知消息缺少标题或内容")
            }
        }
    }

    /**
     * 当 FCM 注册令牌更新时调用
     *
     * 触发场景：
     * 1. 应用首次安装并获取令牌
     * 2. 应用恢复到新设备
     * 3. 用户卸载/重新安装应用
     * 4. 用户清除应用数据
     *
     * 参考：https://firebase.google.com/docs/cloud-messaging/get-started?hl=zh-cn&platform=android#access-the-registration-token
     */
    override fun onNewToken(token: String) {
        super.onNewToken(token)

        LogUtils.i("FCMService", "FCM 注册令牌已更新: $token")
        uploadTokenToServer(token)
    }

    /**
     * 处理数据消息
     */
    private fun handleDataMessage(data: Map<String, String>) {
        // 根据业务需求处理数据消息
        // 例如：更新应用状态、触发特定操作等
    }

    /**
     * 显示通知
     *
     * @param title 通知标题
     * @param body 通知内容
     * @param data 消息数据（可选，用于点击通知后的跳转等）
     */
    @SuppressLint("MissingPermission")
    private fun showNotification(
        title: String,
        body: String,
        data: Map<String, String> = emptyMap()
    ) {
        try {
            // 确保通知渠道已创建
            createNotificationChannelIfNeeded()

            // 获取通知图标资源 ID
            // 优先使用 AndroidManifest 中配置的 default_notification_icon
            // 如果未配置，则使用系统默认图标
            val iconResId = getNotificationIconResId()

            // 构建通知
            val builder = NotificationCompat.Builder(this, NOTIFICATION_CHANNEL_ID)
                .setSmallIcon(iconResId)
                .setContentTitle(title)
                .setContentText(body)
                .setPriority(NotificationCompat.PRIORITY_DEFAULT)
                .setAutoCancel(true)
                .setDefaults(NotificationCompat.DEFAULT_ALL)

            // 根据 data 中的信息设置点击通知后的跳转 Intent
            val pendingIntent = createNotificationIntent(data)
            builder.setContentIntent(pendingIntent)

            // Show notification
            val notificationManager = NotificationManagerCompat.from(this)
            if (notificationManager.areNotificationsEnabled()) {
                notificationManager.notify(System.currentTimeMillis().toInt(), builder.build())
                LogUtils.d("FCMService", "通知已显示: $title")
            } else {
                LogUtils.w(
                    "FCMService",
                    "通知权限未授予，无法显示通知"
                )
            }
        } catch (e: Exception) {
            LogUtils.e("FCMService", "显示通知失败", e)
        }
    }

    /**
     * 创建通知渠道（Android 8.0+ 必需）
     *
     * 参考：https://firebase.google.com/docs/cloud-messaging/get-started?hl=zh-cn&platform=android#android-80-or-higher
     */
    private fun createNotificationChannelIfNeeded() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val notificationManager = getSystemService(NotificationManager::class.java)

            // 检查渠道是否已存在
            if (notificationManager.getNotificationChannel(NOTIFICATION_CHANNEL_ID) == null) {
                val channel = NotificationChannel(
                    NOTIFICATION_CHANNEL_ID,
                    NOTIFICATION_CHANNEL_NAME,
                    NotificationManager.IMPORTANCE_DEFAULT
                ).apply {
                    description = NOTIFICATION_CHANNEL_DESCRIPTION
                    enableVibration(true)
                    vibrationPattern = longArrayOf(0, 250, 250, 250)
                    enableLights(true)
                }

                notificationManager.createNotificationChannel(channel)
                LogUtils.d("FCMService", "通知渠道已创建: $NOTIFICATION_CHANNEL_ID")
            }
        }
    }

    /**
     * 获取通知图标资源 ID
     *
     * 优先使用 AndroidManifest 中配置的 default_notification_icon
     * 如果未配置，则使用系统默认图标
     */
    private fun getNotificationIconResId(): Int {
        return try {
            // 尝试从 AndroidManifest 的 meta-data 中获取图标资源 ID
            val appInfo = packageManager.getApplicationInfo(
                packageName,
                android.content.pm.PackageManager.GET_META_DATA
            )
            val iconResId = appInfo.metaData?.getInt(
                "com.google.firebase.messaging.default_notification_icon",
                0
            )

            if (iconResId != null && iconResId != 0) {
                iconResId
            } else {
                // 如果未配置，使用应用图标
                appInfo.icon
            }
        } catch (e: Exception) {
            LogUtils.w("FCMService", "获取通知图标失败，使用系统默认图标", e)
            android.R.drawable.ic_dialog_info
        }
    }

    /**
     * 创建通知点击后的 Intent
     *
     * 根据消息类型和数据进行不同的跳转：
     * - chat: 跳转到聊天页面（需要 agent_id）
     * - system: 跳转到主页面
     * - 其他: 跳转到主页面
     */
    private fun createNotificationIntent(data: Map<String, String>): PendingIntent {
        val intent = when (val messageType = data[DATA_KEY_TYPE]) {
            TYPE_CHAT -> {
                // 聊天消息：跳转到聊天页面
                val agentId = data[DATA_KEY_AGENT_ID]
                if (!agentId.isNullOrEmpty()) {
                    // 使用反射调用 ChatActivity.launch，避免直接依赖 app 模块
                    try {
                        val chatActivityClass =
                            Class.forName("com.ai.intellimate.chat.ChatActivity")
                        val launchMethod = chatActivityClass.getMethod(
                            "launch",
                            android.content.Context::class.java,
                            String::class.java
                        )
                        // 创建 Intent 用于启动 ChatActivity
                        Intent(this, chatActivityClass).apply {
                            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
                            putExtra("intent_key_agent_id", agentId)
                            putExtra("intent_key_page_source", "push_notification")
                        }
                    } catch (e: Exception) {
                        LogUtils.w(
                            "FCMService",
                            "启动 ChatActivity 失败，使用 MainActivity",
                            e
                        )
                        createMainActivityIntent()
                    }
                } else {
                    LogUtils.w(
                        "FCMService",
                        "聊天消息缺少 agent_id，跳转到主页面"
                    )
                    createMainActivityIntent()
                }
            }

            TYPE_SYSTEM, null -> {
                // System notification or other: navigate to main page
                createMainActivityIntent()
            }

            else -> {
                LogUtils.d(
                    "FCMService",
                    "未知消息类型: $messageType，跳转到主页面"
                )
                createMainActivityIntent()
            }
        }

        val flags = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        } else {
            PendingIntent.FLAG_UPDATE_CURRENT
        }

        return PendingIntent.getActivity(this, 0, intent, flags)
    }

    /**
     * 创建跳转到主页面的 Intent
     */
    private fun createMainActivityIntent(): Intent {
        return try {
            val mainActivityClass = Class.forName("com.ai.intellimate.MainActivity")
            Intent(this, mainActivityClass).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            }
        } catch (e: Exception) {
            LogUtils.e("FCMService", "未找到 MainActivity", e)
            // Fallback to launcher Intent
            packageManager.getLaunchIntentForPackage(packageName)?.apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            } ?: Intent(Intent.ACTION_MAIN).apply {
                addCategory(Intent.CATEGORY_LAUNCHER)
                setPackage(packageName)
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            }
        }
    }

    /**
     * Upload FCM Token to server
     *
     * Delegates to FirebaseManager, which uses callback to avoid circular dependencies
     */
    private fun uploadTokenToServer(token: String) {
        serviceScope.launch {
            try {
                LogUtils.d("FCMService", "开始上传 FCM Token 到服务器")
                FirebaseManager.uploadFCMToken(token)
            } catch (e: Exception) {
                LogUtils.e("FCMService", "上传 FCM Token 失败", e)
            }
        }
    }
}
