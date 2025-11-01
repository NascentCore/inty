package ai.sxwl.android.data.http

import ai.sxwl.android.data.http.config.NetworkConfig
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.utils.AppUtils
import ai.sxwl.android.utils.DeviceUtils
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.Utils
import com.chuckerteam.chucker.api.ChuckerInterceptor
import okhttp3.ConnectionPool
import okhttp3.Dns
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import java.net.InetAddress
import java.util.UUID
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

/**
 * 统一的 OkHttpClient 工厂
 * 提供统一的网络客户端配置，包含所有必要的拦截器和配置
 */
object UnifiedOkHttpClient {

    // 性能监控专用线程池
    internal val performanceExecutor =
        Executors.newFixedThreadPool(2) { r ->
            Thread(r, "PerformanceMonitor").apply { isDaemon = true }
        }

    /**
     * 创建统一的 OkHttpClient 实例
     * 包含所有必要的拦截器：设备信息、认证、性能监控、调试等
     */
    fun create(): OkHttpClient {
        val environmentConfig = NetworkConfig.getCurrentEnvironmentConfig()

        return OkHttpClient.Builder()
            // 超时配置（根据环境配置）
            .connectTimeout(
                environmentConfig.timeout.connectTimeoutMs,
                TimeUnit.MILLISECONDS
            )
            .writeTimeout(
                environmentConfig.timeout.writeTimeoutMs,
                TimeUnit.MILLISECONDS
            )
            .readTimeout(
                environmentConfig.timeout.readTimeoutMs,
                TimeUnit.MILLISECONDS
            )
            // 连接池配置
            .connectionPool(
                ConnectionPool(
                    environmentConfig.connection.maxConnections,
                    environmentConfig.connection.keepAliveDurationMs,
                    TimeUnit.MILLISECONDS
                )
            )
            // DNS缓存（如果启用）
            .dns(if (environmentConfig.connection.enableDnsCache) CachedDns() else Dns.SYSTEM)
            // 拦截器（注意顺序：性能监控 -> 设备信息 -> 认证 -> 调试）
            .addInterceptor(PerformanceInterceptor())
            .addInterceptor(DeviceInfoInterceptor())
            .addInterceptor(AuthInterceptor())
            .apply {
                // Chucker 调试工具（根据配置）
                if (environmentConfig.logging.enableChuckerLogging) {
                    addInterceptor(ChuckerInterceptor(Utils.getApp()))
                }
            }
            .build()
    }
}

/**
 * 设备信息拦截器
 * 添加应用版本、设备信息、请求ID、时间戳等 header，便于后端数据分析和请求统计
 */
private class DeviceInfoInterceptor : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        val builder = request.newBuilder()

        // 应用版本信息（使用后端约定的驼峰命名风格）
        // 后端通过 FastAPI Header alias 约定使用驼峰命名：appVersionCode, appVersionName
        builder.addHeader("appVersionCode", AppUtils.getVersionCode().toString())
        builder.addHeader("appVersionName", AppUtils.getVersionName())

        // 设备信息（使用后端约定的驼峰命名风格）
        builder.addHeader("deviceModel", DeviceUtils.getModel())
        builder.addHeader("deviceManufacturer", DeviceUtils.getManufacturer())
        builder.addHeader("deviceBrand", DeviceUtils.getBrand())
        builder.addHeader("osVersion", DeviceUtils.getSDKVersionName())
        builder.addHeader("osVersionCode", DeviceUtils.getSDKVersionCode().toString())

        // 请求唯一标识（使用后端一致的小写连字符，x- 前缀）
        // 后端 TODO 中提到 x-request-id，使用小写连字符风格
        val requestId = UUID.randomUUID().toString()
        builder.addHeader("x-request-id", requestId)

        // 时间戳（使用后端一致的小写连字符，x- 前缀）
        val timestamp = System.currentTimeMillis()
        builder.addHeader("x-request-timestamp", timestamp.toString())

        // 设备唯一标识（使用后端一致的小写连字符，x- 前缀）
        val deviceId = DeviceUtils.getUniqueDeviceId()
        if (deviceId.isNotEmpty()) {
            builder.addHeader("x-device-id", deviceId)
        }

        // Accept header
        builder.addHeader("accept", "application/json")

        return chain.proceed(builder.build())
    }
}

/**
 * 认证拦截器
 * 添加认证 token 并处理 401 响应
 */
private class AuthInterceptor : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        LogUtils.i("AuthInterceptor - getCurToken: ${IntySetting.getCurToken()}")

        val request = chain.request()
        val builder = request.newBuilder()

        // 添加认证 token（如果存在）
        val token = IntySetting.getCurToken()
        if (token.isNotEmpty()) {
            builder.addHeader("Authorization", "Bearer $token")
        }

        val modifiedRequest = builder.build()
        LogUtils.i("request = $modifiedRequest")

        val response = chain.proceed(modifiedRequest)

        // 处理 401 未授权响应
        when (response.code) {
            401 -> {
                LogUtils.e("http 401 for ${modifiedRequest.url}")

                // Firebase Analytics - 记录认证失败
                FirebaseManager.logEvent(
                    "auth_failure",
                    mapOf(
                        "http_code" to 401,
                        "url" to modifiedRequest.url.toString(),
                        "user_logged_out" to IntySetting.isLoggingOut(),
                    ),
                )

                // Firebase Crashlytics - 记录认证失败
                FirebaseManager.setCustomKey("last_401_url", modifiedRequest.url.toString())
                FirebaseManager.recordException(
                    Exception("HTTP 401 Unauthorized: ${modifiedRequest.url}")
                )

                // 追踪认证失败
                trackError(
                    "HTTP 401 Unauthorized",
                    "auth_failure",
                    mapOf(
                        "url" to modifiedRequest.url.toString(),
                        "user_logged_out" to IntySetting.isLoggingOut(),
                    ),
                )

                // 检查是否正在退出登录过程中，避免重复重启
                if (IntySetting.isLoggingOut()) {
                    LogUtils.i("Ignoring 401 during logout process")
                } else {
                    LogUtils.e("401 unauthorized - switching to guest mode")
                    IntySetting.logout()
                    AppUtils.relaunchApp(true)
                }
            }
        }

        return response
    }
}

/**
 * 记录错误和异常
 */
private fun trackError(
    error: String,
    errorType: String = "unknown",
    additionalParams: Map<String, Any> = emptyMap(),
) {
    try {
        FirebaseManager.logEvent(
            "app_error",
            mapOf(
                "error" to error,
                "error_type" to errorType,
                "timestamp" to System.currentTimeMillis(),
            ) + additionalParams,
        )
    } catch (e: Exception) {
        LogUtils.e("Failed to track error: ${e.message}")
    }
}

/**
 * 网络性能监控拦截器
 * 使用 Firebase Performance 监控请求性能
 */
private class PerformanceInterceptor : Interceptor {

    private companion object {
        const val FAST_REQUEST_THRESHOLD = 1000L
        const val SLOW_REQUEST_THRESHOLD = 3000L
    }

    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        val startTime = System.currentTimeMillis()

        // 使用 Firebase Performance 创建 HTTP 监控
        val httpMetric: Any? =
            FirebaseManager.createHttpMetric(request.url.toString(), request.method)
        FirebaseManager.startHttpMetric(httpMetric)

        // 记录请求开始（仅在调试模式下）
        if (AppUtils.isAppDebug()) {
            LogUtils.i("🌐 Starting request: ${request.method} ${request.url}")
        }

        return try {
            // 执行实际请求
            val response = chain.proceed(request)
            val endTime = System.currentTimeMillis()
            val duration = endTime - startTime

            // 使用 Firebase Performance 停止监控
            FirebaseManager.stopHttpMetric(httpMetric, response.code)

            // 记录性能指标（不影响请求结果）
            recordPerformanceMetrics(request, duration, response.isSuccessful)

            response
        } catch (e: Exception) {
            val endTime = System.currentTimeMillis()
            val duration = endTime - startTime

            // 使用 Firebase Performance 停止监控（即使请求失败）
            FirebaseManager.stopHttpMetric(httpMetric, -1)

            // 记录失败的性能指标
            recordFailureMetrics(request, duration, e)

            // 重新抛出异常，让其他拦截器或业务逻辑处理
            throw e
        }
    }

    /** 记录性能指标（异步执行，不阻塞请求） */
    private fun recordPerformanceMetrics(
        request: Request,
        duration: Long,
        isSuccessful: Boolean
    ) {
        try {
            // 使用线程池异步记录性能指标，避免阻塞主线程
            UnifiedOkHttpClient.performanceExecutor.execute {
                when {
                    duration < FAST_REQUEST_THRESHOLD -> {
                        if (AppUtils.isAppDebug()) {
                            LogUtils.i(
                                "✅ Fast request: ${request.method} ${request.url} (${duration}ms)"
                            )
                        }
                    }

                    duration < SLOW_REQUEST_THRESHOLD -> {
                        LogUtils.w(
                            "⚠️ Slow request: ${request.method} ${request.url} (${duration}ms)"
                        )

                        // 使用 Firebase Analytics 记录慢请求
                        FirebaseManager.logEvent(
                            "slow_request",
                            mapOf(
                                "duration_ms" to duration,
                                "method" to request.method,
                                "url" to request.url.toString(),
                                "successful" to isSuccessful
                            )
                        )
                    }

                    else -> {
                        LogUtils.e(
                            "🚨 Very slow request: ${request.method} ${request.url} (${duration}ms)"
                        )

                        // 使用 Firebase Analytics 记录极慢请求
                        FirebaseManager.logEvent(
                            "very_slow_request",
                            mapOf(
                                "duration_ms" to duration,
                                "method" to request.method,
                                "url" to request.url.toString(),
                                "successful" to isSuccessful
                            )
                        )

                        // 使用 Firebase Crashlytics 记录性能问题
                        FirebaseManager.setCustomKey("slow_request_url", request.url.toString())
                        FirebaseManager.setCustomKey(
                            "slow_request_duration",
                            duration.toString()
                        )
                    }
                }
            }
        } catch (e: Exception) {
            // 性能记录失败不应该影响业务请求
            LogUtils.w("Failed to record performance metrics: ${e.message}")
        }
    }

    /** 记录失败的性能指标 */
    private fun recordFailureMetrics(request: Request, duration: Long, exception: Exception) {
        try {
            // 使用线程池异步记录失败指标
            UnifiedOkHttpClient.performanceExecutor.execute {
                LogUtils.e(
                    "❌ Request failed: ${request.method} ${request.url} (${duration}ms): ${exception.message}"
                )

                // 使用 Firebase Analytics 记录请求失败
                FirebaseManager.logEvent(
                    "request_failure",
                    mapOf(
                        "duration_ms" to duration,
                        "method" to request.method,
                        "url" to request.url.toString(),
                        "error_type" to exception.javaClass.simpleName,
                        "error_message" to (exception.message ?: "unknown")
                    )
                )

                // 使用 Firebase Crashlytics 记录网络错误
                FirebaseManager.setCustomKey("failed_request_url", request.url.toString())
                FirebaseManager.setCustomKey(
                    "failed_request_duration",
                    duration.toString()
                )
                FirebaseManager.recordException(exception)
            }
        } catch (e: Exception) {
            // 性能记录失败不应该影响业务请求
            LogUtils.w("Failed to record failure metrics: ${e.message}")
        }
    }
}

/**
 * 自定义 DNS 解析器，支持缓存
 */
private class CachedDns : Dns {
    // 使用线程安全的 ConcurrentHashMap
    private val cache = ConcurrentHashMap<String, List<InetAddress>>()

    // 缓存过期时间（5分钟）
    private val cacheExpiry = ConcurrentHashMap<String, Long>()
    private val CACHE_DURATION = 5 * 60 * 1000L // 5分钟

    override fun lookup(hostname: String): List<InetAddress> {
        val now = System.currentTimeMillis()
        val expiry = cacheExpiry[hostname] ?: 0L

        // 检查缓存是否过期
        if (now > expiry) {
            cache.remove(hostname)
            cacheExpiry.remove(hostname)
        }

        return cache.getOrPut(hostname) {
            val result = Dns.SYSTEM.lookup(hostname)
            cacheExpiry[hostname] = now + CACHE_DURATION
            result
        }
    }
}
