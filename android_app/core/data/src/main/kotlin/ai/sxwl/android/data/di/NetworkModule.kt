package ai.sxwl.android.data.di

import ai.sxwl.android.data.http.UnifiedOkHttpClient
import io.ktor.client.HttpClient
import io.ktor.client.engine.okhttp.OkHttp
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.plugins.websocket.WebSockets
import io.ktor.serialization.kotlinx.KotlinxWebsocketSerializationConverter
import io.ktor.serialization.kotlinx.json.json
import kotlinx.serialization.json.Json
import org.koin.dsl.module

/**
 * 网络模块
 *
 * 提供：
 * - Ktor HttpClient：支持Http和WebSocket
 */
val networkModule = module { single<HttpClient> { provideHttpClient() } }

/** 创建Ktor HttpClient */
private fun provideHttpClient(): HttpClient {
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
