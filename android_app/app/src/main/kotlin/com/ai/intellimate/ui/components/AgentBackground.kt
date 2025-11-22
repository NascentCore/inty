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

    // 视频缓存管理器
    val videoCacheManager = remember { VideoCacheManager.getInstance(context) }

    // 视频缓存状态
    var isVideoCached by remember { mutableStateOf(false) }

    // 播放控制：页面切换时播放2次，加载状态时播放1次
    var shouldPlayPageSwitch by remember { mutableStateOf(false) }
    var shouldPlayLoading by remember { mutableStateOf(false) }
    var isVideoPlaying by remember { mutableStateOf(false) } // 视频是否正在播放
    var isLoadingTriggeredPlay by remember { mutableStateOf(false) } // 是否因为 loading 触发的播放

    // 检查视频缓存状态 - 每次进入页面时都重新检查
    // 优化：同步检查缓存状态，避免延迟
    // 关键修复：首次安装时，即使未缓存，也应该在视频准备好后触发播放
    LaunchedEffect(agentInfo?.id, backgroundAnimatedUrl, isCurrentPage) {
        if (backgroundAnimatedUrl != null && isCurrentPage) {
            isVideoCached = videoCacheManager.isCached(backgroundAnimatedUrl)
            LogUtils.d("AgentBackground - 视频缓存状态: $isVideoCached, URL: $backgroundAnimatedUrl")
        } else {
            isVideoCached = false
        }
    }

    // 预加载视频（如果未缓存）
    LaunchedEffect(backgroundAnimatedUrl, isVideoCached) {
        if (backgroundAnimatedUrl != null && !isVideoCached && isCurrentPage) {
            videoCacheManager.preloadVideo(backgroundAnimatedUrl)
        }
    }

    // 页面切换时触发播放
    LaunchedEffect(isCurrentPage, isVideoCached) {
        if (isCurrentPage && backgroundAnimatedUrl != null) {
            shouldPlayPageSwitch = true
        }
    }

    // 加载状态时触发播放
    LaunchedEffect(isLoading) {
        if (isLoading && backgroundAnimatedUrl != null && !isLoadingTriggeredPlay) {
            shouldPlayLoading = true
            isLoadingTriggeredPlay = true
        } else if (!isLoading) {
            isLoadingTriggeredPlay = false
        }
    }

    Box(modifier = modifier.fillMaxSize().clipToBounds()) {
        if (backgroundAnimatedUrl != null) {
            // 有背景视频，使用 AnimatedBackground 组件
            AnimatedBackground(
                videoUrl = backgroundAnimatedUrl,
                staticImageUrl = staticImageUrl,
                isCurrentPage = isCurrentPage,
                shouldPlay = shouldPlayPageSwitch || shouldPlayLoading,
                playCount =
                    if (shouldPlayPageSwitch) VIDEO_FIRST_PLAY_COUNT else VIDEO_MESSAGE_PLAY_COUNT,
                onPlayComplete = {
                    if (shouldPlayPageSwitch) {
                        shouldPlayPageSwitch = false
                    }
                    if (shouldPlayLoading) {
                        shouldPlayLoading = false
                    }
                    onPlayComplete()
                },
                contentScale = contentScale,
            )
        } else if (staticImageUrl != null) {
            // 没有背景视频，只显示静态图片
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
