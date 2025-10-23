package com.ai.inty.viewmodels

import ai.sxwl.android.common.base.BaseVM
import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.GoogleLoginRequest
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.ToastUtils
import ai.sxwl.android.utils.Utils
import android.content.Intent
import androidx.lifecycle.viewModelScope
import com.ai.inty.MainActivity
import com.ai.inty.R
import com.ai.inty.base.ViewModelEvent
import com.ai.inty.utils.NetworkErrorHandler
import com.ai.inty.utils.UserProfileManager
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class LoginViewModel : BaseVM() {

    // 事件通知机制
    private val _events = MutableSharedFlow<ViewModelEvent>()
    val events: SharedFlow<ViewModelEvent> = _events.asSharedFlow()

    /**
     * 发送事件通知
     */
    private fun sendEvent(event: ViewModelEvent) {
        viewModelScope.launch {
            _events.emit(event)
        }
    }

    // 延迟获取依赖，避免在构造函数中立即获取导致空指针异常
    private val userApi by lazy { NetServiceMgr.getUserApi() }


    fun onGoogleLoginSuccess(idToken: String) {
        launchBackground {
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
                    withContext(Dispatchers.Main) { NetworkErrorHandler.showNetworkAwareError(result.message) }
                }
            }
        }
    }
}
