package com.inty.imate.voicecall

import android.Manifest
import android.annotation.SuppressLint
import android.content.pm.PackageManager
import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.AudioTrack
import android.media.MediaRecorder
import androidx.core.content.ContextCompat
import com.ai.core.utils.Utils
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

class VoiceCallAudio {
    private var record: AudioRecord? = null
    private var track: AudioTrack? = null
    private var recordJob: Job? = null

    @SuppressLint("MissingPermission")
    fun startRecording(scope: CoroutineScope, onPcm16k: suspend (ByteArray) -> Unit) {
        if (
            ContextCompat.checkSelfPermission(Utils.getApp(), Manifest.permission.RECORD_AUDIO) !=
                PackageManager.PERMISSION_GRANTED
        ) {
            return
        }
        val minBuffer =
            AudioRecord.getMinBufferSize(
                16000,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
            )
        val bufferSize = minBuffer.coerceAtLeast(3200)
        val recorder =
            AudioRecord(
                MediaRecorder.AudioSource.VOICE_COMMUNICATION,
                16000,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
                bufferSize,
            )
        record = recorder
        recorder.startRecording()
        recordJob =
            scope.launch(Dispatchers.IO) {
                val buffer = ByteArray(bufferSize)
                while (isActive) {
                    val read = recorder.read(buffer, 0, buffer.size)
                    if (read > 0) onPcm16k(buffer.copyOf(read))
                }
            }
    }

    fun playPcm24k(data: ByteArray) {
        val player =
            track
                ?: AudioTrack.Builder()
                    .setAudioAttributes(
                        AudioAttributes.Builder()
                            .setUsage(AudioAttributes.USAGE_VOICE_COMMUNICATION)
                            .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                            .build()
                    )
                    .setAudioFormat(
                        AudioFormat.Builder()
                            .setSampleRate(24000)
                            .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                            .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                            .build()
                    )
                    .setBufferSizeInBytes(
                        AudioTrack.getMinBufferSize(
                            24000,
                            AudioFormat.CHANNEL_OUT_MONO,
                            AudioFormat.ENCODING_PCM_16BIT,
                        ).coerceAtLeast(4800)
                    )
                    .setTransferMode(AudioTrack.MODE_STREAM)
                    .build()
                    .also {
                        track = it
                        it.play()
                    }
        player.write(data, 0, data.size)
    }

    fun stop() {
        recordJob?.cancel()
        recordJob = null
        runCatching { record?.stop() }
        runCatching { record?.release() }
        record = null
        runCatching { track?.stop() }
        runCatching { track?.release() }
        track = null
    }
}
