package ai.sxwl.android.inty.voicecall

import android.util.Base64
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.retryWhen

class IntyVoiceCallClient(private val dataSource: VoiceCallWebSocketDataSource) {
    private var reconnectEnabled = true
    private val reconnectDelayMs = 2000L

    fun packets(url: String): Flow<CallPacket> {
        reconnectEnabled = true
        return flow { dataSource.connect(url).collect { packet -> emit(packet) } }
            .retryWhen { _, attempt ->
                if (!reconnectEnabled) {
                    false
                } else {
                    delay(attempt * reconnectDelayMs)
                    true
                }
            }
    }

    suspend fun sendPacket(packet: CallPacket) {
        dataSource.sendPacket(packet)
    }

    suspend fun sendVoicePcm16kBase64(audio: ByteArray) {
        val base64String = Base64.encodeToString(audio, Base64.NO_WRAP)
        val packet = CallPacket(CallType.AUDIO.name.lowercase(), base64String)
        dataSource.sendPacket(packet)
    }

    suspend fun sendActivityStart() {
        dataSource.sendPacket(CallPacket(CallType.ACTIVITY_START.name.lowercase()))
    }

    suspend fun sendActivityEnd() {
        dataSource.sendPacket(CallPacket(CallType.ACTIVITY_END.name.lowercase()))
    }

    suspend fun close() {
        reconnectEnabled = false
        dataSource.close()
    }

    fun connectionState(): StateFlow<VoiceCallConnectionState> = dataSource.connectionState
}
