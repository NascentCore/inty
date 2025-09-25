package com.ai.inty.viewmodels

import android.content.Intent
import android.widget.Toast
import com.ai.inty.MainActivity
import com.ai.inty.R
import com.ai.inty.base.BaseActivityViewModel
import com.ai.inty.beans.GoogleLoginRequest
import com.ai.inty.net.IUserApi
import com.ai.inty.utils.UserProfileManager
import com.architecture.httplib.core.HttpResult
import com.inty.utils.AppEnv
import com.inty.utils.log.EasyLog
import com.inty.utils.storage.IntySetting
import com.therouter.TheRouter
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class LoginViewModel : BaseActivityViewModel() {

  // 延迟获取依赖，避免在构造函数中立即获取导致空指针异常
  private val userApi by lazy {
    TheRouter.get(IUserApi::class.java)
        ?: throw IllegalStateException("IUserApi not found in TheRouter")
  }

  fun onGoogleLoginSuccess(idToken: String) {
    launchWithNetCheck {
      val result = userApi.loginByGoogle(GoogleLoginRequest(idToken = idToken))
      EasyLog.log("loginByGoogle($idToken) result:")
      when (result) {
        is HttpResult.Success -> {
          // 现在我们可以同时获取到 token 和 userProfile
          val token = result.data.token
          val userProfile = result.data.user
          EasyLog.log("Token: $token")
          EasyLog.log("UserProfile: $userProfile")

          // 保存用户信息和 token
          IntySetting.login(false, userProfile.id, token) // false 表示不是游客用户
          UserProfileManager.saveUserProfile(userProfile)

          withContext(Dispatchers.Main) {
            // 显示登录成功提示
            Toast.makeText(
                    AppEnv.context,
                    AppEnv.context.getString(R.string.login_successfully),
                    Toast.LENGTH_SHORT,
                )
                .show()

            // 关闭当前登录页面
            closeActivity()

            // 重启 MainActivity
            val intent =
                Intent(AppEnv.context, MainActivity::class.java).apply {
                  flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                }
            AppEnv.context.startActivity(intent)
          }
        }
        is HttpResult.Failure -> {
          EasyLog.log("Google login failed: ${result.message}", EasyLog.ERROR)
          withContext(Dispatchers.Main) { showNetworkAwareError(result.message) }
        }
      }
    }
  }
}
