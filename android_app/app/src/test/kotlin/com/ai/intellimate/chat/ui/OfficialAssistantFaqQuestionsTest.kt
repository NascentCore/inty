package com.ai.intellimate.chat.ui

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class OfficialAssistantFaqQuestionsTest {

    @Test
    fun `official assistant faq list should contain up to max items`() {
        val items = officialAssistantFaqItems()
        assertTrue(items.isNotEmpty())
        assertTrue(items.size <= OFFICIAL_ASSISTANT_FAQ_MAX_ITEMS)
        assertEquals(OFFICIAL_ASSISTANT_FAQ_MAX_ITEMS, items.size)
    }

    @Test
    fun `official assistant faq list should have unique title and question resources`() {
        val items = officialAssistantFaqItems()
        assertEquals(items.size, items.map { it.titleResId }.distinct().size)
        assertEquals(items.size, items.map { it.questionResId }.distinct().size)
    }
}
