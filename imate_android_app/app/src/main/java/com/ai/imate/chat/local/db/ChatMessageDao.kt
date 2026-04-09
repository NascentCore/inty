package com.ai.imate.chat.local.db

import androidx.paging.PagingSource
import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import androidx.room.Upsert
import kotlinx.coroutines.flow.Flow

data class AgentMessageCount(val agentId: String, val messageCount: Int)

@Dao
interface ChatMessageDao {

    @Query(
        "SELECT * FROM message WHERE agentId = :agentId AND isOpening = 0 ORDER BY Cast(id as INTEGER) DESC, Cast(indexId as INTEGER) DESC, indexId DESC"
    )
    fun pagingSource(agentId: String): PagingSource<Int, MessageEntity>

    @Query("SELECT COUNT(*) FROM message WHERE agentId = :agentId AND isOpening = 0")
    suspend fun getMessagesCount(agentId: String): Int

    @Query("SELECT COUNT(*) FROM message WHERE agentId = :agentId AND isOpening = 0")
    fun messageCountFlow(agentId: String): Flow<Int>

    @Query("SELECT COUNT(*) FROM message WHERE agentId = :agentId AND role = 'user'")
    suspend fun countUserMessages(agentId: String): Int

    @Query("SELECT COUNT(*) FROM message WHERE agentId = :agentId AND role = 'user'")
    fun userMessageCountFlow(agentId: String): Flow<Int>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(messages: List<MessageEntity>)

    @Upsert(entity = MessageEntity::class)
    suspend fun insertOrDrop(messages: List<MessageUpdate>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(entity: MessageEntity)

    @Query("SELECT * FROM message WHERE agentId = :agentId AND id = :messageId LIMIT 1")
    suspend fun getMessage(agentId: String, messageId: String): MessageEntity?

    @Query(
        "DELETE FROM message WHERE agentId = :agentId AND id = :messageId AND indexId = :indexId"
    )
    suspend fun deleteMessage(agentId: String, messageId: String, indexId: String)

    @Query("DELETE FROM message WHERE agentId = :agentId AND status = 'SENDING'")
    suspend fun deleteSendingMsg(agentId: String)

    @Query(
        "SELECT * FROM message WHERE agentId = :agentId AND status = 'SENDING' AND role = 'user' LIMIT 1"
    )
    suspend fun getSendingUserMessage(agentId: String): MessageEntity?

    @Query(
        "SELECT * FROM message WHERE agentId = :agentId AND status = 'SENDING' AND role = 'user' ORDER BY Cast(id as INTEGER) ASC, Cast(indexId as INTEGER) ASC, indexId ASC LIMIT 1"
    )
    suspend fun getEarliestSendingUserMessage(agentId: String): MessageEntity?

    @Query(
        "UPDATE message SET status = 'SENDING_FAILED' WHERE agentId = :agentId AND status = 'SENDING' AND role = 'user'"
    )
    suspend fun markSendingUserAsFailed(agentId: String)

    @Query(
        "UPDATE message SET generate_image_imageUrl = :imageUrl, generate_image_width = :width, generate_image_height = :height WHERE agentId = :agentId AND status = 'SENDING' AND role = 'user'"
    )
    suspend fun updateSendingUserImage(agentId: String, imageUrl: String, width: Int?, height: Int?)

    @Query(
        "DELETE FROM message WHERE agentId = :agentId AND status = 'SENDING' AND role = 'assistant'"
    )
    suspend fun deleteSendingLoadingOnly(agentId: String)

    @Query("DELETE FROM message WHERE agentId = :agentId")
    suspend fun deleteByAgent(agentId: String)

    @Query("DELETE FROM message")
    suspend fun deleteAll()

    @Query("UPDATE message SET audioUrl = :audioUrl WHERE agentId = :agentId AND id = :messageId")
    suspend fun updateAudioUrl(agentId: String, messageId: String, audioUrl: String?)

    @Query("UPDATE message SET userVote = :feedback WHERE agentId = :agentId AND id = :messageId")
    suspend fun updateUserFeedback(
        agentId: String,
        messageId: String,
        feedback: MessageEntity.UserVote?,
    )

    @Query(
        "UPDATE message SET generate_image_imageUrl = :url, generate_image_width = :width, generate_image_height = :height WHERE agentId = :agentId AND id = :messageId"
    )
    suspend fun updateGeneratedImage(
        agentId: String,
        messageId: String,
        url: String?,
        width: Int?,
        height: Int?,
    )

    @Query("SELECT * FROM message WHERE agentId = :agentId ORDER BY Cast(id as INTEGER) DESC")
    suspend fun getAllMessages(agentId: String): List<MessageEntity>

    @Query("SELECT COUNT(*) FROM message WHERE agentId = :agentId")
    suspend fun getMessageCount(agentId: String): Int

    @Query(
        "SELECT agentId AS agentId, COUNT(*) AS messageCount FROM message WHERE agentId IN (:agentIds) GROUP BY agentId"
    )
    suspend fun getMessageCounts(agentIds: List<String>): List<AgentMessageCount>

    @Query(
        "SELECT * FROM message WHERE agentId = :agentId AND role = 'assistant' AND generate_image_imageUrl IS NOT NULL AND generate_image_imageUrl != '' AND generate_image_imageUrl != 'loading' ORDER BY Cast(id as INTEGER) DESC"
    )
    fun streamMessagesWithImages(agentId: String): Flow<List<MessageEntity>>

    @Query(
        "SELECT * FROM message WHERE agentId = :agentId AND role = 'assistant' AND isOpening = 0 ORDER BY Cast(id as INTEGER) DESC LIMIT 1"
    )
    suspend fun getLatestAgentMessage(agentId: String): MessageEntity?

    @Query(
        "SELECT id FROM message WHERE agentId = :agentId ORDER BY Cast(id as INTEGER) DESC LIMIT 1"
    )
    suspend fun getLatestMessageId(agentId: String): String?

    @Query(
        "SELECT * FROM message WHERE agentId = :agentId AND isOpening = 0 ORDER BY Cast(id as INTEGER) DESC, Cast(indexId as INTEGER) DESC, indexId DESC LIMIT 1"
    )
    suspend fun getLatestMessage(agentId: String): MessageEntity?

    @Query(
        "SELECT * FROM message WHERE agentId = :agentId AND isOpening = 0 AND NOT (status = 'SENDING' AND role = 'assistant' AND content = 'loading_animation') ORDER BY Cast(id as INTEGER) DESC, Cast(indexId as INTEGER) DESC, indexId DESC LIMIT 1"
    )
    suspend fun getLatestMessageExcludingSendingLoading(agentId: String): MessageEntity?

    @Query(
        "SELECT * FROM message WHERE agentId = :agentId AND status = 'SENDING' AND role = 'user' ORDER BY Cast(id as INTEGER) DESC, Cast(indexId as INTEGER) DESC, indexId DESC LIMIT 1"
    )
    suspend fun getLatestSendingUserMessage(agentId: String): MessageEntity?

    @Query(
        "UPDATE message SET generate_image_imageUrl = :imageUrl, generate_image_width = :width, generate_image_height = :height WHERE agentId = :agentId AND id = :messageId AND indexId = :indexId"
    )
    suspend fun updateSendingUserImageByKey(
        agentId: String,
        messageId: String,
        indexId: String,
        imageUrl: String,
        width: Int?,
        height: Int?,
    )

    @Query(
        "UPDATE message SET moment_isPurchased = :isPurchased WHERE agentId = :agentId AND id = :messageId"
    )
    suspend fun setForMomentPurchaseState(agentId: String, messageId: String, isPurchased: Boolean)

    @Query(
        "SELECT COUNT(*) FROM message WHERE role = 'user' AND timestamp IS NOT NULL AND date(timestamp, 'localtime') = date('now', 'localtime', '-1 day')"
    )
    suspend fun getYesterdayMessageCount(): Int

    @Delete
    suspend fun deleteMessage(messages: List<MessageEntity>)

    @Update
    suspend fun updateMessage(message: MessageEntity)
}
