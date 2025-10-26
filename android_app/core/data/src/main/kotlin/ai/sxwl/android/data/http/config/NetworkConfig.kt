package ai.sxwl.android.data.http.config

/** 网络配置管理 提供环境相关的配置管理，替代原有的硬编码配置 */
object NetworkConfig {
    /** 构建类型枚举 */
    enum class BuildType(val value: String) {
        LOCAL("local"),
        DEBUG("debug"),
        PLAY_DEBUG("playdebug"),
        RELEASE("release"),
    }

    /** 环境配置 */
    data class EnvironmentConfig(
        val baseUrl: String,
        val timeout: TimeoutConfig,
        val retry: RetryConfig,
        val connection: ConnectionConfig,
        val logging: LoggingConfig,
    )

    /** 超时配置 */
    data class TimeoutConfig(
        val connectTimeoutMs: Long = 15000,
        val writeTimeoutMs: Long = 15000,
        val readTimeoutMs: Long = 30000,
    )

    /** 重试配置 */
    data class RetryConfig(
        val maxRetries: Int = 3,
        val retryDelayMs: Long = 1000,
        val enableExponentialBackoff: Boolean = true,
    )

    /** 连接池配置 */
    data class ConnectionConfig(
        val maxConnections: Int = 5,
        val keepAliveDurationMs: Long = 300000, // 5 minutes
        val enableDnsCache: Boolean = true,
    )

    /** 日志配置 */
    data class LoggingConfig(
        val enableRequestLogging: Boolean = true,
        val enablePerformanceLogging: Boolean = true,
        val enableChuckerLogging: Boolean = true,
        val logLevel: LogLevel = LogLevel.INFO,
    )

    /** 日志级别 */
    enum class LogLevel {
        VERBOSE,
        DEBUG,
        INFO,
        WARN,
        ERROR,
    }

    private var currentBuildTypeStr = ""

    fun setBuildType(buildType: String) {
        currentBuildTypeStr = buildType
    }

    /** 获取当前构建类型 */
    fun getCurrentBuildType(): BuildType {
        return when (currentBuildTypeStr) {
            "local" -> BuildType.LOCAL
            "debug" -> BuildType.DEBUG
            "playdebug" -> BuildType.PLAY_DEBUG
            "release" -> BuildType.RELEASE
            else -> BuildType.DEBUG // fallback
        }
    }

    /** 获取当前环境配置 */
    fun getCurrentEnvironmentConfig(): EnvironmentConfig {
        return when (getCurrentBuildType()) {
            BuildType.LOCAL -> getLocalConfig()
            BuildType.DEBUG -> getDebugConfig()
            BuildType.PLAY_DEBUG -> getPlayDebugConfig()
            BuildType.RELEASE -> getReleaseConfig()
        }
    }

    /** 本地环境配置 */
    private fun getLocalConfig(): EnvironmentConfig {
        return EnvironmentConfig(
            baseUrl = "http://${Constant.USER_HOST_LOCAL}/",
            timeout =
            TimeoutConfig(
                connectTimeoutMs = 10000, // 本地环境可以更短
                writeTimeoutMs = 10000,
                readTimeoutMs = 20000,
            ),
            retry =
            RetryConfig(
                maxRetries = 2, // 本地环境减少重试
                retryDelayMs = 500,
            ),
            connection =
            ConnectionConfig(
                maxConnections = 3,
                keepAliveDurationMs = 60000, // 1 minute
            ),
            logging =
            LoggingConfig(
                enableRequestLogging = true,
                enablePerformanceLogging = true,
                enableChuckerLogging = true,
                logLevel = LogLevel.DEBUG,
            ),
        )
    }

    /** 调试环境配置 */
    private fun getDebugConfig(): EnvironmentConfig {
        return EnvironmentConfig(
            baseUrl = "https://${Constant.USER_HOST_DEV}/",
            timeout =
            TimeoutConfig(
                connectTimeoutMs = 15000,
                writeTimeoutMs = 15000,
                readTimeoutMs = 30000,
            ),
            retry = RetryConfig(maxRetries = 3, retryDelayMs = 1000),
            connection = ConnectionConfig(maxConnections = 5, keepAliveDurationMs = 300000),
            logging =
            LoggingConfig(
                enableRequestLogging = true,
                enablePerformanceLogging = true,
                enableChuckerLogging = true,
                logLevel = LogLevel.DEBUG,
            ),
        )
    }

    /** Play调试环境配置 */
    private fun getPlayDebugConfig(): EnvironmentConfig {
        return EnvironmentConfig(
            baseUrl = "https://${Constant.USER_HOST_DEV}/",
            timeout =
            TimeoutConfig(
                connectTimeoutMs = 20000, // Play环境可能需要更长时间
                writeTimeoutMs = 20000,
                readTimeoutMs = 45000,
            ),
            retry =
            RetryConfig(
                maxRetries = 5, // Play环境增加重试
                retryDelayMs = 2000,
            ),
            connection =
            ConnectionConfig(
                maxConnections = 8,
                keepAliveDurationMs = 600000, // 10 minutes
            ),
            logging =
            LoggingConfig(
                enableRequestLogging = true,
                enablePerformanceLogging = true,
                enableChuckerLogging = false, // Play环境关闭Chucker
                logLevel = LogLevel.INFO,
            ),
        )
    }

    /** 生产环境配置 */
    private fun getReleaseConfig(): EnvironmentConfig {
        return EnvironmentConfig(
            baseUrl = "https://${Constant.USER_HOST}/",
            timeout =
            TimeoutConfig(
                connectTimeoutMs = 10000, // 生产环境优化超时
                writeTimeoutMs = 10000,
                readTimeoutMs = 20000,
            ),
            retry = RetryConfig(maxRetries = 3, retryDelayMs = 1000),
            connection =
            ConnectionConfig(
                maxConnections = 10,
                keepAliveDurationMs = 600000, // 10 minutes
            ),
            logging =
            LoggingConfig(
                enableRequestLogging = false, // 生产环境关闭详细日志
                enablePerformanceLogging = true,
                enableChuckerLogging = false,
                logLevel = LogLevel.WARN,
            ),
        )
    }

    /** 获取基础URL 兼容原有接口 */
    fun getBaseUrl(): String {
        return getCurrentEnvironmentConfig().baseUrl
    }

    /** 检查是否为调试环境 */
    fun isDebugEnvironment(): Boolean {
        return getCurrentBuildType() in listOf(BuildType.LOCAL, BuildType.DEBUG)
    }

    /** 检查是否为生产环境 */
    fun isProductionEnvironment(): Boolean {
        return getCurrentBuildType() == BuildType.RELEASE
    }

    /** 检查是否启用详细日志 */
    fun shouldEnableDetailedLogging(): Boolean {
        return getCurrentEnvironmentConfig().logging.enableRequestLogging
    }

    /** 检查是否启用性能监控 */
    fun shouldEnablePerformanceMonitoring(): Boolean {
        return getCurrentEnvironmentConfig().logging.enablePerformanceLogging
    }

    /** 检查是否启用Chucker */
    fun shouldEnableChucker(): Boolean {
        return getCurrentEnvironmentConfig().logging.enableChuckerLogging
    }
}
