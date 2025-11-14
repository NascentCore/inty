package ai.sxwl.android.firebase

/**
 * FCM 消息处理回调接口
 *
 * 用于解耦 FCMService (infrastructure 层) 与业务逻辑层
 * 实现应该由 common 层或 app 层提供
 */
interface FCMessageHandler {
    /**
     * 处理收到的 FCM 消息
     *
     * @param messageId 消息 ID
     * @param type 消息类型（chat、agent_message、system 等）
     * @param title 通知标题（可选）
     * @param body 通知内容（可选）
     * @param data 消息数据（包含 agent_id、chat_id 等）
     */
    fun handleMessage(
        messageId: String?,
        type: String?,
        title: String?,
        body: String?,
        data: Map<String, String>,
    )

    /**
     * 需要显示推送通知
     *
     * @param title 通知标题
     * @param body 通知内容
     * @param data 消息数据（用于点击通知后的跳转）
     */
    fun showNotification(
        title: String,
        body: String,
        data: Map<String, String>,
    )
}

