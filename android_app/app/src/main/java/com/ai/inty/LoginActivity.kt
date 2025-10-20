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
import com.ai.inty.utils.CredentialManagerHelper
import com.ai.inty.utils.FirebaseManager
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
 * 登录页面 使用最新的 Credential Manager API 进行 Google 登录 参考:
 * https://developer.android.com/identity/sign-in/credential-manager-siwg
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
                    onGoogleLoginSuccess = { idToken -> viewModel.onGoogleLoginSuccess(idToken) },
                )
            }
        }

        // 跟踪LoginActivity页面访问
        FirebaseManager.logScreenView(screenName = "LoginScreen", screenClass = "LoginActivity")

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
            CoroutineScope(Dispatchers.Main).launch {
                delay(300)
                TheRouter.build(Constant.ROUTE_REG_INFO).navigation(this@LoginActivity)
            }
        } else {
            EasyLog.log("User has set gender, no need to show RegInfoActivity")
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        // 1. **避免误清理**：如果用户已经登录成功，不应该清除凭证
        // 2. **区分退出方式**：正常退出不需要清理，异常退出需要清理
        // 3. **安全考虑**：确保在用户未成功认证的情况下清理敏感信息
        // 用户没有用户档案（未登录成功） // Activity 不是正常结束状态
        if (!UserProfileManager.hasUserProfile() && !isFinishing) {
            lifecycleScope.launch {
                CredentialManagerHelper.clearCredentialState(this@LoginActivity)
            }
        }
    }
}

/** 登录内容组件 */
@Composable
private fun LoginContent(onClose: () -> Unit, onGoogleLoginSuccess: (idToken: String) -> Unit) {
    LoginScreen(onClose = onClose, onGoogleLoginSuccess = onGoogleLoginSuccess)
}
