package com.ai.intellimate.ui.components

// CREATED_BY_AGENT

import ai.sxwl.android.design.theme.HolidayCelebrationColors
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material.icons.rounded.EmojiEvents
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawWithCache
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.BlendMode
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Fill
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.graphics.drawscope.translate
import androidx.compose.ui.graphics.drawscope.withTransform
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.ai.intellimate.ui.UiConfigs
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin
import kotlin.random.Random

private const val CONFETTI_SEED = 202512
private const val CONFETTI_COUNT = 90
private const val CONFETTI_ANIM_MILLIS = 4200
private const val TWINKLE_ANIM_MILLIS = 1600
private const val BREATHE_ANIM_MILLIS = 980

private val HERO_ICON_CONTAINER_SIZE = 74.dp
private val HERO_RING_STROKE_WIDTH = 5.dp

/**
 * 圣诞 & 新年庆祝弹窗（极其吸睛、splashy）。
 *
 * 预期视觉效果：
 * - 深色夜空渐变背景 + 霓虹辉光环 + 星光闪烁
 * - 彩纸/亮片从上往下飘落（confetti）
 * - 主按钮“呼吸感”放大缩小，鼓励用户点击关闭
 *
 * 可配置项：
 * - 文案：title/subtitle/primary/secondary
 * - 行为：onDismiss / onPrimaryClick
 */
@Composable
fun HolidayCelebrationDialog(
    title: String,
    subtitle: String,
    primaryButtonText: String,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier,
    onPrimaryClick: () -> Unit = onDismiss,
) {
    val particles =
        remember { ConfettiParticle.createBatch(seed = CONFETTI_SEED, count = CONFETTI_COUNT) }

    val infinite = rememberInfiniteTransition(label = "holiday_celebration")
    val t by
        infinite.animateFloat(
            initialValue = 0f,
            targetValue = 1f,
            animationSpec =
                infiniteRepeatable(tween(CONFETTI_ANIM_MILLIS, easing = LinearEasing)),
            label = "confetti_progress",
        )
    val twinkle by
        infinite.animateFloat(
            initialValue = 0.15f,
            targetValue = 0.85f,
            animationSpec =
                infiniteRepeatable(
                    animation = tween(TWINKLE_ANIM_MILLIS, easing = LinearEasing),
                    repeatMode = RepeatMode.Reverse,
                ),
            label = "twinkle",
        )
    val breathe by
        infinite.animateFloat(
            initialValue = 0.985f,
            targetValue = 1.03f,
            animationSpec =
                infiniteRepeatable(
                    animation = tween(BREATHE_ANIM_MILLIS, easing = LinearEasing),
                    repeatMode = RepeatMode.Reverse,
                ),
            label = "breathe",
        )

    Dialog(
        onDismissRequest = onDismiss,
        properties =
            DialogProperties(
                dismissOnBackPress = true,
                dismissOnClickOutside = true,
                usePlatformDefaultWidth = false,
            ),
    ) {
        Box(
            modifier =
                modifier
                    .fillMaxWidth()
                    .padding(horizontal = UiConfigs.Padding.DialogEdge)
                    .clip(RoundedCornerShape(UiConfigs.Shape.DialogLarge))
                    .background(color = Color.Transparent),
        ) {
            HolidayCelebrationBackdrop(
                modifier = Modifier.matchParentSize(),
                confettiProgress = t,
                twinkle = twinkle,
                particles = particles,
            )

            HolidayCelebrationContent(
                title = title,
                subtitle = subtitle,
                primaryButtonText = primaryButtonText,
                breathe = breathe,
                onDismiss = onDismiss,
                onPrimaryClick = onPrimaryClick,
                modifier = Modifier.align(Alignment.Center),
            )
        }
    }
}

@Composable
private fun HolidayCelebrationContent(
    title: String,
    subtitle: String,
    primaryButtonText: String,
    breathe: Float,
    onDismiss: () -> Unit,
    onPrimaryClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier =
            modifier
                .fillMaxWidth()
                .padding(
                    horizontal = UiConfigs.Padding.DialogContentHorizontal,
                    vertical = UiConfigs.Padding.DialogContentVertical,
                ),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        HolidayCelebrationHero(breathe = breathe)

        Spacer(modifier = Modifier.height(UiConfigs.Spacing.MediumPlus))

        Text(
            text = title,
            modifier = Modifier.fillMaxWidth(),
            textAlign = TextAlign.Center,
            style =
                MaterialTheme.typography.titleLarge.merge(
                    TextStyle(
                        fontSize = UiConfigs.Typography.Title,
                        fontWeight = FontWeight.ExtraBold,
                        brush =
                            Brush.linearGradient(
                                colors =
                                    listOf(
                                        HolidayCelebrationColors.GlowGold,
                                        HolidayCelebrationColors.GlowPink,
                                        HolidayCelebrationColors.GlowCyan,
                                    )
                            ),
                    )
                ),
        )

        Spacer(modifier = Modifier.height(UiConfigs.Spacing.Small))

        Text(
            text = subtitle,
            modifier = Modifier.fillMaxWidth(),
            textAlign = TextAlign.Center,
            color = HolidayCelebrationColors.FrostWhite,
            style = MaterialTheme.typography.bodyMedium,
        )

        Spacer(modifier = Modifier.height(UiConfigs.Spacing.XLarge))

        HolidayCelebrationPrimaryButton(
            text = primaryButtonText,
            breathe = breathe,
            onClick = onPrimaryClick,
        )
    }
}

@Composable
private fun HolidayCelebrationHero(breathe: Float, modifier: Modifier = Modifier) {
    Box(
        modifier = modifier.size(HERO_ICON_CONTAINER_SIZE),
        contentAlignment = Alignment.Center,
    ) {
        Box(
            modifier =
                Modifier.matchParentSize().drawWithCache {
                    val center = Offset(x = size.width / 2f, y = size.height / 2f)
                    val radius = this.size.minDimension / 2f
                    val stroke = Stroke(width = HERO_RING_STROKE_WIDTH.toPx())
                    val ringBrush =
                        Brush.sweepGradient(
                            colors =
                                listOf(
                                    HolidayCelebrationColors.GlowGold,
                                    HolidayCelebrationColors.GlowPink,
                                    HolidayCelebrationColors.GlowCyan,
                                    HolidayCelebrationColors.GlowGreen,
                                    HolidayCelebrationColors.GlowGold,
                                )
                        )
                    val alpha = 0.85f

                    onDrawBehind {
                        drawCircle(
                            brush = ringBrush,
                            radius = radius,
                            center = center,
                            style = stroke,
                            alpha = alpha,
                        )
                        drawCircle(
                            color = HolidayCelebrationColors.StarWhite,
                            radius = radius,
                            center = center,
                            style = Stroke(width = (stroke.width * 0.22f)),
                            alpha = 0.12f,
                        )
                    }
                }
        )

        Icon(
            imageVector = Icons.Rounded.EmojiEvents,
            contentDescription = null,
            tint = HolidayCelebrationColors.GlowGold,
            modifier = Modifier.size(34.dp).scale(breathe),
        )
        Icon(
            imageVector = Icons.Rounded.AutoAwesome,
            contentDescription = null,
            tint = HolidayCelebrationColors.GlowCyan.copy(alpha = 0.85f),
            modifier = Modifier.size(22.dp).align(Alignment.TopEnd).alpha(0.9f),
        )
    }
}

@Composable
private fun HolidayCelebrationPrimaryButton(
    text: String,
    breathe: Float,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Box(
        modifier =
            modifier
                .fillMaxWidth(UiConfigs.Fractions.PrimaryButtonWidth)
                .height(UiConfigs.Size.PrimaryButtonHeight)
                .scale(breathe)
                .clip(RoundedCornerShape(UiConfigs.Shape.PrimaryButton))
                .background(
                    brush =
                        Brush.horizontalGradient(
                            colors =
                                listOf(
                                    HolidayCelebrationColors.GlowRed,
                                    HolidayCelebrationColors.GlowGold,
                                    HolidayCelebrationColors.GlowCyan,
                                )
                        )
                )
                .clickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = text,
            color = Color.White,
            fontWeight = FontWeight.SemiBold,
            fontSize = UiConfigs.Typography.ButtonLarge,
        )
    }
}

@Composable
private fun HolidayCelebrationBackdrop(
    confettiProgress: Float,
    twinkle: Float,
    particles: List<ConfettiParticle>,
    modifier: Modifier = Modifier,
) {
    Box(
        modifier =
            modifier
                .background(
                    brush =
                        Brush.verticalGradient(
                            colors =
                                listOf(
                                    HolidayCelebrationColors.BackdropTop,
                                    HolidayCelebrationColors.BackdropMid,
                                    HolidayCelebrationColors.BackdropBottom,
                                )
                        )
                )
                .drawWithCache {
                    val stars = StarField.create(seed = 1225, count = 34)
                    val center = Offset(x = size.width / 2f, y = size.height / 2f)
                    val glow =
                        Brush.radialGradient(
                            colors =
                                listOf(
                                    HolidayCelebrationColors.GlowPink.copy(alpha = 0.22f),
                                    Color.Transparent,
                                ),
                            radius = size.minDimension * 0.72f,
                            center = center,
                        )

                    onDrawBehind {
                        // 霓虹辉光底
                        drawRect(brush = glow)

                        // 星光（twinkle）
                        stars.forEach { star ->
                            val x = star.x01 * size.width
                            val y = star.y01 * size.height
                            val r = star.radiusPx * density
                            val a = (star.baseAlpha * twinkle).coerceIn(0f, 1f)
                            drawCircle(
                                color = HolidayCelebrationColors.StarWhite,
                                radius = r,
                                center = androidx.compose.ui.geometry.Offset(x, y),
                                alpha = a,
                            )
                        }

                        // 彩纸（confetti）
                        drawConfettiLayer(
                            particles = particles,
                            progress = confettiProgress,
                            cardWidth = size.width,
                            cardHeight = size.height,
                        )
                    }
                },
    )
}

private fun androidx.compose.ui.graphics.drawscope.DrawScope.drawConfettiLayer(
    particles: List<ConfettiParticle>,
    progress: Float,
    cardWidth: Float,
    cardHeight: Float,
) {
    particles.forEach { p ->
        val x = p.x01 * cardWidth
        val y = ((p.y01 + progress * p.speed01) % 1f) * cardHeight

        val sizePx = (p.size01 * 14f + 6f) * density
        val rotation = (p.spin01 * 2f * PI.toFloat() + progress * p.spinSpeed01 * 8f).toFloat()

        val color = HolidayCelebrationColors.ConfettiColors[p.colorIndex]
        val alpha = (0.35f + 0.65f * p.alpha01).coerceIn(0f, 1f)

        when (p.shape) {
            ConfettiShape.Circle -> {
                drawCircle(
                    color = color,
                    radius = sizePx * 0.36f,
                    center = androidx.compose.ui.geometry.Offset(x, y),
                    alpha = alpha,
                )
            }
            ConfettiShape.Square -> {
                withTransform(
                    {
                        translate(left = x, top = y)
                        rotate(degrees = rotation * 57.29578f)
                    }
                ) {
                    drawRect(
                        color = color,
                        topLeft = androidx.compose.ui.geometry.Offset(-sizePx / 2f, -sizePx / 2f),
                        size = androidx.compose.ui.geometry.Size(sizePx, sizePx),
                        alpha = alpha,
                    )
                }
            }
            ConfettiShape.Ribbon -> {
                val w = sizePx * 1.05f
                val h = sizePx * 0.28f
                withTransform(
                    {
                        translate(left = x, top = y)
                        rotate(degrees = rotation * 57.29578f)
                    }
                ) {
                    drawRoundRect(
                        color = color,
                        topLeft = androidx.compose.ui.geometry.Offset(-w / 2f, -h / 2f),
                        size = androidx.compose.ui.geometry.Size(w, h),
                        cornerRadius =
                            androidx.compose.ui.geometry.CornerRadius(x = h / 2f, y = h / 2f),
                        alpha = alpha,
                    )
                }
            }
            ConfettiShape.Star -> {
                drawStar(
                    centerX = x,
                    centerY = y,
                    outerRadiusPx = sizePx * 0.55f,
                    innerRadiusPx = sizePx * 0.24f,
                    points = 5,
                    rotationRad = rotation,
                    color = color,
                    alpha = alpha,
                )
            }
        }
    }
}

private fun androidx.compose.ui.graphics.drawscope.DrawScope.drawStar(
    centerX: Float,
    centerY: Float,
    outerRadiusPx: Float,
    innerRadiusPx: Float,
    points: Int,
    rotationRad: Float,
    color: Color,
    alpha: Float,
) {
    val step = (PI.toFloat() * 2f) / points.toFloat()
    val halfStep = step / 2f
    val path = Path()

    for (i in 0 until points) {
        val outerAngle = rotationRad + i * step
        val innerAngle = outerAngle + halfStep

        val ox = centerX + cos(outerAngle) * outerRadiusPx
        val oy = centerY + sin(outerAngle) * outerRadiusPx
        val ix = centerX + cos(innerAngle) * innerRadiusPx
        val iy = centerY + sin(innerAngle) * innerRadiusPx

        if (i == 0) path.moveTo(ox, oy) else path.lineTo(ox, oy)
        path.lineTo(ix, iy)
    }
    path.close()

    drawPath(path = path, color = color, alpha = alpha, style = Fill, blendMode = BlendMode.SrcOver)
    drawPath(
        path = path,
        color = HolidayCelebrationColors.StarWhite,
        alpha = alpha * 0.12f,
        style = Stroke(width = 1.2f * density),
    )
}

@Immutable
private data class StarSpec(
    val x01: Float,
    val y01: Float,
    val radiusPx: Float,
    val baseAlpha: Float,
)

private object StarField {
    fun create(seed: Int, count: Int): List<StarSpec> {
        val rnd = Random(seed)
        return List(count) {
            StarSpec(
                x01 = rnd.nextFloat(),
                y01 = rnd.nextFloat() * 0.62f,
                radiusPx = 0.9f + rnd.nextFloat() * 1.8f,
                baseAlpha = 0.25f + rnd.nextFloat() * 0.75f,
            )
        }
    }
}

private enum class ConfettiShape {
    Circle,
    Square,
    Ribbon,
    Star,
}

@Immutable
private data class ConfettiParticle(
    val x01: Float,
    val y01: Float,
    val size01: Float,
    val speed01: Float,
    val spin01: Float,
    val spinSpeed01: Float,
    val alpha01: Float,
    val colorIndex: Int,
    val shape: ConfettiShape,
) {
    companion object {
        fun createBatch(seed: Int, count: Int): List<ConfettiParticle> {
            val rnd = Random(seed)
            val maxColorIndex = HolidayCelebrationColors.ConfettiColors.size.coerceAtLeast(1) - 1
            return List(count) {
                val shape =
                    when (rnd.nextInt(4)) {
                        0 -> ConfettiShape.Circle
                        1 -> ConfettiShape.Ribbon
                        2 -> ConfettiShape.Square
                        else -> ConfettiShape.Star
                    }
                ConfettiParticle(
                    x01 = rnd.nextFloat(),
                    y01 = rnd.nextFloat(),
                    size01 = rnd.nextFloat(),
                    speed01 = 0.35f + rnd.nextFloat() * 0.9f,
                    spin01 = rnd.nextFloat(),
                    spinSpeed01 = 0.6f + rnd.nextFloat() * 1.8f,
                    alpha01 = 0.35f + rnd.nextFloat() * 0.65f,
                    colorIndex = rnd.nextInt(0, maxColorIndex + 1),
                    shape = shape,
                )
            }
        }
    }
}
