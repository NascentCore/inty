package ai.sxwl.android.design.theme

// CREATED_BY_AGENT

import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.composed
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawWithCache
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.TileMode
import androidx.compose.ui.graphics.drawscope.rotate
import kotlin.math.hypot
import kotlin.random.Random

private const val CHRISTMAS_OVERLAY_SEED = 1225
private const val CHRISTMAS_SNOW_COUNT = 88
private const val CHRISTMAS_STRIPE_ROTATION_DEG = -18f

@Immutable
private data class SnowDot(
    val center: Offset,
    val radiusPx: Float,
    val color: Color,
    val alpha: Float,
)

/**
 * 为全局 UI 叠加“节日图案层”（目前仅圣诞主题启用）。
 *
 * 预期视觉效果：
 * - 非侵入：非常轻的糖果条纹 + 雪点
 * - 覆盖整个屏幕：即使页面内部自绘 background，也能保持节日氛围
 */
fun Modifier.intelliMateSeasonalOverlay(scheme: IntelliMateThemeScheme): Modifier = composed {
    if (scheme != IntelliMateThemeScheme.Christmas) return@composed this

    val stripeRed = MaterialTheme.colorScheme.primary.copy(alpha = 0.055f)
    val stripeGreen = MaterialTheme.colorScheme.secondary.copy(alpha = 0.045f)
    val snowWhite = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.06f)
    val snowGold = MaterialTheme.colorScheme.tertiary.copy(alpha = 0.055f)

    drawWithCache {
        val rnd = Random(CHRISTMAS_OVERLAY_SEED)
        val width = size.width
        val height = size.height
        val center = Offset(x = width / 2f, y = height / 2f)
        val diag = hypot(width, height)
        val overlayTopLeft = Offset(x = (width - diag) / 2f, y = (height - diag) / 2f)
        val overlaySize = Size(width = diag, height = diag)

        val stripeBrush =
            Brush.linearGradient(
                colorStops =
                    arrayOf(
                        0.00f to stripeRed,
                        0.12f to stripeRed,
                        0.12f to Color.Transparent,
                        0.24f to Color.Transparent,
                        0.24f to stripeGreen,
                        0.36f to stripeGreen,
                        0.36f to Color.Transparent,
                        0.48f to Color.Transparent,
                    ),
                start = Offset.Zero,
                end = Offset(x = overlaySize.width, y = overlaySize.width),
                tileMode = TileMode.Repeated,
            )

        val snowDots =
            List(CHRISTMAS_SNOW_COUNT) {
                val x = rnd.nextFloat() * width
                val y = rnd.nextFloat() * height
                val radius = (0.8f + rnd.nextFloat() * 2.8f) * density
                val alpha = 0.22f + rnd.nextFloat() * 0.55f
                val color = if (rnd.nextFloat() < 0.14f) snowGold else snowWhite
                SnowDot(center = Offset(x, y), radiusPx = radius, color = color, alpha = alpha)
            }

        onDrawWithContent {
            drawContent()

            rotate(degrees = CHRISTMAS_STRIPE_ROTATION_DEG, pivot = center) {
                drawRect(brush = stripeBrush, topLeft = overlayTopLeft, size = overlaySize)
            }

            snowDots.forEach { dot ->
                drawCircle(
                    color = dot.color,
                    radius = dot.radiusPx,
                    center = dot.center,
                    alpha = dot.alpha,
                )
            }
        }
    }
}

