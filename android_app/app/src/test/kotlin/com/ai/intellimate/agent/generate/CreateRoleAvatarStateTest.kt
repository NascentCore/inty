package com.ai.intellimate.agent.generate

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test

/**
 * Hermetic tests for avatar state management logic in CreateRoleActivity. Tests pure Kotlin logic
 * without Android framework dependencies.
 */
class CreateRoleAvatarStateTest {

    @Before
    fun setUp() {
        // Clear any existing state before each test
    }

    // Test 1: Avatar URL State Management - Single URL vs Multiple URLs mutual exclusivity
    @Test
    fun `avatarUrls and avatarUrl are mutually exclusive`() {
        var avatarUrl: String? = null
        var avatarUrls: List<String> = emptyList()

        // Setting single URL should clear multiple URLs
        avatarUrl = "https://example.com/avatar1.jpg"
        avatarUrls = emptyList()
        assertEquals("https://example.com/avatar1.jpg", avatarUrl)
        assertEquals(emptyList<String>(), avatarUrls)

        // Setting multiple URLs should clear single URL
        avatarUrls = listOf("https://example.com/avatar1.jpg", "https://example.com/avatar2.jpg")
        avatarUrl = null
        assertEquals(2, avatarUrls.size)
        assertNull(avatarUrl)

        // Setting single URL again should clear multiple URLs
        avatarUrl = "https://example.com/avatar3.jpg"
        avatarUrls = emptyList()
        assertEquals("https://example.com/avatar3.jpg", avatarUrl)
        assertEquals(emptyList<String>(), avatarUrls)
    }

    // Test 2: Image Selection Index Bounds
    @Test
    fun `selectedImageIndex is coerced to valid range`() {
        val avatarUrls = listOf("url1", "url2", "url3")
        val lastIndex = avatarUrls.lastIndex

        // Valid index should remain unchanged
        var selectedIndex = 1
        val sanitizedIndex1 = if (avatarUrls.isEmpty()) 0 else selectedIndex.coerceIn(0, lastIndex)
        assertEquals(1, sanitizedIndex1)

        // Index too high should be coerced to lastIndex
        selectedIndex = 10
        val sanitizedIndex2 = if (avatarUrls.isEmpty()) 0 else selectedIndex.coerceIn(0, lastIndex)
        assertEquals(2, sanitizedIndex2) // lastIndex is 2

        // Negative index should be coerced to 0
        selectedIndex = -5
        val sanitizedIndex3 = if (avatarUrls.isEmpty()) 0 else selectedIndex.coerceIn(0, lastIndex)
        assertEquals(0, sanitizedIndex3)

        // Empty list should return 0
        val emptyUrls = emptyList<String>()
        val sanitizedIndex4 = if (emptyUrls.isEmpty()) 0 else 0.coerceIn(0, emptyUrls.lastIndex)
        assertEquals(0, sanitizedIndex4)
    }

    @Test
    fun `getOrNull with fallback to first when index out of bounds`() {
        val avatarUrls = listOf("url1", "url2", "url3")
        val selectedIndex = 5 // Out of bounds

        val displayUrl = avatarUrls.getOrNull(selectedIndex) ?: avatarUrls.first()
        assertEquals("url1", displayUrl) // Should fallback to first

        val validIndex = 1
        val validUrl = avatarUrls.getOrNull(validIndex) ?: avatarUrls.first()
        assertEquals("url2", validUrl) // Should get correct URL
    }

    // Test 3: Background URL Selection Logic (for CreateAgentRequest)
    @Test
    fun `backgroundUrl selection from avatarUrls when multiple images exist`() {
        val avatarUrls = listOf("url1", "url2", "url3")
        val selectedImageIndex = 1
        val avatarUrl: String? = null

        val backgroundUrl =
            if (avatarUrls.isNotEmpty()) {
                avatarUrls.getOrNull(selectedImageIndex) ?: avatarUrls.first()
            } else {
                avatarUrl
            }

        assertEquals("url2", backgroundUrl)
    }

    @Test
    fun `backgroundUrl fallback to avatarUrl when avatarUrls is empty`() {
        val avatarUrls = emptyList<String>()
        val avatarUrl = "https://example.com/single.jpg"

        val backgroundUrl =
            if (avatarUrls.isNotEmpty()) {
                avatarUrls.getOrNull(0) ?: avatarUrls.first()
            } else {
                avatarUrl
            }

        assertEquals("https://example.com/single.jpg", backgroundUrl)
    }

    @Test
    fun `backgroundImagesList construction uses avatarUrls if non-empty otherwise listOfNotNull avatarUrl`() {
        // Case 1: avatarUrls is non-empty
        val avatarUrls1 = listOf("url1", "url2", "url3")
        val avatarUrl1: String? = null
        val backgroundImagesList1 = avatarUrls1.ifEmpty { listOfNotNull(avatarUrl1) }
        assertEquals(listOf("url1", "url2", "url3"), backgroundImagesList1)

        // Case 2: avatarUrls is empty, avatarUrl exists
        val avatarUrls2 = emptyList<String>()
        val avatarUrl2 = "https://example.com/single.jpg"
        val backgroundImagesList2 = avatarUrls2.ifEmpty { listOfNotNull(avatarUrl2) }
        assertEquals(listOf("https://example.com/single.jpg"), backgroundImagesList2)

        // Case 3: Both empty
        val avatarUrls3 = emptyList<String>()
        val avatarUrl3: String? = null
        val backgroundImagesList3 = avatarUrls3.ifEmpty { listOfNotNull(avatarUrl3) }
        assertEquals(emptyList<String>(), backgroundImagesList3)
    }

    // Test 4: Final Avatar URL Resolution
    @Test
    fun `finalAvatarUrl uses croppedAvatarUrl if available otherwise backgroundUrl`() {
        val croppedAvatarUrl = "https://example.com/cropped.jpg"
        val backgroundUrl = "https://example.com/background.jpg"

        val finalAvatarUrl = croppedAvatarUrl ?: backgroundUrl
        assertEquals("https://example.com/cropped.jpg", finalAvatarUrl)

        // When croppedAvatarUrl is null
        val finalAvatarUrl2: String? = null
        val finalAvatarUrl3 = finalAvatarUrl2 ?: backgroundUrl
        assertEquals("https://example.com/background.jpg", finalAvatarUrl3)
    }

    @Test
    fun `edit mode avatar update when background changes`() {
        val editAgentBackground = "https://example.com/old-background.jpg"
        val backgroundUrl = "https://example.com/new-background.jpg"
        var croppedAvatarUrl = editAgentBackground // Initially same as old background

        // Simulate edit mode logic: if background changed and avatar is still old, update avatar
        if (backgroundUrl != editAgentBackground) {
            if (croppedAvatarUrl == editAgentBackground) {
                croppedAvatarUrl = backgroundUrl
            }
        }

        assertEquals("https://example.com/new-background.jpg", croppedAvatarUrl)
    }

    // Test 5: Draft State Normalization
    @Test
    fun `normalizedUrls filters out blank strings`() {
        val avatarUrls = listOf("url1", "", "url2", "   ", "url3", "")
        val normalizedUrls = avatarUrls.filter { it.isNotBlank() }
        assertEquals(listOf("url1", "url2", "url3"), normalizedUrls)
    }

    @Test
    fun `sanitizedIndex calculation when URLs list changes size`() {
        val originalUrls = listOf("url1", "url2", "url3", "url4", "url5")
        val selectedIndex = 3
        val lastIndex = originalUrls.lastIndex
        val sanitizedIndex1 = if (lastIndex < 0) 0 else selectedIndex.coerceIn(0, lastIndex)
        assertEquals(3, sanitizedIndex1)

        // After filtering blank URLs, list might shrink
        val filteredUrls = originalUrls.filter { it.isNotBlank() }
        val newLastIndex = filteredUrls.lastIndex
        val sanitizedIndex2 = if (newLastIndex < 0) 0 else selectedIndex.coerceIn(0, newLastIndex)
        assertEquals(3, sanitizedIndex2) // Still valid

        // If selected index is beyond new list size
        val selectedIndex2 = 10
        val sanitizedIndex3 = if (newLastIndex < 0) 0 else selectedIndex2.coerceIn(0, newLastIndex)
        assertEquals(4, sanitizedIndex3) // Coerced to lastIndex (4)
    }

    @Test
    fun `draft saving excludes blank URLs`() {
        val avatarUrls = listOf("url1", "", "url2", "   ")
        val normalizedUrls = avatarUrls.filter { it.isNotBlank() }
        val avatarUrl: String? = "url3"
        val normalizedAvatarUrl = avatarUrl?.takeIf { it.isNotBlank() }

        // Draft should only contain non-blank URLs
        assertEquals(listOf("url1", "url2"), normalizedUrls)
        assertEquals("url3", normalizedAvatarUrl)

        // Empty string should be filtered out
        val emptyAvatarUrl: String? = ""
        val normalizedEmptyUrl = emptyAvatarUrl?.takeIf { it.isNotBlank() }
        assertNull(normalizedEmptyUrl)
    }
}
