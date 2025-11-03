package com.ai.intellimate.explore

import ai.sxwl.android.common.base.BaseVM
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.billing.VipStatusHelper
import ai.sxwl.android.data.di.DataModule
import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.utils.LogUtils
import androidx.lifecycle.viewModelScope
import androidx.paging.PagingData
import androidx.paging.cachedIn
import com.ai.intellimate.utils.UnifiedStartupManager
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.launch

/** Explore页面ViewModel 负责管理推荐agents的Paging数据流、刷新、缓存等逻辑 */
class ExploreViewModel : BaseVM(), ExploreFetchCallback {

    private val getRecommendAgentsUseCase = DataModule.getRecommendAgentsUseCase

    // 使用app层的ExplorePagingRepository替代core/data层的Repository，以支持事件回调
    // 注意：这会使用不同的缓存策略，但可以支持事件上报
    private val explorePagingRepository by lazy {
        // 创建新的cacheProvider实例，因为它使用静态的AgentCacheManager，所以新实例也可以正常工作
        val cacheProvider = try {
            // RecommendedAgentCacheProviderImpl 使用静态的 AgentCacheManager，所以创建新实例是安全的
            com.ai.intellimate.utils.RecommendedAgentCacheProviderImpl()
        } catch (e: Exception) {
            LogUtils.e("ExploreViewModel - 创建cacheProvider失败: ${e.message}")
            null
        }
        ExplorePagingRepository(
            cacheProvider = cacheProvider,
            fetchCallback = this
        )
    }

    // Paging数据流
    private val _agentsFlow = MutableStateFlow<Flow<PagingData<AgentInfo>>?>(null)

    // 是否已初始化
    private var isInitialized = false

    // 保存滚动位置
    private val _savedFirstVisibleIndex = MutableStateFlow(0)
    val savedFirstVisibleIndex = _savedFirstVisibleIndex
    private val _savedFirstVisibleOffset = MutableStateFlow(0)
    val savedFirstVisibleOffset = _savedFirstVisibleOffset

    // 当前UI中显示的agents总数
    private val _currentUiAgentsCount = MutableStateFlow(0)
    val currentUiAgentsCount = _currentUiAgentsCount

    // 实现 ExploreFetchCallback 接口
    override suspend fun onSuccess(
        page: Int,
        pageSize: Int,
        responseTime: Long,
        agentsCount: Int,
        sortSeed: Int
    ) {
        reportExploreFetchSuccess(page, pageSize, responseTime, agentsCount, sortSeed)
    }

    override suspend fun onFailure(
        page: Int,
        pageSize: Int,
        responseTime: Long,
        errorMessage: String,
        sortSeed: Int
    ) {
        reportExploreFetchFailure(page, pageSize, responseTime, errorMessage, sortSeed)
    }

    override suspend fun onException(
        page: Int,
        pageSize: Int,
        responseTime: Long,
        exception: Exception,
        sortSeed: Int
    ) {
        reportExploreFetchException(page, pageSize, responseTime, exception, sortSeed)
    }

    /** 初始化Paging数据流 */
    fun initializePagingData() {
        if (isInitialized) return

        // Firebase Analytics - 记录探索页面访问
        FirebaseManager.logEvent(
            "explore_page_view",
            mapOf("page_type" to "recommendations", "is_initial_load" to true),
        )

        // 使用app层的ExplorePagingRepository，支持事件回调
        val initialFlow = explorePagingRepository.getRecommendAgentsFlow(
            useCache = true,
        ).cachedIn(viewModelScope)

        _agentsFlow.value = initialFlow
        isInitialized = true
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

    fun saveScrollPosition(index: Int, offset: Int) {
        _savedFirstVisibleIndex.value = index
        _savedFirstVisibleOffset.value = offset
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

    /** 上报Explore接口请求失败事件 */
    fun reportExploreFetchFailure(
        page: Int,
        pageSize: Int,
        responseTime: Long,
        errorMessage: String,
        sortSeed: Int,
    ) {
        viewModelScope.launch {
            FirebaseManager.logEvent(
                FirebaseManager.Events.EXPLORE_AGENTS_FETCH_FAILURE,
                FirebaseManager.safeEventParams(
                    "page" to page,
                    "page_size" to pageSize,
                    "response_time" to responseTime,
                    "error_message" to errorMessage,
                    "current_ui_agents_count" to _currentUiAgentsCount.value,
                    "sort_seed" to sortSeed,
                    "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                    "timestamp" to System.currentTimeMillis(),
                ),
            )
        }
    }

    /** 上报Explore接口请求异常事件 */
    fun reportExploreFetchException(
        page: Int,
        pageSize: Int,
        responseTime: Long,
        exception: Exception,
        sortSeed: Int,
    ) {
        viewModelScope.launch {
            FirebaseManager.logEvent(
                FirebaseManager.Events.EXPLORE_AGENTS_FETCH_EXCEPTION,
                FirebaseManager.safeEventParams(
                    "page" to page,
                    "page_size" to pageSize,
                    "response_time" to responseTime,
                    "exception_type" to exception.javaClass.simpleName,
                    "exception_message" to (exception.message ?: "unknown"),
                    "current_ui_agents_count" to _currentUiAgentsCount.value,
                    "sort_seed" to sortSeed,
                    "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                    "timestamp" to System.currentTimeMillis(),
                ),
            )

            // 记录异常到Crashlytics
            FirebaseManager.recordException(
                exception,
                mapOf(
                    "page" to page.toString(),
                    "page_size" to pageSize.toString(),
                    "sort_seed" to sortSeed.toString(),
                ),
            )
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

    /** 清空数据（用于用户登出等场景） */
    fun clearData() {
        _agentsFlow.value = null
        isInitialized = false
    }
}
