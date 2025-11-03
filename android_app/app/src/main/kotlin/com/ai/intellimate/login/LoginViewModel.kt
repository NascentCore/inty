package com.ai.intellimate.login

import ai.sxwl.android.common.base.BaseVM
import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.GoogleLoginRequest
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.ToastUtils
import com.ai.intellimate.R
import com.ai.intellimate.ViewModelEvent
import com.ai.intellimate.utils.NetworkErrorHandler
import com.ai.intellimate.utils.UserProfileManager
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.withContext

class LoginViewModel : BaseVM() {

    // 事件通知机制
    private val _events = MutableSharedFlow<ViewModelEvent>()
    val events: SharedFlow<ViewModelEvent> = _events.asSharedFlow()

    /** 发送事件通知 */
    private fun sendEvent(event: ViewModelEvent) {
        launchUI { _events.emit(event) }
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

                    // 通知MainViewModel更新登录状态（如果MainViewModel已初始化）
                    // 注意：这里不直接引用MainViewModel，而是通过MainActivity来处理

                    // 上报用户登录事件（使用 Firebase 内置 LOGIN 事件）
                    FirebaseManager.logEvent(
                        FirebaseManager.Events.LOGIN,
                        FirebaseManager.safeEventParams(
                            "user_id" to userProfile.id,
                            "user_name" to (userProfile.nickname),
                            "login_method" to "google",
                            "timestamp" to System.currentTimeMillis()
                        )
                    )

                    // 登录成功，IntySetting已经保存了登录状态

                    // 检查用户信息是否完整（年龄和性别）
                    val needsRegInfo =
                        userProfile.gender.isNullOrEmpty() ||
                            userProfile.ageGroup.isNullOrEmpty() ||
                            userProfile.ageGroup == "<18"

                    withContext(Dispatchers.Main) {
                        // 显示登录成功提示
                        ToastUtils.showShort(R.string.login_successfully)

                        if (needsRegInfo) {
                            // 需要完善注册信息，跳转到RegInfo页面
                            sendEvent(ViewModelEvent.NeedRegInfo)
                        } else {
                            // 用户信息完整，发送登录成功事件
                            // 注意：不再重启MainActivity，因为MainActivity已经支持响应式登录状态
                            // 如果是从MainActivity的SplashLoginUI登录，UI会自动切换到HomeScreen
                            // 如果是从LoginActivity登录，LoginActivity会监听事件并finish
                            sendEvent(ViewModelEvent.LoginSuccess)
                        }
                    }
                }
                is HttpResult.Failure -> {
                    LogUtils.e("Google login failed: ${result.message}")
                    withContext(Dispatchers.Main) {
                        NetworkErrorHandler.showNetworkAwareError(result.message)
                    }
                }
            }
        }
    }
}
