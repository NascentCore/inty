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
                NarrationInputButton(
                    onInsertParentheses = {
                        insertTextAtCursor(
                            currentText = inputData.value,
                            currentSelection = chatViewModel.inputSelection.value,
                            onTextUpdate = { newText -> chatViewModel.inputData.value = newText },
                            onSelectionUpdate = { newSelection -> chatViewModel.inputSelection.value = newSelection }
                        )
                    }
                )
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

/**
 * 旁白输入按钮组件
 * @param onInsertParentheses 插入括号的回调函数
 */
@Composable
private fun NarrationInputButton(onInsertParentheses: (String) -> Unit) {
    val parenthesesText = stringResource(R.string.empty_parentheses_symbol)
    val narrationInputFontSize = 14.sp
    
    Box(
        modifier =
            Modifier.size(40.dp)
                .padding(horizontal = 8.dp, vertical = 8.dp)
                .background(Color.White.copy(alpha = 0.1f), RoundedCornerShape(16.dp))
                .noRippleClickable {
                    onInsertParentheses(parenthesesText)
                },
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = parenthesesText,
            color = Color.White,
            fontSize = narrationInputFontSize,
            fontWeight = FontWeight.Medium,
        )
    }
}

/**
 * 在光标位置插入文本的辅助函数
 * @param currentText 当前文本内容
 * @param currentSelection 当前光标位置
 * @param textToInsert 要插入的文本
 * @param onTextUpdate 文本更新回调
 * @param onSelectionUpdate 光标位置更新回调
 */
private fun insertTextAtCursor(
    currentText: String,
    currentSelection: Int,
    onTextUpdate: (String) -> Unit,
    onSelectionUpdate: (Int) -> Unit,
) {
    // 确保光标位置在有效范围内
    val safeSelection = currentSelection.coerceIn(0, currentText.length)

    // 检查当前光标是否已经在括号内
    if (isCursorInsideParentheses(currentText, safeSelection)) {
        return // 如果已经在括号内，直接返回，不做任何动作
    }

    // 在光标位置插入文本
    var tmpText = "()"
    val beforeCursor = currentText.substring(0, safeSelection)
    if (beforeCursor.isNotEmpty() && beforeCursor.last() != ' ') {
        tmpText = " $tmpText"
    }
    val afterCursor = currentText.substring(safeSelection)
    if (afterCursor.isNotEmpty() && afterCursor.first() != ' ') {
        tmpText = "$tmpText "
    }
    val newText = "$beforeCursor$tmpText$afterCursor"

    // 更新文本
    onTextUpdate(newText)

    // 设置光标位置到插入文本的中间（对于括号，光标应该在中间）
    onSelectionUpdate(safeSelection + 1)
}

/**
 * 检查光标是否在括号内
 * @param text 文本内容
 * @param cursorPosition 光标位置
 * @return true 如果光标在括号内，false 否则
 */
private fun isCursorInsideParentheses(text: String, cursorPosition: Int): Boolean {
    if (text.isEmpty() || cursorPosition >= text.length) return false
    
    // 从光标位置向前查找最近的 '('
    var openParenIndex = -1
    for (i in cursorPosition - 1 downTo 0) {
        if (text[i] == '(') {
            openParenIndex = i
            break
        } else if (text[i] == ')') {
            // 如果遇到 ')'，说明光标不在括号内
            break
        }
    }
    
    // 如果没有找到 '('，光标不在括号内
    if (openParenIndex == -1) return false
    
    // 从光标位置向后查找对应的 ')'
    for (i in cursorPosition until text.length) {
        if (text[i] == ')') {
            return true // 找到了对应的 ')'，光标在括号内
        } else if (text[i] == '(') {
            // 如果遇到新的 '('，说明光标不在当前括号内
            break
        }
    }
    
    return false
}
