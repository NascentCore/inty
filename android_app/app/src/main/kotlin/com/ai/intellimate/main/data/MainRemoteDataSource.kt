package com.ai.intellimate.main.data

import ai.sxwl.android.data.api.model.ChatClientContextWsMessage
import ai.sxwl.android.data.api.model.ChatWebSocketReq
import ai.sxwl.android.data.api.model.ChatWsControlFrame
import ai.sxwl.android.data.api.model.SendMsgReq
import ai.sxwl.android.data.api.model.SendMsgResponse
import ai.sxwl.android.data.api.model.shouldDeferChatResponseParsing
import ai.sxwl.android.data.chat.data.ChatRemoteDataSource
import ai.sxwl.android.data.di.HttpClientProvider
import ai.sxwl.android.data.http.config.DebugBackendEndpointStore
import ai.sxwl.android.data.http.config.NetworkConfig
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.utils.LogUtils
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import io.ktor.client.HttpClient
import io.ktor.client.plugins.websocket.DefaultClientWebSocketSession
import io.ktor.client.plugins.websocket.webSocket
import io.ktor.client.request.header
import io.ktor.client.request.url
import io.ktor.websocket.Frame
import java.util.concurrent.atomic.AtomicReference
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.channelFlow
import kotlinx.coroutines.flow.retry
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

private const val CHAT_WEBSOCKET_PATH = "api/v1/chat/ws"
private const val CHAT_WEBSOCKET_VERIFY_PATH = "api/v1/chat/ws/verify"
private const val PING_INTERVAL_MS = 25_000L

/**
 * 主 WebSocket 数据源单例，保证接收（connectWebsocket）与发送（sendMessageFireAndForget）共用同一连接（`/api/v1/chat/ws`，见后端 `app/api/ENDPOINTS.md`）。
 */
object MainRemoteDataSource {
    private val httpClient: HttpClient = HttpClientProvider.ktorClient
    private val currentSession = AtomicReference<DefaultClientWebSocketSession?>(null)
    private val moshi = Moshi.Builder().addLast(KotlinJsonAdapterFactory()).build()
    private val requestAdapter = moshi.adapter(ChatWebSocketReq::class.java)
    private val responseAdapter = moshi.adapter(SendMsgResponse::class.java)
    private val controlFrameAdapter = moshi.adapter(ChatWsControlFrame::class.java)
    private val clientContextAdapter = moshi.adapter(ChatClientContextWsMessage::class.java)

    /** 通过主 WebSocket 发送消息，不等待响应（fire-and-forget）。参数与 ChatWebSocketSessionManager 一致。 */
    suspend fun sendMessageFireAndForget(agentId: String, request: SendMsgReq) {
        val session =
            currentSession.get() ?: throw IllegalStateException("Main WebSocket not connected")
        val payload = ChatWebSocketReq(agentId = agentId, request = request)
        session.send(Frame.Text(requestAdapter.toJson(payload)))
    }

    fun connectWebsocket() =
        channelFlow<SendMsgResponse> {
                httpClient.webSocket(
                    request = {
                        url(buildChatWebSocketUrl())
                        val token = IntySetting.getCurToken()

                        if (token.isNotBlank()) {
                            header("Authorization", "Bearer $token")
                        }
                    }
                ) {
                    val session = this
                    currentSession.set(session)
                    try {
                        LogUtils.d("Main WebSocket已连接")
                        ChatRemoteDataSource.buildUserTimeContextOrNull()?.let { utc ->
                            val payload = ChatClientContextWsMessage(timeContext = utc)
                            session.send(Frame.Text(clientContextAdapter.toJson(payload)))
                        }
                        coroutineScope {
                            launch {
                                while (isActive) {
                                    delay(PING_INTERVAL_MS)
                                    session.send(Frame.Text("""{"type":"ping"}"""))
                                }
                            }
                            while (true) {
                                val frame = session.incoming.receive()
                                if (frame is Frame.Close) break
                                if (frame !is Frame.Text) continue
                                val text = frame.data.decodeToString()
                                val control =
                                    kotlin
                                        .runCatching { controlFrameAdapter.fromJson(text) }
                                        .getOrNull()
                                if (control.shouldDeferChatResponseParsing()) {
                                    continue
                                }
                                val response =
                                    kotlin
                                        .runCatching { responseAdapter.fromJson(text) }
                                        .getOrNull()
                                if (response != null) {
                                    send(response)
                                } else {
                                    LogUtils.w("Main WebSocket: 无法解析为聊天响应，已忽略: ${text.take(200)}")
                                }
                            }
                        }
                    } finally {
                        currentSession.set(null)
                    }
                }
            }
            .retry {
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
        val path =
            if (DebugBackendEndpointStore.getChatWebSocketUseVerifyPath())
                CHAT_WEBSOCKET_VERIFY_PATH
            else CHAT_WEBSOCKET_PATH
        return "$websocketBase/$path"
    }
}
