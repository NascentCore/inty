package ai.sxwl.android.data.chat.data

import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.utils.LogUtils
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

/** 聊天本地数据源 负责管理聊天消息的本地缓存和状态 遵循Clean Architecture的数据层模式 */
class ChatLocalDataSource {

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
        return agentIdToSession.getOrPut(agentId) { AgentChatSession() }
    }

    fun getMessagesFlow(agentId: String): StateFlow<List<MsgInfo>> =
        getSession(agentId).messages.asStateFlow()

    fun getLoadingMoreFlow(agentId: String): StateFlow<Boolean> =
        getSession(agentId).isLoadingMore.asStateFlow()

    fun getHasMoreFlow(agentId: String): StateFlow<Boolean> =
        getSession(agentId).hasMore.asStateFlow()

    suspend fun updateMessages(agentId: String, messages: List<MsgInfo>) {
        val session = getSession(agentId)
        session.lock.withLock { session.messages.value = messages }
    }

    suspend fun appendMessages(agentId: String, newMessages: List<MsgInfo>) {
        val session = getSession(agentId)
        session.lock.withLock {
            val combined = session.messages.value + newMessages
            val unique = combined.distinctBy { keyFor(it) }
            session.messages.value = unique
        }
    }

    suspend fun prependMessages(agentId: String, newMessages: List<MsgInfo>) {
        val session = getSession(agentId)
        session.lock.withLock {
            val combined = newMessages + session.messages.value
            val unique = combined.distinctBy { keyFor(it) }
            session.messages.value = unique
        }
    }

    suspend fun setLoadingMore(agentId: String, loading: Boolean) {
        getSession(agentId).isLoadingMore.value = loading
    }

    suspend fun setHasMore(agentId: String, hasMore: Boolean) {
        getSession(agentId).hasMore.value = hasMore
    }

    suspend fun setInitialLoaded(agentId: String, loaded: Boolean) {
        getSession(agentId).isInitialLoaded = loaded
    }

    suspend fun isInitialLoaded(agentId: String): Boolean {
        return getSession(agentId).isInitialLoaded
    }

    suspend fun setOffset(agentId: String, offset: Int) {
        getSession(agentId).offset = offset
    }

    suspend fun getOffset(agentId: String): Int {
        return getSession(agentId).offset
    }

    suspend fun incrementOffset(agentId: String, increment: Int) {
        val session = getSession(agentId)
        session.offset += increment
    }

    fun updateMessageAudioUrl(agentId: String, messageId: String, audioUrl: String) {
        val session = getSession(agentId)
        session.messages.value =
            session.messages.value.map { msg ->
                if (msg.localMsgId == messageId) msg.copy(audio_url = audioUrl) else msg
            }
    }

    fun updateMessageFeedback(agentId: String, messageId: String, feedback: MsgInfo.UserFeedback?) {
        val session = getSession(agentId)
        session.messages.value =
            session.messages.value.map { msg ->
                if (msg.localMsgId == messageId) {
                    msg.copy(userFeedback = feedback)
                } else {
                    msg
                }
            }
    }

    fun updateMessageGeneratedImage(
        agentId: String,
        messageId: String,
        generatedImage: MsgInfo.MsgMetaData.GeneratedImage?,
    ) {
        val session = getSession(agentId)
        session.messages.value =
            session.messages.value.map { msg ->
                if (msg.id == messageId || msg.localMsgId == messageId) {
                    val currentMeta = msg.meta_data ?: MsgInfo.MsgMetaData(agentId = agentId)
                    val updatedMeta = if (generatedImage != null) {
                        currentMeta.copy(generatedImage = generatedImage)
                    } else {
                        // 移除 generatedImage：创建新的 meta_data，不包含 generatedImage
                        MsgInfo.MsgMetaData(
                            agentId = currentMeta.agentId,
                            isOpening = currentMeta.isOpening,
                            generatedImage = null,
                        )
                    }
                    msg.copy(meta_data = updatedMeta)
                } else {
                    msg
                }
            }
    }

    suspend fun removeMessage(agentId: String, messageId: String) {
        val session = getSession(agentId)
        session.lock.withLock {
            session.messages.value = session.messages.value.filter { it.localMsgId != messageId }
        }
    }

    suspend fun addMessage(agentId: String, message: MsgInfo) {
        val session = getSession(agentId)
        session.lock.withLock {
            val combined = listOf(message) + session.messages.value
            val unique = combined.distinctBy { keyFor(it) }
            session.messages.value = unique
        }
    }

    fun clearChatData(agentId: String) {
        agentIdToSession.remove(agentId)
        IntySetting.clearChatData(agentId)
        LogUtils.i("ChatLocalDataSource cleared chat data for agent $agentId")
    }

    fun clearAllChatData() {
        agentIdToSession.clear()
        IntySetting.clearAllChatData()
        LogUtils.i("ChatLocalDataSource cleared all chat data")
    }

    private fun keyFor(msg: MsgInfo): String {
        return if (msg.id.isNotEmpty()) {
            msg.id
        } else {
            "${msg.role}_${msg.content}_${msg.localMsgId}"
        }
    }
}
