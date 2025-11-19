package ai.sxwl.android.common.fcm

import ai.sxwl.android.common.event.EventBus
import ai.sxwl.android.common.event.PushNotificationEvent
import ai.sxwl.android.firebase.FCMessageHandler

/**
 * FCM 消息处理器默认实现
 *
 * 通过 EventBus 发布事件，将消息处理逻辑委托给订阅者 这个实现位于 common 层，可以依赖 firebase 和 EventBus
 */
class FCMessageHandlerImpl : FCMessageHandler {
    override fun handleMessage(
        messageId: String?,
        type: String?,
        title: String?,
        body: String?,
        data: Map<String, String>,
    ) {
        EventBus.post(
            PushNotificationEvent.MessageReceived(
                messageId = messageId,
                type = type,
                title = title,
                body = body,
                data = data,
            )
        )
    }

    override fun showNotification(title: String, body: String, data: Map<String, String>) {
        EventBus.post(
            PushNotificationEvent.ShowNotification(title = title, body = body, data = data)
        )
    }
}
