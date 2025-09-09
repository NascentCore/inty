package com.ai.inty.audio

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Pause
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
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
import androidx.compose.ui.text.font.FontWeight
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
    showProgress: Boolean = true,
    compact: Boolean = false
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

    // 格式化时间
    fun formatTime(timeMs: Long): String {
        val seconds = timeMs / 1000
        val minutes = seconds / 60
        val remainingSeconds = seconds % 60
        return String.format("%d:%02d", minutes, remainingSeconds)
    }

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

    if (compact) {
        CompactVoicePlayer(
            isPlaying = isPlaying,
            isLoading = isLoading,
            hasError = hasError,
            onPlayPause = {
                EasyLog.log("CompactVoicePlayer clicked: isPlaying=$isPlaying, messageId=$messageId")
                audioManager.playAudio(audioInfo, autoPlay = true)
            },
            modifier = modifier
        )
    } else {
        FullVoicePlayer(
            audioInfo = audioInfo,
            isPlaying = isPlaying,
            isLoading = isLoading,
            hasError = hasError,
            currentPosition = currentPosition,
            duration = duration,
            showProgress = showProgress,
            onPlayPause = {
                EasyLog.log("FullVoicePlayer clicked: isPlaying=$isPlaying, messageId=$messageId")
                audioManager.playAudio(audioInfo, autoPlay = true)
            },
            onSeek = { position ->
                audioManager.seekTo(position)
            },
            formatTime = ::formatTime,
            modifier = modifier
        )
    }
}

/**
 * 紧凑型语音播放器
 */
@Composable
private fun CompactVoicePlayer(
    isPlaying: Boolean,
    isLoading: Boolean,
    hasError: Boolean,
    onPlayPause: () -> Unit,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier
            .clip(RoundedCornerShape(20.dp))
            .background(Color.Black.copy(alpha = 0.3f))
            .clickable { onPlayPause() }
            .padding(horizontal = 12.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        // 播放按钮
        Box(
            modifier = Modifier.size(24.dp),
            contentAlignment = Alignment.Center
        ) {
            when {
                isLoading -> {
                    CircularProgressIndicator(
                        modifier = Modifier.size(20.dp),
                        strokeWidth = 2.dp,
                        color = Color.White
                    )
                }

                hasError -> {
                    Icon(
                        imageVector = Icons.Default.PlayArrow,
                        contentDescription = "Error",
                        tint = Color.Red,
                        modifier = Modifier.size(20.dp)
                    )
                }

                else -> {
                    Icon(
                        imageVector = if (isPlaying) Icons.Default.Pause else Icons.Default.PlayArrow,
                        contentDescription = if (isPlaying) "Pause" else "Play",
                        tint = Color.White,
                        modifier = Modifier.size(20.dp)
                    )
                }
            }
        }

        // 状态文本
        Text(
            text = when {
                isLoading -> "加载中..."
                hasError -> "播放失败"
                isPlaying -> "播放中"
                else -> "点击播放"
            },
            color = Color.White,
            fontSize = 12.sp,
            fontWeight = FontWeight.Medium
        )
    }
}

/**
 * 完整型语音播放器
 */
@Composable
private fun FullVoicePlayer(
    audioInfo: AudioInfo,
    isPlaying: Boolean,
    isLoading: Boolean,
    hasError: Boolean,
    currentPosition: Long,
    duration: Long,
    showProgress: Boolean,
    onPlayPause: () -> Unit,
    onSeek: (Long) -> Unit,
    formatTime: (Long) -> String,
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .background(Color.Black.copy(alpha = 0.4f))
            .padding(16.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            // 播放按钮
            IconButton(
                onClick = onPlayPause,
                modifier = Modifier
                    .size(48.dp)
                    .clip(CircleShape)
                    .background(
                        if (hasError) Color.Red.copy(alpha = 0.3f)
                        else Color.White.copy(alpha = 0.2f)
                    )
            ) {
                when {
                    isLoading -> {
                        CircularProgressIndicator(
                            modifier = Modifier.size(24.dp),
                            strokeWidth = 3.dp,
                            color = Color.White
                        )
                    }

                    hasError -> {
                        Icon(
                            imageVector = Icons.Default.PlayArrow,
                            contentDescription = "Retry",
                            tint = Color.Red,
                            modifier = Modifier.size(24.dp)
                        )
                    }

                    else -> {
                        Icon(
                            imageVector = if (isPlaying) Icons.Default.Pause else Icons.Default.PlayArrow,
                            contentDescription = if (isPlaying) "Pause" else "Play",
                            tint = Color.White,
                            modifier = Modifier.size(24.dp)
                        )
                    }
                }
            }

            // 音频信息
            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                // 标题
                Text(
                    text = audioInfo.title ?: "语音消息",
                    color = Color.White,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Medium,
                    maxLines = 1
                )

                // 时间信息
                if (duration > 0) {
                    Text(
                        text = "${formatTime(currentPosition)} / ${formatTime(duration)}",
                        color = Color.White.copy(alpha = 0.7f),
                        fontSize = 12.sp
                    )
                }

                // 进度条
                if (showProgress && duration > 0) {
                    Spacer(modifier = Modifier.height(4.dp))
                    LinearProgressIndicator(
                        progress = { currentPosition.toFloat() / duration.toFloat() },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(3.dp)
                            .clip(RoundedCornerShape(1.5.dp)),
                        color = Color.White,
                        trackColor = Color.White.copy(alpha = 0.3f)
                    )
                }
            }
        }
    }
}
