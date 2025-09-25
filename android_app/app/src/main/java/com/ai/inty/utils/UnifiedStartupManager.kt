package com.ai.inty.utils

import android.content.Context
import com.ai.inty.beans.AgentInfo
import com.ai.inty.beans.UserProfile
import com.ai.inty.explore.ExploreConstants
import com.ai.inty.net.IAgentApi
import com.architecture.httplib.core.HttpResult
import com.inty.utils.log.EasyLog
import com.inty.utils.storage.IntySetting
import com.therouter.TheRouter
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.async
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * 统一启动管理器
 * 整合所有启动相关功能：缓存加载、网络预加载、用户管理、进度跟踪
 */
object UnifiedStartupManager {
    
    private val startupScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    
    // 启动状态
    private val _startupState = MutableStateFlow(StartupState.Initializing)
    val startupState: StateFlow<StartupState> = _startupState.asStateFlow()
    
    // 预加载数据
    private val _userProfile = MutableStateFlow<UserProfile?>(null)
    val userProfile: StateFlow<UserProfile?> = _userProfile.asStateFlow()
    
    private val _recommendedAgents = MutableStateFlow<List<AgentInfo>>(emptyList())
    val recommendedAgents: StateFlow<List<AgentInfo>> = _recommendedAgents.asStateFlow()
    
    // 启动进度
    private val _startupProgress = MutableStateFlow(0f)
    val startupProgress: StateFlow<Float> = _startupProgress.asStateFlow()
    
    // 启动阶段
    private val _currentPhase = MutableStateFlow(StartupPhase.Initializing)
    val currentPhase: StateFlow<StartupPhase> = _currentPhase.asStateFlow()
    
    /**
     * 启动状态枚举
     */
    enum class StartupState {
        Initializing,    // 初始化中
        CacheLoaded,     // 缓存已加载
        UserReady,       // 用户准备就绪
        NetworkUpdated,  // 网络数据已更新
        Completed,       // 启动完成
        Failed          // 启动失败
    }
    
    /**
     * 启动阶段枚举
     */
    enum class StartupPhase {
        Initializing,    // 初始化
        LoadingCache,    // 加载缓存
        UserSetup,       // 用户设置
        NetworkSync,     // 网络同步
        Completed        // 完成
    }
    
    /**
     * 初始化启动管理器 - 只做必要的登录判断，不阻塞启动
     */
    fun initializeEssential(context: Context) {
        EasyLog.log("UnifiedStartupManager - 开始必要初始化")
        _startupState.value = StartupState.Initializing
        _currentPhase.value = StartupPhase.Initializing
        
        // 异步进行必要的登录判断，给splash页面显示时间
        startupScope.launch {
            try {
                // 给splash页面一些显示时间
                kotlinx.coroutines.delay(800) // 至少显示800ms
                
                // 检查登录状态，如果未登录则尝试创建游客账户（不阻塞）
                if (!IntySetting.isLogin()) {
                    EasyLog.log("UnifiedStartupManager - 用户未登录，尝试创建游客账户")
                    try {
                        createGuestAccount()
                    } catch (e: Exception) {
                        EasyLog.log("UnifiedStartupManager - 游客账户创建失败，但不阻塞启动: ${e.message}", EasyLog.WARN)
                    }
                }
                
                _startupState.value = StartupState.UserReady
                _startupProgress.value = 0.3f
                EasyLog.log("UnifiedStartupManager - 必要初始化完成")
                
            } catch (e: Exception) {
                EasyLog.log("UnifiedStartupManager - 必要初始化失败，但不阻塞启动: ${e.message}", EasyLog.WARN)
                _startupState.value = StartupState.UserReady // 即使失败也标记为用户就绪，不阻塞启动
            }
        }
    }
    
    /**
     * 异步初始化 - 进行数据预加载和缓存，不阻塞启动
     */
    fun initializeAsync(context: Context) {
        EasyLog.log("UnifiedStartupManager - 开始异步初始化")
        
        startupScope.launch {
            try {
                // 阶段0：初始化图片预加载管理器（在后台线程中）
                initializeImagePreloadManager(context)
                
                // 阶段1：加载缓存数据
                loadCacheData()
                
                // 阶段2：网络同步（如果已登录）
                syncNetworkData()
                
                _startupState.value = StartupState.Completed
                _currentPhase.value = StartupPhase.Completed
                _startupProgress.value = 1.0f
                
                EasyLog.log("UnifiedStartupManager - 异步初始化完成")
                
            } catch (e: Exception) {
                EasyLog.log("UnifiedStartupManager - 异步初始化失败: ${e.message}", EasyLog.ERROR)
                _startupState.value = StartupState.Failed
            }
        }
    }
    
    /**
     * 阶段0：初始化图片预加载管理器
     */
    private suspend fun initializeImagePreloadManager(context: Context) {
        try {
            ImagePreloadManager.init(context)
            EasyLog.log("UnifiedStartupManager - 图片预加载管理器初始化完成")
        } catch (e: Exception) {
            EasyLog.log("UnifiedStartupManager - 图片预加载管理器初始化失败: ${e.message}", EasyLog.ERROR)
        }
    }
    
    /**
     * 阶段1：加载缓存数据
     */
    private suspend fun loadCacheData() {
        _currentPhase.value = StartupPhase.LoadingCache
        EasyLog.log("UnifiedStartupManager - 开始加载缓存数据")
        
        // 并行加载缓存数据
        val userProfileDeferred = startupScope.async { 
            if (UserProfileManager.hasUserProfile()) {
                val profile = UserProfileManager.getUserProfile()
                EasyLog.log("UnifiedStartupManager - 加载缓存用户信息: ${profile.nickname}")
                profile
            } else {
                EasyLog.log("UnifiedStartupManager - 无缓存用户信息")
                null
            }
        }
        
        val agentsDeferred = startupScope.async { 
            val cachedAgents = AgentCacheManager.getCachedAgents()
            EasyLog.log("UnifiedStartupManager - 加载缓存agents: ${cachedAgents.size}个")
            cachedAgents
        }
        
        // 等待缓存数据加载完成
        _userProfile.value = userProfileDeferred.await()
        _recommendedAgents.value = agentsDeferred.await()
        
        _startupState.value = StartupState.CacheLoaded
        _startupProgress.value = 0.3f
        EasyLog.log("UnifiedStartupManager - 缓存数据加载完成")
    }
    
    /**
     * 阶段2：用户设置
     */
    private suspend fun setupUser() {
        _currentPhase.value = StartupPhase.UserSetup
        EasyLog.log("UnifiedStartupManager - 开始用户设置")
        
        if (!IntySetting.isLogin()) {
            EasyLog.log("UnifiedStartupManager - 用户未登录，创建游客账户")
            createGuestAccount()
        }
        
        _startupState.value = StartupState.UserReady
        _startupProgress.value = 0.6f
        EasyLog.log("UnifiedStartupManager - 用户设置完成")
    }
    
    /**
     * 阶段3：网络同步
     */
    private suspend fun syncNetworkData() {
        _currentPhase.value = StartupPhase.NetworkSync
        EasyLog.log("UnifiedStartupManager - 开始网络同步")
        
        // 检查登录状态
        if (!IntySetting.isLogin() || IntySetting.getCurToken().isEmpty()) {
            EasyLog.log("UnifiedStartupManager - 未登录或token为空，跳过网络同步")
            return
        }
        
        // 并行同步网络数据
        val userProfileTask = startupScope.async {
            syncUserProfile()
        }
        
        val agentsTask = startupScope.async {
            syncRecommendedAgents()
        }
        
        // 等待网络同步完成
        userProfileTask.await()
        agentsTask.await()
        
        _startupState.value = StartupState.NetworkUpdated
        _startupProgress.value = 0.9f
        EasyLog.log("UnifiedStartupManager - 网络同步完成")
    }
    
    /**
     * 创建游客账户
     */
    private suspend fun createGuestAccount() {
        try {
            val result = com.ai.inty.netapi.services.AuthService.createGuest()
            when (result) {
                is com.ai.inty.netapi.ApiResult.Success -> {
                    val (guestId, token) = result.data
                    IntySetting.login(true, guestId, token)
                    EasyLog.log("UnifiedStartupManager - 游客账户创建成功: $guestId")
                }
                is com.ai.inty.netapi.ApiResult.Error -> {
                    EasyLog.log("UnifiedStartupManager - 游客账户创建失败: ${result.message}", EasyLog.ERROR)
                    throw Exception("Guest account creation failed: ${result.message}")
                }
            }
        } catch (e: Exception) {
            EasyLog.log("UnifiedStartupManager - 游客账户创建异常: ${e.message}", EasyLog.ERROR)
            throw e
        }
    }
    
    /**
     * 同步用户信息
     */
    private suspend fun syncUserProfile() {
        try {
            val userProfile = IntyUserProfileSDK.getUserProfile()
            if (userProfile != null) {
                UserProfileManager.saveUserProfile(userProfile)
                _userProfile.value = userProfile
                EasyLog.log("UnifiedStartupManager - 用户信息同步成功: ${userProfile.nickname}")
            } else {
                EasyLog.log("UnifiedStartupManager - 用户信息同步失败", EasyLog.WARN)
            }
        } catch (e: Exception) {
            EasyLog.log("UnifiedStartupManager - 用户信息同步异常: ${e.message}", EasyLog.ERROR)
        }
    }
    
    /**
     * 同步推荐agents
     */
    private suspend fun syncRecommendedAgents() {
        try {
            val agentApi: IAgentApi = TheRouter.get(IAgentApi::class.java)
                ?: throw IllegalStateException("IAgentApi not found")
            
            val sortSeed = IntySetting.sortSeed()
            val result = agentApi.recommendAgents(
                page = 1, 
                pageSize = ExploreConstants.PAGE_SIZE, // 使用统一的页面大小
                sort_seed = sortSeed.toString()
            )
            
            when (result) {
                is HttpResult.Success -> {
                    val agents = result.data.list ?: emptyList()
                    AgentCacheManager.cacheAgents(agents)
                    _recommendedAgents.value = agents
                    EasyLog.log("UnifiedStartupManager - 推荐agents同步成功: ${agents.size}个")
                    
                    // 异步预加载图片资源，不阻塞启动流程
                    kotlinx.coroutines.CoroutineScope(kotlinx.coroutines.Dispatchers.IO).launch {
                        try {
                            // 先预加载关键图片（前10个），确保首屏快速渲染
                            ImagePreloadManager.preloadCriticalImages(agents, 10)
                            
                            // 然后预加载所有图片，优化后续页面渲染
                            ImagePreloadManager.preloadAgentsImages(agents, 5)
                        } catch (e: Exception) {
                            EasyLog.log("UnifiedStartupManager - 图片预加载异常: ${e.message}", EasyLog.ERROR)
                        }
                    }
                }
                is HttpResult.Failure -> {
                    EasyLog.log("UnifiedStartupManager - 推荐agents同步失败: ${result.message}", EasyLog.WARN)
                }
            }
        } catch (e: Exception) {
            EasyLog.log("UnifiedStartupManager - 推荐agents同步异常: ${e.message}", EasyLog.ERROR)
        }
    }
    
    /**
     * 获取当前用户信息
     */
    fun getCurrentUserProfile(): UserProfile? {
        return _userProfile.value
    }
    
    /**
     * 获取当前推荐agents
     */
    fun getCurrentRecommendedAgents(): List<AgentInfo> {
        return _recommendedAgents.value
    }
    
    /**
     * 检查是否已完成启动
     */
    fun isStartupCompleted(): Boolean {
        return _startupState.value == StartupState.Completed
    }
    
    /**
     * 检查是否有缓存数据
     */
    fun hasCacheData(): Boolean {
        return _recommendedAgents.value.isNotEmpty() || _userProfile.value != null
    }
    
    /**
     * 手动刷新推荐agents
     */
    fun refreshRecommendedAgents() {
        startupScope.launch {
            syncRecommendedAgents()
        }
    }
    
    /**
     * 手动刷新用户信息
     */
    fun refreshUserProfile() {
        startupScope.launch {
            syncUserProfile()
        }
    }
    
    /**
     * 清理所有启动数据（用于用户登出等场景）
     */
    fun clearAllData() {
        _userProfile.value = null
        _recommendedAgents.value = emptyList()
        _startupProgress.value = 0f
        _startupState.value = StartupState.Initializing
        _currentPhase.value = StartupPhase.Initializing
        EasyLog.log("UnifiedStartupManager - 清理所有启动数据")
    }
}
