package ai.sxwl.android.data.error

import java.io.FileNotFoundException
import java.net.ConnectException
import java.net.SocketTimeoutException
import java.net.UnknownHostException

/**
 * 数据层统一错误定义
 */
sealed class DataError : Exception() {

    // 网络相关错误
    sealed class Network : DataError() {
        data object NoConnection : Network()
        data object Timeout : Network()
        data object ServerError : Network()
        data object BadRequest : Network()
        data object Unauthorized : Network()
        data object Forbidden : Network()
        data object NotFound : Network()
        data object TooManyRequests : Network()
        data class Unknown(val code: Int, override val message: String) : Network()
    }

    // 本地存储相关错误
    sealed class Local : DataError() {
        data object DatabaseError : Local()
        data object FileNotFound : Local()
        data object PermissionDenied : Local()
        data object StorageFull : Local()
        data object CorruptedData : Local()
        data class Unknown(override val message: String) : Local()
    }

    // 业务逻辑相关错误
    sealed class Business : DataError() {
        data object UserNotFound : Business()
        data object AgentNotFound : Business()
        data object SessionNotFound : Business()
        data object AlreadyFollowing : Business()
        data object NotFollowing : Business()
        data object InsufficientPermission : Business()
        data object InvalidInput : Business()
        data object LimitExceeded : Business()
        data class ValidationError(val field: String, override val message: String) : Business()
    }

    // 认证相关错误
    sealed class Auth : DataError() {
        data object TokenExpired : Auth()
        data object InvalidCredentials : Auth()
        data object AccountLocked : Auth()
        data object AccountNotActivated : Auth()
        data object RefreshTokenExpired : Auth()
        data object SessionExpired : Auth()
    }

    // 内容相关错误
    sealed class Content : DataError() {
        data object ContentFiltered : Content()
        data object UnsupportedFormat : Content()
        data object FileTooLarge : Content()
        data object EmptyContent : Content()
        data object InvalidFormat : Content()
    }

    // 配额相关错误
    sealed class Quota : DataError() {
        data object DailyLimitExceeded : Quota()
        data object MonthlyLimitExceeded : Quota()
        data object StorageLimitExceeded : Quota()
        data object MessageLimitExceeded : Quota()
        data object VipRequired : Quota()
    }
}

/**
 * 错误消息映射
 */
object ErrorMessages {

    fun getErrorMessage(error: DataError): String {
        return when (error) {
            // 网络错误
            is DataError.Network.NoConnection -> "网络连接不可用，请检查网络设置"
            is DataError.Network.Timeout -> "网络连接超时，请稍后重试"
            is DataError.Network.ServerError -> "服务器暂时不可用，请稍后重试"
            is DataError.Network.BadRequest -> "请求参数错误"
            is DataError.Network.Unauthorized -> "请先登录"
            is DataError.Network.Forbidden -> "访问被拒绝"
            is DataError.Network.NotFound -> "请求的资源不存在"
            is DataError.Network.TooManyRequests -> "请求过于频繁，请稍后重试"
            is DataError.Network.Unknown -> error.message

            // 本地存储错误
            is DataError.Local.DatabaseError -> "数据库错误，请重启应用"
            is DataError.Local.FileNotFound -> "文件不存在"
            is DataError.Local.PermissionDenied -> "权限不足"
            is DataError.Local.StorageFull -> "存储空间不足"
            is DataError.Local.CorruptedData -> "数据损坏，请重新同步"
            is DataError.Local.Unknown -> error.message

            // 业务逻辑错误
            is DataError.Business.UserNotFound -> "用户不存在"
            is DataError.Business.AgentNotFound -> "Agent不存在"
            is DataError.Business.SessionNotFound -> "会话不存在"
            is DataError.Business.AlreadyFollowing -> "已经关注了该Agent"
            is DataError.Business.NotFollowing -> "还未关注该Agent"
            is DataError.Business.InsufficientPermission -> "权限不足"
            is DataError.Business.InvalidInput -> "输入内容无效"
            is DataError.Business.LimitExceeded -> "超出限制"
            is DataError.Business.ValidationError -> "${error.field}: ${error.message}"

            // 认证错误
            is DataError.Auth.TokenExpired -> "登录已过期，请重新登录"
            is DataError.Auth.InvalidCredentials -> "用户名或密码错误"
            is DataError.Auth.AccountLocked -> "账户已被锁定"
            is DataError.Auth.AccountNotActivated -> "账户未激活"
            is DataError.Auth.RefreshTokenExpired -> "会话已过期，请重新登录"
            is DataError.Auth.SessionExpired -> "会话已过期，请重新登录"

            // 内容错误
            is DataError.Content.ContentFiltered -> "内容包含敏感信息，无法发送"
            is DataError.Content.UnsupportedFormat -> "不支持的文件格式"
            is DataError.Content.FileTooLarge -> "文件大小超出限制"
            is DataError.Content.EmptyContent -> "内容不能为空"
            is DataError.Content.InvalidFormat -> "格式错误"

            // 配额错误
            is DataError.Quota.DailyLimitExceeded -> "今日使用次数已达上限"
            is DataError.Quota.MonthlyLimitExceeded -> "本月使用次数已达上限"
            is DataError.Quota.StorageLimitExceeded -> "存储空间已满"
            is DataError.Quota.MessageLimitExceeded -> "消息发送次数已达上限"
            is DataError.Quota.VipRequired -> "该功能需要VIP会员"
        }
    }
}

/**
 * HTTP状态码转换为DataError
 */
fun Int.toDataError(message: String = ""): DataError.Network {
    return when (this) {
        400 -> DataError.Network.BadRequest
        401 -> DataError.Network.Unauthorized
        403 -> DataError.Network.Forbidden
        404 -> DataError.Network.NotFound
        429 -> DataError.Network.TooManyRequests
        in 500..599 -> DataError.Network.ServerError
        else -> DataError.Network.Unknown(this, message)
    }
}

/**
 * Exception转换为DataError
 */
fun Throwable.toDataError(): DataError {
    return when (this) {
        is DataError -> this
        is UnknownHostException -> DataError.Network.NoConnection
        is SocketTimeoutException -> DataError.Network.Timeout
        is ConnectException -> DataError.Network.NoConnection
        is FileNotFoundException -> DataError.Local.FileNotFound
        is SecurityException -> DataError.Local.PermissionDenied
        is IllegalArgumentException -> DataError.Business.InvalidInput
        else -> DataError.Network.Unknown(-1, message ?: "Unknown error")
    }
}
