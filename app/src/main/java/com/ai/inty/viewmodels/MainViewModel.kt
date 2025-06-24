package com.ai.inty.viewmodels

import android.content.Context
import android.content.Intent
import androidx.compose.runtime.mutableStateListOf
import androidx.lifecycle.viewModelScope
import com.ai.inty.Constant
import com.ai.inty.MainActivity
import com.ai.inty.base.BaseActivityViewModel
import com.ai.inty.beans.AgentInfo
import com.ai.inty.beans.CreateAgentRequest
import com.ai.inty.beans.CreateAgentResponse
import com.ai.inty.beans.CreateGuestReq
import com.ai.inty.beans.SysMsgItem
import com.ai.inty.beans.TokenBean
import com.ai.inty.beans.UserProfile
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
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext


enum class HomeTabIndex {
    Chat,
    Conversions,
    Add,
    Suggest,
    My
}

class MainViewModel: BaseActivityViewModel() {

    val userApi: IUserApi = TheRouter.get(IUserApi::class.java)!!
    val agentApi: IAgentApi = TheRouter.get(IAgentApi::class.java)!!
    val userApi2: IUserApi2 = TheRouter.get(IUserApi2::class.java)!!

    val agentList = mutableStateListOf<AgentInfo>()
    val followingAgents = mutableStateListOf<AgentInfo>()
    val userCreatedAgents = mutableStateListOf<AgentInfo>()

    private val _selectedTab = MutableStateFlow(HomeTabIndex.Chat)
    val selectedTab = _selectedTab.asStateFlow()

    private val _selectedConversionsTab = MutableStateFlow(ConversionsPageTab.TabMessage)
    val selectedConversionsTab = _selectedConversionsTab.asStateFlow()

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
        EasyLog.log("getAgents")
        viewModelScope.launch(Dispatchers.IO) {

            val result = agentApi.recommendAgents(0, 10)
            EasyLog.log("getAgents = $result")

            when (result) {
                is HttpResult.Success -> {
                    result.data.list?.let { agents ->
                        agentList.addAll(agents)
                    }
                }
                is HttpResult.Failure -> {
                    showSnackbar(result.message)
                }
            }

            EasyLog.log("Agents = $agentList")

            chatViewModel?.setAgentInfo(agentList.firstOrNull())
        }
    }

    fun selectTab(tab: Int) {
        _selectedTab.value = HomeTabIndex.entries.toTypedArray()[tab]
        when (_selectedTab.value) {
            HomeTabIndex.Conversions -> {
                chatViewModel?.getConversions()
                getSysMsgs()
            }
            HomeTabIndex.My -> {
                // Temporarily commented out to isolate crash issue
                // getUserCreatedAgents()
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
                getFollowingAgents()
            }
            else -> {}
        }
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
                        EasyLog.log("getUserProfile failure: ${result.message}", priority = EasyLog.ERROR)
                        withContext(Dispatchers.Main) {
                            showSnackbar(result.message)
                        }
                    }
                }
            } catch (e: Exception) {
                EasyLog.log("getUserProfile exception: ${e.message}", priority = EasyLog.ERROR)
                EasyLog.log(e)
                withContext(Dispatchers.Main) {
                    showSnackbar("获取用户信息失败: ${e.message}")
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
                    EasyLog.log("Fetching FCM registration token failed, ${task.exception}", EasyLog.ERROR)
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
                    // Send broadcast to update UI
                    val intent = Intent("FOLLOW_STATE_CHANGED")
                    LocalBroadcastManager.getInstance(AppEnv.context).sendBroadcast(intent)
                    // Refresh following list if on conversions tab
                    refreshFollowingListIfOnTab()
                }
                is HttpResult.Failure -> {
                    EasyLog.log("followAgent error: $result", priority = EasyLog.ERROR)
                    showSnackbar(result.message)
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
                    // Send broadcast to update UI
                    val intent = Intent("FOLLOW_STATE_CHANGED")
                    LocalBroadcastManager.getInstance(AppEnv.context).sendBroadcast(intent)
                }
                is HttpResult.Failure -> {
                    EasyLog.log("unfollowAgent error: $result", priority = EasyLog.ERROR)
                    showSnackbar(result.message)
                }
            }
        }
    }
    
    fun refreshFollowingListIfOnTab() {
        if (_selectedTab.value == HomeTabIndex.Conversions && 
            _selectedConversionsTab.value == ConversionsPageTab.Following) {
            getFollowingAgents()
        }
    }
    
    fun getUserCreatedAgents() {
        EasyLog.log("getUserCreatedAgents - Starting API call")
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val result = agentApi.getUserCreatedAgents(0, 10)
                EasyLog.log("getUserCreatedAgents API result = $result")
                
                when (result) {
                    is HttpResult.Success -> {
                        EasyLog.log("getUserCreatedAgents - Success: Found ${result.data.size} agents")
                        userCreatedAgents.clear()
                        userCreatedAgents.addAll(result.data)
                        EasyLog.log("getUserCreatedAgents - Updated userCreatedAgents list with ${userCreatedAgents.size} items")
                    }
                    is HttpResult.Failure -> {
                        EasyLog.log("getUserCreatedAgents - API failure: ${result.message}", priority = EasyLog.ERROR)
                        showSnackbar(result.message)
                    }
                }
            } catch (e: Exception) {
                EasyLog.log("getUserCreatedAgents - Exception occurred: ${e.message}", priority = EasyLog.ERROR)
                EasyLog.log(e)
                showSnackbar("Failed to load created agents: ${e.message}")
            }
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
                            val errorMessage = if (result.message.isBlank()) "创建失败，请检查网络连接" else result.message
                            onError(errorMessage)
                        }
                    }
                }
            } catch (e: Exception) {
                EasyLog.log("createAgent exception: ${e.message}", priority = EasyLog.ERROR)
                EasyLog.log(e)
                val errorMessage = when {
                    e.message?.contains("timeout", ignoreCase = true) == true -> "网络超时，请稍后重试"
                    e.message?.contains("network", ignoreCase = true) == true -> "网络连接失败，请检查网络"
                    e.message?.contains("json", ignoreCase = true) == true -> "数据格式错误，请稍后重试"
                    else -> "创建失败：${e.message ?: "未知错误"}"
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
        
        // 清理本地存储
        IntySetting.logout()
        UserProfileManager.clearUserProfile()
        
        // 清理内存数据
        agentList.clear()
        sysMsgs.clear()
        _userProfile.value = UserProfile()
        chatViewModel?.let { chat ->
            chat.clearAllData()
        }
        EasyLog.log("User logged out successfully")
        
        // 重启应用以完全清理状态
        val intent = Intent(AppEnv.context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        }
        AppEnv.context.startActivity(intent)
    }
}