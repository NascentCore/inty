package com.ai.intellimate.ui.components

import ai.sxwl.android.utils.LogUtils
import android.content.Context
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.datasource.DefaultDataSource
import androidx.media3.datasource.okhttp.OkHttpDataSource
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.exoplayer.source.DefaultMediaSourceFactory
import androidx.media3.ui.PlayerView
import coil3.compose.AsyncImage
import coil3.request.ImageRequest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import okhttp3.OkHttpClient
import java.util.concurrent.TimeUnit

/**
 * 判断 URL 是否为视频格式
 */
private fun isVideoUrl(url: String?): Boolean {
    if (url.isNullOrBlank()) return false
    val lowerUrl = url.lowercase()
    return lowerUrl.endsWith(".mp4") || lowerUrl.endsWith(".webm") || lowerUrl.contains(".mp4?") || lowerUrl.contains(
        ".webm?"
    )
}

/**
 * 判断 URL 是否为 GIF 格式
 */
private fun isGifUrl(url: String?): Boolean {
    if (url.isNullOrBlank()) return false
    val lowerUrl = url.lowercase()
    return lowerUrl.endsWith(".gif") || lowerUrl.contains(".gif?")
}

/**
 * 基于 ExoPlayer 的视频播放器，支持播放次数控制和错误处理
 */
private class ControlledExoPlayer(
    context: Context,
    private val onPrepared: () -> Unit,
    private val onError: (String) -> Unit,
    private val onPlayComplete: () -> Unit
) : Player.Listener {
    private var exoPlayer: ExoPlayer? = null
    private var playCount = 0
    private var targetPlayCount = 1
    private var videoUrl: String? = null
    private var isPrepared = false

    init {
        initializePlayer(context)
    }

    private fun initializePlayer(context: Context) {
        try {
            LogUtils.d("AnimatedBackground - [ControlledExoPlayer] 初始化 ExoPlayer...")

            // 创建 OkHttp 客户端，复用项目配置
            val okHttpClient = OkHttpClient.Builder()
                .connectTimeout(30, TimeUnit.SECONDS)
                .readTimeout(60, TimeUnit.SECONDS)
                .writeTimeout(30, TimeUnit.SECONDS)
                .retryOnConnectionFailure(true)
                .build()

            val dataSourceFactory = DefaultDataSource.Factory(
                context,
                OkHttpDataSource.Factory(okHttpClient)
            )

            val mediaSourceFactory = DefaultMediaSourceFactory(dataSourceFactory)

            // 创建 ExoPlayer 实例
            exoPlayer = ExoPlayer.Builder(context)
                .setMediaSourceFactory(mediaSourceFactory)
                .build()
                .apply {
                    addListener(this@ControlledExoPlayer)
                    playWhenReady = false
                    volume = 0f // 静音播放
                    repeatMode = Player.REPEAT_MODE_OFF
                }

            LogUtils.d("AnimatedBackground - [ControlledExoPlayer] ✓ ExoPlayer 初始化完成")
        } catch (e: Exception) {
            LogUtils.e("AnimatedBackground - [ControlledExoPlayer] ✗ 初始化失败: ${e.message}")
            onError("播放器初始化失败: ${e.message}")
        }
    }

    fun setVideoUrl(url: String) {
        videoUrl = url
        LogUtils.d("AnimatedBackground - [ControlledExoPlayer] 设置视频 URL: $url")
    }

    fun setPlayCount(count: Int) {
        targetPlayCount = count
        playCount = 0
        LogUtils.d("AnimatedBackground - [ControlledExoPlayer] 设置播放次数: $count")
    }

    fun setMediaItem(uri: String) {
        try {
            LogUtils.d("AnimatedBackground - [ControlledExoPlayer: setMediaItem] ========== 设置媒体项 ==========")
            LogUtils.d("AnimatedBackground - [ControlledExoPlayer: setMediaItem] uri: $uri")
            LogUtils.d("AnimatedBackground - [ControlledExoPlayer: setMediaItem] exoPlayer=${exoPlayer != null}")

            val mediaItem = MediaItem.fromUri(uri)
            LogUtils.d("AnimatedBackground - [ControlledExoPlayer: setMediaItem] MediaItem 创建成功")

            exoPlayer?.setMediaItem(mediaItem)
            LogUtils.d("AnimatedBackground - [ControlledExoPlayer: setMediaItem] MediaItem 已设置到 ExoPlayer")

            exoPlayer?.prepare()
            LogUtils.d("AnimatedBackground - [ControlledExoPlayer: setMediaItem] ✓ 已调用 prepare()，开始准备...")
            LogUtils.d("AnimatedBackground - [ControlledExoPlayer: setMediaItem] ========== 设置完成 ==========")
        } catch (e: Exception) {
            LogUtils.e("AnimatedBackground - [ControlledExoPlayer: setMediaItem] ✗ 设置媒体项失败: ${e.message}")
            LogUtils.e("AnimatedBackground - [ControlledExoPlayer: setMediaItem] 异常堆栈: ${e.stackTraceToString()}")
            onError("设置媒体项失败: ${e.message}")
        }
    }

    fun startPlayback() {
        LogUtils.d("AnimatedBackground - [ControlledExoPlayer: startPlayback] ========== 开始播放 ==========")
        LogUtils.d("AnimatedBackground - [ControlledExoPlayer: startPlayback] isPrepared=$isPrepared, playCount=$playCount, targetPlayCount=$targetPlayCount")
        LogUtils.d("AnimatedBackground - [ControlledExoPlayer: startPlayback] exoPlayer=${exoPlayer != null}")

        if (isPrepared && playCount < targetPlayCount) {
            try {
                val currentState = exoPlayer?.playbackState
                val playWhenReady = exoPlayer?.playWhenReady
                LogUtils.d("AnimatedBackground - [ControlledExoPlayer: startPlayback] 当前播放状态: $currentState, playWhenReady=$playWhenReady")
                LogUtils.d("AnimatedBackground - [ControlledExoPlayer: startPlayback] 设置 playWhenReady=true")
                exoPlayer?.playWhenReady = true
                LogUtils.d("AnimatedBackground - [ControlledExoPlayer: startPlayback] ✓ 播放已启动")
            } catch (e: Exception) {
                LogUtils.e("AnimatedBackground - [ControlledExoPlayer: startPlayback] ✗ 播放失败: ${e.message}")
                LogUtils.e("AnimatedBackground - [ControlledExoPlayer: startPlayback] 异常堆栈: ${e.stackTraceToString()}")
                onError("播放失败: ${e.message}")
            }
        } else {
            LogUtils.w("AnimatedBackground - [ControlledExoPlayer: startPlayback] ⏳ 视频未准备好，无法播放: isPrepared=$isPrepared, playCount=$playCount, targetPlayCount=$targetPlayCount")
        }
        LogUtils.d("AnimatedBackground - [ControlledExoPlayer: startPlayback] ========== 播放处理完成 ==========")
    }

    fun resetPlayback() {
        try {
            LogUtils.d("AnimatedBackground - [ControlledExoPlayer] 重置播放")
            exoPlayer?.pause()
            exoPlayer?.seekTo(0)
            playCount = 0
        } catch (e: Exception) {
            LogUtils.e("AnimatedBackground - [ControlledExoPlayer] ✗ 重置失败: ${e.message}")
        }
    }

    fun getPlayer(): ExoPlayer? = exoPlayer

    fun release() {
        try {
            LogUtils.d("AnimatedBackground - [ControlledExoPlayer] 释放播放器")
            exoPlayer?.removeListener(this)
            exoPlayer?.release()
            exoPlayer = null
        } catch (e: Exception) {
            LogUtils.e("AnimatedBackground - [ControlledExoPlayer] ✗ 释放失败: ${e.message}")
        }
    }

    // Player.Listener 实现
    override fun onPlaybackStateChanged(playbackState: Int) {
        val stateName = when (playbackState) {
            Player.STATE_IDLE -> "IDLE"
            Player.STATE_BUFFERING -> "BUFFERING"
            Player.STATE_READY -> "READY"
            Player.STATE_ENDED -> "ENDED"
            else -> "UNKNOWN($playbackState)"
        }
        LogUtils.d("AnimatedBackground - [ControlledExoPlayer: onPlaybackStateChanged] ========== 播放状态变化 ==========")
        LogUtils.d("AnimatedBackground - [ControlledExoPlayer: onPlaybackStateChanged] state=$playbackState ($stateName)")
        LogUtils.d("AnimatedBackground - [ControlledExoPlayer: onPlaybackStateChanged] videoUrl: $videoUrl")
        LogUtils.d("AnimatedBackground - [ControlledExoPlayer: onPlaybackStateChanged] isPrepared=$isPrepared, playCount=$playCount, targetPlayCount=$targetPlayCount")

        when (playbackState) {
            Player.STATE_IDLE -> {
                LogUtils.d("AnimatedBackground - [ControlledExoPlayer: onPlaybackStateChanged] 状态: IDLE（空闲）")
            }

            Player.STATE_BUFFERING -> {
                LogUtils.d("AnimatedBackground - [ControlledExoPlayer: onPlaybackStateChanged] 状态: BUFFERING（缓冲中）")
            }

            Player.STATE_READY -> {
                if (!isPrepared) {
                    isPrepared = true
                    val duration = exoPlayer?.duration ?: 0L
                    val playWhenReady = exoPlayer?.playWhenReady ?: false
                    LogUtils.d("AnimatedBackground - [ControlledExoPlayer: onPlaybackStateChanged] ========== 视频准备完成 ==========")
                    LogUtils.d("AnimatedBackground - [ControlledExoPlayer: onPlaybackStateChanged] videoUrl: $videoUrl")
                    LogUtils.d("AnimatedBackground - [ControlledExoPlayer: onPlaybackStateChanged] duration: ${duration}ms")
                    LogUtils.d("AnimatedBackground - [ControlledExoPlayer: onPlaybackStateChanged] playWhenReady: $playWhenReady")
                    LogUtils.d("AnimatedBackground - [ControlledExoPlayer: onPlaybackStateChanged] isPrepared: true")
                    onPrepared()
                    LogUtils.d("AnimatedBackground - [ControlledExoPlayer: onPlaybackStateChanged] ✓ 已通知外部监听器")
                    LogUtils.d("AnimatedBackground - [ControlledExoPlayer: onPlaybackStateChanged] ========== 准备完成 ==========")
                } else {
                    LogUtils.d("AnimatedBackground - [ControlledExoPlayer: onPlaybackStateChanged] 状态: READY（已准备好，但之前已通知）")
                }
            }

            Player.STATE_ENDED -> {
                playCount++
                LogUtils.d("AnimatedBackground - [ControlledExoPlayer: onPlaybackStateChanged] ========== 播放完成 ==========")
                LogUtils.d("AnimatedBackground - [ControlledExoPlayer: onPlaybackStateChanged] playCount=$playCount, targetPlayCount=$targetPlayCount")
                if (playCount >= targetPlayCount) {
                    LogUtils.d("AnimatedBackground - [ControlledExoPlayer: onPlaybackStateChanged] ✓ 达到目标播放次数，停止并回调")
                    resetPlayback()
                    onPlayComplete()
                } else {
                    LogUtils.d("AnimatedBackground - [ControlledExoPlayer: onPlaybackStateChanged] ⏳ 继续播放下一次")
                    // 继续播放下一次
                    exoPlayer?.seekTo(0)
                    exoPlayer?.playWhenReady = true
                }
                LogUtils.d("AnimatedBackground - [ControlledExoPlayer: onPlaybackStateChanged] ========== 播放完成处理完成 ==========")
            }
        }
        LogUtils.d("AnimatedBackground - [ControlledExoPlayer: onPlaybackStateChanged] ========== 状态变化处理完成 ==========")
    }

    override fun onIsPlayingChanged(isPlaying: Boolean) {
        LogUtils.d("AnimatedBackground - [ControlledExoPlayer: onIsPlayingChanged] isPlaying=$isPlaying")
    }

    override fun onPlayWhenReadyChanged(playWhenReady: Boolean, reason: Int) {
        val reasonName = when (reason) {
            Player.PLAY_WHEN_READY_CHANGE_REASON_USER_REQUEST -> "USER_REQUEST"
            Player.PLAY_WHEN_READY_CHANGE_REASON_AUDIO_FOCUS_LOSS -> "AUDIO_FOCUS_LOSS"
            Player.PLAY_WHEN_READY_CHANGE_REASON_AUDIO_BECOMING_NOISY -> "AUDIO_BECOMING_NOISY"
            else -> "UNKNOWN($reason)"
        }
        LogUtils.d("AnimatedBackground - [ControlledExoPlayer: onPlayWhenReadyChanged] playWhenReady=$playWhenReady, reason=$reason ($reasonName)")
    }

    override fun onPlayerError(error: androidx.media3.common.PlaybackException) {
        val errorMsg =
            "视频播放错误: ${error.message}, errorCode=${error.errorCode}, cause=${error.cause?.message}"
        LogUtils.e("AnimatedBackground - [ControlledExoPlayer: onPlayerError] ========== 视频播放错误 ==========")
        LogUtils.e("AnimatedBackground - [ControlledExoPlayer: onPlayerError] videoUrl: $videoUrl")
        LogUtils.e("AnimatedBackground - [ControlledExoPlayer: onPlayerError] errorMsg: $errorMsg")
        isPrepared = false
        onError(errorMsg)
        LogUtils.e("AnimatedBackground - [ControlledExoPlayer: onPlayerError] ========== 错误处理完成 ==========")
    }
}

/**
 * 动图/视频背景播放组件
 *
 * @param videoUrl 视频或动图 URL
 * @param staticImageUrl 静态背景图 URL（用于首次加载优化）
 * @param modifier Modifier
 * @param contentScale ContentScale
 * @param shouldPlay 是否应该播放
 * @param playCount 播放次数（首次进入为2，loading时为1）
 * @param onPlayComplete 播放完成回调
 * @param onStaticImageLoaded 静态图加载完成回调
 */
@Composable
fun AnimatedBackground(
    videoUrl: String?,
    staticImageUrl: String?,
    modifier: Modifier = Modifier,
    contentScale: ContentScale = ContentScale.Crop,
    shouldPlay: Boolean = false,
    playCount: Int = 1,
    onPlayComplete: () -> Unit = {},
    onStaticImageLoaded: () -> Unit = {},
) {
    LogUtils.d("AnimatedBackground - [Composable] ========== AnimatedBackground 组件初始化 ==========")
    LogUtils.d("AnimatedBackground - [Composable] videoUrl: $videoUrl")
    LogUtils.d("AnimatedBackground - [Composable] staticImageUrl: $staticImageUrl")
    LogUtils.d("AnimatedBackground - [Composable] shouldPlay: $shouldPlay")
    LogUtils.d("AnimatedBackground - [Composable] playCount: $playCount")
    LogUtils.d("AnimatedBackground - [Composable] ========== 初始化完成 ==========")

    val context = LocalContext.current
    val videoCacheManager = remember { VideoCacheManager.getInstance(context) }

    // 显示逻辑：
    // 1. 如果有 staticImageUrl，先显示静态图
    // 2. 如果是视频，等待视频准备好后再切换
    // 3. 如果是 GIF，等待静态图加载完成后再切换
    var showStaticImage by remember { mutableStateOf(staticImageUrl != null) }
    var staticImageLoaded by remember { mutableStateOf(false) }
    var videoPrepared by remember { mutableStateOf(false) }
    var controlledPlayer by remember { mutableStateOf<ControlledExoPlayer?>(null) }
    var currentPlayCount by remember { mutableIntStateOf(0) }
    var videoError by remember { mutableStateOf<String?>(null) }
    var videoPath by remember(videoUrl) { mutableStateOf<String?>(null) }
    var videoUriSet by remember { mutableStateOf(false) }

    // 判断资源类型
    val isVideo = isVideoUrl(videoUrl)
    val isGif = isGifUrl(videoUrl)

    // 状态变化日志（在 shouldShowVideo 计算之后）

    // 预加载视频到缓存（如果是视频）
    LaunchedEffect(videoUrl, isVideo) {
        LogUtils.d("AnimatedBackground - [LaunchedEffect: videoUrl] ========== 开始处理视频 ==========")
        LogUtils.d("AnimatedBackground - [LaunchedEffect: videoUrl] videoUrl=$videoUrl, isVideo=$isVideo")

        if (isVideo && videoUrl != null) {
            LogUtils.d("AnimatedBackground - [LaunchedEffect: videoUrl] 开始获取视频路径...")
            val pathStartTime = System.currentTimeMillis()

            // 异步获取视频路径（优先使用缓存）
            videoPath = videoCacheManager.getVideoPath(videoUrl)
            val pathTime = System.currentTimeMillis() - pathStartTime
            LogUtils.d("AnimatedBackground - [LaunchedEffect: videoUrl] ✓ 视频路径获取完成: $videoPath, time=${pathTime}ms")

            // 后台预加载视频（如果未缓存）
            val isCached = videoCacheManager.isCached(videoUrl)
            LogUtils.d("AnimatedBackground - [LaunchedEffect: videoUrl] 缓存检查: isCached=$isCached")

            if (!isCached) {
                LogUtils.d("AnimatedBackground - [LaunchedEffect: videoUrl] 开始后台预加载视频...")
                launch(Dispatchers.IO) {
                    videoCacheManager.preloadVideo(videoUrl)
                }
            } else {
                LogUtils.d("AnimatedBackground - [LaunchedEffect: videoUrl] 视频已缓存，跳过预加载")
            }
        } else {
            videoPath = null
            LogUtils.d("AnimatedBackground - [LaunchedEffect: videoUrl] 不是视频或 videoUrl 为 null，videoPath=null")
        }
        LogUtils.d("AnimatedBackground - [LaunchedEffect: videoUrl] ========== 处理完成 ==========")
    }

    // 调试日志
    LaunchedEffect(videoUrl, isVideo, isGif) {
        LogUtils.d("AnimatedBackground - videoUrl: $videoUrl, isVideo: $isVideo, isGif: $isGif")
    }

    // 当 shouldPlay 变化时，触发播放
    LaunchedEffect(shouldPlay, playCount, videoUrl, isVideo, isGif, videoPath, controlledPlayer) {
        if (shouldPlay && (isVideo || isGif)) {
            currentPlayCount = playCount
            LogUtils.d("AnimatedBackground - [LaunchedEffect: shouldPlay] 触发播放: shouldPlay=$shouldPlay, playCount=$playCount, isVideo=$isVideo, isGif=$isGif, videoPath=$videoPath")

            if (isVideo && videoPath != null) {
                // 视频：延迟一下确保视图已准备好
                delay(500)
                if (controlledPlayer != null) {
                    LogUtils.d("AnimatedBackground - [LaunchedEffect: shouldPlay] 设置播放次数: $playCount")
                    controlledPlayer?.setPlayCount(playCount)
                    controlledPlayer?.startPlayback()
                } else {
                    LogUtils.w("AnimatedBackground - [LaunchedEffect: shouldPlay] controlledPlayer 为 null，无法播放")
                }
            } else if (isVideo) {
                LogUtils.w("AnimatedBackground - [LaunchedEffect: shouldPlay] videoPath 为 null，等待视频路径准备")
            }
            // GIF 由 Coil 自动处理，播放完成后需要手动回调
            // 注意：GIF 无法精确控制播放次数，这里使用延时来模拟
            if (isGif && playCount > 0) {
                // 估算 GIF 播放时间（假设平均 2 秒一次循环）
                val estimatedDuration = 2000L * playCount
                delay(estimatedDuration)
                onPlayComplete()
            }
        } else if (!shouldPlay && isVideo) {
            // 停止播放
            LogUtils.d("AnimatedBackground - [LaunchedEffect: shouldPlay] 停止播放")
            controlledPlayer?.resetPlayback()
        }
    }

    // 当视频 URL 变化时，重置状态
    LaunchedEffect(videoUrl, staticImageUrl) {
        LogUtils.d("AnimatedBackground - [LaunchedEffect: reset] ========== 重置状态 ==========")
        LogUtils.d("AnimatedBackground - [LaunchedEffect: reset] videoUrl=$videoUrl, staticImageUrl=$staticImageUrl")
        showStaticImage = staticImageUrl != null
        staticImageLoaded = false
        videoPrepared = false
        currentPlayCount = 0
        videoUriSet = false
        videoError = null
        LogUtils.d("AnimatedBackground - [LaunchedEffect: reset] showStaticImage=$showStaticImage, staticImageLoaded=$staticImageLoaded, videoPrepared=$videoPrepared")
        controlledPlayer?.resetPlayback()
        LogUtils.d("AnimatedBackground - [LaunchedEffect: reset] ========== 重置完成 ==========")
    }

    // 切换显示逻辑：
    // 1. 如果是视频：等待静态图加载完成 AND 视频准备好
    // 2. 如果是 GIF：等待静态图加载完成
    // 3. 如果视频加载失败：继续显示静态图
    LaunchedEffect(
        staticImageLoaded,
        videoPrepared,
        isVideo,
        isGif,
        videoError,
        videoUrl,
        staticImageUrl
    ) {
        LogUtils.d("AnimatedBackground - [LaunchedEffect: switch] ========== 检查切换条件 ==========")
        LogUtils.d("AnimatedBackground - [LaunchedEffect: switch] staticImageLoaded=$staticImageLoaded, videoPrepared=$videoPrepared")
        LogUtils.d("AnimatedBackground - [LaunchedEffect: switch] isVideo=$isVideo, isGif=$isGif, videoError=$videoError")
        LogUtils.d("AnimatedBackground - [LaunchedEffect: switch] videoUrl=$videoUrl, staticImageUrl=$staticImageUrl, showStaticImage=$showStaticImage")

        if (videoUrl != null && staticImageUrl != null && showStaticImage) {
            val shouldSwitch = when {
                isVideo -> {
                    // 视频：等待静态图加载完成 AND 视频准备好（且没有错误）
                    val result = staticImageLoaded && videoPrepared && videoError == null
                    LogUtils.d("AnimatedBackground - [LaunchedEffect: switch] 视频切换条件: staticImageLoaded=$staticImageLoaded && videoPrepared=$videoPrepared && videoError==null, result=$result")
                    result
                }

                isGif -> {
                    // GIF：等待静态图加载完成
                    val result = staticImageLoaded
                    LogUtils.d("AnimatedBackground - [LaunchedEffect: switch] GIF切换条件: staticImageLoaded=$staticImageLoaded, result=$result")
                    result
                }

                else -> {
                    LogUtils.d("AnimatedBackground - [LaunchedEffect: switch] 不是视频也不是GIF，不切换")
                    false
                }
            }

            if (shouldSwitch) {
                LogUtils.d("AnimatedBackground - [LaunchedEffect: switch] ✓ 满足切换条件，延迟300ms后切换...")
                delay(300) // 延迟一下，让切换更平滑
                showStaticImage = false
                LogUtils.d("AnimatedBackground - [LaunchedEffect: switch] ✓ 已切换显示动图/视频: isVideo=$isVideo, isGif=$isGif")
            } else if (isVideo && videoError != null) {
                // 视频加载失败，继续显示静态图
                LogUtils.w("AnimatedBackground - [LaunchedEffect: switch] ✗ 视频加载失败，继续显示静态图: $videoError")
            } else {
                LogUtils.d("AnimatedBackground - [LaunchedEffect: switch] ⏳ 等待切换条件满足...")
            }
        } else if (videoUrl != null && staticImageUrl == null) {
            // 没有静态图，直接显示动图/视频（不需要切换）
            LogUtils.d("AnimatedBackground - [LaunchedEffect: switch] 没有静态图，直接显示动图/视频")
            showStaticImage = false
        } else {
            LogUtils.d("AnimatedBackground - [LaunchedEffect: switch] 不满足切换条件: videoUrl=$videoUrl, staticImageUrl=$staticImageUrl, showStaticImage=$showStaticImage")
        }
        LogUtils.d("AnimatedBackground - [LaunchedEffect: switch] ========== 检查完成 ==========")
    }

    Box(modifier = modifier.fillMaxSize()) {
        // 静态背景图（首次加载时显示）
        if (showStaticImage && staticImageUrl != null) {
            LogUtils.d("AnimatedBackground - [StaticImage] 显示静态图: $staticImageUrl")
            AsyncImage(
                modifier = Modifier.fillMaxSize(),
                model = ImageRequest.Builder(context).data(staticImageUrl).build(),
                contentDescription = null,
                contentScale = contentScale,
                onSuccess = {
                    LogUtils.d("AnimatedBackground - [StaticImage: onSuccess] ========== 静态图加载成功 ==========")
                    LogUtils.d("AnimatedBackground - [StaticImage: onSuccess] staticImageUrl: $staticImageUrl")
                    LogUtils.d("AnimatedBackground - [StaticImage: onSuccess] 设置 staticImageLoaded=true")
                    staticImageLoaded = true
                    onStaticImageLoaded()
                    LogUtils.d("AnimatedBackground - [StaticImage: onSuccess] ✓ 静态图已加载完成")
                    LogUtils.d("AnimatedBackground - [StaticImage: onSuccess] ========== 加载完成 ==========")
                },
                onError = {
                    LogUtils.e("AnimatedBackground - [StaticImage: onError] ✗ 静态图加载失败: $staticImageUrl")
                },
            )
        }

        // 动图/视频内容
        // 显示条件：
        // 1. 如果没有静态图，直接显示
        // 2. 如果有静态图，等待静态图加载完成后再显示
        // 3. 如果是视频，还需要等待视频准备好
        val shouldShowVideo = when {
            staticImageUrl == null -> {
                LogUtils.d("AnimatedBackground - [shouldShowVideo] 没有静态图，直接显示")
                true // 没有静态图，直接显示
            }

            isVideo -> {
                val result = !showStaticImage && videoPrepared && videoError == null
                LogUtils.d("AnimatedBackground - [shouldShowVideo] 视频显示条件: !showStaticImage=$!showStaticImage && videoPrepared=$videoPrepared && videoError==null=$videoError, result=$result")
                result // 视频：等待切换且已准备好
            }

            isGif -> {
                val result = !showStaticImage && staticImageLoaded
                LogUtils.d("AnimatedBackground - [shouldShowVideo] GIF显示条件: !showStaticImage=$!showStaticImage && staticImageLoaded=$staticImageLoaded, result=$result")
                result // GIF：等待切换且静态图已加载
            }

            else -> {
                LogUtils.d("AnimatedBackground - [shouldShowVideo] 不是视频也不是GIF，不显示")
                false
            }
        }

        // 视频需要在后台加载，即使不显示也要开始加载
        // 这样可以提前准备好视频，减少等待时间
        val shouldLoadVideo =
            videoUrl != null && isVideo && (staticImageUrl == null || staticImageLoaded)
        LogUtils.d("AnimatedBackground - [shouldLoadVideo] videoUrl=$videoUrl, isVideo=$isVideo, staticImageUrl=$staticImageUrl, staticImageLoaded=$staticImageLoaded, result=$shouldLoadVideo")

        val shouldCreateVideoView =
            videoUrl != null && (shouldShowVideo || (isVideo && shouldLoadVideo))
        LogUtils.d("AnimatedBackground - [shouldCreateVideoView] videoUrl=$videoUrl, shouldShowVideo=$shouldShowVideo, shouldLoadVideo=$shouldLoadVideo, result=$shouldCreateVideoView")

        // 状态变化日志
        LaunchedEffect(
            showStaticImage,
            staticImageLoaded,
            videoPrepared,
            videoError,
            videoPath,
            videoUriSet,
            shouldShowVideo,
            shouldLoadVideo,
            shouldCreateVideoView
        ) {
            LogUtils.d("AnimatedBackground - [State] ========== 状态更新 ==========")
            LogUtils.d("AnimatedBackground - [State] showStaticImage=$showStaticImage")
            LogUtils.d("AnimatedBackground - [State] staticImageLoaded=$staticImageLoaded")
            LogUtils.d("AnimatedBackground - [State] videoPrepared=$videoPrepared")
            LogUtils.d("AnimatedBackground - [State] videoError=$videoError")
            LogUtils.d("AnimatedBackground - [State] videoPath=$videoPath")
            LogUtils.d("AnimatedBackground - [State] videoUriSet=$videoUriSet")
            LogUtils.d("AnimatedBackground - [State] shouldShowVideo=$shouldShowVideo")
            LogUtils.d("AnimatedBackground - [State] shouldLoadVideo=$shouldLoadVideo")
            LogUtils.d("AnimatedBackground - [State] shouldCreateVideoView=$shouldCreateVideoView")
            LogUtils.d("AnimatedBackground - [State] controlledPlayer=${controlledPlayer != null}")
            LogUtils.d("AnimatedBackground - [State] ========== 状态更新完成 ==========")
        }

        if (shouldCreateVideoView) {
            when {
                isVideo -> {
                    // 视频播放 - 使用 ExoPlayer
                    AndroidView(
                        factory = { ctx ->
                            LogUtils.d("AnimatedBackground - [ExoPlayer: factory] ========== 创建 PlayerView ==========")

                            // 创建 ControlledExoPlayer
                            val player = ControlledExoPlayer(
                                context = ctx,
                                onPrepared = {
                                    LogUtils.d("AnimatedBackground - [ExoPlayer: factory: onPrepared] ========== 视频已准备好 ==========")
                                    LogUtils.d("AnimatedBackground - [ExoPlayer: factory: onPrepared] videoUrl: $videoUrl")
                                    LogUtils.d("AnimatedBackground - [ExoPlayer: factory: onPrepared] 设置 videoPrepared=true")
                                    videoPrepared = true
                                    LogUtils.d("AnimatedBackground - [ExoPlayer: factory: onPrepared] ========== 准备完成 ==========")
                                },
                                onError = { errorMsg ->
                                    LogUtils.e("AnimatedBackground - [ExoPlayer: factory: onError] ========== 视频加载错误 ==========")
                                    LogUtils.e("AnimatedBackground - [ExoPlayer: factory: onError] videoUrl: $videoUrl")
                                    LogUtils.e("AnimatedBackground - [ExoPlayer: factory: onError] errorMsg: $errorMsg")
                                    videoError = errorMsg
                                    videoPrepared = false
                                    LogUtils.e("AnimatedBackground - [ExoPlayer: factory: onError] 设置 videoError=$errorMsg, videoPrepared=false")
                                    LogUtils.e("AnimatedBackground - [ExoPlayer: factory: onError] ========== 错误处理完成 ==========")
                                },
                                onPlayComplete = {
                                    LogUtils.d("AnimatedBackground - [ExoPlayer: factory: onPlayComplete] 播放完成回调")
                                    onPlayComplete()
                                }
                            )

                            controlledPlayer = player
                            player.setVideoUrl(videoUrl)

                            // 创建 PlayerView
                            val exoPlayerInstance = player.getPlayer()
                            LogUtils.d("AnimatedBackground - [ExoPlayer: factory] ExoPlayer 实例: ${exoPlayerInstance != null}")

                            PlayerView(ctx).apply {
                                LogUtils.d("AnimatedBackground - [ExoPlayer: factory] PlayerView 创建成功")

                                this.player = exoPlayerInstance
                                LogUtils.d("AnimatedBackground - [ExoPlayer: factory] ExoPlayer 已设置到 PlayerView")

                                useController = false // 隐藏控制器
                                LogUtils.d("AnimatedBackground - [ExoPlayer: factory] 控制器已隐藏")

                                resizeMode =
                                    androidx.media3.ui.AspectRatioFrameLayout.RESIZE_MODE_ZOOM // 填充模式
                                LogUtils.d("AnimatedBackground - [ExoPlayer: factory] 填充模式: RESIZE_MODE_ZOOM")

                                visibility = android.view.View.VISIBLE
                                LogUtils.d("AnimatedBackground - [ExoPlayer: factory] 设置 visibility=VISIBLE")

                                // 如果只是后台加载，隐藏视频
                                if (!shouldShowVideo) {
                                    alpha = 0f
                                    LogUtils.d("AnimatedBackground - [ExoPlayer: factory] 后台加载模式，设置 alpha=0")
                                } else {
                                    alpha = 1f
                                    LogUtils.d("AnimatedBackground - [ExoPlayer: factory] 显示模式，设置 alpha=1")
                                }

                                // 设置媒体项（如果 videoPath 已准备好）
                                val pathToUse = videoPath ?: videoUrl
                                LogUtils.d("AnimatedBackground - [ExoPlayer: factory] pathToUse=$pathToUse, videoPath=$videoPath, videoUrl=$videoUrl")
                                if (pathToUse != null) {
                                    LogUtils.d("AnimatedBackground - [ExoPlayer: factory] 设置媒体项: $pathToUse")
                                    player.setMediaItem(pathToUse)
                                    videoUriSet = true
                                    LogUtils.d("AnimatedBackground - [ExoPlayer: factory] ✓ 媒体项已设置，videoUriSet=true")
                                } else {
                                    LogUtils.w("AnimatedBackground - [ExoPlayer: factory] ⏳ videoPath 未准备好，等待 update 中设置")
                                }

                                // 记录 PlayerView 的最终状态
                                LogUtils.d("AnimatedBackground - [ExoPlayer: factory] PlayerView 最终状态: alpha=$alpha, visibility=$visibility, player=${this.player != null}")
                                LogUtils.d("AnimatedBackground - [ExoPlayer: factory] PlayerView 配置完成")
                            }
                        },
                        modifier = Modifier.fillMaxSize(),
                        update = { playerView ->
                            LogUtils.d("AnimatedBackground - [ExoPlayer: update] ========== update 被调用 ==========")
                            val player = controlledPlayer
                            LogUtils.d("AnimatedBackground - [ExoPlayer: update] controlledPlayer=${player != null}")

                            if (player != null) {
                                val pathToUse = videoPath ?: videoUrl
                                LogUtils.d("AnimatedBackground - [ExoPlayer: update] pathToUse=$pathToUse, videoUriSet=$videoUriSet, shouldShowVideo=$shouldShowVideo")

                                // 更新视频 URI（如果 videoPath 已准备好且还未设置）
                                if (pathToUse != null && !videoUriSet) {
                                    try {
                                        LogUtils.d("AnimatedBackground - [ExoPlayer: update] 设置媒体项: $pathToUse")
                                        player.setMediaItem(pathToUse)
                                        videoUriSet = true

                                        // 如果只是后台加载，隐藏视频
                                        if (!shouldShowVideo) {
                                            playerView.alpha = 0f
                                            LogUtils.d("AnimatedBackground - [ExoPlayer: update] 后台加载模式，设置 alpha=0")
                                        } else {
                                            playerView.alpha = 1f
                                            LogUtils.d("AnimatedBackground - [ExoPlayer: update] 显示模式，设置 alpha=1")
                                        }

                                        LogUtils.d("AnimatedBackground - [ExoPlayer: update] ✓ 媒体项已设置: $pathToUse, videoUriSet=true")
                                    } catch (e: Exception) {
                                        LogUtils.e("AnimatedBackground - [ExoPlayer: update] ✗ 设置媒体项失败: ${e.message}")
                                        LogUtils.e("AnimatedBackground - [ExoPlayer: update] 异常堆栈: ${e.stackTraceToString()}")
                                        videoError = e.message
                                    }
                                } else if (pathToUse == null) {
                                    LogUtils.w("AnimatedBackground - [ExoPlayer: update] ⏳ pathToUse 为 null，等待视频路径准备")
                                } else if (videoUriSet) {
                                    LogUtils.d("AnimatedBackground - [ExoPlayer: update] ✓ 媒体项已设置，跳过")
                                }

                                // 更新显示状态（从后台加载切换到显示）
                                val currentAlpha = playerView.alpha
                                val visibility = playerView.visibility
                                val exoPlayerState = player.getPlayer()?.playbackState
                                val exoPlayerPlayWhenReady = player.getPlayer()?.playWhenReady
                                val exoPlayerIsPlaying = player.getPlayer()?.isPlaying
                                LogUtils.d("AnimatedBackground - [ExoPlayer: update] 当前状态: alpha=$currentAlpha, visibility=$visibility")
                                LogUtils.d("AnimatedBackground - [ExoPlayer: update] ExoPlayer状态: playbackState=$exoPlayerState, playWhenReady=$exoPlayerPlayWhenReady, isPlaying=$exoPlayerIsPlaying")
                                LogUtils.d("AnimatedBackground - [ExoPlayer: update] shouldShowVideo=$shouldShowVideo")

                                if (shouldShowVideo && currentAlpha == 0f) {
                                    LogUtils.d("AnimatedBackground - [ExoPlayer: update] 从后台加载切换到显示，设置 alpha=1")
                                    playerView.alpha = 1f
                                    playerView.visibility = android.view.View.VISIBLE
                                    LogUtils.d("AnimatedBackground - [ExoPlayer: update] ✓ 视频已显示")
                                } else if (!shouldShowVideo && currentAlpha != 0f) {
                                    LogUtils.d("AnimatedBackground - [ExoPlayer: update] 切换到后台加载，设置 alpha=0")
                                    playerView.alpha = 0f
                                }

                                // 确保 PlayerView 可见
                                if (playerView.visibility != android.view.View.VISIBLE) {
                                    LogUtils.w("AnimatedBackground - [ExoPlayer: update] ⚠️ PlayerView 不可见，设置 VISIBLE")
                                    playerView.visibility = android.view.View.VISIBLE
                                }

                                // 如果需要播放且播放次数大于0，触发播放
                                LogUtils.d("AnimatedBackground - [ExoPlayer: update] 检查播放条件: shouldPlay=$shouldPlay, currentPlayCount=$currentPlayCount, videoPath=$videoPath, shouldShowVideo=$shouldShowVideo")
                                if (shouldPlay && currentPlayCount > 0 && videoPath != null && shouldShowVideo) {
                                    LogUtils.d("AnimatedBackground - [ExoPlayer: update] ✓ 满足播放条件，触发播放: playCount=$currentPlayCount")
                                    player.setPlayCount(currentPlayCount)
                                    player.startPlayback()
                                } else {
                                    LogUtils.d("AnimatedBackground - [ExoPlayer: update] ⏳ 不满足播放条件，等待...")
                                }
                            } else {
                                LogUtils.w("AnimatedBackground - [ExoPlayer: update] ✗ controlledPlayer 为 null")
                            }
                            LogUtils.d("AnimatedBackground - [ExoPlayer: update] ========== update 完成 ==========")
                        }
                    )

                    DisposableEffect(videoUrl) {
                        onDispose {
                            LogUtils.d("AnimatedBackground - [DisposableEffect] 释放播放器")
                            controlledPlayer?.release()
                            controlledPlayer = null
                        }
                    }
                }

                isGif -> {
                    // GIF 动图（Coil 自动处理）
                    // 注意：GIF 的播放次数控制通过 LaunchedEffect 中的延时来实现
                    AsyncImage(
                        modifier = Modifier.fillMaxSize(),
                        model = ImageRequest.Builder(context).data(videoUrl).build(),
                        contentDescription = null,
                        contentScale = contentScale,
                    )
                }
            }
        }
    }
}
