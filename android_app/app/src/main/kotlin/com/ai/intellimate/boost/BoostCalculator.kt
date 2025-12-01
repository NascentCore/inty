/*
 * CREATED_BY_AGENT
 */
package com.ai.intellimate.boost

import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

/** 负责 token ↔ point 的估算与通用校验。 */
object BoostCalculator {

    fun estimateTokensFromMessage(message: String): Int {
        if (message.isBlank()) return 0
        val normalized = message.trim()
        val estimated = normalized.length / BoostConfig.AVG_CHARS_PER_TOKEN
        return max(1, estimated.roundToInt())
    }

    fun tokensToPoints(tokens: Int): Int {
        if (tokens <= 0) return 0
        val converted = tokens * BoostConfig.TOKEN_TO_POINT_RATIO
        return max(1, converted.roundToInt())
    }

    fun imageGenerationPoints(): Int = tokensToPoints(BoostConfig.IMAGE_TOKEN_COST)

    fun audioPlaybackPoints(): Int = tokensToPoints(BoostConfig.AUDIO_TOKEN_COST)

    fun clampDailyGain(current: Int, delta: Int): Int {
        if (delta <= 0) return 0
        val allowed =
            BoostConfig.MAX_POINTS_PER_DAY
        if (current >= allowed) return 0
        return min(delta, allowed - current)
    }

    fun normalizeBoostAmount(requested: Int, available: Int): Int {
        if (available < BoostConfig.BOOST_STEP_POINTS) return 0
        val safeRequested = if (requested <= 0) BoostConfig.BOOST_STEP_POINTS else requested
        val maxAffordable = available - (available % BoostConfig.BOOST_STEP_POINTS)
        val clamped = min(safeRequested, maxAffordable)
        return clamped - (clamped % BoostConfig.BOOST_STEP_POINTS)
    }
}
