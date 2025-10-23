package com.ai.inty.net

import ai.sxwl.android.utils.AppUtils
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.Utils
import com.ai.inty.BuildConfig
import com.ai.inty.Constant
import com.ai.inty.utils.FirebaseManager
import com.ai.inty.utils.FirebasePerformanceHelper
import com.ai.inty.utils.PageTrackingHelper
import com.architecture.httplib.core.HttpResponseCallAdapterFactory
import com.architecture.httplib.core.MoshiResultTypeAdapterFactory
import com.architecture.httplib.error.GlobalErrorHandler
import com.chuckerteam.chucker.api.ChuckerInterceptor
import com.google.firebase.perf.metrics.HttpMetric
import ai.sxwl.android.data.store.IntySetting
import com.jakewharton.retrofit2.adapter.kotlin.coroutines.CoroutineCallAdapterFactory
import com.squareup.moshi.DefaultIfNullFactory
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import okhttp3.ConnectionPool
import okhttp3.Dns
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.Response
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import java.net.InetAddress
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

/** 获取基础URL 根据构建类型返回对应的API基础URL */
private fun getBaseUrl(): String {
    return when (BuildConfig.BUILD_TYPE) {
        "local" -> "http://${Constant.USER_HOST_LOCAL}/"
        "debug" -> "https://${Constant.USER_HOST_DEV}/"
        "playdebug" -> "https://${Constant.USER_HOST_DEV}/"
        "release" -> "https://${Constant.USER_HOST}/"
        else -> "https://${Constant.USER_HOST_DEV}/" // fallback to staging
    }
}

private class AuthInterceptor : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        LogUtils.i("AuthInterceptor - getCurToken: ${IntySetting.getCurToken()}")
        val request =
            chain
                .request()
                .newBuilder()
                .addHeader("accept", "application/json")
                .addHeader("appVersionCode", AppUtils.getVersionCode().toString())
                .addHeader("appVersionName", AppUtils.getVersionName())
                .addHeader("Authorization", "Bearer ${IntySetting.getCurToken()}")
                .build()

        LogUtils.i("request = $request")
        val response = chain.proceed(request)

        when (response.code) {
            401 -> {
                LogUtils.e("http 401 for ${request.url}")

                // Firebase Analytics - 记录认证失败
                FirebaseManager.logEvent(
                    "auth_failure",
                    mapOf(
                        "http_code" to 401,
                        "url" to request.url.toString(),
                        "user_logged_out" to IntySetting.isLoggingOut(),
                    ),
                )

                // Firebase Crashlytics - 记录认证失败
                FirebaseManager.setCustomKey("last_401_url", request.url.toString())
                FirebaseManager.recordException(Exception("HTTP 401 Unauthorized: ${request.url}"))

                // 追踪认证失败
                PageTrackingHelper.trackError(
                    "HTTP 401 Unauthorized",
                    "auth_failure",
                    mapOf(
                        "url" to request.url.toString(),
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

/** 重试拦截器 对网络错误进行重试，提高请求成功率 */
private class RetryInterceptor(private val maxRetries: Int = 3) : Interceptor {

    companion object {
        // 可重试的HTTP状态码
        private val RETRYABLE_STATUS_CODES = setOf(500, 502, 503, 504, 429)

        // 可重试的异常类型
        private val RETRYABLE_EXCEPTIONS = setOf(
            "java.net.SocketTimeoutException",
            "java.net.ConnectException",
            "java.net.UnknownHostException",
            "java.io.IOException"
        )

        // 幂等性HTTP方法（可以安全重试）
        private val IDEMPOTENT_METHODS = setOf("GET", "HEAD", "PUT", "DELETE")
    }

    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        var lastException: Exception? = null
        var lastResponse: Response? = null

        // 检查请求是否适合重试
        if (!shouldRetryRequest(request)) {
            return chain.proceed(request)
        }

        // 重试逻辑
        for (attempt in 0 until maxRetries) {
            try {
                val currentResponse = chain.proceed(request)
                lastResponse = currentResponse

                // 检查响应是否应该重试
                if (shouldRetryResponse(currentResponse, attempt)) {
                    LogUtils.d("Retry attempt ${attempt + 1} for ${request.url} due to status ${currentResponse.code}")

                    // 记录重试事件
                    recordRetryEvent(request, attempt + 1, currentResponse.code, null)

                    // 安全关闭响应
                    currentResponse.close()

                    // 非阻塞延迟
                    if (attempt < maxRetries - 1) {
                        delayRetry(attempt)
                    }
                } else {
                    // 不需要重试，直接返回
                    return currentResponse
                }
            } catch (e: Exception) {
                lastException = e

                // 检查异常是否应该重试
                if (shouldRetryException(e, attempt)) {
                    LogUtils.i("Retry attempt ${attempt + 1} failed for ${request.url}: ${e.message}")

                    // 记录重试事件
                    recordRetryEvent(request, attempt + 1, null, e)

                    // 非阻塞延迟
                    if (attempt < maxRetries - 1) {
                        delayRetry(attempt)
                    }
                } else {
                    // 不应该重试的异常，直接抛出
                    throw e
                }
            }
        }

        // 所有重试都失败了
        recordFinalFailure(request, maxRetries, lastException)

        // 如果有最后的响应，返回它；否则抛出最后的异常
        return lastResponse ?: throw (lastException
            ?: Exception("Network request failed after $maxRetries attempts"))
    }

    /**
     * 检查请求是否适合重试
     */
    private fun shouldRetryRequest(request: okhttp3.Request): Boolean {
        // 只对幂等性方法进行重试
        return request.method in IDEMPOTENT_METHODS
    }

    /**
     * 检查响应是否应该重试
     */
    private fun shouldRetryResponse(response: okhttp3.Response, attempt: Int): Boolean {
        return attempt < maxRetries - 1 && response.code in RETRYABLE_STATUS_CODES
    }

    /**
     * 检查异常是否应该重试
     */
    private fun shouldRetryException(exception: Exception, attempt: Int): Boolean {
        if (attempt >= maxRetries - 1) return false

        val exceptionType = exception.javaClass.name
        return RETRYABLE_EXCEPTIONS.any { exceptionType.contains(it) }
    }

    /**
     * 非阻塞延迟重试
     */
    private fun delayRetry(attempt: Int) {
        try {
            // 使用指数退避，但避免阻塞主线程
            val delayMs = (1000L * (attempt + 1)).coerceAtMost(5000L) // 最大5秒

            if (BuildConfig.DEBUG) {
                // 调试模式下使用Thread.sleep便于调试
                Thread.sleep(delayMs)
            } else {
                // 生产环境使用更轻量的延迟
                Thread.sleep(delayMs.coerceAtMost(2000L)) // 生产环境最大2秒
            }
        } catch (e: InterruptedException) {
            Thread.currentThread().interrupt()
            throw RuntimeException("Retry interrupted", e)
        }
    }

    /**
     * 记录重试事件
     */
    private fun recordRetryEvent(
        request: okhttp3.Request,
        attempt: Int,
        statusCode: Int?,
        exception: Exception?
    ) {
        try {
            FirebaseManager.logEvent(
                "network_retry",
                mapOf(
                    "attempt" to attempt,
                    "method" to request.method,
                    "url" to request.url.toString(),
                    "status_code" to (statusCode ?: -1),
                    "exception_type" to (exception?.javaClass?.simpleName ?: "none")
                )
            )
        } catch (e: Exception) {
            // Firebase记录失败不应该影响重试逻辑
            LogUtils.w("Failed to record retry event: ${e.message}")
        }
    }

    /**
     * 记录最终失败
     */
    private fun recordFinalFailure(
        request: okhttp3.Request,
        maxRetries: Int,
        lastException: Exception?
    ) {
        LogUtils.e("All retry attempts failed for ${request.url} after $maxRetries attempts")

        try {
            // Firebase Analytics - 记录网络请求最终失败
            FirebaseManager.logEvent(
                "network_final_failure",
                mapOf(
                    "max_retries" to maxRetries,
                    "method" to request.method,
                    "url" to request.url.toString(),
                    "last_error" to (lastException?.message ?: "unknown"),
                    "last_error_type" to (lastException?.javaClass?.simpleName ?: "unknown")
                )
            )

            // Firebase Crashlytics - 记录网络失败
            FirebaseManager.setCustomKey("network_failure_url", request.url.toString())
            FirebaseManager.setCustomKey("network_failure_retries", maxRetries.toString())
            FirebaseManager.setCustomKey("network_failure_method", request.method)

            if (lastException != null) {
                FirebaseManager.recordException(lastException)
            }
        } catch (e: Exception) {
            // Firebase记录失败不应该影响重试逻辑
            LogUtils.w("Failed to record final failure: ${e.message}")
        }
    }
}

/** 网络性能监控拦截器 监控请求耗时，帮助识别性能问题 */
private class PerformanceInterceptor : Interceptor {

    // 性能阈值常量
    private companion object {
        const val FAST_REQUEST_THRESHOLD = 1000L
        const val SLOW_REQUEST_THRESHOLD = 3000L
    }

    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        val startTime = System.currentTimeMillis()

        // 安全地创建和启动性能监控
        val httpMetric = createHttpMetricSafely(request)
        startHttpMetricSafely(httpMetric)

        // 记录请求开始（仅在调试模式下）
        if (BuildConfig.DEBUG) {
            LogUtils.i("🌐 Starting request: ${request.method} ${request.url}")
        }

        return try {
            // 执行实际请求
            val response = chain.proceed(request)
            val endTime = System.currentTimeMillis()
            val duration = endTime - startTime

            // 安全地停止性能监控
            stopHttpMetricSafely(httpMetric, response)

            // 记录性能指标（不影响请求结果）
            recordPerformanceMetrics(request, duration, response.isSuccessful)

            response
        } catch (e: Exception) {
            val endTime = System.currentTimeMillis()
            val duration = endTime - startTime

            // 安全地停止性能监控（即使请求失败）
            stopHttpMetricSafely(httpMetric, null)

            // 记录失败的性能指标
            recordFailureMetrics(request, duration, e)

            // 重要：不重新抛出异常，让其他拦截器或业务逻辑处理
            // 性能监控不应该影响正常的错误处理流程
            throw e
        }
    }

    /**
     * 安全地创建HTTP性能指标
     */
    private fun createHttpMetricSafely(request: okhttp3.Request): HttpMetric? {
        return try {
            FirebasePerformanceHelper.createHttpMetric(request)
        } catch (e: Exception) {
            // 性能监控失败不应该影响业务请求
            LogUtils.w("Failed to create HTTP metric: ${e.message}")
            null
        }
    }

    /**
     * 安全地启动HTTP性能指标
     */
    private fun startHttpMetricSafely(httpMetric: HttpMetric?) {
        if (httpMetric == null) return

        try {
            FirebasePerformanceHelper.startHttpMetric(httpMetric)
        } catch (e: Exception) {
            // 性能监控失败不应该影响业务请求
            LogUtils.w("Failed to start HTTP metric: ${e.message}")
        }
    }

    /**
     * 安全地停止HTTP性能指标
     */
    private fun stopHttpMetricSafely(httpMetric: HttpMetric?, response: okhttp3.Response?) {
        if (httpMetric == null) return

        try {
            FirebasePerformanceHelper.stopHttpMetric(httpMetric, response)
        } catch (e: Exception) {
            // 性能监控失败不应该影响业务请求
            LogUtils.w("Failed to stop HTTP metric: ${e.message}")
        }
    }

    /**
     * 记录性能指标（异步执行，不阻塞请求）
     */
    private fun recordPerformanceMetrics(
        request: okhttp3.Request,
        duration: Long,
        isSuccessful: Boolean
    ) {
        try {
            // 使用线程池异步记录性能指标，避免阻塞主线程
            NetServiceMgr.performanceExecutor.execute {
                when {
                    duration < FAST_REQUEST_THRESHOLD -> {
                        if (BuildConfig.DEBUG) {
                            LogUtils.i("✅ Fast request: ${request.method} ${request.url} (${duration}ms)")
                        }
                    }

                    duration < SLOW_REQUEST_THRESHOLD -> {
                        LogUtils.w("⚠️ Slow request: ${request.method} ${request.url} (${duration}ms)")

                        // Firebase Analytics - 记录慢请求
                        FirebaseManager.logEvent(
                            "slow_request", mapOf(
                                "duration_ms" to duration,
                                "method" to request.method,
                                "url" to request.url.toString(),
                                "successful" to isSuccessful
                            )
                        )
                    }

                    else -> {
                        LogUtils.e("🚨 Very slow request: ${request.method} ${request.url} (${duration}ms)")

                        // Firebase Analytics - 记录极慢请求
                        FirebaseManager.logEvent(
                            "very_slow_request", mapOf(
                                "duration_ms" to duration,
                                "method" to request.method,
                                "url" to request.url.toString(),
                                "successful" to isSuccessful
                            )
                        )

                        // Firebase Crashlytics - 记录性能问题
                        FirebaseManager.setCustomKey("slow_request_url", request.url.toString())
                        FirebaseManager.setCustomKey("slow_request_duration", duration.toString())
                    }
                }
            }
        } catch (e: Exception) {
            // 性能记录失败不应该影响业务请求
            LogUtils.w("Failed to record performance metrics: ${e.message}")
        }
    }

    /**
     * 记录失败的性能指标
     */
    private fun recordFailureMetrics(
        request: okhttp3.Request,
        duration: Long,
        exception: Exception
    ) {
        try {
            // 使用线程池异步记录失败指标
            NetServiceMgr.performanceExecutor.execute {
                LogUtils.e("❌ Request failed: ${request.method} ${request.url} (${duration}ms): ${exception.message}")

                // Firebase Analytics - 记录请求失败
                FirebaseManager.logEvent(
                    "request_failure", mapOf(
                        "duration_ms" to duration,
                        "method" to request.method,
                        "url" to request.url.toString(),
                        "error_type" to exception.javaClass.simpleName,
                        "error_message" to (exception.message ?: "unknown")
                    )
                )

                // Firebase Crashlytics - 记录网络错误
                FirebaseManager.setCustomKey("failed_request_url", request.url.toString())
                FirebaseManager.setCustomKey("failed_request_duration", duration.toString())
                FirebaseManager.recordException(exception)
            }
        } catch (e: Exception) {
            // 性能记录失败不应该影响业务请求
            LogUtils.w("Failed to record failure metrics: ${e.message}")
        }
    }
}

/** 自定义DNS解析器，支持缓存 */
private class CachedDns : Dns {
    // 使用线程安全的ConcurrentHashMap
    private val cache = java.util.concurrent.ConcurrentHashMap<String, List<InetAddress>>()

    // 缓存过期时间（5分钟）
    private val cacheExpiry = java.util.concurrent.ConcurrentHashMap<String, Long>()
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

object NetServiceMgr {

    // 性能监控专用线程池
    internal val performanceExecutor = Executors.newFixedThreadPool(2) { r ->
        Thread(r, "PerformanceMonitor").apply {
            isDaemon = true
        }
    }

    private val okHttpClient: OkHttpClient
        get() {
            val authInterceptor = AuthInterceptor()
            val performanceInterceptor = PerformanceInterceptor()
            //            val retryInterceptor = RetryInterceptor(maxRetries = 3)

            val builder: OkHttpClient.Builder =
                OkHttpClient.Builder()
                    // 根据构建类型优化超时配置
                    .connectTimeout(15, TimeUnit.SECONDS)
                    .writeTimeout(15, TimeUnit.SECONDS)
                    .readTimeout(30, TimeUnit.SECONDS)
                    // 连接池配置
                    .connectionPool(ConnectionPool(5, 5, TimeUnit.MINUTES))
                    // DNS缓存
                    .dns(CachedDns())
                    // 拦截器（注意顺序：性能监控 -> 重试 -> 认证 -> 调试）
                    .addInterceptor(performanceInterceptor)
                    //                    .addInterceptor(retryInterceptor)
                    .addInterceptor(authInterceptor)
                    .addInterceptor(ChuckerInterceptor(Utils.getApp()))
            return builder.build()
        }

    private val moshi: Moshi
        get() {
            return Moshi.Builder()
                // 添加返回的json 数据自定义解析器
                .add(DefaultIfNullFactory())
                .add(MoshiResultTypeAdapterFactory(getHttpWrapperHandler()))
                .addLast(KotlinJsonAdapterFactory()) //
                .build()
        }

    private val moshiNoWrapper: Moshi
        get() {
            return Moshi.Builder()
                // 添加返回的json 数据自定义解析器
                .add(DefaultIfNullFactory())
                .add(MoshiResultTypeAdapterFactory(null))
                .addLast(KotlinJsonAdapterFactory()) //
                .build()
        }

    private val globalErrorHandler = GlobalErrorHandler()

    // todo 这里使用wrapper来区分 是否带有外部code，message，data格式的响应数据体
    private fun getHttpWrapperHandler(): MoshiResultTypeAdapterFactory.HttpWrapper {

        return object : MoshiResultTypeAdapterFactory.HttpWrapper {
            override fun getStatusCodeKey(): String {
                return "code"
            }

            override fun getErrorMsgKey(): String {
                return "message"
            }

            override fun getDataKey(): String {
                return "data"
            }

            override fun isRequestSuccess(statusCode: Int): Boolean {
                return statusCode == 200 // 200 表示业务上是正确返回了数据
            }
        }
    }

    fun baseUrl(): String {
        return getBaseUrl()
    }

    private val retrofitNormal: Retrofit
        get() {

            val retrofitUser =
                Retrofit.Builder()
                    .baseUrl(baseUrl())
                    .client(okHttpClient)
                    .addConverterFactory(MoshiConverterFactory.create(moshi))
                    .addCallAdapterFactory(CoroutineCallAdapterFactory())
                    .addCallAdapterFactory(
                        HttpResponseCallAdapterFactory(globalErrorHandler) // 全局的错误处理器
                    )
                    .build()

            return retrofitUser
        }

    private val retrofitNoWrapper: Retrofit
        get() {
            val retrofitUser =
                Retrofit.Builder()
                    .baseUrl(baseUrl())
                    .client(okHttpClient)
                    .addConverterFactory(MoshiConverterFactory.create(moshiNoWrapper))
                    .addCallAdapterFactory(CoroutineCallAdapterFactory())
                    .addCallAdapterFactory(
                        HttpResponseCallAdapterFactory(globalErrorHandler) // 全局的错误处理器
                    )
                    .build()

            return retrofitUser
        }


    fun getUserApi(): IUserApi {
        return retrofitNormal.create(IUserApi::class.java)
    }

    fun getAgentApi(): IAgentApi {
        return retrofitNormal.create(IAgentApi::class.java)
    }

    fun getChatApi(): IChatApi {
        return retrofitNoWrapper.create(IChatApi::class.java)
    }

    fun getSubscriptionApi(): ISubscriptionApi {
        return retrofitNormal.create(ISubscriptionApi::class.java)
    }

    fun getCommonApi(): ICommonApi {
        return retrofitNormal.create(ICommonApi::class.java)
    }

}
