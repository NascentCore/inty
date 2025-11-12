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
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import okhttp3.OkHttpClient

/** 判断 URL 是否为视频格式 */
private fun isVideoUrl(url: String?): Boolean {
    if (url.isNullOrBlank()) return false
    val lowerUrl = url.lowercase()
    return lowerUrl.endsWith(".mp4") ||
        lowerUrl.endsWith(".webm") ||
        lowerUrl.contains(".mp4?") ||
        lowerUrl.contains(".webm?")
}

/** 判断 URL 是否为 GIF 格式 */
private fun isGifUrl(url: String?): Boolean {
    if (url.isNullOrBlank()) return false
    val lowerUrl = url.lowercase()
    return lowerUrl.endsWith(".gif") || lowerUrl.contains(".gif?")
}

/** 基于 ExoPlayer 的视频播放器，支持播放次数控制和错误处理 */
private class ControlledExoPlayer(
    context: Context,
    private val onPrepared: () -> Unit,
    private val onError: (String) -> Unit,
    private val onPlayComplete: () -> Unit,
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
            val okHttpClient =
                OkHttpClient.Builder()
                    .connectTimeout(30, TimeUnit.SECONDS)
                    .readTimeout(60, TimeUnit.SECONDS)
                    .writeTimeout(30, TimeUnit.SECONDS)
                    .retryOnConnectionFailure(true)
                    .build()

            val dataSourceFactory =
                DefaultDataSource.Factory(context, OkHttpDataSource.Factory(okHttpClient))

            val mediaSourceFactory = DefaultMediaSourceFactory(dataSourceFactory)

            exoPlayer =
                ExoPlayer.Builder(context).setMediaSourceFactory(mediaSourceFactory).build().apply {
                    addListener(this@ControlledExoPlayer)
                    playWhenReady = false
                    volume = 0f
                    repeatMode = Player.REPEAT_MODE_OFF
                }
        } catch (e: Exception) {
            LogUtils.e("AnimatedBackground - ExoPlayer 初始化失败: ${e.message}")
            onError("播放器初始化失败: ${e.message}")
        }
    }

    fun setVideoUrl(url: String) {
        videoUrl = url
    }

    fun setPlayCount(count: Int) {
        targetPlayCount = count
        playCount = 0
    }

    fun setMediaItem(uri: String) {
        try {
            val mediaItem = MediaItem.fromUri(uri)
            exoPlayer?.setMediaItem(mediaItem)
            exoPlayer?.prepare()
        } catch (e: Exception) {
            LogUtils.e("AnimatedBackground - 设置媒体项失败: ${e.message}")
            onError("设置媒体项失败: ${e.message}")
        }
    }

    fun startPlayback() {
        if (isPrepared && playCount < targetPlayCount) {
            try {
                exoPlayer?.playWhenReady = true
            } catch (e: Exception) {
                LogUtils.e("AnimatedBackground - 播放失败: ${e.message}")
                onError("播放失败: ${e.message}")
            }
        }
    }

    fun resetPlayback() {
        try {
            exoPlayer?.pause()
            exoPlayer?.seekTo(0)
            playCount = 0
        } catch (e: Exception) {
            LogUtils.e("AnimatedBackground - 重置失败: ${e.message}")
        }
    }

    fun getPlayer(): ExoPlayer? = exoPlayer

    fun release() {
        try {
            exoPlayer?.removeListener(this)
            exoPlayer?.release()
            exoPlayer = null
        } catch (e: Exception) {
            LogUtils.e("AnimatedBackground - 释放失败: ${e.message}")
        }
    }

    override fun onPlaybackStateChanged(playbackState: Int) {
        when (playbackState) {
            Player.STATE_READY -> {
                if (!isPrepared) {
                    isPrepared = true
                    onPrepared()
                }
            }

            Player.STATE_ENDED -> {
                playCount++
                if (playCount >= targetPlayCount) {
                    resetPlayback()
                    onPlayComplete()
                } else {
                    exoPlayer?.seekTo(0)
                    exoPlayer?.playWhenReady = true
                }
            }
        }
    }

    override fun onPlayerError(error: androidx.media3.common.PlaybackException) {
        val errorMsg = "视频播放错误: ${error.message}, errorCode=${error.errorCode}"
        isPrepared = false
        onError(errorMsg)
    }
}

/** 动图/视频背景播放组件 */
@Composable
fun AnimatedBackground(
    videoUrl: String?,
    staticImageUrl: String?,
    modifier: Modifier = Modifier,
    contentScale: ContentScale = ContentScale.Crop,
    shouldPlay: Boolean = false,
    playCount: Int = 1,
    onPlayComplete: () -> Unit = {},
) {
    val context = LocalContext.current
    val videoCacheManager = remember { VideoCacheManager.getInstance(context) }

    var showStaticImage by remember { mutableStateOf(staticImageUrl != null) }
    var staticImageLoaded by remember { mutableStateOf(false) }
    var videoPrepared by remember { mutableStateOf(false) }
    var controlledPlayer by remember { mutableStateOf<ControlledExoPlayer?>(null) }
    var currentPlayCount by remember { mutableIntStateOf(0) }
    var videoError by remember { mutableStateOf<String?>(null) }
    var videoPath by remember(videoUrl) { mutableStateOf<String?>(null) }
    var videoUriSet by remember { mutableStateOf(false) }

    val isVideo = isVideoUrl(videoUrl)
    val isGif = isGifUrl(videoUrl)

    LaunchedEffect(videoUrl, isVideo) {
        if (isVideo && videoUrl != null) {
            videoPath = videoCacheManager.getVideoPath(videoUrl)
            if (!videoCacheManager.isCached(videoUrl)) {
                launch(Dispatchers.IO) { videoCacheManager.preloadVideo(videoUrl) }
            }
        } else {
            videoPath = null
        }
    }

    LaunchedEffect(
        shouldPlay,
        playCount,
        videoUrl,
        isVideo,
        isGif,
        videoPath,
        controlledPlayer,
        videoPrepared,
    ) {
        if (shouldPlay && (isVideo || isGif)) {
            currentPlayCount = playCount
            if (isVideo && videoPath != null && controlledPlayer != null) {
                delay(500)
                if (videoPrepared) {
                    controlledPlayer?.setPlayCount(playCount)
                    controlledPlayer?.startPlayback()
                }
            }
            if (isGif && playCount > 0) {
                val estimatedDuration = 2000L * playCount
                delay(estimatedDuration)
                onPlayComplete()
            }
        } else if (!shouldPlay && isVideo && controlledPlayer != null) {
            controlledPlayer?.resetPlayback()
        }
    }

    LaunchedEffect(videoPrepared, shouldPlay, currentPlayCount, controlledPlayer) {
        if (
            videoPrepared &&
                shouldPlay &&
                currentPlayCount > 0 &&
                controlledPlayer != null &&
                isVideo
        ) {
            delay(100)
            controlledPlayer?.setPlayCount(currentPlayCount)
            controlledPlayer?.startPlayback()
        }
    }

    LaunchedEffect(videoUrl, staticImageUrl) {
        showStaticImage = staticImageUrl != null
        staticImageLoaded = false
        videoPrepared = false
        videoUriSet = false
        videoError = null
        controlledPlayer?.resetPlayback()
    }

    LaunchedEffect(
        staticImageLoaded,
        videoPrepared,
        isVideo,
        isGif,
        videoError,
        videoUrl,
        staticImageUrl,
    ) {
        if (videoUrl != null && staticImageUrl != null && showStaticImage) {
            val shouldSwitch =
                when {
                    isVideo -> staticImageLoaded && videoPrepared && videoError == null
                    isGif -> staticImageLoaded
                    else -> false
                }

            if (shouldSwitch) {
                delay(300)
                showStaticImage = false
            }
        } else if (videoUrl != null && staticImageUrl == null) {
            showStaticImage = false
        }
    }

    Box(modifier = modifier.fillMaxSize()) {
        if (showStaticImage && staticImageUrl != null) {
            AsyncImage(
                modifier = Modifier.fillMaxSize(),
                model = ImageRequest.Builder(context).data(staticImageUrl).build(),
                contentDescription = null,
                contentScale = contentScale,
                onSuccess = { staticImageLoaded = true },
            )
        }

        val shouldShowVideo =
            when {
                staticImageUrl == null -> true
                isVideo -> !showStaticImage && videoPrepared && videoError == null
                isGif -> !showStaticImage && staticImageLoaded
                else -> false
            }

        val shouldLoadVideo =
            videoUrl != null && isVideo && (staticImageUrl == null || staticImageLoaded)
        val shouldCreateVideoView =
            videoUrl != null && (shouldShowVideo || (isVideo && shouldLoadVideo))

        if (shouldCreateVideoView) {
            when {
                isVideo -> {
                    AndroidView(
                        factory = { ctx ->
                            val player =
                                ControlledExoPlayer(
                                    context = ctx,
                                    onPrepared = { videoPrepared = true },
                                    onError = { errorMsg ->
                                        videoError = errorMsg
                                        videoPrepared = false
                                    },
                                    onPlayComplete = { onPlayComplete() },
                                )

                            controlledPlayer = player
                            player.setVideoUrl(videoUrl ?: "")

                            val exoPlayerInstance = player.getPlayer()
                            PlayerView(ctx).apply {
                                this.player = exoPlayerInstance
                                useController = false
                                resizeMode =
                                    androidx.media3.ui.AspectRatioFrameLayout.RESIZE_MODE_ZOOM
                                visibility = android.view.View.VISIBLE
                                alpha = if (!shouldShowVideo) 0f else 1f

                                val pathToUse = videoPath ?: videoUrl
                                if (pathToUse != null) {
                                    player.setMediaItem(pathToUse)
                                    videoUriSet = true
                                }
                            }
                        },
                        modifier = Modifier.fillMaxSize(),
                        update = { playerView ->
                            val player = controlledPlayer
                            if (player != null) {
                                val pathToUse = videoPath ?: videoUrl
                                if (pathToUse != null && !videoUriSet) {
                                    try {
                                        player.setMediaItem(pathToUse)
                                        videoUriSet = true
                                        playerView.alpha = if (!shouldShowVideo) 0f else 1f
                                    } catch (e: Exception) {
                                        videoError = e.message
                                    }
                                }

                                if (shouldShowVideo && playerView.alpha == 0f) {
                                    playerView.alpha = 1f
                                    playerView.visibility = android.view.View.VISIBLE
                                } else if (!shouldShowVideo && playerView.alpha != 0f) {
                                    playerView.alpha = 0f
                                }

                                if (playerView.visibility != android.view.View.VISIBLE) {
                                    playerView.visibility = android.view.View.VISIBLE
                                }

                                if (
                                    shouldPlay &&
                                        currentPlayCount > 0 &&
                                        videoPath != null &&
                                        shouldShowVideo
                                ) {
                                    player.setPlayCount(currentPlayCount)
                                    player.startPlayback()
                                }
                            }
                        },
                    )

                    DisposableEffect(videoUrl) {
                        onDispose {
                            controlledPlayer?.release()
                            controlledPlayer = null
                        }
                    }
                }

                isGif -> {
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
