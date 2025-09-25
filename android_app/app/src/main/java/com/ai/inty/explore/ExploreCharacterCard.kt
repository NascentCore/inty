package com.ai.inty.explore

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.inty.base.IntyImage
import com.ai.inty.base.noRippleClickable
import com.ai.inty.beans.AgentInfo
import com.ai.inty.ui.components.ShimmerPlaceholder
import com.ai.inty.ui.components.SmartTagsLayout
import com.ai.inty.utils.AvatarManager
import com.ai.inty.utils.ImageSizeCache

/** Explore页面的角色卡片组件 */
@Composable
fun ExploreCharacterCard(modifier: Modifier = Modifier, agentInfo: AgentInfo, onClick: () -> Unit) {
    val density = LocalDensity.current

    // 缓存渐变画笔，避免每次重组时重新创建
    val gradientBrush = remember {
        Brush.verticalGradient(
            colors = listOf(Color.Transparent, Color.Black.copy(.5f), Color.Black.copy(.9f))
        )
    }

    // 缓存过滤后的标签，避免每次重组时重新计算
    val filteredTags = remember(agentInfo.tags) { agentInfo.tags?.filterNotNull() ?: emptyList() }

    // 获取图片URL
    val imageUrl =
        remember(agentInfo.id, agentInfo.background, agentInfo.avatar) {
            AvatarManager.getChatBackgroundForAgent(agentInfo)
        }

    // 动态计算卡片高度，基于图片宽高比
    // 使用mutableStateOf确保高度可以动态更新，实现瀑布流效果
    var cardHeight by
        remember(imageUrl) {
            mutableStateOf(with(density) { ImageSizeCache.getDisplayHeightPx(imageUrl).toDp() })
        }

    // 图片加载状态
    var imageLoaded by remember { mutableStateOf(false) }

    // 预加载图片尺寸，动态更新卡片高度
    LaunchedEffect(imageUrl) {
        if (!imageUrl.isNullOrEmpty()) {
            try {
                ImageSizeCache.preloadImageSize(imageUrl)
                // 预加载完成后，重新计算高度
                val newHeightPx = ImageSizeCache.getDisplayHeightPx(imageUrl)
                val newHeightDp = with(density) { newHeightPx.toDp() }
                if (newHeightDp != cardHeight) {
                    cardHeight = newHeightDp
                }
            } catch (e: Exception) {
                // 预加载失败，保持当前高度
            }
        }
    }

    Box(
        modifier =
            modifier
                .fillMaxWidth()
                .height(cardHeight)
                .clip(RoundedCornerShape(8.dp))
                .noRippleClickable { onClick() }
    ) {
        // 背景图片层
        Box(modifier = Modifier.fillMaxSize()) {
            // 使用 Shimmer 占位符
            if (!imageLoaded) {
                ShimmerPlaceholder(modifier = Modifier.fillMaxSize(), cornerRadius = 8.dp)
            }

            IntyImage(
                modifier = Modifier.fillMaxSize(),
                model = imageUrl,
                contentScale = ContentScale.Crop,
                onSuccess = { imageLoaded = true },
                onError = { imageLoaded = false },
            )
        }

        // 文本内容层 - 立即显示，不依赖图片加载状态
        Column(
            modifier =
                Modifier.fillMaxWidth()
                    .background(brush = gradientBrush)
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
