package com.ai.intellimate.call.data.bean

import ai.sxwl.android.data.http.IntyErrorCode
import androidx.annotation.Keep
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

@Keep
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
    @SerialName("session_id") val sessionId: String? = null,
    @SerialName("voice_session_id") val voiceSessionId: String? = null,
    val id: String? = null,
    @SerialName("session_info") val sessionInfo: SessionInfo? = null,
) {
    val errorEnum: IntyErrorCode?
        get() =
            runCatching { errorCode?.let { IntyErrorCode.valueOf(it) } ?: IntyErrorCode.UNKNOWN }
                .getOrNull()

    val typeEnum: CallType
        get() = runCatching { CallType.valueOf(type.uppercase()) }.getOrDefault(CallType.UNKNOW)

    val statusEnum: CallStatus?
        get() = runCatching { status?.let { CallStatus.valueOf(it.uppercase()) } }.getOrNull()

    /** 解析并返回可用于关联文本消息与录音文件的 session id。 */
    fun resolveVoiceSessionId(): String? {
        val directCandidates =
            listOf(
                voiceSessionId,
                sessionId,
                sessionInfo?.voiceSessionId,
                sessionInfo?.sessionId,
                sessionInfo?.id,
                id,
            )
        directCandidates.firstOrNull { !it.isNullOrBlank() }?.let { return it }

        // 兼容后端把 session 信息塞进 data 字段（JSON 字符串）
        if (data.isBlank()) return null
        val payloadRaw = data.trim()
        if (!payloadRaw.startsWith("{")) return null
        val payload =
            runCatching { Json.parseToJsonElement(payloadRaw).jsonObject }
                .getOrNull()
                ?: return null
        return listOf("voice_session_id", "session_id", "id")
            .firstNotNullOfOrNull { key ->
                payload[key]?.jsonPrimitive?.contentOrNull?.takeIf { it.isNotBlank() }
            }
            ?: run {
                val sessionInfoObject =
                    runCatching { payload["session_info"]?.jsonObject }.getOrNull()
                        ?: return@run null
                listOf("voice_session_id", "session_id", "id")
                    .firstNotNullOfOrNull { key ->
                        sessionInfoObject[key]
                            ?.jsonPrimitive
                            ?.contentOrNull
                            ?.takeIf { it.isNotBlank() }
                    }
            }
    }

    @Keep
    @Serializable
    data class Reason(
        val code: Int,
        @SerialName("error_code") val errorCode: IntyErrorCode,
        val message: String = "",
    )

    @Keep
    @Serializable
    data class SessionInfo(
        val id: String? = null,
        @SerialName("session_id") val sessionId: String? = null,
        @SerialName("voice_session_id") val voiceSessionId: String? = null,
    )
}

/** 消息类型 */
@Serializable
enum class CallType {
    /** 发送Base64编码的16kHz PCM音频 */
    @SerialName("audio") AUDIO,

    /** 文本输入 */
    @SerialName("text") TEXT,

    /** 用户活动开始（用于打断/提示） */
    @SerialName("activity_start") ACTIVITY_START,

    /** 用户活动结束（用于打断/提示） */
    @SerialName("activity_end") ACTIVITY_END,

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
    UNKNOW,
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
    @SerialName("disconnected") DISCONNECTED,
}
