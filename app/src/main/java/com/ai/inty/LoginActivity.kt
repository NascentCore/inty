package com.ai.inty

import android.content.Intent
import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
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
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.net.toUri
import androidx.lifecycle.lifecycleScope
import com.ai.inty.base.AntiClick
import com.ai.inty.base.BaseActivity
import com.ai.inty.base.ToastUtils
import com.ai.inty.base.noRippleClickable
import com.ai.inty.ui.theme.IntyTheme
import com.ai.inty.utils.CredentialManagerHelper
import com.ai.inty.utils.TextStyleUtils
import com.ai.inty.utils.UserProfileManager
import com.ai.inty.viewmodels.LoginActivityViewModel
import com.inty.utils.log.EasyLog
import com.therouter.TheRouter
import com.therouter.router.Route
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/**
 * 登录页面
 * 使用最新的 Credential Manager API 进行 Google 登录
 */
@Route(path = Constant.ROUTE_LOGIN)
class LoginActivity : BaseActivity() {

    private val viewModel: LoginActivityViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        setContent {
            IntyTheme {
                LoginScreen(
                    onClose = {
                        finish()
                    },
                    onGoogleLoginSuccess = { idToken ->
                        viewModel.onGoogleLoginSuccess(idToken)
                    }
                )
            }
        }

        lifecycleScope.launch {
            viewModel.finishActivity.collect {
                if (it) {
                    checkAndShowRegInfo()
                    finish()
                }
            }
        }
    }

    private fun checkAndShowRegInfo() {
        val userProfile = UserProfileManager.getUserProfile()
        if (userProfile.gender.isNullOrEmpty()) {
            EasyLog.log("User has not set gender, showing RegInfoActivity")
            CoroutineScope(Dispatchers.Main).launch {
                delay(300)
                TheRouter.build(Constant.ROUTE_REG_INFO)
                    .navigation(this@LoginActivity)
            }
        } else {
            EasyLog.log("User has set gender, no need to show RegInfoActivity")
        }
    }
}

/**
 * 登录页面 UI 组件
 * 使用最新的 Credential Manager API
 */
@Composable
fun LoginScreen(
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
            Image(
                modifier = Modifier
                    .align(Alignment.End)
                    .padding(end = 16.dp, top = 16.dp)
                    .size(18.dp, 18.dp)
                    .noRippleClickable { onClose() },
                painter = painterResource(R.drawable.close),
                contentDescription = null,
            )

            Spacer(Modifier.height(12.dp))

            // Logo 图片
            Image(
                modifier = Modifier.size(width = 239.dp, height = 190.dp),
                painter = painterResource(R.drawable.group2085655930),
                contentScale = ContentScale.Crop,
                alignment = Alignment.TopCenter,
                contentDescription = ""
            )

            Spacer(modifier = Modifier.height(40.dp))

            // 欢迎文本
            Text(
                text = stringResource(R.string.welcome_to_intellimate),
                color = Color.White,
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold
            )

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = stringResource(R.string.create_account_or_login),
                color = Color.White.copy(alpha = 0.55f),
                fontSize = 14.sp,
                fontWeight = FontWeight.Normal
            )

            Spacer(modifier = Modifier.height(40.dp))

            // Google 登录按钮
            var selected by remember { mutableStateOf(false) }
            Button(
                onClick = {
                    if (selected) {
                        performGoogleSignIn()
                    } else {
                        coroutineScope.launch {
                            ToastUtils.showToast(context.getString(R.string.toast_check_terms_privacy))
                        }
                    }
                },
                modifier = Modifier.size(width = 300.dp, height = 56.dp),
                shape = RoundedCornerShape(30.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = Color.White,
                    disabledContainerColor = Color.White.copy(.7f)
                ),
                border = BorderStroke(1.dp, Color(0xFFEEEEEE)),
                contentPadding = PaddingValues(0.dp),
                enabled = !isLoading
            ) {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    Image(
                        painter = painterResource(id = R.drawable.google),
                        contentDescription = stringResource(R.string.content_desc_google_login),
                        modifier = Modifier
                            .align(Alignment.CenterStart)
                            .padding(start = 20.dp)
                            .size(24.dp)
                    )
                    Text(
                        text = stringResource(R.string.continue_with_google),
                        color = Color.Black,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.SemiBold
                    )

                    if (isLoading) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(24.dp),
                            color = Color.Black,
                            strokeWidth = 2.dp
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            // 隐私政策文本
            PolicyText(selected, { selected = it })

            Spacer(modifier = Modifier.height(60.dp))
        }
    }
}

/**
 * 隐私政策文本组件
 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun PolicyText(checked: Boolean, onCheckedChange: (Boolean) -> Unit) {
    val context = LocalContext.current
    val baseTextStyle = TextStyle(
        color = Color.White.copy(alpha = 0.35f),
        fontSize = 12.sp,
        fontWeight = FontWeight.Normal,
        textAlign = TextAlign.Center
    )

    Row(verticalAlignment = Alignment.CenterVertically) {
        Image(
            painter = painterResource(
                if (checked) R.drawable.checked else R.drawable.check_no
            ),
            contentDescription = null,
            modifier = Modifier.clickable { onCheckedChange(!checked) }
        )

        Spacer(Modifier.width(8.dp))

        Column(
            modifier = Modifier,
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = stringResource(R.string.by_continuing_agree_full),
                style = baseTextStyle
            )

            Spacer(Modifier.height(4.dp))

            Row {
                Text(
                    text = TextStyleUtils.createUnderlinedText(stringResource(R.string.terms_of_use)),
                    fontSize = 12.sp,
                    color = Color.White,
                    modifier = Modifier.noRippleClickable(onClick = {
                        val intent = Intent(
                            Intent.ACTION_VIEW,
                            context.getString(R.string.settings_str_user_agreement).toUri()
                        )
                        context.startActivity(intent)
                    })
                )

                Text(
                    text = stringResource(R.string.and_symbol),
                    color = Color.White.copy(alpha = 0.6f),
                    fontSize = 12.sp
                )

                Text(
                    text = TextStyleUtils.createUnderlinedText(stringResource(R.string.privacy_policy)),
                    fontSize = 12.sp,
                    color = Color.White,
                    modifier = Modifier.noRippleClickable(onClick = {
                        val intent = Intent(
                            Intent.ACTION_VIEW,
                            context.getString(R.string.settings_str_privacy_policy).toUri()
                        )
                        context.startActivity(intent)
                    })
                )
            }
        }
    }
}

@Preview(backgroundColor = 0xFFffffff, showBackground = true)
@Composable
fun LoginPreview() {
    LoginScreen(onGoogleLoginSuccess = {})
}