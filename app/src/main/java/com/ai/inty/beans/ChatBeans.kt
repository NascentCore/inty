package com.ai.inty.beans

import com.inty.utils.convertUtcToLocal
import com.inty.utils.storage.IntySetting
import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class SendMsgReq(
    @Json(name = "messages")
    val messages: List<MsgInfo> = listOf(),
    @Json(name = "model")
    val model: String = "chatbot",
    @Json(name = "stream")
    val stream: Boolean = false
)

@JsonClass(generateAdapter = true)
data class SendMsgResponse(
    @Json(name = "choices")
    val choices: List<Choice> = listOf(),
    @Json(name = "created")
    val created: Int = 0,
    @Json(name = "id")
    val id: String = "",
    @Json(name = "model")
    val model: String = "",
    @Json(name = "object")
    val objectX: String = "",
    @Json(name = "usage")
    val usage: Usage = Usage()
)

@JsonClass(generateAdapter = true)
data class Choice(
    @Json(name = "finish_reason")
    val finishReason: String = "",
    @Json(name = "index")
    val index: Int = 0,
    @Json(name = "message")
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
    @Json(name = "page")
    val page: String = "",
    @Json(name = "page_size")
    val pageSize: String = ""
)

@JsonClass(generateAdapter = true)
data class QueryMsgsResponse(
    @Json(name = "has_more")
    val hasMore: Boolean = false,
    @Json(name = "limit")
    val limit: Int = 0,
    @Json(name = "messages")
    val messages: List<MsgInfo> = listOf(),
    @Json(name = "offset")
    val offset: Int = 0,
    @Json(name = "page")
    val page: Int = 0,
    @Json(name = "total")
    val total: Int = 0
)

@JsonClass(generateAdapter = true)
data class MsgInfo(
    @Json(name = "content")
    val content: String = "",
    @Json(name = "role")
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
    @Json(name = "id")
    val id: String = "",
    @Json(name = "last_message")
    val lastMessage: String = "",
    @Json(name = "settings")
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
    @Json(name = "list")
    val list: List<SysMsgItem> = listOf(),
    @Json(name = "page")
    val page: Int = 0,
    @Json(name = "page_size")
    val pageSize: Int = 0,
    @Json(name = "total")
    val total: Int = 0,
    @Json(name = "total_pages")
    val totalPages: Int = 0
)

@JsonClass(generateAdapter = true)
data class SysMsgItem(
    @Json(name = "content")
    val content: String = "",
    @Json(name = "created_at")
    val createdAt: String = "",
    @Json(name = "id")
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
    @Json(name = "title")
    val title: String = "",
    @Json(name = "type")
    val type: Int = 0
)