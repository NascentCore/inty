package com.ai.intellimate.chat.touch

import java.util.Locale
import kotlin.math.max
import kotlin.math.roundToInt

enum class CharacterTouchGestureType(val analyticsValue: String) {
    TAP("tap"),
    SWIPE("swipe"),
}

data class CharacterTouchPoint(
    val x: Int,
    val y: Int,
    val normalizedX: Float,
    val normalizedY: Float,
)

data class CharacterTouchAction(
    val gestureType: CharacterTouchGestureType,
    val description: String,
    val sourceImageWidth: Int,
    val sourceImageHeight: Int,
    val startPoint: CharacterTouchPoint,
    val endPoint: CharacterTouchPoint? = null,
)

data class CharacterBackgroundLayout(
    val containerWidthPx: Float,
    val containerHeightPx: Float,
    val sourceImageWidthPx: Float,
    val sourceImageHeightPx: Float,
)

/**
 * Maps touch coordinates from the chat background container to the original source image, matching
 * [ContentScale.Crop] (scale to cover, then center both axes).
 */
object CharacterTouchCoordinateMapper {
    fun mapPoint(
        layout: CharacterBackgroundLayout,
        touchX: Float,
        touchY: Float,
    ): CharacterTouchPoint? {
        if (
            layout.containerWidthPx <= 0f ||
                layout.containerHeightPx <= 0f ||
                layout.sourceImageWidthPx <= 0f ||
                layout.sourceImageHeightPx <= 0f
        ) {
            return null
        }

        val scale =
            max(
                layout.containerWidthPx / layout.sourceImageWidthPx,
                layout.containerHeightPx / layout.sourceImageHeightPx,
            )
        if (scale <= 0f || !scale.isFinite()) return null

        val displayedWidth = layout.sourceImageWidthPx * scale
        val displayedHeight = layout.sourceImageHeightPx * scale
        val offsetX = (layout.containerWidthPx - displayedWidth) / 2f
        val offsetY = (layout.containerHeightPx - displayedHeight) / 2f
        val mappedX = ((touchX - offsetX) / scale).coerceIn(0f, layout.sourceImageWidthPx - 1f)
        val mappedY = ((touchY - offsetY) / scale).coerceIn(0f, layout.sourceImageHeightPx - 1f)

        val normalizedX =
            if (layout.sourceImageWidthPx <= 1f) 0f
            else (mappedX / (layout.sourceImageWidthPx - 1f)).coerceIn(0f, 1f)
        val normalizedY =
            if (layout.sourceImageHeightPx <= 1f) 0f
            else (mappedY / (layout.sourceImageHeightPx - 1f)).coerceIn(0f, 1f)

        return CharacterTouchPoint(
            x = mappedX.roundToInt(),
            y = mappedY.roundToInt(),
            normalizedX = normalizedX,
            normalizedY = normalizedY,
        )
    }
}

object CharacterTouchActionFormatter {
    fun buildTapAction(
        startPoint: CharacterTouchPoint,
        sourceImageWidth: Int,
        sourceImageHeight: Int,
        useAsteriskMarker: Boolean,
    ): CharacterTouchAction {
        val body =
            "User tapped the character background at (${startPoint.x}, ${startPoint.y}) " +
                "on original image ${sourceImageWidth}x${sourceImageHeight} " +
                "(normalized ${formatDecimal(startPoint.normalizedX)}, " +
                "${formatDecimal(startPoint.normalizedY)})."
        return CharacterTouchAction(
            gestureType = CharacterTouchGestureType.TAP,
            description = wrapActionMarker(body, useAsteriskMarker),
            sourceImageWidth = sourceImageWidth,
            sourceImageHeight = sourceImageHeight,
            startPoint = startPoint,
        )
    }

    fun buildSwipeAction(
        startPoint: CharacterTouchPoint,
        endPoint: CharacterTouchPoint,
        sourceImageWidth: Int,
        sourceImageHeight: Int,
        useAsteriskMarker: Boolean,
    ): CharacterTouchAction {
        val body =
            "User swiped on the character background from (${startPoint.x}, ${startPoint.y}) " +
                "to (${endPoint.x}, ${endPoint.y}) on original image " +
                "${sourceImageWidth}x${sourceImageHeight} " +
                "(normalized ${formatDecimal(startPoint.normalizedX)}, " +
                "${formatDecimal(startPoint.normalizedY)} -> " +
                "${formatDecimal(endPoint.normalizedX)}, " +
                "${formatDecimal(endPoint.normalizedY)})."
        return CharacterTouchAction(
            gestureType = CharacterTouchGestureType.SWIPE,
            description = wrapActionMarker(body, useAsteriskMarker),
            sourceImageWidth = sourceImageWidth,
            sourceImageHeight = sourceImageHeight,
            startPoint = startPoint,
            endPoint = endPoint,
        )
    }

    private fun wrapActionMarker(text: String, useAsteriskMarker: Boolean): String {
        return if (useAsteriskMarker) {
            "*$text*"
        } else {
            "($text)"
        }
    }

    private fun formatDecimal(value: Float): String {
        return String.format(Locale.US, "%.3f", value)
    }
}
