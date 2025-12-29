package com.ai.intellimate.chat.ui

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.store.SettingStateManager
import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.design.theme.AppColors
import ai.sxwl.android.utils.ToastUtils
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.ime
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.wrapContentHeight
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
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
import com.ai.intellimate.ui.UiConfigs
import kotlinx.coroutines.launch
import kotlinx.coroutines.yield

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
    val inputData = chatViewModel.inputData.collectAsState()
    val inputSelection = chatViewModel.inputSelection.collectAsState()
    val agentInfo by chatViewModel.agentInfo.collectAsState()
    val showSceneActionButton by SettingStateManager.showSceneActionButtonFlow.collectAsState()

    val density = LocalDensity.current
    val keyboardController = LocalSoftwareKeyboardController.current
    val scope = rememberCoroutineScope()
    val isKeyboardVisible = WindowInsets.ime.getBottom(density) > 0

    fun focusInputAndShowKeyboard() {
        focusRequester?.requestFocus()
        // requestFocus() 的生效时机可能在下一帧，show() 放到协程里更稳定
        scope.launch {
            yield()
            keyboardController?.show()
        }
    }

    val config = UiConfigs.ChatPage.ChatInput
    val minHeight = config.MinHeight
    val maxHeight = config.MaxHeight

    Column(
        modifier =
            Modifier.padding(
                    start = config.HorizontalPadding,
                    top = config.TopPadding,
                    end = config.HorizontalPadding,
                    bottom = bottomPadding,
                )
                .fillMaxWidth()
                .clip(RoundedCornerShape(config.CornerRadius))
                .background(AppColors.DarkPurpleOverlay60)
    ) {
        Box(
            modifier =
                Modifier.fillMaxWidth()
                    .heightIn(min = minHeight, max = maxHeight)
                    .wrapContentHeight()
        ) {
            IntySmallTextField(
                modifier =
                    Modifier.padding(end = config.TrailingControlsPadding).align(Alignment.Center),
                value = inputData.value,
                singleLine = false,
                placeholder =
                    agentInfo?.let {
                        {
                            val targetName =
                                it.firstNameOrNull()
                                    ?: stringResource(R.string.chat_ai_typing_default_name)
                            Text(
                                text = stringResource(R.string.chat_input_placeholder, targetName),
                                fontSize = 14.sp,
                                color = Color.White.copy(alpha = 0.5f),
                            )
                        }
                    },
                onValueChange = { chatViewModel.inputData.value = it },
                keyboardOptions =
                    KeyboardOptions(
                        imeAction = ImeAction.Default,
                        capitalization = KeyboardCapitalization.Sentences,
                    ),
                keyboardActions = KeyboardActions(),
                onFocusChanged = onFocusChange,
                onSelectionChanged = { chatViewModel.inputSelection.value = it },
                selection = inputSelection.value,
                maxLines = 4,
                maxLength = CHAT_INPUT_MAX_LENGTH,
                focusRequester = focusRequester,
            )

            val onSceneActionClick = {
                if (!isKeyboardVisible) {
                    focusInputAndShowKeyboard()
                }
                val templateLength = SCENE_ACTION_TEMPLATE.length
                val currentText = inputData.value
                if (currentText.length > CHAT_INPUT_MAX_LENGTH - templateLength) {
                    ToastUtils.showShort(R.string.str_message_is_too_long)
                } else {
                    val safeSelection = inputSelection.value.coerceIn(0, currentText.length)
                    val newText =
                        buildString(currentText.length + templateLength) {
                            append(currentText.take(safeSelection))
                            append(SCENE_ACTION_TEMPLATE)
                            append(currentText.substring(safeSelection))
                        }
                    chatViewModel.inputData.value = newText
                    chatViewModel.inputSelection.value = safeSelection + 1
                    focusInputAndShowKeyboard()
                }
            }

            Row(
                modifier =
                    Modifier.align(Alignment.BottomEnd)
                        .padding(
                            end = config.ButtonRightPadding,
                            top = config.VerticalPadding,
                            bottom = config.VerticalPadding,
                        ),
                horizontalArrangement = Arrangement.spacedBy(config.SceneActionButtonSpacing),
                verticalAlignment = Alignment.Bottom,
            ) {
                if (showSceneActionButton) {
                    SceneActionQuickButton(
                        buttonHeight = config.ButtonSize,
                        onClick = onSceneActionClick,
                    )
                }
                MultiUseAccessButton(
                    buttonSize = config.ButtonSize,
                    hasInput = inputData.value.isNotEmpty(),
                    showMorePanel = showMorePanel,
                    onSendMessage = onSendMessage,
                    onToggleMorePanel = {
                        // 点击加号按钮时，直接切换更多面板
                        // 如果键盘已显示，先隐藏键盘，然后显示更多面板
                        // 注意：这与"()"按钮的逻辑不同，"()"按钮会弹出键盘并插入文本
                        if (isKeyboardVisible) {
                            keyboardController?.hide()
                        }
                        onToggleMorePanel()
                    },
                )
            }
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

@Composable
private fun SceneActionQuickButton(
    modifier: Modifier = Modifier,
    buttonHeight: Dp,
    onClick: () -> Unit,
) {
    Box(
        modifier =
            modifier
                .height(buttonHeight)
                .clip(RoundedCornerShape(buttonHeight / 2))
                .background(Color.White.copy(alpha = 0.12f))
                .noRippleClickable { onClick() },
        contentAlignment = Alignment.Center,
    ) {
        Text(
            modifier = Modifier.padding(horizontal = 10.dp),
            text = SCENE_ACTION_TEMPLATE,
            color = Color.White,
            fontSize = 14.sp,
        )
    }
}

private val NameDelimiterRegex = "\\s+".toRegex()
private const val SCENE_ACTION_TEMPLATE = "()"
private const val CHAT_INPUT_MAX_LENGTH = 500

private fun AgentInfo?.firstNameOrNull(): String? {
    val rawName = this?.name?.trim().orEmpty()
    if (rawName.isBlank()) return null
    val firstToken = NameDelimiterRegex.split(rawName).firstOrNull { it.isNotBlank() }
    return firstToken ?: rawName
}
