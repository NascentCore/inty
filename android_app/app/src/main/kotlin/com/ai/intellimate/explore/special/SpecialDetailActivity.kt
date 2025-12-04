package com.ai.intellimate.explore.special

import ai.sxwl.android.common.base.BaseActivity
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

        /**
         * 启动主题详情页面
         *
         * @param context 上下文
         * @param themeId 主题ID
         * @param themeTitle 主题标题（可选，用于快速显示）
         * @param themeDescription 主题描述（可选，用于快速显示）
         */
        fun launch(
            context: Context,
            themeId: String,
            themeTitle: String? = null,
            themeDescription: String? = null,
        ) {
            context.startActivity(
                Intent(context, SpecialDetailActivity::class.java).apply {
                    putExtra(INTENT_KEY_THEME_ID, themeId)
                    themeTitle?.let { putExtra(INTENT_KEY_THEME_TITLE, it) }
                    themeDescription?.let { putExtra(INTENT_KEY_THEME_DESCRIPTION, it) }
                }
            )
        }
    }

    private val viewModel: SpecialDetailVM by viewModels()
    private var themeId: String? = null

    override fun initConfigData() {
        super.initConfigData()
        themeId = intent.getStringExtra(INTENT_KEY_THEME_ID)
        val themeTitle = intent.getStringExtra(INTENT_KEY_THEME_TITLE)
        val themeDescription = intent.getStringExtra(INTENT_KEY_THEME_DESCRIPTION)

        if (themeId != null) {
            if (themeTitle != null && themeDescription != null) {
                // 如果有预加载的数据，直接设置
                viewModel.setThemeData(themeTitle, themeDescription, emptyList())
            } else {
                // 否则从 API 加载
                viewModel.setThemeId(themeId!!)
            }
        } else {
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
