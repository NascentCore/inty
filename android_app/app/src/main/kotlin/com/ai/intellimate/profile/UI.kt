package com.ai.intellimate.profile

import ai.sxwl.android.data.api.getCdnImageUrl
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
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
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
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.ElevatedButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil3.compose.AsyncImage
import coil3.request.ImageRequest
import com.ai.intellimate.R
import com.ai.intellimate.ui.UiConfigs
import kotlin.math.max
import kotlin.math.min
import kotlin.random.Random

@Preview
@Composable
internal fun AgentsEmptyUI(modifier: Modifier = Modifier, onClick: () -> Unit = {}) {
    Column(modifier) {
        Spacer(Modifier.height(UiConfigs.MePage.EmptyStateTopSpacing))

        AsyncImage(
            modifier =
                Modifier.size(UiConfigs.MePage.EmptyStateIconSize)
                    .align(Alignment.CenterHorizontally)
                    .clickable(onClick = onClick),
            model = R.drawable.img_empty_magic,
            contentDescription = null,
        )

        Spacer(Modifier.height(UiConfigs.MePage.EmptyStateBottomSpacing))

        Text(
            modifier =
                Modifier.padding(horizontal = UiConfigs.Padding.ScreenHorizontal)
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
internal fun ProfileHeaderBg(modifier: Modifier = Modifier, userPhoto: String? = null) {
    val context = LocalContext.current
    val hasUserPhoto = !userPhoto.isNullOrBlank()

    Box(modifier) {
        if (hasUserPhoto) {
            // 有用户照片时，显示用户照片作为背景
            val photoUrl = getCdnImageUrl(userPhoto, width = 1024)
            AsyncImage(
                modifier = Modifier.fillMaxSize(),
                model = ImageRequest.Builder(context).data(photoUrl).build(),
                contentDescription = null,
                contentScale = ContentScale.Crop,
                alignment = Alignment.TopCenter,
                placeholder = painterResource(R.drawable.img_profile_header_bg),
                error = painterResource(R.drawable.img_profile_header_bg),
            )

            Spacer(
                modifier =
                    Modifier.matchParentSize()
                        .background(
                            brush =
                                Brush.verticalGradient(
                                    0f to HeartColor.primaryColor.copy(.0f),
                                    .25f to HeartColor.primaryColor,
                                )
                        )
            )
        } else {
            // 没有用户照片时，保持现状（显示默认背景图）
            AsyncImage(
                modifier = Modifier.fillMaxWidth(),
                model = R.drawable.img_profile_header_bg,
                contentDescription = null,
            )

            Box(
                modifier =
                    Modifier.matchParentSize()
                        .background(
                            brush =
                                Brush.verticalGradient(
                                    colors =
                                        listOf(
                                            HeartColor.primaryColor.copy(.0f),
                                            HeartColor.primaryColor.copy(.7f),
                                            HeartColor.primaryColor.copy(.9f),
                                        )
                                )
                        )
            )
        }
    }
}

private data class BannerContent(
    val title: String,
    val subtitle: String,
    val showActionButton: Boolean,
    val buttonText: String,
)

/**
 * Premium Banner 组件。
 *
 * 使用范围：个人页（Me/Profile）区块内，用于展示订阅状态并引导用户查看/续费/激活会员。
 * 预期视觉效果：圆角卡片、紫色径向渐变背景、左右浮动粒子动画、标题/副标题 + 右侧 CTA 按钮。
 * 可配置项：status（订阅状态）、purchaseTime/expireTime（展示用日期）、onClick（点击整卡或按钮的回调）。
 */
@Composable
internal fun PremiumBanner(
    status: String? = null,
    purchaseTime: String? = null,
    expireTime: String? = null,
    onClick: () -> Unit = {},
) {
    var lastClickTimePremium by remember { mutableLongStateOf(0L) }

    val subscribedTitle = stringResource(R.string.profile_premium_banner_title_subscribed)
    val expiringSoonTitle = stringResource(R.string.profile_premium_banner_title_expiring_soon)
    val upgradeTitle = stringResource(R.string.profile_premium_banner_title_upgrade)
    val unlockSubtitle = stringResource(R.string.profile_premium_banner_subtitle_unlock)
    val keepPremiumButton = stringResource(R.string.profile_premium_banner_button_keep_premium)
    val viewButton = stringResource(R.string.profile_premium_banner_button_view)
    val activateButton = stringResource(R.string.profile_premium_banner_button_activate)
    val memberSinceFormat = stringResource(R.string.profile_premium_banner_subtitle_member_since)
    val expiresOnFormat = stringResource(R.string.profile_premium_banner_subtitle_expires_on)

    val bannerContent =
        remember(
            status,
            purchaseTime,
            expireTime,
            subscribedTitle,
            expiringSoonTitle,
            upgradeTitle,
            unlockSubtitle,
            keepPremiumButton,
            activateButton,
            memberSinceFormat,
            expiresOnFormat,
        ) {
            when (status) {
                VipStatus.UI_SUBSCRIBED -> {
                    val dateText = purchaseTime?.takeIf { it.isNotEmpty() } ?: ""
                    BannerContent(
                        title = subscribedTitle,
                        subtitle = memberSinceFormat.format(dateText),
                        showActionButton = true,
                        buttonText = viewButton,
                    )
                }

                VipStatus.UI_SUBSCRIBED_EXPIRE_SOON -> {
                    val dateText = expireTime?.takeIf { it.isNotEmpty() } ?: ""
                    BannerContent(
                        title = expiringSoonTitle,
                        subtitle = expiresOnFormat.format(dateText),
                        showActionButton = true,
                        buttonText = keepPremiumButton,
                    )
                }

                else -> {
                    BannerContent(
                        title = upgradeTitle,
                        subtitle = unlockSubtitle,
                        showActionButton = true,
                        buttonText = activateButton,
                    )
                }
            }
        }

    Box(
        modifier =
            Modifier.fillMaxWidth()
                .clip(RoundedCornerShape(UiConfigs.MePage.SectionBannerCornerRadius))
                .background(MaterialTheme.colorScheme.surface)
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
        LeftParticleEffects()

        var boxSize by remember { mutableStateOf(Size.Zero) }

        val backgroundBrush =
            remember(boxSize) {
                if (boxSize == Size.Zero) {
                    Brush.radialGradient(
                        colors = listOf(Color.Transparent, Color.Transparent),
                        radius = 1f,
                    )
                } else {
                    val minSize = min(boxSize.width, boxSize.height)
                    val radius = max(minSize * .8f, 1f)
                    Brush.radialGradient(
                        colors =
                            listOf(
                                UiConfigs.Colors.GradientStart.copy(.5f),
                                UiConfigs.Colors.GradientStart.copy(.2f),
                                Color.Transparent,
                                Color.Transparent,
                            ),
                        center = Offset(boxSize.width / 2f, boxSize.height / 2f),
                        radius = radius,
                    )
                }
            }

        Row(
            modifier =
                Modifier.fillMaxSize()
                    .background(brush = backgroundBrush)
                    .onSizeChanged { size ->
                        boxSize = Size(size.width.toFloat(), size.height.toFloat())
                    }
                    .padding(
                        start = UiConfigs.MePage.SectionBannerHorizontalPadding,
                        end = UiConfigs.MePage.SectionBannerHorizontalPadding,
                    )
                    .align(Alignment.CenterStart),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.Center,
                horizontalAlignment = Alignment.Start,
            ) {
                Text(
                    text = bannerContent.title,
                    fontSize = 14.sp,
                    lineHeight = 14.sp,
                    fontWeight = FontWeight(700),
                    color = Color(0xFFFFFFFF),
                    textAlign = TextAlign.Start,
                )

                Text(
                    text = bannerContent.subtitle,
                    fontSize = 12.sp,
                    lineHeight = 12.sp,
                    fontWeight = FontWeight(500),
                    color = UiConfigs.Colors.VipSecondaryText,
                    textAlign = TextAlign.Start,
                )
            }
            if (bannerContent.showActionButton) {
                ActionButton(
                    modifier = Modifier,
                    onClick = onClick,
                    buttonText = bannerContent.buttonText,
                )
            }
        }

        RightParticleEffects()
    }
}

@Composable
internal fun PurpleStar(modifier: Modifier = Modifier) {
    Box(
        modifier.background(
            brush =
                Brush.radialGradient(
                    colors =
                        listOf(
                            UiConfigs.Colors.GradientStart.copy(.5f),
                            UiConfigs.Colors.GradientStart.copy(.3f),
                            Color.Transparent,
                        )
                )
        )
    )
}

@Composable
internal fun GoldDot(modifier: Modifier = Modifier) {
    Box(modifier.clip(CircleShape).background(Color(0xFFFFC93F)))
}

@Composable
private fun LeftParticleEffects() {
    ParticleEffects(
        initialXMin = 0f,
        initialXMax = 0.5f,
        durationBase = 3000,
    ) { particle, containerSize ->
        FloatingParticle(particle = particle, containerSize = containerSize)
    }
}

@Composable
private fun RightParticleEffects() {
    ParticleEffects(
        initialXMin = 0.5f,
        initialXMax = 1f,
        durationBase = 2500,
    ) { particle, containerSize ->
        FloatingGoldDot(particle = particle, containerSize = containerSize)
    }
}

@Composable
private fun ParticleEffects(
    initialXMin: Float,
    initialXMax: Float,
    durationBase: Int,
    content: @Composable (ParticleConfig, Size) -> Unit,
) {
    val density = LocalDensity.current
    var containerSize by remember { mutableStateOf(Size.Zero) }

    val particleCount = 12
    val particles =
        remember(particleCount, initialXMin, initialXMax, durationBase) {
            (0 until particleCount).map { index ->
                ParticleConfig(
                    initialX = initialXMin + Random.nextFloat() * (initialXMax - initialXMin),
                    initialY = -0.2f - (index * 0.15f),
                    size = (6f + Random.nextFloat() * 10f).dp,
                    alpha = 0.05f + Random.nextFloat() * 0.45f,
                    duration = (durationBase + Random.nextInt(2000)).toInt(),
                    delay = (index * 200) + Random.nextInt(300),
                )
            }
        }

    Box(
        modifier =
            Modifier.fillMaxSize().onSizeChanged { size ->
                with(density) {
                    containerSize = Size(size.width.toDp().value, size.height.toDp().value)
                }
            }
    ) {
        if (containerSize.width > 0 && containerSize.height > 0) {
            particles.forEach { particle ->
                content(particle, containerSize)
            }
        }
    }
}

@Composable
private fun FloatingParticle(particle: ParticleConfig, containerSize: Size) {
    val infiniteTransition =
        rememberInfiniteTransition(label = "particle_float_${particle.hashCode()}")

    val animateY by
        infiniteTransition.animateFloat(
            initialValue = particle.initialY,
            targetValue = 1.2f,
            animationSpec =
                infiniteRepeatable(
                    animation =
                        tween(
                            particle.duration,
                            delayMillis = particle.delay,
                            easing = LinearEasing,
                        ),
                    repeatMode = RepeatMode.Restart,
                ),
            label = "float_y",
        )

    val animateX by
        infiniteTransition.animateFloat(
            initialValue = -0.3f,
            targetValue = 0.3f,
            animationSpec =
                infiniteRepeatable(
                    animation =
                        tween(
                            particle.duration / 2,
                            delayMillis = particle.delay,
                            easing = LinearEasing,
                        ),
                    repeatMode = RepeatMode.Reverse,
                ),
            label = "float_x",
        )

    val animateScale by
        infiniteTransition.animateFloat(
            initialValue = 0.6f,
            targetValue = 1.2f,
            animationSpec =
                infiniteRepeatable(
                    animation =
                        tween(
                            (800 + Random.nextInt(400)).toInt(),
                            delayMillis = particle.delay,
                            easing = LinearEasing,
                        ),
                    repeatMode = RepeatMode.Reverse,
                ),
            label = "scale",
        )

    val currentX = particle.initialX * containerSize.width + animateX * containerSize.width * 0.4f
    val currentY = animateY * containerSize.height

    Box(
        modifier =
            Modifier.offset(x = currentX.dp, y = currentY.dp)
                .alpha(particle.alpha)
                .size(particle.size * animateScale)
    ) {
        PurpleStar(modifier = Modifier.fillMaxSize())
    }
}

@Composable
private fun FloatingGoldDot(particle: ParticleConfig, containerSize: Size) {
    val infiniteTransition =
        rememberInfiniteTransition(label = "gold_dot_float_${particle.hashCode()}")

    val animateY by
        infiniteTransition.animateFloat(
            initialValue = particle.initialY,
            targetValue = 1.2f,
            animationSpec =
                infiniteRepeatable(
                    animation =
                        tween(
                            particle.duration,
                            delayMillis = particle.delay,
                            easing = LinearEasing,
                        ),
                    repeatMode = RepeatMode.Restart,
                ),
            label = "float_y",
        )

    val animateX by
        infiniteTransition.animateFloat(
            initialValue = -0.2f,
            targetValue = 0.2f,
            animationSpec =
                infiniteRepeatable(
                    animation =
                        tween(
                            particle.duration / 2,
                            delayMillis = particle.delay,
                            easing = LinearEasing,
                        ),
                    repeatMode = RepeatMode.Reverse,
                ),
            label = "float_x",
        )

    val animateScale by
        infiniteTransition.animateFloat(
            initialValue = 0.6f,
            targetValue = 1.2f,
            animationSpec =
                infiniteRepeatable(
                    animation =
                        tween(
                            (800 + Random.nextInt(400)).toInt(),
                            delayMillis = particle.delay,
                            easing = LinearEasing,
                        ),
                    repeatMode = RepeatMode.Reverse,
                ),
            label = "scale",
        )

    val currentX = particle.initialX * containerSize.width + animateX * containerSize.width * 0.3f
    val currentY = animateY * containerSize.height

    Box(
        modifier =
            Modifier.offset(x = currentX.dp, y = currentY.dp)
                .alpha(particle.alpha)
                .size(particle.size * animateScale)
    ) {
        GoldDot(modifier = Modifier.fillMaxSize())
    }
}

private data class ParticleConfig(
    val initialX: Float,
    val initialY: Float,
    val size: Dp,
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
    }
}

@Composable
internal fun ActionButton(
    modifier: Modifier = Modifier,
    onClick: () -> Unit = {},
    buttonText: String = stringResource(R.string.profile_premium_banner_button_activate),
) {
    val borderBrush =
        Brush.horizontalGradient(colors = listOf(Color(0xFFC2F7FD), Color(0xFFC2F7FD)))

    val iconRes = R.drawable.icon_gold_heart

    ElevatedButton(
        onClick = onClick,
        modifier = modifier,
        shape = RoundedCornerShape(30.dp),
        colors =
            ButtonDefaults.buttonColors(
                containerColor = Color(0xFF1F1F1F),
                contentColor = Color.White,
                disabledContainerColor = Color(0xFF1F1F1F).copy(alpha = 0.6f),
                disabledContentColor = Color.White.copy(alpha = 0.6f),
            ),
        elevation =
            ButtonDefaults.buttonElevation(
                defaultElevation = 4.dp,
                pressedElevation = 2.dp,
                disabledElevation = 0.dp,
            ),
        border = BorderStroke(width = 1.dp, brush = borderBrush),
    ) {
        Image(
            painter = painterResource(iconRes),
            contentDescription = null,
            modifier = Modifier.size(24.dp),
        )
        Spacer(Modifier.width(10.dp))
        Text(
            text =
                buildAnnotatedString {
                    withStyle(
                        style =
                            SpanStyle(
                                brush =
                                    Brush.horizontalGradient(
                                        colors = listOf(Color(0xFFFFEECC), Color(0xFFAD9515))
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

@Preview
@Composable
private fun PreviewActionButton() {
    Column {
        ActionButton(modifier = Modifier.size(170.dp, 48.dp))
        ActionButton(
            modifier = Modifier.size(200.dp, 56.dp),
            buttonText = stringResource(R.string.profile_premium_banner_button_keep_premium),
        )
    }
}

@Preview
@Composable
private fun PreviewPremiumBanner() {
    PremiumBanner()
}
