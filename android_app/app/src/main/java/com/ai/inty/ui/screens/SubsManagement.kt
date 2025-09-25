package com.ai.inty.ui.screens

import android.annotation.SuppressLint
import android.widget.Toast
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.inty.R
import com.ai.inty.base.noRippleClickable
import com.ai.inty.billing.BillingRepository
import com.ai.inty.ui.components.SettingDivider
import com.ai.inty.ui.components.SubscriptionManagementContainer
import com.ai.inty.ui.components.SubscriptionManagementItem
import com.ai.inty.ui.components.openPlayStoreSubscriptions
import com.ai.inty.viewmodels.SubsManageViewModel
import com.ai.inty.viewmodels.SubscriptionUiEvent

/** 订阅管理屏幕 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SubscriptionManagementScreen(
    modifier: Modifier,
    onBack: () -> Unit,
    viewModel: SubsManageViewModel,
) {
    val context = LocalContext.current

    // 获取订阅状态
    val vipStatus by BillingRepository.vipStatusFlow.collectAsState()

    // 观察来自 ViewModel 的 UI 事件
    LaunchedEffect(Unit) {
        viewModel.uiEvent.collect { event ->
            when (event) {
                SubscriptionUiEvent.NavigateToPlayStoreSubscriptions -> {
                    // 在View层执行实际的Intent启动
                    openPlayStoreSubscriptions(context)
                }

                is SubscriptionUiEvent.ShowToast -> {
                    Toast.makeText(context, event.message, Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    Scaffold(
        modifier = modifier,
        topBar = {
            CenterAlignedTopAppBar(
                title = {
                    Text(
                        text = stringResource(R.string.settings_subscription_management),
                        color = Color.White,
                        fontWeight = FontWeight.SemiBold,
                        fontSize = 20.sp,
                    )
                },
                navigationIcon = {
                    Image(
                        modifier =
                            Modifier.padding(horizontal = 12.dp).noRippleClickable { onBack() },
                        painter = painterResource(R.drawable.back),
                        contentDescription = null,
                    )
                },
            )
        },
    ) { innerPadding ->
        Column(modifier = Modifier.padding(innerPadding)) {
            SubscriptionManagementContainer {
                SubscriptionManagementItem(
                    icon = R.drawable.icon_list_row_3,
                    title = stringResource(R.string.cancel_subscription),
                    onClick = { viewModel.navigateToGooglePlaySubscription() },
                )
                SettingDivider()
                SubscriptionManagementItem(
                    icon = R.drawable.icon_list_row_1,
                    title = stringResource(R.string.restore_subscription),
                    onClick = { viewModel.navigateToGooglePlaySubscription() },
                )
            }
        }
    }
}

@SuppressLint("ViewModelConstructorInComposable")
@Preview(showBackground = true)
@Composable
private fun SubscriptionManagementScreenPreview() {
    // 这里需要模拟 ViewModel，实际使用时会在 Activity 中传入
    SubscriptionManagementScreen(
        modifier = Modifier,
        onBack = {},
        viewModel = SubsManageViewModel(),
    )
}
