package com.ai.inty.audio

import android.content.Context
import com.inty.utils.log.EasyLog
import com.inty.utils.storage.IntySetting
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * Agent语音服务
 * 负责管理Agent开场白和消息的语音播放
 */
class AgentVoiceService private constructor(
    private val context: Context
) {
    
    companion object {
        @Volatile
        private var INSTANCE: AgentVoiceService? = null
        
        fun getInstance(context: Context): AgentVoiceService {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: AgentVoiceService(context.applicationContext).also { INSTANCE = it }
            }
        }
    }
    
    private val audioManager = AudioPlaybackManager.getInstance(context)
    private val scope = CoroutineScope(Dispatchers.Main)
    
    // 状态管理
    private val _isPlayingOpening = MutableStateFlow(false)
    val isPlayingOpening: StateFlow<Boolean> = _isPlayingOpening.asStateFlow()
    
    private val _currentPlayingAgent = MutableStateFlow<String?>(null)
    val currentPlayingAgent: StateFlow<String?> = _currentPlayingAgent.asStateFlow()
    
    // 播放任务管理
    private var openingPlayJob: Job? = null
    
    /**
     * 播放Agent开场白
     * @param agentId Agent ID
     * @param openingText 开场白文本
     * @param autoPlay 是否自动播放
     */
    fun playAgentOpening(
        agentId: String,
        openingText: String,
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
        
        // 生成开场白语音URL（临时使用测试URL）
        val openingAudioInfo = generateOpeningAudioInfo(agentId, openingText)
        
        EasyLog.log("Playing agent opening for agent: $agentId")
        
        _isPlayingOpening.value = true
        _currentPlayingAgent.value = agentId
        
        // 播放开场白
        audioManager.playAudio(openingAudioInfo, autoPlay = true)
        
        // 监听播放状态
        openingPlayJob = scope.launch {
            // 等待播放开始
            delay(100)
            
            // 监听播放结束
            while (_isPlayingOpening.value) {
                val playbackState = audioManager.playbackState.value
                val currentAudioInfo = audioManager.getCurrentAudioInfo()
                
                if (playbackState == PlaybackState.ENDED || 
                    playbackState == PlaybackState.ERROR ||
                    currentAudioInfo?.agentId != agentId) {
                    break
                }
                
                delay(500) // 每500ms检查一次
            }
            
            // 播放结束，清理状态
            _isPlayingOpening.value = false
            _currentPlayingAgent.value = null
            EasyLog.log("Agent opening playback finished for agent: $agentId")
        }
    }
    
    /**
     * 播放消息语音
     * @param messageId 消息ID
     * @param messageText 消息文本
     * @param agentId Agent ID
     * @param autoPlay 是否自动播放
     */
    fun playMessageVoice(
        messageId: String,
        messageText: String,
        agentId: String,
        autoPlay: Boolean = false
    ) {
        // 检查是否启用自动播放
        if (!autoPlay || !IntySetting.isAutoPlayAudio()) {
            EasyLog.log("Auto play audio is disabled, skipping message voice playback")
            return
        }
        
        // 如果正在播放开场白，先停止
        if (_isPlayingOpening.value) {
            EasyLog.log("Stopping opening playback to play message voice")
            stopCurrentOpening()
        }
        
        // 生成消息语音URL（临时使用测试URL）
        val messageAudioInfo = generateMessageAudioInfo(messageId, messageText, agentId)
        
        EasyLog.log("Playing message voice for message: $messageId")
        
        // 播放消息语音
        audioManager.playAudio(messageAudioInfo, autoPlay = true)
    }
    
    /**
     * 停止当前开场白播放
     */
    fun stopCurrentOpening() {
        if (_isPlayingOpening.value) {
            EasyLog.log("Stopping current opening playback")
            audioManager.stopPlayback()
            _isPlayingOpening.value = false
            _currentPlayingAgent.value = null
            openingPlayJob?.cancel()
        }
    }
    
    /**
     * 停止所有语音播放
     */
    fun stopAllPlayback() {
        EasyLog.log("Stopping all voice playback")
        audioManager.stopPlayback()
        _isPlayingOpening.value = false
        _currentPlayingAgent.value = null
        openingPlayJob?.cancel()
    }
    
    /**
     * 暂停语音播放
     */
    fun pausePlayback() {
        EasyLog.log("Pausing voice playback")
        audioManager.pausePlayback()
    }
    
    /**
     * 重置播放状态（页面切换时调用）
     */
    fun resetForPageChange() {
        EasyLog.log("Resetting voice playback for page change")
        audioManager.resetForPageChange()
    }
    
    /**
     * 生成开场白音频信息
     * 临时实现：使用测试URL，后续需要对接服务端API
     */
    private fun generateOpeningAudioInfo(agentId: String, openingText: String): AudioInfo {
        // TODO: 对接服务端API生成开场白语音
        // 临时使用测试URL，后续将使用openingText生成真实语音
        EasyLog.log("Generating opening audio for agent: $agentId, text: ${openingText.take(50)}...")
        return AudioInfo(
            url = "http://demo.fengxianqi.com/audio/static/opus.opus", // 固定测试URL
            title = "开场白",
            artist = "AI助手",
            messageId = "opening_$agentId",
            agentId = agentId
        )
    }
    
    /**
     * 生成消息音频信息
     * 临时实现：使用测试URL，后续需要对接服务端API
     */
    private fun generateMessageAudioInfo(
        messageId: String,
        messageText: String,
        agentId: String
    ): AudioInfo {
        // TODO: 对接服务端API生成消息语音
        // 临时使用测试URL，后续将使用messageText生成真实语音
        EasyLog.log("Generating message audio for message: $messageId, text: ${messageText.take(50)}...")
        return AudioInfo(
            url = "http://demo.fengxianqi.com/audio/static/opus.opus", // 固定测试URL
            title = "语音消息",
            artist = "AI助手",
            messageId = messageId,
            agentId = agentId
        )
    }
    
    /**
     * 检查是否正在播放指定Agent的语音
     */
    fun isPlayingAgentVoice(agentId: String): Boolean {
        return _currentPlayingAgent.value == agentId && 
               (audioManager.isPlaying() || _isPlayingOpening.value)
    }
    
    /**
     * 获取当前播放状态
     */
    fun getCurrentPlaybackState(): PlaybackState {
        return audioManager.playbackState.value
    }
    
    /**
     * 释放资源
     */
    fun release() {
        EasyLog.log("Releasing AgentVoiceService")
        stopAllPlayback()
        openingPlayJob?.cancel()
    }
}
