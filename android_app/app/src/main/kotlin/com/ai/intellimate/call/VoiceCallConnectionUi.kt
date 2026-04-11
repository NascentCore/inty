package com.ai.intellimate.call

import ai.sxwl.android.inty.voicecall.VoiceCallConnectionState
import com.ai.intellimate.R

enum class VoiceCallConnectionUi(val textRes: Int?) {
    DISCONNECTED(null),
    CONNECTING(R.string.voice_call_connecting),
    CONNECTED(R.string.voice_call_connected),
    DISCONNECTING(null),
    ERROR(R.string.voice_call_error),
}

fun VoiceCallConnectionState.toUi(): VoiceCallConnectionUi =
    when (this) {
        VoiceCallConnectionState.DISCONNECTED -> VoiceCallConnectionUi.DISCONNECTED
        VoiceCallConnectionState.CONNECTING -> VoiceCallConnectionUi.CONNECTING
        VoiceCallConnectionState.CONNECTED -> VoiceCallConnectionUi.CONNECTED
        VoiceCallConnectionState.DISCONNECTING -> VoiceCallConnectionUi.DISCONNECTING
        VoiceCallConnectionState.ERROR -> VoiceCallConnectionUi.ERROR
    }
