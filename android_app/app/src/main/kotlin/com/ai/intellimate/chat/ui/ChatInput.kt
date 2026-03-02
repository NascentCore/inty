package com.ai.intellimate.chat.ui

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.store.SettingStateManager
import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.design.theme.AppColors
import ai.sxwl.android.utils.ToastUtils
import android.Manifest
import android.content.Intent
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.ime
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.wrapContentHeight
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Close
import androidx.compose.material.icons.rounded.Image
import androidx.compose.material.icons.rounded.Keyboard
import androidx.compose.material.icons.rounded.Mic
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil3.compose.AsyncImage
import com.ai.intellimate.R
import com.ai.intellimate.chat.viewmodel.ChatViewModel
import com.ai.intellimate.ui.IntySmallTextField
import com.ai.intellimate.ui.UiConfigs
import com.ai.intellimate.ui.components.ImagePickerBottomSheet
import com.google.accompanist.permissions.ExperimentalPermissionsApi
import com.google.accompanist.permissions.isGranted
import com.google.accompanist.permissions.rememberPermissionState
import com.google.accompanist.permissions.shouldShowRationale
import java.util.Locale
import kotlinx.coroutines.launch
import kotlinx.coroutines.yield

/** 聊天输入框组件 */
@OptIn(ExperimentalPermissionsApi::class)
@Composable
fun ChatInput(
    chatViewModel: ChatViewModel,
    onSendMessage: () -> Unit,
    onToggleMorePanel: () -> Unit,
    showMorePanel: Boolean,
    bottomPadding: Dp,
    focusRequester: FocusRequester? = null,
    onFocusChange: (Boolean) -> Unit = {},
    onVoiceInputActiveChange: (Boolean) -> Unit = {},
) {
    val inputData = chatViewModel.inputData.collectAsState()
    val inputSelection = chatViewModel.inputSelection.collectAsState()
    val inputImageUri = chatViewModel.inputImageUri.collectAsState()
    val agentInfo by chatViewModel.agentInfo.collectAsState()
    val showSceneActionButton by SettingStateManager.showSceneActionButtonFlow.collectAsState()
    val sceneActionTemplate = if (agentInfo?.useDoubleAsteriskActionMarker() == true) "**" else "()"

    val density = LocalDensity.current
    val keyboardController = LocalSoftwareKeyboardController.current
    val scope = rememberCoroutineScope()
    val isKeyboardVisible = WindowInsets.ime.getBottom(density) > 0
    val context = LocalContext.current
    val voicePermissionState = rememberPermissionState(Manifest.permission.RECORD_AUDIO)
    val isSpeechRecognitionAvailable =
        remember(context) { SpeechRecognizer.isRecognitionAvailable(context) }
    var isVoiceInputMode by remember { mutableStateOf(false) }
    var isVoiceRecording by remember { mutableStateOf(false) }
    var showImagePicker by remember { mutableStateOf(false) }
    /** 点击语音按钮时因无权限而发起了授权请求，授权通过后需切到语音模式 */
    var pendingSwitchToVoiceMode by remember { mutableStateOf(false) }
    val speechRecognizer =
        remember(context, isSpeechRecognitionAvailable) {
            if (isSpeechRecognitionAvailable) {
                SpeechRecognizer.createSpeechRecognizer(context)
            } else {
                null
            }
        }

    fun ensureVoiceInputReady(): Boolean {
        if (!isSpeechRecognitionAvailable || speechRecognizer == null) {
            ToastUtils.showShort(R.string.chat_voice_input_not_available)
            return false
        }
        if (!voicePermissionState.status.isGranted) {
            if (voicePermissionState.status.shouldShowRationale) {
                ToastUtils.showShort(R.string.chat_voice_input_permission_rationale)
            }
            voicePermissionState.launchPermissionRequest()
            return false
        }
        return true
    }

    fun focusInputAndShowKeyboard() {
        focusRequester?.requestFocus()
        // requestFocus() 的生效时机可能在下一帧，show() 放到协程里更稳定
        scope.launch {
            yield()
            keyboardController?.show()
        }
    }

    val currentOnSendMessage = rememberUpdatedState(onSendMessage)

    DisposableEffect(speechRecognizer) {
        if (speechRecognizer == null) return@DisposableEffect onDispose {}
        val listener =
            object : RecognitionListener {
                override fun onReadyForSpeech(params: Bundle?) = Unit

                override fun onBeginningOfSpeech() = Unit

                override fun onRmsChanged(rmsdB: Float) = Unit

                override fun onBufferReceived(buffer: ByteArray?) = Unit

                override fun onEndOfSpeech() {
                    scope.launch { isVoiceRecording = false }
                }

                override fun onError(error: Int) {
                    scope.launch {
                        isVoiceRecording = false
                        if (error != SpeechRecognizer.ERROR_CLIENT) {
                            ToastUtils.showShort(R.string.chat_voice_input_failed)
                        }
                    }
                }

                override fun onResults(results: Bundle?) {
                    val resultText =
                        results
                            ?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                            ?.firstOrNull()
                            .orEmpty()
                    scope.launch {
                        isVoiceRecording = false
                        if (resultText.isBlank()) {
                            ToastUtils.showShort(R.string.chat_voice_input_failed)
                            return@launch
                        }
                        chatViewModel.inputData.value = resultText.trim()
                        currentOnSendMessage.value.invoke()
                    }
                }

                override fun onPartialResults(partialResults: Bundle?) = Unit

                override fun onEvent(eventType: Int, params: Bundle?) = Unit
            }
        speechRecognizer.setRecognitionListener(listener)
        onDispose {
            speechRecognizer.cancel()
            speechRecognizer.destroy()
        }
    }

    LaunchedEffect(voicePermissionState.status.isGranted) {
        if (voicePermissionState.status.isGranted && pendingSwitchToVoiceMode) {
            pendingSwitchToVoiceMode = false
            if (showMorePanel) {
                onToggleMorePanel()
            }
            if (isKeyboardVisible) {
                keyboardController?.hide()
            }
            isVoiceInputMode = true
        } else if (!voicePermissionState.status.isGranted && isVoiceInputMode) {
            isVoiceInputMode = false
            isVoiceRecording = false
        }
    }

    LaunchedEffect(isVoiceInputMode) {
        if (!isVoiceInputMode && isVoiceRecording) {
            speechRecognizer?.cancel()
            isVoiceRecording = false
        }
    }

    LaunchedEffect(isVoiceInputMode, isVoiceRecording) {
        onVoiceInputActiveChange(isVoiceInputMode || isVoiceRecording)
    }

    if (showImagePicker) {
        ImagePickerBottomSheet(
            onDismiss = { showImagePicker = false },
            onImageSelected = { uri ->
                chatViewModel.setInputImage(uri)
                showImagePicker = false
            },
        )
    }

    val config = UiConfigs.ChatPage.ChatInput
    val minHeight = config.MinHeight
    val maxHeight = config.MaxHeight
    // 文字模式下测量到的输入区高度（px），用于切到语音模式时保持高度一致，避免输入框突然变矮
    var lastTextModeHeightPx by remember { mutableIntStateOf(0) }

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
        if (!inputImageUri.value.isNullOrBlank()) {
            ChatInputImagePreview(
                imageUri = inputImageUri.value.orEmpty(),
                previewSize = config.ImagePreviewSize,
                cornerRadius = config.ImagePreviewCornerRadius,
                removeButtonSize = config.ImagePreviewRemoveButtonSize,
                removeIconSize = config.ImagePreviewRemoveIconSize,
                removeButtonPadding = config.ImagePreviewRemoveButtonPadding,
                onRemove = { chatViewModel.clearInputImage() },
                modifier =
                    Modifier.fillMaxWidth()
                        .padding(
                            start = config.LeadingControlsPadding,
                            top = config.TopPadding,
                            end = config.LeadingControlsPadding,
                            bottom = config.ImagePreviewBottomSpacing,
                        ),
            )
        }
        Box(
            modifier =
                Modifier.fillMaxWidth()
                    .then(
                        if (isVoiceInputMode && lastTextModeHeightPx > 0) {
                            Modifier.height(with(density) { lastTextModeHeightPx.toDp() })
                        } else {
                            Modifier.heightIn(min = minHeight, max = maxHeight).wrapContentHeight()
                        }
                    )
                    .onSizeChanged { if (!isVoiceInputMode) lastTextModeHeightPx = it.height }
        ) {
            val trailingPadding =
                when {
                    isVoiceInputMode && showSceneActionButton ->
                        config.VoiceModeTrailingPaddingWithSceneAction
                    isVoiceInputMode -> config.VoiceModeTrailingPadding
                    showSceneActionButton -> config.TrailingControlsPaddingWithSceneAction
                    else -> config.TrailingControlsPadding
                }
            val inputContentModifier =
                Modifier.padding(start = config.LeadingControlsPadding, end = trailingPadding)
                    .align(Alignment.Center)
            val onVoiceToggleClick: () -> Unit = onVoiceToggleClick@{
                if (isVoiceInputMode) {
                    isVoiceInputMode = false
                    // 切换回文字模式后延迟一帧再请求焦点并拉键盘，确保 IntySmallTextField 已重组
                    scope.launch {
                        yield()
                        focusRequester?.requestFocus()
                        yield()
                        keyboardController?.show()
                    }
                } else {
                    if (!ensureVoiceInputReady()) {
                        if (
                            isSpeechRecognitionAvailable &&
                                speechRecognizer != null &&
                                !voicePermissionState.status.isGranted
                        ) {
                            pendingSwitchToVoiceMode = true
                        }
                        return@onVoiceToggleClick
                    }
                    if (showMorePanel) {
                        onToggleMorePanel()
                    }
                    if (isKeyboardVisible) {
                        keyboardController?.hide()
                    }
                    isVoiceInputMode = true
                }
            }
            val onVoicePressStart: () -> Boolean = onVoicePressStart@{
                if (!ensureVoiceInputReady()) return@onVoicePressStart false
                if (isVoiceRecording) return@onVoicePressStart true
                val intent =
                    Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                        putExtra(
                            RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                            RecognizerIntent.LANGUAGE_MODEL_FREE_FORM,
                        )
                        putExtra(
                            RecognizerIntent.EXTRA_LANGUAGE,
                            Locale.getDefault().toLanguageTag(),
                        )
                        putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, VOICE_INPUT_MAX_RESULTS)
                    }
                isVoiceRecording = true
                speechRecognizer?.startListening(intent)
                true
            }
            val onVoicePressEnd: () -> Unit = onVoicePressEnd@{
                if (!isVoiceRecording) return@onVoicePressEnd
                isVoiceRecording = false
                speechRecognizer?.stopListening()
            }
            val onVoicePressCancel: () -> Unit = onVoicePressCancel@{
                if (!isVoiceRecording) return@onVoicePressCancel
                isVoiceRecording = false
                speechRecognizer?.cancel()
            }

            if (isVoiceInputMode) {
                VoiceHoldToTalkButton(
                    modifier = inputContentModifier.fillMaxWidth(),
                    isRecording = isVoiceRecording,
                    enabled = voicePermissionState.status.isGranted && isSpeechRecognitionAvailable,
                    idleText = stringResource(R.string.chat_voice_input_hold_to_talk),
                    recordingText = stringResource(R.string.chat_voice_input_release_to_end),
                    minHeight = minHeight,
                    cornerRadius = config.MinHeight / 2,
                    borderWidth = config.VoiceHoldButtonBorderWidth,
                    borderAlpha = config.VoiceHoldButtonBorderAlpha,
                    idleBackgroundAlpha = config.VoiceHoldButtonIdleAlpha,
                    recordingBackgroundAlpha = config.VoiceHoldButtonRecordingAlpha,
                    disabledTextAlpha = config.VoiceHoldButtonDisabledTextAlpha,
                    onPressStart = onVoicePressStart,
                    onPressEnd = onVoicePressEnd,
                    onPressCancel = onVoicePressCancel,
                )
            } else {
                // 文本输入区左边界与语音“按住说话”按钮左边界对齐（均为 LeadingControlsPadding），两者内部均有 TextFieldHorizontal
                // 内边距，文字起始位置一致
                val textFieldContentModifier =
                    Modifier.padding(start = config.LeadingControlsPadding, end = trailingPadding)
                        .align(Alignment.Center)
                IntySmallTextField(
                    modifier = textFieldContentModifier,
                    value = inputData.value,
                    singleLine = false,
                    placeholder =
                        agentInfo?.let {
                            {
                                val targetName =
                                    it.firstNameOrNull()
                                        ?: stringResource(R.string.chat_ai_typing_default_name)
                                Text(
                                    text =
                                        stringResource(R.string.chat_input_placeholder, targetName),
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
                    maxLines = 3,
                    maxLength = CHAT_INPUT_MAX_LENGTH,
                    focusRequester = focusRequester,
                )
            }

            VoiceInputToggleButton(
                modifier =
                    Modifier.align(Alignment.CenterStart)
                        .padding(start = config.VoiceTogglePaddingStart),
                isVoiceMode = isVoiceInputMode,
                buttonSize = config.VoiceToggleButtonSize,
                iconSize = config.VoiceToggleIconSize,
                isAvailable = isSpeechRecognitionAvailable,
                onClick = onVoiceToggleClick,
            )

            val onSceneActionClick = {
                if (!isKeyboardVisible) {
                    focusInputAndShowKeyboard()
                }
                val templateLength = sceneActionTemplate.length
                val currentText = inputData.value
                if (currentText.length > CHAT_INPUT_MAX_LENGTH - templateLength) {
                    ToastUtils.showShort(R.string.str_message_is_too_long)
                } else {
                    val safeSelection = inputSelection.value.coerceIn(0, currentText.length)
                    val newText =
                        buildString(currentText.length + templateLength) {
                            append(currentText.take(safeSelection))
                            append(sceneActionTemplate)
                            append(currentText.substring(safeSelection))
                        }
                    chatViewModel.inputData.value = newText
                    chatViewModel.inputSelection.value = safeSelection + 1
                    focusInputAndShowKeyboard()
                }
            }

            Row(
                modifier =
                    Modifier.align(Alignment.CenterEnd).padding(end = config.ButtonRightPadding),
                horizontalArrangement = Arrangement.spacedBy(config.SceneActionButtonSpacing),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                ChatImageAttachButton(
                    buttonSize = config.ButtonSize,
                    iconSize = config.VoiceToggleIconSize,
                    hasSelectedImage = !inputImageUri.value.isNullOrBlank(),
                    onClick = {
                        if (showMorePanel) {
                            onToggleMorePanel()
                        }
                        showImagePicker = true
                    },
                )
                if (showSceneActionButton) {
                    SceneActionQuickButton(
                        buttonHeight = config.ButtonSize,
                        sceneActionTemplate = sceneActionTemplate,
                        onClick = onSceneActionClick,
                    )
                }
                MultiUseAccessButton(
                    buttonSize = config.ButtonSize,
                    hasInput = inputData.value.isNotEmpty() || !inputImageUri.value.isNullOrBlank(),
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
 * 聊天输入区已选图片预览（Image + Text 输入场景）。
 *
 * 适用范围：
 * - 仅用于 ChatInput 顶部，展示当前待发送的单张图片。
 *
 * 视觉预期：
 * - 小尺寸圆角缩略图，右上角有删除按钮，用户可在发送前撤销附件。
 *
 * 可配置项：
 * - 通过入参传入尺寸、圆角、删除按钮大小，避免在调用侧写魔法值。
 */
@Composable
private fun ChatInputImagePreview(
    imageUri: String,
    previewSize: Dp,
    cornerRadius: Dp,
    removeButtonSize: Dp,
    removeIconSize: Dp,
    removeButtonPadding: Dp,
    onRemove: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Box(modifier = modifier, contentAlignment = Alignment.CenterStart) {
        Box(
            modifier =
                Modifier.size(previewSize)
                    .clip(RoundedCornerShape(cornerRadius))
                    .background(Color.White.copy(alpha = 0.08f))
        ) {
            AsyncImage(
                model = imageUri,
                contentDescription = stringResource(R.string.chat_input_selected_image),
                modifier = Modifier.fillMaxSize(),
                contentScale = ContentScale.Crop,
            )
            Box(
                modifier =
                    Modifier.align(Alignment.TopEnd)
                        .padding(removeButtonPadding)
                        .size(removeButtonSize)
                        .clip(CircleShape)
                        .background(Color.Black.copy(alpha = 0.45f))
                        .noRippleClickable(onClick = onRemove),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    imageVector = Icons.Rounded.Close,
                    contentDescription = stringResource(R.string.chat_input_remove_image),
                    tint = Color.White,
                    modifier = Modifier.size(removeIconSize),
                )
            }
        }
    }
}

/**
 * 聊天输入区图片附件按钮（“选图”入口）。
 *
 * 适用范围：
 * - 仅用于 ChatInput 右侧操作区，与发送/更多按钮并列。
 *
 * 视觉预期：
 * - 未选择图片时为普通按钮态，已选择图片时高亮提示。
 *
 * 可配置项：
 * - 按钮尺寸、图标尺寸、是否已选中图片（用于样式态切换）。
 */
@Composable
private fun ChatImageAttachButton(
    buttonSize: Dp,
    iconSize: Dp,
    hasSelectedImage: Boolean,
    onClick: () -> Unit,
) {
    val backgroundColor =
        if (hasSelectedImage) {
            Color.White.copy(alpha = 0.2f)
        } else {
            AppColors.DarkPurpleOverlay60
        }
    Box(
        modifier =
            Modifier.size(buttonSize)
                .clip(CircleShape)
                .background(backgroundColor)
                .noRippleClickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Icon(
            imageVector = Icons.Rounded.Image,
            contentDescription = stringResource(R.string.chat_input_add_image),
            tint = Color.White,
            modifier = Modifier.size(iconSize),
        )
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
    sceneActionTemplate: String,
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
            text = sceneActionTemplate,
            color = Color.White,
            fontSize = 14.sp,
        )
    }
}

/**
 * 语音输入切换按钮：用于聊天输入框左侧，提供类似微信的语音/键盘切换入口。
 *
 * 预期视觉效果：
 * - 圆形半透明底色，白色图标；
 * - 语音模式显示键盘图标，文本模式显示麦克风图标；
 * - 点击不显示波纹，交互与输入框风格保持一致。
 *
 * 可配置项：
 *
 * @param modifier 按钮外层修饰符（用于定位与间距）
 * @param isVoiceMode 当前是否处于语音输入模式
 * @param buttonSize 按钮尺寸
 * @param iconSize 图标尺寸
 * @param isAvailable 设备是否支持语音识别，用于调节视觉状态
 * @param onClick 点击回调（建议处理权限与模式切换）
 */
@Composable
private fun VoiceInputToggleButton(
    modifier: Modifier = Modifier,
    isVoiceMode: Boolean,
    buttonSize: Dp,
    iconSize: Dp,
    isAvailable: Boolean,
    onClick: () -> Unit,
) {
    val config = UiConfigs.ChatPage.ChatInput
    val backgroundAlpha =
        if (isAvailable) {
            config.VoiceToggleBackgroundAlpha
        } else {
            config.VoiceToggleDisabledBackgroundAlpha
        }
    val iconAlpha =
        if (isAvailable) {
            1f
        } else {
            config.VoiceToggleDisabledIconAlpha
        }
    val icon = if (isVoiceMode) Icons.Rounded.Keyboard else Icons.Rounded.Mic
    val contentDescription =
        if (isVoiceMode) {
            stringResource(R.string.chat_voice_input_toggle_to_keyboard)
        } else {
            stringResource(R.string.chat_voice_input_toggle_to_voice)
        }
    Box(
        modifier =
            modifier
                .size(buttonSize)
                .clip(RoundedCornerShape(buttonSize / 2))
                .background(Color.White.copy(alpha = backgroundAlpha))
                .noRippleClickable { onClick() },
        contentAlignment = Alignment.Center,
    ) {
        Icon(
            modifier = Modifier.size(iconSize),
            imageVector = icon,
            contentDescription = contentDescription,
            tint = Color.White.copy(alpha = iconAlpha),
        )
    }
}

/**
 * 语音输入“按住说话”按钮：用于语音模式下替代文本输入区域。
 *
 * 预期视觉效果：
 * - 横向长条按钮，带轻微描边与半透明底色；
 * - 按住时背景加深、提示文案切换为“松开结束”；
 * - 文案居中，整体高度与输入框最小高度一致。
 *
 * 可配置项：
 *
 * @param modifier 按钮外层修饰符（用于宽度、对齐）
 * @param isRecording 是否处于录制中状态
 * @param enabled 是否允许录制（权限/设备能力）
 * @param idleText 默认文案（未录制）
 * @param recordingText 录制中文案（按住中）
 * @param minHeight 最小高度（与输入框高度一致）
 * @param cornerRadius 圆角
 * @param borderWidth 描边宽度
 * @param borderAlpha 描边透明度
 * @param idleBackgroundAlpha 默认背景透明度
 * @param recordingBackgroundAlpha 录制中背景透明度
 * @param disabledTextAlpha 禁用状态文字透明度
 * @param onPressStart 按下开始回调，返回是否成功开始录制
 * @param onPressEnd 松开结束回调
 * @param onPressCancel 手势取消回调
 */
@Composable
private fun VoiceHoldToTalkButton(
    modifier: Modifier = Modifier,
    isRecording: Boolean,
    enabled: Boolean,
    idleText: String,
    recordingText: String,
    minHeight: Dp,
    cornerRadius: Dp,
    borderWidth: Dp,
    borderAlpha: Float,
    idleBackgroundAlpha: Float,
    recordingBackgroundAlpha: Float,
    disabledTextAlpha: Float,
    onPressStart: () -> Boolean,
    onPressEnd: () -> Unit,
    onPressCancel: () -> Unit,
) {
    val backgroundAlpha = if (isRecording) recordingBackgroundAlpha else idleBackgroundAlpha
    val textAlpha = if (enabled) 1f else disabledTextAlpha
    val shape = RoundedCornerShape(cornerRadius)
    val displayText = if (isRecording) recordingText else idleText
    Box(
        modifier =
            modifier
                .heightIn(min = minHeight)
                .clip(shape)
                .background(Color.White.copy(alpha = backgroundAlpha))
                .border(borderWidth, Color.White.copy(alpha = borderAlpha), shape)
                .pointerInput(enabled) {
                    if (!enabled) return@pointerInput
                    detectTapGestures(
                        onPress = {
                            val started = onPressStart()
                            if (!started) return@detectTapGestures
                            val released = tryAwaitRelease()
                            if (released) {
                                onPressEnd()
                            } else {
                                onPressCancel()
                            }
                        }
                    )
                },
        contentAlignment = Alignment.Center,
    ) {
        Text(
            modifier =
                Modifier.padding(
                    horizontal = UiConfigs.Padding.TextFieldHorizontal,
                    vertical = UiConfigs.Padding.TextFieldVertical,
                ),
            text = displayText,
            color = Color.White.copy(alpha = textAlpha),
            fontSize = UiConfigs.Typography.Body,
            textAlign = TextAlign.Center,
        )
    }
}

private val NameDelimiterRegex = "\\s+".toRegex()
// 长一些的输入方便用户问官方机器人
private const val CHAT_INPUT_MAX_LENGTH = 5000
private const val VOICE_INPUT_MAX_RESULTS = 1

private fun AgentInfo?.firstNameOrNull(): String? {
    val rawName = this?.name?.trim().orEmpty()
    if (rawName.isBlank()) return null
    val firstToken = NameDelimiterRegex.split(rawName).firstOrNull { it.isNotBlank() }
    return firstToken ?: rawName
}
