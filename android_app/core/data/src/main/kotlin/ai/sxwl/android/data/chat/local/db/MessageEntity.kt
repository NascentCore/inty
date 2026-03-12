package ai.sxwl.android.data.chat.local.db

// CREATED_BY_AGENT

import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.chat.local.db.MessageEntity.MetaData
import ai.sxwl.android.data.chat.local.db.MessageEntity.MomentExtra
import ai.sxwl.android.data.chat.local.db.MessageEntity.Status
import ai.sxwl.android.data.chat.local.db.MessageEntity.UserVote
import androidx.room.Embedded
import androidx.room.Entity
import androidx.room.Index

@Entity(
    tableName = "message",
    indices = [Index(value = ["agentId"]), Index(value = ["indexId"])],
    primaryKeys = ["id", "agentId", "indexId"],
)
data class MessageEntity(
    val id: String,
    val indexId: String = "",
    val role: String = "",
    val content: String = "",
    val timestamp: String? = null,
    val audioUrl: String? = null,
    val userVote: UserVote? = null,
    @Embedded val metaData: MetaData,
    // 以下为本地字段
    //val isSending: Boolean = false,
    val status: Status? = Status.SUCCESS,
    val type: String? = null,
    val festivalMemoryId: Long? = null,
    @Embedded("moment_") val momentExtra: MomentExtra? = null
) {
    val isVoice: Boolean
        get() = metaData.isVoice

    val isOpening: Boolean
        get() = metaData.isOpening

    fun agentId(): String {
        return metaData.agentId
    }

    fun hasGeneratedImage(): Boolean {
        return metaData.generatedImage != null
    }

    fun getGeneratedImageUrl(): String? {
        return metaData.generatedImage?.imageUrl
    }

    fun getGeneratedImageWidth(): Int? {
        return metaData.generatedImage?.width
    }

    fun getGeneratedImageHeight(): Int? {
        return metaData.generatedImage?.height
    }

    data class MomentExtra(
        val image: String? = null,
        val isPurchased: Boolean = false,
        val price: Int = 10,
    )

    data class MetaData(
        val agentId: String,
        val isVoice: Boolean = false,
        val isOpening: Boolean = false,
        val voiceSessionId: String? = null,
        @Embedded("generate_image_") val generatedImage: GeneratedImage? = null,
    ) {
        data class GeneratedImage(
            val imageUrl: String? = null,
            val width: Int? = null,
            val height: Int? = null,
        )
    }

    // 用户反馈状态（本地状态，不序列化）
    enum class UserVote {
        LIKE,
        DISLIKE,
    }

    enum class Status {
        SUCCESS, //成功
        SENDING, //发送中
        SENDING_FAILED //发送失败
    }
}

data class MessageUpdate(
    val id: String,
    val indexId: String = "",
    val role: String? = null,
    val content: String? = null,
    val timestamp: String? = null,
    val audioUrl: String? = null,
    @Embedded val metaData: MetaData,
    //val isSending: Boolean = false,
    //val status: Status? = null,
    val type: String? = null,
    val festivalMemoryId: Long? = null,
    @Embedded("moment_") val momentExtra: MomentExtra? = null
)

fun MsgInfo.toUpdate(agentId: String): MessageUpdate {
    val extractedTextFromContentParts = extractTextFromContentParts()
    val extractedImageUrlFromContentParts = extractFirstImageUrlFromContentParts()
    return MessageUpdate(
        id = id,
        role = role,
        content =
            content
                .ifBlank { extractedTextFromContentParts }
                .ifBlank { caption.orEmpty() },
        timestamp = timestamp,
        audioUrl = audio_url,
        metaData =
            meta_data?.run {
                MetaData(
                    agentId = this.agentId ?: agentId,
                    isVoice = isVoice,
                    isOpening = isOpening,
                    generatedImage =
                        generatedImage?.run {
                            MetaData.GeneratedImage(
                                imageUrl = imageUrl,
                                width = width,
                                height = height,
                            )
                        }
                            ?: extractedImageUrlFromContentParts?.let { imageUrl ->
                                MetaData.GeneratedImage(
                                    imageUrl = imageUrl,
                                    width = null,
                                    height = null,
                                )
                            },
                    voiceSessionId = voice_session_id,
                )
            } ?: MetaData(agentId),
        type = type,
        festivalMemoryId = festivalMemoryId,
        momentExtra = if (type == "surprise_snap") {
            MessageEntity.MomentExtra(
                image = mediaUrl,
                price = price,
                isPurchased = !unPurchased
            )
        } else null
    )
}

fun MsgInfo.toEntity(): MessageEntity? {
    val extractedTextFromContentParts = extractTextFromContentParts()
    val extractedImageUrlFromContentParts = extractFirstImageUrlFromContentParts()

    return meta_data?.let {
        MessageEntity(
            id = id,
            role = role,
            content =
                content
                    .ifBlank { extractedTextFromContentParts }
                    .ifBlank { caption.orEmpty() },
            timestamp = timestamp,
            audioUrl = audio_url,
            userVote = user_vote?.let { runCatching { UserVote.valueOf(it) }.getOrNull() },
            metaData =
                meta_data.run {
                    MessageEntity.MetaData(
                        agentId = this.agentId.orEmpty(),
                        isVoice = isVoice,
                        isOpening = isOpening,
                        generatedImage =
                            generatedImage?.run {
                                MessageEntity.MetaData.GeneratedImage(
                                    imageUrl = imageUrl,
                                    width = width,
                                    height = height,
                                )
                            }
                                ?: extractedImageUrlFromContentParts?.let { imageUrl ->
                                    MessageEntity.MetaData.GeneratedImage(
                                        imageUrl = imageUrl,
                                        width = null,
                                        height = null,
                                    )
                                },
                    )
                },
            status = MessageEntity.Status.SUCCESS,
            type = type,
            festivalMemoryId = festivalMemoryId,
            momentExtra = if (type == "surprise_snap") {
                MessageEntity.MomentExtra(
                    image = mediaUrl,
                    price = price,
                    isPurchased = !unPurchased
                )
            } else null
        )
    }
}

fun MsgInfo.toEntity(agentId: String): MessageEntity {
    val extractedTextFromContentParts = extractTextFromContentParts()
    val extractedImageUrlFromContentParts = extractFirstImageUrlFromContentParts()
    return MessageEntity(
        id = id,
        role = role,
        content =
            content
                .ifBlank { extractedTextFromContentParts }
                .ifBlank { caption.orEmpty() },
        timestamp = timestamp,
        audioUrl = audio_url,
        userVote = user_vote?.let { runCatching { UserVote.valueOf(it) }.getOrNull() },
        metaData =
            meta_data?.run {
                MessageEntity.MetaData(
                    agentId = this.agentId.orEmpty(),
                    isVoice = isVoice,
                    isOpening = isOpening,
                    generatedImage =
                        generatedImage?.run {
                            MessageEntity.MetaData.GeneratedImage(
                                imageUrl = imageUrl,
                                width = width,
                                height = height,
                            )
                        }
                            ?: extractedImageUrlFromContentParts?.let { imageUrl ->
                                MessageEntity.MetaData.GeneratedImage(
                                    imageUrl = imageUrl,
                                    width = null,
                                    height = null,
                                )
                        },
                )
            } ?: MessageEntity.MetaData(agentId),
        status = MessageEntity.Status.SUCCESS,
        type = type,
        festivalMemoryId = festivalMemoryId,
        momentExtra = if (type == "surprise_snap") {
            MessageEntity.MomentExtra(
                image = mediaUrl,
                price = price,
                isPurchased = !unPurchased
            )
        } else null
    )
}

/** 将 Room 实体转回 MsgInfo，localMsgId 使用实体的 id 以保持稳定。 */
fun MessageEntity.toModel(): MsgInfo {
    return MsgInfo(
        id = id,
        content = content,
        role = role,
        timestamp = timestamp,
        audio_url = audioUrl,
        user_vote = userVote?.name,
        localMsgId = id,
        meta_data =
            MsgInfo.MsgMetaData(
                agentId = metaData.agentId,
                isVoice = metaData.isVoice,
                isOpening = metaData.isOpening,
                generatedImage =
                    metaData.generatedImage?.let { g ->
                        MsgInfo.MsgMetaData.GeneratedImage(
                            imageUrl = g.imageUrl.orEmpty(),
                            width = g.width ?: 0,
                            height = g.height ?: 0,
                        )
                    },
            ),
    )
}

/** 发送中占位内容，与 RoomImpl/ChatRepositoryImpl 中 LOADING_PLACEHOLDER_CONTENT 一致 */
private const val LOADING_PLACEHOLDER_CONTENT = "loading_animation"

/**
 * 创建“正在发送”的用户消息临时实体。id 使用当前最后一条消息的 id，indexId 为最后一条的 indexId + 1。
 * 用于发送前插入本地，发送成功后删除并用 user_message_id 更新为正式消息。
 * @param lastMessageId 当前最后一条消息的 id，无消息时传 null（此时 id 为 "0"）
 * @param lastMessageIndexId 当前最后一条消息的 indexId，无消息时传 null（此时 indexId 为 "1"）
 * @param userImageUrl 用户附带图片的 URL，可选
 */
fun createTempSendingUserEntity(
    agentId: String,
    content: String,
    lastMessageId: String?,
    lastMessageIndexId: String?,
    userImageUrl: String? = null,
): MessageEntity {
    val timestamp = java.time.Instant.ofEpochMilli(System.currentTimeMillis()).toString()
    val id = lastMessageId ?: "0"
    val indexId = "${(lastMessageIndexId?.toLongOrNull() ?: 0L) + 1}"
    return MessageEntity(
        id = id,
        indexId = indexId,
        role = "user",
        content = content,
        timestamp = timestamp,
        metaData =
            MessageEntity.MetaData(
                agentId = agentId,
                generatedImage =
                    userImageUrl?.let {
                        MessageEntity.MetaData.GeneratedImage(
                            imageUrl = it,
                            width = null,
                            height = null,
                        )
                    },
            ),
        status = MessageEntity.Status.SENDING,
    )
}

/**
 * 创建“正在发送”的 loading 占位临时实体。localId 应最大（如 temp_loading_${Long.MAX_VALUE}_${nano}），sortKey 最大。
 * 发送成功后与临时用户消息一并删除。
 */
fun createTempSendingLoadingEntity(agentId: String): MessageEntity {
    val timestamp = java.time.Instant.ofEpochMilli(System.currentTimeMillis()).toString()
    return MessageEntity(
        id = "${(Long.MAX_VALUE)}",
        role = "assistant",
        content = LOADING_PLACEHOLDER_CONTENT,
        timestamp = timestamp,
        metaData = MessageEntity.MetaData(agentId = agentId),
        status = MessageEntity.Status.SENDING,
    )
}
