package com.ai.intellimate

import ai.sxwl.android.common.analytics.GlobalExceptionHandler
import ai.sxwl.android.common.fcm.FCMessageHandlerImpl
import ai.sxwl.android.data.billing.BillingRepository
import ai.sxwl.android.data.di.DataModule
import ai.sxwl.android.data.http.ApiResult
import ai.sxwl.android.data.http.IntyNetworkManager
import ai.sxwl.android.data.http.config.NetworkConfig
import ai.sxwl.android.data.http.services.UserService
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.data.store.SettingStateManager
import ai.sxwl.android.firebase.FCMTokenUploadCallback
import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.utils.AppUtils
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

        // 记录并验证 baseUrl 配置（特别是 release 构建）
        // 如果验证失败，会直接退出应用，不继续执行后续初始化
        if (!logAndValidateBaseUrl()) {
            // 验证失败，应用即将退出，不继续执行初始化
            return
        }

        // 初始化缓存提供者并注入到DataModule
        val chatCacheProvider = AgentCacheProviderImpl()
        val recommendedCacheProvider = RecommendedAgentCacheProviderImpl()
        DataModule.setAgentCacheProvider(chatCacheProvider)
        DataModule.setRecommendedCacheProvider(recommendedCacheProvider)

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
        // 注意：Remote Config 参数会在 initializeRemoteConfigDefaults() 中获取完成后补充上报
        FirebaseManager.logEvent(FirebaseManager.Events.APP_OPEN)

        // 设置设备信息
        FirebaseManager.setDeviceInfo()
    }

    /** 初始化 Remote Config 默认值并获取配置 用于设置聊天开关的默认值（Keep Talking 和 Auto Play Voice） */
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
                        // 首页默认 Tab 索引（0 = Chat tab）
                        FirebaseManager.RemoteConfigKeys.HOME_PAGE_DEFAULT_TAB_INDEX to 0L,
                    )
                )

                FirebaseManager.fetchAndActivateRemoteConfigForced()

                // 获取 Remote Config 参数值
                val autoEnableKeepTalking =
                    FirebaseManager.getRemoteConfigBoolean(
                        FirebaseManager.RemoteConfigKeys.AUTO_ENABLE_KEEP_TALKING
                    )
                val autoPlayOpeningVoice =
                    FirebaseManager.getRemoteConfigBoolean(
                        FirebaseManager.RemoteConfigKeys.AUTO_PLAY_OPENING_VOICE
                    )
                val homePageDefaultTabIndex =
                    FirebaseManager.getRemoteConfigLong(
                        FirebaseManager.RemoteConfigKeys.HOME_PAGE_DEFAULT_TAB_INDEX
                    )

                if (ai.sxwl.android.utils.AppUtils.isAppDebug()) {
                    LogUtils.d(
                        "IntelliMateApp",
                        "Remote Config home_page_default_tab_index = $homePageDefaultTabIndex",
                    )
                }

                // 上报 Remote Config 配置参数到 APP_OPEN 事件（补充上报）
                // 注意：APP_OPEN 事件已经在 initializeFirebaseAnalytics() 中上报，这里补充上报配置参数
                // Firebase Analytics 允许同一个事件多次上报，每次上报都会记录一次事件
                FirebaseManager.logEvent(
                    FirebaseManager.Events.APP_OPEN,
                    FirebaseManager.safeEventParams(
                        "remote_config_auto_enable_keep_talking" to autoEnableKeepTalking,
                        "remote_config_auto_play_opening_voice" to autoPlayOpeningVoice,
                        "remote_config_home_page_default_tab_index" to homePageDefaultTabIndex,
                    ),
                )

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
     * Connects firebase layer (core/firebase) with common layer (core/common) Uses default
     * implementation that publishes events via EventBus
     */
    private fun setupFCMessageHandler() {
        FirebaseManager.setMessageHandler(FCMessageHandlerImpl())
    }

    /**
     * Setup FCM token upload callback
     *
     * Connects infrastructure layer (core/firebase) with data layer (core/data) This avoids
     * circular dependency between modules
     */
    private fun setupFCMTokenUploadCallback() {
        FirebaseManager.setTokenUploadCallback(
            object : FCMTokenUploadCallback {
                override suspend fun uploadToken(token: String) {
                    // Check if user is logged in before uploading token
                    // This avoids 401 errors when token is obtained before login
                    if (!IntySetting.isLogin() || IntySetting.getCurToken().isEmpty()) {
                        LogUtils.w(
                            "IntelliMateApp",
                            "用户未登录，跳过 FCM Token 上传。登录后将自动上传。"
                        )
                        return
                    }

                    // Delegate to UserService in data layer
                    when (val result = UserService.registerDeviceToken(token)) {
                        is ApiResult.Success -> {
                            // Token 上传成功
                        }

                        is ApiResult.Error -> {
                            LogUtils.e("IntelliMateApp", "FCM Token 上传失败: ${result.message}")
                        }
                    }
                }
            }
        )
    }

    /**
     * 记录并验证 baseUrl 配置
     * 对于 release 构建，如果 baseUrl 不正确，直接退出应用
     *
     * @return Boolean 返回 true 表示验证通过或不需要验证，可以继续执行；返回 false 表示验证失败，应用即将退出
     */
    private fun logAndValidateBaseUrl(): Boolean {
        val buildType = NetworkConfig.getCurrentBuildType()
        val baseUrl = NetworkConfig.getBaseUrl()

        // 记录 baseUrl 信息（所有构建类型都记录）
        LogUtils.i("IntelliMateApp", "当前构建类型: ${buildType.value}, baseUrl: $baseUrl")

        // 上报到 Firebase（便于监控）
        try {
            FirebaseManager.setCustomKey("app_build_type", buildType.value)
            FirebaseManager.setCustomKey("app_base_url", baseUrl)
        } catch (e: Exception) {
            LogUtils.w("IntelliMateApp", "设置 Firebase 自定义键失败: ${e.message}")
        }

        // Release 构建的强验证
        if (buildType == NetworkConfig.BuildType.RELEASE) {
            val (isValid, errorMessage) = NetworkConfig.validateReleaseBaseUrl()
            if (!isValid) {
                // 记录严重错误
                LogUtils.e("IntelliMateApp", "❌ 严重错误: $errorMessage")

                // 上报到 Firebase Crashlytics（尝试上报，但不阻塞退出）
                try {
                    FirebaseManager.setCustomKey("base_url_validation_failed", true)
                    FirebaseManager.setCustomKey("base_url_validation_error", errorMessage)
                    FirebaseManager.recordException(
                        IllegalStateException("Release 构建 baseUrl 验证失败: $errorMessage")
                    )
                } catch (e: Exception) {
                    LogUtils.e("IntelliMateApp", "上报 Firebase 失败: ${e.message}")
                    // 即使上报失败，也要退出应用
                }

                // 直接退出应用，不继续运行
                // 这是一个严重的安全问题，必须立即退出
                LogUtils.e(
                    "IntelliMateApp",
                    "Release 构建 baseUrl 配置错误，强制退出应用。错误: $errorMessage"
                )
                AppUtils.exitApp()
                // 返回 false，表示验证失败，调用方不应继续执行初始化
                return false
            } else {
                LogUtils.i("IntelliMateApp", "✅ Release 构建 baseUrl 验证通过: $baseUrl")
            }
        }

        // 验证通过或不需要验证，返回 true
        return true
    }

    override fun onTerminate() {
        super.onTerminate()
        // 应用退出时释放Billing连接
        if (BillingRepository.isInitialized()) {
            BillingRepository.release()
        }
    }
}
