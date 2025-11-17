package com.ai.intellimate.utils

import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class AvatarManagerTest {

    @Before
    fun setUp() {
        AvatarManager.clearAllAvatarData()
    }

    @After
    fun tearDown() {
        AvatarManager.clearAllAvatarData()
    }

    @Test
    fun setGeneratedAvatarUrl_clearsMultiImageState() {
        AvatarManager.setGeneratedAvatarUrls(listOf("multi-1", "multi-2"))
        AvatarManager.setSelectedImageIndex(1)

        AvatarManager.setGeneratedAvatarUrl("single-avatar")

        assertEquals("single-avatar", AvatarManager.getCurrentAvatarUrl())
        assertTrue(AvatarManager.getCurrentAvatarUrls().isEmpty())
        assertEquals(0, AvatarManager.getSelectedImageIndex())
    }

    @Test
    fun setGenerationPrompt_setsGeneratingFlagAndClearsPreviousError() {
        AvatarManager.setGenerationError("previous error")

        AvatarManager.setGenerationPrompt("describe avatar like ...")

        assertTrue(AvatarManager.isGenerating())
        assertEquals("describe avatar like ...", AvatarManager.getGenerationPrompt())
        assertNull(AvatarManager.getGenerationError())
    }

    @Test
    fun getGenerationError_returnsOnceAndClearsState() {
        AvatarManager.setGenerationError("network failure")

        assertEquals("network failure", AvatarManager.getGenerationError())
        assertNull(AvatarManager.getGenerationError())
    }

    @Test
    fun clearAllAvatarData_resetsEveryField() {
        AvatarManager.setGeneratedAvatarUrls(listOf("url-1", "url-2"))
        AvatarManager.setSelectedImageIndex(1)
        AvatarManager.setGenerationPrompt("prompt")
        AvatarManager.setGenerationError("error")

        AvatarManager.clearAllAvatarData()

        assertNull(AvatarManager.getCurrentAvatarUrl())
        assertTrue(AvatarManager.getCurrentAvatarUrls().isEmpty())
        assertEquals(0, AvatarManager.getSelectedImageIndex())
        assertFalse(AvatarManager.isGenerating())
        assertEquals("", AvatarManager.getGenerationPrompt())
        assertNull(AvatarManager.getGenerationError())
    }
}
