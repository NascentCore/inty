package ai.sxwl.android.firebase

import ai.sxwl.android.utils.LogUtils
import android.content.Context
import android.os.Bundle
import com.google.firebase.analytics.FirebaseAnalytics
import com.google.firebase.crashlytics.FirebaseCrashlytics
import com.google.firebase.messaging.FirebaseMessaging
import com.google.firebase.perf.FirebasePerformance
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Firebase管理器
 * 负责Firebase Analytics、Crashlytics和Performance的初始化和使用
 *
 * 特性：
 * - 线程安全的单例模式
 * - 完善的错误处理和日志记录
 * - 支持采样和限频机制
 * - 操作避免阻止主线程
 * - 资源管理和内存优化
 */
object FirebaseManager {
// 使用AtomicBoolean确保线程安全
    private val isInitialized = AtomicBoolean(false)
// 存储Fire实例库，避免重复
    @Volatile
    private var analytics: FirebaseAnalytics? = null

    @Volatile
    private var crashlytics: FirebaseCrashlytics? = null

    @Volatile
    private var performance: FirebasePerformance? = null
// 使用SupervisorJob确保子协程异常不影响其他协程
    private val firebaseScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    private data class Config(
        val analyticsEnabled: Boolean = true,
        val crashlyticsEnabled: Boolean = true,
        val performanceEnabled: Boolean = true,
        val disabledEvents: Set<String> = emptySet(),
        val samplingRates: Map<String, Double> = emptyMap(),
        val minIntervalMsPerEvent: Map<String, Long> = emptyMap(),
    )

    @Volatile
    private var config: Config = Config(
        analyticsEnabled = true,
        crashlyticsEnabled = true,
        performanceEnabled = true,
// 低值默认事件加入采样
        samplingRates = mapOf(
            "user_interaction" to 0.1,
            "message_sent" to 0.5,
// 保留高价值100%：失败/401/最终失败/页面
        ),
        minIntervalMsPerEvent = mapOf("user_interaction" to 5_000L, "message_sent" to 1_000L),
    )
// 错误统计，避免重复错误日志
    private val errorCounts = ConcurrentHashMap<String, Int>()
    private val maxErrorLogs = 5 // 每种错误最多记录5次
    private val lastEventTimes = ConcurrentHashMap<String, Long>()

    /**
     * 初始化Firebase服务
     * 线程安全，支持重复调用
     */
    fun initialize(context: Context) {
        if (isInitialized.get()) {
            LogUtils.i("FirebaseManager - 已经初始化，跳过重复初始化")
            return
        }

        try {
            val appContext = context.applicationContext
// 初始化 Firebase Analytics
            analytics = FirebaseAnalytics.getInstance(appContext)
// 初始化 Firebase Crashlytics
            crashlytics = FirebaseCrashlytics.getInstance()
// 初始化 Firebase 性能
            performance = FirebasePerformance.getInstance()

            isInitialized.set(true)
            LogUtils.i("FirebaseManager - 初始化成功")
        } catch (e: Exception) {
            LogUtils.e("FirebaseManager - 初始化失败: ${e.message}")
//即使初始化失败，也不应该崩溃应用
// 重置状态，允许重试
            isInitialized.set(false)
        }
    }

    /** 检查是否已初始化 */
    fun isInitialized(): Boolean = isInitialized.get()

    /** 安全地获取 Analytics 实例 */
    fun getAnalytics(): FirebaseAnalytics? {
        if (!isInitialized.get()) {
            logError("getAnalytics", "FirebaseManager not initialized")
            return null
        }
        if (!config.analyticsEnabled) return null
        return analytics
    }

    /** 安全地获取 Crashlytics 实例 */
    fun getCrashlytics(): FirebaseCrashlytics? {
        if (!isInitialized.get()) {
            logError("getCrashlytics", "FirebaseManager not initialized")
            return null
        }
        if (!config.crashlyticsEnabled) return null
        return crashlytics
    }

    /** 安全地获取性能实例 */
    fun getPerformance(): FirebasePerformance? {
        if (!isInitialized.get()) {
            logError("getPerformance", "FirebaseManager not initialized")
            return null
        }
        if (!config.performanceEnabled) return null
        return performance
    }

    /**
     * 安全地记录事件到分析
     * 使用SupervisorJob确保异常不会影响其他操作
     */
    fun logEvent(eventName: String, parameters: Map<String, Any> = emptyMap()) {
        if (!shouldLogEvent(eventName)) return

        try {
            val analytics = getAnalytics() ?: return
// 使用firebaseScope确保异常隔离
            firebaseScope.launch {
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

    /**
     * 安全地记录页面访问
     * 使用SupervisorJob确保异常隔离
     */
    fun logScreenView(
        screenName: String,
        screenClass: String,
        additionalParams: Map<String, Any> = emptyMap(),
    ) {
        try {
            val analytics = getAnalytics() ?: return

            firebaseScope.launch {
                try {
                    val bundle = Bundle().apply {
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

    /**
     * 安全地设置用户属性
     * 使用SupervisorJob确保异常隔离
     */
    fun setUserProperty(property: String, value: String) {
        try {
            val analytics = getAnalytics()
            val crashlytics = getCrashlytics()

            firebaseScope.launch {
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

    /**
     * 安全地设置用户ID
     * 使用SupervisorJob确保异常隔离
     */
    fun setUserId(userId: String) {
        try {
            val analytics = getAnalytics()
            val crashlytics = getCrashlytics()

            firebaseScope.launch {
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

    /**
     * 安全地记录异常
     * 使用SupervisorJob确保异常隔离
     */
    fun recordException(exception: Throwable, customKeys: Map<String, String> = emptyMap()) {
        try {
            val crashlytics = getCrashlytics() ?: return

            firebaseScope.launch {
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

    /**
     * 安全地设置自定义键
     */
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

    fun setCustomKey(key: String, value: Boolean) {
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

    fun setCustomKey(key: String, value: Int) {
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

    fun setCustomKey(key: String, value: Long) {
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

    fun setCustomKey(key: String, value: Float) {
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

    fun setCustomKey(key: String, value: Double) {
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

    /**
     * 记录习惯
     */
    fun log(message: String) {
        try {
            val crashlytics = getCrashlytics() ?: return
            CoroutineScope(Dispatchers.IO).launch {
                try {
                    crashlytics.log(message)
                } catch (e: Exception) {
                    logError("log", "Failed to log message: ${e.message}")
                }
            }
        } catch (e: Exception) {
            logError("log", "Failed to create log: ${e.message}")
        }
    }

    /**
     *更新日志开关与采样配置
     */
    fun updateSwitches(
        enableAnalytics: Boolean? = null,
        enableCrashlytics: Boolean? = null,
        enablePerformance: Boolean? = null,
        disabledEvents: Set<String>? = null,
        samplingRates: Map<String, Double>? = null,
        minIntervalMsPerEvent: Map<String, Long>? = null,
    ) {
        config = config.copy(
            analyticsEnabled = enableAnalytics ?: config.analyticsEnabled,
            crashlyticsEnabled = enableCrashlytics ?: config.crashlyticsEnabled,
            performanceEnabled = enablePerformance ?: config.performanceEnabled,
            disabledEvents = disabledEvents ?: config.disabledEvents,
            samplingRates = samplingRates ?: config.samplingRates,
            minIntervalMsPerEvent = minIntervalMsPerEvent ?: config.minIntervalMsPerEvent,
        )
    }

    /**
     * 预定义的事件常量
     */
    object Events {
        const val APP_OPEN = "app_open"
        const val USER_LOGIN = "user_login"
        const val USER_LOGOUT = "user_logout"
        const val CHAT_STARTED = "chat_started"
        const val MESSAGE_SENT = "message_sent"
        const val AI_RESPONSE_RECEIVED = "ai_response_received"
        const val PROFILE_UPDATED = "profile_updated"
        const val SETTINGS_CHANGED = "settings_changed"
    }

    /**
     * 预定义的用户属性常量
     */
    object UserProperties {
        const val USER_TYPE = "user_type"
        const val SUBSCRIPTION_LEVEL = "subscription_level"
        const val APP_VERSION = "app_version"
        const val DEVICE_TYPE = "device_type"
    }

    /**
     * Firebase大众消息注册
     */
    suspend fun registerFCM(): String {
        val token = FirebaseMessaging.getInstance().token.await()
        return token
    }
//区域性能监控相关方法

    /**
     * 开始一个自定义追踪
     */
    fun startTrace(traceName: String): com.google.firebase.perf.metrics.Trace? {
        return try {
            val perf = getPerformance() ?: return null
            val trace = perf.newTrace(traceName)
            trace.start()
            trace
        } catch (e: Exception) {
            logError("startTrace", "Failed to start trace '$traceName': ${e.message}")
            null
        }
    }

    /**
     * 停止追踪并记录
     */
    fun stopTrace(trace: com.google.firebase.perf.metrics.Trace?) {
        try {
            trace?.stop()
        } catch (e: Exception) {
            logError("stopTrace", "Failed to stop trace: ${e.message}")
        }
    }

    /**
     * 为追踪添加自定义属性
     */
    fun putTraceAttribute(
        trace: com.google.firebase.perf.metrics.Trace?,
        attributeName: String,
        value: String
    ) {
        try {
            trace?.putAttribute(attributeName, value)
        } catch (e: Exception) {
            logError("putTraceAttribute", "Failed to put attribute '$attributeName': ${e.message}")
        }
    }

    /**
     * 为追踪添加自定义指标
     */
    fun putTraceMetric(
        trace: com.google.firebase.perf.metrics.Trace?,
        metricName: String,
        value: Long
    ) {
        try {
            trace?.putMetric(metricName, value)
        } catch (e: Exception) {
            logError("putTraceMetric", "Failed to put metric '$metricName': ${e.message}")
        }
    }

    /**
     * 创建网络请求监控
     */
    fun createHttpMetric(
        url: String,
        method: String
    ): Any? {
        return try {
            val perf = getPerformance() ?: return null
            val httpMetric = perf.newHttpMetric(url, method)
            httpMetric
        } catch (e: Exception) {
            logError("createHttpMetric", "Failed to create HTTP metric: ${e.message}")
            null
        }
    }

    /**
     * 开始网络请求监控
     */
    fun startHttpMetric(httpMetric: Any?) {
        try {
            (httpMetric as? com.google.firebase.perf.metrics.HttpMetric)?.start()
        } catch (e: Exception) {
            logError("startHttpMetric", "Failed to start HTTP metric: ${e.message}")
        }
    }

    /**
     * 停止网络请求监控
     */
    fun stopHttpMetric(
        httpMetric: Any?,
        responseCode: Int,
        responseSize: Long? = null
    ) {
        try {
            val metric = httpMetric as? com.google.firebase.perf.metrics.HttpMetric
            if (metric != null) {
                metric.setHttpResponseCode(responseCode)
                responseSize?.let { metric.setResponsePayloadSize(it) }
                metric.stop()
            }
        } catch (e: Exception) {
            logError("stopHttpMetric", "Failed to stop HTTP metric: ${e.message}")
        }
    }

    /**
     * 便捷方法：执行带性能监控的操作
     */
    inline fun <T> trace(
        traceName: String,
        operation: (com.google.firebase.perf.metrics.Trace?) -> T
    ): T {
        val trace = startTrace(traceName)
        return try {
            operation(trace)
        } finally {
            stopTrace(trace)
        }
    }
//区域结束

    /**
     * 清理资源
     * 在应用程序退出时调用，避免内存溢出
     */
    fun cleanup() {
        try {
// 取消所有协程
            firebaseScope.coroutineContext.cancel()
// 清理缓存
            analytics = null
            crashlytics = null
            performance = null
// 状态重置
            isInitialized.set(false)
// 清理统计信息
            errorCounts.clear()
            lastEventTimes.clear()

            LogUtils.i("FirebaseManager - 资源清理完成")
        } catch (e: Exception) {
            LogUtils.e("FirebaseManager - 资源清理失败: ${e.message}")
        }
    }
// 辅助方法
    private fun shouldLogEvent(eventName: String): Boolean {
        if (!isInitialized.get() || !config.analyticsEnabled) return false
        if (eventName in config.disabledEvents) return false
//检查采样率
        val samplingRate = config.samplingRates[eventName] ?: 1.0
        if (Math.random() > samplingRate) return false
//查询限频
        val minInterval = config.minIntervalMsPerEvent[eventName] ?: 0L
        if (minInterval > 0) {
            val lastTime = lastEventTimes[eventName] ?: 0L
            val currentTime = System.currentTimeMillis()
            if (currentTime - lastTime < minInterval) return false
            lastEventTimes[eventName] = currentTime
        }

        return true
    }

    private fun createBundle(parameters: Map<String, Any>): Bundle {
        val bundle = Bundle()
        putParamsToBundle(bundle, parameters)
        return bundle
    }

    private fun putParamsToBundle(bundle: Bundle, parameters: Map<String, Any>) {
        parameters.forEach { (key, value) ->
            when (value) {
                is String -> bundle.putString(key, value)
                is Long -> bundle.putLong(key, value)
                is Int -> bundle.putLong(key, value.toLong())
                is Double -> bundle.putDouble(key, value)
                is Boolean -> bundle.putString(key, value.toString())
                is Float -> bundle.putDouble(key, value.toDouble())
                else -> bundle.putString(key, value.toString())
            }
        }
    }

    private fun logError(operation: String, message: String) {
        val errorKey = "$operation:$message"
        val count = errorCounts.getOrDefault(errorKey, 0)
        if (count < maxErrorLogs) {
            errorCounts[errorKey] = count + 1
            LogUtils.e("FirebaseManager - $operation: $message")
        }
    }
}
