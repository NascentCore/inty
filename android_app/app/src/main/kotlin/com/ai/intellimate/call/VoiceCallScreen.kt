package com.ai.intellimate.call

import ai.sxwl.android.data.api.getCdnImageUrl
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.http.IntyErrorCode
import ai.sxwl.android.design.isInEditMode
import ai.sxwl.android.design.theme.IntelliMateTheme
import ai.sxwl.android.utils.ToastUtils
import android.Manifest
import android.annotation.SuppressLint
import android.content.Intent
import android.media.AudioFormat
import android.net.Uri
import android.provider.Settings
import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import coil3.compose.AsyncImage
import com.ai.intellimate.R
import com.ai.intellimate.audio.AudioParams
import com.ai.intellimate.audio.AudioRecordManager
import com.ai.intellimate.audio.AudioStreamPlayer
import com.ai.intellimate.call.data.ConnectionState
import com.ai.intellimate.call.uistate.VoiceCallUiState
import com.ai.intellimate.ui.ChatDialogData
import com.ai.intellimate.ui.UnlimitChatDialog
import com.google.accompanist.permissions.ExperimentalPermissionsApi
import com.google.accompanist.permissions.isGranted
import com.google.accompanist.permissions.rememberPermissionState
import com.google.accompanist.permissions.shouldShowRationale
import kotlin.time.Duration.Companion.seconds
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

    VoiceCallScreen(onBack = {onBack(viewModel.messageCount)}) { contentPadding ->
        // 权限请求Launcher
        val audioPermissionState = rememberPermissionState(Manifest.permission.RECORD_AUDIO)
        val context = LocalContext.current

        if (audioPermissionState.status.isGranted) {
            val uiState by viewModel.uiState.collectAsState()
            val audioStreamPlayer = AudioStreamPlayer.getInstance()
            val audioRecordManager = AudioRecordManager.getInstance(context)
            var error by remember { mutableStateOf<Pair<IntyErrorCode, String>?>(null) }

            // 启动通话连接
            LaunchedEffect(agentId) { viewModel.startCalling(agentId) }

            LaunchedEffect(viewModel) { viewModel.error.collect { error = it } }

            // 播放接收的音频数据
            LaunchedEffect(Unit) {
                viewModel.audioResponse.collect { audioData ->
                    // 播放音频
                    audioStreamPlayer.addAudioData(audioData)
                }
            }

            // 管理播放器生命周期
            LaunchedEffect(uiState.connectionState) {
                when (uiState.connectionState) {
                    ConnectionState.CONNECTED -> {
                        // 连接建立时启动播放（24kHz PCM，单声道，16位）
                        val playbackParams =
                            AudioParams(
                                sampleRate = 24000,
                                channelConfig = AudioFormat.CHANNEL_OUT_MONO,
                                audioFormat = AudioFormat.ENCODING_PCM_16BIT,
                            )
                        audioStreamPlayer.startPlayback(playbackParams)
                    }
                    ConnectionState.DISCONNECTED,
                    ConnectionState.ERROR,
                    ConnectionState.DISCONNECTING -> {
                        // 断开连接时停止播放
                        audioStreamPlayer.stopPlayback()
                    }
                    else -> {}
                }
            }

            LaunchedEffect(Unit) {
                snapshotFlow {
                        uiState.connectionState == ConnectionState.CONNECTED && !uiState.isMuted
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
                onEnd = {onBack(viewModel.messageCount)},
                uiState = uiState,
                onMuteChange = viewModel::setMuted,
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

@Composable
private fun VoiceCallContent(
    onEnd: () -> Unit,
    onMuteChange: (Boolean) -> Unit,
    uiState: VoiceCallUiState,
    modifier: Modifier = Modifier,
) {
    Box(modifier = modifier) {
        Column(
            modifier = Modifier.align(Alignment.TopCenter),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Spacer(Modifier.height(160.dp))
            uiState.agent?.run {
                val avatarModifier =
                    Modifier.size(120.dp)
                        .border(width = 1.dp, color = Color.White, shape = CircleShape)
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

                Spacer(Modifier.height(16.dp))

                // 名字
                Text(
                    text = name,
                    color = Color.White,
                    style = MaterialTheme.typography.titleLarge,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )

                Spacer(Modifier.height(8.dp))
            }

            // 连接状态
            uiState.connectionState.textRes?.let {
                Text(
                    text = stringResource(it),
                    color = Color.White,
                    style = MaterialTheme.typography.bodySmall,
                )
            }

            Spacer(Modifier.height(50.dp))

            uiState.time?.run {
                Text(
                    text = stringResource(R.string.voice_call_duration),
                    style = MaterialTheme.typography.titleSmall,
                    color = Color.White.copy(0.8f),
                )
                Spacer(Modifier.height(6.dp))
                Text(
                    text = "${duration.seconds}",
                    style = MaterialTheme.typography.titleLarge,
                    color = Color.White,
                )
                Spacer(Modifier.height(16.dp))
                Text(
                    text = stringResource(R.string.voice_call_remaining_time),
                    style = MaterialTheme.typography.titleSmall,
                    color = Color.White.copy(0.8f),
                )
                Spacer(Modifier.height(6.dp))
                Text(
                    text = "${remaining.seconds}",
                    style = MaterialTheme.typography.titleLarge,
                    color = Color.White,
                )
            }
        }

        Row(
            modifier =
                Modifier.align(Alignment.BottomCenter).fillMaxWidth().padding(bottom = 50.dp),
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

@Preview
@Composable
private fun VoiceCallPreview() {
    IntelliMateTheme {
        VoiceCallScreen(onBack = {}) {
            VoiceCallContent(
                onEnd = {},
                onMuteChange = {},
                uiState =
                    VoiceCallUiState(
                        agent = AgentInfo(name = "July"),
                        connectionState = ConnectionState.CONNECTING,
                        time = VoiceCallUiState.Time(30, 100),
                    ),
                modifier = Modifier.padding(it).fillMaxSize(),
            )
        }
    }
}
