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
import androidx.compose.material.icons.filled.ReportGmailerrorred
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
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
import kotlinx.coroutines.launch

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
    val coroutineScope = rememberCoroutineScope()
    val audioManager = remember {
        AudioManager.getInstance(
            context,
            kotlinx.coroutines.CoroutineScope(kotlinx.coroutines.Dispatchers.Main)
        )
    }

    // 使用消息ID作为状态标识
    val messageId = audioInfo.messageId ?: audioInfo.url

    // 本地状态 - 每个消息独立管理
    var duration by remember(messageId) { mutableLongStateOf(0L) }
    var isLoading by remember(messageId) { mutableStateOf(false) }
    var isGeneratingTts by remember(messageId) { mutableStateOf(false) }
    var isUserClicked by remember(messageId) { mutableStateOf(false) } // 用户是否点击过
    var ttsGenerationFailed by remember(messageId) { mutableStateOf(false) } // TTS生成是否失败
    
    // 防抖状态
    var isClickDebounced by remember(messageId) { mutableStateOf(false) }

    // 监听TTS生成状态
    LaunchedEffect(messageId) {
        while (true) {
            // 从AudioManager获取TTS生成状态
            val managerTtsState = audioManager.isGeneratingTtsForMessage(messageId)
            
            // 如果AudioManager显示正在生成TTS，则更新本地状态
            if (managerTtsState) {
                isGeneratingTts = true
            }
            // 如果AudioManager显示不在生成TTS，且用户没有手动设置状态，则更新本地状态
            else if (!isUserClicked) {
                isGeneratingTts = false
            }
            
            delay(100) // 每100ms检查一次
        }
    }

    // 本地状态
    var isPlaying by remember(messageId) { mutableStateOf(false) }
    var hasError by remember(messageId) { mutableStateOf(false) }

    // 监听播放状态变化 - 只监听当前消息的状态
    LaunchedEffect(messageId) {
        audioManager.playbackState.collect { state ->
            val currentAudioInfo = audioManager.getCurrentAudioInfo()
            val isCurrentMessage = currentAudioInfo?.messageId == messageId

            EasyLog.log("VoicePlayer state change: messageId=$messageId, state=$state, isCurrentMessage=$isCurrentMessage, currentAudioInfo=${currentAudioInfo?.messageId}")

            if (isCurrentMessage) {
                isPlaying = state == PlaybackState.PLAYING
                hasError = state == PlaybackState.ERROR
                // 如果用户点击过且正在缓冲，显示loading
                isLoading = state == PlaybackState.BUFFERING && isUserClicked
                
                // 播放完成后重置用户点击状态
                if (state == PlaybackState.ENDED) {
                    isUserClicked = false
                }
                
                onPlayStateChange?.invoke(isPlaying)
            } else {
                isPlaying = false
                hasError = false
                // 非当前消息不显示loading，除非正在生成TTS
                isLoading = false
            }
        }
    }

    // 监听时长变化 - 只监听当前消息的时长
    LaunchedEffect(messageId) {
        audioManager.duration.collect { globalDuration ->
            val currentAudioInfo = audioManager.getCurrentAudioInfo()
            val isCurrentMessage = currentAudioInfo?.messageId == messageId

            if (isCurrentMessage) {
                duration = globalDuration
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
            if (!isPlaying && !hasError) {
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
        isUserClicked = isUserClicked,
        ttsGenerationFailed = ttsGenerationFailed,
        onPlayPause = {
            EasyLog.log("VoicePlayer clicked: isPlaying=$isPlaying, messageId=$messageId, audioUrl=${audioInfo.url}")
            EasyLog.log("Click debounce state: isClickDebounced=$isClickDebounced, isGeneratingTts=$isGeneratingTts")

            // 防抖检查：防止快速重复点击
            if (isClickDebounced) {
                EasyLog.log("Click ignored due to debounce")
                return@ChatVoicePlayer
            }

            // 如果正在生成TTS且不是失败状态，则阻止点击
            if (isGeneratingTts && !ttsGenerationFailed) {
                EasyLog.log("Click ignored due to TTS generation in progress")
                return@ChatVoicePlayer
            }

            // 设置防抖状态
            isClickDebounced = true
            coroutineScope.launch {
                // 防抖延迟：500ms
                delay(500)
                isClickDebounced = false
                EasyLog.log("Click debounce reset for messageId: $messageId")
            }

            if (isPlaying) {
                audioManager.pausePlayback()
            } else {
                // 立即显示loading状态
                isUserClicked = true
                ttsGenerationFailed = false // 重置失败状态
                
                // 如果audioUrl为空，立即显示TTS生成loading
                if (audioInfo.url.isEmpty()) {
                    EasyLog.log("Audio URL is empty, showing TTS generation loading immediately")
                    isGeneratingTts = true // 立即显示TTS生成状态
                } else {
                    EasyLog.log("Audio URL exists, showing audio loading")
                    isLoading = true // 立即显示音频加载状态
                }
                
                audioManager.playMessageVoice(
                    messageId = messageId, // 使用localMsgId用于播放状态管理
                    audioUrl = audioInfo.url,
                    agentId = audioInfo.agentId ?: "",
                    autoPlay = true, // 手动点击时也需要播放
                    isManualClick = true, // 标记为手动点击
                    onTtsGenerated = { generatedUrl ->
                        // TTS生成成功，重置状态并继续播放
                        isGeneratingTts = false
                        ttsGenerationFailed = false
                        isUserClicked = false // 重置用户点击状态，允许轮询接管
                        onTtsGenerated?.invoke(generatedUrl)
                    },
                    onTtsFailed = { error ->
                        // TTS生成失败，显示错误状态
                        EasyLog.log("TTS generation failed: $error", EasyLog.ERROR)
                        isGeneratingTts = false
                        ttsGenerationFailed = true
                        isUserClicked = false // 重置用户点击状态，允许轮询接管
                    },
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
    isUserClicked: Boolean = false,
    ttsGenerationFailed: Boolean = false,
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
                // 优先显示错误状态
                hasError -> {
                    Icon(
                        imageVector = Icons.Default.Error,
                        contentDescription = "Error",
                        tint = Color.Red,
                        modifier = Modifier.size(16.dp)
                    )
                }
                
                // 显示TTS生成失败状态（⚠️图标）
                ttsGenerationFailed -> {
                    Icon(
                        imageVector = Icons.Default.ReportGmailerrorred,
                        contentDescription = "TTS Failed",
                        tint = Color.Yellow,
                        modifier = Modifier.size(16.dp)
                    )
                }
                
                // 显示loading状态：TTS生成中或音频加载中
                isGeneratingTts || isLoading -> {
                    CircularProgressIndicator(
                        modifier = Modifier.size(12.dp),
                        strokeWidth = 1.dp,
                        color = Color.White
                    )
                }

                // 正常播放状态
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
