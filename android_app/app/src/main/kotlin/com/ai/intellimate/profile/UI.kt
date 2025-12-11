package com.ai.intellimate.profile

import ai.sxwl.android.data.billing.VipStatus
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.design.AntiClick
import ai.sxwl.android.design.theme.HeartColor
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.BiasAlignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.unit.times
import coil3.compose.AsyncImage
import com.ai.intellimate.R
import com.ai.intellimate.ui.UiConfigs
import kotlin.random.Random

@Preview
@Composable
internal fun AgentsEmptyUI(modifier: Modifier = Modifier) {
    Column(modifier) {
        Spacer(Modifier.height(UiConfigs.MePage.EmptyStateTopSpacing))

        AsyncImage(
            modifier = Modifier.align(Alignment.CenterHorizontally),
            model = R.drawable.img_empty_magic,
            contentDescription = null,
        )

        Spacer(Modifier.height(UiConfigs.MePage.EmptyStateBottomSpacing))

        Text(
            modifier =
                Modifier
                    .padding(horizontal = UiConfigs.Padding.ScreenHorizontal)
                    .align(Alignment.CenterHorizontally),
            text = stringResource(R.string.no_agent),
            color = Color.White.copy(0.55f),
            fontSize = 14.sp,
            fontWeight = FontWeight.Normal,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
    }

}

@Preview
@Composable
internal fun ProfileHeaderBg(modifier: Modifier = Modifier) {
    Box(modifier) {
        AsyncImage(
            modifier = Modifier.fillMaxWidth(),
            model = R.drawable.img_profile_header_bg,
            contentDescription = null,
        )
        Box(
            modifier = Modifier
                .matchParentSize()
                .background(
                    brush = Brush.verticalGradient(
                        colors = listOf(
                            HeartColor.primaryColor.copy(.0f),
                            HeartColor.primaryColor.copy(.7f),
                            HeartColor.primaryColor.copy(.9f),
                        )
                    )
                )
        )
    }

}

/** Premium Banner 组件 */
@Composable
internal fun PremiumBanner(
    status: String? = "Activate Now",
    purchaseTime: String? = null,
    expireTime: String? = null,
    onClick: () -> Unit = {},
    isChristmas: Boolean = false,
) {
    var lastClickTimePremium by remember { mutableLongStateOf(0L) }

    Box(
        modifier =
            Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp)
                .clip(RoundedCornerShape(8.dp))
                .height(UiConfigs.MePage.VipBannerHeight)
                .clickable {
                    val currentTime = System.currentTimeMillis()
                    if (AntiClick.isValidClick(lastClickTimePremium)) {
                        lastClickTimePremium = currentTime
                        if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
                            onClick()
                        }
                    }
                }
    ) {
        Image(
            painter = painterResource(R.drawable.img_banner_bg_bg),
            contentDescription = "",
            contentScale = ContentScale.Crop,
            modifier = Modifier.fillMaxHeight(),
        )
        Image(
            painter = painterResource(
                if (isChristmas) R.drawable.img_vip_banner_bg_christmas else R.drawable.img_vip_banner_bg
            ),
            contentDescription = "",
            contentScale = ContentScale.Crop,
            modifier = Modifier.fillMaxHeight(),
        )
        Box(
            modifier = Modifier
                .matchParentSize()
                .background(
                    brush = Brush.radialGradient(
                        colors = listOf(Color.Black.copy(.1f), Color.Black.copy(.7f)),
                        center = Offset(x = 300f, y = 150f),
                    )
                )
        )

        LeftParticleEffects(isChristmas = isChristmas)

        ActionButton(
            modifier = Modifier.align(BiasAlignment(.95f, .1f)),
            isChristmas = isChristmas,
            status = status,
            purchaseTime = purchaseTime,
            expireTime = expireTime,
        )

        RightParticleEffects(isChristmas = isChristmas)
    }
}

@Composable
internal fun PurpleStar(modifier: Modifier = Modifier) {
    Box(
        modifier.background(
            brush = Brush.radialGradient(
                colors = listOf(
                    Color(0xC122FF).copy(.5f),
                    Color(0xC122FF).copy(.3f),
                    Color.Transparent
                ),
            )
        )
    )
}

@Composable
internal fun GoldDot(modifier: Modifier = Modifier) {
    Box(
        modifier
            .clip(CircleShape)
            .background(Color(0xFFFFC93F))
    )
}

@Composable
fun SnowPiece(modifier: Modifier = Modifier) {
    val infiniteTransition = rememberInfiniteTransition(label = "snow_breathing")
    val breathingAlpha by infiniteTransition.animateFloat(
        initialValue = 0.6f,
        targetValue = 1.0f,
        animationSpec = infiniteRepeatable(
            animation = tween(2000, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "breathing_alpha"
    )

    Box(
        modifier
            .alpha(breathingAlpha)
            .background(
                brush = Brush.radialGradient(
                    colors = listOf(
                        Color(0x99FDE8BF),
                        Color(0xFDE8BF),
                        Color.Transparent
                    ),
                )
            ),
        contentAlignment = Alignment.Center
    ) {
        Image(
            painter = painterResource(R.drawable.ic_snow_piece),
            contentDescription = null,
            modifier = Modifier.fillMaxSize(.3f)
        )
    }
}

@Composable
private fun LeftParticleEffects(isChristmas: Boolean) {
    val particleCount = 8
    val particles = remember(particleCount) {
        (0 until particleCount).map {
            ParticleConfig(
                initialX = Random.nextFloat() * 0.5f,
                initialY = Random.nextFloat(),
                size = (8f + Random.nextFloat() * 16f).dp,
                alpha = 0.3f + Random.nextFloat() * 0.7f,
                duration = (3000 + Random.nextInt(2000)).toInt(),
                delay = Random.nextInt(1000),
            )
        }
    }

    Box(modifier = Modifier.fillMaxSize()) {
        particles.forEach { particle ->
            FloatingParticle(
                particle = particle,
                modifier = Modifier
                    .align(Alignment.TopStart)
                    .offset(
                        x = particle.initialX * 200.dp,
                        y = particle.initialY * 120.dp
                    ),
                isChristmas = isChristmas,
            )
        }
    }
}

@Composable
private fun RightParticleEffects(isChristmas: Boolean) {
    val particleCount = 6
    val particles = remember(particleCount) {
        (0 until particleCount).map {
            ParticleConfig(
                initialX = 0.5f + Random.nextFloat() * 0.5f,
                initialY = Random.nextFloat(),
                size = (6f + Random.nextFloat() * 12f).dp,
                alpha = 0.4f + Random.nextFloat() * 0.6f,
                duration = (2500 + Random.nextInt(2000)).toInt(),
                delay = Random.nextInt(1000),
            )
        }
    }

    Box(modifier = Modifier.fillMaxSize()) {
        particles.forEach { particle ->
            FloatingGoldDot(
                particle = particle,
                modifier = Modifier
                    .align(Alignment.TopStart)
                    .offset(
                        x = particle.initialX * 200.dp,
                        y = particle.initialY * 120.dp
                    ),
            )
        }
    }
}

@Composable
private fun FloatingParticle(
    particle: ParticleConfig,
    modifier: Modifier = Modifier,
    isChristmas: Boolean,
) {
    val infiniteTransition = rememberInfiniteTransition(label = "particle_float")
    val offsetY by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(
                particle.duration,
                delayMillis = particle.delay,
                easing = LinearEasing
            ),
            repeatMode = RepeatMode.Restart
        ),
        label = "float_y"
    )
    val offsetX by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 0.3f,
        animationSpec = infiniteRepeatable(
            animation = tween(
                particle.duration,
                delayMillis = particle.delay,
                easing = LinearEasing
            ),
            repeatMode = RepeatMode.Restart
        ),
        label = "float_x"
    )

    Box(
        modifier = modifier
            .alpha(particle.alpha)
            .size(particle.size)
            .offset(
                x = offsetX * 60.dp,
                y = offsetY * 120.dp
            )
    ) {
        if (isChristmas) {
            SnowPiece(modifier = Modifier.fillMaxSize())
        } else {
            PurpleStar(modifier = Modifier.fillMaxSize())
        }
    }
}

@Composable
private fun FloatingGoldDot(
    particle: ParticleConfig,
    modifier: Modifier = Modifier,
) {
    val infiniteTransition = rememberInfiniteTransition(label = "gold_dot_float")
    val offsetY by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(
                particle.duration,
                delayMillis = particle.delay,
                easing = LinearEasing
            ),
            repeatMode = RepeatMode.Restart
        ),
        label = "float_y"
    )
    val offsetX by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 0.2f,
        animationSpec = infiniteRepeatable(
            animation = tween(
                particle.duration,
                delayMillis = particle.delay,
                easing = LinearEasing
            ),
            repeatMode = RepeatMode.Restart
        ),
        label = "float_x"
    )

    Box(
        modifier = modifier
            .alpha(particle.alpha)
            .size(particle.size)
            .offset(
                x = offsetX * 40.dp,
                y = offsetY * 120.dp
            )
    ) {
        GoldDot(modifier = Modifier.fillMaxSize())
    }
}

private data class ParticleConfig(
    val initialX: Float,
    val initialY: Float,
    val size: androidx.compose.ui.unit.Dp,
    val alpha: Float,
    val duration: Int,
    val delay: Int,
)

@Preview
@Composable
private fun PreviewPurpleStar() {
    Row(modifier = Modifier.fillMaxWidth()) {
        PurpleStar(modifier = Modifier.size(100.dp))
        GoldDot(Modifier.size(30.dp))
        SnowPiece(Modifier.size(90.dp))
    }
}

@Composable
internal fun ActionButton(
    modifier: Modifier = Modifier,
    isChristmas: Boolean = false,
    status: String? = null,
    purchaseTime: String? = null,
    expireTime: String? = null,
) {
    val buttonText =
        when (status) {
            VipStatus.UI_SUBSCRIBED -> "Since $purchaseTime"
            VipStatus.UI_SUBSCRIBED_EXPIRE_SOON -> "Expires on $expireTime"
            else -> "Activate now"
        }

    var boxSize by remember { mutableStateOf(Size.Zero) }

    val backgroundBrush =
        remember(boxSize, isChristmas) {
            if (boxSize == Size.Zero) {
                Brush.radialGradient(
                    colors = listOf(Color.Transparent, Color.Transparent)
                )
            } else if (isChristmas) {
                Brush.radialGradient(
                    colors = listOf(
                        Color(0xFFFFE898).copy(alpha = 0.8f),
                        Color(0xFFFFE898).copy(alpha = 0.5f),
                        Color.Transparent
                    ),
                    center = Offset(boxSize.width / 2f, boxSize.height / 2f),
                    radius = kotlin.math.min(boxSize.width, boxSize.height) * 0.8f
                )
            } else {
                Brush.radialGradient(
                    colors = listOf(
                        Color(0xC122FF).copy(.5f),
                        Color.Transparent
                    ),
                    center = Offset(boxSize.width / 2f, boxSize.height / 2f),
                    radius = kotlin.math.min(boxSize.width, boxSize.height) * 0.8f
                )
            }
        }

    val borderBrush =
        if (isChristmas) {
            Brush.horizontalGradient(
                colors = listOf(
                    Color(0xFF408B2F),
                    Color(0xFFE56135)
                )
            )
        } else {
            Brush.horizontalGradient(
                colors = listOf(
                    Color(0xFFC2F7FD),
                    Color(0xFFC2F7FD)
                )
            )
        }

    val iconRes =
        if (isChristmas) {
            R.drawable.tab_icon_explore_christmas
        } else {
            R.drawable.icon_gold_heart
        }

    Box(
        modifier
            .clip(RoundedCornerShape(30.dp))
            .onSizeChanged { size ->
                boxSize = Size(size.width.toFloat(), size.height.toFloat())
            }
            .background(brush = backgroundBrush)
            .padding(horizontal = 12.dp, vertical = 16.dp),
        contentAlignment = Alignment.Center,
    ) {
        Row(
            Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(30.dp))
                .background(
                    if (isChristmas) {
                        Color(0xFF1F1F1F)
                    } else {
                        Color(0xFF1F1F1F)
                    }
                )
                .border(
                    width = 1.dp,
                    brush = borderBrush,
                    shape = RoundedCornerShape(30.dp)
                )
                .padding(horizontal = 25.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Image(
                painter = painterResource(iconRes),
                contentDescription = null,
                modifier = Modifier.size(24.dp)
            )
            Spacer(Modifier.width(10.dp))
            Text(
                text = buildAnnotatedString {
                    withStyle(
                        style = SpanStyle(
                            brush = Brush.horizontalGradient(
                                colors = listOf(
                                    Color(0xFFFFEECC),
                                    Color(0xFFAD9515)
                                )
                            )
                        )
                    ) {
                        append(buttonText)
                    }
                },
                fontSize = 14.sp,
                fontWeight = FontWeight.Bold,
                textAlign = TextAlign.Center,
            )
        }
    }
}

@Preview
@Composable
private fun PreviewActionButton() {
    ActionButton(modifier = Modifier.size(200.dp, 80.dp))
}

@Preview
@Composable
private fun PreviewActionButtonChristmas() {
    ActionButton(
        modifier = Modifier.size(200.dp, 80.dp),
        isChristmas = true
    )
}

@Preview
@Composable
private fun PreviewPremiumBanner() {
    PremiumBanner()
}

@Preview
@Composable
private fun PreviewPremiumBannerChristmas() {
    PremiumBanner(isChristmas = true)
}
