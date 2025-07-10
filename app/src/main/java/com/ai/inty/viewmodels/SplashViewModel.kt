package com.ai.inty.viewmodels

import androidx.lifecycle.viewModelScope
import com.ai.inty.base.BaseActivityViewModel
import com.ai.inty.beans.CreateGuestReq
import com.ai.inty.beans.UserProfile
import com.ai.inty.net.IUserApi
import com.ai.inty.net.IUserApi2
import com.ai.inty.net.ISubscriptionApi
import com.ai.inty.billing.BillingConfig
import com.ai.inty.billing.RemoteBillingConfig
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
import kotlinx.coroutines.async

enum class InitState {
    Loading,
    Success,
    Failed
}

class SplashViewModel : BaseActivityViewModel() {

    private val userApi: IUserApi = TheRouter.get(IUserApi::class.java)!!
    private val userApi2: IUserApi2 = TheRouter.get(IUserApi2::class.java)!!
    private val subscriptionApi: ISubscriptionApi = TheRouter.get(ISubscriptionApi::class.java)!!

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
        
        // 并行获取用户信息和订阅配置
        kotlinx.coroutines.coroutineScope {
            val userProfileDeferred = async { getUserProfile() }
            val subscriptionConfigDeferred = async { getSubscriptionConfig() }
            
            // 等待两个任务完成
            userProfileDeferred.await()
            subscriptionConfigDeferred.await()
        }
        
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
    
    /**
     * 获取订阅配置信息并缓存
     */
    private suspend fun getSubscriptionConfig() {
        EasyLog.log("开始获取订阅配置...")
        try {
            // 使用 withTimeout 添加应用层超时控制
            kotlinx.coroutines.withTimeout(3000) { // 3秒超时
                EasyLog.log("发起订阅配置网络请求...")
                val result = subscriptionApi.getSubscriptionPlans()
                EasyLog.log("订阅配置网络请求完成: $result")
                
                when (result) {
                    is HttpResult.Success -> {
                        val plans = result.data.plans
                        EasyLog.log("Received ${plans.size} subscription plans from server")
                        
                        if (plans.isEmpty()) {
                            EasyLog.log("服务器返回空的订阅计划列表")
                            return@withTimeout
                        }
                        
                        // 转换为BillingConfig格式并缓存
                        val subscriptionIds = plans.associate { plan ->
                            plan.googlePlayProductId to plan.name
                        }
                        
                        EasyLog.log("转换后的订阅ID映射: $subscriptionIds")
                        
                        val remoteConfig = RemoteBillingConfig(
                            subscriptionIds = subscriptionIds,
                            version = "1.0.0", // 可以从服务器返回的版本信息
                            enabled = true,
                            updateTime = System.currentTimeMillis()
                        )
                        
                        // 更新BillingConfig
                        BillingConfig.updateRemoteConfig(remoteConfig)
                        EasyLog.log("Subscription configuration cached successfully")
                    }
                    is HttpResult.Failure -> {
                        EasyLog.log("Failed to get subscription plans: ${result.message}", EasyLog.ERROR)
                        EasyLog.log("使用默认配置作为fallback")
                        // 不阻止初始化成功，使用默认配置
                    }
                }
            }
        } catch (e: kotlinx.coroutines.TimeoutCancellationException) {
            EasyLog.log("Subscription config request timeout after 3 seconds", EasyLog.ERROR)
            EasyLog.log("使用默认配置作为fallback")
            // 超时不影响初始化，使用默认配置
        } catch (e: Exception) {
            EasyLog.log("Exception while fetching subscription config: ${e.message}", EasyLog.ERROR)
            EasyLog.log("使用默认配置作为fallback")
            // 不阻止初始化成功，使用默认配置
        }
    }
}