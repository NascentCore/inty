package com.ai.inty.beans

import com.inty.utils.convertUtcToLocal
import com.inty.utils.storage.IntySetting
import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class SendMsgReq(
    val messages: List<MsgInfo> = listOf(),
    val model: String = "chatbot",
    val stream: Boolean = false
)

@JsonClass(generateAdapter = true)
data class SendMsgResponse(
    val choices: List<Choice> = listOf(),
    val created: Int = 0,
    val id: String = "",
    val model: String = "",
    @Json(name = "object")
    val objectX: String = "",
    val usage: Usage = Usage()
)

@JsonClass(generateAdapter = true)
data class Choice(
    @Json(name = "finish_reason")
    val finishReason: String = "",
    val index: Int = 0,
    val message: MsgInfo = MsgInfo()
)

@JsonClass(generateAdapter = true)
data class Usage(
    @Json(name = "completion_tokens")
    val completionTokens: Int = 0,
    @Json(name = "prompt_tokens")
    val promptTokens: Int = 0,
    @Json(name = "total_tokens")
    val totalTokens: Int = 0
)


@JsonClass(generateAdapter = true)
data class QueryMsgReq(
    val page: String = "",
    @Json(name = "page_size")
    val pageSize: String = ""
)

@JsonClass(generateAdapter = true)
data class QueryMsgsResponse(
    @Json(name = "has_more")
    val hasMore: Boolean = false,
    val limit: Int = 0,
    val messages: List<MsgInfo> = listOf(),
    val offset: Int = 0,
    val page: Int = 0,
    val total: Int = 0
)

@JsonClass(generateAdapter = true)
data class MsgInfo(
    val content: String = "",
    val role: String = "",
)


@JsonClass(generateAdapter = true)
data class ConversationItem(
    @Json(name = "agent_id")
    val agentId: String = "",
    @Json(name = "agent_name")
    val agentName: String = "",
    @Json(name = "agent_avatar")
    val agentAvatar: String = "",
    @Json(name = "created_at")
    val createdAt: String = "",
    val id: String = "",
    @Json(name = "last_message")
    val lastMessage: String = "",
    val settings: Any? = null,
    @Json(name = "updated_at")
    val updatedAt: Any? = null,
    @Json(name = "user_id")
    val userId: String = "",
    val isNew: Boolean = !IntySetting.isConversationReaded(agentId, lastMessage)
) {
    fun getShowTime(): String {
        return convertUtcToLocal(createdAt)
    }

}

@JsonClass(generateAdapter = true)
data class SysMsgResponse(
    val list: List<SysMsgItem> = listOf(),
    val page: Int = 0,
    @Json(name = "page_size")
    val pageSize: Int = 0,
    val total: Int = 0,
    @Json(name = "total_pages")
    val totalPages: Int = 0
)

@JsonClass(generateAdapter = true)
data class SysMsgItem(
    val content: String = "",
    @Json(name = "created_at")
    val createdAt: String = "",
    val id: String = "",
    @Json(name = "image_urls")
    val imageUrls: List<Any?> = listOf(),
    @Json(name = "is_read")
    val isRead: Boolean = false,
    @Json(name = "link_urls")
    val linkUrls: List<String> = listOf(),
    @Json(name = "read_at")
    val readAt: String = "",
    @Json(name = "template_id")
    val templateId: Int = 0,
    val title: String = "",
    val type: Int = 0
)