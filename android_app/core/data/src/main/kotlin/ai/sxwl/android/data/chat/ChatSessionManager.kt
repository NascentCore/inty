package ai.sxwl.android.data.chat

import ai.sxwl.android.data.annotations.GeneratedByAI
import ai.sxwl.android.data.api.IChatApi
import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.api.model.SendMsgReq
import ai.sxwl.android.data.api.model.SendMsgResponse
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.utils.LogUtils
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

@GeneratedByAI
object ChatSessionManager {
    private const val DEFAULT_PAGE_SIZE = 20
    private const val LOADING_PLACEHOLDER_CONTENT = "loading_animation"
    private const val ROLE_ASSISTANT = "assistant"

    private data class AgentChatSession(
        val messages: MutableStateFlow<List<MsgInfo>> = MutableStateFlow(emptyList()),
        val isLoadingMore: MutableStateFlow<Boolean> = MutableStateFlow(false),
        val hasMore: MutableStateFlow<Boolean> = MutableStateFlow(true),
        var isInitialLoaded: Boolean = false,
        var offset: Int = 0,
        val lock: Mutex = Mutex(),
    )

    private val agentIdToSession = mutableMapOf<String, AgentChatSession>()

    private fun getSession(agentId: String): AgentChatSession {
        return agentIdToSession.getOrPut(agentId) {
            // 从本地存储加载数据
            loadSessionFromStorage(agentId)
        }
    }

    /** 从本地存储加载会话数据 暂时禁用数据持久化，避免序列化问题 */
    private fun loadSessionFromStorage(agentId: String): AgentChatSession {
        val session = AgentChatSession()

        // 暂时禁用数据持久化，避免序列化问题
        // TODO: 实现更简单的数据存储方案
        LogUtils.i("ChatSessionManager: Data persistence temporarily disabled for $agentId")

        return session
    }

    /** 保存会话数据到本地存储 暂时禁用数据持久化，避免序列化问题 */
    private fun saveSessionToStorage(
        agentId: String,
        session: AgentChatSession,
    ) {
        // 暂时禁用数据持久化，避免序列化问题
        // TODO: 实现更简单的数据存储方案
        LogUtils.d("ChatSessionManager: Data persistence temporarily disabled for $agentId")
    }

    fun messagesFlow(agentId: String): StateFlow<List<MsgInfo>> = getSession(
        agentId
    ).messages.asStateFlow()

    fun isLoadingMoreFlow(agentId: String): StateFlow<Boolean> = getSession(
        agentId
    ).isLoadingMore.asStateFlow()

    fun hasMoreFlow(agentId: String): StateFlow<Boolean> = getSession(agentId).hasMore.asStateFlow()

    suspend fun ensureInitialHistory(
        agentId: String,
        pageSize: Int = DEFAULT_PAGE_SIZE,
    ) {
        val session = getSession(agentId)
        LogUtils.i(
            "ChatSessionManager.ensureInitialHistory called for $agentId, isInitialLoaded=${session.isInitialLoaded}",
        )
        if (session.isInitialLoaded) return
        session.lock.withLock {
            if (session.isInitialLoaded) return
            try {
                LogUtils.i(
                    "ChatSessionManager.ensureInitialHistory calling API for $agentId with pageSize=$pageSize, offset=0",
                )
                val api: IChatApi = NetServiceMgr.getChatApi()
                val result = api.getMsgs(agentId, pageSize, 0)
                when (result) {
                    is HttpResult.Success -> {
                        val newMessages = result.data.messages ?: emptyList()
                        LogUtils.i(
                            "ChatSessionManager.ensureInitialHistory API returned ${newMessages.size} messages for $agentId",
                        )

                        // 调试：打印每条消息的详细信息
                        newMessages.forEachIndexed { index, msg ->
                            LogUtils.d(
                                "Message $index: role=${msg.role}, content=${
                                    msg.content.take(
                                        50,
                                    )
                                }..., id=${msg.id}, localMsgId=${msg.localMsgId}",
                            )
                        }

                        // 调试：打印每个消息的key
                        newMessages.forEachIndexed { index, msg ->
                            val key = keyFor(msg)
                            LogUtils.d("Message $index key: $key")
                        }

                        val unique = newMessages.distinctBy { keyFor(it) }
                        LogUtils.i(
                            "ChatSessionManager.ensureInitialHistory after distinctBy: ${unique.size} unique messages",
                        )

                        session.messages.value = unique
                        session.hasMore.value = result.data.hasMore
                        session.offset = if (unique.isNotEmpty()) pageSize else 0
                        session.isInitialLoaded = true

                        // 保存到本地存储
                        saveSessionToStorage(agentId, session)

                        LogUtils.i(
                            "ChatSessionManager.ensureInitialHistory loaded ${unique.size} msgs for $agentId, hasMore=${session.hasMore.value}",
                        )
                    }
                    is HttpResult.Failure -> {
                        LogUtils.e(
                            "ChatSessionManager.ensureInitialHistory failure for $agentId: ${result.message}",
                        )
                        // 标记已尝试加载，避免重复打接口；仍允许后续手动刷新时再拉
                        session.isInitialLoaded = true
                        saveSessionToStorage(agentId, session)
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("ChatSessionManager.ensureInitialHistory exception: ${e.message}")
                session.isInitialLoaded = true
                saveSessionToStorage(agentId, session)
            }
        }
    }

    suspend fun loadMore(
        agentId: String,
        pageSize: Int = DEFAULT_PAGE_SIZE,
    ) {
        val session = getSession(agentId)
        session.lock.withLock {
            if (session.isLoadingMore.value) return
            if (!session.hasMore.value) return
            session.isLoadingMore.value = true
            try {
                val api: IChatApi = NetServiceMgr.getChatApi()
                val result = api.getMsgs(agentId, pageSize, session.offset)
                when (result) {
                    is HttpResult.Success -> {
                        val more = result.data.messages ?: emptyList()
                        if (more.isNotEmpty()) {
                            val combined = session.messages.value + more
                            val unique = combined.distinctBy { keyFor(it) }
                            session.messages.value = unique
                            session.offset += pageSize
                        }
                        session.hasMore.value = result.data.hasMore

                        // 保存到本地存储
                        saveSessionToStorage(agentId, session)

                        LogUtils.i(
                            "ChatSessionManager.loadMore for $agentId loaded ${more.size}, hasMore=${session.hasMore.value}, offset=${session.offset}",
                        )
                    }
                    is HttpResult.Failure -> {
                        LogUtils.e(
                            "ChatSessionManager.loadMore failure for $agentId: ${result.message}",
                        )
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("ChatSessionManager.loadMore exception: ${e.message}")
            } finally {
                session.isLoadingMore.value = false
            }
        }
    }

    suspend fun sendMessage(
        agentId: String,
        content: String,
    ): HttpResult<SendMsgResponse> {
        val session = getSession(agentId)
        return session.lock.withLock {
            // 1) 先插入用户消息与loading占位
            val userMsg = MsgInfo(content = content.trimEnd(), role = "user")
            val loadingMsg = MsgInfo(content = LOADING_PLACEHOLDER_CONTENT, role = ROLE_ASSISTANT)
            session.messages.value =
                buildList {
                    add(loadingMsg)
                    add(userMsg)
                    addAll(session.messages.value)
                }

            // 立即保存用户消息到本地存储
            saveSessionToStorage(agentId, session)

            val api: IChatApi = NetServiceMgr.getChatApi()
            val req = SendMsgReq(listOf(userMsg))
            val result =
                try {
                    api.sendMsg(agentId, req)
                } catch (e: Exception) {
                    LogUtils.e("ChatSessionManager.sendMessage exception: ${e.message}")
                    HttpResult.Failure(e.message ?: "unknown error", -1)
                }

            // 2) 移除loading
            session.messages.value =
                session.messages.value.filterNot {
                    it.content == LOADING_PLACEHOLDER_CONTENT && it.role == ROLE_ASSISTANT
                }

            // 3) 追加AI回复
            if (result is HttpResult.Success) {
                val choices = result.data.data?.choices ?: emptyList()
                if (choices.isNotEmpty()) {
                    val assistantMsgs = choices.map { it.message }
                    val merged =
                        buildList {
                            addAll(assistantMsgs)
                            addAll(session.messages.value)
                        }
                    session.messages.value = merged

                    // 会话已读更新
                    choices.lastOrNull()?.message?.content?.let { lastContent ->
                        IntySetting.setConversationReaded(agentId, lastContent)
                    }
                }
            }

            // 保存最终的消息状态到本地存储
            saveSessionToStorage(agentId, session)

            result
        }
    }

    fun updateMessageAudioUrl(
        agentId: String,
        messageId: String,
        audioUrl: String,
    ) {
        val session = getSession(agentId)
        session.messages.value =
            session.messages.value.map { msg ->
                if (msg.localMsgId == messageId) msg.copy(audio_url = audioUrl) else msg
            }

        // 保存更新后的消息到本地存储
        saveSessionToStorage(agentId, session)
    }

    /** 清理指定agent的聊天数据 */
    fun clearChatData(agentId: String) {
        agentIdToSession.remove(agentId)
        IntySetting.clearChatData(agentId)
        LogUtils.i("ChatSessionManager cleared chat data for agent $agentId")
    }

    /** 清理所有聊天数据 */
    fun clearAllChatData() {
        agentIdToSession.clear()
        IntySetting.clearAllChatData()
        LogUtils.i("ChatSessionManager cleared all chat data")
    }

    /** 增量同步：检查服务器是否有新消息 只在本地有数据且已初始化时调用，避免重复请求 */
    suspend fun syncLatestMessages(
        agentId: String,
        pageSize: Int = DEFAULT_PAGE_SIZE,
    ) {
        val session = getSession(agentId)
        LogUtils.i(
            "ChatSessionManager.syncLatestMessages called for $agentId, isInitialLoaded=${session.isInitialLoaded}, messagesCount=${session.messages.value.size}",
        )
        if (!session.isInitialLoaded || session.messages.value.isEmpty()) {
            // 如果没有初始化或没有本地数据，使用正常的初始化流程
            LogUtils.i(
                "ChatSessionManager.syncLatestMessages calling ensureInitialHistory for $agentId",
            )
            ensureInitialHistory(agentId, pageSize)
            return
        }

        session.lock.withLock {
            try {
                val api: IChatApi = NetServiceMgr.getChatApi()
                // 只获取最新的几条消息来检查是否有更新
                val result = api.getMsgs(agentId, pageSize, 0)
                when (result) {
                    is HttpResult.Success -> {
                        val serverMessages = result.data.messages ?: emptyList()
                        val localMessages = session.messages.value

                        // 检查是否有新消息（通过比较消息ID或内容）
                        val hasNewMessages =
                            serverMessages.any { serverMsg ->
                                localMessages.none { localMsg ->
                                    localMsg.id == serverMsg.id ||
                                        (
                                            localMsg.content == serverMsg.content &&
                                                localMsg.role == serverMsg.role
                                            )
                                }
                            }

                        if (hasNewMessages) {
                            // 有新消息，重新加载完整数据
                            val unique = serverMessages.distinctBy { keyFor(it) }
                            session.messages.value = unique
                            session.hasMore.value = result.data.hasMore
                            session.offset = if (unique.isNotEmpty()) pageSize else 0

                            // 保存到本地存储
                            saveSessionToStorage(agentId, session)

                            LogUtils.i(
                                "ChatSessionManager.syncLatestMessages found new messages for $agentId, updated ${unique.size} messages",
                            )
                        } else {
                            LogUtils.i(
                                "ChatSessionManager.syncLatestMessages no new messages for $agentId",
                            )
                        }
                    }
                    is HttpResult.Failure -> {
                        LogUtils.e(
                            "ChatSessionManager.syncLatestMessages failure for $agentId: ${result.message}",
                        )
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("ChatSessionManager.syncLatestMessages exception: ${e.message}")
            }
        }
    }

    private fun keyFor(msg: MsgInfo): String {
        // 优先使用服务器ID，如果没有则使用内容+角色作为键
        return if (msg.id.isNotEmpty()) {
            msg.id
        } else {
            "${msg.role}_${msg.content}_${msg.localMsgId}"
        }
    }
}
