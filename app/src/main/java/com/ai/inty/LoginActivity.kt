package com.ai.inty

import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.runtime.Composable
import androidx.lifecycle.lifecycleScope
import com.ai.inty.base.BaseActivity
import com.ai.inty.ui.screens.LoginScreen
import com.ai.inty.ui.theme.IntyTheme
import com.ai.inty.utils.UserProfileManager
import com.ai.inty.viewmodels.LoginViewModel
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

    private val viewModel: LoginViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        setContent {
            IntyTheme {
                LoginContent(
                    onClose = { finish() },
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
 * 登录内容组件
 */
@Composable
private fun LoginContent(
    onClose: () -> Unit,
    onGoogleLoginSuccess: (idToken: String) -> Unit
) {
    LoginScreen(
        onClose = onClose,
        onGoogleLoginSuccess = onGoogleLoginSuccess
    )
}
