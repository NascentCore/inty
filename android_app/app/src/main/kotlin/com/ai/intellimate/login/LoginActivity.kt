package com.ai.intellimate.login

import ai.sxwl.android.common.base.BaseActivity
import ai.sxwl.android.firebase.FirebaseManager
import android.content.Context
import android.content.Intent
import androidx.activity.viewModels
import androidx.compose.runtime.Composable
import androidx.lifecycle.lifecycleScope
import com.ai.inty.utils.CredentialManagerHelper
import com.ai.inty.utils.UserProfileManager
import com.ai.inty.viewmodels.ViewModelEvent
import kotlinx.coroutines.launch

/**
 * 登录页面 使用最新的 Credential Manager API 进行 Google 登录 参考:
 * https://developer.android.com/identity/sign-in/credential-manager-siwg
 */
class LoginActivity : BaseActivity() {

    companion object {

        /**
         * 启动登录界面
         * @param context 上下文context
         */
        fun launch(context: Context) {
            context.startActivity(Intent(context, LoginActivity::class.java))
        }
    }

    private val viewModel: LoginViewModel by viewModels()

    override fun initConfigData() {
        super.initConfigData()
        // 跟踪LoginActivity页面访问
        FirebaseManager.logScreenView(screenName = "LoginScreen", screenClass = "LoginActivity")

        // 监听ViewModel事件
        lifecycleScope.launch {
            viewModel.events.collect { event ->
                when (event) {
                    is ViewModelEvent.LoginSuccess -> {
                        finish()
                    }
                    is ViewModelEvent.NeedRegInfo -> {
                        // 跳转到注册信息页面
                        RegInfoActivity.launch(this@LoginActivity)
                        finish()
                    }
                    else -> {
                        // 其他事件暂不处理
                    }
                }
            }
        }
    }

    @Composable
    override fun ConfigComposeUI() {
        super.ConfigComposeUI()
        LoginContent(
            onClose = { finish() },
            onGoogleLoginSuccess = { idToken -> viewModel.onGoogleLoginSuccess(idToken) },
        )
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
