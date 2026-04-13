package com.ai.intellimate.call

import ai.sxwl.android.data.api.getCdnImageUrl
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.http.IntyErrorCode
import ai.sxwl.android.design.isInEditMode
import ai.sxwl.android.design.theme.IntelliMateTheme
import ai.sxwl.android.inty.voicecall.CallStatus
import ai.sxwl.android.utils.ToastUtils
import android.Manifest
import android.annotation.SuppressLint
import android.content.Intent
import android.media.AudioFormat
import android.net.Uri
import android.os.SystemClock
import android.provider.Settings
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.StartOffset
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Close
import androidx.compose.material.icons.rounded.Mic
import androidx.compose.material.icons.rounded.MicOff
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.IconButtonDefaults
import androidx.compose.material3.IconToggleButton
import androidx.compose.material3.LocalContentColor
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ProvideTextStyle
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.dimensionResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import coil3.compose.AsyncImage
import com.ai.intellimate.R
import com.ai.intellimate.audio.AudioParams
import com.ai.intellimate.audio.AudioRecordManager
import com.ai.intellimate.audio.AudioStreamPlayer
import com.ai.intellimate.call.uistate.VoiceCallUiState
import com.ai.intellimate.ui.ChatDialogData
import com.ai.intellimate.ui.UiConfigs
import com.ai.intellimate.ui.UnlimitChatDialog
import com.ai.intellimate.utils.NetworkErrorHandler
import com.google.accompanist.permissions.ExperimentalPermissionsApi
import com.google.accompanist.permissions.isGranted
import com.google.accompanist.permissions.rememberPermissionState
import com.google.accompanist.permissions.shouldShowRationale
import kotlin.time.Duration.Companion.seconds
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import org.koin.compose.viewmodel.koinViewModel

/**
 * 语音通话页面 提供与AI的实时语音通讯功能
 *
 * @param onBack 退出界面
 * @param agentId 角色ID
 */
@SuppressLint("MissingPermission")
@OptIn(ExperimentalPermissionsApi::class)
@Composable
fun VoiceCallScreen(
    onBack: (Int) -> Unit,
    onVip: () -> Unit,
    onVipMoreInfo: () -> Unit,
    agentId: String,
) {

    val viewModel = koinViewModel<VoiceCallViewModel>()

    VoiceCallScreen(onBack = { onBack(viewModel.messageCount) }) { contentPadding ->
        // 权限请求Launcher
        val audioPermissionState = rememberPermissionState(Manifest.permission.RECORD_AUDIO)
        val context = LocalContext.current

        if (audioPermissionState.status.isGranted) {
            val uiState by viewModel.uiState.collectAsState()
            val audioStreamPlayer = AudioStreamPlayer.getInstance()
            val hasPendingPlaybackData by
                audioStreamPlayer.hasPendingPlaybackData.collectAsState(initial = false)
            val audioRecordManager = AudioRecordManager.getInstance(context)
            var error by remember { mutableStateOf<Pair<IntyErrorCode, String>?>(null) }
            val isSpeakingFromAudio =
                rememberVoiceCallSpeakingFromAudio(
                    hasPendingPlaybackData = hasPendingPlaybackData,
                    audioResponse = viewModel.audioResponse,
                    onAudioData = { audioStreamPlayer.addAudioData(it) },
                )

            // 启动通话连接
            LaunchedEffect(agentId) { viewModel.startCalling(agentId) }

            LaunchedEffect(viewModel) { viewModel.error.collect { error = it } }

            // 管理播放器生命周期
            LaunchedEffect(uiState.connectionState) {
                when (uiState.connectionState) {
                    VoiceCallConnectionUi.CONNECTED -> {
                        // 连接建立时启动播放（24kHz PCM，单声道，16位）
                        val playbackParams =
                            AudioParams(
                                sampleRate = 24000,
                                channelConfig = AudioFormat.CHANNEL_OUT_MONO,
                                audioFormat = AudioFormat.ENCODING_PCM_16BIT,
                            )
                        audioStreamPlayer.startPlayback(playbackParams)
                    }
                    VoiceCallConnectionUi.DISCONNECTED,
                    VoiceCallConnectionUi.ERROR,
                    VoiceCallConnectionUi.DISCONNECTING -> {
                        // 断开连接时停止播放
                        audioStreamPlayer.stopPlayback()
                    }
                    else -> {}
                }
            }

            LaunchedEffect(Unit) {
                snapshotFlow {
                        uiState.connectionState == VoiceCallConnectionUi.CONNECTED &&
                            !uiState.isMuted
                    }
                    .collect {
                        if (it) {
                            audioRecordManager.startRecording { audioData ->
                                viewModel.sendVoice(audioData)
                            }
                        } else {
                            // 断开连接或静音时停止录制
                            audioRecordManager.stopRecording()
                        }
                    }
            }

            // 组件销毁时清理所有资源
            DisposableEffect(Unit) {
                onDispose {
                    audioRecordManager.stopRecording()
                    audioStreamPlayer.stopPlayback()
                }
            }

            VoiceCallContent(
                onEnd = { onBack(viewModel.messageCount) },
                uiState = uiState,
                onMuteChange = viewModel::setMuted,
                onInterrupt = {
                    audioStreamPlayer.interruptPlayback()
                    viewModel.interruptSpeaking()
                },
                isSpeakingFromAudio = isSpeakingFromAudio,
                modifier = Modifier.padding(contentPadding).fillMaxSize(),
            )

            error?.let {
                val dialogData =
                    when (it.first) {
                        IntyErrorCode.SUBSCRIPTION_REQUIRED -> {
                            ChatDialogData(
                                R.drawable.img_unlimit_dialog_bg,
                                stringResource(R.string.voice_call_subscription_guide_content),
                                stringResource(R.string.voice_call_subscription_guide_btn_text),
                            )
                        }

                        IntyErrorCode.LIVE_CHAT_DURATION_LIMIT_REACHED,
                        IntyErrorCode.LIVE_CHAT_AGENT_LIMIT_REACHED -> {
                            ChatDialogData(
                                R.drawable.img_unlimit_dialog_bg,
                                stringResource(R.string.voice_call_limit_exceeded_content),
                                stringResource(R.string.voice_call_limit_exceeded_btn_text),
                            )
                        }
                        else -> {
                            // #region agent log（上报 Crashlytics）
                            NetworkErrorHandler.reportTlsParseToCrashlyticsIfRelevant(
                                "D",
                                "VoiceCallScreen.kt:error Toast",
                                it.second,
                            )
                            // #endregion
                            ToastUtils.showShort(it.second)
                            null
                        }
                    }

                if (dialogData != null) {
                    UnlimitChatDialog(
                        dialogData,
                        onCancel = {
                            error = null
                            onBack(viewModel.messageCount)
                        },
                        onSure = {
                            error = null
                            when (it.first) {
                                IntyErrorCode.SUBSCRIPTION_REQUIRED -> {
                                    onVip()
                                }
                                else -> onBack(viewModel.messageCount)
                            }
                        },
                        onMoreInfo = {
                            error = null
                            onVipMoreInfo()
                        },
                    )
                }
            }
        } else {
            if (!audioPermissionState.status.shouldShowRationale) {
                LaunchedEffect(Unit) { audioPermissionState.launchPermissionRequest() }
                Column(
                    modifier = Modifier.padding(contentPadding).fillMaxSize(),
                    verticalArrangement = Arrangement.Center,
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Text(
                        text = stringResource(R.string.voice_call_requesting_permission),
                        textAlign = TextAlign.Center,
                        color = Color.White,
                    )
                }
            } else {
                Column(
                    modifier = Modifier.padding(contentPadding).fillMaxSize(),
                    verticalArrangement = Arrangement.Center,
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Text(
                        text = stringResource(R.string.voice_call_permission_rationale),
                        textAlign = TextAlign.Center,
                        color = Color.White,
                    )
                    Spacer(Modifier.height(8.dp))
                    Button(
                        onClick = {
                            try {
                                val intent =
                                    Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                                        data = Uri.fromParts("package", context.packageName, null)
                                        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                                    }
                                context.startActivity(intent)
                            } catch (e: Exception) {
                                // 如果打开设置失败，回退到权限请求
                                audioPermissionState.launchPermissionRequest()
                            }
                        }
                    ) {
                        Text(stringResource(R.string.voice_call_open_settings))
                    }
                }
            }
        }
    }
}

/**
 * 根据待播队列与最近收到音频的时间，推导「来自音频的 speaking」状态。
 *
 * 使用场景：语音通话中 UI 需要在不依赖服务端 STATUS 的情况下，用本地播放缓冲与 HOLD/TAIL 时间保持 speaking 显示。
 * 入参：hasPendingPlaybackData（播放器队列是否非空）、音频流、以及收到每帧时调用的 onAudioData。 返回：是否应显示为 speaking（true 时与
 * callState 合并后显示“tap to interrupt”等）。
 */
@Composable
private fun rememberVoiceCallSpeakingFromAudio(
    hasPendingPlaybackData: Boolean,
    audioResponse: Flow<ByteArray>,
    onAudioData: (ByteArray) -> Unit,
): Boolean {
    var lastAudioTimestamp by remember { mutableStateOf(0L) }
    var isSpeakingFromAudio by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        audioResponse.collect { audioData ->
            onAudioData(audioData)
            lastAudioTimestamp = SystemClock.elapsedRealtime()
            isSpeakingFromAudio = true
        }
    }

    LaunchedEffect(hasPendingPlaybackData) {
        if (hasPendingPlaybackData) {
            isSpeakingFromAudio = true
            return@LaunchedEffect
        }
        if (lastAudioTimestamp == 0L) return@LaunchedEffect
        val elapsed = SystemClock.elapsedRealtime() - lastAudioTimestamp
        if (elapsed < UiConfigs.VoiceCall.SPEAKING_INDICATOR_HOLD_MS) {
            delay(UiConfigs.VoiceCall.SPEAKING_INDICATOR_HOLD_MS - elapsed)
        }
        delay(UiConfigs.VoiceCall.SPEAKING_INDICATOR_TAIL_MS)
        if (!hasPendingPlaybackData) {
            isSpeakingFromAudio = false
        }
    }

    return isSpeakingFromAudio
}

@Composable
private fun VoiceCallContent(
    onEnd: () -> Unit,
    onMuteChange: (Boolean) -> Unit,
    onInterrupt: () -> Unit,
    isSpeakingFromAudio: Boolean,
    uiState: VoiceCallUiState,
    modifier: Modifier = Modifier,
) {
    val isSpeaking = isSpeakingFromAudio || uiState.callState == CallStatus.SPEAKING
    val statusText: String? =
        when {
            isSpeaking -> null
            uiState.callState == CallStatus.LISTENING ->
                stringResource(R.string.voice_call_ai_status_listening)
            uiState.connectionState == VoiceCallConnectionUi.CONNECTED ->
                stringResource(R.string.voice_call_ai_status_listening)
            else -> uiState.connectionState.textRes?.let { stringResource(it) }
        }
    val promptText: String? =
        if (isSpeaking) stringResource(R.string.voice_call_tap_to_interrupt_ai) else null

    Column(modifier = modifier, horizontalAlignment = Alignment.CenterHorizontally) {
        Column(
            modifier = Modifier.weight(1f),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            uiState.agent?.run {
                val avatarModifier =
                    Modifier.size(UiConfigs.VoiceCall.Layout.AvatarSize)
                        .border(
                            width = UiConfigs.VoiceCall.Layout.AvatarBorderWidth,
                            color = Color.White,
                            shape = CircleShape,
                        )
                        .clip(CircleShape)

                // 头像
                if (isInEditMode) {
                    Box(avatarModifier.background(color = Color.Black))
                } else {
                    AsyncImage(
                        model = getCdnImageUrl(avatar),
                        contentDescription = "avatar",
                        contentScale = ContentScale.Crop,
                        modifier = avatarModifier,
                    )
                }

                Spacer(Modifier.height(UiConfigs.VoiceCall.Layout.AvatarToNameSpacing))

                // 名字
                Text(
                    text = name,
                    color = Color.White,
                    style = MaterialTheme.typography.titleLarge,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )

                Spacer(Modifier.height(UiConfigs.VoiceCall.Layout.NameToStatusSpacing))
            }

            Spacer(modifier = Modifier.height(dimensionResource(R.dimen.padding_large)))

            uiState.time?.run {
                Text(
                    text = stringResource(R.string.voice_call_duration),
                    style = MaterialTheme.typography.titleSmall,
                    color = Color.White.copy(0.8f),
                )
                Spacer(Modifier.height(UiConfigs.VoiceCall.Layout.TimeBlockSpacing))
                Text(
                    text = "${duration.seconds}",
                    style = MaterialTheme.typography.titleLarge,
                    color = Color.White,
                )
                Spacer(Modifier.height(UiConfigs.VoiceCall.Layout.TimeSectionSpacing))
                Text(
                    text = stringResource(R.string.voice_call_remaining_time),
                    style = MaterialTheme.typography.titleSmall,
                    color = Color.White.copy(0.8f),
                )
                Spacer(Modifier.height(UiConfigs.VoiceCall.Layout.TimeBlockSpacing))
                Text(
                    text = "${remaining.seconds}",
                    style = MaterialTheme.typography.titleLarge,
                    color = Color.White,
                )
            }

            Spacer(Modifier.height(dimensionResource(R.dimen.padding_large)))

            VoiceCallInterruptButton(
                statusText = statusText,
                promptText = promptText,
                isSpeaking = isSpeaking,
                onInterrupt = onInterrupt,
                modifier = Modifier.size(100.dp),
            )
        }

        Row(
            modifier =
                Modifier.fillMaxWidth()
                    .padding(bottom = UiConfigs.VoiceCall.Layout.BottomBarPadding),
            horizontalArrangement = Arrangement.SpaceEvenly,
        ) {
            MenuItem(
                button = {
                    IconToggleButton(
                        checked = uiState.isMuted,
                        onCheckedChange = onMuteChange,
                        shape = CircleShape,
                        colors =
                            IconButtonDefaults.iconToggleButtonColors(
                                containerColor = Color.White.copy(alpha = 0.3f),
                                checkedContainerColor = Color.White.copy(alpha = 0.3f),
                                contentColor = Color.White,
                                checkedContentColor = Color.White,
                            ),
                    ) {
                        if (uiState.isMuted) {
                            Icon(imageVector = Icons.Rounded.MicOff, contentDescription = "muted")
                        } else {
                            Icon(imageVector = Icons.Rounded.Mic, contentDescription = "mute")
                        }
                    }
                },
                text = { Text(text = stringResource(R.string.mute)) },
            )

            MenuItem(text = { Text(stringResource(R.string.end)) }) {
                IconButton(
                    onClick = onEnd,
                    colors = IconButtonDefaults.iconButtonColors(containerColor = Color(0xFFEB4E3D)),
                ) {
                    Icon(imageVector = Icons.Rounded.Close, contentDescription = "end")
                }
            }
        }
    }
}

/**
 * 语音通话页“打断 AI”圆形按钮。
 *
 * 使用场景：语音通话中展示 AI 当前状态，并提供用户打断 AI 的快捷操作入口。 预期视觉效果：Listening 时仅展示状态文案；Speaking 时仅展示“tap to
 * interrupt”提示，按钮外侧有波浪动画。 可配置项：状态文本（可选）、提示文本（可选）、是否在讲话、按钮尺寸、波浪尺寸、点击回调。
 */
@Composable
private fun VoiceCallInterruptButton(
    statusText: String?,
    promptText: String?,
    isSpeaking: Boolean,
    onInterrupt: () -> Unit,
    modifier: Modifier = Modifier,
    size: Dp = UiConfigs.VoiceCall.InterruptButton.Size,
    waveSize: Dp = UiConfigs.VoiceCall.InterruptButton.WaveSize,
) {
    val backgroundColor =
        Color.White.copy(alpha = UiConfigs.VoiceCall.InterruptButton.BackgroundAlpha)
    val borderColor = Color.White.copy(alpha = UiConfigs.VoiceCall.InterruptButton.BorderAlpha)
    val statusColor = Color.White.copy(alpha = UiConfigs.VoiceCall.InterruptButton.StatusTextAlpha)

    Box(modifier = modifier.size(waveSize), contentAlignment = Alignment.Center) {
        if (isSpeaking) {
            VoiceCallSpeakingWaveAnimation(
                modifier = Modifier.size(waveSize),
                waveColor = Color.White,
            )
        }

        Box(
            modifier =
                Modifier.size(size)
                    .clip(CircleShape)
                    .border(
                        width = UiConfigs.VoiceCall.InterruptButton.BorderWidth,
                        color = borderColor,
                        shape = CircleShape,
                    )
                    .background(backgroundColor)
                    .clickable(role = Role.Button, onClick = onInterrupt),
            contentAlignment = Alignment.Center,
        ) {
            Column(
                modifier = Modifier.padding(UiConfigs.VoiceCall.InterruptButton.ContentPadding),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center,
            ) {
                if (statusText != null) {
                    Text(
                        text = statusText,
                        color = statusColor,
                        style =
                            MaterialTheme.typography.labelSmall.copy(
                                fontSize = UiConfigs.Typography.Support,
                                lineHeight = UiConfigs.LineHeight.Support,
                            ),
                        maxLines = 1,
                    )
                    if (promptText != null) {
                        Spacer(Modifier.height(UiConfigs.VoiceCall.InterruptButton.TextSpacing))
                    }
                }
                if (promptText != null) {
                    Text(
                        text = promptText,
                        color = Color.White,
                        style = MaterialTheme.typography.labelSmall,
                        textAlign = TextAlign.Center,
                        maxLines = 2,
                    )
                }
            }
        }
    }
}

/**
 * 语音通话中 AI 讲话时的波浪动画。
 *
 * 使用场景：仅在 Speaking 状态显示，用于强化 AI 正在讲话的反馈。 预期视觉效果：按钮外侧出现多层扩散的圆形波纹，低频、柔和、循环播放。
 * 可配置项：波浪颜色、数量、时长、错开间隔、缩放范围、线宽。
 */
@Composable
private fun VoiceCallSpeakingWaveAnimation(
    modifier: Modifier = Modifier,
    waveColor: Color,
    waveCount: Int = UiConfigs.VoiceCall.InterruptButton.WaveCount,
    waveDurationMs: Int = UiConfigs.VoiceCall.InterruptButton.WaveDurationMs,
    waveDelayMs: Int = UiConfigs.VoiceCall.InterruptButton.WaveDelayMs,
    minScale: Float = UiConfigs.VoiceCall.InterruptButton.WaveStartScale,
    maxScale: Float = UiConfigs.VoiceCall.InterruptButton.WaveEndScale,
    baseAlpha: Float = UiConfigs.VoiceCall.InterruptButton.WaveAlpha,
    strokeWidth: Dp = UiConfigs.VoiceCall.InterruptButton.WaveStrokeWidth,
) {
    val transition = rememberInfiniteTransition(label = "VoiceCallSpeakingWave")
    val waveScales =
        List(waveCount) { index ->
            transition.animateFloat(
                initialValue = minScale,
                targetValue = maxScale,
                animationSpec =
                    infiniteRepeatable(
                        animation = tween(durationMillis = waveDurationMs, easing = LinearEasing),
                        repeatMode = RepeatMode.Restart,
                        initialStartOffset = StartOffset(index * waveDelayMs),
                    ),
                label = "VoiceCallSpeakingWave$index",
            )
        }

    Canvas(modifier = modifier) {
        val baseRadius = size.minDimension / 2f / maxScale
        waveScales.forEach { scaleState ->
            val scale = scaleState.value
            val progress = ((scale - minScale) / (maxScale - minScale)).coerceIn(0f, 1f)
            val alpha = baseAlpha * (1f - progress)
            drawCircle(
                color = waveColor.copy(alpha = alpha),
                radius = baseRadius * scale,
                style = Stroke(width = strokeWidth.toPx()),
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun VoiceCallScreen(onBack: () -> Unit, content: @Composable (PaddingValues) -> Unit) {

    Scaffold(
        topBar = {
            TopAppBar(
                title = {},
                colors =
                    TopAppBarDefaults.topAppBarColors(
                        containerColor = Color.Transparent,
                        navigationIconContentColor = Color.White,
                    ),
            )
        },
        containerColor = Color.Transparent,
        modifier =
            Modifier.background(
                brush = Brush.verticalGradient(0f to Color(0xFF6685D1), 1f to Color(0xFF926BCE))
            ),
        content = content,
    )
}

@Composable
private fun MenuItem(
    text: @Composable () -> Unit,
    modifier: Modifier = Modifier,
    button: @Composable () -> Unit,
) {
    Box(modifier = modifier) {
        CompositionLocalProvider(LocalContentColor provides Color.White) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                button()

                ProvideTextStyle(MaterialTheme.typography.bodySmall, text)
            }
        }
    }
}

@Preview(device = "id:Galaxy Nexus")
@Composable
private fun VoiceCallPreview() {
    IntelliMateTheme {
        VoiceCallScreen(onBack = {}) {
            VoiceCallContent(
                onEnd = {},
                onMuteChange = {},
                onInterrupt = {},
                isSpeakingFromAudio = true,
                uiState =
                    VoiceCallUiState(
                        agent = AgentInfo(name = "July"),
                        connectionState = VoiceCallConnectionUi.CONNECTING,
                        callState = CallStatus.SPEAKING,
                        time = VoiceCallUiState.Time(30, 100),
                    ),
                modifier = Modifier.padding(it).fillMaxSize(),
            )
        }
    }
}
