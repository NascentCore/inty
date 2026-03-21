package com.ai.intellimate.ui

import ai.sxwl.android.data.store.IntySetting
import androidx.compose.material3.AlertDialog
import androidx.navigation.NavController
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.res.stringResource
import com.ai.intellimate.R
import com.ai.intellimate.chat.viewmodel.ChatViewModel
import com.ai.intellimate.xb.navigation.Routes

/**
 * 全局聊天额度限制弹窗。
 *
 * 用于在非 ChatPage 上下文中展示聊天额度限制提示（如 WebSocket 等全局路径触发的订阅/额度引导）。
 * 与 ChatPage 内的 ShowLimitDialog 复用相同的 ChatViewModel.showChatLimitDialog 流。
 *
 * 使用场景：MainActivity 根层级，当 showChatLimitDialogFromGlobalSource 被调用后显示。
 */
@Composable
fun GlobalChatLimitDialog(
    navController: NavController,
    chatViewModel: ChatViewModel,
) {
    val dialogType by chatViewModel.showChatLimitDialog.collectAsState()
    dialogType?.let { type ->
        when (type) {
            ChatViewModel.ChatLimitDialogType.FREE_USER_SUBSCRIPTION_REQUIRED -> {
                val data =
                    ChatDialogData(
                        R.drawable.img_unlimit_dialog_bg,
                        stringResource(R.string.str_unlimit_dialog_content),
                        stringResource(R.string.str_unlimit_btn_text),
                    )
                UnlimitChatDialog(
                    data,
                    onCancel = { chatViewModel.dismissChatLimitDialog() },
                    onSure = {
                        if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
                            navController.navigate(Routes.Me.vipCenter("chat_unlimit_dialog"))
                        }
                        chatViewModel.dismissChatLimitDialog()
                    },
                    onMoreInfo = {
                        if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
                            navController.navigate(Routes.Me.vipCenter("chat_unlimit_dialog"))
                        }
                        chatViewModel.dismissChatLimitDialog()
                    },
                )
            }
            ChatViewModel.ChatLimitDialogType.SUBSCRIBER_LIMIT_REACHED -> {
                AlertDialog(
                    onDismissRequest = { chatViewModel.dismissChatLimitDialog() },
                    confirmButton = {
                        TextButton(onClick = { chatViewModel.dismissChatLimitDialog() }) {
                            Text(
                                text = stringResource(R.string.chat_subscriber_limit_reached_confirm),
                            )
                        }
                    },
                    title = {
                        Text(text = stringResource(R.string.chat_subscriber_limit_reached_title))
                    },
                    text = {
                        Text(text = stringResource(R.string.chat_subscriber_limit_reached_content))
                    },
                )
            }
        }
    }
}
