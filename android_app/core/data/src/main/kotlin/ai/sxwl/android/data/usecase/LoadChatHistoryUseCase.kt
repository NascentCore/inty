package ai.sxwl.android.data.usecase

import ai.sxwl.android.data.domain.ChatRepository
import ai.sxwl.android.utils.LogUtils
import javax.inject.Inject

/** 加载聊天历史用例 封装加载聊天历史的业务逻辑 */
class LoadChatHistoryUseCase
@Inject
constructor(private val chatRepository: ChatRepository) {
    suspend operator fun invoke(
        agentId: String,
        pageSize: Int = 20,
    ) {
        LogUtils.d("LoadChatHistoryUseCase: loading chat history for agent $agentId")
        chatRepository.ensureInitialHistory(agentId, pageSize)
    }
}
