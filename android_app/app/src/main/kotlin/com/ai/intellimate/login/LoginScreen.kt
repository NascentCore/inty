package com.ai.intellimate.login

import ai.sxwl.android.design.AntiClick
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.ToastUtils
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
import androidx.credentials.exceptions.GetCredentialCancellationException
import androidx.credentials.exceptions.GetCredentialException
import androidx.credentials.exceptions.GetCredentialInterruptedException
import androidx.credentials.exceptions.NoCredentialException
import com.ai.intellimate.R
import com.ai.intellimate.ui.components.GoogleLoginButton
import com.ai.intellimate.ui.components.LoginCloseButton
import com.ai.intellimate.ui.components.LogoImage
import com.ai.intellimate.ui.components.PolicyText
import com.ai.intellimate.ui.components.WelcomeSubtitle
import com.ai.intellimate.ui.components.WelcomeTitle
import com.ai.intellimate.utils.CredentialManagerHelper
import kotlinx.coroutines.launch

/** 登录屏幕 */
@Composable
internal fun LoginScreen(
    onClose: () -> Unit = {},
    onGoogleLoginSuccess: (idToken: String) -> Unit,
) {
    val context = LocalContext.current
    var lastClickTime by remember { mutableLongStateOf(0L) }
    var isLoading by remember { mutableStateOf(false) }
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
                        LogUtils.i("Credential Manager sign-in successful")
                        onGoogleLoginSuccess(idToken)
                    },
                    onFailure = { exception ->
                        // 检查是否为用户取消操作，如果是则不显示错误提示
                        when (exception) {
                            is GetCredentialCancellationException -> {
                                // 用户取消登录，不显示错误提示
                                LogUtils.i("User cancelled the login process")
                                return@fold
                            }
                            is GetCredentialInterruptedException -> {
                                // 登录过程被中断，不显示错误提示
                                LogUtils.i("Login process was interrupted")
                                return@fold
                            }
                            is NoCredentialException -> {
                                val errorMessage =
                                    context.getString(R.string.no_credentials_available)
                                LogUtils.e("Credential Manager sign-in failed: $errorMessage")
                                // 显示错误提示
                                coroutineScope.launch { ToastUtils.showShort(errorMessage) }
                            }
                            is GetCredentialException -> {
                                val errorMessage = context.getString(R.string.get_credential_failed)
                                LogUtils.e("Credential Manager sign-in failed: $errorMessage")
                                // 显示错误提示
                                coroutineScope.launch { ToastUtils.showShort(errorMessage) }
                            }
                            else -> {
                                val errorMessage = context.getString(R.string.login_failed)
                                LogUtils.e("Credential Manager sign-in failed: $errorMessage")
                                // 显示错误提示
                                coroutineScope.launch { ToastUtils.showShort(errorMessage) }
                            }
                        }
                    },
                )
            } finally {
                isLoading = false
            }
        }
    }

    Box(modifier = Modifier.fillMaxSize().background(Color.Black.copy(0.6f))) {
        Column(
            modifier =
                Modifier.fillMaxWidth()
                    .align(Alignment.BottomCenter)
                    .background(
                        brush =
                            Brush.verticalGradient(
                                colors = listOf(Color(0xFF322341), Color(0xFF120E24))
                            ),
                        shape = RoundedCornerShape(24.dp, 24.dp, 0.dp, 0.dp),
                    ),
            horizontalAlignment = Alignment.CenterHorizontally,
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
            GoogleLoginButton(isLoading = isLoading, onLoginClick = { performGoogleSignIn() })

            Spacer(modifier = Modifier.height(24.dp))

            // 隐私政策文本
            PolicyText()

            Spacer(modifier = Modifier.height(60.dp))
        }
    }
}

@Preview(backgroundColor = 0xFFffffff, showBackground = true)
@Composable
private fun LoginScreenPreview() {
    LoginScreen(onGoogleLoginSuccess = {})
}
