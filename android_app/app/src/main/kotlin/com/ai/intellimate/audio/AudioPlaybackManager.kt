package com.ai.inty.audio

import ai.sxwl.android.utils.LogUtils
import android.content.Context
import android.media.AudioAttributes
import android.media.AudioFocusRequest
import android.media.AudioManager
import android.os.Build
import androidx.annotation.RequiresApi
import androidx.core.content.getSystemService
import androidx.media3.common.C
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.datasource.DefaultDataSource
import androidx.media3.datasource.okhttp.OkHttpDataSource
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.exoplayer.source.DefaultMediaSourceFactory
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import okhttp3.OkHttpClient
import java.util.concurrent.TimeUnit
import androidx.media3.common.AudioAttributes as Media3AudioAttributes

/** 企业级音频播放管理器 基于Media3实现，支持Opus格式，提供完整的音频焦点管理和播放控制 */
class AudioPlaybackManager private constructor(private val context: Context) : Player.Listener {

    companion object {
        @Volatile
        private var INSTANCE: AudioPlaybackManager? = null

        fun getInstance(context: Context): AudioPlaybackManager {
            return INSTANCE
                ?: synchronized(this) {
                    INSTANCE
                        ?: AudioPlaybackManager(context.applicationContext).also { INSTANCE = it }
                }
        }
    }

    // 播放器相关
    private var exoPlayer: ExoPlayer? = null
    private val audioManager = context.getSystemService<AudioManager>()
    private var audioFocusRequest: AudioFocusRequest? = null

    // 状态管理
    private val _playbackState = MutableStateFlow(PlaybackState.IDLE)
    val playbackState: StateFlow<PlaybackState> = _playbackState.asStateFlow()

    private val _currentPosition = MutableStateFlow(0L)
    val currentPosition: StateFlow<Long> = _currentPosition.asStateFlow()

    private val _duration = MutableStateFlow(0L)
    val duration: StateFlow<Long> = _duration.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()

    // 协程管理
    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())
    private var positionUpdateJob: Job? = null

    // 当前播放的音频信息
    private var currentAudioInfo: AudioInfo? = null

    // 缓存管理器
    private val cacheManager = AudioCacheManager.getInstance(context)

    init {
        initializePlayer()
    }

    /** 初始化ExoPlayer */
    private fun initializePlayer() {
        try {

            // 创建OkHttp数据源工厂，支持缓存
            val okHttpClient =
                OkHttpClient.Builder()
                    .connectTimeout(10, TimeUnit.SECONDS)
                    .readTimeout(30, TimeUnit.SECONDS)
                    .writeTimeout(30, TimeUnit.SECONDS)
                    .build()

            val dataSourceFactory =
                DefaultDataSource.Factory(context, OkHttpDataSource.Factory(okHttpClient))

            val mediaSourceFactory = DefaultMediaSourceFactory(dataSourceFactory)

            // 创建ExoPlayer实例 - 使用更简单的配置
            exoPlayer =
                ExoPlayer.Builder(context).setMediaSourceFactory(mediaSourceFactory).build().apply {
                    addListener(this@AudioPlaybackManager)
                    playWhenReady = false
                    // 设置音频属性
                    setAudioAttributes(
                        Media3AudioAttributes.Builder()
                            .setUsage(C.USAGE_MEDIA)
                            .setContentType(C.AUDIO_CONTENT_TYPE_SPEECH)
                            .build(),
                        false, // 手动处理音频焦点
                    )
                }
        } catch (e: Exception) {
            LogUtils.e("音频LOG测试 Failed to initialize AudioPlaybackManager: ${e.message}")
            _error.value = "播放器初始化失败: ${e.message}"
        }
    }

    /**
     * 播放音频
     *
     * @param audioInfo 音频信息
     * @param autoPlay 是否自动播放
     */
    fun playAudio(audioInfo: AudioInfo, autoPlay: Boolean = true) {
        try {
            // 检查是否是同一个音频（优先使用messageId判断）
            val isSameAudio = currentAudioInfo?.messageId == audioInfo.messageId

            if (isSameAudio && isPlaying()) {
                // 如果是同一个音频且正在播放，则暂停
                pausePlayback()
                return
            }

            // 停止当前播放（如果不是同一个音频）
            if (!isSameAudio) {
                stopPlayback()
            }

            // 请求音频焦点
            if (!requestAudioFocus()) {
                LogUtils.e("音频LOG测试 Failed to request audio focus")
                _error.value = "无法获取音频焦点"
                return
            }

            currentAudioInfo = audioInfo
            _isLoading.value = true
            _error.value = null

            // 设置媒体项 - 优先使用缓存文件
            val mediaItem =
                if (cacheManager.isCached(audioInfo.url)) {
                    val cachedPath = cacheManager.getCachedFilePath(audioInfo.url)
                    if (cachedPath != null) {
                        MediaItem.fromUri("file://$cachedPath")
                    } else {
                        MediaItem.fromUri(audioInfo.url)
                    }
                } else {
                    // 异步预加载音频到缓存
                    scope.launch {
                        try {
                            cacheManager.preloadAudio(audioInfo.url)
                        } catch (e: Exception) {
                            LogUtils.e("音频LOG测试 Failed to preload audio: ${e.message}")
                        }
                    }
                    MediaItem.fromUri(audioInfo.url)
                }

            exoPlayer?.setMediaItem(mediaItem)
            exoPlayer?.prepare()

            if (autoPlay) {
                exoPlayer?.play()
            }
        } catch (e: Exception) {
            LogUtils.e("音频LOG测试 Failed to play audio: ${e.message}")
            _error.value = "播放失败: ${e.message}"
            _isLoading.value = false
        }
    }

    /** 暂停播放 */
    fun pausePlayback() {
        try {
            exoPlayer?.pause()
            // 立即更新状态
            _playbackState.value = PlaybackState.PAUSED
            stopPositionUpdate()
        } catch (e: Exception) {
            LogUtils.e("音频LOG测试 Failed to pause playback: ${e.message}")
        }
    }

    /** 恢复播放 */
    fun resumePlayback() {
        try {
            // 检查当前状态是否允许恢复
            if (_playbackState.value != PlaybackState.PAUSED) {
                LogUtils.w("音频LOG测试 Cannot resume: current state is ${_playbackState.value}, expected PAUSED")
                return
            }

            // 直接恢复播放，不重新请求音频焦点
            // 因为音频焦点在初始播放时已经获得，暂停时不会释放
            exoPlayer?.play()

            // 立即更新状态
            _playbackState.value = PlaybackState.PLAYING
            startPositionUpdate()
        } catch (e: Exception) {
            LogUtils.e("音频LOG测试 Failed to resume playback: ${e.message}")
        }
    }

    /** 停止播放 */
    fun stopPlayback() {
        try {
            exoPlayer?.stop()
            exoPlayer?.clearMediaItems()
            abandonAudioFocus()
            currentAudioInfo = null
            _currentPosition.value = 0L
            _duration.value = 0L
            _playbackState.value = PlaybackState.IDLE
            positionUpdateJob?.cancel()
        } catch (e: Exception) {
            LogUtils.e("音频LOG测试 Failed to stop playback: ${e.message}")
        }
    }

    /** 重置播放器状态（播放完成后调用） */
    private fun resetPlayerState() {
        try {
            currentAudioInfo = null
            _currentPosition.value = 0L
            _duration.value = 0L
            _playbackState.value = PlaybackState.IDLE
            _isLoading.value = false
            _error.value = null
            positionUpdateJob?.cancel()
        } catch (e: Exception) {
            LogUtils.e("音频LOG测试 Failed to reset player state: ${e.message}")
        }
    }

    /** 跳转到指定位置 */
    fun seekTo(positionMs: Long) {
        try {
            exoPlayer?.seekTo(positionMs)
        } catch (e: Exception) {
            LogUtils.e("音频LOG测试 Failed to seek: ${e.message}")
        }
    }

    /** 请求音频焦点 */
    private fun requestAudioFocus(): Boolean {
        return try {
            val result =
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    requestAudioFocusV26()
                } else {
                    requestAudioFocusLegacy()
                }
            result
        } catch (e: Exception) {
            LogUtils.e("音频LOG测试 Failed to request audio focus: ${e.message}")
            false
        }
    }

    @RequiresApi(Build.VERSION_CODES.O)
    private fun requestAudioFocusV26(): Boolean {
        val audioAttributes =
            AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_MEDIA)
                .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                .build()

        audioFocusRequest =
            AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN)
                .setAudioAttributes(audioAttributes)
                .setAcceptsDelayedFocusGain(true)
                .setOnAudioFocusChangeListener { focusChange ->
                    handleAudioFocusChange(focusChange)
                }
                .build()

        return audioManager?.requestAudioFocus(audioFocusRequest!!) ==
                AudioManager.AUDIOFOCUS_REQUEST_GRANTED
    }

    @Suppress("DEPRECATION")
    private fun requestAudioFocusLegacy(): Boolean {
        return audioManager?.requestAudioFocus(
            { focusChange -> handleAudioFocusChange(focusChange) },
            AudioManager.STREAM_MUSIC,
            AudioManager.AUDIOFOCUS_GAIN,
        ) == AudioManager.AUDIOFOCUS_REQUEST_GRANTED
    }

    /** 处理音频焦点变化 */
    private fun handleAudioFocusChange(focusChange: Int) {
        when (focusChange) {
            AudioManager.AUDIOFOCUS_GAIN -> {
                // 恢复音量
                exoPlayer?.volume = 1.0f
                // 如果当前状态是暂停的，则恢复播放
                if (_playbackState.value == PlaybackState.PAUSED) {
                    exoPlayer?.play()
                }
            }

            AudioManager.AUDIOFOCUS_LOSS -> {
                // 永久丢失焦点，暂停播放但不改变状态
                exoPlayer?.pause()
            }

            AudioManager.AUDIOFOCUS_LOSS_TRANSIENT -> {
                // 临时丢失焦点，暂停播放但不改变状态
                exoPlayer?.pause()
            }

            AudioManager.AUDIOFOCUS_LOSS_TRANSIENT_CAN_DUCK -> {
                // 降低音量而不是暂停
                exoPlayer?.volume = 0.3f
            }
        }
    }

    /** 释放音频焦点 */
    private fun abandonAudioFocus() {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                audioFocusRequest?.let { request ->
                    audioManager?.abandonAudioFocusRequest(request)
                }
            } else {
                @Suppress("DEPRECATION") audioManager?.abandonAudioFocus {}
            }
            audioFocusRequest = null
        } catch (e: Exception) {
            LogUtils.e("音频LOG测试 Failed to abandon audio focus: ${e.message}")
        }
    }

    /** 开始位置更新 */
    private fun startPositionUpdate() {
        positionUpdateJob?.cancel()
        positionUpdateJob =
            scope.launch {
                while (true) {
                    exoPlayer?.let { player ->
                        if (player.isPlaying) {
                            _currentPosition.value = player.currentPosition
                        }
                    }
                    delay(100) // 每100ms更新一次
                }
            }
    }

    /** 停止位置更新 */
    private fun stopPositionUpdate() {
        positionUpdateJob?.cancel()
    }

    // Player.Listener 实现
    override fun onPlaybackStateChanged(playbackState: Int) {
        super.onPlaybackStateChanged(playbackState)


        when (playbackState) {
            Player.STATE_IDLE -> {
                _playbackState.value = PlaybackState.IDLE
                _isLoading.value = false
                stopPositionUpdate()
            }

            Player.STATE_BUFFERING -> {
                _playbackState.value = PlaybackState.BUFFERING
                _isLoading.value = true
            }

            Player.STATE_READY -> {
                _playbackState.value = PlaybackState.READY
                _isLoading.value = false
                _duration.value = exoPlayer?.duration ?: 0L
                startPositionUpdate()
            }

            Player.STATE_ENDED -> {
                _playbackState.value = PlaybackState.ENDED
                _isLoading.value = false
                stopPositionUpdate()
                abandonAudioFocus()

                // 播放完成后延迟释放资源，给UI更多时间更新状态
                scope.launch {
                    delay(500) // 增加延迟时间，确保UI状态正确更新
                    resetPlayerState()
                }
            }
        }
    }

    override fun onIsPlayingChanged(isPlaying: Boolean) {
        super.onIsPlayingChanged(isPlaying)

        if (isPlaying) {
            _playbackState.value = PlaybackState.PLAYING
            startPositionUpdate()
        } else {
            // 只有在不是缓冲状态时才设置为暂停状态
            // 如果当前状态是 PLAYING，则设置为 PAUSED
            // 如果当前状态是其他状态，则保持原状态
            when (_playbackState.value) {
                PlaybackState.PLAYING -> {
                    _playbackState.value = PlaybackState.PAUSED
                }

                PlaybackState.BUFFERING -> {
                    // 保持缓冲状态，不改变
                }

                else -> {
                    // 其他状态保持不变
                }
            }
            stopPositionUpdate()
        }
    }

    override fun onPlayerError(error: androidx.media3.common.PlaybackException) {
        super.onPlayerError(error)
        LogUtils.e("音频LOG测试 Player error: ${error.message}")
        _error.value = "播放错误: ${error.message}"
        _isLoading.value = false
        _playbackState.value = PlaybackState.ERROR
    }

    /** 释放资源 */
    fun release() {
        try {
            stopPlayback()
            exoPlayer?.release()
            exoPlayer = null
            abandonAudioFocus()
            positionUpdateJob?.cancel()
        } catch (e: Exception) {
            LogUtils.e("音频LOG测试 Failed to release AudioPlaybackManager: ${e.message}")
        }
    }

    /** 获取当前播放信息 */
    fun getCurrentAudioInfo(): AudioInfo? = currentAudioInfo

    /** 是否正在播放 */
    fun isPlaying(): Boolean = exoPlayer?.isPlaying ?: false

    /** 获取播放进度百分比 */
    fun getProgress(): Float {
        val duration = _duration.value
        val position = _currentPosition.value
        return if (duration > 0) (position.toFloat() / duration.toFloat()) else 0f
    }

    /** 重置播放器状态（页面切换时调用） */
    fun resetForPageChange() {
        try {
            stopPlayback()
            resetPlayerState()
        } catch (e: Exception) {
            LogUtils.e("音频LOG测试 Failed to reset player state for page change: ${e.message}")
        }
    }
}

/** 播放状态枚举 */
enum class PlaybackState {
    IDLE, // 空闲
    BUFFERING, // 缓冲中
    READY, // 准备就绪
    PLAYING, // 播放中
    PAUSED, // 暂停
    ENDED, // 播放结束
    ERROR, // 错误
}

/** 音频信息数据类 */
data class AudioInfo(
    val url: String,
    val title: String? = null,
    val artist: String? = null,
    val duration: Long? = null,
    val messageId: String? = null,
    val agentId: String? = null,
    val agentName: String? = null,
)
