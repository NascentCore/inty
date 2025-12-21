package com.ai.intellimate.explore

import ai.sxwl.android.common.analytics.PageTrackingHelper
import ai.sxwl.android.common.base.BaseVM
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.billing.VipStatusHelper
import ai.sxwl.android.data.character.repository.CharacterRepository
import ai.sxwl.android.data.http.services.AgentService
import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.utils.LogUtils
import androidx.lifecycle.viewModelScope
import androidx.paging.PagingData
import androidx.paging.cachedIn
import androidx.paging.filter
import com.ai.intellimate.utils.AgentCacheManager
import com.ai.intellimate.utils.UnifiedStartupManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.launch

/** Explore页面ViewModel 负责管理推荐agents的Paging数据流、刷新、缓存等逻辑 */
class ExploreViewModel : BaseVM(), ExploreFetchCallback {
    // 角色数据库仓库，用于搜索
    private val characterRepository = CharacterRepository()

    // 使用app层的ExplorePagingRepository替代core/data层的Repository，以支持事件回调
    // 注意：这会使用不同的缓存策略，但可以支持事件上报
    private val explorePagingRepository by lazy {
        // 创建新的cacheProvider实例，因为它使用静态的AgentCacheManager，所以新实例也可以正常工作
        val cacheProvider =
            try {
                // RecommendedAgentCacheProviderImpl 使用静态的 AgentCacheManager，所以创建新实例是安全的
                com.ai.intellimate.utils.RecommendedAgentCacheProviderImpl()
            } catch (e: Exception) {
                LogUtils.e("ExploreViewModel - 创建cacheProvider失败: ${e.message}")
                null
            }
        ExplorePagingRepository(cacheProvider = cacheProvider, fetchCallback = this)
    }

    // Paging数据流
    private val _agentsFlow = MutableStateFlow<Flow<PagingData<AgentInfo>>?>(null)

    // 是否已初始化
    private var isInitialized = false

    // 保存滚动位置（保存的是网格索引，可以区分theme项和agent项）
    private val _savedFirstVisibleGridIndex = MutableStateFlow(0)
    val savedFirstVisibleGridIndex = _savedFirstVisibleGridIndex
    private val _savedFirstVisibleOffset = MutableStateFlow(0)
    val savedFirstVisibleOffset = _savedFirstVisibleOffset

    // 当前UI中显示的agents总数
    private val _currentUiAgentsCount = MutableStateFlow(0)
    val currentUiAgentsCount = _currentUiAgentsCount

    // 主题专区列表（最多显示两个）
    private val _characterThemes =
        MutableStateFlow<List<AgentService.CharacterThemeItem>>(emptyList())
    val characterThemes: StateFlow<List<AgentService.CharacterThemeItem>> =
        _characterThemes.asStateFlow()

    // 是否正在加载主题专区
    private val _isLoadingThemes = MutableStateFlow(false)
    val isLoadingThemes: StateFlow<Boolean> = _isLoadingThemes.asStateFlow()

    // 缓存是否已加载完成（用于避免竞态条件）
    private val _isCacheLoaded = MutableStateFlow(false)
    val isCacheLoaded: StateFlow<Boolean> = _isCacheLoaded.asStateFlow()

    // 搜索相关状态
    private val _searchResults = MutableStateFlow<List<AgentInfo>>(emptyList())
    val searchResults: StateFlow<List<AgentInfo>> = _searchResults.asStateFlow()

    private val _isSearching = MutableStateFlow(false)
    val isSearching: StateFlow<Boolean> = _isSearching.asStateFlow()

    private val _hasSearchExecuted = MutableStateFlow(false)
    val hasSearchExecuted: StateFlow<Boolean> = _hasSearchExecuted.asStateFlow()

    private enum class ExploreSearchMode {
        Name,
        Tag,
    }

    private data class ParsedExploreSearch(val mode: ExploreSearchMode, val query: String)

    // 实现 ExploreFetchCallback 接口
    override suspend fun onSuccess(
        page: Int,
        pageSize: Int,
        responseTime: Long,
        agentsCount: Int,
        sortSeed: Int,
    ) {
        reportExploreFetchSuccess(page, pageSize, responseTime, agentsCount, sortSeed)
    }

    override suspend fun onFailure(
        page: Int,
        pageSize: Int,
        responseTime: Long,
        errorMessage: String,
        sortSeed: Int,
    ) {
        reportExploreFetchError(
            page = page,
            pageSize = pageSize,
            responseTime = responseTime,
            errorType = "failure",
            errorMessage = errorMessage,
            errorException = null,
            sortSeed = sortSeed,
        )
    }

    override suspend fun onException(
        page: Int,
        pageSize: Int,
        responseTime: Long,
        exception: Exception,
        sortSeed: Int,
    ) {
        reportExploreFetchError(
            page = page,
            pageSize = pageSize,
            responseTime = responseTime,
            errorType = "exception",
            errorMessage = exception.message ?: "unknown",
            errorException = exception,
            sortSeed = sortSeed,
        )
    }

    /** 初始化Paging数据流 */
    fun initializePagingData() {
        if (isInitialized) return

        // Firebase Analytics - 记录探索页面访问（使用 SCREEN_VIEW 事件）
        PageTrackingHelper.trackPageView(pageName = "ExplorePage", pageClass = "ExploreViewModel")

        // 使用app层的ExplorePagingRepository，支持事件回调
        val initialFlow =
            explorePagingRepository
                .getRecommendAgentsFlow(useCache = true)
                .map { pagingData ->
                    // 分页会导致不同页面可能存在相同agent，临时去重解决方案，更好的解决方式需要重构整个流程，从根源上去重
                    val agentIds = mutableSetOf<String>()

                    pagingData.filter { item ->
                        if (agentIds.contains(item.id)) {
                            false // 过滤重复
                        } else {
                            agentIds.add(item.id)
                            true
                        }
                    }
                }
                .cachedIn(viewModelScope)

        _agentsFlow.value = initialFlow
        isInitialized = true

        // 初始化时从缓存加载主题专区数据，确保快速显示
        loadCharacterThemesFromCache()
    }

    /** 获取推荐agents的Paging数据流 */
    fun getRecommendAgentsFlow(): Flow<PagingData<AgentInfo>>? {
        if (!isInitialized) {
            initializePagingData()
        }
        return _agentsFlow.value
    }

    /** 强制刷新推荐agents：先清空数据，再加载新数据（更新sort seed） */
    fun refreshRecommendAgents() {
        viewModelScope.launch {
            try {
                // 先清空数据，显示空页面，等待新数据
                _agentsFlow.value = null

                // 使用刷新方法，会更新sort seed并禁用缓存
                val refreshFlow =
                    explorePagingRepository.refreshRecommendAgents().cachedIn(viewModelScope)

                _agentsFlow.value = refreshFlow
            } catch (e: Exception) {
                LogUtils.e("ExploreViewModel - refreshRecommendAgents异常: ${e.message}")
            }
        }
    }

    /**
     * 保存滚动位置
     *
     * @param gridIndex 网格索引（LazyVerticalGrid 的索引，从 0 开始，包括theme项和agent项）
     * @param offset 滚动偏移量
     */
    fun saveScrollPosition(gridIndex: Int, offset: Int) {
        _savedFirstVisibleGridIndex.value = gridIndex
        _savedFirstVisibleOffset.value = offset
    }

    /**
     * 获取恢复滚动位置时的网格索引
     *
     * @param currentThemeItemCount 当前主题项数量（用于向后兼容，如果保存的是旧格式的agent索引）
     * @return 网格索引（用于 LazyVerticalGrid 的 initialFirstVisibleItemIndex）
     */
    fun getRestoredGridIndex(currentThemeItemCount: Int): Int {
        // 直接返回保存的网格索引
        // 如果没有保存位置（默认是0），会显示第一个item（theme或agent）
        return _savedFirstVisibleGridIndex.value
    }

    /** 更新当前UI中显示的agents总数 */
    fun updateCurrentUiAgentsCount(count: Int) {
        _currentUiAgentsCount.value = count
    }

    /** 上报Explore接口请求成功事件 */
    fun reportExploreFetchSuccess(
        page: Int,
        pageSize: Int,
        responseTime: Long,
        agentsCount: Int,
        sortSeed: Int,
    ) {
        viewModelScope.launch {
            FirebaseManager.logEvent(
                FirebaseManager.Events.EXPLORE_AGENTS_FETCH_SUCCESS,
                FirebaseManager.safeEventParams(
                    "page" to page,
                    "page_size" to pageSize,
                    "response_time" to responseTime,
                    "agents_count" to agentsCount,
                    "current_ui_agents_count" to _currentUiAgentsCount.value,
                    "sort_seed" to sortSeed,
                    "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                    "timestamp" to System.currentTimeMillis(),
                ),
            )

            // 记录Explore接口响应时间性能指标
            FirebaseManager.logPerformanceMetric(
                FirebaseManager.Events.EXPLORE_RESPONSE_TIME,
                responseTime,
                "ms",
                FirebaseManager.safeEventParams(
                    "page" to page,
                    "page_size" to pageSize,
                    "agents_count" to agentsCount,
                    "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                ),
            )
        }
    }

    /** 上报Explore接口请求错误事件（合并 failure 和 exception） */
    fun reportExploreFetchError(
        page: Int,
        pageSize: Int,
        responseTime: Long,
        errorType: String, // "failure" 或 "exception"
        errorMessage: String,
        errorException: Exception? = null, // 异常时提供
        sortSeed: Int,
    ) {
        viewModelScope.launch {
            // 构建完整的错误消息，包含错误类型和异常类型信息
            val fullErrorMessage =
                if (errorException != null) {
                    "$errorType: ${errorException.javaClass.simpleName}, $errorMessage"
                } else {
                    "$errorType: $errorMessage"
                }

            val params =
                mutableMapOf<String, Any>(
                    "page" to page,
                    "page_size" to pageSize,
                    "response_time" to responseTime,
                    "error_message" to fullErrorMessage,
                    "current_ui_agents_count" to _currentUiAgentsCount.value,
                    "sort_seed" to sortSeed,
                    "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                    "timestamp" to System.currentTimeMillis(),
                )

            FirebaseManager.logEvent(
                FirebaseManager.Events.EXPLORE_AGENTS_FETCH_ERROR,
                FirebaseManager.safeEventParams(*params.map { (k, v) -> k to v }.toTypedArray()),
            )

            // 如果是异常，记录到Crashlytics
            errorException?.let {
                FirebaseManager.recordException(
                    it,
                    mapOf(
                        "page" to page.toString(),
                        "page_size" to pageSize.toString(),
                        "sort_seed" to sortSeed.toString(),
                    ),
                )
            }
        }
    }

    /** 监听预加载数据更新 */
    fun startListeningPreloadUpdates() {
        viewModelScope.launch {
            // 监听统一启动管理器的预加载数据更新
            UnifiedStartupManager.recommendedAgents.collect { preloadedAgents ->
                if (preloadedAgents.isEmpty()) {
                    // 监听数据清理（如用户登出）
                    clearData()
                } else if (!isInitialized) {
                    // 如果还未初始化且有预加载数据，则初始化
                    initializePagingData()
                }
            }
        }
    }

    /** 监听用户账户就绪状态，账户就绪时重新触发加载 */
    fun startListeningUserAccountReady() {
        viewModelScope.launch {
            UnifiedStartupManager.userAccountReady.collect { isReady ->
                if (isReady) {
                    if (!isInitialized) {
                        // 账户已就绪，但还未初始化，执行初始化
                        LogUtils.i("ExploreViewModel - 用户账户已就绪，初始化数据流")
                        initializePagingData()
                    } else if (_agentsFlow.value == null) {
                        // 账户已就绪，已初始化，但数据流为空，重新初始化
                        LogUtils.i("ExploreViewModel - 用户账户已就绪，数据流为空，重新初始化")
                        initializePagingData()
                    }
                    // 如果数据流已存在，说明可能正在加载或已加载成功，不需要额外操作
                }
            }
        }
    }

    /** 清空数据（用于用户登出等场景） */
    fun clearData() {
        _agentsFlow.value = null
        isInitialized = false
        _characterThemes.value = emptyList()
        _isCacheLoaded.value = false
    }

    /** 从缓存加载主题专区列表（用于快速显示） */
    private fun loadCharacterThemesFromCache() {
        viewModelScope.launch {
            try {
                val cachedThemes = AgentCacheManager.getCachedCharacterThemes()
                if (cachedThemes.isNotEmpty()) {
                    LogUtils.d("ExploreViewModel - 从缓存加载主题专区列表: ${cachedThemes.size} 条")
                    _characterThemes.value = cachedThemes
                } else {
                    LogUtils.d("ExploreViewModel - 缓存中没有主题专区数据")
                }
            } catch (e: Exception) {
                LogUtils.e("ExploreViewModel - 从缓存加载主题专区列表异常: ${e.message}", e)
            } finally {
                // 标记缓存加载已完成（无论是否有数据）
                _isCacheLoaded.value = true
            }
        }
    }

    /** 加载主题专区列表（从网络加载，并更新缓存） */
    fun loadCharacterThemes(skip: Int = 0, limit: Int = 100) {
        viewModelScope.launch {
            _isLoadingThemes.value = true
            try {
                when (val result = AgentService.getCharacterThemes(skip = skip, limit = limit)) {
                    is ai.sxwl.android.data.http.ApiResult.Success -> {
                        LogUtils.d("ExploreViewModel - 获取主题专区列表成功: ${result.data.size} 条")
                        val themes = result.data
                        _characterThemes.value = themes
                        // 更新缓存，用于下次快速显示
                        AgentCacheManager.cacheCharacterThemes(themes)
                    }
                    is ai.sxwl.android.data.http.ApiResult.Error -> {
                        // 所有异常（包括网络异常、业务错误等）都会被 IntyNetworkManager.executeRequest
                        // 捕获并转换为 ApiResult.Error，这里安全处理，不会导致崩溃
                        LogUtils.w(
                            "ExploreViewModel - 获取主题专区列表失败: code=${result.code}, message=${result.message}"
                        )
                        // 如果网络请求失败，保持缓存数据（如果有的话），不设置为空列表
                        if (_characterThemes.value.isEmpty()) {
                            _characterThemes.value = emptyList()
                        }
                    }
                }
            } catch (e: Exception) {
                // 额外的保护层，防止意外异常（虽然理论上不会发生，因为 getCharacterThemes 返回 ApiResult）
                LogUtils.e("ExploreViewModel - 加载主题专区列表异常: ${e.message}", e)
                // 如果网络请求异常，保持缓存数据（如果有的话），不设置为空列表
                if (_characterThemes.value.isEmpty()) {
                    _characterThemes.value = emptyList()
                }
            } finally {
                _isLoadingThemes.value = false
            }
        }
    }

    /** 搜索角色（从本地数据库搜索，按名称模糊匹配） */
    fun searchAgentsByName(keyword: String) {
        val parsed = parseExploreSearch(keyword)
        if (parsed == null) {
            resetSearchState()
            return
        }

        viewModelScope.launch(Dispatchers.IO) {
            _isSearching.value = true
            _hasSearchExecuted.value = true
            try {
                val dbResults =
                    when (parsed.mode) {
                        ExploreSearchMode.Name ->
                            characterRepository.searchCharactersByName(parsed.query, limit = 100)
                        ExploreSearchMode.Tag ->
                            characterRepository.searchCharactersByTag(parsed.query, limit = 100)
                    }

                LogUtils.d(
                    "ExploreViewModel - 从数据库搜索(mode=${parsed.mode}) 关键词'${parsed.query}'，找到${dbResults.size}个匹配结果"
                )

                if (dbResults.isNotEmpty()) {
                    _searchResults.value = dbResults
                    return@launch
                }

                val recommendedAgents = AgentCacheManager.getCachedAgents()
                val chatAgents = AgentCacheManager.getCachedChatAgents()
                val userCreatedAgents = AgentCacheManager.getCachedUserCreatedAgents()
                val allCachedAgents =
                    mergeAgentsUniqueById(recommendedAgents + chatAgents + userCreatedAgents)

                val cacheResults =
                    when (parsed.mode) {
                        ExploreSearchMode.Name -> filterAgentsByName(allCachedAgents, parsed.query)
                        ExploreSearchMode.Tag -> filterAgentsByTag(allCachedAgents, parsed.query)
                    }

                LogUtils.d(
                    "ExploreViewModel - 数据库无结果，从缓存搜索(mode=${parsed.mode}): " +
                        "推荐${recommendedAgents.size}个, 聊天${chatAgents.size}个, " +
                        "用户创建${userCreatedAgents.size}个, 找到${cacheResults.size}个匹配结果"
                )

                _searchResults.value = cacheResults
            } catch (e: Exception) {
                LogUtils.e("ExploreViewModel - searchAgentsByName异常: ${e.message}", e)
                _searchResults.value = emptyList()
            } finally {
                _isSearching.value = false
            }
        }
    }

    private fun parseExploreSearch(raw: String): ParsedExploreSearch? {
        val trimmed = raw.trim()
        if (trimmed.isBlank()) return null

        val normalizedPrefix =
            if (trimmed.firstOrNull() == '＃') {
                "#${trimmed.drop(1)}"
            } else {
                trimmed
            }

        if (!normalizedPrefix.startsWith("#")) {
            return ParsedExploreSearch(mode = ExploreSearchMode.Name, query = trimmed)
        }

        val tagQuery = normalizedPrefix.removePrefix("#").trim()
        if (tagQuery.isBlank()) return null
        return ParsedExploreSearch(mode = ExploreSearchMode.Tag, query = tagQuery)
    }

    private fun mergeAgentsUniqueById(agents: List<AgentInfo>): List<AgentInfo> {
        if (agents.isEmpty()) return emptyList()
        val unique = ArrayList<AgentInfo>(agents.size)
        val seenIds = HashSet<String>(agents.size)
        agents.forEach { agent ->
            val id = agent.id
            if (id.isNotEmpty() && seenIds.add(id)) {
                unique.add(agent)
            }
        }
        return unique
    }

    private fun filterAgentsByName(agents: List<AgentInfo>, query: String): List<AgentInfo> {
        if (agents.isEmpty()) return emptyList()
        return agents.filter { it.name.contains(query, ignoreCase = true) }
    }

    private fun filterAgentsByTag(agents: List<AgentInfo>, query: String): List<AgentInfo> {
        if (agents.isEmpty()) return emptyList()
        return agents.filter { agent ->
            agent.tags?.asSequence()?.filterNotNull()?.any {
                it.contains(query, ignoreCase = true)
            } == true
        }
    }

    /** 重置搜索状态 */
    fun resetSearchState() {
        _searchResults.value = emptyList()
        _isSearching.value = false
        _hasSearchExecuted.value = false
    }

    /** 刷新主题专区列表（用于下拉刷新，只有成功获取数据后才更新 UI） */
    fun refreshCharacterThemes(skip: Int = 0, limit: Int = 100) {
        viewModelScope.launch {
            _isLoadingThemes.value = true
            try {
                when (val result = AgentService.getCharacterThemes(skip = skip, limit = limit)) {
                    is ai.sxwl.android.data.http.ApiResult.Success -> {
                        LogUtils.d("ExploreViewModel - 刷新主题专区列表成功: ${result.data.size} 条")
                        val themes = result.data
                        // 只有在成功获取数据后才更新 UI
                        _characterThemes.value = themes
                        // 更新缓存，用于下次快速显示
                        AgentCacheManager.cacheCharacterThemes(themes)
                    }
                    is ai.sxwl.android.data.http.ApiResult.Error -> {
                        // 刷新失败时，保持现有 UI 数据不变，不更新也不清空
                        LogUtils.w(
                            "ExploreViewModel - 刷新主题专区列表失败: code=${result.code}, message=${result.message}，保持现有数据"
                        )
                    }
                }
            } catch (e: Exception) {
                // 刷新异常时，保持现有 UI 数据不变
                LogUtils.e("ExploreViewModel - 刷新主题专区列表异常: ${e.message}，保持现有数据", e)
            } finally {
                _isLoadingThemes.value = false
            }
        }
    }
}
