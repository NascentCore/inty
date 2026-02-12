package com.ai.intellimate.call

/**
 * 语音通话返回结果。
 *
 * 使用场景：
 * - 语音通话结束后返回到聊天页；
 * - 将会话级信息（sessionId）与本地录音路径一起传回；
 * - 可选携带 turn 级录音 JSON，供聊天页按 turn 精确关联回放按钮。
 */
data class VoiceCallResult(
    val messageCount: Int,
    val voiceSessionId: String?,
    val recordingPath: String?,
    val recordingDurationMs: Long,
    val turnRecordingsJson: String? = null,
)

/** 语音通话中某一轮的录音条目（用于通话页返回聊天页时传递）。 */
data class VoiceCallTurnRecordingResult(
    val voiceTurnId: String,
    val recordingPath: String,
    val recordingDurationMs: Long,
)

/** 语音通话按轮录音的返回载荷。 */
data class VoiceCallTurnRecordingResultPayload(
    val entries: List<VoiceCallTurnRecordingResult> = emptyList(),
)
