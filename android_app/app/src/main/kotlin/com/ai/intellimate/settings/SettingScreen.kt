package com.ai.intellimate.settings

// import com.ai.intellimate.vip.VipCenterActivity
import ai.sxwl.android.design.theme.HeartColor
import ai.sxwl.android.design.ui.HeartTopAppBar
import ai.sxwl.android.design.ui.IntelliMateDivider
import ai.sxwl.android.design.ui.SettingsArrowItem
import ai.sxwl.android.design.ui.SettingsItemData
import ai.sxwl.android.design.ui.SettingsItemGroup
import ai.sxwl.android.utils.ClipboardUtils
import ai.sxwl.android.utils.ToastUtils
import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.core.net.toUri
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import com.ai.intellimate.BuildConfig
import com.ai.intellimate.MainViewModel
import com.ai.intellimate.R
import com.ai.intellimate.agent.report.ReportActivity
import com.ai.intellimate.boost.BoostManager
import com.ai.intellimate.chat.viewmodel.ChatViewModel
import com.ai.intellimate.ui.UiConfigs
import com.ai.intellimate.ui.components.DeleteAccountDialog
import com.ai.intellimate.ui.components.LogoutConfirmDialog
import com.ai.intellimate.vip.SubsManageActivity
import com.ai.intellimate.xb.navigation.Routes
import kotlinx.coroutines.flow.collectLatest

private const val GOOGLE_PLAY_MARKET_URL_PREFIX = "market://details?id="

/** 设置页面主内容 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingScreen(
    navController: NavController,
    modifier: Modifier = Modifier,
    //    onBack: () -> Unit,
    //    onLogout: (isDelete: Boolean) -> Unit,
    mainViewModel: MainViewModel,
    chatViewModel: ChatViewModel,
    viewModel: SettingViewModel = viewModel(),
) {
    val context = LocalContext.current
    val state = viewModel.state.collectAsState().value

    fun onLogout(isDelete: Boolean) {
        mainViewModel.logout()
        chatViewModel.clearAllData()
        val str =
            if (isDelete) context.getString(R.string.delete_account_successfully)
            else context.getString(R.string.logout_successfully)
        ToastUtils.showShort(str)
    }

    // 每次打开设置界面时，重置删除账号结果状态和对话框状态，避免残留状态导致误触发
    // 这可以防止在删除账号后，再次登录并打开设置界面时误触发 onLogout(true) 或显示对话框
    LaunchedEffect(Unit) {
        viewModel.resetDeleteAccountResult()
        viewModel.resetDialogState()
        // 刷新用户数据，确保显示最新状态
        viewModel.refreshUserData()
    }

    // 监听删除账号结果
    LaunchedEffect(viewModel) {
        viewModel.deleteAccountResultFlow.collectLatest { deleted ->
            if (deleted) {
                // 账号删除成功，先关闭对话框
                viewModel.hideDeleteAccountDialog()
                // 立即重置状态，避免残留导致下次打开设置界面时误触发
                // 注意：SettingViewModel 的作用域是 MainActivity，如果不重置，
                // 下次打开设置界面时会再次触发 onLogout(true)
                viewModel.resetDeleteAccountResult()
                // 触发登出流程
                onLogout(true)
            }
        }
    }

    Scaffold(
        modifier = modifier,
        containerColor = HeartColor.primaryColor,
        topBar = {
            HeartTopAppBar(
                modifier = Modifier.background(color = HeartColor.primaryColor),
                title = stringResource(R.string.settings),
                navIcon = R.drawable.back,
                //                onBack = onBack,
                onBack = { navController.popBackStack() },
            )
        },
    ) { innerPadding ->
        val scrollState = rememberScrollState()
        Column(
            modifier = Modifier.verticalScroll(scrollState).padding(innerPadding).padding(16.dp)
        ) {
            AccountInfoSection(userId = state.userId, userEmail = state.userEmail)

            Spacer(Modifier.height(16.dp))

            // 支持与帮助区域
            SupportAndHelpSection(
                navController,
                isVipSubscribed = state.isVipSubscribed,
                hasAppUpdateTips = state.hasAppUpdateTips,
                context = context,
            )

            Spacer(Modifier.height(16.dp))

            // 退出登录按钮
            LogoutButton(
                onLogout = { viewModel.showLogoutConfirmDialog() },
                onDeleteAccount = { viewModel.showDeleteAccountDialog() },
            )

            // Debug 环境后端切换（仅 debug 可见）
            if (BuildConfig.BUILD_TYPE.equals("debug", ignoreCase = true)) {
                Spacer(Modifier.height(16.dp))
                DebugBackendSettingsEntry()

                Spacer(Modifier.height(16.dp))
                DebugBoostPointsEntry()
            }

            // 对话框
            SettingDialogs(
                dialogState = state.dialogState,
                onHideDeleteDialog = { viewModel.hideDeleteAccountDialog() },
                onConfirmDelete = { viewModel.deleteUserAccount() },
                onHideLogoutDialog = { viewModel.hideLogoutConfirmDialog() },
                onConfirmLogout = {
                    viewModel.hideLogoutConfirmDialog()
                    onLogout(false)
                },
            )
        }
    }
}

/** 账号信息区域 */
@Composable
private fun AccountInfoSection(userId: String, userEmail: String) {
    val context = LocalContext.current
    val displayId = userId.ifBlank { stringResource(R.string.settings_user_id_unavailable) }
    val displayEmail =
        userEmail.ifBlank { stringResource(R.string.settings_user_email_unavailable) }
    val userIdTitle = stringResource(R.string.settings_user_id)
    val userEmailTitle = stringResource(R.string.settings_user_email)

    SettingsItemGroup {
        SettingsArrowItem(
            item =
                SettingsItemData.CommonItemData(
                    title = userIdTitle,
                    content = displayId,
                    arrow = false,
                ),
            isInGroup = true,
            onLongClick = {
                if (userId.isNotBlank()) {
                    ClipboardUtils.copyToClipboard(context, label = userIdTitle, text = userId)
                    ToastUtils.showShort(R.string.toast_copied_to_clipboard)
                }
            },
        )

        IntelliMateDivider()

        SettingsArrowItem(
            item =
                SettingsItemData.CommonItemData(
                    title = userEmailTitle,
                    content = displayEmail,
                    arrow = false,
                ),
            isInGroup = true,
            selectableContent = true,
            onLongClick = {
                if (userEmail.isNotBlank()) {
                    ClipboardUtils.copyToClipboard(
                        context,
                        label = userEmailTitle,
                        text = userEmail,
                    )
                    ToastUtils.showShort(R.string.toast_copied_to_clipboard)
                }
            },
        )
    }
}

/** 支持与帮助区域 */
@Composable
private fun SupportAndHelpSection(
    navController: NavController,
    isVipSubscribed: Boolean,
    hasAppUpdateTips: Boolean,
    context: Context,
) {
    val uriHandler = LocalUriHandler.current
    SettingsItemGroup {
        // 邮件联系
        val email = stringResource(R.string.settings_email_inty)
        SettingsArrowItem(
            item =
                SettingsItemData.CommonItemData(
                    title = stringResource(R.string.settings_email_support),
                    content = email,
                ),
            isInGroup = true,
            onItemClick = { mailTo(context, email) },
        )

        IntelliMateDivider()

        // 帮助中心
        SettingsArrowItem(
            item = SettingsItemData.CommonItemData(title = stringResource(R.string.settings_help)),
            isInGroup = true,
            onItemClick = {
                runCatching { uriHandler.openUri(UiConfigs.Urls.HelpCenter) }
                    .onFailure { ToastUtils.showShort(R.string.toast_navigation_failed) }
            },
        )

        IntelliMateDivider()

        // Feedback
        SettingsArrowItem(
            item = SettingsItemData.CommonItemData(title = stringResource(R.string.str_feedback)),
            isInGroup = true,
            onItemClick = { ReportActivity.launchFeedback(context) },
        )

        IntelliMateDivider()

        // 举报
        SettingsArrowItem(
            item = SettingsItemData.CommonItemData(title = stringResource(R.string.str_report)),
            isInGroup = true,
            onItemClick = { ReportActivity.launch(context) },
        )

        IntelliMateDivider()

        // 用户协议
        SettingsArrowItem(
            item = SettingsItemData.CommonItemData(title = stringResource(R.string.terms_of_use)),
            isInGroup = true,
            onItemClick = {
                val intent =
                    Intent(
                        Intent.ACTION_VIEW,
                        context.getString(R.string.url_user_agreement).toUri(),
                    )
                context.startActivity(intent)
            },
        )

        IntelliMateDivider()

        // 隐私政策
        SettingsArrowItem(
            item = SettingsItemData.CommonItemData(title = stringResource(R.string.privacy_policy)),
            isInGroup = true,
            onItemClick = {
                val intent =
                    Intent(
                        Intent.ACTION_VIEW,
                        context.getString(R.string.url_privacy_policy).toUri(),
                    )
                context.startActivity(intent)
            },
        )

        IntelliMateDivider()

        // 订阅管理
        val subscriptionTitle =
            if (isVipSubscribed) {
                stringResource(R.string.settings_subscription_management)
            } else {
                stringResource(R.string.settings_update_subscription)
            }
        SettingsArrowItem(
            item = SettingsItemData.CommonItemData(title = subscriptionTitle),
            isInGroup = true,
            onItemClick = {
                if (isVipSubscribed) {
                    SubsManageActivity.launch(context)
                } else {
                    navController.navigate(Routes.Me.VipCenter)
                    //                    VipCenterActivity.launch(context,
                    // VipCenterActivity.SETTINGS_SUBSCRIPTION)
                }
            },
        )

        IntelliMateDivider()

        val playStoreUrl = playStoreUrl()
        // 版本号
        SettingsArrowItem(
            item =
                SettingsItemData.CommonItemData(
                    title = stringResource(R.string.settings_version),
                    content =
                        if (hasAppUpdateTips) {
                            stringResource(
                                R.string.version_update_available,
                                BuildConfig.VERSION_NAME,
                            )
                        } else {
                            BuildConfig.VERSION_NAME
                        },
                    arrow = true,
                ),
            isInGroup = true,
            showRedDot = hasAppUpdateTips,
            onItemClick = {
                runCatching { uriHandler.openUri(playStoreUrl) }
                    .onFailure { ToastUtils.showShort(R.string.toast_google_play_unavailable) }
            },
        )

        IntelliMateDivider()

        // Rate us
        SettingsArrowItem(
            item =
                SettingsItemData.CommonItemData(
                    title = stringResource(R.string.settings_rate_us),
                    arrow = true,
                ),
            isInGroup = true,
            onItemClick = {
                if (!openRateUsPage(context = context, fallbackUrl = playStoreUrl)) {
                    ToastUtils.showShort(R.string.toast_google_play_unavailable)
                }
            },
        )
    }
}

/** 打开 Google Play 评价 */
private fun openRateUsPage(context: Context, fallbackUrl: String): Boolean {
    val packageName = BuildConfig.APPLICATION_ID
    val marketUri = "$GOOGLE_PLAY_MARKET_URL_PREFIX$packageName".toUri()
    val marketIntent =
        Intent(Intent.ACTION_VIEW, marketUri).apply {
            addFlags(Intent.FLAG_ACTIVITY_NO_HISTORY or Intent.FLAG_ACTIVITY_NEW_DOCUMENT)
        }

    return try {
        context.startActivity(marketIntent)
        true
    } catch (marketError: ActivityNotFoundException) {
        runCatching {
                val webIntent =
                    Intent(Intent.ACTION_VIEW, fallbackUrl.toUri()).apply {
                        addFlags(
                            Intent.FLAG_ACTIVITY_NO_HISTORY or Intent.FLAG_ACTIVITY_NEW_DOCUMENT
                        )
                    }
                context.startActivity(webIntent)
            }
            .isSuccess
    } catch (error: Exception) {
        false
    }
}

/** 设置对话框 */
@Composable
private fun SettingDialogs(
    dialogState: DialogState,
    onHideDeleteDialog: () -> Unit,
    onConfirmDelete: () -> Unit,
    onHideLogoutDialog: () -> Unit,
    onConfirmLogout: () -> Unit,
) {
    // 删除账号对话框
    if (dialogState.showDeleteAccountDialog) {
        DeleteAccountDialog(onDismiss = onHideDeleteDialog, onConfirm = onConfirmDelete)
    }

    // 退出登录对话框
    if (dialogState.showLogoutConfirmDialog) {
        LogoutConfirmDialog(onDismiss = onHideLogoutDialog, onConfirm = onConfirmLogout)
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

/** Debug 环境 Boost Points 测试入口（仅 debug 可见） */
@Composable
private fun DebugBoostPointsEntry() {
    SettingsItemGroup {
        SettingsArrowItem(
            item =
                SettingsItemData.CommonItemData(
                    title = "Add 10000 Boost Points (Debug)",
                    content = "Click to add 10000 boost points for testing",
                ),
            isInGroup = true,
            onItemClick = {
                BoostManager.requestManualPoints(10000)
                ToastUtils.showShort("Added 10000 boost points!")
            },
        )
    }
}
