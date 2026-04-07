package com.ai.core.data.bean

import kotlinx.serialization.Serializable

@Serializable
data class HttpResult<T : Any>(
    val code: Int = 200,
    val message: String = "success",
    val data: T? = null,
) {
    enum class ErrorCode(val value: Int) {
        EmptyResponse(-111)
    }
}
