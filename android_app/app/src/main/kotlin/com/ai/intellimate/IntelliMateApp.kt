package com.ai.intellimate

import ai.sxwl.android.common.analytics.GlobalExceptionHandler
import ai.sxwl.android.data.billing.BillingRepository
import ai.sxwl.android.data.di.DataModule
import ai.sxwl.android.data.http.IntyNetworkManager
import ai.sxwl.android.data.http.services.UserService
import ai.sxwl.android.firebase.FCMTokenUploadCallback
import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.utils.LogUtils
import android.app.Application
import com.ai.intellimate.utils.AgentCacheProviderImpl
import com.ai.intellimate.utils.RecommendedAgentCacheProviderImpl
import com.ai.intellimate.utils.UnifiedStartupManager
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

/** 应用Application的实现类 */
class IntelliMateApp : Application() {

    override fun onCreate() {
        super.onCreate()
        // 初始化网络管理器（IntyNetworkManager 内部已包含 NetworkStateManager）
        IntyNetworkManager.initialize(this, buildType = BuildConfig.BUILD_TYPE)

        // 初始化缓存提供者并注入到DataModule
        val chatCacheProvider = AgentCacheProviderImpl()
        val recommendedCacheProvider = RecommendedAgentCacheProviderImpl()
        DataModule.setAgentCacheProvider(chatCacheProvider)
        DataModule.setRecommendedCacheProvider(recommendedCacheProvider)
        LogUtils.i("IntelliMateApp - 数据层依赖注入初始化完成")

        // 立即初始化统一启动管理器（只做必要的登录判断，不阻塞）
        UnifiedStartupManager.initializeEssential(this)

        // Firebase初始化和设备信息设置
        initializeFirebaseAnalytics()

        // 设置FCM token上传回调（连接infrastructure层和data层）
        setupFCMTokenUploadCallback()

        // 安装全局异常处理器
        GlobalExceptionHandler.Companion.install(this)

        // 异步初始化所有可能阻塞的组件
        CoroutineScope(Dispatchers.IO).launch {
            try {
                // 异步进行完整的数据预加载和缓存
                UnifiedStartupManager.initializeAsync(this@IntelliMateApp)
            } catch (e: Exception) {
                LogUtils.e("IntyApp - 异步初始化失败: ${e.message}")
            }
        }
    }

    /** Firebase Analytics初始化 */
    private fun initializeFirebaseAnalytics() {
        // FirebaseManager内部已有完善的异常处理，这里主要是Application级别的额外保护
        // FirebaseInitializer已经自动初始化了FirebaseManager，这里作为备用保障

        // 记录应用启动事件 - 使用Firebase内置事件
        FirebaseManager.logEvent(FirebaseManager.Events.APP_OPEN)

        // 设置设备信息
        FirebaseManager.setDeviceInfo()

        LogUtils.i("IntelliMateApp - Firebase Analytics初始化完成")
    }

    /**
     * Setup FCM token upload callback
     *
     * Connects infrastructure layer (core/firebase) with data layer (core/data)
     * This avoids circular dependency between modules
     */
    private fun setupFCMTokenUploadCallback() {
        FirebaseManager.setTokenUploadCallback(object : FCMTokenUploadCallback {
            override suspend fun uploadToken(token: String) {
                // Delegate to UserService in data layer
                when (val result = UserService.registerDeviceToken(token)) {
                    is ai.sxwl.android.data.http.ApiResult.Success -> {
                        LogUtils.i("IntelliMateApp", "FCM token uploaded successfully")
                    }

                    is ai.sxwl.android.data.http.ApiResult.Error -> {
                        LogUtils.e("IntelliMateApp", "FCM token upload failed: ${result.message}")
                    }
                }
            }
        })
        LogUtils.d("IntelliMateApp", "FCM token upload callback set")
    }

    override fun onTerminate() {
        super.onTerminate()
        // 应用退出时释放Billing连接
        if (BillingRepository.isInitialized()) {
            LogUtils.i("IntyApp - 应用退出，释放Billing连接")
            BillingRepository.release()
        }
    }
}
