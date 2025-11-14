package com.ai.intellimate.ui.components

import ai.sxwl.android.data.api.getCdnImageUrl
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
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.dp
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
import coil3.request.crossfade
import coil3.size.Size
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import java.util.concurrent.TimeUnit

// CDN 图片优化参数（与 AgentBackground 保持一致）
// 使用固定参数确保预加载和实际使用的 URL 完全一致，提高缓存命中率
// 80% 质量在清晰度和文件大小之间取得最佳平衡，相比 75% 质量提升明显但文件大小增加有限（约 5-8%）
private const val CDN_IMAGE_QUALITY = 80
private const val CDN_STATIC_BACKGROUND_WIDTH = 1080 // 固定宽度，确保预加载和实际使用 URL 一致

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

    // 关键修复：立即显示静态图（如果有），避免黑屏
    // 初始状态：如果有静态图URL，立即显示；如果有视频URL且有静态图，也立即显示作为占位符
    var showStaticImage by remember(videoUrl, staticImageUrl) {
        mutableStateOf(staticImageUrl != null && (videoUrl == null || isVideoUrl(videoUrl)))
    }
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

    // 确保视频第一帧已渲染：视频准备好后，立即触发第一帧渲染
    // 关键修复：使用更短的延迟，并立即触发第一帧显示
    LaunchedEffect(videoPrepared, exoPlayer, videoUrl) {
        LogUtils.d("AnimatedBackground - [第一帧渲染] videoPrepared=$videoPrepared, exoPlayer=${exoPlayer != null}, videoUrl=$videoUrl, videoFirstFrameRendered=$videoFirstFrameRendered")
        if (videoPrepared && exoPlayer != null && videoUrl != null && !videoFirstFrameRendered) {
            // 确保视频显示第一帧（不播放）
            exoPlayer?.seekTo(0)
            exoPlayer?.playWhenReady = false
            LogUtils.d("AnimatedBackground - [第一帧渲染] 设置视频到第一帧，playWhenReady=false")

            // 关键修复：使用更短的延迟（50ms），快速响应
            // onVideoSizeChanged 回调已经提供了更准确的信号，这里只需要短暂等待确保渲染完成
            kotlinx.coroutines.delay(50) // 减少延迟，快速响应
            if (videoPrepared && exoPlayer != null) {
                videoFirstFrameRendered = true
                LogUtils.d("AnimatedBackground - [第一帧渲染] ✅ 视频第一帧已渲染完成")

                // 关键修复：第一帧渲染完成后，如果 shouldPlay 为 true，立即触发播放
                // 这解决了视频加载完成后没有自动播放的问题
                if (shouldPlay && currentPlayCount > 0 && isCurrentPage && !isPlaying && !hasPlayCompleted) {
                    LogUtils.d("AnimatedBackground - [第一帧渲染] ✅ 第一帧渲染完成，立即触发播放: shouldPlay=$shouldPlay, currentPlayCount=$currentPlayCount")
                    actualPlayCount = 0
                    exoPlayer?.seekTo(0)
                    exoPlayer?.playWhenReady = true
                    LogUtils.d("AnimatedBackground - [第一帧渲染] ✅ 已触发播放，playWhenReady=true")
                }
            }
        } else if (videoUrl == null) {
            // 只有在 videoUrl 变化时才重置，避免在视频准备过程中误重置
            videoFirstFrameRendered = false
            LogUtils.d("AnimatedBackground - [第一帧渲染] videoUrl=null, 重置 videoFirstFrameRendered=false")
        }
    }

    // 处理静态图和视频的切换逻辑：视频第一帧渲染完成后，立即触发动画隐藏静态图
    // 关键修复：不依赖 isVideoCached，只要视频第一帧已渲染就立即隐藏静态图
    LaunchedEffect(videoFirstFrameRendered, isVideo, videoUrl, staticImageUrl) {
        if (videoUrl != null && staticImageUrl != null && showStaticImage) {
            // 如果视频第一帧已渲染，立即触发动画隐藏静态图（不等待额外延迟）
            if (isVideo && videoFirstFrameRendered) {
                // 关键修复：立即触发淡出动画，不等待额外延迟
                targetStaticImageAlpha = 0f
                LogUtils.d("AnimatedBackground - [静态图切换] ✅ 立即触发静态图淡出动画 (videoFirstFrameRendered=$videoFirstFrameRendered)")
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
    // 使用 matchParentSize() 而不是 fillMaxSize()，因为：
    // 1. matchParentSize() 不会影响父 Box 的尺寸测量（父 Box 尺寸由 HorizontalPager 决定）
    // 2. 子元素仅在布局阶段匹配父 Box 的最终尺寸
    // 3. 这符合 BoxScope 的最佳实践，避免子元素影响父容器尺寸
    Box(
        modifier = modifier
            .fillMaxSize()
            .clipToBounds()
    ) {

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

                                                    // 关键修复：视频准备完成后，立即 seekTo(0) 触发第一帧渲染
                                                    // 不等待延迟，直接触发第一帧显示
                                                    seekTo(0)
                                                    playWhenReady = false

                                                    // 使用协程在后台等待第一帧渲染
                                                    // 注意：这里不能直接使用协程，需要在外部 LaunchedEffect 中处理
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

                                        override fun onVideoSizeChanged(videoSize: androidx.media3.common.VideoSize) {
                                            // 关键修复：视频尺寸变化时，说明第一帧可能已经渲染
                                            // 这是一个更准确的信号，比固定延迟更可靠
                                            if (videoPrepared && !videoFirstFrameRendered && videoSize.width > 0 && videoSize.height > 0) {
                                                LogUtils.d("AnimatedBackground - [第一帧渲染] onVideoSizeChanged 触发，视频尺寸: ${videoSize.width}x${videoSize.height}")
                                                // 不在这里直接设置 videoFirstFrameRendered，让 LaunchedEffect 处理
                                                // 但可以触发一次 seekTo(0) 确保第一帧显示
                                                if (playWhenReady == false) {
                                                    seekTo(0)
                                                }
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

                    // 使用 FrameLayout 包裹 PlayerView，确保 crop 模式不会超出容器边界
                    // 关键修复：使用 ConstraintLayout 或 FrameLayout 并严格限制尺寸
                    val frameLayout =
                        android.widget.FrameLayout(ctx).apply {
                            // 关键：使用 MATCH_PARENT 确保填充父容器，但父容器已经通过 layout modifier 限制了宽度
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

                            // 关键：使用 MATCH_PARENT 填充父容器（FrameLayout）
                            // MATCH_PARENT 是最合适的选择，因为：
                            // 1. 自动适应父容器尺寸变化
                            // 2. 父容器已经通过 Compose 的 layout modifier 限制了宽度
                            // 3. 符合 Android 布局最佳实践
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
                    .matchParentSize()
                    .clipToBounds(),
                update = { view ->
                    // 关键修复：在更新时确保视图使用 MATCH_PARENT，自动适应父容器尺寸
                    // 使用 MATCH_PARENT 比设置具体像素值更合适，因为：
                    // 1. 自动适应父容器尺寸变化
                    // 2. 避免硬编码像素值导致的布局问题
                    // 3. 符合 Android 布局最佳实践
                    val layoutParams = view.layoutParams
                    if (layoutParams != null) {
                        // 确保使用 MATCH_PARENT，让系统自动处理尺寸
                        if (layoutParams.width != android.view.ViewGroup.LayoutParams.MATCH_PARENT ||
                            layoutParams.height != android.view.ViewGroup.LayoutParams.MATCH_PARENT
                        ) {
                            layoutParams.width = android.view.ViewGroup.LayoutParams.MATCH_PARENT
                            layoutParams.height = android.view.ViewGroup.LayoutParams.MATCH_PARENT
                            view.layoutParams = layoutParams
                        }
                    }

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
                val density = LocalDensity.current
                val configuration = LocalConfiguration.current

                // 使用固定 CDN 参数，确保与预加载 URL 一致，提高缓存命中率
                val staticImageRequest = remember(staticImageUrl) {
                    val containerWidthPx =
                        with(density) { configuration.screenWidthDp.dp.toPx().toInt() }
                    val containerHeightPx =
                        with(density) { configuration.screenHeightDp.dp.toPx().toInt() }

                    ImageRequest.Builder(context)
                        .data(
                            getCdnImageUrl(
                                staticImageUrl,
                                width = CDN_STATIC_BACKGROUND_WIDTH, // 使用固定宽度，确保预加载和实际使用 URL 一致
                                quality = CDN_IMAGE_QUALITY,
                            ) ?: staticImageUrl
                        )
                        .size(Size(containerWidthPx, containerHeightPx))
                        .crossfade(true) // 启用淡入淡出效果
                        .build()
                }
                AsyncImage(
                    modifier = Modifier
                        .fillMaxWidth()
                        .fillMaxSize()
                        .alpha(animatedAlpha), // 使用动画的 alpha 值，alpha=0 时完全透明
                    model = staticImageRequest,
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
