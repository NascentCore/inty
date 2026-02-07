package com.ai.intellimate.audio

import ai.sxwl.android.utils.LogUtils
import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioTrack
import android.os.Build
import com.ai.intellimate.ui.UiConfigs
import java.util.concurrent.LinkedBlockingQueue
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** 实时音频流播放管理器 使用AudioTrack实时播放PCM数据流，支持流式播放 */
class AudioStreamPlayer private constructor() {

    companion object {
        @Volatile private var INSTANCE: AudioStreamPlayer? = null

        fun getInstance(): AudioStreamPlayer {
            return INSTANCE
                ?: synchronized(this) { INSTANCE ?: AudioStreamPlayer().also { INSTANCE = it } }
        }
    }

    // 播放状态
    private val _playbackState = MutableStateFlow<PlaybackState>(PlaybackState.IDLE)
    val playbackState: StateFlow<PlaybackState> = _playbackState.asStateFlow()

    /** 是否仍有待播数据（队列非空）。用于 UI 在音频播完前保持「speaking」状态。 */
    private val _hasPendingPlaybackData = MutableStateFlow(false)
    val hasPendingPlaybackData: StateFlow<Boolean> = _hasPendingPlaybackData.asStateFlow()

    // 错误信息
    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()

    // AudioTrack实例
    private var audioTrack: AudioTrack? = null

    // 播放协程
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var playbackJob: Job? = null

    // 音频数据队列 - 使用有界队列避免内存溢出
    private val audioDataQueue =
        LinkedBlockingQueue<ByteArray>(UiConfigs.VoiceCall.MAX_PLAYBACK_QUEUE_SIZE)

    // 音频参数
    private var audioParams: AudioParams? = null

    // 日志节流：记录上次打印警告的时间
    private var lastWarningLogTime = 0L
    private val warningLogInterval = 5000L // 5秒内最多打印一次警告

    // 缓冲区倍数 - 增大缓冲区以减少卡顿
    private val bufferSizeMultiplier = 8

    // 预填充阈值 - 在开始播放前需要填充的最小数据量（字节）
    private var prefillThreshold = 0

    /** 初始化AudioTrack */
    private fun initializeAudioTrack(params: AudioParams): Boolean {
        return try {
            audioParams = params

            // 计算缓冲区大小
            val bufferSize =
                AudioTrack.getMinBufferSize(
                    params.sampleRate,
                    params.channelConfig,
                    params.audioFormat,
                )

            if (bufferSize == AudioTrack.ERROR_BAD_VALUE || bufferSize == AudioTrack.ERROR) {
                LogUtils.e("无法获取有效的缓冲区大小")
                _error.value = "无法初始化音频播放器：无效的缓冲区大小"
                return false
            }

            // 计算实际缓冲区大小（使用更大的倍数以减少卡顿）
            val actualBufferSize = bufferSize * bufferSizeMultiplier
            // 预填充阈值设为缓冲区大小的 50%，确保有足够数据才开始播放
            prefillThreshold = actualBufferSize / 2

            // 创建AudioTrack实例
            audioTrack =
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                    AudioTrack.Builder()
                        .setAudioAttributes(
                            AudioAttributes.Builder()
                                .setUsage(AudioAttributes.USAGE_MEDIA)
                                .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                                .build()
                        )
                        .setAudioFormat(
                            AudioFormat.Builder()
                                .setSampleRate(params.sampleRate)
                                .setEncoding(params.audioFormat)
                                .setChannelMask(params.channelConfig)
                                .build()
                        )
                        .setBufferSizeInBytes(actualBufferSize)
                        .setTransferMode(AudioTrack.MODE_STREAM)
                        .build()
                } else {
                    @Suppress("DEPRECATION")
                    AudioTrack(
                        AudioManager.STREAM_MUSIC,
                        params.sampleRate,
                        params.channelConfig,
                        params.audioFormat,
                        actualBufferSize,
                        AudioTrack.MODE_STREAM,
                    )
                }

            if (audioTrack?.state != AudioTrack.STATE_INITIALIZED) {
                LogUtils.e("AudioTrack初始化失败")
                _error.value = "无法初始化音频播放器"
                releaseAudioTrack()
                return false
            }

            LogUtils.d(
                "AudioTrack初始化成功，缓冲区大小: $actualBufferSize (最小: $bufferSize, 倍数: $bufferSizeMultiplier)"
            )
            true
        } catch (e: Exception) {
            LogUtils.e("初始化AudioTrack异常: ${e.message}")
            _error.value = "初始化音频播放器失败: ${e.message}"
            releaseAudioTrack()
            false
        }
    }

    /**
     * 开始播放
     *
     * @param params 音频参数（需要与录制参数一致）
     */
    fun startPlayback(params: AudioParams) {
        if (_playbackState.value == PlaybackState.PLAYING) {
            LogUtils.w("已经在播放中")
            return
        }

        // 如果参数变化或未初始化，重新初始化
        if (audioTrack == null || audioParams != params) {
            if (!initializeAudioTrack(params)) {
                _playbackState.value = PlaybackState.ERROR
                return
            }
        }

        val track =
            audioTrack
                ?: run {
                    _error.value = "音频播放器未初始化"
                    _playbackState.value = PlaybackState.ERROR
                    return
                }

        // 清空队列
        audioDataQueue.clear()
        _hasPendingPlaybackData.value = false
        _error.value = null
        _playbackState.value = PlaybackState.PLAYING

        // 启动播放协程
        playbackJob =
            scope.launch {
                try {
                    // 预填充缓冲区：在开始播放前先填充一些数据，避免启动时卡顿
                    var prefillBytes = 0
                    val prefillStartTime = System.currentTimeMillis()
                    val prefillTimeout = 2000L // 预填充超时时间 2 秒

                    while (
                        prefillBytes < prefillThreshold &&
                            isActive &&
                            _playbackState.value == PlaybackState.PLAYING &&
                            (System.currentTimeMillis() - prefillStartTime) < prefillTimeout
                    ) {
                        try {
                            // 使用 poll 非阻塞方式获取数据，避免长时间等待
                            val audioData =
                                audioDataQueue.poll(100, java.util.concurrent.TimeUnit.MILLISECONDS)
                            if (audioData != null) {
                                val bytesWritten = writeAudioDataWithRetry(track, audioData)
                                if (bytesWritten > 0) {
                                    prefillBytes += bytesWritten
                                }
                            }
                        } catch (e: InterruptedException) {
                            break
                        } catch (e: Exception) {
                            LogUtils.w("预填充音频数据异常: ${e.message}")
                            break
                        }
                    }

                    if (prefillBytes > 0) {
                        LogUtils.d("预填充完成，已填充: $prefillBytes 字节")
                    }

                    // 开始播放
                    track.play()
                    LogUtils.d("开始播放音频流")

                    // 主播放循环：持续从队列中读取并播放音频数据
                    while (isActive && _playbackState.value == PlaybackState.PLAYING) {
                        try {
                            // 从队列中获取音频数据（阻塞等待，但设置超时以避免永久阻塞）
                            val audioData =
                                audioDataQueue.poll(100, java.util.concurrent.TimeUnit.MILLISECONDS)
                            if (audioData != null) {
                                // 使用重试机制写入音频数据
                                writeAudioDataWithRetry(track, audioData)
                            } else {
                                if (audioDataQueue.isEmpty()) {
                                    _hasPendingPlaybackData.value = false
                                }
                                // 队列为空时，检查 AudioTrack 状态，确保播放不中断
                                // 如果 AudioTrack 还有数据在播放，继续循环等待新数据
                                if (track.playState != AudioTrack.PLAYSTATE_PLAYING) {
                                    LogUtils.w("AudioTrack 播放状态异常，停止播放")
                                    break
                                }
                            }
                        } catch (e: InterruptedException) {
                            // 队列poll被中断，正常退出
                            break
                        } catch (e: Exception) {
                            LogUtils.e("播放音频异常: ${e.message}")
                            _error.value = "播放失败: ${e.message}"
                            withContext(Dispatchers.Main) {
                                _playbackState.value = PlaybackState.ERROR
                            }
                            break
                        }
                    }
                } catch (e: Exception) {
                    LogUtils.e("播放音频流异常: ${e.message}")
                    _error.value = "播放失败: ${e.message}"
                    withContext(Dispatchers.Main) { _playbackState.value = PlaybackState.ERROR }
                } finally {
                    try {
                        if (track.playState == AudioTrack.PLAYSTATE_PLAYING) {
                            track.stop()
                        }
                    } catch (e: Exception) {
                        LogUtils.e("停止播放异常: ${e.message}")
                    }
                }
            }
    }

    /**
     * 写入音频数据到 AudioTrack，支持部分写入重试
     *
     * @param track AudioTrack 实例
     * @param audioData 要写入的音频数据
     * @return 实际写入的字节数
     */
    private suspend fun writeAudioDataWithRetry(track: AudioTrack, audioData: ByteArray): Int {
        var offset = 0
        var totalWritten = 0
        val maxRetries = 3
        var retryCount = 0

        while (
            offset < audioData.size &&
                retryCount < maxRetries &&
                _playbackState.value == PlaybackState.PLAYING
        ) {
            try {
                val remaining = audioData.size - offset
                val bytesWritten = track.write(audioData, offset, remaining)

                when {
                    bytesWritten == AudioTrack.ERROR_INVALID_OPERATION -> {
                        LogUtils.e("写入音频数据失败：无效操作")
                        return totalWritten
                    }
                    bytesWritten == AudioTrack.ERROR_BAD_VALUE -> {
                        LogUtils.e("写入音频数据失败：无效值")
                        return totalWritten
                    }
                    bytesWritten < 0 -> {
                        LogUtils.e("写入音频数据失败：错误码 $bytesWritten")
                        retryCount++
                        if (retryCount < maxRetries) {
                            kotlinx.coroutines.delay(10) // 短暂延迟后重试
                        }
                    }
                    bytesWritten == 0 -> {
                        // 缓冲区可能已满，短暂等待后重试
                        retryCount++
                        if (retryCount < maxRetries) {
                            kotlinx.coroutines.delay(5)
                        }
                    }
                    bytesWritten < remaining -> {
                        // 部分写入，继续写入剩余数据
                        offset += bytesWritten
                        totalWritten += bytesWritten
                        retryCount = 0 // 重置重试计数
                    }
                    else -> {
                        // 完全写入
                        offset += bytesWritten
                        totalWritten += bytesWritten
                        retryCount = 0
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("写入音频数据异常: ${e.message}")
                retryCount++
                if (retryCount < maxRetries) {
                    kotlinx.coroutines.delay(10)
                } else {
                    break
                }
            }
        }

        if (offset < audioData.size) {
            LogUtils.w("音频数据未完全写入，期望: ${audioData.size}, 实际: $totalWritten")
        }

        return totalWritten
    }

    /**
     * 添加音频数据到播放队列 优化：使用 offer 非阻塞方式，避免阻塞主线程
     *
     * @param audioData PCM格式的音频数据
     */
    fun addAudioData(audioData: ByteArray) {
        if (_playbackState.value == PlaybackState.PLAYING) {
            try {
                _hasPendingPlaybackData.value = true
                // 如果队列已满，丢弃最旧的数据以保持实时性
                if (!audioDataQueue.offer(audioData)) {
                    // offer 失败说明队列已满，移除最旧的数据
                    val dropped = audioDataQueue.poll()
                    if (dropped != null) {
                        LogUtils.w("播放队列已满，丢弃旧音频数据包，大小: ${dropped.size} bytes")
                    }
                    // 再次尝试添加
                    if (!audioDataQueue.offer(audioData)) {
                        LogUtils.w("添加音频数据失败，队列可能已满")
                    }
                }

                // 监控队列大小，超过警告阈值时记录日志（带节流）
                val queueSize = audioDataQueue.size
                val queueUsage = queueSize.toFloat() / UiConfigs.VoiceCall.MAX_PLAYBACK_QUEUE_SIZE
                val currentTime = System.currentTimeMillis()
                if (
                    queueUsage >= UiConfigs.VoiceCall.QUEUE_WARNING_THRESHOLD &&
                        (currentTime - lastWarningLogTime) >= warningLogInterval
                ) {
                    LogUtils.w(
                        "播放队列使用率较高: ${(queueUsage * 100).toInt()}% ($queueSize/${UiConfigs.VoiceCall.MAX_PLAYBACK_QUEUE_SIZE})"
                    )
                    lastWarningLogTime = currentTime
                }
            } catch (e: Exception) {
                LogUtils.e("添加音频数据到队列失败: ${e.message}")
            }
        }
    }

    /** 停止播放 */
    fun stopPlayback() {
        if (_playbackState.value != PlaybackState.PLAYING) {
            return
        }

        _playbackState.value = PlaybackState.IDLE
        _hasPendingPlaybackData.value = false
        playbackJob?.cancel()
        playbackJob = null

        // 清空队列
        audioDataQueue.clear()

        try {
            audioTrack?.stop()
            LogUtils.d("停止播放音频")
        } catch (e: Exception) {
            LogUtils.e("停止播放异常: ${e.message}")
        }
    }

    /**
     * 打断当前播放并重启播放通道。
     *
     * 使用场景：语音通话中用户点击“打断 AI”按钮，需要立即清空缓冲并继续接收后续音频。
     */
    fun interruptPlayback() {
        val params = audioParams ?: return
        if (_playbackState.value != PlaybackState.PLAYING) {
            return
        }
        stopPlayback()
        releaseAudioTrack()
        startPlayback(params)
    }

    /** 暂停播放 */
    fun pausePlayback() {
        if (_playbackState.value == PlaybackState.PLAYING) {
            _playbackState.value = PlaybackState.PAUSED
            playbackJob?.cancel()
            playbackJob = null
            try {
                audioTrack?.pause()
            } catch (e: Exception) {
                LogUtils.e("暂停播放异常: ${e.message}")
            }
        }
    }

    /** 恢复播放 */
    fun resumePlayback() {
        if (_playbackState.value == PlaybackState.PAUSED && audioParams != null) {
            startPlayback(audioParams!!)
        }
    }

    /** 释放AudioTrack资源 */
    private fun releaseAudioTrack() {
        try {
            audioTrack?.release()
            audioTrack = null
        } catch (e: Exception) {
            LogUtils.e("释放AudioTrack异常: ${e.message}")
        }
    }

    /** 释放所有资源 */
    fun release() {
        stopPlayback()
        releaseAudioTrack()
        scope.cancel()
    }
}
