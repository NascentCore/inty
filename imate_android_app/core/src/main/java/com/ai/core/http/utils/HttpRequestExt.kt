package com.ai.core.http.utils

import com.ai.core.data.bean.HttpResult
import com.ai.core.data.exceptions.IntyException
import com.ai.core.http.HttpErrorHandler
import com.ai.core.http.di.KtorHttpClientSingleton
import io.ktor.client.request.HttpRequestBuilder
import io.ktor.client.request.get
import io.ktor.client.request.post
import io.ktor.client.request.put
import io.ktor.client.statement.HttpResponse

@PublishedApi
internal fun <T : Any> unwrapHttpResultOrThrow(result: HttpResult<T>): T {
    if (result.code != 200) {
        throw IntyException(result.code, result.message)
    }
    return result.data ?: throw IllegalStateException("Empty response")
}

@PublishedApi
internal suspend inline fun <reified T : Any> parseHttpResult(
    response: HttpResponse
): HttpResult<T> =
    HttpErrorHandler.parseHttpResultOrFailure(response, KtorHttpClientSingleton.ktorHttpJson)

suspend inline fun <reified T : Any> post(
    url: String,
    noinline block: HttpRequestBuilder.() -> Unit = {},
): T {
    val response = KtorHttpClientSingleton.httpClient.post(url, block)
    val result = HttpErrorHandler.parseHttpResultOrFailure<T>(response, KtorHttpClientSingleton.ktorHttpJson)
    return unwrapHttpResultOrThrow(result)
}

suspend inline fun <reified T : Any> get(
    url: String,
    noinline block: HttpRequestBuilder.() -> Unit = {},
): T {
    val response = KtorHttpClientSingleton.httpClient.get(url, block)
    val result = HttpErrorHandler.parseHttpResultOrFailure<T>(response, KtorHttpClientSingleton.ktorHttpJson)
    return unwrapHttpResultOrThrow(result)
}

suspend inline fun <reified T : Any> put(
    url: String,
    noinline block: HttpRequestBuilder.() -> Unit = {},
): T {
    val response = KtorHttpClientSingleton.httpClient.put(url, block)
    val result = HttpErrorHandler.parseHttpResultOrFailure<T>(response, KtorHttpClientSingleton.ktorHttpJson)
    return unwrapHttpResultOrThrow(result)
}

suspend inline fun <reified T : Any> getRaw(
    url: String,
    noinline block: HttpRequestBuilder.() -> Unit = {},
): T {
    val response = KtorHttpClientSingleton.httpClient.get(url, block)
    val result = HttpErrorHandler.parseRawBodyOrFailure<T>(response, KtorHttpClientSingleton.ktorHttpJson)
    return unwrapHttpResultOrThrow(result)
}

suspend inline fun <reified T : Any> postRaw(
    url: String,
    noinline block: HttpRequestBuilder.() -> Unit = {},
): T {
    val response = KtorHttpClientSingleton.httpClient.post(url, block)
    val result = HttpErrorHandler.parseRawBodyOrFailure<T>(response, KtorHttpClientSingleton.ktorHttpJson)
    return unwrapHttpResultOrThrow(result)
}

suspend inline fun <reified T : Any> putRaw(
    url: String,
    noinline block: HttpRequestBuilder.() -> Unit = {},
): T {
    val response = KtorHttpClientSingleton.httpClient.put(url, block)
    val result = HttpErrorHandler.parseRawBodyOrFailure<T>(response, KtorHttpClientSingleton.ktorHttpJson)
    return unwrapHttpResultOrThrow(result)
}
