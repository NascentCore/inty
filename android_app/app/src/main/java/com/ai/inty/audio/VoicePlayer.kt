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
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
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
 * 简化版本，只负责UI显示，业务逻辑由AudioManager处理
 */
@Composable
fun VoicePlayer(
    audioInfo: AudioInfo,
    modifier: Modifier = Modifier,
    onPlayStateChange: ((Boolean) -> Unit)? = null,
    autoPlay: Boolean = false,
    onTtsGenerated: ((String) -> Unit)? = null, // TTS生成成功回调
    serverMessageId: String? = null, // 服务器端消息ID，用于TTS生成
) {
    val context = LocalContext.current
    val audioManager = remember {
        AudioManager.getInstance(
            context,
            kotlinx.coroutines.CoroutineScope(kotlinx.coroutines.Dispatchers.Main)
        )
    }

    // 使用消息ID作为状态标识
    val messageId = audioInfo.messageId ?: audioInfo.url

    // 监听播放状态
    val duration by audioManager.duration.collectAsState()
    val isLoading by audioManager.isLoading.collectAsState()
    var isGeneratingTts by remember(messageId) { mutableStateOf(false) }

    // 监听TTS生成状态
    LaunchedEffect(messageId) {
        while (true) {
            isGeneratingTts = audioManager.isGeneratingTtsForMessage(messageId)
            kotlinx.coroutines.delay(100) // 每100ms检查一次
        }
    }

    // 本地状态
    var isPlaying by remember(messageId) { mutableStateOf(false) }
    var hasError by remember(messageId) { mutableStateOf(false) }

    // 监听播放状态变化
    LaunchedEffect(messageId) {
        audioManager.playbackState.collect { state ->
            val currentAudioInfo = audioManager.getCurrentAudioInfo()
            val isCurrentMessage = currentAudioInfo?.messageId == messageId

            EasyLog.log("VoicePlayer state change: messageId=$messageId, state=$state, isCurrentMessage=$isCurrentMessage, currentAudioInfo=${currentAudioInfo?.messageId}")

            if (isCurrentMessage) {
                isPlaying = state == PlaybackState.PLAYING
                hasError = state == PlaybackState.ERROR
                onPlayStateChange?.invoke(isPlaying)
            } else {
                isPlaying = false
                hasError = false
            }
        }
    }

    // 自动播放（仅开场白消息）
    LaunchedEffect(autoPlay) {
        EasyLog.log("=== VoicePlayer LaunchedEffect ===")
        EasyLog.log("autoPlay: $autoPlay")
        EasyLog.log("audioUrl: ${audioInfo.url}")
        EasyLog.log("isPlaying: $isPlaying")
        EasyLog.log("hasError: $hasError")
        EasyLog.log("messageId: $messageId")
        
        if (autoPlay && !isPlaying && !hasError) {
            EasyLog.log("VoicePlayer conditions met, starting auto play...")
            // 增加延迟，确保组件完全初始化
            delay(200)
            
            // 再次检查状态，确保条件仍然满足
            if (autoPlay && !isPlaying && !hasError) {
                EasyLog.log("VoicePlayer auto playing opening message: $messageId, audioUrl: ${audioInfo.url}")
                audioManager.playMessageVoice(
                    messageId = messageId, // 使用localMsgId用于播放状态管理
                    audioUrl = audioInfo.url,
                    agentId = audioInfo.agentId ?: "",
                    autoPlay = true,
                    isManualClick = false, // 自动播放
                    onTtsGenerated = onTtsGenerated,
                    serverMessageId = serverMessageId // 传递服务器端ID用于TTS生成
                )
            } else {
                EasyLog.log("VoicePlayer auto play conditions no longer met after delay: autoPlay=$autoPlay, isPlaying=$isPlaying, hasError=$hasError")
            }
        } else {
            EasyLog.log("VoicePlayer auto play conditions not met: autoPlay=$autoPlay, isPlaying=$isPlaying, hasError=$hasError")
        }
        EasyLog.log("=== End VoicePlayer LaunchedEffect ===")
    }

    ChatVoicePlayer(
        isPlaying = isPlaying,
        isLoading = isLoading || isGeneratingTts,
        hasError = hasError,
        duration = duration,
        isGeneratingTts = isGeneratingTts,
        onPlayPause = {
            EasyLog.log("VoicePlayer clicked: isPlaying=$isPlaying, messageId=$messageId, audioUrl=${audioInfo.url}")

            if (isPlaying) {
                audioManager.pausePlayback()
            } else {
                audioManager.playMessageVoice(
                    messageId = messageId, // 使用localMsgId用于播放状态管理
                    audioUrl = audioInfo.url,
                    agentId = audioInfo.agentId ?: "",
                    autoPlay = true, // 手动点击时也需要播放
                    isManualClick = true, // 标记为手动点击
                    onTtsGenerated = onTtsGenerated,
                    serverMessageId = serverMessageId // 传递服务器端ID用于TTS生成
                )
            }
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
    isGeneratingTts: Boolean = false,
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
                        contentDescription = if (isPlaying) "Pause" else if (isGeneratingTts) "Generating" else "Play",
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
