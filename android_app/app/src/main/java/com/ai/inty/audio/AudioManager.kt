package com.ai.inty.audio

import android.content.Context
import com.inty.utils.log.EasyLog
import com.inty.utils.storage.IntySetting
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

/**
 * 统一音频管理器
 * 协调各个音频子模块，提供统一的音频服务接口
 */
class AudioManager private constructor(
    private val context: Context,
    private var scope: CoroutineScope
) {

    companion object {
        @Volatile
        private var INSTANCE: AudioManager? = null

        fun getInstance(context: Context, scope: CoroutineScope): AudioManager {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: AudioManager(context.applicationContext, scope).also { INSTANCE = it }
            }.also { instance ->
                // 更新Scope以确保协程能正常执行
                instance.scope = scope
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
        onTtsFailed: ((String) -> Unit)? = null,
        serverMessageId: String? = null, // 服务器端消息ID，用于TTS生成
        agentName: String? = null // Agent名称，用于日志分析
    ) {
        // 参数验证
        if (messageId.isEmpty()) {
            EasyLog.log("音频LOG测试 playMessageVoice failed: messageId is empty", EasyLog.ERROR)
            onTtsFailed?.invoke("消息ID不能为空")
            return
        }
        
        if (agentId.isEmpty()) {
            EasyLog.log("音频LOG测试 playMessageVoice failed: agentId is empty", EasyLog.ERROR)
            onTtsFailed?.invoke("Agent ID不能为空")
            return
        }
        
        EasyLog.log("音频LOG测试 === AudioManager.playMessageVoice START ===")
        EasyLog.log("音频LOG测试 Message ID: $messageId")
        EasyLog.log("音频LOG测试 Agent ID: $agentId")
        EasyLog.log("音频LOG测试 Audio URL: $audioUrl")
        EasyLog.log("音频LOG测试 Auto play: $autoPlay")
        EasyLog.log("音频LOG测试 Is manual click: $isManualClick")

        // 检查是否启用自动播放
        // 手动点击时不受自动播放设置影响
        // 开场白消息的自动播放不受用户设置影响（业务逻辑必需）
        if (autoPlay && !isManualClick && !IntySetting.isAutoPlayAudio()) {
            // 检查是否是开场白消息，如果是则允许播放
            // 开场白消息的localMsgId通常包含_assistant_标识
            val isOpeningMessage = messageId.contains("_assistant_")
            if (!isOpeningMessage) {
                EasyLog.log("音频LOG测试 Auto play audio is disabled, skipping message voice playback")
                return
            } else {
                EasyLog.log("音频LOG测试 Opening message detected (messageId contains '_assistant_'), allowing auto play despite user setting")
            }
        }

        // 开场白状态管理已移至消息级别，不再需要特殊处理

        // 如果audioUrl为空，生成TTS
        if (audioUrl.isNullOrEmpty()) {
            val ttsMessageId = serverMessageId ?: messageId
            EasyLog.log("音频LOG测试 Audio URL is empty, generating TTS for message: $messageId (serverId: $ttsMessageId)")
            ttsManager.generateMessageVoice(
                messageId = ttsMessageId, // 使用服务器端ID进行TTS生成
                agentId = agentId,
                onSuccess = { generatedUrl ->
                    EasyLog.log("音频LOG测试 TTS generated successfully: $generatedUrl")
                    onTtsGenerated?.invoke(generatedUrl)
                    // 使用生成的URL播放
                    EasyLog.log("音频LOG测试 Playing TTS generated audio: messageId=$messageId, generatedUrl=$generatedUrl, autoPlay=$autoPlay (Agent: $agentName)")
                    playMessageWithUrl(messageId, generatedUrl, agentId, autoPlay, agentName)
                },
                onError = { error ->
                    EasyLog.log("音频LOG测试 TTS generation failed: $error", EasyLog.ERROR)
                    onTtsFailed?.invoke(error)
                }
            )
        } else {
            // 直接播放
            playMessageWithUrl(messageId, audioUrl, agentId, autoPlay, agentName)
        }
    }

    /**
     * 使用指定URL播放消息
     */
    private fun playMessageWithUrl(
        messageId: String,
        audioUrl: String,
        agentId: String,
        autoPlay: Boolean,
        agentName: String? = null
    ) {
        val audioInfo = AudioInfo(
            url = audioUrl,
            title = "msg voice",
            artist = "AI",
            messageId = messageId,
            agentId = agentId,
            agentName = agentName
        )

        EasyLog.log("音频LOG测试 Playing message voice for message: $messageId (Agent: $agentName)")
        EasyLog.log("音频LOG测试 AudioInfo created: url=${audioInfo.url}, messageId=${audioInfo.messageId}, agentId=${audioInfo.agentId}, agentName=${audioInfo.agentName}")
        EasyLog.log("音频LOG测试 Scope is active: ${scope.isActive}")
        EasyLog.log("音频LOG测试 PlaybackManager instance: ${playbackManager.hashCode()}")
        
        // 检查Scope是否活跃，如果不活跃则直接调用playbackManager
        if (!scope.isActive) {
            EasyLog.log("音频LOG测试 Scope is not active, calling playbackManager directly on main thread")
            try {
                playbackManager.playAudio(audioInfo, autoPlay = autoPlay)
                EasyLog.log("音频LOG测试 Direct playbackManager.playAudio call completed")
            } catch (e: Exception) {
                EasyLog.log("音频LOG测试 Error in direct playbackManager.playAudio: ${e.message}", EasyLog.ERROR)
                e.printStackTrace()
            }
        } else {
            // 确保在主线程上调用ExoPlayer
            scope.launch {
                try {
                    EasyLog.log("音频LOG测试 Coroutine started, calling playbackManager.playAudio...")
                    playbackManager.playAudio(audioInfo, autoPlay = autoPlay)
                    EasyLog.log("音频LOG测试 playbackManager.playAudio call completed")
                } catch (e: Exception) {
                    EasyLog.log("音频LOG测试 Error in playbackManager.playAudio: ${e.message}", EasyLog.ERROR)
                    e.printStackTrace()
                }
            }
        }
    }


    /**
     * 停止所有语音播放
     */
    fun stopAllPlayback() {
        EasyLog.log("音频LOG测试 Stopping all voice playback")
        scope.launch {
            playbackManager.stopPlayback()
        }
    }

    /**
     * 暂停语音播放
     */
    fun pausePlayback() {
        EasyLog.log("音频LOG测试 === AudioManager.pausePlayback START ===")
        EasyLog.log("音频LOG测试 Scope is active: ${scope.isActive}")
        EasyLog.log("音频LOG测试 Current audio info: ${playbackManager.getCurrentAudioInfo()?.messageId}")
        EasyLog.log("音频LOG测试 Is playing: ${playbackManager.isPlaying()}")
        
        if (!scope.isActive) {
            EasyLog.log("音频LOG测试 Scope is not active, calling playbackManager directly")
            try {
                playbackManager.pausePlayback()
                EasyLog.log("音频LOG测试 Direct pausePlayback call completed")
            } catch (e: Exception) {
                EasyLog.log("音频LOG测试 Error in direct pausePlayback: ${e.message}", EasyLog.ERROR)
            }
        } else {
            scope.launch {
                try {
                    EasyLog.log("音频LOG测试 Calling playbackManager.pausePlayback in coroutine")
                    playbackManager.pausePlayback()
                    EasyLog.log("音频LOG测试 pausePlayback coroutine completed")
                } catch (e: Exception) {
                    EasyLog.log("音频LOG测试 Error in pausePlayback coroutine: ${e.message}", EasyLog.ERROR)
                }
            }
        }
        EasyLog.log("音频LOG测试 === AudioManager.pausePlayback END ===")
    }

    /**
     * 恢复语音播放
     */
    fun resumePlayback() {
        EasyLog.log("音频LOG测试 === AudioManager.resumePlayback START ===")
        EasyLog.log("音频LOG测试 Scope is active: ${scope.isActive}")
        EasyLog.log("音频LOG测试 Current audio info: ${playbackManager.getCurrentAudioInfo()?.messageId}")
        EasyLog.log("音频LOG测试 Is playing: ${playbackManager.isPlaying()}")
        
        if (!scope.isActive) {
            EasyLog.log("音频LOG测试 Scope is not active, calling playbackManager directly")
            try {
                playbackManager.resumePlayback()
                EasyLog.log("音频LOG测试 Direct resumePlayback call completed")
            } catch (e: Exception) {
                EasyLog.log("音频LOG测试 Error in direct resumePlayback: ${e.message}", EasyLog.ERROR)
            }
        } else {
            scope.launch {
                try {
                    EasyLog.log("音频LOG测试 Calling playbackManager.resumePlayback in coroutine")
                    playbackManager.resumePlayback()
                    EasyLog.log("音频LOG测试 resumePlayback coroutine completed")
                } catch (e: Exception) {
                    EasyLog.log("音频LOG测试 Error in resumePlayback coroutine: ${e.message}", EasyLog.ERROR)
                }
            }
        }
        EasyLog.log("音频LOG测试 === AudioManager.resumePlayback END ===")
    }

    /**
     * 重置播放状态（页面切换时调用）
     */
    fun resetForPageChange() {
        EasyLog.log("音频LOG测试 Resetting voice playback for page change")
        scope.launch {
            playbackManager.resetForPageChange()
        }
    }

    /**
     * 检查是否正在播放指定Agent的语音
     */
    fun isPlayingAgentVoice(agentId: String): Boolean {
        val currentAudioInfo = playbackManager.getCurrentAudioInfo()
        return currentAudioInfo?.agentId == agentId && playbackManager.isPlaying()
    }

    /**
     * 停止非当前Agent的音频播放
     * 用于页面切换时确保只播放当前Agent的音频
     */
    fun stopNonCurrentAgentPlayback(currentAgentId: String) {
        val currentAudioInfo = playbackManager.getCurrentAudioInfo()
        if (currentAudioInfo?.agentId != currentAgentId && playbackManager.isPlaying()) {
            EasyLog.log("音频LOG测试 Stopping non-current agent playback: current=${currentAudioInfo?.agentId}, target=$currentAgentId")
            scope.launch {
                playbackManager.stopPlayback()
            }
        }
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
        EasyLog.log("音频LOG测试 Releasing AudioManager")
        stopAllPlayback()
        playbackManager.release()
        ttsManager.cancelAllGenerations()
    }
}
