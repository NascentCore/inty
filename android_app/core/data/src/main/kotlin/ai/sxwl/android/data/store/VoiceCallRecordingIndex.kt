package ai.sxwl.android.data.store

/**
 * 语音录音索引（UI 读取模型）。
 *
 * 设计目标：
 * - 将 turn/session 两层映射集中管理，避免在 ViewModel/UI 重复拼接 key；
 * - 提供统一 resolve 接口：turn 优先、session 兜底。
 */
data class VoiceCallRecordingIndex(
    val bySession: Map<String, VoiceCallRecordingEntry> = emptyMap(),
    val byTurn: Map<String, VoiceCallRecordingEntry> = emptyMap(),
) {
    fun resolve(voiceSessionId: String?, voiceTurnId: String?): VoiceCallRecordingEntry? {
        val sessionId = voiceSessionId?.trim().orEmpty()
        if (sessionId.isBlank()) return null
        val turnId = voiceTurnId?.trim().orEmpty()
        val fromTurn =
            if (turnId.isBlank()) {
                null
            } else {
                byTurn[buildTurnKey(sessionId, turnId)]
            }
        return fromTurn ?: bySession[sessionId]
    }

    companion object {
        fun empty(): VoiceCallRecordingIndex = VoiceCallRecordingIndex()

        fun fromEntries(entries: List<VoiceCallRecordingEntry>): VoiceCallRecordingIndex {
            val normalizedEntries =
                entries
                    .asSequence()
                    .map { it.normalizeForIndex() }
                    .filter { it.voiceSessionId.isNotBlank() }
                    .toList()

            val sessionMap =
                normalizedEntries
                    .groupBy { it.voiceSessionId }
                    .mapValues { (_, list) ->
                        list.firstOrNull { it.voiceTurnId.isNullOrBlank() } ?: list.first()
                    }
            val turnMap =
                normalizedEntries
                    .asSequence()
                    .filter { !it.voiceTurnId.isNullOrBlank() }
                    .associateBy { buildTurnKey(it.voiceSessionId, it.voiceTurnId.orEmpty()) }

            return VoiceCallRecordingIndex(bySession = sessionMap, byTurn = turnMap)
        }

        fun buildTurnKey(voiceSessionId: String, voiceTurnId: String): String {
            return "${voiceSessionId.trim()}::${voiceTurnId.trim()}"
        }
    }
}

private fun VoiceCallRecordingEntry.normalizeForIndex(): VoiceCallRecordingEntry {
    return copy(
        voiceSessionId = voiceSessionId.trim(),
        voiceTurnId = voiceTurnId?.trim()?.takeIf { it.isNotBlank() },
    )
}
