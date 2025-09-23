package com.ai.inty.chat

import android.app.Activity
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.ai.inty.Constant
import com.ai.inty.R
import com.ai.inty.base.BottomSheetDialog
import com.ai.inty.base.DiaAmountLayout
import com.ai.inty.base.noRippleClickable
import com.ai.inty.beans.AgentInfo
import com.ai.inty.billing.BillingRepository
import com.ai.inty.ui.ChatDialogData
import com.ai.inty.ui.PremiumChatDialog
import com.ai.inty.ui.ReplyStyleSheet
import com.ai.inty.ui.theme.DarkPurple
import com.ai.inty.viewmodels.ChatViewModel
import com.inty.utils.storage.IntySetting
import com.therouter.TheRouter

/**
 * 聊天更多面板组件
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatMorePanel(
    visible: Boolean,
    agentInfo: AgentInfo?,
    chatViewModel: ChatViewModel,
    onDismiss: () -> Unit,
) {
    if (!visible) return

    val context = LocalContext.current
    var showSheet by remember { mutableStateOf(false) }
    // VIP状态
    val vipStatus by BillingRepository.vipStatusFlow.collectAsState()
    //reply的vip拦截弹窗标记
    var showDialog by remember { mutableStateOf(false) }

    Dialog(
        onDismissRequest = onDismiss,
        properties = DialogProperties(
            usePlatformDefaultWidth = false
        )
    ) {
        DiaAmountLayout {
            SetDiaAmount(0f)
            BottomSheetDialog(
                modifier = Modifier,
                visible = true,
                onDismissRequest = onDismiss
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(color = DarkPurple)
                ) {
                    Spacer(Modifier.width(16.dp))
                    MorePanelItem(
                        icon = R.drawable.icon_reply_chat,
                        text = stringResource(R.string.reply_style),
                        onClick = {
                            // 检查是否正式登录（非游客且已登录）
                            if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                                //已经登录，判断是否vip，是则弹出输入框sheet，否则弹拦截弹窗
                                if (vipStatus.isSubscribed) {
                                    showSheet = true
                                } else {
                                    showDialog = true
                                }
                            } else {
                                // 未登录或游客时跳转到登录页面
                                TheRouter.build(Constant.ROUTE_LOGIN)
                                    .navigation(context)
                            }
                        }
                    )
                    Spacer(Modifier.width(16.dp))
                    MorePanelItem(
                        icon = R.drawable.icon_report,
                        text = stringResource(R.string.report_button),
                        onClick = {
                            // 检查是否正式登录（非游客且已登录）
                            if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                                TheRouter.build(Constant.ROUTE_REPORT)
                                    .withString("targetID", agentInfo?.id)
                                    .withString("targetType", "AGENT")
                                    .navigation(context)
                            } else {
                                // 未登录或游客时跳转到登录页面
                                TheRouter.build(Constant.ROUTE_LOGIN)
                                    .navigation(context)
                            }
                        }
                    )
                    Spacer(Modifier.width(16.dp))
                }
            }
        }
    }

    //reply sheet
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)

    LaunchedEffect(showSheet) {
        if (showSheet) sheetState.show() else sheetState.hide()
    }
    
    // 获取当前agent的聊天设置，确保按agent隔离
    val currentChatSetting by remember(agentInfo?.id) {
        derivedStateOf { 
            agentInfo?.id?.let { agentId ->
                chatViewModel.getChatSettingForAgent(agentId)
            }
        }
    }

    val replyStr = remember(agentInfo?.id) { 
        derivedStateOf { (currentChatSetting?.style_prompt ?: "") } 
    }
    if (showSheet) {
        ReplyStyleSheet(
            sheetState = sheetState,
            inputStr = replyStr.value,
            hintStr = stringResource(R.string.reply_hint_str),
            onDismiss = {
                showSheet = false
            },
            onSave = { str ->
                //调用接口 save
                chatViewModel.updateChatReplySettings(str.trim())
                showSheet = false
            }
        )
    }
    //会员定制回复的拦截弹窗
    if (showDialog) {
        val data = ChatDialogData(
            R.drawable.img_premium_dialog_bg,
            stringResource(R.string.str_premium_chat_dialog_content),
            stringResource(R.string.str_beeter_ai_responeses)
        )
        PremiumChatDialog(
            data,
            onCancel = { showDialog = false },
            onSure = {
                // 检查是否正式登录（非游客且已登录）
                if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                    //购买最低档位的vip会员订阅
                    if (context is Activity) {
                        chatViewModel.purchaseFirstVip(context)
                    }
                } else {
                    //如果未登录，要求先登录
                    TheRouter.build(Constant.ROUTE_LOGIN)
                        .navigation(context)
                }
                showDialog = false
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
                showDialog = false
            },
        )
    }

}

/**
 * 更多面板项目组件
 */
@Composable
private fun MorePanelItem(
    icon: Int,
    text: String,
    onClick: () -> Unit,
) {
    Column(
        modifier = Modifier.noRippleClickable { onClick() },
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Spacer(Modifier.height(20.dp))
        Box(
            modifier = Modifier
                .size(64.dp)
                .background(color = Color.White.copy(0.05f), shape = RoundedCornerShape(8.dp))
        ) {
            Image(
                modifier = Modifier
                    .size(36.dp)
                    .align(Alignment.Center),
                painter = painterResource(id = icon),
                contentDescription = null
            )
        }
        Spacer(Modifier.height(6.dp))
        Text(
            text = text,
            fontSize = 14.sp,
            fontWeight = FontWeight.Normal,
            color = Color.White,
        )
        Spacer(Modifier.height(60.dp))
    }
} 
