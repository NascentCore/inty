package com.ai.intellimate.explore

import ai.sxwl.android.common.utils.HeartAppUtils
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.design.noRippleClickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.intellimate.ui.components.CharacterCard
import com.ai.intellimate.ui.components.SmartTagsLayout
import com.ai.intellimate.xb.components.IgnoreSystemFontScaling

// 固定使用 9:16 宽高比
private const val CARD_ASPECT_RATIO = 9f / 16f

/** Explore页面的角色卡片组件 */
@Composable
fun ExploreCharacterCard(
    modifier: Modifier = Modifier,
    agentInfo: AgentInfo,
    onClick: () -> Unit,
    index: Int? = null,
) {

    // 缓存过滤后的标签，避免每次重组时重新计算
    val filteredTags = remember(agentInfo.tags) { agentInfo.tags?.filterNotNull() ?: emptyList() }

    // 获取图片URL
    val imageUrl =
        remember(agentInfo.id, agentInfo.background, agentInfo.avatar) { agentInfo.getAlbumImage() }

    // 判断是否是 debug 模式
    val isDebugMode = HeartAppUtils.isAppDebugMode()

    CharacterCard(
        modifier =
            modifier
                .fillMaxWidth()
                .aspectRatio(CARD_ASPECT_RATIO)
                .noRippleClickable { onClick() },
        imageUrl = imageUrl,
        title = agentInfo.name,
        subtitle = agentInfo.intro,
        subtitleMaxLines = 3,
        shape =
            RoundedCornerShape(
                topStart = 7.dp,
                topEnd = 7.dp,
                bottomStart = 8.dp,
                bottomEnd = 8.dp,
            ),
        gradientBrush =
            Brush.verticalGradient(
                colors = listOf(Color.Transparent, Color.Black.copy(.6f), Color.Black.copy(.95f))
            ),
        textPadding = PaddingValues(start = 8.dp, end = 8.dp, top = 16.dp, bottom = 8.dp),
        shimmerCornerRadius = 8.dp,
        overlayContent = {
            if (isDebugMode && index != null) {
                Box(
                    modifier =
                        Modifier.align(Alignment.TopStart)
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
        },
        footerContent = {
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
        },
    )
}
