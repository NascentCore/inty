package com.ai.intellimate.explore.special

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.design.theme.HeartColor
import ai.sxwl.android.design.ui.HeartTopAppBar
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shadow
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.zIndex
import com.ai.intellimate.R
import kotlin.random.Random

/** 角色专区详情页面 */
@Composable
fun ThemedDetailScreen(
    viewModel: CollectionDetailVM,
    onBack: () -> Unit,
    onClickAgent: (AgentInfo) -> Unit,
) {
    val themeTitle by viewModel.themeTitle.collectAsState()
    val eventDescription by viewModel.eventDescription.collectAsState()
    val agents by viewModel.agents.collectAsState()
    val isChristmas by viewModel.isChristmas.collectAsState()

    Box(modifier = Modifier.fillMaxSize().background(HeartColor.primaryColor)) {
        Column(modifier = Modifier.fillMaxSize().zIndex(0f)) {
            HeartTopAppBar(
                title = themeTitle,
                onBack = onBack,
                titleTextStyle =
                    TextStyle(
                        fontSize = 20.sp,
                        color = Color.White,
                        fontWeight = FontWeight.Bold,
                        shadow =
                            Shadow(
                                color = Color(0xFF8C8992),
                                offset = Offset(5f, 3f),
                                blurRadius = 15f,
                            ),
                    ),
            )

            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(bottom = 16.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                item { EventCard(description = eventDescription, isChristmas = isChristmas) }

                items(agents) { agent ->
                    ThemedCharacterCard(agent = agent, onClick = { onClickAgent(agent) })
                }
            }
        }

        if (isChristmas) {
            Box(
                modifier =
                    Modifier.fillMaxSize()
                        .zIndex(1f)
            ) {
                SnowFallingEffect()
            }
        }
    }
}

@Composable
private fun SnowPiece(modifier: Modifier = Modifier) {
    val infiniteTransition = rememberInfiniteTransition(label = "snow_breathing")
    val breathingAlpha by
        infiniteTransition.animateFloat(
            initialValue = 0.6f,
            targetValue = 1.0f,
            animationSpec =
                infiniteRepeatable(
                    animation = tween(2000, easing = LinearEasing),
                    repeatMode = RepeatMode.Reverse,
                ),
            label = "breathing_alpha",
        )

    Box(
        modifier
            .alpha(breathingAlpha)
            .background(
                brush =
                    Brush.radialGradient(
                        colors = listOf(Color(0xCCFFFFFF), Color(0x66FFFFFF), Color.Transparent)
                    )
            ),
        contentAlignment = Alignment.Center,
    ) {
        Image(
            painter = painterResource(R.drawable.ic_snow_piece),
            contentDescription = null,
            modifier = Modifier.fillMaxSize(.7f),
            contentScale = ContentScale.Fit,
        )
    }
}

@Composable
private fun SnowFallingEffect() {
    val density = LocalDensity.current
    var containerSize by remember { mutableStateOf(Size.Zero) }

    val particleCount = 60
    val particles =
        remember(particleCount) {
            (0 until particleCount).map { index ->
                ParticleConfig(
                    initialX = Random.nextFloat(),
                    initialY = -0.2f - (index * 0.05f),
                    size = (40f + Random.nextFloat() * 37f).dp,
                    alpha = 0.2f + Random.nextFloat() * 0.6f,
                    duration = (6000 + Random.nextInt(4000)).toInt(),
                    delay = (index * 100) + Random.nextInt(150),
                )
            }
        }

    Box(
        modifier =
            Modifier.fillMaxSize()
                .onSizeChanged { layoutSize ->
                    with(density) {
                        containerSize = Size(layoutSize.width.toDp().value, layoutSize.height.toDp().value)
                    }
                }
    ) {
        if (containerSize.width > 0 && containerSize.height > 0) {
            particles.forEach { particle ->
                FloatingSnowParticle(particle = particle, containerSize = containerSize)
            }
        }
    }
}

@Composable
private fun FloatingSnowParticle(particle: ParticleConfig, containerSize: Size) {
    val infiniteTransition =
        rememberInfiniteTransition(label = "snow_particle_float_${particle.hashCode()}")

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
            initialValue = -0.25f,
            targetValue = 0.25f,
            animationSpec =
                infiniteRepeatable(
                    animation =
                        tween(
                            (particle.duration * 0.6).toInt(),
                            delayMillis = particle.delay,
                            easing = LinearEasing,
                        ),
                    repeatMode = RepeatMode.Reverse,
                ),
            label = "float_x",
        )

    val animateScale by
        infiniteTransition.animateFloat(
            initialValue = 0.7f,
            targetValue = 1.1f,
            animationSpec =
                infiniteRepeatable(
                    animation =
                        tween(
                            (1200 + Random.nextInt(600)).toInt(),
                            delayMillis = particle.delay,
                            easing = LinearEasing,
                        ),
                    repeatMode = RepeatMode.Reverse,
                ),
            label = "scale",
        )

    val currentX = particle.initialX * containerSize.width + animateX * containerSize.width * 0.35f
    val currentY = animateY * containerSize.height

    Box(
        modifier =
            Modifier.offset(x = currentX.dp, y = currentY.dp)
                .alpha(particle.alpha)
                .size(particle.size * animateScale)
    ) {
        SnowPiece(modifier = Modifier.fillMaxSize())
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
