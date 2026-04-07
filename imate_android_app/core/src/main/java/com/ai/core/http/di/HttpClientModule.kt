package com.ai.core.http.di

import com.ai.core.http.ktor.ChatImageTimeoutPlugin
import com.ai.core.http.okhttp.UnifiedOkHttpClientFactory
import io.ktor.client.HttpClient
import io.ktor.client.engine.okhttp.OkHttp
import io.ktor.client.plugins.DefaultRequest
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.http.ContentType
import io.ktor.http.contentType
import io.ktor.serialization.kotlinx.json.json
import kotlinx.serialization.json.Json

object KtorHttpClientSingleton {
    private const val BASE_URL = "https://dev.ops.inty.cc/"

    @Volatile
    private var bearerTokenProvider: () -> String? = { null }

    fun setBearerTokenProvider(provider: () -> String?) {
        bearerTokenProvider = provider
    }

    private val json: Json =
        Json {
            ignoreUnknownKeys = true
            isLenient = true
            encodeDefaults = false
        }

    private val dynamicBearerTokenProvider: () -> String? = { bearerTokenProvider() }

    val httpClient: HttpClient by lazy {
        HttpClient(OkHttp) {
            engine {
                preconfigured = UnifiedOkHttpClientFactory.create(dynamicBearerTokenProvider)
            }
            install(ContentNegotiation) { json(json) }
            install(ChatImageTimeoutPlugin)
            install(DefaultRequest) {
                contentType(ContentType.Application.Json)
                url(BASE_URL)
            }
        }
    }
}
