package com.ai.intellimate.settings.check

import ai.sxwl.android.common.base.BaseActivity
import android.content.Context
import android.content.Intent
import androidx.compose.runtime.Composable

class CheckInActivity  : BaseActivity() {
    companion object {
        private const val INTENT_KEY_PAGE_SOURCE = "intent_key_page_source"
        private const val DEFAULT_PAGE_SOURCE = "unknown"

        /**
         * 启动订阅中心界面
         *
         * @param context 上下文context
         * @param pageSource 页面来源，用于统计曝光事件，建议使用 [PageSource] 常量
         */
        fun launch(context: Context, pageSource: String = DEFAULT_PAGE_SOURCE) {
            context.startActivity(
                Intent(context, CheckInActivity::class.java).apply {
                    putExtra(INTENT_KEY_PAGE_SOURCE, pageSource)
                }
            )
        }
    }

    @Composable
    override fun ConfigComposeUI() {
        super.ConfigComposeUI()

        CheckInScreen (
            onClose = { finish() }
        )
    }
}