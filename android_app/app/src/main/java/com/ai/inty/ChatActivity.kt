package com.ai.inty

import ai.sxwl.android.design.theme.HeartColor
import ai.sxwl.android.design.theme.IntelliMateTheme
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
import com.ai.inty.base.BaseActivity
import com.ai.inty.beans.AgentInfo
import com.ai.inty.chat.ChatPage
import com.ai.inty.chat.ChatViewModel
import com.ai.inty.utils.FirebaseManager
import com.therouter.router.Autowired
import com.therouter.router.Route

/** 私聊的聊天页面 */
@Route(path = Constant.ROUTE_CHAT)
class ChatActivity : BaseActivity() {

    @Autowired
    var agent: AgentInfo? = null

    @Autowired
    var agent_id: String? = null

    private val chatViewModel: ChatViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setupWindow()
        initializeChatViewModel()
        setupUI()
    }

    /** 设置窗口属性 */
    private fun setupWindow() {
        enableEdgeToEdge()
        // 设置状态栏图标为白色（深色主题）
        WindowCompat.setDecorFitsSystemWindows(window, false)
        val windowInsetsController = WindowCompat.getInsetsController(window, window.decorView)
        windowInsetsController.isAppearanceLightStatusBars = false
    }

    /** 初始化聊天ViewModel */
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
                finish()
                return
            }
        }
        chatViewModel.updateUserInfo()
    }

    /** 设置UI */
    private fun setupUI() {
        setContent {
            IntelliMateTheme {
                ChatPage(
                    modifier =
                        Modifier
                            .fillMaxSize()
                            .background(HeartColor.primaryColor)
                            .imePadding()
                            .navigationBarsPadding(),
                    chatViewModel = chatViewModel,
                    showBackButton = true,
                    onBack = { finish() },
                )
            }
        }

        // 跟踪ChatActivity页面访问
        val agentId = agent?.id ?: agent_id ?: "unknown"
        FirebaseManager.logScreenView(
            screenName = "ChatScreen",
            screenClass = "ChatActivity",
            additionalParams =
                mapOf("agent_id" to agentId, "agent_name" to (agent?.name ?: "unknown")),
        )
    }

    override fun onDestroy() {
        super.onDestroy()
        // 清理 ChatViewModel 资源
        chatViewModel.clearAllData()
    }

    override fun onPause() {
        super.onPause()
        // 统一生命周期：Activity 页面进入后台即停止音频
        chatViewModel.pauseVoicePlayback()
    }
}
