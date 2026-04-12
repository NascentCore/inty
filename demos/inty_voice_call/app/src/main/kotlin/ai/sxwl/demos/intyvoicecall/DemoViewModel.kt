package ai.sxwl.demos.intyvoicecall

import android.app.Application
import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioRecord
import android.media.AudioTrack
import android.media.MediaRecorder
import android.util.Base64
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import ai.sxwl.demos.intyvoicecall.voicecall.CallType
import ai.sxwl.demos.intyvoicecall.voicecall.IntyVoiceCallClient
import ai.sxwl.demos.intyvoicecall.voicecall.IntyVoiceCallUrls
import ai.sxwl.demos.intyvoicecall.voicecall.VoiceCallConnectionState
import ai.sxwl.demos.intyvoicecall.voicecall.VoiceCallWebSocketDataSource
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.launch

data class DemoUiState(
    val apiEndpoint: String = "",
    val apiKey: String = "",
    val agentId: String = "",
    val speechLanguageCode: String = "en-US",
    val responseLanguageName: String = "English",
    val statusLine: String = "",
    val logTail: String = "",
    val liveChatEnabled: Boolean? = null,
    val sendSampleRate: Int? = null,
    val receiveSampleRate: Int? = null,
    val inCall: Boolean = false,
    val micPermissionGranted: Boolean = false,
)

class DemoViewModel(application: Application) : AndroidViewModel(application) {
    private val httpClient = createIntyDemoHttpClient()
    private val dataSource = VoiceCallWebSocketDataSource(httpClient)
    private val voiceClient = IntyVoiceCallClient(dataSource)

    var ui by mutableStateOf(DemoUiState())
        private set

    private var receiveJob: Job? = null
    private var micJob: Job? = null
    private var audioRecord: AudioRecord? = null
    private var audioTrack: AudioTrack? = null

    fun updateEndpoint(v: String) {
        ui = ui.copy(apiEndpoint = v)
    }

    fun updateApiKey(v: String) {
        ui = ui.copy(apiKey = v)
    }

    fun updateAgentId(v: String) {
        ui = ui.copy(agentId = v)
    }

    fun updateSpeechLanguage(v: String) {
        ui = ui.copy(speechLanguageCode = v)
    }

    fun updateResponseLanguage(v: String) {
        ui = ui.copy(responseLanguageName = v)
    }

    fun setMicPermissionGranted(granted: Boolean) {
        ui = ui.copy(micPermissionGranted = granted)
    }

    fun appendLog(line: String) {
        val next = (ui.logTail + line + "\n").lines().takeLast(40).joinToString("\n") + "\n"
        ui = ui.copy(logTail = next)
    }

    fun checkStatus() {
        viewModelScope.launch {
            try {
                val base = ui.apiEndpoint.trim()
                val token = ui.apiKey.trim()
                if (base.isEmpty() || token.isEmpty()) {
                    ui = ui.copy(statusLine = "Fill API endpoint and API key")
                    return@launch
                }
                val data = fetchLiveChatStatus(httpClient, base, token)
                ui =
                    ui.copy(
                        statusLine =
                            "live-chat enabled=${data.enabled} sendHz=${data.sendSampleRate} recvHz=${data.receiveSampleRate}",
                        liveChatEnabled = data.enabled,
                        sendSampleRate = data.sendSampleRate,
                        receiveSampleRate = data.receiveSampleRate,
                    )
            } catch (e: Throwable) {
                ui = ui.copy(statusLine = "status error: ${e.message}")
            }
        }
    }

    fun startCall() {
        if (ui.inCall) return
        val base = ui.apiEndpoint.trim()
        val token = ui.apiKey.trim()
        val agent = ui.agentId.trim()
        if (base.isEmpty() || token.isEmpty() || agent.isEmpty()) {
            ui = ui.copy(statusLine = "Fill endpoint, API key, agent id")
            return
        }
        if (!ui.micPermissionGranted) {
            ui = ui.copy(statusLine = "Grant RECORD_AUDIO permission")
            return
        }

        receiveJob?.cancel()
        receiveJob =
            viewModelScope.launch {
                try {
                    val status = fetchLiveChatStatus(httpClient, base, token)
                    if (!status.enabled) {
                        ui = ui.copy(statusLine = "Live chat disabled on server (enabled=false)")
                        return@launch
                    }
                    val sendRate = status.sendSampleRate
                    val recvRate = status.receiveSampleRate
                    ui =
                        ui.copy(
                            sendSampleRate = sendRate,
                            receiveSampleRate = recvRate,
                            inCall = true,
                            statusLine = "Connecting WebSocket...",
                        )

                    val wssBase = httpsToWssBase(base)
                    val wsUrl =
                        IntyVoiceCallUrls.liveChatWebSocketUrl(
                            wssBase,
                            agent,
                            speechLanguageCode = ui.speechLanguageCode.trim().ifEmpty { null },
                            responseLanguageName = ui.responseLanguageName.trim().ifEmpty { null },
                        )

                    appendLog("WS $wsUrl")

                    ensureAudioTrack(recvRate)

                    var micStarted = false
                    voiceClient
                        .packets(wsUrl, token)
                        .catch { e ->
                            appendLog("flow error: ${e.message}")
                            throw e
                        }
                        .collect { packet ->
                            if (!micStarted) {
                                micStarted = true
                                startMic(sendRate)
                            }
                            when (packet.typeEnum) {
                                CallType.AUDIO_RESPONSE -> {
                                    val pcm = Base64.decode(packet.data, Base64.NO_WRAP)
                                    val rate =
                                        if (packet.sampleRate > 0) packet.sampleRate else recvRate
                                    playPcm(pcm, rate)
                                }
                                CallType.SESSION_INFO -> {
                                    appendLog(
                                        "session_info remaining=${packet.remainingDuration}s agents=${packet.agentCount}/${packet.agentLimit}"
                                    )
                                }
                                CallType.STATUS -> appendLog("status ${packet.status} ${packet.message}")
                                CallType.ERROR ->
                                    appendLog("error ${packet.errorCode} ${packet.message}")
                                CallType.TRANSCRIPT,
                                CallType.USER_TRANSCRIPT ->
                                    appendLog(
                                        "${packet.typeEnum.name.lowercase()} final=${packet.isFinal} ${packet.text}"
                                    )
                                else -> {}
                            }
                        }
                } catch (e: Throwable) {
                    ui = ui.copy(statusLine = "call error: ${e.message}")
                    appendLog("call error: ${e.message}")
                } finally {
                    stopMicInternal()
                    audioTrack?.stop()
                    audioTrack?.release()
                    audioTrack = null
                    voiceClient.close()
                    ui = ui.copy(inCall = false, statusLine = "Disconnected")
                }
            }
    }

    fun stopCall() {
        receiveJob?.cancel()
        receiveJob = null
    }

    override fun onCleared() {
        stopCall()
        httpClient.close()
        super.onCleared()
    }

    private fun httpsToWssBase(httpsBase: String): String {
        val t = httpsBase.trim()
        return when {
            t.startsWith("https://", ignoreCase = true) -> "wss://" + t.drop(8)
            t.startsWith("http://", ignoreCase = true) -> "ws://" + t.drop(7)
            else -> throw IllegalArgumentException("API endpoint must start with https:// or http://")
        }
    }

    private fun ensureAudioTrack(sampleRate: Int) {
        audioTrack?.release()
        val min =
            AudioTrack.getMinBufferSize(
                sampleRate,
                AudioFormat.CHANNEL_OUT_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
            )
        if (min <= 0) {
            throw IllegalStateException("AudioTrack min buffer: $min")
        }
        val track =
            AudioTrack(
                AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_VOICE_COMMUNICATION)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                    .build(),
                AudioFormat.Builder()
                    .setSampleRate(sampleRate)
                    .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                    .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                    .build(),
                min * 2,
                AudioTrack.MODE_STREAM,
                AudioManager.AUDIO_SESSION_ID_GENERATE,
            )
        track.play()
        audioTrack = track
    }

    private fun playPcm(bytes: ByteArray, sampleRate: Int) {
        if (bytes.isEmpty()) return
        val t = audioTrack
        if (t == null || t.sampleRate != sampleRate) {
            ensureAudioTrack(sampleRate)
        }
        audioTrack?.write(bytes, 0, bytes.size, AudioTrack.WRITE_BLOCKING)
    }

    private fun startMic(sampleRate: Int) {
        stopMicInternal()
        val min =
            AudioRecord.getMinBufferSize(
                sampleRate,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
            )
        if (min <= 0) {
            throw IllegalStateException("AudioRecord min buffer: $min")
        }
        val r =
            AudioRecord(
                MediaRecorder.AudioSource.VOICE_COMMUNICATION,
                sampleRate,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
                min * 2,
            )
        if (r.state != AudioRecord.STATE_INITIALIZED) {
            r.release()
            throw IllegalStateException("AudioRecord init failed")
        }
        audioRecord = r
        r.startRecording()
        val frameBytes = (sampleRate / 50) * 2
        micJob =
            viewModelScope.launch(Dispatchers.IO) {
                val buf = ByteArray(frameBytes)
                while (true) {
                    val n = r.read(buf, 0, buf.size)
                    if (n <= 0) break
                    val chunk = if (n == buf.size) buf.copyOf() else buf.copyOf(n)
                    voiceClient.sendVoicePcmBase64(chunk)
                }
            }
    }

    private fun stopMicInternal() {
        micJob?.cancel()
        micJob = null
        audioRecord?.let {
            try {
                it.stop()
            } catch (_: IllegalStateException) {}
            it.release()
        }
        audioRecord = null
    }
}
