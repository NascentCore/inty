package com.ai.intellimate.ui.components

import ai.sxwl.android.design.noRippleClickable
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.intellimate.R
import java.util.regex.Pattern

/** 登录页面关闭按钮组件 */
@Composable
internal fun LoginCloseButton(onClose: () -> Unit) {
    Image(
        modifier =
            Modifier.padding(end = 16.dp, top = 16.dp).size(18.dp, 18.dp).noRippleClickable {
                onClose()
            },
        painter = painterResource(R.drawable.close),
        contentDescription = null,
    )
}

/** Logo 图片组件 */
@Composable
internal fun LogoImage() {
    Image(
        modifier = Modifier.size(width = 239.dp, height = 190.dp),
        painter = painterResource(R.drawable.img_login_hi),
        contentScale = ContentScale.Crop,
        alignment = Alignment.TopCenter,
        contentDescription = "",
    )
}

/** 欢迎标题组件 */
@Composable
internal fun WelcomeTitle() {
    Text(
        text = stringResource(R.string.welcome_to_intellimate),
        color = Color.White,
        fontSize = 24.sp,
        fontWeight = FontWeight.Bold,
    )
}

/** 欢迎副标题组件 */
@Composable
internal fun WelcomeSubtitle() {
    Text(
        text = stringResource(R.string.create_account_or_login),
        color = Color.White.copy(alpha = 0.55f),
        fontSize = 14.sp,
        fontWeight = FontWeight.Normal,
    )
}

/** Google 登录按钮组件 */
@Composable
internal fun GoogleLoginButton(isLoading: Boolean, onLoginClick: () -> Unit) {
    Button(
        onClick = onLoginClick,
        modifier = Modifier.size(width = 300.dp, height = 56.dp),
        shape = RoundedCornerShape(30.dp),
        colors =
            ButtonDefaults.buttonColors(
                containerColor = Color.White,
                disabledContainerColor = Color.White.copy(.7f),
            ),
        border = BorderStroke(1.dp, Color(0xFFEEEEEE)),
        contentPadding = PaddingValues(0.dp),
        enabled = !isLoading,
    ) {
        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Image(
                painter = painterResource(id = R.drawable.google),
                contentDescription = stringResource(R.string.content_desc_google_login),
                modifier = Modifier.align(Alignment.CenterStart).padding(start = 20.dp).size(24.dp),
            )
            Text(
                text = stringResource(R.string.continue_with_google),
                color = Color.Black,
                fontSize = 14.sp,
                fontWeight = FontWeight.SemiBold,
            )
            if (isLoading) {
                CircularProgressIndicator(
                    modifier = Modifier.size(24.dp),
                    color = Color.Black,
                    strokeWidth = 2.dp,
                )
            }
        }
    }
}

/** 隐私政策文本组件 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
internal fun PolicyText() {
    val context = LocalContext.current
    val baseTextStyle =
        TextStyle(
            color = Color.White.copy(alpha = 0.35f),
            fontSize = 12.sp,
            fontWeight = FontWeight.Normal,
            textAlign = TextAlign.Center,
        )

    Column(
        modifier = Modifier,
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(text = stringResource(R.string.by_continuing_agree_full), style = baseTextStyle)

        Spacer(Modifier.height(4.dp))

        PolicyRow(context = context, fontSize = 12.sp)
    }
}

/** Email 登录按钮组件 */
@Composable
internal fun EmailLoginButton(isLoading: Boolean, onLoginClick: () -> Unit) {
    Button(
        onClick = onLoginClick,
        modifier = Modifier.size(width = 300.dp, height = 56.dp),
        shape = RoundedCornerShape(30.dp),
        colors =
            ButtonDefaults.buttonColors(
                containerColor = Color(0xFF8B5CF6),
                disabledContainerColor = Color(0xFF8B5CF6).copy(.7f),
            ),
        contentPadding = PaddingValues(0.dp),
        enabled = !isLoading,
    ) {
        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Text(
                text = stringResource(R.string.continue_with_email),
                color = Color.White,
                fontSize = 14.sp,
                fontWeight = FontWeight.SemiBold,
            )
            if (isLoading) {
                CircularProgressIndicator(
                    modifier = Modifier.size(24.dp),
                    color = Color.White,
                    strokeWidth = 2.dp,
                )
            }
        }
    }
}

/** Email 验证函数 */
private fun isValidEmail(email: String): Boolean {
    val emailPattern =
        Pattern.compile(
            "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
            Pattern.CASE_INSENSITIVE,
        )
    return emailPattern.matcher(email).matches()
}

/** Enter Email 页面 */
@Composable
internal fun EnterEmailScreen(
    onBack: () -> Unit,
    onContinue: (String) -> Unit,
) {
    var email by remember { mutableStateOf("") }
    var emailError by remember { mutableStateOf<String?>(null) }

    Box(modifier = Modifier.fillMaxSize().background(Color(0xFF1A1A2E))) {
        Column(
            modifier =
                Modifier.fillMaxSize()
                    .padding(horizontal = 24.dp)
                    .padding(top = 60.dp, bottom = 40.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            // 返回按钮
            Image(
                modifier =
                    Modifier.align(Alignment.Start)
                        .size(18.dp, 18.dp)
                        .noRippleClickable { onBack() },
                painter = painterResource(R.drawable.close),
                contentDescription = stringResource(R.string.content_desc_back),
            )

            Spacer(modifier = Modifier.height(40.dp))

            // 标题
            Text(
                text = stringResource(R.string.enter_email),
                color = Color.White,
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.fillMaxWidth(),
            )

            Spacer(modifier = Modifier.height(40.dp))

            // Email 输入框
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
                        color = Color.White.copy(alpha = 0.5f),
                    )
                },
                singleLine = true,
                keyboardOptions =
                    KeyboardOptions(
                        keyboardType = KeyboardType.Email,
                        imeAction = ImeAction.Next,
                    ),
                colors =
                    OutlinedTextFieldDefaults.colors(
                        focusedTextColor = Color.White,
                        unfocusedTextColor = Color.White,
                        focusedBorderColor = Color(0xFF8B5CF6),
                        unfocusedBorderColor = Color(0xFF8B5CF6),
                        cursorColor = Color.White,
                    ),
                shape = RoundedCornerShape(30.dp),
                isError = emailError != null,
            )

            emailError?.let {
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = it,
                    color = Color.Red,
                    fontSize = 12.sp,
                    modifier = Modifier.fillMaxWidth().padding(start = 16.dp),
                )
            }

            Spacer(modifier = Modifier.height(32.dp))

            // Continue 按钮
            Button(
                onClick = {
                    if (email.isBlank()) {
                        emailError = stringResource(R.string.invalid_email_format)
                    } else if (!isValidEmail(email)) {
                        emailError = stringResource(R.string.invalid_email_format)
                    } else {
                        onContinue(email)
                    }
                },
                modifier = Modifier.fillMaxWidth().height(56.dp),
                shape = RoundedCornerShape(30.dp),
                colors =
                    ButtonDefaults.buttonColors(
                        containerColor = Color(0xFF8B5CF6),
                    ),
            ) {
                Text(
                    text = stringResource(R.string.continue_button),
                    color = Color.White,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.SemiBold,
                )
            }

            Spacer(modifier = Modifier.weight(1f))

            // 隐私政策文本
            PolicyText()
        }
    }
}

/** Login with Email 页面 */
@Composable
internal fun LoginWithEmailScreen(
    email: String,
    onBack: () -> Unit,
    onLogin: (String, String) -> Unit,
    isLoading: Boolean = false,
) {
    var password by remember { mutableStateOf("") }
    var passwordVisible by remember { mutableStateOf(false) }

    Box(modifier = Modifier.fillMaxSize().background(Color(0xFF1A1A2E))) {
        Column(
            modifier =
                Modifier.fillMaxSize()
                    .padding(horizontal = 24.dp)
                    .padding(top = 60.dp, bottom = 40.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            // 返回按钮
            Image(
                modifier =
                    Modifier.align(Alignment.Start)
                        .size(18.dp, 18.dp)
                        .noRippleClickable { onBack() },
                painter = painterResource(R.drawable.close),
                contentDescription = stringResource(R.string.content_desc_back),
            )

            Spacer(modifier = Modifier.height(40.dp))

            // 标题
            Text(
                text = stringResource(R.string.login_with_email_password),
                color = Color.White,
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.fillMaxWidth(),
            )

            Spacer(modifier = Modifier.height(40.dp))

            // Email 输入框（只读，预填充）
            OutlinedTextField(
                value = email,
                onValueChange = {},
                modifier = Modifier.fillMaxWidth(),
                enabled = false,
                singleLine = true,
                keyboardOptions =
                    KeyboardOptions(
                        keyboardType = KeyboardType.Email,
                        imeAction = ImeAction.Next,
                    ),
                colors =
                    OutlinedTextFieldDefaults.colors(
                        focusedTextColor = Color.White,
                        unfocusedTextColor = Color.White,
                        disabledTextColor = Color.White.copy(alpha = 0.7f),
                        focusedBorderColor = Color(0xFF8B5CF6),
                        unfocusedBorderColor = Color(0xFF8B5CF6),
                        disabledBorderColor = Color(0xFF8B5CF6).copy(alpha = 0.5f),
                        cursorColor = Color.White,
                    ),
                shape = RoundedCornerShape(30.dp),
            )

            Spacer(modifier = Modifier.height(24.dp))

            // Password 输入框
            OutlinedTextField(
                value = password,
                onValueChange = { newValue ->
                    if (newValue.length <= 50) {
                        password = newValue
                    }
                },
                modifier = Modifier.fillMaxWidth(),
                placeholder = {
                    Text(
                        text = stringResource(R.string.enter_password_placeholder),
                        color = Color.White.copy(alpha = 0.5f),
                    )
                },
                singleLine = true,
                visualTransformation =
                    if (passwordVisible) VisualTransformation.None
                    else PasswordVisualTransformation(),
                keyboardOptions =
                    KeyboardOptions(
                        keyboardType = KeyboardType.Password,
                        imeAction = ImeAction.Done,
                    ),
                trailingIcon = {
                    IconButton(onClick = { passwordVisible = !passwordVisible }) {
                        Icon(
                            imageVector =
                                if (passwordVisible) Icons.Default.VisibilityOff
                                else Icons.Default.Visibility,
                            contentDescription =
                                if (passwordVisible) "Hide password"
                                else "Show password",
                            tint = Color.White.copy(alpha = 0.7f),
                        )
                    }
                },
                colors =
                    OutlinedTextFieldDefaults.colors(
                        focusedTextColor = Color.White,
                        unfocusedTextColor = Color.White,
                        focusedBorderColor = Color(0xFF8B5CF6),
                        unfocusedBorderColor = Color(0xFF8B5CF6),
                        cursorColor = Color.White,
                    ),
                shape = RoundedCornerShape(30.dp),
            )

            Spacer(modifier = Modifier.height(32.dp))

            // Login 按钮
            Button(
                onClick = {
                    if (password.isNotBlank()) {
                        onLogin(email, password)
                    }
                },
                modifier = Modifier.fillMaxWidth().height(56.dp),
                shape = RoundedCornerShape(30.dp),
                colors =
                    ButtonDefaults.buttonColors(
                        containerColor = Color(0xFF8B5CF6),
                        disabledContainerColor = Color(0xFF8B5CF6).copy(.7f),
                    ),
                enabled = !isLoading && password.isNotBlank(),
            ) {
                if (isLoading) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(24.dp),
                        color = Color.White,
                        strokeWidth = 2.dp,
                    )
                } else {
                    Text(
                        text = stringResource(R.string.login_button),
                        color = Color.White,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.SemiBold,
                    )
                }
            }

            Spacer(modifier = Modifier.weight(1f))

            // 隐私政策文本
            PolicyText()
        }
    }
}
