package com.ai.intellimate.chat.data

// CREATED_BY_AGENT

import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.api.model.SendMsgResponse
import ai.sxwl.android.data.chat.data.ChatRemoteDataSource
import ai.sxwl.android.data.chat.data.RoomDataSource
import ai.sxwl.android.data.chat.local.db.IntyChatDatabase
import ai.sxwl.android.data.chat.local.db.MessageEntity
import ai.sxwl.android.data.chat.local.db.toEntity
import ai.sxwl.android.data.chat.local.db.toUpdate
import ai.sxwl.android.data.http.BusinessErrorCodes
import ai.sxwl.android.utils.LogUtils
import androidx.paging.ExperimentalPagingApi
import androidx.paging.Pager
import androidx.paging.PagingConfig
import androidx.paging.PagingData
import com.ai.intellimate.boost.BoostManager
import com.ai.intellimate.boost.PointSource
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.withContext

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
    fun getMessagesFlow(agentId: String): Flow<PagingData<MessageEntity>> {
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
    }

    suspend fun sendMessage(agentId: String, content: String): HttpResult<SendMsgResponse> {
        LogUtils.d("RoomImpl.sendMessage called for $agentId: $content")

        val trimmed = content.trimEnd()
        val timestamp = java.time.Instant.ofEpochMilli(System.currentTimeMillis()).toString()

        localDataSource.appendSendingMessages(agentId, trimmed)

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

        roomDataSource.removeSendingMessage(agentId)

        if (
            result is HttpResult.Success &&
                result.data.code != BusinessErrorCodes.SUBSCRIPTION_REQUIRED_CODE
        ) {

            result.data.data?.let { data ->
                val buildMessages = buildList {
                    add(
                        MessageEntity(
                            id = data.user_message_id.toString(),
                            content = content,
                            role = "user",
                            metaData = MessageEntity.MetaData(agentId),
                            timestamp = timestamp,
                        )
                    )
                    addAll(data.choices.map { it.message.toEntity(agentId) })
                }

                localDataSource.appendMessages(buildMessages)

                LogUtils.d(
                    "RoomImpl.sendMessage saving ${buildMessages.size} assistant messages for agentId=$agentId"
                )
            }
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

        localDataSource.removeMessage(
            agentId,
            lastAssistantMessage.id,
            lastAssistantMessage.indexId,
        )
        localDataSource.appendSendingLoadingOnly(agentId)

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
                val assistantMsgs = choices.map { it.message.toEntity(agentId) }
                localDataSource.appendMessages(assistantMsgs)
            }
        } else {
            localDataSource.upsert(lastAssistantMessage)
        }
    }

    suspend fun getMessageCounts(agentId: String) = localDataSource.getMessageCounts(agentId)

    suspend fun countUserMessages(agentId: String) = localDataSource.countUserMessages(agentId)

    suspend fun getMessage(agentId: String, msgId: String) =
        localDataSource.getMessage(agentId, msgId)

    suspend fun loadRecentMessages(agentId: String, count: Int) {
        val result =
            runCatching {
                    LogUtils.d("加载最近消息:Count=$count")
                    remoteDataSource.getMessages(agentId, count, 0)
                }
                .getOrElse { HttpResult.Failure(it.message ?: "unknown error", -1) }

        if (result is HttpResult.Success) {
            val entities = result.data.messages?.map { it.toUpdate(agentId) }.orEmpty()

            if (entities.isNotEmpty()) {
                localDataSource.upsert(entities)
            }
        }
    }

    suspend fun setMessageVote(
        agentId: String,
        messageId: String,
        userVote: MessageEntity.UserVote,
    ) {
        withContext(Dispatchers.IO) {
            try {
                localDataSource.setMessageVote(agentId, messageId, userVote)

                val result = remoteDataSource.voteMessage(agentId, messageId, userVote.name)

                if (result is HttpResult.Failure) {
                    throw Exception(result.message)
                }
            } catch (error: Exception) {
                // 不再回滚本地状态：远程投票失败时保留用户已选的 like/dislike，避免 UI 闪一下又恢复
                // 只提示错误日志，不抛出异常
                LogUtils.e("Vote message remote failure (local vote kept): ${error.message}")
                throw error
            }
        }
    }

    suspend fun resetMessageVote(agentId: String, msgId: String) {
        withContext(Dispatchers.IO) { localDataSource.setMessageVote(agentId, msgId, null) }
    }

    suspend fun addImageGenerationErrorTips(agentId: String, messageId: String) {
        // 在消息列表中添加 tips 消息（使用字符串常量，后续在 UI 层处理）
        val tipMessage =
            MessageEntity(
                id = messageId,
                content = "image_generation_error_tip", // 特殊标记，UI 层会转换为实际文案
                role = "system",
                indexId = "image_generation_error_${System.nanoTime()}",
                metaData = MessageEntity.MetaData(agentId = agentId),
            )

        withContext(Dispatchers.IO) { localDataSource.appendMessages(listOf(tipMessage)) }
    }

    suspend fun appendBoostSystemMessage(agentId: String, content: String) {

        withContext(Dispatchers.IO) {
            val lastMessageId = localDataSource.getLatestMessageId(agentId)

            val message =
                MessageEntity(
                    id = lastMessageId ?: "${Long.MAX_VALUE}",
                    content = content,
                    role = "system",
                    indexId = "boost_${System.nanoTime()}",
                    metaData = MessageEntity.MetaData(agentId = agentId),
                )

            localDataSource.appendMessages(listOf(message))
        }
    }

    suspend fun removeMessage(agentId: String, msgId: String, indexId: String) {
        localDataSource.removeMessage(agentId, msgId, indexId)
    }

    suspend fun getImageMessages(agentId: String) = localDataSource.getImageMessages(agentId)

    fun messageCountFlow(agentId: String) = localDataSource.messageCountFlow(agentId)

    fun userMessageCountFlow(agentId: String) = localDataSource.userMessageCountFlow(agentId)

    suspend fun purchaseForMoment(agentId: String, messageId: String, price: Int) {
        if (BoostManager.boostState.value.availablePoints >= price) {
            when (val result = remoteDataSource.unlockSurpriseSnap(messageId.toLong())) {
                is HttpResult.Success -> {
                    if (BoostManager.consume(price, PointSource.ForMoment)) {
                        localDataSource.setForMomentPurchased(agentId, messageId)
                    } else {
                        throw Exception("Not enough credits.")
                    }
                }
                is HttpResult.Failure -> {
                    throw Exception(result.message)
                }
            }
        } else {
            throw Exception("Not enough credits.")
        }
    }
}
