package com.ai.core.http.di

import android.util.Log
import com.ai.core.BuildConfig
import com.ai.core.http.ktor.ChatImageTimeoutPlugin
import com.ai.core.http.okhttp.UnifiedOkHttpClientFactory
import okhttp3.OkHttpClient
import io.ktor.client.HttpClient
import io.ktor.client.engine.okhttp.OkHttp
import io.ktor.client.plugins.DefaultRequest
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.plugins.logging.LogLevel
import io.ktor.client.plugins.logging.Logger
import io.ktor.client.plugins.logging.Logging
import io.ktor.client.plugins.websocket.WebSockets
import io.ktor.http.ContentType
import io.ktor.http.HttpHeaders
import io.ktor.http.contentType
import io.ktor.serialization.kotlinx.json.json
import kotlinx.serialization.json.Json

object KtorHttpClientSingleton {
    private const val BASE_URL = "https://dev.ops.inty.cc/"
    private const val LOG_TAG = "KtorHttp"

    private val debugNetworkLogger =
        object : Logger {
            override fun log(message: String) {
                Log.d(LOG_TAG, message)
            }
        }

    @Volatile
    private var bearerTokenProvider: () -> String? = { null }

    fun setBearerTokenProvider(provider: () -> String?) {
        bearerTokenProvider = provider
    }

    val ktorHttpJson: Json =
        Json {
            ignoreUnknownKeys = true
            isLenient = true
            encodeDefaults = false
            coerceInputValues = true
        }

    private val dynamicBearerTokenProvider: () -> String? = { bearerTokenProvider() }

    val httpClient: HttpClient by lazy {
        HttpClient(OkHttp) {
            engine {
                preconfigured = UnifiedOkHttpClientFactory.create(dynamicBearerTokenProvider)
            }
            if (BuildConfig.DEBUG) {
                install(Logging) {
                    logger = debugNetworkLogger
                    level = LogLevel.ALL
                    sanitizeHeader { name -> name.equals(HttpHeaders.Authorization, ignoreCase = true) }
                }
            }
            install(WebSockets)
            install(ContentNegotiation) { json(ktorHttpJson) }
            install(ChatImageTimeoutPlugin)
            install(DefaultRequest) {
                contentType(ContentType.Application.Json)
                url(BASE_URL)
            }
        }
    }

    /** Long-lived chat WS: no read idle cap + OkHttp ping frames; do not reuse [httpClient] (30s read). */
    val webSocketHttpClient: HttpClient by lazy {
        HttpClient(OkHttp) {
            engine {
                preconfigured =
                    UnifiedOkHttpClientFactory.createForLongLivedWebSocket(dynamicBearerTokenProvider)
            }
            if (BuildConfig.DEBUG) {
                install(Logging) {
                    logger = debugNetworkLogger
                    level = LogLevel.HEADERS
                    sanitizeHeader { name -> name.equals(HttpHeaders.Authorization, ignoreCase = true) }
                }
            }
            install(WebSockets)
        }
    }

    fun httpBaseUrlTrimmed(): String = BASE_URL.trimEnd('/')

    /** 与 [httpClient] 相同鉴权，用于 multipart 等不适合走 DefaultRequest JSON 的请求。 */
    fun authenticatedOkHttp(): OkHttpClient =
        UnifiedOkHttpClientFactory.create { bearerTokenProvider() }
}
