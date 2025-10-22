package ai.sxwl.android.data.error

import ai.sxwl.android.utils.LogUtils

/**
 * 业务错误处理管理器
 * 提供统一的错误处理和用户友好的错误提示
 *
 * 职责：
 * 1. 统一错误分类和处理
 * 2. 提供用户友好的错误信息
 * 3. 错误日志记录和分析
 * 4. 错误恢复建议
 * 5. 网络错误重试策略
 */
object BusinessErrorHandler {

    /**
     * 处理业务错误
     * @param error 错误对象
     * @param context 错误上下文信息
     * @return 处理结果
     */
    suspend fun handleError(error: DataError, context: String = ""): ErrorHandlingResult {
        return when (error) {
            // 网络错误处理
            is DataError.Network -> handleNetworkError(error, context)

            // 认证错误处理
            is DataError.Auth -> handleAuthError(error, context)

            // 业务逻辑错误处理
            is DataError.Business -> handleBusinessError(error, context)

            // 本地存储错误处理
            is DataError.Local -> handleLocalError(error, context)

            // 内容相关错误处理
            is DataError.Content -> handleContentError(error, context)

            // 配额相关错误处理
            is DataError.Quota -> handleQuotaError(error, context)
        }
    }

    /**
     * 处理网络错误
     */
    private suspend fun handleNetworkError(
        error: DataError.Network,
        context: String
    ): ErrorHandlingResult {
        LogUtils.e("网络错误 [$context]: $error")

        return when (error) {
            is DataError.Network.NoConnection -> {
                ErrorHandlingResult(
                    userMessage = "网络连接不可用，请检查网络设置",
                    shouldRetry = true,
                    retryDelay = 3000L,
                    action = ErrorAction.SHOW_NETWORK_SETTINGS
                )
            }

            is DataError.Network.Timeout -> {
                ErrorHandlingResult(
                    userMessage = "网络连接超时，请稍后重试",
                    shouldRetry = true,
                    retryDelay = 2000L,
                    action = ErrorAction.RETRY
                )
            }

            is DataError.Network.ServerError -> {
                ErrorHandlingResult(
                    userMessage = "服务器暂时不可用，请稍后重试",
                    shouldRetry = true,
                    retryDelay = 5000L,
                    action = ErrorAction.RETRY
                )
            }

            is DataError.Network.Unauthorized -> {
                ErrorHandlingResult(
                    userMessage = "登录已过期，请重新登录",
                    shouldRetry = false,
                    action = ErrorAction.LOGIN_REQUIRED
                )
            }

            is DataError.Network.Forbidden -> {
                ErrorHandlingResult(
                    userMessage = "访问被拒绝，请检查权限",
                    shouldRetry = false,
                    action = ErrorAction.SHOW_PERMISSION_DIALOG
                )
            }

            is DataError.Network.TooManyRequests -> {
                ErrorHandlingResult(
                    userMessage = "请求过于频繁，请稍后重试",
                    shouldRetry = true,
                    retryDelay = 10000L,
                    action = ErrorAction.WAIT_AND_RETRY
                )
            }

            else -> {
                ErrorHandlingResult(
                    userMessage = "${error.message}",
                    shouldRetry = false,
                    action = ErrorAction.SHOW_ERROR_DIALOG
                )
            }
        }
    }

    /**
     * 处理认证错误
     */
    private suspend fun handleAuthError(
        error: DataError.Auth,
        context: String
    ): ErrorHandlingResult {
        LogUtils.e("认证错误 [$context]: $error")

        return when (error) {
            is DataError.Auth.TokenExpired -> {
                // 尝试刷新token
                ErrorHandlingResult(
                    userMessage = "登录已过期，正在重新登录...",
                    shouldRetry = true,
                    retryDelay = 1000L,
                    action = ErrorAction.REFRESH_TOKEN
                )
            }

            is DataError.Auth.InvalidCredentials -> {
                ErrorHandlingResult(
                    userMessage = "用户名或密码错误",
                    shouldRetry = false,
                    action = ErrorAction.SHOW_LOGIN_DIALOG
                )
            }

            is DataError.Auth.AccountLocked -> {
                ErrorHandlingResult(
                    userMessage = "账户已被锁定，请联系客服",
                    shouldRetry = false,
                    action = ErrorAction.CONTACT_SUPPORT
                )
            }

            else -> {
                ErrorHandlingResult(
                    userMessage = "认证失败，请重新登录",
                    shouldRetry = false,
                    action = ErrorAction.LOGIN_REQUIRED
                )
            }
        }
    }

    /**
     * 处理业务逻辑错误
     */
    private suspend fun handleBusinessError(
        error: DataError.Business,
        context: String
    ): ErrorHandlingResult {
        LogUtils.e("业务错误 [$context]: $error")

        return when (error) {
            is DataError.Business.UserNotFound -> {
                ErrorHandlingResult(
                    userMessage = "用户不存在",
                    shouldRetry = false,
                    action = ErrorAction.REFRESH_USER_DATA
                )
            }

            is DataError.Business.InsufficientPermission -> {
                ErrorHandlingResult(
                    userMessage = "权限不足，请升级账户",
                    shouldRetry = false,
                    action = ErrorAction.SHOW_UPGRADE_DIALOG
                )
            }

            is DataError.Business.LimitExceeded -> {
                ErrorHandlingResult(
                    userMessage = "操作次数已达上限",
                    shouldRetry = false,
                    action = ErrorAction.SHOW_LIMIT_DIALOG
                )
            }

            is DataError.Business.ValidationError -> {
                ErrorHandlingResult(
                    userMessage = "输入格式错误：${error.message}",
                    shouldRetry = false,
                    action = ErrorAction.SHOW_VALIDATION_ERROR
                )
            }

            else -> {
                ErrorHandlingResult(
                    userMessage = "${error.message}",
                    shouldRetry = false,
                    action = ErrorAction.SHOW_ERROR_DIALOG
                )
            }
        }
    }

    /**
     * 处理本地存储错误
     */
    private suspend fun handleLocalError(
        error: DataError.Local,
        context: String
    ): ErrorHandlingResult {
        LogUtils.e("本地存储错误 [$context]: $error")

        return when (error) {
            is DataError.Local.DatabaseError -> {
                ErrorHandlingResult(
                    userMessage = "数据存储错误，请重启应用",
                    shouldRetry = true,
                    retryDelay = 2000L,
                    action = ErrorAction.RESTART_APP
                )
            }

            is DataError.Local.StorageFull -> {
                ErrorHandlingResult(
                    userMessage = "存储空间不足，请清理缓存",
                    shouldRetry = false,
                    action = ErrorAction.CLEAR_CACHE
                )
            }

            is DataError.Local.PermissionDenied -> {
                ErrorHandlingResult(
                    userMessage = "权限不足，请在设置中开启相关权限",
                    shouldRetry = false,
                    action = ErrorAction.SHOW_PERMISSION_DIALOG
                )
            }

            else -> {
                ErrorHandlingResult(
                    userMessage = "本地数据错误，请重试",
                    shouldRetry = true,
                    retryDelay = 1000L,
                    action = ErrorAction.RETRY
                )
            }
        }
    }

    /**
     * 处理内容相关错误
     */
    private suspend fun handleContentError(
        error: DataError.Content,
        context: String
    ): ErrorHandlingResult {
        LogUtils.e("内容错误 [$context]: $error")

        return when (error) {
            is DataError.Content.ContentFiltered -> {
                ErrorHandlingResult(
                    userMessage = "内容包含敏感信息，请修改后重试",
                    shouldRetry = false,
                    action = ErrorAction.SHOW_CONTENT_WARNING
                )
            }

            is DataError.Content.FileTooLarge -> {
                ErrorHandlingResult(
                    userMessage = "文件过大，请选择较小的文件",
                    shouldRetry = false,
                    action = ErrorAction.SHOW_FILE_SIZE_LIMIT
                )
            }

            is DataError.Content.EmptyContent -> {
                ErrorHandlingResult(
                    userMessage = "内容不能为空",
                    shouldRetry = false,
                    action = ErrorAction.SHOW_VALIDATION_ERROR
                )
            }

            else -> {
                ErrorHandlingResult(
                    userMessage = "内容格式错误，请检查后重试",
                    shouldRetry = false,
                    action = ErrorAction.SHOW_ERROR_DIALOG
                )
            }
        }
    }

    /**
     * 处理配额相关错误
     */
    private suspend fun handleQuotaError(
        error: DataError.Quota,
        context: String
    ): ErrorHandlingResult {
        LogUtils.e("配额错误 [$context]: $error")

        return when (error) {
            is DataError.Quota.DailyLimitExceeded -> {
                ErrorHandlingResult(
                    userMessage = "今日使用次数已达上限，明天再来吧",
                    shouldRetry = false,
                    action = ErrorAction.SHOW_QUOTA_LIMIT
                )
            }

            is DataError.Quota.VipRequired -> {
                ErrorHandlingResult(
                    userMessage = "该功能需要VIP会员，立即升级享受更多特权",
                    shouldRetry = false,
                    action = ErrorAction.SHOW_VIP_UPGRADE
                )
            }

            else -> {
                ErrorHandlingResult(
                    userMessage = "使用次数已达上限，请稍后重试",
                    shouldRetry = false,
                    action = ErrorAction.SHOW_QUOTA_LIMIT
                )
            }
        }
    }

    /**
     * 检查是否需要显示错误提示
     * 避免频繁显示相同错误
     */
    suspend fun shouldShowError(error: DataError): Boolean {
        // 这里可以实现错误频率控制逻辑
        // 比如：相同错误在短时间内只显示一次
        return true
    }

    /**
     * 记录错误统计
     */
    fun recordError(error: DataError, context: String) {
        // 这里可以实现错误统计和上报逻辑
        LogUtils.e("错误统计 [$context]: ${error::class.simpleName}")
    }
}

/**
 * 错误处理结果
 */
data class ErrorHandlingResult(
    val userMessage: String,
    val shouldRetry: Boolean = false,
    val retryDelay: Long = 0L,
    val action: ErrorAction = ErrorAction.SHOW_ERROR_DIALOG
)

/**
 * 错误处理动作
 */
enum class ErrorAction {
    SHOW_ERROR_DIALOG,        // 显示错误对话框
    SHOW_NETWORK_SETTINGS,    // 显示网络设置
    SHOW_PERMISSION_DIALOG,   // 显示权限对话框
    SHOW_LOGIN_DIALOG,        // 显示登录对话框
    SHOW_UPGRADE_DIALOG,      // 显示升级对话框
    SHOW_VIP_UPGRADE,         // 显示VIP升级
    SHOW_QUOTA_LIMIT,         // 显示配额限制
    SHOW_CONTENT_WARNING,     // 显示内容警告
    SHOW_FILE_SIZE_LIMIT,     // 显示文件大小限制
    SHOW_VALIDATION_ERROR,    // 显示验证错误
    SHOW_LIMIT_DIALOG,        // 显示限制对话框
    LOGIN_REQUIRED,           // 需要登录
    REFRESH_TOKEN,            // 刷新token
    REFRESH_USER_DATA,        // 刷新用户数据
    RETRY,                    // 重试
    WAIT_AND_RETRY,          // 等待后重试
    RESTART_APP,             // 重启应用
    CLEAR_CACHE,             // 清理缓存
    CONTACT_SUPPORT          // 联系客服
}
