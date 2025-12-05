package com.ai.intellimate.ui.components

import ai.sxwl.android.data.api.getCdnImageUrl
import ai.sxwl.android.data.api.model.AgentConstants
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.store.IntySetting
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
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import kotlinx.coroutines.delay
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

private const val CDN_IMAGE_QUALITY = 80
private const val CDN_STATIC_BACKGROUND_WIDTH = 1080
private const val TOP_GRADIENT_HEIGHT_DP = 120
private const val BOTTOM_GRADIENT_HEIGHT_DP = 300
private const val VIDEO_FIRST_PLAY_COUNT = 2
private const val VIDEO_MESSAGE_PLAY_COUNT = 1

private fun isVideoUrl(url: String?): Boolean {
    if (url.isNullOrBlank()) return false
    val lower = url.lowercase()
    return lower.endsWith(".mp4") ||
        lower.endsWith(".webm") ||
        lower.contains(".mp4?") ||
        lower.contains(".webm?")
}

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
    val containerWidthDp = remember(configuration.screenWidthDp) { configuration.screenWidthDp }
    val containerHeightDp = remember(configuration.screenHeightDp) { configuration.screenHeightDp }
    val contentScale = ContentScale.Crop

    val isIntelliMateAgent = AgentConstants.isIntelliMateAgent(agentInfo?.id, agentInfo?.name)
    val backgroundAnimatedUrl = agentInfo?.backgroundAnimatedUrl?.takeIf { it.isNotBlank() }
    
    // 检查是否有自定义背景图片（仅用于静态背景，不覆盖动画背景）
    // 使用状态变量来跟踪背景 URL，并通过 LaunchedEffect 定期检查更新
    // 只在当前页面时检查，避免不必要的资源消耗
    var customBackgroundUrl by remember(agentInfo?.id) {
        mutableStateOf<String?>(
            if (agentInfo?.id != null && backgroundAnimatedUrl == null) {
                IntySetting.getChatBackgroundImage(agentInfo.id)
            } else {
                null
            }
        )
    }
    
    // 监听背景设置变化，定期检查以确保及时更新
    // 只在当前页面时检查，减少资源消耗
    val currentPageState = rememberUpdatedState(isCurrentPage)
    LaunchedEffect(agentInfo?.id, backgroundAnimatedUrl, isCurrentPage) {
        if (!isCurrentPage) return@LaunchedEffect
        
        while (currentPageState.value) {
            val newBackgroundUrl =
                if (agentInfo?.id != null && backgroundAnimatedUrl == null) {
                    IntySetting.getChatBackgroundImage(agentInfo.id)
                } else {
                    null
                }
            if (customBackgroundUrl != newBackgroundUrl) {
                customBackgroundUrl = newBackgroundUrl
            }
            delay(500) // 每 500ms 检查一次
        }
    }
    
    val staticImageUrl =
        if (isIntelliMateAgent) {
            null
        } else {
            // 优先使用自定义背景，然后才是默认背景
            customBackgroundUrl?.takeIf { it.isNotBlank() }
                ?: agentInfo?.getOriginShowImage()?.takeIf { it.isNotBlank() }
        }

    val videoCacheManager = remember { VideoCacheManager.getInstance(context) }
    var isVideoCached by remember { mutableStateOf(false) }
    var shouldPlayPageSwitch by remember { mutableStateOf(false) }
    var shouldPlayLoading by remember { mutableStateOf(false) }
    var isVideoPlaying by remember { mutableStateOf(false) }
    var hasCompletedPageSwitchPlay by remember(agentInfo?.id) { mutableStateOf(false) }
    var isLoadingTriggeredPlay by remember { mutableStateOf(false) }

    LaunchedEffect(agentInfo?.id, backgroundAnimatedUrl, isCurrentPage) {
        shouldPlayPageSwitch = false
        if (backgroundAnimatedUrl != null && isCurrentPage) {
            val isVideo = isVideoUrl(backgroundAnimatedUrl)
            val isAnimatedImage =
                !isVideo &&
                    (backgroundAnimatedUrl.lowercase().endsWith(".gif") ||
                        backgroundAnimatedUrl.lowercase().endsWith(".webp") ||
                        backgroundAnimatedUrl.lowercase().endsWith(".avif") ||
                        backgroundAnimatedUrl.lowercase().contains(".gif?") ||
                        backgroundAnimatedUrl.lowercase().contains(".webp?") ||
                        backgroundAnimatedUrl.lowercase().contains(".avif?"))

            if (isVideo) {
                isVideoCached = videoCacheManager.isCached(backgroundAnimatedUrl)
                if (isVideoCached && !hasCompletedPageSwitchPlay) {
                    shouldPlayPageSwitch = true
                }
            } else {
                isVideoCached = false
                if (!hasCompletedPageSwitchPlay) {
                    shouldPlayPageSwitch = true
                }
            }
        } else {
            isVideoCached = false
        }
    }

    LaunchedEffect(backgroundAnimatedUrl, isVideoCached) {
        if (
            backgroundAnimatedUrl != null &&
                !isVideoCached &&
                isCurrentPage &&
                isVideoUrl(backgroundAnimatedUrl)
        ) {
            videoCacheManager.preloadVideo(backgroundAnimatedUrl)
        }
    }

    LaunchedEffect(isLoading, backgroundAnimatedUrl, isVideoCached, isCurrentPage, isVideoPlaying) {
        if (isLoading && backgroundAnimatedUrl != null && isCurrentPage) {
            val isVideo = isVideoUrl(backgroundAnimatedUrl)
            if ((!isVideo || isVideoCached) && !isVideoPlaying) {
                shouldPlayLoading = true
                isLoadingTriggeredPlay = true
            }
        }
    }

    val shouldPlay =
        (shouldPlayPageSwitch || shouldPlayLoading || (isLoadingTriggeredPlay && isVideoPlaying)) &&
            isCurrentPage
    val playCount = if (shouldPlayPageSwitch) VIDEO_FIRST_PLAY_COUNT else VIDEO_MESSAGE_PLAY_COUNT

    Box(modifier = modifier.fillMaxSize().clipToBounds()) {
        if (backgroundAnimatedUrl != null) {
            AnimatedBackground(
                videoUrl = backgroundAnimatedUrl,
                staticImageUrl = staticImageUrl,
                isCurrentPage = isCurrentPage,
                shouldPlay = shouldPlay,
                playCount = playCount,
                isVideoCached = isVideoCached,
                onPlayComplete = {
                    val wasPageSwitch = shouldPlayPageSwitch
                    shouldPlayPageSwitch = false
                    shouldPlayLoading = false
                    if (isLoadingTriggeredPlay) {
                        isLoadingTriggeredPlay = false
                    }
                    if (wasPageSwitch) {
                        hasCompletedPageSwitchPlay = true
                    }
                    onPlayComplete()
                },
                onIsPlayingChange = { isVideoPlaying = it },
                contentScale = contentScale,
            )
        } else if (staticImageUrl != null) {
            // 使用 key() 确保当背景 URL 改变时强制重新组合
            key(staticImageUrl) {
                val staticImageRequest =
                    remember(staticImageUrl) {
                        val containerWidthPx = with(density) { containerWidthDp.dp.toPx().toInt() }
                        val containerHeightPx = with(density) { containerHeightDp.dp.toPx().toInt() }
                        ImageRequest.Builder(context)
                            .data(
                                getCdnImageUrl(
                                    staticImageUrl,
                                    width = CDN_STATIC_BACKGROUND_WIDTH,
                                    quality = CDN_IMAGE_QUALITY,
                                ) ?: staticImageUrl
                            )
                            .size(Size(containerWidthPx, containerHeightPx))
                            .crossfade(true)
                            .build()
                    }
                AsyncImage(
                    modifier = Modifier.fillMaxWidth().fillMaxSize(),
                    model = staticImageRequest,
                    contentDescription = null,
                    alignment = Alignment.TopCenter,
                    contentScale = contentScale,
                )
            }
        } else if (isIntelliMateAgent) {
            Image(
                modifier = Modifier.fillMaxWidth().fillMaxSize(),
                painter = painterResource(R.drawable.img_official_agent_background),
                contentDescription = null,
                alignment = Alignment.TopCenter,
                contentScale = contentScale,
            )
        }

        if (showGradients) {
            Box(
                modifier =
                    Modifier.fillMaxWidth()
                        .height(TOP_GRADIENT_HEIGHT_DP.dp)
                        .background(
                            Brush.verticalGradient(
                                listOf(Color.Black.copy(alpha = 0.3f), Color.Transparent)
                            )
                        )
                        .align(Alignment.TopCenter)
            )
            Box(
                modifier =
                    Modifier.fillMaxWidth()
                        .height(BOTTOM_GRADIENT_HEIGHT_DP.dp)
                        .background(
                            Brush.verticalGradient(
                                listOf(Color.Transparent, Color.Black.copy(alpha = 0.5f))
                            )
                        )
                        .align(Alignment.BottomCenter)
            )
        }
    }
}
