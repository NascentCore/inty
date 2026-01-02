package com.ai.intellimate.explore

import ai.sxwl.android.common.utils.HeartAppUtils
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.design.theme.AppColors
import ai.sxwl.android.utils.LogUtils
import android.graphics.drawable.AnimatedImageDrawable
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.outlined.FavoriteBorder
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.IconButtonDefaults
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
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
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
    val FavoriteButtonPadding = 10.dp
    val FavoriteButtonSize = 36.dp
    val FavoriteIconSize = 18.dp
    val VipCornerSize = 64.dp
    val VipFavoriteExtraPadding = 8.dp
    val VipFavoriteTopOffset = 4.dp // VIP 角标与收藏按钮之间的间距
    val VipTextPaddingTop = 6.dp
    val VipTextPaddingEnd = 6.dp
    val VipTextSize = 11.sp
}

// 判断是否为动图URL（非视频）
private fun isAnimatedImageUrl(url: String?): Boolean {
    if (url.isNullOrBlank()) return false
    val lowerUrl = url.lowercase()
    return lowerUrl.endsWith(".gif") ||
        lowerUrl.endsWith(".webp") ||
        lowerUrl.endsWith(".avif") ||
        lowerUrl.contains(".gif?") ||
        lowerUrl.contains(".webp?") ||
        lowerUrl.contains(".avif?")
}

private fun normalizeTag(tag: String): String {
    val trimmed = tag.trim()
    if (trimmed.isEmpty()) return ""
    return trimmed.removePrefix("#").lowercase()
}

/**
 * Explore 网格角色卡片的 VIP 右上角高亮角标。
 *
 * 使用范围：
 * - 仅用于 Explore 推荐列表的 `ExploreCharacterCard`。
 *
 * 预期视觉效果：
 * - 在卡片右上角绘制一个高饱和强对比色的三角角标，覆盖在图片上方但不影响收藏按钮的点击。
 * - 角标内显示 “VIP” 文案，强化视觉提醒。
 *
 * 可配置项：
 * - [label]：角标文案（来自 string 资源，便于本地化与一致性管理）。
 */
@Composable
private fun VipCornerHighlighter(
    modifier: Modifier = Modifier,
    label: String,
    contentDescription: String,
) {
    Box(
        modifier =
            modifier.size(CardConfig.VipCornerSize).semantics {
                this.contentDescription = contentDescription
            }
    ) {
        Canvas(modifier = Modifier.fillMaxSize()) {
            val triangle =
                Path().apply {
                    moveTo(size.width, 0f)
                    lineTo(size.width, size.height)
                    lineTo(0f, 0f)
                    close()
                }
            drawPath(path = triangle, color = AppColors.VipHighlighterStrong)
        }

        Text(
            text = label,
            modifier =
                Modifier.align(Alignment.TopEnd)
                    .padding(
                        top = CardConfig.VipTextPaddingTop,
                        end = CardConfig.VipTextPaddingEnd,
                    ),
            fontSize = CardConfig.VipTextSize,
            fontWeight = FontWeight.Black,
            color = AppColors.Background,
            maxLines = 1,
        )
    }
}

/** Explore页面的角色卡片组件 */
@Composable
fun ExploreCharacterCard(
    modifier: Modifier = Modifier,
    agentInfo: AgentInfo,
    onClick: () -> Unit,
    index: Int? = null,
    shouldPlayAnimated: Boolean = false,
    showNewTag: Boolean = false,
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

    // 缓存过滤后的标签，如果 showNewTag 为 true 则添加 #new tag
    val filteredTags = remember(agentInfo.tags, showNewTag) {
        val baseTags = agentInfo.tags?.filterNotNull() ?: emptyList()
        if (showNewTag && !baseTags.any { normalizeTag(it) == "new" }) {
            baseTags + "#new"
        } else {
            baseTags
        }
    }
    val isVip = remember(filteredTags) { filteredTags.any { normalizeTag(it) == "vip" } }
    val favoriteButtonTopPadding =
        remember(isVip) {
            if (isVip) {
                CardConfig.VipCornerSize + CardConfig.VipFavoriteTopOffset
            } else {
                CardConfig.FavoriteButtonPadding
            }
        }
    val favoriteButtonEndPadding =
        remember(isVip) {
            if (isVip) {
                CardConfig.FavoriteButtonPadding + CardConfig.VipFavoriteExtraPadding
            } else {
                CardConfig.FavoriteButtonPadding
            }
        }

    // 获取静态图片URL
    val staticImageUrl =
        remember(agentInfo.id, agentInfo.background, agentInfo.avatar) { agentInfo.getAlbumImage() }

    // 获取动图URL（只处理动图，不处理视频）
    val animatedImageUrl =
        remember(agentInfo.id, agentInfo.backgroundAnimatedUrl) {
            agentInfo.backgroundAnimatedUrl.takeIf { url ->
                url.isNotBlank() && isAnimatedImageUrl(url)
            }
        }

    // 图片加载状态
    var staticImageLoaded by remember(agentInfo.id) { mutableStateOf(false) }
    var animatedImageLoaded by remember(agentInfo.id) { mutableStateOf(false) }
    var animatedImageDrawable by
        remember(agentInfo.id) { mutableStateOf<AnimatedImageDrawable?>(null) }

    // 是否显示动图（动图加载成功且应该播放）
    var showAnimatedImage by remember(agentInfo.id) { mutableStateOf(false) }

    var isFavorite by
        remember(agentInfo.id) { mutableStateOf(IntySetting.isExploreAgentFavorite(agentInfo.id)) }
    val favoriteIcon = if (isFavorite) Icons.Filled.Favorite else Icons.Outlined.FavoriteBorder
    val favoriteTint = if (isFavorite) Color(0xFFFF5A8A) else Color.White
    val favoriteDescription = if (isFavorite) "Remove from favorites" else "Add to favorites"

    // 当动图加载成功且应该播放时，显示动图并开始播放
    LaunchedEffect(animatedImageLoaded, shouldPlayAnimated, animatedImageDrawable) {
        showAnimatedImage = animatedImageLoaded && shouldPlayAnimated
        if (showAnimatedImage && animatedImageDrawable != null) {
            val drawable = animatedImageDrawable
            if (drawable != null && !drawable.isRunning) {
                try {
                    drawable.start()
                } catch (e: Exception) {
                    LogUtils.e("ExploreCharacterCard - 启动动画失败: ${e.message}")
                }
            }
        } else if (!showAnimatedImage && animatedImageDrawable != null) {
            try {
                animatedImageDrawable?.stop()
            } catch (e: Exception) {
                LogUtils.e("ExploreCharacterCard - 停止动画失败: ${e.message}")
            }
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

        // Debug 模式下显示索引或私有标识
        if (isDebugMode) {
            val isPrivate = agentInfo.visibility.equals("private", ignoreCase = true)
            val displayText =
                when {
                    index != null && isPrivate -> {
                        "#$index ${context.getString(com.ai.intellimate.R.string.private_label)}"
                    }
                    index != null -> {
                        "#$index"
                    }
                    isPrivate -> {
                        context.getString(com.ai.intellimate.R.string.private_label)
                    }
                    else -> {
                        null
                    }
                }

            if (displayText != null) {
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
                        text = displayText,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.White,
                    )
                }
            }
        }

        if (isVip) {
            VipCornerHighlighter(
                modifier =
                    Modifier.align(Alignment.TopEnd)
                        .clip(RoundedCornerShape(topEnd = CardConfig.CornerRadius)),
                label = stringResource(com.ai.intellimate.R.string.vip_badge_label),
                contentDescription =
                    stringResource(com.ai.intellimate.R.string.vip_badge_content_description),
            )
        }

        // 收藏按钮
        IconButton(
            modifier =
                Modifier.align(Alignment.TopEnd)
                    .padding(top = favoriteButtonTopPadding, end = favoriteButtonEndPadding)
                    .size(CardConfig.FavoriteButtonSize),
            onClick = {
                val nextFavorite = !isFavorite
                isFavorite = nextFavorite
                IntySetting.setExploreAgentFavorite(agentInfo.id, nextFavorite)
            },
            colors =
                IconButtonDefaults.iconButtonColors(
                    contentColor = favoriteTint,
                    containerColor = Color.Black.copy(alpha = 0.35f),
                ),
        ) {
            Icon(
                imageVector = favoriteIcon,
                contentDescription = favoriteDescription,
                tint = favoriteTint,
                modifier = Modifier.size(CardConfig.FavoriteIconSize),
            )
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
