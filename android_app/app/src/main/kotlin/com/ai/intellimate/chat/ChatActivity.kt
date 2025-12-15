package com.ai.intellimate.chat

import ai.sxwl.android.common.base.BaseActivity
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.store.SettingStateManager
import ai.sxwl.android.design.theme.HeartColor
import ai.sxwl.android.firebase.FirebaseManager
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.activity.viewModels
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.navigation.compose.rememberNavController
import com.ai.intellimate.agent.report.ReportActivity
import com.ai.intellimate.chat.viewmodel.ChatViewModel
import com.ai.intellimate.ui.FeedbackRequestDialog
import com.ai.intellimate.ui.components.AgentBackground

/**
 * 私聊的聊天页面（独立 Activity）
 *
 * 使用场景：
 * 1. 从推送通知启动 - 当用户点击 FCM 推送通知时，通过 MainActivity.handleNotificationIntent() 调用 ChatActivity.launch()
 * 2. 从 Boost 排行榜页面启动 - 当用户在 BoostLeaderboardActivity 中点击排行榜项时调用 ChatActivity.launch()
 *
 * 注意：应用内大部分聊天页面跳转使用导航系统（Routes.ChatPage），通过 ChatScreen 组件显示，
 * 而不是使用独立的 ChatActivity。只有上述两种场景会使用 ChatActivity。
 */
class ChatActivity : BaseActivity() {

    companion object {
        private const val INTENT_KEY_AGENT_ID = "intent_key_agent_id"
        private const val INTENT_KEY_AGENT_INFO = "intent_key_agent_info"
        private const val INTENT_KEY_PAGE_SOURCE = "intent_key_page_source"
        private const val INTENT_KEY_AUTO_BOOST = "intent_key_auto_boost"
        private const val DEFAULT_PAGE_SOURCE = "unknown"

        /** 页面来源常量 - 用于统计曝光事件 */
        const val MESSAGES_TAB = "messages_tab" // 消息列表Tab
        const val EXPLORE_TAB = "explore_tab" // 探索Tab
        const val PROFILE_TAB = "profile_tab" // 个人中心Tab
        const val PUSH_NOTIFICATION = "push_notification" // 消息推送通知

        /**
         * 启动单独的聊天界面
         *
         * @param context 上下文context
         * @param agentInfo Agent的Info对象
         * @param agentId agent的id 两个参数选一即可，也必须只要有一个
         * @param pageSource 页面来源，用于统计曝光事件，建议使用常量
         */
        fun launch(
            context: Context,
            agentInfo: AgentInfo? = null,
            agentId: String? = null,
            pageSource: String = DEFAULT_PAGE_SOURCE,
            showBoostSheet: Boolean = false,
        ) {
            context.startActivity(
                Intent(context, ChatActivity::class.java).also { intent ->
                    intent.putExtra(INTENT_KEY_AGENT_ID, agentId)
                    intent.putExtra(INTENT_KEY_AGENT_INFO, agentInfo)
                    intent.putExtra(INTENT_KEY_PAGE_SOURCE, pageSource)
                    intent.putExtra(INTENT_KEY_AUTO_BOOST, showBoostSheet)
                }
            )
        }

        /** 消息推送通知打开聊天页面需要的intent */
        fun notifyIntent(context: Context, agentId: String?): Intent {
            return Intent(context, ChatActivity::class.java).also { intent ->
                intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
                intent.putExtra(INTENT_KEY_AGENT_ID, agentId)
                intent.putExtra(INTENT_KEY_PAGE_SOURCE, PUSH_NOTIFICATION)
            }
        }
    }

    private val chatViewModel: ChatViewModel by viewModels()
    private var agent: AgentInfo? = null
    private var agentId: String? = null
    private var pageSource: String = DEFAULT_PAGE_SOURCE
    private var shouldShowBoostSheet: Boolean = false
    private var isFromNotification: Boolean = false

    override fun getPageName(): String = "ChatPage"

    /** 重写以提供额外的页面追踪参数（页面来源） */
    override fun getAdditionalPageTrackingParams(): Map<String, Any> {
        return mapOf("page_source" to pageSource)
    }

    override fun initConfigData() {
        super.initConfigData()
        handleIntent(intent)
    }

    /** 处理 Intent 数据，提取 agent 信息和页面来源 */
    private fun handleIntent(intent: Intent) {
        agent =
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                intent.getParcelableExtra(INTENT_KEY_AGENT_INFO, AgentInfo::class.java)
            } else {
                intent.getParcelableExtra(INTENT_KEY_AGENT_INFO)
            }
        agentId = intent.getStringExtra(INTENT_KEY_AGENT_ID)
        pageSource = intent.getStringExtra(INTENT_KEY_PAGE_SOURCE) ?: DEFAULT_PAGE_SOURCE
        shouldShowBoostSheet = intent.getBooleanExtra(INTENT_KEY_AUTO_BOOST, false)
        isFromNotification = pageSource == PUSH_NOTIFICATION

        val resolvedAgent = agent
        if (resolvedAgent != null) {
            // 如果是从通知进入，强制同步消息
            chatViewModel.setAgentInfo(resolvedAgent, forceSync = isFromNotification)
        } else {
            val resolvedAgentId = agentId
            if (resolvedAgentId.isNullOrBlank()) {
                // 既没有agent对象也没有可用的agent_id，说明参数传递有问题
                finish()
                return
            }
            // 如果是从通知进入，先获取 agent 信息，然后强制同步
            chatViewModel.setAgentID(resolvedAgentId, forceSync = isFromNotification)
        }
        chatViewModel.updateUserInfo()

        // 如果是从推送通知进入，记录推送通知点击事件
        if (isFromNotification) {
            FirebaseManager.logEvent(
                FirebaseManager.Events.PUSH_NOTIFICATION_CLICK,
                FirebaseManager.safeEventParams(
                    "agent_id" to (agentId ?: "unknown"),
                    "page_source" to pageSource,
                ),
            )
        }
    }

    /** 处理 Activity 复用场景（singleTop 模式） */
    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        // 重新处理 Intent，确保从通知进入时能触发消息同步
        handleIntent(intent)
    }

    @Composable
    override fun ConfigComposeUI() {
        super.ConfigComposeUI()
        val agentInfo by chatViewModel.agentInfo.collectAsState()
        val chatMessages by chatViewModel.msgs.collectAsState()
        val showFeedbackDialog by chatViewModel.showFeedbackRequestDialog.collectAsState()
        val context = LocalContext.current
        val autoPlayAnimation by SettingStateManager.autoPlayAnimationFlow.collectAsState()
        val hasLoadingMessage =
            chatMessages.any { msg ->
                val hasGeneratedImage = msg.hasGeneratedImage()
                val generatedImageUrl = msg.getGeneratedImageUrl()
                msg.content == "loading_animation" &&
                    !hasGeneratedImage &&
                    generatedImageUrl != "loading"
            }

        val navController = rememberNavController()

        Box(modifier = Modifier.fillMaxSize().background(HeartColor.primaryColor)) {
            // 背景图放在最底层，不受 imePadding 影响
            AgentBackground(
                agentInfo = agentInfo,
                showGradients = true,
                isLoading = hasLoadingMessage,
                isCurrentPage = true,
                modifier = Modifier.fillMaxSize(),
                enableAnimatedBackground = autoPlayAnimation,
            )

            ChatPage(
                navController = navController,
                modifier = Modifier.fillMaxSize().imePadding().navigationBarsPadding(),
                chatViewModel = chatViewModel,
                showBackButton = true,
                onBack = { finish() },
                pageSourceOverride = pageSource, // 传递 ChatActivity 的 pageSource，避免重复追踪
                shouldShowBoostSheetOnOpen = shouldShowBoostSheet,
            )

            // 反馈请求对话框
            if (showFeedbackDialog) {
                FeedbackRequestDialog(
                    onCancel = { chatViewModel.hideFeedbackDialog() },
                    onSendSuggestions = {
                        chatViewModel.hideFeedbackDialog()
                        ReportActivity.launchFeedback(context)
                    },
                )
            }
        }
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
