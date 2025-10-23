package com.ai.intellimate.vip

import ai.sxwl.android.common.base.BaseActivity
import android.content.Context
import android.content.Intent
import androidx.activity.viewModels
import androidx.compose.runtime.Composable

/** 会员中心页面，展示会员权益与订阅选项。 */
class VipCenterActivity : BaseActivity() {


    companion object {

        /**
         * 启动订阅中心界面
         * @param context 上下文context
         */
        fun launch(context: Context) {
            context.startActivity(Intent(context, VipCenterActivity::class.java))
        }
    }

    private val viewModel: VipCenterViewModel by viewModels()

    @Composable
    override fun ConfigComposeUI() {
        super.ConfigComposeUI()
        VipCenterContent(
            onClose = { finish() },
            onPurchase = { viewModel.purchaseSelectedPlan(this) },
        )
    }
}
