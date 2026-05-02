package com.inty.imate.chat.data.datasource

import com.ai.core.http.di.KtorHttpClientSingleton
import com.ai.core.utils.LogUtils
import com.inty.imate.chat.data.bean.ChatClientContextWsMessage
import com.inty.imate.chat.data.bean.ChatUserSignedOnWsMessage
import com.inty.imate.chat.data.bean.ChatWebSocketReq
import com.inty.imate.chat.data.bean.ChatWsControlFrame
import com.inty.imate.chat.data.bean.SendMsgReq
import com.inty.imate.chat.data.bean.SendMsgResponse
import com.inty.imate.chat.data.bean.UserTimeContext
import com.inty.imate.chat.data.bean.shouldDeferChatResponseParsing
import io.ktor.client.plugins.websocket.DefaultClientWebSocketSession
import io.ktor.client.plugins.websocket.webSocket
import io.ktor.client.request.url
import io.ktor.websocket.Frame
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter
import java.util.concurrent.atomic.AtomicReference
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.channelFlow
import kotlinx.coroutines.flow.retry
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.serialization.json.Json

private const val CHAT_WEBSOCKET_PATH = "api/v1/chat/ws"
/** Server closes the socket if no inbound text within `chat_ws_idle_timeout_seconds` (config min 10s). */
private const val PING_INTERVAL_MS = 9_000L
private const val WAIT_SESSION_STEP_MS = 50L
private const val WAIT_SESSION_TIMEOUT_MS = 30_000L

@Singleton
class ChatWebSocketRemoteDataSource
@Inject
constructor() {

    private val httpClient = KtorHttpClientSingleton.webSocketHttpClient
    private val currentSession = AtomicReference<DefaultClientWebSocketSession?>(null)
    private val sendMutex = Mutex()
    private val userSignedOnAgentIdForConnection = AtomicReference<String?>(null)

    private val _isSessionActive = MutableStateFlow(false)
    val isSessionActive: StateFlow<Boolean> = _isSessionActive.asStateFlow()

    private val json =
        Json {
            ignoreUnknownKeys = true
            isLenient = true
        }

    suspend fun sendMessageFireAndForget(agentId: String, request: SendMsgReq) {
        waitUntilSessionReadyOrThrow()
        sendMutex.withLock {
            val session =
                currentSession.get()
                    ?: throw IllegalStateException("Chat WebSocket not connected")
            if (userSignedOnAgentIdForConnection.get() != agentId) {
                session.send(
                    Frame.Text(
                        json.encodeToString(
                            ChatUserSignedOnWsMessage.serializer(),
                            ChatUserSignedOnWsMessage(agentId = agentId),
                        ),
                    ),
                )
                userSignedOnAgentIdForConnection.set(agentId)
            }
            val payload = ChatWebSocketReq(agentId = agentId, request = request)
            session.send(Frame.Text(json.encodeToString(ChatWebSocketReq.serializer(), payload)))
        }
    }

    private suspend fun waitUntilSessionReadyOrThrow() {
        val deadlineNs = System.nanoTime() + WAIT_SESSION_TIMEOUT_MS * 1_000_000L
        while (currentSession.get() == null) {
            if (System.nanoTime() >= deadlineNs) {
                throw IllegalStateException("Chat WebSocket not connected")
            }
            delay(WAIT_SESSION_STEP_MS)
        }
    }

    fun connectWebsocket() =
        channelFlow<SendMsgResponse> {
                httpClient.webSocket(
                    request = {
                        url(buildChatWebSocketUrl())
                    }
                ) {
                    val session = this
                    currentSession.set(session)
                    userSignedOnAgentIdForConnection.set(null)
                    _isSessionActive.value = true
                    try {
                        LogUtils.d("Chat WebSocket connected")
                        coroutineScope {
                            launch {
                                while (isActive) {
                                    session.send(Frame.Text("""{"type":"ping"}"""))
                                    delay(PING_INTERVAL_MS)
                                }
                            }
                            while (true) {
                                val frame = session.incoming.receive()
                                if (frame is Frame.Close) break
                                if (frame !is Frame.Text) continue
                                val text = frame.data.decodeToString()
                                LogUtils.d("websocket msg: $text")
                                val control =
                                    runCatching {
                                        json.decodeFromString(ChatWsControlFrame.serializer(), text)
                                    }.getOrNull()
                                if (control.shouldDeferChatResponseParsing()) {
                                    continue
                                }
                                val response =
                                    runCatching { json.decodeFromString(SendMsgResponse.serializer(), text) }
                                        .getOrNull()
                                if (response != null) {
                                    send(response)
                                } else {
                                    LogUtils.d("Chat WebSocket: skip non-chat frame: ${text.take(200)}")
                                }
                            }
                        }
                    } finally {
                        currentSession.set(null)
                        userSignedOnAgentIdForConnection.set(null)
                        _isSessionActive.value = false
                    }
                }
            }
            .retry {
                LogUtils.d("Chat WebSocket disconnected, retry in 5s: ${it.message}")
                delay(5000L)
                true
            }

    private fun buildChatWebSocketUrl(): String {
        val httpBase = KtorHttpClientSingleton.httpBaseUrlTrimmed()
        val websocketBase =
            when {
                httpBase.startsWith("https://") -> "wss://${httpBase.removePrefix("https://")}"
                httpBase.startsWith("http://") -> "ws://${httpBase.removePrefix("http://")}"
                else -> httpBase
            }
        return "$websocketBase/$CHAT_WEBSOCKET_PATH"
    }

    companion object {
        fun buildUserTimeContextOrNull(): UserTimeContext? {
            val now = ZonedDateTime.now()
            val utcOffsetMinutes = now.offset.totalSeconds / 60
            return UserTimeContext(
                localTime = now.format(DateTimeFormatter.ISO_OFFSET_DATE_TIME),
                timezone = now.zone.id,
                utcOffsetMinutes = utcOffsetMinutes,
            )
        }
    }
}
