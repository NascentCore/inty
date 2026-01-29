package com.ai.intellimate.chat.data

// CREATED_BY_AGENT

import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.api.model.SendMsgResponse
import ai.sxwl.android.data.chat.data.ChatRemoteDataSource
import ai.sxwl.android.data.chat.data.RoomDataSource
import ai.sxwl.android.data.chat.local.db.ChatMessageEntity
import ai.sxwl.android.data.chat.local.db.IntyChatDatabase
import ai.sxwl.android.data.http.BusinessErrorCodes
import ai.sxwl.android.utils.LogUtils
import androidx.paging.ExperimentalPagingApi
import androidx.paging.Pager
import androidx.paging.PagingConfig
import androidx.paging.PagingData
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.flow.Flow

/**
 * 聊天消息的 Paging Repository 使用 RemoteMediator 实现数据库查询和网络同步
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
    private val remoteDataSource: ChatRemoteDataSource = ChatRemoteDataSource(),
    private val localDataSource: ChatLocalDataSource = ChatLocalDataSource(database),
    private val roomDataSource: RoomDataSource = RoomDataSource(database),
) {

    /** 获取聊天消息的 PagingData Flow 返回的 Flow 会从数据库读取数据，并在需要时通过 RemoteMediator 从网络同步 */
    @OptIn(ExperimentalPagingApi::class)
    fun getMessagesFlow(agentId: String): Flow<PagingData<ChatMessageEntity>> {
        return Pager(
                config = PagingConfig(pageSize = 20, enablePlaceholders = false),
                remoteMediator =
                    ChatMessageRemoteMediator(
                        agentId = agentId,
                        database = database,
                        remoteDataSource = remoteDataSource,
                    ),
                pagingSourceFactory = { database.chatMessageDao().pagingSource(agentId) },
            )
            .flow
    }

    suspend fun clearMessages(agentId: String) {
        localDataSource.chatMessageDao.deleteByAgent(agentId)
        localDataSource.updateSyncState(agentId) { it.copy(offset = 0) }
    }

    suspend fun sendMessage(agentId: String, content: String): HttpResult<SendMsgResponse> {
        LogUtils.d("RoomImpl.sendMessage called for $agentId: $content")

        val trimmed = content.trimEnd()
        val timestamp = java.time.Instant.ofEpochMilli(System.currentTimeMillis()).toString()

        roomDataSource.appendSendingMessages(agentId, trimmed)

        val result =
            try {
                remoteDataSource.sendMessage(
                    agentId,
                    listOf(MsgInfo(content = trimmed, role = "user")),
                )
            } catch (e: Exception) {
                LogUtils.e("RoomImpl.sendMessage exception: ${e.message}")
                HttpResult.Failure(e.message ?: "unknown error", -1)
            }

        if (
            result is HttpResult.Success &&
                result.data.code != BusinessErrorCodes.SUBSCRIPTION_REQUIRED_CODE
        ) {
            roomDataSource.removeSendingMessage(agentId)

            val userMessageId = result.data.data?.user_message_id ?: 0L

            roomDataSource.appendMessages(
                agentId,
                listOf(
                    MsgInfo(
                        id = userMessageId.toString(),
                        content = trimmed,
                        role = "user",
                        timestamp = timestamp,
                    )
                ),
            )
            val choices = result.data.data?.choices ?: emptyList()
            if (choices.isNotEmpty()) {
                val assistantMsgs = choices.map { it.message }
                LogUtils.d(
                    "RoomImpl.sendMessage saving ${assistantMsgs.size} assistant messages for agentId=$agentId"
                )
                roomDataSource.appendMessages(agentId, assistantMsgs)
                localDataSource.updateSyncState(agentId) { it.copy(offset = it.offset + 2) }
            } else {
                localDataSource.updateSyncState(agentId) { it.copy(offset = it.offset + 1) }
            }
        } else {
            roomDataSource.removeSendingMessage(agentId)
        }

        return result
    }

    suspend fun recallLastAssistantMessage(agentId: String) {
        LogUtils.d("RoomImpl.recallLastAssistantMessage called for $agentId")
        val lastAssistantMessage = localDataSource.getLatesAgentMessage(agentId)

        if (lastAssistantMessage == null) {
            LogUtils.w("RoomImpl.recallLastAssistantMessage: No assistant message to recall")
            return
        }

        localDataSource.removeMessage(agentId, lastAssistantMessage.localId)
        roomDataSource.appendSendingLoadingOnly(agentId)

        val result =
            try {
                remoteDataSource.sendMessage(
                    agentId,
                    listOf(MsgInfo(content = "recall", role = "user")),
                )
            } catch (e: Exception) {
                LogUtils.e("RoomImpl.recallLastAssistantMessage exception: ${e.message}")
                HttpResult.Failure(e.message ?: "unknown error", -1)
            }

        roomDataSource.removeSendingMessage(agentId)

        if (result is HttpResult.Success) {
            val choices = result.data.data?.choices ?: emptyList()
            if (choices.isNotEmpty()) {
                val assistantMsgs = choices.map { it.message }
                roomDataSource.appendMessages(agentId, assistantMsgs)
            }
        } else {
            localDataSource.upsert(lastAssistantMessage)
        }
    }

    suspend fun getMessageCounts(agentId: String) = localDataSource.getMessageCounts(agentId)

    suspend fun countUserMessages(agentId: String) = localDataSource.countUserMessages(agentId)

    suspend fun getMessage(agentId: String, msgId: String) =
        localDataSource.getMessage(agentId, msgId)
}
