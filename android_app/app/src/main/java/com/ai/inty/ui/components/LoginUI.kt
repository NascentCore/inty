package com.ai.inty.ui.components

import android.content.Intent
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
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
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
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


import com.ai.inty.R
import com.ai.inty.base.noRippleClickable
import com.ai.inty.utils.TextStyleUtils
import com.ai.inty.ui.components.PolicyRow

/**
 * 登录页面关闭按钮组件
 */
@Composable
internal fun LoginCloseButton(onClose: () -> Unit) {
    Image(
        modifier = Modifier
            .padding(end = 16.dp, top = 16.dp)
            .size(18.dp, 18.dp)
            .noRippleClickable { onClose() },
        painter = painterResource(R.drawable.close),
        contentDescription = null,
    )
}

/**
 * Logo 图片组件
 */
@Composable
internal fun LogoImage() {
    Image(
        modifier = Modifier.size(width = 239.dp, height = 190.dp),
        painter = painterResource(R.drawable.group2085655930),
        contentScale = ContentScale.Crop,
        alignment = Alignment.TopCenter,
        contentDescription = ""
    )
}

/**
 * 欢迎标题组件
 */
@Composable
internal fun WelcomeTitle() {
    Text(
        text = stringResource(R.string.welcome_to_intellimate),
        color = Color.White,
        fontSize = 24.sp,
        fontWeight = FontWeight.Bold
    )
}

/**
 * 欢迎副标题组件
 */
@Composable
internal fun WelcomeSubtitle() {
    Text(
        text = stringResource(R.string.create_account_or_login),
        color = Color.White.copy(alpha = 0.55f),
        fontSize = 14.sp,
        fontWeight = FontWeight.Normal
    )
}

/**
 * Google 登录按钮组件
 */
@Composable
internal fun GoogleLoginButton(
    isLoading: Boolean,
    onLoginClick: () -> Unit
) {
    Button(
        onClick = onLoginClick,
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
}

/**
 * 隐私政策文本组件
 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
internal fun PolicyText() {
    val context = LocalContext.current
    val baseTextStyle = TextStyle(
        color = Color.White.copy(alpha = 0.35f),
        fontSize = 12.sp,
        fontWeight = FontWeight.Normal,
        textAlign = TextAlign.Center
    )

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

        PolicyRow(
            context = context,
            fontSize = 12.sp
        )
    }
}

// Preview 函数
@Preview(showBackground = true)
@Composable
private fun LoginCloseButtonPreview() {
    LoginCloseButton(onClose = {})
}

@Preview(showBackground = true)
@Composable
private fun LogoImagePreview() {
    LogoImage()
}

@Preview(showBackground = true)
@Composable
private fun WelcomeTitlePreview() {
    WelcomeTitle()
}

@Preview(showBackground = true)
@Composable
private fun WelcomeSubtitlePreview() {
    WelcomeSubtitle()
}

@Preview(showBackground = true)
@Composable
private fun GoogleLoginButtonPreview() {
    GoogleLoginButton(
        isLoading = false,
        onLoginClick = {}
    )
}

@Preview(showBackground = true)
@Composable
private fun PolicyTextPreview() {
    PolicyText()
}
