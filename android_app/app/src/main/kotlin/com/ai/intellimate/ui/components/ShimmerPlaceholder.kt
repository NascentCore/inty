package com.ai.intellimate.ui.components

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

/** Shimmer占符位组件用于图片加载时的占位效果 */
@Composable
fun ShimmerPlaceholder(
    modifier: Modifier = Modifier,
    cornerRadius: Dp = 8.dp,
) {
    val infiniteTransition = rememberInfiniteTransition(label = "shimmer")
    val alpha by
    infiniteTransition.animateFloat(
        initialValue = 0.2f,
        targetValue = 0.6f,
        animationSpec =
            infiniteRepeatable(animation = tween(1000), repeatMode = RepeatMode.Reverse),
        label = "shimmer_alpha",
    )

    Box(
        modifier =
            modifier
                .clip(RoundedCornerShape(cornerRadius))
                .background(
                    brush =
                        Brush.verticalGradient(
                            colors =
                                listOf(
                                    Color(0xFF2A2A2A).copy(alpha = alpha),
                                    Color(0xFF3A3A3A).copy(alpha = alpha),
                                    Color(0xFF2A2A2A).copy(alpha = alpha),
                                )
                        )
                )
    )
}
