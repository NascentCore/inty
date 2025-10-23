package com.ai.inty.viewmodels

import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.ToastUtils
import ai.sxwl.android.utils.Utils
import android.content.Intent
import com.ai.inty.MainActivity
import com.ai.inty.R
import com.ai.inty.base.BaseViewModel
import com.ai.inty.base.ViewModelEvent
import com.ai.inty.beans.GoogleLoginRequest
import com.ai.inty.net.NetServiceMgr
import com.ai.inty.utils.UserProfileManager
import com.architecture.httplib.core.HttpResult
import com.inty.utils.storage.IntySetting
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class LoginViewModel : BaseViewModel() {

    // 延迟获取依赖，避免在构造函数中立即获取导致空指针异常
    private val userApi by lazy { NetServiceMgr.getUserApi() }


    fun onGoogleLoginSuccess(idToken: String) {
        launchWithNetCheck {
            val result = userApi.loginByGoogle(GoogleLoginRequest(idToken = idToken))
            LogUtils.i("loginByGoogle($idToken) result:")
            when (result) {
                is HttpResult.Success -> {
                    // 现在我们可以同时获取到 token 和 userProfile
                    val token = result.data.token
                    val userProfile = result.data.user
                    LogUtils.i("Token: $token ,, UserProfile: $userProfile")

                    // 保存用户信息和 token
                    IntySetting.login(false, userProfile.id, token) // false 表示不是游客用户
                    UserProfileManager.saveUserProfile(userProfile)

                    withContext(Dispatchers.Main) {
                        // 显示登录成功提示
                        ToastUtils.showShort(R.string.login_successfully)

                        // 发送登录成功事件
                        sendEvent(ViewModelEvent.LoginSuccess)

                        // 重启 MainActivity
                        val intent =
                            Intent(Utils.getApp(), MainActivity::class.java).apply {
                                flags =
                                    Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                            }
                        Utils.getApp().startActivity(intent)
                    }
                }

                is HttpResult.Failure -> {
                    LogUtils.e("Google login failed: ${result.message}")
                    withContext(Dispatchers.Main) { showNetworkAwareError(result.message) }
                }
            }
        }
    }
}
