package com.ai.intellimate.call.data.bean

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
    @SerialName("sample_rate") val sampleRate: Int = 0,
    val text: String = "",
    @SerialName("is_final") val isFinal: Boolean = false,
)

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
