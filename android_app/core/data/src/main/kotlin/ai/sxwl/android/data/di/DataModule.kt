package ai.sxwl.android.data.di

import ai.sxwl.android.data.agent.domain.AgentRepository
import ai.sxwl.android.data.agent.domain.GetChatAgentsUseCase
import ai.sxwl.android.data.agent.repository.AgentRepositoryImpl
import ai.sxwl.android.data.cache.AgentCacheProvider
import ai.sxwl.android.data.cache.RecommendedAgentCacheProvider
import ai.sxwl.android.data.character.repository.CharacterRepository
import ai.sxwl.android.data.chat.data.ChatRemoteDataSource
import ai.sxwl.android.data.chat.data.RoomDataSource
import ai.sxwl.android.data.chat.domain.ChatRepository
import ai.sxwl.android.data.chat.domain.GenerateImageUseCase
import ai.sxwl.android.data.chat.repository.RoomImpl

/** 数据层依赖注入管理 遵循Clean Architecture的依赖注入模式 不使用Hilt，采用手动依赖注入 */
object DataModule {
    // Data Sources
    private val _roomDataSource: RoomDataSource by lazy { RoomDataSource() }
    private val _chatRemoteDataSource: ChatRemoteDataSource by lazy { ChatRemoteDataSource() }

    // Cache Providers (injected from app module)
    private var _agentCacheProvider: AgentCacheProvider? = null
    private var _recommendedCacheProvider: RecommendedAgentCacheProvider? = null

    // Repositories
    private val _chatRepository: ChatRepository by lazy {
        RoomImpl(_roomDataSource, _chatRemoteDataSource)
    }

    private val _characterRepository: CharacterRepository by lazy { CharacterRepository() }

    private val _agentRepository: AgentRepository by lazy {
        AgentRepositoryImpl(_agentCacheProvider)
    }

    val generateImageUseCase: GenerateImageUseCase by lazy { GenerateImageUseCase(_chatRepository) }

    val getChatAgentsUseCase: GetChatAgentsUseCase by lazy {
        GetChatAgentsUseCase(_agentRepository)
    }

    fun getChatRepository(): ChatRepository = _chatRepository

    fun getRoomDataSource(): RoomDataSource = _roomDataSource

    fun getCharacterRepository(): CharacterRepository = _characterRepository

    fun setAgentCacheProvider(cacheProvider: AgentCacheProvider) {
        _agentCacheProvider = cacheProvider
    }

    fun setRecommendedCacheProvider(cacheProvider: RecommendedAgentCacheProvider) {
        _recommendedCacheProvider = cacheProvider
    }
}
