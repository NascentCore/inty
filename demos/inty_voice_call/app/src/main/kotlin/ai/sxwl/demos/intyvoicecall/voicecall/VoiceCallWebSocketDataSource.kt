package ai.sxwl.demos.intyvoicecall.voicecall

import io.ktor.client.HttpClient
import io.ktor.client.plugins.websocket.DefaultClientWebSocketSession
import io.ktor.client.plugins.websocket.receiveDeserialized
import io.ktor.client.plugins.websocket.sendSerialized
import io.ktor.client.plugins.websocket.webSocketSession
import io.ktor.client.request.headers
import io.ktor.client.request.url
import io.ktor.http.HttpHeaders
import io.ktor.websocket.close
import kotlinx.coroutines.channels.ClosedReceiveChannelException
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.onCompletion
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

class VoiceCallWebSocketDataSource(private val httpClient: HttpClient) {
    private var _session: DefaultClientWebSocketSession? = null
    private val sessionMutex = Mutex()

    private val _connectionState = MutableStateFlow(VoiceCallConnectionState.DISCONNECTED)
    val connectionState: StateFlow<VoiceCallConnectionState> = _connectionState.asStateFlow()

    private var closedByClient = false

    suspend fun connect(wsUrl: String, bearerToken: String): Flow<CallPacket> {
        close()

        closedByClient = false
        _connectionState.value = VoiceCallConnectionState.CONNECTING

        return flow {
                val session =
                    httpClient.webSocketSession {
                        url(wsUrl)
                        headers { append(HttpHeaders.Authorization, "Bearer $bearerToken") }
                    }

                sessionMutex.withLock { _session = session }
                _connectionState.value = VoiceCallConnectionState.CONNECTED
                while (true) {
                    emit(session.receiveDeserialized<CallPacket>())
                }
            }
            .catch { error -> if (error !is ClosedReceiveChannelException) throw error }
            .onCompletion { cause ->
                if (closedByClient) {
                    _connectionState.value = VoiceCallConnectionState.DISCONNECTED
                } else if (cause != null) {
                    _connectionState.value = VoiceCallConnectionState.ERROR
                } else {
                    _connectionState.value = VoiceCallConnectionState.DISCONNECTED
                }
            }
    }

    suspend fun sendPacket(packet: CallPacket) {
        val session = sessionMutex.withLock { _session }
        if (session == null) {
            throw IllegalStateException("WebSocket connection not established")
        }

        if (_connectionState.value != VoiceCallConnectionState.CONNECTED) {
            throw IllegalStateException(
                "WebSocket connection state is ${_connectionState.value}, cannot send"
            )
        }

        session.sendSerialized(packet)
    }

    suspend fun close() {
        closedByClient = true
        _connectionState.value = VoiceCallConnectionState.DISCONNECTING

        val session =
            sessionMutex.withLock {
                val current = _session
                _session = null
                current
            }

        session?.close()

        _connectionState.value = VoiceCallConnectionState.DISCONNECTED
    }
}
