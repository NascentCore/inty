package com.ai.intellimate.chat.data

import ai.sxwl.android.data.chat.local.db.ChatMessageEntity
import ai.sxwl.android.data.chat.local.db.ChatSyncStateEntity
import ai.sxwl.android.data.chat.local.db.IntyChatDatabase

class ChatLocalDataSource(
    private val database: IntyChatDatabase = IntyChatDatabase.getInstance()
) {
    val chatMessageDao = database.chatMessageDao()
    val syncStateDao = database.chatSyncStateDao()

    suspend fun getMessageCounts(agentId: String): Int {
        return chatMessageDao.getMessagesCount(agentId)
    }

    suspend fun countUserMessages(agentId: String): Int{
        return chatMessageDao.countUserMessages(agentId)
    }

    suspend fun clearMessages(agentId: String) {
        chatMessageDao.deleteByAgent(agentId)
    }

    suspend fun getLatesAgentMessage(agentId: String): ChatMessageEntity? {
        return chatMessageDao.getLatestAgentMessage(agentId)
    }

    suspend fun removeMessage(agentId: String, messageId: String): ChatMessageEntity? {
        val entity = chatMessageDao.getMessage(agentId, messageId)
        if (entity != null) chatMessageDao.deleteMessage(agentId, messageId)
        return entity
    }

    suspend fun upsert(entity: ChatMessageEntity) {
        chatMessageDao.upsert(entity)
    }

    suspend fun getMessage(agentId: String, localMessageId: String): ChatMessageEntity? {
        return chatMessageDao.getMessage(agentId, localMessageId)
    }

    suspend fun updateSyncState(
        agentId: String,
        updater: (ChatSyncStateEntity) -> ChatSyncStateEntity
    ) {
        val current = syncStateDao.get(agentId) ?: ChatSyncStateEntity(agentId = agentId)
        syncStateDao.upsert(updater(current).copy(updatedAt = System.currentTimeMillis()))
    }
}