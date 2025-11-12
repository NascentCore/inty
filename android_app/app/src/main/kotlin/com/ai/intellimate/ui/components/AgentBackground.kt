package com.ai.intellimate.ui.components

import ai.sxwl.android.data.api.getCdnImageUrl
import ai.sxwl.android.data.api.model.AgentInfo
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableLongStateOf
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
import kotlin.math.abs
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
    val density = LocalDensity.current
    val containerSize = LocalWindowInfo.current.containerSize

    // 容器尺寸（dp），用于图片显示和 ContentScale 计算
    // 始终使用当前窗口尺寸，确保内容不超出屏幕
    val containerWidthDp = remember(containerSize.width, density) {
        with(density) { containerSize.width.toDp().value.roundToInt() }
    }
    var containerHeightDp by remember {
        mutableIntStateOf(with(density) { containerSize.height.toDp().value.roundToInt() })
    }

    // 监听窗口尺寸变化，更新容器高度（宽度始终跟随窗口宽度）
    LaunchedEffect(containerSize.height, density) {
        val currentHeightDp = with(density) { containerSize.height.toDp().value.roundToInt() }
        containerHeightDp = currentHeightDp
    }

    // 图片原始尺寸（像素），用于计算 ContentScale
    var imageWidthPx by remember { mutableStateOf<Int?>(null) }
    var imageHeightPx by remember { mutableStateOf<Int?>(null) }

    // 计算最佳的 ContentScale（单位统一为 dp）
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
            // 将图片尺寸从像素转换为 dp，确保单位一致
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

    val context = LocalContext.current
    val backgroundGifUrl = agentInfo?.backgroundGifUrl?.takeIf { it.isNotBlank() }
    val staticImageUrl = agentInfo?.getAlbumImage()?.takeIf { it.isNotBlank() }

    // 播放控制逻辑
    var shouldPlay by remember { mutableStateOf(false) }
    var playCount by remember { mutableIntStateOf(1) }
    var lastPlayedAgentId by remember { mutableStateOf<String?>(null) }
    var lastPlayedPageState by remember { mutableStateOf(false) }
    var lastPlayedTimestamp by remember { mutableLongStateOf(0L) }

    LaunchedEffect(isCurrentPage, agentInfo?.id, backgroundGifUrl) {
        if (isCurrentPage && backgroundGifUrl != null) {
            val currentAgentId = agentInfo?.id
            val currentTime = System.currentTimeMillis()
            val shouldTriggerPlay = currentAgentId != null && (
                    currentAgentId != lastPlayedAgentId ||
                            !lastPlayedPageState ||
                            (currentTime - lastPlayedTimestamp > 1000)
                    )

            if (shouldTriggerPlay) {
                lastPlayedAgentId = currentAgentId
                lastPlayedPageState = true
                lastPlayedTimestamp = currentTime
                playCount = 2
                shouldPlay = true
            }
        } else if (!isCurrentPage) {
            lastPlayedPageState = false
        }
    }

    LaunchedEffect(isLoading, backgroundGifUrl) {
        if (isLoading && backgroundGifUrl != null) {
            playCount = 1
            shouldPlay = true
        }
    }

    // 构建静态图片请求（用于首次加载优化）
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
        Column(
            modifier =
                Modifier
                    .fillMaxSize()
                    .verticalScroll(rememberScrollState(), false)
        ) {
            if (backgroundGifUrl != null) {
                AnimatedBackground(
                    videoUrl = backgroundGifUrl,
                    staticImageUrl = staticImageUrl,
                    modifier = Modifier.size(containerWidthDp.dp, containerHeightDp.dp),
                    contentScale = optimalContentScale,
                    shouldPlay = shouldPlay,
                    playCount = playCount,
                    onPlayComplete = {
                        shouldPlay = false
                        onPlayComplete()
                    },
                )
            } else if (staticImageUrl != null && staticImageRequest != null) {
                AsyncImage(
                    modifier = Modifier.size(containerWidthDp.dp, containerHeightDp.dp),
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
    val aspectRatioDiff = abs(containerAspectRatio - imageAspectRatio) / imageAspectRatio

    return when {
        // 如果容器和图片宽高比非常接近（差异小于阈值），使用 Fit 显示完整图片
        // 例如：容器 9:16 (0.5625)，图片 9:16 (0.5625) → 使用 Fit
        aspectRatioDiff < ASPECT_RATIO_THRESHOLD -> ContentScale.Fit

        // 如果容器比图片更宽（容器宽高比 > 图片宽高比），图片相对较窄，使用 FillWidth
        // 例如：容器 16:9 (1.78)，图片 9:16 (0.5625) → 使用 FillWidth
        containerAspectRatio > imageAspectRatio -> ContentScale.FillWidth

        // 如果容器比图片更窄（容器宽高比 < 图片宽高比），图片相对较宽，使用 FillHeight
        // 例如：容器 9:16 (0.5625)，图片 16:9 (1.78) → 使用 FillHeight
        else -> ContentScale.FillHeight
    }
}
