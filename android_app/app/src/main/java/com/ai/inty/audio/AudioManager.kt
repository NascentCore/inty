package com.ai.inty.audio

import android.content.Context
import com.inty.utils.log.EasyLog
import com.inty.utils.storage.IntySetting
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

/**
 * 统一音频管理器
 * 协调各个音频子模块，提供统一的音频服务接口
 */
class AudioManager private constructor(
    private val context: Context,
    private val scope: CoroutineScope
) {

    companion object {
        @Volatile
        private var INSTANCE: AudioManager? = null

        fun getInstance(context: Context, scope: CoroutineScope): AudioManager {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: AudioManager(context.applicationContext, scope).also { INSTANCE = it }
            }
        }
    }

    // 子模块
    private val playbackManager = AudioPlaybackManager.getInstance(context)
    private val cacheManager = AudioCacheManager.getInstance(context)
    private val ttsManager = TtsManager.getInstance(context, scope)

    // 业务状态管理（开场白状态管理已移至消息级别处理）

    // 播放状态代理
    val playbackState: StateFlow<PlaybackState> = playbackManager.playbackState
    val currentPosition: StateFlow<Long> = playbackManager.currentPosition
    val duration: StateFlow<Long> = playbackManager.duration
    val isLoading: StateFlow<Boolean> = playbackManager.isLoading
    val error: StateFlow<String?> = playbackManager.error


    /**
     * 播放消息语音
     * 如果audioUrl为空，会自动生成TTS
     */
    fun playMessageVoice(
        messageId: String,
        audioUrl: String?,
        agentId: String,
        autoPlay: Boolean = false,
        isManualClick: Boolean = false,
        onTtsGenerated: ((String) -> Unit)? = null,
        serverMessageId: String? = null // 服务器端消息ID，用于TTS生成
    ) {
        EasyLog.log("=== AudioManager.playMessageVoice ===")
        EasyLog.log("messageId: $messageId")
        EasyLog.log("audioUrl: $audioUrl")
        EasyLog.log("agentId: $agentId")
        EasyLog.log("autoPlay: $autoPlay")
        EasyLog.log("isManualClick: $isManualClick")
        EasyLog.log("IntySetting.isAutoPlayAudio(): ${IntySetting.isAutoPlayAudio()}")
        
        // 检查是否启用自动播放
        // 手动点击时不受自动播放设置影响
        // 开场白消息的自动播放不受用户设置影响（业务逻辑必需）
        if (autoPlay && !isManualClick && !IntySetting.isAutoPlayAudio()) {
            // 检查是否是开场白消息，如果是则允许播放
            // 开场白消息的localMsgId通常包含_assistant_标识
            val isOpeningMessage = messageId.contains("_assistant_")
            if (!isOpeningMessage) {
                EasyLog.log("Auto play audio is disabled, skipping message voice playback")
                return
            } else {
                EasyLog.log("Opening message detected (messageId contains '_assistant_'), allowing auto play despite user setting")
            }
        }

        // 开场白状态管理已移至消息级别，不再需要特殊处理

        // 如果audioUrl为空，生成TTS
        if (audioUrl.isNullOrEmpty()) {
            val ttsMessageId = serverMessageId ?: messageId
            EasyLog.log("Audio URL is empty, generating TTS for message: $messageId (serverId: $ttsMessageId)")
            ttsManager.generateMessageVoice(
                messageId = ttsMessageId, // 使用服务器端ID进行TTS生成
                agentId = agentId,
                onSuccess = { generatedUrl ->
                    EasyLog.log("TTS generated successfully: $generatedUrl")
                    onTtsGenerated?.invoke(generatedUrl)
                    // 使用生成的URL播放
                    EasyLog.log("Playing TTS generated audio: messageId=$messageId, generatedUrl=$generatedUrl, autoPlay=$autoPlay")
                    playMessageWithUrl(messageId, generatedUrl, agentId, autoPlay)
                },
                onError = { error ->
                    EasyLog.log("TTS generation failed: $error", EasyLog.ERROR)
                }
            )
        } else {
            // 直接播放
            playMessageWithUrl(messageId, audioUrl, agentId, autoPlay)
        }
    }

    /**
     * 使用指定URL播放消息
     */
    private fun playMessageWithUrl(
        messageId: String,
        audioUrl: String,
        agentId: String,
        autoPlay: Boolean
    ) {
        val audioInfo = AudioInfo(
            url = audioUrl,
            title = "msg voice",
            artist = "AI",
            messageId = messageId,
            agentId = agentId
        )

        EasyLog.log("Playing message voice for message: $messageId")
        playbackManager.playAudio(audioInfo, autoPlay = autoPlay)
    }


    /**
     * 停止所有语音播放
     */
    fun stopAllPlayback() {
        EasyLog.log("Stopping all voice playback")
        playbackManager.stopPlayback()
    }

    /**
     * 暂停语音播放
     */
    fun pausePlayback() {
        EasyLog.log("Pausing voice playback")
        playbackManager.pausePlayback()
    }

    /**
     * 恢复语音播放
     */
    fun resumePlayback() {
        EasyLog.log("Resuming voice playback")
        playbackManager.resumePlayback()
    }

    /**
     * 重置播放状态（页面切换时调用）
     */
    fun resetForPageChange() {
        EasyLog.log("Resetting voice playback for page change")
        playbackManager.resetForPageChange()
    }

    /**
     * 检查是否正在播放指定Agent的语音
     */
    fun isPlayingAgentVoice(agentId: String): Boolean {
        val currentAudioInfo = playbackManager.getCurrentAudioInfo()
        return currentAudioInfo?.agentId == agentId && playbackManager.isPlaying()
    }

    /**
     * 获取当前播放信息
     */
    fun getCurrentAudioInfo(): AudioInfo? = playbackManager.getCurrentAudioInfo()

    /**
     * 是否正在播放
     */
    fun isPlaying(): Boolean = playbackManager.isPlaying()

    /**
     * 获取播放进度百分比
     */
    fun getProgress(): Float = playbackManager.getProgress()

    /**
     * 跳转到指定位置
     */
    fun seekTo(positionMs: Long) = playbackManager.seekTo(positionMs)

    /**
     * 检查是否正在生成指定消息的TTS
     */
    fun isGeneratingTtsForMessage(messageId: String): Boolean {
        return ttsManager.isGeneratingForMessage(messageId)
    }

    /**
     * 预加载音频
     */
    fun preloadAudio(url: String) {
        scope.launch {
            cacheManager.preloadAudio(url)
        }
    }

    /**
     * 清理缓存
     */
    fun clearCache() {
        cacheManager.clearCache()
    }

    /**
     * 释放资源
     */
    fun release() {
        EasyLog.log("Releasing AudioManager")
        stopAllPlayback()
        playbackManager.release()
        ttsManager.cancelAllGenerations()
    }
}
