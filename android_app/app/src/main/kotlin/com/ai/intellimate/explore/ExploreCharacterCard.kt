package com.ai.intellimate.explore

import ai.sxwl.android.common.utils.HeartAppUtils
import ai.sxwl.android.data.api.getCdnImageUrl
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.design.noRippleClickable
import android.graphics.drawable.Animatable
import android.graphics.drawable.AnimatedImageDrawable
import android.graphics.drawable.Drawable
import android.widget.ImageView
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
import androidx.compose.runtime.DisposableEffect
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
import androidx.compose.ui.viewinterop.AndroidView
import coil3.SingletonImageLoader
import coil3.compose.AsyncImage
import coil3.request.ImageRequest
import coil3.request.target
import com.ai.intellimate.ui.components.ShimmerPlaceholder
import com.ai.intellimate.ui.components.SmartTagsLayout
import com.ai.intellimate.xb.components.IgnoreSystemFontScaling
import kotlinx.coroutines.delay

// 固定使用 9:16 宽高比
private const val CARD_ASPECT_RATIO = 9f / 16f

/** Explore页面的角色卡片组件 */
@Composable
fun ExploreCharacterCard(
    modifier: Modifier = Modifier,
    agentInfo: AgentInfo,
    onClick: () -> Unit,
    index: Int? = null,
    shouldPlayAnimated: Boolean = false,
) {

    // 缓存渐变画笔，避免每次重组时重新创建
    val gradientBrush = remember {
        Brush.verticalGradient(
            colors = listOf(Color.Transparent, Color.Black.copy(.6f), Color.Black.copy(.95f))
        )
    }

    // 底部渐变背景画笔，用于填充图片高度不足时的空白区域
    val bottomGradientBrush = remember {
        Brush.verticalGradient(colors = listOf(Color.Black.copy(.95f), Color.Black.copy(.95f)))
    }

    // 缓存过滤后的标签，避免每次重组时重新计算
    val filteredTags = remember(agentInfo.tags) { agentInfo.tags?.filterNotNull() ?: emptyList() }

    // 获取静态图片URL
    val staticImageUrl =
        remember(agentInfo.id, agentInfo.background, agentInfo.avatar) { agentInfo.getAlbumImage() }

    // 获取动图URL（使用 CDN 优化）
    val animatedImageUrl =
        remember(agentInfo.id, agentInfo.backgroundAnimatedUrl) {
            agentInfo.backgroundAnimatedUrl.takeIf { it.isNotBlank() }
                ?.let { getCdnImageUrl(it, width = 1080, quality = 80) }
        }

    // 是否有动图
    val hasAnimatedImage = animatedImageUrl != null

    // 静态图片加载状态
    var staticImageLoaded by remember(agentInfo.id) { mutableStateOf(false) }

    // 动图加载状态
    var animatedImageLoaded by remember(agentInfo.id) { mutableStateOf(false) }

    // 是否显示动图（动图加载成功且应该播放）
    var showAnimatedImage by remember(agentInfo.id) { mutableStateOf(false) }

    // 动图 Drawable 引用（用于控制播放）
    var animatedDrawable by remember(agentInfo.id) { mutableStateOf<Drawable?>(null) }

    // 判断是否是 debug 模式
    val isDebugMode = HeartAppUtils.isAppDebugMode()

    Box(
        modifier =
            modifier
                .fillMaxWidth()
                .aspectRatio(CARD_ASPECT_RATIO)
                .noRippleClickable { onClick() }
    ) {
        // 底部渐变背景层 - 填充整个容器，确保图片高度不足时有渐变背景
        Box(
            modifier =
                Modifier
                    .fillMaxSize()
                    .background(
                        brush = bottomGradientBrush,
                        shape =
                            RoundedCornerShape(
                                topStart = 7.dp,
                                topEnd = 7.dp,
                                bottomStart = 8.dp,
                                bottomEnd = 8.dp,
                            ),
                    )
        )

        // 背景图片层
        Box(
            modifier =
                Modifier
                    .fillMaxSize()
                    .clip(
                        RoundedCornerShape(
                            topStart = 7.dp,
                            topEnd = 7.dp,
                            bottomStart = 8.dp,
                            bottomEnd = 8.dp,
                        )
                    )
        ) {
            // 使用 Shimmer 占位符
            if (!staticImageLoaded && !animatedImageLoaded) {
                ShimmerPlaceholder(modifier = Modifier.fillMaxSize(), cornerRadius = 8.dp)
            }

            // 静态图片层（优先显示）
            if (staticImageUrl != null) {
                val staticImageAlpha by animateFloatAsState(
                    targetValue = if (showAnimatedImage) 0f else 1f,
                    animationSpec = tween(durationMillis = 300),
                    label = "staticImageAlpha",
                )

                AsyncImage(
                    modifier = Modifier
                        .fillMaxSize()
                        .alpha(staticImageAlpha),
                    model = ImageRequest.Builder(LocalContext.current).data(staticImageUrl).build(),
                    contentDescription = null,
                    contentScale = ContentScale.Crop,
                    alignment = Alignment.TopCenter,
                    onSuccess = {
                        if (!staticImageLoaded) {
                            staticImageLoaded = true
                        }
                    },
                    onError = {
                        if (staticImageLoaded) {
                            staticImageLoaded = false
                        }
                    },
                )
            }

            // 动图层（异步加载，加载成功后切换显示）
            if (hasAnimatedImage) {
                val context = LocalContext.current
                val imageLoader = remember { SingletonImageLoader.get(context) }

                val animatedImageAlpha by animateFloatAsState(
                    targetValue = if (showAnimatedImage) 1f else 0f,
                    animationSpec = tween(durationMillis = 300),
                    label = "animatedImageAlpha",
                )

                // 使用 AndroidView + ImageView 来加载和显示动图，同时获取 Drawable 用于控制播放
                // 这是获取 Drawable 以控制播放的正确方法
                val animatedImageView = remember { ImageView(context) }

                LaunchedEffect(animatedImageUrl, agentInfo.id) {
                    if (!animatedImageLoaded) {
                        // 使用 target(ImageView) 方法，Coil 会将 Drawable 设置到 ImageView
                        val request =
                            ImageRequest.Builder(context)
                                .data(animatedImageUrl)
                                .target(animatedImageView)
                                .build()
                        imageLoader.enqueue(request)

                        // 定期检查 drawable 是否已加载
                        while (!animatedImageLoaded) {
                            val drawable = animatedImageView.drawable
                            if (drawable != null) {
                                animatedImageLoaded = true
                                animatedDrawable = drawable
                                break
                            }
                            delay(50)
                        }
                    }
                }

                // 使用 AndroidView 显示 ImageView，通过 alpha 控制显示/隐藏
                AndroidView(
                    factory = { animatedImageView },
                    modifier = Modifier
                        .fillMaxSize()
                        .alpha(animatedImageAlpha)
                )

                // 当动图加载成功且应该显示时，显示动图
                LaunchedEffect(animatedImageLoaded, shouldPlayAnimated) {
                    if (animatedImageLoaded && shouldPlayAnimated) {
                        showAnimatedImage = true
                    } else if (!shouldPlayAnimated) {
                        showAnimatedImage = false
                    }
                }

                // 控制动图播放/暂停
                LaunchedEffect(shouldPlayAnimated, showAnimatedImage, animatedDrawable) {
                    val drawable = animatedDrawable
                    if (drawable is Animatable) {
                        if (shouldPlayAnimated && showAnimatedImage) {
                            // 开始播放（循环播放）
                            if (drawable is AnimatedImageDrawable) {
                                drawable.repeatCount = AnimatedImageDrawable.REPEAT_INFINITE
                            }
                            if (!drawable.isRunning) {
                                drawable.start()
                            }
                        } else {
                            // 暂停播放
                            if (drawable.isRunning) {
                                drawable.stop()
                            }
                        }
                    }
                }

                // 清理：组件销毁时停止播放
                DisposableEffect(agentInfo.id) {
                    onDispose {
                        animatedDrawable?.let { drawable ->
                            if (drawable is Animatable && drawable.isRunning) {
                                drawable.stop()
                            }
                        }
                    }
                }
            }
        }

        // Debug 模式下显示索引（左上角）
        if (isDebugMode && index != null) {
            Box(
                modifier =
                    Modifier
                        .align(Alignment.TopStart)
                        .padding(8.dp)
                        .background(
                            color = Color.Black.copy(alpha = 0.7f),
                            shape = RoundedCornerShape(4.dp),
                        )
                        .padding(horizontal = 6.dp, vertical = 4.dp)
            ) {
                Text(
                    text = "#$index",
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color.White,
                )
            }
        }

        // 文本内容层 - 立即显示，不依赖图片加载状态
        Column(
            modifier =
                Modifier
                    .fillMaxWidth()
                    .background(
                        brush = gradientBrush,
                        shape =
                            RoundedCornerShape(
                                bottomStart = 7.dp,
                                bottomEnd = 7.dp,
                            ), // 比图片的倒角8.dp小1，来遮挡像素级白边
                    )
                    .padding(start = 8.dp, end = 8.dp, top = 16.dp, bottom = 8.dp)
                    .align(Alignment.BottomCenter),
            verticalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            Text(
                modifier = Modifier,
                text = agentInfo.name,
                fontSize = 14.sp,
                lineHeight = 22.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color.White,
            )

            Text(
                modifier = Modifier,
                text = agentInfo.intro,
                fontSize = 12.sp,
                lineHeight = 12.sp,
                fontWeight = FontWeight.Normal,
                color = Color(0xB2FFFFFF),
                maxLines = 3,
                overflow = TextOverflow.Ellipsis,
            )

            if (filteredTags.isNotEmpty()) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(16.dp)
                ) {
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
