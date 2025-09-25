package com.ai.inty.viewmodels

import androidx.lifecycle.viewModelScope
import com.ai.inty.base.BaseActivityViewModel
import com.ai.inty.beans.AgentInfo
import com.ai.inty.net.IAgentApi
import com.ai.inty.net.IChatApi
import com.architecture.httplib.core.HttpResult
import com.inty.utils.log.EasyLog
import com.therouter.TheRouter
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class AgentInfoViewModel : BaseActivityViewModel() {

    private val _agentInfo = MutableStateFlow<AgentInfo?>(null)
    val agentInfo = _agentInfo.asStateFlow()

    // 延迟获取依赖，避免在构造函数中立即获取导致空指针异常
    val chatApi by lazy {
        TheRouter.get(IChatApi::class.java)
            ?: throw IllegalStateException("IChatApi not found in TheRouter")
    }
    val agentApi by lazy {
        TheRouter.get(IAgentApi::class.java)
            ?: throw IllegalStateException("IAgentApi not found in TheRouter")
    }

    fun setAgentID(agentId: String) {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val result = chatApi.getAgentInfo(agentId)
                EasyLog.log("getAgentInfo = $result")
                when (result) {
                    is HttpResult.Success -> {
                        setAgentInfo(result.data)
                    }

                    is HttpResult.Failure -> {
                        showNetworkAwareError(result.message)
                    }
                }
            } catch (e: Exception) {
                EasyLog.log("setAgentID exception: ${e.message}", priority = EasyLog.ERROR)
            }
        }
    }

    fun setAgentInfo(agentInfo: AgentInfo?) {
        EasyLog.log("agent = $agentInfo")
        _agentInfo.value = agentInfo
        // Refresh agent data to get latest follower count and follow status
        agentInfo?.let { agent -> refreshAgentData(agent.id) }
    }

    private fun refreshAgentData(agentId: String) {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val result = agentApi.getAgentDetail(agentId)
                EasyLog.log("refreshAgentData = $result")
                when (result) {
                    is HttpResult.Success -> {
                        _agentInfo.value = result.data
                    }

                    is HttpResult.Failure -> {
                        showNetworkAwareError(result.message)
                    }
                }
            } catch (e: Exception) {
                EasyLog.log("refreshAgentData exception: ${e.message}", priority = EasyLog.ERROR)
            }
        }
    }
}
