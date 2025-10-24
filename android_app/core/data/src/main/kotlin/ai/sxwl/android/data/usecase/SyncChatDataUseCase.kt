package ai.sxwl.android.data.usecase

import ai.sxwl.android.data.domain.ChatRepository
import ai.sxwl.android.utils.LogUtils
import javax.inject.Inject

/**
 * 同步聊天数据用例
 * 封装同步聊天数据的业务逻辑
 */
class SyncChatDataUseCase @Inject constructor(
    private val chatRepository: ChatRepository
) {
    
    suspend operator fun invoke(agentId: String, pageSize: Int = 20) {
        LogUtils.d("SyncChatDataUseCase: syncing chat data for agent $agentId")
        chatRepository.syncLatestMessages(agentId, pageSize)
    }
}
