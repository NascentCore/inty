package com.ai.intellimate.explore

import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.input.nestedscroll.NestedScrollConnection
import androidx.compose.ui.input.nestedscroll.NestedScrollSource
import androidx.compose.ui.unit.Velocity
import kotlin.math.abs
import kotlin.math.sign

// CREATED_BY_AGENT
@Composable
fun rememberExploreScrollConnection(
    initialVelocityMultiplier: Float = ExploreConstants.SCROLL_INITIAL_VELOCITY_MULTIPLIER,
    minFlingVelocity: Float = ExploreConstants.SCROLL_MIN_FLING_VELOCITY,
    maxFlingVelocity: Float = ExploreConstants.SCROLL_MAX_FLING_VELOCITY,
    decelerationMultiplier: Float = ExploreConstants.SCROLL_DECELERATION_MULTIPLIER,
    scrollDeltaThreshold: Float = ExploreConstants.SCROLL_DELTA_THRESHOLD,
): NestedScrollConnection {
    return remember {
        object : NestedScrollConnection {

            override fun onPreScroll(available: Offset, source: NestedScrollSource): Offset {
                if (source != NestedScrollSource.Drag || scrollDeltaThreshold <= 0f) {
                    return Offset.Zero
                }

                val availableY = available.y
                if (abs(availableY) <= scrollDeltaThreshold) {
                    return Offset.Zero
                }

                val consumed = availableY - scrollDeltaThreshold * sign(availableY)
                return Offset(0f, consumed)
            }

            override suspend fun onPreFling(available: Velocity): Velocity {
                val scaledVelocity = available.y * initialVelocityMultiplier
                val deceleratedVelocity = scaledVelocity / decelerationMultiplier
                val clampedVelocity =
                    deceleratedVelocity.coerceIn(-maxFlingVelocity, maxFlingVelocity)

                val finalVelocity =
                    if (abs(clampedVelocity) < minFlingVelocity) 0f else clampedVelocity

                return Velocity(0f, available.y - finalVelocity)
            }
        }
    }
}
