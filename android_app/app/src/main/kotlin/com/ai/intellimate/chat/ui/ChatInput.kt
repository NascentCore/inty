package com.ai.intellimate.chat.ui

import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.design.theme.AppColors
import androidx.compose.foundation.background
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
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil3.compose.AsyncImage
import com.ai.intellimate.R
import com.ai.intellimate.chat.viewmodel.ChatViewModel
import com.ai.intellimate.ui.IntySmallTextField

/** 聊天输入框组件 */
@Composable
fun ChatInput(
    chatViewModel: ChatViewModel,
    onSendMessage: () -> Unit,
    onToggleMorePanel: () -> Unit,
    showMorePanel: Boolean,
    bottomPadding: Dp,
    focusRequester: FocusRequester? = null,
    onFocusChange: (Boolean) -> Unit = {},
) {
    val context = LocalContext.current
    val inputData = chatViewModel.inputData.collectAsState()
    val inputSelection = chatViewModel.inputSelection.collectAsState()
    val isInputFocused = remember { mutableStateOf(false) }

    // 键盘弹出状态跟踪
    // 获取agent信息用于事件上报
    val agentInfo by chatViewModel.agentInfo.collectAsState()

    val horizontalPadding = 16.dp
    val topPadding = 16.dp

    Column(
        modifier =
            Modifier.padding(
                    start = horizontalPadding,
                    top = topPadding,
                    end = horizontalPadding,
                    bottom = bottomPadding,
                )
                .fillMaxWidth()
                .clip(RoundedCornerShape(horizontalPadding))
                .background(AppColors.DarkPurpleOverlay60)
    ) {
        // 主输入区域
        Row(
            modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp),
            verticalAlignment = Alignment.Bottom,
        ) {
            IntySmallTextField(
                modifier = Modifier.weight(1f),
                value = inputData.value,
                singleLine = false,
                placeholder = {
                    Text(
                        text = stringResource(R.string.chat_input_placeholder),
                        fontSize = 14.sp,
                        color = Color.White.copy(alpha = 0.5f),
                    )
                },
                onValueChange = { input -> chatViewModel.inputData.value = input },
                keyboardOptions =
                    KeyboardOptions(
                        imeAction = ImeAction.Default,
                        capitalization = KeyboardCapitalization.Sentences,
                    ),
                keyboardActions = KeyboardActions(),
                onFocusChanged = { focused ->
                    isInputFocused.value = focused
                    onFocusChange(focused)
                },
                onSelectionChanged = { selection ->
                    chatViewModel.inputSelection.value = selection
                },
                selection = inputSelection.value,
                maxLines = 4,
                maxLength = 500,
                focusRequester = focusRequester,
            )

            // 视觉上保持与底部 8.dp 的坚决，这样初始，只有一行输入时，其位置位于
            // 输入框垂直方向中央位置。增加输入行数，则位置不变。
            val verticalPadding = 16.dp
            val rightPadding = 8.dp
            // 发送/更多按钮区域
            MultiUseAccessButton(
                modifier =
                    Modifier.padding(
                        end = rightPadding,
                        top = verticalPadding,
                        bottom = verticalPadding,
                    ),
                buttonSize = 30.dp,
                hasInput = inputData.value.isNotEmpty(),
                showMorePanel = showMorePanel,
                onSendMessage = onSendMessage,
                onToggleMorePanel = onToggleMorePanel,
            )
        }
    }
}

/**
 * 多功能访问按钮组件（发送/更多按钮）
 *
 * @param modifier 修饰符
 * @param buttonSize 按钮大小
 * @param hasInput 是否有输入内容
 * @param showMorePanel 是否显示更多面板
 * @param onSendMessage 发送消息回调
 * @param onToggleMorePanel 切换更多面板回调
 */
@Composable
private fun MultiUseAccessButton(
    modifier: Modifier = Modifier,
    buttonSize: Dp,
    hasInput: Boolean,
    showMorePanel: Boolean,
    onSendMessage: () -> Unit,
    onToggleMorePanel: () -> Unit,
) {
    Box(modifier = modifier, contentAlignment = Alignment.BottomStart) {
        // 有输入内容时，发送按钮显示
        if (hasInput) {
            AsyncImage(
                modifier = Modifier.size(buttonSize).noRippleClickable { onSendMessage() },
                model = R.drawable.btn_send,
                contentDescription = null,
            )
        } else {
            AsyncImage(
                modifier = Modifier.size(buttonSize).noRippleClickable { onToggleMorePanel() },
                model = if (showMorePanel) R.drawable.btn_down else R.drawable.btn_add2,
                contentDescription = null,
            )
        }
    }
}
