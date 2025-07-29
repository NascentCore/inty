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
 * 私聊的聊天页面
 */
@Route(path = Constant.ROUTE_CHAT)
class ChatActivity : BaseActivity() {

    @Autowired
    var agent: AgentInfo? = null

    @Autowired
    var agent_id: String? = null

    private val chatViewModel: ChatViewModel by viewModels()
    private val agentApi: IAgentApi = TheRouter.get(IAgentApi::class.java)!!

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setupWindow()
        initializeChatViewModel()
        setupUI()
    }

    /**
     * 设置窗口属性
     */
    private fun setupWindow() {
        enableEdgeToEdge()
        // 设置状态栏图标为白色（深色主题）
        WindowCompat.setDecorFitsSystemWindows(window, false)
        val windowInsetsController = WindowCompat.getInsetsController(window, window.decorView)
        windowInsetsController.isAppearanceLightStatusBars = false
    }

    /**
     * 初始化聊天ViewModel
     */
    private fun initializeChatViewModel() {
        when {
            agent != null -> {
                chatViewModel.setAgentInfo(agent)
            }

            agent_id != null -> {
                chatViewModel.setAgentID(agent_id!!)
            }

            else -> {
                // 既没有agent对象也没有agent_id，说明参数传递有问题
                EasyLog.log("ChatActivity: No agent or agent_id provided, finishing activity")
                finish()
                return
            }
        }
        chatViewModel.updateUserInfo()
    }

    /**
     * 设置UI
     */
    private fun setupUI() {
        setContent {
            IntyTheme {
                ChatPage(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(BackGround)
                        .imePadding()
                        .navigationBarsPadding(),
                    chatViewModel = chatViewModel,
                    showBackButton = true,
                    onBack = { finish() },
                    onFollowAgent = { agentId ->
                        toggleFollowAgent(agentId)
                    }
                )
            }
        }
    }

    /**
     * 切换关注状态
     */
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

    /**
     * 关注代理
     */
    private fun followAgent(agentId: String) {
        EasyLog.log("followAgent: $agentId")
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val result = agentApi.followAgent(agentId)
                EasyLog.log("followAgent = $result")

                when (result) {
                    is HttpResult.Success -> {
                        handleFollowSuccess(agentId, true)
                    }

                    is HttpResult.Failure -> {
                        handleFollowFailure("Follow Failed: ${result.message}")
                    }
                }
            } catch (e: Exception) {
                EasyLog.log("followAgent exception: ${e.message}", EasyLog.ERROR)
                handleFollowFailure("Network error: ${e.message}")
            }
        }
    }

    /**
     * 取消关注代理
     */
    private fun unfollowAgent(agentId: String) {
        EasyLog.log("unfollowAgent: $agentId")
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val result = agentApi.unfollowAgent(agentId)
                EasyLog.log("unfollowAgent = $result")

                when (result) {
                    is HttpResult.Success -> {
                        handleFollowSuccess(agentId, false)
                    }

                    is HttpResult.Failure -> {
                        handleFollowFailure(result.message)
                    }
                }
            } catch (e: Exception) {
                EasyLog.log("unfollowAgent exception: ${e.message}", EasyLog.ERROR)
                handleFollowFailure("Network error: ${e.message}")
            }
        }
    }

    /**
     * 处理关注成功
     */
    private fun handleFollowSuccess(agentId: String, isFollowed: Boolean) {
        runOnUiThread {
            lifecycleScope.launch {
                val message = if (isFollowed) "Followed" else "Unfollowed"
                ToastUtils.showToast(message)
            }
        }

        // 更新ChatViewModel中的代理状态
        chatViewModel.updateAgentFollowState(agentId, isFollowed)

        // 通知其他组件关注状态变更
        sendFollowStateBroadcast(agentId, isFollowed)

        EasyLog.log("Sent FOLLOW_STATE_CHANGED broadcast - ${if (isFollowed) "followed" else "unfollowed"}: $agentId")
    }

    /**
     * 处理关注失败
     */
    private fun handleFollowFailure(message: String) {
        runOnUiThread {
            lifecycleScope.launch {
                ToastUtils.showToast(message)
            }
        }
    }

    /**
     * 发送关注状态变更广播
     */
    private fun sendFollowStateBroadcast(agentId: String, isFollowed: Boolean) {
        val intent = Intent("FOLLOW_STATE_CHANGED").apply {
            putExtra("agentId", agentId)
            putExtra("isFollowed", isFollowed)
        }
        LocalBroadcastManager.getInstance(this@ChatActivity).sendBroadcast(intent)
    }
}
