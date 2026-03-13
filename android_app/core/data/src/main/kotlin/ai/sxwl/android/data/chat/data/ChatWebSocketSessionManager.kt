package ai.sxwl.android.data.chat.data

import ai.sxwl.android.data.api.model.ChatWebSocketReq
import ai.sxwl.android.data.api.model.ChatWebSocketStreamFrame
import ai.sxwl.android.data.api.model.SendMsgReq
import ai.sxwl.android.data.api.model.SendMsgResponse
import ai.sxwl.android.data.http.UnifiedOkHttpClient
import ai.sxwl.android.data.http.config.NetworkConfig
import ai.sxwl.android.data.store.IntySetting
import com.architecture.httplib.core.HttpResult
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import io.ktor.client.HttpClient
import io.ktor.client.engine.okhttp.OkHttp
import io.ktor.client.plugins.websocket.DefaultClientWebSocketSession
import io.ktor.client.plugins.websocket.WebSockets
import io.ktor.client.plugins.websocket.webSocketSession
import io.ktor.client.request.header
import io.ktor.client.request.url
import io.ktor.websocket.Frame
import io.ktor.websocket.close
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

private const val CHAT_WEBSOCKET_PATH = "api/v1/chat/ws"

/** 复用单条聊天 WebSocket 连接，支持不同 agent 的消息复用同一个 session。 */
object ChatWebSocketSessionManager {
    private val connectionMutex = Mutex()
    private val requestMutex = Mutex()
    private var session: DefaultClientWebSocketSession? = null
    private var sessionToken: String? = null

    private val httpClient by lazy {
        HttpClient(OkHttp) {
            engine { preconfigured = UnifiedOkHttpClient.create() }
            install(WebSockets)
        }
    }

    private val moshi = Moshi.Builder().addLast(KotlinJsonAdapterFactory()).build()
    private val requestAdapter = moshi.adapter(ChatWebSocketReq::class.java)
    private val responseAdapter = moshi.adapter(SendMsgResponse::class.java)
    private val streamFrameAdapter = moshi.adapter(ChatWebSocketStreamFrame::class.java)

    suspend fun sendMessage(
        agentId: String,
        request: SendMsgReq,
        onStreamingDelta: (suspend (String) -> Unit)? = null,
    ): HttpResult<SendMsgResponse> {
        return try {
            // AI implementation summary:
            // 1) 复用单连接并串行处理请求；2) 支持 stream.start/stream.delta/stream.final 帧；
            // 3) 兼容旧单帧响应，统一返回 SendMsgResponse。
            requestMutex.withLock {
                val activeSession = ensureSession()
                val websocketPayload = ChatWebSocketReq(agentId = agentId, request = request)
                activeSession.send(Frame.Text(requestAdapter.toJson(websocketPayload)))
                while (true) {
                    val frame = activeSession.incoming.receive()
                    if (frame !is Frame.Text) {
                        return@withLock HttpResult.Failure("Unexpected websocket frame type", -1)
                    }
                    val payloadText = frame.data.decodeToString()
                    val streamFrame = streamFrameAdapter.fromJson(payloadText)
                    if (streamFrame == null) {
                        val legacyPayload = responseAdapter.fromJson(payloadText)
                        if (legacyPayload == null) {
                            return@withLock HttpResult.Failure(
                                "Invalid websocket response body",
                                -1,
                            )
                        }
                        return@withLock HttpResult.Success(legacyPayload)
                    }

                    if (
                        streamFrame.type == null &&
                            (streamFrame.code != null ||
                                streamFrame.message != null ||
                                streamFrame.data != null)
                    ) {
                        return@withLock HttpResult.Success(
                            SendMsgResponse(
                                code = streamFrame.code,
                                message = streamFrame.message,
                                data = streamFrame.data,
                            )
                        )
                    }

                    when (streamFrame.type) {
                        "stream.start" -> {
                            continue
                        }
                        "stream.delta" -> {
                            val delta = streamFrame.delta
                            if (!delta.isNullOrEmpty() && onStreamingDelta != null) {
                                onStreamingDelta(delta)
                            }
                        }
                        "stream.final" -> {
                            val finalResponse =
                                streamFrame.response
                                    ?: SendMsgResponse(
                                        code = streamFrame.code,
                                        message = streamFrame.message,
                                        data = streamFrame.data,
                                    )
                            return@withLock HttpResult.Success(finalResponse)
                        }
                        else -> {
                            val fallbackPayload = responseAdapter.fromJson(payloadText)
                            if (fallbackPayload != null) {
                                return@withLock HttpResult.Success(fallbackPayload)
                            }
                            return@withLock HttpResult.Failure(
                                "Unknown websocket response frame type",
                                -1,
                            )
                        }
                    }
                }
            }
        } catch (e: Exception) {
            closeSession()
            HttpResult.Failure(e.message ?: "WebSocket chat request failed", -1)
        }
    }

    suspend fun closeSession() {
        connectionMutex.withLock { closeSessionLocked() }
    }

    private suspend fun ensureSession(): DefaultClientWebSocketSession {
        val token = IntySetting.getCurToken()
        return connectionMutex.withLock {
            val existing = session
            if (existing != null && sessionToken == token) {
                return@withLock existing
            }
            closeSessionLocked()
            val newSession =
                httpClient.webSocketSession {
                    url(buildChatWebSocketUrl())
                    if (token.isNotBlank()) {
                        header("Authorization", "Bearer $token")
                    }
                }
            session = newSession
            sessionToken = token
            newSession
        }
    }

    private suspend fun closeSessionLocked() {
        session?.close()
        session = null
        sessionToken = null
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
