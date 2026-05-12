package com.inty.imate.voicecall

import android.util.Base64
import com.ai.core.http.di.KtorHttpClientSingleton
import com.ai.core.utils.LogUtils
import io.ktor.client.plugins.websocket.webSocket
import io.ktor.client.request.url
import io.ktor.websocket.Frame
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.serialization.encodeToString

class VoiceCallClient {
    private val json = KtorHttpClientSingleton.ktorHttpJson
    private val httpClient = KtorHttpClientSingleton.webSocketHttpClient
    private val _connectionState = MutableStateFlow(VoiceCallConnectionState.DISCONNECTED)
    val connectionState = _connectionState.asStateFlow()

    private var session: io.ktor.client.plugins.websocket.DefaultClientWebSocketSession? = null

    fun packets(agentId: String): Flow<VoiceCallPacket> =
        callbackFlow {
            _connectionState.value = VoiceCallConnectionState.CONNECTING
            try {
                httpClient.webSocket(request = { url(buildUrl(agentId)) }) {
                    session = this
                    _connectionState.value = VoiceCallConnectionState.CONNECTED
                    try {
                        for (frame in incoming) {
                            if (frame !is Frame.Text) continue
                            val packet =
                                runCatching {
                                        json.decodeFromString(
                                            VoiceCallPacket.serializer(),
                                            frame.data.decodeToString(),
                                        )
                                    }
                                    .getOrNull()
                            if (packet != null) trySend(packet)
                        }
                    } finally {
                        session = null
                        _connectionState.value = VoiceCallConnectionState.DISCONNECTED
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("Voice call WebSocket failed: ${e.message}")
                _connectionState.value = VoiceCallConnectionState.ERROR
                close(e)
            }
            awaitClose { close() }
        }

    suspend fun sendAudioPcm16k(data: ByteArray) {
        val s = session ?: return
        val packet =
            VoiceCallPacket(
                type = VoiceCallPacketType.AUDIO,
                data = Base64.encodeToString(data, Base64.NO_WRAP),
            )
        s.send(Frame.Text(json.encodeToString(packet)))
    }

    suspend fun end() {
        session?.send(Frame.Text("""{"type":"end"}"""))
        close()
    }

    fun close() {
        runCatching { session = null }
        _connectionState.value = VoiceCallConnectionState.DISCONNECTED
    }

    private fun buildUrl(agentId: String): String {
        val httpBase = KtorHttpClientSingleton.httpBaseUrlTrimmed()
        val websocketBase =
            when {
                httpBase.startsWith("https://") -> "wss://${httpBase.removePrefix("https://")}"
                httpBase.startsWith("http://") -> "ws://${httpBase.removePrefix("http://")}"
                else -> httpBase
            }
        return "$websocketBase/api/v1/live-chat/$agentId?agent_starts_conversation=true"
    }
}
