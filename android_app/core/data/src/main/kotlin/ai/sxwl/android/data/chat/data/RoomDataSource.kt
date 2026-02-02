package ai.sxwl.android.data.chat.data

import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.chat.local.db.ChatMessageDao
import ai.sxwl.android.data.chat.local.db.ChatSyncStateDao
import ai.sxwl.android.data.chat.local.db.IntyChatDatabase
import ai.sxwl.android.data.chat.local.db.MessageEntity
import androidx.room.withTransaction
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import mu.KotlinLogging

/**
 * 聊天本地数据源 使用 Room 作为单一可信数据源，遵循 Offline-First 设计：
 * - 所有 UI 读取来自本地数据库（StateFlow）
 * - 网络同步只负责刷新数据库
 * - 分页状态（hasMore/offset）持久化到 sync 表
 *
 * 目前还未接入 IntelliMate，是引入 Room IntelliMate 中的一步
 */
class RoomDataSource(
    private val database: IntyChatDatabase? = null,
    private val dispatcher: CoroutineDispatcher = Dispatchers.IO,
) {

    private val logger = KotlinLogging.logger {}

    // 延迟初始化数据库，避免在应用未初始化时调用Utils.getApp()
    private val db: IntyChatDatabase by lazy { database ?: IntyChatDatabase.getInstance() }

    private val scope = CoroutineScope(SupervisorJob() + dispatcher)
    private val messageDao: ChatMessageDao by lazy { db.chatMessageDao() }
    private val syncStateDao: ChatSyncStateDao by lazy { db.chatSyncStateDao() }

    fun updateMessageAudioUrl(agentId: String, messageId: String, audioUrl: String) {
        scope.launch { messageDao.updateAudioUrl(agentId, messageId, audioUrl) }
    }

    suspend fun updateMessage(agentId: String, messageId: String, updatedMessage: MessageEntity) =
        withContext(dispatcher) { messageDao.upsert(updatedMessage) }

    fun updateMessageGeneratedImage(
        agentId: String,
        messageId: String,
        generatedImage: MsgInfo.MsgMetaData.GeneratedImage?,
    ) {
        scope.launch {
            messageDao.updateGeneratedImage(
                agentId = agentId,
                messageId = messageId,
                url = generatedImage?.imageUrl,
                width = generatedImage?.width,
                height = generatedImage?.height,
            )
        }
    }

    suspend fun removeSendingMessage(agentId: String) {
        with(dispatcher) { messageDao.deleteSendingMsg(agentId) }
    }

    suspend fun clearChatData(agentId: String) =
        withContext(dispatcher) {
            logger.debug { "RoomDataSource.clearChatData starting for agent $agentId" }
            db.withTransaction {
                messageDao.deleteByAgent(agentId)
                syncStateDao.delete(agentId)
            }
            // 等待数据库操作完成后再清理内存状态和设置
            logger.info { "RoomDataSource cleared chat data for agent $agentId" }
        }

    suspend fun clearAllChatData() =
        withContext(dispatcher) {
            logger.debug { "RoomDataSource.clearAllChatData starting" }
            db.withTransaction {
                messageDao.deleteAll()
                syncStateDao.deleteAll()
            }
            logger.info { "RoomDataSource cleared all chat data" }
        }

    private fun now(): Long = System.currentTimeMillis()
}
