package com.ai.inty.chat.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.inty.Constant
import com.ai.inty.R
import com.ai.inty.base.IntyImage
import com.ai.inty.base.IntySmallTextField
import com.ai.inty.base.noRippleClickable
import com.ai.inty.chat.ChatViewModel
import com.inty.utils.storage.IntySetting
import com.therouter.TheRouter

/** 聊天输入框组件 */
@Composable
fun ChatInput(
    chatViewModel: ChatViewModel,
    onSendMessage: () -> Unit,
    onToggleMorePanel: () -> Unit,
    showMorePanel: Boolean,
    bottomPadding: Dp,
) {
    val context = LocalContext.current
    val inputData = chatViewModel.inputData.collectAsState()
    val inputSelection = chatViewModel.inputSelection.collectAsState()
    val isInputFocused = remember { mutableStateOf(false) }

    Column(
        modifier =
            Modifier.padding(start = 16.dp, top = 16.dp, end = 16.dp, bottom = bottomPadding)
                .fillMaxWidth()
                .clip(RoundedCornerShape(24.dp))
                .background(Color(0x9937303D))
                .clickable(enabled = IntySetting.needBlockInput()) {
                    // 游客 未登录的用户，需要弹出年龄段选择，18岁以下的，不让输入。
                    TheRouter.build(Constant.ROUTE_REG_INFO).navigation(context)
                }
    ) {
        // 主输入区域
        Row(
            modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp),
            verticalAlignment = Alignment.Bottom,
        ) {
            IntySmallTextField(
                modifier = Modifier.weight(1f),
                enabled = IntySetting.needBlockInput().not(),
                value = inputData.value,
                singleLine = false,
                onValueChange = { input -> chatViewModel.inputData.value = input },
                keyboardOptions =
                    KeyboardOptions(
                        imeAction = ImeAction.Default,
                        capitalization = KeyboardCapitalization.Sentences,
                    ),
                keyboardActions = KeyboardActions(),
                onFocusChanged = { focused -> isInputFocused.value = focused },
                onSelectionChanged = { selection ->
                    chatViewModel.inputSelection.value = selection
                },
                selection = inputSelection.value,
                maxLines = 6,
                maxLength = 500,
            )

            // 括号按钮区域 - 仅在输入框获得焦点时显示
            if (isInputFocused.value) {
                val stringResource = stringResource(R.string.empty_parentheses_symbol)
                Box(
                    modifier =
                        Modifier.size(40.dp)
                            .padding(horizontal = 8.dp, vertical = 8.dp)
                            .background(Color.White.copy(alpha = 0.1f), RoundedCornerShape(16.dp))
                            .noRippleClickable {
                                // 获取当前光标位置
                                val currentText = inputData.value
                                val currentSelection = chatViewModel.inputSelection.value

                                // 确保光标位置在有效范围内
                                val safeSelection = currentSelection.coerceIn(0, currentText.length)

                                // 在光标位置插入一对括号
                                val beforeCursor = currentText.substring(0, safeSelection)
                                val afterCursor = currentText.substring(safeSelection)
                                val newText = "$beforeCursor$stringResource$afterCursor"

                                // 更新文本
                                chatViewModel.inputData.value = newText

                                // 设置光标位置到括号中间
                                val newCursorPosition = safeSelection + 1
                                chatViewModel.inputSelection.value = newCursorPosition
                            },
                    contentAlignment = Alignment.Center,
                ) {
                    Text(
                        text = stringResource(R.string.empty_parentheses_symbol),
                        color = Color.White,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Medium,
                    )
                }
            }

            // 发送/更多按钮区域
            Box(
                modifier = Modifier.padding(horizontal = 8.dp, vertical = 8.dp),
                contentAlignment = Alignment.Center
            ) {
                val sendButtonSize = 24.dp
                // 有输入内容时，发送按钮显示
                if (inputData.value.isNotEmpty()) {
                    IntyImage(
                        modifier =
                            Modifier.size(sendButtonSize).noRippleClickable {
                                onSendMessage()
                            },
                        model = R.drawable.btn_send,
                    )
                } else {
                    IntyImage(
                        modifier =
                            Modifier.size(sendButtonSize).noRippleClickable {
                                onToggleMorePanel()
                            },
                        model = if (showMorePanel) R.drawable.btn_down else R.drawable.btn_add2,
                    )
                }
            }
        }
    }
}
