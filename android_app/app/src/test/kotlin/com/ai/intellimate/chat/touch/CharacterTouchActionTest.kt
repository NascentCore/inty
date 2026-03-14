package com.ai.intellimate.chat.touch

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class CharacterTouchActionTest {
    /** Scale-from-height: container taller than source aspect; offsetX non-zero, offsetY zero. */
    @Test
    fun mapPoint_scaleFromHeight_mapsToOriginalImageCoordinates() {
        val layout =
            CharacterBackgroundLayout(
                containerWidthPx = 800f,
                containerHeightPx = 1600f,
                sourceImageWidthPx = 1080f,
                sourceImageHeightPx = 1920f,
            )

        val point =
            CharacterTouchCoordinateMapper.mapPoint(
                layout = layout,
                touchX = 0f,
                touchY = 800f,
            )

        assertEquals(60, point?.x)
        assertEquals(960, point?.y)
    }

    /** Scale-from-width: container wider than source aspect; offsetY non-zero (center-crop). */
    @Test
    fun mapPoint_scaleFromWidth_centerCropMapsCorrectly() {
        val layout =
            CharacterBackgroundLayout(
                containerWidthPx = 1080f,
                containerHeightPx = 1080f,
                sourceImageWidthPx = 1080f,
                sourceImageHeightPx = 1920f,
            )

        val point =
            CharacterTouchCoordinateMapper.mapPoint(
                layout = layout,
                touchX = 540f,
                touchY = 540f,
            )

        assertEquals(540, point?.x)
        assertEquals(960, point?.y)
    }

    @Test
    fun mapPoint_outsideBounds_clampsToImageEdges() {
        val layout =
            CharacterBackgroundLayout(
                containerWidthPx = 1080f,
                containerHeightPx = 1920f,
                sourceImageWidthPx = 1080f,
                sourceImageHeightPx = 1920f,
            )

        val point =
            CharacterTouchCoordinateMapper.mapPoint(
                layout = layout,
                touchX = -200f,
                touchY = 4000f,
            )

        assertEquals(0, point?.x)
        assertEquals(1919, point?.y)
        assertEquals(0f, point?.normalizedX)
        assertEquals(1f, point?.normalizedY)
    }

    @Test
    fun buildTapAction_wrapsWithParenthesesMarker() {
        val start = CharacterTouchPoint(x = 120, y = 340, normalizedX = 0.11f, normalizedY = 0.22f)
        val action =
            CharacterTouchActionFormatter.buildTapAction(
                startPoint = start,
                sourceImageWidth = 1080,
                sourceImageHeight = 1920,
                useAsteriskMarker = false,
            )

        assertEquals(CharacterTouchGestureType.TAP, action.gestureType)
        assertTrue(action.description.startsWith("("))
        assertTrue(action.description.endsWith(")"))
        assertTrue(action.description.contains("User tapped"))
        assertTrue(action.description.contains("(120, 340)"))
    }

    @Test
    fun buildSwipeAction_wrapsWithAsteriskMarker() {
        val start = CharacterTouchPoint(x = 10, y = 20, normalizedX = 0.01f, normalizedY = 0.02f)
        val end = CharacterTouchPoint(x = 200, y = 320, normalizedX = 0.2f, normalizedY = 0.33f)
        val action =
            CharacterTouchActionFormatter.buildSwipeAction(
                startPoint = start,
                endPoint = end,
                sourceImageWidth = 1080,
                sourceImageHeight = 1920,
                useAsteriskMarker = true,
            )

        assertEquals(CharacterTouchGestureType.SWIPE, action.gestureType)
        assertTrue(action.description.startsWith("*"))
        assertTrue(action.description.endsWith("*"))
        assertTrue(action.description.contains("User swiped"))
        assertTrue(action.description.contains("(10, 20)"))
        assertTrue(action.description.contains("(200, 320)"))
    }
}
