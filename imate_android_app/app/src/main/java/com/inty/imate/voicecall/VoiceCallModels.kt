package com.inty.imate.voicecall

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
enum class VoiceCallPacketType {
    @SerialName("audio") AUDIO,
    @SerialName("audio_response") AUDIO_RESPONSE,
    @SerialName("status") STATUS,
    @SerialName("error") ERROR,
    @SerialName("session_info") SESSION_INFO,
    @SerialName("transcript") TRANSCRIPT,
    @SerialName("user_transcript") USER_TRANSCRIPT,
    @SerialName("end") END,
    UNKNOWN,
}

@Serializable
data class VoiceCallPacket(
    val type: VoiceCallPacketType = VoiceCallPacketType.UNKNOWN,
    val data: String? = null,
    val status: String? = null,
    val message: String? = null,
    @SerialName("error_code") val errorCode: String? = null,
    @SerialName("remaining_duration") val remainingDuration: Int? = null,
)

enum class VoiceCallConnectionState {
    DISCONNECTED,
    CONNECTING,
    CONNECTED,
    ERROR,
}
