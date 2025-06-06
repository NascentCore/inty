package com.ai.inty.viewmodels

import androidx.compose.runtime.mutableStateListOf
import androidx.lifecycle.viewModelScope
import com.ai.inty.base.BaseActivityViewModel
import com.ai.inty.beans.AgentInfo
import com.ai.inty.beans.CreateGuestReq
import com.ai.inty.net.IAgentApi
import com.ai.inty.net.IUserApi
import com.architecture.httplib.core.HttpResult
import com.inty.utils.AppEnv
import com.inty.utils.log.EasyLog
import com.inty.utils.storage.IntySetting
import com.therouter.TheRouter
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
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

    val agentList = mutableStateListOf<AgentInfo>()

    private val _selectedTab = MutableStateFlow(HomeTabIndex.Chat)
    val selectedTab = _selectedTab.asStateFlow()

    private var chatViewModel: ChatViewModel? = null

    init {

        if (IntySetting.isLogin()) {
            getAgents()
        } else {
            createGuest() {
                getAgents()
            }
        }
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
    }

    fun setChatViewModel(chatViewModel: ChatViewModel) {
        this.chatViewModel = chatViewModel

        chatViewModel.setAgentInfo(agentList.firstOrNull())
    }

}