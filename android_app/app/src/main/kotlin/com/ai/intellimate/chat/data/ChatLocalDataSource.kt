package com.ai.intellimate.chat.data

import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.chat.local.db.IntyChatDatabase
import ai.sxwl.android.data.chat.local.db.MessageEntity
import ai.sxwl.android.data.chat.local.db.SyncStateEntity
import ai.sxwl.android.data.chat.local.db.createTempSendingLoadingEntity
import ai.sxwl.android.data.chat.local.db.createTempSendingUserEntity
import androidx.room.withTransaction
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.withContext

class ChatLocalDataSource(private val database: IntyChatDatabase = IntyChatDatabase.getInstance()) {
    val chatMessageDao = database.chatMessageDao()
    val syncStateDao = database.chatSyncStateDao()

    suspend fun getMessageCounts(agentId: String): Int {
        return chatMessageDao.getMessagesCount(agentId)
    }

    suspend fun countUserMessages(agentId: String): Int {
        return chatMessageDao.countUserMessages(agentId)
    }

    suspend fun clearMessages(agentId: String) {
        chatMessageDao.deleteByAgent(agentId)
    }

    suspend fun getLatesAgentMessage(agentId: String): MessageEntity? {
        return chatMessageDao.getLatestAgentMessage(agentId)
    }

    suspend fun removeMessage(agentId: String, messageId: String, indexId: String): MessageEntity? {
        val entity = chatMessageDao.getMessage(agentId, messageId)
        if (entity != null) chatMessageDao.deleteMessage(agentId, messageId, indexId)
        return entity
    }

    suspend fun upsert(entity: MessageEntity) {
        chatMessageDao.upsert(entity)
    }

    suspend fun getMessage(agentId: String, messageId: String): MessageEntity? {
        return chatMessageDao.getMessage(agentId, messageId)
    }

    suspend fun updateSyncState(
        agentId: String,
        updater: (SyncStateEntity) -> SyncStateEntity,
    ) {
        val current = syncStateDao.get(agentId) ?: SyncStateEntity(agentId = agentId)
        syncStateDao.upsert(updater(current).copy(updatedAt = System.currentTimeMillis()))
    }

    suspend fun appendSendingMessages(agentId: String, userContent: String) {

        val userEntity =
            createTempSendingUserEntity(
                agentId = agentId,
                content = userContent
            )
        val loadingEntity =
            createTempSendingLoadingEntity(agentId = agentId)

        chatMessageDao.upsert(listOf(userEntity, loadingEntity))
    }

    /**
     * 仅插入“正在发送”的 loading 占位（isSending=true），用于 recall 等不附带用户消息的请求。 请求结束后调用
     * removeSendingMessage(agentId) 移除。
     */
    suspend fun appendSendingLoadingOnly(agentId: String) {
        chatMessageDao.upsert(
            createTempSendingLoadingEntity(agentId = agentId)
        )
    }

    suspend fun appendUserMessage(agentId: String, messageId: String, content: String, timestamp: String) {
        chatMessageDao.upsert(
            MessageEntity(
                id = messageId,
                content = content,
                role = "user",
                metaData = MessageEntity.MetaData(agentId),
                timestamp = timestamp,
            )
        )
    }

    suspend fun appendMessages(messages: List<MessageEntity>) {
        chatMessageDao.upsert(messages)
    }

    suspend fun setMessageVote(
        agentId: String,
        messageId: String,
        userVote: MessageEntity.UserVote?
    ) {
        chatMessageDao.updateUserFeedback(agentId, messageId, userVote)
    }

    suspend fun getLatestMessageId(agentId: String): String? {
        return chatMessageDao.getLatestMessageId(agentId)
    }

    suspend fun getImageMessages(agentId: String): Flow<List<MessageEntity>> {
        return chatMessageDao.streamMessagesWithImages(agentId)
    }
}
