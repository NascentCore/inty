package ai.sxwl.android.data.http

import ai.sxwl.android.data.http.config.NetworkConfig
import ai.sxwl.android.data.http.services.AgentService
import ai.sxwl.android.data.http.services.AuthService
import ai.sxwl.android.data.http.services.ChatService
import ai.sxwl.android.data.http.services.ReportService
import ai.sxwl.android.data.http.services.SubscriptionService
import ai.sxwl.android.data.http.services.UserService
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.utils.LogUtils
import android.content.Context
import com.inty.api.client.IntyClient
import com.inty.api.client.IntyClientImpl
import com.inty.api.client.okhttp.OkHttpClient
import com.inty.api.core.ClientOptions
import kotlinx.coroutines.withTimeout
import java.lang.ref.WeakReference
import java.util.concurrent.ConcurrentHashMap

/**
 * Inty网络管理器 - 企业级网络库封装 提供统一的网络管理和API服务入口
 *
 * 核心功能：
 * 1. 统一的客户端管理和缓存
 * 2. 网络状态管理
 * 3. 统一的日志记录
 * 4. 环境配置管理
 * 5. 业务API服务入口
 */
object IntyNetworkManager {

    private val clientCache = ConcurrentHashMap<String, IntyClient>()
    private var isInitialized = false
    private var applicationContextRef: WeakReference<Context>? = null

    /** 初始化网络管理器 使用弱引用避免内存泄露 */
    fun initialize(context: Context, buildType: String) {
        if (!isInitialized) {
            // 使用弱引用保存 ApplicationContext，避免内存泄露
            this.applicationContextRef = WeakReference(context.applicationContext)
            NetworkStateManager.initialize(context)
            NetworkConfig.setBuildType(buildType)
            isInitialized = true
            LogUtils.d(
                "IntyNetworkManager initialized with environment: ${NetworkConfig.getCurrentBuildType()}"
            )
        }
    }

    /** 获取Inty客户端实例 支持客户端缓存和自动重新创建 */
    fun getClient(): IntyClient {
        checkInitialized()

        val currentApiKey = IntySetting.getCurToken()
        val currentBaseUrl = NetworkConfig.getBaseUrl()
        val cacheKey = "${currentApiKey}_$currentBaseUrl"

        return clientCache.getOrPut(cacheKey) { createClient(currentApiKey, currentBaseUrl) }
    }

    /** 创建新的客户端实例 使用新的配置系统 */
    private fun createClient(apiKey: String, baseUrl: String): IntyClient {
        val environmentConfig = NetworkConfig.getCurrentEnvironmentConfig()
        LogUtils.d(
            "Creating new IntyClient: apiKey=${apiKey.take(8)}..., baseUrl=$baseUrl, environment=${NetworkConfig.getCurrentBuildType()}"
        )

        // 使用统一的 OkHttpClient，包含所有必要的拦截器（包括动态 header 拦截器）
        // 这样 SDK 的请求也会包含 requestId 和 timestamp
        val unifiedOkHttpClient = UnifiedOkHttpClient.create()

        // 创建 SDK 的 HttpClient，使用我们的统一 OkHttpClient
        // SDK 的 OkHttpClient 类接受底层的 okhttp3.OkHttpClient
        // 但 SDK 的 OkHttpClient 是 private 的，我们无法直接创建
        // 所以我们通过 ClientOptions 直接设置 HttpClient
        val sdkHttpClient = createSdkHttpClient(unifiedOkHttpClient, environmentConfig)

        // 创建 ClientOptions，使用统一的 OkHttpClient
        val clientOptions = ClientOptions.builder()
            .apiKey(apiKey)
            .baseUrl(baseUrl)
            .httpClient(sdkHttpClient)
            .build()

        return IntyClientImpl(clientOptions)
    }

    /**
     * 创建 SDK 的 HttpClient，使用统一的 OkHttpClient
     * 通过反射创建 SDK 的 OkHttpClient 实例，传入我们的统一 OkHttpClient
     */
    private fun createSdkHttpClient(
        okHttpClient: okhttp3.OkHttpClient,
        environmentConfig: NetworkConfig.EnvironmentConfig
    ): com.inty.api.core.http.HttpClient {
        // SDK 的 OkHttpClient 类使用反射来创建实例
        // 我们通过创建一个包装器 HttpClient 来实现
        // 但由于 SDK 的复杂性，我们直接使用 SDK 的 OkHttpClient.builder()
        // 并在 build() 时替换内部的 okhttp3.OkHttpClient

        // 使用 SDK 的 OkHttpClient.Builder，但我们需要在内部使用我们的统一 OkHttpClient
        // 由于 SDK 的 OkHttpClient 是 private 的，我们通过反射来创建
        val timeout = com.inty.api.core.Timeout.builder()
            .connect(java.time.Duration.ofMillis(environmentConfig.timeout.connectTimeoutMs))
            .read(java.time.Duration.ofMillis(environmentConfig.timeout.readTimeoutMs))
            .write(java.time.Duration.ofMillis(environmentConfig.timeout.writeTimeoutMs))
            .build()

        // 创建 SDK 的 HttpClient，使用我们的统一 OkHttpClient
        // 通过反射创建 SDK 的 OkHttpClient 实例
        try {
            val sdkHttpClientClass = Class.forName("com.inty.api.client.okhttp.OkHttpClient")
            val constructor =
                sdkHttpClientClass.getDeclaredConstructor(okhttp3.OkHttpClient::class.java)
            constructor.isAccessible = true
            @Suppress("UNCHECKED_CAST")
            return constructor.newInstance(okHttpClient) as com.inty.api.core.http.HttpClient
        } catch (e: Exception) {
            LogUtils.w("Failed to create SDK HttpClient with unified OkHttpClient: ${e.message}")
            // 如果反射失败，使用 SDK 的默认方式
            return OkHttpClient.builder()
                .timeout(timeout)
                .build()
        }
    }

    /** 清除客户端缓存 当用户登录状态发生变化时调用 */
    fun clearClientCache() {
        clientCache.clear()
        LogUtils.i("IntyNetworkManager: Cleared client cache")
    }

    /** 清理资源，释放Context引用 在应用退出或需要重置时调用 */
    fun cleanup() {
        clientCache.clear()
        applicationContextRef = null
        isInitialized = false
        LogUtils.i("IntyNetworkManager: Cleaned up resources")
    }

    /** 获取ApplicationContext（安全方式） 如果Context已被回收，返回null */
    private fun getApplicationContext(): Context? {
        return applicationContextRef?.get()
    }

    /** 检查网络管理器是否已初始化 */
    private fun checkInitialized() {
        if (!isInitialized) {
            throw IllegalStateException(
                "IntyNetworkManager not initialized. Call initialize() first."
            )
        }
    }

    /** 检查是否已初始化 */
    fun isInitialized(): Boolean = isInitialized

    /** 获取网络状态管理器 */
    fun getNetworkStateManager(): NetworkStateManager {
        checkInitialized()
        return NetworkStateManager
    }

    /** 获取当前环境配置 */
    fun getCurrentEnvironmentConfig(): NetworkConfig.EnvironmentConfig =
        NetworkConfig.getCurrentEnvironmentConfig()

    /** 检查是否为调试环境 */
    fun isDebugEnvironment(): Boolean = NetworkConfig.isDebugEnvironment()

    /** 检查是否启用详细日志 */
    fun shouldEnableDetailedLogging(): Boolean = NetworkConfig.shouldEnableDetailedLogging()

    /** 释放资源 */
    fun release() {
        clientCache.clear()
        NetworkStateManager.release()
        applicationContextRef = null
        isInitialized = false
        LogUtils.i("IntyNetworkManager released")
    }

    // ==================== 业务API服务入口 ====================

    /** 认证相关API 替换: IUserApi 的认证相关方法 */
    val auth: AuthService
        get() = AuthService

    /** 用户相关API 替换: IUserApi 的用户相关方法 */
    val user: UserService
        get() = UserService

    /** 智能体相关API 替换: IAgentApi */
    val agent: AgentService
        get() = AgentService

    /** 聊天相关API 替换: IChatApi */
    val chat: ChatService
        get() = ChatService

    /** 订阅相关API 替换: ISubscriptionApi */
    val subscription: SubscriptionService
        get() = SubscriptionService

    /** 举报相关API 替换: IReportApi */
    val report: ReportService
        get() = ReportService

    /** 网络状态管理器 */
    val networkState: NetworkStateManager
        get() = getNetworkStateManager()

    // ==================== 请求执行功能 ====================

    /** 请求配置 */
    data class RequestConfig(val timeoutMs: Long = 30000)

    /** 执行API请求 提供统一的请求执行和错误处理 */
    suspend fun <T> executeRequest(
        operation: String,
        config: RequestConfig? = null,
        apiCall: suspend () -> T,
    ): ApiResult<T> {
        val actualConfig = config ?: getDefaultRequestConfig()

        return try {
            if (NetworkConfig.shouldEnableDetailedLogging()) {
                LogUtils.i("🔄 Executing $operation")
            }

            val result = withTimeout(actualConfig.timeoutMs) { apiCall() }

            if (NetworkConfig.shouldEnableDetailedLogging()) {
                LogUtils.i("✅ $operation succeeded")
            }

            ApiResult.Success(result)
        } catch (e: Exception) {
            if (NetworkConfig.shouldEnableDetailedLogging()) {
                LogUtils.i("❌ $operation failed: ${e.message}")
            }
            e.toApiResult()
        }
    }

    /** 获取默认请求配置 */
    private fun getDefaultRequestConfig(): RequestConfig {
        val environmentConfig = NetworkConfig.getCurrentEnvironmentConfig()
        return RequestConfig(timeoutMs = environmentConfig.timeout.readTimeoutMs)
    }

    /** 创建快速请求配置 */
    fun createFastRequestConfig(): RequestConfig = RequestConfig(timeoutMs = 10000)

    /** 创建关键请求配置 */
    fun createCriticalRequestConfig(): RequestConfig = RequestConfig(timeoutMs = 120000)
}
