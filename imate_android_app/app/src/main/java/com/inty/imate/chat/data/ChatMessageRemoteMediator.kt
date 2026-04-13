package com.inty.imate.chat.data

import androidx.paging.ExperimentalPagingApi
import androidx.paging.LoadType
import androidx.paging.PagingState
import androidx.paging.RemoteMediator
import androidx.room.withTransaction
import com.ai.core.utils.LogUtils
import com.inty.imate.chat.data.datasource.ChatHistoryRemoteDataSource
import com.inty.imate.chat.local.db.ChatMessageDao
import com.inty.imate.chat.local.db.ImateChatDatabase
import com.inty.imate.chat.local.db.MessageEntity
import kotlinx.coroutines.delay

@OptIn(ExperimentalPagingApi::class)
class ChatMessageRemoteMediator(
    private val agentId: String,
    private val database: ImateChatDatabase,
    private val remoteDataSource: ChatHistoryRemoteDataSource,
) : RemoteMediator<Int, MessageEntity>() {

    private val messageDao: ChatMessageDao = database.chatMessageDao()

    override suspend fun load(
        loadType: LoadType,
        state: PagingState<Int, MessageEntity>,
    ): MediatorResult {
        return try {
            val nextPageKey =
                when (loadType) {
                    LoadType.REFRESH -> 0
                    LoadType.PREPEND -> return MediatorResult.Success(endOfPaginationReached = true)
                    LoadType.APPEND -> {
                        val lastItem = state.lastItemOrNull()
                        if (lastItem == null) 0 else state.pages.sumOf { it.data.size }
                    }
                }
            LogUtils.d(
                "ChatMessageRemoteMediator",
                "agentId=$agentId offset=$nextPageKey pageSize=${state.config.pageSize}",
            )
            val response =
                remoteDataSource.getMessages(agentId, state.config.pageSize, nextPageKey)
            val messages = response.messages ?: emptyList()

            database.withTransaction {
                if (messages.isNotEmpty()) {
                    val entities = messages.map { msg -> msg.toMessageUpdate(agentId) }
                    messageDao.insertOrDrop(entities)
                }
            }

            MediatorResult.Success(
                endOfPaginationReached =
                    !response.hasMore || messages.size < state.config.pageSize
            )
        } catch (e: Exception) {
            LogUtils.d("ChatMessageRemoteMediator", "load failed: ${e.message}")
            MediatorResult.Error(e)
        }
    }

    override suspend fun initialize(): InitializeAction {
        return InitializeAction.SKIP_INITIAL_REFRESH
    }
}
