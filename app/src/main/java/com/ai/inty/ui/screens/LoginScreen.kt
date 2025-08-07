package com.ai.inty.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.ai.inty.R
import com.ai.inty.base.AntiClick
import com.ai.inty.base.ToastUtils
import com.ai.inty.ui.components.GoogleLoginButton
import com.ai.inty.ui.components.LoginCloseButton
import com.ai.inty.ui.components.LogoImage
import com.ai.inty.ui.components.PolicyText
import com.ai.inty.ui.components.WelcomeSubtitle
import com.ai.inty.ui.components.WelcomeTitle
import com.ai.inty.utils.CredentialManagerHelper
import com.inty.utils.log.EasyLog
import kotlinx.coroutines.launch

/**
 * 登录屏幕
 */
@Composable
internal fun LoginScreen(
    onClose: () -> Unit = {},
    onGoogleLoginSuccess: (idToken: String) -> Unit,
) {
    val context = LocalContext.current
    var lastClickTime by remember { mutableLongStateOf(0L) }
    var isLoading by remember { mutableStateOf(false) }
    var selected by remember { mutableStateOf(false) }
    val coroutineScope = rememberCoroutineScope()

    // 使用新的 Credential Manager 登录
    fun performGoogleSignIn() {
        if (isLoading) return

        val currentTime = System.currentTimeMillis()
        if (!AntiClick.isValidClick(lastClickTime)) return
        lastClickTime = currentTime

        coroutineScope.launch {
            isLoading = true
            try {
                val result = CredentialManagerHelper.signInWithGoogle(context)
                result.fold(
                    onSuccess = { idToken ->
                        EasyLog.log("Credential Manager sign-in successful")
                        onGoogleLoginSuccess(idToken)
                    },
                    onFailure = { exception ->
                        val errorMessage = when (exception) {
                            is androidx.credentials.exceptions.NoCredentialException -> "No credentials available"
                            else -> "Login Failed: ${exception.message}"
                        }
                        EasyLog.log(
                            "Credential Manager sign-in failed: $errorMessage",
                            EasyLog.ERROR
                        )
                        // 显示错误提示
                        coroutineScope.launch {
                            ToastUtils.showToast(errorMessage)
                        }
                    }
                )
            } finally {
                isLoading = false
            }
        }
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black.copy(0.6f)),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .align(Alignment.BottomCenter)
                .background(
                    brush = Brush.verticalGradient(
                        colors = listOf(
                            Color(0xFF322341),
                            Color(0xFF120E24)
                        )
                    ),
                    shape = RoundedCornerShape(24.dp, 24.dp, 0.dp, 0.dp)
                ),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // 关闭按钮
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                LoginCloseButton(onClose = onClose)
            }

            Spacer(Modifier.height(12.dp))

            // Logo 图片
            LogoImage()

            Spacer(modifier = Modifier.height(40.dp))

            // 欢迎文本
            WelcomeTitle()

            Spacer(modifier = Modifier.height(8.dp))

            WelcomeSubtitle()

            Spacer(modifier = Modifier.height(40.dp))

            // Google 登录按钮
            GoogleLoginButton(
                isLoading = isLoading,
                isSelected = selected,
                onLoginClick = {
                    if (selected) {
                        performGoogleSignIn()
                    } else {
                        coroutineScope.launch {
                            ToastUtils.showToast(context.getString(R.string.toast_check_terms_privacy))
                        }
                    }
                }
            )

            Spacer(modifier = Modifier.height(24.dp))

            // 隐私政策文本
            PolicyText(selected, { selected = it })

            Spacer(modifier = Modifier.height(60.dp))
        }
    }
}

@Preview(backgroundColor = 0xFFffffff, showBackground = true)
@Composable
private fun LoginScreenPreview() {
    LoginScreen(onGoogleLoginSuccess = {})
}
