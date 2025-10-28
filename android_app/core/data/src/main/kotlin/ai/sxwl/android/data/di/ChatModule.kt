package ai.sxwl.android.data.di

import ai.sxwl.android.data.chat.local.ChatLocalDataSource
import ai.sxwl.android.data.chat.remote.ChatRemoteDataSource
import ai.sxwl.android.data.domain.AgentRepository
import ai.sxwl.android.data.domain.ChatRepository
import ai.sxwl.android.data.repository.AgentRepositoryImpl
import ai.sxwl.android.data.repository.ChatRepositoryImpl
import ai.sxwl.android.data.usecase.LoadChatHistoryUseCase
import ai.sxwl.android.data.usecase.SendMessageUseCase
import ai.sxwl.android.data.usecase.SyncChatDataUseCase
import ai.sxwl.android.data.usecase.agent.GetChatAgentsUseCase

/** 聊天模块依赖注入 提供聊天相关的依赖 */
object ChatModule {

    // Data Sources
    private val _chatLocalDataSource: ChatLocalDataSource by lazy { ChatLocalDataSource() }
    private val _chatRemoteDataSource: ChatRemoteDataSource by lazy { ChatRemoteDataSource() }

    // Repositories
    private val _chatRepository: ChatRepository by lazy {
        ChatRepositoryImpl(_chatLocalDataSource, _chatRemoteDataSource)
    }
    private val _agentRepository: AgentRepository by lazy { AgentRepositoryImpl() }

    // UseCases
    val sendMessageUseCase: SendMessageUseCase by lazy { SendMessageUseCase(_chatRepository) }

    val loadChatHistoryUseCase: LoadChatHistoryUseCase by lazy {
        LoadChatHistoryUseCase(_chatRepository)
    }

    val syncChatDataUseCase: SyncChatDataUseCase by lazy { SyncChatDataUseCase(_chatRepository) }

    val getChatAgentsUseCase: GetChatAgentsUseCase by lazy { GetChatAgentsUseCase(_agentRepository) }

    // Repository for external access
    fun getChatRepository(): ChatRepository = _chatRepository
    fun getAgentRepository(): AgentRepository = _agentRepository
}
