package ai.sxwl.android.data.http

import ai.sxwl.android.utils.LogUtils

/** 统一的API响应结果包装器 提供统一的成功/失败状态和错误处理 */
sealed class ApiResult<out T> {
    data class Success<T>(val data: T) : ApiResult<T>()

    data class Error(val code: Int, val message: String?, val exception: Throwable? = null) :
        ApiResult<Nothing>()
}

/** 将异常转换为ApiResult */
fun <T> Exception.toApiResult(): ApiResult<T> {
    LogUtils.e("API exception: ${this.message}")
    LogUtils.e("API exception type: ${this.javaClass.simpleName}")
    LogUtils.e("API exception stack trace:", this)
    
    // 尝试获取HTTP状态码
    val httpCode = when (this) {
        is com.inty.api.errors.InternalServerException -> 500
        is com.inty.api.errors.BadRequestException -> 400
        is com.inty.api.errors.UnauthorizedException -> 401
        is com.inty.api.errors.NotFoundException -> 404
        else -> -1
    }
    
    LogUtils.e("API exception HTTP code: $httpCode")
    
    return ApiResult.Error(code = httpCode, message = this.message ?: "Unknown error", exception = this)
}

/** 执行API调用并返回ApiResult */
suspend fun <T> executeApiCall(apiCall: suspend () -> T): ApiResult<T> {
    return try {
        val result = apiCall()
        ApiResult.Success(result)
    } catch (e: Exception) {
        e.toApiResult()
    }
}
