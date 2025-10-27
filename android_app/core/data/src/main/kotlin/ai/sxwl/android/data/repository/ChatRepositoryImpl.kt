package ai.sxwl.android.data.repository

import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.api.model.SendMsgResponse
import ai.sxwl.android.data.chat.local.ChatLocalDataSource
import ai.sxwl.android.data.chat.remote.ChatRemoteDataSource
import ai.sxwl.android.data.domain.ChatRepository
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.utils.LogUtils
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.flow.StateFlow

/** 聊天Repository实现 作为Domain层和Data层之间的桥梁 */
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

        try {
            val result = remoteDataSource.getMessages(agentId, pageSize, 0)
            when (result) {
                is HttpResult.Success -> {
                    val messages = result.data.messages ?: emptyList()
                    LogUtils.i("ChatRepositoryImpl.ensureInitialHistory loaded ${messages.size} messages for $agentId")

                    localDataSource.updateMessages(agentId, messages)
                    localDataSource.setHasMore(agentId, result.data.hasMore)
                    localDataSource.setOffset(agentId, if (messages.isNotEmpty()) pageSize else 0)
                    localDataSource.setInitialLoaded(agentId, true)
                }

                is HttpResult.Failure -> {
                    LogUtils.e("ChatRepositoryImpl.ensureInitialHistory failure for $agentId: ${result.message}")
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

                    LogUtils.i("ChatRepositoryImpl.loadMoreMessages loaded ${moreMessages.size} more messages for $agentId")
                }

                is HttpResult.Failure -> {
                    LogUtils.e("ChatRepositoryImpl.loadMoreMessages failure for $agentId: ${result.message}")
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

        val result = try {
            remoteDataSource.sendMessage(agentId, listOf(userMsg))
        } catch (e: Exception) {
            LogUtils.e("ChatRepositoryImpl.sendMessage exception: ${e.message}")
            HttpResult.Failure(e.message ?: "unknown error", -1)
        }

        // 2) 移除loading占位
        val currentMessages = localDataSource.getMessagesFlow(agentId).value
        val filteredMessages = currentMessages.filterNot {
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

        if (!localDataSource.isInitialLoaded(agentId) || localDataSource.getMessagesFlow(agentId).value.isEmpty()) {
            // 如果没有初始化或没有本地数据，使用正常的初始化流程
            LogUtils.i("ChatRepositoryImpl.syncLatestMessages calling ensureInitialHistory for $agentId")
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
                    val hasNewMessages = serverMessages.any { serverMsg ->
                        localMessages.none { localMsg ->
                            localMsg.id == serverMsg.id ||
                                    (localMsg.content == serverMsg.content && localMsg.role == serverMsg.role)
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

                        LogUtils.i("ChatRepositoryImpl.syncLatestMessages found new messages for $agentId, updated ${serverMessages.size} messages")
                    } else {
                        LogUtils.i("ChatRepositoryImpl.syncLatestMessages no new messages for $agentId")
                    }
                }

                is HttpResult.Failure -> {
                    LogUtils.e("ChatRepositoryImpl.syncLatestMessages failure for $agentId: ${result.message}")
                }
            }
        } catch (e: Exception) {
            LogUtils.e("ChatRepositoryImpl.syncLatestMessages exception: ${e.message}")
        }
    }

    override fun updateMessageAudioUrl(agentId: String, messageId: String, audioUrl: String) {
        LogUtils.d("ChatRepositoryImpl.updateMessageAudioUrl called for $agentId, messageId: $messageId")
        localDataSource.updateMessageAudioUrl(agentId, messageId, audioUrl)
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
