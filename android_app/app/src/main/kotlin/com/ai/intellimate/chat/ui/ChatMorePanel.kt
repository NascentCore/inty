package com.ai.intellimate.chat.ui

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.billing.BillingRepository
import ai.sxwl.android.data.http.config.NetworkConfig
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.design.theme.HeartColor
import ai.sxwl.android.design.theme.IntelliMateTheme
import ai.sxwl.android.design.tmp.BottomSheetDialog
import ai.sxwl.android.design.tmp.DiaAmountLayout
import ai.sxwl.android.firebase.FirebaseManager
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.ime
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyHorizontalGrid
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Call
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.ProvideTextStyle
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.graphics.RectangleShape
import androidx.compose.ui.layout.onGloballyPositioned
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.navigation.NavController
import com.ai.intellimate.BuildConfig
import com.ai.intellimate.R
import com.ai.intellimate.chat.viewmodel.ChatViewModel
import com.ai.intellimate.ui.ReplyStyleSheet
import com.ai.intellimate.xb.navigation.Routes
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/** 聊天更多面板组件 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatMorePanel(
    navController: NavController,
    visible: Boolean,
    agentInfo: AgentInfo?,
    chatViewModel: ChatViewModel,
    onDismiss: () -> Unit,
    onHeightChange: (Dp) -> Unit,
    onReset: () -> Unit,
    onCall: () -> Unit,
    windowInsets: WindowInsets = WindowInsets.navigationBars,
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var showSheet by remember { mutableStateOf(false) }
    // VIP状态
    val vipStatus by BillingRepository.vipStatusFlow.collectAsState()
    var showResetConfirmDialog by remember { mutableStateOf(false) }

    // 内部状态控制Dialog和BottomSheetDialog的显示
    // 当visible变为false时，先让BottomSheetDialog执行退出动画，然后再关闭Dialog
    var showDialog by remember { mutableStateOf(visible) }
    var showBottomSheet by remember { mutableStateOf(visible) }

    // 当visible变为false时，先触发退出动画，延迟后再关闭Dialog
    LaunchedEffect(visible) {
        if (!visible) {
            // 先让BottomSheetDialog执行退出动画
            showBottomSheet = false
            // 等待退出动画完成（300ms）后再关闭Dialog
            delay(350)
            showDialog = false
            onHeightChange(0.dp)
        } else {
            // visible变为true时，立即显示Dialog和BottomSheet
            showDialog = true
            showBottomSheet = true
        }
    }

    if (!showDialog) {
        return
    }

    if (showResetConfirmDialog) {
        ResetConfirmDialog(
            onReset = {
                onReset()
                showResetConfirmDialog = false
            },
            onDismiss = { showResetConfirmDialog = false },
        )
    }

    Dialog(
        onDismissRequest = {
            // 点击外部关闭时，也先执行退出动画
            scope.launch {
                showBottomSheet = false
                delay(350)
                showDialog = false
                onDismiss()
            }
        },
        properties =
            DialogProperties(usePlatformDefaultWidth = false, decorFitsSystemWindows = false),
    ) {
        DiaAmountLayout {
            SetDiaAmount(0f)
            BottomSheetDialog(
                modifier = Modifier,
                visible = showBottomSheet,
                onDismissRequest = {
                    // 关闭时先执行退出动画
                    scope.launch {
                        showBottomSheet = false
                        delay(350)
                        showDialog = false
                        onDismiss()
                    }
                },
                // ChatMorePanel 出现时直接展示并占据位置，不使用滑入动画
                slideInOnEnter = false,
            ) {
                val density = LocalDensity.current
                // 获取键盘高度，用于匹配panel高度，避免键盘消失时输入框高度变化
                val imeHeight = WindowInsets.ime.getBottom(density)
                val keyboardHeightDp = with(density) { imeHeight.toDp() }

                LazyVerticalGrid(
                    columns = GridCells.Fixed(4),
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(color = HeartColor.primaryColor)
                        .windowInsetsPadding(windowInsets)
                        // 如果键盘高度大于0，设置最小高度为键盘高度，确保panel高度至少与键盘一致
                        // 使用 heightIn 而不是 height，允许内容高度大于键盘高度时自适应
                        .then(
                            if (keyboardHeightDp > 0.dp) {
                                Modifier.heightIn(min = keyboardHeightDp)
                            } else {
                                Modifier
                            }
                        )
                        .onGloballyPositioned { coords ->
                            val h = with(density) { coords.size.height.toDp() }
                            onHeightChange(h)
                        },
                    contentPadding = PaddingValues(vertical = 20.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    item("Chat Style") {
                        MorePanelItem(
                            isVip = true,
                            onClick = {
                                // 检查是否已登录
                                if (
                                    IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()
                                ) {
                                    FirebaseManager.logEvent(
                                        FirebaseManager.Events.CHAT_MORE_CLICK,
                                        FirebaseManager.safeEventParams(
                                            "click_type" to "reply_style",
                                            "agent_id" to (agentInfo?.id ?: ""),
                                            "timestamp" to System.currentTimeMillis(),
                                        ),
                                    )
                                    // 已经登录，判断是否vip，是则弹出输入框sheet，否则弹拦截弹窗
                                    if (vipStatus.isSubscribed) {
                                        showSheet = true
                                    } else {
                                        // 去会员中心
                                        navController.navigate(Routes.Me.VipCenter)
                                        onDismiss() // 要关闭掉panel
                                    }
                                }
                            },
                            icon = {
                                Image(
                                    painter = painterResource(R.drawable.icon_reply_chat),
                                    contentDescription = "chatStyle",
                                    modifier = Modifier.fillMaxSize()
                                )
                            },
                            text = {
                                Text(stringResource(R.string.reply_style))
                            }
                        )
                    }

                    item("Reset") {
                        MorePanelItem(
                            onClick = {
                                // 检查是否已登录
                                if (IntySetting.isLogin()) {
                                    // 清空当前chat的所有聊天消息，（保留intro和opening），然后给服务器发送reset消息
                                    // 相当于重新开始和agent初次聊天
                                    showResetConfirmDialog = true
                                }
                            },
                            icon = {
                                Image(
                                    painter = painterResource(R.drawable.icon_reset_chat),
                                    contentDescription = "reset",
                                    modifier = Modifier.fillMaxSize()
                                )
                            },
                            text = {
                                Text(stringResource(R.string.str_reset))
                            }
                        )
                    }

                    item("Feedback") {
                        MorePanelItem(
                            onClick = {
                                // 检查是否已登录
                                if (
                                    IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()
                                ) {
                                    FirebaseManager.logEvent(
                                        FirebaseManager.Events.CHAT_MORE_CLICK,
                                        FirebaseManager.safeEventParams(
                                            "click_type" to "feedback",
                                            "agent_id" to (agentInfo?.id ?: ""),
                                            "timestamp" to System.currentTimeMillis(),
                                        ),
                                    )
                                    navController.navigate(Routes.Me.reportPage(true))
//                                    ReportActivity.launchFeedback(context)
                                }
                            },
                            icon = {
                                Image(
                                    painter = painterResource(R.drawable.icon_feedback),
                                    contentDescription = "feedback",
                                    modifier = Modifier.fillMaxSize()
                                )
                            },
                            text = {
                                Text(stringResource(R.string.str_feedback))
                            }
                        )
                    }

                    item("Report") {
                        MorePanelItem(
                            onClick = {
                                // 检查是否已登录
                                if (
                                    IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()
                                ) {
                                    FirebaseManager.logEvent(
                                        FirebaseManager.Events.CHAT_MORE_CLICK,
                                        FirebaseManager.safeEventParams(
                                            "click_type" to "report",
                                            "agent_id" to (agentInfo?.id ?: ""),
                                            "timestamp" to System.currentTimeMillis(),
                                        ),
                                    )
                                    navController.navigate(Routes.Me.reportPage(false, "AGENT", agentInfo?.id ?: ""))
//                                    ReportActivity.launch(context, agentInfo?.id ?: "", "AGENT")
                                }
                            },
                            icon = {
                                Image(
                                    painter = painterResource(R.drawable.icon_report),
                                    contentDescription = "report",
                                    modifier = Modifier.fillMaxSize()
                                )
                            },
                            text = {
                                Text(stringResource(R.string.str_report))
                            }
                        )
                    }

                    item("Call") {
                        MorePanelItem(
                            onClick = {
                                FirebaseManager.logEvent(
                                    FirebaseManager.Events.CHAT_MORE_CALL,
                                    FirebaseManager.safeEventParams(
                                        "click_type" to "call",
                                        "agent_id" to (agentInfo?.id ?: ""),
                                        "timestamp" to System.currentTimeMillis(),
                                    ),
                                )
                                onCall()
                            },
                            icon = {
                                Image(
                                    imageVector = Icons.Rounded.Call,
                                    contentDescription = "call",
                                    colorFilter = ColorFilter.tint(Color(0x99FFFFFF)),
                                    modifier = Modifier.fillMaxSize()
                                )
                            },
                            text = {
                                Text(stringResource(R.string.call))
                            }
                        )
                    }
                }
            }
        }
    }

    // reply sheet
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)

    LaunchedEffect(showSheet) { if (showSheet) sheetState.show() else sheetState.hide() }

    // 监听chatSettings的变化，确保数据同步
    val chatSettings by chatViewModel.chatSettings.collectAsState()

    // 获取当前agent的聊天设置，确保按agent隔离，并监听chatSettings变化
    val currentChatSetting by
        remember(agentInfo?.id, chatSettings) {
            derivedStateOf {
                agentInfo?.id?.let { agentId -> chatViewModel.getChatSettingForAgent(agentId) }
            }
        }

    val replyStr by
        remember(agentInfo?.id, currentChatSetting) {
            derivedStateOf { (currentChatSetting?.style_prompt ?: "") }
        }
    if (showSheet) {
        ReplyStyleSheet(
            sheetState = sheetState,
            inputStr = replyStr,
            hintStr = stringResource(R.string.reply_hint_str),
            onDismiss = { showSheet = false },
            onSave = { str ->
                // 调用接口 save
                chatViewModel.updateChatReplySettings(str.trim())
                showSheet = false
            },
        )
    }
}

@Composable
private fun MorePanelItem(
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    isVip: Boolean = false,
    icon: @Composable () -> Unit,
    text: @Composable () -> Unit
) {
    Column(
        modifier = modifier.noRippleClickable { onClick() },
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box(
            modifier =
                Modifier
                    .size(64.dp)
                    .background(color = Color.White.copy(0.05f), shape = RoundedCornerShape(8.dp))
        ) {
            Box(
                modifier = Modifier
                    .align(Alignment.Center)
                    .size(36.dp)
            ) {

                icon()
            }

            if (isVip) {
                Image(
                    modifier = Modifier
                        .align(Alignment.TopEnd)
                        .padding(top = 5.dp, end = 2.dp),
                    painter = painterResource(R.drawable.ic_vip_badge),
                    contentDescription = null,
                )
            }
        }
        ProvideTextStyle(
            TextStyle(
                fontSize = 14.sp, fontWeight = FontWeight.Normal, color = Color.White
            ),
            text
        )
    }
}

/** 更多面板项目组件 */
@Composable
private fun MorePanelItem(icon: Int, text: String, isVip: Boolean = false, onClick: () -> Unit) {
    Column(
        modifier = Modifier.noRippleClickable { onClick() },
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box(
            modifier =
                Modifier
                    .size(64.dp)
                    .background(color = Color.White.copy(0.05f), shape = RoundedCornerShape(8.dp))
        ) {
            Image(
                modifier = Modifier
                    .size(36.dp)
                    .align(Alignment.Center),
                painter = painterResource(id = icon),
                contentDescription = null,
            )
            if (isVip) {
                Image(
                    modifier = Modifier
                        .align(Alignment.TopEnd)
                        .padding(top = 5.dp, end = 2.dp),
                    painter = painterResource(R.drawable.ic_vip_badge),
                    contentDescription = null,
                )
            }
        }
        Spacer(Modifier.height(6.dp))
        Text(text = text, fontSize = 14.sp, fontWeight = FontWeight.Normal, color = Color.White)
    }
}

@Composable
private fun ResetConfirmDialog(onReset: () -> Unit, onDismiss: () -> Unit) {
    Dialog(onDismissRequest = onDismiss) {
        Box(
            Modifier
                .clip(RoundedCornerShape(24.dp))
                .background(
                    brush =
                        Brush.verticalGradient(
                            colors = listOf(Color(0xFF322341), Color(0xFF120E24))
                        )
                )
        ) {
            Column() {
                Text(
                    color = Color.White,
                    fontSize = 16.sp,
                    text = stringResource(R.string.chat_reset_tips),
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 24.dp),
                )
                HorizontalDivider(thickness = .5.dp, color = Color(0xFF201731))
                Row {
                    TextButton(
                        onClick = onDismiss,
                        shape = RectangleShape,
                        modifier = Modifier
                            .height(40.dp)
                            .weight(1f),
                    ) {
                        Text(
                            fontSize = 16.sp,
                            fontWeight = FontWeight.W700,
                            text = stringResource(R.string.cancel),
                            color = Color.White,
                        )
                    }
                    TextButton(
                        onClick = onReset,
                        shape = RectangleShape,
                        modifier = Modifier
                            .height(40.dp)
                            .weight(1f),
                    ) {
                        Text(
                            text = stringResource(R.string.reset),
                            fontSize = 16.sp,
                            fontWeight = FontWeight.W700,
                            color = Color(0xFFFF3B30),
                        )
                    }
                }
            }
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun ResetConfirmDialogPreview() {
    IntelliMateTheme { ResetConfirmDialog(onReset = {}, onDismiss = {}) }
}
