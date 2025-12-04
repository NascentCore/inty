package com.ai.intellimate.explore

import ai.sxwl.android.common.utils.HeartAppUtils
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.design.noRippleClickable
import android.graphics.drawable.AnimatedImageDrawable
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil3.asDrawable
import coil3.compose.AsyncImage
import coil3.compose.AsyncImagePainter
import coil3.compose.SubcomposeAsyncImage
import coil3.compose.SubcomposeAsyncImageContent
import coil3.request.ImageRequest
import com.ai.intellimate.ui.components.ShimmerPlaceholder
import com.ai.intellimate.ui.components.SmartTagsLayout
import com.ai.intellimate.xb.components.IgnoreSystemFontScaling

// 固定使用 9:16 宽高比
private const val CARD_ASPECT_RATIO = 9f / 16f

// 卡片圆角配置
private object CardConfig {
    val CornerRadius = 7.dp
    val BottomCornerRadius = 8.dp
    val TextPadding = 8.dp
    val TextTopPadding = 16.dp
    val TextSpacing = 4.dp
    val TagHeight = 16.dp
    val DebugIndexPadding = 8.dp
    val DebugIndexInnerPadding = 6.dp to 4.dp
}

/** Explore页面的角色卡片组件 */
@Composable
fun ExploreCharacterCard(
    modifier: Modifier = Modifier,
    agentInfo: AgentInfo,
    onClick: () -> Unit,
    index: Int? = null,
    shouldPlayAnimated: Boolean = false,
) {
    val context = LocalContext.current

    // 缓存渐变画笔
    val gradientBrush = remember {
        Brush.verticalGradient(
            colors =
                listOf(
                    Color.Transparent,
                    Color.Black.copy(alpha = 0.6f),
                    Color.Black.copy(alpha = 0.95f),
                )
        )
    }

    val bottomGradientBrush = remember {
        Brush.verticalGradient(
            colors = listOf(Color.Black.copy(alpha = 0.95f), Color.Black.copy(alpha = 0.95f))
        )
    }

    // 缓存过滤后的标签
    val filteredTags = remember(agentInfo.tags) { agentInfo.tags?.filterNotNull() ?: emptyList() }

    // 获取静态图片URL
    val staticImageUrl =
        remember(agentInfo.id, agentInfo.background, agentInfo.avatar) { agentInfo.getAlbumImage() }

    // 获取动图URL
    val animatedImageUrl =
        remember(agentInfo.id, agentInfo.backgroundAnimatedUrl) {
            agentInfo.backgroundAnimatedUrl.takeIf { it.isNotBlank() }
        }

    // 图片加载状态
    var staticImageLoaded by remember(agentInfo.id) { mutableStateOf(false) }
    var animatedImageLoaded by remember(agentInfo.id) { mutableStateOf(false) }
    var animatedImageDrawable by remember(agentInfo.id) { mutableStateOf<AnimatedImageDrawable?>(null) }

    // 是否显示动图（动图加载成功且应该播放）
    var showAnimatedImage by remember(agentInfo.id) { mutableStateOf(false) }

    // 当动图加载成功且应该播放时，显示动图并开始播放
    LaunchedEffect(animatedImageLoaded, shouldPlayAnimated, animatedImageDrawable) {
        showAnimatedImage = animatedImageLoaded && shouldPlayAnimated
        if (showAnimatedImage && animatedImageDrawable != null) {
            val drawable = animatedImageDrawable
            if (drawable != null && !drawable.isRunning) {
                drawable.start()
            }
        } else if (!showAnimatedImage && animatedImageDrawable != null) {
            animatedImageDrawable?.stop()
        }
    }

    val isDebugMode = HeartAppUtils.isAppDebugMode()

    Box(
        modifier =
            modifier.fillMaxWidth().aspectRatio(CARD_ASPECT_RATIO).noRippleClickable { onClick() }
    ) {
        // 底部渐变背景层
        Box(
            modifier =
                Modifier.fillMaxSize()
                    .background(
                        brush = bottomGradientBrush,
                        shape =
                            RoundedCornerShape(
                                topStart = CardConfig.CornerRadius,
                                topEnd = CardConfig.CornerRadius,
                                bottomStart = CardConfig.BottomCornerRadius,
                                bottomEnd = CardConfig.BottomCornerRadius,
                            ),
                    )
        )

        // 背景图片层
        Box(
            modifier =
                Modifier.fillMaxSize()
                    .clip(
                        RoundedCornerShape(
                            topStart = CardConfig.CornerRadius,
                            topEnd = CardConfig.CornerRadius,
                            bottomStart = CardConfig.BottomCornerRadius,
                            bottomEnd = CardConfig.BottomCornerRadius,
                        )
                    )
        ) {
            // 加载占位符
            if (!staticImageLoaded && !animatedImageLoaded) {
                ShimmerPlaceholder(
                    modifier = Modifier.fillMaxSize(),
                    cornerRadius = CardConfig.CornerRadius,
                )
            }

            // 静态图片层
            if (staticImageUrl != null) {
                val staticImageAlpha by
                    animateFloatAsState(
                        targetValue = if (showAnimatedImage) 0f else 1f,
                        animationSpec = tween(durationMillis = 300),
                        label = "staticImageAlpha",
                    )

                AsyncImage(
                    modifier = Modifier.fillMaxSize().alpha(staticImageAlpha),
                    model = ImageRequest.Builder(context).data(staticImageUrl).build(),
                    contentDescription = null,
                    contentScale = ContentScale.Crop,
                    alignment = Alignment.TopCenter,
                    onSuccess = { staticImageLoaded = true },
                    onError = { staticImageLoaded = false },
                )
            }

            // 动图层（异步加载，加载成功后切换显示）
            if (animatedImageUrl != null) {
                val animatedImageAlpha by
                    animateFloatAsState(
                        targetValue = if (showAnimatedImage) 1f else 0f,
                        animationSpec = tween(durationMillis = 300),
                        label = "animatedImageAlpha",
                    )

                SubcomposeAsyncImage(
                    modifier = Modifier.fillMaxSize().alpha(animatedImageAlpha),
                    model = ImageRequest.Builder(context).data(animatedImageUrl).build(),
                    contentDescription = null,
                    contentScale = ContentScale.Crop,
                    alignment = Alignment.TopCenter,
                    onState = { state ->
                        if (state is AsyncImagePainter.State.Success) {
                            val drawable = state.result.image.asDrawable(context.resources)
                            if (drawable is AnimatedImageDrawable) {
                                if (animatedImageDrawable != drawable) {
                                    animatedImageDrawable = drawable
                                }
                                if (!animatedImageLoaded) {
                                    animatedImageLoaded = true
                                }
                            } else {
                                if (!animatedImageLoaded) {
                                    animatedImageLoaded = true
                                }
                            }
                        } else if (state is AsyncImagePainter.State.Error) {
                            animatedImageLoaded = false
                        }
                    },
                ) {
                    SubcomposeAsyncImageContent()
                }
            }
        }

        // Debug 模式下显示索引
        if (isDebugMode && index != null) {
            Box(
                modifier =
                    Modifier.align(Alignment.TopStart)
                        .padding(CardConfig.DebugIndexPadding)
                        .background(
                            color = Color.Black.copy(alpha = 0.7f),
                            shape = RoundedCornerShape(4.dp),
                        )
                        .padding(
                            horizontal = CardConfig.DebugIndexInnerPadding.first,
                            vertical = CardConfig.DebugIndexInnerPadding.second,
                        )
            ) {
                Text(
                    text = "#$index",
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color.White,
                )
            }
        }

        // 文本内容层
        Column(
            modifier =
                Modifier.fillMaxWidth()
                    .background(
                        brush = gradientBrush,
                        shape =
                            RoundedCornerShape(
                                bottomStart = CardConfig.CornerRadius,
                                bottomEnd = CardConfig.CornerRadius,
                            ),
                    )
                    .padding(
                        start = CardConfig.TextPadding,
                        end = CardConfig.TextPadding,
                        top = CardConfig.TextTopPadding,
                        bottom = CardConfig.TextPadding,
                    )
                    .align(Alignment.BottomCenter),
            verticalArrangement = Arrangement.spacedBy(CardConfig.TextSpacing),
        ) {
            Text(
                text = agentInfo.name,
                fontSize = 14.sp,
                lineHeight = 22.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color.White,
            )

            Text(
                text = agentInfo.intro,
                fontSize = 12.sp,
                lineHeight = 12.sp,
                fontWeight = FontWeight.Normal,
                color = Color(0xB2FFFFFF),
                maxLines = 3,
                overflow = TextOverflow.Ellipsis,
            )

            if (filteredTags.isNotEmpty()) {
                Box(modifier = Modifier.fillMaxWidth().height(CardConfig.TagHeight)) {
                    IgnoreSystemFontScaling {
                        SmartTagsLayout(
                            modifier = Modifier.matchParentSize(),
                            tags = filteredTags,
                            isCardTag = true,
                        )
                    }
                }
            }
        }
    }
}
