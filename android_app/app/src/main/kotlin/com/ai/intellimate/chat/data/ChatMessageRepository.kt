package com.ai.intellimate.chat.data

// CREATED_BY_AGENT

import ai.sxwl.android.data.chat.data.ChatRemoteDataSource
import ai.sxwl.android.data.chat.data.RoomDataSource
import ai.sxwl.android.data.chat.local.db.ChatMessageEntity
import ai.sxwl.android.data.chat.local.db.IntyChatDatabase
import androidx.paging.ExperimentalPagingApi
import androidx.paging.Pager
import androidx.paging.PagingConfig
import androidx.paging.PagingData
import kotlinx.coroutines.flow.Flow

/**
 * 聊天消息的 Paging Repository
 * 使用 RemoteMediator 实现数据库查询和网络同步
 *
 * 使用场景：
 * - 在聊天页面中使用 Paging 加载聊天记录
 * - 自动从网络同步数据到数据库
 * - 支持下拉刷新和上拉加载更多
 *
 * 可配置项：
 * - agentId: 智能体 ID
 * - pageSize: 每页加载的消息数量，默认 20
 * - prefetchDistance: 预取距离，默认 3
 * - enablePlaceholders: 是否启用占位符，默认 false
 */
class ChatMessageRepository(
    private val database: IntyChatDatabase = IntyChatDatabase.getInstance(),
    private val remoteDataSource: ChatRemoteDataSource = ChatRemoteDataSource()
) {

    /**
     * 获取聊天消息的 PagingData Flow
     * 返回的 Flow 会从数据库读取数据，并在需要时通过 RemoteMediator 从网络同步
     */
    @OptIn(ExperimentalPagingApi::class)
    fun getMessagesFlow(agentId: String): Flow<PagingData<ChatMessageEntity>> {
        return Pager(
            config = PagingConfig(pageSize = 20),
            remoteMediator = ChatMessageRemoteMediator(
                agentId = agentId,
                database = database,
                remoteDataSource = remoteDataSource
            ),
            pagingSourceFactory = {
                database.chatMessageDao().pagingSource(agentId)
            },
        ).flow
    }
}
