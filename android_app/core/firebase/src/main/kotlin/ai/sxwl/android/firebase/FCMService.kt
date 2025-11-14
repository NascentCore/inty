package ai.sxwl.android.firebase

import ai.sxwl.android.utils.LogUtils
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
    }


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
                type = data[FCMConstants.DATA_KEY_TYPE],
                agentId = data[FCMConstants.DATA_KEY_AGENT_ID],
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

        val data = remoteMessage.data
        val notification = remoteMessage.notification
        val messageType = data[FCMConstants.DATA_KEY_TYPE]

        // 通过回调处理消息
        val handler = FirebaseManager.getMessageHandler()
        handler?.handleMessage(
            messageId = remoteMessage.messageId,
            type = messageType,
            title = notification?.title,
            body = notification?.body,
            data = data,
        )

        // 如果有通知内容，通过回调显示通知（仅在前台触发；后台时系统自动显示）
        notification?.let { notif ->
            val title = notif.title
            val body = notif.body

            if (title != null && body != null) {
                LogUtils.i("FCMService", "通知消息 - 标题: $title, 内容: $body")
                handler?.showNotification(
                    title = title,
                    body = body,
                    data = data,
                )
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
     * Upload FCM Token to server
     *
     * Delegates to FirebaseManager, which uses callback to avoid circular dependencies
     */
    private fun uploadTokenToServer(token: String) {
        CoroutineScope(SupervisorJob() + Dispatchers.IO).launch {
            try {
                LogUtils.d("FCMService", "开始上传 FCM Token 到服务器")
                FirebaseManager.uploadFCMToken(token)
            } catch (e: Exception) {
                LogUtils.e("FCMService", "上传 FCM Token 失败", e)
            }
        }
    }
}
