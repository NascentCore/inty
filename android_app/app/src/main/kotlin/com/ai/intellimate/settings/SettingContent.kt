package com.ai.intellimate.settings

import ai.sxwl.android.data.billing.BillingRepository
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.utils.ToastUtils
import android.content.Context
import android.content.Intent
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
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
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.net.toUri
import androidx.lifecycle.viewmodel.compose.viewModel
import com.ai.intellimate.BuildConfig
import com.ai.intellimate.R
import com.ai.intellimate.agent.report.ReportActivity
import com.ai.intellimate.login.LoginActivity
import com.ai.intellimate.ui.components.DeleteAccountDialog
import com.ai.intellimate.ui.components.LogoutButton
import com.ai.intellimate.ui.components.SettingDivider
import com.ai.intellimate.ui.components.SettingNavigationItem
import com.ai.intellimate.ui.components.SettingSection
import com.ai.intellimate.vip.SubsManageActivity
import com.ai.intellimate.vip.VipCenterActivity
import kotlinx.coroutines.flow.collectLatest

/** 设置页面主内容 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingContent(
    modifier: Modifier = Modifier,
    onBack: () -> Unit,
    onLogout: (isDelete: Boolean) -> Unit,
    viewModel: SettingViewModel = viewModel(),
) {
    val context = LocalContext.current
    val dialogState by viewModel.dialogState.collectAsState()

    // 监听删除账号结果
    LaunchedEffect(viewModel) {
        viewModel.deleteAccountResultFlow.collectLatest { deleted ->
            if (deleted) {
                // 账号删除成功
                onLogout(true)
            }
        }
    }

    Scaffold(modifier = modifier, topBar = { SettingTopBar(onBack = onBack) }) { innerPadding ->
        Column(modifier = Modifier.padding(innerPadding)) {

            // 支持与帮助区域
            SupportAndHelpSection(
                context = context,
                onShowDeleteDialog = { viewModel.showDeleteAccountDialog() },
            )

            Spacer(Modifier.height(16.dp))

            // 退出登录按钮
            LogoutButton(onLogout = { onLogout(false) })

            // 对话框
            SettingDialogs(
                dialogState = dialogState,
                onHideDeleteDialog = { viewModel.hideDeleteAccountDialog() },
                onConfirmDelete = { viewModel.checkAccountSubscribe() },
            )
        }
    }
}

/** 设置页面顶部栏 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun SettingTopBar(onBack: () -> Unit) {
    CenterAlignedTopAppBar(
        title = {
            Text(
                text = stringResource(R.string.settings),
                color = Color.White,
                fontWeight = FontWeight.SemiBold,
                fontSize = 20.sp,
            )
        },
        navigationIcon = {
            Image(
                modifier = Modifier.padding(horizontal = 12.dp).noRippleClickable { onBack() },
                painter = painterResource(R.drawable.back),
                contentDescription = null,
            )
        },
    )
}

/** 支持与帮助区域 */
@Composable
private fun SupportAndHelpSection(context: Context, onShowDeleteDialog: () -> Unit) {
    SettingSection {
        // 邮件联系
        val email = stringResource(R.string.settings_email_inty)
        SettingNavigationItem(
            title = stringResource(R.string.settings_email_support),
            subtitle = email,
            onClick = { mailTo(context, email) },
        )

        SettingDivider()

        // 举报
        SettingNavigationItem(
            title = stringResource(R.string.str_report),
            onClick = { ReportActivity.launch(context) },
        )

        SettingDivider()

        // 用户协议
        SettingNavigationItem(
            title = stringResource(R.string.terms_of_use),
            onClick = {
                val intent =
                    Intent(
                        Intent.ACTION_VIEW,
                        context.getString(R.string.url_user_agreement).toUri(),
                    )
                context.startActivity(intent)
            },
        )

        SettingDivider()

        // 隐私政策
        SettingNavigationItem(
            title = stringResource(R.string.privacy_policy),
            onClick = {
                val intent =
                    Intent(
                        Intent.ACTION_VIEW,
                        context.getString(R.string.url_privacy_policy).toUri(),
                    )
                context.startActivity(intent)
            },
        )

        SettingDivider()

        // 删除账号
        SettingNavigationItem(
            title = stringResource(R.string.settings_str_delete_account),
            onClick = onShowDeleteDialog,
        )

        SettingDivider()

        // 订阅管理
        // VIP状态
        val vipStatus by BillingRepository.vipStatusFlow.collectAsState()
        val str =
            if (vipStatus.isSubscribed) {
                stringResource(R.string.settings_subscription_management)
            } else {
                stringResource(R.string.settings_update_subscription)
            }
        SettingNavigationItem(
            title = str,
            onClick = {
                if (vipStatus.isSubscribed) {
                    SubsManageActivity.launch(context)
                } else {
                    VipCenterActivity.launch(context)
                }
            },
        )

        SettingDivider()

        // 版本号
        val uriHandler = LocalUriHandler.current
        SettingNavigationItem(
            title = stringResource(R.string.settings_about),
            subtitle =
                if (IntySetting.hasAppUpdateTips())
                    stringResource(R.string.version_update_available, BuildConfig.VERSION_NAME)
                else BuildConfig.VERSION_NAME,
            onClick = {
                runCatching {
                    val url = IntySetting.appGooglePlayUrl()
                    if (url.isNotBlank()) uriHandler.openUri(url)
                }
            },
            showRedDot = IntySetting.hasAppUpdateTips(),
        )
    }
}

/** 设置对话框 */
@Composable
private fun SettingDialogs(
    dialogState: DialogState,
    onHideDeleteDialog: () -> Unit,
    onConfirmDelete: () -> Unit,
) {
    // 删除账号对话框
    if (dialogState.showDeleteAccountDialog) {
        DeleteAccountDialog(onDismiss = onHideDeleteDialog, onConfirm = onConfirmDelete)
    }

    // 高级模型对话框
    if (dialogState.showPremiumDialog) {
        val context = LocalContext.current
        // 检查是否正式登录（非游客且已登录）
        if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
            // 去会员中心
            VipCenterActivity.launch(context)
        } else {
            // 如果未登录，要求先登录
            LoginActivity.launch(context)
        }
    }
}

/** 发送邮件 */
private fun mailTo(context: Context, email: String) {
    val intent = Intent(Intent.ACTION_SENDTO).apply { data = "mailto:$email".toUri() }
    try {
        context.startActivity(Intent.createChooser(intent, "email"))
    } catch (e: Exception) {
        ToastUtils.showShort(R.string.toast_email_error)
    }
}

@Preview(showBackground = true)
@Composable
private fun SettingContentPreview() {
    SettingContent(modifier = Modifier.fillMaxSize(), onBack = {}, onLogout = {})
}
