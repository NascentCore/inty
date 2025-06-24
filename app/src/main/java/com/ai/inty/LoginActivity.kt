package com.ai.inty

import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.viewModels
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.ClickableText
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.lifecycleScope
import com.ai.inty.base.BaseActivity
import com.ai.inty.base.noRippleClickable
import com.ai.inty.beans.GENDER
import com.ai.inty.ui.theme.IntyTheme
import com.ai.inty.viewmodels.LoginActivityViewModel
import com.google.android.gms.auth.api.signin.GoogleSignIn
import com.google.android.gms.auth.api.signin.GoogleSignInOptions
import com.google.android.gms.common.api.ApiException
import com.inty.utils.log.EasyLog
import com.therouter.TheRouter
import com.therouter.router.Route
import kotlinx.coroutines.launch
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import com.ai.inty.utils.UserProfileManager

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

@Composable
fun LoginScreen(
    onClose: () -> Unit = {},
    onGoogleLoginSuccess: (idToken: String) -> Unit
) {
    val context = androidx.compose.ui.platform.LocalContext.current

    val googleSignInLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.StartActivityForResult(),
        onResult = { result ->
            val task = GoogleSignIn.getSignedInAccountFromIntent(result.data)
            try {
                val account = task.getResult(ApiException::class.java)!!
                val idToken = account.idToken
                if (idToken != null) {
                    onGoogleLoginSuccess(idToken)
                } else {
                    EasyLog.log("Google Sign-In idToken is null")
                }
            } catch (e: ApiException) {
                EasyLog.log("Google Sign-In failed with code: ${e.statusCode}")
            }
        }
    )

    val gso = remember {
        GoogleSignInOptions.Builder(GoogleSignInOptions.DEFAULT_SIGN_IN)
            .requestIdToken(context.getString(R.string.web_client_id))
            .requestEmail()
            .build()
    }
    val googleSignInClient = remember { GoogleSignIn.getClient(context, gso) }

    // var selectGender by remember { mutableStateOf(GENDER.OTHER) }
    // var selectAge by remember { mutableStateOf("") }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black.copy(0.6f))
        ,
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
            Image(
                modifier = Modifier
                    .align(Alignment.End)
                    .padding(end = 16.dp, top = 16.dp)
                    .size(18.dp, 18.dp)
                    .noRippleClickable {
                        onClose()
                    },
                painter = painterResource(R.drawable.close),
                contentDescription = null,
            )

            Spacer(Modifier.height(12.dp))

            Image(
                modifier = Modifier
                    .size(width = 239.dp, height = 190.dp),
                painter = painterResource(R.drawable.group2085655930),
                contentScale = ContentScale.Crop,
                alignment = Alignment.TopCenter,
                contentDescription = ""
            )

            Spacer(modifier = Modifier.height(40.dp))

            Text(
                text = "Welcome to HeartMate",
                color = Color.White,
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold
            )

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = "Create an account or log in to continue",
                color = Color.White.copy(alpha = 0.55f),
                fontSize = 14.sp,
                fontWeight = FontWeight.Normal
            )

            Spacer(modifier = Modifier.height(40.dp))

            Button(
                onClick = {
                    val signInIntent = googleSignInClient.signInIntent
                    googleSignInLauncher.launch(signInIntent)
                },
                modifier = Modifier
                    .size(width = 300.dp, height = 56.dp),
                shape = RoundedCornerShape(30.dp),
                colors = ButtonDefaults.buttonColors(containerColor = Color.White),
                border = BorderStroke(1.dp, Color(0xFFEEEEEE)),
                contentPadding = PaddingValues(0.dp)
            ) {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    Image(
                        painter = painterResource(id = R.drawable.google),
                        contentDescription = "Google Login",
                        modifier = Modifier
                            .align(Alignment.CenterStart)
                            .padding(start = 20.dp)
                            .size(24.dp)
                    )
                    Text(
                        text = "Continue with Google",
                        color = Color.Black,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            PolicyText()

            Spacer(modifier = Modifier.height(60.dp))
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun PolicyText() {
    val baseTextStyle = TextStyle(
        color = Color.White.copy(alpha = 0.35f),
        fontSize = 12.sp,
        fontWeight = FontWeight.Normal,
        textAlign = TextAlign.Center
    )

    val linkTextStyle = TextStyle(
        color = Color.White,
        fontSize = 12.sp,
        fontWeight = FontWeight.Normal,
        textAlign = TextAlign.Center
    )

    FlowRow(
        modifier = Modifier.width(259.dp),
        horizontalArrangement = Arrangement.Center,
        verticalArrangement = Arrangement.Center
    ) {
        Text(
            text = "By continuing, you agree to InTy's",
            style = baseTextStyle
        )
        TextButton(
            onClick = { /* TODO: 打开用户协议页面 */ },
            contentPadding = PaddingValues(horizontal = 4.dp, vertical = 0.dp)
        ) {
            Text(
                text = "User Agreement",
                style = linkTextStyle
            )
        }
        Text(text = "and", style = baseTextStyle)
        TextButton(
            onClick = { /* TODO: 打开隐私政策页面 */ },
            contentPadding = PaddingValues(horizontal = 4.dp, vertical = 0.dp)
        ) {
            Text(
                text = "Privacy Policy",
                style = linkTextStyle
            )
        }
    }
}

@Preview(backgroundColor = 0xFFffffff, showBackground = true)
@Composable
fun LoginPreview() {
    LoginScreen(onGoogleLoginSuccess = {})
}