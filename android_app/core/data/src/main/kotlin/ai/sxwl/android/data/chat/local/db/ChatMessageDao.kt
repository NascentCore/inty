package ai.sxwl.android.data.chat.local.db

// CREATED_BY_AGENT

import androidx.paging.PagingSource
import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

data class AgentMessageCount(val agentId: String, val messageCount: Int)

@Dao
interface ChatMessageDao {

    @Query(
        "SELECT * FROM chat_messages WHERE agentId = :agentId ORDER BY sortKey DESC, createdAt DESC"
    )
    fun streamMessages(agentId: String): Flow<List<ChatMessageEntity>>

    /**
     * 返回 PagingSource，用于配合 RemoteMediator 进行分页加载 按 sortKey DESC 排序，最新的消息在列表底部 排除 isOpening 为 true
     * 的数据
     */
    @Query(
        "SELECT * FROM chat_messages WHERE agentId = :agentId AND isOpening = 0 ORDER BY localId DESC"
    )
    fun pagingSource(agentId: String): PagingSource<Int, ChatMessageEntity>

    @Query("SELECT COUNT(*) FROM chat_messages WHERE agentId = :agentId AND isOpening = 0")
    suspend fun getMessagesCount(agentId: String): Int

    /** 查询用户是否对该 agent 发送过消息（存在 role = 'user' 的记录即视为发送过） */
    @Query("SELECT COUNT(*) FROM chat_messages WHERE agentId = :agentId AND role = 'user'")
    suspend fun countUserMessages(agentId: String): Int

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(messages: List<ChatMessageEntity>)

    @Insert(onConflict = OnConflictStrategy.REPLACE) suspend fun upsert(entity: ChatMessageEntity)

    @Query(
        "SELECT * FROM chat_messages WHERE agentId = :agentId AND (localId = :messageId OR remoteId = :messageId) LIMIT 1"
    )
    suspend fun getMessage(agentId: String, messageId: String): ChatMessageEntity?

    @Query(
        "DELETE FROM chat_messages WHERE agentId = :agentId AND (localId = :messageId OR remoteId = :messageId)"
    )
    suspend fun deleteMessage(agentId: String, messageId: String)

    @Query("DELETE FROM chat_messages WHERE agentId = :agentId AND isSending = 1")
    suspend fun deleteSendingMsg(agentId: String)

    @Query("DELETE FROM chat_messages WHERE agentId = :agentId")
    suspend fun deleteByAgent(agentId: String)

    @Query("DELETE FROM chat_messages") suspend fun deleteAll()

    @Query(
        "UPDATE chat_messages SET audioUrl = :audioUrl, updatedAt = :updatedAt WHERE agentId = :agentId AND (localId = :messageId OR remoteId = :messageId)"
    )
    suspend fun updateAudioUrl(
        agentId: String,
        messageId: String,
        audioUrl: String?,
        updatedAt: Long,
    )

    @Query(
        "UPDATE chat_messages SET userFeedback = :feedback, updatedAt = :updatedAt WHERE agentId = :agentId AND (localId = :messageId OR remoteId = :messageId)"
    )
    suspend fun updateUserFeedback(
        agentId: String,
        messageId: String,
        feedback: String?,
        updatedAt: Long,
    )

    @Query(
        "UPDATE chat_messages SET generatedImageUrl = :url, generatedImageWidth = :width, generatedImageHeight = :height, updatedAt = :updatedAt WHERE agentId = :agentId AND (localId = :messageId OR remoteId = :messageId)"
    )
    suspend fun updateGeneratedImage(
        agentId: String,
        messageId: String,
        url: String?,
        width: Int?,
        height: Int?,
        updatedAt: Long,
    )

    @Query("SELECT MAX(sortKey) FROM chat_messages WHERE agentId = :agentId")
    suspend fun getMaxSortKey(agentId: String): Long?

    @Query("SELECT MIN(sortKey) FROM chat_messages WHERE agentId = :agentId")
    suspend fun getMinSortKey(agentId: String): Long?

    @Query("SELECT * FROM chat_messages WHERE agentId = :agentId")
    suspend fun getAllMessages(agentId: String): List<ChatMessageEntity>

    @Query("SELECT COUNT(*) FROM chat_messages WHERE agentId = :agentId")
    suspend fun getMessageCount(agentId: String): Int

    @Query(
        "SELECT agentId AS agentId, COUNT(*) AS messageCount FROM chat_messages WHERE agentId IN (:agentIds) GROUP BY agentId"
    )
    suspend fun getMessageCounts(agentIds: List<String>): List<AgentMessageCount>

    @Query(
        "SELECT * FROM chat_messages WHERE agentId = :agentId AND role = 'assistant' AND generatedImageUrl IS NOT NULL AND generatedImageUrl != '' AND generatedImageUrl != 'loading' ORDER BY sortKey DESC, createdAt DESC"
    )
    fun streamMessagesWithImages(agentId: String): Flow<List<ChatMessageEntity>>

    /** 查询该 agent 最近一条 AI 回复消息，排除 isOpening = true（开场白） */
    @Query(
        "SELECT * FROM chat_messages WHERE agentId = :agentId AND role = 'assistant' AND isOpening = 0 ORDER BY sortKey DESC, createdAt DESC LIMIT 1"
    )
    suspend fun getLatestAgentMessage(agentId: String): ChatMessageEntity?
}
