package ai.sxwl.android.data.di

import ai.sxwl.android.data.agent.domain.AgentRepository
import ai.sxwl.android.data.agent.domain.GetChatAgentsUseCase
import ai.sxwl.android.data.agent.repository.AgentRepositoryImpl
import ai.sxwl.android.data.cache.AgentCacheProvider
import ai.sxwl.android.data.cache.RecommendedAgentCacheProvider
import ai.sxwl.android.data.chat.data.ChatLocalDataSource
import ai.sxwl.android.data.chat.data.ChatRemoteDataSource
import ai.sxwl.android.data.chat.domain.ChatRepository
import ai.sxwl.android.data.chat.domain.GenerateImageUseCase
import ai.sxwl.android.data.chat.domain.LoadChatHistoryUseCase
import ai.sxwl.android.data.chat.domain.RecallMessageUseCase
import ai.sxwl.android.data.chat.domain.SendMessageUseCase
import ai.sxwl.android.data.chat.domain.SyncChatDataUseCase
import ai.sxwl.android.data.chat.domain.UpdateMessageFeedbackUseCase
import ai.sxwl.android.data.chat.repository.ChatRepositoryImpl
import ai.sxwl.android.data.explore.domain.ExploreRepository
import ai.sxwl.android.data.explore.domain.GetRecommendAgentsUseCase
import ai.sxwl.android.data.explore.repository.ExploreRepositoryImpl

/** 数据层依赖注入管理 遵循Clean Architecture的依赖注入模式 不使用Hilt，采用手动依赖注入 */
object DataModule {

    // Data Sources
    private val _chatLocalDataSource: ChatLocalDataSource by lazy { ChatLocalDataSource() }
    private val _chatRemoteDataSource: ChatRemoteDataSource by lazy { ChatRemoteDataSource() }

    // Cache Providers (injected from app module)
    private var _agentCacheProvider: AgentCacheProvider? = null
    private var _recommendedCacheProvider: RecommendedAgentCacheProvider? = null

    // Repositories
    private val _chatRepository: ChatRepository by lazy {
        ChatRepositoryImpl(_chatLocalDataSource, _chatRemoteDataSource)
    }

    private val _agentRepository: AgentRepository by lazy {
        AgentRepositoryImpl(_agentCacheProvider)
    }

    private val _exploreRepository: ExploreRepository by lazy {
        ExploreRepositoryImpl(_recommendedCacheProvider)
    }

    // UseCases
    val loadChatHistoryUseCase: LoadChatHistoryUseCase by lazy {
        LoadChatHistoryUseCase(_chatRepository)
    }

    val sendMessageUseCase: SendMessageUseCase by lazy { SendMessageUseCase(_chatRepository) }

    val syncChatDataUseCase: SyncChatDataUseCase by lazy { SyncChatDataUseCase(_chatRepository) }

    val updateMessageFeedbackUseCase: UpdateMessageFeedbackUseCase by lazy {
        UpdateMessageFeedbackUseCase(_chatRepository)
    }

    val recallMessageUseCase: RecallMessageUseCase by lazy { RecallMessageUseCase(_chatRepository) }

    val generateImageUseCase: GenerateImageUseCase by lazy { GenerateImageUseCase(_chatRepository) }

    val getChatAgentsUseCase: GetChatAgentsUseCase by lazy {
        GetChatAgentsUseCase(_agentRepository)
    }

    val getRecommendAgentsUseCase: GetRecommendAgentsUseCase by lazy {
        GetRecommendAgentsUseCase(_exploreRepository)
    }

    // Repository accessors
    fun getChatRepository(): ChatRepository = _chatRepository

    fun getAgentRepository(): AgentRepository = _agentRepository

    fun getExploreRepository(): ExploreRepository = _exploreRepository

    // Cache provider setters
    fun setAgentCacheProvider(cacheProvider: AgentCacheProvider) {
        _agentCacheProvider = cacheProvider
    }

    fun setRecommendedCacheProvider(cacheProvider: RecommendedAgentCacheProvider) {
        _recommendedCacheProvider = cacheProvider
    }
}
