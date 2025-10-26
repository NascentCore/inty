package ai.sxwl.android.data.di

import ai.sxwl.android.data.domain.ChatRepository
import ai.sxwl.android.data.repository.ChatRepositoryImpl
import ai.sxwl.android.data.usecase.LoadChatHistoryUseCase
import ai.sxwl.android.data.usecase.SendMessageUseCase
import ai.sxwl.android.data.usecase.SyncChatDataUseCase

/** 聊天模块依赖注入 提供聊天相关的依赖 */
object ChatModule {
    // Repository
    private val _chatRepository: ChatRepository by lazy { ChatRepositoryImpl() }

    // UseCases
    val sendMessageUseCase: SendMessageUseCase by lazy { SendMessageUseCase(_chatRepository) }

    val loadChatHistoryUseCase: LoadChatHistoryUseCase by lazy {
        LoadChatHistoryUseCase(_chatRepository)
    }

    val syncChatDataUseCase: SyncChatDataUseCase by lazy { SyncChatDataUseCase(_chatRepository) }

    // Repository for external access
    fun getChatRepository(): ChatRepository = _chatRepository
}
