package com.ai.intellimate.chat.data

import ai.sxwl.android.data.api.model.ChatMode
import ai.sxwl.android.data.chat.local.db.IntyChatDatabase
import ai.sxwl.android.data.chat.local.db.MessageEntity
import ai.sxwl.android.data.chat.local.db.MessageUpdate
import ai.sxwl.android.data.chat.local.db.createTempSendingLoadingEntity
import ai.sxwl.android.data.chat.local.db.createTempSendingUserEntity
import ai.sxwl.android.data.store.jsonDataStore
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.Utils
import android.content.Context
import androidx.room.withTransaction
import kotlinx.coroutines.flow.Flow

private val Context.chatModes by jsonDataStore("chatModes", emptyList<ChatMode>())

class ChatLocalDataSource(private val database: IntyChatDatabase = IntyChatDatabase.getInstance()) {
    val chatMessageDao = database.chatMessageDao()

    suspend fun getMessageCounts(agentId: String): Int {
        return chatMessageDao.getMessagesCount(agentId)
    }

    suspend fun countUserMessages(agentId: String): Int {
        return chatMessageDao.countUserMessages(agentId)
    }

    suspend fun clearMessages(agentId: String) {
        chatMessageDao.deleteByAgent(agentId)
    }

    fun messageCountFlow(agentId: String) = chatMessageDao.messageCountFlow(agentId)

    fun userMessageCountFlow(agentId: String) = chatMessageDao.userMessageCountFlow(agentId)

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

    suspend fun getLatestMessage(agentId: String): MessageEntity? {
        return chatMessageDao.getLatestMessage(agentId)
    }

    suspend fun appendSendingMessages(
        agentId: String,
        userContent: String,
        userImageUrl: String? = null,
    ) {
        chatMessageDao.deleteSendingLoadingOnly(agentId)
        val last = chatMessageDao.getLatestMessageExcludingSendingLoading(agentId)
        val userEntity =
            createTempSendingUserEntity(
                agentId = agentId,
                content = userContent,
                lastMessageId = last?.id,
                lastMessageIndexId = last?.indexId,
                userImageUrl = userImageUrl,
            )
        val loadingEntity = createTempSendingLoadingEntity(agentId = agentId)
        chatMessageDao.upsert(listOf(userEntity, loadingEntity))
    }

    /**
     * 仅插入“正在发送”的 loading 占位（status=SENDING），用于 recall 等不附带用户消息的请求。 请求结束后调用
     * removeSendingMessage(agentId) 或 markSendingFailedAndRemoveLoading(agentId) 处理。
     */
    suspend fun appendSendingLoadingOnly(agentId: String) {
        chatMessageDao.upsert(createTempSendingLoadingEntity(agentId = agentId))
    }

    /** 发送成功时：删除该会话下所有 SENDING 的临时消息（用户占位 + loading 占位）。 */
    suspend fun removeSendingMessage(agentId: String) {
        chatMessageDao.deleteSendingMsg(agentId)
    }

    /** 发送失败时：将发送中的用户消息标记为 SENDING_FAILED，仅删除 loading 占位。 */
    suspend fun markSendingFailedAndRemoveLoading(agentId: String) {
        database.withTransaction {
            chatMessageDao.markSendingUserAsFailed(agentId)
            chatMessageDao.deleteSendingLoadingOnly(agentId)
        }
    }

    suspend fun updateSendingUserImage(
        agentId: String,
        imageUrl: String,
        width: Int?,
        height: Int?,
    ) {
        val latest = chatMessageDao.getLatestSendingUserMessage(agentId) ?: return
        chatMessageDao.updateSendingUserImageByKey(
            agentId = agentId,
            messageId = latest.id,
            indexId = latest.indexId,
            imageUrl = imageUrl,
            width = width,
            height = height,
        )
    }

    suspend fun appendUserMessage(
        agentId: String,
        messageId: String,
        content: String,
        timestamp: String,
    ) {
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

    suspend fun upsert(updates: List<MessageUpdate>) {
        chatMessageDao.insertOrDrop(updates)
    }

    suspend fun setMessageVote(
        agentId: String,
        messageId: String,
        userVote: MessageEntity.UserVote?,
    ) {
        chatMessageDao.updateUserFeedback(agentId, messageId, userVote)
    }

    suspend fun getLatestMessageId(agentId: String): String? {
        return chatMessageDao.getLatestMessageId(agentId)
    }

    suspend fun getImageMessages(agentId: String): Flow<List<MessageEntity>> {
        return chatMessageDao.streamMessagesWithImages(agentId)
    }

    suspend fun setForMomentPurchased(agentId: String, messageId: String) {
        chatMessageDao.setForMomentPurchaseState(agentId, messageId, true)
    }

    suspend fun getYesterdaySendCount(): Int {
        return chatMessageDao.getYesterdayMessageCount().also {
            LogUtils.d("Chat:Yesterday send message count = $it")
        }
    }

    suspend fun withTransaction(block: suspend () -> Unit) {
        database.withTransaction(block)
    }

    suspend fun removeMessages(messages: List<MessageEntity>) {
        chatMessageDao.deleteMessage(messages)
    }

    suspend fun updateMessage(message: MessageEntity) {
        chatMessageDao.updateMessage(message)
    }

    fun getChatModes() = Utils.getApp().chatModes.data

    suspend fun setChatModes(chatModes: List<ChatMode>) {
        Utils.getApp().chatModes.updateData { chatModes }
    }
}
