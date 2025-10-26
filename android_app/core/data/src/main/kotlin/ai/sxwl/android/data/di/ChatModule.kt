package ai.sxwl.android.data.di

import ai.sxwl.android.data.domain.ChatRepository
import ai.sxwl.android.data.repository.ChatRepositoryImpl
import ai.sxwl.android.data.usecase.LoadChatHistoryUseCase
import ai.sxwl.android.data.usecase.SendMessageUseCase
import ai.sxwl.android.data.usecase.SyncChatDataUseCase

/**
 * 聊天模块依赖注入
 * 提供聊天相关的依赖
 */
object ChatModule {
// 存储库
    private val _chatRepository: ChatRepository by lazy { ChatRepositoryImpl() }
// 例子
    val sendMessageUseCase: SendMessageUseCase by lazy {
        SendMessageUseCase(_chatRepository)
    }

    val loadChatHistoryUseCase: LoadChatHistoryUseCase by lazy {
        LoadChatHistoryUseCase(_chatRepository)
    }

    val syncChatDataUseCase: SyncChatDataUseCase by lazy {
        SyncChatDataUseCase(_chatRepository)
    }
// 提供外部访问的存储库
    fun getChatRepository(): ChatRepository = _chatRepository
}
