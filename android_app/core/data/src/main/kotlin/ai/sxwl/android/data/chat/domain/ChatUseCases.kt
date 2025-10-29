package ai.sxwl.android.data.chat.domain

import ai.sxwl.android.data.api.model.SendMsgResponse
import com.architecture.httplib.core.HttpResult

/**
 * 加载聊天历史用例
 * 封装加载聊天历史的业务逻辑
 * 遵循Clean Architecture的UseCase模式
 */
class LoadChatHistoryUseCase(
    private val chatRepository: ChatRepository
) {

    suspend operator fun invoke(agentId: String, pageSize: Int = 20) {
        chatRepository.ensureInitialHistory(agentId, pageSize)
    }
}

/**
 * 发送消息用例
 * 封装发送消息的业务逻辑
 */
class SendMessageUseCase(
    private val chatRepository: ChatRepository
) {

    suspend operator fun invoke(
        agentId: String,
        content: String
    ): HttpResult<SendMsgResponse> {
        return chatRepository.sendMessage(agentId, content)
    }
}

/**
 * 同步聊天数据用例
 * 封装同步聊天数据的业务逻辑
 */
class SyncChatDataUseCase(
    private val chatRepository: ChatRepository
) {

    suspend operator fun invoke(agentId: String, pageSize: Int = 20) {
        chatRepository.syncLatestMessages(agentId, pageSize)
    }
}
