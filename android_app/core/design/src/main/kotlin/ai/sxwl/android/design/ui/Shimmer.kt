package ai.sxwl.android.design.ui

import androidx.compose.animation.core.LinearEasing
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
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp

/**
 * 骨架屏基础组件
 */
@Composable
fun ShimmerBox(
    modifier: Modifier = Modifier,
    shape: Shape = RoundedCornerShape(4.dp)
) {
    val transition = rememberInfiniteTransition(label = "shimmer")
    val translateAnim by transition.animateFloat(
        initialValue = 0f,
        targetValue = 1000f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 1200, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "shimmer"
    )

    val shimmerColors = listOf(
        Color.LightGray.copy(alpha = 0.6f),
        Color.LightGray.copy(alpha = 0.2f),
        Color.LightGray.copy(alpha = 0.6f),
    )

    val brush = Brush.linearGradient(
        colors = shimmerColors,
        start = Offset.Zero,
        end = Offset(x = translateAnim, y = translateAnim)
    )

    Box(
        modifier = modifier
            .clip(shape)
            .background(brush)
    )
}

/**
 * Agent卡片骨架屏
 */
@Composable
fun AgentCardShimmer(
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(12.dp))
            .background(Color(0xFF2A2A2A))
    ) {
        // 模拟背景图片的骨架屏
        ShimmerBox(
            modifier = Modifier.matchParentSize(),
            shape = RoundedCornerShape(12.dp)
        )

        // 模拟渐变遮罩
        Box(
            modifier = Modifier
                .matchParentSize()
                .background(
                    brush = Brush.verticalGradient(
                        colors = listOf(
                            Color.Transparent,
                            Color.Black.copy(alpha = 0.3f),
                            Color.Black.copy(alpha = 0.7f)
                        )
                    )
                )
        )

        // 内容区域 - 底部对齐
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp)
                .align(Alignment.BottomStart)
        ) {
            // Agent名称和关注按钮
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                // 名称
                ShimmerBox(
                    modifier = Modifier
                        .weight(1f)
                        .height(16.dp)
                )

                Spacer(modifier = Modifier.width(8.dp))

                // 关注按钮
                ShimmerBox(
                    modifier = Modifier.size(32.dp),
                    shape = CircleShape
                )
            }

            Spacer(modifier = Modifier.height(4.dp))

            // Agent描述
            ShimmerBox(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(12.dp)
            )
            Spacer(modifier = Modifier.height(4.dp))
            ShimmerBox(
                modifier = Modifier
                    .width(200.dp)
                    .height(12.dp)
            )

            Spacer(modifier = Modifier.height(8.dp))

            // 统计信息
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                ShimmerBox(
                    modifier = Modifier
                        .width(60.dp)
                        .height(10.dp)
                )

                Spacer(modifier = Modifier.width(12.dp))

                ShimmerBox(
                    modifier = Modifier
                        .width(60.dp)
                        .height(10.dp)
                )
            }
        }
    }
}

/**
 * Agent头像卡片骨架屏
 */
@Composable
fun AgentAvatarCardShimmer(
    modifier: Modifier = Modifier
) {
    ShimmerBox(
        modifier = modifier
            .clip(RoundedCornerShape(12.dp))
    )
}

/**
 * Agents页面骨架屏
 */
@Composable
fun AgentsScreenShimmer(
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .fillMaxWidth()
    ) {

        // 主卡片区域 - 使用weight(1f)占满剩余空间
        AgentCardShimmer(
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f)
                .padding(horizontal = 24.dp, vertical = 16.dp)
        )

        // 头像轮播区域
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(112.dp)
                .padding(horizontal = 16.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                repeat(5) { index ->
                    AgentAvatarCardShimmer(
                        modifier = Modifier.size(88.dp)
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(18.dp))
    }
}

@Preview
@Composable
private fun PreviewAgentCardShimmer() {
    AgentCardShimmer()
}

@Preview
@Composable
private fun PreviewAgentAvatarCardShimmer() {
    AgentAvatarCardShimmer()
}

@Preview
@Composable
private fun PreviewAgentsScreenShimmer() {
    AgentsScreenShimmer()
}
