package ai.sxwl.android.firebase

/**
 * FCM 消息相关常量
 *
 * 用于统一管理 FCM 推送消息的类型和数据键名
 */
object FCMConstants {
    /** 数据键名：消息类型 */
    const val DATA_KEY_TYPE = "type"

    /** 数据键名：Agent ID（用于跳转到聊天页面） */
    const val DATA_KEY_AGENT_ID = "agent_id"

    /** 数据键名：节日记忆 ID（memory 表主键，用于跳转到 Love Journal 对应条目） */
    const val DATA_KEY_FESTIVAL_MEMORY_ID = "festival_memory_id"

    /** 消息类型：聊天消息 */
    const val TYPE_AGENT_MESSAGE = "agent_message"

    /** 消息类型：节日记忆通知（跳转到该角色 Love Journal 并定位到对应记忆条目） */
    const val TYPE_FESTIVAL_MEMORY = "festival_memory"

    /** 消息类型：系统通知 */
    const val TYPE_SYSTEM = "system"

    /** 消息类型：反馈请求 */
    const val TYPE_FEEDBACK_REQUEST = "feedback_request"
}
