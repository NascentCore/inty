package com.ai.intellimate

import ai.sxwl.android.common.analytics.GlobalExceptionHandler
import ai.sxwl.android.common.fcm.FCMessageHandlerImpl
import ai.sxwl.android.data.billing.BillingRepository
import ai.sxwl.android.data.di.DataModule
import ai.sxwl.android.data.http.ApiResult
import ai.sxwl.android.data.http.IntyNetworkManager
import ai.sxwl.android.data.http.services.UserService
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.data.store.SettingStateManager
import ai.sxwl.android.firebase.FCMTokenUploadCallback
import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.utils.LogUtils
import android.app.Application
import com.ai.intellimate.notifications.PushNotificationManager
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

        // 初始化 Remote Config 并设置聊天开关的默认值
        initializeRemoteConfigDefaults()

        // 设置FCM token上传回调（连接infrastructure层和data层）
        setupFCMTokenUploadCallback()

        // 设置FCM消息处理器（连接firebase层和common层）
        setupFCMessageHandler()

        // 初始化推送通知管理器
        PushNotificationManager.getInstance(this).initialize()

        // 安装全局异常处理器
        GlobalExceptionHandler.install(this)

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
     * 初始化 Remote Config 默认值并获取配置
     * 用于设置聊天开关的默认值（Keep Talking 和 Auto Play Voice）
     */
    private fun initializeRemoteConfigDefaults() {
        // 异步初始化，避免阻塞应用启动
        CoroutineScope(Dispatchers.IO).launch {
            try {
                // 设置 Remote Config 默认值（降级方案）
                // 如果 Firebase 后台未配置或网络不可用，使用这些默认值
                FirebaseManager.setRemoteConfigDefaults(
                    mapOf(
                        // Keep Talking 开关默认值（false = 关闭）
                        FirebaseManager.RemoteConfigKeys.AUTO_ENABLE_KEEP_TALKING to false,
                        // Auto Play Opening Voice 开关默认值（true = 开启）
                        FirebaseManager.RemoteConfigKeys.AUTO_PLAY_OPENING_VOICE to true,
                    )
                )

                // 获取并激活 Remote Config
                val hasNewConfig = FirebaseManager.fetchAndActivateRemoteConfig()
                if (hasNewConfig) {
                    LogUtils.i("IntelliMateApp", "Remote Config 已获取并激活新配置")
                }

                // 在调试模式下输出所有 Remote Config 参数（用于验证配置）
                if (ai.sxwl.android.utils.AppUtils.isAppDebug()) {
                    val allConfig = FirebaseManager.getAllRemoteConfigValues()
                    if (allConfig.isNotEmpty()) {
                        LogUtils.d(
                            "IntelliMateApp",
                            "Remote Config 所有参数: ${allConfig.entries.joinToString { "${it.key}=${it.value}" }}"
                        )
                    }
                }

                // 从 Remote Config 读取默认值并初始化设置
                SettingStateManager.initializeFromRemoteConfig()
            } catch (e: Exception) {
                LogUtils.e("IntelliMateApp", "初始化 Remote Config 失败: ${e.message}", e)
                // 即使 Remote Config 失败，也使用本地默认值初始化
                SettingStateManager.initializeFromRemoteConfig()
            }
        }
    }

    /**
     * Setup FCM message handler
     *
     * Connects firebase layer (core/firebase) with common layer (core/common)
     * Uses default implementation that publishes events via EventBus
     */
    private fun setupFCMessageHandler() {
        FirebaseManager.setMessageHandler(FCMessageHandlerImpl())
        LogUtils.d("IntelliMateApp", "FCM 消息处理器已设置")
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
                // Check if user is logged in before uploading token
                // This avoids 401 errors when token is obtained before login
                if (!IntySetting.isLogin() || IntySetting.getCurToken().isEmpty()) {
                    LogUtils.w("IntelliMateApp", "用户未登录，跳过 FCM Token 上传。登录后将自动上传。")
                    return
                }

                // Delegate to UserService in data layer
                when (val result = UserService.registerDeviceToken(token)) {
                    is ApiResult.Success -> {
                        LogUtils.i("IntelliMateApp", "FCM Token 上传成功")
                    }

                    is ApiResult.Error -> {
                        LogUtils.e("IntelliMateApp", "FCM Token 上传失败: ${result.message}")
                    }
                }
            }
        })
        LogUtils.d("IntelliMateApp", "FCM Token 上传回调已设置")
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
