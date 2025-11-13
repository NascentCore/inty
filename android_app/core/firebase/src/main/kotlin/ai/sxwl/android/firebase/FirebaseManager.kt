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
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicBoolean
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await

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
                    Events.PAGE_VISIBLE, // 页面可见性变化过于频繁
                    Events.PAGE_HIDDEN, // 页面隐藏事件价值较低
                    Events.PAGE_LIFECYCLE, // 生命周期事件过于详细
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
                    Events.USER_LOGOUT to 1.0, // 用户登出
                    Events.CHAT_STARTED to 1.0, // 聊天开始（第一次发送消息时触发）
                    Events.MESSAGE_SENT to 1.0, // 消息发送
                    Events.AGENT_SWITCH to 1.0, // Agent切换
                    Events.SUBSCRIPTION_SUCCESS to 1.0, // 订阅验证成功
                    Events.SUBSCRIPTION_FAILURE to 1.0, // 订阅验证失败
                    Events.FREE_LIMIT_REACHED to 1.0, // 达到免费限制
                    Events.SUBSCRIPTION_PRICE_VIEW to 1.0, // 订阅价格查看（100%采样）
                    Events.EXPLORE_AGENTS_FETCH_SUCCESS to 1.0, // Explore接口请求成功（100%采样）
                    Events.EXPLORE_AGENTS_FETCH_ERROR to 1.0, // Explore接口请求错误（100%采样）

                    // 🔴 错误和失败事件 - 100%采样
                    Events.AUTH_FAILURE to 1.0, // 认证失败
                    Events.APP_ERROR to 1.0, // 应用错误
                    Events.MESSAGE_SEND_FAILURE to 1.0, // 消息发送错误（合并 failure 和 exception）
                    Events.REQUEST_FAILURE to 1.0, // 请求失败（网络请求失败时触发）
                    Events.VERY_SLOW_REQUEST to 1.0, // 极慢请求

                    // 🔴 页面追踪事件 - 100%采样
                    Events.DURATION to 1.0, // 页面停留时长
                    Events.MESSAGE_SEND_SUCCESS to 1.0, // 消息发送成功

                    // 🔴 用户交互事件 - 100%采样
                    Events.CHAT_PAGE_CLICK to 1.0, // 聊天页面点击
                    Events.CHAT_SIDEBAR_CLICK to 1.0, // 聊天侧边栏点击
                    Events.CHAT_MORE_CLICK to 1.0, // 聊天更多面板点击

                    // 🔴 图片生成相关事件 - 100%采样
                    Events.MESSAGE_TO_IMAGE_GENERATION_BUTTON_CLICKED to 1.0, // 图片生成开始
                    Events.MESSAGE_TO_IMAGE_GENERATION_SUCCESS to 1.0, // 图片生成成功
                    Events.MESSAGE_TO_IMAGE_GENERATION_FAILURE to 1.0, // 图片生成失败
                    Events.IMAGE_GENERATION_LIMIT_REACHED to 1.0, // 图片生成限制达到

                    // 🟡 性能相关事件 - 保持现有采样配置
                    Events.SLOW_REQUEST to if (AppUtils.isAppDebug()) 1.0 else 0.3, // 调试100%，发布30%

                    // 🟡 性能指标事件 - 保持原有采样配置
                    Events.AI_RESPONSE_TIME to
                        if (AppUtils.isAppDebug()) 1.0 else 0.3, // 调试100%，发布30%
                    Events.EXPLORE_RESPONSE_TIME to
                        if (AppUtils.isAppDebug()) 1.0 else 0.3, // 调试100%，发布30%
                    Events.TTS_GENERATION_TIME to
                        if (AppUtils.isAppDebug()) 1.0 else 0.3, // 调试100%，发布30%
                    Events.IMAGE_LOAD_TIME to
                        if (AppUtils.isAppDebug()) 1.0 else 0.2, // 调试100%，发布20%
                    Events.IMAGE_GENERATION_TIME to
                        if (AppUtils.isAppDebug()) 1.0 else 0.3, // 调试100%，发布30%
                    Events.PAGE_LOAD_TIME to
                        if (AppUtils.isAppDebug()) 1.0 else 0.3, // 调试100%，发布30%
                    Events.DATABASE_OPERATION_TIME to
                        if (AppUtils.isAppDebug()) 1.0 else 0.2, // 调试100%，发布20%
                ),
            minIntervalMsPerEvent =
                mapOf(
                    // 🔴 业务数据点 - 无限制或很宽松的限频
                    Events.MESSAGE_SENT to
                        if (AppUtils.isAppDebug()) 500L else 1_000L, // 调试0.5秒，发布1秒
                    Events.MESSAGE_SEND_FAILURE to
                        if (AppUtils.isAppDebug()) 500L else 1_000L, // 调试0.5秒，发布1秒
                    Events.CHAT_PAGE_CLICK to
                        if (AppUtils.isAppDebug()) 500L else 1_000L, // 调试0.5秒，发布1秒

                    // 🟡 性能相关事件 - 保持现有限频配置
                    Events.SLOW_REQUEST to
                        if (AppUtils.isAppDebug()) 2_000L else 5_000L, // 调试2秒，发布5秒
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
            LogUtils.d("FirebaseManager", "尝试记录事件: $eventName, 参数数量: ${parameters.size}")
            LogUtils.d("FirebaseManager", "参数详情: $parameters")
        }

        if (!shouldLogEvent(eventName)) {
            if (AppUtils.isAppDebug()) {
                LogUtils.d("FirebaseManager", "事件被过滤: $eventName")
            } else {
                // 关键事件即使非调试模式也输出警告，便于排查问题
                if (
                    eventName in
                        listOf(
                            Events.MESSAGE_TO_IMAGE_GENERATION_FAILURE,
                            Events.MESSAGE_SEND_FAILURE,
                        )
                ) {
                    LogUtils.w("FirebaseManager", "事件被过滤: $eventName（非调试模式）")
                }
            }
            return
        }

        // 验证参数数量
        if (parameters.size > MAX_PARAMS_PER_EVENT) {
            logError(
                "logEvent",
                "事件 '$eventName' 参数数量超过限制: ${parameters.size} > $MAX_PARAMS_PER_EVENT",
            )
        }

        try {
            val analytics = getAnalytics() ?: return

            // 使用firebaseScope确保异常隔离
            firebaseScope.launch {
                try {
                    val bundle = createBundle(parameters)

                    // 调试模式下输出 Bundle 信息
                    if (AppUtils.isAppDebug()) {
                        val bundleSize = bundle.size()
                        LogUtils.d(
                            "FirebaseManager",
                            "Bundle 创建成功: 事件=$eventName, 参数数量=${bundle.size()}, Bundle大小=$bundleSize",
                        )
                        // 输出每个参数的键值对，便于调试
                        bundle.keySet().forEach { key ->
                            val value = bundle.get(key)
                            LogUtils.d(
                                "FirebaseManager",
                                "  参数: $key = $value (类型: ${value?.javaClass?.simpleName})",
                            )
                        }
                    }
                    analytics.logEvent(eventName, bundle)

                    // 调试模式下确认事件已发送
                    if (AppUtils.isAppDebug()) {
                        LogUtils.d(
                            "FirebaseManager",
                            "✅ 事件已发送: $eventName (${parameters.size} 个参数)",
                        )
                    } else {
                        // 关键事件即使非调试模式也输出确认日志，便于排查问题
                        if (
                            eventName in
                                listOf(
                                    Events.MESSAGE_TO_IMAGE_GENERATION_FAILURE,
                                    Events.MESSAGE_SEND_FAILURE,
                                )
                        ) {
                            LogUtils.i(
                                "FirebaseManager",
                                "✅ 事件已发送: $eventName (${parameters.size} 个参数)",
                            )
                        }
                    }
                } catch (e: Exception) {
                    logError("logEvent", "Failed to log event '$eventName': ${e.message}")
                }
            }
        } catch (e: Exception) {
            logError("logEvent", "Failed to create event '$eventName': ${e.message}")
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
        const val USER_LOGOUT = "user_logout"
        const val MESSAGE_SENT = "message_sent"
        const val MESSAGE_SEND_SUCCESS = "message_send_success"
        const val MESSAGE_SEND_FAILURE = "message_send_failure" // 消息发送错误（合并 failure 和 exception）

        // 性能相关事件
        const val AI_RESPONSE_TIME = "ai_response_time"
        const val TTS_GENERATION_TIME = "tts_generation_time"
        const val VOICE_PLAYBACK_TIME = "voice_playback_time"
        const val IMAGE_LOAD_TIME = "image_load_time"
        const val IMAGE_GENERATION_TIME = "image_generation_time" // 图片生成耗时
        const val PAGE_LOAD_TIME = "page_load_time"
        const val DATABASE_OPERATION_TIME = "database_operation_time"

        // 业务关键事件
        const val CHAT_STARTED = "chat_started" // 聊天开始（第一次发送消息时触发）
        const val AGENT_SWITCH = "agent_switch"

        // 订阅相关事件
        const val SUBSCRIPTION_SUCCESS = "subscription_success" // 订阅验证成功
        const val SUBSCRIPTION_FAILURE = "subscription_failure" // 订阅验证失败
        const val SUBSCRIPTION_PRICE_VIEW = "subscription_price_view" // 订阅价格查看
        const val FREE_LIMIT_REACHED = "free_limit_reached"

        // 用户交互事件
        const val CHAT_PAGE_CLICK = "chat_page_click" // 聊天页面点击
        const val CHAT_SIDEBAR_CLICK = "chat_sidebar_click" // 聊天侧边栏点击
        const val CHAT_MORE_CLICK = "chat_more_click" // 聊天更多面板点击

        // 图片生成相关事件
        const val MESSAGE_TO_IMAGE_GENERATION_BUTTON_CLICKED =
            "message_to_image_generation_button_clicked"
        const val MESSAGE_TO_IMAGE_GENERATION_SUCCESS = "message_to_image_generation_success"
        // 图片生成失败，除生成数量上线超标以外的错误
        const val MESSAGE_TO_IMAGE_GENERATION_FAILURE = "message_to_image_generation_failure"
        // 图片生成限制达到，这个限制与其他生图操作（如创建角色时生图）累加到一起的
        const val IMAGE_GENERATION_LIMIT_REACHED = "image_generation_limit_reached"

        // Explore相关事件
        const val EXPLORE_AGENTS_FETCH_SUCCESS = "explore_agents_fetch_success" // Explore接口请求成功
        const val EXPLORE_AGENTS_FETCH_ERROR =
            "explore_agents_fetch_error" // Explore接口请求错误（合并 failure 和 exception）

        // Explore性能指标
        const val EXPLORE_RESPONSE_TIME = "explore_response_time" // Explore接口响应时间

        // 认证相关事件
        const val AUTH_FAILURE = "auth_failure" // HTTP 401认证失败（在 error_message 中注明白名单接口）

        // 错误相关事件
        const val APP_ERROR = "app_error" // 应用错误
        const val REQUEST_FAILURE = "request_failure" // 请求失败（网络请求失败时触发）

        // 性能相关事件
        const val SLOW_REQUEST = "slow_request" // 慢请求（>3秒）
        const val VERY_SLOW_REQUEST = "very_slow_request" // 极慢请求（>10秒）

        // 页面追踪相关事件
        const val DURATION = "duration" // 页面停留时长
        const val PAGE_VISIBLE = "page_visible" // 页面变为可见（已禁用）
        const val PAGE_HIDDEN = "page_hidden" // 页面变为不可见（已禁用）
        const val PAGE_LIFECYCLE = "page_lifecycle" // 页面生命周期事件（已禁用）
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
        additionalParams: Map<String, Any> = emptyMap(),
    ) {
        try {
            val params =
                mapOf(
                    "metric_value" to value,
                    "metric_unit" to unit,
                    "timestamp" to System.currentTimeMillis(),
                ) + additionalParams

            // 使用指定的事件名称记录性能指标
            logEvent(metricName, params)
        } catch (e: Exception) {
            logError("logPerformanceMetric", "Failed to log performance metric: ${e.message}")
        }
    }

    // Firebase Analytics 参数限制常量（根据 Firebase 官方文档）
    // 参考: https://firebase.google.com/docs/analytics/events
    private const val MAX_PARAM_NAME_LENGTH = 40 // Firebase 官方限制：参数名最多 40 个字符
    private const val MAX_PARAM_VALUE_LENGTH = 100 // Firebase 官方限制：参数值最多 100 个字符
    private const val MAX_PARAMS_PER_EVENT = 25 // Firebase 官方限制：每个事件最多 25 个参数

    /** 验证参数名是否符合 Firebase 规范 */
    private fun isValidParameterName(name: String): Boolean {
        // Firebase 参数名规则：
        // 1. 必须以字母开头
        // 2. 只能包含字母、数字、下划线
        // 3. 长度限制：最多 40 个字符
        val pattern = "^[a-zA-Z][a-zA-Z0-9_]{0,${MAX_PARAM_NAME_LENGTH - 1}}$".toRegex()
        return pattern.matches(name)
    }

    /** 验证并规范化参数名 */
    private fun sanitizeParameterName(name: String): String {
        // 如果参数名不符合规范，尝试规范化
        if (isValidParameterName(name)) {
            return name
        }

        // 规范化：移除特殊字符，确保以字母开头
        var sanitized =
            name
                .replace(Regex("[^a-zA-Z0-9_]"), "_") // 将特殊字符替换为下划线
                .take(MAX_PARAM_NAME_LENGTH) // 限制长度

        // 如果规范化后以数字开头，添加前缀
        if (sanitized.isNotEmpty() && sanitized[0].isDigit()) {
            sanitized = "param_$sanitized"
            sanitized = sanitized.take(MAX_PARAM_NAME_LENGTH)
        }

        // 如果仍然不符合规范，返回默认值
        return if (isValidParameterName(sanitized)) {
            sanitized
        } else {
            "invalid_param"
        }
    }

    /** 验证并规范化参数值 */
    private fun sanitizeParamValue(value: String): String {
        // Firebase 官方限制：字符串参数值最多 100 个字符
        // 对于超长值（如 URL），截断并添加省略号
        // 注意：如果参数值对业务很重要，建议在发送前进行哈希或拆分处理
        return if (value.length > MAX_PARAM_VALUE_LENGTH) {
            // 超长时截断并添加省略号
            value.take(MAX_PARAM_VALUE_LENGTH - 3) + "..."
        } else {
            value
        }
    }

    /** 安全的事件参数处理 - 添加验证和规范化 */
    fun safeEventParam(key: String, value: Any?): Pair<String, String> {
        // 验证并规范化参数名
        val sanitizedKey = sanitizeParameterName(key)

        // 转换参数值
        val stringValue =
            when (value) {
                null -> "unknown"
                is String -> sanitizeParamValue(value)
                else -> sanitizeParamValue(value.toString())
            }

        // 如果参数名被规范化，记录警告（仅在调试模式）
        if (sanitizedKey != key && AppUtils.isAppDebug()) {
            LogUtils.w("FirebaseManager", "参数名被规范化: '$key' -> '$sanitizedKey'")
        }

        // 如果参数值被截断，记录警告（仅在调试模式）
        if (value is String && stringValue.length < value.length && AppUtils.isAppDebug()) {
            LogUtils.w(
                "FirebaseManager",
                "参数值被截断: '$key' 原长度=${value.length}, 截断后=${stringValue.length}",
            )
        }

        return sanitizedKey to stringValue
    }

    /** 批量安全事件参数处理 - 添加参数数量验证 */
    fun safeEventParams(vararg params: Pair<String, Any?>): Map<String, String> {
        // 验证参数数量
        if (params.size > MAX_PARAMS_PER_EVENT) {
            logError(
                "safeEventParams",
                "参数数量超过限制: ${params.size} > $MAX_PARAMS_PER_EVENT，将只保留前 $MAX_PARAMS_PER_EVENT 个参数",
            )
        }

        return params
            .take(MAX_PARAMS_PER_EVENT) // 限制参数数量
            .associate { (key, value) -> safeEventParam(key, value) }
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
        value: String,
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
        value: Long,
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
        operation: (com.google.firebase.perf.metrics.Trace?) -> T,
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
                        "事件被限频: $eventName (间隔: ${currentTime - lastTime}ms < ${minInterval}ms)",
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
                        "事件被采样过滤: $eventName (随机值: $random > 采样率: $samplingRate)",
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
        // 验证参数数量
        if (parameters.size > MAX_PARAMS_PER_EVENT) {
            logError("putParamsToBundle", "参数数量超过限制: ${parameters.size} > $MAX_PARAMS_PER_EVENT")
        }

        var paramCount = 0
        parameters.forEach { (key, value) ->
            // 限制参数数量
            if (paramCount >= MAX_PARAMS_PER_EVENT) {
                if (AppUtils.isAppDebug()) {
                    LogUtils.w("FirebaseManager", "参数数量已达上限 ($MAX_PARAMS_PER_EVENT)，跳过参数: $key")
                }
                return@forEach
            }

            try {
                // 验证并规范化参数名
                val finalKey =
                    if (isValidParameterName(key)) {
                        key
                    } else {
                        val sanitizedKey = sanitizeParameterName(key)
                        if (AppUtils.isAppDebug()) {
                            LogUtils.w("FirebaseManager", "参数名不符合规范: '$key'，已规范化: '$sanitizedKey'")
                        }
                        sanitizedKey
                    }

                when (value) {
                    is String -> {
                        val sanitizedValue = sanitizeParamValue(value)
                        bundle.putString(finalKey, sanitizedValue)
                        if (sanitizedValue.length < value.length && AppUtils.isAppDebug()) {
                            LogUtils.d(
                                "FirebaseManager",
                                "参数值被截断: $finalKey (${value.length} -> ${sanitizedValue.length})",
                            )
                        }
                    }

                    is Long -> bundle.putLong(finalKey, value)
                    is Int -> bundle.putLong(finalKey, value.toLong())
                    is Double -> bundle.putDouble(finalKey, value)
                    is Boolean -> {
                        val boolValue = value.toString()
                        bundle.putString(finalKey, boolValue)
                    }

                    is Float -> bundle.putDouble(finalKey, value.toDouble())
                    else -> {
                        // 其他类型转换为字符串并验证长度
                        val stringValue = value.toString()
                        val sanitizedValue = sanitizeParamValue(stringValue)
                        bundle.putString(finalKey, sanitizedValue)
                    }
                }
                paramCount++
            } catch (e: Exception) {
                logError("putParamsToBundle", "处理参数失败: $key = $value, 错误: ${e.message}")
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
