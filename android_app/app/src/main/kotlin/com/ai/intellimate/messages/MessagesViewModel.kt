package com.ai.intellimate.messages

import ai.sxwl.android.common.analytics.PageTrackingHelper
import ai.sxwl.android.common.base.BaseVM
import ai.sxwl.android.common.event.EventBus
import ai.sxwl.android.common.event.EventSubscriber
import ai.sxwl.android.common.event.PushNotificationEvent
import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.AgentConstants
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.api.model.ConversationItem
import ai.sxwl.android.data.character.repository.CharacterRepository
import ai.sxwl.android.data.chat.ChatMessageCountStore
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.firebase.FCMConstants
import ai.sxwl.android.utils.LogUtils
import androidx.lifecycle.viewModelScope
import com.ai.intellimate.utils.AgentCacheManager
import com.architecture.httplib.core.HttpResult
import java.util.Locale
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** Messages页面ViewModel 负责管理会话列表的状态和业务逻辑 */
class MessagesViewModel : BaseVM() {
    // UI状态
    private val _uiState = MutableStateFlow(MessagesUiState())
    val uiState = _uiState.asStateFlow()

    // 对话列表分页状态
    private var currentConversationsPage = 0
    private var hasMoreConversations = true

    // 页面跟踪上下文名称（默认为当前类名，可在外部设置）
    private var pageTrackingContext: String = "MessagesViewModel"

    // IntelliMate agent 缓存（只在启动时加载一次，避免频繁调用网络接口）
    private var cachedIntelliMateAgent: ConversationItem? = null
    private var intelliMateAgentLoaded = false // 标记是否已尝试加载过

    // CharacterRepository用于从Room数据库查询agents
    private val characterRepository = CharacterRepository()

    private val _selectedTab = MutableStateFlow(MessageSecondaryTab.Conversations)
    internal val selectedTab = _selectedTab.asStateFlow()

    // 收藏列表缓存：保存上一次的收藏ID列表和对应的agents
    // 使用 Set 进行比较，避免顺序问题；使用 @Volatile 确保可见性
    @Volatile private var cachedFavoriteIdsSet: Set<String> = emptySet()
    private var cachedFavoriteAgents: List<AgentInfo> = emptyList()
    private val pushMessageSubscriber =
        object : EventSubscriber<PushNotificationEvent.MessageReceived> {
            override fun onEvent(event: PushNotificationEvent.MessageReceived) {
                handlePushMessageEvent(event)
            }
        }

    init {
        // 页面跟踪
        trackPageView()
        // 启动时加载 IntelliMate agent（只调用一次）
        loadIntelliMateAgentOnce()
        subscribePushEvents()
    }

    private fun subscribePushEvents() {
        EventBus.subscribe(PushNotificationEvent.MessageReceived::class, pushMessageSubscriber)
    }

    private fun handlePushMessageEvent(event: PushNotificationEvent.MessageReceived) {
        if (event.type != FCMConstants.TYPE_AGENT_MESSAGE) return
        val agentId = event.data[FCMConstants.DATA_KEY_AGENT_ID]
        if (agentId.isNullOrBlank()) return
        viewModelScope.launch(Dispatchers.Main) { markConversationHasPush(agentId) }
    }

    internal fun setSelectedTab(tab: MessageSecondaryTab) {
        _selectedTab.value = tab
    }

    /** 加载用户收藏的角色列表（仅从本地数据源，不发起网络请求） */
    fun loadFavoriteAgents() {
        viewModelScope.launch(Dispatchers.IO) {
            _uiState.update { it.copy(isLoadingFavorites = true) }
            try {
                val favoriteIds = IntySetting.getExploreFavoriteAgentIds()
                val favoriteIdsSet = favoriteIds.toSet()
                if (favoriteIds.isEmpty()) {
                    cachedFavoriteIdsSet = emptySet()
                    cachedFavoriteAgents = emptyList()
                    _uiState.update { it.copy(favoriteAgents = emptyList()) }
                    return@launch
                }

                // 检查收藏ID列表是否变化，如果没变化且已有缓存，直接使用
                // 使用 Set 比较，避免顺序问题
                if (favoriteIdsSet == cachedFavoriteIdsSet && cachedFavoriteAgents.isNotEmpty()) {
                    _uiState.update { it.copy(favoriteAgents = cachedFavoriteAgents) }
                    return@launch
                }

                val agentMap = LinkedHashMap<String, AgentInfo>()

                fun collectAgents(source: List<AgentInfo>) {
                    source.forEach { agent ->
                        // 确保 agent.id 不为空且存在于收藏列表中
                        if (agent.id.isNotBlank() && agent.id in favoriteIdsSet) {
                            agentMap[agent.id] = agent
                        }
                    }
                }

                // 优先级1: 从AgentCacheManager查找（内存缓存，最快）
                collectAgents(AgentCacheManager.getCachedAgents())
                collectAgents(AgentCacheManager.getCachedChatAgents())
                collectAgents(AgentCacheManager.getCachedUserCreatedAgents())

                // 优先级2: 从CharacterRepository（Room数据库）批量查询缺失的agents
                val missingIds = favoriteIds.filterNot { agentMap.containsKey(it) }
                if (missingIds.isNotEmpty()) {
                    try {
                        val agentsFromDb = characterRepository.getAgentsByIds(missingIds)
                        agentsFromDb.forEach { agent ->
                            // 确保 agent.id 不为空且存在于收藏列表中
                            if (agent.id.isNotBlank() && agent.id in favoriteIdsSet) {
                                agentMap[agent.id] = agent
                            }
                        }
                    } catch (e: Exception) {
                        LogUtils.e("MessagesViewModel - 从Room数据库查询收藏agents失败: ${e.message}")
                    }
                }

                // 对于本地找不到的agent，直接跳过，不显示（不发起网络请求）
                val orderedAgents =
                    if (agentMap.isEmpty()) {
                        emptyList()
                    } else {
                        val ordered = favoriteIds.mapNotNull { agentMap[it] }
                        if (ordered.isNotEmpty()) ordered
                        else
                            agentMap.values.sortedBy {
                                // 处理空字符串情况，确保排序稳定
                                it.name.takeIf { it.isNotBlank() }?.lowercase(Locale.getDefault())
                                    ?: ""
                            }
                    }

                // 更新缓存（使用 Set 避免顺序问题）
                cachedFavoriteIdsSet = favoriteIdsSet
                cachedFavoriteAgents = orderedAgents

                _uiState.update { it.copy(favoriteAgents = orderedAgents) }
            } finally {
                _uiState.update { it.copy(isLoadingFavorites = false) }
            }
        }
    }

    /**
     * 跟踪页面访问
     *
     * @param contextName 上下文名称，默认为 "MessagesViewModel"
     */
    fun trackPageView(contextName: String = "MessagesViewModel") {
        pageTrackingContext = contextName
        val currentState = _uiState.value
        PageTrackingHelper.trackPageView(
            "MessagesPage",
            contextName,
            mapOf(
                "conversation_count" to currentState.conversations.size,
                "is_loading" to currentState.isLoading,
            ),
        )
    }

    /** 获取会话列表（首次加载或刷新） */
    fun getConversations() {
        currentConversationsPage = 0
        hasMoreConversations = true

        // 如果已经有数据，则不显示loading，直接后台刷新
        if (_uiState.value.conversations.isNotEmpty()) {
            loadConversationsSilently()
        } else {
            // 没有数据时才显示loading
            loadConversations()
        }
    }

    /** 加载更多会话 */
    fun loadMoreConversations() {
        val currentState = _uiState.value
        if (!currentState.isLoading && hasMoreConversations) {
            currentConversationsPage++
            loadConversations()
        } else {
            LogUtils.d(
                "loadMoreConversations - 跳过加载: isLoading=${currentState.isLoading}, hasMoreData=$hasMoreConversations"
            )
        }
    }

    /** 静默加载会话（后台刷新，不显示loading） */
    private fun loadConversationsSilently() {
        val currentState = _uiState.value
        if (currentState.isLoading || currentState.isRefreshing) return

        viewModelScope.launch(Dispatchers.IO) {
            try {
                val skip = currentConversationsPage * 20
                val result = NetServiceMgr.getChatApi().getConversations(skip, 20)

                when (result) {
                    is HttpResult.Success -> {
                        val userInitiatedConversations = result.data

                        if (userInitiatedConversations.isEmpty()) {
                            hasMoreConversations = false
                        } else {
                            // 应用 Pin/Hide 逻辑：排序和过滤（包含 IntelliMate agent）
                            val (processedConversations, intelliMateAgentIds) =
                                processConversationsWithPinHide(userInitiatedConversations)
                            // 静默更新数据，不显示loading
                            _uiState.update {
                                copyWithConversations(
                                    baseState = it,
                                    conversations = processedConversations,
                                    intelliMateAgentIds = intelliMateAgentIds,
                                )
                            }
                            refreshIntimateMessageCounts(processedConversations)
                        }
                    }

                    is HttpResult.Failure -> {
                        LogUtils.e(
                            "loadConversationsSilently - 第${currentConversationsPage + 1}页加载失败: ${result.message}"
                        )
                    }
                }
            } catch (e: Exception) {
                LogUtils.e(
                    "loadConversationsSilently - 第${currentConversationsPage + 1}页加载异常: ${e.message}"
                )
            }
        }
    }

    /** 加载会话列表（显示loading） */
    private fun loadConversations() {
        val currentState = _uiState.value
        if (currentState.isLoading || currentState.isRefreshing) return

        // 记录当前页码，用于后续状态重置
        val isFirstPage = currentConversationsPage == 0

        // 根据当前页码决定使用哪个loading状态
        if (isFirstPage) {
            // 第一页，使用刷新状态
            _uiState.update { it.copy(isRefreshing = true) }
        } else {
            // 后续页，使用加载更多状态
            _uiState.update { it.copy(isLoading = true) }
        }

        viewModelScope.launch(Dispatchers.IO) {
            try {
                val skip = currentConversationsPage * 20
                val result = NetServiceMgr.getChatApi().getConversations(skip, 20)

                when (result) {
                    is HttpResult.Success -> {
                        val userInitiatedConversations = result.data

                        if (userInitiatedConversations.isEmpty()) {
                            hasMoreConversations = false
                        } else {
                            // 应用 Pin/Hide 逻辑：排序和过滤（包含 IntelliMate agent）
                            val (processedConversations, intelliMateAgentIds) =
                                processConversationsWithPinHide(userInitiatedConversations)

                            if (currentConversationsPage == 0) {
                                // 第一页，直接替换
                                _uiState.update {
                                    copyWithConversations(
                                        baseState = it,
                                        conversations = processedConversations,
                                        intelliMateAgentIds = intelliMateAgentIds,
                                    )
                                }
                                refreshIntimateMessageCounts(processedConversations)
                            } else {
                                // 后续页，追加到现有列表（需要重新处理整个列表以保持排序）
                                val currentConversations = _uiState.value.conversations
                                val allConversations =
                                    currentConversations + userInitiatedConversations
                                val (allProcessed, allIntelliMateAgentIds) =
                                    processConversationsWithPinHide(allConversations)
                                _uiState.update {
                                    copyWithConversations(
                                        baseState = it,
                                        conversations = allProcessed,
                                        intelliMateAgentIds = allIntelliMateAgentIds,
                                    )
                                }
                                refreshIntimateMessageCounts(allProcessed)
                            }
                        }
                    }

                    is HttpResult.Failure -> {
                        LogUtils.e(
                            "loadConversations - 第${currentConversationsPage + 1}页加载失败: ${result.message}"
                        )
                        // 如果加载失败，回退页码
                        if (currentConversationsPage > 0) {
                            currentConversationsPage--
                            LogUtils.i("loadConversations - 页码回退到: $currentConversationsPage")
                        }
                    }
                }
            } catch (e: Exception) {
                LogUtils.e(
                    "loadConversations - 第${currentConversationsPage + 1}页加载异常: ${e.message}"
                )
                // 如果加载失败，回退页码
                if (currentConversationsPage > 0) {
                    currentConversationsPage--
                    LogUtils.i("loadConversations - 页码回退到: $currentConversationsPage")
                }
            }

            // 重置对应的loading状态
            _uiState.update { currentState ->
                if (isFirstPage) {
                    currentState.copy(isRefreshing = false)
                } else {
                    currentState.copy(isLoading = false)
                }
            }
        }
    }

    private fun refreshIntimateMessageCounts(conversations: List<ConversationItem>) {
        viewModelScope.launch(Dispatchers.IO) {
            val agentIds = conversations.map { it.agentId }.filter { it.isNotBlank() }.distinct()
            if (agentIds.isEmpty()) {
                _uiState.update { it.copy(intimateMessageCounts = emptyMap()) }
                return@launch
            }

            val completed =
                runCatching { ChatMessageCountStore.getMessageCounts(agentIds) }
                    .onFailure { e -> LogUtils.w("MessagesViewModel - 读取本地消息条数失败: ${e.message}") }
                    .getOrNull()
                    .orEmpty()
            _uiState.update { it.copy(intimateMessageCounts = completed) }
        }
    }

    /** 启动时加载 IntelliMate agent（只调用一次） */
    private fun loadIntelliMateAgentOnce() {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                // 首先从缓存中查找
                val cachedAgents = AgentCacheManager.getCachedAgents()
                var intelliMateAgent: AgentInfo? =
                    cachedAgents.firstOrNull { agent ->
                        AgentConstants.isIntelliMateAgent(agent.id, agent.name)
                    }

                // 如果缓存中没有找到，尝试从网络请求获取（只调用一次）
                if (intelliMateAgent == null && !intelliMateAgentLoaded) {
                    LogUtils.i("MessagesViewModel - 缓存中未找到 IntelliMate agent，从网络获取（启动时只调用一次）")
                    intelliMateAgentLoaded = true // 标记已尝试加载
                    try {
                        // 尝试通过 ID 获取
                        val agentResult =
                            NetServiceMgr.getChatApi()
                                .getAgentInfo(AgentConstants.INTELLIMATE_AGENT_ID)
                        when (agentResult) {
                            is HttpResult.Success -> {
                                val agent = agentResult.data
                                if (AgentConstants.isIntelliMateAgent(agent.id, agent.name)) {
                                    intelliMateAgent = agent
                                    LogUtils.i(
                                        "MessagesViewModel - 从网络获取 IntelliMate agent 成功: ${agent.id}_${agent.name}"
                                    )
                                }
                            }

                            is HttpResult.Failure -> {
                                LogUtils.w(
                                    "MessagesViewModel - 从网络获取 IntelliMate agent 失败: ${agentResult.message}"
                                )
                            }
                        }
                    } catch (e: Exception) {
                        LogUtils.e("MessagesViewModel - 从网络获取 IntelliMate agent 异常: ${e.message}")
                    }
                } else if (intelliMateAgent != null) {
                    LogUtils.i(
                        "MessagesViewModel - 从缓存获取 IntelliMate agent 成功: ${intelliMateAgent.id}_${intelliMateAgent.name}"
                    )
                }

                // 缓存转换后的 ConversationItem
                val conversationItem = intelliMateAgent?.toConversationItem()
                cachedIntelliMateAgent = conversationItem

                // 确保 IntelliMate agent 默认置顶
                conversationItem?.let {
                    if (!IntySetting.isConversationPinned(it.agentId)) {
                        IntySetting.setConversationPinned(it.agentId, true)
                        LogUtils.i("MessagesViewModel - 设置 IntelliMate agent 默认置顶: ${it.agentId}")
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("MessagesViewModel - 加载 IntelliMate agent 失败: ${e.message}")
            }
        }
    }

    /** 获取 IntelliMate agent 并转换为 ConversationItem（使用缓存，不频繁调用网络） */
    private suspend fun getIntelliMateAgentAsConversation(): List<ConversationItem> {
        // 如果已有缓存，重新创建 ConversationItem 以确保 isPinned 状态是最新的
        val cached = cachedIntelliMateAgent
        if (cached != null) {
            // 重新创建 ConversationItem 以确保 isPinned 等计算属性能获取最新值
            return listOf(
                ConversationItem(
                    agentId = cached.agentId,
                    agentName = cached.agentName,
                    agentAvatar = cached.agentAvatar,
                    agentBackground = cached.agentBackground,
                    agentBackgroundAnimated = cached.agentBackgroundAnimated,
                    agentIntro = cached.agentIntro,
                    agentOpening = cached.agentOpening,
                    agentOpeningAudioUrl = cached.agentOpeningAudioUrl,
                    createdAt = cached.createdAt,
                    id = cached.id,
                    lastMessage = cached.lastMessage,
                    lastMessageTime = cached.lastMessageTime,
                    settings = cached.settings,
                    updatedAt = cached.updatedAt,
                    userId = cached.userId,
                    isDeleted = cached.isDeleted,
                )
            )
        }

        // 如果缓存为空，尝试从 AgentCacheManager 获取（不发起网络请求）
        return try {
            val cachedAgents = AgentCacheManager.getCachedAgents()
            val intelliMateAgents =
                cachedAgents.filter { agent ->
                    AgentConstants.isIntelliMateAgent(agent.id, agent.name)
                }
            intelliMateAgents.map { agent -> agent.toConversationItem() }
        } catch (e: Exception) {
            LogUtils.e("MessagesViewModel - 获取 IntelliMate agent 失败: ${e.message}")
            emptyList()
        }
    }

    /** AgentInfo 转换为 ConversationItem 的扩展方法 */
    private fun AgentInfo.toConversationItem(): ConversationItem {
        return ConversationItem(
            agentId = this.id,
            agentName = this.name,
            agentAvatar = this.avatar,
            agentBackground = this.background,
            agentBackgroundAnimated = this.backgroundAnimatedUrl,
            agentIntro = this.intro,
            agentOpening = this.opening,
            agentOpeningAudioUrl = this.opening_audio_url,
            createdAt = this.createdAt,
            id = "", // IntelliMate agent 没有实际的 conversation id
            lastMessage = this.opening, // 使用 opening 作为 last message
            lastMessageTime = this.createdAt, // 使用创建时间作为最后消息时间
            settings = null,
            updatedAt = null,
            userId = "",
            isDeleted = this.isDeleted,
        )
    }

    /** 处理会话列表：排序（IntelliMate在前，Pin在前）和过滤（隐藏的移除，除非有新消息） */
    private suspend fun processConversationsWithPinHide(
        rawConversations: List<ConversationItem>
    ): Pair<List<ConversationItem>, Set<String>> {
        // 获取 IntelliMate agent
        val intelliMateAgents = getIntelliMateAgentAsConversation()
        val intelliMateAgentIds = intelliMateAgents.map { it.agentId }.toSet()

        // 获取用户已聊过的 agent IDs（从 rawConversations 中提取）
        val userChattedAgentIds = rawConversations.map { it.agentId }.toSet()

        // 只显示用户未聊过的 IntelliMate agent
        val intelliMateAgentsToShow =
            intelliMateAgents.filter { it.agentId !in userChattedAgentIds }

        // 过滤普通会话：隐藏的会话（除非有新消息）
        val regularConversations =
            rawConversations.filter { conversation ->
                // 过滤隐藏的会话，除非有新消息
                !conversation.isHidden || conversation.shouldShow()
            }

        // 合并 IntelliMate agent 和普通会话
        val allConversations = intelliMateAgentsToShow + regularConversations

        // 排序逻辑：
        // 1. 如果 IntelliMate agent 是 pinned 的，它排在最前面
        // 2. 否则，按照 pin 状态排序（pinned 在前），然后按时间排序
        // 3. unpinned 的 IntelliMate agent 和普通 item 一样参与排序
        val sortedConversations =
            allConversations.sortedWith(
                compareBy<ConversationItem> { conversation ->
                        val isIntelliMate = conversation.agentId in intelliMateAgentIds
                        // 如果 IntelliMate 是 pinned，排在最前面（优先级最高）
                        if (isIntelliMate && conversation.isPinned) {
                            0
                        } else if (conversation.isPinned) {
                            // 其他 pinned 的 item 排在第二优先级
                            1
                        } else {
                            // unpinned 的 item（包括 unpinned 的 IntelliMate）排在最后
                            2
                        }
                    }
                    .thenBy { conversation ->
                        // 在相同优先级内，IntelliMate 优先（仅当都是 pinned 时）
                        val isIntelliMate = conversation.agentId in intelliMateAgentIds
                        if (conversation.isPinned && isIntelliMate) {
                            0
                        } else {
                            1
                        }
                    }
                    .thenByDescending { conversation ->
                        // 最后按时间排序
                        ai.sxwl.android.utils.TimeUtils.parseIsoTimeToTimestamp(
                            conversation.lastMessageTime
                        ) ?: 0L
                    }
            )

        // 返回排序后的会话列表和 IntelliMate agent IDs
        return Pair(sortedConversations, intelliMateAgentIds)
    }

    fun clearConversationPush(agentId: String) {
        if (agentId.isBlank()) return
        viewModelScope.launch(Dispatchers.Main) {
            IntySetting.setConversationHasPushSuspend(agentId, false)
            _uiState.update { it.copy(pushAgentIds = it.pushAgentIds - agentId) }
        }
    }

    private fun markConversationHasPush(agentId: String) {
        viewModelScope.launch(Dispatchers.Main) {
            IntySetting.setConversationHasPushSuspend(agentId, true)
            _uiState.update { it.copy(pushAgentIds = it.pushAgentIds + agentId) }
        }
    }

    private fun syncPushAgentIds(conversations: List<ConversationItem>): Set<String> {
        if (conversations.isEmpty()) return emptySet()
        return conversations
            .mapNotNull { conversation ->
                val agentId = conversation.agentId
                if (agentId.isNotBlank() && IntySetting.hasConversationPush(agentId)) agentId
                else null
            }
            .toSet()
    }

    private fun copyWithConversations(
        baseState: MessagesUiState,
        conversations: List<ConversationItem>,
        intelliMateAgentIds: Set<String>,
    ): MessagesUiState {
        val pushAgentIds = syncPushAgentIds(conversations)
        return baseState.copy(
            conversations = conversations,
            intelliMateAgentIds = intelliMateAgentIds,
            pushAgentIds = pushAgentIds,
        )
    }

    /** 置顶会话 */
    fun pinConversation(agentId: String) {
        viewModelScope.launch(Dispatchers.Main) {
            IntySetting.setConversationPinned(agentId, true)
            refreshConversationsWithPinHide()
        }
    }

    /** 取消置顶 */
    fun unpinConversation(agentId: String) {
        viewModelScope.launch(Dispatchers.Main) {
            IntySetting.setConversationPinned(agentId, false)
            refreshConversationsWithPinHide()
        }
    }

    /** 隐藏会话 */
    fun hideConversation(agentId: String) {
        viewModelScope.launch(Dispatchers.Main) {
            IntySetting.setConversationHidden(agentId, true)
            refreshConversationsWithPinHide()
        }
    }

    /** 取消隐藏 */
    fun unhideConversation(agentId: String) {
        viewModelScope.launch(Dispatchers.Main) {
            IntySetting.setConversationHidden(agentId, false)
            refreshConversationsWithPinHide()
        }
    }

    /** 刷新会话列表（应用Pin/Hide逻辑） */
    private suspend fun refreshConversationsWithPinHide() {
        // 获取当前原始会话列表（不包含 IntelliMate agent，因为它会在 processConversationsWithPinHide 中添加）
        val currentRawConversations =
            _uiState.value.conversations.filter { conversation ->
                !AgentConstants.isIntelliMateAgent(conversation.agentId, conversation.agentName)
            }

        // 重新创建所有 ConversationItem 以确保 isPinned 等计算属性能获取最新值
        val refreshedRawConversations =
            currentRawConversations.map { conv ->
                ConversationItem(
                    agentId = conv.agentId,
                    agentName = conv.agentName,
                    agentAvatar = conv.agentAvatar,
                    agentBackground = conv.agentBackground,
                    agentBackgroundAnimated = conv.agentBackgroundAnimated,
                    agentIntro = conv.agentIntro,
                    agentOpening = conv.agentOpening,
                    agentOpeningAudioUrl = conv.agentOpeningAudioUrl,
                    createdAt = conv.createdAt,
                    id = conv.id,
                    lastMessage = conv.lastMessage,
                    lastMessageTime = conv.lastMessageTime,
                    settings = conv.settings,
                    updatedAt = conv.updatedAt,
                    userId = conv.userId,
                    isDeleted = conv.isDeleted,
                )
            }

        val (processedConversations, intelliMateAgentIds) =
            processConversationsWithPinHide(refreshedRawConversations)

        // 使用 withContext 确保在主线程更新 UI StateFlow
        withContext(Dispatchers.Main) {
            // 直接更新 StateFlow，确保 UI 立即刷新
            // 使用 refreshKey 强制 Compose 重新组合所有 item
            val updatedState =
                copyWithConversations(
                    baseState = _uiState.value,
                    conversations = processedConversations,
                    intelliMateAgentIds = intelliMateAgentIds,
                )
            _uiState.value =
                updatedState.copy(
                    refreshKey = System.currentTimeMillis() // 更新 refreshKey 强制刷新
                )
        }
        refreshIntimateMessageCounts(processedConversations)
    }

    /** 检查是否有新消息，自动取消隐藏 */
    fun checkAndUnhideConversations() {
        viewModelScope.launch(Dispatchers.Main) {
            val currentConversations = _uiState.value.conversations
            var needRefresh = false

            currentConversations.forEach { conversation ->
                if (conversation.isHidden && conversation.shouldShow()) {
                    // 有新消息，自动取消隐藏
                    IntySetting.setConversationHidden(conversation.agentId, false)
                    needRefresh = true
                }
            }

            if (needRefresh) {
                refreshConversationsWithPinHide()
            }
        }
    }

    override fun onCleared() {
        EventBus.unsubscribe(PushNotificationEvent.MessageReceived::class, pushMessageSubscriber)
        super.onCleared()
    }

    /** 清理所有数据 */
    fun clearAllData() {
        currentConversationsPage = 0
        hasMoreConversations = true
        _uiState.value = MessagesUiState()
        // 注意：不清理 cachedIntelliMateAgent，因为它是启动时加载的，应该保持
    }

    /** 刷新 IntelliMate agent 显示（如果缓存中没有，等待启动时加载完成） */
    fun refreshIntelliMateAgentIfNeeded() {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                // 如果缓存为空，等待启动时加载完成（最多等待 2 秒）
                if (cachedIntelliMateAgent == null) {
                    var waitCount = 0
                    while (cachedIntelliMateAgent == null && waitCount < 20) {
                        kotlinx.coroutines.delay(100)
                        waitCount++
                    }
                }

                // 重新处理会话列表，使用缓存的 IntelliMate agent
                val currentConversations = _uiState.value.conversations
                val hasIntelliMateInList =
                    currentConversations.any {
                        AgentConstants.isIntelliMateAgent(it.agentId, it.agentName)
                    }
                if (!hasIntelliMateInList && cachedIntelliMateAgent != null) {
                    val (processedConversations, intelliMateAgentIds) =
                        processConversationsWithPinHide(currentConversations)
                    _uiState.update {
                        copyWithConversations(
                            baseState = it,
                            conversations = processedConversations,
                            intelliMateAgentIds = intelliMateAgentIds,
                        )
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("MessagesViewModel - refreshIntelliMateAgentIfNeeded 异常: ${e.message}")
            }
        }
    }
}
