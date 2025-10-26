package ai.sxwl.android.data.usecase

import ai.sxwl.android.data.api.model.SendMsgResponse
import ai.sxwl.android.data.domain.ChatRepository
import ai.sxwl.android.utils.LogUtils
import com.architecture.httplib.core.HttpResult
import javax.inject.Inject

/**
 * 发送消息用例
 * 封装发送消息的业务逻辑
 */
class SendMessageUseCase @Inject constructor(
    private val chatRepository: ChatRepository
) {

    suspend operator fun invoke(agentId: String, content: String): HttpResult<SendMsgResponse> {
        LogUtils.d("SendMessageUseCase: sending message to agent $agentId")
        return chatRepository.sendMessage(agentId, content)
    }
}
