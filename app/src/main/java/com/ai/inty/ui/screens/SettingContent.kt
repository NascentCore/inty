package com.ai.inty.ui.screens

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.widget.Toast
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
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.net.toUri
import androidx.lifecycle.viewmodel.compose.viewModel
import com.ai.inty.BuildConfig
import com.ai.inty.Constant
import com.ai.inty.R
import com.ai.inty.base.noRippleClickable
import com.ai.inty.billing.BillingRepository
import com.ai.inty.ui.AdvancedModelChatDialog
import com.ai.inty.ui.ChatDialogData
import com.ai.inty.ui.components.DeleteAccountDialog
import com.ai.inty.ui.components.LogoutButton
import com.ai.inty.ui.components.SettingDivider
import com.ai.inty.ui.components.SettingInfoItem
import com.ai.inty.ui.components.SettingNavigationItem
import com.ai.inty.ui.components.SettingSection
import com.ai.inty.ui.components.SettingSwitchItem
import com.ai.inty.viewmodels.DialogState
import com.ai.inty.viewmodels.MainViewModel
import com.ai.inty.viewmodels.SettingViewModel
import com.ai.inty.viewmodels.SettingsState
import com.therouter.TheRouter
import kotlinx.coroutines.flow.collectLatest

/**
 * 设置页面主内容
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingContent(
    modifier: Modifier = Modifier,
    onBack: () -> Unit,
    onLogout: () -> Unit,
    viewModel: SettingViewModel = viewModel()
) {
    val context = LocalContext.current
    val settingsState by viewModel.settingsState.collectAsState()
    val dialogState by viewModel.dialogState.collectAsState()
    val vipStatus by BillingRepository.vipStatusFlow.collectAsState()

    // 监听删除账号结果
    val mainViewModel = viewModel<MainViewModel>()
    LaunchedEffect(mainViewModel) {
        mainViewModel.deleteAccountResultFlow.collectLatest { deleted ->
            if (deleted) {
                // 账号删除成功
                onLogout()
            }
        }
    }

    Scaffold(
        modifier = modifier,
        topBar = {
            SettingTopBar(onBack = onBack)
        }
    ) { innerPadding ->
        Column(modifier = Modifier.padding(innerPadding)) {

            // 设置选项区域
            SettingOptionsSection(
                settingsState = settingsState,
                vipStatus = vipStatus,
                onToggleKeepTalking = { viewModel.toggleKeepTalking() },
                onTogglePremiumMode = { viewModel.togglePremiumMode() }
            )

            Spacer(Modifier.height(16.dp))

            // 支持与帮助区域
            SupportAndHelpSection(
                context = context,
                onShowDeleteDialog = { viewModel.showDeleteAccountDialog() }
            )

            Spacer(Modifier.height(16.dp))

            // 退出登录按钮
            LogoutButton(onLogout = onLogout)

            // 对话框
            SettingDialogs(
                dialogState = dialogState,
                onHideDeleteDialog = { viewModel.hideDeleteAccountDialog() },
                onConfirmDelete = { mainViewModel.checkAccountSubscribe() },
                onHidePremiumDialog = { viewModel.hidePremiumDialog() }
            )
        }
    }
}

/**
 * 设置页面顶部栏
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun SettingTopBar(
    onBack: () -> Unit
) {
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
                modifier = Modifier
                    .padding(horizontal = 12.dp)
                    .noRippleClickable { onBack() },
                painter = painterResource(R.drawable.back),
                contentDescription = null,
            )
        }
    )
}

/**
 * 设置选项区域
 */
@Composable
private fun SettingOptionsSection(
    settingsState: SettingsState,
    vipStatus: com.ai.inty.billing.VipStatus,
    onToggleKeepTalking: () -> Unit,
    onTogglePremiumMode: () -> Unit
) {
    SettingSection {
        SettingSwitchItem(
            title = stringResource(R.string.settings_keep_talking),
            isEnabled = settingsState.keepTalking,
            onToggle = onToggleKeepTalking
        )

        SettingDivider()

        SettingSwitchItem(
            title = stringResource(R.string.settings_premium_model),
            isEnabled = settingsState.premiumMode,
            onToggle = onTogglePremiumMode
        )
    }
}

/**
 * 支持与帮助区域
 */
@Composable
private fun SupportAndHelpSection(
    context: Context,
    onShowDeleteDialog: () -> Unit
) {
    SettingSection {
        // 邮件联系
        val email = stringResource(R.string.settings_email_inty)
        SettingNavigationItem(
            title = stringResource(R.string.settings_email_support),
            subtitle = email,
            onClick = { mailTo(context, email) }
        )

        SettingDivider()

        // 举报
        SettingNavigationItem(
            title = stringResource(R.string.report),
            onClick = { TheRouter.build(Constant.ROUTE_REPORT).navigation(context) }
        )

        SettingDivider()

        // 用户协议
        SettingNavigationItem(
            title = stringResource(R.string.terms_of_use),
            onClick = {
                val intent = Intent(
                    Intent.ACTION_VIEW,
                    context.getString(R.string.settings_str_user_agreement).toUri()
                )
                context.startActivity(intent)
            }
        )

        SettingDivider()

        // 隐私政策
        SettingNavigationItem(
            title = stringResource(R.string.privacy_policy),
            onClick = {
                val intent = Intent(
                    Intent.ACTION_VIEW,
                    Uri.parse(context.getString(R.string.settings_str_privacy_policy))
                )
                context.startActivity(intent)
            }
        )

        SettingDivider()

        // 删除账号
        SettingNavigationItem(
            title = stringResource(R.string.settings_str_delete_account),
            onClick = onShowDeleteDialog
        )

        SettingDivider()

        // 订阅管理
        val vipStatus by BillingRepository.vipStatusFlow.collectAsState()
        SettingNavigationItem(
            title = stringResource(R.string.settings_subscription_management),
            subtitle = if (vipStatus.isSubscribed) {
                stringResource(R.string.subscribed)
            } else {
                stringResource(R.string.unsubscribed)
            },
            onClick = {
                TheRouter.build(Constant.ROUTE_SUBSCRIPTION_MANAGEMENT).navigation(context)
            }
        )

        SettingDivider()

        // 版本号
        SettingInfoItem(
            title = stringResource(R.string.settings_about),
            value = BuildConfig.VERSION_NAME
        )
    }
}

/**
 * 设置对话框
 */
@Composable
private fun SettingDialogs(
    dialogState: DialogState,
    onHideDeleteDialog: () -> Unit,
    onConfirmDelete: () -> Unit,
    onHidePremiumDialog: () -> Unit
) {
    // 删除账号对话框
    if (dialogState.showDeleteAccountDialog) {
        DeleteAccountDialog(
            onDismiss = onHideDeleteDialog,
            onConfirm = onConfirmDelete
        )
    }

    // 高级模型对话框
    if (dialogState.showPremiumDialog) {
        val data = ChatDialogData(
            R.drawable.img_advanced_model_dialog_bg,
            stringResource(R.string.str_premium_mode_dialog_content),
            stringResource(R.string.settings_premium_model)
        )
        AdvancedModelChatDialog(
            data,
            onCancel = onHidePremiumDialog,
            onSure = {
                // 购买最低档位的订阅
                onHidePremiumDialog()
            },
            onMoreInfo = {
                // 去会员中心
                TheRouter.build(Constant.ROUTE_VIP_CENTER).navigation()
                onHidePremiumDialog()
            }
        )
    }
}

/**
 * 发送邮件
 */
private fun mailTo(context: Context, email: String) {
    val intent = Intent(Intent.ACTION_SENDTO).apply {
        data = Uri.parse("mailto:$email")
    }
    try {
        context.startActivity(Intent.createChooser(intent, "email"))
    } catch (e: Exception) {
        Toast.makeText(context, "email error", Toast.LENGTH_SHORT).show()
    }
}

@Preview(showBackground = true)
@Composable
private fun SettingContentPreview() {
    SettingContent(
        modifier = Modifier.fillMaxSize(),
        onBack = {},
        onLogout = {}
    )
} 
