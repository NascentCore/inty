package com.ai.inty.utils

import android.content.Context
import com.ai.inty.beans.AgentInfo
import com.ai.inty.beans.UserProfile
import com.ai.inty.net.IAgentApi
import com.ai.inty.net.IUserApi2
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
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext

/**
 * 应用启动管理器
 * 负责优化应用启动流程，实现并行初始化、缓存优先、预加载等功能
 */
object AppStartupManager {

    private val startupScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    // 启动状态
    private val _startupState = MutableStateFlow(StartupState.Initializing)
    val startupState: StateFlow<StartupState> = _startupState.asStateFlow()

    // 缓存数据
    private val _cachedUserProfile = MutableStateFlow<UserProfile?>(null)
    val cachedUserProfile: StateFlow<UserProfile?> = _cachedUserProfile.asStateFlow()

    private val _cachedAgents = MutableStateFlow<List<AgentInfo>>(emptyList())
    val cachedAgents: StateFlow<List<AgentInfo>> = _cachedAgents.asStateFlow()



    // 预加载状态
    private val _preloadProgress = MutableStateFlow(0f)
    val preloadProgress: StateFlow<Float> = _preloadProgress.asStateFlow()

    // 防抖机制
    private var lastProgressUpdate = 0L
    private val PROGRESS_UPDATE_THRESHOLD = 100L // 100ms防抖间隔

    /**
     * 启动状态枚举
     */
    enum class StartupState {
        Initializing,    // 初始化中
        CacheLoaded,     // 缓存已加载
        NetworkUpdated,  // 网络数据已更新
        Completed,       // 启动完成
        Failed          // 启动失败
    }

    /**
     * 安全更新进度，带防抖机制
     */
    private fun updateProgressSafely(newProgress: Float) {
        val currentTime = System.currentTimeMillis()
        if (currentTime - lastProgressUpdate > PROGRESS_UPDATE_THRESHOLD) {
            _preloadProgress.value = newProgress
            lastProgressUpdate = currentTime
            EasyLog.log(
                "AppStartupManager - 进度更新: ${
                    String.format(
                        "%.1f",
                        newProgress * 100
                    )
                }%"
            )
        }
    }

    /**
     * 初始化启动管理器
     */
    fun initialize(context: Context) {
        EasyLog.log("AppStartupManager - 开始初始化")
        _startupState.value = StartupState.Initializing

        startupScope.launch {
            try {
                // 第一步：并行加载缓存数据（不需要登录）
                loadCacheData()

                // 第二步：等待登录完成后再预加载网络数据
                _startupState.value = StartupState.CacheLoaded
                EasyLog.log("AppStartupManager - 缓存数据加载完成，等待登录")

            } catch (e: Exception) {
                EasyLog.log("AppStartupManager - 启动失败: ${e.message}", EasyLog.ERROR)
                _startupState.value = StartupState.Failed
            }
        }
    }

    /**
     * 登录成功后调用，开始预加载网络数据
     */
    fun onLoginSuccess() {
        EasyLog.log("AppStartupManager - 登录成功，开始预加载网络数据")

        startupScope.launch {
            try {
                // 确保有有效的token
                if (IntySetting.getCurToken().isNotEmpty()) {
                    preloadNetworkData()
                    _startupState.value = StartupState.NetworkUpdated
                    EasyLog.log("AppStartupManager - 网络数据预加载完成")
                } else {
                    EasyLog.log("AppStartupManager - Token为空，跳过网络预加载")
                    _startupState.value = StartupState.Completed
                }
            } catch (e: Exception) {
                EasyLog.log("AppStartupManager - 网络预加载失败: ${e.message}", EasyLog.ERROR)
                _startupState.value = StartupState.Completed // 即使失败也标记为完成，不影响启动
            }
        }
    }

    /**
     * 加载缓存数据（快速展示）
     */
    private suspend fun loadCacheData() {
        EasyLog.log("AppStartupManager - 加载缓存数据")

        // 并行加载各种缓存数据
        val userProfileDeferred = startupScope.async { loadCachedUserProfile() }
        val agentsDeferred = startupScope.async { loadCachedAgents() }

        // 等待所有缓存数据加载完成
        _cachedUserProfile.value = userProfileDeferred.await()
        _cachedAgents.value = agentsDeferred.await()

        _startupState.value = StartupState.CacheLoaded
        _preloadProgress.value = 0.3f
        EasyLog.log("AppStartupManager - 缓存数据加载完成")
    }

    /**
     * 预加载网络数据（后台更新）
     */
    private suspend fun preloadNetworkData() {
        EasyLog.log("AppStartupManager - 开始预加载网络数据")

        val totalTasks = 2  // 修复：实际只有2个任务
        val completedTasks = Mutex()
        var completedCount = 0

        // 并行预加载各种网络数据
        val tasks = listOf(
            startupScope.async {
                updateUserProfileFromNetwork()
                completedTasks.withLock {
                    completedCount++
                    val progress = 0.3f + (completedCount.toFloat() / totalTasks) * 0.7f
                    updateProgressSafely(progress)
                }
            },
            startupScope.async {
                updateAgentsFromNetwork()
                completedTasks.withLock {
                    completedCount++
                    val progress = 0.3f + (completedCount.toFloat() / totalTasks) * 0.7f
                    updateProgressSafely(progress)
                }
            },
        )

        // 等待所有预加载任务完成
        tasks.forEach { it.await() }

        _startupState.value = StartupState.NetworkUpdated
        _preloadProgress.value = 1.0f
        EasyLog.log("AppStartupManager - 网络数据预加载完成")
    }

    /**
     * 加载缓存的用户信息
     */
    private suspend fun loadCachedUserProfile(): UserProfile? {
        return withContext(Dispatchers.IO) {
            if (UserProfileManager.hasUserProfile()) {
                val profile = UserProfileManager.getUserProfile()
                EasyLog.log("AppStartupManager - 加载缓存用户信息: ${profile.nickname}")
                profile
            } else {
                EasyLog.log("AppStartupManager - 无缓存用户信息")
                null
            }
        }
    }

    /**
     * 加载缓存的推荐agents
     */
    private suspend fun loadCachedAgents(): List<AgentInfo> {
        return withContext(Dispatchers.IO) {
            val cachedAgents = AgentCacheManager.getCachedAgents()
            EasyLog.log("AppStartupManager - 加载缓存agents: ${cachedAgents.size}个")
            cachedAgents
        }
    }



    /**
     * 从网络更新用户信息
     */
    private suspend fun updateUserProfileFromNetwork() {
        // 检查登录状态和token
        if (!IntySetting.isLogin() || IntySetting.getCurToken().isEmpty()) {
            EasyLog.log("AppStartupManager - 未登录或token为空，跳过用户信息更新")
            return
        }

        try {
            val userApi2: IUserApi2 = TheRouter.get(IUserApi2::class.java)
                ?: throw IllegalStateException("IUserApi2 not found")

            val result = userApi2.getUserProfile()
            when (result) {
                is HttpResult.Success -> {
                    UserProfileManager.saveUserProfile(result.data)
                    _cachedUserProfile.value = result.data
                    EasyLog.log("AppStartupManager - 更新用户信息成功: ${result.data.nickname}")
                }

                is HttpResult.Failure -> {
                    EasyLog.log(
                        "AppStartupManager - 更新用户信息失败: ${result.message}",
                        EasyLog.WARN
                    )
                }
            }
        } catch (e: Exception) {
            EasyLog.log("AppStartupManager - 更新用户信息异常: ${e.message}", EasyLog.ERROR)
        }
    }

    /**
     * 从网络更新推荐agents
     */
    private suspend fun updateAgentsFromNetwork() {
        // 检查登录状态和token
        if (!IntySetting.isLogin() || IntySetting.getCurToken().isEmpty()) {
            EasyLog.log("AppStartupManager - 未登录或token为空，跳过推荐agents更新")
            return
        }

        try {
            val agentApi: IAgentApi = TheRouter.get(IAgentApi::class.java)
                ?: throw IllegalStateException("IAgentApi not found")

            val result = agentApi.recommendAgents(1, 10)
            when (result) {
                is HttpResult.Success -> {
                    val agents = result.data.list ?: emptyList()
                    AgentCacheManager.cacheAgents(agents)
                    _cachedAgents.value = agents
                    EasyLog.log("AppStartupManager - 更新推荐agents成功: ${agents.size}个")
                }

                is HttpResult.Failure -> {
                    EasyLog.log(
                        "AppStartupManager - 更新推荐agents失败: ${result.message}",
                        EasyLog.WARN
                    )
                }
            }
        } catch (e: Exception) {
            EasyLog.log("AppStartupManager - 更新推荐agents异常: ${e.message}", EasyLog.ERROR)
        }
    }


    /**
     * 更新缓存的推荐agents
     */
    fun updateCachedAgents(agents: List<AgentInfo>) {
        _cachedAgents.value = agents
        EasyLog.log("AppStartupManager - 更新缓存推荐agents: ${agents.size}个")
    }



}
