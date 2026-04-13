package com.inty.imate.chat.data

import com.inty.imate.chat.data.bean.MsgInfo
import com.inty.imate.chat.local.db.MessageEntity
import com.inty.imate.chat.local.db.MessageUpdate

fun MsgInfo.toMessageEntity(): MessageEntity? {
    val extractedTextFromContentParts = extractTextFromContentParts()
    val extractedImageUrlFromContentParts = extractFirstImageUrlFromContentParts()

    return meta_data?.let {
        MessageEntity(
            id = id,
            role = role,
            content =
                content.ifBlank { extractedTextFromContentParts }.ifBlank { caption.orEmpty() },
            timestamp = timestamp,
            audioUrl = audio_url,
            userVote = user_vote?.let { runCatching { MessageEntity.UserVote.valueOf(it) }.getOrNull() },
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
            momentExtra =
                if (type == "surprise_snap") {
                    MessageEntity.MomentExtra(
                        image = mediaUrl,
                        price = price,
                        isPurchased = !unPurchased,
                    )
                } else null,
        )
    }
}

fun MsgInfo.toMessageEntity(agentId: String): MessageEntity {
    val extractedTextFromContentParts = extractTextFromContentParts()
    val extractedImageUrlFromContentParts = extractFirstImageUrlFromContentParts()
    return MessageEntity(
        id = id,
        role = role,
        content = content.ifBlank { extractedTextFromContentParts }.ifBlank { caption.orEmpty() },
        timestamp = timestamp,
        audioUrl = audio_url,
        userVote = user_vote?.let { runCatching { MessageEntity.UserVote.valueOf(it) }.getOrNull() },
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
        momentExtra =
            if (type == "surprise_snap") {
                MessageEntity.MomentExtra(
                    image = mediaUrl,
                    price = price,
                    isPurchased = !unPurchased,
                )
            } else null,
    )
}

fun MsgInfo.toMessageUpdate(agentId: String): MessageUpdate {
    val extractedTextFromContentParts = extractTextFromContentParts()
    val extractedImageUrlFromContentParts = extractFirstImageUrlFromContentParts()
    return MessageUpdate(
        id = id,
        role = role,
        content = content.ifBlank { extractedTextFromContentParts }.ifBlank { caption.orEmpty() },
        timestamp = timestamp,
        audioUrl = audio_url,
        metaData =
            meta_data?.run {
                MessageEntity.MetaData(
                    agentId = this.agentId ?: agentId,
                    isVoice = isVoice,
                    isOpening = isOpening,
                    voiceSessionId = voice_session_id,
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
        type = type,
        festivalMemoryId = festivalMemoryId,
        momentExtra =
            if (type == "surprise_snap") {
                MessageEntity.MomentExtra(
                    image = mediaUrl,
                    price = price,
                    isPurchased = !unPurchased,
                )
            } else null,
    )
}
