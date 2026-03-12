package com.ai.intellimate.chat.data

import kotlin.math.abs
import kotlin.math.ceil
import kotlin.math.floor
import kotlin.math.roundToInt
import kotlin.math.sqrt

internal data class ScaledImageSize(
    val width: Int,
    val height: Int,
)

internal object ChatInputImageScaling {
    const val TARGET_TOTAL_PIXELS: Int = 57_600

    fun scaleToTargetArea(
        originalWidth: Int,
        originalHeight: Int,
        targetTotalPixels: Int = TARGET_TOTAL_PIXELS,
    ): ScaledImageSize {
        require(originalWidth > 0) { "originalWidth must be > 0" }
        require(originalHeight > 0) { "originalHeight must be > 0" }
        require(targetTotalPixels > 0) { "targetTotalPixels must be > 0" }

        val aspectRatio = originalWidth.toDouble() / originalHeight.toDouble()
        val rawHeight = sqrt(targetTotalPixels.toDouble() / aspectRatio)
        val rawWidth = rawHeight * aspectRatio

        val widthCandidates = buildCandidates(rawWidth)
        val heightCandidates = buildCandidates(rawHeight)

        val best =
            widthCandidates
                .flatMap { w -> heightCandidates.map { h -> ScaledImageSize(w, h) } }
                .filter { it.width > 0 && it.height > 0 }
                .minWithOrNull(
                    compareBy<ScaledImageSize> {
                        abs(it.width.toLong() * it.height.toLong() - targetTotalPixels.toLong())
                    }.thenBy {
                        abs((it.width.toDouble() / it.height.toDouble()) - aspectRatio)
                    }
                )

        return best ?: ScaledImageSize(originalWidth, originalHeight)
    }

    private fun buildCandidates(raw: Double): Set<Int> {
        val rounded = raw.roundToInt()
        val floorValue = floor(raw).toInt()
        val ceilValue = ceil(raw).toInt()
        return setOf(floorValue, rounded, ceilValue, rounded - 1, rounded + 1)
            .filter { it > 0 }
            .toSet()
    }
}
