package com.ai.core.http

import com.ai.core.data.bean.HttpResult
import io.ktor.client.plugins.HttpRequestTimeoutException
import io.ktor.client.statement.HttpResponse
import io.ktor.client.statement.bodyAsText
import io.ktor.serialization.JsonConvertException
import java.io.IOException
import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.serializer

@PublishedApi
internal fun looksLikeHttpResultEnvelope(root: JsonElement): Boolean {
    val obj = root as? JsonObject ?: return false
    if (!obj.containsKey("data")) return false
    return obj.containsKey("code") || obj.containsKey("message")
}

object HttpErrorHandler {
    fun toUserMessage(t: Throwable, operation: String = "operation"): String {
        t.printStackTrace()
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

    suspend inline fun <reified T : Any> parseHttpResultOrFailure(
        response: HttpResponse,
        json: Json,
    ): HttpResult<T> {
        if (response.status.value !in 200..299) {
            val message = try {
                response.bodyAsText()
            } catch (t: Throwable) {
                toUserMessage(t, "read error response")
            }
            return HttpResult(code = response.status.value, message = message)
        }
        val text = try {
            response.bodyAsText()
        } catch (t: Throwable) {
            return HttpResult(code = response.status.value, message = toUserMessage(t, "read response"))
        }
        return try {
            val root = json.parseToJsonElement(text)
            if (looksLikeHttpResultEnvelope(root)) {
                json.decodeFromString(serializer<HttpResult<T>>(), text)
            } else {
                val data: T = json.decodeFromString(serializer<T>(), text)
                HttpResult(code = 200, message = "success", data = data)
            }
        } catch (t: Throwable) {
            HttpResult(code = response.status.value, message = toUserMessage(t, "parse response"))
        }
    }

    suspend inline fun <reified T : Any> parseRawBodyOrFailure(
        response: HttpResponse,
        json: Json,
    ): HttpResult<T> {
        if (response.status.value !in 200..299) {
            val message = try {
                response.bodyAsText()
            } catch (t: Throwable) {
                toUserMessage(t, "read error response")
            }
            return HttpResult(code = response.status.value, message = message)
        }
        val text = try {
            response.bodyAsText()
        } catch (t: Throwable) {
            return HttpResult(code = response.status.value, message = toUserMessage(t, "read response"))
        }
        return try {
            val data: T = json.decodeFromString(serializer<T>(), text)
            HttpResult(code = 200, message = "success", data = data)
        } catch (t: Throwable) {
            HttpResult(code = response.status.value, message = toUserMessage(t, "parse response"))
        }
    }
}

