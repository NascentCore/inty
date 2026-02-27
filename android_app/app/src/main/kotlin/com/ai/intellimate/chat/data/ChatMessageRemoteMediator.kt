package com.ai.intellimate.chat.data

// CREATED_BY_AGENT

import ai.sxwl.android.data.chat.data.ChatRemoteDataSource
import ai.sxwl.android.data.chat.local.db.ChatMessageDao
import ai.sxwl.android.data.chat.local.db.IntyChatDatabase
import ai.sxwl.android.data.chat.local.db.MessageEntity
import ai.sxwl.android.data.chat.local.db.toUpdate
import ai.sxwl.android.utils.LogUtils
import androidx.paging.ExperimentalPagingApi
import androidx.paging.LoadType
import androidx.paging.PagingState
import androidx.paging.RemoteMediator
import androidx.room.withTransaction
import com.architecture.httplib.core.HttpResult

/**
 * 聊天消息的 RemoteMediator 负责从网络同步数据到数据库，并管理分页状态
 *
 * 使用场景：
 * - 当 Paging 需要更多数据时，从网络获取并保存到数据库
 * - 处理刷新操作，重置分页状态
 * - 管理分页偏移量（offset）和是否有更多数据（hasMore）的状态
 *
 * 可配置项：
 * - agentId: 智能体 ID，用于区分不同智能体的聊天记录
 * - pageSize: 每页加载的消息数量，默认 20
 */
@OptIn(ExperimentalPagingApi::class)
class ChatMessageRemoteMediator(
    private val agentId: String,
    private val database: IntyChatDatabase,
    private val remoteDataSource: ChatRemoteDataSource,
) : RemoteMediator<Int, MessageEntity>() {

    private val messageDao: ChatMessageDao = database.chatMessageDao()

    override suspend fun load(
        loadType: LoadType,
        state: PagingState<Int, MessageEntity>,
    ): MediatorResult {
        return try {
            // 确定当前应该使用的 offset
            // API 使用 order=desc，offset=0 是最新消息，offset 增加时获取更早的消息
            val nextPageKey =
                when (loadType) {
                    LoadType.REFRESH -> {
                        // 刷新时重置 offset 为 0，获取最新消息
                        LogUtils.d(
                            "ChatMessageRemoteMediator",
                            "REFRESH: resetting offset to 0 for agentId=$agentId",
                        )
                        0
                    }
                    LoadType.PREPEND -> {
                        return MediatorResult.Success(endOfPaginationReached = true)
                    }
                    LoadType.APPEND -> {
                        val lastItem = state.lastItemOrNull()
                        if (lastItem == null) 0 else state.pages.sumOf { it.data.size }
                    }
                }
            LogUtils.d(
                "ChatMessageRemoteMediator",
                "offset=${nextPageKey} PageSize=${state.config.pageSize}",
            )
            // 从网络获取数据
            when (
                val result =
                    remoteDataSource.getMessages(agentId, state.config.pageSize, nextPageKey)
            ) {
                is HttpResult.Success -> {
                    val response = result.data
                    val messages = response.messages ?: emptyList()

                    LogUtils.d(
                        "ChatMessageRemoteMediator",
                        "Network request succeeded: agentId=$agentId, offset=$nextPageKey, messagesCount=${messages.size}, hasMore=${response.hasMore}",
                    )

                    // 在事务中保存数据到数据库
                    database.withTransaction {
                        // 保存消息到数据库
                        if (messages.isNotEmpty()) {
                            val entities = messages.map { msg -> msg.toUpdate(agentId) }

                            messageDao.insertOrDrop(entities)
                            LogUtils.d(
                                "ChatMessageRemoteMediator",
                                "Saved ${entities.size} messages to database for agentId=$agentId",
                            )
                        }
                    }

                    // 返回成功结果
                    MediatorResult.Success(
                        endOfPaginationReached =
                            !response.hasMore || messages.size < state.config.pageSize
                    )
                }
                is HttpResult.Failure -> {
                    LogUtils.e(
                        "ChatMessageRemoteMediator",
                        "Network request failed: agentId=$agentId, offset=${nextPageKey}, error=${result.message}, code=${result.code}",
                    )
                    MediatorResult.Error(
                        Exception("Network error: ${result.message} (code: ${result.code})")
                    )
                }
            }
        } catch (e: Exception) {
            LogUtils.e(
                "ChatMessageRemoteMediator",
                "Exception during load: agentId=$agentId, error=${e.message}",
                e,
            )
            MediatorResult.Error(e)
        }
    }

    override suspend fun initialize(): InitializeAction {
        return InitializeAction.SKIP_INITIAL_REFRESH
    }
}
