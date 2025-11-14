package com.ai.intellimate.ui.components

import ai.sxwl.android.utils.LogUtils
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

/** 判断 URL 是否为视频格式 */
private fun isVideoUrl(url: String?): Boolean {
    if (url.isNullOrBlank()) return false
    val lowerUrl = url.lowercase()
    return lowerUrl.endsWith(".mp4") ||
        lowerUrl.endsWith(".webm") ||
        lowerUrl.contains(".mp4?") ||
        lowerUrl.contains(".webm?")
}

/** 视频背景播放组件
 * 逻辑：
 * 1. 如果有视频URL，始终渲染视频控件，同时显示静态图作为占位符
 * 2. 视频加载完成后，隐藏静态图并播放视频
 * 3. 如果没有视频URL，只显示静态图
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
    onIsPlayingChange: ((Boolean) -> Unit)? = null, // 播放状态变化回调
) {
    val context = LocalContext.current
    val videoCacheManager = remember { VideoCacheManager.getInstance(context) }

    var showStaticImage by remember { mutableStateOf(false) }
    var videoPrepared by remember { mutableStateOf(false) }
    var videoFirstFrameRendered by remember { mutableStateOf(false) } // 视频第一帧是否已渲染
    var targetStaticImageAlpha by remember { mutableFloatStateOf(1f) } // 静态图目标透明度，用于动画
    var exoPlayer by remember { mutableStateOf<ExoPlayer?>(null) }
    var currentPlayCount by remember { mutableIntStateOf(0) }
    var actualPlayCount by remember { mutableIntStateOf(0) }
    var videoPath by remember(videoUrl) { mutableStateOf<String?>(null) }
    var isPlaying by remember { mutableStateOf(false) } // 视频是否正在播放
    var hasPlayCompleted by remember { mutableStateOf(false) } // 是否已经播放完成（达到目标次数）

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
            hasPlayCompleted = false // 重置完成标志
            LogUtils.d("AnimatedBackground - 设置播放次数: $playCount")
        } else {
            currentPlayCount = 0
            hasPlayCompleted = false
        }
    }

    // 当 videoUrl 变化时，重置状态
    // 注意：不在这里释放播放器，让 DisposableEffect 处理，避免黑屏
    LaunchedEffect(videoUrl, staticImageUrl) {
        LogUtils.d(
            "AnimatedBackground - [URL变化] 视频URL变化，重置状态: videoUrl=$videoUrl, staticImageUrl=$staticImageUrl"
        )
        // 如果有视频URL且有静态图，先显示静态图作为占位符
        showStaticImage = videoUrl != null && staticImageUrl != null
        targetStaticImageAlpha = 1f // 重置目标透明度
        videoPrepared = false
        videoFirstFrameRendered = false
        actualPlayCount = 0
        hasPlayCompleted = false // 重置完成标志
        // 暂停播放，但不释放播放器（由 DisposableEffect 处理）
        exoPlayer?.pause()
        exoPlayer?.seekTo(0)
        LogUtils.d("AnimatedBackground - [URL变化] 状态已重置: showStaticImage=$showStaticImage, videoPrepared=false")
    }

    // 确保视频第一帧已渲染：视频准备好后，等待第一帧渲染完成
    // 关键修复：确保在 videoPrepared 变为 true 时能正确触发
    LaunchedEffect(videoPrepared, exoPlayer, videoUrl) {
        LogUtils.d("AnimatedBackground - [第一帧渲染] videoPrepared=$videoPrepared, exoPlayer=${exoPlayer != null}, videoUrl=$videoUrl, videoFirstFrameRendered=$videoFirstFrameRendered")
        if (videoPrepared && exoPlayer != null && videoUrl != null) {
            // 确保视频显示第一帧（不播放）
            exoPlayer?.seekTo(0)
            exoPlayer?.playWhenReady = false
            LogUtils.d("AnimatedBackground - [第一帧渲染] 设置视频到第一帧，playWhenReady=false")

            // 等待更长时间，确保第一帧已完全渲染到屏幕上
            kotlinx.coroutines.delay(200)
            videoFirstFrameRendered = true
            LogUtils.d("AnimatedBackground - [第一帧渲染] ✅ 视频第一帧已渲染完成 (videoPrepared=$videoPrepared, exoPlayer=${exoPlayer != null})")

            // 关键修复：视频第一帧渲染完成后，如果 shouldPlay 为 true 但视频未播放，立即触发播放
            // 这解决了首次进入时，shouldPlay 在 videoPrepared 之前就为 true 的问题
            if (shouldPlay && currentPlayCount > 0 && isCurrentPage && !isPlaying && !hasPlayCompleted) {
                LogUtils.d("AnimatedBackground - [第一帧渲染] ✅ 视频第一帧渲染完成，触发延迟播放: shouldPlay=$shouldPlay, currentPlayCount=$currentPlayCount")
                kotlinx.coroutines.delay(100) // 再等待一小段时间，确保第一帧完全稳定
                if (currentPlayCount > 0 && !isPlaying && !hasPlayCompleted && exoPlayer != null) {
                    actualPlayCount = 0
                    exoPlayer?.seekTo(0)
                    exoPlayer?.playWhenReady = true
                    LogUtils.d("AnimatedBackground - [第一帧渲染] ✅ 已触发延迟播放，playWhenReady=true")
                }
            }
        } else {
            // 只有在 videoUrl 变化时才重置，避免在视频准备过程中误重置
            if (videoUrl == null) {
                videoFirstFrameRendered = false
                LogUtils.d("AnimatedBackground - [第一帧渲染] videoUrl=null, 重置 videoFirstFrameRendered=false")
            }
        }
    }

    // 处理静态图和视频的切换逻辑：视频第一帧渲染完成后，触发动画隐藏静态图
    // 关键修复：不依赖 isVideoCached，只要视频第一帧已渲染就隐藏静态图
    // 因为即使未缓存，视频也能正常播放，只是可能稍慢
    LaunchedEffect(videoFirstFrameRendered, isVideo, videoUrl, staticImageUrl) {
        if (videoUrl != null && staticImageUrl != null && showStaticImage) {
            // 如果视频第一帧已渲染，就触发动画隐藏静态图
            // 不依赖 isVideoCached，因为即使未缓存，视频也能正常显示
            if (isVideo && videoFirstFrameRendered) {
                // 等待一小段时间，确保视频第一帧完全稳定
                kotlinx.coroutines.delay(50)
                // 设置目标透明度为 0，触发 Compose 动画
                targetStaticImageAlpha = 0f
                LogUtils.d("AnimatedBackground - [静态图切换] 触发静态图淡出动画 (videoFirstFrameRendered=$videoFirstFrameRendered)")
            }
        } else if (videoUrl != null && staticImageUrl == null) {
            // 没有静态图，直接显示视频
            showStaticImage = false
            targetStaticImageAlpha = 0f
        } else if (videoUrl == null && staticImageUrl != null) {
            // 没有视频，显示静态图
            showStaticImage = true
            targetStaticImageAlpha = 1f
        }
    }

    // 使用 Compose 动画 API 实现平滑的 alpha 过渡
    // 当 targetStaticImageAlpha 变化时，自动执行动画
    val animatedAlpha by
        animateFloatAsState(
            targetValue = if (showStaticImage) targetStaticImageAlpha else 0f,
            animationSpec =
                tween(
                    durationMillis = 300, // 300ms 的淡出动画
                    easing = FastOutSlowInEasing,
                ),
            label = "staticImageAlpha",
        )

    // 当动画完成后，如果 alpha 为 0，则隐藏静态图组件
    LaunchedEffect(animatedAlpha) {
        if (animatedAlpha <= 0f && showStaticImage) {
            // 延迟一小段时间再隐藏，确保动画完全完成
            kotlinx.coroutines.delay(50)
            showStaticImage = false
            LogUtils.d("AnimatedBackground - 静态图淡出动画完成，隐藏组件")
        }
    }

    // 关键：在 Compose 层面添加裁剪，防止视频超出容器边界
    // 使用 fillMaxWidth() 确保宽度不超过屏幕宽度，防止影响相邻 Page
    Box(modifier = modifier
        .fillMaxWidth()
        .fillMaxSize()
        .clipToBounds()) {

        // 如果有视频URL，创建视频视图
        if (videoUrl != null && isVideo) {
            AndroidView(
                factory = { ctx ->
                    LogUtils.d("AnimatedBackground - 创建新的播放器实例")

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
                                addListener(
                                    object : Player.Listener {
                                        override fun onPlaybackStateChanged(playbackState: Int) {
                                            if (playbackState == Player.STATE_READY) {
                                                if (!videoPrepared) {
                                                    videoPrepared = true
                                                    LogUtils.d("AnimatedBackground - 视频准备完成")
                                                }
                                            } else if (playbackState == Player.STATE_ENDED) {
                                                isPlaying = false
                                                onIsPlayingChange?.invoke(false)
                                                actualPlayCount++
                                                LogUtils.d(
                                                    "AnimatedBackground - 视频播放结束，已播放次数: $actualPlayCount, 目标次数: $currentPlayCount"
                                                )
                                                if (actualPlayCount >= currentPlayCount) {
                                                    pause()
                                                    seekTo(0)
                                                    actualPlayCount = 0
                                                    hasPlayCompleted = true // 标记播放完成
                                                    onPlayComplete()
                                                    LogUtils.d(
                                                        "AnimatedBackground - 播放完成，已达到目标次数: $currentPlayCount"
                                                    )
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

                                        override fun onPlayerError(
                                            error: androidx.media3.common.PlaybackException
                                        ) {
                                            LogUtils.e(
                                                "AnimatedBackground - 视频播放错误: ${error.message}"
                                            )
                                            videoPrepared = false
                                        }
                                    }
                                )
                            }

                    exoPlayer = player

                    // 使用 FrameLayout 包裹 PlayerView，确保 crop 模式不会超出容器边界
                    // 关键：必须严格限制宽度，防止影响相邻 Page
                    val frameLayout =
                        android.widget.FrameLayout(ctx).apply {
                            // 关键：使用 MATCH_PARENT 确保填充父容器，但父容器已经通过 fillMaxWidth() 限制了宽度
                            layoutParams =
                                android.view.ViewGroup.LayoutParams(
                                    android.view.ViewGroup.LayoutParams.MATCH_PARENT,
                                    android.view.ViewGroup.LayoutParams.MATCH_PARENT,
                                )
                            // 关键：启用裁剪，防止视频超出容器边界影响相邻页面
                            clipChildren = true
                            clipToPadding = true
                        }

                    val view =
                        PlayerView(ctx).apply {
                            this.player = player
                            useController = false
                            // 使用 ZOOM 模式（crop），填充整个容器，超出部分裁剪
                            // 这与 ContentScale.Crop 保持一致
                            resizeMode = androidx.media3.ui.AspectRatioFrameLayout.RESIZE_MODE_ZOOM
                            visibility = android.view.View.VISIBLE
                            alpha = 1f // 始终可见

                            // 关键：确保 PlayerView 的布局参数不会超出父容器
                            // 使用 MATCH_PARENT 填充父容器，父容器已经限制了宽度
                            layoutParams =
                                android.widget.FrameLayout.LayoutParams(
                                    android.widget.FrameLayout.LayoutParams.MATCH_PARENT,
                                    android.widget.FrameLayout.LayoutParams.MATCH_PARENT,
                                )
                            // 关键：确保 PlayerView 本身不会超出父容器
                            clipToOutline = true
                        }

                    frameLayout.addView(view)

                    // 设置媒体项：优先使用缓存的本地路径，否则使用原始URL
                    // 如果 isVideoCached 为 true，videoPath 应该已经同步获取到了
                    val pathToUse =
                        if (isVideoCached) {
                            videoPath ?: videoUrl
                        } else {
                            videoUrl // 未缓存时先使用 URL，等缓存准备好后再切换
                        }
                    player.setMediaItem(MediaItem.fromUri(pathToUse))
                    player.prepare()
                    LogUtils.d(
                        "AnimatedBackground - [播放器创建] ✅ 设置视频路径: $pathToUse (factory, isVideoCached=$isVideoCached), playWhenReady=${player.playWhenReady}"
                    )

                    frameLayout
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .fillMaxSize()
                    .clipToBounds(), // 使用 fillMaxWidth() 确保宽度不超过屏幕宽度
                update = {
                    // 更新视频路径（如果变化）：当 videoPath 准备好后，从 URL 切换到缓存路径
                    val pathToUse = videoPath ?: videoUrl
                    if (exoPlayer != null) {
                        val currentMediaItem = exoPlayer?.currentMediaItem
                        val currentMediaId = currentMediaItem?.mediaId
                        // 如果路径变化了（比如从 URL 切换到缓存路径），需要更新
                        if (currentMediaId == null || currentMediaId != pathToUse) {
                            LogUtils.d("AnimatedBackground - [播放器更新] 更新视频路径: $currentMediaId -> $pathToUse")
                            exoPlayer?.setMediaItem(MediaItem.fromUri(pathToUse))
                            exoPlayer?.prepare()
                            LogUtils.d("AnimatedBackground - [播放器更新] ✅ 已更新视频路径并准备播放")
                        } else {
                            LogUtils.d("AnimatedBackground - [播放器更新] 视频路径未变化，跳过更新: $pathToUse")
                        }
                    }
                },
            )

            // 播放控制：当需要播放时，直接播放
            // 注意：如果 shouldPlay 为 false，但视频正在播放中（由 loading 触发），则继续播放到结束
            // 关键修复：添加 isPlaying 和 hasPlayCompleted 到 key 中，确保播放状态变化时也能触发检查
            LaunchedEffect(
                shouldPlay,
                videoPrepared,
                currentPlayCount,
                isCurrentPage,
                exoPlayer,
                isPlaying,
                hasPlayCompleted
            ) {
                LogUtils.d(
                    "AnimatedBackground - [播放控制检查] shouldPlay=$shouldPlay, videoPrepared=$videoPrepared, currentPlayCount=$currentPlayCount, isCurrentPage=$isCurrentPage, exoPlayer=${exoPlayer != null}, isPlaying=$isPlaying, hasPlayCompleted=$hasPlayCompleted"
                )
                if (
                    isCurrentPage &&
                        shouldPlay &&
                        videoPrepared &&
                        currentPlayCount > 0 &&
                        exoPlayer != null &&
                        !hasPlayCompleted
                ) {
                    // 如果视频正在播放中，则不处理（避免打断正在播放的视频）
                    if (!isPlaying) {
                        LogUtils.d("AnimatedBackground - [播放控制] ✅ 开始播放视频，次数: $currentPlayCount, playWhenReady=${exoPlayer?.playWhenReady}")
                        actualPlayCount = 0
                        exoPlayer?.seekTo(0)
                        exoPlayer?.playWhenReady = true
                        LogUtils.d("AnimatedBackground - [播放控制] ✅ 已设置 playWhenReady=true")
                    } else {
                        LogUtils.d("AnimatedBackground - [播放控制] ⏭️ 视频正在播放中，跳过")
                    }
                } else if (!shouldPlay && exoPlayer != null && !isPlaying) {
                    // 只有在视频未播放时才停止，如果正在播放则让它播放到结束
                    LogUtils.d("AnimatedBackground - [播放控制] ⏹️ 停止播放（视频未播放）")
                    exoPlayer?.pause()
                    exoPlayer?.seekTo(0)
                    actualPlayCount = 0
                    hasPlayCompleted = false
                } else if (hasPlayCompleted) {
                    LogUtils.d("AnimatedBackground - [播放控制] ✅ 播放已完成，不再重复播放")
                } else {
                    LogUtils.d(
                        "AnimatedBackground - [播放控制] ❌ 播放条件不满足: shouldPlay=$shouldPlay, videoPrepared=$videoPrepared, currentPlayCount=$currentPlayCount, isCurrentPage=$isCurrentPage, isPlaying=$isPlaying, hasPlayCompleted=$hasPlayCompleted"
                    )
                }
            }

            // 生命周期监听：页面恢复时强制播放（关键：每次 onResume 都会触发）
            // 使用 Unit 作为 key，确保每次 onResume 都会执行，参考 BackgroundVideoPlayer 的实现
            LifecycleResumeEffect(Unit) {
                LogUtils.d(
                    "AnimatedBackground - LifecycleResumeEffect触发: isCurrentPage=$isCurrentPage, shouldPlay=$shouldPlay, videoPrepared=$videoPrepared, currentPlayCount=$currentPlayCount, exoPlayer=${exoPlayer != null}, hasPlayCompleted=$hasPlayCompleted"
                )
                if (
                    isCurrentPage &&
                        shouldPlay &&
                        videoPrepared &&
                        currentPlayCount > 0 &&
                        exoPlayer != null &&
                        !hasPlayCompleted &&
                        !isPlaying
                ) {
                    LogUtils.d(
                        "AnimatedBackground - LifecycleResumeEffect: 强制播放视频，次数: $currentPlayCount"
                    )
                    actualPlayCount = 0
                    exoPlayer?.seekTo(0)
                    exoPlayer?.playWhenReady = true
                } else if (
                    isCurrentPage &&
                        shouldPlay &&
                        currentPlayCount > 0 &&
                        exoPlayer != null &&
                        !videoPrepared
                ) {
                    // 如果视频还没准备好，等待一下再尝试
                    LogUtils.d("AnimatedBackground - LifecycleResumeEffect: 视频未准备好，等待...")
                } else if (hasPlayCompleted) {
                    LogUtils.d("AnimatedBackground - LifecycleResumeEffect: 播放已完成，不再重复播放")
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

            // 在 Compose 层覆盖静态图，使用 Compose 动画实现平滑过渡
            // 关键：静态图作为占位符，覆盖在视频上方，视频加载完成后淡出
            if (showStaticImage && staticImageUrl != null) {
                AsyncImage(
                    modifier = Modifier
                        .fillMaxWidth()
                        .fillMaxSize()
                        .alpha(animatedAlpha), // 使用动画的 alpha 值，alpha=0 时完全透明
                    // 使用 fillMaxWidth() 确保宽度不超过屏幕宽度，防止影响相邻 Page
                    model = ImageRequest.Builder(context).data(staticImageUrl).build(),
                    contentDescription = null,
                    contentScale = contentScale, // 使用 Crop 确保不超出边界
                )
                // 添加日志，追踪静态图显示状态
                LaunchedEffect(showStaticImage, animatedAlpha) {
                    LogUtils.d("AnimatedBackground - [静态图] showStaticImage=$showStaticImage, animatedAlpha=$animatedAlpha")
                }
            }
        } else if (staticImageUrl != null) {
            // 没有视频URL，只显示静态图片
            AsyncImage(
                modifier = Modifier
                    .fillMaxWidth()
                    .fillMaxSize(), // 使用 fillMaxWidth() 确保宽度不超过屏幕宽度
                model = ImageRequest.Builder(context).data(staticImageUrl).build(),
                contentDescription = null,
                contentScale = contentScale, // 使用 Crop 确保不超出边界
            )
        }
    }
}
