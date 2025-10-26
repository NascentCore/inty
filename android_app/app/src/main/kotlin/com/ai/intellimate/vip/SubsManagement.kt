package com.ai.intellimate.vip

import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.utils.ToastUtils
import android.annotation.SuppressLint
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.intellimate.R
import com.ai.intellimate.ui.components.SettingDivider
import com.ai.intellimate.ui.components.SettingNavigationItem
import com.ai.intellimate.ui.components.SubscriptionManagementContainer
import com.ai.intellimate.ui.components.openPlayStoreSubscriptions

/** 订阅管理屏幕 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SubscriptionManagementScreen(
    modifier: Modifier,
    onBack: () -> Unit,
    viewModel: SubsManageViewModel,
) {
    val context = LocalContext.current

    // 观察来自 ViewModel 的 UI 事件
    LaunchedEffect(Unit) {
        viewModel.uiEvent.collect { event ->
            when (event) {
                SubscriptionUiEvent.NavigateToPlayStoreSubscriptions -> {
                    // 在View层执行实际的Intent启动
                    openPlayStoreSubscriptions(context)
                }
                is SubscriptionUiEvent.ShowToast -> {
                    ToastUtils.showShort(event.message)
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
                SettingNavigationItem(
                    title = stringResource(R.string.cancel_subscription),
                    onClick = { viewModel.navigateToGooglePlaySubscription() },
                )
                SettingDivider()
                SettingNavigationItem(
                    title = stringResource(R.string.restore_subscription),
                    onClick = { viewModel.navigateToGooglePlaySubscription() },
                )
            }
        }
    }
}

@SuppressLint("ViewModelConstructorInComposable")
@Preview
@Composable
private fun SubscriptionManagementScreenPreview() {
    // 这里需要模拟 ViewModel，实际使用时会在 Activity 中传入
    SubscriptionManagementScreen(
        modifier = Modifier,
        onBack = {},
        viewModel = SubsManageViewModel(),
    )
}
