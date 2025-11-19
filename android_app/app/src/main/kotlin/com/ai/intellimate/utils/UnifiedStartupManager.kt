package com.ai.intellimate.utils

import ai.sxwl.android.common.startup.ImagePreloadManager
import ai.sxwl.android.data.api.IAgentApi
import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.api.model.UserProfile
import ai.sxwl.android.data.billing.VipStatusHelper
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.utils.LogUtils
import android.content.Context
import com.ai.intellimate.audio.AudioPreloadManager
import com.ai.intellimate.explore.ExploreConstants
import com.ai.intellimate.ui.components.VideoCacheManager
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/** 统一启动管理器 整合所有启动相关功能：缓存加载、网络预加载、用户管理、进度跟踪 */
object UnifiedStartupManager {

    private val startupScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var applicationContext: Context? = null

    // 启动状态
    private val _startupState = MutableStateFlow(StartupState.Initializing)
    val startupState: StateFlow<StartupState> = _startupState.asStateFlow()

    // 用户账户状态 - 用于确保PagingSource在有效token下发起请求
    private val _userAccountReady = MutableStateFlow(false)
    val userAccountReady: StateFlow<Boolean> = _userAccountReady.asStateFlow()

    // 预加载数据
    private val _userProfile = MutableStateFlow<UserProfile?>(null)
    val userProfile: StateFlow<UserProfile?> = _userProfile.asStateFlow()

    private val _recommendedAgents = MutableStateFlow<List<AgentInfo>>(emptyList())
    val recommendedAgents: StateFlow<List<AgentInfo>> = _recommendedAgents.asStateFlow()

    private val _chatAgents = MutableStateFlow<List<AgentInfo>>(emptyList())
    val chatAgents: StateFlow<List<AgentInfo>> = _chatAgents.asStateFlow()

    // 启动进度
    private val _startupProgress = MutableStateFlow(0f)
    val startupProgress: StateFlow<Float> = _startupProgress.asStateFlow()

    // 启动阶段
    private val _currentPhase = MutableStateFlow(StartupPhase.Initializing)
    val currentPhase: StateFlow<StartupPhase> = _currentPhase.asStateFlow()

    /** 启动状态枚举 */
    enum class StartupState {
        Initializing, // 初始化中 - 显示 SplashUI
        EssentialReady, // 必要初始化完成 - 可以隐藏 SplashUI
        Completed, // 启动完成
        Failed, // 启动失败
    }

    /** 启动阶段枚举 */
    enum class StartupPhase {
        Initializing, // 初始化
        LoadingCache, // 加载缓存
        NetworkSync, // 网络同步
        Completed, // 完成
    }

    /** 初始化启动管理器 - 只做必要的登录判断，不阻塞启动 注意：保持Initializing状态直到SplashUI主动检查完成 */
    fun initializeEssential(context: Context) {
        _startupState.value = StartupState.Initializing
        _currentPhase.value = StartupPhase.Initializing

        // 异步进行必要的登录判断，基于实际任务完成状态
        startupScope.launch {
            try {
                // 检查登录状态，确保有有效的token
                if (!isUserLoggedIn()) {
                    // 不再创建游客账户，等待用户登录
                    _userAccountReady.value = false
                    _startupProgress.value = 0.0f
                    return@launch
                }

                // 确保用户账户状态已就绪
                _userAccountReady.value = true
                _startupProgress.value = 0.3f
                // 立即开始关键数据预加载，不等待异步初始化
                loadCriticalData()
            } catch (e: Exception) {
                LogUtils.w("UnifiedStartupManager - 必要初始化失败，但不阻塞启动: ${e.message}")
                // 即使失败也继续，让SplashUI处理
            }
        }
    }

    /** 异步初始化 - 进行数据预加载和缓存，不阻塞启动 */
    fun initializeAsync(context: Context) {

        startupScope.launch {
            try {
                // 阶段0：初始化预加载管理器（在后台线程中）
                initializePreloadManagers(context)

                // 阶段1：加载缓存数据
                loadCacheData()

                // 阶段2：网络同步（如果已登录）
                syncNetworkData()

                _startupState.value = StartupState.Completed
                _currentPhase.value = StartupPhase.Completed
                _startupProgress.value = 1.0f
            } catch (e: Exception) {
                LogUtils.e("UnifiedStartupManager - 异步初始化失败: ${e.message}")
                _startupState.value = StartupState.Failed
            }
        }
    }

    /** 加载关键数据 - 优先加载recommend agents，确保UI有数据展示 */
    private fun loadCriticalData() {
        startupScope.launch {
            try {

                // 优先加载缓存数据（非阻塞）
                loadCacheDataNonBlocking()

                // 确保用户账户已就绪且有有效token后，才加载关键数据
                if (isUserLoggedIn()) {
                    // 优先加载chat agents（关键数据），阻塞等待完成
                    syncChatAgents()

                    // 异步加载explore agents（非关键数据），不阻塞启动
                    startupScope.launch {
                        try {
                            syncRecommendedAgents()
                        } catch (e: Exception) {
                            LogUtils.e("UnifiedStartupManager - 异步加载explore agents失败: ${e.message}")
                        }
                    }

                    // 异步加载用户自建agents（非关键数据），不阻塞启动
                    startupScope.launch {
                        try {
                            syncUserCreatedAgents()
                        } catch (e: Exception) {
                            LogUtils.e("UnifiedStartupManager - 异步加载用户自建agents失败: ${e.message}")
                        }
                    }
                } else {
                    LogUtils.w("UnifiedStartupManager - 用户未登录或token无效，跳过数据加载")
                    // 如果 chatAgents 接口不需要 token，可以尝试预加载（但可能失败）
                    // 这里不预加载，等待用户登录后再加载
                }
            } catch (e: Exception) {
                LogUtils.e("UnifiedStartupManager - 关键数据加载失败: ${e.message}")
            }
        }
    }

    /** 阶段0：初始化预加载管理器 */
    private suspend fun initializePreloadManagers(context: Context) {
        try {
            // 保存 applicationContext 用于后续预加载
            applicationContext = context.applicationContext

            // 初始化图片预加载管理器
            ImagePreloadManager.init(context)

            // 初始化音频预加载管理器
            AudioPreloadManager.init(context)
        } catch (e: Exception) {
            LogUtils.e("UnifiedStartupManager - 预加载管理器初始化失败: ${e.message}")
        }
    }

    /** 阶段1：加载缓存数据 */
    private suspend fun loadCacheData() {
        _currentPhase.value = StartupPhase.LoadingCache

        // 并行加载缓存数据
        val userProfileDeferred =
            startupScope.async {
                if (UserProfileManager.hasUserProfile()) {
                    UserProfileManager.getUserProfile()
                } else {
                    null
                }
            }

        val agentsDeferred = startupScope.async { AgentCacheManager.getCachedAgents() }

        val chatAgentsDeferred = startupScope.async { AgentCacheManager.getCachedChatAgents() }

        // 等待缓存数据加载完成
        _userProfile.value = userProfileDeferred.await()
        _recommendedAgents.value = agentsDeferred.await()
        _chatAgents.value = chatAgentsDeferred.await()
        // 用户自建agents缓存由ProfileViewModel管理，不需要在这里预加载

        _startupState.value = StartupState.EssentialReady
        _startupProgress.value = 0.3f
    }

    /** 加载缓存数据（非阻塞版本，用于关键数据加载） */
    private suspend fun loadCacheDataNonBlocking() {
        try {

            // 快速加载缓存数据，不等待
            if (UserProfileManager.hasUserProfile()) {
                _userProfile.value = UserProfileManager.getUserProfile()
            }

            val cachedAgents = AgentCacheManager.getCachedAgents()
            _recommendedAgents.value = cachedAgents

            val cachedChatAgents = AgentCacheManager.getCachedChatAgents()
            _chatAgents.value = cachedChatAgents
        } catch (e: Exception) {
            LogUtils.e("UnifiedStartupManager - 缓存数据加载异常: ${e.message}")
        }
    }

    /** 阶段3：网络同步 */
    private suspend fun syncNetworkData() {
        _currentPhase.value = StartupPhase.NetworkSync

        // 检查登录状态
        if (!isUserLoggedIn()) {
            return
        }

        // 并行同步网络数据
        val userProfileTask = startupScope.async { syncUserProfile() }

        val agentsTask = startupScope.async { syncRecommendedAgents() }

        val chatAgentsTask = startupScope.async { syncChatAgents() }

        // 等待网络同步完成
        userProfileTask.await()
        agentsTask.await()
        chatAgentsTask.await()

        _startupState.value = StartupState.Completed
        _startupProgress.value = 0.9f
    }

    /** 检查用户是否已登录且token有效 */
    private fun isUserLoggedIn(): Boolean {
        return try {
            val isLogin = IntySetting.isLogin()
            val token = IntySetting.getCurToken()
            val userId = IntySetting.getCurUserID()

            isLogin && token.isNotEmpty() && userId.isNotEmpty()
        } catch (e: Exception) {
            LogUtils.e("UnifiedStartupManager - 登录状态检查异常: ${e.message}")
            false
        }
    }

    /** 同步用户信息 */
    private suspend fun syncUserProfile() {
        try {
            val userProfile = IntyUserProfileSDK.getUserProfile()
            if (userProfile != null) {
                UserProfileManager.saveUserProfile(userProfile)
                _userProfile.value = userProfile

                // 设置Firebase用户信息
                val userId = IntySetting.getCurUserID()
                val userType = if (VipStatusHelper.isUserVip()) "vip" else "free"
                val subscriptionLevel = VipStatusHelper.getSubscriptionLevel()
                FirebaseManager.setUserInfo(userId, userType, subscriptionLevel)

                LogUtils.i("UnifiedStartupManager - 用户信息同步成功: ${userProfile.nickname}")
            } else {
                LogUtils.w("UnifiedStartupManager - 用户信息同步失败")
            }
        } catch (e: Exception) {
            LogUtils.e("UnifiedStartupManager - 用户信息同步异常: ${e.message}")
        }
    }

    /** 同步推荐agents */
    private suspend fun syncRecommendedAgents() {
        try {
            val agentApi: IAgentApi = NetServiceMgr.getAgentApi()

            val sortSeed = IntySetting.sortSeed()
            val result =
                agentApi.exploreAgents(
                    page = 1,
                    pageSize = ExploreConstants.PAGE_SIZE, // 使用统一的页面大小
                    sort_seed = sortSeed.toString(),
                )

            when (result) {
                is HttpResult.Success -> {
                    val agents = result.data.list ?: emptyList()
                    AgentCacheManager.cacheAgents(agents)
                    _recommendedAgents.value = agents

                    // 异步预加载资源，不阻塞启动流程
                    // 关键优化：优先预加载静态背景图（避免黑屏），然后预加载视频和音频
                    val contextForPreload = applicationContext
                    if (contextForPreload != null) {
                        CoroutineScope(Dispatchers.IO).launch {
                            try {
                                // 第一步：优先预加载关键静态背景图（前10个，避免黑屏）
                                // 这是最重要的，因为静态图是用户首先看到的
                                ImagePreloadManager.preloadCriticalImages(agents, 10)

                                // 第二步：预加载关键音频（前5个）
                                AudioPreloadManager.preloadCriticalOpeningAudios(agents, 5)

                                // 第三步：预加载关键背景视频（前5个）
                                preloadBackgroundVideos(contextForPreload, agents, 5)

                                // 第四步：预加载所有图片资源（包括静态背景图）
                                ImagePreloadManager.preloadAgentsImages(agents, 5)

                                // 第五步：预加载所有音频资源
                                AudioPreloadManager.preloadAgentsOpeningAudios(agents, 3)
                            } catch (e: Exception) {
                                LogUtils.e("UnifiedStartupManager - 资源预加载异常: ${e.message}")
                            }
                        }
                    }
                }
                is HttpResult.Failure -> {
                    LogUtils.w("UnifiedStartupManager - 推荐agents同步失败: ${result.message}")
                }
            }
        } catch (e: Exception) {
            LogUtils.e("UnifiedStartupManager - 推荐agents同步异常: ${e.message}")
        }
    }

    /** 同步聊天agents */
    private suspend fun syncChatAgents() {
        try {
            val agentApi: IAgentApi = NetServiceMgr.getAgentApi()

            val sortSeed = IntySetting.randomSortSeed()
            val result =
                agentApi.chatAgents(
                    page = 1,
                    pageSize = 20, // 使用聊天页面大小
                    sort_seed = sortSeed.toString(),
                )

            when (result) {
                is HttpResult.Success -> {
                    val agents = result.data.list ?: emptyList()
                    AgentCacheManager.cacheChatAgents(agents)
                    _chatAgents.value = agents

                    // 异步预加载资源，不阻塞启动流程
                    // 关键优化：chatAgents是核心数据，需要更积极的预加载策略
                    // 优先预加载静态背景图（避免黑屏），然后预加载视频和音频
                    val contextForPreload = applicationContext
                    if (contextForPreload != null) {
                        CoroutineScope(Dispatchers.IO).launch {
                            try {
                                // 第一步：优先预加载关键静态背景图（前10个，避免黑屏）
                                // chatAgents是核心数据，需要更积极的预加载
                                ImagePreloadManager.preloadCriticalImages(agents, 10)

                                // 第二步：预加载关键音频（前5个）
                                AudioPreloadManager.preloadCriticalOpeningAudios(agents, 5)

                                // 第三步：预加载关键背景视频（前5个）
                                preloadBackgroundVideos(contextForPreload, agents, 5)

                                // 第四步：预加载所有图片资源（包括静态背景图）
                                // chatAgents通常有20个，预加载所有以确保流畅体验
                                ImagePreloadManager.preloadAgentsImages(agents, 5)

                                // 第五步：预加载所有音频资源
                                AudioPreloadManager.preloadAgentsOpeningAudios(agents, 3)
                            } catch (e: Exception) {
                                LogUtils.e("UnifiedStartupManager - 聊天agents资源预加载异常: ${e.message}")
                            }
                        }
                    }
                }
                is HttpResult.Failure -> {
                    LogUtils.w("UnifiedStartupManager - 聊天agents同步失败: ${result.message}")
                }
            }
        } catch (e: Exception) {
            LogUtils.e("UnifiedStartupManager - 聊天agents同步异常: ${e.message}")
        }
    }

    /** 同步用户自建agents */
    suspend fun syncUserCreatedAgents() {
        try {
            // 检查登录状态，确保有有效的token后再调用需要认证的接口
            if (!isUserLoggedIn()) {
                LogUtils.w("UnifiedStartupManager - 用户未登录或token无效，跳过用户自建agents同步")
                return
            }

            val agentApi: IAgentApi = NetServiceMgr.getAgentApi()

            when (val result = agentApi.getUserCreatedAgents(skip = 0, limit = 20)) {
                is HttpResult.Success -> {
                    val agents = result.data
                    AgentCacheManager.cacheUserCreatedAgents(agents)
                }

                is HttpResult.Failure -> {
                    LogUtils.w("UnifiedStartupManager - 用户自建agents同步失败: ${result.message}")
                }
            }
        } catch (e: Exception) {
            LogUtils.e("UnifiedStartupManager - 用户自建agents同步异常: ${e.message}")
        }
    }

    /** 获取当前用户信息 */
    fun getCurrentUserProfile(): UserProfile? {
        return _userProfile.value
    }

    /** 获取当前推荐agents */
    fun getCurrentRecommendedAgents(): List<AgentInfo> {
        return _recommendedAgents.value
    }

    /** 获取当前聊天agents */
    fun getCurrentChatAgents(): List<AgentInfo> {
        return _chatAgents.value
    }

    /** 检查是否已完成启动 */
    fun isStartupCompleted(): Boolean {
        return _startupState.value == StartupState.Completed
    }

    /** 检查用户账户是否已就绪（包括游客账户） */
    fun isUserAccountReady(): Boolean {
        return _userAccountReady.value
    }

    /** 检查是否有缓存数据 */
    fun hasCacheData(): Boolean {
        return _recommendedAgents.value.isNotEmpty() ||
            _chatAgents.value.isNotEmpty() ||
            _userProfile.value != null
    }

    /** 手动刷新推荐agents */
    fun refreshRecommendedAgents() {
        startupScope.launch {
            try {
                syncRecommendedAgents()
            } catch (e: Exception) {
                LogUtils.e("UnifiedStartupManager - recommended agents刷新失败: ${e.message}")
            }
        }
    }

    /** 手动刷新聊天agents */
    fun refreshChatAgents() {
        startupScope.launch {
            try {
                syncChatAgents()
            } catch (e: Exception) {
                LogUtils.e("UnifiedStartupManager - chat agents刷新失败: ${e.message}")
            }
        }
    }

    /** 手动刷新用户信息 */
    fun refreshUserProfile() {
        startupScope.launch { syncUserProfile() }
    }

    /** 标记必要初始化完成 - 由SplashUI调用 用于控制SplashUI的显示时机 */
    fun markEssentialInitializationComplete() {
        _startupState.value = StartupState.EssentialReady
    }

    /** 清理所有启动数据（用于用户登出等场景） */
    fun clearAllData() {
        _userAccountReady.value = false
        _userProfile.value = null
        _recommendedAgents.value = emptyList()
        _chatAgents.value = emptyList()
        _startupProgress.value = 0f
        _startupState.value = StartupState.Initializing
        _currentPhase.value = StartupPhase.Initializing
    }

    /** 标记用户账户已就绪（用于logout后恢复状态） */
    fun markUserAccountReady() {
        _userAccountReady.value = true
    }

    /**
     * 预加载背景视频（backgroundAnimatedUrl）
     *
     * @param context 上下文
     * @param agents 需要预加载的agents列表
     * @param maxConcurrent 最大并发预加载数量
     */
    private suspend fun preloadBackgroundVideos(
        context: Context,
        agents: List<AgentInfo>,
        maxConcurrent: Int = 5,
    ) {
        try {
            val videoCacheManager = VideoCacheManager.getInstance(context)
            val videoUrls =
                agents
                    .mapNotNull { it.backgroundAnimatedUrl?.takeIf { url -> url.isNotBlank() } }
                    .distinct()

            if (videoUrls.isEmpty()) {
                return
            }

            // 将URL列表分组，每组最多maxConcurrent个
            val chunks = videoUrls.chunked(maxConcurrent)

            coroutineScope {
                chunks.forEach { chunk ->
                    // 并发预加载当前组的所有视频
                    val jobs =
                        chunk.map { url ->
                            async {
                                try {
                                    // 检查是否已经缓存
                                    if (!videoCacheManager.isCached(url)) {
                                        videoCacheManager.preloadVideo(url)
                                    }
                                } catch (e: Exception) {
                                    LogUtils.e(
                                        "UnifiedStartupManager - 预加载背景视频失败: $url, 错误: ${e.message}"
                                    )
                                }
                            }
                        }

                    // 等待当前组的所有任务完成
                    jobs.forEach { it.await() }
                }
            }
        } catch (e: Exception) {
            LogUtils.e("UnifiedStartupManager - 背景视频预加载异常: ${e.message}")
        }
    }
}
