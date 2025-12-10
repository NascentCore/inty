package ai.sxwl.android.data.chat.repository

import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.api.model.SendMsgResponse
import ai.sxwl.android.data.api.model.VoteConstants
import ai.sxwl.android.data.api.model.VoteMessageRsp
import ai.sxwl.android.data.chat.data.ChatLocalDataSource
import ai.sxwl.android.data.chat.data.ChatRemoteDataSource
import ai.sxwl.android.data.chat.domain.ChatRepository
import ai.sxwl.android.utils.LogUtils
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.flow.StateFlow

/** 聊天Repository实现 作为Domain层和Data层之间的桥梁 遵循Clean Architecture的Repository模式 */
class ChatRepositoryImpl(
    private val localDataSource: ChatLocalDataSource,
    private val remoteDataSource: ChatRemoteDataSource,
) : ChatRepository {

    companion object {
        private const val DEFAULT_PAGE_SIZE = 20
        private const val LOADING_PLACEHOLDER_CONTENT = "loading_animation"
        private const val ROLE_ASSISTANT = "assistant"
    }

    /** 将服务端返回的消息中的 user_vote 转换为 userFeedback */
    private fun convertUserVoteToFeedback(messages: List<MsgInfo>): List<MsgInfo> {
        return messages.map { msg ->
            if (msg.user_vote != null && msg.userFeedback == null) {
                // 如果消息有 user_vote 但没有 userFeedback，进行转换
                val userFeedback =
                    when (msg.user_vote) {
                        VoteConstants.LIKE -> MsgInfo.UserFeedback.LIKE
                        VoteConstants.DISLIKE -> MsgInfo.UserFeedback.DISLIKE
                        else -> null
                    }
                msg.copy(userFeedback = userFeedback)
            } else {
                msg
            }
        }
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
                        val serverMessages =
                            convertUserVoteToFeedback(result.data.messages ?: emptyList())
                        if (serverMessages.isNotEmpty()) {
                            localDataSource.updateMessages(agentId, serverMessages)
                            localDataSource.setHasMore(agentId, result.data.hasMore)
                            localDataSource.setOffset(
                                agentId,
                                if (serverMessages.isNotEmpty()) pageSize else 0,
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
            when (val result = remoteDataSource.getMessages(agentId, pageSize, 0)) {
                is HttpResult.Success -> {
                    val messages = convertUserVoteToFeedback(result.data.messages ?: emptyList())
                    LogUtils.i(
                        "ChatRepositoryImpl.ensureInitialHistory loaded ${messages.size} messages for $agentId"
                    )

                    // 注意：ChatLocalDataSource.updateMessages 只是直接替换消息列表，不涉及 sortKey 分配
                    // 所以不需要反转消息列表，直接使用服务器返回的顺序即可
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
            when (val result = remoteDataSource.getMessages(agentId, pageSize, offset)) {
                is HttpResult.Success -> {
                    val moreMessages =
                        convertUserVoteToFeedback(result.data.messages ?: emptyList())
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
        content: String,
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
            }
        }

        return result
    }

    override suspend fun syncLatestMessages(agentId: String, pageSize: Int) {
        val isInitialLoaded = localDataSource.isInitialLoaded(agentId)
        val localMessages = localDataSource.getMessagesFlow(agentId).value
        val hasLocalMessages = localMessages.isNotEmpty()

        if (!isInitialLoaded || !hasLocalMessages) {
            // 如果没有初始化或没有本地数据，使用正常的初始化流程
            ensureInitialHistory(agentId, pageSize)
            return
        }

        try {
            when (val result = remoteDataSource.getMessages(agentId, pageSize, 0)) {
                is HttpResult.Success -> {
                    val serverMessages =
                        convertUserVoteToFeedback(result.data.messages ?: emptyList())
                    val currentLocalMessages = localDataSource.getMessagesFlow(agentId).value

                    // 检查是否有新消息或消息状态变化（如 user_vote）
                    val hasNewMessages =
                        serverMessages.any { serverMsg ->
                            currentLocalMessages.none { localMsg ->
                                localMsg.id == serverMsg.id ||
                                    (localMsg.content == serverMsg.content &&
                                        localMsg.role == serverMsg.role)
                            }
                        }

                    // 检查是否有消息状态变化（如 user_vote 更新）
                    val hasStatusChanges =
                        serverMessages.any { serverMsg ->
                            currentLocalMessages.any { localMsg ->
                                localMsg.id == serverMsg.id &&
                                    localMsg.user_vote != serverMsg.user_vote
                            }
                        }

                    if (hasNewMessages || hasStatusChanges) {
                        // 有新消息或状态变化，更新本地数据
                        // 🔧 修复消息顺序问题：
                        // 服务器返回的消息是 DESC 顺序（最新的在前），参见 IChatApi.getMsgs() 中 order 参数的默认值 "desc"
                        // 但 updateMessages 按列表顺序递增分配 sortKey（baseTime, baseTime+1, baseTime+2...）
                        // 如果第一条消息（最新的）得到最小的 sortKey，会导致排序错误
                        // 解决方案：反转消息列表，确保最旧的消息得到最小的 sortKey，最新的消息得到最大的 sortKey
                        // 这样在 ORDER BY sortKey DESC 查询时，最新的消息会排在前面，配合 reverseLayout=true 显示在底部
                        val reversedServerMessages = serverMessages.reversed()
                        if (serverMessages.isNotEmpty()) {
                            LogUtils.i(
                                "聊天接口数据",
                                "syncLatestMessages REVERSING messages: " +
                                    "original first=${serverMessages.first().id.take(8)}, last=${serverMessages.last().id.take(8)} | " +
                                    "reversed first=${reversedServerMessages.first().id.take(8)}, last=${reversedServerMessages.last().id.take(8)}"
                            )
                        }
                        
                        // 🔧 修复：合并服务器消息和本地消息，而不是只使用服务器消息
                        // 因为服务器只返回最新的20条消息，如果只使用服务器消息，会丢失历史消息
                        // 合并策略：保留本地消息，用服务器消息更新或追加
                        val allMessages = mutableListOf<MsgInfo>()
                        val serverMessageKeys = serverMessages.mapNotNull {
                            it.id.ifEmpty { it.localMsgId.ifEmpty { null } }
                        }.toSet()
                        
                        // 先添加本地消息中不在服务器消息列表中的消息（历史消息）
                        currentLocalMessages.forEach { localMsg ->
                            val localKey = localMsg.id.ifEmpty { localMsg.localMsgId }
                            if (localKey !in serverMessageKeys) {
                                allMessages.add(localMsg)
                            }
                        }
                        
                        // 然后添加服务器消息（已反转，确保顺序正确）
                        allMessages.addAll(reversedServerMessages)
                        
                        localDataSource.updateMessages(agentId, allMessages)
                        localDataSource.setHasMore(agentId, result.data.hasMore)
                        localDataSource.setOffset(
                            agentId,
                            if (serverMessages.isNotEmpty()) pageSize else 0,
                        )

                        LogUtils.i(
                            "聊天接口数据",
                            "syncLatestMessages 更新消息: agentId=$agentId, merged ${allMessages.size} messages (${currentLocalMessages.size} local + ${serverMessages.size} server)"
                        )
                    }
                }
                is HttpResult.Failure -> {
                    LogUtils.e(
                        "聊天接口数据",
                        "syncLatestMessages 失败: agentId=$agentId, error=${result.message}",
                    )
                }
            }
        } catch (e: Exception) {
            LogUtils.e("聊天接口数据", "syncLatestMessages 异常: agentId=$agentId, exception=${e.message}")
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
        feedback: MsgInfo.UserFeedback?,
    ) {
        LogUtils.d(
            "ChatRepositoryImpl.updateMessageFeedback called for $agentId, messageId: $messageId, feedback: $feedback"
        )
        localDataSource.updateMessageFeedback(agentId, messageId, feedback)
    }

    override suspend fun voteMessage(
        agentId: String,
        messageId: String,
        vote: String,
    ): HttpResult<VoteMessageRsp> {
        LogUtils.d(
            "ChatRepositoryImpl.voteMessage called for $agentId, messageId: $messageId, vote: $vote"
        )

        val result = remoteDataSource.voteMessage(agentId, messageId, vote)

        // 如果投票成功，更新本地消息的 user_vote 和 userFeedback 字段
        if (result is HttpResult.Success) {
            val voteValue = result.data.data?.vote
            if (voteValue != null) {
                // 将服务端的 vote 值转换为本地的 userFeedback
                val userFeedback =
                    when (voteValue) {
                        VoteConstants.LIKE -> MsgInfo.UserFeedback.LIKE
                        VoteConstants.DISLIKE -> MsgInfo.UserFeedback.DISLIKE
                        else -> null
                    }
                // 更新本地消息的 user_vote 和 userFeedback 字段
                val messages = localDataSource.getMessagesFlow(agentId).value
                val targetMessage =
                    messages.find { it.id == messageId || it.localMsgId == messageId }
                if (targetMessage != null) {
                    val updatedMessage =
                        targetMessage.copy(user_vote = voteValue, userFeedback = userFeedback)
                    localDataSource.updateMessage(agentId, targetMessage.localMsgId, updatedMessage)
                }
            }
        }

        return result
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
            messages.lastOrNull {
                it.role == ROLE_ASSISTANT && it.content != LOADING_PLACEHOLDER_CONTENT
            }

        if (lastAssistantMessage == null) {
            LogUtils.w(
                "ChatRepositoryImpl.recallLastAssistantMessage: No assistant message to recall"
            )
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
            }
        }
    }

    override suspend fun generateImageForMessage(
        agentId: String,
        messageId: String,
    ): com.architecture.httplib.core.HttpResult<
        ai.sxwl.android.data.http.services.ChatService.ChatImageGenerationResult
    > {
        LogUtils.d(
            "ChatRepositoryImpl.generateImageForMessage called for $agentId, messageId: $messageId"
        )

        // 找到触发消息生图的那条消息
        val messages = localDataSource.getMessagesFlow(agentId).value
        val sourceMessage = messages.find { it.id == messageId || it.localMsgId == messageId }

        if (sourceMessage == null) {
            LogUtils.e(
                "ChatRepositoryImpl.generateImageForMessage: source message not found: $messageId"
            )
            return HttpResult.Failure("Source message not found", -1)
        }

        // 在触发消息上设置 loading 状态：通过设置一个临时的 generatedImage（imageUrl 为 "loading"）
        // 这样图片会显示在触发消息的下方，而不是创建新消息
        // 使用 9:16 的宽高比（竖屏），与生成的图片尺寸匹配
        val loadingImage =
            MsgInfo.MsgMetaData.GeneratedImage(
                imageUrl = "loading", // 特殊标记，表示正在生成图片
                width = 300,
                height = 533, // 9:16 比例 (300 * 16 / 9 ≈ 533)
            )
        localDataSource.updateMessageGeneratedImage(agentId, messageId, loadingImage)

        val result = remoteDataSource.messageGenerateImage(agentId, messageId)

        when (result) {
            is HttpResult.Success -> {
                // 更新触发消息的 generatedImage 为实际图片
                val generatedImage =
                    MsgInfo.MsgMetaData.GeneratedImage(
                        imageUrl = result.data.imageUrl,
                        width = result.data.width,
                        height = result.data.height,
                    )
                localDataSource.updateMessageGeneratedImage(agentId, messageId, generatedImage)
                LogUtils.i(
                    "ChatRepositoryImpl.generateImageForMessage success: ${result.data.imageUrl}"
                )
            }

            is HttpResult.Failure -> {
                LogUtils.e("ChatRepositoryImpl.generateImageForMessage failure: ${result.message}")
                // 生成失败时，移除 loading 状态
                localDataSource.updateMessageGeneratedImage(agentId, messageId, null)
            }
        }

        return result
    }

    override suspend fun clearChatData(agentId: String) {
        LogUtils.d("ChatRepositoryImpl.clearChatData called for $agentId")
        localDataSource.clearChatData(agentId)
    }

    override suspend fun clearAllChatData() {
        LogUtils.d("ChatRepositoryImpl.clearAllChatData called")
        localDataSource.clearAllChatData()
    }
}
