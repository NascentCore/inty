package ai.sxwl.android.data.chat.repository

import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.api.model.SendMsgResponse
import ai.sxwl.android.data.chat.data.ChatLocalDataSource
import ai.sxwl.android.data.chat.data.ChatRemoteDataSource
import ai.sxwl.android.data.chat.domain.ChatRepository
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.utils.LogUtils
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.flow.StateFlow

/** 聊天Repository实现 作为Domain层和Data层之间的桥梁 遵循Clean Architecture的Repository模式 */
class ChatRepositoryImpl(
    private val localDataSource: ChatLocalDataSource,
    private val remoteDataSource: ChatRemoteDataSource
) : ChatRepository {

    companion object {
        private const val DEFAULT_PAGE_SIZE = 20
        private const val LOADING_PLACEHOLDER_CONTENT = "loading_animation"
        private const val ROLE_ASSISTANT = "assistant"
    }

    override fun getMessagesFlow(agentId: String): StateFlow<List<MsgInfo>> {
        return localDataSource.getMessagesFlow(agentId)
    }

    override fun getLoadingMoreFlow(agentId: String): StateFlow<Boolean> {
        return localDataSource.getLoadingMoreFlow(agentId)
    }

    override fun getHasMoreFlow(agentId: String): StateFlow<Boolean> {
        return localDataSource.getHasMoreFlow(agentId)
    }

    override suspend fun ensureInitialHistory(agentId: String, pageSize: Int) {
        LogUtils.d("ChatRepositoryImpl.ensureInitialHistory called for $agentId")

        if (localDataSource.isInitialLoaded(agentId)) return

        // 先检查是否有本地缓存数据
        val localMessages = localDataSource.getMessagesFlow(agentId).value
        if (localMessages.isNotEmpty()) {
            LogUtils.i(
                "ChatRepositoryImpl.ensureInitialHistory found ${localMessages.size} local messages for $agentId"
            )
            localDataSource.setInitialLoaded(agentId, true)
            // 后台同步最新数据
            try {
                val result = remoteDataSource.getMessages(agentId, pageSize, 0)
                when (result) {
                    is HttpResult.Success -> {
                        val serverMessages = result.data.messages ?: emptyList()
                        if (serverMessages.isNotEmpty()) {
                            localDataSource.updateMessages(agentId, serverMessages)
                            localDataSource.setHasMore(agentId, result.data.hasMore)
                            localDataSource.setOffset(
                                agentId,
                                if (serverMessages.isNotEmpty()) pageSize else 0
                            )
                            LogUtils.i(
                                "ChatRepositoryImpl.ensureInitialHistory synced ${serverMessages.size} server messages for $agentId"
                            )
                        }
                    }
                    is HttpResult.Failure -> {
                        LogUtils.e(
                            "ChatRepositoryImpl.ensureInitialHistory sync failure for $agentId: ${result.message}"
                        )
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("ChatRepositoryImpl.ensureInitialHistory sync exception: ${e.message}")
            }
            return
        }

        try {
            val result = remoteDataSource.getMessages(agentId, pageSize, 0)
            when (result) {
                is HttpResult.Success -> {
                    val messages = result.data.messages ?: emptyList()
                    LogUtils.i(
                        "ChatRepositoryImpl.ensureInitialHistory loaded ${messages.size} messages for $agentId"
                    )

                    localDataSource.updateMessages(agentId, messages)
                    localDataSource.setHasMore(agentId, result.data.hasMore)
                    localDataSource.setOffset(agentId, if (messages.isNotEmpty()) pageSize else 0)
                    localDataSource.setInitialLoaded(agentId, true)
                }
                is HttpResult.Failure -> {
                    LogUtils.e(
                        "ChatRepositoryImpl.ensureInitialHistory failure for $agentId: ${result.message}"
                    )
                    localDataSource.setInitialLoaded(agentId, true)
                }
            }
        } catch (e: Exception) {
            LogUtils.e("ChatRepositoryImpl.ensureInitialHistory exception: ${e.message}")
            localDataSource.setInitialLoaded(agentId, true)
        }
    }

    override suspend fun loadMoreMessages(agentId: String, pageSize: Int) {
        LogUtils.d("ChatRepositoryImpl.loadMoreMessages called for $agentId")

        if (localDataSource.getLoadingMoreFlow(agentId).value) return
        if (!localDataSource.getHasMoreFlow(agentId).value) return

        localDataSource.setLoadingMore(agentId, true)

        try {
            val offset = localDataSource.getOffset(agentId)
            val result = remoteDataSource.getMessages(agentId, pageSize, offset)

            when (result) {
                is HttpResult.Success -> {
                    val moreMessages = result.data.messages ?: emptyList()
                    if (moreMessages.isNotEmpty()) {
                        localDataSource.appendMessages(agentId, moreMessages)
                        localDataSource.incrementOffset(agentId, pageSize)
                    }
                    localDataSource.setHasMore(agentId, result.data.hasMore)

                    LogUtils.i(
                        "ChatRepositoryImpl.loadMoreMessages loaded ${moreMessages.size} more messages for $agentId"
                    )
                }
                is HttpResult.Failure -> {
                    LogUtils.e(
                        "ChatRepositoryImpl.loadMoreMessages failure for $agentId: ${result.message}"
                    )
                }
            }
        } catch (e: Exception) {
            LogUtils.e("ChatRepositoryImpl.loadMoreMessages exception: ${e.message}")
        } finally {
            localDataSource.setLoadingMore(agentId, false)
        }
    }

    override suspend fun sendMessage(
        agentId: String,
        content: String
    ): HttpResult<SendMsgResponse> {
        LogUtils.d("ChatRepositoryImpl.sendMessage called for $agentId: $content")

        // 1) 先插入用户消息与loading占位
        val userMsg = MsgInfo(content = content.trimEnd(), role = "user")
        val loadingMsg = MsgInfo(content = LOADING_PLACEHOLDER_CONTENT, role = ROLE_ASSISTANT)

        localDataSource.prependMessages(agentId, listOf(loadingMsg, userMsg))

        val result =
            try {
                remoteDataSource.sendMessage(agentId, listOf(userMsg))
            } catch (e: Exception) {
                LogUtils.e("ChatRepositoryImpl.sendMessage exception: ${e.message}")
                HttpResult.Failure(e.message ?: "unknown error", -1)
            }

        // 2) 移除loading占位
        val currentMessages = localDataSource.getMessagesFlow(agentId).value
        val filteredMessages =
            currentMessages.filterNot {
                it.content == LOADING_PLACEHOLDER_CONTENT && it.role == ROLE_ASSISTANT
            }
        localDataSource.updateMessages(agentId, filteredMessages)

        // 3) 追加AI回复
        if (result is HttpResult.Success) {
            val choices = result.data.data?.choices ?: emptyList()
            if (choices.isNotEmpty()) {
                val assistantMsgs = choices.map { it.message }
                localDataSource.prependMessages(agentId, assistantMsgs)

                // 会话已读更新
                choices.lastOrNull()?.message?.content?.let { lastContent ->
                    IntySetting.setConversationReaded(agentId, lastContent)
                }
            }
        }

        return result
    }

    override suspend fun syncLatestMessages(agentId: String, pageSize: Int) {
        LogUtils.d("ChatRepositoryImpl.syncLatestMessages called for $agentId")

        if (
            !localDataSource.isInitialLoaded(agentId) ||
                localDataSource.getMessagesFlow(agentId).value.isEmpty()
        ) {
            // 如果没有初始化或没有本地数据，使用正常的初始化流程
            LogUtils.i(
                "ChatRepositoryImpl.syncLatestMessages calling ensureInitialHistory for $agentId"
            )
            ensureInitialHistory(agentId, pageSize)
            return
        }

        try {
            val result = remoteDataSource.getMessages(agentId, pageSize, 0)
            when (result) {
                is HttpResult.Success -> {
                    val serverMessages = result.data.messages ?: emptyList()
                    val localMessages = localDataSource.getMessagesFlow(agentId).value

                    // 检查是否有新消息
                    val hasNewMessages =
                        serverMessages.any { serverMsg ->
                            localMessages.none { localMsg ->
                                localMsg.id == serverMsg.id ||
                                    (localMsg.content == serverMsg.content &&
                                        localMsg.role == serverMsg.role)
                            }
                        }

                    if (hasNewMessages) {
                        // 有新消息，更新本地数据
                        localDataSource.updateMessages(agentId, serverMessages)
                        localDataSource.setHasMore(agentId, result.data.hasMore)
                        localDataSource.setOffset(
                            agentId,
                            if (serverMessages.isNotEmpty()) pageSize else 0
                        )

                        LogUtils.i(
                            "ChatRepositoryImpl.syncLatestMessages found new messages for $agentId, updated ${serverMessages.size} messages"
                        )
                    } else {
                        LogUtils.i(
                            "ChatRepositoryImpl.syncLatestMessages no new messages for $agentId"
                        )
                    }
                }
                is HttpResult.Failure -> {
                    LogUtils.e(
                        "ChatRepositoryImpl.syncLatestMessages failure for $agentId: ${result.message}"
                    )
                }
            }
        } catch (e: Exception) {
            LogUtils.e("ChatRepositoryImpl.syncLatestMessages exception: ${e.message}")
        }
    }

    override fun updateMessageAudioUrl(agentId: String, messageId: String, audioUrl: String) {
        LogUtils.d(
            "ChatRepositoryImpl.updateMessageAudioUrl called for $agentId, messageId: $messageId"
        )
        localDataSource.updateMessageAudioUrl(agentId, messageId, audioUrl)
    }

    override fun updateMessageFeedback(
        agentId: String,
        messageId: String,
        feedback: MsgInfo.UserFeedback?
    ) {
        LogUtils.d(
            "ChatRepositoryImpl.updateMessageFeedback called for $agentId, messageId: $messageId, feedback: $feedback"
        )
        localDataSource.updateMessageFeedback(agentId, messageId, feedback)
        // TODO: 后续对接接口上报反馈
    }

    override fun updateMessageGeneratedImage(
        agentId: String,
        messageId: String,
        generatedImage: MsgInfo.MsgMetaData.GeneratedImage?,
    ) {
        LogUtils.d(
            "ChatRepositoryImpl.updateMessageGeneratedImage called for $agentId, messageId: $messageId, generatedImage: ${if (generatedImage != null) "set" else "null (remove)"}"
        )
        localDataSource.updateMessageGeneratedImage(agentId, messageId, generatedImage)
    }

    override suspend fun removeMessage(agentId: String, messageId: String) {
        LogUtils.d("ChatRepositoryImpl.removeMessage called for $agentId, messageId: $messageId")
        localDataSource.removeMessage(agentId, messageId)
    }

    override suspend fun addMessage(agentId: String, message: MsgInfo) {
        LogUtils.d("ChatRepositoryImpl.addMessage called for $agentId")
        localDataSource.addMessage(agentId, message)
    }

    override suspend fun recallLastAssistantMessage(agentId: String) {
        LogUtils.d("ChatRepositoryImpl.recallLastAssistantMessage called for $agentId")
        val messages = localDataSource.getMessagesFlow(agentId).value

        // 找到最后一条AI消息（排除loading）
        val lastAssistantMessage =
            messages.lastOrNull { it.role == ROLE_ASSISTANT && it.content != LOADING_PLACEHOLDER_CONTENT }

        if (lastAssistantMessage == null) {
            LogUtils.w("ChatRepositoryImpl.recallLastAssistantMessage: No assistant message to recall")
            return
        }

        // 删除最后一条AI消息，变成loading状态
        localDataSource.removeMessage(agentId, lastAssistantMessage.localMsgId)

        // 添加 loading 消息占位
        val loadingMsg = MsgInfo(content = LOADING_PLACEHOLDER_CONTENT, role = ROLE_ASSISTANT)
        localDataSource.prependMessages(agentId, listOf(loadingMsg))

        // 发送 recall 消息给服务器（类似 keep talking 的实现）
        // 服务器应该理解 "recall" 标记并重新生成最后一条AI消息
        val recallMsg = MsgInfo(content = "recall", role = "user")
        val result =
            try {
                remoteDataSource.sendMessage(agentId, listOf(recallMsg))
            } catch (e: Exception) {
                LogUtils.e("ChatRepositoryImpl.recallLastAssistantMessage exception: ${e.message}")
                HttpResult.Failure(e.message ?: "unknown error", -1)
            }

        // 移除loading占位
        val currentMessages = localDataSource.getMessagesFlow(agentId).value
        val filteredMessages =
            currentMessages.filterNot {
                it.content == LOADING_PLACEHOLDER_CONTENT && it.role == ROLE_ASSISTANT
            }
        localDataSource.updateMessages(agentId, filteredMessages)

        // 追加AI回复
        if (result is HttpResult.Success) {
            val choices = result.data.data?.choices ?: emptyList()
            if (choices.isNotEmpty()) {
                val assistantMsgs = choices.map { it.message }
                localDataSource.prependMessages(agentId, assistantMsgs)

                // 会话已读更新
                choices.lastOrNull()?.message?.content?.let { lastContent ->
                    IntySetting.setConversationReaded(agentId, lastContent)
                }
            }
        }
    }

    override suspend fun generateImageForMessage(
        agentId: String,
        messageId: String,
    ): com.architecture.httplib.core.HttpResult<ai.sxwl.android.data.http.services.ChatService.ChatImageGenerationResult> {
        LogUtils.d("ChatRepositoryImpl.generateImageForMessage called for $agentId, messageId: $messageId")

        // 找到触发消息生图的那条消息
        val messages = localDataSource.getMessagesFlow(agentId).value
        val sourceMessage = messages.find { it.id == messageId || it.localMsgId == messageId }

        if (sourceMessage == null) {
            LogUtils.e("ChatRepositoryImpl.generateImageForMessage: source message not found: $messageId")
            return HttpResult.Failure("Source message not found", -1)
        }

        // 在触发消息上设置 loading 状态：通过设置一个临时的 generatedImage（imageUrl 为 "loading"）
        // 这样图片会显示在触发消息的下方，而不是创建新消息
        val loadingImage = MsgInfo.MsgMetaData.GeneratedImage(
            imageUrl = "loading", // 特殊标记，表示正在生成图片
            width = 300,
            height = 300,
        )
        localDataSource.updateMessageGeneratedImage(agentId, messageId, loadingImage)

        val result = remoteDataSource.messageGenerateImage(agentId, messageId)

        when (result) {
            is HttpResult.Success -> {
                // 更新触发消息的 generatedImage 为实际图片
                val generatedImage = MsgInfo.MsgMetaData.GeneratedImage(
                    imageUrl = result.data.imageUrl,
                    width = result.data.width,
                    height = result.data.height,
                )
                localDataSource.updateMessageGeneratedImage(agentId, messageId, generatedImage)
                LogUtils.i("ChatRepositoryImpl.generateImageForMessage success: ${result.data.imageUrl}")
            }

            is HttpResult.Failure -> {
                LogUtils.e("ChatRepositoryImpl.generateImageForMessage failure: ${result.message}")
                // 生成失败时，移除 loading 状态
                localDataSource.updateMessageGeneratedImage(agentId, messageId, null)
            }
        }

        return result
    }

    override fun clearChatData(agentId: String) {
        LogUtils.d("ChatRepositoryImpl.clearChatData called for $agentId")
        localDataSource.clearChatData(agentId)
    }

    override fun clearAllChatData() {
        LogUtils.d("ChatRepositoryImpl.clearAllChatData called")
        localDataSource.clearAllChatData()
    }
}
