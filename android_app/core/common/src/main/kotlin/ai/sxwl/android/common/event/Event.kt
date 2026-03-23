package ai.sxwl.android.common.event

import java.util.UUID

/** 事件基类 */
abstract class BaseEvent {
    val timestamp: Long = System.currentTimeMillis()
    val eventId: String = UUID.randomUUID().toString()
}

/** 用户相关事件 */
sealed class UserEvent : BaseEvent() {
    data class Login(val userId: String, val userName: String) : UserEvent()

    data class Logout(val userId: String) : UserEvent()

    data class ProfileUpdated(val userId: String, val profile: Map<String, Any>) : UserEvent()
}

/** 聊天相关事件 */
sealed class ChatEvent : BaseEvent() {
    data class MessageReceived(val messageId: String, val content: String, val senderId: String) :
        ChatEvent()

    data class MessageSent(val messageId: String, val content: String) : ChatEvent()

    data class TypingStarted(val userId: String) : ChatEvent()

    data class TypingStopped(val userId: String) : ChatEvent()
}

/** 系统相关事件 */
sealed class SystemEvent : BaseEvent() {
    data class NetworkChanged(val isConnected: Boolean) : SystemEvent()

    data class AppStateChanged(val isForeground: Boolean) : SystemEvent()

    data class ErrorOccurred(val error: Throwable, val context: String) : SystemEvent()
}

/** FCM 推送通知相关事件 */
sealed class PushNotificationEvent : BaseEvent() {
    /**
     * 收到推送通知消息
     *
     * @param messageId 消息 ID
     * @param type 消息类型（chat、agent_message、system 等）
     * @param title 通知标题
     * @param body 通知内容
     * @param data 消息数据（包含 agent_id、chat_id 等）
     */
    data class MessageReceived(
        val messageId: String?,
        val type: String?,
        val title: String?,
        val body: String?,
        val data: Map<String, String>,
    ) : PushNotificationEvent()

    /**
     * 需要显示推送通知
     *
     * @param title 通知标题
     * @param body 通知内容
     * @param data 消息数据（用于点击通知后的跳转）
     */
    data class ShowNotification(
        val title: String,
        val body: String,
        val data: Map<String, String>,
    ) : PushNotificationEvent()
}
