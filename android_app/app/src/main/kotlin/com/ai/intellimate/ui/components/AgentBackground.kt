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
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalWindowInfo
import androidx.compose.ui.unit.dp
import coil3.compose.AsyncImage
import coil3.request.ImageRequest
import coil3.request.crossfade
import coil3.size.Size
import kotlin.math.roundToInt

private const val CDN_IMAGE_QUALITY = 75
private const val ASPECT_RATIO_THRESHOLD = 0.05f
private const val TOP_GRADIENT_HEIGHT_DP = 120
private const val BOTTOM_GRADIENT_HEIGHT_DP = 300

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
    val containerSize = LocalWindowInfo.current.containerSize

    // 容器尺寸（dp），用于图片显示和 ContentScale 计算
    val containerWidthDp = remember(containerSize.width, density) {
        with(density) { containerSize.width.toDp().value.roundToInt() }
    }
    var containerHeightDp by remember {
        mutableIntStateOf(with(density) { containerSize.height.toDp().value.roundToInt() })
    }

    // 监听窗口尺寸变化，更新容器高度
    LaunchedEffect(containerSize.height, density) {
        val currentHeightDp = with(density) { containerSize.height.toDp().value.roundToInt() }
        containerHeightDp = currentHeightDp
    }

    // 图片原始尺寸（像素），用于计算 ContentScale
    var imageWidthPx by remember { mutableStateOf<Int?>(null) }
    var imageHeightPx by remember { mutableStateOf<Int?>(null) }

    // 计算最佳的 ContentScale
    val optimalContentScale = remember(
        imageWidthPx,
        imageHeightPx,
        containerWidthDp,
        containerHeightDp,
        density
    ) {
        if (
            imageWidthPx != null &&
            imageHeightPx != null &&
            imageWidthPx!! > 0 &&
            imageHeightPx!! > 0
        ) {
            val imageWidthDpValue = with(density) { imageWidthPx!!.toFloat().toDp().value }
            val imageHeightDpValue = with(density) { imageHeightPx!!.toFloat().toDp().value }

            calculateOptimalContentScale(
                containerWidthDp = containerWidthDp,
                containerHeightDp = containerHeightDp,
                imageWidthDp = imageWidthDpValue,
                imageHeightDp = imageHeightDpValue,
            )
        } else {
            ContentScale.Crop
        }
    }

    val backgroundAnimatedUrl = agentInfo?.backgroundAnimatedUrl?.takeIf { it.isNotBlank() }
    val staticImageUrl = agentInfo?.getAlbumImage()?.takeIf { it.isNotBlank() }

    // 视频缓存管理器
    val videoCacheManager = remember { VideoCacheManager.getInstance(context) }

    // 视频缓存状态
    var isVideoCached by remember { mutableStateOf(false) }

    // 播放控制：页面切换时播放2次，加载状态时播放1次
    var shouldPlayPageSwitch by remember { mutableStateOf(false) }
    var shouldPlayLoading by remember { mutableStateOf(false) }
    var playCount by remember { mutableIntStateOf(1) }

    // 检查视频缓存状态 - 每次进入页面时都重新检查
    // 优化：同步检查缓存状态，避免延迟
    LaunchedEffect(agentInfo?.id, backgroundAnimatedUrl, isCurrentPage) {
        LogUtils.d("AgentBackground - LaunchedEffect触发: agentId=${agentInfo?.id}, backgroundAnimatedUrl=$backgroundAnimatedUrl, isCurrentPage=$isCurrentPage")

        // 重置状态
        shouldPlayPageSwitch = false

        if (backgroundAnimatedUrl != null && isCurrentPage) {
            // 同步检查缓存状态（快速响应）
            val cached = videoCacheManager.isCached(backgroundAnimatedUrl)
            isVideoCached = cached
            LogUtils.d("AgentBackground - 视频缓存状态: $cached, URL: $backgroundAnimatedUrl")

            // 如果已缓存，立即触发页面切换播放（2次）
            if (cached) {
                playCount = 2
                shouldPlayPageSwitch = true
                LogUtils.d("AgentBackground - 设置页面切换播放: playCount=2, shouldPlayPageSwitch=true")
            } else {
                isVideoCached = false
            }
        } else {
            isVideoCached = false
        }
    }

    // 加载状态时播放视频（1次）- 仅在普通loading时触发，不包含图片生成loading
    LaunchedEffect(isLoading, backgroundAnimatedUrl, isVideoCached, isCurrentPage) {
        if (isLoading && backgroundAnimatedUrl != null && isVideoCached && isCurrentPage) {
            playCount = 1
            shouldPlayLoading = true
            LogUtils.d("AgentBackground - 设置加载播放: playCount=1, shouldPlayLoading=true")
        } else {
            shouldPlayLoading = false
        }
    }

    // 合并播放状态：页面切换播放优先于加载播放
    val shouldPlay = (shouldPlayPageSwitch || shouldPlayLoading) && isCurrentPage
    val finalPlayCount = if (shouldPlayPageSwitch) 2 else if (shouldPlayLoading) 1 else 1

    // 构建静态图片请求
    val staticImageRequest =
        remember(staticImageUrl, containerWidthDp, containerHeightDp, density) {
            if (staticImageUrl != null) {
                val containerWidthPx = with(density) { containerWidthDp.dp.toPx().toInt() }
                val containerHeightPx = with(density) { containerHeightDp.dp.toPx().toInt() }

                ImageRequest.Builder(context)
                    .data(
                        getCdnImageUrl(
                            staticImageUrl,
                            width = containerWidthPx,
                            quality = CDN_IMAGE_QUALITY
                        ) ?: staticImageUrl
                    )
                    .size(Size(containerWidthPx, containerHeightPx))
                    .crossfade(true)
                    .build()
            } else {
                null
            }
        }

    Box(modifier = modifier) {
        // 如果有背景视频URL，始终渲染 AnimatedBackground
        if (backgroundAnimatedUrl != null) {
            AnimatedBackground(
                videoUrl = backgroundAnimatedUrl,
                staticImageUrl = staticImageUrl,
                modifier = Modifier.fillMaxSize(),
                contentScale = optimalContentScale,
                shouldPlay = shouldPlay,
                playCount = finalPlayCount,
                isVideoCached = isVideoCached,
                isCurrentPage = isCurrentPage,
                onPlayComplete = {
                    shouldPlayPageSwitch = false
                    shouldPlayLoading = false
                    onPlayComplete()
                },
            )
        } else if (staticImageUrl != null && staticImageRequest != null) {
            // 没有背景视频，只显示静态图片
            AsyncImage(
                modifier = Modifier.fillMaxSize(),
                model = staticImageRequest,
                contentDescription = null,
                alignment = Alignment.TopCenter,
                contentScale = optimalContentScale,
                onSuccess = { state ->
                    val drawable = state.painter
                    imageWidthPx = drawable.intrinsicSize.width.toInt()
                    imageHeightPx = drawable.intrinsicSize.height.toInt()
                },
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
                            brush = Brush.verticalGradient(
                                listOf(Color(0xFF000000), Color(0x00000000))
                            )
                        )
            )

            // 底部渐变遮罩
            Box(
                modifier =
                    Modifier
                        .fillMaxWidth()
                        .height(BOTTOM_GRADIENT_HEIGHT_DP.dp)
                        .background(
                            brush = Brush.verticalGradient(
                                listOf(Color(0x001C1523), Color(0xFF1C1523))
                            )
                        )
                        .align(Alignment.BottomCenter)
            )
        }
    }
}

/**
 * 根据容器和图片的宽高比计算最佳的 ContentScale
 * 只支持人像模式屏幕显示，即尽量不留左右两侧空白。
 * 当容器高宽比大于图片高宽比时，使用 FillHeight 填充高度，否则使用 FillWidth 填充宽度。
 *
 * @param containerWidthDp 容器宽度（dp）
 * @param containerHeightDp 容器高度（dp）
 * @param imageWidthDp 图片宽度（dp）
 * @param imageHeightDp 图片高度（dp）
 * @return 最佳的 ContentScale
 */
private fun calculateOptimalContentScale(
    containerWidthDp: Int,
    containerHeightDp: Int,
    imageWidthDp: Float,
    imageHeightDp: Float,
): ContentScale {
    val containerAspectRatio = containerWidthDp.toFloat() / containerHeightDp.toFloat()
    val imageAspectRatio = imageWidthDp / imageHeightDp
    val aspectRatioDiff =
        kotlin.math.abs(containerAspectRatio - imageAspectRatio) / imageAspectRatio

    return when {
        // 如果容器和图片宽高比非常接近（差异小于阈值），使用 Fit 显示完整图片
        aspectRatioDiff < ASPECT_RATIO_THRESHOLD -> ContentScale.Fit

        // 如果容器比图片更宽（容器宽高比 > 图片宽高比），图片相对较窄，使用 FillWidth
        containerAspectRatio > imageAspectRatio -> ContentScale.FillWidth

        // 如果容器比图片更窄（容器宽高比 < 图片宽高比），图片相对较宽，使用 FillHeight
        else -> ContentScale.FillHeight
    }
}
