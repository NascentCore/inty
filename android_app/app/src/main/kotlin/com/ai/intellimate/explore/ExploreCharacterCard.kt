package com.ai.intellimate.explore

import ai.sxwl.android.common.utils.HeartAppUtils
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.design.noRippleClickable
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
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil3.compose.AsyncImage
import coil3.request.ImageRequest
import com.ai.intellimate.ui.components.ShimmerPlaceholder
import com.ai.intellimate.ui.components.SmartTagsLayout
import com.ai.intellimate.xb.components.IgnoreSystemFontScaling

/** Explore页面的角色卡片组件 */
@Composable
fun ExploreCharacterCard(
    modifier: Modifier = Modifier,
    agentInfo: AgentInfo,
    onClick: () -> Unit,
    index: Int? = null,
) {
    // 缓存渐变画笔，避免每次重组时重新创建
    val gradientBrush = remember {
        Brush.verticalGradient(
            colors = listOf(Color.Transparent, Color.Black.copy(.6f), Color.Black.copy(.95f))
        )
    }

    // 缓存过滤后的标签，避免每次重组时重新计算
    val filteredTags = remember(agentInfo.tags) { agentInfo.tags?.filterNotNull() ?: emptyList() }

    // 获取图片URL
    val imageUrl =
        remember(agentInfo.id, agentInfo.background, agentInfo.avatar) { agentInfo.getAlbumImage() }

    // 图片加载状态 - 使用稳定的key避免不必要的重组
    var imageLoaded by remember(agentInfo.id) { mutableStateOf(false) }

    // 判断是否是 debug 模式
    val isDebugMode = HeartAppUtils.isAppDebugMode()

    Box(
        modifier =
            modifier.fillMaxWidth().aspectRatio(agentInfo.imageAspectRatio()).noRippleClickable {
                onClick()
            }
    ) {
        // 背景图片层
        Box(
            modifier =
                Modifier.fillMaxSize()
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
            if (!imageLoaded) {
                ShimmerPlaceholder(modifier = Modifier.fillMaxSize(), cornerRadius = 8.dp)
            }

            AsyncImage(
                modifier = Modifier.fillMaxSize(),
                model = ImageRequest.Builder(LocalContext.current).data(imageUrl).build(),
                contentDescription = null,
                contentScale = ContentScale.Crop,
                alignment = Alignment.TopCenter,
                onSuccess = {
                    // 只在状态真正改变时才更新，避免不必要的重组
                    if (!imageLoaded) {
                        imageLoaded = true
                    }
                },
                onError = {
                    // 只在状态真正改变时才更新，避免不必要的重组
                    if (imageLoaded) {
                        imageLoaded = false
                    }
                },
            )
        }

        // Debug 模式下显示索引（左上角）
        if (isDebugMode && index != null) {
            Box(
                modifier =
                    Modifier.align(Alignment.TopStart)
                        .padding(8.dp)
                        .background(
                            color = Color.Black.copy(alpha = 0.7f),
                            shape = RoundedCornerShape(4.dp),
                        )
                        .padding(horizontal = 6.dp, vertical = 4.dp),
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
                Modifier.fillMaxWidth()
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
                Box(modifier = Modifier.fillMaxWidth().height(16.dp)) {
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
