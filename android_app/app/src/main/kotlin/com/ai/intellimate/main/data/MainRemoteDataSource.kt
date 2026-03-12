package com.ai.intellimate.main.data

import ai.sxwl.android.data.api.model.SendMsgResponse
import ai.sxwl.android.data.di.HttpClientProvider
import ai.sxwl.android.data.http.config.NetworkConfig
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.utils.LogUtils
import io.ktor.client.HttpClient
import io.ktor.client.plugins.websocket.receiveDeserialized
import io.ktor.client.plugins.websocket.webSocket
import io.ktor.client.request.header
import io.ktor.client.request.url
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.channelFlow
import kotlinx.coroutines.flow.retry

private const val CHAT_WEBSOCKET_PATH = "api/v1/chat/ws"

class MainRemoteDataSource(private val httpClient: HttpClient = HttpClientProvider.ktorClient) {
    fun connectWebsocket() = channelFlow<SendMsgResponse> {
        httpClient.webSocket(
            request = {
                url(buildChatWebSocketUrl())
                val token = IntySetting.getCurToken()

                if (token.isNotBlank()) {
                    header("Authorization", "Bearer $token")
                }
            }
        ) {
            LogUtils.d("Main WebSocket已连接")
            while (true) {
                val response = receiveDeserialized<SendMsgResponse>()

                send(response)
            }
        }
    }.retry {
        LogUtils.e("Main WebSocket连接断开，5s后重试:\n${it.message}")
        delay(5000L)
        true
    }

    private fun buildChatWebSocketUrl(): String {
        val httpBase = NetworkConfig.getBaseUrl().trimEnd('/')
        val websocketBase =
            when {
                httpBase.startsWith("https://") -> "wss://${httpBase.removePrefix("https://")}"
                httpBase.startsWith("http://") -> "ws://${httpBase.removePrefix("http://")}"
                else -> httpBase
            }
        return "$websocketBase/$CHAT_WEBSOCKET_PATH"
    }
}