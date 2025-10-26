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
import com.inty.api.client.okhttp.IntyOkHttpClient
import kotlinx.coroutines.withTimeout
import java.lang.ref.WeakReference
import java.util.concurrent.ConcurrentHashMap

/**
 * Inty网络管理器 - 企业级网络库封装提供统一的网络管理和API服务入口
 *
 * 核心功能：
 * 1.统一的客户端管理和存储
 * 2. 网络状态管理
 * 3.统一的日志记录
 * 4.环境配置管理
 * 5.业务API服务入口
 */
object IntyNetworkManager {

    private val clientCache = ConcurrentHashMap<String, IntyClient>()
    private var isInitialized = false
    private var applicationContextRef: WeakReference<Context>? = null

    /** 初始化网络管理器使用弱引用避免内存丢失 */
    fun initialize(context: Context, buildType: String) {
        if (!isInitialized) {
// 使用弱引用保存ApplicationContext，避免内存泄漏
            this.applicationContextRef = WeakReference(context.applicationContext)
            NetworkStateManager.initialize(context)
            NetworkConfig.setBuildType(buildType)
            isInitialized = true
            LogUtils.d("IntyNetworkManager initialized with environment: ${NetworkConfig.getCurrentBuildType()}")
        }
    }

    /** 获取Inty客户端实例支持客户端缓存并自动重新创建 */
    fun getClient(): IntyClient {
        checkInitialized()

        val currentApiKey = IntySetting.getCurToken()
        val currentBaseUrl = NetworkConfig.getBaseUrl()
        val cacheKey = "${currentApiKey}_$currentBaseUrl"

        return clientCache.getOrPut(cacheKey) { createClient(currentApiKey, currentBaseUrl) }
    }

    /** 使用新的配置系统创建新的客户端实例 */
    private fun createClient(apiKey: String, baseUrl: String): IntyClient {
        val environmentConfig = NetworkConfig.getCurrentEnvironmentConfig()
        LogUtils.d("Creating new IntyClient: apiKey=${apiKey.take(8)}..., baseUrl=$baseUrl, environment=${NetworkConfig.getCurrentBuildType()}")
        return IntyOkHttpClient.builder().apiKey(apiKey).baseUrl(baseUrl).build()
    }

    /**当用户登录状态发生变化时调用清除客户端存储 */
    fun clearClientCache() {
        clientCache.clear()
        LogUtils.i("IntyNetworkManager: Cleared client cache")
    }

    /** 清理资源，释放上下文引用在应用退出或需要重置时调用 */
    fun cleanup() {
        clientCache.clear()
        applicationContextRef = null
        isInitialized = false
        LogUtils.i("IntyNetworkManager: Cleaned up resources")
    }

    /** 获取ApplicationContext（安全方式）如果Context已被恢复，返回null */
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

    /** 报告相关API 替换: IReportApi */
    val report: ReportService
        get() = ReportService

    /** 网络状态管理器 */
    val networkState: NetworkStateManager
        get() = getNetworkStateManager()
// ==================== 请求执行功能 ====================

    /** 请求配置 */
    data class RequestConfig(val timeoutMs: Long = 30000)

    /** 执行API请求提供统一的执行请求和错误处理 */
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
