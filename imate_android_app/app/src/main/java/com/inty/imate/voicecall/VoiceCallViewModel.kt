package com.inty.imate.voicecall

import android.util.Base64
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ai.core.utils.LogUtils
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

class VoiceCallViewModel : ViewModel() {
    private val client = VoiceCallClient()
    private val audio = VoiceCallAudio()

    private val _state = MutableStateFlow(VoiceCallConnectionState.DISCONNECTED)
    val state = _state.asStateFlow()

    private val _remainingSeconds = MutableStateFlow<Int?>(null)
    val remainingSeconds = _remainingSeconds.asStateFlow()

    private val _lastError = MutableStateFlow<String?>(null)
    val lastError = _lastError.asStateFlow()

    init {
        viewModelScope.launch {
            client.connectionState.collectLatest { _state.value = it }
        }
    }

    fun start(agentId: String) {
        if (_state.value == VoiceCallConnectionState.CONNECTED || agentId.isBlank()) return
        _lastError.value = null
        viewModelScope.launch {
            audio.startRecording(viewModelScope) { pcm -> client.sendAudioPcm16k(pcm) }
            client.packets(agentId).collect { packet ->
                when (packet.type) {
                    VoiceCallPacketType.AUDIO_RESPONSE -> {
                        val raw = packet.data ?: return@collect
                        val bytes = Base64.decode(raw, Base64.NO_WRAP)
                        audio.playPcm24k(bytes)
                    }
                    VoiceCallPacketType.SESSION_INFO -> {
                        _remainingSeconds.value = packet.remainingDuration
                    }
                    VoiceCallPacketType.ERROR -> {
                        _lastError.value = packet.message ?: packet.errorCode ?: "Voice call failed"
                        stop()
                    }
                    VoiceCallPacketType.END -> stop()
                    else -> Unit
                }
            }
        }
    }

    fun stop() {
        viewModelScope.launch {
            runCatching { client.end() }
                .onFailure { LogUtils.e("Voice call end failed: ${it.message}") }
            audio.stop()
            _state.value = VoiceCallConnectionState.DISCONNECTED
        }
    }

    override fun onCleared() {
        audio.stop()
        client.close()
        super.onCleared()
    }
}
