package com.ai.core.http.utils

import com.ai.core.data.bean.HttpResult
import com.ai.core.data.exceptions.IntyException
import com.ai.core.http.HttpErrorHandler
import com.ai.core.http.di.KtorHttpClientSingleton
import io.ktor.client.plugins.HttpRequestTimeoutException
import io.ktor.client.request.HttpRequestBuilder
import io.ktor.client.request.get
import io.ktor.client.request.post
import io.ktor.client.request.put
import io.ktor.client.statement.HttpResponse

@PublishedApi
internal fun Throwable.toIntyException(operation: String, code: Int = -1): IntyException {
    val msg = HttpErrorHandler.toUserMessage(this, operation)
    return IntyException(code, msg)
}

@PublishedApi
internal fun <T : Any> unwrapHttpResultOrThrow(result: HttpResult<T>): T {
    if (result.code != 200) {
        throw IntyException(result.code, result.message)
    }
    return result.data ?: throw IntyException(HttpResult.ErrorCode.EmptyResponse.value, "Empty response")
}

@PublishedApi
internal suspend inline fun <reified T : Any> parseHttpResult(
    response: HttpResponse
): HttpResult<T> = HttpErrorHandler.parseHttpResultOrFailure(response)

suspend inline fun <reified T : Any> post(
    url: String,
    noinline block: HttpRequestBuilder.() -> Unit = {},
): T {
    try {
        val response = KtorHttpClientSingleton.httpClient.post(url, block)
        val result: HttpResult<T> = parseHttpResult(response)
        return unwrapHttpResultOrThrow(result)
    } catch (t: HttpRequestTimeoutException) {
        throw t.toIntyException("post $url")
    } catch (t: Throwable) {
        throw t.toIntyException("post $url")
    }
}

suspend inline fun <reified T : Any> get(
    url: String,
    noinline block: HttpRequestBuilder.() -> Unit = {},
): T {
    try {
        val response = KtorHttpClientSingleton.httpClient.get(url, block)
        val result: HttpResult<T> = parseHttpResult(response)
        return unwrapHttpResultOrThrow(result)
    } catch (t: HttpRequestTimeoutException) {
        throw t.toIntyException("get $url")
    } catch (t: Throwable) {
        throw t.toIntyException("get $url")
    }
}

suspend inline fun <reified T : Any> put(
    url: String,
    noinline block: HttpRequestBuilder.() -> Unit = {},
): T {
    try {
        val response = KtorHttpClientSingleton.httpClient.put(url, block)
        val result: HttpResult<T> = parseHttpResult(response)
        return unwrapHttpResultOrThrow(result)
    } catch (t: HttpRequestTimeoutException) {
        throw t.toIntyException("put $url")
    } catch (t: Throwable) {
        throw t.toIntyException("put $url")
    }
}
