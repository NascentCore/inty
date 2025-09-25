package com.ai.inty.audio

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
import com.inty.utils.log.EasyLog
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

/**
 * 企业级音频播放管理器
 * 基于Media3实现，支持Opus格式，提供完整的音频焦点管理和播放控制
 */
class AudioPlaybackManager private constructor(private val context: Context) : Player.Listener {

    companion object {
        @Volatile
        private var INSTANCE: AudioPlaybackManager? = null

        fun getInstance(context: Context): AudioPlaybackManager {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: AudioPlaybackManager(context.applicationContext).also { INSTANCE = it }
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

    /**
     * 初始化ExoPlayer
     */
    private fun initializePlayer() {
        try {
            EasyLog.log("音频LOG测试 === Initializing AudioPlaybackManager ===")

            // 创建OkHttp数据源工厂，支持缓存
            val okHttpClient = OkHttpClient.Builder()
                .connectTimeout(10, TimeUnit.SECONDS)
                .readTimeout(30, TimeUnit.SECONDS)
                .writeTimeout(30, TimeUnit.SECONDS)
                .build()

            val dataSourceFactory = DefaultDataSource.Factory(
                context,
                OkHttpDataSource.Factory(okHttpClient)
            )

            val mediaSourceFactory = DefaultMediaSourceFactory(dataSourceFactory)

            // 创建ExoPlayer实例 - 使用更简单的配置
            exoPlayer = ExoPlayer.Builder(context)
                .setMediaSourceFactory(mediaSourceFactory)
                .build()
                .apply {
                    addListener(this@AudioPlaybackManager)
                    playWhenReady = false
                    // 设置音频属性
                    setAudioAttributes(
                        Media3AudioAttributes.Builder()
                            .setUsage(C.USAGE_MEDIA)
                            .setContentType(C.AUDIO_CONTENT_TYPE_SPEECH)
                            .build(),
                        false // 手动处理音频焦点
                    )
                }

            EasyLog.log("音频LOG测试 ExoPlayer created successfully")
            EasyLog.log("音频LOG测试 ExoPlayer state: ${exoPlayer?.playbackState}")
            EasyLog.log("音频LOG测试 ExoPlayer isPlaying: ${exoPlayer?.isPlaying}")
            EasyLog.log("音频LOG测试 === AudioPlaybackManager initialization completed ===")
        } catch (e: Exception) {
            EasyLog.log("音频LOG测试 Failed to initialize AudioPlaybackManager: ${e.message}", EasyLog.ERROR)
            _error.value = "播放器初始化失败: ${e.message}"
        }
    }

    /**
     * 播放音频
     * @param audioInfo 音频信息
     * @param autoPlay 是否自动播放
     */
    fun playAudio(audioInfo: AudioInfo, autoPlay: Boolean = true) {
        try {
            EasyLog.log("音频LOG测试 === AudioPlaybackManager.playAudio START ===")
            EasyLog.log("音频LOG测试 Audio URL: ${audioInfo.url}")
            EasyLog.log("音频LOG测试 Message ID: ${audioInfo.messageId}")
            EasyLog.log("音频LOG测试 Auto play: $autoPlay")
            EasyLog.log("音频LOG测试 Current audio info: ${currentAudioInfo?.messageId}")
            EasyLog.log("音频LOG测试 Is currently playing: ${isPlaying()}")

            // 检查是否是同一个音频（优先使用messageId判断）
            val isSameAudio = currentAudioInfo?.messageId == audioInfo.messageId

            EasyLog.log("音频LOG测试 Is same audio: $isSameAudio (current: ${currentAudioInfo?.messageId}, new: ${audioInfo.messageId})")

            if (isSameAudio && isPlaying()) {
                // 如果是同一个音频且正在播放，则暂停
                EasyLog.log("音频LOG测试 Same audio playing, pausing...")
                pausePlayback()
                return
            }

            // 停止当前播放（如果不是同一个音频）
            if (!isSameAudio) {
                EasyLog.log("音频LOG测试 Different audio, stopping current playback...")
                stopPlayback()
            }

            // 请求音频焦点
            EasyLog.log("音频LOG测试 Requesting audio focus...")
            if (!requestAudioFocus()) {
                EasyLog.log("音频LOG测试 Failed to request audio focus", EasyLog.ERROR)
                _error.value = "无法获取音频焦点"
                return
            }
            EasyLog.log("音频LOG测试 Audio focus granted")

            currentAudioInfo = audioInfo
            _isLoading.value = true
            _error.value = null

            // 设置媒体项 - 优先使用缓存文件
            val mediaItem = if (cacheManager.isCached(audioInfo.url)) {
                val cachedPath = cacheManager.getCachedFilePath(audioInfo.url)
                if (cachedPath != null) {
                    EasyLog.log("音频LOG测试 Using cached audio file: $cachedPath")
                    MediaItem.fromUri("file://$cachedPath")
                } else {
                    EasyLog.log("音频LOG测试 Cache check failed, using original URL")
                    MediaItem.fromUri(audioInfo.url)
                }
            } else {
                EasyLog.log("音频LOG测试 Audio not cached, using original URL")
                // 异步预加载音频到缓存
                scope.launch {
                    try {
                        cacheManager.preloadAudio(audioInfo.url)
                        EasyLog.log("音频LOG测试 Audio preloaded to cache: ${audioInfo.url}")
                    } catch (e: Exception) {
                        EasyLog.log("音频LOG测试 Failed to preload audio: ${e.message}", EasyLog.ERROR)
                    }
                }
                MediaItem.fromUri(audioInfo.url)
            }

            EasyLog.log("音频LOG测试 Setting media item and preparing...")
            exoPlayer?.setMediaItem(mediaItem)
            exoPlayer?.prepare()

            // 等待准备完成
            EasyLog.log("音频LOG测试 Waiting for player to be ready...")
            // 注意：这里不等待，让Player.Listener处理状态变化

            if (autoPlay) {
                EasyLog.log("音频LOG测试 Starting playback...")
                exoPlayer?.play()
            }

            EasyLog.log("音频LOG测试 === AudioPlaybackManager.playAudio END ===")

        } catch (e: Exception) {
            EasyLog.log("音频LOG测试 Failed to play audio: ${e.message}", EasyLog.ERROR)
            _error.value = "播放失败: ${e.message}"
            _isLoading.value = false
        }
    }

    /**
     * 暂停播放
     */
    fun pausePlayback() {
        try {
            exoPlayer?.pause()
            EasyLog.log("音频LOG测试 Audio playback paused")
        } catch (e: Exception) {
            EasyLog.log("音频LOG测试 Failed to pause playback: ${e.message}", EasyLog.ERROR)
        }
    }

    /**
     * 恢复播放
     */
    fun resumePlayback() {
        try {
            EasyLog.log("音频LOG测试 Attempting to resume playback...")
            
            // 直接恢复播放，不重新请求音频焦点
            // 因为音频焦点在初始播放时已经获得，暂停时不会释放
            exoPlayer?.play()
            EasyLog.log("音频LOG测试 Audio playback resumed successfully")
            
        } catch (e: Exception) {
            EasyLog.log("音频LOG测试 Failed to resume playback: ${e.message}", EasyLog.ERROR)
        }
    }

    /**
     * 停止播放
     */
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
            EasyLog.log("音频LOG测试 Audio playback stopped")
        } catch (e: Exception) {
            EasyLog.log("音频LOG测试 Failed to stop playback: ${e.message}", EasyLog.ERROR)
        }
    }

    /**
     * 重置播放器状态（播放完成后调用）
     */
    private fun resetPlayerState() {
        try {
            EasyLog.log("音频LOG测试 Resetting player state after playback completion")
            currentAudioInfo = null
            _currentPosition.value = 0L
            _duration.value = 0L
            _playbackState.value = PlaybackState.IDLE
            _isLoading.value = false
            _error.value = null
            positionUpdateJob?.cancel()
            EasyLog.log("音频LOG测试 Player state reset completed")
        } catch (e: Exception) {
            EasyLog.log("音频LOG测试 Failed to reset player state: ${e.message}", EasyLog.ERROR)
        }
    }

    /**
     * 跳转到指定位置
     */
    fun seekTo(positionMs: Long) {
        try {
            exoPlayer?.seekTo(positionMs)
            EasyLog.log("音频LOG测试 Seeked to position: $positionMs")
        } catch (e: Exception) {
            EasyLog.log("音频LOG测试 Failed to seek: ${e.message}", EasyLog.ERROR)
        }
    }

    /**
     * 请求音频焦点
     */
    private fun requestAudioFocus(): Boolean {
        return try {
            EasyLog.log("音频LOG测试 Requesting audio focus...")
            val result = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                requestAudioFocusV26()
            } else {
                requestAudioFocusLegacy()
            }
            EasyLog.log("音频LOG测试 Audio focus request result: $result")
            result
        } catch (e: Exception) {
            EasyLog.log("音频LOG测试 Failed to request audio focus: ${e.message}", EasyLog.ERROR)
            false
        }
    }

    @RequiresApi(Build.VERSION_CODES.O)
    private fun requestAudioFocusV26(): Boolean {
        val audioAttributes = AudioAttributes.Builder()
            .setUsage(AudioAttributes.USAGE_MEDIA)
            .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
            .build()

        audioFocusRequest = AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN)
            .setAudioAttributes(audioAttributes)
            .setAcceptsDelayedFocusGain(true)
            .setOnAudioFocusChangeListener { focusChange ->
                handleAudioFocusChange(focusChange)
            }
            .build()

        return audioManager?.requestAudioFocus(audioFocusRequest!!) == AudioManager.AUDIOFOCUS_REQUEST_GRANTED
    }

    @Suppress("DEPRECATION")
    private fun requestAudioFocusLegacy(): Boolean {
        return audioManager?.requestAudioFocus(
            { focusChange -> handleAudioFocusChange(focusChange) },
            AudioManager.STREAM_MUSIC,
            AudioManager.AUDIOFOCUS_GAIN
        ) == AudioManager.AUDIOFOCUS_REQUEST_GRANTED
    }

    /**
     * 处理音频焦点变化
     */
    private fun handleAudioFocusChange(focusChange: Int) {
        EasyLog.log("音频LOG测试 Audio focus change: $focusChange")
        when (focusChange) {
            AudioManager.AUDIOFOCUS_GAIN -> {
                EasyLog.log("音频LOG测试 Audio focus gained")
                // 恢复音量
                exoPlayer?.volume = 1.0f
                // 如果当前状态是暂停的，则恢复播放
                if (_playbackState.value == PlaybackState.PAUSED) {
                    EasyLog.log("音频LOG测试 Resuming playback due to audio focus gain")
                    exoPlayer?.play()
                }
            }

            AudioManager.AUDIOFOCUS_LOSS -> {
                EasyLog.log("音频LOG测试 Audio focus lost permanently")
                // 永久丢失焦点，暂停播放但不改变状态
                exoPlayer?.pause()
            }

            AudioManager.AUDIOFOCUS_LOSS_TRANSIENT -> {
                EasyLog.log("音频LOG测试 Audio focus lost temporarily")
                // 临时丢失焦点，暂停播放但不改变状态
                exoPlayer?.pause()
            }

            AudioManager.AUDIOFOCUS_LOSS_TRANSIENT_CAN_DUCK -> {
                EasyLog.log("音频LOG测试 Audio focus lost, can duck")
                // 降低音量而不是暂停
                exoPlayer?.volume = 0.3f
            }
        }
    }

    /**
     * 释放音频焦点
     */
    private fun abandonAudioFocus() {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                audioFocusRequest?.let { request ->
                    audioManager?.abandonAudioFocusRequest(request)
                }
            } else {
                @Suppress("DEPRECATION")
                audioManager?.abandonAudioFocus { }
            }
            audioFocusRequest = null
        } catch (e: Exception) {
            EasyLog.log("音频LOG测试 Failed to abandon audio focus: ${e.message}", EasyLog.ERROR)
        }
    }

    /**
     * 开始位置更新
     */
    private fun startPositionUpdate() {
        positionUpdateJob?.cancel()
        positionUpdateJob = scope.launch {
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

    /**
     * 停止位置更新
     */
    private fun stopPositionUpdate() {
        positionUpdateJob?.cancel()
    }

    // Player.Listener 实现
    override fun onPlaybackStateChanged(playbackState: Int) {
        super.onPlaybackStateChanged(playbackState)

        EasyLog.log("音频LOG测试 === onPlaybackStateChanged: $playbackState ===")

        when (playbackState) {
            Player.STATE_IDLE -> {
                EasyLog.log("音频LOG测试 Player state: IDLE")
                _playbackState.value = PlaybackState.IDLE
                _isLoading.value = false
                stopPositionUpdate()
            }

            Player.STATE_BUFFERING -> {
                EasyLog.log("音频LOG测试 Player state: BUFFERING")
                _playbackState.value = PlaybackState.BUFFERING
                _isLoading.value = true
            }

            Player.STATE_READY -> {
                EasyLog.log("音频LOG测试 Player state: READY")
                _playbackState.value = PlaybackState.READY
                _isLoading.value = false
                _duration.value = exoPlayer?.duration ?: 0L
                startPositionUpdate()
            }

            Player.STATE_ENDED -> {
                EasyLog.log("音频LOG测试 Player state: ENDED - 播放完成，释放资源")
                _playbackState.value = PlaybackState.ENDED
                _isLoading.value = false
                stopPositionUpdate()
                abandonAudioFocus()

                // 播放完成后自动释放资源
                scope.launch {
                    delay(100) // 短暂延迟确保UI更新完成
                    resetPlayerState()
                }
            }
        }
    }

    override fun onIsPlayingChanged(isPlaying: Boolean) {
        super.onIsPlayingChanged(isPlaying)

        EasyLog.log("音频LOG测试 === onIsPlayingChanged: $isPlaying ===")

        if (isPlaying) {
            EasyLog.log("音频LOG测试 Player started playing")
            _playbackState.value = PlaybackState.PLAYING
            startPositionUpdate()
        } else {
            EasyLog.log("音频LOG测试 Player stopped playing")
            if (_playbackState.value != PlaybackState.BUFFERING) {
                _playbackState.value = PlaybackState.PAUSED
            }
            stopPositionUpdate()
        }
    }

    override fun onPlayerError(error: androidx.media3.common.PlaybackException) {
        super.onPlayerError(error)
        EasyLog.log("音频LOG测试 Player error: ${error.message}", EasyLog.ERROR)
        _error.value = "播放错误: ${error.message}"
        _isLoading.value = false
        _playbackState.value = PlaybackState.ERROR
    }

    /**
     * 释放资源
     */
    fun release() {
        try {
            stopPlayback()
            exoPlayer?.release()
            exoPlayer = null
            abandonAudioFocus()
            positionUpdateJob?.cancel()
            EasyLog.log("音频LOG测试 AudioPlaybackManager released")
        } catch (e: Exception) {
            EasyLog.log("音频LOG测试 Failed to release AudioPlaybackManager: ${e.message}", EasyLog.ERROR)
        }
    }

    /**
     * 获取当前播放信息
     */
    fun getCurrentAudioInfo(): AudioInfo? = currentAudioInfo

    /**
     * 是否正在播放
     */
    fun isPlaying(): Boolean = exoPlayer?.isPlaying ?: false

    /**
     * 获取播放进度百分比
     */
    fun getProgress(): Float {
        val duration = _duration.value
        val position = _currentPosition.value
        return if (duration > 0) (position.toFloat() / duration.toFloat()) else 0f
    }

    /**
     * 重置播放器状态（页面切换时调用）
     */
    fun resetForPageChange() {
        try {
            EasyLog.log("音频LOG测试 Resetting player state for page change")
            stopPlayback()
            resetPlayerState()
        } catch (e: Exception) {
            EasyLog.log("音频LOG测试 Failed to reset player state for page change: ${e.message}", EasyLog.ERROR)
        }
    }
}

/**
 * 播放状态枚举
 */
enum class PlaybackState {
    IDLE,       // 空闲
    BUFFERING,  // 缓冲中
    READY,      // 准备就绪
    PLAYING,    // 播放中
    PAUSED,     // 暂停
    ENDED,      // 播放结束
    ERROR       // 错误
}

/**
 * 音频信息数据类
 */
data class AudioInfo(
    val url: String,
    val title: String? = null,
    val artist: String? = null,
    val duration: Long? = null,
    val messageId: String? = null,
    val agentId: String? = null
)
