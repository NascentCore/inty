package com.ai.imate.account.ui

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.ai.core.ui.theme.IMateTheme
import com.ai.intellimate.R
import java.util.regex.Pattern

@Composable
fun EmailInputScreen(
    onBack: () -> Unit,
    onContinue: (String) -> Unit,
    initialEmail: String = "",
) {
    var email by rememberSaveable(initialEmail) { mutableStateOf(initialEmail) }
    var emailError by remember { mutableStateOf<String?>(null) }
    val invalidEmailErrorText = stringResource(R.string.invalid_email_format)
    val primary = MaterialTheme.colorScheme.primary
    val onBackground = MaterialTheme.colorScheme.onBackground

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
        Column(
            modifier =
                Modifier.fillMaxSize()
                    .padding(horizontal = 24.dp)
                    .padding(top = 60.dp, bottom = 40.dp)
                    .windowInsetsPadding(WindowInsets.navigationBars),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            IconButton(
                onClick = onBack,
                modifier = Modifier.align(Alignment.Start),
            ) {
                Icon(
                    imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                    contentDescription = stringResource(R.string.content_desc_back),
                    tint = onBackground,
                    modifier = Modifier.size(22.dp),
                )
            }

            Spacer(modifier = Modifier.height(40.dp))

            Text(
                text = stringResource(R.string.enter_email),
                color = onBackground,
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.fillMaxWidth(),
            )

            Spacer(modifier = Modifier.height(40.dp))

            OutlinedTextField(
                value = email,
                onValueChange = { newValue ->
                    if (newValue.length <= 50) {
                        email = newValue
                        emailError = null
                    }
                },
                modifier = Modifier.fillMaxWidth(),
                placeholder = {
                    Text(
                        text = stringResource(R.string.enter_email_placeholder),
                        color = onBackground.copy(alpha = 0.5f),
                    )
                },
                singleLine = true,
                keyboardOptions =
                    KeyboardOptions(keyboardType = KeyboardType.Email, imeAction = ImeAction.Next),
                colors =
                    OutlinedTextFieldDefaults.colors(
                        focusedTextColor = onBackground,
                        unfocusedTextColor = onBackground,
                        focusedBorderColor = primary,
                        unfocusedBorderColor = primary,
                        cursorColor = onBackground,
                    ),
                shape = RoundedCornerShape(30.dp),
                isError = emailError != null,
            )

            emailError?.let {
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = it,
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.fillMaxWidth().padding(start = 16.dp),
                )
            }

            Spacer(modifier = Modifier.height(32.dp))

            Button(
                onClick = {
                    if (email.isBlank() || !isValidEmail(email)) {
                        emailError = invalidEmailErrorText
                    } else {
                        onContinue(email)
                    }
                },
                modifier = Modifier.fillMaxWidth().height(56.dp),
                shape = RoundedCornerShape(30.dp),
                colors = ButtonDefaults.buttonColors(containerColor = primary),
            ) {
                Text(
                    text = stringResource(R.string.continue_button),
                    color = MaterialTheme.colorScheme.onPrimary,
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.SemiBold,
                )
            }

            Spacer(modifier = Modifier.weight(1f))

            Text(
                text = stringResource(R.string.login_disclaimer),
                style = MaterialTheme.typography.labelSmall,
                color = onBackground.copy(alpha = 0.35f),
            )
        }
    }
}

private fun isValidEmail(email: String): Boolean {
    val emailPattern =
        Pattern.compile(
            "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
            Pattern.CASE_INSENSITIVE,
        )
    return emailPattern.matcher(email).matches()
}


@Preview(showBackground = true)
@Composable
private fun EmailInputScreenPreview() {
    IMateTheme {
        EmailInputScreen(onBack = {}, onContinue = {})
    }
}
