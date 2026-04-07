package com.ai.core.data.bean

sealed class HttpResult<out T : Any> {

    enum class ErrorCode(val value: Int) {
        EmptyResponse(-111)
    }

    // 200-300 就是Success，body 就是业务上真实的成功时候需要的数据
    data class Success<T : Any>(val data: T) : HttpResult<T>()

    // 各种失败，异常全部到这里来吧
    data class Failure(val message: String, val code: Int) : HttpResult<Nothing>()
}
