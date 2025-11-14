package com.ai.intellimate.ui.components

import ai.sxwl.android.data.api.getCdnImageUrl
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.utils.LogUtils
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
import androidx.compose.ui.unit.dp
import coil3.compose.AsyncImage
import coil3.request.ImageRequest
import coil3.request.crossfade
import coil3.size.Size

private const val CDN_IMAGE_QUALITY = 75
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

    val backgroundAnimatedUrl = agentInfo?.backgroundAnimatedUrl?.takeIf { it.isNotBlank() }
    val staticImageUrl = agentInfo?.getOriginShowImage()?.takeIf { it.isNotBlank() }

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
        LogUtils.d(
            "AgentBackground - [缓存检查] LaunchedEffect触发: agentId=${agentInfo?.id}, backgroundAnimatedUrl=$backgroundAnimatedUrl, isCurrentPage=$isCurrentPage, shouldPlayPageSwitch=$shouldPlayPageSwitch"
        )

        if (backgroundAnimatedUrl != null && isCurrentPage) {
            // 同步检查缓存状态（快速响应）
            val cached = videoCacheManager.isCached(backgroundAnimatedUrl)
            isVideoCached = cached
            LogUtils.d("AgentBackground - [缓存检查] 视频缓存状态: $cached, URL: $backgroundAnimatedUrl")

            // 关键修复：无论是否缓存，都应该触发首次播放
            // 已缓存：立即触发页面切换播放（2次）
            // 未缓存：也设置 shouldPlayPageSwitch，等视频准备好后播放
            if (!shouldPlayPageSwitch) {
                shouldPlayPageSwitch = true
                LogUtils.d("AgentBackground - [缓存检查] ✅ 设置页面切换播放: shouldPlayPageSwitch=true, isVideoCached=$cached")
            } else {
                LogUtils.d("AgentBackground - [缓存检查] shouldPlayPageSwitch 已设置，保持状态: isVideoCached=$cached")
            }
        } else {
            // 只有在没有视频URL或不在当前页面时才重置
            shouldPlayPageSwitch = false
            isVideoCached = false
            LogUtils.d("AgentBackground - [缓存检查] 重置状态: backgroundAnimatedUrl=$backgroundAnimatedUrl, isCurrentPage=$isCurrentPage")
        }
    }

    // 加载状态时播放视频（1次）- 仅在普通loading时触发，不包含图片生成loading
    // 优化：如果视频正在播放中，则不处理；如果视频未播放，则触发播放，并让视频播放完整到结束
    LaunchedEffect(isLoading, backgroundAnimatedUrl, isVideoCached, isCurrentPage, isVideoPlaying) {
        if (isLoading && backgroundAnimatedUrl != null && isVideoCached && isCurrentPage) {
            // 如果视频正在播放中，则不处理
            if (!isVideoPlaying) {
                shouldPlayLoading = true
                isLoadingTriggeredPlay = true
                LogUtils.d(
                    "AgentBackground - 设置加载播放: shouldPlayLoading=true, isLoadingTriggeredPlay=true"
                )
            } else {
                LogUtils.d("AgentBackground - 视频正在播放中，跳过加载播放")
            }
        }
        // 注意：loading 结束时，不立即停止播放，让视频播放到结束
        // 状态重置在 onPlayComplete 中处理
    }

    // 合并播放状态：页面切换播放优先于加载播放
    // 注意：如果是因为 loading 触发的播放，即使 loading 结束，也继续播放到结束
    val shouldPlay =
        (shouldPlayPageSwitch || shouldPlayLoading || (isLoadingTriggeredPlay && isVideoPlaying)) &&
            isCurrentPage
    val finalPlayCount =
        if (shouldPlayPageSwitch) VIDEO_FIRST_PLAY_COUNT
        else if (shouldPlayLoading || isLoadingTriggeredPlay) VIDEO_MESSAGE_PLAY_COUNT
        else VIDEO_MESSAGE_PLAY_COUNT

    // 关键：在 Compose 层面添加裁剪，防止视频超出容器边界
    // 使用 fillMaxWidth() 确保宽度不超过屏幕宽度，防止影响相邻 Page
    Box(
        modifier = modifier
            .fillMaxWidth()
            .fillMaxSize()
            .clipToBounds()
    ) {
        // 如果有背景视频URL，始终渲染 AnimatedBackground（内部会处理静态图占位符）
        if (backgroundAnimatedUrl != null) {
            AnimatedBackground(
                videoUrl = backgroundAnimatedUrl,
                staticImageUrl = staticImageUrl,
                modifier = Modifier
                    .fillMaxWidth()
                    .fillMaxSize(),
                contentScale = contentScale, // 统一使用 Crop
                shouldPlay = shouldPlay,
                playCount = finalPlayCount,
                isVideoCached = isVideoCached,
                isCurrentPage = isCurrentPage,
                onPlayComplete = {
                    shouldPlayPageSwitch = false
                    shouldPlayLoading = false
                    if (isLoadingTriggeredPlay) {
                        isLoadingTriggeredPlay = false
                    }
                    onPlayComplete()
                },
                onIsPlayingChange = { playing -> isVideoPlaying = playing },
            )
        } else if (staticImageUrl != null) {
            // 没有背景视频，只显示静态图片
            // 构建优化的图片请求，使用 CDN 根据容器尺寸生成
            val staticImageRequest =
                remember(staticImageUrl, containerWidthDp, containerHeightDp, density) {
                    val containerWidthPx = with(density) { containerWidthDp.dp.toPx().toInt() }
                    val containerHeightPx = with(density) { containerHeightDp.dp.toPx().toInt() }

                    ImageRequest.Builder(context)
                        .data(
                            getCdnImageUrl(
                                staticImageUrl,
                                width = containerWidthPx,
                                quality = CDN_IMAGE_QUALITY,
                            ) ?: staticImageUrl
                        )
                        .size(Size(containerWidthPx, containerHeightPx))
                        .crossfade(true)
                        .build()
                }
            
            AsyncImage(
                modifier = Modifier
                    .fillMaxWidth()
                    .fillMaxSize(), // 使用 fillMaxWidth() 确保宽度不超过屏幕宽度
                model = staticImageRequest,
                contentDescription = null,
                alignment = Alignment.TopCenter,
                contentScale = contentScale, // 统一使用 Crop
            )
        }

        // 渐变遮罩 - 仅在需要时显示
        if (showGradients) {
            // 顶部渐变遮罩
            Box(
                modifier =
                    Modifier
                        .fillMaxWidth()
                        .height(TOP_GRADIENT_HEIGHT_DP.dp)
                        .background(
                            brush =
                                Brush.verticalGradient(listOf(Color(0xFF000000), Color(0x00000000)))
                        )
            )

            // 底部渐变遮罩
            Box(
                modifier =
                    Modifier
                        .fillMaxWidth()
                        .height(BOTTOM_GRADIENT_HEIGHT_DP.dp)
                        .background(
                            brush =
                                Brush.verticalGradient(listOf(Color(0x001C1523), Color(0xFF1C1523)))
                        )
                        .align(Alignment.BottomCenter)
            )
        }
    }
}
