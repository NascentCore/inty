package ai.sxwl.android.data.http

import ai.sxwl.android.data.http.config.NetworkConfig
import ai.sxwl.android.data.http.services.AgentService
import ai.sxwl.android.data.http.services.AuthService
import ai.sxwl.android.data.http.services.ChatService
import ai.sxwl.android.data.http.services.ReportService
import ai.sxwl.android.data.http.services.SubscriptionService
import ai.sxwl.android.data.http.services.UserService
import ai.sxwl.android.data.http.services.VersionService
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.utils.LogUtils
import android.content.Context
import com.inty.api.client.IntyClient
import com.inty.api.client.IntyClientImpl
import com.inty.api.client.okhttp.OkHttpClient
import com.inty.api.core.ClientOptions
import java.lang.ref.WeakReference
import java.util.concurrent.ConcurrentHashMap
import kotlinx.coroutines.withTimeout

/**
 * Inty 网络管理器 - 企业级网络库封装，提供统一的网络管理和 API 服务入口
 *
 * ## 用途
 * 管理基于 Stainless 生成的 Inty SDK 的现代化网络请求，主要用于**新功能开发**。
 *
 * ## 与 NetServiceMgr 的关系
 * 项目中存在**双网络栈并行架构**：
 * - **IntyNetworkManager** (本文件): Inty SDK 栈（Stainless 生成），用于新功能开发
 * - **NetServiceMgr**: 传统 Retrofit 栈，用于已有功能维护
 *
 * ## 共享基础设施
 * 两者都使用：
 * - `UnifiedOkHttpClient`: 统一的 OkHttpClient 实例
 * - `NetworkConfig`: 统一的环境配置和 baseUrl 管理
 * - `DebugBackendEndpointStore`: 运行时 URL 切换支持
 *
 * ## 缓存机制
 * - IntyClient 实例缓存: 基于 `apiKey + baseUrl` (key: `"${apiKey}_${baseUrl}"`)
 * - 与 NetServiceMgr 的缓存机制不同（NetServiceMgr 使用 `${baseUrl}_${ApiType}`）
 * - 缓存 key 包含 apiKey，因为不同用户需要不同的客户端实例
 *
 * ## URL 切换协调
 * 当切换 URL 时，需要同时清除两个管理器的缓存：
 *
 * ```kotlin
 * IntyNetworkManager.clearClientCache()  // 清除 SDK 缓存（本方法）
 * NetServiceMgr.clearCache()              // 清除 Retrofit 缓存
 * ```
 *
 * ## 使用指导
 * - **已有功能改善修改**: 继续使用 NetServiceMgr，不进行迁移
 * - **新功能开发**: 优先使用 IntyNetworkManager（本管理器）
 * - **不要混用**: 同一个功能不要同时使用两套网络栈
 *
 * ## 响应格式
 * 通过 Service 层封装，返回 `ApiResult<T>` 包装：
 * - `ApiResult.Success<T>`: 请求成功
 * - `ApiResult.Error`: 请求失败（包含错误信息）
 *
 * ## 核心功能
 * 1. 统一的客户端管理和缓存
 * 2. 网络状态管理
 * 3. 统一的日志记录
 * 4. 环境配置管理
 * 5. 业务API服务入口
 */
object IntyNetworkManager {

    /**
     * IntyClient 实例缓存
     *
     * 缓存 key 格式: `"${apiKey}_${baseUrl}"` 例如: `"token123_https://dev.inty.sxwl.ai/"`
     *
     * 注意：与 NetServiceMgr 的缓存机制不同
     * - IntyNetworkManager: 缓存 key 包含 apiKey，因为不同用户需要不同的客户端实例
     * - NetServiceMgr: 缓存 key 不包含 apiKey，因为 Retrofit 通过拦截器添加认证
     *
     * 当 baseUrl 或 apiKey 变化时，会自动创建新的客户端实例
     */
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

    /**
     * 获取 Inty 客户端实例，支持客户端缓存和自动重新创建
     *
     * ## 缓存机制
     * - 缓存 key: `"${apiKey}_${baseUrl}"`
     * - 当 apiKey 或 baseUrl 变化时，会自动创建新的客户端实例
     * - 会自动清理旧 token 的客户端缓存，避免内存泄漏
     *
     * ## 与 NetServiceMgr 的区别
     * - IntyNetworkManager: 每次调用都会检查最新的 baseUrl（支持运行时切换）
     * - NetServiceMgr: 同样支持运行时 baseUrl 切换，但缓存机制不同
     */
    fun getClient(): IntyClient {
        checkInitialized()

        val currentApiKey = IntySetting.getCurToken()
        val currentBaseUrl = NetworkConfig.getBaseUrl()
        val cacheKey = "${currentApiKey}_$currentBaseUrl"

        // 清除所有旧token的客户端缓存（避免旧token的客户端残留）
        // 只保留当前token的客户端，确保使用最新token
        clearOldTokenClients(currentApiKey, currentBaseUrl)

        return clientCache.getOrPut(cacheKey) { createClient(currentApiKey, currentBaseUrl) }
    }

    /** 清除旧token的客户端缓存 只保留当前token的客户端，确保使用最新token */
    private fun clearOldTokenClients(currentApiKey: String, currentBaseUrl: String) {
        val currentCacheKey = "${currentApiKey}_$currentBaseUrl"
        val entriesToRemove =
            clientCache.entries.filter { (key, _) ->
                // 清除所有相同baseUrl但不同token的客户端
                key != currentCacheKey && key.endsWith("_$currentBaseUrl")
            }

        if (entriesToRemove.isNotEmpty()) {
            entriesToRemove.forEach { (key, _) ->
                clientCache.remove(key)
                LogUtils.d("IntyNetworkManager: Removed old token client cache: $key")
            }
        }
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
        val clientOptions =
            ClientOptions.builder()
                .apiKey(apiKey)
                .baseUrl(baseUrl)
                .httpClient(sdkHttpClient)
                .build()

        return IntyClientImpl(clientOptions)
    }

    /** 创建 SDK 的 HttpClient，使用统一的 OkHttpClient 通过反射创建 SDK 的 OkHttpClient 实例，传入我们的统一 OkHttpClient */
    private fun createSdkHttpClient(
        okHttpClient: okhttp3.OkHttpClient,
        environmentConfig: NetworkConfig.EnvironmentConfig,
    ): com.inty.api.core.http.HttpClient {
        // SDK 的 OkHttpClient 类使用反射来创建实例
        // 我们通过创建一个包装器 HttpClient 来实现
        // 但由于 SDK 的复杂性，我们直接使用 SDK 的 OkHttpClient.builder()
        // 并在 build() 时替换内部的 okhttp3.OkHttpClient

        // 使用 SDK 的 OkHttpClient.Builder，但我们需要在内部使用我们的统一 OkHttpClient
        // 由于 SDK 的 OkHttpClient 是 private 的，我们通过反射来创建
        val timeout =
            com.inty.api.core.Timeout.builder()
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
            return OkHttpClient.builder().timeout(timeout).build()
        }
    }

    /**
     * 清除客户端缓存
     *
     * ## 调用时机
     * 1. 当用户登录状态发生变化时调用（例如：`IntySetting.login()`）
     * 2. Debug build 专用：当用户需要切换后端地址时调用（例如：`DebugBackendSettingsViewModel.applySelectedOverride()`）
     *
     * ## 重要：需要与 NetServiceMgr 协调
     * 切换 URL 或登录状态变化时，需要同时清除两个管理器的缓存：
     *
     * ```kotlin
     * IntyNetworkManager.clearClientCache()  // 清除 SDK 缓存（本方法）
     * NetServiceMgr.clearCache()              // 清除 Retrofit 缓存
     * ```
     *
     * 参考: `DebugBackendSettingsViewModel.applySelectedOverride()` 和 `IntySetting.login()`
     */
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

    /**
     * 业务 API 服务入口
     *
     * 这些服务封装了 Inty SDK 的 API 调用，提供统一的接口和错误处理。 推荐使用这些服务，而不是直接使用 `getClient()`。
     *
     * ## 与 NetServiceMgr 的对应关系
     * - `auth`: 对应 NetServiceMgr 的认证相关 API
     * - `user`: 对应 NetServiceMgr 的 `getUserApi()`
     * - `agent`: 对应 NetServiceMgr 的 `getAgentApi()`
     * - `chat`: 对应 NetServiceMgr 的 `getChatApi()`
     * - `subscription`: 对应 NetServiceMgr 的 `getSubscriptionApi()`
     * - `report`: 对应 NetServiceMgr 的举报相关 API
     *
     * ## 使用示例
     *
     * ```kotlin
     * // 推荐：使用 Service 层
     * when (val result = IntyNetworkManager.user.getProfile()) {
     *     is ApiResult.Success -> { /* 处理成功 */ }
     *     is ApiResult.Error -> { /* 处理失败 */ }
     * }
     *
     * // 不推荐：直接使用 getClient()
     * val client = IntyNetworkManager.getClient()
     * val response = client.api().v1().users().profile().me()
     * ```
     */

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

    /** 版本检查相关API 替换: ICommonApi.checkAppUpgrade() */
    val version: VersionService
        get() = VersionService

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
            val result = withTimeout(actualConfig.timeoutMs) { apiCall() }
            ApiResult.Success(result)
        } catch (e: Exception) {
            LogUtils.e("❌ $operation failed: ${e.message}")
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
