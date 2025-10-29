package ai.sxwl.android.firebase

import ai.sxwl.android.utils.AppUtils
import ai.sxwl.android.utils.DeviceUtils
import ai.sxwl.android.utils.LanguageUtils
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
 * Firebase管理器 负责Firebase Analytics、Crashlytics和Performance的初始化和使用
 *
 * 特性：
 * - 线程安全的单例模式
 * - 完善的错误处理和日志记录
 * - 支持采样和限频机制
 * - 异步操作避免阻塞主线程
 * - 资源管理和内存优化
 */
object FirebaseManager {

    // 使用AtomicBoolean确保线程安全
    private val isInitialized = AtomicBoolean(false)

    // 缓存 Firebase 实例，避免重复获取
    @Volatile private var analytics: FirebaseAnalytics? = null

    @Volatile private var crashlytics: FirebaseCrashlytics? = null

    @Volatile private var performance: FirebasePerformance? = null

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
    private var config: Config =
        Config(
            analyticsEnabled = true,
            crashlyticsEnabled = true,
            performanceEnabled = true,
            // 优化采样配置 - 业务数据点100%采样，性能事件保持现有配置
            disabledEvents =
                setOf(
                    // 完全禁用低价值事件
                    "page_visible", // 页面可见性变化过于频繁
                    "page_hidden", // 页面隐藏事件价值较低
                    "page_lifecycle", // 生命周期事件过于详细
                ),
            samplingRates =
                mapOf(
                    // 🔴 业务数据点 - 100%采样（关键业务事件）
                    Events.APP_OPEN to 1.0, // 应用启动
                    Events.LOGIN to 1.0, // 用户登录
                    Events.SIGN_UP to 1.0, // 用户注册
                    Events.SCREEN_VIEW to 1.0, // 页面访问
                    Events.SELECT_CONTENT to 1.0, // 内容选择
                    Events.SHARE to 1.0, // 分享功能
                    Events.SEARCH to 1.0, // 搜索功能
                    Events.PURCHASE to 1.0, // 购买事件
                    Events.USER_LOGIN to 1.0, // 用户登录
                    Events.USER_LOGOUT to 1.0, // 用户登出
                    Events.CHAT_STARTED to 1.0, // 聊天开始
                    Events.MESSAGE_SENT to 1.0, // 消息发送
                    Events.AI_RESPONSE_RECEIVED to 1.0, // AI回复接收
                    Events.PROFILE_UPDATED to 1.0, // 个人资料更新
                    Events.SETTINGS_CHANGED to 1.0, // 设置变更
                    Events.AGENT_SWITCH to 1.0, // Agent切换
                    Events.SUBSCRIPTION_START to 1.0, // 订阅开始
                    Events.FREE_LIMIT_HIT to 1.0, // 达到免费限制

                    // 🔴 错误和失败事件 - 100%采样
                    "auth_failure" to 1.0, // 认证失败
                    "app_error" to 1.0, // 应用错误
                    "message_send_failure" to 1.0, // 消息发送失败
                    "network_final_failure" to 1.0, // 网络请求最终失败
                    "request_failure" to 1.0, // 请求失败
                    "very_slow_request" to 1.0, // 极慢请求

                    // 🔴 页面追踪事件 - 100%采样
                    "page_leave" to 1.0, // 页面离开
                    "explore_page_view" to 1.0, // 探索页面访问
                    "chat_session_start" to 1.0, // 聊天会话开始
                    "chat_session_end" to 1.0, // 聊天会话结束
                    "message_send_success" to 1.0, // 消息发送成功
                    "free_limit_reached" to 1.0, // 达到免费限制

                    // 🟡 性能相关事件 - 保持现有采样配置
                    "user_interaction" to if (AppUtils.isAppDebug()) 1.0 else 0.1, // 调试100%，发布10%
                    Events.VOICE_PLAYBACK_START to if (AppUtils.isAppDebug()) 1.0 else 0.5, // 调试100%，发布50%
                    "slow_request" to if (AppUtils.isAppDebug()) 1.0 else 0.3, // 调试100%，发布30%
                    "network_retry" to if (AppUtils.isAppDebug()) 1.0 else 0.5, // 调试100%，发布50%
                    "network_request" to if (AppUtils.isAppDebug()) 1.0 else 0.2, // 调试100%，发布20%

                    // 🟡 性能指标事件 - 保持现有采样配置
                    Events.AI_RESPONSE_TIME to if (AppUtils.isAppDebug()) 1.0 else 0.5, // 调试100%，发布50%
                    Events.TTS_GENERATION_TIME to if (AppUtils.isAppDebug()) 1.0 else 0.3, // 调试100%，发布30%
                    Events.VOICE_PLAYBACK_TIME to if (AppUtils.isAppDebug()) 1.0 else 0.3, // 调试100%，发布30%
                    Events.IMAGE_LOAD_TIME to if (AppUtils.isAppDebug()) 1.0 else 0.2, // 调试100%，发布20%
                    Events.PAGE_LOAD_TIME to if (AppUtils.isAppDebug()) 1.0 else 0.3, // 调试100%，发布30%
                    Events.DATABASE_OPERATION_TIME to if (AppUtils.isAppDebug()) 1.0 else 0.2, // 调试100%，发布20%
                ),
            minIntervalMsPerEvent =
                mapOf(
                    // 🔴 业务数据点 - 无限制或很宽松的限频
                    Events.MESSAGE_SENT to if (AppUtils.isAppDebug()) 500L else 1_000L, // 调试0.5秒，发布1秒
                    Events.VOICE_PLAYBACK_START to if (AppUtils.isAppDebug()) 500L else 1_000L, // 调试0.5秒，发布1秒

                    // 🟡 性能相关事件 - 保持现有限频配置
                    "user_interaction" to if (AppUtils.isAppDebug()) 1_000L else 10_000L, // 调试1秒，发布10秒
                    "slow_request" to if (AppUtils.isAppDebug()) 2_000L else 5_000L, // 调试2秒，发布5秒
                    "network_retry" to if (AppUtils.isAppDebug()) 1_000L else 3_000L, // 调试1秒，发布3秒
                    "network_request" to if (AppUtils.isAppDebug()) 500L else 2_000L, // 调试0.5秒，发布2秒
                ),
        )

    // 错误统计，避免重复错误日志
    private val errorCounts = ConcurrentHashMap<String, Int>()
    private val maxErrorLogs = 5 // 每种错误最多记录5次
    private val lastEventTimes = ConcurrentHashMap<String, Long>()

    /** 初始化Firebase服务 线程安全，支持重复调用 */
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

            // 初始化 Firebase Performance
            performance = FirebasePerformance.getInstance()

            isInitialized.set(true)
            LogUtils.i("FirebaseManager - 初始化成功")
        } catch (e: Exception) {
            LogUtils.e("FirebaseManager - 初始化失败: ${e.message}")
            // 即使初始化失败，也不应该崩溃应用
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

    /** 安全地获取 Performance 实例 */
    fun getPerformance(): FirebasePerformance? {
        if (!isInitialized.get()) {
            logError("getPerformance", "FirebaseManager not initialized")
            return null
        }
        if (!config.performanceEnabled) return null
        return performance
    }

    /** 安全地记录事件到 Analytics 使用SupervisorJob确保异常不会影响其他操作 */
    fun logEvent(eventName: String, parameters: Map<String, Any> = emptyMap()) {
        // 调试模式下输出详细日志
        if (AppUtils.isAppDebug()) {
            LogUtils.d("FirebaseManager", "尝试记录事件: $eventName, 参数: $parameters")
        }

        if (!shouldLogEvent(eventName)) {
            if (AppUtils.isAppDebug()) {
                LogUtils.d("FirebaseManager", "事件被过滤: $eventName")
            }
            return
        }

        try {
            val analytics = getAnalytics() ?: return

            // 使用firebaseScope确保异常隔离
            firebaseScope.launch {
                try {
                    val bundle = createBundle(parameters)
                    analytics.logEvent(eventName, bundle)

                    // 调试模式下确认事件已发送
                    if (AppUtils.isAppDebug()) {
                        LogUtils.d("FirebaseManager", "✅ 事件已发送: $eventName")
                    }
                } catch (e: Exception) {
                    logError("logEvent", "Failed to log event: ${e.message}")
                }
            }
        } catch (e: Exception) {
            logError("logEvent", "Failed to create event: ${e.message}")
        }
    }

    /** 安全地记录页面访问 使用SupervisorJob确保异常隔离 */
    fun logScreenView(
        screenName: String,
        screenClass: String,
        additionalParams: Map<String, Any> = emptyMap(),
    ) {
        try {
            val analytics = getAnalytics() ?: return

            firebaseScope.launch {
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

    /** 安全地设置用户属性 使用SupervisorJob确保异常隔离 */
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

    /** 安全地设置用户ID 使用SupervisorJob确保异常隔离 */
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

    /** 安全地记录异常 使用SupervisorJob确保异常隔离 */
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

    /** 设置Crashlytics自定义键 - 支持多种类型 */
    fun setCustomKey(key: String, value: Any?) {
        try {
            val crashlytics = getCrashlytics() ?: return

            CoroutineScope(Dispatchers.IO).launch {
                try {
                    when (value) {
                        is String -> crashlytics.setCustomKey(key, value)
                        is Boolean -> crashlytics.setCustomKey(key, value)
                        is Int -> crashlytics.setCustomKey(key, value)
                        is Long -> crashlytics.setCustomKey(key, value)
                        is Float -> crashlytics.setCustomKey(key, value)
                        is Double -> crashlytics.setCustomKey(key, value)
                        null -> crashlytics.setCustomKey(key, "null")
                        else -> crashlytics.setCustomKey(key, value.toString())
                    }
                } catch (e: Exception) {
                    logError("setCustomKey", "Failed to set custom key: ${e.message}")
                }
            }
        } catch (e: Exception) {
            logError("setCustomKey", "Failed to create custom key: ${e.message}")
        }
    }

    /** 记录自定义日志 */
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

    /** 预定义的事件常量 */
    object Events {
        // Firebase内置事件
        const val APP_OPEN = FirebaseAnalytics.Event.APP_OPEN
        const val LOGIN = FirebaseAnalytics.Event.LOGIN
        const val SIGN_UP = FirebaseAnalytics.Event.SIGN_UP
        const val SCREEN_VIEW = FirebaseAnalytics.Event.SCREEN_VIEW
        const val SELECT_CONTENT = FirebaseAnalytics.Event.SELECT_CONTENT
        const val SHARE = FirebaseAnalytics.Event.SHARE
        const val SEARCH = FirebaseAnalytics.Event.SEARCH
        const val PURCHASE = FirebaseAnalytics.Event.PURCHASE

        // 业务自定义事件
        const val USER_LOGIN = "user_login"
        const val USER_LOGOUT = "user_logout"
        const val CHAT_STARTED = "chat_started"
        const val MESSAGE_SENT = "message_sent"
        const val AI_RESPONSE_RECEIVED = "ai_response_received"
        const val PROFILE_UPDATED = "profile_updated"
        const val SETTINGS_CHANGED = "settings_changed"

        // 性能相关事件
        const val AI_RESPONSE_TIME = "ai_response_time"
        const val TTS_GENERATION_TIME = "tts_generation_time"
        const val VOICE_PLAYBACK_TIME = "voice_playback_time"
        const val IMAGE_LOAD_TIME = "image_load_time"
        const val PAGE_LOAD_TIME = "page_load_time"
        const val DATABASE_OPERATION_TIME = "database_operation_time"

        // 业务关键事件
        const val AGENT_SWITCH = "agent_switch"

        // UI交互事件
        const val IMAGE_SHOW_SUCCESS = "image_show_success"
        const val AUDIO_PLAY_END = "audio_play_end"
        const val PULL_UP_INPUT = "pull_up_input"
        const val VOICE_PLAYBACK_START = "voice_playback_start"
        const val IMAGE_GENERATION_START = "image_generation_start"
        const val SUBSCRIPTION_START = "subscription_start"
        const val FREE_LIMIT_HIT = "free_limit_hit"
    }

    /** 预定义的用户属性常量 */
    object UserProperties {
        const val USER_TYPE = "user_type"
        const val SUBSCRIPTION_LEVEL = "subscription_level"
        const val APP_VERSION = "app_version"
        const val DEVICE_TYPE = "device_type"
        const val DEVICE_MODEL = "device_model"
        const val OS_VERSION = "os_version"
        const val APP_BUILD_TYPE = "app_build_type"
        const val USER_REGION = "user_region"
        const val LANGUAGE = "language"
    }

    /** Firebase 推送消息注册 */
    suspend fun registerFCM(): String {
        val token = FirebaseMessaging.getInstance().token.await()
        return token
    }

    /** 设置设备信息 */
    fun setDeviceInfo() {
        try {
            // 设置应用版本信息
            val versionName = AppUtils.getVersionName()
            val versionCode = AppUtils.getVersionCode()
            setUserProperty(UserProperties.APP_VERSION, versionName)
            setUserProperty("app_version_code", versionCode.toString())

            // 设置设备信息
            setUserProperty(UserProperties.DEVICE_MODEL, DeviceUtils.getModel())
            setUserProperty(UserProperties.OS_VERSION, DeviceUtils.getSDKVersionName())
            setUserProperty("os_version_code", DeviceUtils.getSDKVersionCode().toString())
            setUserProperty(UserProperties.DEVICE_TYPE, "android")
            setUserProperty("device_brand", DeviceUtils.getBrand())
            setUserProperty("device_manufacturer", DeviceUtils.getManufacturer())
            setUserProperty("device_product", DeviceUtils.getProduct())

            // 设置屏幕信息
            setUserProperty("screen_width", DeviceUtils.getScreenWidth().toString())
            setUserProperty("screen_height", DeviceUtils.getScreenHeight().toString())
            setUserProperty("screen_density", DeviceUtils.getScreenDensity().toString())
            setUserProperty("screen_density_dpi", DeviceUtils.getScreenDensityDpi().toString())

            // 设置语言和地区信息
            val currentLocale = LanguageUtils.getCurrentLanguage()
            setUserProperty(UserProperties.LANGUAGE, currentLocale.language)
            setUserProperty(UserProperties.USER_REGION, currentLocale.country)
            setUserProperty("locale_display", currentLocale.displayName)

            // 设置设备特殊属性
            setUserProperty("is_emulator", DeviceUtils.isEmulator().toString())
            setUserProperty("is_rooted", DeviceUtils.isDeviceRooted().toString())
            setUserProperty("is_debug", AppUtils.isAppDebug().toString())

            LogUtils.i("FirebaseManager - 设备信息设置完成")
        } catch (e: Exception) {
            logError("setDeviceInfo", "Failed to set device info: ${e.message}")
        }
    }

    /** 设置用户信息（登录后调用） */
    fun setUserInfo(userId: String, userType: String = "free", subscriptionLevel: String = "none") {
        try {
            // 设置用户ID
            setUserId(userId)

            // 设置用户属性
            setUserProperty(UserProperties.USER_TYPE, userType)
            setUserProperty(UserProperties.SUBSCRIPTION_LEVEL, subscriptionLevel)

            LogUtils.i("FirebaseManager - 用户信息设置完成: userId=$userId, userType=$userType")
        } catch (e: Exception) {
            logError("setUserInfo", "Failed to set user info: ${e.message}")
        }
    }

    /** 记录性能指标 */
    fun logPerformanceMetric(
        metricName: String,
        value: Long,
        unit: String = "ms",
        additionalParams: Map<String, Any> = emptyMap()
    ) {
        try {
            val params =
                mapOf(
                    "metric_name" to metricName,
                    "metric_value" to value,
                    "metric_unit" to unit,
                    "timestamp" to System.currentTimeMillis()
                ) + additionalParams

            logEvent("performance_metric", params)
        } catch (e: Exception) {
            logError("logPerformanceMetric", "Failed to log performance metric: ${e.message}")
        }
    }

    /** 安全的事件参数处理 */
    fun safeEventParam(key: String, value: Any?): Pair<String, String> {
        return key to (value?.toString() ?: "unknown")
    }

    /** 批量安全事件参数处理 */
    fun safeEventParams(vararg params: Pair<String, Any?>): Map<String, String> {
        return params.associate { (key, value) -> safeEventParam(key, value) }
    }

    // region Performance Monitoring 相关方法

    /** 开始一个自定义追踪 */
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

    /** 停止追踪并记录 */
    fun stopTrace(trace: com.google.firebase.perf.metrics.Trace?) {
        try {
            trace?.stop()
        } catch (e: Exception) {
            logError("stopTrace", "Failed to stop trace: ${e.message}")
        }
    }

    /** 为追踪添加自定义属性 */
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

    /** 为追踪添加自定义指标 */
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

    /** 创建网络请求监控 */
    fun createHttpMetric(url: String, method: String): Any? {
        return try {
            val perf = getPerformance() ?: return null
            val httpMetric = perf.newHttpMetric(url, method)
            httpMetric
        } catch (e: Exception) {
            logError("createHttpMetric", "Failed to create HTTP metric: ${e.message}")
            null
        }
    }

    /** 开始网络请求监控 */
    fun startHttpMetric(httpMetric: Any?) {
        try {
            (httpMetric as? com.google.firebase.perf.metrics.HttpMetric)?.start()
        } catch (e: Exception) {
            logError("startHttpMetric", "Failed to start HTTP metric: ${e.message}")
        }
    }

    /** 停止网络请求监控 */
    fun stopHttpMetric(httpMetric: Any?, responseCode: Int, responseSize: Long? = null) {
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

    /** 便捷方法：执行带性能监控的操作 */
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

    // endregion

    /** 清理资源 在应用退出时调用，避免内存泄漏 */
    fun cleanup() {
        try {
            // 取消所有协程
            firebaseScope.coroutineContext.cancel()

            // 清理缓存
            analytics = null
            crashlytics = null
            performance = null

            // 重置状态
            isInitialized.set(false)

            // 清理统计信息
            errorCounts.clear()
            lastEventTimes.clear()

            LogUtils.i("FirebaseManager - 资源清理完成")
        } catch (e: Exception) {
            LogUtils.e("FirebaseManager - 资源清理失败: ${e.message}")
        }
    }

    // 私有辅助方法
    private fun shouldLogEvent(eventName: String): Boolean {
        if (!isInitialized.get()) {
            if (AppUtils.isAppDebug()) {
                LogUtils.w("FirebaseManager", "FirebaseManager未初始化，拒绝事件: $eventName")
            }
            return false
        }

        if (!config.analyticsEnabled) {
            if (AppUtils.isAppDebug()) {
                LogUtils.w("FirebaseManager", "Analytics已禁用，拒绝事件: $eventName")
            }
            return false
        }

        // 检查是否被禁用
        if (eventName in config.disabledEvents) {
            if (AppUtils.isAppDebug()) {
                LogUtils.d("FirebaseManager", "事件被禁用: $eventName")
            }
            return false
        }

        // 检查限频（优先检查，避免频繁计算）
        val minInterval = config.minIntervalMsPerEvent[eventName] ?: 0L
        if (minInterval > 0) {
            val lastTime = lastEventTimes[eventName] ?: 0L
            val currentTime = System.currentTimeMillis()
            if (currentTime - lastTime < minInterval) {
                if (AppUtils.isAppDebug()) {
                    LogUtils.d(
                        "FirebaseManager",
                        "事件被限频: $eventName (间隔: ${currentTime - lastTime}ms < ${minInterval}ms)"
                    )
                }
                return false
            }
            lastEventTimes[eventName] = currentTime
        }

        // 检查采样率
        val samplingRate = config.samplingRates[eventName] ?: 1.0
        if (samplingRate < 1.0) {
            val random = Math.random()
            if (random > samplingRate) {
                if (AppUtils.isAppDebug()) {
                    LogUtils.d(
                        "FirebaseManager",
                        "事件被采样过滤: $eventName (随机值: $random > 采样率: $samplingRate)"
                    )
                }
                return false
            }
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
