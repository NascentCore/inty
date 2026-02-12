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
    private companion object {
        private const val STREAM_SYNC_FETCH_LIMIT = 20
        private const val TEMP_ASSISTANT_MESSAGE_ID = "${Long.MAX_VALUE}"
    }


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

    suspend fun sendMessage(
        agentId: String,
        content: String,
        stream: Boolean = false,
    ): HttpResult<SendMsgResponse> {
        LogUtils.d("RoomImpl.sendMessage called for $agentId: $content")

        val trimmed = content.trimEnd()
        val timestamp = java.time.Instant.ofEpochMilli(System.currentTimeMillis()).toString()
        val streamAssistantBuffer = StringBuilder()

        localDataSource.appendSendingMessages(agentId, trimmed)

        val result =
            try {
                remoteDataSource.sendMessage(
                    agentId,
                    listOf(MsgInfo(content = trimmed, role = "user")),
                    stream = stream,
                    onStreamDelta =
                        if (stream) {
                            { delta ->
                                if (delta.isNotEmpty()) {
                                    streamAssistantBuffer.append(delta)
                                    updateStreamingAssistantDraft(
                                        agentId = agentId,
                                        content = streamAssistantBuffer.toString(),
                                        timestamp = timestamp,
                                    )
                                }
                            }
                        } else {
                            null
                        },
                )
            } catch (e: Exception) {
                LogUtils.e("RoomImpl.sendMessage exception: ${e.message}")
                HttpResult.Failure(e.message ?: "unknown error", -1)
            }

        if (
            stream &&
                result is HttpResult.Success &&
                result.data.code != BusinessErrorCodes.SUBSCRIPTION_REQUIRED_CODE
        ) {
            val finalAssistantContent =
                streamAssistantBuffer.toString().ifBlank {
                    result.data.data?.choices?.firstOrNull()?.message?.content.orEmpty()
                }
            persistStreamedSendMessages(
                agentId = agentId,
                userContent = trimmed,
                assistantContent = finalAssistantContent,
                timestamp = timestamp,
            )
        }

        roomDataSource.removeSendingMessage(agentId)

        if (
            !stream &&
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

    suspend fun recallLastAssistantMessage(agentId: String, stream: Boolean = false) {
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
        val timestamp = java.time.Instant.ofEpochMilli(System.currentTimeMillis()).toString()
        val streamAssistantBuffer = StringBuilder()

        val result =
            try {
                remoteDataSource.sendMessage(
                    agentId,
                    listOf(MsgInfo(content = "recall", role = "user")),
                    stream = stream,
                    onStreamDelta =
                        if (stream) {
                            { delta ->
                                if (delta.isNotEmpty()) {
                                    streamAssistantBuffer.append(delta)
                                    updateStreamingAssistantDraft(
                                        agentId = agentId,
                                        content = streamAssistantBuffer.toString(),
                                        timestamp = timestamp,
                                    )
                                }
                            }
                        } else {
                            null
                        },
                )
            } catch (e: Exception) {
                LogUtils.e("RoomImpl.recallLastAssistantMessage exception: ${e.message}")
                HttpResult.Failure(e.message ?: "unknown error", -1)
            }

        if (stream && result is HttpResult.Success && result.data.code == 200) {
            val finalAssistantContent =
                streamAssistantBuffer.toString().ifBlank {
                    result.data.data?.choices?.firstOrNull()?.message?.content.orEmpty()
                }
            persistStreamedRecallAssistantMessage(
                agentId = agentId,
                assistantContent = finalAssistantContent,
                timestamp = timestamp,
            )
        }

        roomDataSource.removeSendingMessage(agentId)

        if (!stream && result is HttpResult.Success) {
            val choices = result.data.data?.choices ?: emptyList()
            if (choices.isNotEmpty()) {
                val assistantMsgs = choices.map { it.message.toEntity(agentId) }
                localDataSource.appendMessages(assistantMsgs)
            }
        } else if (result is HttpResult.Failure) {
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
            val preMessage = localDataSource.getMessage(agentId, messageId)

            try {
                localDataSource.setMessageVote(agentId, messageId, userVote)

                val result = remoteDataSource.voteMessage(agentId, messageId, userVote.name)

                if (result is HttpResult.Failure) {
                    throw Exception(result.message)
                }
            } catch (error: Exception) {
                localDataSource.setMessageVote(agentId, messageId, preMessage?.userVote)
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

    private suspend fun updateStreamingAssistantDraft(
        agentId: String,
        content: String,
        timestamp: String,
    ) {
        localDataSource.appendMessages(
            listOf(
                MessageEntity(
                    id = TEMP_ASSISTANT_MESSAGE_ID,
                    content = content,
                    role = "assistant",
                    metaData = MessageEntity.MetaData(agentId),
                    timestamp = timestamp,
                    isSending = true,
                )
            )
        )
    }

    private suspend fun persistStreamedSendMessages(
        agentId: String,
        userContent: String,
        assistantContent: String,
        timestamp: String,
    ) {
        if (assistantContent.isBlank()) return

        val synced =
            runCatching { remoteDataSource.getMessages(agentId, STREAM_SYNC_FETCH_LIMIT, 0) }
                .getOrNull()
        if (synced is HttpResult.Success) {
            val nowMs = System.currentTimeMillis()
            val messages = synced.data.messages.orEmpty()
            val userMessage = messages.firstOrNull { it.role == "user" && it.content == userContent }
            val assistantMessage =
                messages.firstOrNull {
                    it.role == "assistant" && it.content == assistantContent
                }
            if (userMessage != null || assistantMessage != null) {
                val userEntity =
                    userMessage?.toEntity(agentId)
                        ?: MessageEntity(
                            id = nowMs.toString(),
                            content = userContent,
                            role = "user",
                            metaData = MessageEntity.MetaData(agentId),
                            timestamp = timestamp,
                        )
                val assistantEntity =
                    assistantMessage?.toEntity(agentId)
                        ?: MessageEntity(
                            id = (nowMs + 1).toString(),
                            content = assistantContent,
                            role = "assistant",
                            metaData = MessageEntity.MetaData(agentId),
                            timestamp = timestamp,
                        )
                localDataSource.appendMessages(listOf(userEntity, assistantEntity))
                return
            }
        }

        val nowMs = System.currentTimeMillis()
        localDataSource.appendMessages(
            listOf(
                MessageEntity(
                    id = nowMs.toString(),
                    content = userContent,
                    role = "user",
                    metaData = MessageEntity.MetaData(agentId),
                    timestamp = timestamp,
                ),
                MessageEntity(
                    id = (nowMs + 1).toString(),
                    content = assistantContent,
                    role = "assistant",
                    metaData = MessageEntity.MetaData(agentId),
                    timestamp = timestamp,
                ),
            )
        )
    }

    private suspend fun persistStreamedRecallAssistantMessage(
        agentId: String,
        assistantContent: String,
        timestamp: String,
    ) {
        if (assistantContent.isBlank()) return

        val synced =
            runCatching { remoteDataSource.getMessages(agentId, STREAM_SYNC_FETCH_LIMIT, 0) }
                .getOrNull()
        if (synced is HttpResult.Success) {
            val assistantMessage =
                synced.data.messages
                    ?.orEmpty()
                    ?.firstOrNull {
                        it.role == "assistant" && it.content == assistantContent
                    }
            if (assistantMessage != null) {
                localDataSource.appendMessages(listOf(assistantMessage.toEntity(agentId)))
                return
            }
        }

        localDataSource.appendMessages(
            listOf(
                MessageEntity(
                    id = System.currentTimeMillis().toString(),
                    content = assistantContent,
                    role = "assistant",
                    metaData = MessageEntity.MetaData(agentId),
                    timestamp = timestamp,
                )
            )
        )
    }
}
