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
import com.ai.intellimate.call.data.bean.CallStatus
import com.ai.intellimate.call.data.bean.CallType
import com.ai.intellimate.call.uistate.VoiceCallUiState
import com.ai.intellimate.ui.UiConfigs
import com.ai.intellimate.utils.NetworkErrorHandler
import com.architecture.httplib.utils.MoshiUtils
import java.util.ArrayDeque
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
    private var activeFallbackTurnId: String? = null
    private var fallbackTurnCounter = 0
    private var lastStatusForTurnStatsLog: CallStatus? = null
    private val turnIdAliasMap = linkedMapOf<String, String>()
    private val pendingFallbackTurnIds = ArrayDeque<String>()
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
                        if (_uiState.value.connectionState != ConnectionState.CONNECTED) {
                            continue
                        }
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
        activeFallbackTurnId = null
        fallbackTurnCounter = 0
        voiceTurnId = null
        lastStatusForTurnStatsLog = null
        turnIdAliasMap.clear()
        pendingFallbackTurnIds.clear()
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
                            packet.resolveVoiceTurnId()?.let {
                                applyResolvedServerTurnId(it, source = "audio_response")
                            }
                            // 将packet.data从base64转化为音频数据并通过_audioResponseChannel发送
                            try {
                                val audioData = Base64.decode(packet.data, Base64.NO_WRAP)
                                recordingCollector.appendPcmData(audioData)
                                val resolvedTurnId = resolveTurnIdForIncomingAudio(packet)
                                if (resolvedTurnId != null) {
                                    turnRecordingCollector.appendPcmData(resolvedTurnId, audioData)
                                } else {
                                    LogUtils.w(
                                        "voice_turn_unresolved_on_audio: bytes=${audioData.size}, sessionId=$voiceSessionId"
                                    )
                                }
                                _audioResponseChannel.send(audioData)
                            } catch (e: Exception) {
                                LogUtils.e("Base64解码音频数据失败: ${e.message}")
                            }
                        }

                        CallType.END -> {
                            packet.resolveVoiceSessionId()?.let(::updateVoiceSessionId)
                            packet.resolveVoiceTurnId()?.let {
                                applyResolvedServerTurnId(it, source = "end")
                            }
                            activeFallbackTurnId = null
                            voiceTurnId = null
                            lastStatusForTurnStatsLog = null
                            logTurnCollectorSnapshot("voice_turn_on_end")
                            stopCalling()
                        }

                        CallType.ERROR -> {
                            packet.resolveVoiceSessionId()?.let(::updateVoiceSessionId)
                            packet.resolveVoiceTurnId()?.let {
                                applyResolvedServerTurnId(it, source = "error")
                            }
                            activeFallbackTurnId = null
                            voiceTurnId = null
                            lastStatusForTurnStatsLog = null
                            logTurnCollectorSnapshot("voice_turn_on_error")
                            // 处理错误消息
                            LogUtils.e("收到错误消息: ${packet.message}")
                            _uiState.update { it.copy(connectionState = ConnectionState.ERROR) }
                            packet.errorEnum?.let {
                                _error.trySend(it to packet.errorCode.orEmpty())
                            }
                        }

                        CallType.STATUS -> {
                            packet.resolveVoiceSessionId()?.let(::updateVoiceSessionId)
                            val resolvedTurnId =
                                packet.resolveVoiceTurnId()?.trim()?.takeIf { it.isNotBlank() }
                            if (resolvedTurnId != null) {
                                applyResolvedServerTurnId(
                                    resolvedTurnId,
                                    source = "status",
                                    allowPendingAlias = true,
                                )
                            }
                            packet.statusEnum?.let { status ->
                                if (lastStatusForTurnStatsLog != status) {
                                    LogUtils.i(
                                        "voice_turn_status_transition: from=${lastStatusForTurnStatsLog?.name}, to=${status.name}, voiceTurnId=${voiceTurnId.orEmpty()}, fallbackTurn=${activeFallbackTurnId.orEmpty()}"
                                    )
                                    logTurnCollectorSnapshot("voice_turn_status_${status.name.lowercase()}")
                                    lastStatusForTurnStatsLog = status
                                }
                                when (status) {
                                    CallStatus.SPEAKING -> {
                                        if (
                                            resolvedTurnId == null &&
                                                activeFallbackTurnId.isNullOrBlank() &&
                                                voiceTurnId.isNullOrBlank()
                                        ) {
                                            val fallbackTurnId = createFallbackTurnId()
                                            activeFallbackTurnId = fallbackTurnId
                                            updateVoiceTurnId(fallbackTurnId)
                                            LogUtils.i(
                                                "voice_turn_fallback_created: turnId=$fallbackTurnId, sessionId=$voiceSessionId"
                                            )
                                        }
                                    }

                                    CallStatus.LISTENING,
                                    CallStatus.DISCONNECTED,
                                    CallStatus.ERROR -> {
                                        if (!voiceTurnId.isNullOrBlank() || !activeFallbackTurnId.isNullOrBlank()) {
                                            LogUtils.i(
                                                "voice_turn_closed_on_status: status=${status.name}, closingTurn=${voiceTurnId.orEmpty()}, fallback=${activeFallbackTurnId.orEmpty()}"
                                            )
                                        }
                                        activeFallbackTurnId?.let(::markFallbackTurnPendingForAlias)
                                        activeFallbackTurnId = null
                                        voiceTurnId = null
                                    }

                                    else -> {}
                                }
                                _uiState.update { it.copy(callState = status) }
                            }
                        }

                        CallType.SESSION_INFO -> {
                            packet.resolveVoiceSessionId()?.let(::updateVoiceSessionId)
                            packet.resolveVoiceTurnId()?.let {
                                applyResolvedServerTurnId(it, source = "session_info")
                            }
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
                            packet.resolveVoiceTurnId()?.let {
                                applyResolvedServerTurnId(it, source = "transcript")
                            }
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
        logTurnCollectorSnapshot("voice_turn_before_finalize")
        val recordingOutput = recordingCollector.finalizeAndExport(resolvedSessionId)
        val turnRecordingOutputs = turnRecordingCollector.finalizeAllAndExport(resolvedSessionId)
        stopCalling()
        val turnRecordingsJson =
            turnRecordingOutputs
                .map {
                    val exportedTurnId = resolveExportTurnId(it.voiceTurnId)
                    VoiceCallTurnRecordingResult(
                        voiceTurnId = exportedTurnId,
                        recordingPath = it.filePath,
                        recordingDurationMs = it.durationMs,
                    )
                }
                .takeIf { it.isNotEmpty() }
                ?.let { MoshiUtils.toJson(VoiceCallTurnRecordingResultPayload(entries = it)) }
                ?.takeIf { it.isNotBlank() }
        if (turnIdAliasMap.isNotEmpty()) {
            LogUtils.i(
                "voice_turn_alias_summary: sessionId=$resolvedSessionId, aliasCount=${turnIdAliasMap.size}, aliases=${turnIdAliasMap.entries.joinToString(",") { "${it.key}->${it.value}" }}"
            )
        }
        return VoiceCallResult(
                messageCount = messageCount,
                voiceSessionId = resolvedSessionId,
                recordingPath = recordingOutput?.filePath,
                recordingDurationMs = recordingOutput?.durationMs ?: 0L,
                turnRecordingsJson = turnRecordingsJson,
            )
            .also {
                finalCallResult = it
                LogUtils.i(
                    "voice_turn_finish_summary: sessionId=$resolvedSessionId, messageCount=$messageCount, exportedTurns=${turnRecordingOutputs.size}, exportedTurnIds=${turnRecordingOutputs.joinToString(",") { output -> resolveExportTurnId(output.voiceTurnId) }}"
                )
            }
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

    private fun resolveTurnIdForIncomingAudio(packet: com.ai.intellimate.call.data.bean.CallPacket): String? {
        val packetTurnId = packet.resolveVoiceTurnId()?.trim()?.takeIf { it.isNotBlank() }
        if (packetTurnId != null) {
            val activeFallback = activeFallbackTurnId?.trim()?.takeIf { it.isNotBlank() }
            if (activeFallback != null) {
                bindFallbackTurnAlias(activeFallback, packetTurnId, source = "audio_append")
                updateVoiceTurnId(activeFallback)
                return activeFallback
            }
            updateVoiceTurnId(packetTurnId)
            return packetTurnId
        }
        activeFallbackTurnId?.let { fallbackTurnId ->
            updateVoiceTurnId(fallbackTurnId)
            return fallbackTurnId
        }
        val currentTurnId = voiceTurnId?.trim().orEmpty()
        if (currentTurnId.isNotBlank()) {
            return currentTurnId
        }
        val generatedTurnId = createFallbackTurnId()
        activeFallbackTurnId = generatedTurnId
        updateVoiceTurnId(generatedTurnId)
        return generatedTurnId
    }

    private fun createFallbackTurnId(): String {
        fallbackTurnCounter += 1
        return "local_turn_${fallbackTurnCounter}_${System.nanoTime()}"
    }

    private fun resolveExportTurnId(rawTurnId: String): String {
        val normalized = rawTurnId.trim()
        if (normalized.isBlank()) return rawTurnId
        return turnIdAliasMap[normalized]?.trim()?.takeIf { it.isNotBlank() } ?: normalized
    }

    private fun applyResolvedServerTurnId(
        candidate: String,
        source: String,
        allowPendingAlias: Boolean = false,
    ) {
        val normalized = candidate.trim()
        if (normalized.isBlank()) return
        val activeFallback = activeFallbackTurnId?.trim()?.takeIf { it.isNotBlank() }
        if (activeFallback != null) {
            bindFallbackTurnAlias(activeFallback, normalized, source)
            updateVoiceTurnId(activeFallback)
            return
        }
        if (allowPendingAlias) {
            val pendingFallback = consumePendingFallbackTurnForAlias()
            if (pendingFallback != null) {
                bindFallbackTurnAlias(pendingFallback, normalized, "$source-pending")
            }
        }
        updateVoiceTurnId(normalized)
    }

    private fun markFallbackTurnPendingForAlias(localTurnId: String) {
        val normalized = localTurnId.trim()
        if (normalized.isBlank()) return
        if (!normalized.startsWith("local_turn_")) return
        if (turnIdAliasMap.containsKey(normalized)) return
        if (pendingFallbackTurnIds.contains(normalized)) return
        pendingFallbackTurnIds.addLast(normalized)
        LogUtils.i(
            "voice_turn_alias_pending: localTurn=$normalized, pendingCount=${pendingFallbackTurnIds.size}"
        )
    }

    private fun consumePendingFallbackTurnForAlias(): String? {
        while (pendingFallbackTurnIds.isNotEmpty()) {
            val candidate = pendingFallbackTurnIds.removeFirst().trim()
            if (candidate.isBlank()) continue
            if (turnIdAliasMap.containsKey(candidate)) continue
            return candidate
        }
        return null
    }

    private fun bindFallbackTurnAlias(localTurnId: String, serverTurnId: String, source: String) {
        val normalizedLocal = localTurnId.trim()
        val normalizedServer = serverTurnId.trim()
        if (normalizedLocal.isBlank() || normalizedServer.isBlank()) return
        if (normalizedLocal == normalizedServer) return
        if (turnIdAliasMap[normalizedLocal] == normalizedServer) return
        turnIdAliasMap[normalizedLocal] = normalizedServer
        pendingFallbackTurnIds.remove(normalizedLocal)
        LogUtils.i(
            "voice_turn_alias_bound: source=$source, localTurn=$normalizedLocal, serverTurn=$normalizedServer, pendingCount=${pendingFallbackTurnIds.size}"
        )
    }

    private fun logTurnCollectorSnapshot(prefix: String) {
        val stats = turnRecordingCollector.snapshotStats()
        LogUtils.i(
            "$prefix: turns=${stats.turnCount}, chunks=${stats.totalChunkCount}, bytes=${stats.totalBytes}, details=${stats.turns.joinToString(";") { stat -> "${stat.turnId}[chunks=${stat.chunkCount},bytes=${stat.totalBytes}]" }}"
        )
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
