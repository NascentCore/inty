package com.ai.imate.chat.data.datasource

import androidx.paging.PagingSource
import androidx.room.withTransaction
import com.ai.imate.chat.local.db.ChatMessageDao
import com.ai.imate.chat.local.db.ImateChatDatabase
import com.ai.imate.chat.local.db.MessageEntity
import com.ai.imate.chat.local.db.createTempSendingLoadingEntity
import com.ai.imate.chat.local.db.createTempSendingUserEntity
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

@Singleton
class ChatLocalDataSource
@Inject
constructor() {
    private val database: ImateChatDatabase = ImateChatDatabase.getInstance()
    private val chatMessageDao: ChatMessageDao = database.chatMessageDao()

    suspend fun appendSendingMessages(agentId: String, content: String) {
        withContext(Dispatchers.IO) {
            chatMessageDao.deleteSendingLoadingOnly(agentId)
            val last = chatMessageDao.getLatestMessageExcludingSendingLoading(agentId)
            val userEntity =
                createTempSendingUserEntity(
                    agentId = agentId,
                    content = content,
                    lastMessageId = last?.id,
                    lastMessageIndexId = last?.indexId,
                    userImageUrl = null,
                )
            val loadingEntity = createTempSendingLoadingEntity(agentId)
            chatMessageDao.upsert(listOf(userEntity, loadingEntity))
        }
    }

    suspend fun removeSendingMessage(agentId: String) {
        withContext(Dispatchers.IO) { chatMessageDao.deleteSendingMsg(agentId) }
    }

    suspend fun markSendingFailedAndRemoveLoading(agentId: String) {
        withContext(Dispatchers.IO) {
            database.withTransaction {
                chatMessageDao.markSendingUserAsFailed(agentId)
                chatMessageDao.deleteSendingLoadingOnly(agentId)
            }
        }
    }

    suspend fun getEarliestSendingUserMessage(agentId: String): MessageEntity? =
        withContext(Dispatchers.IO) { chatMessageDao.getEarliestSendingUserMessage(agentId) }

    suspend fun removeEarliestSendingUserAndLoadingIfLast(agentId: String) {
        withContext(Dispatchers.IO) {
            val earliest = chatMessageDao.getEarliestSendingUserMessage(agentId) ?: return@withContext
            chatMessageDao.deleteMessage(agentId, earliest.id, earliest.indexId)
            if (chatMessageDao.getEarliestSendingUserMessage(agentId) == null) {
                chatMessageDao.deleteSendingLoadingOnly(agentId)
            }
        }
    }

    suspend fun markEarliestSendingUserAsFailedAndRemoveLoadingIfLast(agentId: String) {
        withContext(Dispatchers.IO) {
            val earliest = chatMessageDao.getEarliestSendingUserMessage(agentId) ?: return@withContext
            chatMessageDao.updateMessage(earliest.copy(status = MessageEntity.Status.SENDING_FAILED))
            if (chatMessageDao.getEarliestSendingUserMessage(agentId) == null) {
                chatMessageDao.deleteSendingLoadingOnly(agentId)
            }
        }
    }

    suspend fun appendMessages(messages: List<MessageEntity>) {
        withContext(Dispatchers.IO) { chatMessageDao.upsert(messages) }
    }

    suspend fun getAllMessages(agentId: String): List<MessageEntity> =
        withContext(Dispatchers.IO) { chatMessageDao.getAllMessages(agentId) }

    suspend fun getLatestMessage(agentId: String): MessageEntity? =
        withContext(Dispatchers.IO) { chatMessageDao.getLatestMessage(agentId) }

    suspend fun getMessage(agentId: String, messageId: String): MessageEntity? =
        withContext(Dispatchers.IO) { chatMessageDao.getMessage(agentId, messageId) }

    fun messagesPagingSource(agentId: String): PagingSource<Int, MessageEntity> =
        chatMessageDao.pagingSource(agentId)
}
