package com.ai.intellimate.chat.ui

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.billing.BillingRepository
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.design.theme.HeartColor
import ai.sxwl.android.design.tmp.BottomSheetDialog
import ai.sxwl.android.design.tmp.DiaAmountLayout
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Text
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.onGloballyPositioned
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.ai.intellimate.R
import com.ai.intellimate.agent.report.ReportActivity
import com.ai.intellimate.chat.ChatViewModel
import com.ai.intellimate.login.LoginActivity
import com.ai.intellimate.ui.ReplyStyleSheet
import com.ai.intellimate.vip.VipCenterActivity

/** 聊天更多面板组件 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatMorePanel(
    visible: Boolean,
    agentInfo: AgentInfo?,
    chatViewModel: ChatViewModel,
    onDismiss: () -> Unit,
    onHeightChange: (Dp) -> Unit,
) {
    if (!visible) {
        onHeightChange(0.dp)
        return
    }

    val context = LocalContext.current
    var showSheet by remember { mutableStateOf(false) }
    // VIP状态
    val vipStatus by BillingRepository.vipStatusFlow.collectAsState()
    // reply的vip拦截弹窗标记
    var showDialog by remember { mutableStateOf(false) }

    Dialog(
        onDismissRequest = onDismiss,
        properties = DialogProperties(usePlatformDefaultWidth = false),
    ) {
        DiaAmountLayout {
            SetDiaAmount(0f)
            BottomSheetDialog(modifier = Modifier, visible = true, onDismissRequest = onDismiss) {
                val density = LocalDensity.current
                Column(
                    modifier =
                        Modifier.fillMaxWidth()
                            .background(color = HeartColor.primaryColor)
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
                            onClick = {
                                // 检查是否正式登录（非游客且已登录）
                                if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                                    // 已经登录，判断是否vip，是则弹出输入框sheet，否则弹拦截弹窗
                                    if (vipStatus.isSubscribed) {
                                        showSheet = true
                                    } else {
                                        showDialog = true
                                    }
                                } else {
                                    // 未登录或游客时跳转到登录页面
                                    LoginActivity.launch(context)
                                }
                            },
                        )
                        Spacer(Modifier.width(16.dp))
                        MorePanelItem(
                            icon = R.drawable.icon_report,
                            text = stringResource(R.string.str_report),
                            onClick = {
                                // 检查是否正式登录（非游客且已登录）
                                if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                                    ReportActivity.launch(context, agentInfo?.id ?: "", "AGENT")
                                } else {
                                    // 未登录或游客时跳转到登录页面
                                    LoginActivity.launch(context)
                                }
                            },
                        )
                        Spacer(Modifier.width(16.dp))
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
    // 会员定制回复的拦截跳转到vip center
    if (showDialog) {
        // 检查是否正式登录（非游客且已登录）
        if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
            // 去会员中心
            VipCenterActivity.launch(context)
        } else {
            // 如果未登录，要求先登录
            LoginActivity.launch(context)
        }
        showDialog = false
    }
}

/** 更多面板项目组件 */
@Composable
private fun MorePanelItem(icon: Int, text: String, onClick: () -> Unit) {
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
        }
        Spacer(Modifier.height(6.dp))
        Text(text = text, fontSize = 14.sp, fontWeight = FontWeight.Normal, color = Color.White)
        Spacer(Modifier.height(60.dp))
    }
}
