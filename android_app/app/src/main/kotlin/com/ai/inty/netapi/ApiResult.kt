package com.ai.inty.netapi

import com.inty.utils.log.EasyLog

/** 统一的API响应结果包装器 提供统一的成功/失败状态和错误处理 */
sealed class ApiResult<out T> {
    data class Success<T>(val data: T) : ApiResult<T>()

    data class Error(val code: Int, val message: String?, val exception: Throwable? = null) :
        ApiResult<Nothing>()
}

/** 将异常转换为ApiResult */
fun <T> Exception.toApiResult(): ApiResult<T> {
    EasyLog.log("API exception: ${this.message}", EasyLog.ERROR)
    return ApiResult.Error(code = -1, message = this.message ?: "Unknown error", exception = this)
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
