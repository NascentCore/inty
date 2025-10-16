package com.ai.inty.utils

import org.junit.Test
import org.junit.Assert.*

/**
 * 测试 getCdnImageUrl 函数的功能
 */
class CdnImageTest {

    @Test
    fun `getCdnImageUrl should return null when originUrl is null`() {
        // Given
        val originUrl: String? = null

        // When
        val result = getCdnImageUrl(originUrl)

        // Then
        assertNull(result)
    }

    @Test
    fun `getCdnImageUrl should return null when originUrl is empty`() {
        // Given
        val originUrl = ""

        // When
        val result = getCdnImageUrl(originUrl)

        // Then
        assertNull(result)
    }

    @Test
    fun `getCdnImageUrl should return original URL when it already contains cdn-cgi`() {
        // Given
        val originUrl = "https://images.sxwl.dev/cdn-cgi/image/width=720,quality=75/inty-static/test.jpg"

        // When
        val result = getCdnImageUrl(originUrl, width = 1080, quality = 80)

        // Then
        assertEquals(originUrl, result)
    }

    @Test
    fun `getCdnImageUrl should return original URL for Google Storage URLs`() {
        // Given
        val originUrl = "https://storage.googleapis.com/bucket/image.jpg"

        // When
        val result = getCdnImageUrl(originUrl, width = 1080, quality = 80)

        // Then
        assertEquals(originUrl, result)
    }

    @Test
    fun `getCdnImageUrl should transform inty-static URLs with default parameters`() {
        // Given
        val originUrl = "https://images.sxwl.dev/inty-static/backgrounds/user-123/sample.jpg"
        val expectedUrl = "https://images.sxwl.dev/cdn-cgi/image/width=1080,quality=75/inty-static/backgrounds/user-123/sample.jpg"

        // When
        val result = getCdnImageUrl(originUrl)

        // Then
        assertEquals(expectedUrl, result)
    }

    @Test
    fun `getCdnImageUrl should transform inty-static URLs with custom parameters`() {
        // Given
        val originUrl = "https://images.sxwl.dev/inty-static/agents/avatar-123.jpeg"
        val expectedUrl = "https://images.sxwl.dev/cdn-cgi/image/width=264,quality=75/inty-static/agents/avatar-123.jpeg"

        // When
        val result = getCdnImageUrl(originUrl, width = 264, quality = 75)

        // Then
        assertEquals(expectedUrl, result)
    }

    @Test
    fun `getCdnImageUrl should handle URLs with double inty-static path`() {
        // Given
        val originUrl = "https://images.sxwl.dev/inty-static//inty-static/agents/avatar-123.jpeg"
        val expectedUrl = "https://images.sxwl.dev/cdn-cgi/image/width=264,quality=75/inty-static//inty-static/agents/avatar-123.jpeg"

        // When
        val result = getCdnImageUrl(originUrl, width = 264, quality = 75)

        // Then
        assertEquals(expectedUrl, result)
    }

    @Test
    fun `getCdnImageUrl should be case insensitive for inty-static`() {
        // Given
        val originUrl = "https://images.sxwl.dev/INTY-STATIC/backgrounds/test.jpg"
        val expectedUrl = "https://images.sxwl.dev/cdn-cgi/image/width=720,quality=80/inty-static/backgrounds/test.jpg"

        // When
        val result = getCdnImageUrl(originUrl, width = 720, quality = 80)

        // Then
        assertEquals(expectedUrl, result)
    }

    @Test
    fun `getCdnImageUrl should return original URL for other domains`() {
        // Given
        val originUrl = "https://example.com/image.jpg"

        // When
        val result = getCdnImageUrl(originUrl, width = 1080, quality = 75)

        // Then
        assertEquals(originUrl, result)
    }

    @Test
    fun `getCdnImageUrl should handle URLs with query parameters`() {
        // Given
        val originUrl = "https://images.sxwl.dev/inty-static/backgrounds/test.jpg?v=123&t=456"
        val expectedUrl = "https://images.sxwl.dev/cdn-cgi/image/width=1080,quality=75/inty-static/backgrounds/test.jpg?v=123&t=456"

        // When
        val result = getCdnImageUrl(originUrl)

        // Then
        assertEquals(expectedUrl, result)
    }

    @Test
    fun `getCdnImageUrl should handle URLs with fragments`() {
        // Given
        val originUrl = "https://images.sxwl.dev/inty-static/backgrounds/test.jpg#section"
        val expectedUrl = "https://images.sxwl.dev/cdn-cgi/image/width=1080,quality=75/inty-static/backgrounds/test.jpg#section"

        // When
        val result = getCdnImageUrl(originUrl)

        // Then
        assertEquals(expectedUrl, result)
    }
}
