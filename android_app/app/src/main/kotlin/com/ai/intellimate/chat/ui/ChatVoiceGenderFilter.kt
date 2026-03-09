package com.ai.intellimate.chat.ui

import ai.sxwl.android.data.api.model.TextToSpeechVoiceOption
import java.util.Locale

private const val GENDER_MALE = "MALE"
private const val GENDER_FEMALE = "FEMALE"

internal fun filterChatVoiceOptionsByAgentGender(
    voices: List<TextToSpeechVoiceOption>,
    agentGender: String?,
): List<TextToSpeechVoiceOption> {
    val normalizedAgentGender = normalizeBinaryGender(agentGender) ?: return voices
    return voices.filter { normalizeBinaryGender(it.gender) == normalizedAgentGender }
}

private fun normalizeBinaryGender(rawGender: String?): String? {
    if (rawGender.isNullOrBlank()) return null
    return when (rawGender.trim().replace('-', '_').uppercase(Locale.ROOT)) {
        GENDER_MALE -> GENDER_MALE
        GENDER_FEMALE -> GENDER_FEMALE
        else -> null
    }
}
