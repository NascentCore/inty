package com.ai.inty.viewmodels

import android.content.Context
import androidx.compose.runtime.mutableStateListOf
import androidx.lifecycle.viewModelScope
import com.ai.inty.Constant
import com.ai.inty.R
import com.ai.inty.base.BaseActivityViewModel
import com.ai.inty.base.ToastUtils
import com.ai.inty.beans.AgentInfo
import com.ai.inty.beans.AppVersionRsp
import com.ai.inty.beans.CreateAgentRequest
import com.ai.inty.beans.UserProfile
import com.ai.inty.billing.BillingRepository
import com.ai.inty.net.IAgentApi
import com.ai.inty.net.ICommonApi
import com.ai.inty.net.IUserApi
import com.ai.inty.utils.AgentCacheManager
import com.ai.inty.utils.AppStartupManager
import com.ai.inty.utils.CredentialManagerHelper.clearCredentialState
import com.ai.inty.utils.IntyUserProfileSDK
import com.ai.inty.utils.UserProfileManager
import com.architecture.httplib.core.HttpResult
import com.inty.utils.AppEnv
import com.inty.utils.log.EasyLog
import com.inty.utils.storage.IntySetting
import com.therouter.TheRouter
import com.therouter.router.Navigator
import com.therouter.router.action.interceptor.ActionInterceptor
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext


enum class HomeTabIndex {
    Chat,
    Conversation,
    Create,
    Explore,
    Profile
}

class MainViewModel : BaseActivityViewModel() {

    // 延迟获取依赖，避免在构造函数中立即获取导致空指针异常
    private val userApi: IUserApi by lazy {
        TheRouter.get(IUserApi::class.java)
            ?: throw IllegalStateException("IUserApi not found in TheRouter")
    }
    private val agentApi: IAgentApi by lazy {
        TheRouter.get(IAgentApi::class.java)
            ?: throw IllegalStateException("IAgentApi not found in TheRouter")
    }

    private val commonApi: ICommonApi by lazy {
        TheRouter.get(ICommonApi::class.java)
            ?: throw IllegalStateException("ICommonApi not found in TheRouter")
    }

    //系统推荐agents列表，也是首页默认的几个agents
    val agentList = mutableStateListOf<AgentInfo>()
    val followingAgents = mutableStateListOf<AgentInfo>()//关注的agents列表数据
    val userCreatedAgents = mutableStateListOf<AgentInfo>()//用户自创建的agents数据

    private var currentPage = 0
    private var _isLoading = MutableStateFlow(false)
    val isLoading = _isLoading.asStateFlow()
    private var hasMoreData = true

    // Pagination state for user created agents
    private var currentUserAgentsPage = 0
    private var _isLoadingUserAgents = MutableStateFlow(false)
    val isLoadingUserAgents = _isLoadingUserAgents.asStateFlow()
    private var hasMoreUserAgents = true

    private val _selectedTab = MutableStateFlow(HomeTabIndex.Chat)
    val selectedTab = _selectedTab.asStateFlow()

    private val _currentChatPageIndex = MutableStateFlow(0)
    val currentChatPageIndex = _currentChatPageIndex.asStateFlow()

    private var chatViewModel: ChatViewModel? = null

    //使用flow数据流的形式，感知用户数据
    private val _userProfile = MutableStateFlow(UserProfile())
    val userProfile = _userProfile.asStateFlow()

    //用户切换触发更新数据的拦截器
    private val userProfileChanged = object : ActionInterceptor() {
        override fun handle(context: Context, navigator: Navigator): Boolean {
            getUserProfile()
            return super.handle(context, navigator)
        }
    }

    //用于推荐接口的sort seed
    var sortSeed = IntySetting.sortSeed()

    init {
        EasyLog.log("MainViewModel init - current user: ${IntySetting.getCurUserID()}")

        // 使用启动管理器的缓存数据快速初始化UI
        loadCachedData()

        // 后台更新网络数据
        loadBusinessData()

        TheRouter.addActionInterceptor(Constant.ACTION_USER_PROFILE_CHANGED, userProfileChanged)
    }

    /**
     * 加载缓存数据（快速展示）
     * 在App启动时快速展示缓存数据，提供良好的用户体验
     */
    private fun loadCachedData() {
        // 从启动管理器获取缓存的用户信息
        val cachedUserProfile = AppStartupManager.cachedUserProfile.value
        if (cachedUserProfile != null) {
            _userProfile.value = cachedUserProfile
            EasyLog.log("MainViewModel - 使用缓存用户信息: ${cachedUserProfile.nickname}")
        }

        // 从启动管理器获取缓存的推荐agents
        val cachedAgents = AppStartupManager.cachedAgents.value
        if (cachedAgents.isNotEmpty()) {
            agentList.clear()
            agentList.addAll(cachedAgents)
            EasyLog.log("MainViewModel - 使用缓存推荐agents: ${cachedAgents.size}个")
        }


    }

    private fun loadBusinessData() {
        // 加载业务数据
        getAgents() // 现在会先使用缓存，然后后台静默刷新
        getUserProfile() // 从服务器获取最新信息并更新本地缓存
        //检查app版本更新
        checkAppVersion()

    }

    /**
     * 检查是否需要从网络更新数据
     */
    private fun shouldUpdateFromNetwork(): Boolean {
        // 只有在已登录且有有效token的情况下才进行网络更新
        return IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()
    }

    fun getAgents() {
        EasyLog.log("getAgents - 开始加载推荐agents")
        currentPage = 1
        hasMoreData = true

        // 第一步：如果有缓存数据，先使用缓存数据快速展示
        val cachedAgents = AppStartupManager.cachedAgents.value
        if (cachedAgents.isNotEmpty()) {
            agentList.clear()
            agentList.addAll(cachedAgents)
            EasyLog.log("getAgents - 使用缓存数据快速展示: ${cachedAgents.size}个")
            chatViewModel?.setAgentInfo(agentList.firstOrNull())
        }

        // 第二步：后台静默刷新数据（无论是否有缓存）
        // 避免重复请求：只有在没有正在加载时才进行网络请求
        if (shouldUpdateFromNetwork() && !_isLoading.value) {
            EasyLog.log("getAgents - 后台静默刷新数据")
            loadAgentsSilently()
        } else {
            EasyLog.log("getAgents - 跳过网络更新，使用缓存数据")
        }
    }

    /**
     * 强制刷新agents数据（用于下拉刷新）
     */
    fun refreshAgents() {
        EasyLog.log("refreshAgents - Force refresh from network")
        currentPage = 1
        hasMoreData = true
        agentList.clear()
        //每次手动刷新，需要重置sort seed,并保存，因为在AppStartupManger中有使用，可确保缓存与接口数据一致。
        sortSeed = sortSeed + 1
        IntySetting.updateSortSeed(sortSeed)
        loadAgents()
    }

    /**
     * 后台静默刷新数据
     * 用于在进入页面时静默更新数据，不影响用户当前浏览
     */
    private fun loadAgentsSilently() {
        if (_isLoading.value) return

        viewModelScope.launch(Dispatchers.IO) {
            try {
                EasyLog.log("loadAgentsSilently - 开始静默刷新第一页数据")
                val result = agentApi.recommendAgents(
                    page = 1,
                    pageSize = 10,
                    sort_seed = sortSeed.toString()
                )

                when (result) {
                    is HttpResult.Success -> {
                        result.data.list?.let { agents ->
                            if (agents.isNotEmpty()) {
                                // 静默更新UI和缓存，不显示加载状态
                                agentList.clear()
                                agentList.addAll(agents)
                                EasyLog.log("loadAgentsSilently - 静默更新成功: ${agents.size}个")

                                // 更新缓存
                                AgentCacheManager.cacheAgents(agents)
                                AppStartupManager.updateCachedAgents(agents)

                                // 设置第一个agent给chatViewModel
                                chatViewModel?.setAgentInfo(agentList.firstOrNull())
                            } else {
                                EasyLog.log("loadAgentsSilently - 第一页数据为空")
                            }
                        }
                    }

                    is HttpResult.Failure -> {
                        EasyLog.log("loadAgentsSilently - 静默刷新失败: ${result.message}")
                    }
                }
            } catch (e: Exception) {
                EasyLog.log("loadAgentsSilently - 静默刷新异常: ${e.message}")
            }
        }
    }

    fun loadMoreAgents() {
        if (!_isLoading.value && hasMoreData) {
            EasyLog.log("loadMoreAgents - 开始加载第${currentPage + 1}页")
            currentPage++
            loadAgents()
        } else {
            EasyLog.log("loadMoreAgents - 跳过加载: isLoading=${_isLoading.value}, hasMoreData=$hasMoreData")
        }
    }


    /**
     * 加载agents数据
     */
    private fun loadAgents() {
        if (_isLoading.value) return

        _isLoading.update { true }
        EasyLog.log("loadAgents - page: $currentPage")
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val result = agentApi.recommendAgents(
                    page = currentPage,
                    pageSize = 10,
                    sort_seed = sortSeed.toString()
                )
                EasyLog.log("loadAgents - API响应: $result")

                when (result) {
                    is HttpResult.Success -> {
                        result.data.list?.let { agents ->
                            if (agents.isEmpty()) {
                                hasMoreData = false
                                EasyLog.log("loadAgents - 第${currentPage}页数据为空，没有更多数据")
                            } else {
                                // 第一页数据替换，其他页数据追加
                                if (currentPage == 1) {
                                    // 确保清空列表，避免与缓存数据重复
                                    agentList.clear()
                                    agentList.addAll(agents)
                                    EasyLog.log("loadAgents - 替换第一页数据: ${agents.size}个，总计: ${agentList.size}个")

                                    // 缓存第一页数据并更新AppStartupManager的缓存
                                    AgentCacheManager.cacheAgents(agents)
                                    AppStartupManager.updateCachedAgents(agents)
                                    chatViewModel?.setAgentInfo(agentList.firstOrNull())
                                } else {
                                    agentList.addAll(agents)
                                    EasyLog.log("loadAgents - 追加第${currentPage}页数据: ${agents.size}个，总计: ${agentList.size}个")
                                }
                            }
                        } ?: run {
                            EasyLog.log("loadAgents - 第${currentPage}页返回空列表")
                            if (currentPage > 1) {
                                hasMoreData = false
                            }
                        }
                    }

                    is HttpResult.Failure -> {
                        EasyLog.log("loadAgents - 第${currentPage}页加载失败: ${result.message}")
                        // 如果加载失败，回退页码
                        if (currentPage > 1) {
                            currentPage--
                        }
                        // 如果是第一页失败，可能需要重新加载
                        if (currentPage == 1) {
                            EasyLog.log("loadAgents - 第一页加载失败，可能需要重新加载")
                        }
                    }
                }
            } catch (e: Exception) {
                EasyLog.log("loadAgents - 第${currentPage}页加载异常: ${e.message}")
                // 如果加载失败，回退页码
                if (currentPage > 1) {
                    currentPage--
                }
            }
            _isLoading.update { false }

            EasyLog.log("loadAgents - 完成，当前列表大小: ${agentList.size}")
        }
    }

    fun selectTab(tab: Int) {
        // 防止数组越界，确保tab索引在有效范围内
        val tabEntries = HomeTabIndex.entries.toTypedArray()
        if (tab < 0 || tab >= tabEntries.size) {
            EasyLog.log(
                "selectTab - 无效的tab索引: $tab, 有效范围: 0-${tabEntries.size - 1}",
                priority = EasyLog.ERROR
            )
            return
        }
        _selectedTab.value = tabEntries[tab]
        when (_selectedTab.value) {
            HomeTabIndex.Conversation -> {
                chatViewModel?.getConversations()
            }

            HomeTabIndex.Profile -> {
                // 使用refreshCreatedAgentsListIfOnTab()来避免重复请求
                // 这样可以在一个地方统一管理Profile tab的数据刷新逻辑
                refreshCreatedAgentsListIfOnTab()
            }

            else -> {

            }
        }
    }

    fun setChatViewModel(chatViewModel: ChatViewModel) {
        this.chatViewModel = chatViewModel

        chatViewModel.setAgentInfo(agentList.firstOrNull())
    }


    fun updateCurrentChatPageIndex(index: Int) {
        _currentChatPageIndex.value = index
        EasyLog.log("Updated current chat page index to: $index")
    }

    /**
     * 接口请求获取用户信息
     */
    fun getUserProfile() {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val userProfile = IntyUserProfileSDK.getUserProfile()
                if (userProfile != null) {
                    _userProfile.value = userProfile
                    // 更新本地缓存
                    UserProfileManager.saveUserProfile(userProfile)
                    EasyLog.log("Updated user profile from server: ${userProfile.nickname}")
                } else {
                    EasyLog.log("getUserProfile failure: Failed to get user profile", EasyLog.ERROR)
                }
            } catch (e: Exception) {
                EasyLog.log("getUserProfile exception: ${e.message}", priority = EasyLog.ERROR)
            }
        }
    }

    override fun onCleared() {
        super.onCleared()

        TheRouter.removeActionInterceptor(Constant.ACTION_USER_PROFILE_CHANGED, userProfileChanged)
    }


    //感知接口获取到的用户订阅状态
    val vipStatusFlow = BillingRepository.vipStatusFlow
    val vipPlanFlow = BillingRepository.plansFlow

    /**
     * 异步更新订阅计划列表和会员状态
     */
    fun updatePlans() {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                EasyLog.log("BillingRepository MainViewModel 开始更新会员状态...")

                // 等待BillingRepository初始化完成
                var retryCount = 0
                while (!BillingRepository.isInitialized() && retryCount < 10) {
                    delay(500) // 等待500ms
                    retryCount++
                }

                if (!BillingRepository.isInitialized()) {
                    EasyLog.log("BillingRepository MainViewModel BillingRepository 初始化超时，跳过更新")
                    return@launch
                }

                // 检查BillingRepository是否已连接
                if (!BillingRepository.isConnected()) {
                    EasyLog.log("BillingRepository MainViewModel BillingRepository 未连接，跳过更新")
                    return@launch
                }

                BillingRepository.fetchRemote()
                EasyLog.log("BillingRepository MainViewModel 会员状态更新完成")
            } catch (e: kotlinx.coroutines.CancellationException) {
                EasyLog.log("BillingRepository MainViewModel Member status update cancelled: ${e.message}")
                // 协程被取消是正常情况，不需要特殊处理
            } catch (e: Exception) {
                EasyLog.log(
                    "BillingRepository MainViewModel Member status update failed: ${e.message}",
                    EasyLog.ERROR
                )
                // 不影响主流程，静默处理
            }
        }
    }

    fun getUserCreatedAgents() {
        EasyLog.log("getUserCreatedAgents - Loading first page")
        currentUserAgentsPage = 0
        hasMoreUserAgents = true

        // 如果已经有数据，则不立即清空，保持显示已有数据，等加载成功后再更新
        if (userCreatedAgents.isNotEmpty()) {
            EasyLog.log("getUserCreatedAgents - 已有数据，后台刷新，不立即清空")
            loadUserCreatedAgentsSilently()
        } else {
            // 没有数据时才清空并显示loading
            EasyLog.log("getUserCreatedAgents - 无数据，清空并显示loading")
            userCreatedAgents.clear()
            loadUserCreatedAgents()
        }
    }

    fun loadMoreUserCreatedAgents() {
        if (!_isLoadingUserAgents.value && hasMoreUserAgents) {
            currentUserAgentsPage++
            loadUserCreatedAgents()
        }
    }

    private fun loadUserCreatedAgentsSilently() {
        if (_isLoadingUserAgents.value) return

        EasyLog.log("loadUserCreatedAgentsSilently - 静默刷新，不显示loading")
        val skip = currentUserAgentsPage * 10
        EasyLog.log("loadUserCreatedAgentsSilently - page: $currentUserAgentsPage, skip: $skip")

        viewModelScope.launch(Dispatchers.IO) {
            try {
                val result = agentApi.getUserCreatedAgents(skip, 10)
                EasyLog.log("loadUserCreatedAgentsSilently API result = $result")

                when (result) {
                    is HttpResult.Success -> {
                        if (result.data.isEmpty()) {
                            hasMoreUserAgents = false
                            EasyLog.log("loadUserCreatedAgentsSilently - No more user created agents to load")
                        } else {
                            // 静默更新数据，直接替换
                            userCreatedAgents.clear()
                            userCreatedAgents.addAll(result.data)
                            EasyLog.log("loadUserCreatedAgentsSilently - 静默更新数据: ${result.data.size}个")
                        }
                    }

                    is HttpResult.Failure -> {
                        EasyLog.log(
                            "loadUserCreatedAgentsSilently - API failure: ${result.message}",
                            priority = EasyLog.ERROR
                        )
                    }
                }
            } catch (e: Exception) {
                EasyLog.log(
                    "loadUserCreatedAgentsSilently exception: ${e.message}",
                    priority = EasyLog.ERROR
                )
            }
        }
    }

    private fun loadUserCreatedAgents() {
        if (_isLoadingUserAgents.value) return

        _isLoadingUserAgents.value = true
        val skip = currentUserAgentsPage * 10
        EasyLog.log("loadUserCreatedAgents - page: $currentUserAgentsPage, skip: $skip")

        viewModelScope.launch(Dispatchers.IO) {
            try {
                val result = agentApi.getUserCreatedAgents(skip, 10)
                EasyLog.log("loadUserCreatedAgents API result = $result")

                when (result) {
                    is HttpResult.Success -> {
                        if (result.data.isEmpty()) {
                            hasMoreUserAgents = false
                            EasyLog.log("No more user created agents to load")
                        } else {
                            if (currentUserAgentsPage == 0) {
                                // 第一页，直接替换（这里才清空并替换数据）
                                userCreatedAgents.clear()
                                userCreatedAgents.addAll(result.data)
                                EasyLog.log("loadUserCreatedAgents - 替换第一页数据: ${result.data.size}个")
                            } else {
                                // 后续页，追加到现有列表
                                userCreatedAgents.addAll(result.data)
                                EasyLog.log("loadUserCreatedAgents - 追加第${currentUserAgentsPage + 1}页数据: ${result.data.size}个，总计: ${userCreatedAgents.size}个")
                            }
                        }
                    }

                    is HttpResult.Failure -> {
                        EasyLog.log(
                            "loadUserCreatedAgents - API failure: ${result.message}",
                            priority = EasyLog.ERROR
                        )
//                        showNetworkAwareError(result.message)
                        // If loading failed, rollback page counter
                        if (currentUserAgentsPage > 0) {
                            currentUserAgentsPage--
                        }
                    }
                }
            } catch (e: Exception) {
                EasyLog.log(
                    "loadUserCreatedAgents exception: ${e.message}",
                    priority = EasyLog.ERROR
                )
                EasyLog.log(e)
                // If loading failed, rollback page counter
                if (currentUserAgentsPage > 0) {
                    currentUserAgentsPage--
                }
            }
            _isLoadingUserAgents.value = false
        }
    }

    fun refreshCreatedAgentsListIfOnTab() {
        if (_selectedTab.value == HomeTabIndex.Profile) {
            // 如果已经在加载中，避免重复请求
            if (!_isLoadingUserAgents.value) {
                EasyLog.log("refreshCreatedAgentsListIfOnTab - 刷新Profile tab数据")
                getUserCreatedAgents()
            } else {
                EasyLog.log("refreshCreatedAgentsListIfOnTab - 跳过刷新，正在加载中")
            }
        }
    }

    /**
     * 创建Ai Agent的接口
     */
    fun createAgent(
        request: CreateAgentRequest,
        onSuccess: (AgentInfo) -> Unit,
        onError: (String) -> Unit,
    ) {
        EasyLog.log("createAgent: ${request.name}")
        EasyLog.log("createAgent request full details: $request")
        EasyLog.log("createAgent avatar URL: ${request.avatar}")
        launchWithNetCheck {
            try {
                val result = agentApi.createAgent(request)
                EasyLog.log("createAgent = $result")

                withContext(Dispatchers.Main) {
                    when (result) {
                        is HttpResult.Success -> {
                            EasyLog.log("createAgent success: ${result.data}")
                            // 刷新用户创建的角色列表
                            refreshCreatedAgentsListIfOnTab()
                            onSuccess(result.data)
                        }

                        is HttpResult.Failure -> {
                            EasyLog.log("createAgent error: $result", priority = EasyLog.ERROR)
                            val errorMessage =
                                result.message.ifBlank { "Creation failed, please check network connection" }
                            onError(errorMessage)
                        }
                    }
                }
            } catch (e: retrofit2.HttpException) {
                // 专门处理HTTP异常
                EasyLog.log(
                    "createAgent HTTP Exception: ${e.code()} - ${e.message()}",
                    EasyLog.ERROR
                )
                val errorMessage = handleHttpException(e, "create")
                withContext(Dispatchers.Main) {
                    onError(errorMessage)
                }
            } catch (e: Exception) {
                EasyLog.log("createAgent exception: ${e.message}", priority = EasyLog.ERROR)
                EasyLog.log(e)
                val errorMessage = handleGeneralException(e, "create")
                withContext(Dispatchers.Main) {
                    onError(errorMessage)
                }
            }
        }
    }

    // 新增：用户登出方法
    fun logout() {
        EasyLog.log("User logout - clearing all data")

        // 清理内存数据
        agentList.clear()
        followingAgents.clear()
        userCreatedAgents.clear()
        _userProfile.value = UserProfile()
        chatViewModel?.clearAllData()

        // 清理本地存储（这会切换到游客模式）
        IntySetting.logout()
        UserProfileManager.clearUserProfile()

        // 清除凭证状态 - 通知所有凭证提供者清除存储的凭证会话
        // 参考: https://developer.android.com/identity/sign-in/credential-manager-siwg#handle-sign-out
        viewModelScope.launch {
            try {
                clearCredentialState(AppEnv.context)
                EasyLog.log("Credential state cleared successfully during logout")
            } catch (e: Exception) {
                EasyLog.log(
                    "Failed to clear credential state during logout: ${e.message}",
                    EasyLog.ERROR
                )
            }
        }

        // 切换到游客模式后，只加载本地数据，不进行网络请求
        loadGuestModeData()
        EasyLog.log("User logged out successfully - switched to guest mode")
    }

    // 游客模式数据加载，不涉及需要认证的API调用
    private fun loadGuestModeData() {
        EasyLog.log("Loading guest mode data")

        // 只加载不需要认证的数据
        viewModelScope.launch {
            try {
                // 可以在这里加载一些公开的推荐数据等
                // 但暂时保持简单，只更新UI状态
                _userProfile.value = UserProfile()
                EasyLog.log("Guest mode data loaded successfully")
            } catch (e: Exception) {
                EasyLog.log("Failed to load guest mode data: ${e.message}", EasyLog.ERROR)
            }
        }
    }

    fun deleteAgent(
        agentId: String,
        onSuccess: () -> Unit,
        onError: (String) -> Unit,
    ) {
        EasyLog.log("deleteAgent: $agentId")
        launchWithNetCheck {
            try {
                val result = agentApi.deleteAgent(agentId)
                EasyLog.log("deleteAgent = $result")

                withContext(Dispatchers.Main) {
                    when (result) {
                        is HttpResult.Success -> {
                            EasyLog.log("deleteAgent success: ${result.data}")
                            // 从用户创建的角色列表中移除
                            userCreatedAgents.removeAll { it.id == agentId }
                            // 从主列表中移除（如果存在）
                            agentList.removeAll { it.id == agentId }
                            // 从关注列表中移除（如果存在）
                            followingAgents.removeAll { it.id == agentId }

                            // 同步更新缓存
                            AgentCacheManager.removeAgent(agentId)

                            ToastUtils.showToast(R.string.character_deleted_successfully)
                            onSuccess()
                        }

                        is HttpResult.Failure -> {
                            EasyLog.log("deleteAgent error: $result", priority = EasyLog.ERROR)
                            val errorMessage = result.message.ifBlank {
                                AppEnv.context.getString(
                                    R.string.operation_failed_check_network,
                                    AppEnv.context.getString(R.string.delete_failed),
                                    AppEnv.context.getString(R.string.check_network_connection)
                                )
                            }
                            ToastUtils.showToast(R.string.delete_failed_with_reason, errorMessage)
                            onError(errorMessage)
                        }
                    }
                }
            } catch (e: retrofit2.HttpException) {
                // 专门处理HTTP异常
                EasyLog.log(
                    "deleteAgent HTTP Exception: ${e.code()} - ${e.message()}",
                    EasyLog.ERROR
                )
                val errorMessage = handleHttpException(e, "delete")
                withContext(Dispatchers.Main) {
                    ToastUtils.showToast(errorMessage)
                    onError(errorMessage)
                }
            } catch (e: Exception) {
                EasyLog.log("deleteAgent exception: ${e.message}", priority = EasyLog.ERROR)
                EasyLog.log(e)
                val errorMessage = handleGeneralException(e, "delete")
                withContext(Dispatchers.Main) {
                    ToastUtils.showToast(errorMessage)
                    onError(errorMessage)
                }
            }
        }
    }

    fun updateAgent(
        agentId: String,
        request: CreateAgentRequest,
        onSuccess: (AgentInfo) -> Unit,
        onError: (String) -> Unit,
    ) {
        EasyLog.log("updateAgent: $agentId")
        launchWithNetCheck {
            try {
                val result = agentApi.updateAgent(agentId, request)
                EasyLog.log("updateAgent = $result")

                withContext(Dispatchers.Main) {
                    when (result) {
                        is HttpResult.Success -> {
                            EasyLog.log("updateAgent success: ${result.data}")
                            // 刷新用户创建的角色列表
                            refreshCreatedAgentsListIfOnTab()
                            // Toast removed to avoid duplicate - handled by calling activity
                            onSuccess(result.data)
                        }

                        is HttpResult.Failure -> {
                            EasyLog.log("updateAgent error: $result", priority = EasyLog.ERROR)
                            val errorMessage = result.message.ifBlank {
                                AppEnv.context.getString(
                                    R.string.operation_failed_check_network,
                                    AppEnv.context.getString(R.string.update_failed),
                                    AppEnv.context.getString(R.string.check_network_connection)
                                )
                            }
                            ToastUtils.showToast(R.string.update_failed_with_reason, errorMessage)
                            onError(errorMessage)
                        }
                    }
                }
            } catch (e: retrofit2.HttpException) {
                // 专门处理HTTP异常
                EasyLog.log(
                    "updateAgent HTTP Exception: ${e.code()} - ${e.message()}",
                    EasyLog.ERROR
                )
                val errorMessage = handleHttpException(e, "update")
                withContext(Dispatchers.Main) {
                    ToastUtils.showToast(errorMessage)
                    onError(errorMessage)
                }
            } catch (e: Exception) {
                EasyLog.log("updateAgent exception: ${e.message}", priority = EasyLog.ERROR)
                EasyLog.log(e)
                val errorMessage = handleGeneralException(e, "update")
                withContext(Dispatchers.Main) {
                    ToastUtils.showToast(errorMessage)
                    onError(errorMessage)
                }
            }
        }
    }

    /**
     * 检查app版本更新
     */
    val needForceUpgrade = MutableStateFlow<AppVersionRsp.AppVersionData?>(null)
    private fun checkAppVersion() = launchWithNetCheck {
        val result = commonApi.checkAppUpgrade()
        when (result) {
            is HttpResult.Success -> {
                val rsp = result.data
                if (rsp.update_required && rsp.force_update) {
                    //有更新，且需要强制更新
                    needForceUpgrade.emit(rsp)
                }
                IntySetting.setAppUpdateTips(rsp.update_required)
                IntySetting.setAppGooglePlayUrl(rsp.download_url ?: "")
            }

            is HttpResult.Failure -> {
                EasyLog.log(result.message, EasyLog.WARN)
            }
        }
    }
}
