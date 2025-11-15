package com.ai.intellimate.utils

import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class AvatarManagerTest {

    @After
    fun tearDown() {
        AvatarManager.clearAllAvatarData()
    }

    @Test
    fun setGeneratedAvatarUrl_switchesToSingleMode() {
        AvatarManager.setGeneratedAvatarUrls(listOf("multi-1", "multi-2"))

        AvatarManager.setGeneratedAvatarUrl("single-url")

        assertEquals("single-url", AvatarManager.getCurrentAvatarUrl())
        assertTrue(AvatarManager.getCurrentAvatarUrls().isEmpty())
        assertEquals(0, AvatarManager.getSelectedImageIndex())
        assertFalse(AvatarManager.isGenerating())
    }

    @Test
    fun setGeneratedAvatarUrls_switchesToMultipleModeAndResetsState() {
        AvatarManager.setGeneratedAvatarUrl("single-url")
        AvatarManager.setSelectedImageIndex(1)

        val urls = listOf("multi-1", "multi-2", "multi-3")
        AvatarManager.setGeneratedAvatarUrls(urls)

        assertNull(AvatarManager.getCurrentAvatarUrl())
        assertEquals(urls, AvatarManager.getCurrentAvatarUrls())
        assertEquals(0, AvatarManager.getSelectedImageIndex())
        assertFalse(AvatarManager.isGenerating())
    }

    @Test
    fun generationPromptAndError_updateFlagsProperly() {
        AvatarManager.setGenerationPrompt("draw a smile")

        assertEquals("draw a smile", AvatarManager.getGenerationPrompt())
        assertTrue(AvatarManager.isGenerating())
        assertNull(AvatarManager.getGenerationError())

        AvatarManager.setGenerationError("quota exceeded")

        assertFalse(AvatarManager.isGenerating())
        assertEquals("quota exceeded", AvatarManager.getGenerationError())
        assertNull("error should auto clear after reading", AvatarManager.getGenerationError())
    }

    @Test
    fun clearAllAvatarData_resetsAllFields() {
        AvatarManager.setGeneratedAvatarUrl("single")
        AvatarManager.setGeneratedAvatarUrls(listOf("a", "b"))
        AvatarManager.setSelectedImageIndex(2)
        AvatarManager.setGenerationPrompt("prompt")
        AvatarManager.setGenerationError("error")

        AvatarManager.clearAllAvatarData()

        assertNull(AvatarManager.getCurrentAvatarUrl())
        assertTrue(AvatarManager.getCurrentAvatarUrls().isEmpty())
        assertEquals(0, AvatarManager.getSelectedImageIndex())
        assertEquals("", AvatarManager.getGenerationPrompt())
        assertFalse(AvatarManager.isGenerating())
        assertNull(AvatarManager.getGenerationError())
    }
}
