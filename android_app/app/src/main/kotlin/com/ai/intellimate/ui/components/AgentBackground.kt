package com.ai.intellimate.ui.components

import ai.sxwl.android.data.api.getCdnImageUrl
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.utils.LogUtils
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
import androidx.compose.ui.layout.onSizeChanged
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
    isFirstEnter: Boolean = false,
    isLoading: Boolean = false,
    isCurrentPage: Boolean = true,
    onPlayComplete: () -> Unit = {},
) {
    val density = LocalDensity.current
    val containerSize = LocalWindowInfo.current.containerSize

    // 容器尺寸（dp），用于图片显示和 ContentScale 计算
    var containerWidthDp by remember {
        mutableIntStateOf(with(density) { containerSize.width.toDp().value.roundToInt() })
    }
    var containerHeightDp by remember {
        mutableIntStateOf(with(density) { containerSize.height.toDp().value.roundToInt() })
    }

    // 监听窗口尺寸变化，更新容器尺寸（只增大，不减小）
    LaunchedEffect(containerSize.width, containerSize.height, density) {
        val currentWidthDp = with(density) { containerSize.width.toDp().value.roundToInt() }
        val currentHeightDp = with(density) { containerSize.height.toDp().value.roundToInt() }

        if (currentWidthDp > containerWidthDp) {
            containerWidthDp = currentWidthDp
        }
        if (currentHeightDp > containerHeightDp) {
            containerHeightDp = currentHeightDp
        }
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

    // 调试日志
    LaunchedEffect(agentInfo?.id, backgroundGifUrl, staticImageUrl) {
        LogUtils.d("AgentBackground - agentId: ${agentInfo?.id}, backgroundGifUrl: $backgroundGifUrl, staticImageUrl: $staticImageUrl")
    }

    // 播放控制逻辑
    var shouldPlay by remember { mutableStateOf(false) }
    var playCount by remember { mutableIntStateOf(1) }
    var lastPlayedAgentId by remember { mutableStateOf<String?>(null) }
    var lastPlayedPageState by remember { mutableStateOf(false) }
    var lastPlayedTimestamp by remember { mutableLongStateOf(0L) }

    // 每次进入页面时：播放2次
    // 基于页面可见性（isCurrentPage）和 agent 变化来触发
    // 注意：这里不依赖 isFirstEnter，因为用户需求是每次进入页面都播放
    LaunchedEffect(isCurrentPage, agentInfo?.id, backgroundGifUrl) {
        // 当页面变为可见且有背景动图时，触发播放
        if (isCurrentPage && backgroundGifUrl != null) {
            val currentAgentId = agentInfo?.id
            val currentTime = System.currentTimeMillis()
            // 如果 agent 变化了，或者页面从不可见变为可见，或者距离上次播放超过1秒，则播放
            // 这样可以确保每次进入 Activity 时都能播放（即使 agent 相同）
            val shouldTriggerPlay = currentAgentId != null && (
                    currentAgentId != lastPlayedAgentId ||
                            (isCurrentPage && !lastPlayedPageState) ||
                            (currentTime - lastPlayedTimestamp > 1000) // 距离上次播放超过1秒
                    )

            if (shouldTriggerPlay) {
                LogUtils.d("AgentBackground - 触发页面进入播放: agentId=$currentAgentId, isCurrentPage=$isCurrentPage, lastPlayedAgentId=$lastPlayedAgentId, lastPlayedPageState=$lastPlayedPageState, timeSinceLastPlay=${currentTime - lastPlayedTimestamp}ms")
                lastPlayedAgentId = currentAgentId
                lastPlayedPageState = isCurrentPage
                lastPlayedTimestamp = currentTime
                playCount = 2
                shouldPlay = true
            }
        } else if (!isCurrentPage) {
            // 页面不可见时，更新状态但不播放
            lastPlayedPageState = false
        }
    }

    // Loading 时：播放1次
    // 注意：只在 Loading 时设置 shouldPlay，不主动设置为 false，避免覆盖页面进入时的播放
    LaunchedEffect(isLoading, backgroundGifUrl) {
        if (isLoading && backgroundGifUrl != null) {
            playCount = 1
            shouldPlay = true
        }
        // 不在 !isLoading 时设置 shouldPlay = false，让播放完成回调来处理
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
                    .onSizeChanged {
                        val newHeightDp = with(density) { it.height.toDp().value.roundToInt() }
                        if (newHeightDp > containerHeightDp) {
                            containerHeightDp = newHeightDp
                        }
                    }
        ) {
            // 如果有动图/视频，使用 AnimatedBackground
            if (backgroundGifUrl != null) {
                LogUtils.d("测试，agent背景图gifUrl : $backgroundGifUrl")
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
                    onStaticImageLoaded = {
                        // 静态图加载完成，可以开始加载动图/视频
                    },
                )
            } else {
                // 没有动图/视频，显示静态图
                if (staticImageUrl != null && staticImageRequest != null) {
                    LogUtils.d("AgentBackground - 显示静态图: $staticImageUrl")
                    AsyncImage(
                        modifier = Modifier.size(containerWidthDp.dp, containerHeightDp.dp),
                        model = staticImageRequest,
                        contentDescription = null,
                        alignment = Alignment.TopCenter,
                        contentScale = optimalContentScale,
                        onSuccess = { state ->
                            // 获取图片原始尺寸（像素），用于计算 ContentScale
                            val drawable = state.painter
                            imageWidthPx = drawable.intrinsicSize.width.toInt()
                            imageHeightPx = drawable.intrinsicSize.height.toInt()
                        },
                        onError = {
                            LogUtils.e("AgentBackground - 静态图加载失败: $staticImageUrl")
                        },
                    )
                } else {
                    LogUtils.w("AgentBackground - 静态图URL为空，无法显示背景")
                }
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
