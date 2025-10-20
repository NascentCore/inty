package com.ai.inty.utils

import android.content.Context
import android.os.Bundle
import com.google.firebase.analytics.FirebaseAnalytics
import com.google.firebase.crashlytics.FirebaseCrashlytics
import com.google.firebase.perf.FirebasePerformance
import com.inty.utils.log.EasyLog
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import java.util.concurrent.ConcurrentHashMap

/** Firebase 统一管理器 负责 Firebase 服务的初始化、管理和错误处理 */
object FirebaseManager {

    private var isInitialized = false

    // 缓存 Firebase 实例，避免重复获取
    private var analytics: FirebaseAnalytics? = null
    private var crashlytics: FirebaseCrashlytics? = null
    private var performance: FirebasePerformance? = null

    private data class Config(
        val analyticsEnabled: Boolean = true,
        val crashlyticsEnabled: Boolean = true,
        val performanceEnabled: Boolean = true,
        val disabledEvents: Set<String> = emptySet(),
        val samplingRates: Map<String, Double> = emptyMap(),
        val minIntervalMsPerEvent: Map<String, Long> = emptyMap(),
    )

    @Volatile
    private var config: Config =
        Config(
            analyticsEnabled = true,
            crashlyticsEnabled = true,
            performanceEnabled = true,
            // 低价值事件默认加入采样
            samplingRates =
                mapOf(
                    "user_interaction" to 0.1,
                    "message_sent" to 0.5,
                    // 保留高价值 100%：失败/401/最终失败/页面
                ),
            minIntervalMsPerEvent = mapOf("user_interaction" to 5_000L, "message_sent" to 1_000L),
        )

    // 错误统计，避免重复错误日志
    private val errorCounts = ConcurrentHashMap<String, Int>()
    private val maxErrorLogs = 5 // 每种错误最多记录5次

    private val lastEventTimes = ConcurrentHashMap<String, Long>()

    /** 初始化 Firebase 服务 应该在 Application.onCreate() 中调用 */
    fun initialize(context: Context) {
        if (isInitialized) {
            EasyLog.log("FirebaseManager - 已经初始化，跳过重复初始化")
            return
        }

        try {
            val appContext = context.applicationContext

            // 初始化 Firebase Analytics
            analytics = FirebaseAnalytics.getInstance(appContext)

            // 初始化 Firebase Crashlytics
            crashlytics = FirebaseCrashlytics.getInstance()

            // 初始化 Firebase Performance
            performance = FirebasePerformance.getInstance()

            isInitialized = true
        } catch (e: Exception) {
            EasyLog.log("FirebaseManager - 初始化失败: ${e.message}", EasyLog.ERROR)
            // 即使初始化失败，也不应该崩溃应用
        }
    }

    /** 检查是否已初始化 */
    fun isInitialized(): Boolean = isInitialized

    /** 安全地获取 Analytics 实例 */
    fun getAnalytics(): FirebaseAnalytics? {
        if (!isInitialized) {
            logError("getAnalytics", "FirebaseManager not initialized")
            return null
        }
        if (!config.analyticsEnabled) return null
        return analytics
    }

    /** 安全地获取 Crashlytics 实例 */
    fun getCrashlytics(): FirebaseCrashlytics? {
        if (!isInitialized) {
            logError("getCrashlytics", "FirebaseManager not initialized")
            return null
        }
        if (!config.crashlyticsEnabled) return null
        return crashlytics
    }

    /** 安全地获取 Performance 实例 */
    fun getPerformance(): FirebasePerformance? {
        if (!isInitialized) {
            logError("getPerformance", "FirebaseManager not initialized")
            return null
        }
        if (!config.performanceEnabled) return null
        return performance
    }

    /** 安全地记录事件到 Analytics */
    fun logEvent(eventName: String, parameters: Map<String, Any> = emptyMap()) {
        try {
            if (!shouldLogEvent(eventName)) return
            val analytics = getAnalytics() ?: return

            // 在后台线程执行，避免阻塞主线程
            CoroutineScope(Dispatchers.IO).launch {
                try {
                    val bundle = createBundle(parameters)
                    analytics.logEvent(eventName, bundle)
                } catch (e: Exception) {
                    logError("logEvent", "Failed to log event: ${e.message}")
                }
            }
        } catch (e: Exception) {
            logError("logEvent", "Failed to create event: ${e.message}")
        }
    }

    /** 安全地记录页面访问 */
    fun logScreenView(
        screenName: String,
        screenClass: String,
        additionalParams: Map<String, Any> = emptyMap(),
    ) {
        try {
            val analytics = getAnalytics() ?: return

            CoroutineScope(Dispatchers.IO).launch {
                try {
                    val bundle =
                        Bundle().apply {
                            putString(FirebaseAnalytics.Param.SCREEN_NAME, screenName)
                            putString(FirebaseAnalytics.Param.SCREEN_CLASS, screenClass)
                            putParamsToBundle(this, additionalParams)
                        }
                    analytics.logEvent(FirebaseAnalytics.Event.SCREEN_VIEW, bundle)
                } catch (e: Exception) {
                    logError("logScreenView", "Failed to log screen view: ${e.message}")
                }
            }
        } catch (e: Exception) {
            logError("logScreenView", "Failed to create screen view: ${e.message}")
        }
    }

    /** 安全地设置自定义键 */
    fun setCustomKey(key: String, value: String) {
        try {
            val crashlytics = getCrashlytics() ?: return

            CoroutineScope(Dispatchers.IO).launch {
                try {
                    crashlytics.setCustomKey(key, value)
                } catch (e: Exception) {
                    logError("setCustomKey", "Failed to set custom key: ${e.message}")
                }
            }
        } catch (e: Exception) {
            logError("setCustomKey", "Failed to create custom key: ${e.message}")
        }
    }

    /** 安全地记录异常 */
    fun recordException(exception: Throwable, customKeys: Map<String, String> = emptyMap()) {
        try {
            val crashlytics = getCrashlytics() ?: return

            CoroutineScope(Dispatchers.IO).launch {
                try {
                    customKeys.forEach { (key, value) -> crashlytics.setCustomKey(key, value) }
                    crashlytics.recordException(exception)
                } catch (e: Exception) {
                    logError("recordException", "Failed to record exception: ${e.message}")
                }
            }
        } catch (e: Exception) {
            logError("recordException", "Failed to create exception record: ${e.message}")
        }
    }

    /** 安全地设置用户ID */
    fun setUserId(userId: String) {
        try {
            val analytics = getAnalytics()
            val crashlytics = getCrashlytics()

            CoroutineScope(Dispatchers.IO).launch {
                try {
                    analytics?.setUserId(userId)
                    crashlytics?.setUserId(userId)
                } catch (e: Exception) {
                    logError("setUserId", "Failed to set user ID: ${e.message}")
                }
            }
        } catch (e: Exception) {
            logError("setUserId", "Failed to create user ID: ${e.message}")
        }
    }

    /** 安全地设置用户属性 */
    fun setUserProperty(property: String, value: String) {
        try {
            val analytics = getAnalytics()
            val crashlytics = getCrashlytics()

            CoroutineScope(Dispatchers.IO).launch {
                try {
                    analytics?.setUserProperty(property, value)
                    crashlytics?.setCustomKey("user_$property", value)
                } catch (e: Exception) {
                    logError("setUserProperty", "Failed to set user property: ${e.message}")
                }
            }
        } catch (e: Exception) {
            logError("setUserProperty", "Failed to create user property: ${e.message}")
        }
    }

    /** 更新日志开关与采样配置 */
    fun updateSwitches(
        enableAnalytics: Boolean? = null,
        enableCrashlytics: Boolean? = null,
        enablePerformance: Boolean? = null,
        disabledEvents: Set<String>? = null,
        samplingRates: Map<String, Double>? = null,
        minIntervalMsPerEvent: Map<String, Long>? = null,
    ) {
        config =
            config.copy(
                analyticsEnabled = enableAnalytics ?: config.analyticsEnabled,
                crashlyticsEnabled = enableCrashlytics ?: config.crashlyticsEnabled,
                performanceEnabled = enablePerformance ?: config.performanceEnabled,
                disabledEvents = disabledEvents ?: config.disabledEvents,
                samplingRates = samplingRates ?: config.samplingRates,
                minIntervalMsPerEvent = minIntervalMsPerEvent ?: config.minIntervalMsPerEvent,
            )
    }

    private fun shouldLogEvent(eventName: String): Boolean {
        if (!config.analyticsEnabled) return false
        if (config.disabledEvents.contains(eventName)) return false

        // 限频
        val minInterval = config.minIntervalMsPerEvent[eventName]
        if (minInterval != null) {
            val last = lastEventTimes[eventName] ?: 0L
            val now = System.currentTimeMillis()
            if (now - last < minInterval) return false
            lastEventTimes[eventName] = now
        }

        // 采样
        val rate = config.samplingRates[eventName] ?: 1.0
        if (rate >= 1.0) return true
        return Math.random() < rate
    }

    /** 创建 Bundle 对象 */
    private fun createBundle(parameters: Map<String, Any>): Bundle {
        return Bundle().apply { putParamsToBundle(this, parameters) }
    }

    /** 将参数添加到 Bundle */
    private fun putParamsToBundle(bundle: Bundle, parameters: Map<String, Any>) {
        parameters.forEach { (key, value) ->
            when (value) {
                is String -> bundle.putString(key, value)
                is Int -> bundle.putInt(key, value)
                is Long -> bundle.putLong(key, value)
                is Double -> bundle.putDouble(key, value)
                is Float -> bundle.putFloat(key, value)
                is Boolean -> bundle.putBoolean(key, value)
                else -> bundle.putString(key, value.toString())
            }
        }
    }

    /** 记录错误，避免重复日志 */
    private fun logError(operation: String, message: String) {
        val key = "$operation:$message"
        val count = errorCounts.getOrDefault(key, 0)

        if (count < maxErrorLogs) {
            errorCounts[key] = count + 1
            EasyLog.log("FirebaseManager - $operation failed: $message", EasyLog.ERROR)
        }
    }

    /** 清理资源 */
    fun cleanup() {
        isInitialized = false
        analytics = null
        crashlytics = null
        performance = null
        errorCounts.clear()
        EasyLog.log("FirebaseManager - 资源清理完成")
    }
}
