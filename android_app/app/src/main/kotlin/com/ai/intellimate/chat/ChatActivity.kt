package com.ai.intellimate.chat

import ai.sxwl.android.common.base.BaseActivity
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.design.theme.HeartColor
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.activity.viewModels
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.ai.intellimate.chat.viewmodel.ChatViewModel

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

        /**
         * 启动单独的聊天界面
         *
         * @param context 上下文context
         * @param agentInfo Agent的Info对象
         * @param agentId agent的id 两个参数选一即可，也必须只要有一个
         * @param pageSource 页面来源，用于统计曝光事件，建议使用 [PageSource] 常量
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
    }

    private val chatViewModel: ChatViewModel by viewModels()
    private var agent: AgentInfo? = null
    private var agentId: String? = null
    private val pageSource: String by lazy {
        intent.getStringExtra(INTENT_KEY_PAGE_SOURCE) ?: DEFAULT_PAGE_SOURCE
    }

    override fun getPageName(): String = "ChatActivity"

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
        when {
            agent != null -> {
                chatViewModel.setAgentInfo(agent)
            }

            agentId != null -> {
                chatViewModel.setAgentID(agentId!!)
            }

            else -> {
                // 既没有agent对象也没有agent_id，说明参数传递有问题
                finish()
                return
            }
        }
        chatViewModel.updateUserInfo()
    }

    @Composable
    override fun ConfigComposeUI() {
        super.ConfigComposeUI()
        ChatPage(
            modifier =
                Modifier.fillMaxSize()
                    .background(HeartColor.primaryColor)
                    .imePadding()
                    .navigationBarsPadding(),
            chatViewModel = chatViewModel,
            showBackButton = true,
            onBack = { finish() },
        )
        // 注意：ChatPage 内部已通过 PageTrackingHelper.trackPageView() 统一跟踪页面访问
        // 无需在此处重复记录，避免冗余统计
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
