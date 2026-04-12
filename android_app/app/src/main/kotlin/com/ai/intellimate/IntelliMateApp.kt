package com.ai.intellimate

import ai.sxwl.android.common.analytics.GlobalExceptionHandler
import ai.sxwl.android.common.fcm.FCMessageHandlerImpl
import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.DeviceTokenRegisterRequest
import ai.sxwl.android.data.billing.BillingRepository
import ai.sxwl.android.data.di.DataModule
import ai.sxwl.android.data.http.NetworkStackCoordinator
import ai.sxwl.android.data.http.config.DebugBackendEndpointStore
import ai.sxwl.android.data.http.config.NetworkConfig
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.data.store.SettingStateManager
import ai.sxwl.android.firebase.FCMTokenUploadCallback
import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.utils.AppUtils
import ai.sxwl.android.utils.LogUtils
import android.app.Application
import com.ai.intellimate.boost.BoostManager
import com.ai.intellimate.notifications.PushNotificationManager
import com.ai.intellimate.utils.AgentCacheProviderImpl
import com.ai.intellimate.utils.RecommendedAgentCacheProviderImpl
import com.ai.intellimate.utils.UnifiedStartupManager
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

/** 应用Application的实现类 */
class IntelliMateApp : Application() {

    override fun onCreate() {
        super.onCreate()

        IntySetting.initialize(this)

        DebugBackendEndpointStore.removeLegacyChatWebSocketPreferenceKeysIfPresent()

        NetworkStackCoordinator.initialize(this, buildType = BuildConfig.BUILD_TYPE)

        // 验证 baseUrl 配置（必须在其他初始化之前，如果失败会退出应用）
        if (!logAndValidateBaseUrl()) {
            return
        }

        val chatCacheProvider = AgentCacheProviderImpl()
        val recommendedCacheProvider = RecommendedAgentCacheProviderImpl()
        DataModule.setAgentCacheProvider(chatCacheProvider)
        DataModule.setRecommendedCacheProvider(recommendedCacheProvider)

        UnifiedStartupManager.initializeEssential(this)

        // 初始化本地 为角色应援/Boost 体系
        // TODO：是否可以讲 IntySetting 初始化也转移到这里。
        BoostManager.initialize(this)
        initializeFirebaseAnalytics()
        initializeRemoteConfigDefaults()
        setupFCMessageHandler()
        setupFCMTokenUploadCallback()
        PushNotificationManager.getInstance(this).initialize()
        GlobalExceptionHandler.install(this)

        CoroutineScope(Dispatchers.IO).launch {
            try {
                UnifiedStartupManager.initializeAsync(this@IntelliMateApp)
            } catch (e: Exception) {
                LogUtils.e("IntelliMateApp", "异步初始化失败: ${e.message}")
            }
        }
    }

    private fun initializeFirebaseAnalytics() {
        FirebaseManager.logEvent(FirebaseManager.Events.APP_OPEN)
        FirebaseManager.setDeviceInfo()
    }

    private fun initializeRemoteConfigDefaults() {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                FirebaseManager.setRemoteConfigDefaults(
                    mapOf(
                        FirebaseManager.RemoteConfigKeys.AUTO_ENABLE_KEEP_TALKING to false,
                        FirebaseManager.RemoteConfigKeys.AUTO_PLAY_OPENING_VOICE to true,
                        FirebaseManager.RemoteConfigKeys.HOME_PAGE_DEFAULT_TAB_INDEX to 0L,
                    )
                )

                FirebaseManager.fetchAndActivateRemoteConfigForced()

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

                FirebaseManager.logEvent(
                    FirebaseManager.Events.APP_OPEN,
                    FirebaseManager.safeEventParams(
                        "remote_config_auto_enable_keep_talking" to autoEnableKeepTalking,
                        "remote_config_auto_play_opening_voice" to autoPlayOpeningVoice,
                        "remote_config_home_page_default_tab_index" to homePageDefaultTabIndex,
                    ),
                )

                SettingStateManager.initializeFromRemoteConfig()
            } catch (e: Exception) {
                LogUtils.e("IntelliMateApp", "初始化 Remote Config 失败: ${e.message}", e)
                SettingStateManager.initializeFromRemoteConfig()
            }
        }
    }

    private fun setupFCMessageHandler() {
        FirebaseManager.setMessageHandler(FCMessageHandlerImpl())
    }

    private fun setupFCMTokenUploadCallback() {
        FirebaseManager.setTokenUploadCallback(
            object : FCMTokenUploadCallback {
                override suspend fun uploadToken(token: String) {
                    if (!IntySetting.isLogin() || IntySetting.getCurToken().isEmpty()) {
                        return
                    }

                    val request = DeviceTokenRegisterRequest(token = token)
                    when (val result = NetServiceMgr.getUserApi().registerDeviceToken(request)) {
                        is HttpResult.Success -> {}
                        is HttpResult.Failure -> {
                            LogUtils.e("IntelliMateApp", "FCM Token 上传失败: ${result.message}")
                        }
                    }
                }
            }
        )
    }

    private fun logAndValidateBaseUrl(): Boolean {
        val buildType = NetworkConfig.getCurrentBuildType()
        val baseUrl = NetworkConfig.getBaseUrl()

        LogUtils.i("IntelliMateApp", "当前构建类型: ${buildType.value}, baseUrl: $baseUrl")

        ensureFirebaseInitialized()

        try {
            FirebaseManager.setCustomKey("app_build_type", buildType.value)
            FirebaseManager.setCustomKey("app_base_url", baseUrl)
        } catch (e: Exception) {
            LogUtils.w("IntelliMateApp", "设置 Firebase 自定义键失败: ${e.message}")
        }

        if (buildType == NetworkConfig.BuildType.RELEASE) {
            val (isValid, errorMessage) = NetworkConfig.validateReleaseBaseUrl()
            if (!isValid) {
                LogUtils.e("IntelliMateApp", "严重错误: $errorMessage")

                try {
                    ensureFirebaseInitialized()
                    FirebaseManager.setCustomKey("base_url_validation_failed", true)
                    FirebaseManager.setCustomKey("base_url_validation_error", errorMessage)
                    FirebaseManager.recordException(
                        IllegalStateException("Release 构建 baseUrl 验证失败: $errorMessage")
                    )
                } catch (e: Exception) {
                    LogUtils.e("IntelliMateApp", "上报 Firebase 失败: ${e.message}")
                }

                LogUtils.e("IntelliMateApp", "Release 构建 baseUrl 配置错误，强制退出应用。错误: $errorMessage")
                AppUtils.exitApp()
                return false
            }
        }

        return true
    }

    private fun ensureFirebaseInitialized() {
        if (!FirebaseManager.isInitialized()) {
            try {
                FirebaseManager.initialize(this)
            } catch (e: Exception) {
                LogUtils.e("IntelliMateApp", "Firebase 初始化失败: ${e.message}")
            }
        }
    }

    override fun onTerminate() {
        super.onTerminate()
        // 应用退出时释放Billing连接
        if (BillingRepository.isInitialized()) {
            BillingRepository.release()
        }
    }
}
