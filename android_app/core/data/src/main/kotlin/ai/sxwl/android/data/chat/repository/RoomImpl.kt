package ai.sxwl.android.data.chat.repository

import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.api.model.SendMsgResponse
import ai.sxwl.android.data.api.model.VoteConstants
import ai.sxwl.android.data.api.model.VoteMessageRsp
import ai.sxwl.android.data.chat.data.ChatRemoteDataSource
import ai.sxwl.android.data.chat.data.RoomDataSource
import ai.sxwl.android.data.chat.domain.ChatRepository
import ai.sxwl.android.utils.LogUtils
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.flow.StateFlow

/** 聊天Repository实现 作为Domain层和Data层之间的桥梁 遵循Clean Architecture的Repository模式 */
class RoomImpl(
    private val localDataSource: RoomDataSource,
    private val remoteDataSource: ChatRemoteDataSource,
) : ChatRepository {

    companion object {
        private const val LOADING_PLACEHOLDER_CONTENT = "loading_animation"
        private const val ROLE_ASSISTANT = "assistant"
    }

    private fun convertUserVoteToFeedback(messages: List<MsgInfo>): List<MsgInfo> {
        return messages.map { msg ->
            if (msg.user_vote != null && msg.userFeedback == null) {
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

    private fun reverseServerMessages(messages: List<MsgInfo>): List<MsgInfo> {
        if (messages.isEmpty()) return messages
        return messages.reversed()
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
        LogUtils.d("RoomImpl.ensureInitialHistory called for $agentId")

        // ✅ 修复：检查状态一致性，如果标记为 loaded 但数据库为空，应该重新加载
        val isInitialLoaded = localDataSource.isInitialLoaded(agentId)
        val localMessages = localDataSource.getMessages(agentId)
        val hasLocalMessages = localMessages.isNotEmpty()

        // 如果已标记为 loaded 且有数据，直接返回
        if (isInitialLoaded && hasLocalMessages) {
            LogUtils.d(
                "RoomImpl.ensureInitialHistory: already loaded with ${localMessages.size} messages for $agentId"
            )
            return
        }

        // ✅ 修复：如果标记为 loaded 但没有数据，重置状态并重新加载
        if (isInitialLoaded) {
            LogUtils.w(
                "RoomImpl.ensureInitialHistory: isInitialLoaded=true but no messages, resetting state for $agentId"
            )
            localDataSource.setInitialLoaded(agentId, false)
        }

        // 先检查是否有本地缓存数据
        if (localMessages.isNotEmpty()) {
            LogUtils.i(
                "RoomImpl.ensureInitialHistory found ${localMessages.size} local messages for $agentId"
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
                            val reversedServerMessages = reverseServerMessages(serverMessages)
                            localDataSource.updateMessages(agentId, reversedServerMessages)
                            localDataSource.setHasMore(agentId, result.data.hasMore)
                            localDataSource.setOffset(
                                agentId,
                                if (serverMessages.isNotEmpty()) pageSize else 0,
                            )
                            LogUtils.i(
                                "RoomImpl.ensureInitialHistory synced ${serverMessages.size} server messages for $agentId"
                            )
                        }
                    }
                    is HttpResult.Failure -> {
                        LogUtils.e(
                            "RoomImpl.ensureInitialHistory sync failure for $agentId: ${result.message}"
                        )
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("RoomImpl.ensureInitialHistory sync exception: ${e.message}")
            }
            return
        }

        try {
            when (val result = remoteDataSource.getMessages(agentId, pageSize, 0)) {
                is HttpResult.Success -> {
                    val messages = convertUserVoteToFeedback(result.data.messages ?: emptyList())
                    LogUtils.i(
                        "RoomImpl.ensureInitialHistory loaded ${messages.size} messages for $agentId"
                    )

                    val reversedMessages = reverseServerMessages(messages)
                    localDataSource.updateMessages(agentId, reversedMessages)
                    localDataSource.setHasMore(agentId, result.data.hasMore)
                    localDataSource.setOffset(agentId, if (messages.isNotEmpty()) pageSize else 0)
                    localDataSource.setInitialLoaded(agentId, true)
                }
                is HttpResult.Failure -> {
                    LogUtils.e(
                        "RoomImpl.ensureInitialHistory failure for $agentId: ${result.message}"
                    )
                    localDataSource.setInitialLoaded(agentId, true)
                }
            }
        } catch (e: Exception) {
            LogUtils.e("RoomImpl.ensureInitialHistory exception: ${e.message}")
            localDataSource.setInitialLoaded(agentId, true)
        }
    }

    override suspend fun loadMoreMessages(agentId: String, pageSize: Int) {
        LogUtils.d("RoomImpl.loadMoreMessages called for $agentId")

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
                        val reversedMoreMessages = reverseServerMessages(moreMessages)
                        localDataSource.prependMessages(agentId, reversedMoreMessages)
                        localDataSource.incrementOffset(agentId, pageSize)
                    }
                    localDataSource.setHasMore(agentId, result.data.hasMore)

                    LogUtils.i(
                        "RoomImpl.loadMoreMessages loaded ${moreMessages.size} more messages for $agentId"
                    )
                }
                is HttpResult.Failure -> {
                    LogUtils.e("RoomImpl.loadMoreMessages failure for $agentId: ${result.message}")
                }
            }
        } catch (e: Exception) {
            LogUtils.e("RoomImpl.loadMoreMessages exception: ${e.message}")
        } finally {
            localDataSource.setLoadingMore(agentId, false)
        }
    }

    override suspend fun sendMessage(
        agentId: String,
        content: String,
    ): HttpResult<SendMsgResponse> {
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

        if (result is HttpResult.Success) {
            localDataSource.removeSendingMessage(agentId)

            val userMessageId = result.data.data?.user_message_id ?: 0L

            localDataSource.appendMessages(
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
                localDataSource.appendMessages(agentId, assistantMsgs)
            }
        } else {
            localDataSource.removeSendingMessage(agentId)
        }

        return result
    }

    override suspend fun syncLatestMessages(agentId: String, pageSize: Int) {
        LogUtils.d("RoomImpl.syncLatestMessages called for $agentId")

        // ✅ 修复：检查状态一致性，确保判断准确
        val isInitialLoaded = localDataSource.isInitialLoaded(agentId)
        val localMessages = localDataSource.getMessagesFlow(agentId).value
        val hasLocalMessages = localMessages.isNotEmpty()

        if (!isInitialLoaded || !hasLocalMessages) {
            LogUtils.i(
                "RoomImpl.syncLatestMessages calling ensureInitialHistory for $agentId (isInitialLoaded=$isInitialLoaded, hasLocalMessages=$hasLocalMessages)"
            )
            // ✅ 修复：确保 ensureInitialHistory 完成后再返回
            ensureInitialHistory(agentId, pageSize)
            return
        }

        try {
            when (val result = remoteDataSource.getMessages(agentId, pageSize, 0)) {
                is HttpResult.Success -> {
                    val serverMessages =
                        convertUserVoteToFeedback(result.data.messages ?: emptyList())
                    val localMessages = localDataSource.getMessagesFlow(agentId).value

                    // 检查是否有新消息或消息状态变化（如 user_vote）
                    val hasNewMessages =
                        serverMessages.any { serverMsg ->
                            localMessages.none { localMsg ->
                                localMsg.id == serverMsg.id ||
                                    (localMsg.content == serverMsg.content &&
                                        localMsg.role == serverMsg.role)
                            }
                        }

                    // 检查是否有消息状态变化（如 user_vote 更新）
                    val hasStatusChanges =
                        serverMessages.any { serverMsg ->
                            localMessages.any { localMsg ->
                                localMsg.id == serverMsg.id &&
                                    localMsg.user_vote != serverMsg.user_vote
                            }
                        }

                    if (hasNewMessages || hasStatusChanges) {
                        val reversedServerMessages = reverseServerMessages(serverMessages)

                        val allMessages = mutableListOf<MsgInfo>()
                        val serverMessageKeys =
                            serverMessages
                                .mapNotNull { it.id.ifEmpty { it.localMsgId.ifEmpty { null } } }
                                .toSet()

                        localMessages.forEach { localMsg ->
                            val localKey = localMsg.id.ifEmpty { localMsg.localMsgId }
                            if (localKey !in serverMessageKeys) {
                                allMessages.add(localMsg)
                            }
                        }

                        allMessages.addAll(reversedServerMessages)

                        localDataSource.updateMessages(agentId, allMessages)
                        localDataSource.setHasMore(agentId, result.data.hasMore)
                        localDataSource.setOffset(
                            agentId,
                            if (serverMessages.isNotEmpty()) pageSize else 0,
                        )

                        LogUtils.i(
                            "RoomImpl.syncLatestMessages found new messages or status changes for $agentId, merged ${allMessages.size} messages (${localMessages.size} local + ${serverMessages.size} server)"
                        )
                    } else {
                        LogUtils.i(
                            "RoomImpl.syncLatestMessages no new messages or status changes for $agentId"
                        )
                    }
                }
                is HttpResult.Failure -> {
                    LogUtils.e(
                        "RoomImpl.syncLatestMessages failure for $agentId: ${result.message}"
                    )
                }
            }
        } catch (e: Exception) {
            LogUtils.e("RoomImpl.syncLatestMessages exception: ${e.message}")
        }
    }

    override fun updateMessageAudioUrl(agentId: String, messageId: String, audioUrl: String) {
        LogUtils.d("RoomImpl.updateMessageAudioUrl called for $agentId, messageId: $messageId")
        localDataSource.updateMessageAudioUrl(agentId, messageId, audioUrl)
    }

    override fun updateMessageFeedback(
        agentId: String,
        messageId: String,
        feedback: MsgInfo.UserFeedback?,
    ) {
        LogUtils.d(
            "RoomImpl.updateMessageFeedback called for $agentId, messageId: $messageId, feedback: $feedback"
        )
        localDataSource.updateMessageFeedback(agentId, messageId, feedback)
    }

    override suspend fun voteMessage(
        agentId: String,
        messageId: String,
        vote: String,
    ): HttpResult<VoteMessageRsp> {
        LogUtils.d("RoomImpl.voteMessage called for $agentId, messageId: $messageId, vote: $vote")

        val result = remoteDataSource.voteMessage(agentId, messageId, vote)

        if (result is HttpResult.Success) {
            val voteValue = result.data.data?.vote
            if (voteValue != null) {
                val userFeedback =
                    when (voteValue) {
                        VoteConstants.LIKE -> MsgInfo.UserFeedback.LIKE
                        VoteConstants.DISLIKE -> MsgInfo.UserFeedback.DISLIKE
                        else -> null
                    }
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
            "RoomImpl.updateMessageGeneratedImage called for $agentId, messageId: $messageId, generatedImage: ${if (generatedImage != null) "set" else "null (remove)"}"
        )
        localDataSource.updateMessageGeneratedImage(agentId, messageId, generatedImage)
    }

    override suspend fun removeMessage(agentId: String, messageId: String) {
        LogUtils.d("RoomImpl.removeMessage called for $agentId, messageId: $messageId")
        localDataSource.removeMessage(agentId, messageId)
    }

    override suspend fun addMessage(agentId: String, message: MsgInfo) {
        LogUtils.d("RoomImpl.addMessage called for $agentId")
        localDataSource.addMessage(agentId, message)
    }

    override suspend fun recallLastAssistantMessage(agentId: String) {
        LogUtils.d("RoomImpl.recallLastAssistantMessage called for $agentId")
        val messages = localDataSource.getMessagesFlow(agentId).value

        val lastAssistantMessage =
            messages.lastOrNull {
                it.role == ROLE_ASSISTANT && it.content != LOADING_PLACEHOLDER_CONTENT
            }

        if (lastAssistantMessage == null) {
            LogUtils.w("RoomImpl.recallLastAssistantMessage: No assistant message to recall")
            return
        }

        localDataSource.removeMessage(agentId, lastAssistantMessage.localMsgId)
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

        localDataSource.removeSendingMessage(agentId)

        if (result is HttpResult.Success) {
            val choices = result.data.data?.choices ?: emptyList()
            if (choices.isNotEmpty()) {
                val assistantMsgs = choices.map { it.message }
                localDataSource.appendMessages(agentId, assistantMsgs)
            }
        }
    }

    override suspend fun generateImageForMessage(
        agentId: String,
        messageId: String,
    ): com.architecture.httplib.core.HttpResult<
        ai.sxwl.android.data.http.services.ChatService.ChatImageGenerationResult
    > {
        LogUtils.d("RoomImpl.generateImageForMessage called for $agentId, messageId: $messageId")

        val messages = localDataSource.getMessagesFlow(agentId).value
        val sourceMessage = messages.find { it.id == messageId || it.localMsgId == messageId }

        if (sourceMessage == null) {
            LogUtils.e("RoomImpl.generateImageForMessage: source message not found: $messageId")
            return HttpResult.Failure("Source message not found", -1)
        }

        val loadingImage =
            MsgInfo.MsgMetaData.GeneratedImage(imageUrl = "loading", width = 300, height = 533)
        localDataSource.updateMessageGeneratedImage(agentId, messageId, loadingImage)

        val result = remoteDataSource.messageGenerateImage(agentId, messageId)

        when (result) {
            is HttpResult.Success -> {
                val generatedImage =
                    MsgInfo.MsgMetaData.GeneratedImage(
                        imageUrl = result.data.imageUrl,
                        width = result.data.width,
                        height = result.data.height,
                    )
                localDataSource.updateMessageGeneratedImage(agentId, messageId, generatedImage)
                LogUtils.i("RoomImpl.generateImageForMessage success: ${result.data.imageUrl}")
            }

            is HttpResult.Failure -> {
                LogUtils.e("RoomImpl.generateImageForMessage failure: ${result.message}")
                localDataSource.updateMessageGeneratedImage(agentId, messageId, null)
            }
        }

        return result
    }

    override suspend fun clearChatData(agentId: String) {
        LogUtils.d("RoomImpl.clearChatData called for $agentId")
        localDataSource.clearChatData(agentId)
        LogUtils.i("RoomImpl.clearChatData completed for $agentId")
    }

    override suspend fun clearAllChatData() {
        LogUtils.d("RoomImpl.clearAllChatData called")
        localDataSource.clearAllChatData()
        LogUtils.i("RoomImpl.clearAllChatData completed")
    }

    override suspend fun clearMessage(agentId: String): Boolean {
        return remoteDataSource.clearMessage(agentId)
    }
}
