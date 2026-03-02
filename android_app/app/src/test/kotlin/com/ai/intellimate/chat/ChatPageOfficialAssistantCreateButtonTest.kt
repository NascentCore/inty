package com.ai.intellimate.chat

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ChatPageOfficialAssistantCreateButtonTest {
    @Test
    fun `should show create button when official assistant and keyboard hidden`() {
        val shouldShow =
            shouldDisplayOfficialAssistantCreateButton(
                isOfficialAssistantChat = true,
                isKeyboardVisible = false,
            )

        assertTrue(shouldShow)
    }

    @Test
    fun `should hide create button when keyboard visible`() {
        val shouldShow =
            shouldDisplayOfficialAssistantCreateButton(
                isOfficialAssistantChat = true,
                isKeyboardVisible = true,
            )

        assertFalse(shouldShow)
    }

    @Test
    fun `should hide create button when not official assistant`() {
        val shouldShow =
            shouldDisplayOfficialAssistantCreateButton(
                isOfficialAssistantChat = false,
                isKeyboardVisible = false,
            )

        assertFalse(shouldShow)
    }
}
