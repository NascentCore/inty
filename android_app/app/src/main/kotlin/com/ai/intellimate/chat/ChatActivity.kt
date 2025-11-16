package com.ai.intellimate.chat

import ai.sxwl.android.common.base.BaseActivity
import ai.sxwl.android.data.api.model.AgentInfo
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
import com.ai.intellimate.chat.viewmodel.ChatViewModel
import com.ai.intellimate.ui.components.AgentBackground

/** 私聊的聊天页面 */
class ChatActivity : BaseActivity() {

    companion object {
        private const val INTENT_KEY_AGENT_ID = "intent_key_agent_id"
        private const val INTENT_KEY_AGENT_INFO = "intent_key_agent_info"
        private const val INTENT_KEY_PAGE_SOURCE = "intent_key_page_source"
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
        ) {
            context.startActivity(
                Intent(context, ChatActivity::class.java).also { intent ->
                    intent.putExtra(INTENT_KEY_AGENT_ID, agentId)
                    intent.putExtra(INTENT_KEY_AGENT_INFO, agentInfo)
                    intent.putExtra(INTENT_KEY_PAGE_SOURCE, pageSource)
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
    private val pageSource: String by lazy {
        intent.getStringExtra(INTENT_KEY_PAGE_SOURCE) ?: DEFAULT_PAGE_SOURCE
    }

    override fun getPageName(): String = "ChatPage"

    /** 重写以提供额外的页面追踪参数（页面来源） */
    override fun getAdditionalPageTrackingParams(): Map<String, Any> {
        return mapOf("page_source" to pageSource)
    }

    override fun initConfigData() {
        super.initConfigData()
        agent =
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                intent.getParcelableExtra(INTENT_KEY_AGENT_INFO, AgentInfo::class.java)
            } else {
                intent.getParcelableExtra(INTENT_KEY_AGENT_INFO)
            }
        agentId = intent.getStringExtra(INTENT_KEY_AGENT_ID)
        val resolvedAgent = agent
        if (resolvedAgent != null) {
            chatViewModel.setAgentInfo(resolvedAgent)
        } else {
            val resolvedAgentId = agentId
            if (resolvedAgentId.isNullOrBlank()) {
                // 既没有agent对象也没有可用的agent_id，说明参数传递有问题
                finish()
                return
            }
            chatViewModel.setAgentID(resolvedAgentId)
        }
        chatViewModel.updateUserInfo()

        // 如果是从推送通知进入，记录推送通知点击事件
        if (pageSource == PUSH_NOTIFICATION) {
            FirebaseManager.logEvent(
                FirebaseManager.Events.PUSH_NOTIFICATION_CLICK,
                FirebaseManager.safeEventParams(
                    "agent_id" to (agentId ?: "unknown"),
                    "page_source" to pageSource,
                ),
            )
        }
    }

    @Composable
    override fun ConfigComposeUI() {
        super.ConfigComposeUI()
        val agentInfo by chatViewModel.agentInfo.collectAsState()
        val chatMessages by chatViewModel.msgs.collectAsState()
        val hasLoadingMessage =
            chatMessages.any { msg ->
                val hasGeneratedImage = msg.hasGeneratedImage()
                val generatedImageUrl = msg.getGeneratedImageUrl()
                msg.content == "loading_animation" &&
                    !hasGeneratedImage &&
                    generatedImageUrl != "loading"
            }

        Box(modifier = Modifier.fillMaxSize().background(HeartColor.primaryColor)) {
            // 背景图放在最底层，不受 imePadding 影响
            AgentBackground(
                agentInfo = agentInfo,
                showGradients = true,
                isLoading = hasLoadingMessage,
                isCurrentPage = true,
                modifier = Modifier.fillMaxSize(),
            )

            ChatPage(
                modifier = Modifier.fillMaxSize().imePadding().navigationBarsPadding(),
                chatViewModel = chatViewModel,
                showBackButton = true,
                onBack = { finish() },
                pageSourceOverride = pageSource, // 传递 ChatActivity 的 pageSource，避免重复追踪
            )
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
