package com.ai.intellimate.chat.data

// CREATED_BY_AGENT

import ai.sxwl.android.data.chat.data.ChatRemoteDataSource
import ai.sxwl.android.data.chat.local.db.ChatMessageDao
import ai.sxwl.android.data.chat.local.db.ChatMessageEntity
import ai.sxwl.android.data.chat.local.db.ChatSyncStateDao
import ai.sxwl.android.data.chat.local.db.ChatSyncStateEntity
import ai.sxwl.android.data.chat.local.db.IntyChatDatabase
import ai.sxwl.android.data.chat.local.db.toEntity
import ai.sxwl.android.utils.LogUtils
import androidx.paging.ExperimentalPagingApi
import androidx.paging.LoadType
import androidx.paging.PagingState
import androidx.paging.RemoteMediator
import androidx.room.withTransaction
import com.architecture.httplib.core.HttpResult

/**
 * 聊天消息的 RemoteMediator
 * 负责从网络同步数据到数据库，并管理分页状态
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
    private val pageSize: Int = 20,
) : RemoteMediator<Int, ChatMessageEntity>() {

    private val messageDao: ChatMessageDao = database.chatMessageDao()
    private val syncStateDao: ChatSyncStateDao = database.chatSyncStateDao()

    override suspend fun load(
        loadType: LoadType,
        state: PagingState<Int, ChatMessageEntity>,
    ): MediatorResult {
        return try {
            // 确定当前应该使用的 offset
            // API 使用 order=desc，offset=0 是最新消息，offset 增加时获取更早的消息
            val nextPageKey = when (loadType) {
                LoadType.REFRESH -> {
                    // 刷新时重置 offset 为 0，获取最新消息
                    LogUtils.d("ChatMessageRemoteMediator", "REFRESH: resetting offset to 0 for agentId=$agentId")
                    0
                }
                LoadType.PREPEND -> {
                    return MediatorResult.Success(endOfPaginationReached = true)
                }
                LoadType.APPEND -> {
                    // 追加加载：在列表末尾加载更早的消息（历史消息）
                    // offset 增加以获取更早的消息
                    val syncState = syncStateDao.get(agentId)
                    val currentOffset = syncState?.offset ?: 0
                    LogUtils.d(
                        "ChatMessageRemoteMediator",
                        "APPEND: loading older messages from offset=$currentOffset for agentId=$agentId",
                    )
                    currentOffset
                }
            }

            // 从网络获取数据
            when (val result = remoteDataSource.getMessages(agentId, pageSize, nextPageKey)) {
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
                            val entities = messages.map { msg ->
                                msg.toEntity(agentId, existing = null)
                            }

                            messageDao.upsert(entities)
                            LogUtils.d(
                                "ChatMessageRemoteMediator",
                                "Saved ${entities.size} messages to database for agentId=$agentId",
                            )
                        }

                        // 更新同步状态
                        // 对于 REFRESH，offset 重置为已加载的消息数量
                        // 对于 APPEND，offset 更新为当前 offset + 已加载的消息数量
                        val newOffset = if (loadType == LoadType.REFRESH) {
                            messages.size
                        } else {
                            nextPageKey + messages.size
                        }
                        val updatedSyncState = ChatSyncStateEntity(
                            agentId = agentId,
                            offset = newOffset,
                            hasMore = response.hasMore,
                            isInitialLoaded = true,
                            lastSyncedAt = System.currentTimeMillis(),
                            updatedAt = System.currentTimeMillis()
                        )
                        syncStateDao.upsert(updatedSyncState)
                    }

                    // 返回成功结果
                    MediatorResult.Success(endOfPaginationReached = !response.hasMore)
                }
                is HttpResult.Failure -> {
                    LogUtils.e(
                        "ChatMessageRemoteMediator",
                        "Network request failed: agentId=$agentId, offset=${nextPageKey}, error=${result.message}, code=${result.code}",
                    )
                    MediatorResult.Error(
                        Exception("Network error: ${result.message} (code: ${result.code})"),
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
