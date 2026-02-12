package com.ai.intellimate.call.data.bean

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class CallPacketTurnIdTest {

    @Test
    fun `resolveVoiceTurnId returns top-level voice turn id first`() {
        val packet =
            CallPacket(
                type = "audio_response",
                voiceTurnId = "voice-turn-001",
                turnId = "turn-001",
                responseId = "resp-001",
            )

        assertEquals("voice-turn-001", packet.resolveVoiceTurnId())
    }

    @Test
    fun `resolveVoiceTurnId parses turn id from data json`() {
        val packet =
            CallPacket(
                type = "audio_response",
                data = """{"turn_info":{"turn_id":"turn-from-data"}}""",
            )

        assertEquals("turn-from-data", packet.resolveVoiceTurnId())
    }

    @Test
    fun `resolveVoiceTurnId returns null when packet has no turn id`() {
        val packet = CallPacket(type = "status", data = "not-json")

        assertNull(packet.resolveVoiceTurnId())
    }
}
