package com.ai.inty.net

import android.content.Context
import android.content.Intent
import com.ai.inty.Constant
import com.ai.inty.utils.FirebaseManager
import com.ai.inty.utils.FirebasePerformanceHelper
import com.ai.inty.utils.PageTrackingHelper
import com.architecture.httplib.core.HttpResponseCallAdapterFactory
import com.architecture.httplib.core.MoshiResultTypeAdapterFactory
import com.architecture.httplib.error.GlobalErrorHandler
import com.chuckerteam.chucker.api.ChuckerInterceptor
import com.inty.utils.AppEnv
import com.inty.utils.log.EasyLog
import com.inty.utils.storage.IntySetting
import com.jakewharton.retrofit2.adapter.kotlin.coroutines.CoroutineCallAdapterFactory
import com.squareup.moshi.DefaultIfNullFactory
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import com.therouter.inject.ServiceProvider
import okhttp3.ConnectionPool
import okhttp3.Dns
import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Protocol
import okhttp3.Response
import okhttp3.ResponseBody.Companion.toResponseBody
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import java.net.InetAddress
import java.util.concurrent.TimeUnit

/** 获取基础URL 根据构建类型返回对应的API基础URL */
fun getBaseUrl(): String {
    return when (AppEnv.buildType) {
        "local" -> "http://${Constant.USER_HOST_LOCAL}/"
        "debug" -> "https://${Constant.USER_HOST_DEV}/"
        "playdebug" -> "https://${Constant.USER_HOST_DEV}/"
        "release" -> "https://${Constant.USER_HOST}/"
        else -> "https://${Constant.USER_HOST_DEV}/" // fallback to staging
    }
}

class AuthInterceptor : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        EasyLog.log("AuthInterceptor - getCurToken: ${IntySetting.getCurToken()}")
        val request =
            chain
                .request()
                .newBuilder()
                .addHeader("accept", "application/json")
                .addHeader("appVersionCode", AppEnv.version_code.toString())
                .addHeader("appVersionName", AppEnv.version_name)
                .addHeader("Authorization", "Bearer ${IntySetting.getCurToken()}")
                .build()

        EasyLog.log("request = $request")
        val response = chain.proceed(request)

        when (response.code) {
            401 -> {
                EasyLog.log("http 401 for ${request.url}", EasyLog.ERROR)

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
                    EasyLog.log("Ignoring 401 during logout process")
                } else {
                    EasyLog.log("401 unauthorized - switching to guest mode", EasyLog.ERROR)
                    IntySetting.logout()
                    restartAppProcess(context = AppEnv.context)
                }
            }
        }

        return response
    }
}

/** 重试拦截器 对网络错误进行重试，提高请求成功率 */
class RetryInterceptor(private val maxRetries: Int = 3) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        var lastException: Exception? = null

        // 重试逻辑
        for (attempt in 0 until maxRetries) {
            try {
                val currentResponse = chain.proceed(request)

                // 如果响应成功或客户端错误（4xx），不重试
                if (currentResponse.isSuccessful || currentResponse.code in 400..499) {
                    return currentResponse
                }

                // 服务器错误（5xx）才重试
                if (currentResponse.code in 500..599) {
                    EasyLog.log(
                        "Retry attempt ${attempt + 1} for ${request.url} due to server error ${currentResponse.code}"
                    )

                    // Firebase Analytics - 记录服务器错误重试
                    FirebaseManager.logEvent(
                        "network_retry",
                        mapOf(
                            "attempt" to (attempt + 1),
                            "http_code" to currentResponse.code,
                            "url" to request.url.toString(),
                        ),
                    )

                    currentResponse.close()
                    if (attempt < maxRetries - 1) {
                        Thread.sleep(1000L * (attempt + 1)) // 指数退避
                    }
                } else {
                    return currentResponse
                }
            } catch (e: Exception) {
                lastException = e
                EasyLog.log("Retry attempt ${attempt + 1} failed for ${request.url}: ${e.message}")
                if (attempt < maxRetries - 1) {
                    Thread.sleep(1000L * (attempt + 1)) // 指数退避
                }
            }
        }

        // 所有重试都失败了，返回错误响应而不是抛出异常
        EasyLog.log(
            "All retry attempts failed for ${request.url} after $maxRetries attempts",
            EasyLog.ERROR,
        )

        // Firebase Analytics - 记录网络请求最终失败
        FirebaseManager.logEvent(
            "network_final_failure",
            mapOf(
                "max_retries" to maxRetries,
                "url" to request.url.toString(),
                "last_error" to (lastException?.message ?: "unknown"),
            ),
        )

        // Firebase Crashlytics - 记录网络失败
        FirebaseManager.setCustomKey("network_failure_url", request.url.toString())
        FirebaseManager.setCustomKey("network_failure_retries", maxRetries.toString())
        FirebaseManager.recordException(
            Exception(
                "Network request failed after $maxRetries attempts: ${lastException?.message}"
            )
        )

        // 如果没有响应但有异常，创建一个错误响应
        val errorMessage = lastException?.message ?: ""
        EasyLog.log("Creating error response for ${request.url}: $errorMessage", EasyLog.ERROR)

        // 创建一个表示网络错误的响应
        return Response.Builder()
            .request(request)
            .protocol(Protocol.HTTP_1_1)
            .code(500) // 内部服务器错误
            .message("RetryInterceptor Network Error")
            .body(errorMessage.toResponseBody("text/plain".toMediaType()))
            .build()
    }
}

/** 网络性能监控拦截器 监控请求耗时，帮助识别性能问题 */
private class PerformanceInterceptor : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        val startTime = System.currentTimeMillis()

        EasyLog.log("🌐 Starting request: ${request.method} ${request.url}")

        // 创建 Firebase Performance HTTP Metric
        val httpMetric = FirebasePerformanceHelper.createHttpMetric(request)
        FirebasePerformanceHelper.startHttpMetric(httpMetric)

        return try {
            val response = chain.proceed(request)
            val endTime = System.currentTimeMillis()
            val duration = endTime - startTime

            // 停止 Firebase Performance HTTP Metric
            FirebasePerformanceHelper.stopHttpMetric(httpMetric, response)

            // 记录请求性能
            when {
                duration < 1000 -> {
                    EasyLog.log(
                        "✅ Request completed: ${request.method} ${request.url} (${duration}ms)"
                    )
                }

                duration < 3000 -> {
                    EasyLog.log(
                        "⚠️ Slow request: ${request.method} ${request.url} (${duration}ms)",
                        EasyLog.WARN,
                    )
                }

                else -> {
                    EasyLog.log(
                        "🚨 Very slow request: ${request.method} ${request.url} (${duration}ms)",
                        EasyLog.ERROR,
                    )
                }
            }

            response
        } catch (e: Exception) {
            val endTime = System.currentTimeMillis()
            val duration = endTime - startTime

            // 停止 Firebase Performance HTTP Metric (即使请求失败)
            FirebasePerformanceHelper.stopHttpMetric(httpMetric, null)

            EasyLog.log(
                "❌ Request failed: ${request.method} ${request.url} (${duration}ms): ${e.message}",
                EasyLog.ERROR,
            )
            throw e
        }
    }
}

/** 自定义DNS解析器，支持缓存 */
private class CachedDns : Dns {
    private val cache = mutableMapOf<String, List<InetAddress>>()

    override fun lookup(hostname: String): List<InetAddress> {
        return cache.getOrPut(hostname) { Dns.SYSTEM.lookup(hostname) }
    }
}

private fun restartAppProcess(context: Context) {
    val intent = context.packageManager.getLaunchIntentForPackage(context.packageName)
    intent?.apply {
        addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP) // 清除历史栈
        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK) // 新任务栈
        context.startActivity(this)
    }
    // 终止当前进程
    android.os.Process.killProcess(android.os.Process.myPid())
}

object NetServiceMgr {

    val okHttpClient: OkHttpClient
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
                    .addInterceptor(ChuckerInterceptor(AppEnv.context))
            return builder.build()
        }

    val moshi: Moshi
        get() {
            return Moshi.Builder()
                // 添加返回的json 数据自定义解析器
                .add(DefaultIfNullFactory())
                .add(MoshiResultTypeAdapterFactory(getHttpWrapperHandler()))
                .addLast(KotlinJsonAdapterFactory()) //
                .build()
        }

    val moshiNoWrapper: Moshi
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

    val retrofitNormal: Retrofit
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

    val retrofitNoWrapper: Retrofit
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
}

@ServiceProvider
fun getUserApi(): IUserApi {
    return NetServiceMgr.retrofitNormal.create(IUserApi::class.java)
}

@ServiceProvider
fun getAgentApi(): IAgentApi {
    return NetServiceMgr.retrofitNormal.create(IAgentApi::class.java)
}

@ServiceProvider
fun getChatApi(): IChatApi {
    return NetServiceMgr.retrofitNoWrapper.create(IChatApi::class.java)
}

@ServiceProvider
fun getSubscriptionApi(): ISubscriptionApi {
    return NetServiceMgr.retrofitNormal.create(ISubscriptionApi::class.java)
}

@ServiceProvider
fun getCommonApi(): ICommonApi {
    return NetServiceMgr.retrofitNormal.create(ICommonApi::class.java)
}
