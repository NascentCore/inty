package com.ai.intellimate.chat.data

import kotlin.math.abs
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ChatInputImageScalingTest {
    @Test
    fun `scaleToTargetArea keeps area near 57600 and ratio for landscape image`() {
        val result = ChatInputImageScaling.scaleToTargetArea(1200, 800)

        assertTrue(
            abs(result.width * result.height - ChatInputImageScaling.TARGET_TOTAL_PIXELS) <= 200
        )
        assertTrue(abs(result.width.toDouble() / result.height.toDouble() - 1.5) < 0.02)
    }

    @Test
    fun `scaleToTargetArea keeps area near 57600 and ratio for portrait image`() {
        val result = ChatInputImageScaling.scaleToTargetArea(800, 1200)

        assertTrue(
            abs(result.width * result.height - ChatInputImageScaling.TARGET_TOTAL_PIXELS) <= 200
        )
        assertTrue(abs(result.width.toDouble() / result.height.toDouble() - (2.0 / 3.0)) < 0.02)
    }

    @Test
    fun `scaleToTargetArea keeps exact square when already target area`() {
        val result = ChatInputImageScaling.scaleToTargetArea(240, 240)
        assertEquals(240, result.width)
        assertEquals(240, result.height)
    }

    @Test(expected = IllegalArgumentException::class)
    fun `scaleToTargetArea rejects non-positive width`() {
        ChatInputImageScaling.scaleToTargetArea(0, 100)
    }
}
