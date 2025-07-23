package com.ai.inty

import android.content.Intent
import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.ui.Modifier
import androidx.core.view.WindowCompat
import androidx.lifecycle.lifecycleScope
import androidx.localbroadcastmanager.content.LocalBroadcastManager
import com.ai.inty.base.BaseActivity
import com.ai.inty.base.ToastUtils
import com.ai.inty.beans.AgentInfo
import com.ai.inty.chat.ChatPage
import com.ai.inty.net.IAgentApi
import com.ai.inty.ui.theme.BackGround
import com.ai.inty.ui.theme.IntyTheme
import com.ai.inty.viewmodels.ChatViewModel
import com.architecture.httplib.core.HttpResult
import com.inty.utils.log.EasyLog
import com.therouter.TheRouter
import com.therouter.router.Autowired
import com.therouter.router.Route
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

/**
 * 私聊的 聊天页面
 */
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
        
        // Set status bar icons to white for dark theme
        WindowCompat.setDecorFitsSystemWindows(window, false)
        val windowInsetsController = WindowCompat.getInsetsController(window, window.decorView)
        windowInsetsController.isAppearanceLightStatusBars = false

        if (agent == null) {
            if (agent_id != null) {
                chatViewModel.setAgentID(agent_id!!)
            } else {
                // 既没有 agent 对象也没有 agent_id，说明参数传递有问题
                finish()
                return
            }
        } else {
            chatViewModel.setAgentInfo(agent)
        }
        chatViewModel.updateUserInfo()

        setContent {
            IntyTheme {
                ChatPage(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(BackGround)
                        .imePadding()
                        .navigationBarsPadding()
                    ,
                    chatViewModel = chatViewModel,
                    showBackButton = true,
                    onBack = { finish() },
                    onFollowAgent = { agentId ->
                        toggleFollowAgent(agentId)
                    }
                )
//                Box(
//                    modifier = Modifier
//                        .fillMaxSize()
//                        .background(BackGround)
//                        .imePadding()
//                    ,
//                ) {
//                    var textData by remember { mutableStateOf("") }
//                    IntySmallTextField(
//                        modifier = Modifier.fillMaxWidth().height(80.dp)
//                            .background(Color.Red)
//                            .align(Alignment.BottomCenter)
//                        ,
//                        value = textData,
//                        onValueChange = {
//                            textData = it
//                        }
//                    )
//                }
            }
        }
    }
    
    private fun toggleFollowAgent(agentId: String) {
        val currentAgent = chatViewModel.agentInfo.value
        val isCurrentlyFollowed = currentAgent?.isFollowed ?: false
        
        EasyLog.log("toggleFollowAgent - agentId: $agentId, current state: $isCurrentlyFollowed")
        
        if (isCurrentlyFollowed) {
            EasyLog.log("Agent is currently followed, will unfollow")
            unfollowAgent(agentId)
        } else {
            EasyLog.log("Agent is not followed, will follow")
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
                            ToastUtils.showToast("Successfully Followed")
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
                            ToastUtils.showToast("Follow Failed: ${result.message}")
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
                            ToastUtils.showToast("Unfollowed")
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
                            ToastUtils.showToast("Unfollow request failed: ${result.message}")
                        }
                    }
                }
            }
        }
    }
}
