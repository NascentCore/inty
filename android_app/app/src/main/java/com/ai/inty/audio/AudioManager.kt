package com.ai.inty.audio

import android.content.Context
import com.inty.utils.log.EasyLog
import com.inty.utils.storage.IntySetting
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
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

    // 业务状态管理
    private val _isPlayingOpening = MutableStateFlow(false)
    val isPlayingOpening: StateFlow<Boolean> = _isPlayingOpening.asStateFlow()

    private val _currentPlayingAgent = MutableStateFlow<String?>(null)
    val currentPlayingAgent: StateFlow<String?> = _currentPlayingAgent.asStateFlow()

    // 播放状态代理
    val playbackState: StateFlow<PlaybackState> = playbackManager.playbackState
    val currentPosition: StateFlow<Long> = playbackManager.currentPosition
    val duration: StateFlow<Long> = playbackManager.duration
    val isLoading: StateFlow<Boolean> = playbackManager.isLoading
    val error: StateFlow<String?> = playbackManager.error

    /**
     * 播放Agent开场白
     */
    fun playAgentOpening(
        agentId: String,
        audioUrl: String,
        autoPlay: Boolean = true
    ) {
        // 检查是否启用自动播放
        if (!autoPlay || !IntySetting.isAutoPlayAudio()) {
            EasyLog.log("Auto play audio is disabled, skipping opening playback")
            return
        }

        // 检查是否正在播放其他Agent的开场白
        if (_isPlayingOpening.value && _currentPlayingAgent.value != agentId) {
            EasyLog.log("Another agent opening is playing, stopping current playback")
            stopCurrentOpening()
        }

        val audioInfo = AudioInfo(
            url = audioUrl,
            title = "opening",
            artist = "AI",
            messageId = "opening_$agentId",
            agentId = agentId
        )

        EasyLog.log("Playing agent opening for agent: $agentId")

        _isPlayingOpening.value = true
        _currentPlayingAgent.value = agentId

        // 播放开场白
        playbackManager.playAudio(audioInfo, autoPlay = true)

        // 监听播放结束
        scope.launch {
            while (_isPlayingOpening.value) {
                val state = playbackManager.playbackState.value
                val currentAudioInfo = playbackManager.getCurrentAudioInfo()

                if (state == PlaybackState.ENDED ||
                    state == PlaybackState.ERROR ||
                    currentAudioInfo?.agentId != agentId
                ) {
                    break
                }

                kotlinx.coroutines.delay(500)
            }

            // 播放结束，清理状态
            _isPlayingOpening.value = false
            _currentPlayingAgent.value = null
            EasyLog.log("Agent opening playback finished for agent: $agentId")
        }
    }

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
        onTtsGenerated: ((String) -> Unit)? = null
    ) {
        // 检查是否启用自动播放（只有在自动播放且用户禁用了自动播放时才跳过）
        // 手动点击时不受自动播放设置影响
        if (autoPlay && !isManualClick && !IntySetting.isAutoPlayAudio()) {
            EasyLog.log("Auto play audio is disabled, skipping message voice playback")
            return
        }

        // 如果正在播放开场白，先停止
        if (_isPlayingOpening.value) {
            EasyLog.log("Stopping opening playback to play message voice")
            stopCurrentOpening()
        }

        // 如果audioUrl为空，生成TTS
        if (audioUrl.isNullOrEmpty()) {
            EasyLog.log("Audio URL is empty, generating TTS for message: $messageId")
            ttsManager.generateMessageVoice(
                messageId = messageId,
                agentId = agentId,
                onSuccess = { generatedUrl ->
                    EasyLog.log("TTS generated successfully: $generatedUrl")
                    onTtsGenerated?.invoke(generatedUrl)
                    // 使用生成的URL播放
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
     * 停止当前开场白播放
     */
    fun stopCurrentOpening() {
        if (_isPlayingOpening.value) {
            EasyLog.log("Stopping current opening playback")
            playbackManager.stopPlayback()
            _isPlayingOpening.value = false
            _currentPlayingAgent.value = null
        }
    }

    /**
     * 停止所有语音播放
     */
    fun stopAllPlayback() {
        EasyLog.log("Stopping all voice playback")
        playbackManager.stopPlayback()
        _isPlayingOpening.value = false
        _currentPlayingAgent.value = null
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
        _isPlayingOpening.value = false
        _currentPlayingAgent.value = null
    }

    /**
     * 检查是否正在播放指定Agent的语音
     */
    fun isPlayingAgentVoice(agentId: String): Boolean {
        return _currentPlayingAgent.value == agentId &&
                (playbackManager.isPlaying() || _isPlayingOpening.value)
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