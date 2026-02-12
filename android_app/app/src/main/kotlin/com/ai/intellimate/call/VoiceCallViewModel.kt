package com.ai.intellimate.call

import ai.sxwl.android.data.http.IntyErrorCode
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.Utils
import android.util.Base64
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ai.intellimate.call.data.AICallRepository
import com.ai.intellimate.call.data.ConnectionState
import com.ai.intellimate.call.data.VoiceCallRecordingCollector
import com.ai.intellimate.call.data.VoiceCallTurnRecordingCollector
import com.ai.intellimate.call.data.bean.CallType
import com.ai.intellimate.call.uistate.VoiceCallUiState
import com.ai.intellimate.ui.UiConfigs
import com.ai.intellimate.utils.NetworkErrorHandler
import com.architecture.httplib.utils.MoshiUtils
import kotlin.time.Duration.Companion.seconds
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
    private val fallbackVoiceSessionId = "local_${System.currentTimeMillis()}_${System.nanoTime()}"
    private var voiceSessionId: String = fallbackVoiceSessionId
    private var voiceTurnId: String? = null
    private val recordingCollector = VoiceCallRecordingCollector(Utils.getApp().filesDir)
    private val turnRecordingCollector = VoiceCallTurnRecordingCollector(Utils.getApp().filesDir)
    private var finalCallResult: VoiceCallResult? = null

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
                    _uiState.update { it.copy(connectionState = connectionState) }

                    if (connectionState == ConnectionState.CONNECTING) {
                        _error.trySend(null)
                    }
                }
                .collectLatest { state ->
                    if (state == ConnectionState.CONNECTED) {
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

    fun startCalling(agentId: String) {
        viewModelScope.launch(Dispatchers.IO) {
            repository.getAgentInfo(agentId).collect { result ->
                result.getOrNull()?.let { agent -> _uiState.update { it.copy(agent = agent) } }
            }
        }
        viewModelScope.launch(Dispatchers.IO) {
            repository
                .call(agentId)
                .catch { error ->
                    // #region agent log（上报 Crashlytics）
                    NetworkErrorHandler.reportTlsParseToCrashlyticsIfRelevant(
                        "C",
                        "VoiceCallViewModel.kt:call.catch",
                        error.message,
                    )
                    // #endregion
                    LogUtils.e("连接语音通话失败: ${error.message}")
                    _uiState.update { it.copy(connectionState = ConnectionState.ERROR) }
                }
                .collect { packet ->
                    when (packet.typeEnum) {
                        CallType.AUDIO_RESPONSE -> {
                            packet.resolveVoiceSessionId()?.let(::updateVoiceSessionId)
                            packet.resolveVoiceTurnId()?.let(::updateVoiceTurnId)
                            // 将packet.data从base64转化为音频数据并通过_audioResponseChannel发送
                            try {
                                val audioData = Base64.decode(packet.data, Base64.NO_WRAP)
                                recordingCollector.appendPcmData(audioData)
                                voiceTurnId?.let { turnRecordingCollector.appendPcmData(it, audioData) }
                                _audioResponseChannel.send(audioData)
                            } catch (e: Exception) {
                                LogUtils.e("Base64解码音频数据失败: ${e.message}")
                            }
                        }

                        CallType.END -> {
                            packet.resolveVoiceSessionId()?.let(::updateVoiceSessionId)
                            packet.resolveVoiceTurnId()?.let(::updateVoiceTurnId)
                            stopCalling()
                        }

                        CallType.ERROR -> {
                            packet.resolveVoiceSessionId()?.let(::updateVoiceSessionId)
                            packet.resolveVoiceTurnId()?.let(::updateVoiceTurnId)
                            // 处理错误消息
                            LogUtils.e("收到错误消息: ${packet.message}")
                            _uiState.update { it.copy(connectionState = ConnectionState.ERROR) }
                            packet.errorEnum?.let {
                                _error.trySend(it to packet.errorCode.orEmpty())
                            }
                        }

                        CallType.STATUS -> {
                            packet.resolveVoiceSessionId()?.let(::updateVoiceSessionId)
                            packet.resolveVoiceTurnId()?.let(::updateVoiceTurnId)
                            packet.statusEnum?.let { status ->
                                _uiState.update { it.copy(callState = status) }
                            }
                        }

                        CallType.SESSION_INFO -> {
                            packet.resolveVoiceSessionId()?.let(::updateVoiceSessionId)
                            packet.resolveVoiceTurnId()?.let(::updateVoiceTurnId)
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
                        CallType.USER_TRANSCRIPT -> {
                            packet.resolveVoiceSessionId()?.let(::updateVoiceSessionId)
                            packet.resolveVoiceTurnId()?.let(::updateVoiceTurnId)
                            messageCount++
                        }

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
        viewModelScope.launch(Dispatchers.IO) { repository.closeCall() }
    }

    /** 结束通话并生成返回结果（只会生成一次）。 */
    fun finishCall(): VoiceCallResult {
        finalCallResult?.let { return it }
        val resolvedSessionId = voiceSessionId.ifBlank { fallbackVoiceSessionId }
        val recordingOutput = recordingCollector.finalizeAndExport(resolvedSessionId)
        val turnRecordingOutputs = turnRecordingCollector.finalizeAllAndExport(resolvedSessionId)
        stopCalling()
        val turnRecordingsJson =
            turnRecordingOutputs
                .map {
                    VoiceCallTurnRecordingResult(
                        voiceTurnId = it.voiceTurnId,
                        recordingPath = it.filePath,
                        recordingDurationMs = it.durationMs,
                    )
                }
                .takeIf { it.isNotEmpty() }
                ?.let { MoshiUtils.toJson(VoiceCallTurnRecordingResultPayload(entries = it)) }
                ?.takeIf { it.isNotBlank() }
        return VoiceCallResult(
                messageCount = messageCount,
                voiceSessionId = resolvedSessionId,
                recordingPath = recordingOutput?.filePath,
                recordingDurationMs = recordingOutput?.durationMs ?: 0L,
                turnRecordingsJson = turnRecordingsJson,
            )
            .also { finalCallResult = it }
    }

    private fun updateVoiceSessionId(candidate: String) {
        val normalized = candidate.trim()
        if (normalized.isBlank()) return
        voiceSessionId = normalized
    }

    private fun updateVoiceTurnId(candidate: String) {
        val normalized = candidate.trim()
        if (normalized.isBlank()) return
        voiceTurnId = normalized
    }

    fun setMuted(isMuted: Boolean) {
        _uiState.update { it.copy(isMuted = isMuted) }
    }

    override fun onCleared() {
        super.onCleared()
        stopCalling()
        if (finalCallResult == null) {
            recordingCollector.discard()
            turnRecordingCollector.discard()
        }
        // 关闭队列和通道
        sendQueueJob?.cancel()
        sendQueueJob = null
        _audioSendQueue.close()
        _audioResponseChannel.close()
    }
}
