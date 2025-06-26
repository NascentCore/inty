package com.ai.inty

import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.ui.Modifier
import com.ai.inty.base.BaseActivity
import com.ai.inty.beans.AgentInfo
import com.ai.inty.chat.ChatPage
import com.ai.inty.ui.theme.BackGround
import com.ai.inty.ui.theme.IntyTheme
import com.ai.inty.viewmodels.ChatViewModel
import com.ai.inty.viewmodels.MainViewModel
import com.ai.inty.net.IAgentApi
import com.architecture.httplib.core.HttpResult
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import com.therouter.TheRouter
import com.inty.utils.log.EasyLog
import com.ai.inty.base.ToastUtils
import androidx.localbroadcastmanager.content.LocalBroadcastManager
import android.content.Intent
import com.therouter.router.Autowired
import com.therouter.router.Route

@Route(path = Constant.ROUTE_CHAT)
class ChatActivity : BaseActivity() {

    @Autowired
    var agent: AgentInfo? = null

    @Autowired
    var agent_id: String? = null

    val chatViewModel: ChatViewModel by viewModels()
    private val agentApi: IAgentApi = TheRouter.get(IAgentApi::class.java)!!

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        if (agent == null) {
            chatViewModel.setAgentID(agent_id!!)
        } else {
            chatViewModel.setAgentInfo(agent)
        }
        chatViewModel.updateUserInfo()

        setContent {
            IntyTheme {
                ChatPage(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(BackGround),
                    chatViewModel = chatViewModel,
                    onFollowAgent = { agentId ->
                        toggleFollowAgent(agentId)
                    }
                )
            }
        }
    }
    
    private fun toggleFollowAgent(agentId: String) {
        val currentAgent = chatViewModel.agentInfo.value
        val isCurrentlyFollowed = currentAgent?.isFollowed ?: false
        
        if (isCurrentlyFollowed) {
            unfollowAgent(agentId)
        } else {
            followAgent(agentId)
        }
    }
    
    private fun followAgent(agentId: String) {
        EasyLog.log("followAgent: $agentId")
        lifecycleScope.launch(Dispatchers.IO) {
            val result = agentApi.followAgent(agentId)
            EasyLog.log("followAgent = $result")
            
            when (result) {
                is HttpResult.Success -> {
                    runOnUiThread {
                        lifecycleScope.launch {
                            ToastUtils.showToast("关注成功")
                        }
                    }
                    // Update agent state in ChatViewModel
                    chatViewModel.updateAgentFollowState(agentId, true)
                    
                    // Notify other components about follow state change
                    val intent = Intent("FOLLOW_STATE_CHANGED")
                    intent.putExtra("agentId", agentId)
                    intent.putExtra("isFollowed", true)
                    LocalBroadcastManager.getInstance(this@ChatActivity).sendBroadcast(intent)
                    
                    EasyLog.log("Sent FOLLOW_STATE_CHANGED broadcast - followed: $agentId")
                }
                is HttpResult.Failure -> {
                    runOnUiThread {
                        lifecycleScope.launch {
                            ToastUtils.showToast("关注失败: ${result.message}")
                        }
                    }
                }
            }
        }
    }
    
    private fun unfollowAgent(agentId: String) {
        EasyLog.log("unfollowAgent: $agentId")
        lifecycleScope.launch(Dispatchers.IO) {
            val result = agentApi.unfollowAgent(agentId)
            EasyLog.log("unfollowAgent = $result")
            
            when (result) {
                is HttpResult.Success -> {
                    runOnUiThread {
                        lifecycleScope.launch {
                            ToastUtils.showToast("取消关注成功")
                        }
                    }
                    // Update agent state in ChatViewModel
                    chatViewModel.updateAgentFollowState(agentId, false)
                    
                    // Notify other components about follow state change
                    val intent = Intent("FOLLOW_STATE_CHANGED")
                    intent.putExtra("agentId", agentId)
                    intent.putExtra("isFollowed", false)
                    LocalBroadcastManager.getInstance(this@ChatActivity).sendBroadcast(intent)
                    
                    EasyLog.log("Sent FOLLOW_STATE_CHANGED broadcast - unfollowed: $agentId")
                }
                is HttpResult.Failure -> {
                    runOnUiThread {
                        lifecycleScope.launch {
                            ToastUtils.showToast("取消关注失败: ${result.message}")
                        }
                    }
                }
            }
        }
    }
}
