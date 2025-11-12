package com.ai.intellimate.ui.components

import ai.sxwl.android.utils.LogUtils
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
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
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.compose.LifecycleResumeEffect
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
import kotlinx.coroutines.withContext
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
 * 视频背景播放组件
 * 简化实现：有视频URL时直接显示视频，不等待静态图
 */
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
) {
    val context = LocalContext.current
    val videoCacheManager = remember { VideoCacheManager.getInstance(context) }

    var showStaticImage by remember { mutableStateOf(false) }
    var staticImageLoaded by remember { mutableStateOf(false) }
    var videoPrepared by remember { mutableStateOf(false) }
    var exoPlayer by remember { mutableStateOf<ExoPlayer?>(null) }
    var currentPlayCount by remember { mutableIntStateOf(0) }
    var actualPlayCount by remember { mutableIntStateOf(0) }
    var videoPath by remember(videoUrl) { mutableStateOf<String?>(null) }

    val isVideo = isVideoUrl(videoUrl)

    // 获取视频路径
    // 如果 isVideoCached 为 true，同步获取路径（避免黑屏）
    // 否则异步获取并预加载
    LaunchedEffect(videoUrl, isVideo, isVideoCached) {
        if (isVideo && videoUrl != null) {
            if (isVideoCached) {
                // 已缓存，同步获取路径（快速显示）
                videoPath = videoCacheManager.getVideoPath(videoUrl)
                LogUtils.d("AnimatedBackground - 同步获取缓存路径: $videoPath")
            } else {
                // 未缓存，异步获取并预加载
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

    // 当 shouldPlay 或 playCount 变化时，更新 currentPlayCount
    LaunchedEffect(shouldPlay, playCount) {
        if (shouldPlay) {
            currentPlayCount = playCount
            LogUtils.d("AnimatedBackground - 设置播放次数: $playCount")
        } else {
            currentPlayCount = 0
        }
    }

    // 当 videoUrl 变化时，重置状态
    // 注意：不在这里释放播放器，让 DisposableEffect 处理，避免黑屏
    LaunchedEffect(videoUrl, staticImageUrl) {
        LogUtils.d("AnimatedBackground - 视频URL变化，重置状态: videoUrl=$videoUrl, staticImageUrl=$staticImageUrl")
        // 如果有视频URL且有静态图，先显示静态图
        showStaticImage = videoUrl != null && staticImageUrl != null
        staticImageLoaded = false
        videoPrepared = false
        actualPlayCount = 0
        // 暂停播放，但不释放播放器（由 DisposableEffect 处理）
        exoPlayer?.pause()
        exoPlayer?.seekTo(0)
    }

    // 处理静态图和视频的切换逻辑：视频准备好后切换到视频
    LaunchedEffect(
        staticImageLoaded,
        videoPrepared,
        isVideo,
        videoUrl,
        staticImageUrl,
        isVideoCached
    ) {
        if (videoUrl != null && staticImageUrl != null && showStaticImage) {
            // 如果视频已准备好且已缓存，切换到视频
            val shouldSwitch = isVideo && staticImageLoaded && videoPrepared && isVideoCached
            if (shouldSwitch) {
                showStaticImage = false
                LogUtils.d("AnimatedBackground - 从静态图切换到视频")
            }
        } else if (videoUrl != null && staticImageUrl == null) {
            // 没有静态图，直接显示视频
            showStaticImage = false
        } else if (videoUrl == null && staticImageUrl != null) {
            // 没有视频，显示静态图
            showStaticImage = true
        }
    }

    // 判断是否应该显示视频
    val shouldShowVideo = when {
        staticImageUrl == null -> true // 没有静态图，直接显示视频
        isVideo -> !showStaticImage && videoPrepared && isVideoCached
        else -> false
    }

    // 静态图和视频的渐变动画
    val staticImageAlpha by animateFloatAsState(
        targetValue = if (showStaticImage && staticImageUrl != null) 1f else 0f,
        animationSpec = tween(durationMillis = 300),
        label = "staticImageAlpha"
    )

    val videoAlpha by animateFloatAsState(
        targetValue = if (shouldShowVideo) 1f else 0f,
        animationSpec = tween(durationMillis = 300),
        label = "videoAlpha"
    )

    // 关键：在 Compose 层面添加裁剪，防止视频超出容器边界
    Box(modifier = modifier
        .fillMaxSize()
        .clipToBounds()) {
        // 显示静态图片（如果有且需要显示，在视频准备好之前显示）
        if (staticImageUrl != null && staticImageAlpha > 0f) {
            AsyncImage(
                modifier = Modifier
                    .fillMaxSize()
                    .alpha(staticImageAlpha),
                model = ImageRequest.Builder(context).data(staticImageUrl).build(),
                contentDescription = null,
                contentScale = contentScale,
                onSuccess = {
                    staticImageLoaded = true
                },
            )
        }

        // 如果有视频URL，创建视频视图
        if (videoUrl != null && isVideo) {
            AndroidView(
                factory = { ctx ->
                    LogUtils.d("AnimatedBackground - 创建新的播放器实例")

                    val okHttpClient = OkHttpClient.Builder()
                        .connectTimeout(30, TimeUnit.SECONDS)
                        .readTimeout(60, TimeUnit.SECONDS)
                        .writeTimeout(30, TimeUnit.SECONDS)
                        .retryOnConnectionFailure(true)
                        .build()

                    val dataSourceFactory = DefaultDataSource.Factory(
                        ctx,
                        OkHttpDataSource.Factory(okHttpClient)
                    )

                    val mediaSourceFactory = DefaultMediaSourceFactory(dataSourceFactory)

                    val player = ExoPlayer.Builder(ctx)
                        .setMediaSourceFactory(mediaSourceFactory)
                        .build()
                        .apply {
                            playWhenReady = false
                            volume = 0f
                            repeatMode = Player.REPEAT_MODE_OFF
                            addListener(object : Player.Listener {
                                override fun onPlaybackStateChanged(playbackState: Int) {
                                    if (playbackState == Player.STATE_READY) {
                                        if (!videoPrepared) {
                                            videoPrepared = true
                                            LogUtils.d("AnimatedBackground - 视频准备完成")
                                        }
                                    } else if (playbackState == Player.STATE_ENDED) {
                                        actualPlayCount++
                                        LogUtils.d("AnimatedBackground - 视频播放结束，已播放次数: $actualPlayCount, 目标次数: $currentPlayCount")
                                        if (actualPlayCount >= currentPlayCount) {
                                            pause()
                                            seekTo(0)
                                            actualPlayCount = 0
                                            onPlayComplete()
                                        } else {
                                            seekTo(0)
                                            playWhenReady = true
                                        }
                                    }
                                }

                                override fun onPlayerError(error: androidx.media3.common.PlaybackException) {
                                    LogUtils.e("AnimatedBackground - 视频播放错误: ${error.message}")
                                    videoPrepared = false
                                }
                            })
                        }

                    exoPlayer = player

                    // 使用 FrameLayout 包裹 PlayerView，确保 crop 模式不会超出容器边界
                    val frameLayout = android.widget.FrameLayout(ctx).apply {
                        layoutParams = android.view.ViewGroup.LayoutParams(
                            android.view.ViewGroup.LayoutParams.MATCH_PARENT,
                            android.view.ViewGroup.LayoutParams.MATCH_PARENT
                        )
                        // 关键：启用裁剪，防止视频超出容器边界影响相邻页面
                        clipChildren = true
                        clipToPadding = true
                    }
                    
                    val view = PlayerView(ctx).apply {
                        this.player = player
                        useController = false
                        // 使用 ZOOM 模式（crop），填充整个容器，超出部分裁剪
                        resizeMode = androidx.media3.ui.AspectRatioFrameLayout.RESIZE_MODE_ZOOM
                        visibility = android.view.View.VISIBLE
                        alpha = 0f // 初始透明，通过动画控制

                        // 确保 PlayerView 的布局参数不会超出父容器
                        layoutParams = android.widget.FrameLayout.LayoutParams(
                            android.widget.FrameLayout.LayoutParams.MATCH_PARENT,
                            android.widget.FrameLayout.LayoutParams.MATCH_PARENT
                        )
                    }

                    frameLayout.addView(view)
                    
                    // 设置媒体项：优先使用缓存的本地路径，否则使用原始URL
                    // 如果 isVideoCached 为 true，videoPath 应该已经同步获取到了
                    val pathToUse = if (isVideoCached) {
                        videoPath ?: videoUrl
                    } else {
                        videoUrl // 未缓存时先使用 URL，等缓存准备好后再切换
                    }
                    if (pathToUse != null) {
                        player.setMediaItem(MediaItem.fromUri(pathToUse))
                        player.prepare()
                        LogUtils.d("AnimatedBackground - 设置视频路径: $pathToUse (factory, isVideoCached=$isVideoCached)")
                    } else {
                        LogUtils.w("AnimatedBackground - 视频路径为空，无法设置媒体项")
                    }

                    frameLayout
                },
                modifier = Modifier
                    .fillMaxSize()
                    .clipToBounds(),
                update = { frameLayout ->
                    // 获取 PlayerView（FrameLayout 的第一个子视图）
                    val playerView = frameLayout.getChildAt(0) as? PlayerView

                    // 更新视频视图的透明度（使用动画值）
                    playerView?.alpha = videoAlpha
                    // visibility 保持 VISIBLE，通过 alpha 控制显示/隐藏
                    
                    // 更新视频路径（如果变化）：当 videoPath 准备好后，从 URL 切换到缓存路径
                    val pathToUse = videoPath ?: videoUrl
                    if (pathToUse != null && exoPlayer != null) {
                        val currentMediaItem = exoPlayer?.currentMediaItem
                        val currentMediaId = currentMediaItem?.mediaId
                        // 如果路径变化了（比如从 URL 切换到缓存路径），需要更新
                        if (currentMediaId == null || currentMediaId != pathToUse) {
                            exoPlayer?.setMediaItem(MediaItem.fromUri(pathToUse))
                            exoPlayer?.prepare()
                            LogUtils.d("AnimatedBackground - 更新视频路径: $pathToUse (update)")
                        }
                    }
                }
            )

            // 播放控制：当需要播放时，直接播放
            LaunchedEffect(shouldPlay, videoPrepared, currentPlayCount, isCurrentPage, exoPlayer) {
                LogUtils.d("AnimatedBackground - 播放控制检查: shouldPlay=$shouldPlay, videoPrepared=$videoPrepared, currentPlayCount=$currentPlayCount, isCurrentPage=$isCurrentPage, exoPlayer=${exoPlayer != null}")
                if (isCurrentPage && shouldPlay && videoPrepared && currentPlayCount > 0 && exoPlayer != null) {
                    LogUtils.d("AnimatedBackground - 开始播放视频，次数: $currentPlayCount")
                    actualPlayCount = 0
                    exoPlayer?.seekTo(0)
                    exoPlayer?.playWhenReady = true
                } else if (!shouldPlay && exoPlayer != null) {
                    LogUtils.d("AnimatedBackground - 停止播放")
                    exoPlayer?.pause()
                    exoPlayer?.seekTo(0)
                    actualPlayCount = 0
                } else {
                    LogUtils.d("AnimatedBackground - 播放条件不满足: shouldPlay=$shouldPlay, videoPrepared=$videoPrepared, currentPlayCount=$currentPlayCount, isCurrentPage=$isCurrentPage")
                }
            }

            // 生命周期监听：页面恢复时强制播放（关键：每次 onResume 都会触发）
            // 使用 Unit 作为 key，确保每次 onResume 都会执行，参考 BackgroundVideoPlayer 的实现
            LifecycleResumeEffect(Unit) {
                LogUtils.d("AnimatedBackground - LifecycleResumeEffect触发: isCurrentPage=$isCurrentPage, shouldPlay=$shouldPlay, videoPrepared=$videoPrepared, currentPlayCount=$currentPlayCount, exoPlayer=${exoPlayer != null}")
                if (isCurrentPage && shouldPlay && videoPrepared && currentPlayCount > 0 && exoPlayer != null) {
                    LogUtils.d("AnimatedBackground - LifecycleResumeEffect: 强制播放视频，次数: $currentPlayCount")
                    actualPlayCount = 0
                    exoPlayer?.seekTo(0)
                    exoPlayer?.playWhenReady = true
                } else if (isCurrentPage && shouldPlay && currentPlayCount > 0 && exoPlayer != null && !videoPrepared) {
                    // 如果视频还没准备好，等待一下再尝试
                    LogUtils.d("AnimatedBackground - LifecycleResumeEffect: 视频未准备好，等待...")
                }
                onPauseOrDispose {
                    LogUtils.d("AnimatedBackground - onPauseOrDispose: 暂停播放")
                    exoPlayer?.pause()
                    exoPlayer?.seekTo(0)
                }
            }

            DisposableEffect(videoUrl) {
                onDispose {
                    LogUtils.d("AnimatedBackground - DisposableEffect: 释放播放器: $videoUrl")
                    exoPlayer?.release()
                    exoPlayer = null
                }
            }
        } else if (staticImageUrl != null) {
            // 没有视频URL，显示静态图片
            AsyncImage(
                modifier = Modifier.fillMaxSize(),
                model = ImageRequest.Builder(context).data(staticImageUrl).build(),
                contentDescription = null,
                contentScale = contentScale,
            )
        }
    }
}
