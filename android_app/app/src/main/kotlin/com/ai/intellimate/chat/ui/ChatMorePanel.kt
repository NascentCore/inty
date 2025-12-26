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
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
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
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.RectangleShape
import androidx.compose.ui.layout.onGloballyPositioned
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
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
import com.ai.intellimate.agent.report.ReportActivity
import com.ai.intellimate.chat.viewmodel.ChatViewModel
import com.ai.intellimate.ui.ReplyStyleSheet
import com.ai.intellimate.xb.navigation.Routes

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
    if (!visible) {
        onHeightChange(0.dp)
        return
    }

    val context = LocalContext.current
    var showSheet by remember { mutableStateOf(false) }
    // VIP状态
    val vipStatus by BillingRepository.vipStatusFlow.collectAsState()
    var showResetConfirmDialog by remember { mutableStateOf(false) }

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
        onDismissRequest = onDismiss,
        properties =
            DialogProperties(usePlatformDefaultWidth = false, decorFitsSystemWindows = false),
    ) {
        DiaAmountLayout {
            SetDiaAmount(0f)
            BottomSheetDialog(modifier = Modifier, visible = true, onDismissRequest = onDismiss) {
                val density = LocalDensity.current
                Column(
                    modifier =
                        Modifier.fillMaxWidth()
                            .background(color = HeartColor.primaryColor)
                            .windowInsetsPadding(windowInsets)
                            .onGloballyPositioned { coords ->
                                val h = with(density) { coords.size.height.toDp() }
                                onHeightChange(h)
                            }
                ) {
                    Row(modifier = Modifier.fillMaxWidth()) {
                        Spacer(Modifier.width(16.dp))
                        MorePanelItem(
                            icon = R.drawable.icon_reply_chat,
                            text = stringResource(R.string.reply_style),
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
                        )
                        Spacer(Modifier.width(16.dp))
                        MorePanelItem(
                            icon = R.drawable.icon_reset_chat,
                            text = stringResource(R.string.str_reset),
                            onClick = {
                                // 检查是否已登录
                                if (IntySetting.isLogin()) {
                                    // 清空当前chat的所有聊天消息，（保留intro和opening），然后给服务器发送reset消息
                                    // 相当于重新开始和agent初次聊天
                                    showResetConfirmDialog = true
                                }
                            },
                        )
                        Spacer(Modifier.width(16.dp))
                        MorePanelItem(
                            icon = R.drawable.icon_feedback,
                            text = stringResource(R.string.str_feedback),
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
                                    ReportActivity.launchFeedback(context)
                                }
                            },
                        )
                        Spacer(Modifier.width(16.dp))
                        MorePanelItem(
                            icon = R.drawable.icon_report,
                            text = stringResource(R.string.str_report),
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
                                    ReportActivity.launch(context, agentInfo?.id ?: "", "AGENT")
                                }
                            },
                        )
                        Spacer(Modifier.width(16.dp))

                        if (BuildConfig.DEBUG) {} else {}
                    }

                    if (BuildConfig.BUILD_TYPE != NetworkConfig.BuildType.RELEASE.value) {
                        Row(modifier = Modifier.fillMaxWidth()) {
                            Spacer(Modifier.width(16.dp))
                            MorePanelItem(
                                icon = R.drawable.icon_report,
                                text = "Call",
                                onClick = onCall,
                            )
                            Spacer(Modifier.width(16.dp))
                        }
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

/** 更多面板项目组件 */
@Composable
private fun MorePanelItem(icon: Int, text: String, isVip: Boolean = false, onClick: () -> Unit) {
    Column(
        modifier = Modifier.noRippleClickable { onClick() },
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Spacer(Modifier.height(20.dp))
        Box(
            modifier =
                Modifier.size(64.dp)
                    .background(color = Color.White.copy(0.05f), shape = RoundedCornerShape(8.dp))
        ) {
            Image(
                modifier = Modifier.size(36.dp).align(Alignment.Center),
                painter = painterResource(id = icon),
                contentDescription = null,
            )
            if (isVip) {
                Image(
                    modifier = Modifier.align(Alignment.TopEnd).padding(top = 5.dp, end = 2.dp),
                    painter = painterResource(R.drawable.ic_vip_badge),
                    contentDescription = null,
                )
            }
        }
        Spacer(Modifier.height(6.dp))
        Text(text = text, fontSize = 14.sp, fontWeight = FontWeight.Normal, color = Color.White)
        Spacer(Modifier.height(60.dp))
    }
}

@Composable
private fun ResetConfirmDialog(onReset: () -> Unit, onDismiss: () -> Unit) {
    Dialog(onDismissRequest = onDismiss) {
        Box(
            Modifier.clip(RoundedCornerShape(24.dp))
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
                        modifier = Modifier.height(40.dp).weight(1f),
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
                        modifier = Modifier.height(40.dp).weight(1f),
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
