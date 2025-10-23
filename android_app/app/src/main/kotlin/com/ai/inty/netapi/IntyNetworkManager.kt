package com.ai.inty.netapi

import ai.sxwl.android.utils.LogUtils
import android.content.Context
import com.ai.inty.netapi.config.NetworkConfig
import com.inty.api.client.IntyClient
import com.inty.api.client.okhttp.IntyOkHttpClient
import com.inty.utils.storage.IntySetting
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
    fun initialize(context: Context) {
        if (!isInitialized) {
            // 使用弱引用保存 ApplicationContext，避免内存泄露
            this.applicationContextRef = WeakReference(context.applicationContext)
            NetworkStateManager.initialize(context)
            isInitialized = true
            LogUtils.d("IntyNetworkManager initialized with environment: ${NetworkConfig.getCurrentBuildType()}")
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
        LogUtils.d("Creating new IntyClient: apiKey=${apiKey.take(8)}..., baseUrl=$baseUrl, environment=${NetworkConfig.getCurrentBuildType()}")
        return IntyOkHttpClient.builder().apiKey(apiKey).baseUrl(baseUrl).build()
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
    val auth: com.ai.inty.netapi.services.AuthService
        get() = com.ai.inty.netapi.services.AuthService

    /** 用户相关API 替换: IUserApi 的用户相关方法 */
    val user: com.ai.inty.netapi.services.UserService
        get() = com.ai.inty.netapi.services.UserService

    /** 智能体相关API 替换: IAgentApi */
    val agent: com.ai.inty.netapi.services.AgentService
        get() = com.ai.inty.netapi.services.AgentService

    /** 聊天相关API 替换: IChatApi */
    val chat: com.ai.inty.netapi.services.ChatService
        get() = com.ai.inty.netapi.services.ChatService

    /** 订阅相关API 替换: ISubscriptionApi */
    val subscription: com.ai.inty.netapi.services.SubscriptionService
        get() = com.ai.inty.netapi.services.SubscriptionService

    /** 举报相关API 替换: IReportApi */
    val report: com.ai.inty.netapi.services.ReportService
        get() = com.ai.inty.netapi.services.ReportService

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
