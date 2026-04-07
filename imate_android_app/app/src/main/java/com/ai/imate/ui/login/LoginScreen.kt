package com.ai.imate.ui.login

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.material3.ripple
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.core.ui.theme.IMateTheme
import com.ai.imate.R
import kotlin.random.Random

private val LoginGradientTop = Color(0xFF0B0B15)
private val LoginGradientBottom = Color(0xFF000000)
private val InfoBoxBorder = Color(0x33FFFFFF)
private val InfoHighlight = Color(0xFF6EB7FF)
private val GoogleButtonStart = Color(0xFF569AFF)
private val GoogleButtonEnd = Color(0xFF3E80C2)
private val FooterMuted = Color(0xFF9AA0A6)
private val TaglineColor = Color(0xFFB0B8C1)

@Composable
fun LoginScreen(
    isSigningIn: Boolean,
    onContinueWithGoogle: () -> Unit,
    onTermsClick: () -> Unit,
    onPrivacyClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Box(
        modifier
            .fillMaxSize()
            .background(Brush.verticalGradient(listOf(LoginGradientTop, LoginGradientBottom)))
    ) {
        StarfieldBackdrop(Modifier.fillMaxSize())
        Column(
            modifier =
                Modifier
                    .fillMaxSize()
                    .statusBarsPadding()
                    .navigationBarsPadding()
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = 28.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Spacer(Modifier.height(40.dp))
            Image(
                painter = painterResource(R.drawable.imate_logo),
                contentDescription = stringResource(R.string.login_logo_content_description),
                modifier =
                    Modifier
                        .height(140.dp)
                        .fillMaxWidth(),
                contentScale = ContentScale.Fit,
            )
            Spacer(Modifier.height(24.dp))
            Text(
                text = stringResource(R.string.login_app_name),
                color = Color.White,
                fontSize = 34.sp,
                fontWeight = FontWeight.Bold,
                letterSpacing = (-0.5).sp,
            )
            Spacer(Modifier.height(8.dp))
            Text(
                text = stringResource(R.string.login_tagline),
                color = TaglineColor,
                fontSize = 16.sp,
                fontWeight = FontWeight.Normal,
            )
            Spacer(Modifier.height(40.dp))
            InfoCard()
            Spacer(Modifier.height(48.dp))
            GoogleSignInButton(
                enabled = !isSigningIn,
                isLoading = isSigningIn,
                onClick = onContinueWithGoogle,
            )
            Spacer(Modifier.height(56.dp))
            FooterLinks(onTermsClick = onTermsClick, onPrivacyClick = onPrivacyClick)
            Spacer(Modifier.height(8.dp))
            Text(
                text = stringResource(R.string.login_disclaimer),
                color = FooterMuted.copy(alpha = 0.85f),
                fontSize = 12.sp,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(horizontal = 8.dp),
            )
            Spacer(Modifier.height(16.dp))
        }
    }
}

@Composable
private fun InfoCard() {
    val infoText = buildAnnotatedString {
        append(stringResource(R.string.login_info_prefix))
        withStyle(SpanStyle(color = InfoHighlight, fontWeight = FontWeight.Bold)) {
            append(stringResource(R.string.login_info_highlight))
        }
        append(stringResource(R.string.login_info_suffix))
    }
    Text(
        text = infoText,
        color = Color.White,
        fontSize = 15.sp,
        lineHeight = 22.sp,
        textAlign = TextAlign.Center,
        modifier =
            Modifier
                .fillMaxWidth()
                .border(1.dp, InfoBoxBorder, RoundedCornerShape(16.dp))
                .background(Color(0x33000000), RoundedCornerShape(16.dp))
                .padding(vertical = 18.dp, horizontal = 20.dp),
    )
}

@Composable
private fun GoogleSignInButton(
    enabled: Boolean,
    isLoading: Boolean,
    onClick: () -> Unit,
) {
    val interactionSource = remember { MutableInteractionSource() }
    val label = stringResource(R.string.login_continue_google)
    Box(
        modifier =
            Modifier
                .fillMaxWidth()
                .height(56.dp)
                .shadow(
                    elevation = 12.dp,
                    shape = RoundedCornerShape(28.dp),
                    spotColor = GoogleButtonStart.copy(alpha = 0.65f),
                )
                .clip(RoundedCornerShape(28.dp))
                .background(Brush.horizontalGradient(listOf(GoogleButtonStart, GoogleButtonEnd)))
                .semantics {
                    role = Role.Button
                    contentDescription = label
                }
                .clickable(
                    interactionSource = interactionSource,
                    indication = ripple(color = Color.White.copy(alpha = 0.25f)),
                    enabled = enabled,
                    onClick = onClick,
                ),
        contentAlignment = Alignment.Center,
    ) {
        if (isLoading) {
            CircularProgressIndicator(
                modifier = Modifier.size(28.dp),
                color = Color.White,
                strokeWidth = 2.dp,
            )
        } else {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.Center,
            ) {
                Text(
                    text = "G",
                    color = Color.White,
                    fontSize = 22.sp,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(end = 12.dp),
                )
                Text(
                    text = label,
                    color = Color.White,
                    fontSize = 17.sp,
                    fontWeight = FontWeight.SemiBold,
                )
            }
        }
    }
}

@Composable
private fun FooterLinks(
    onTermsClick: () -> Unit,
    onPrivacyClick: () -> Unit,
) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.Center,
    ) {
        Text(
            text = stringResource(R.string.login_terms),
            color = FooterMuted,
            fontSize = 13.sp,
            modifier =
                Modifier.clickable(onClick = onTermsClick).padding(horizontal = 4.dp, vertical = 8.dp),
        )
        Text(text = " | ", color = FooterMuted.copy(alpha = 0.5f), fontSize = 13.sp)
        Text(
            text = stringResource(R.string.login_privacy),
            color = FooterMuted,
            fontSize = 13.sp,
            modifier =
                Modifier.clickable(onClick = onPrivacyClick).padding(horizontal = 4.dp, vertical = 8.dp),
        )
    }
}

@Composable
private fun StarfieldBackdrop(modifier: Modifier = Modifier) {
    val stars = remember {
        val r = Random(42)
        List(120) {
            Triple(r.nextFloat(), r.nextFloat(), r.nextFloat() * 1.8f + 0.4f)
        }
    }
    Canvas(modifier) {
        val w = size.width
        val h = size.height
        stars.forEach { (nx, ny, radius) ->
            val alpha = 0.25f + (nx + ny) * 0.35f
            drawCircle(
                color = Color.White.copy(alpha = alpha.coerceIn(0.2f, 1f)),
                radius = radius * 3f,
                center = Offset(nx * w, ny * h),
            )
        }
    }
}

@Preview(showBackground = true, heightDp = 800, widthDp = 400)
@Composable
private fun LoginScreenPreview() {
    IMateTheme {
        LoginScreen(
            isSigningIn = false,
            onContinueWithGoogle = {},
            onTermsClick = {},
            onPrivacyClick = {},
        )
    }
}
