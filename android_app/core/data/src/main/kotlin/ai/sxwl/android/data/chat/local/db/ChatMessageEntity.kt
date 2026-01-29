package ai.sxwl.android.data.chat.local.db

// CREATED_BY_AGENT

import ai.sxwl.android.data.api.model.MsgInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "chat_messages",
    indices =
        [
            Index(value = ["agentId"]),
            Index(value = ["localId"]),
        ],
    primaryKeys = ["localId", "agentId"]
)
data class ChatMessageEntity(
    val localId: String,
    val agentId: String,
    val remoteId: String?,
    val role: String,
    val content: String,
    val timestamp: String?,
    val audioUrl: String?,
    val userVote: String?,
    val userFeedback: String?,
    val isOpening: Boolean,
    val isVoice: Boolean = false, // 是否为语音聊天消息
    val metaAgentId: String?,
    val generatedImageUrl: String?,
    val generatedImageWidth: Int?,
    val generatedImageHeight: Int?,
    val sortKey: Long,
    val createdAt: Long,
    val updatedAt: Long,
    val isSending: Boolean = false,
)

fun MsgInfo.toEntity(
    agentId: String,
    existing: ChatMessageEntity? = null,
    now: Long = System.nanoTime(),
    isSending: Boolean = false,
): ChatMessageEntity {
    val stableLocalId = resolveLocalId(agentId, existing)
    val hasMetaPayload = meta_data != null
    val generatedImage = meta_data?.generatedImage
    // 始终使用本地时间（now参数）作为sortKey，忽略服务器时间戳以确保正确的本地时间顺序
    // 保留服务器时间戳在timestamp字段中用于显示，但不用于排序
    val sortKey = existing?.sortKey ?: now

    val resolvedMetaAgentId =
        when {
            hasMetaPayload -> meta_data?.agentId ?: agentId
            else -> existing?.metaAgentId ?: agentId
        }
    val resolvedIsOpening =
        when {
            hasMetaPayload -> meta_data?.isOpening ?: false
            else -> existing?.isOpening ?: false
        }
    val resolvedIsVoice =
        when {
            hasMetaPayload -> meta_data?.isVoice ?: false
            else -> existing?.isVoice ?: false
        }
    val resolvedGeneratedImageUrl =
        when {
            hasMetaPayload -> generatedImage?.imageUrl
            else -> existing?.generatedImageUrl
        }
    val resolvedGeneratedImageWidth =
        when {
            hasMetaPayload -> generatedImage?.width
            else -> existing?.generatedImageWidth
        }
    val resolvedGeneratedImageHeight =
        when {
            hasMetaPayload -> generatedImage?.height
            else -> existing?.generatedImageHeight
        }

    // 使用服务器时间戳（用于UI显示），如果不存在则保留现有的timestamp
    // 对于本地消息（如用户消息），如果没有timestamp且没有existing entity，则从当前时间生成
    val resolvedTimestamp =
        timestamp
            ?: existing?.timestamp
            ?: if (existing == null) {
                // 为本地消息生成ISO 8601格式的时间戳
                java.time.Instant.ofEpochMilli(System.currentTimeMillis()).toString()
            } else {
                null
            }

    return ChatMessageEntity(
        localId = id,
        agentId = agentId,
        remoteId = id.takeIf { it.isNotEmpty() } ?: existing?.remoteId,
        role = role,
        content = content,
        timestamp = resolvedTimestamp,
        audioUrl = audio_url ?: existing?.audioUrl,
        userVote = user_vote ?: existing?.userVote,
        userFeedback = userFeedback?.name ?: existing?.userFeedback,
        isOpening = resolvedIsOpening,
        isVoice = resolvedIsVoice,
        metaAgentId = resolvedMetaAgentId,
        generatedImageUrl = resolvedGeneratedImageUrl,
        generatedImageWidth = resolvedGeneratedImageWidth,
        generatedImageHeight = resolvedGeneratedImageHeight,
        sortKey = sortKey,
        createdAt = existing?.createdAt ?: now,
        updatedAt = now,
        isSending = isSending,
    )
}

/** 发送中占位内容，与 RoomImpl/ChatRepositoryImpl 中 LOADING_PLACEHOLDER_CONTENT 一致 */
private const val LOADING_PLACEHOLDER_CONTENT = "loading_animation"

/**
 * 创建“正在发送”的用户消息临时实体。localId 应尽量大（如 temp_user_${Long.MAX_VALUE}_${nano}），sortKey 尽量大。
 * 用于发送前插入本地，发送成功后删除并用 user_message_id 更新为正式消息。
 */
fun createTempSendingUserEntity(
    agentId: String,
    content: String,
    localId: String,
): ChatMessageEntity {
    val timestamp = java.time.Instant.ofEpochMilli(System.currentTimeMillis()).toString()
    return ChatMessageEntity(
        localId = localId,
        agentId = agentId,
        remoteId = null,
        role = "user",
        content = content,
        timestamp = timestamp,
        audioUrl = null,
        userVote = null,
        userFeedback = null,
        isOpening = false,
        isVoice = false,
        metaAgentId = agentId,
        generatedImageUrl = null,
        generatedImageWidth = null,
        generatedImageHeight = null,
        sortKey = 0,
        createdAt = 0,
        updatedAt = 0,
        isSending = true,
    )
}

/**
 * 创建“正在发送”的 loading 占位临时实体。localId 应最大（如 temp_loading_${Long.MAX_VALUE}_${nano}），sortKey 最大。
 * 发送成功后与临时用户消息一并删除。
 */
fun createTempSendingLoadingEntity(agentId: String, localId: String): ChatMessageEntity {
    val timestamp = java.time.Instant.ofEpochMilli(System.currentTimeMillis()).toString()
    return ChatMessageEntity(
        localId = localId,
        agentId = agentId,
        remoteId = null,
        role = "assistant",
        content = LOADING_PLACEHOLDER_CONTENT,
        timestamp = timestamp,
        audioUrl = null,
        userVote = null,
        userFeedback = null,
        isOpening = false,
        isVoice = false,
        metaAgentId = agentId,
        generatedImageUrl = null,
        generatedImageWidth = null,
        generatedImageHeight = null,
        sortKey = 0,
        createdAt = 0,
        updatedAt = 0,
        isSending = true,
    )
}

fun ChatMessageEntity.toModel(): MsgInfo {
    val generatedImage =
        generatedImageUrl?.let {
            MsgInfo.MsgMetaData.GeneratedImage(
                imageUrl = it,
                width = generatedImageWidth ?: 0,
                height = generatedImageHeight ?: 0,
            )
        }

    val meta =
        if (metaAgentId == null && !isOpening && !isVoice && generatedImage == null) {
            null
        } else {
            MsgInfo.MsgMetaData(
                agentId = metaAgentId,
                isOpening = isOpening,
                isVoice = isVoice,
                generatedImage = generatedImage,
            )
        }

    val feedback =
        userFeedback?.let { value ->
            runCatching { MsgInfo.UserFeedback.valueOf(value) }.getOrNull()
        }

    return MsgInfo(
        id = localId,
        content = content,
        role = role,
        meta_data = meta,
        audio_url = audioUrl,
        timestamp = timestamp,
        user_vote = userVote,
        localMsgId = localId,
        userFeedback = feedback,
    )
}

private fun MsgInfo.resolveLocalId(agentId: String, existing: ChatMessageEntity?): String {
    if (existing != null) return existing.localId
    if (id.isNotEmpty()) return id
    if (localMsgId.isNotEmpty()) return localMsgId
    return "${agentId}_${role}_${content.hashCode()}_${System.nanoTime()}"
}
