package com.ai.intellimate.ui.components

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/** Shimmer 占位符组件 用于图片加载时的占位效果 */
@Composable
fun ShimmerPlaceholder(
    modifier: Modifier = Modifier,
    cornerRadius: Dp = 8.dp,
    showLoadingDots: Boolean = false,
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
                ),
        contentAlignment = Alignment.Center,
    ) {
        // 如果需要显示loading点点点，在shimmer内部显示
        if (showLoadingDots) {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center,
            ) {
                // Loading点点点动画
                Row(
                    horizontalArrangement = Arrangement.spacedBy(4.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    repeat(3) { index ->
                        val delay = index * 200
                        val dotAlpha by
                            infiniteTransition.animateFloat(
                                initialValue = 0.3f,
                                targetValue = 1.0f,
                                animationSpec =
                                    infiniteRepeatable(animation = tween(600, delayMillis = delay)),
                                label = "dot_alpha_$index",
                            )

                        Box(
                            modifier =
                                Modifier.size(6.dp)
                                    .background(
                                        color = Color.White.copy(alpha = dotAlpha * 0.7f),
                                        shape = CircleShape,
                                    )
                        )
                    }
                }
                // "Image generating..." 文字
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "Image generating...",
                    color = Color.White.copy(alpha = 0.6f),
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Normal,
                )
            }
        }
    }
}
