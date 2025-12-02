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
            Index(value = ["remoteId"]),
            Index(value = ["agentId", "sortKey"]),
        ],
)
data class ChatMessageEntity(
    @PrimaryKey val localId: String,
    val agentId: String,
    val remoteId: String?,
    val role: String,
    val content: String,
    val timestamp: String?,
    val audioUrl: String?,
    val userVote: String?,
    val userFeedback: String?,
    val isOpening: Boolean,
    val metaAgentId: String?,
    val generatedImageUrl: String?,
    val generatedImageWidth: Int?,
    val generatedImageHeight: Int?,
    val sortKey: Long,
    val createdAt: Long,
    val updatedAt: Long,
)

internal fun MsgInfo.toEntity(
    agentId: String,
    existing: ChatMessageEntity? = null,
    now: Long = System.nanoTime(),
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
        localId = stableLocalId,
        agentId = agentId,
        remoteId = id.takeIf { it.isNotEmpty() } ?: existing?.remoteId,
        role = role,
        content = content,
        timestamp = resolvedTimestamp,
        audioUrl = audio_url ?: existing?.audioUrl,
        userVote = user_vote ?: existing?.userVote,
        userFeedback = userFeedback?.name ?: existing?.userFeedback,
        isOpening = resolvedIsOpening,
        metaAgentId = resolvedMetaAgentId,
        generatedImageUrl = resolvedGeneratedImageUrl,
        generatedImageWidth = resolvedGeneratedImageWidth,
        generatedImageHeight = resolvedGeneratedImageHeight,
        sortKey = sortKey,
        createdAt = existing?.createdAt ?: now,
        updatedAt = now,
    )
}

internal fun ChatMessageEntity.toModel(): MsgInfo {
    val generatedImage =
        generatedImageUrl?.let {
            MsgInfo.MsgMetaData.GeneratedImage(
                imageUrl = it,
                width = generatedImageWidth ?: 0,
                height = generatedImageHeight ?: 0,
            )
        }

    val meta =
        if (metaAgentId == null && !isOpening && generatedImage == null) {
            null
        } else {
            MsgInfo.MsgMetaData(
                agentId = metaAgentId,
                isOpening = isOpening,
                generatedImage = generatedImage,
            )
        }

    val feedback =
        userFeedback?.let { value ->
            runCatching { MsgInfo.UserFeedback.valueOf(value) }.getOrNull()
        }

    return MsgInfo(
        id = remoteId.orEmpty(),
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
