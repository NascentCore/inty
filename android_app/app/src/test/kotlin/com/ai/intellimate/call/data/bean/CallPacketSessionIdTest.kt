package com.ai.intellimate.call.data.bean

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class CallPacketSessionIdTest {

    @Test
    fun `resolveVoiceSessionId returns top-level voice session id first`() {
        val packet =
            CallPacket(
                type = "session_info",
                voiceSessionId = "voice-session-123",
                sessionId = "session-abc",
            )

        assertEquals("voice-session-123", packet.resolveVoiceSessionId())
    }

    @Test
    fun `resolveVoiceSessionId parses session id from data json`() {
        val packet =
            CallPacket(
                type = "session_info",
                data = """{"session_id":"session-from-data"}""",
            )

        assertEquals("session-from-data", packet.resolveVoiceSessionId())
    }

    @Test
    fun `resolveVoiceSessionId returns null when packet has no session id`() {
        val packet = CallPacket(type = "status", data = "not-json")

        assertNull(packet.resolveVoiceSessionId())
    }
}
