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
