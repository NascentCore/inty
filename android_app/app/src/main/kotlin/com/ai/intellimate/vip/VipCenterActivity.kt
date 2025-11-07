package com.ai.intellimate.vip

import ai.sxwl.android.common.base.BaseActivity
import android.content.Context
import android.content.Intent
import androidx.activity.viewModels
import androidx.compose.runtime.Composable

/** 会员中心页面，展示会员权益与订阅选项。 */
class VipCenterActivity : BaseActivity() {

    companion object {
        private const val INTENT_KEY_PAGE_SOURCE = "intent_key_page_source"
        private const val DEFAULT_PAGE_SOURCE = "unknown"

        /** 页面来源常量 - 用于统计曝光事件 */
        const val HOME_EXPIRED_DIALOG = "home_expired_dialog" // 首页过期VIP对话框
        const val CHAT_PAGE = "chat_page" // 聊天页面
        const val CHAT_MORE_PANEL = "chat_more_panel" // 聊天更多面板
        const val PROFILE_UPGRADE = "profile_upgrade" // 个人中心升级按钮
        const val SETTINGS_SUBSCRIPTION = "settings_subscription" // 设置页面订阅管理

        /**
         * 启动订阅中心界面
         *
         * @param context 上下文context
         * @param pageSource 页面来源，用于统计曝光事件，建议使用 [PageSource] 常量
         */
        fun launch(context: Context, pageSource: String = DEFAULT_PAGE_SOURCE) {
            context.startActivity(
                Intent(context, VipCenterActivity::class.java).apply {
                    putExtra(INTENT_KEY_PAGE_SOURCE, pageSource)
                }
            )
        }
    }

    private val pageSource: String by lazy {
        intent.getStringExtra(INTENT_KEY_PAGE_SOURCE) ?: DEFAULT_PAGE_SOURCE
    }

    private val viewModel: VipCenterViewModel by viewModels()

    /** 重写以提供额外的页面追踪参数（页面来源） */
    override fun getAdditionalPageTrackingParams(): Map<String, Any> {
        return mapOf("page_source" to pageSource)
    }

    @Composable
    override fun ConfigComposeUI() {
        super.ConfigComposeUI()
        VipCenterContent(
            onClose = { finish() },
            onPurchase = { viewModel.purchaseSelectedPlan(this) },
        )
    }
}
