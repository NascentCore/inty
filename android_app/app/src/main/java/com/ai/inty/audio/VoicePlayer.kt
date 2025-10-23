package com.ai.inty.audio

import ai.sxwl.android.utils.LogUtils
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
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.vectorResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.inty.R
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay

/** 语音播放器组件 简化版本，只负责UI显示，业务逻辑由AudioManager处理 */
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
        AudioManager.getInstance(context, CoroutineScope(Dispatchers.Main + SupervisorJob()))
    }

    // 本地播放状态使用本地messageId；TTS状态跟踪优先使用serverMessageId
    val messageId = audioInfo.messageId ?: audioInfo.url
    val ttsTrackingId = serverMessageId ?: messageId

    // 本地状态 - 每个消息独立管理
    var duration by remember(messageId) { mutableLongStateOf(0L) }
    var isLoading by remember(messageId) { mutableStateOf(false) }
    var isGeneratingTts by remember(messageId) { mutableStateOf(false) }
    var ttsGenerationFailed by remember(messageId) { mutableStateOf(false) } // TTS生成是否失败
    var userClickedRecently by remember(messageId) { mutableStateOf(false) } // 用户最近是否点击过
    var ttsGenerationStartTime by remember(messageId) { mutableLongStateOf(0L) } // TTS生成开始时间

    // 监听TTS生成状态（使用serverMessageId优先作为跟踪ID）
    LaunchedEffect(ttsTrackingId) {
        while (true) {
            // 从AudioManager获取TTS生成状态
            val managerTtsState = audioManager.isGeneratingTtsForMessage(ttsTrackingId)

            // 同步TTS生成状态
            if (managerTtsState) {
                if (!isGeneratingTts) {
                    // TTS刚开始生成，记录开始时间
                    ttsGenerationStartTime = System.currentTimeMillis()
                }
                isGeneratingTts = true
                // 不要立即清除userClickedRecently，保持用户点击状态
            } else if (isGeneratingTts) {
                // TTS生成完成或失败，重置状态
                isGeneratingTts = false
                userClickedRecently = false
                ttsGenerationStartTime = 0L
            }

            // 检查TTS生成超时（30秒超时）
            if (isGeneratingTts && ttsGenerationStartTime > 0) {
                val elapsedTime = System.currentTimeMillis() - ttsGenerationStartTime
                if (elapsedTime > 30000) { // 30秒超时
                    LogUtils.e("音频LOG测试 TTS generation timeout: trackingId=$ttsTrackingId (localMsgId=$messageId), elapsed: ${elapsedTime}ms")
                    isGeneratingTts = false
                    ttsGenerationFailed = true
                    userClickedRecently = false
                    ttsGenerationStartTime = 0L
                }
            }

            // 如果TTS生成完成且之前失败过，重置失败状态
            if (!managerTtsState && ttsGenerationFailed && userClickedRecently) {
                // 用户重新点击后，重置失败状态
                ttsGenerationFailed = false
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

            if (isCurrentMessage) {
                // 更准确的状态判断
                val wasPlaying = isPlaying
                val wasLoading = isLoading

                // 更新播放状态
                isPlaying = state == PlaybackState.PLAYING
                hasError = state == PlaybackState.ERROR

                // 更新loading状态
                when (state) {
                    PlaybackState.BUFFERING -> {
                        isLoading = true
                    }

                    PlaybackState.PLAYING,
                    PlaybackState.READY,
                    PlaybackState.ENDED,
                    PlaybackState.ERROR -> {
                        isLoading = false
                    }

                    else -> {
                        // 保持当前loading状态
                    }
                }

                // 当播放开始时，清除TTS生成状态和用户点击标志
                if (state == PlaybackState.PLAYING) {
                    isGeneratingTts = false
                    userClickedRecently = false

                    // 开场白播放开始时立即标记为已播放
                    if (messageId.contains("_assistant_")) {
                        audioInfo.agentId?.let { agentId ->
                            OpeningPlayState.openingPlayedAsync(agentId)
                        }
                    }
                }
                // 只有在播放状态真正改变时才调用回调
                if (wasPlaying != isPlaying) {
                    onPlayStateChange?.invoke(isPlaying)
                }
            } else {
                // 非当前消息时，立即停止显示播放状态
                // 当有其他消息开始播放时，当前消息应该立即停止显示播放状态
                val wasPlaying = isPlaying
                val wasLoading = isLoading

                // 立即重置播放状态
                isPlaying = false
                hasError = false
                isLoading = false

                // 如果从播放状态变为非当前消息，调用回调
                if (wasPlaying || wasLoading) {
                    onPlayStateChange?.invoke(false)
                }
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
    LaunchedEffect(autoPlay, messageId) {

        if (autoPlay && !isPlaying && !hasError && !(audioInfo.agentId.isNullOrEmpty())) {
            // 增加延迟，确保组件完全初始化和UI渲染稳定
            // 开场白消息需要等待queryMsgs完成，所以延迟时间稍长一些
            delay(500)

            // 再次检查状态，确保条件仍然满足
            if (!isPlaying && !hasError) {
                audioManager.playMessageVoice(
                    messageId = messageId, // 使用localMsgId用于播放状态管理
                    audioUrl = audioInfo.url,
                    agentId = audioInfo.agentId,
                    autoPlay = true,
                    isManualClick = false, // 自动播放
                    onTtsGenerated = onTtsGenerated,
                    onTtsFailed = { error ->
                        LogUtils.e("音频LOG测试 Auto play TTS generation failed: $error (Agent: ${audioInfo.agentName})")
                        ttsGenerationFailed = true
                        isLoading = false
                    },
                    serverMessageId = serverMessageId, // 传递服务器端ID用于TTS生成
                    agentName = audioInfo.agentName, // 传递Agent名称用于日志分析
                )
            } else {
                LogUtils.d("音频LOG测试 VoicePlayer auto play conditions no longer met after delay: autoPlay=$autoPlay, isPlaying=$isPlaying, hasError=$hasError")
            }
        } else {
            LogUtils.w("音频LOG测试 VoicePlayer auto play conditions not met: autoPlay=$autoPlay, isPlaying=$isPlaying, hasError=$hasError, agentId='${audioInfo.agentId}'")
        }
    }

    ChatVoicePlayer(
        modifier = modifier,
        isPlaying = isPlaying,
        isLoading = isLoading || isGeneratingTts,
        hasError = hasError,
        duration = duration,
        isGeneratingTts = isGeneratingTts,
        ttsGenerationFailed = ttsGenerationFailed,
        onPlayPause = {
            val currentAudioInfo = audioManager.getCurrentAudioInfo()

            // 如果正在生成TTS且不是失败状态，则阻止点击
            if (isGeneratingTts && !ttsGenerationFailed) {
                LogUtils.i("音频LOG测试 Click ignored due to TTS generation in progress")
                return@ChatVoicePlayer
            }

            val isCurrentMessage = currentAudioInfo?.messageId == messageId

            if (isPlaying) {
                // 暂停播放
                audioManager.pausePlayback()
            } else if (isCurrentMessage) {
                // 恢复播放（当前消息已加载但未播放）
                audioManager.resumePlayback()
            } else {
                // 重置失败状态（如果之前失败过）
                if (ttsGenerationFailed) {
                    ttsGenerationFailed = false
                }

                // 设置用户点击标志，保护loading状态不被过早重置
                userClickedRecently = true

                // 立即显示loading状态
                if (audioInfo.url.isEmpty()) {
                    // 立即设置TTS生成状态为true，显示loading
                    isGeneratingTts = true
                } else {
                    // 立即设置loading状态为true
                    isLoading = true
                }

                audioManager.playMessageVoice(
                    messageId = messageId, // 使用localMsgId用于播放状态管理
                    audioUrl = audioInfo.url,
                    agentId = audioInfo.agentId ?: "",
                    autoPlay = true, // 手动点击时也需要播放
                    isManualClick = true, // 标记为手动点击
                    onTtsGenerated = { generatedUrl ->
                        // TTS生成成功，继续播放
                        onTtsGenerated?.invoke(generatedUrl)
                    },
                    onTtsFailed = { error ->
                        // TTS生成失败，显示错误状态
                        LogUtils.e("音频LOG测试 TTS generation failed: $error")
                        ttsGenerationFailed = true
                    },
                    serverMessageId = serverMessageId, // 传递服务器端ID用于TTS生成
                    agentName = audioInfo.agentName, // 传递Agent名称用于日志分析
                    forceRegenerateTts = ttsGenerationFailed, // 如果之前失败过，强制重新生成
                )
            }
        },
    )
}

/** 紧凑型语音播放器 */
@Composable
private fun ChatVoicePlayer(
    isPlaying: Boolean,
    isLoading: Boolean,
    hasError: Boolean,
    duration: Long,
    isGeneratingTts: Boolean = false,
    ttsGenerationFailed: Boolean = false,
    onPlayPause: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier =
            modifier
                .clip(RoundedCornerShape(topEnd = 10.dp, topStart = 10.dp, bottomEnd = 10.dp))
                .background(Color(0xFF44354F))
                .clickable { onPlayPause() }
                .padding(horizontal = 8.dp, vertical = 2.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.Center,
    ) {
        // 播放按钮
        Box(modifier = Modifier.size(16.dp), contentAlignment = Alignment.Center) {
            when {
                // 优先显示错误状态
                hasError -> {
                    Icon(
                        painter = painterResource(R.drawable.ic_warning_voice),
                        contentDescription = "Error",
                        tint = Color.White,
                        modifier = Modifier.size(16.dp),
                    )
                }

                // 显示TTS生成失败状态（⚠️图标）
                ttsGenerationFailed -> {
                    Icon(
                        painter = painterResource(R.drawable.ic_warning_voice),
                        contentDescription = "TTS Failed",
                        tint = Color.White,
                        modifier = Modifier.size(16.dp),
                    )
                }

                // 显示loading状态：TTS生成中或音频加载中
                isGeneratingTts || isLoading -> {
                    CircularProgressIndicator(
                        modifier = Modifier.size(12.dp),
                        strokeWidth = 1.dp,
                        color = Color.White,
                    )
                }

                // 正常播放状态
                else -> {
                    Icon(
                        imageVector =
                            ImageVector.vectorResource(
                                if (isPlaying) R.drawable.ic_pause_voice
                                else R.drawable.ic_play_voice
                            ),
                        contentDescription = if (isPlaying) "Pause" else "Play",
                        tint = Color.White,
                        modifier = Modifier.size(16.dp),
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
                lineHeight = 12.sp,
            )
        } else if (ttsGenerationFailed) {
            Text(text = "Failed to play", color = Color.White, fontSize = 12.sp, lineHeight = 12.sp)
        }
    }
}
