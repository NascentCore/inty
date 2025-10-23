package com.ai.inty.chat.ui

import ai.sxwl.android.data.store.IntySetting
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
import androidx.compose.ui.res.colorResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.inty.R
import com.ai.inty.RegInfoActivity
import com.ai.inty.base.IntyImage
import com.ai.inty.base.IntySmallTextField
import com.ai.inty.base.noRippleClickable
import com.ai.inty.chat.ChatViewModel

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

    val horizontalPadding = 16.dp
    val topPadding = 16.dp

    Column(
        modifier =
            Modifier
                .padding(
                    start = horizontalPadding,
                    top = topPadding,
                    end = horizontalPadding,
                    bottom = bottomPadding,
                )
                .fillMaxWidth()
                .clip(RoundedCornerShape(horizontalPadding))
                .background(colorResource(id = R.color.dark_purple_60_percent))
                .clickable(enabled = IntySetting.needBlockInput()) {
                    // 游客 未登录的用户，需要弹出年龄段选择，18岁以下的，不让输入。
                    RegInfoActivity.launch(context)
                }
    ) {
        // 主输入区域
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 48.dp),
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
                maxLines = 4,
                maxLength = 500,
            )

            // 视觉上保持与底部 8.dp 的坚决，这样初始，只有一行输入时，其位置位于
            // 输入框垂直方向中央位置。增加输入行数，则位置不变。
            val bottomPadding = 8.dp
            // 括号按钮区域 - 仅在输入框获得焦点时显示
            if (isInputFocused.value) {
                NarrationInputButton(
                    modifier = Modifier.padding(bottom = bottomPadding),
                    onInsertParentheses = {
                        insertParenthesesAtCursor(
                            currentText = inputData.value,
                            currentSelection = chatViewModel.inputSelection.value,
                            onTextUpdate = { newText -> chatViewModel.inputData.value = newText },
                            onSelectionUpdate = { newSelection ->
                                chatViewModel.inputSelection.value = newSelection
                            },
                        )
                    },
                )
            }

            // 发送/更多按钮区域
            MultiUseAccessButton(
                modifier = Modifier.padding(bottom = bottomPadding),
                hasInput = inputData.value.isNotEmpty(),
                showMorePanel = showMorePanel,
                onSendMessage = onSendMessage,
                onToggleMorePanel = onToggleMorePanel,
            )
        }
    }
}

/**
 * 旁白输入按钮组件
 *
 * @param modifier 修饰符
 * @param onInsertParentheses 插入括号的回调函数
 */
@Composable
private fun NarrationInputButton(
    modifier: Modifier = Modifier,
    onInsertParentheses: (String) -> Unit,
) {
    val parenthesesText = stringResource(R.string.empty_parentheses_symbol)
    val narrationInputFontSize = 14.sp

    Box(
        modifier =
            modifier
                .size(40.dp)
                .padding(horizontal = 8.dp, vertical = 8.dp)
                .background(Color.White.copy(alpha = 0.1f), RoundedCornerShape(16.dp))
                .noRippleClickable { onInsertParentheses(parenthesesText) },
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
 *
 * @param currentText 当前文本内容
 * @param currentSelection 当前光标位置
 * @param onTextUpdate 文本更新回调
 * @param onSelectionUpdate 光标位置更新回调
 */
internal fun insertParenthesesAtCursor(
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
 *
 * @param text 文本内容
 * @param cursorPosition 光标位置
 * @return true 如果光标在括号内，false 否则
 */
internal fun isCursorInsideParentheses(text: String, cursorPosition: Int): Boolean {
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

/**
 * 多功能访问按钮组件（发送/更多按钮）
 *
 * @param modifier 修饰符
 * @param hasInput 是否有输入内容
 * @param showMorePanel 是否显示更多面板
 * @param onSendMessage 发送消息回调
 * @param onToggleMorePanel 切换更多面板回调
 */
@Composable
private fun MultiUseAccessButton(
    modifier: Modifier = Modifier,
    hasInput: Boolean,
    showMorePanel: Boolean,
    onSendMessage: () -> Unit,
    onToggleMorePanel: () -> Unit,
) {
    Box(
        modifier = modifier.padding(horizontal = 8.dp, vertical = 8.dp),
        contentAlignment = Alignment.Center,
    ) {
        val buttonSize = 24.dp
        // 有输入内容时，发送按钮显示
        if (hasInput) {
            IntyImage(
                modifier = Modifier
                    .size(buttonSize)
                    .noRippleClickable { onSendMessage() },
                model = R.drawable.btn_send,
            )
        } else {
            IntyImage(
                modifier = Modifier
                    .size(buttonSize)
                    .noRippleClickable { onToggleMorePanel() },
                model = if (showMorePanel) R.drawable.btn_down else R.drawable.btn_add2,
            )
        }
    }
}
