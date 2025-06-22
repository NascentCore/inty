package com.ai.inty.viewmodels

import android.content.Context
import android.content.Intent
import androidx.lifecycle.viewModelScope
import androidx.localbroadcastmanager.content.LocalBroadcastManager
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

class AgentInfoViewModel: BaseActivityViewModel() {

    private val _agentInfo = MutableStateFlow<AgentInfo?>(null)
    val agentInfo = _agentInfo.asStateFlow()

    val chatApi = TheRouter.get(IChatApi::class.java)!!
    val agentApi = TheRouter.get(IAgentApi::class.java)!!

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
    
    fun followAgent(agentId: String, context: Context) {
        val currentAgent = _agentInfo.value ?: return
        EasyLog.log("followAgent: $agentId, current status: ${currentAgent.isFollowed}")
        
        viewModelScope.launch(Dispatchers.IO) {
            val result = if (currentAgent.isFollowed) {
                agentApi.unfollowAgent(agentId)
            } else {
                agentApi.followAgent(agentId)
            }
            EasyLog.log("followAgent result = $result")
            
            when (result) {
                is HttpResult.Success -> {
                    val newFollowStatus = !currentAgent.isFollowed
                    _agentInfo.value = currentAgent.copy(isFollowed = newFollowStatus)
                    showSnackbar(result.data.message)
                    
                    // Send broadcast to notify MainActivity about follow state change
                    val intent = Intent("FOLLOW_STATE_CHANGED")
                    intent.putExtra("agentId", agentId)
                    intent.putExtra("isFollowed", newFollowStatus)
                    LocalBroadcastManager.getInstance(context).sendBroadcast(intent)
                }
                is HttpResult.Failure -> {
                    showSnackbar(result.message)
                }
            }
        }
    }

}