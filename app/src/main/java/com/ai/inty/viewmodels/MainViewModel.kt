package com.ai.inty.viewmodels

import android.content.Context
import android.content.Intent
import androidx.compose.runtime.mutableStateListOf
import androidx.lifecycle.viewModelScope
import androidx.localbroadcastmanager.content.LocalBroadcastManager
import com.ai.inty.Constant
import com.ai.inty.R
import com.ai.inty.base.BaseActivityViewModel
import com.ai.inty.base.ToastUtils
import com.ai.inty.beans.AgentInfo
import com.ai.inty.beans.CreateAgentRequest
import com.ai.inty.beans.GenerateBackgroundRequest
import com.ai.inty.beans.GenerateBackgroundResponse
import com.ai.inty.beans.SysMsgItem
import com.ai.inty.beans.TokenBean
import com.ai.inty.beans.UserProfile
//import com.ai.inty.billing.BillingRepository
import com.ai.inty.home.ConversionsPageTab
import com.ai.inty.net.IAgentApi
import com.ai.inty.net.IUserApi
import com.ai.inty.net.IUserApi2
import com.ai.inty.utils.UserProfileManager
import com.architecture.httplib.core.HttpResult
import com.google.android.gms.tasks.OnCompleteListener
import com.google.firebase.messaging.FirebaseMessaging
import com.inty.utils.AppEnv
import com.inty.utils.log.EasyLog
import com.inty.utils.storage.IntySetting
import com.therouter.TheRouter
import com.therouter.router.Navigator
import com.therouter.router.action.interceptor.ActionInterceptor
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext


enum class HomeTabIndex {
    Chat,
    Conversions,
    Add,
    Suggest,
    My
}

class MainViewModel : BaseActivityViewModel() {

    val userApi: IUserApi = TheRouter.get(IUserApi::class.java)!!
    val agentApi: IAgentApi = TheRouter.get(IAgentApi::class.java)!!
    val userApi2: IUserApi2 = TheRouter.get(IUserApi2::class.java)!!

    val agentList = mutableStateListOf<AgentInfo>()
    val followingAgents = mutableStateListOf<AgentInfo>()
    val userCreatedAgents = mutableStateListOf<AgentInfo>()

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

    private val _selectedConversionsTab = MutableStateFlow(ConversionsPageTab.TabMessage)
    val selectedConversionsTab = _selectedConversionsTab.asStateFlow()

    private val _currentChatPageIndex = MutableStateFlow(0)
    val currentChatPageIndex = _currentChatPageIndex.asStateFlow()

    private var chatViewModel: ChatViewModel? = null

    private val _userProfile = MutableStateFlow<UserProfile>(UserProfile())
    val userProfile = _userProfile.asStateFlow()

    val sysMsgs = mutableStateListOf<SysMsgItem>()


    val userProfileChanged = object : ActionInterceptor() {
        override fun handle(context: Context, navigator: Navigator): Boolean {
            getUserProfile()

            return super.handle(context, navigator)
        }
    }

    init {
        EasyLog.log("MainViewModel init - current user: ${IntySetting.getCurUserID()}")

        // 直接加载业务数据，登录状态已在 SplashActivity 中处理
        loadBusinessData()

        TheRouter.addActionInterceptor(Constant.ACTION_USER_PROFILE_CHANGED, userProfileChanged)
    }

    private fun loadBusinessData() {
        // 优先从本地缓存获取用户信息
        if (UserProfileManager.hasUserProfile()) {
            _userProfile.value = UserProfileManager.getUserProfile()
            EasyLog.log("Loaded user profile from cache: ${_userProfile.value.nickname}")
        }

        // 加载业务数据
        getAgents()
        getUserProfile() // 从服务器获取最新信息并更新本地缓存
        regFCM()
        getSysMsgs()
    }

    fun getAgents() {
        EasyLog.log("getAgents - Loading first page")
        currentPage = 1
        agentList.clear()
        hasMoreData = true
        loadAgents()
    }

    fun loadMoreAgents() {
        if (!_isLoading.value && hasMoreData) {
            currentPage++
            loadAgents()
        }
    }

    private fun loadAgents() {
        if (_isLoading.value) return

        _isLoading.value = true
        EasyLog.log("loadAgents - page: $currentPage")
        viewModelScope.launch(Dispatchers.IO) {
            val result = agentApi.recommendAgents(currentPage, 10)
            EasyLog.log("loadAgents = $result")

            when (result) {
                is HttpResult.Success -> {
                    result.data.list?.let { agents ->
                        if (agents.isEmpty()) {
                            hasMoreData = false
                            EasyLog.log("No more agents to load")
                        } else {
                            agentList.addAll(agents)
                            EasyLog.log("Added ${agents.size} agents, total: ${agentList.size}")
                            // 只在第一页加载时设置chatViewModel
                            if (currentPage == 1) {
                                chatViewModel?.setAgentInfo(agentList.firstOrNull())
                            }
                        }
                    }
                }

                is HttpResult.Failure -> {
                    showSnackbar(result.message)
                    // 如果加载失败，回退页码
                    if (currentPage > 1) {
                        currentPage--
                    }
                }
            }
            _isLoading.value = false

            EasyLog.log("Agents = $agentList")
        }
    }

    fun selectTab(tab: Int) {
        _selectedTab.value = HomeTabIndex.entries.toTypedArray()[tab]
        when (_selectedTab.value) {
            HomeTabIndex.Conversions -> {
                chatViewModel?.getConversions()
                getSysMsgs()
                // 如果切换到对话页面且当前选中关注列表，则刷新关注列表
                if (_selectedConversionsTab.value == ConversionsPageTab.TabFollowing) {
                    EasyLog.log("Switching to Conversions tab while following tab is selected - refreshing following agents")
                    getFollowingAgents()
                }
            }

            HomeTabIndex.My -> {
                getUserCreatedAgents()
            }

            else -> {

            }
        }
    }

    fun setChatViewModel(chatViewModel: ChatViewModel) {
        this.chatViewModel = chatViewModel

        chatViewModel.setAgentInfo(agentList.firstOrNull())
    }

    fun onSelectConversionsTab(tab: ConversionsPageTab) {
        _selectedConversionsTab.value = tab
        when (tab) {
            ConversionsPageTab.TabFollowing -> {
                // 每次切换到关注列表时都刷新
                EasyLog.log("Switching to following tab - refreshing following agents")
                getFollowingAgents()
            }

            else -> {}
        }
    }

    fun updateCurrentChatPageIndex(index: Int) {
        _currentChatPageIndex.value = index
        EasyLog.log("Updated current chat page index to: $index")
    }


    fun getUserProfile() {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val result = userApi2.getUserProfile()
                EasyLog.log("getUserProfile result = $result")

                when (result) {
                    is HttpResult.Success -> {
                        _userProfile.value = result.data
                        // 更新本地缓存
                        UserProfileManager.saveUserProfile(result.data)
                        EasyLog.log("Updated user profile from server: ${result.data.nickname}")
                    }

                    is HttpResult.Failure -> {
                        EasyLog.log(
                            "getUserProfile failure: ${result.message}",
                            priority = EasyLog.ERROR
                        )
                        withContext(Dispatchers.Main) {
                            showSnackbar(result.message)
                        }
                    }
                }
            } catch (e: retrofit2.HttpException) {
                // 专门处理HTTP异常
                EasyLog.log("getUserProfile HTTP Exception: ${e.code()} - ${e.message()}", EasyLog.ERROR)
                val errorMessage = when (e.code()) {
                    401 -> "Session expired, please login again"
                    403 -> "Permission denied to access user information"
                    404 -> "User information not found"
                    429 -> "Too many requests, please try again later"
                    500 -> "Internal server error, please try again later"
                    502, 503 -> "Server temporarily unavailable, please try again later"
                    else -> "Failed to get user information (${e.code()})"
                }
                withContext(Dispatchers.Main) {
                    showSnackbar(errorMessage)
                }
            } catch (e: Exception) {
                EasyLog.log("getUserProfile exception: ${e.message}", priority = EasyLog.ERROR)
                EasyLog.log(e)
                withContext(Dispatchers.Main) {
                    showSnackbar("Failed to get user information: ${e.message}")
                }
            }
        }
    }

    override fun onCleared() {
        super.onCleared()

        TheRouter.removeActionInterceptor(Constant.ACTION_USER_PROFILE_CHANGED, userProfileChanged)
    }

    fun regFCM() {
        viewModelScope.launch {
            FirebaseMessaging.getInstance().token.addOnCompleteListener(OnCompleteListener { task ->
                if (!task.isSuccessful) {
                    EasyLog.log(
                        "Fetching FCM registration token failed, ${task.exception}",
                        EasyLog.ERROR
                    )
                    task.exception?.let { EasyLog.log(it) }
                    return@OnCompleteListener
                }

                // Get new FCM registration token
                val token = task.result

                EasyLog.log("FCM token = $token")
                viewModelScope.launch(Dispatchers.IO) {
                    val result = userApi.regFCM(TokenBean(token))
                    EasyLog.log("regFCM = $result")
                }
            })
        }
    }

    fun getSysMsgs() {
        viewModelScope.launch(Dispatchers.IO) {
            val result = userApi.getSysMsgs(1, 10)
            EasyLog.log("getSysMsgs = $result")
            when (result) {
                is HttpResult.Success -> {
                    sysMsgs.addAll(result.data.list)
                }

                is HttpResult.Failure -> {

                }
            }
        }
    }

    /**
     * 异步更新订阅计划列表和会员状态
     */
    fun updatePlans() {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                EasyLog.log("开始更新会员状态...")
//                BillingRepository.fetchRemote()
                EasyLog.log("会员状态更新完成")
            } catch (e: kotlinx.coroutines.CancellationException) {
                EasyLog.log("Member status update cancelled: ${e.message}")
                // 协程被取消是正常情况，不需要特殊处理
            } catch (e: Exception) {
                EasyLog.log("Member status update failed: ${e.message}", EasyLog.ERROR)
                // 不影响主流程，静默处理
            }
        }
    }

    fun getFollowingAgents() {
        EasyLog.log("getFollowingAgents")
        viewModelScope.launch(Dispatchers.IO) {
            val result = agentApi.getFollowingAgents(1, 10)
            EasyLog.log("getFollowingAgents = $result")

            when (result) {
                is HttpResult.Success -> {
                    followingAgents.clear()
                    result.data.list?.let { agents ->
                        followingAgents.addAll(agents)
                    }
                }

                is HttpResult.Failure -> {
                    showSnackbar(result.message)
                }
            }
        }
    }

    fun followAgent(agentId: String) {
        EasyLog.log("followAgent: $agentId")
        viewModelScope.launch(Dispatchers.IO) {
            val result = agentApi.followAgent(agentId)
            EasyLog.log("followAgent = $result")

            when (result) {
                is HttpResult.Success -> {
                    EasyLog.log("followAgent success")
                    // Update the agent list to reflect follow status
                    agentList.find { it.id == agentId }?.let { agent ->
                        val index = agentList.indexOf(agent)
                        if (index != -1) {
                            agentList[index] = agent.copy(isFollowed = true)
                        }
                    }
                    // Show success toast
                    viewModelScope.launch(Dispatchers.Main) {
                        ToastUtils.showToast(R.string.followed_successfully)
                    }
                    // Update agent state in list
                    updateAgentFollowStateInList(agentId, true)
                    // Send broadcast to update UI with required parameters
                    val intent = Intent("FOLLOW_STATE_CHANGED")
                    intent.putExtra("agentId", agentId)
                    intent.putExtra("isFollowed", true)
                    LocalBroadcastManager.getInstance(AppEnv.context).sendBroadcast(intent)
                    EasyLog.log("Sent FOLLOW_STATE_CHANGED broadcast - followed: $agentId")
                    // Refresh following list if on conversions tab
                    refreshFollowingListIfOnTab()
                }

                is HttpResult.Failure -> {
                    EasyLog.log("followAgent error: $result", priority = EasyLog.ERROR)
                    viewModelScope.launch(Dispatchers.Main) {
                        ToastUtils.showToast(R.string.follow_failed_with_reason, result.message)
                    }
                }
            }
        }
    }

    fun unfollowAgent(agentId: String) {
        EasyLog.log("unfollowAgent: $agentId")
        viewModelScope.launch(Dispatchers.IO) {
            val result = agentApi.unfollowAgent(agentId)
            EasyLog.log("unfollowAgent = $result")

            when (result) {
                is HttpResult.Success -> {
                    EasyLog.log("unfollowAgent success")
                    // Update the agent list to reflect follow status
                    agentList.find { it.id == agentId }?.let { agent ->
                        val index = agentList.indexOf(agent)
                        if (index != -1) {
                            agentList[index] = agent.copy(isFollowed = false)
                        }
                    }
                    // Remove from following list
                    followingAgents.removeAll { it.id == agentId }
                    // Show success toast
                    viewModelScope.launch(Dispatchers.Main) {
                        ToastUtils.showToast(R.string.unfollowed_successfully)
                    }
                    // Update agent state in list
                    updateAgentFollowStateInList(agentId, false)
                    // Send broadcast to update UI with required parameters
                    val intent = Intent("FOLLOW_STATE_CHANGED")
                    intent.putExtra("agentId", agentId)
                    intent.putExtra("isFollowed", false)
                    LocalBroadcastManager.getInstance(AppEnv.context).sendBroadcast(intent)
                    EasyLog.log("Sent FOLLOW_STATE_CHANGED broadcast - unfollowed: $agentId")
                }

                is HttpResult.Failure -> {
                    EasyLog.log("unfollowAgent error: $result", priority = EasyLog.ERROR)
                    viewModelScope.launch(Dispatchers.Main) {
                        ToastUtils.showToast(R.string.unfollow_failed_with_reason, result.message)
                    }
                }
            }
        }
    }

    fun refreshFollowingListIfOnTab() {
        EasyLog.log("refreshFollowingListIfOnTab - selectedTab: ${_selectedTab.value}, selectedConversionsTab: ${_selectedConversionsTab.value}")
        if (_selectedTab.value == HomeTabIndex.Conversions &&
            _selectedConversionsTab.value == ConversionsPageTab.TabFollowing
        ) {
            EasyLog.log("Refreshing following agents due to follow state change")
            getFollowingAgents()
        } else {
            EasyLog.log("Not refreshing - not on following tab")
        }
    }

    fun updateAgentFollowStateInList(agentId: String, isFollowed: Boolean) {
        EasyLog.log("Updating agent follow state in list - agentId: $agentId, isFollowed: $isFollowed")

        // 更新主列表中的agent状态
        val index = agentList.indexOfFirst { it.id == agentId }
        if (index != -1) {
            val updatedAgent = agentList[index].copy(isFollowed = isFollowed)
            agentList[index] = updatedAgent
            EasyLog.log("Updated agent in main list: ${updatedAgent.name}")
        }

        // 如果是取消关注，从关注列表中移除
        if (!isFollowed) {
            followingAgents.removeAll { it.id == agentId }
            EasyLog.log("Removed agent from following list")
        }
    }

    fun getUserCreatedAgents() {
        EasyLog.log("getUserCreatedAgents - Loading first page")
        currentUserAgentsPage = 0
        userCreatedAgents.clear()
        hasMoreUserAgents = true
        loadUserCreatedAgents()
    }

    fun loadMoreUserCreatedAgents() {
        if (!_isLoadingUserAgents.value && hasMoreUserAgents) {
            currentUserAgentsPage++
            loadUserCreatedAgents()
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
                            userCreatedAgents.addAll(result.data)
                            EasyLog.log("Added ${result.data.size} user agents, total: ${userCreatedAgents.size}")
                        }
                    }

                    is HttpResult.Failure -> {
                        EasyLog.log(
                            "loadUserCreatedAgents - API failure: ${result.message}",
                            priority = EasyLog.ERROR
                        )
                        showSnackbar(result.message)
                        // If loading failed, rollback page counter
                        if (currentUserAgentsPage > 0) {
                            currentUserAgentsPage--
                        }
                    }
                }
            } catch (e: Exception) {
                EasyLog.log(
                    "loadUserCreatedAgents - Exception occurred: ${e.message}",
                    priority = EasyLog.ERROR
                )
                EasyLog.log(e)
                showSnackbar("Failed to load created agents: ${e.message}")
                // If loading failed, rollback page counter
                if (currentUserAgentsPage > 0) {
                    currentUserAgentsPage--
                }
            }
            _isLoadingUserAgents.value = false
        }
    }

    fun refreshCreatedAgentsListIfOnTab() {
        if (_selectedTab.value == HomeTabIndex.My) {
            getUserCreatedAgents()
        }
    }

    fun createAgent(
        request: CreateAgentRequest,
        onSuccess: (AgentInfo) -> Unit,
        onError: (String) -> Unit
    ) {
        EasyLog.log("createAgent: ${request.name}")
        EasyLog.log("createAgent request full details: $request")
        EasyLog.log("createAgent avatar URL: ${request.avatar}")
        viewModelScope.launch(Dispatchers.IO) {
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
                            val errorMessage = result.message.ifBlank { "Creation failed, please check network connection" }
                            onError(errorMessage)
                        }
                    }
                }
            } catch (e: retrofit2.HttpException) {
                // 专门处理HTTP异常
                EasyLog.log("createAgent HTTP Exception: ${e.code()} - ${e.message()}", EasyLog.ERROR)
                val errorMessage = when (e.code()) {
                    400 -> "Invalid request parameters, please check your input"
                    401 -> "Session expired, please login again"
                    403 -> "Permission denied for this operation"
                    404 -> "Service not found"
                    429 -> "Too many requests, please try again later"
                    500 -> "Internal server error, please try again later"
                    502, 503 -> "Server temporarily unavailable, please try again later"
                    else -> "Network request failed (${e.code()})"
                }
                withContext(Dispatchers.Main) {
                    onError(errorMessage)
                }
            } catch (e: Exception) {
                EasyLog.log("createAgent exception: ${e.message}", priority = EasyLog.ERROR)
                EasyLog.log(e)
                val errorMessage = when {
                    e.message?.contains(
                        "timeout",
                        ignoreCase = true
                    ) == true -> "Request timeout, please try again later"

                    e.message?.contains(
                        "network",
                        ignoreCase = true
                    ) == true -> "Network connection failed, please check your connection"

                    e.message?.contains(
                        "json",
                        ignoreCase = true
                    ) == true -> "Data format error, please try again later"

                    else -> "Creation failed: ${e.message ?: "Unknown error"}"
                }
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
        sysMsgs.clear()
        _userProfile.value = UserProfile()
        chatViewModel?.clearAllData()

        // 清理本地存储（这会切换到游客模式）
        IntySetting.logout()
        UserProfileManager.clearUserProfile()

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
        onError: (String) -> Unit
    ) {
        EasyLog.log("deleteAgent: $agentId")
        viewModelScope.launch(Dispatchers.IO) {
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
                EasyLog.log("deleteAgent HTTP Exception: ${e.code()} - ${e.message()}", EasyLog.ERROR)
                val errorMessage = when (e.code()) {
                    400 -> "Invalid request parameters, please check your input"
                    401 -> "Session expired, please login again"
                    403 -> "Permission denied for this operation"
                    404 -> "Character not found"
                    429 -> "Too many requests, please try again later"
                    500 -> "Internal server error, please try again later"
                    502, 503 -> "Server temporarily unavailable, please try again later"
                    else -> "Network request failed (${e.code()})"
                }
                withContext(Dispatchers.Main) {
                    ToastUtils.showToast(errorMessage)
                    onError(errorMessage)
                }
            } catch (e: Exception) {
                EasyLog.log("deleteAgent exception: ${e.message}", priority = EasyLog.ERROR)
                EasyLog.log(e)
                val errorMessage = when {
                    e.message?.contains(
                        "timeout",
                        ignoreCase = true
                    ) == true -> "Request timeout, please try again later"

                    e.message?.contains(
                        "network",
                        ignoreCase = true
                    ) == true -> "Network connection failed, please check your connection"

                    else -> "Delete failed: ${e.message ?: "Unknown error"}"
                }
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
        onError: (String) -> Unit
    ) {
        EasyLog.log("updateAgent: $agentId")
        viewModelScope.launch(Dispatchers.IO) {
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
                EasyLog.log("updateAgent HTTP Exception: ${e.code()} - ${e.message()}", EasyLog.ERROR)
                val errorMessage = when (e.code()) {
                    400 -> "Invalid request parameters, please check your input"
                    401 -> "Session expired, please login again"
                    403 -> "Permission denied for this operation"
                    404 -> "Character not found"
                    429 -> "Too many requests, please try again later"
                    500 -> "Internal server error, please try again later"
                    502, 503 -> "Server temporarily unavailable, please try again later"
                    else -> "Network request failed (${e.code()})"
                }
                withContext(Dispatchers.Main) {
                    ToastUtils.showToast(errorMessage)
                    onError(errorMessage)
                }
            } catch (e: Exception) {
                EasyLog.log("updateAgent exception: ${e.message}", priority = EasyLog.ERROR)
                EasyLog.log(e)
                val errorMessage = when {
                    e.message?.contains(
                        "timeout",
                        ignoreCase = true
                    ) == true -> "Request timeout, please try again later"

                    e.message?.contains(
                        "network",
                        ignoreCase = true
                    ) == true -> "Network connection failed, please check your connection"

                    else -> "Update failed: ${e.message ?: "Unknown error"}"
                }
                withContext(Dispatchers.Main) {
                    ToastUtils.showToast(errorMessage)
                    onError(errorMessage)
                }
            }
        }
    }

    fun generateBackground(
        request: GenerateBackgroundRequest,
        onSuccess: (GenerateBackgroundResponse) -> Unit,
        onError: (String) -> Unit
    ) {
        EasyLog.log("generateBackground: ${request.prompt}")
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val result = agentApi.generateBackground(request)
                EasyLog.log("generateBackground = $result")

                withContext(Dispatchers.Main) {
                    when (result) {
                        is HttpResult.Success -> {
                            EasyLog.log("generateBackground success: ${result.data}")
                            onSuccess(result.data)
                        }

                        is HttpResult.Failure -> {
                            EasyLog.log(
                                "generateBackground error: $result",
                                priority = EasyLog.ERROR
                            )
                            val errorMessage = result.message.ifBlank { "Generation failed, please check network connection" }
                            onError(errorMessage)
                        }
                    }
                }
            } catch (e: retrofit2.HttpException) {
                // 专门处理HTTP异常
                EasyLog.log("generateBackground HTTP Exception: ${e.code()} - ${e.message()}", EasyLog.ERROR)
                val errorMessage = when (e.code()) {
                    400 -> "Invalid request parameters, please check your input"
                    401 -> "Session expired, please login again"
                    403 -> "Permission denied for this operation"
                    404 -> "Service not found"
                    429 -> "Too many requests, please try again later"
                    500 -> "Internal server error, please try again later"
                    502, 503 -> "Server temporarily unavailable, please try again later"
                    else -> "Network request failed (${e.code()})"
                }
                withContext(Dispatchers.Main) {
                    onError(errorMessage)
                }
            } catch (e: Exception) {
                EasyLog.log("generateBackground exception: ${e.message}", priority = EasyLog.ERROR)
                EasyLog.log(e)
                val errorMessage = when {
                    e.message?.contains(
                        "timeout",
                        ignoreCase = true
                    ) == true -> "Request timeout, please try again later"

                    e.message?.contains(
                        "network",
                        ignoreCase = true
                    ) == true -> "Network connection failed, please check your connection"

                    e.message?.contains(
                        "json",
                        ignoreCase = true
                    ) == true -> "Data format error, please try again later"

                    else -> "Generation failed: ${e.message ?: "Unknown error"}"
                }
                withContext(Dispatchers.Main) {
                    onError(errorMessage)
                }
            }
        }
    }

    /**
     * 检查账号是否有订阅需要取消，才能用来删除账号
     */
    fun checkAccountSubscribe() {
        EasyLog.log("检查账号需要取消订阅 ---> ")
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val result = userApi.userDeletionCheck()

                EasyLog.log("检查账号需要取消订阅的结果 = $result")

                withContext(Dispatchers.Main) {
                    when (result) {
                        is HttpResult.Success -> {
                            EasyLog.log("检查账号需要取消订阅的结果 success: ${result.data}")
                            if (result.data.canDelete && !result.data.activeSubscription) {
                                deleteUserAccount()
                            } else {
                                ToastUtils.showToast("Please cancel the subscription before proceeding")
                            }
                        }

                        is HttpResult.Failure -> {
                            EasyLog.log(
                                "检查账号需要取消订阅的结果 error: $result",
                                priority = EasyLog.ERROR
                            )
                            ToastUtils.showToast("Check Account Deletion Server Error !")
                        }
                    }
                }
            } catch (e: retrofit2.HttpException) {
                // 专门处理HTTP异常
                EasyLog.log("checkAccountSubscribe HTTP Exception: ${e.code()} - ${e.message()}", EasyLog.ERROR)
                val errorMessage = when (e.code()) {
                    400 -> "Invalid request parameters, please check your input"
                    401 -> "Session expired, please login again"
                    403 -> "Permission denied for this operation"
                    404 -> "Account information not found"
                    429 -> "Too many requests, please try again later"
                    500 -> "Internal server error, please try again later"
                    502, 503 -> "Server temporarily unavailable, please try again later"
                    else -> "Network request failed (${e.code()})"
                }
                withContext(Dispatchers.Main) {
                    ToastUtils.showToast(errorMessage)
                }
            } catch (e: Exception) {
                EasyLog.log(
                    "检查账号需要取消订阅 exception: ${e.message}",
                    priority = EasyLog.ERROR
                )
                EasyLog.log(e)
                val errorMessage = when {
                    e.message?.contains(
                        "timeout",
                        ignoreCase = true
                    ) == true -> "Request timeout, please try again later"

                    e.message?.contains(
                        "network",
                        ignoreCase = true
                    ) == true -> "Network connection failed, please check your connection"

                    else -> "Update failed: ${e.message ?: "Unknown error"}"
                }
                withContext(Dispatchers.Main) {
                    ToastUtils.showToast(errorMessage)
                }
            }
        }
    }

    //删除账号的结果
    val deleteAccountResultFlow = MutableStateFlow(false)

    /**
     * 删除账号的接口
     */
    private fun deleteUserAccount() {
        EasyLog.log("删除用户账号 ---> ")
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val result = userApi.userDeleteAccount()

                EasyLog.log("删除用户账号的结果 = $result")

                withContext(Dispatchers.Main) {
                    when (result) {
                        is HttpResult.Success -> {
                            EasyLog.log("删除用户账号的结果 success: ${result.data}")
                            deleteAccountResultFlow.emit(true)
                        }

                        is HttpResult.Failure -> {
                            EasyLog.log(
                                "删除用户账号的结果 error: $result",
                                priority = EasyLog.ERROR
                            )
                            ToastUtils.showToast("Account Deletion Server Error !")
                        }
                    }
                }
            } catch (e: retrofit2.HttpException) {
                // 专门处理HTTP异常
                EasyLog.log("deleteUserAccount HTTP Exception: ${e.code()} - ${e.message()}", EasyLog.ERROR)
                val errorMessage = when (e.code()) {
                    400 -> "Invalid request parameters, please check your input"
                    401 -> "Session expired, please login again"
                    403 -> "Permission denied for this operation"
                    404 -> "Account information not found"
                    429 -> "Too many requests, please try again later"
                    500 -> "Internal server error, please try again later"
                    502, 503 -> "Server temporarily unavailable, please try again later"
                    else -> "Network request failed (${e.code()})"
                }
                withContext(Dispatchers.Main) {
                    ToastUtils.showToast(errorMessage)
                }
            } catch (e: Exception) {
                EasyLog.log("删除用户账号 exception: ${e.message}", priority = EasyLog.ERROR)
                EasyLog.log(e)
                val errorMessage = when {
                    e.message?.contains(
                        "timeout",
                        ignoreCase = true
                    ) == true -> "Request timeout, please try again later"

                    e.message?.contains(
                        "network",
                        ignoreCase = true
                    ) == true -> "Network connection failed, please check your connection"

                    else -> "Update failed: ${e.message ?: "Unknown error"}"
                }
                withContext(Dispatchers.Main) {
                    ToastUtils.showToast(errorMessage)
                }
            }
        }
    }
}