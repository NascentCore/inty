package com.ai.intellimate.explore.special

import ai.sxwl.android.common.base.BaseActivity
import ai.sxwl.android.data.api.model.AgentInfo
import android.content.Context
import android.content.Intent
import androidx.activity.viewModels
import androidx.compose.runtime.Composable
import com.ai.intellimate.chat.ChatActivity

/** Explore界面顶部主题专区详情 */
class SpecialDetailActivity : BaseActivity() {

    companion object {
        private const val INTENT_KEY_THEME_ID = "intent_key_theme_id"
        private const val INTENT_KEY_THEME_TITLE = "intent_key_theme_title"
        private const val INTENT_KEY_THEME_DESCRIPTION = "intent_key_theme_description"
        private const val INTENT_KEY_IS_CHRISTMAS = "intent_key_is_christmas"
        private const val INTENT_KEY_AGENTS = "intent_key_agents"

        /**
         * 启动主题详情页面
         *
         * @param context 上下文
         * @param themeId 主题ID
         * @param themeTitle 主题标题（可选，用于快速显示）
         * @param themeDescription 主题描述（可选，用于快速显示）
         * @param isChristmas 是否为圣诞主题（可选，用于显示圣诞装饰）
         * @param agents Agents 列表（可选，用于模拟界面效果，如果提供则不会从 API 加载）
         */
        fun launch(
            context: Context,
            themeId: String,
            themeTitle: String? = null,
            themeDescription: String? = null,
            isChristmas: Boolean = false,
            agents: List<AgentInfo>? = null,
        ) {
            context.startActivity(
                Intent(context, SpecialDetailActivity::class.java).apply {
                    putExtra(INTENT_KEY_THEME_ID, themeId)
                    themeTitle?.let { putExtra(INTENT_KEY_THEME_TITLE, it) }
                    themeDescription?.let { putExtra(INTENT_KEY_THEME_DESCRIPTION, it) }
                    putExtra(INTENT_KEY_IS_CHRISTMAS, isChristmas)
                    agents?.let {
                        putParcelableArrayListExtra(INTENT_KEY_AGENTS, ArrayList(it))
                    }
                }
            )
        }
    }

    private val viewModel: SpecialDetailVM by viewModels()

    override fun initConfigData() {
        super.initConfigData()
        val themeTitle = intent.getStringExtra(INTENT_KEY_THEME_TITLE)
        val themeDescription = intent.getStringExtra(INTENT_KEY_THEME_DESCRIPTION)
        val isChristmas = intent.getBooleanExtra(INTENT_KEY_IS_CHRISTMAS, false)
        @Suppress("DEPRECATION")
        val agents = intent.getParcelableArrayListExtra<AgentInfo>(INTENT_KEY_AGENTS)

        // 所有数据都从外部传入，直接设置到 ViewModel
        if (themeTitle != null && themeDescription != null) {
            val agentsList = agents ?: emptyList()
            viewModel.setThemeData(themeTitle, themeDescription, agentsList, isChristmas)
        } else {
            // 如果没有传入必要的数据，关闭页面
            finish()
        }
    }

    @Composable
    override fun ConfigComposeUI() {
        super.ConfigComposeUI()
        ThemedDetailScreen(
            viewModel = viewModel,
            onBack = { finish() },
            onClickAgent = { agent ->
                ChatActivity.launch(this, agent, pageSource = ChatActivity.EXPLORE_TAB)
            },
        )
    }
}
