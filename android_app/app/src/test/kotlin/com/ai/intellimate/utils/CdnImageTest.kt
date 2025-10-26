package com.ai.intellimate.utils

import ai.sxwl.android.data.api.getCdnImageUrl
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/** 测试 getCdnImageUrl 函数的功能 */
class CdnImageTest {

    @Test
    fun `getCdnImageUrl should return null when originUrl is null`() {
// 给定
        val originUrl: String? = null
// 什么时候
        val result = getCdnImageUrl(originUrl)
// 然后
        assertNull(result)
    }

    @Test
    fun `getCdnImageUrl should return null when originUrl is empty`() {
// 给定
        val originUrl = ""
// 什么时候
        val result = getCdnImageUrl(originUrl)
// 然后
        assertNull(result)
    }

    @Test
    fun `getCdnImageUrl should return original URL when it already contains cdn-cgi`() {
// 给定
        val originUrl =
            "https://images.sxwl.dev/cdn-cgi/image/width=720,quality=75/inty-static/test.jpg"
// 什么时候
        val result = getCdnImageUrl(originUrl, width = 1080, quality = 80)
// 然后
        assertEquals(originUrl, result)
    }

    @Test
    fun `getCdnImageUrl should return original URL for Google Storage URLs`() {
// 给定
        val originUrl = "https://storage.googleapis.com/bucket/image.jpg"
// 什么时候
        val result = getCdnImageUrl(originUrl, width = 1080, quality = 80)
// 然后
        assertEquals(originUrl, result)
    }

    @Test
    fun `getCdnImageUrl should transform inty-static URLs with default parameters`() {
// 给定
        val originUrl = "https://images.sxwl.dev/inty-static/backgrounds/user-123/sample.jpg"
        val expectedUrl =
            "https://images.sxwl.dev/cdn-cgi/image/width=1080,quality=75/inty-static/backgrounds/user-123/sample.jpg"
// 什么时候
        val result = getCdnImageUrl(originUrl)
// 然后
        assertEquals(expectedUrl, result)
    }

    @Test
    fun `getCdnImageUrl should transform inty-static URLs with custom parameters`() {
// 给定
        val originUrl = "https://images.sxwl.dev/inty-static/agents/avatar-123.jpeg"
        val expectedUrl =
            "https://images.sxwl.dev/cdn-cgi/image/width=264,quality=75/inty-static/agents/avatar-123.jpeg"
// 什么时候
        val result = getCdnImageUrl(originUrl, width = 264, quality = 75)
// 然后
        assertEquals(expectedUrl, result)
    }

    @Test
    fun `getCdnImageUrl should handle URLs with double inty-static path`() {
// 给定
        val originUrl = "https://images.sxwl.dev/inty-static//inty-static/agents/avatar-123.jpeg"
        val expectedUrl =
            "https://images.sxwl.dev/cdn-cgi/image/width=264,quality=75/inty-static//inty-static/agents/avatar-123.jpeg"
// 什么时候
        val result = getCdnImageUrl(originUrl, width = 264, quality = 75)
// 然后
        assertEquals(expectedUrl, result)
    }

    @Test
    fun `getCdnImageUrl should be case insensitive for inty-static`() {
// 给定
        val originUrl = "https://images.sxwl.dev/INTY-STATIC/backgrounds/test.jpg"
        val expectedUrl =
            "https://images.sxwl.dev/cdn-cgi/image/width=720,quality=80/inty-static/backgrounds/test.jpg"
// 什么时候
        val result = getCdnImageUrl(originUrl, width = 720, quality = 80)
// 然后
        assertEquals(expectedUrl, result)
    }

    @Test
    fun `getCdnImageUrl should return original URL for other domains`() {
// 给定
        val originUrl = "https://example.com/image.jpg"
// 什么时候
        val result = getCdnImageUrl(originUrl, width = 1080, quality = 75)
// 然后
        assertEquals(originUrl, result)
    }

    @Test
    fun `getCdnImageUrl should handle URLs with query parameters`() {
// 给定
        val originUrl = "https://images.sxwl.dev/inty-static/backgrounds/test.jpg?v=123&t=456"
        val expectedUrl =
            "https://images.sxwl.dev/cdn-cgi/image/width=1080,quality=75/inty-static/backgrounds/test.jpg?v=123&t=456"
// 什么时候
        val result = getCdnImageUrl(originUrl)
// 然后
        assertEquals(expectedUrl, result)
    }

    @Test
    fun `getCdnImageUrl should handle URLs with fragments`() {
// 给定
        val originUrl = "https://images.sxwl.dev/inty-static/backgrounds/test.jpg#section"
        val expectedUrl =
            "https://images.sxwl.dev/cdn-cgi/image/width=1080,quality=75/inty-static/backgrounds/test.jpg#section"
// 什么时候
        val result = getCdnImageUrl(originUrl)
// 然后
        assertEquals(expectedUrl, result)
    }
}
