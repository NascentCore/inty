package com.inty.imate.chat.data

import androidx.paging.ExperimentalPagingApi
import androidx.paging.Pager
import androidx.paging.PagingConfig
import androidx.paging.PagingData
import com.inty.imate.chat.data.datasource.ChatHistoryRemoteDataSource
import com.inty.imate.chat.data.datasource.ChatLocalDataSource
import com.inty.imate.chat.local.db.ImateChatDatabase
import com.inty.imate.chat.local.db.MessageEntity
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.Flow

@OptIn(ExperimentalPagingApi::class)
@Singleton
class ChatMessageRepository
@Inject
constructor(
    private val chatMainRepository: ChatMainRepository,
    private val chatLocalDataSource: ChatLocalDataSource,
    private val chatHistoryRemoteDataSource: ChatHistoryRemoteDataSource,
) {

    suspend fun getAllMessages(agentId: String): List<MessageEntity> =
        chatLocalDataSource.getAllMessages(agentId)

    suspend fun getLatestMessage(agentId: String): MessageEntity? =
        chatLocalDataSource.getLatestMessage(agentId)

    suspend fun getMessage(agentId: String, messageId: String): MessageEntity? =
        chatLocalDataSource.getMessage(agentId, messageId)

    fun getMessagesPagingFlow(agentId: String): Flow<PagingData<MessageEntity>> =
        Pager(
                config =
                    PagingConfig(
                        pageSize = 20,
                        prefetchDistance = 30,
                        enablePlaceholders = false,
                        initialLoadSize = 20,
                    ),
                remoteMediator =
                    ChatMessageRemoteMediator(
                        agentId = agentId,
                        database = ImateChatDatabase.getInstance(),
                        remoteDataSource = chatHistoryRemoteDataSource,
                    ),
                pagingSourceFactory = { chatLocalDataSource.messagesPagingSource(agentId) },
            )
            .flow

    suspend fun sendTextViaWebSocket(agentId: String, content: String) {
        val trimmed = content.trimEnd()
        if (trimmed.isEmpty()) return

        chatLocalDataSource.appendSendingMessages(agentId, trimmed)
        val request = ChatTextSendRequestFactory.buildTextSendMsgReq(agentId, trimmed)
        try {
            chatMainRepository.sendMessageViaWebSocketFireAndForget(agentId, request)
        } catch (e: Exception) {
            chatLocalDataSource.markSendingFailedAndRemoveLoading(agentId)
            throw e
        }
    }
}
