package com.ai.intellimate.settings

// import com.ai.intellimate.vip.VipCenterActivity
import ai.sxwl.android.data.billing.BillingRepository
import ai.sxwl.android.data.billing.VipStatus
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.data.store.SettingStateManager
import ai.sxwl.android.design.theme.HeartColor
import ai.sxwl.android.design.theme.VibeModeColors
import ai.sxwl.android.design.ui.HeartTopAppBar
import ai.sxwl.android.design.ui.IntelliMateDivider
import ai.sxwl.android.design.ui.SettingsArrowItem
import ai.sxwl.android.design.ui.SettingsItemData
import ai.sxwl.android.design.ui.SettingsItemGroup
import ai.sxwl.android.design.ui.SettingsSwitchItem
import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.utils.ClipboardUtils
import ai.sxwl.android.utils.ToastUtils
import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.net.toUri
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import com.ai.intellimate.BuildConfig
import com.ai.intellimate.MainViewModel
import com.ai.intellimate.R
import com.ai.intellimate.boost.BoostManager
import com.ai.intellimate.chat.viewmodel.ChatViewModel
import com.ai.intellimate.ui.UiConfigs
import com.ai.intellimate.ui.components.DeleteAccountDialog
import com.ai.intellimate.ui.components.LogoutConfirmDialog
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
    val sendUxUiGestureSignals by SettingStateManager.sendUxUiGestureSignalsFlow.collectAsState()

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
            VibeModeBanner(
                isSubscribed = state.isVipSubscribed,
                onRequestSubscribe = {
                    navController.navigate(Routes.Me.vipCenter("settings_vibe_mode"))
                },
            )
            Spacer(Modifier.height(16.dp))
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

            Spacer(Modifier.height(16.dp))

            GestureSignalSettingsSection(
                enabled = sendUxUiGestureSignals,
                onEnabledChange = { enabled ->
                    SettingStateManager.updateSendUxUiGestureSignals(enabled)
                },
            )

            // Debug 环境后端切换（仅 debug 可见）
            if (BuildConfig.BUILD_TYPE.equals("debug", ignoreCase = true)) {
                Spacer(Modifier.height(16.dp))
                DebugBackendSettingsEntry()

                Spacer(Modifier.height(16.dp))
                DebugBoostPointsEntry()

                Spacer(Modifier.height(16.dp))
                DebugVipStatus()

                Spacer(Modifier.height(16.dp))
                DebugFcmTokenEntry()

                Spacer(Modifier.height(16.dp))
                DebugClearLastRankDateEntry(chatViewModel = chatViewModel)
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

/**
 * Settings section for the "Send UX/UI gesture signals" toggle (chat background tap/swipe → AI).
 */
@Composable
private fun GestureSignalSettingsSection(enabled: Boolean, onEnabledChange: (Boolean) -> Unit) {
    SettingsItemGroup {
        SettingsSwitchItem(
            item =
                SettingsItemData.SwitchItemData(
                    title = stringResource(R.string.settings_send_ux_ui_gesture_signals),
                    checked = enabled,
                ),
            isInGroup = true,
            onCheckChanged = onEnabledChange,
        )
    }
}

@Composable
private fun DebugVipStatus() {
    SettingsItemGroup(modifier = Modifier.padding(12.dp)) {
        Column(Modifier.fillMaxWidth()) {
            val vipStatus by BillingRepository.debugVipStatus.collectAsState()

            Text(
                text = "Vip订阅状态",
                color = Color.White.copy(alpha = 0.7f),
                style = MaterialTheme.typography.bodySmall,
            )
            Spacer(Modifier.height(12.dp))

            FlowRow(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                FilterChip(
                    onClick = { BillingRepository.setDebugVipStatus(null) },
                    selected = vipStatus == null,
                    label = { Text("同步后端") },
                )

                FilterChip(
                    onClick = {
                        BillingRepository.setDebugVipStatus(
                            VipStatus(
                                isSubscribed = true,
                                subscriptionStatus = VipStatus.UI_SUBSCRIBED,
                            )
                        )
                    },
                    selected = vipStatus?.isSubscribed == true,
                    label = { Text("订阅") },
                )

                FilterChip(
                    onClick = {
                        BillingRepository.setDebugVipStatus(
                            VipStatus(
                                isSubscribed = false,
                                subscriptionStatus = VipStatus.UI_UNSUBSCRIBED,
                            )
                        )
                    },
                    selected = vipStatus?.isSubscribed == false,
                    label = { Text("非订阅") },
                )
            }
        }
    }
}

/**
 * Debug 下展示当前设备 FCM Token，支持长按复制。
 *
 * 使用范围：仅 build type 为 debug 时在 Me → Settings 页展示，位于现有 Debug 区块（后端切换、Boost、Vip 状态）下方。 预期效果：进入设置后异步拉取
 * FCM token，展示为一行文案（加载中 / Unavailable / token 字符串），长按可复制 token 到剪贴板并提示已复制。 无入参，无可配置项。
 */
@Composable
private fun DebugFcmTokenEntry() {
    val context = LocalContext.current
    var token by remember { mutableStateOf<String?>(null) }
    LaunchedEffect(Unit) { token = runCatching { FirebaseManager.registerFCM() }.getOrElse { "" } }
    val title = stringResource(R.string.settings_debug_fcm_token)
    val content =
        when {
            token == null -> stringResource(R.string.settings_debug_fcm_token_loading)
            token.isNullOrBlank() -> stringResource(R.string.settings_user_id_unavailable)
            else -> token!!
        }
    val tokenToCopy = token
    SettingsItemGroup {
        SettingsArrowItem(
            item = SettingsItemData.CommonItemData(title = title, content = content, arrow = false),
            isInGroup = true,
            onLongClick = {
                if (!tokenToCopy.isNullOrBlank()) {
                    ClipboardUtils.copyToClipboard(context, label = title, text = tokenToCopy)
                    ToastUtils.showShort(R.string.toast_copied_to_clipboard)
                }
            },
        )
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

/** The Vibe Mode 卡片：订阅用户可开关，未订阅点击跳转会员中心。原在 Me 页，已移至设置页顶部。 */
@Composable
private fun VibeModeBanner(
    modifier: Modifier = Modifier,
    isSubscribed: Boolean,
    onRequestSubscribe: () -> Unit,
) {
    var vibeEnabled by remember { mutableStateOf(false) }
    val isActive = isSubscribed && vibeEnabled

    LaunchedEffect(isSubscribed) {
        if (isSubscribed) {
            vibeEnabled = IntySetting.isVibeModeEnabledSuspend()
        } else {
            vibeEnabled = false
        }
    }

    LaunchedEffect(vibeEnabled, isSubscribed) {
        if (isSubscribed) {
            IntySetting.setVibeModeEnabledSuspend(vibeEnabled)
        } else {
            if (vibeEnabled) vibeEnabled = false
        }
    }

    val backgroundBrush =
        when {
            !isSubscribed ->
                Brush.linearGradient(
                    listOf(VibeModeColors.DisabledStart, VibeModeColors.DisabledEnd)
                )
            isActive ->
                Brush.horizontalGradient(
                    listOf(VibeModeColors.ActiveStart, VibeModeColors.ActiveEnd)
                )
            else ->
                Brush.horizontalGradient(
                    listOf(VibeModeColors.InactiveStart, VibeModeColors.InactiveEnd)
                )
        }

    val shape = RoundedCornerShape(UiConfigs.MePage.SectionBannerCornerRadius)
    val borderColor =
        if (isActive) Color.White.copy(alpha = 0.45f)
        else Color.White.copy(alpha = UiConfigs.Alpha.SubtleBorder)

    val switchColors =
        SwitchDefaults.colors(
            checkedThumbColor = Color.White,
            checkedTrackColor = VibeModeColors.SwitchTrackActive,
            uncheckedThumbColor = Color.White,
            uncheckedTrackColor =
                if (isSubscribed) VibeModeColors.SwitchTrackInactive
                else VibeModeColors.SwitchTrackDisabled,
            checkedBorderColor = Color.Transparent,
            uncheckedBorderColor = Color.Transparent,
            disabledCheckedThumbColor = Color.White,
            disabledCheckedTrackColor = VibeModeColors.SwitchTrackActive,
            disabledUncheckedThumbColor = Color.White.copy(alpha = UiConfigs.Alpha.DisabledButton),
            disabledUncheckedTrackColor = VibeModeColors.SwitchTrackDisabled,
            disabledCheckedBorderColor = Color.Transparent,
            disabledUncheckedBorderColor = Color.Transparent,
        )

    val baseModifier =
        modifier
            .clip(shape)
            .background(brush = backgroundBrush, shape = shape)
            .border(
                width = UiConfigs.MePage.VibeMode.BorderWidth,
                color = borderColor,
                shape = shape,
            )
            .padding(
                horizontal = UiConfigs.MePage.SectionBannerHorizontalPadding,
                vertical = UiConfigs.MePage.SectionBannerVerticalPadding,
            )

    Row(
        modifier =
            baseModifier.then(
                if (isSubscribed) Modifier else Modifier.clickable(onClick = onRequestSubscribe)
            ),
        verticalAlignment = androidx.compose.ui.Alignment.CenterVertically,
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text =
                    stringResource(
                        if (isActive) R.string.vibe_mode_active_title else R.string.vibe_mode_title
                    ),
                color = Color.White,
                fontSize = UiConfigs.Typography.ButtonLarge,
                fontWeight = FontWeight.SemiBold,
            )
            if (!isActive) {
                Text(
                    text = stringResource(R.string.vibe_mode_subtitle),
                    color = Color.White.copy(alpha = UiConfigs.Alpha.DimmedText),
                    fontSize = UiConfigs.Typography.Support,
                    lineHeight = UiConfigs.LineHeight.Support,
                )
            }
        }
        Spacer(Modifier.width(UiConfigs.MePage.VibeMode.ContentSpacing))
        val toggleContentDescription = stringResource(R.string.vibe_mode_toggle_content_desc)
        Box {
            Switch(
                checked = isActive,
                onCheckedChange = { if (isSubscribed) vibeEnabled = it },
                enabled = isSubscribed,
                colors = switchColors,
                modifier = Modifier.semantics { contentDescription = toggleContentDescription },
            )
            if (!isSubscribed) {
                Box(modifier = Modifier.matchParentSize().clickable(onClick = onRequestSubscribe))
            }
        }
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
            onItemClick = {
                //                ReportActivity.launchFeedback(context)
                navController.navigate(Routes.Me.reportPage(true))
            },
        )

        IntelliMateDivider()

        // 举报
        SettingsArrowItem(
            item = SettingsItemData.CommonItemData(title = stringResource(R.string.str_report)),
            isInGroup = true,
            onItemClick = {
                //                ReportActivity.launch(context)
                navController.navigate(Routes.Me.reportPage(false))
            },
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
                    //                    SubsManageActivity.launch(context)
                    navController.navigate(Routes.Me.SubsManagement)
                } else {
                    navController.navigate(Routes.Me.vipCenter("settings"))
                }
            },
        )

        IntelliMateDivider()

        val playStoreUrl = playStoreUrl()
        // 版本号
        val versionTitle = stringResource(R.string.settings_version)
        val versionName = BuildConfig.VERSION_NAME
        SettingsArrowItem(
            item =
                SettingsItemData.CommonItemData(
                    title = versionTitle,
                    content =
                        if (hasAppUpdateTips) {
                            stringResource(R.string.version_update_available, versionName)
                        } else {
                            versionName
                        },
                    arrow = true,
                ),
            isInGroup = true,
            showRedDot = hasAppUpdateTips,
            onItemClick = {
                runCatching { uriHandler.openUri(playStoreUrl) }
                    .onFailure { ToastUtils.showShort(R.string.toast_google_play_unavailable) }
            },
            onLongClick = {
                ClipboardUtils.copyToClipboard(context, label = versionTitle, text = versionName)
                ToastUtils.showShort(R.string.toast_copied_to_clipboard)
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

/** Debug 环境 Credits 测试入口（仅 debug 可见） */
@Composable
private fun DebugBoostPointsEntry() {
    SettingsItemGroup {
        SettingsArrowItem(
            item =
                SettingsItemData.CommonItemData(
                    title = "Add 10000 Credits (Debug)",
                    content = "Click to add 10000 credits for testing",
                ),
            isInGroup = true,
            onItemClick = {
                BoostManager.requestManualPoints(10000)
                ToastUtils.showShort("Added 10000 credits!")
            },
        )
    }
}

/**
 * Debug 下清除 KEY_LAST_RANK_DATE 缓存入口。 使用范围：仅 build type 为 debug 时在 Me → Settings 页展示。点击后直接调用
 * ChatViewModel.testRank()。
 */
@Composable
private fun DebugClearLastRankDateEntry(chatViewModel: ChatViewModel) {
    SettingsItemGroup {
        SettingsArrowItem(
            item =
                SettingsItemData.CommonItemData(
                    title = stringResource(R.string.settings_debug_clear_last_rank_date),
                    content = stringResource(R.string.settings_debug_clear_last_rank_date_hint),
                    arrow = false,
                ),
            isInGroup = true,
            onItemClick = { chatViewModel.testRank() },
        )
    }
}
