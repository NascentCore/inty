package ai.sxwl.android.data.chat.local.db

// CREATED_BY_AGENT

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface ChatMessageDao {

    @Query(
        "SELECT * FROM chat_messages WHERE agentId = :agentId ORDER BY " +
            "CASE " +
            "WHEN remoteId IS NOT NULL AND remoteId != '' AND remoteId GLOB '[0-9]*' THEN CAST(remoteId AS INTEGER) " +
            "WHEN localId GLOB '[0-9]*' THEN CAST(localId AS INTEGER) " +
            "ELSE 999999999 " +
            "END DESC, " +
            "timestamp DESC, createdAt DESC"
    )
    fun streamMessages(agentId: String): Flow<List<ChatMessageEntity>>

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

    @Query("SELECT * FROM chat_messages WHERE agentId = :agentId")
    suspend fun getAllMessages(agentId: String): List<ChatMessageEntity>
}
