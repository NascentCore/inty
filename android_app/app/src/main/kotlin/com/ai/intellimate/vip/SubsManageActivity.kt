package com.ai.intellimate.vip

import ai.sxwl.android.common.base.BaseActivity
import ai.sxwl.android.design.theme.HeartColor
import android.content.Context
import android.content.Intent
import androidx.activity.viewModels
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier

/** 订阅管理页面 */
class SubsManageActivity : BaseActivity() {
    companion object {
        /**
         * 启动订阅管理页面
         *
         * @param context 上下文context
         */
        fun launch(context: Context) {
            context.startActivity(Intent(context, SubsManageActivity::class.java))
        }
    }

    private val viewModel: SubsManageViewModel by viewModels()

    @Composable
    override fun ConfigComposeUI() {
        super.ConfigComposeUI()
        SubsManageContent(onBack = { finish() }, viewModel = viewModel)
    }
}

/** 订阅管理内容组件 */
@Composable
private fun SubsManageContent(
    onBack: () -> Unit,
    viewModel: SubsManageViewModel,
) {
    SubscriptionManagementScreen(
        modifier = Modifier.fillMaxSize().background(HeartColor.primaryColor),
        onBack = onBack,
        viewModel = viewModel,
    )
}
