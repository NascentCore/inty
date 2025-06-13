package com.ai.inty.viewmodels

import androidx.lifecycle.viewModelScope
import com.ai.inty.base.BaseActivityViewModel
import com.ai.inty.beans.AgentInfo
import com.ai.inty.net.IChatApi
import com.architecture.httplib.core.HttpResult
import com.inty.utils.log.EasyLog
import com.therouter.TheRouter
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class AgentInfoViewModel: BaseActivityViewModel() {

    private val _agentInfo = MutableStateFlow<AgentInfo?>(null)
    val agentInfo = _agentInfo.asStateFlow()

    val chatApi = TheRouter.get(IChatApi::class.java)!!

    fun setAgentID(agentId: String) {
        viewModelScope.launch(Dispatchers.IO) {
            val result = chatApi.getAgentInfo(agentId)
            EasyLog.log("getAgentInfo = $result")
            when (result) {
                is HttpResult.Success -> {
                    setAgentInfo(result.data)

                }
                is HttpResult.Failure -> {
                    showSnackbar(result.message)
                }
            }
        }

    }

    fun setAgentInfo(agentInfo: AgentInfo?) {
        EasyLog.log("agent = $agentInfo")
        if (_agentInfo.value == agentInfo) {
            return
        }
        _agentInfo.value = agentInfo
    }

}