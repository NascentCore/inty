package com.ai.imate.account.ui

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.ai.core.data.exceptions.GlobalErrorHandler
import com.ai.core.ui.theme.IMateTheme
import com.ai.intellimate.R
import com.ai.imate.utils.GoogleSignInHelper
import kotlinx.coroutines.launch

@Composable
fun LoginScreen(
    onContinueWithEmail: () -> Unit,
    onContinueWithGoogle: (String) -> Unit,
    modifier: Modifier = Modifier,
    onTermsClick: () -> Unit = {},
    onPrivacyClick: () -> Unit = {},
) {

    var isSignIngIn by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    val context = LocalContext.current

    LoginContent(
        isSigningIn = isSignIngIn,
        onContinueWithGoogle = {
            scope.launch {
                isSignIngIn = true
                try {
                    val tokenResult = GoogleSignInHelper.signInWithGoogle(context)
                    tokenResult
                        .onSuccess { onContinueWithGoogle(it) }
                        .onFailure { e ->
                            val ex = e as? Exception ?: Exception(e.message)
                            GlobalErrorHandler.sendError(ex)
                        }
                } finally {
                    isSignIngIn = false
                }
            }
        },
        onContinueWithEmail = onContinueWithEmail,
        onTermsClick = onTermsClick,
        onPrivacyClick = onPrivacyClick,
        modifier = modifier,
    )
}

@Composable
private fun LoginContent(
    isSigningIn: Boolean,
    onContinueWithGoogle: () -> Unit,
    onContinueWithEmail: () -> Unit,
    onTermsClick: () -> Unit,
    onPrivacyClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Box(
        modifier =
            modifier
                .fillMaxSize()
                .background(
                    brush =
                        Brush.linearGradient(
                            0f to Color(0xFF1C1523),
                            1f to Color(0xFF0E0B14),
                        ),
                )
                .padding(horizontal = 32.dp),
        contentAlignment = Alignment.Center,
    ) {
        Column(
            modifier = Modifier.fillMaxSize(),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.SpaceBetween,
        ) {
            Spacer(modifier = Modifier.height(72.dp))

            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Image(
                    painter = painterResource(R.drawable.imate_logo),
                    contentDescription = stringResource(R.string.login_logo_content_description),
                    modifier = Modifier.size(106.dp),
                )
                Spacer(modifier = Modifier.height(20.dp))
                Text(
                    text = stringResource(R.string.login_app_name),
                    style = MaterialTheme.typography.headlineLarge,
                    color = Color.White,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = MaterialTheme.typography.headlineLarge.letterSpacing * 2,
                )
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = stringResource(R.string.login_tagline),
                    style = MaterialTheme.typography.bodyMedium,
                    color = Color.White.copy(alpha = 0.5f),
                )
            }

            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Surface(
                    shape = RoundedCornerShape(32.dp),
                    color = Color(0xFF3C3445).copy(alpha = 0.5f),
                    tonalElevation = 0.dp,
                    shadowElevation = 0.dp,
                    modifier = Modifier.width(329.dp),
                ) {
                    Text(
                        text =
                            buildAnnotatedString {
                                append(stringResource(R.string.login_info_prefix))
                                withStyle(SpanStyle(color = Color(0xFF5BA3D4), fontWeight = FontWeight.SemiBold)) {
                                    append(stringResource(R.string.login_info_highlight))
                                }
                                append(stringResource(R.string.login_info_suffix))
                            },
                        modifier = Modifier.padding(horizontal = 24.dp, vertical = 20.dp),
                        color = Color.White.copy(alpha = 0.7f),
                        style = MaterialTheme.typography.bodyMedium,
                        textAlign = TextAlign.Center,
                    )
                }

                Spacer(modifier = Modifier.height(24.dp))

                Column(
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Box {
                        Button(
                            onClick = onContinueWithGoogle,
                            enabled = !isSigningIn,
                            colors =
                                ButtonDefaults.buttonColors(
                                    containerColor = Color(0xFF2C7BB6),
                                    contentColor = Color.White,
                                    disabledContainerColor = Color(0xFF2C7BB6).copy(alpha = 0.6f),
                                    disabledContentColor = Color.White.copy(alpha = 0.7f),
                                ),
                            shape = RoundedCornerShape(999.dp),
                            modifier =
                                Modifier
                                    .width(329.dp)
                                    .height(56.dp),
                        ) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Box(
                                    modifier =
                                        Modifier
                                            .size(22.dp)
                                            .clip(CircleShape)
                                            .background(Color.White.copy(alpha = 0.08f)),
                                    contentAlignment = Alignment.Center,
                                ) {
                                    Text(text = "G", fontWeight = FontWeight.Bold)
                                }
                                Spacer(modifier = Modifier.width(12.dp))
                                Text(
                                    text = stringResource(R.string.login_continue_google),
                                    style = MaterialTheme.typography.titleMedium,
                                    fontWeight = FontWeight.SemiBold,
                                )
                            }
                        }

                        if (isSigningIn) {
                            CircularProgressIndicator(
                                modifier =
                                    Modifier
                                        .align(Alignment.CenterEnd)
                                        .padding(end = 20.dp)
                                        .size(18.dp),
                                strokeWidth = 2.dp,
                                color = Color.White.copy(alpha = 0.9f),
                            )
                        }
                    }

                    TextButton(
                        onClick = onContinueWithEmail,
                        enabled = !isSigningIn,
                    ) {
                        Text(
                            text = stringResource(R.string.continue_with_email),
                            style = MaterialTheme.typography.bodyMedium,
                            color = Color.White.copy(alpha = 0.35f),
                            textDecoration = TextDecoration.Underline,
                        )
                    }

                }
            }

            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier.padding(bottom = 32.dp),
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = stringResource(R.string.login_terms),
                        style = MaterialTheme.typography.labelMedium,
                        color = Color.White.copy(alpha = 0.35f),
                        modifier = Modifier.clickable(onClick = onTermsClick),
                    )
                    Spacer(modifier = Modifier.width(16.dp))
                    Box(
                        modifier =
                            Modifier
                                .width(1.dp)
                                .height(12.dp)
                                .background(Color.White.copy(alpha = 0.15f)),
                    )
                    Spacer(modifier = Modifier.width(16.dp))
                    Text(
                        text = stringResource(R.string.login_privacy),
                        style = MaterialTheme.typography.labelMedium,
                        color = Color.White.copy(alpha = 0.35f),
                        modifier = Modifier.clickable(onClick = onPrivacyClick),
                    )
                }
                Spacer(modifier = Modifier.height(12.dp))
                Text(
                    text = stringResource(R.string.login_disclaimer),
                    style = MaterialTheme.typography.labelSmall,
                    color = Color.White.copy(alpha = 0.2f),
                    textAlign = TextAlign.Center,
                )
            }
        }
    }
}

@Preview(showBackground = true, heightDp = 800, widthDp = 400)
@Composable
private fun LoginScreenPreview() {
    IMateTheme {
        LoginContent(
            isSigningIn = false,
            onContinueWithGoogle = {},
            onContinueWithEmail = {},
            onTermsClick = {},
            onPrivacyClick = {},
        )
    }
}
