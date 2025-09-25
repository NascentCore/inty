package com.ai.inty

import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.ai.inty.base.BaseActivity
import com.ai.inty.ui.screens.SubscriptionManagementScreen
import com.ai.inty.ui.theme.DarkPurple
import com.ai.inty.ui.theme.IntyTheme
import com.ai.inty.viewmodels.SubsManageViewModel
import com.therouter.router.Route

/** 订阅管理页面 */
@Route(path = Constant.ROUTE_SUBSCRIPTION_MANAGEMENT)
class SubscriptionManagementActivity : BaseActivity() {

  private val viewModel: SubsManageViewModel by viewModels()

  override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    setContent { IntyTheme { SubsManageContent(onBack = { finish() }, viewModel = viewModel) } }
  }
}

/** 订阅管理内容组件 */
@Composable
private fun SubsManageContent(onBack: () -> Unit, viewModel: SubsManageViewModel) {
  SubscriptionManagementScreen(
      modifier = Modifier.fillMaxSize().background(DarkPurple),
      onBack = onBack,
      viewModel = viewModel,
  )
}
