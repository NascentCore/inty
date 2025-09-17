package com.ai.inty.viewmodels

import androidx.lifecycle.viewModelScope
import com.ai.inty.base.BaseActivityViewModel
import com.ai.inty.net.IUserApi
import com.ai.inty.netapi.services.AuthService
import com.ai.inty.utils.AppStartupManager
import com.ai.inty.utils.IntyUserProfileSDK
import com.ai.inty.utils.UserProfileManager
import com.inty.utils.log.EasyLog
import com.inty.utils.storage.IntySetting
import com.therouter.TheRouter
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

enum class InitState {
    Loading,
    Success,
    Failed
}

class SplashViewModel : BaseActivityViewModel() {

    // 延迟获取依赖，避免在构造函数中立即获取导致空指针异常
    private val userApi: IUserApi by lazy {
        TheRouter.get(IUserApi::class.java)
            ?: throw IllegalStateException("IUserApi not found in TheRouter")
    }

    private val _initState = MutableStateFlow(InitState.Loading)
    val initState = _initState.asStateFlow()

    //启动初始化流程
    fun initTask() {
        EasyLog.log("SplashViewModel initTask - starting initialization")

        viewModelScope.launch(Dispatchers.IO) {
            try {
                // 等待启动管理器的缓存数据加载完成
                waitForCacheData()

                if (IntySetting.isLogin()) {
                    EasyLog.log("User already logged in: ${IntySetting.getCurUserID()}")
                    onLoginSuccess()
                } else {
                    EasyLog.log("No login found, creating guest account")
                    createGuestWithIntySdk()
                }
            } catch (e: Exception) {
                EasyLog.log("Initialization failed: ${e.message}", EasyLog.ERROR)
                _initState.value = InitState.Failed
            }
        }
    }

    /**
     * 等待缓存数据加载完成
     */
    private suspend fun waitForCacheData() {
        // 等待启动管理器的缓存数据加载完成
        while (AppStartupManager.startupState.value == AppStartupManager.StartupState.Initializing) {
            kotlinx.coroutines.delay(50) // 50ms检查一次
        }

        EasyLog.log("SplashViewModel - 缓存数据加载完成，状态: ${AppStartupManager.startupState.value}")
    }

    private suspend fun createGuestWithIntySdk() {
        EasyLog.log("Creating guest account with inty-sdk...")

        // 使用封装的 AuthService 创建游客账户
        val result = AuthService.createGuest()

        when (result) {
            is com.ai.inty.netapi.ApiResult.Success -> {
                val (guestId, token) = result.data
                IntySetting.login(true, guestId, token)
                EasyLog.log("Guest created successfully with inty-sdk: $guestId")
                onLoginSuccess()
            }

            is com.ai.inty.netapi.ApiResult.Error -> {
                EasyLog.log("Guest creation failed with inty-sdk: ${result.message}", EasyLog.ERROR)
                _initState.value = InitState.Failed
            }
        }
    }

    /**
     * Guest或正式用户登录成功后，执行更新用户信息逻辑
     */
    private suspend fun onLoginSuccess() {
        EasyLog.log("onLoginSuccess - user: ${IntySetting.getCurUserID()}")

        // 优先从本地缓存获取用户信息
        if (UserProfileManager.hasUserProfile()) {
            EasyLog.log("Loaded user profile from cache")
        }

        // 获取用户信息
        getUserProfile()

        // 通知启动管理器开始网络预加载
        AppStartupManager.onLoginSuccess()

        EasyLog.log("Initialization completed successfully")
        _initState.value = InitState.Success
    }

    /**
     * 从接口获取用户信息（Guest或正式用户）
     */
    private suspend fun getUserProfile() {
        val userProfile = IntyUserProfileSDK.getUserProfile()
        if (userProfile != null) {
            UserProfileManager.saveUserProfile(userProfile)
            EasyLog.log("Updated user profile from inty-sdk: ${userProfile.nickname}")
        } else {
            EasyLog.log("Failed to get user profile from inty-sdk", EasyLog.ERROR)
            // 不阻止初始化成功，因为用户信息不是必需的
        }
    }


}
