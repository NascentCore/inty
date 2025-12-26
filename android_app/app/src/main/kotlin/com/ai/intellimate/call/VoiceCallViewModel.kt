package com.ai.intellimate.call

import ai.sxwl.android.common.base.BaseVM
import ai.sxwl.android.utils.LogUtils
import android.util.Base64
import androidx.lifecycle.viewModelScope
import com.ai.intellimate.audio.PlaybackState
import com.ai.intellimate.audio.RecordingState
import com.ai.intellimate.call.data.AICallRepository
import com.ai.intellimate.call.data.ConnectionState
import com.ai.intellimate.call.data.bean.CallType
import com.ai.intellimate.call.uistate.VoiceCallUiState
import com.ai.intellimate.ui.UiConfigs
import com.ai.intellimate.xb.helper.AgentStore
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.flow.launchIn
import kotlinx.coroutines.flow.onEach
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/** 语音通话状态 */
data class VoiceCallState(
    val isCallActive: Boolean = false,
    val connectionState: ConnectionState = ConnectionState.DISCONNECTED,
    val recordingState: RecordingState = RecordingState.IDLE,
    val playbackState: PlaybackState = PlaybackState.IDLE,
    val error: String? = null,
    val hasPermission: Boolean = false,
)

/** 语音通话ViewModel 管理语音通话的状态和业务逻辑 */
class VoiceCallViewModel() : BaseVM() {

    // 数据源
    private val repository: AICallRepository = AICallRepository()

    // UI状态
    private val _uiState = MutableStateFlow(VoiceCallUiState())
    val uiState = _uiState.asStateFlow()

    // 接收音频数据，ui只管接收到音频数据后播放
    private val _audioResponseChannel = Channel<ByteArray>()
    val audioResponse = _audioResponseChannel.receiveAsFlow()

    // 音频发送队列，确保按顺序发送 - 使用有界Channel避免内存溢出
    private val _audioSendQueue =
        Channel<ByteArray>(
            capacity = UiConfigs.VoiceCall.MAX_SEND_QUEUE_SIZE,
            onBufferOverflow = kotlinx.coroutines.channels.BufferOverflow.DROP_OLDEST,
        )
    private var sendQueueJob: kotlinx.coroutines.Job? = null

    // 发送队列大小计数器（近似值，用于监控）
    private var sendQueueSize = 0

    // 日志节流：记录上次打印警告的时间
    private var lastWarningLogTime = 0L
    private val warningLogInterval = 5000L // 5秒内最多打印一次警告

    init {
        // 启动队列消费协程
        sendQueueJob =
            viewModelScope.launch(Dispatchers.IO) {
                for (audioData in _audioSendQueue) {
                    try {
                        sendQueueSize = maxOf(0, sendQueueSize - 1) // 减少计数器
                        repository.sendVoice(audioData)
                    } catch (e: Exception) {
                        LogUtils.e("发送音频数据失败: ${e.message}")
                    }
                }
            }

        // 监听连接状态变化并同步到uiState
        repository
            .getConnectionState()
            .onEach { connectionState ->
                _uiState.update { it.copy(connectionState = connectionState) }
            }
            .launchIn(viewModelScope)
    }

    fun startCalling(agentId: String) {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                _uiState.update { it.copy(agent = AgentStore.getAgent(agentId)) }
                repository.call(agentId).collect { packet ->
                    when (packet.type) {
                        CallType.AUDIO_RESPONSE -> {
                            // 将packet.data从base64转化为音频数据并通过_audioResponseChannel发送
                            try {
                                val audioData = Base64.decode(packet.data, Base64.NO_WRAP)
                                _audioResponseChannel.send(audioData)
                            } catch (e: Exception) {
                                LogUtils.e("Base64解码音频数据失败: ${e.message}")
                            }
                        }
                        CallType.END -> {
                            stopCalling()
                        }
                        CallType.ERROR -> {
                            // 处理错误消息
                            LogUtils.e("收到错误消息: ${packet.data}")
                            _uiState.update { it.copy(connectionState = ConnectionState.ERROR) }
                        }
                        CallType.STATUS -> {
                            try {
                                // val callStatus = CallStatus.valueOf(packet.data.uppercase())
                                _uiState.update { it.copy(callState = packet.status) }
                            } catch (e: Exception) {
                                LogUtils.e("解析通话状态失败: ${packet.data}, ${e.message}")
                            }
                        }
                        else -> {}
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("连接语音通话失败: ${e.message}")
                _uiState.update { it.copy(connectionState = ConnectionState.ERROR) }
            }
        }
    }

    fun sendVoice(data: ByteArray) {
        // 通过队列缓存并按顺序发送，以避免同时发送多个音频数据而出现混乱
        viewModelScope.launch {
            try {
                // 使用send()让DROP_OLDEST策略生效：当队列满时自动丢弃最旧的数据
                // 这对于实时语音通话是合理的，因为旧数据已经过时
                _audioSendQueue.send(data)

                // 增加计数器并监控队列大小（带节流）
                sendQueueSize++
                val queueUsage = sendQueueSize.toFloat() / UiConfigs.VoiceCall.MAX_SEND_QUEUE_SIZE
                val currentTime = System.currentTimeMillis()
                if (
                    queueUsage >= UiConfigs.VoiceCall.QUEUE_WARNING_THRESHOLD &&
                        (currentTime - lastWarningLogTime) >= warningLogInterval
                ) {
                    LogUtils.w(
                        "发送队列使用率较高: ${(queueUsage * 100).toInt()}% (约${sendQueueSize}/${UiConfigs.VoiceCall.MAX_SEND_QUEUE_SIZE})"
                    )
                    lastWarningLogTime = currentTime
                }
            } catch (e: Exception) {
                LogUtils.e("添加音频数据到发送队列失败: ${e.message}")
            }
        }
    }

    private fun stopCalling() {
        viewModelScope.launch(Dispatchers.IO) { repository.closeCall() }
    }

    override fun onCleared() {
        super.onCleared()
        stopCalling()
        // 关闭队列和通道
        sendQueueJob?.cancel()
        sendQueueJob = null
        _audioSendQueue.close()
        _audioResponseChannel.close()
    }
}
