package ai.sxwl.demos.intyvoicecall.voicecall

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class CallPacket(
    val type: String,
    val data: String = "",
    val status: String? = null,
    val message: String? = null,
    @SerialName("error_code") val errorCode: String? = null,
    @SerialName("sample_rate") val sampleRate: Int = 0,
    val text: String = "",
    @SerialName("is_final") val isFinal: Boolean = false,
    @SerialName("remaining_duration") val remainingDuration: Long = 0,
    @SerialName("agent_limit") val agentLimit: Int = 0,
    @SerialName("agent_count") val agentCount: Int = 0,
) {
    val typeEnum: CallType
        get() = runCatching { CallType.valueOf(type.uppercase()) }.getOrDefault(CallType.UNKNOWN)
}

@Serializable
enum class CallType {
    @SerialName("audio") AUDIO,
    @SerialName("text") TEXT,
    @SerialName("activity_start") ACTIVITY_START,
    @SerialName("activity_end") ACTIVITY_END,
    @SerialName("end") END,
    @SerialName("audio_response") AUDIO_RESPONSE,
    @SerialName("status") STATUS,
    @SerialName("session_info") SESSION_INFO,
    @SerialName("error") ERROR,
    @SerialName("user_transcript") USER_TRANSCRIPT,
    @SerialName("transcript") TRANSCRIPT,
    UNKNOWN,
}
