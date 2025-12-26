package com.ai.intellimate.call.data

import ai.sxwl.android.data.http.UnifiedOkHttpClient
import io.ktor.client.HttpClient
import io.ktor.client.engine.okhttp.OkHttp
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.plugins.websocket.WebSockets
import io.ktor.serialization.kotlinx.KotlinxWebsocketSerializationConverter
import io.ktor.serialization.kotlinx.json.json
import kotlinx.serialization.json.Json

/**
 * Ktor HttpClient工厂 基于UnifiedOkHttpClient创建Ktor HttpClient，复用统一的网络配置和拦截器
 * 使用单例模式，确保整个应用只创建一个HttpClient实例
 */
object KtorHttpClientFactory {

    @Volatile private var instance: HttpClient? = null

    /**
     * 获取Ktor HttpClient单例实例 使用OkHttp引擎，复用UnifiedOkHttpClient的配置
     *
     * @return HttpClient单例实例
     */
    fun getInstance(): HttpClient {
        return instance
            ?: synchronized(this) { instance ?: createHttpClient().also { instance = it } }
    }

    /** 创建Ktor HttpClient实例 使用OkHttp引擎，复用UnifiedOkHttpClient的配置 */
    private fun createHttpClient(): HttpClient {
        return HttpClient(OkHttp) {
            // 使用统一的OkHttpClient，复用所有拦截器和配置
            engine { preconfigured = UnifiedOkHttpClient.create() }

            // 安装内容协商插件，支持JSON序列化
            install(ContentNegotiation) {
                json(
                    Json {
                        ignoreUnknownKeys = true
                        isLenient = true
                        encodeDefaults = false
                    }
                )
            }

            // 安装WebSocket插件
            install(WebSockets) {
                // WebSocket相关配置可以在这里添加
                contentConverter =
                    KotlinxWebsocketSerializationConverter(
                        Json {
                            ignoreUnknownKeys = true
                            isLenient = true
                            encodeDefaults = false
                        }
                    )
            }
        }
    }

    /**
     * 创建新的HttpClient实例（不推荐使用，除非有特殊需求） 建议使用getInstance()获取单例
     *
     * @deprecated 使用getInstance()替代，以复用单例实例
     */
    @Deprecated("使用getInstance()替代，以复用单例实例", ReplaceWith("getInstance()"))
    fun create(): HttpClient {
        return createHttpClient()
    }
}
