package ai.sxwl.android.firebase

/**
 * FCM 消息相关常量
 *
 * 用于统一管理 FCM 推送消息的类型和数据键名
 */
object FCMConstants {
    /**
     * 数据键名：消息类型
     */
    const val DATA_KEY_TYPE = "type"

    /**
     * 数据键名：Agent ID（用于跳转到聊天页面）
     */
    const val DATA_KEY_AGENT_ID = "agent_id"


    /**
     * 消息类型：聊天消息
     */
    const val TYPE_AGENT_MESSAGE = "agent_message"

    /**
     * 消息类型：系统通知
     */
    const val TYPE_SYSTEM = "system"
}
