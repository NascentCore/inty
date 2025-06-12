package com.ai.inty.viewmodels

import android.content.Context
import androidx.compose.runtime.mutableStateListOf
import androidx.lifecycle.viewModelScope
import com.ai.inty.Constant
import com.ai.inty.base.BaseActivityViewModel
import com.ai.inty.beans.AgentInfo
import com.ai.inty.beans.CreateGuestReq
import com.ai.inty.beans.SysMsgItem
import com.ai.inty.beans.TokenBean
import com.ai.inty.beans.UserProfile
import com.ai.inty.home.ConversionsPageTab
import com.ai.inty.net.IAgentApi
import com.ai.inty.net.IUserApi
import com.ai.inty.net.IUserApi2
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

        if (IntySetting.isLogin()) {
            onLoginSuccess()
        } else {
            createGuest() {
                onLoginSuccess()
            }
        }

        TheRouter.addActionInterceptor(Constant.ACTION_USER_PROFILE_CHANGED, userProfileChanged)
    }

    private fun onLoginSuccess() {
        getAgents()
        getUserProfile()
        regFCM()
        getSysMsgs()
    }

    fun createGuest(onSuccess: () -> Unit) {
        EasyLog.log("getAgents")
        viewModelScope.launch(Dispatchers.IO) {
            val result = userApi.createGuest(CreateGuestReq(device_id = AppEnv.DeviceID, AppEnv.locale.language))
            EasyLog.log("create guest = $result", EasyLog.INFO)
            when (result) {
                is HttpResult.Success -> {
                    IntySetting.login(true, result.data.guest_id, result.data.token)
                    onSuccess()
                }
                is HttpResult.Failure -> {
                    EasyLog.log("error: $result", priority = EasyLog.ERROR)
                    showSnackbar(result.message)

                }
            }
        }
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
    }


    fun getUserProfile() {
        viewModelScope.launch(Dispatchers.IO) {
            val result = userApi2.getUserProfile()

            when (result) {
                is HttpResult.Success -> {
                    _userProfile.value = result.data
                }

                is HttpResult.Failure -> {
                    showSnackbar(result.message)
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
}