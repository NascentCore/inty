package com.ai.inty

import ai.sxwl.android.utils.LogUtils
import android.app.Application
import com.ai.inty.billing.BillingRepository
import com.ai.inty.netapi.IntyNetworkManager
import com.ai.inty.utils.FirebaseManager
import com.ai.inty.utils.GlobalExceptionHandler
import com.ai.inty.utils.NetworkManager
import com.ai.inty.utils.UnifiedStartupManager
import kotlinx.coroutines.launch

/** 应用Application的实现类 */
class IntyApp : Application() {

    override fun onCreate() {
        super.onCreate()

        // 立即初始化日志，不阻塞
        LogUtils.getConfig()
            .setLogSwitch(true)
            .setConsoleSwitch(true)
            .setGlobalTag("IntyApp")

        // 立即初始化网络管理器（轻量级，不阻塞）
        NetworkManager.getInstance().initialize(this)
        IntyNetworkManager.initialize(this)

        // 立即初始化统一启动管理器（只做必要的登录判断，不阻塞）
        UnifiedStartupManager.initializeEssential(this)

        // 统一初始化 Firebase 服务
        FirebaseManager.initialize(this)
        // 默认开关：可由你后续策略化控制（Remote Config / 本地开关）
        FirebaseManager.updateSwitches(
            enableAnalytics = true,
            enableCrashlytics = true,
            enablePerformance = true,
            // 可禁用低价值事件示例：
            disabledEvents = emptySet(),
            // 采样/限频默认值已在 FirebaseManager 内设置，可按需覆盖：
            samplingRates = null,
            minIntervalMsPerEvent = null,
        )

        // 兼容层已弃用，不再初始化 FirebaseAnalyticsHelper

        // 记录应用启动事件
        FirebaseManager.logEvent("app_start")

        // 安装全局异常处理器
        GlobalExceptionHandler.install(this)

        // 异步初始化所有可能阻塞的组件
        kotlinx.coroutines.CoroutineScope(kotlinx.coroutines.Dispatchers.IO).launch {
            try {
                // 异步进行完整的数据预加载和缓存
                UnifiedStartupManager.initializeAsync(this@IntyApp)
            } catch (e: Exception) {
                LogUtils.e("IntyApp - 异步初始化失败: ${e.message}")
            }
        }
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
