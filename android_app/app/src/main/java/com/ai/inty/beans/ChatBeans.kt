package com.ai.inty.beans

import com.inty.utils.convertUtcToLocal
import com.inty.utils.storage.IntySetting
import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class SendMsgResponse(
    val code: Int? = null,
    val message: String? = null,
    val data: SentMsgRspData? = null,
) {
    data class SentMsgRspData(
        val error_code: String? = null,
        val description: String? = null,
        val choices: List<Choice> = listOf(),
        val created: Int = 0,
        val id: String = "",
        val model: String = "",
        @Json(name = "object") val objectX: String = "",
        val usage: Usage = Usage(),
    )
}

@JsonClass(generateAdapter = true)
data class SendMsgReq(
    val messages: List<MsgInfo> = listOf(),
    val model: String = "chatbot",
    val stream: Boolean = false,
)

@JsonClass(generateAdapter = true)
data class Choice(
    @Json(name = "finish_reason") val finishReason: String = "",
    val index: Int = 0,
    val message: MsgInfo = MsgInfo(),
)

@JsonClass(generateAdapter = true)
data class Usage(
    @Json(name = "completion_tokens") val completionTokens: Int = 0,
    @Json(name = "prompt_tokens") val promptTokens: Int = 0,
    @Json(name = "total_tokens") val totalTokens: Int = 0,
)

@JsonClass(generateAdapter = true)
data class QueryMsgReq(val page: String = "", @Json(name = "page_size") val pageSize: String = "")

@JsonClass(generateAdapter = true)
data class QueryMsgsResponse(
    @Json(name = "has_more") val hasMore: Boolean = false,
    val limit: Int = 0,
    val messages: List<MsgInfo> = listOf(),
    val offset: Int = 0,
    val page: Int = 0,
    val total: Int = 0,
)

// 该数据结构对应后端 dict 数据结构；每条消息都是对应的 key:value 字典。
// 后端会写入数据库，格式如下：
// {
//  "id": null,
//  "name": null,
//  "type": "human",
//  "content": "test",
//  "example": false,
//  "additional_kwargs": {},
//  "response_metadata": {}
// }
@JsonClass(generateAdapter = true)
data class MsgInfo(
    val id: String = "", // 服务端对应的消息id
    val content: String = "",
    val role: String = "",
    val meta_data: MsgMetaData? = null, // 附带数据
    val audio_url: String? = null, // 音频文件的url
    val timestamp: String? = null, // 消息时间戳 2025-09-11T03:58:29.077875+00:00
    // 本地创建一个msgId，临时用于消息标记
    val localMsgId: String = "${System.nanoTime()}_${role}_${content.hashCode()}",
) {

    fun isOpening(): Boolean {
        return meta_data?.isOpening == true
    }

    fun agentId(): String? {
        return meta_data?.agentId
    }

    data class MsgMetaData(val agentId: String? = null, val isOpening: Boolean = false)
}

@JsonClass(generateAdapter = true)
data class ConversationItem(
    @Json(name = "agent_id") val agentId: String = "",
    @Json(name = "agent_name") val agentName: String = "",
    @Json(name = "agent_avatar") val agentAvatar: String = "",
    @Json(name = "agent_background") val agentBackground: String = "",
    @Json(name = "agent_intro") val agentIntro: String = "",
    @Json(name = "agent_opening") val agentOpening: String = "",
    @Json(name = "agent_opening_audio_url") val agentOpeningAudioUrl: String = "",
    @Json(name = "created_at") val createdAt: String = "",
    val id: String = "",
    @Json(name = "last_message") val lastMessage: String = "",
    @Json(name = "last_message_time") val lastMessageTime: String = "",
    val settings: Any? = null,
    @Json(name = "updated_at") val updatedAt: Any? = null,
    @Json(name = "user_id") val userId: String = "",
    @Json(name = "agent_is_deleted") val isDeleted: Boolean = false, // 标记该agent是否已经被删除（针对自建agent场景）
    val isNew: Boolean = !IntySetting.isConversationReaded(agentId, lastMessage),
) {
    fun getShowTime(): String {
        return convertUtcToLocal(lastMessageTime)
    }

    fun convertToAgentInfo(): AgentInfo {
        return AgentInfo(
                avatar = agentAvatar,
                background = agentBackground,
                id = agentId,
                name = agentName,
                intro = agentIntro,
                opening = agentOpening,
                opening_audio_url = agentOpeningAudioUrl,
            )
            .also { info -> info.isDeleted = this.isDeleted }
    }
}

// chat settings

/** 聊天相关的设置接口，注意一个接口多个使用，不需要的参数，保持null，避免覆盖 */
@JsonClass(generateAdapter = true)
data class ChatSettingsReq(
    val keep_talking: Boolean? = null,
    val language: String? = null,
    val premium_mode: Boolean? = null,
    val style_prompt: String? = null,
    val voice_enabled: Boolean? = null,
)

@JsonClass(generateAdapter = true)
data class ChatSettingsResponse(
    val code: Int? = null,
    val message: String? = null,
    val data: ChatSettingRspData? = null,
) {
    /**
     * "language": "en", "voice_enabled": true, "style_prompt": "string", "premium_mode": false,
     * "id": "string", "user_id": "string", "agent_id": "string", "chat_id": "string", "created_at":
     * "2025-08-28T08:02:50.203Z", "updated_at": "2025-08-28T08:02:50.203Z"
     */
    data class ChatSettingRspData(
        val id: String? = null,
        val user_id: String? = null,
        val agent_id: String? = null,
        val chat_id: String? = null,
        val created_at: String? = null,
        val updated_at: String? = null,
        val language: String? = null, // 聊天语言
        val style_prompt: String? = null, // 定制化回复风格reply
        val voice_enabled: Boolean? = null, // 是否启用语音
        val keep_talking: Boolean? = null, // 连续回复,似乎客户端实现，不需要接口字段
        val premium_mode: Boolean? = null, // 是否会员模式
    )
}

@JsonClass(generateAdapter = true)
data class MsgVoiceRsp(
    val code: Int? = null,
    val message: String? = null,
    val data: MsgVoiceData? = null,
) {
    data class MsgVoiceData(
        val audio_url: String? = null,
        val message_id: String? = null,
        val voice_id: String? = null,
        val language: String? = null,
        val cached: Boolean = false,
        val generation_time: String? = null,
        // 出现limit次数限制时的错误字段
        val error_code: String? = null,
        val description: String? = null,
        val used_count: Int = 0,
        val limit: Int = 0,
    )
}
