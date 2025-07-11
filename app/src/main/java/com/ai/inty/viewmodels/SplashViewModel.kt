package com.ai.inty.viewmodels

import androidx.lifecycle.viewModelScope
import com.ai.inty.base.BaseActivityViewModel
import com.ai.inty.beans.CreateGuestReq
import com.ai.inty.net.IUserApi
import com.ai.inty.net.IUserApi2
import com.ai.inty.utils.UserProfileManager
import com.architecture.httplib.core.HttpResult
import com.inty.utils.AppEnv
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

    private val userApi: IUserApi = TheRouter.get(IUserApi::class.java)!!
    private val userApi2: IUserApi2 = TheRouter.get(IUserApi2::class.java)!!

    private val _initState = MutableStateFlow(InitState.Loading)
    val initState = _initState.asStateFlow()

    fun initTask() {
        EasyLog.log("SplashViewModel initTask - starting initialization")
        
        viewModelScope.launch(Dispatchers.IO) {
            try {
                if (IntySetting.isLogin()) {
                    EasyLog.log("User already logged in: ${IntySetting.getCurUserID()}")
                    onLoginSuccess()
                } else {
                    EasyLog.log("No login found, creating guest account")
                    createGuest()
                }
            } catch (e: Exception) {
                EasyLog.log("Initialization failed: ${e.message}", EasyLog.ERROR)
                _initState.value = InitState.Failed
            }
        }
    }

    private suspend fun createGuest() {
        EasyLog.log("Creating guest account...")
        val result = userApi.createGuest(CreateGuestReq(device_id = AppEnv.DeviceID, AppEnv.locale.language))
        EasyLog.log("createGuest result: $result")
        
        when (result) {
            is HttpResult.Success -> {
                IntySetting.login(true, result.data.guest_id, result.data.token)
                EasyLog.log("Guest created successfully: ${result.data.guest_id}")
                onLoginSuccess()
            }
            is HttpResult.Failure -> {
                EasyLog.log("Guest creation failed: ${result.message}", EasyLog.ERROR)
                _initState.value = InitState.Failed
            }
        }
    }

    private suspend fun onLoginSuccess() {
        EasyLog.log("onLoginSuccess - user: ${IntySetting.getCurUserID()}")
        
        // 优先从本地缓存获取用户信息
        if (UserProfileManager.hasUserProfile()) {
            EasyLog.log("Loaded user profile from cache")
        }
        
        // 获取用户信息
        getUserProfile()
        
        EasyLog.log("Initialization completed successfully")
        _initState.value = InitState.Success
    }

    private suspend fun getUserProfile() {
        val result = userApi2.getUserProfile()
        when (result) {
            is HttpResult.Success -> {
                UserProfileManager.saveUserProfile(result.data)
                EasyLog.log("Updated user profile from server: ${result.data.nickname}")
            }
            is HttpResult.Failure -> {
                EasyLog.log("Failed to get user profile: ${result.message}", EasyLog.ERROR)
                // 不阻止初始化成功，因为用户信息不是必需的
            }
        }
    }
}