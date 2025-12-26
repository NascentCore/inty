package com.ai.intellimate.audio

import ai.sxwl.android.utils.LogUtils
import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import androidx.annotation.RequiresPermission
import androidx.core.content.ContextCompat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * 录制状态
 */
enum class RecordingState {
    IDLE,      // 空闲
    RECORDING, // 录制中
    PAUSED,    // 暂停
    ERROR      // 错误
}

/**
 * 音频录制管理器
 * 使用AudioRecord录制PCM格式音频，支持实时流式读取
 */
class AudioRecordManager private constructor(private val context: Context) {

    companion object {
        @Volatile
        private var INSTANCE: AudioRecordManager? = null

        fun getInstance(context: Context): AudioRecordManager {
            return INSTANCE
                ?: synchronized(this) {
                    INSTANCE ?: AudioRecordManager(context.applicationContext).also { INSTANCE = it }
                }
        }

        // 音频参数配置
        private const val SAMPLE_RATE = 16000 // 16kHz采样率，适合语音
        private const val CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO // 单声道
        private const val AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT // 16位PCM
        private const val AUDIO_SOURCE = MediaRecorder.AudioSource.VOICE_COMMUNICATION // 语音通话源
    }

    // 录制状态
    private val _recordingState = MutableStateFlow<RecordingState>(RecordingState.IDLE)
    val recordingState: StateFlow<RecordingState> = _recordingState.asStateFlow()

    // 错误信息
    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()

    // AudioRecord实例
    private var audioRecord: AudioRecord? = null

    // 录制协程
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var recordingJob: Job? = null

    // 音频数据回调
    private var onAudioDataCallback: ((ByteArray) -> Unit)? = null

    // 缓冲区大小
    private var bufferSize = 0

    /**
     * 检查录音权限
     */
    fun hasPermission(): Boolean {
        return ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.RECORD_AUDIO
        ) == PackageManager.PERMISSION_GRANTED
    }

    /**
     * 初始化AudioRecord
     */
    @RequiresPermission(Manifest.permission.RECORD_AUDIO)
    private fun initializeAudioRecord(): Boolean {
        return try {
            // 计算缓冲区大小
            bufferSize = AudioRecord.getMinBufferSize(
                SAMPLE_RATE,
                CHANNEL_CONFIG,
                AUDIO_FORMAT
            )

            if (bufferSize == AudioRecord.ERROR_BAD_VALUE || bufferSize == AudioRecord.ERROR) {
                LogUtils.e("无法获取有效的缓冲区大小")
                _error.value = "无法初始化音频录制器：无效的缓冲区大小"
                return false
            }

            // 创建AudioRecord实例
            audioRecord = AudioRecord(
                AUDIO_SOURCE,
                SAMPLE_RATE,
                CHANNEL_CONFIG,
                AUDIO_FORMAT,
                bufferSize * 2 // 使用2倍缓冲区大小以确保稳定
            )

            if (audioRecord?.state != AudioRecord.STATE_INITIALIZED) {
                LogUtils.e("AudioRecord初始化失败")
                _error.value = "无法初始化音频录制器"
                releaseAudioRecord()
                return false
            }

            LogUtils.d("AudioRecord初始化成功，缓冲区大小: ${bufferSize * 2}")
            true
        } catch (e: Exception) {
            LogUtils.e("初始化AudioRecord异常: ${e.message}")
            _error.value = "初始化音频录制器失败: ${e.message}"
            releaseAudioRecord()
            false
        }
    }

    /**
     * 开始录制
     * @param onAudioData 音频数据回调，每次读取到数据时调用
     */
    @RequiresPermission(Manifest.permission.RECORD_AUDIO)
    fun startRecording(onAudioData: (ByteArray) -> Unit) {
        if (!hasPermission()) {
            LogUtils.e("没有录音权限")
            _error.value = "没有录音权限"
            _recordingState.value = RecordingState.ERROR
            return
        }

        if (_recordingState.value == RecordingState.RECORDING) {
            LogUtils.w("已经在录制中")
            return
        }

        // 初始化AudioRecord
        if (audioRecord == null && !initializeAudioRecord()) {
            _recordingState.value = RecordingState.ERROR
            return
        }

        val record = audioRecord ?: run {
            _error.value = "音频录制器未初始化"
            _recordingState.value = RecordingState.ERROR
            return
        }

        onAudioDataCallback = onAudioData
        _error.value = null
        _recordingState.value = RecordingState.RECORDING

        // 启动录制协程
        recordingJob = scope.launch {
            try {
                record.startRecording()
                LogUtils.d("开始录制音频")

                val buffer = ByteArray(bufferSize)

                while (isActive && _recordingState.value == RecordingState.RECORDING) {
                    val bytesRead = record.read(buffer, 0, buffer.size)

                    when {
                        bytesRead == AudioRecord.ERROR_INVALID_OPERATION -> {
                            LogUtils.e("读取音频数据失败：无效操作")
                            break
                        }
                        bytesRead == AudioRecord.ERROR_BAD_VALUE -> {
                            LogUtils.e("读取音频数据失败：无效值")
                            break
                        }
                        bytesRead > 0 -> {
                            // 复制实际读取的数据
                            val audioData = ByteArray(bytesRead)
                            buffer.copyInto(audioData, 0, 0, bytesRead)
                            // 回调音频数据
                            onAudioDataCallback?.invoke(audioData)
                        }
                        bytesRead == 0 -> {
                            // 没有数据，短暂等待
                            delay(10)
                        }
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("录制音频异常: ${e.message}")
                _error.value = "录制失败: ${e.message}"
                withContext(Dispatchers.Main) {
                    _recordingState.value = RecordingState.ERROR
                }
            } finally {
                try {
                    if (record.recordingState == AudioRecord.RECORDSTATE_RECORDING) {
                        record.stop()
                    }
                } catch (e: Exception) {
                    LogUtils.e("停止录制异常: ${e.message}")
                }
            }
        }
    }

    /**
     * 停止录制
     */
    fun stopRecording() {
        if (_recordingState.value != RecordingState.RECORDING) {
            return
        }

        _recordingState.value = RecordingState.IDLE
        recordingJob?.cancel()
        recordingJob = null
        onAudioDataCallback = null

        try {
            audioRecord?.stop()
            LogUtils.d("停止录制音频")
        } catch (e: Exception) {
            LogUtils.e("停止录制异常: ${e.message}")
        }
    }

    /**
     * 暂停录制
     */
    fun pauseRecording() {
        if (_recordingState.value == RecordingState.RECORDING) {
            _recordingState.value = RecordingState.PAUSED
            recordingJob?.cancel()
            recordingJob = null
            try {
                audioRecord?.stop()
            } catch (e: Exception) {
                LogUtils.e("暂停录制异常: ${e.message}")
            }
        }
    }

    /**
     * 恢复录制
     */
    @RequiresPermission(Manifest.permission.RECORD_AUDIO)
    fun resumeRecording(onAudioData: (ByteArray) -> Unit) {
        if (_recordingState.value == RecordingState.PAUSED) {
            startRecording(onAudioData)
        }
    }

    /**
     * 释放AudioRecord资源
     */
    private fun releaseAudioRecord() {
        try {
            audioRecord?.release()
            audioRecord = null
        } catch (e: Exception) {
            LogUtils.e("释放AudioRecord异常: ${e.message}")
        }
    }

    /**
     * 释放所有资源
     */
    fun release() {
        stopRecording()
        releaseAudioRecord()
        scope.cancel()
    }

    /**
     * 获取音频参数（供播放器使用）
     */
    fun getAudioParams(): AudioParams {
        return AudioParams(
            sampleRate = SAMPLE_RATE,
            channelConfig = CHANNEL_CONFIG,
            audioFormat = AUDIO_FORMAT
        )
    }
}

/**
 * 音频参数
 */
data class AudioParams(
    val sampleRate: Int,
    val channelConfig: Int,
    val audioFormat: Int
)

