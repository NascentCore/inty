package ai.sxwl.android.data.chat.data

import ai.sxwl.android.data.api.model.ChatWebSocketReq
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

    suspend fun sendMessage(agentId: String, request: SendMsgReq): HttpResult<SendMsgResponse> {
        return try {
            // AI implementation summary:
            // 1) 按 token 维度复用单连接；2) 每次请求按顺序发送并等待单条响应；
            // 3) 解析成与 HTTP 相同的 SendMsgResponse，保持上层逻辑不变。
            requestMutex.withLock {
                val activeSession = ensureSession()
                val websocketPayload = ChatWebSocketReq(agentId = agentId, request = request)
                activeSession.send(Frame.Text(requestAdapter.toJson(websocketPayload)))

                val frame = activeSession.incoming.receive()
                val result: HttpResult<SendMsgResponse> =
                    if (frame !is Frame.Text) {
                        HttpResult.Failure("Unexpected websocket frame type", -1)
                    } else {
                        val payload = responseAdapter.fromJson(frame.data.decodeToString())
                        if (payload == null) {
                            HttpResult.Failure("Invalid websocket response body", -1)
                        } else {
                            HttpResult.Success(payload)
                        }
                    }
                result
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
