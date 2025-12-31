package com.ai.intellimate.call.data.bean

import ai.sxwl.android.data.http.IntyErrorCode
import androidx.annotation.Keep
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Keep
@Serializable
data class CallPacket(
    val type: CallType,
    val data: String = "",
    val status: CallStatus? = null,
    val message: String? = null,
    @SerialName("error_code") val errorCode: IntyErrorCode? = null,
    @SerialName("sample_rate") val sampleRate: Int = 0,
    val text: String = "",
    @SerialName("is_final") val isFinal: Boolean = false,
    @SerialName("remaining_duration") val remainingDuration: Long = 0,
    @SerialName("agent_limit") val agentLimit: Int = 0,
    @SerialName("agent_count") val agentCount: Int = 0,
) {
    @Keep
    @Serializable
    data class Reason(
        val code: Int,
        @SerialName("error_code") val errorCode: IntyErrorCode,
        val message: String = "",
    )
}

/** 消息类型 */
@Serializable
enum class CallType {
    /** 发送Base64编码的16kHz PCM音频 */
    @SerialName("audio") AUDIO,

    /** 文本输入 */
    @SerialName("text") TEXT,

    /** 结束通话 */
    @SerialName("end") END,

    /** 回复的Base64编码的24kHz PCM音频 */
    @SerialName("audio_response") AUDIO_RESPONSE,

    /** 当前状态[CallStatus] */
    @SerialName("status") STATUS,

    /** 会话信息 */
    @SerialName("session_info") SESSION_INFO,

    /** 错误 */
    @SerialName("error") ERROR,
    @SerialName("user_transcript") USER_TRANSCRIPT,
    @SerialName("transcript") TRANSCRIPT,
}

/** 当前状态 */
@Serializable
enum class CallStatus {
    @SerialName("connecting") CONNECTING,
    @SerialName("connected") CONNECTED,
    @SerialName("speaking") SPEAKING,
    @SerialName("listening") LISTENING,
    @SerialName("error") ERROR,
    @SerialName("user_transcript") USER_TRANSCRIPT,
}
