package com.ai.inty.chat

import android.app.Activity
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.ime
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material3.DrawerValue
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.LifecycleStartEffect
import com.ai.inty.Constant
import com.ai.inty.R
import com.ai.inty.billing.BillingRepository
import com.ai.inty.ui.AdvancedModelChatDialog
import com.ai.inty.ui.ChatDialogData
import com.ai.inty.ui.UnlimitChatDialog
import com.ai.inty.utils.SecurityUtils
import com.ai.inty.viewmodels.ChatViewModel
import com.inty.utils.storage.IntySetting
import com.therouter.TheRouter
import kotlinx.coroutines.launch

@Composable
internal fun ChatPage(
    modifier: Modifier,
    chatViewModel: ChatViewModel,
    onFollowAgent: ((String) -> Unit)? = null,
    showBackButton: Boolean = false,
    onBack: (() -> Unit)? = null,
) {

    val context = LocalContext.current

    LifecycleStartEffect(chatViewModel) {
        chatViewModel.queryMsgs()
        if (context is Activity) {
            SecurityUtils.enableSecureMode(context)
        }
        onStopOrDispose {
            if (context is Activity) {
                SecurityUtils.disableSecureMode(context)
            }
        }
    }

    val density = LocalDensity.current
    val agentInfo = chatViewModel.agentInfo.collectAsState().value
    val focusManager = LocalFocusManager.current

    // 检测键盘状态
    val imeHeight = WindowInsets.ime.getBottom(density)
    val isKeyboardVisible = imeHeight > 0

    // 动态计算底部间距
    val bottomPadding = when {
        showBackButton -> 10.dp // 独立聊天页面：固定10dp
        isKeyboardVisible -> 10.dp // 首页聊天页面，键盘呼出时：10dp
        else -> 90.dp // 首页聊天页面，无键盘时：90dp（给底部tab留出更多间隔）
    }

    // Keep talking二状态设置：默认跟随全局设置
    var agentKeepTalking by remember(agentInfo?.id) {
        mutableStateOf(
            agentInfo?.let {
                // 获取角色专用设置，如果不存在则使用全局设置
                IntySetting.getAgentKeepTalking(it.id) ?: IntySetting.isShowKeepTalking()
            } ?: false
        )
    }

    // 用于实时更新按钮显示状态
    var shouldShowButton by remember(agentInfo?.id) { mutableStateOf(agentKeepTalking) }

    // VIP状态
    val vipStatus = BillingRepository.vipStatusFlow.collectAsState().value

    // Premium model二状态设置：默认跟随全局设置，但受VIP状态限制
    var agentPremiumModel by remember(agentInfo?.id, vipStatus.isSubscribed) {
        mutableStateOf(
            if (!vipStatus.isSubscribed) {
                // 如果不是VIP，强制关闭Premium model
                false
            } else {
                agentInfo?.let {
                    // 获取角色专用设置，如果不存在则使用全局设置
                    IntySetting.getAgentPremiumModel(it.id) ?: IntySetting.isShowPremiumModel()
                } ?: false
            }
        )
    }

    var showMorePanel by remember { mutableStateOf(false) }
    var showPremiumDialog by remember { mutableStateOf(false) }

    Box(
        modifier = modifier
            .pointerInput(Unit) {
                detectTapGestures(
                    onTap = {
                        focusManager.clearFocus()
                    }
                )
            }
    ) {
        // 背景
        ChatBackground(agentInfo = agentInfo)

        val drawerState = remember { mutableStateOf(DrawerValue.Closed) }
        val scope = rememberCoroutineScope()

        Scaffold(
            modifier = Modifier
                .fillMaxSize()
                .background(Color.Transparent),
            containerColor = Color.Transparent,
            contentWindowInsets = WindowInsets(0),
        ) { innerPadding ->

            Column(
                modifier = Modifier
                    .padding(innerPadding)
                    .imePadding()
            ) {
                Spacer(Modifier.height(48.dp))

                if (agentInfo != null) {
                    ChatTopBar(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(36.dp)
                            .padding(horizontal = 18.dp, vertical = 0.dp),
                        agentInfo = agentInfo,
                        showBackButton = showBackButton,
                        onBack = onBack,
                        onClickMore = {
                            scope.launch {
                                if (drawerState.value == DrawerValue.Closed) {
                                    drawerState.value = DrawerValue.Open
                                } else {
                                    drawerState.value = DrawerValue.Closed
                                }
                            }
                        },
                        onFollowAgent = onFollowAgent
                    )
                }

                Spacer(Modifier.height(16.dp))

                // Premium model标签
                if (agentInfo != null) {
                    PremiumModelTag(
                        isPremiumModel = agentPremiumModel,
                        onClick = {
                            // 检查VIP状态
                            if (!vipStatus.isSubscribed) {
                                // 如果不是VIP，显示高级模型的弹窗
                                showPremiumDialog = true
                            } else {
                                // 如果是VIP，打开聊天设置抽屉，让用户手动设置开关
                                scope.launch {
                                    if (drawerState.value == DrawerValue.Closed) {
                                        drawerState.value = DrawerValue.Open
                                    } else {
                                        drawerState.value = DrawerValue.Closed
                                    }
                                }
                            }
                        }
                    )
                    Spacer(Modifier.height(8.dp))
                    // 高级模型弹窗
                    if (showPremiumDialog) {
                        val data = ChatDialogData(
                            R.drawable.img_advanced_model_dialog_bg,
                            stringResource(R.string.str_premium_mode_dialog_content),
                            stringResource(R.string.settings_premium_model)
                        )
                        AdvancedModelChatDialog(
                            data,
                            onCancel = { showPremiumDialog = false },
                            onSure = {
                                // 检查是否正式登录（非游客且已登录）
                                if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                                    if (context is Activity) {
                                        // 购买最低档位的订阅
                                        chatViewModel.purchaseFirstVip(context)
                                    }
                                } else {
                                    //如果未登录，要求先登录
                                    TheRouter.build(Constant.ROUTE_LOGIN)
                                        .navigation(context)
                                }
                                showPremiumDialog = false

                            },
                            onMoreInfo = {
                                // 检查是否正式登录（非游客且已登录）
                                if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                                    // 去会员中心
                                    TheRouter.build(Constant.ROUTE_VIP_CENTER).navigation()
                                } else {
                                    //如果未登录，要求先登录
                                    TheRouter.build(Constant.ROUTE_LOGIN)
                                        .navigation(context)
                                }
                                showPremiumDialog = false
                            }
                        )
                    }
                }

                LazyColumn(
                    modifier = Modifier
                        .weight(1f)
                        .padding(horizontal = 16.dp),
                    reverseLayout = true,
                ) {
                    val msgs = chatViewModel.msgs
                    item {
                        Spacer(Modifier.height(16.dp))
                    }
                    //可能会index或者key不唯一的异常
                    runCatching {
                        val items = msgs.filter { !(it.role == "user" && it.content == "continue") }
                        if (items.isNotEmpty()) {
                            itemsIndexed(items) { index, item ->
                                ChatItem(item)
                                Spacer(Modifier.height(16.dp))
                            }
                        }
                    }.onFailure { it.printStackTrace() }

                }

                // 输入框区域
                Column {
                    // Keep talking 按钮
                    KeepTalkingButton(
                        visible = shouldShowButton,
                        onClick = { chatViewModel.sendKeepTalkingMessage() }
                    )

                    // 输入框
                    ChatInput(
                        chatViewModel = chatViewModel,
                        onSendMessage = { chatViewModel.sendMsg() },
                        onToggleMorePanel = { showMorePanel = !showMorePanel },
                        showMorePanel = showMorePanel,
                        bottomPadding = bottomPadding
                    )
                }
            }
        }

        // MorePanel
        ChatMorePanel(
            visible = showMorePanel,
            agentInfo = agentInfo,
            onDismiss = { showMorePanel = false }
        )

        // 聊天设置抽屉
        ChatSettingsDrawer(
            chatViewModel = chatViewModel,
            agentInfo = agentInfo,
            drawerState = drawerState,
            onPremiumDialogShow = { show -> showPremiumDialog = show },
            onPremiumModeChange = { mode -> agentPremiumModel = mode }
        )

        //免费聊天次数限制的dialog
        ShowLimitDialog(chatViewModel)

    }
}

@Composable
private fun ShowLimitDialog(chatViewModel: ChatViewModel) {
    val showDialog by chatViewModel.showLimitDialog.collectAsState()
    val context = LocalContext.current
    if (showDialog) {
        val data = ChatDialogData(
            R.drawable.img_unlimit_dialog_bg,
            stringResource(R.string.str_unlimit_dialog_content),
            stringResource(R.string.str_unlimit_btn_text)
        )
        UnlimitChatDialog(
            data,
            onCancel = {
                chatViewModel.dismissDialog()
            },
            onSure = {
                // 检查是否正式登录（非游客且已登录）
                if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                    if (context is Activity) {
                        //最低档位购买会员订阅
                        chatViewModel.purchaseFirstVip(context)
                    }
                } else {
                    //如果未登录，要求先登录
                    TheRouter.build(Constant.ROUTE_LOGIN)
                        .navigation(context)
                }
                chatViewModel.dismissDialog()
            },
            onMoreInfo = {
                // 检查是否正式登录（非游客且已登录）
                if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                    // 去会员中心
                    TheRouter.build(Constant.ROUTE_VIP_CENTER).navigation()
                } else {
                    //如果未登录，要求先登录
                    TheRouter.build(Constant.ROUTE_LOGIN)
                        .navigation(context)
                }
                chatViewModel.dismissDialog()
            },
        )
    }
}
