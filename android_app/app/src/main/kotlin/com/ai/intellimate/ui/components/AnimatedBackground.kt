package com.ai.intellimate.ui.components

import ai.sxwl.android.data.api.getCdnImageUrl
import ai.sxwl.android.utils.LogUtils
import android.graphics.Matrix
import android.graphics.drawable.AnimatedImageDrawable
import android.view.TextureView
import androidx.annotation.OptIn
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.compose.LifecycleResumeEffect
import androidx.media3.common.C
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.common.VideoSize
import androidx.media3.common.util.UnstableApi
import androidx.media3.datasource.DefaultDataSource
import androidx.media3.datasource.okhttp.OkHttpDataSource
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.exoplayer.source.DefaultMediaSourceFactory
import coil3.asDrawable
import coil3.compose.AsyncImage
import coil3.compose.AsyncImagePainter
import coil3.compose.SubcomposeAsyncImage
import coil3.compose.SubcomposeAsyncImageContent
import coil3.request.ImageRequest
import coil3.request.crossfade
import coil3.size.Size
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import java.util.concurrent.TimeUnit

private const val CDN_IMAGE_QUALITY = 80
private const val CDN_STATIC_BACKGROUND_WIDTH = 1080

private fun isVideoUrl(url: String?): Boolean {
    if (url.isNullOrBlank()) return false
    val lowerUrl = url.lowercase()
    return lowerUrl.endsWith(".mp4") ||
        lowerUrl.endsWith(".webm") ||
        lowerUrl.contains(".mp4?") ||
        lowerUrl.contains(".webm?")
}

private fun isAnimatedImageUrl(url: String?): Boolean {
    if (url.isNullOrBlank()) return false
    val lowerUrl = url.lowercase()
    return lowerUrl.endsWith(".gif") ||
        lowerUrl.endsWith(".webp") ||
        lowerUrl.endsWith(".avif") ||
        lowerUrl.contains(".gif?") ||
        lowerUrl.contains(".webp?") ||
        lowerUrl.contains(".avif?")
}

private fun isAnimatedUrl(url: String?): Boolean {
    return isVideoUrl(url) || isAnimatedImageUrl(url)
}

@OptIn(UnstableApi::class)
@Composable
fun AnimatedBackground(
    videoUrl: String?,
    staticImageUrl: String?,
    modifier: Modifier = Modifier,
    contentScale: ContentScale = ContentScale.Crop,
    shouldPlay: Boolean = false,
    playCount: Int = 1,
    isVideoCached: Boolean = false,
    isCurrentPage: Boolean = true,
    onPlayComplete: () -> Unit = {},
    onIsPlayingChange: ((Boolean) -> Unit)? = null,
) {
    val context = LocalContext.current
    val videoCacheManager = remember { VideoCacheManager.getInstance(context) }

    var showStaticImage by remember(videoUrl, staticImageUrl) {
        mutableStateOf(staticImageUrl != null && (videoUrl == null || isAnimatedUrl(videoUrl)))
    }
    var videoPrepared by remember { mutableStateOf(false) }
    var videoFirstFrameRendered by remember { mutableStateOf(false) }
    var animatedImageLoaded by remember { mutableStateOf(false) }
    var targetStaticImageAlpha by remember { mutableFloatStateOf(1f) }
    var exoPlayer by remember { mutableStateOf<ExoPlayer?>(null) }
    var currentPlayCount by remember { mutableIntStateOf(0) }
    var actualPlayCount by remember { mutableIntStateOf(0) }
    var videoPath by remember(videoUrl) { mutableStateOf<String?>(null) }
    var isPlaying by remember { mutableStateOf(false) }
    var hasPlayCompleted by remember { mutableStateOf(false) }
    var animatedImageDrawable by remember { mutableStateOf<AnimatedImageDrawable?>(null) }

    val isVideo = isVideoUrl(videoUrl)
    val isAnimatedImage = isAnimatedImageUrl(videoUrl)

    LaunchedEffect(videoUrl, isVideo, isVideoCached) {
            if (isVideo && videoUrl != null) {
                if (isVideoCached) {
                    videoPath = videoCacheManager.getVideoPath(videoUrl)
                } else {
                    withContext(Dispatchers.IO) {
                        videoPath = videoCacheManager.getVideoPath(videoUrl)
                        if (!videoCacheManager.isCached(videoUrl)) {
                            try {
                                videoCacheManager.preloadVideo(videoUrl)
                            } catch (e: Exception) {
                                LogUtils.e("AnimatedBackground - 预加载视频失败: ${e.message}")
                            }
                        }
                    }
                }
            } else {
                videoPath = null
            }
    }

    LaunchedEffect(shouldPlay, playCount) {
        if (shouldPlay) {
            currentPlayCount = playCount
            hasPlayCompleted = false
            actualPlayCount = 0
        } else {
            currentPlayCount = 0
            hasPlayCompleted = false
        }
    }

    LaunchedEffect(videoUrl, staticImageUrl) {
        if (videoUrl != null && staticImageUrl != null) {
            showStaticImage = true
            targetStaticImageAlpha = 1f
        } else if (videoUrl == null && staticImageUrl != null) {
            showStaticImage = true
            targetStaticImageAlpha = 1f
        } else {
            showStaticImage = false
            targetStaticImageAlpha = 0f
        }
        videoPrepared = false
        videoFirstFrameRendered = false
        animatedImageLoaded = false
        actualPlayCount = 0
        hasPlayCompleted = false
        animatedImageDrawable?.stop()
        animatedImageDrawable = null
        isPlaying = false
        onIsPlayingChange?.invoke(false)
        exoPlayer?.pause()
        exoPlayer?.seekTo(0)
    }

    LaunchedEffect(videoPrepared, exoPlayer, videoUrl) {
        if (videoPrepared && exoPlayer != null && videoUrl != null && !videoFirstFrameRendered) {
            exoPlayer?.seekTo(0)
            exoPlayer?.playWhenReady = false
            kotlinx.coroutines.delay(50)
            if (videoPrepared && exoPlayer != null) {
                videoFirstFrameRendered = true
                if (shouldPlay && currentPlayCount > 0 && isCurrentPage && !isPlaying && !hasPlayCompleted) {
                    actualPlayCount = 0
                    exoPlayer?.seekTo(0)
                    exoPlayer?.playWhenReady = true
                }
            }
        } else if (videoUrl == null) {
            videoFirstFrameRendered = false
        }
    }

    LaunchedEffect(videoFirstFrameRendered, animatedImageLoaded, isVideo, isAnimatedImage, videoUrl, staticImageUrl, shouldPlay, currentPlayCount, isPlaying) {
        if (videoUrl != null && staticImageUrl != null && showStaticImage) {
            val animationReady = (isVideo && videoFirstFrameRendered) || (isAnimatedImage && animatedImageLoaded)
            if (animationReady && shouldPlay && currentPlayCount > 0 && isPlaying) {
                targetStaticImageAlpha = 0f
            }
        } else if (videoUrl != null && staticImageUrl == null) {
            showStaticImage = false
            targetStaticImageAlpha = 0f
        } else if (videoUrl == null && staticImageUrl != null) {
            showStaticImage = true
            targetStaticImageAlpha = 1f
        }
    }

    val animatedAlpha by animateFloatAsState(
        targetValue = if (showStaticImage) targetStaticImageAlpha else 0f,
        animationSpec = tween(durationMillis = 300, easing = FastOutSlowInEasing),
        label = "staticImageAlpha",
    )

    LaunchedEffect(animatedAlpha) {
        if (animatedAlpha <= 0f && showStaticImage) {
            kotlinx.coroutines.delay(50)
            showStaticImage = false
        }
    }

    var textureViewRef by remember { mutableStateOf<TextureView?>(null) }

    Box(modifier = modifier.fillMaxSize().clipToBounds()) {
        if (videoUrl != null && isVideo) {
            AndroidView(
                factory = { ctx ->
                    val okHttpClient =
                        OkHttpClient.Builder()
                            .connectTimeout(30, TimeUnit.SECONDS)
                            .readTimeout(60, TimeUnit.SECONDS)
                            .writeTimeout(30, TimeUnit.SECONDS)
                            .retryOnConnectionFailure(true)
                            .build()

                    val dataSourceFactory =
                        DefaultDataSource.Factory(ctx, OkHttpDataSource.Factory(okHttpClient))

                    val mediaSourceFactory = DefaultMediaSourceFactory(dataSourceFactory)

                    val player =
                        ExoPlayer.Builder(ctx)
                            .setMediaSourceFactory(mediaSourceFactory)
                            .build()
                            .apply {
                                playWhenReady = false
                                volume = 0f
                                repeatMode = Player.REPEAT_MODE_OFF
                                videoScalingMode = C.VIDEO_SCALING_MODE_SCALE_TO_FIT_WITH_CROPPING
                                addListener(
                                    object : Player.Listener {
                                        override fun onPlaybackStateChanged(playbackState: Int) {
                                            if (playbackState == Player.STATE_READY) {
                                                if (!videoPrepared) {
                                                    videoPrepared = true
                                                    seekTo(0)
                                                    playWhenReady = false
                                                }
                                            } else if (playbackState == Player.STATE_ENDED) {
                                                isPlaying = false
                                                onIsPlayingChange?.invoke(false)
                                                actualPlayCount++
                                                if (actualPlayCount >= currentPlayCount) {
                                                    pause()
                                                    seekTo(0)
                                                    actualPlayCount = 0
                                                    hasPlayCompleted = true
                                                    onPlayComplete()
                                                } else {
                                                    seekTo(0)
                                                    playWhenReady = true
                                                }
                                            } else if (playbackState == Player.STATE_IDLE) {
                                                isPlaying = false
                                                onIsPlayingChange?.invoke(false)
                                            }
                                        }

                                        override fun onIsPlayingChanged(playing: Boolean) {
                                            isPlaying = playing
                                            onIsPlayingChange?.invoke(playing)
                                        }

                                        override fun onVideoSizeChanged(videoSize: VideoSize) {
                                            if (videoPrepared && !videoFirstFrameRendered && videoSize.width > 0 && videoSize.height > 0) {
                                                if (!playWhenReady) {
                                                    seekTo(0)
                                                }
                                            }
                                            val vW = textureViewRef?.width?.toFloat()
                                            val vH = textureViewRef?.height?.toFloat()
                                            val vidW = videoSize.width.toFloat()
                                            val vidH = videoSize.height.toFloat()
                                            if (vW != null && vH != null) {
                                                val matrix = Matrix()
                                                textureViewRef?.getTransform(matrix)
                                                val wFinal = (vidW / vidH) * vH
                                                val ratio = wFinal / vW
                                                matrix.setScale(ratio, 1f, vW / 2, vH / 2)
                                                textureViewRef?.setTransform(matrix)
                                                textureViewRef?.invalidate()
                                            }
                                        }

                                        override fun onPlayerError(
                                            error: androidx.media3.common.PlaybackException
                                        ) {
                                            LogUtils.e(
                                                "AnimatedBackground - 视频播放错误: ${error.message}"
                                            )
                                            videoPrepared = false
                                            videoFirstFrameRendered = false
                                        }
                                    }
                                )
                            }

                    exoPlayer = player

                    val textureView = TextureView(ctx).apply {
                        clipToOutline = true
                        textureViewRef = this
                        player.videoScalingMode = C.VIDEO_SCALING_MODE_SCALE_TO_FIT_WITH_CROPPING
                        player.setVideoTextureView(this)
                        player.videoScalingMode = C.VIDEO_SCALING_MODE_SCALE_TO_FIT_WITH_CROPPING
                    }

                    val pathToUse = if (isVideoCached) videoPath ?: videoUrl else videoUrl
                    player.setMediaItem(MediaItem.fromUri(pathToUse))
                    player.prepare()

                    textureView
                },
                modifier = Modifier.matchParentSize().clipToBounds(),
                update = { view ->
                    val textureView = view as? TextureView
                    textureView?.let {
                        exoPlayer?.let { player ->
                            player.setVideoTextureView(it)
                            player.videoScalingMode = C.VIDEO_SCALING_MODE_SCALE_TO_FIT_WITH_CROPPING
                            val pathToUse = videoPath ?: videoUrl
                            val currentMediaId = player.currentMediaItem?.mediaId
                            if (currentMediaId == null || currentMediaId != pathToUse) {
                                player.setMediaItem(MediaItem.fromUri(pathToUse))
                                player.prepare()
                            }
                        }
                    }
                },
            )

            LaunchedEffect(shouldPlay, videoPrepared, currentPlayCount, isCurrentPage, exoPlayer) {
                if (isCurrentPage && shouldPlay && videoPrepared && currentPlayCount > 0 && exoPlayer != null && !hasPlayCompleted) {
                    if (!isPlaying) {
                        actualPlayCount = 0
                        exoPlayer?.seekTo(0)
                        exoPlayer?.playWhenReady = true
                    }
                } else if (!shouldPlay && exoPlayer != null && !isPlaying) {
                    exoPlayer?.pause()
                    exoPlayer?.seekTo(0)
                    actualPlayCount = 0
                    hasPlayCompleted = false
                }
            }

            LifecycleResumeEffect(Unit) {
                if (isCurrentPage && shouldPlay && !hasPlayCompleted && videoPrepared && currentPlayCount > 0 && exoPlayer != null && !isPlaying) {
                    actualPlayCount = 0
                    exoPlayer?.seekTo(0)
                    exoPlayer?.playWhenReady = true
                }
                onPauseOrDispose {
                    exoPlayer?.pause()
                    exoPlayer?.seekTo(0)
                }
            }

            DisposableEffect(videoUrl) {
                onDispose {
                    exoPlayer?.let { player ->
                        player.clearVideoTextureView(null)
                        player.release()
                    }
                    exoPlayer = null
                }
            }

            if (showStaticImage && staticImageUrl != null) {
                val density = LocalDensity.current
                val configuration = LocalConfiguration.current

                // 使用固定 CDN 参数，确保与预加载 URL 一致，提高缓存命中率
                val staticImageRequest =
                    remember(staticImageUrl) {
                        val containerWidthPx =
                            with(density) { configuration.screenWidthDp.dp.toPx().toInt() }
                        val containerHeightPx =
                            with(density) { configuration.screenHeightDp.dp.toPx().toInt() }

                        ImageRequest.Builder(context)
                            .data(getCdnImageUrl(staticImageUrl, width = CDN_STATIC_BACKGROUND_WIDTH, quality = CDN_IMAGE_QUALITY) ?: staticImageUrl)
                            .size(Size(containerWidthPx, containerHeightPx))
                            .crossfade(true)
                            .build()
                    }
                AsyncImage(
                    modifier = Modifier.fillMaxWidth().fillMaxSize().alpha(animatedAlpha),
                    model = staticImageRequest,
                    contentDescription = null,
                    contentScale = contentScale,
                )
            }
        } else if (videoUrl != null && isAnimatedImage) {
            val density = LocalDensity.current
            val configuration = LocalConfiguration.current
            val animatedImageRequest = remember(videoUrl) {
                val containerWidthPx = with(density) { configuration.screenWidthDp.dp.toPx().toInt() }
                val containerHeightPx = with(density) { configuration.screenHeightDp.dp.toPx().toInt() }
                val imageUrl = try {
                    getCdnImageUrl(videoUrl, width = CDN_STATIC_BACKGROUND_WIDTH, quality = CDN_IMAGE_QUALITY) ?: videoUrl
                } catch (e: Exception) {
                    videoUrl
                }
                ImageRequest.Builder(context)
                    .data(imageUrl)
                    .size(Size(containerWidthPx, containerHeightPx))
                    .crossfade(true)
                    .build()
            }

            val animatedImageRequestWithRepeatCount = remember(videoUrl, animatedImageRequest) {
                animatedImageRequest
            }

            SubcomposeAsyncImage(
                modifier = Modifier.matchParentSize().clipToBounds(),
                model = animatedImageRequestWithRepeatCount,
                contentDescription = null,
                contentScale = contentScale,
                onState = { state ->
                    if (state is AsyncImagePainter.State.Success) {
                        val drawable = state.result.image.asDrawable(context.resources)
                        if (drawable is AnimatedImageDrawable && animatedImageDrawable != drawable) {
                            animatedImageDrawable = drawable
                        }
                        if (!animatedImageLoaded) {
                            animatedImageLoaded = true
                        }
                    } else if (state is AsyncImagePainter.State.Error) {
                        LogUtils.e("AnimatedBackground - 动图加载失败: $videoUrl")
                    }
                },
            ) {
                SubcomposeAsyncImageContent()
            }

            LaunchedEffect(shouldPlay, isCurrentPage, animatedImageLoaded, animatedImageDrawable, currentPlayCount, hasPlayCompleted) {
                if (isCurrentPage && shouldPlay && animatedImageLoaded && currentPlayCount > 0 && !hasPlayCompleted && animatedImageDrawable != null) {
                    val drawable = animatedImageDrawable ?: return@LaunchedEffect
                    if (!drawable.isRunning) {
                        drawable.repeatCount = 1
                        drawable.start()
                        isPlaying = true
                        onIsPlayingChange?.invoke(true)
                    }
                } else if (!shouldPlay && !isPlaying) {
                    animatedImageDrawable?.stop()
                    isPlaying = false
                    onIsPlayingChange?.invoke(false)
                }
            }

            LaunchedEffect(animatedImageDrawable, hasPlayCompleted, shouldPlay, currentPlayCount) {
                if (animatedImageDrawable != null && !hasPlayCompleted && shouldPlay && currentPlayCount > 0) {
                    val drawable = animatedImageDrawable ?: return@LaunchedEffect
                    while (!hasPlayCompleted && actualPlayCount < currentPlayCount && shouldPlay) {
                        kotlinx.coroutines.delay(100)
                        if (!drawable.isRunning && actualPlayCount < currentPlayCount) {
                            actualPlayCount++
                            if (actualPlayCount >= currentPlayCount) {
                                hasPlayCompleted = true
                                isPlaying = false
                                onIsPlayingChange?.invoke(false)
                                drawable.stop()
                                onPlayComplete()
                            } else if (shouldPlay) {
                                drawable.repeatCount = 1
                                drawable.start()
                                isPlaying = true
                                onIsPlayingChange?.invoke(true)
                            } else {
                                break
                            }
                        }
                    }
                }
            }

            if (showStaticImage && staticImageUrl != null) {
                val staticImageRequest = remember(staticImageUrl) {
                    val containerWidthPx = with(density) { configuration.screenWidthDp.dp.toPx().toInt() }
                    val containerHeightPx = with(density) { configuration.screenHeightDp.dp.toPx().toInt() }
                    ImageRequest.Builder(context)
                        .data(getCdnImageUrl(staticImageUrl, width = CDN_STATIC_BACKGROUND_WIDTH, quality = CDN_IMAGE_QUALITY) ?: staticImageUrl)
                        .size(Size(containerWidthPx, containerHeightPx))
                        .crossfade(true)
                        .build()
                }
                AsyncImage(
                    modifier = Modifier.fillMaxWidth().fillMaxSize().alpha(animatedAlpha),
                    model = staticImageRequest,
                    contentDescription = null,
                    contentScale = contentScale,
                )
            }
        } else if (staticImageUrl != null) {
            AsyncImage(
                modifier = Modifier.fillMaxWidth().fillMaxSize(),
                model = ImageRequest.Builder(context).data(staticImageUrl).build(),
                contentDescription = null,
                contentScale = contentScale,
            )
        }
    }
}
