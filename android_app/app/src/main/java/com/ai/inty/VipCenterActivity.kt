package com.ai.inty

import ai.sxwl.android.design.theme.IntelliMateTheme
import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import com.ai.inty.base.BaseActivity
import com.ai.inty.ui.screens.VipCenterContent

import com.ai.inty.viewmodels.VipCenterViewModel
import com.therouter.router.Route

/** 会员中心页面，展示会员权益与订阅选项。 */
@Route(path = Constant.ROUTE_VIP_CENTER)
class VipCenterActivity : BaseActivity() {
    private val viewModel: VipCenterViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            IntelliMateTheme {
                VipCenterContent(
                    onClose = { finish() },
                    onPurchase = { viewModel.purchaseSelectedPlan(this) },
                )
            }
        }
    }
}
