package ai.sxwl.demos.intyvoicecall.voicecall

import android.util.Base64
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.flow

class IntyVoiceCallClient(private val dataSource: VoiceCallWebSocketDataSource) {
    fun packets(wsUrl: String, bearerToken: String): Flow<CallPacket> {
        return flow {
            dataSource.connect(wsUrl, bearerToken).collect { packet -> emit(packet) }
        }
    }

    suspend fun sendPacket(packet: CallPacket) {
        dataSource.sendPacket(packet)
    }

    suspend fun sendVoicePcmBase64(audio: ByteArray) {
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
        dataSource.close()
    }

    fun connectionState(): StateFlow<VoiceCallConnectionState> = dataSource.connectionState
}
