package com.ai.core.http

import com.ai.core.data.bean.HttpResult
import io.ktor.client.call.body
import io.ktor.client.plugins.HttpRequestTimeoutException
import io.ktor.client.statement.HttpResponse
import io.ktor.serialization.JsonConvertException
import java.io.IOException
import kotlinx.serialization.SerializationException

object HttpErrorHandler {
    fun toUserMessage(t: Throwable, operation: String = "operation"): String {
        return when (t) {
            is HttpRequestTimeoutException -> "Request timeout, please try again later"
            is IOException -> "Network connection failed, please check your connection"
            is JsonConvertException, is SerializationException -> "Data format error, please try again later"
            else -> {
                val errorMessage = t.message ?: "Unknown error"
                if (errorMessage.contains(operation, ignoreCase = true)) errorMessage
                else "${operation} failed: $errorMessage"
            }
        }
    }

    suspend fun <T : Any> parseHttpResultOrFailure(response: HttpResponse): HttpResult<T> {
        return try {
            response.body()
        } catch (t: Throwable) {
            HttpResult.Failure(toUserMessage(t, "parse response"), response.status.value)
        }
    }
}

