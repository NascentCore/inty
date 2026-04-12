package ai.sxwl.android.data.chat.local.db

// CREATED_BY_AGENT

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

    /**
     * 返回 PagingSource，用于配合 RemoteMediator 进行分页加载 按 sortKey DESC 排序，最新的消息在列表底部 排除 isOpening 为 true
     * 的数据
     */
    @Query(
        "SELECT * FROM message WHERE agentId = :agentId AND isOpening = 0 ORDER BY Cast(id as INTEGER) DESC, Cast(indexId as INTEGER) DESC, indexId DESC"
    )
    fun pagingSource(agentId: String): PagingSource<Int, MessageEntity>

    @Query("SELECT COUNT(*) FROM message WHERE agentId = :agentId AND isOpening = 0")
    suspend fun getMessagesCount(agentId: String): Int

    @Query("SELECT COUNT(*) FROM message WHERE agentId = :agentId AND isOpening = 0")
    fun messageCountFlow(agentId: String): Flow<Int>

    /** 查询用户是否对该 agent 发送过消息（存在 role = 'user' 的记录即视为发送过） */
    @Query("SELECT COUNT(*) FROM message WHERE agentId = :agentId AND role = 'user'")
    suspend fun countUserMessages(agentId: String): Int

    /** 当前会话用户消息数量的 Flow，用于 UI 根据是否有用户消息启用/禁用重置等操作 */
    @Query("SELECT COUNT(*) FROM message WHERE agentId = :agentId AND role = 'user'")
    fun userMessageCountFlow(agentId: String): Flow<Int>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(messages: List<MessageEntity>)

    @Upsert(entity = MessageEntity::class) suspend fun insertOrDrop(messages: List<MessageUpdate>)

    @Insert(onConflict = OnConflictStrategy.REPLACE) suspend fun upsert(entity: MessageEntity)

    @Query("SELECT * FROM message WHERE agentId = :agentId AND id = :messageId LIMIT 1")
    suspend fun getMessage(agentId: String, messageId: String): MessageEntity?

    @Query(
        "DELETE FROM message WHERE agentId = :agentId AND id = :messageId AND indexId = :indexId"
    )
    suspend fun deleteMessage(agentId: String, messageId: String, indexId: String)

    @Query("DELETE FROM message WHERE agentId = :agentId AND status = 'SENDING'")
    suspend fun deleteSendingMsg(agentId: String)

    /** 将发送中的用户消息标记为 SENDING_FAILED（仅更新 status，不删记录） */
    @Query(
        "UPDATE message SET status = 'SENDING_FAILED' WHERE agentId = :agentId AND status = 'SENDING' AND role = 'user'"
    )
    suspend fun markSendingUserAsFailed(agentId: String)

    @Query(
        "UPDATE message SET generate_image_imageUrl = :imageUrl, generate_image_width = :width, generate_image_height = :height WHERE agentId = :agentId AND status = 'SENDING' AND role = 'user'"
    )
    suspend fun updateSendingUserImage(agentId: String, imageUrl: String, width: Int?, height: Int?)

    /** 仅删除 createTempSendingLoadingEntity 创建的 loading 占位消息（role=assistant 且 status=SENDING） */
    @Query(
        "DELETE FROM message WHERE agentId = :agentId AND status = 'SENDING' AND role = 'assistant'"
    )
    suspend fun deleteSendingLoadingOnly(agentId: String)

    @Query("DELETE FROM message WHERE agentId = :agentId")
    suspend fun deleteByAgent(agentId: String)

    @Query("DELETE FROM message") suspend fun deleteAll()

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

    /** 查询该 agent 最近一条 AI 回复消息，排除 isOpening = true（开场白） */
    @Query(
        "SELECT * FROM message WHERE agentId = :agentId AND role = 'assistant' AND isOpening = 0 ORDER BY Cast(id as INTEGER) DESC LIMIT 1"
    )
    suspend fun getLatestAgentMessage(agentId: String): MessageEntity?

    @Query(
        "SELECT id FROM message WHERE agentId = :agentId ORDER BY Cast(id as INTEGER) DESC LIMIT 1"
    )
    suspend fun getLatestMessageId(agentId: String): String?

    /** 当前会话最后一条消息（按 id DESC, indexId 数值 DESC, indexId 串 DESC），用于创建发送中占位时沿用其 id 与 indexId+1 */
    @Query(
        "SELECT * FROM message WHERE agentId = :agentId AND isOpening = 0 ORDER BY Cast(id as INTEGER) DESC, Cast(indexId as INTEGER) DESC, indexId DESC LIMIT 1"
    )
    suspend fun getLatestMessage(agentId: String): MessageEntity?

    /**
     * 最后一条非「发送中 loading」的消息。连续发送时若用 [getLatestMessage] 会取到 loading（id 极大），导致第二条发送中用户主键错乱、 收包时误删多条。
     */
    @Query(
        "SELECT * FROM message WHERE agentId = :agentId AND isOpening = 0 AND NOT (status = 'SENDING' AND role = 'assistant' AND content = 'loading_animation') ORDER BY Cast(id as INTEGER) DESC, Cast(indexId as INTEGER) DESC, indexId DESC LIMIT 1"
    )
    suspend fun getLatestMessageExcludingSendingLoading(agentId: String): MessageEntity?

    /** 最近一条发送中的用户消息（用于只更新刚发送那条的图片）。 */
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

    /** 查询前一天（本地日期）用户发送的消息总数（role = 'user'，按 timestamp 所在本地日统计） */
    @Query(
        "SELECT COUNT(*) FROM message WHERE role = 'user' AND timestamp IS NOT NULL AND date(timestamp, 'localtime') = date('now', 'localtime', '-1 day')"
    )
    suspend fun getYesterdayMessageCount(): Int

    @Delete suspend fun deleteMessage(messages: List<MessageEntity>)

    @Update suspend fun updateMessage(message: MessageEntity)
}
