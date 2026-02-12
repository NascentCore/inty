package com.ai.intellimate.call

/**
 * 语音通话返回结果。
 *
 * 使用场景：
 * - 语音通话结束后返回到聊天页；
 * - 将会话级信息（sessionId）与本地录音路径一起传回，供聊天页按 session 精确关联回放按钮。
 */
data class VoiceCallResult(
    val messageCount: Int,
    val voiceSessionId: String?,
    val recordingPath: String?,
    val recordingDurationMs: Long,
)
