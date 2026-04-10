package com.ai.imate.chat.data.datasource

import androidx.room.withTransaction
import com.ai.imate.chat.local.db.ChatMessageDao
import com.ai.imate.chat.local.db.ImateChatDatabase
import com.ai.imate.chat.local.db.MessageEntity
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * 聊天本地数据源：Room 为单一可信数据源（与 android_app 的 [ai.sxwl.android.data.chat.data.RoomDataSource] 对齐的薄封装）。
 */
class ChatRoomDataSource(
    private val database: ImateChatDatabase? = null,
    private val dispatcher: CoroutineDispatcher = Dispatchers.IO,
) {

    private val db: ImateChatDatabase by lazy { database ?: ImateChatDatabase.getInstance() }

    private val scope = CoroutineScope(SupervisorJob() + dispatcher)
    private val messageDao: ChatMessageDao by lazy { db.chatMessageDao() }

    fun updateMessageAudioUrl(agentId: String, messageId: String, audioUrl: String) {
        scope.launch { messageDao.updateAudioUrl(agentId, messageId, audioUrl) }
    }

    suspend fun updateMessage(agentId: String, messageId: String, updatedMessage: MessageEntity) =
        withContext(dispatcher) {
            messageDao.upsert(updatedMessage)
        }

    fun updateMessageGeneratedImage(
        agentId: String,
        messageId: String,
        imageUrl: String?,
        width: Int?,
        height: Int?,
    ) {
        scope.launch {
            messageDao.updateGeneratedImage(
                agentId = agentId,
                messageId = messageId,
                url = imageUrl,
                width = width,
                height = height,
            )
        }
    }

    suspend fun removeSendingMessage(agentId: String) {
        withContext(dispatcher) { messageDao.deleteSendingMsg(agentId) }
    }

    suspend fun markSendingFailedAndRemoveLoading(agentId: String) {
        withContext(dispatcher) {
            messageDao.markSendingUserAsFailed(agentId)
            messageDao.deleteSendingLoadingOnly(agentId)
        }
    }

    suspend fun clearChatData(agentId: String) =
        withContext(dispatcher) {
            db.withTransaction { messageDao.deleteByAgent(agentId) }
        }

    suspend fun clearAllChatData() =
        withContext(dispatcher) {
            db.withTransaction { messageDao.deleteAll() }
        }

    fun dao(): ChatMessageDao = messageDao
}
