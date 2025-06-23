package com.ai.inty.viewmodels

import android.content.Intent
import androidx.lifecycle.viewModelScope
import com.ai.inty.MainActivity
import com.ai.inty.base.BaseActivityViewModel
import com.ai.inty.beans.GENDER
import com.ai.inty.beans.GoogleLoginRequest
import com.ai.inty.beans.UserProfile
import com.ai.inty.net.IUserApi
import com.ai.inty.net.IUserApi2
import com.ai.inty.utils.UserProfileManager
import com.architecture.httplib.core.HttpResult
import com.inty.utils.AppEnv
import com.inty.utils.log.EasyLog
import com.inty.utils.storage.IntySetting
import com.therouter.TheRouter
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class LoginActivityViewModel: BaseActivityViewModel() {

    private val userApi = TheRouter.get(IUserApi::class.java)!!
    private val userApi2 = TheRouter.get(IUserApi2::class.java)!!

    fun onGoogleLoginSuccess(idToken: String) {
        viewModelScope.launch(Dispatchers.IO) {
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
                    
                    // 登录成功后重启 MainActivity 以清理所有缓存数据
                    withContext(Dispatchers.Main) {
                        // 关闭当前登录页面
                        closeActivity()
                        
                        // 重启 MainActivity
                        val intent = Intent(AppEnv.context, MainActivity::class.java).apply {
                            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                        }
                        AppEnv.context.startActivity(intent)
                    }
                }
                is HttpResult.Failure -> {
                    EasyLog.log("Google login failed: ${result.message}", EasyLog.ERROR)
                    withContext(Dispatchers.Main) {
                        showSnackbar(result.message)
                    }
                }
            }
        }
    }

    fun onSave(gender: GENDER, age: String) {
        viewModelScope.launch(Dispatchers.IO) {
            val result = userApi2.setUserProfile(
                userProfile = UserProfile(
                    gender = gender.value,
                    ageGroup = age,
                )
            )
            EasyLog.log("setUserProfile($gender, $age) = $result")

            when (result) {
                is HttpResult.Success -> {
                    closeActivity()
                }
                is HttpResult.Failure -> {
                    showSnackbar(result.message)
                }
            }
        }
    }
}