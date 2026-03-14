package com.ai.intellimate.chat.ui

import ai.sxwl.android.data.api.model.TextToSpeechVoiceOption
import org.junit.Assert.assertEquals
import org.junit.Test

class ChatVoiceGenderFilterTest {
    @Test
    fun `female iMate keeps only female voices`() {
        val voices =
            listOf(
                TextToSpeechVoiceOption(voiceId = "google/puck", name = "Puck", gender = "male"),
                TextToSpeechVoiceOption(
                    voiceId = "google/zephyr",
                    name = "Zephyr",
                    gender = "female",
                ),
                TextToSpeechVoiceOption(voiceId = "google/kore", name = "Kore", gender = "FEMALE"),
            )

        val filtered = filterChatVoiceOptionsByAgentGender(voices, agentGender = "Female")

        assertEquals(listOf("google/zephyr", "google/kore"), filtered.map { it.voiceId })
    }

    @Test
    fun `male iMate keeps only male voices`() {
        val voices =
            listOf(
                TextToSpeechVoiceOption(
                    voiceId = "google/charon",
                    name = "Charon",
                    gender = "MALE",
                ),
                TextToSpeechVoiceOption(
                    voiceId = "google/aoede",
                    name = "Aoede",
                    gender = "female",
                ),
                TextToSpeechVoiceOption(voiceId = "google/unknown", name = "Unknown", gender = null),
            )

        val filtered = filterChatVoiceOptionsByAgentGender(voices, agentGender = "male")

        assertEquals(listOf("google/charon"), filtered.map { it.voiceId })
    }

    @Test
    fun `unknown iMate gender keeps all voices`() {
        val voices =
            listOf(
                TextToSpeechVoiceOption(voiceId = "google/puck", name = "Puck", gender = "male"),
                TextToSpeechVoiceOption(
                    voiceId = "google/zephyr",
                    name = "Zephyr",
                    gender = "female",
                ),
            )

        val filtered = filterChatVoiceOptionsByAgentGender(voices, agentGender = "NON_BINARY")

        assertEquals(voices.map { it.voiceId }, filtered.map { it.voiceId })
    }
}
