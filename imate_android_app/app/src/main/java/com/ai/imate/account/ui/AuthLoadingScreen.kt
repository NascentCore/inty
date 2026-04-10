package com.ai.imate.account.ui

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.ai.intellimate.R
import com.ai.imate.account.ui.viewmodel.LoginViewModel
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.filter
import kotlinx.coroutines.flow.first

@Composable
fun AuthLoadingScreen(
    onLoginSuccess: () -> Unit,
    viewModel: LoginViewModel = viewModel()
) {
    val progress = remember { Animatable(0f) }

    LaunchedEffect(Unit) {
        coroutineScope {
            progress.snapTo(0f)

            val atLeastTwoSecondsTo08 = async {
                progress.animateTo(
                    targetValue = 0.8f,
                    animationSpec = tween(durationMillis = 2000, easing = LinearEasing),
                )
            }
            val loginTrue = async { viewModel.isLogin.filter { it }.first() }

            atLeastTwoSecondsTo08.await()
            loginTrue.await()

            progress.animateTo(
                targetValue = 1.0f,
                animationSpec = tween(durationMillis = 100, easing = LinearEasing),
            )
            onLoginSuccess()
        }
    }

    Box(
        modifier =
            Modifier
                .fillMaxSize()
                .background(
                    brush =
                        Brush.linearGradient(
                            0f to Color(0xFF1C1523),
                            1f to Color(0xFF0E0B14),
                        ),
                ),
    ) {
        Box(
            modifier =
                Modifier
                    .fillMaxSize()
                    .background(
                        brush =
                            Brush.radialGradient(
                                0f to Color(0xFF2C7BB6).copy(alpha = 0.18f),
                                0.65f to Color(0xFF1C1523).copy(alpha = 0f),
                            ),
                    ),
        )

        Canvas(modifier = Modifier.fillMaxSize()) {
            val c = center
            fun dp(value: Float) = value.dp.toPx()

            drawCircle(
                color = Color(0xFF2C7BB6).copy(alpha = 0.21f),
                radius = dp(317.28f / 2f),
                center = c,
                style = Stroke(width = dp(1.5f)),
            )
            drawCircle(
                color = Color(0xFF2C7BB6).copy(alpha = 0.44f),
                radius = dp(278.92f / 2f),
                center = c,
                style = Stroke(width = dp(1.5f)),
            )
            drawCircle(
                color = Color(0xFF2C7BB6).copy(alpha = 0.73f),
                radius = dp(130.56f / 2f),
                center = c,
                style = Stroke(width = dp(1.5f)),
            )
            drawCircle(
                color = Color(0xFF2C7BB6).copy(alpha = 0.80f),
                radius = dp(80f / 2f),
                center = c,
                style = Stroke(width = dp(1.5f)),
            )

            data class Dot(val x: Float, val y: Float, val size: Float, val color: Color, val alpha: Float)

            val dots =
                listOf(
                    Dot(315.40f, 362.22f, 7.295f, Color(0xFF2C7BB6), 0.86f),
                    Dot(275.23f, 376.17f, 4.475f, Color(0xFF5BA3D4), 0.90f),
                    Dot(309.46f, 400.99f, 3.63f, Color(0xFFC3F0FD), 0.02f),
                    Dot(332.66f, 434.36f, 2.265f, Color(0xFF7EC8E3), 0.06f),
                    Dot(281.74f, 450.74f, 2.22f, Color(0xFF5BA3D4), 0.05f),
                    Dot(266.24f, 462.28f, 4.61f, Color(0xFFC3F0FD), 0.24f),
                    Dot(266.58f, 503.72f, 1.663f, Color(0xFF7EC8E3), 0.05f),
                    Dot(216.42f, 436.29f, 8.586f, Color(0xFF2C7BB6), 0.84f),
                    Dot(219.17f, 512.98f, 1.599f, Color(0xFF5BA3D4), 0.03f),
                    Dot(193.67f, 448.89f, 5.936f, Color(0xFFC3F0FD), 0.44f),
                    Dot(186.67f, 416.81f, 3.032f, Color(0xFF7EC8E3), 0.46f),
                    Dot(160.50f, 432.61f, 2.262f, Color(0xFF5BA3D4), 0.06f),
                    Dot(153.61f, 420.31f, 3.494f, Color(0xFFC3F0FD), 0.60f),
                    Dot(112.35f, 424.50f, 2.184f, Color(0xFF2C7BB6), 0.21f),
                    Dot(88.62f, 416.82f, 4.675f, Color(0xFF5BA3D4), 0.60f),
                    Dot(141.24f, 378.28f, 8.445f, Color(0xFFC3F0FD), 0.85f),
                    Dot(101.31f, 376.96f, 5.847f, Color(0xFF7EC8E3), 0.60f),
                    Dot(93.50f, 347.75f, 3.228f, Color(0xFF5BA3D4), 0.13f),
                    Dot(148.56f, 347.06f, 8.857f, Color(0xFFC3F0FD), 0.69f),
                    Dot(96.56f, 265.56f, 4.914f, Color(0xFF5BA3D4), 0.44f),
                    Dot(132.38f, 277.77f, 2.574f, Color(0xFFC3F0FD), 0.13f),
                    Dot(177.83f, 312.93f, 4.195f, Color(0xFF2C7BB6), 0.49f),
                    Dot(176.42f, 256.80f, 7.49f, Color(0xFF5BA3D4), 0.90f),
                    Dot(193.85f, 293.92f, 5.107f, Color(0xFFC3F0FD), 0.77f),
                    Dot(213.55f, 305.28f, 3.858f, Color(0xFF2C7BB6), 0.13f),
                    Dot(265.16f, 267.22f, 3.338f, Color(0xFFC3F0FD), 0.15f),
                    Dot(234.26f, 322.25f, 5.126f, Color(0xFF7EC8E3), 0.32f),
                    Dot(259.35f, 317.66f, 2.139f, Color(0xFF2C7BB6), 0.51f),
                    Dot(281.86f, 331.66f, 8.999f, Color(0xFFC3F0FD), 0.90f),
                    Dot(295.92f, 348.30f, 2.646f, Color(0xFF7EC8E3), 0.03f),
                )

            dots.forEach { dot ->
                drawCircle(
                    color = dot.color.copy(alpha = dot.alpha),
                    radius = dp(dot.size / 2f),
                    center = androidx.compose.ui.geometry.Offset(dp(dot.x), dp(dot.y)),
                )
            }
        }

        Column(
            modifier = Modifier.align(Alignment.Center),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Image(
                painter = painterResource(R.drawable.imate_logo),
                contentDescription = stringResource(R.string.login_logo_content_description),
                modifier = Modifier.size(96.dp),
            )
            Spacer(modifier = Modifier.height(24.dp))
            Text(
                text = stringResource(R.string.login_app_name),
                color = Color.White,
                fontWeight = FontWeight.Bold,
                fontSize = 28.sp,
                lineHeight = 42.sp,
                letterSpacing = 7.sp,
                style = MaterialTheme.typography.headlineLarge,
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = stringResource(R.string.auth_loading_tagline),
                color = Color(0xFFC3F0FD).copy(alpha = 0.7f),
                fontSize = 13.sp,
                lineHeight = 19.5.sp,
                letterSpacing = 1.56.sp,
                style = MaterialTheme.typography.bodyMedium,
            )
        }

        Box(
            modifier =
                Modifier
                    .align(Alignment.BottomCenter)
                    .padding(start = 32.dp, end = 32.dp, bottom = 64.dp)
                    .width(329.dp)
                    .height(2.dp)
                    .clip(RoundedCornerShape(999.dp))
                    .background(Color(0xFF3C3445).copy(alpha = 0.8f)),
        ) {
            Box(
                modifier =
                    Modifier
                        .clip(RoundedCornerShape(999.dp))
                        .background(
                            brush =
                                Brush.horizontalGradient(
                                    0f to Color(0xFF2C7BB6),
                                    1f to Color(0xFF5BA3D4),
                                ),
                        )
                        .fillMaxWidth(progress.value.coerceIn(0f, 1f))
                        .height(2.dp),
            )
        }
    }
}
