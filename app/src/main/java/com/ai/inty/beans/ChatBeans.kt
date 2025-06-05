package com.ai.inty.beans
import com.squareup.moshi.JsonClass

import com.squareup.moshi.Json

@JsonClass(generateAdapter = true)
data class SendMsgReq(
    @Json(name = "content")
    val content: String = "",
    @Json(name = "type")
    val type: String = ""
)

@JsonClass(generateAdapter = true)
data class SendMsgResponse(
    @Json(name = "message_id")
    val messageId: String = "",
    @Json(name = "status")
    val status: String = ""
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
    @Json(name = "items")
    val items: List<MsgInfo> = listOf(),
    @Json(name = "page")
    val page: String = "",
    @Json(name = "page_size")
    val pageSize: String = "",
    @Json(name = "total")
    val total: String = ""
)

@JsonClass(generateAdapter = true)
data class MsgInfo(
    @Json(name = "content")
    val content: String = "",
    @Json(name = "created_at")
    val createdAt: String = "",
    @Json(name = "id")
    val id: String = "",
    @Json(name = "sender")
    val sender: MsgSender = MsgSender(),
    @Json(name = "sender_type")
    val senderType: String = "",
    @Json(name = "type")
    val type: String = ""
)

@JsonClass(generateAdapter = true)
data class MsgSender(
    @Json(name = "avatar")
    val avatar: String = "",
    @Json(name = "id")
    val id: String = "",
    @Json(name = "name")
    val name: String = ""
)