package com.ai.intellimate.call

import ai.sxwl.android.data.http.IntyErrorCode
import ai.sxwl.android.utils.LogUtils
import android.util.Base64
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import ai.sxwl.android.data.voicecall.errorEnum
import ai.sxwl.android.inty.voicecall.CallType
import ai.sxwl.android.inty.voicecall.VoiceCallConnectionState
import com.ai.intellimate.call.data.AICallRepository
import com.ai.intellimate.call.toUi
import com.ai.intellimate.call.uistate.VoiceCallUiState
import com.ai.intellimate.ui.UiConfigs
import com.ai.intellimate.utils.NetworkErrorHandler
import kotlin.time.Duration.Companion.seconds
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.flow.onEach
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/** 语音通话ViewModel 管理语音通话的状态和业务逻辑 */
class VoiceCallViewModel(private val repository: AICallRepository) : ViewModel() {
    // UI状态
    private val _uiState = MutableStateFlow(VoiceCallUiState())
    val uiState = _uiState.asStateFlow()
    private val _error = Channel<Pair<IntyErrorCode, String>?>()
    val error = _error.receiveAsFlow()

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
    var messageCount = 0

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
        viewModelScope.launch {
            repository
                .getConnectionState()
                .onEach { connectionState ->
                    _uiState.update { it.copy(connectionState = connectionState.toUi()) }

                    if (connectionState == VoiceCallConnectionState.CONNECTING) {
                        _error.trySend(null)
                    }
                }
                .collectLatest { state ->
                    if (state == VoiceCallConnectionState.CONNECTED) {
                        while (true) {
                            delay(1.seconds)

                            _uiState.update {
                                it.copy(
                                    time =
                                        it.time?.run {
                                            VoiceCallUiState.Time(
                                                duration = duration + 1,
                                                remaining = (remaining - 1).coerceAtLeast(0),
                                            )
                                        }
                                )
                            }
                        }
                    }
                }
        }
    }

    fun startCalling(
        agentId: String,
        speechLanguageCode: String? = null,
        responseLanguageName: String? = null,
    ) {
        viewModelScope.launch(Dispatchers.IO) {
            repository.getAgentInfo(agentId).collect { result ->
                result.getOrNull()?.let { agent -> _uiState.update { it.copy(agent = agent) } }
            }
        }
        viewModelScope.launch(Dispatchers.IO) {
            repository.call(agentId, speechLanguageCode, responseLanguageName)
                .catch { error ->
                    // #region agent log（上报 Crashlytics）
                    NetworkErrorHandler.reportTlsParseToCrashlyticsIfRelevant(
                        "C",
                        "VoiceCallViewModel.kt:call.catch",
                        error.message,
                    )
                    // #endregion
                    LogUtils.e("连接语音通话失败: ${error.message}")
                    _uiState.update { it.copy(connectionState = VoiceCallConnectionUi.ERROR) }
                }
                .collect { packet ->
                    when (packet.typeEnum) {
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
                            LogUtils.e("收到错误消息: ${packet.message}")
                            _uiState.update { it.copy(connectionState = VoiceCallConnectionUi.ERROR) }
                            packet.errorEnum?.let {
                                _error.trySend(it to packet.errorCode.orEmpty())
                            }
                        }

                        CallType.STATUS -> {
                            packet.statusEnum?.let { status ->
                                _uiState.update { it.copy(callState = status) }
                            }
                        }

                        CallType.SESSION_INFO -> {
                            _uiState.update {
                                it.copy(
                                    time =
                                        VoiceCallUiState.Time(
                                            duration = it.time?.duration ?: 0,
                                            remaining = packet.remainingDuration,
                                        )
                                )
                            }
                        }

                        CallType.TRANSCRIPT,
                        CallType.USER_TRANSCRIPT -> messageCount++

                        else -> {}
                    }
                }
        }
    }

    fun interruptSpeaking() {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                repository.sendActivityStart()
                repository.sendActivityEnd()
            } catch (e: Exception) {
                LogUtils.e("发送打断信号失败: ${e.message}")
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
        CoroutineScope(Dispatchers.IO).launch(Dispatchers.IO) { repository.closeCall() }
    }

    fun setMuted(isMuted: Boolean) {
        _uiState.update { it.copy(isMuted = isMuted) }
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
