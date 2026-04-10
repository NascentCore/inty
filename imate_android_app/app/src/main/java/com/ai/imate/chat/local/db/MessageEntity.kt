package com.ai.imate.chat.local.db

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
    val status: Status? = Status.SUCCESS,
    val type: String? = null,
    val festivalMemoryId: Long? = null,
    @Embedded("moment_") val momentExtra: MomentExtra? = null,
) {
    val isVoice: Boolean
        get() = metaData.isVoice

    val isOpening: Boolean
        get() = metaData.isOpening

    fun agentId(): String = metaData.agentId

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

    enum class UserVote {
        LIKE,
        DISLIKE,
    }

    enum class Status {
        SUCCESS,
        SENDING,
        SENDING_FAILED,
    }
}

data class MessageUpdate(
    val id: String,
    val indexId: String = "",
    val role: String = "",
    val content: String = "",
    val timestamp: String? = null,
    val audioUrl: String? = null,
    @Embedded val metaData: MessageEntity.MetaData,
    val type: String? = null,
    val festivalMemoryId: Long? = null,
    @Embedded("moment_") val momentExtra: MessageEntity.MomentExtra? = null,
)

private const val LOADING_PLACEHOLDER_CONTENT = "loading_animation"

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

fun createTempSendingLoadingEntity(agentId: String): MessageEntity {
    val timestamp = java.time.Instant.ofEpochMilli(System.currentTimeMillis()).toString()
    return MessageEntity(
        id = "${Long.MAX_VALUE}",
        indexId = System.nanoTime().toString(),
        role = "assistant",
        content = LOADING_PLACEHOLDER_CONTENT,
        timestamp = timestamp,
        metaData = MessageEntity.MetaData(agentId = agentId),
        status = MessageEntity.Status.SENDING,
    )
}

fun createAgentOpeningMessageEntity(agentId: String, opening: String): MessageEntity =
    MessageEntity(
        id = "__agent_opening__",
        indexId = "0",
        role = "assistant",
        content = opening,
        timestamp = null,
        metaData =
            MessageEntity.MetaData(
                agentId = agentId,
                isOpening = true,
            ),
        status = MessageEntity.Status.SUCCESS,
    )
