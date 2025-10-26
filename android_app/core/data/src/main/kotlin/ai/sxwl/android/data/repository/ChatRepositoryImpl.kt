package ai.sxwl.android.data.repository

import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.api.model.SendMsgResponse
import ai.sxwl.android.data.chat.ChatSessionManager
import ai.sxwl.android.data.domain.ChatRepository
import ai.sxwl.android.utils.LogUtils
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.flow.StateFlow

/**
 * 聊天Repository实现
 * 作为领域层和数据层之间的桥梁
 */
class ChatRepositoryImpl : ChatRepository {

    override fun getMessagesFlow(agentId: String): StateFlow<List<MsgInfo>> {
        return ChatSessionManager.messagesFlow(agentId)
    }

    override fun getLoadingMoreFlow(agentId: String): StateFlow<Boolean> {
        return ChatSessionManager.isLoadingMoreFlow(agentId)
    }

    override fun getHasMoreFlow(agentId: String): StateFlow<Boolean> {
        return ChatSessionManager.hasMoreFlow(agentId)
    }

    override suspend fun ensureInitialHistory(agentId: String, pageSize: Int) {
        LogUtils.d("ChatRepositoryImpl.ensureInitialHistory called for $agentId")
        ChatSessionManager.ensureInitialHistory(agentId, pageSize)
    }

    override suspend fun loadMoreMessages(agentId: String, pageSize: Int) {
        LogUtils.d("ChatRepositoryImpl.loadMoreMessages called for $agentId")
        ChatSessionManager.loadMore(agentId, pageSize)
    }

    override suspend fun sendMessage(agentId: String, content: String): HttpResult<SendMsgResponse> {
        LogUtils.d("ChatRepositoryImpl.sendMessage called for $agentId: $content")
        return ChatSessionManager.sendMessage(agentId, content)
    }

    override suspend fun syncLatestMessages(agentId: String, pageSize: Int) {
        LogUtils.d("ChatRepositoryImpl.syncLatestMessages called for $agentId")
        ChatSessionManager.syncLatestMessages(agentId, pageSize)
    }

    override fun updateMessageAudioUrl(agentId: String, messageId: String, audioUrl: String) {
        LogUtils.d("ChatRepositoryImpl.updateMessageAudioUrl called for $agentId, messageId: $messageId")
        ChatSessionManager.updateMessageAudioUrl(agentId, messageId, audioUrl)
    }

    override fun clearChatData(agentId: String) {
        LogUtils.d("ChatRepositoryImpl.clearChatData called for $agentId")
        ChatSessionManager.clearChatData(agentId)
    }

    override fun clearAllChatData() {
        LogUtils.d("ChatRepositoryImpl.clearAllChatData called")
        ChatSessionManager.clearAllChatData()
    }
}
