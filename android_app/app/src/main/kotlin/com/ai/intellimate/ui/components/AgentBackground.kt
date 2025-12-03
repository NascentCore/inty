package com.ai.intellimate.ui.components

import ai.sxwl.android.data.api.getCdnImageUrl
import ai.sxwl.android.data.api.model.AgentConstants
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.utils.LogUtils
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import coil3.compose.AsyncImage
import coil3.request.ImageRequest
import coil3.request.crossfade
import coil3.size.Size
import com.ai.intellimate.R

// CDN 图片优化参数
// 使用固定参数确保预加载和实际使用的 URL 完全一致，提高缓存命中率
// 1080px 宽度适用于大多数 Android 设备（大多数设备宽度在 360-480dp，转换为 px 约 1080-1440px）
// 80% 质量在清晰度和文件大小之间取得最佳平衡，相比 75% 质量提升明显但文件大小增加有限（约 5-8%）
private const val CDN_IMAGE_QUALITY = 80
private const val CDN_STATIC_BACKGROUND_WIDTH = 1080 // 固定宽度，确保预加载和实际使用 URL 一致

private const val TOP_GRADIENT_HEIGHT_DP = 120
private const val BOTTOM_GRADIENT_HEIGHT_DP = 300

private const val VIDEO_FIRST_PLAY_COUNT = 2 // 首次进入界面播放次数
private const val VIDEO_MESSAGE_PLAY_COUNT = 1 // 发送消息播放次数

// 播放请求类型
private sealed class PlayRequest {
    object PageSwitch : PlayRequest() // 首次进入页面，播放2次
    object Message : PlayRequest() // 发送消息，播放1次
}

/** 通用角色背景组件 可用于聊天页面、角色主页等需要角色背景的地方 */
@Composable
fun AgentBackground(
    agentInfo: AgentInfo?,
    modifier: Modifier = Modifier,
    showGradients: Boolean = true,
    isLoading: Boolean = false,
    isCurrentPage: Boolean = true,
    onPlayComplete: () -> Unit = {},
) {
    val context = LocalContext.current
    val density = LocalDensity.current
    val configuration = LocalConfiguration.current

    // 容器尺寸（dp），使用 LocalConfiguration 获取屏幕物理尺寸，不受键盘影响
    val containerWidthDp = remember(configuration.screenWidthDp) { configuration.screenWidthDp }
    val containerHeightDp = remember(configuration.screenHeightDp) { configuration.screenHeightDp }

    // 统一使用 ContentScale.Crop，确保视频和图片的缩放方式一致
    // 在 HorizontalPager 中，必须确保内容不会超出屏幕宽度，Crop 是最安全的选择
    // 视频使用 RESIZE_MODE_ZOOM（相当于 Crop），图片也使用 Crop 保持一致
    val contentScale = ContentScale.Crop

    // 判断是否为 IntelliMate agent
    val isIntelliMateAgent = AgentConstants.isIntelliMateAgent(agentInfo?.id, agentInfo?.name)

    val backgroundAnimatedUrl = agentInfo?.backgroundAnimatedUrl?.takeIf { it.isNotBlank() }
    val staticImageUrl =
        if (isIntelliMateAgent) {
            // IntelliMate agent 使用本地资源
            null
        } else {
            agentInfo?.getOriginShowImage()?.takeIf { it.isNotBlank() }
        }

    // 动画缓存管理器（用于视频缓存，webp动图由Coil自动处理）
    val videoCacheManager = remember { VideoCacheManager.getInstance(context) }

    // 视频缓存状态（仅对mp4/webm视频有效，webp动图不需要缓存检查）
    var isVideoCached by remember { mutableStateOf(false) }

    // 播放控制状态
    // 使用明确的播放请求机制，确保播放完成后立即停止
    var playRequest by remember { mutableStateOf<PlayRequest?>(null) }
    var hasCompletedPageSwitchPlay by remember(agentInfo?.id) { mutableStateOf(false) } // 记录是否已完成首次播放（随 agent 切换重置）
    var isPlaying by remember { mutableStateOf(false) } // 动画是否正在播放（从 AnimatedBackground 获取）

    // 检查视频缓存状态 - 每次进入页面时都重新检查（仅对mp4/webm视频有效）
    // 注意：动图（gif、webp、avif 等）不需要缓存检查，Coil会自动处理
    LaunchedEffect(agentInfo?.id, backgroundAnimatedUrl, isCurrentPage) {
        if (backgroundAnimatedUrl != null && isCurrentPage) {
            // 仅对视频格式进行缓存检查，动图由Coil自动处理
            val isVideo = backgroundAnimatedUrl.lowercase().endsWith(".mp4") ||
                backgroundAnimatedUrl.lowercase().endsWith(".webm") ||
                backgroundAnimatedUrl.lowercase().contains(".mp4?") ||
                backgroundAnimatedUrl.lowercase().contains(".webm?")
            if (isVideo) {
                isVideoCached = videoCacheManager.isCached(backgroundAnimatedUrl)
                LogUtils.d("AgentBackground - 视频缓存状态: $isVideoCached, URL: $backgroundAnimatedUrl")
            } else {
                // 动图不需要缓存检查，Coil会自动处理
                isVideoCached = false
            }
        } else {
            isVideoCached = false
        }
    }

    // 预加载视频（如果未缓存，仅对mp4/webm视频有效）
    // 注意：动图（gif、webp、avif 等）由Coil自动处理，不需要预加载
    LaunchedEffect(backgroundAnimatedUrl, isVideoCached) {
        if (backgroundAnimatedUrl != null && !isVideoCached && isCurrentPage) {
            val isVideo = backgroundAnimatedUrl.lowercase().endsWith(".mp4") ||
                backgroundAnimatedUrl.lowercase().endsWith(".webm") ||
                backgroundAnimatedUrl.lowercase().contains(".mp4?") ||
                backgroundAnimatedUrl.lowercase().contains(".webm?")
            if (isVideo) {
                videoCacheManager.preloadVideo(backgroundAnimatedUrl)
            }
        }
    }

    // 首次进入页面时触发播放（2次）
    // 关键：只在 agent 切换且未完成首次播放时触发
    LaunchedEffect(agentInfo?.id, isCurrentPage, backgroundAnimatedUrl, isVideoCached) {
        if (isCurrentPage && backgroundAnimatedUrl != null && !hasCompletedPageSwitchPlay) {
            // 判断是否为视频格式
            val isVideo = backgroundAnimatedUrl.lowercase().endsWith(".mp4") ||
                backgroundAnimatedUrl.lowercase().endsWith(".webm") ||
                backgroundAnimatedUrl.lowercase().contains(".mp4?") ||
                backgroundAnimatedUrl.lowercase().contains(".webm?")
            
            // 对于视频，需要等待缓存完成；对于动图，可以直接播放
            if (!isVideo || isVideoCached) {
                playRequest = PlayRequest.PageSwitch
                LogUtils.d("AgentBackground - 触发首次页面播放: playCount=2, isVideo=$isVideo, isVideoCached=$isVideoCached")
            }
        }
    }

    // 发送消息时触发播放（1次）
    // 关键：只在 loading 开始时触发，且当前没有播放请求，且不在播放中
    LaunchedEffect(isLoading, backgroundAnimatedUrl, isCurrentPage, isPlaying) {
        if (isLoading && backgroundAnimatedUrl != null && isCurrentPage && playRequest == null && !isPlaying) {
            playRequest = PlayRequest.Message
            LogUtils.d("AgentBackground - 触发消息播放: playCount=1")
        }
    }

    // 计算播放状态
    val shouldPlay = playRequest != null && isCurrentPage
    val playCount = when (playRequest) {
        is PlayRequest.PageSwitch -> VIDEO_FIRST_PLAY_COUNT
        is PlayRequest.Message -> VIDEO_MESSAGE_PLAY_COUNT
        null -> 0
    }

    Box(modifier = modifier.fillMaxSize().clipToBounds()) {
        if (backgroundAnimatedUrl != null) {
            // 有背景动画（视频或webp动图），使用 AnimatedBackground 组件
            // AnimatedBackground 会自动识别视频格式（mp4/webm）和webp动图格式
            AnimatedBackground(
                videoUrl = backgroundAnimatedUrl,
                staticImageUrl = staticImageUrl,
                isCurrentPage = isCurrentPage,
                shouldPlay = shouldPlay,
                playCount = playCount,
                isVideoCached = isVideoCached,
                onPlayComplete = {
                    // 播放完成后，立即清除播放请求
                    val completedRequest = playRequest
                    playRequest = null
                    
                    // 如果是首次页面播放完成，标记为已完成
                    if (completedRequest is PlayRequest.PageSwitch) {
                        hasCompletedPageSwitchPlay = true
                        LogUtils.d("AgentBackground - 首次页面播放完成，标记为已完成")
                    }
                    
                    LogUtils.d("AgentBackground - 播放完成，清除播放请求: $completedRequest")
                    onPlayComplete()
                },
                onIsPlayingChange = { playing ->
                    // 更新播放状态，用于判断是否可以触发新的播放请求
                    isPlaying = playing
                },
                contentScale = contentScale,
            )
        } else if (staticImageUrl != null) {
            // 没有背景动画，只显示静态图片
            // 使用固定 CDN 参数，确保与预加载 URL 一致
            val staticImageRequest =
                remember(staticImageUrl) {
                    val containerWidthPx = with(density) { containerWidthDp.dp.toPx().toInt() }
                    val containerHeightPx = with(density) { containerHeightDp.dp.toPx().toInt() }

                    ImageRequest.Builder(context)
                        .data(
                            getCdnImageUrl(
                                staticImageUrl,
                                width = CDN_STATIC_BACKGROUND_WIDTH, // 使用固定宽度，确保预加载和实际使用 URL 一致
                                quality = CDN_IMAGE_QUALITY,
                            ) ?: staticImageUrl
                        )
                        .size(Size(containerWidthPx, containerHeightPx))
                        .crossfade(true)
                        .build()
                }

            AsyncImage(
                modifier = Modifier.fillMaxWidth().fillMaxSize(), // 使用 fillMaxWidth() 确保宽度不超过屏幕宽度
                model = staticImageRequest,
                contentDescription = null,
                alignment = Alignment.TopCenter,
                contentScale = contentScale, // 统一使用 Crop
            )
        } else if (isIntelliMateAgent) {
            // IntelliMate agent 使用本地资源图片
            Image(
                modifier = Modifier.fillMaxWidth().fillMaxSize(),
                painter = painterResource(R.drawable.img_official_agent_background),
                contentDescription = null,
                alignment = Alignment.TopCenter,
                contentScale = contentScale,
            )
        }

        // 渐变遮罩 - 仅在需要时显示
        if (showGradients) {
            // 顶部渐变遮罩
            Box(
                modifier =
                    Modifier.fillMaxWidth()
                        .height(TOP_GRADIENT_HEIGHT_DP.dp)
                        .background(
                            Brush.verticalGradient(
                                colors = listOf(Color.Black.copy(alpha = 0.3f), Color.Transparent)
                            )
                        )
                        .align(Alignment.TopCenter)
            )

            // 底部渐变遮罩
            Box(
                modifier =
                    Modifier.fillMaxWidth()
                        .height(BOTTOM_GRADIENT_HEIGHT_DP.dp)
                        .background(
                            Brush.verticalGradient(
                                colors = listOf(Color.Transparent, Color.Black.copy(alpha = 0.5f))
                            )
                        )
                        .align(Alignment.BottomCenter)
            )
        }
    }
}
