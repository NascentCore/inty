package com.ai.inty.viewmodels

import ai.sxwl.android.utils.LogUtils
import androidx.lifecycle.viewModelScope
import com.ai.inty.base.BaseViewModel
import com.ai.inty.beans.AgentInfo
import com.ai.inty.net.NetServiceMgr
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class AgentInfoViewModel : BaseViewModel() {

    private val _agentInfo = MutableStateFlow<AgentInfo?>(null)
    val agentInfo = _agentInfo.asStateFlow()

    // 延迟获取依赖，避免在构造函数中立即获取导致空指针异常
    val chatApi by lazy { NetServiceMgr.getChatApi() }
    val agentApi by lazy { NetServiceMgr.getAgentApi() }

    fun setAgentID(agentId: String) {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val result = chatApi.getAgentInfo(agentId)
                LogUtils.i("getAgentInfo = $result")
                when (result) {
                    is HttpResult.Success -> {
                        setAgentInfo(result.data)
                    }

                    is HttpResult.Failure -> {
                        showNetworkAwareError(result.message)
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("setAgentID exception: ${e.message}")
            }
        }
    }

    fun setAgentInfo(agentInfo: AgentInfo?) {
        LogUtils.i("agent = $agentInfo")
        _agentInfo.value = agentInfo
        // Refresh agent data to get latest follower count and follow status
        agentInfo?.let { agent -> refreshAgentData(agent.id) }
    }

    private fun refreshAgentData(agentId: String) {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val result = agentApi.getAgentDetail(agentId)
                LogUtils.i("refreshAgentData = $result")
                when (result) {
                    is HttpResult.Success -> {
                        _agentInfo.value = result.data
                    }

                    is HttpResult.Failure -> {
                        showNetworkAwareError(result.message)
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("refreshAgentData exception: ${e.message}")
            }
        }
    }
}
