package com.ai.inty.audio

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Error
import androidx.compose.material.icons.filled.Pause
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.inty.utils.log.EasyLog
import kotlinx.coroutines.delay

/**
 * 语音播放器组件
 * 企业级UI设计，支持播放控制、进度显示、状态指示
 */
@Composable
fun VoicePlayer(
    audioInfo: AudioInfo,
    modifier: Modifier = Modifier,
    onPlayStateChange: ((Boolean) -> Unit)? = null,
    autoPlay: Boolean = false,
) {
    val context = LocalContext.current
    val audioManager = remember { AudioPlaybackManager.getInstance(context) }

    // 使用消息ID作为状态标识
    val messageId = audioInfo.messageId ?: audioInfo.url

    // 本地状态
    var isPlaying by remember(messageId) { mutableStateOf(false) }
    var isLoading by remember(messageId) { mutableStateOf(false) }
    var hasError by remember(messageId) { mutableStateOf(false) }
    var currentPosition by remember(messageId) { mutableLongStateOf(0L) }
    var duration by remember(messageId) { mutableLongStateOf(0L) }

    // 监听播放状态变化 - 使用更精确的状态管理
    LaunchedEffect(messageId) {
        // 监听全局播放状态
        audioManager.playbackState.collect { globalState ->
            val currentAudioInfo = audioManager.getCurrentAudioInfo()
            // 优先使用messageId判断，避免URL参数导致的判断错误
            val isCurrentMessage = currentAudioInfo?.messageId == messageId

            EasyLog.log("VoicePlayer[$messageId] state update: globalState=$globalState, isCurrentMessage=$isCurrentMessage")

            if (isCurrentMessage) {
                // 只有当前播放的消息才更新状态
                isPlaying = globalState == PlaybackState.PLAYING
                isLoading = globalState == PlaybackState.BUFFERING
                hasError = globalState == PlaybackState.ERROR
                onPlayStateChange?.invoke(isPlaying)
                EasyLog.log("VoicePlayer[$messageId] updated state: isPlaying=$isPlaying, isLoading=$isLoading, hasError=$hasError")
            } else {
                // 非当前消息保持停止状态
                if (isPlaying || isLoading) {
                    isPlaying = false
                    isLoading = false
                    hasError = false
                    EasyLog.log("VoicePlayer[$messageId] reset state (not current message)")
                }
            }
        }
    }

    // 监听播放进度
    LaunchedEffect(messageId) {
        audioManager.currentPosition.collect { position ->
            val currentAudioInfo = audioManager.getCurrentAudioInfo()
            if (currentAudioInfo?.messageId == messageId) {
                currentPosition = position
            }
        }
    }

    // 监听音频时长
    LaunchedEffect(messageId) {
        audioManager.duration.collect { dur ->
            val currentAudioInfo = audioManager.getCurrentAudioInfo()
            if (currentAudioInfo?.messageId == messageId) {
                duration = dur
            }
        }
    }

    // 自动播放
    LaunchedEffect(audioInfo.url, autoPlay) {
        if (autoPlay && !isPlaying && !hasError) {
            delay(100) // 短暂延迟确保UI准备就绪
            audioManager.playAudio(audioInfo, autoPlay = true)
        }
    }

    // 错误处理
    LaunchedEffect(messageId) {
        audioManager.error.collect { error ->
            val currentAudioInfo = audioManager.getCurrentAudioInfo()
            if (currentAudioInfo?.messageId == messageId) {
                hasError = error != null
                if (error != null) {
                    EasyLog.log("VoicePlayer error: $error", EasyLog.ERROR)
                }
            }
        }
    }

    ChatVoicePlayer(
        isPlaying = isPlaying,
        isLoading = isLoading,
        hasError = hasError,
        duration = duration,
        onPlayPause = {
            EasyLog.log("CompactVoicePlayer clicked: isPlaying=$isPlaying, messageId=$messageId")
            audioManager.playAudio(audioInfo, autoPlay = true)
        },
        modifier = modifier
    )
}

/**
 * 紧凑型语音播放器
 */
@Composable
private fun ChatVoicePlayer(
    isPlaying: Boolean,
    isLoading: Boolean,
    hasError: Boolean,
    duration: Long,
    onPlayPause: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier = modifier
            .clip(RoundedCornerShape(20.dp))
            .background(Color(0xFF44354F))
            .clickable { onPlayPause() }
            .padding(vertical = 2.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.Center
    ) {
        // 播放按钮
        Box(
            modifier = Modifier.size(16.dp),
            contentAlignment = Alignment.Center
        ) {
            when {
                isLoading -> {
                    CircularProgressIndicator(
                        modifier = Modifier.size(12.dp),
                        strokeWidth = 1.dp,
                        color = Color.White
                    )
                }

                hasError -> {
                    Icon(
                        imageVector = Icons.Default.Error,
                        contentDescription = "Error",
                        tint = Color.Red,
                        modifier = Modifier.size(16.dp)
                    )
                }

                else -> {
                    Icon(
                        imageVector = if (isPlaying) Icons.Default.Pause else Icons.Default.PlayArrow,
                        contentDescription = if (isPlaying) "Pause" else "Play",
                        tint = Color.White,
                        modifier = Modifier.size(16.dp)
                    )
                }
            }
        }
        // 格式化时间
        fun formatTime(timeMs: Long): String {
            val seconds = timeMs / 1000
            return "$seconds”"
        }
        Spacer(Modifier.width(2.dp))
        // 状态文本
        if (duration > 0) {
            Text(
                text = formatTime(duration),
                color = Color.White,
                fontSize = 12.sp,
                lineHeight = 12.sp
            )
        }
    }
}
