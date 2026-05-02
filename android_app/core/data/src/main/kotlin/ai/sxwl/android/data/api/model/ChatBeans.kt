package ai.sxwl.android.data.api.model

import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.utils.TimeUtils
import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass
import kotlinx.serialization.Serializable

/** 单条业务动作（如 subscription_popup），用于 chat completions。 注意：biz action 仍处于探索阶段，尚未确定使用。 */
@Serializable
@JsonClass(generateAdapter = true)
data class BizAction(
    @Json(name = "action_type") val actionType: String = "none",
    val message: String = "",
)

@Serializable
@JsonClass(generateAdapter = true)
data class SendMsgResponse(
    val code: Int? = null,
    val message: String? = null,
    val data: SentMsgRspData? = null,
    /** 下行顶层 agent_id，多角色时区分（与后端 `app/api/ENDPOINTS.md` WebSocket 约定一致）。 */
    @Json(name = "agent_id") val agentId: String? = null,
) {
    @Serializable
    data class SentMsgRspData(
        val error_code: String? = null,
        val description: String? = null,
        val user_message_id: Long = 0,
        /** biz action：探索阶段，尚未确定使用。 */
        @Json(name = "business_actions") val businessActions: List<BizAction> = emptyList(),
        val choices: List<Choice> = listOf(),
        val created: Int = 0,
        val id: String = "",
        val model: String = "",
        @Json(name = "object") val objectX: String = "",
        val usage: Usage = Usage(),
        @Json(name = "source_imate_id") val sourceImateId: String? = null,
    )
}

@Serializable
@JsonClass(generateAdapter = true)
data class ChatMessageContentPart(
    val type: String = "text",
    val text: String? = null,
    @Json(name = "image_url") val imageUrl: ImageUrlPayload? = null,
) {
    @Serializable
    @JsonClass(generateAdapter = true)
    data class ImageUrlPayload(val url: String = "")
}

@JsonClass(generateAdapter = true)
data class SendMsgReqMessage(val role: String = "", val content: Any = "") {
    companion object {
        fun text(role: String, text: String) = SendMsgReqMessage(role = role, content = text)

        fun multimodal(role: String, parts: List<ChatMessageContentPart>) =
            SendMsgReqMessage(role = role, content = parts)
    }
}

// TODO(implicit-sign-on): Run :core:data:compileDebugKotlin (or full app compile) when changing
// SendMsgReq; release checklist in /docs/FR_USER_SIGN_ON_GREETINGS.md#open-todos-follow-ups

/** Companion WebSocket turn kind; aligns with Python ``CompanionChatTurnMessageType``. */
object CompanionChatTurnMessageType {
    const val USER_MESSAGE = "USER_MESSAGE"
    const val IMPLICIT_USER_SIGNED_ON = "IMPLICIT_USER_SIGNED_ON"
}

@JsonClass(generateAdapter = true)
data class SendMsgReq(
    val messages: List<SendMsgReqMessage> = listOf(),
    val model: String = "chatbot",
    val stream: Boolean = false,
    @Json(name = "time_context") val timeContext: UserTimeContext? = null,
    @Json(name = "target_imate_id") val targetImateId: String? = null,
    /** Optional; default server-side is USER_MESSAGE. */
    @Json(name = "messageType") val messageType: String? = null,
)

@JsonClass(generateAdapter = true)
data class ChatWebSocketReq(@Json(name = "agent_id") val agentId: String, val request: SendMsgReq)

/** 主 WebSocket 连接建立后上报本地时区与时间，与后端 `client_context` 帧对齐。 */
@JsonClass(generateAdapter = true)
data class ChatClientContextWsMessage(
    val type: String = "client_context",
    @Json(name = "time_context") val timeContext: UserTimeContext,
)

/** Chat WebSocket downstream frames that only carry `type` (e.g. pong, client_context_ack). */
@JsonClass(generateAdapter = true)
data class ChatWsControlFrame(@Json(name = "type") val type: String?)

fun ChatWsControlFrame?.shouldDeferChatResponseParsing(): Boolean =
    this?.type == "pong" || this?.type == "client_context_ack"

@JsonClass(generateAdapter = true)
data class UserTimeContext(
    @Json(name = "local_time") val localTime: String,
    val timezone: String,
    @Json(name = "utc_offset_minutes") val utcOffsetMinutes: Int,
)

@Serializable
@JsonClass(generateAdapter = true)
data class Choice(
    @Json(name = "finish_reason") val finishReason: String = "",
    val index: Int = 0,
    val message: MsgInfo = MsgInfo(),
)

@Serializable
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
    val messages: List<MsgInfo>? = listOf(),
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
@Serializable
@JsonClass(generateAdapter = true)
data class MsgInfo(
    val id: String = "", // 服务端对应的消息id
    val content: String = "",
    @Json(name = "content_parts") val contentParts: List<ChatMessageContentPart> = emptyList(),
    val role: String = "",
    val meta_data: MsgMetaData? = null, // 附带数据
    val audio_url: String? = null, // 音频文件的url
    val timestamp: String? = null, // 消息时间戳 2025-09-11T03:58:29.077875+00:00
    @Json(name = "user_vote") val user_vote: String? = null, // 用户投票状态：like 或 dislike
    // 本地创建一个msgId，临时用于消息标记
    val localMsgId: String = "${System.nanoTime()}_${role}_${content.hashCode()}",
    // 本地状态：用户反馈（like/dislike）- 不序列化
    val userFeedback: UserFeedback? = null,
    val type: String? = null,
    @Json(name = "festival_memory_id") val festivalMemoryId: Long? = null,
    @Json(name = "daily_memory_id") val dailyMemoryId: Long? = null,
    @Json(name = "media_url") val mediaUrl: String? = null,
    val price: Int = 0,
    @Json(name = "is_locked") val unPurchased: Boolean = true,
    val caption: String? = null,
) {

    fun isOpening(): Boolean {
        return meta_data?.isOpening == true
    }

    fun agentId(): String? {
        return meta_data?.agentId
    }

    fun hasGeneratedImage(): Boolean {
        return meta_data?.generatedImage != null
    }

    fun getGeneratedImageUrl(): String? {
        return meta_data?.generatedImage?.imageUrl
    }

    fun getGeneratedImageWidth(): Int? {
        return meta_data?.generatedImage?.width
    }

    fun getGeneratedImageHeight(): Int? {
        return meta_data?.generatedImage?.height
    }

    fun hasGeneratedMusic(): Boolean {
        return meta_data?.generatedMusic != null
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

    fun getGeneratedMusicUrl(): String? {
        return meta_data?.generatedMusic?.audioUrl ?: audio_url
    }

    /** 判断是否为语音聊天消息 */
    fun isVoiceMessage(): Boolean {
        return meta_data?.isVoice == true
    }

    @Serializable
    @JsonClass(generateAdapter = true)
    data class MsgMetaData(
        val agentId: String? = null,
        @Json(name = "is_voice") val isVoice: Boolean = false,
        val isOpening: Boolean = false,
        val voice_session_id: String? = null,
        @Json(name = "generated_image") val generatedImage: GeneratedImage? = null,
        @Json(name = "generated_music") val generatedMusic: GeneratedMusic? = null,
    ) {
        @Serializable
        @JsonClass(generateAdapter = true)
        data class GeneratedImage(
            @Json(name = "image_url") val imageUrl: String = "",
            val width: Int = 0,
            val height: Int = 0,
        )

        @Serializable
        @JsonClass(generateAdapter = true)
        data class GeneratedMusic(
            @Json(name = "audio_url") val audioUrl: String = "",
            val model: String? = null,
            @Json(name = "duration_sec") val durationSec: Double? = null,
            val format: String? = null,
        )
    }

    // 用户反馈状态（本地状态，不序列化）
    enum class UserFeedback {
        LIKE,
        DISLIKE,
    }
}

@JsonClass(generateAdapter = true)
data class ConversationItem(
    @Json(name = "agent_id") val agentId: String = "",
    @Json(name = "agent_name") val agentName: String = "",
    @Json(name = "agent_avatar") val agentAvatar: String = "",
    @Json(name = "agent_background") val agentBackground: String = "",
    @Json(name = "agent_background_animated") val agentBackgroundAnimated: String = "",
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
) {
    // 本地状态（不序列化）
    val isPinned: Boolean
        get() = IntySetting.isConversationPinned(agentId)

    val isHidden: Boolean
        get() = IntySetting.isConversationHidden(agentId)

    // 判断是否应该显示（有新消息时自动取消隐藏）
    fun shouldShow(): Boolean {
        if (!isHidden) return true
        return IntySetting.hasNewMessageSinceHidden(agentId, lastMessageTime)
    }

    fun getShowTime(): String {
        return TimeUtils.convertUtcToLocal(lastMessageTime)
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
                backgroundAnimatedUrl = agentBackgroundAnimated,
            )
            .also { info -> info.isDeleted = this.isDeleted }
    }
}

// chat settings

/** Chat mode option for list API (id, short_name, name, description). */
@JsonClass(generateAdapter = true)
data class ChatModeOption(
    val id: String = "",
    @Json(name = "short_name") val shortName: String = "",
    val name: String = "",
    val description: String = "",
)

/** 聊天相关的设置接口，注意一个接口多个使用，不需要的参数，保持null，避免覆盖 */
@JsonClass(generateAdapter = true)
data class ChatSettingsReq(
    val keep_talking: Boolean? = null,
    val language: String? = null,
    val premium_mode: Boolean? = null,
    val style_prompt: String? = null,
    val voice_enabled: Boolean? = null,
    val voice_id: String? = null,
    val chat_mode: String? = null,
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
        val voice_id: String? = null, // 选中的语音 ID（MVP: google/*）
        val keep_talking: Boolean? = null, // 连续回复,似乎客户端实现，不需要接口字段
        val premium_mode: Boolean? = null, // 是否会员模式
        val chat_mode: String? = null,
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

/** 聊天消息生图请求（Retrofit 目标类型）。 */
@JsonClass(generateAdapter = true)
data class ChatImageGenerationRequest(
    @Json(name = "message_id") val messageId: Long,
    @Json(name = "history_count") val historyCount: Int? = null,
    val model: String? = null,
)

@JsonClass(generateAdapter = true)
data class ChatMusicGenerationRequest(
    @Json(name = "message_id") val messageId: Long,
    @Json(name = "history_count") val historyCount: Int? = null,
    val model: String? = null,
)

/** 聊天消息生图数据载荷（兼容成功与业务失败两类 data 结构）。 */
@JsonClass(generateAdapter = true)
data class ChatImageGenerationPayload(
    @Json(name = "image_url") val imageUrl: String? = null,
    @Json(name = "image_metadata") val imageMetadata: Map<String, Any?> = emptyMap(),
    val prompt: String? = null,
    @Json(name = "message_id") val messageId: Long? = null,
    val model: String? = null,
    @Json(name = "generation_time_ms") val generationTimeMs: Int? = null,
    @Json(name = "model_fallback_due_to_429") val modelFallbackDueTo429: Boolean? = null,
    val code: Int? = null,
    @Json(name = "error_code") val errorCode: String? = null,
    val message: String? = null,
    @Json(name = "daily_limit") val dailyLimit: Int? = null,
    @Json(name = "used_count") val usedCount: Int? = null,
)

/** 聊天消息生图响应（保留 `code/message/data` 包装，供 no-wrapper Retrofit 解析）。 */
@JsonClass(generateAdapter = true)
data class ChatImageGenerationApiResponse(
    val code: Int? = null,
    val message: String? = null,
    val data: ChatImageGenerationPayload? = null,
)

@JsonClass(generateAdapter = true)
data class ChatMusicGenerationPayload(
    @Json(name = "audio_url") val audioUrl: String? = null,
    @Json(name = "audio_metadata") val audioMetadata: Map<String, Any?> = emptyMap(),
    val prompt: String? = null,
    @Json(name = "message_id") val messageId: Long? = null,
    val model: String? = null,
    @Json(name = "generation_time_ms") val generationTimeMs: Int? = null,
    val code: Int? = null,
    @Json(name = "error_code") val errorCode: String? = null,
    val message: String? = null,
    @Json(name = "daily_limit") val dailyLimit: Int? = null,
    @Json(name = "used_count") val usedCount: Int? = null,
)

@JsonClass(generateAdapter = true)
data class ChatMusicGenerationApiResponse(
    val code: Int? = null,
    val message: String? = null,
    val data: ChatMusicGenerationPayload? = null,
)

/** 聊天消息生图结果（供业务层直接使用的本地 DTO）。 */
@JsonClass(generateAdapter = true)
data class ChatImageGenerationResult(
    @Json(name = "image_url") val imageUrl: String,
    val width: Int,
    val height: Int,
    @Json(name = "message_id") val messageId: Long,
)

@JsonClass(generateAdapter = true)
data class ClearMessagesRequest(
    @Json(name = "message_id") val messageId: Long? = null,
    val timestamp: String? = null,
)

@JsonClass(generateAdapter = true)
data class ClearMessagesResponse(
    val success: Boolean = false,
    val message: String = "",
    @Json(name = "deleted_count") val deletedCount: Int = 0,
    @Json(name = "target_message") val targetMessage: Map<String, Any?>? = null,
    @Json(name = "deleted_time_range") val deletedTimeRange: Map<String, Any?>? = null,
    @Json(name = "cutoff_timestamp") val cutoffTimestamp: String? = null,
)

/** 消息投票常量 */
object VoteConstants {
    const val LIKE = "like"
    const val DISLIKE = "dislike"
}

/** 消息投票请求 */
@JsonClass(generateAdapter = true)
data class VoteMessageReq(
    @Json(name = "agent_id") val agent_id: String,
    @Json(name = "message_id") val message_id: String,
    val vote: String, // 使用 VoteConstants.LIKE 或 VoteConstants.DISLIKE
)

/** 消息投票响应 */
@JsonClass(generateAdapter = true)
data class VoteMessageRsp(
    val code: Int? = null,
    val message: String? = null,
    val data: VoteMessageData? = null,
) {
    data class VoteMessageData(
        val vote: String // VoteConstants.LIKE 或 VoteConstants.DISLIKE
    )
}
