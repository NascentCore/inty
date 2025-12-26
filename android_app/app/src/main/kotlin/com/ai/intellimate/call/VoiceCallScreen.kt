package com.ai.intellimate.call

import ai.sxwl.android.design.theme.HeartColor
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.PermissionUtils
import android.Manifest
import android.annotation.SuppressLint
import android.media.AudioFormat
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import coil3.compose.AsyncImage
import com.ai.intellimate.R
import com.ai.intellimate.audio.AudioParams
import com.ai.intellimate.audio.AudioRecordManager
import com.ai.intellimate.audio.AudioStreamPlayer
import com.ai.intellimate.call.data.ConnectionState
import com.ai.intellimate.call.uistate.VoiceCallUiState
import com.ai.intellimate.ui.components.AgentBackground
import com.google.accompanist.permissions.ExperimentalPermissionsApi
import com.google.accompanist.permissions.isGranted
import com.google.accompanist.permissions.rememberPermissionState

/**
 * 语音通话页面
 * 提供与AI的实时语音通讯功能
 *
 * @param onBack 退出界面
 * @param agentId 角色ID
 */
@SuppressLint("MissingPermission")
@OptIn(ExperimentalPermissionsApi::class)
@Composable
fun VoiceCallScreen(
    onBack: () -> Unit,
    agentId: String
) {
    val context = LocalContext.current
    val viewModel = viewModel<VoiceCallViewModel>()
    val uiState by viewModel.uiState.collectAsState()
    // 权限请求Launcher
    val audioPermissionState = rememberPermissionState(Manifest.permission.RECORD_AUDIO)

    if (audioPermissionState.status.isGranted) {
        val audioStreamPlayer = AudioStreamPlayer.getInstance()
        val audioRecordManager = AudioRecordManager.getInstance(context)

        // 启动通话连接
        LaunchedEffect(agentId) {
            viewModel.startCalling(agentId)
        }

        // 播放接收的音频数据
        LaunchedEffect(Unit) {
            viewModel.audioResponse
                .collect { audioData ->
                    // 播放音频
                    audioStreamPlayer.addAudioData(audioData)
                }
        }

        // 管理播放器生命周期
        LaunchedEffect(uiState.connectionState) {
            when (uiState.connectionState) {
                ConnectionState.CONNECTED -> {
                    // 连接建立时启动播放（24kHz PCM，单声道，16位）
                    val playbackParams = AudioParams(
                        sampleRate = 24000,
                        channelConfig = AudioFormat.CHANNEL_OUT_MONO,
                        audioFormat = AudioFormat.ENCODING_PCM_16BIT
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

        // 录制音频，通过viewModel.sendVoice实时发送音频数据
        DisposableEffect(uiState.connectionState) {
            when (uiState.connectionState) {
                ConnectionState.CONNECTED -> {
                    // 连接建立时开始录制
                    audioRecordManager.startRecording { audioData ->
                        viewModel.sendVoice(audioData)
                    }
                }
                else -> {
                    // 断开连接时停止录制
                    audioRecordManager.stopRecording()
                }
            }

            onDispose {
                // 组件销毁时停止录制和播放
                audioRecordManager.stopRecording()
                audioStreamPlayer.stopPlayback()
            }
        }

        VoiceCallScreen(
            onBack = onBack,
            uiState = uiState
        )
    } else {
        Box(
            modifier = Modifier.fillMaxSize(),
            contentAlignment = Alignment.Center
        ) {
            Button(
                onClick = { audioPermissionState.launchPermissionRequest()}
            ) {
                Text("需要录音权限")
            }
        }
    }
}

@Composable
private fun VoiceCallScreen(
    onBack: () -> Unit,
    uiState: VoiceCallUiState
) {

    Box(modifier = Modifier.fillMaxSize()) {
        AsyncImage(
            model = uiState.agent?.background,
            contentDescription = "background",
            contentScale = ContentScale.Crop,
            modifier = Modifier.fillMaxSize()
        )
        Column(
            modifier = Modifier.fillMaxSize(),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Spacer(Modifier.weight(1f))

            Text(text = "连接状态:${uiState.connectionState.name}", color = Color.White)

            if (uiState.callState != null) {
                Text(text = "通话状态:${uiState.callState.name}", color = Color.White)
            }

            Spacer(Modifier.weight(1f))
            Button(
                onClick = onBack,
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.error
                )
            ) {
                Text("结束通话")
            }
            Spacer(Modifier.height(50.dp))
        }
    }
}

/**
 * 连接状态文本
 */
@Composable
private fun ConnectionStatusText(
    connectionState: ConnectionState,
    recordingState: com.ai.intellimate.audio.RecordingState,
    playbackState: com.ai.intellimate.audio.PlaybackState
) {
    val statusText = when {
        connectionState == ConnectionState.CONNECTING -> stringResource(R.string.voice_call_connecting)
        connectionState == ConnectionState.CONNECTED -> {
            when {
                recordingState == com.ai.intellimate.audio.RecordingState.RECORDING ->
                    stringResource(R.string.voice_call_recording)
                playbackState == com.ai.intellimate.audio.PlaybackState.PLAYING ->
                    stringResource(R.string.voice_call_playing)
                else -> stringResource(R.string.voice_call_connected)
            }
        }
        connectionState == ConnectionState.ERROR -> stringResource(R.string.voice_call_error)
        else -> stringResource(R.string.voice_call_disconnected)
    }

    Text(
        text = statusText,
        color = Color.White,
        fontSize = 18.sp,
        textAlign = TextAlign.Center
    )
}

/**
 * 权限请求按钮
 */
@Composable
private fun PermissionRequestButton(onClick: () -> Unit) {
    Button(
        onClick = onClick,
        modifier = Modifier.size(120.dp),
        shape = CircleShape
    ) {
        Text(
            text = stringResource(R.string.voice_call_request_permission),
            fontSize = 14.sp
        )
    }
}

/**
 * 通话控制按钮
 */
@Composable
private fun CallControlButton(
    isCallActive: Boolean,
    connectionState: ConnectionState,
    onClick: () -> Unit
) {
    Box(
        modifier = Modifier.size(120.dp),
        contentAlignment = Alignment.Center
    ) {
        if (connectionState == ConnectionState.CONNECTING) {
            CircularProgressIndicator(
                color = Color.White,
                modifier = Modifier.size(60.dp)
            )
        } else {
            Button(
                onClick = onClick,
                modifier = Modifier.size(120.dp),
                shape = CircleShape,
                colors =
                    androidx.compose.material3.ButtonDefaults.buttonColors(
                        containerColor =
                            if (isCallActive) {
                                Color.Red
                            } else {
                                MaterialTheme.colorScheme.primary
                            }
                    )
            ) {
                Text(
                    text =
                        if (isCallActive) {
                            stringResource(R.string.voice_call_end)
                        } else {
                            stringResource(R.string.voice_call_start)
                        },
                    fontSize = 16.sp,
                    color = Color.White
                )
            }
        }
    }
}

