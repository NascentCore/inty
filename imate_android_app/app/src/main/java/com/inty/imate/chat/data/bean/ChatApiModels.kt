package com.inty.imate.chat.data.bean

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement

// TODO: Verify :app:compileDebugKotlin with ANDROID_HOME before release when changing WS payloads.

/**
 * Companion WebSocket `messageType` string (chat frame request body).
 * Aligns with backend `ChatCompletionRequest.message_type` ([USER_MESSAGE] only).
 * Greeting uses `user_signed_on` with `message_id` (RFC4122).
 */
object CompanionChatTurnMessageType {
    const val USER_MESSAGE = "USER_MESSAGE"
}

@Serializable
data class AgentInfo(
    val avatar: String = "",
    val background: String = "",
    @SerialName("background_animated") val backgroundAnimatedUrl: String? = null,
    val id: String = "",
    val name: String = "",
    @SerialName("status_line") val statusLine: String = "",
    val opening: String = "",
    @SerialName("opening_audio_url") val openingAudioUrl: String = "",
    val intro: String = "",
)

@Serializable
data class CreateAgentRequest(
    val name: String,
    val gender: String,
    val avatar: String? = null,
    val background: String? = null,
    @SerialName("background_images") val backgroundImages: List<String> = emptyList(),
    @SerialName("voice_id") val voiceId: String = "",
    val settings: Map<String, JsonElement> = emptyMap(),
    val intro: String = "",
    val opening: String = "",
    val visibility: String = "false",
    val photos: List<String> = emptyList(),
    val category: String = "",
    val prompt: String = "",
)

@Serializable
data class SendMsgResponse(
    val code: Int? = null,
    val message: String? = null,
    val data: SentMsgRspData? = null,
    @SerialName("agent_id") val agentId: String? = null,
    @SerialName("status_line") val statusLine: String? = null,
) {
    @Serializable
    data class SentMsgRspData(
        val error_code: String? = null,
        val description: String? = null,
        val user_message_id: Long = 0,
        val choices: List<Choice> = emptyList(),
        @SerialName("source_imate_id") val sourceImateId: String? = null,
    )
}

@Serializable
data class Choice(
    @SerialName("finish_reason") val finishReason: String = "",
    val index: Int = 0,
    val message: MsgInfo = MsgInfo(),
)

@Serializable
data class ChatMessageContentPart(
    val type: String = "text",
    val text: String? = null,
    @SerialName("image_url") val imageUrl: ImageUrlPayload? = null,
) {
    @Serializable
    data class ImageUrlPayload(val url: String = "")
}

@Serializable
data class SendMsgReqMessage(
    val role: String = "",
    val content: JsonElement? = null,
)

@Serializable
data class SendMsgReq(
    val messages: List<SendMsgReqMessage> = emptyList(),
    val model: String = "chatbot",
    val stream: Boolean = false,
    @SerialName("time_context") val timeContext: UserTimeContext,
    @SerialName("target_imate_id") val targetImateId: String? = null,
    /** RFC4122; companion WebSocket uses as transcript user_msg_uuid when valid. */
    @SerialName("message_id") val messageId: String? = null,
    /** Optional; default server-side is USER_MESSAGE. */
    @SerialName("messageType") val messageType: String? = null,
)

@Serializable
data class ChatWebSocketReq(
    @SerialName("agent_id") val agentId: String,
    val request: SendMsgReq,
)

@Serializable
data class ChatClientContextWsMessage(
    val type: String = "client_context",
    @SerialName("time_context") val timeContext: UserTimeContext,
)

@Serializable
data class ChatUserSignedOnWsMessage(
    val type: String = "user_signed_on",
    @SerialName("agent_id") val agentId: String,
    @SerialName("message_id") val messageId: String,
    @SerialName("time_context") val timeContext: UserTimeContext,
)

@Serializable
data class ChatWsPingMessage(
    val type: String = "ping",
    @SerialName("time_context") val timeContext: UserTimeContext,
)

@Serializable
data class ChatWsControlFrame(@SerialName("type") val type: String?)

fun ChatWsControlFrame?.shouldDeferChatResponseParsing(): Boolean =
    this?.type == "pong" ||
        this?.type == "client_context_ack" ||
        this?.type == "user_signed_on_ack" ||
        this?.type == "user_signed_out_ack"

@Serializable
data class UserTimeContext(
    @SerialName("local_time") val localTime: String,
    val timezone: String,
    @SerialName("utc_offset_minutes") val utcOffsetMinutes: Int,
)

@Serializable
data class MsgInfo(
    val id: String = "",
    val content: String = "",
    @SerialName("content_parts") val contentParts: List<ChatMessageContentPart> = emptyList(),
    val role: String = "",
    val meta_data: MsgMetaData? = null,
    val audio_url: String? = null,
    val timestamp: String? = null,
    @SerialName("user_vote") val user_vote: String? = null,
    val type: String? = null,
    @SerialName("festival_memory_id") val festivalMemoryId: Long? = null,
    @SerialName("media_url") val mediaUrl: String? = null,
    val price: Int = 0,
    @SerialName("is_locked") val unPurchased: Boolean = true,
    val caption: String? = null,
) {

    @Serializable
    data class MsgMetaData(
        val agentId: String? = null,
        @SerialName("is_voice") val isVoice: Boolean = false,
        val isOpening: Boolean = false,
        @SerialName("voice_session_id") val voice_session_id: String? = null,
        @SerialName("generated_image") val generatedImage: GeneratedImage? = null,
        @SerialName("tool_background_started") val toolBackgroundStarted: Boolean = false,
        @SerialName("reply_modality") val replyModality: String? = null,
        @SerialName("voice_message_script") val voiceMessageScript: String? = null,
        @SerialName("audioDuration") val audioDuration: Double? = null,
    ) {
        @Serializable
        data class GeneratedImage(
            @SerialName("image_url") val imageUrl: String = "",
            val width: Int = 0,
            val height: Int = 0,
        )
    }

    fun extractTextFromContentParts(): String {
        return contentParts
            .asSequence()
            .filter { it.type == "text" }
            .mapNotNull { it.text?.trim() }
            .filter { it.isNotBlank() }
            .joinToString(separator = "\n")
    }

    fun extractFirstImageUrlFromContentParts(): String? {
        return contentParts
            .asSequence()
            .filter { it.type == "image_url" }
            .mapNotNull { it.imageUrl?.url?.trim() }
            .firstOrNull { it.isNotEmpty() }
    }
}

@Serializable
data class QueryMsgsResponse(
    @SerialName("has_more") val hasMore: Boolean = false,
    val limit: Int = 0,
    val messages: List<MsgInfo>? = null,
    val offset: Int = 0,
    val page: Int = 0,
    val total: Int = 0,
)
