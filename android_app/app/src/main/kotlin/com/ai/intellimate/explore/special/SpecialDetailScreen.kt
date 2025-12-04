package com.ai.intellimate.explore.special

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.design.theme.HeartColor
import ai.sxwl.android.design.ui.HeartTopAppBar
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil3.compose.AsyncImage
import com.ai.intellimate.ui.components.SmartTagsLayout

/**
 * 主题详情页面配置常量
 */
private object ThemedDetailConfig {
    val EventCardHeight = 140.dp
    val EventCardPadding = 16.dp
    val EventCardCornerRadius = 6.dp
    val EventDescriptionMaxLines = 4
    val CharacterCardHeight = 142.dp
    val CharacterImageWidth = 80.dp
    val CharacterCardSpacing = 8.dp
    val CharacterCardPadding = 8.dp
    val CharacterCardCornerRadius = 6.dp
    val ListSpacing = 24.dp
    val ContentHorizontalPadding = 16.dp
}

/**
 * 主题详情页面
 */
@Composable
fun ThemedDetailScreen(
    viewModel: SpecialDetailVM,
    onBack: () -> Unit,
    onClickAgent: (AgentInfo) -> Unit,
) {
    val themeTitle by viewModel.themeTitle.collectAsState()
    val eventDescription by viewModel.eventDescription.collectAsState()
    val isEventExpanded by viewModel.isEventExpanded.collectAsState()
    val agents by viewModel.agents.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(HeartColor.primaryColor)
    ) {
        HeartTopAppBar(
            title = themeTitle,
            onBack = onBack,
        )
        
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = androidx.compose.foundation.layout.PaddingValues(
                horizontal = ThemedDetailConfig.ContentHorizontalPadding,
                vertical = ThemedDetailConfig.ListSpacing
            ),
            verticalArrangement = Arrangement.spacedBy(ThemedDetailConfig.ListSpacing)
        ) {
            item {
                EventCard(
                    description = eventDescription,
                    isExpanded = isEventExpanded,
                    onToggleExpanded = { viewModel.toggleEventExpanded() }
                )
            }
            
            items(agents) { agent ->
                ThemedCharacterCard(
                    agent = agent,
                    onClick = { onClickAgent(agent) }
                )
            }
        }
    }
}

/**
 * 事件卡片组件
 */
@Composable
private fun EventCard(
    description: String,
    isExpanded: Boolean,
    onToggleExpanded: () -> Unit,
) {
    val rotationAngle by animateFloatAsState(
        targetValue = if (isExpanded) 180f else 0f,
        animationSpec = tween(durationMillis = 300),
        label = "arrowRotation"
    )
    
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(ThemedDetailConfig.EventCardHeight)
    ) {
        // 背景层（带模糊效果）
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(
                    color = Color(0x991C1523),
                    shape = RoundedCornerShape(ThemedDetailConfig.EventCardCornerRadius)
                )
        )
        
        // 内容层
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(ThemedDetailConfig.EventCardPadding)
        ) {
            Text(
                text = description,
                fontSize = 12.sp,
                lineHeight = 16.sp,
                color = Color(0xB2FFFFFF),
                maxLines = if (isExpanded) Int.MAX_VALUE else ThemedDetailConfig.EventDescriptionMaxLines,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.weight(1f)
            )
            
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.End,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .size(24.dp)
                        .clickable { onToggleExpanded() },
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.KeyboardArrowDown,
                        contentDescription = null,
                        modifier = Modifier.rotate(rotationAngle),
                        tint = Color.White
                    )
                }
            }
        }
        
        // 内阴影效果（根据 Figma 设计）
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(
                    brush = Brush.linearGradient(
                        colors = listOf(
                            Color(0x0AFFFFFF),
                            Color(0x19E1A9F6)
                        )
                    ),
                    shape = RoundedCornerShape(ThemedDetailConfig.EventCardCornerRadius)
                )
        )
    }
}

/**
 * 主题角色卡片组件（横向布局）
 */
@Composable
private fun ThemedCharacterCard(
    agent: AgentInfo,
    onClick: () -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .height(ThemedDetailConfig.CharacterCardHeight)
            .background(
                color = Color(0x991C1523),
                shape = RoundedCornerShape(ThemedDetailConfig.CharacterCardCornerRadius)
            )
            .border(
                width = 0.5.dp,
                color = Color(0x33FFFFFF),
                shape = RoundedCornerShape(ThemedDetailConfig.CharacterCardCornerRadius)
            )
            .clickable { onClick() },
        horizontalArrangement = Arrangement.spacedBy(ThemedDetailConfig.CharacterCardSpacing)
    ) {
        // 角色图片（左侧，固定宽度）
        Box(
            modifier = Modifier
                .width(ThemedDetailConfig.CharacterImageWidth)
                .fillMaxSize()
        ) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(
                        color = Color(0x1AFFFFFF),
                        shape = RoundedCornerShape(
                            topStart = ThemedDetailConfig.CharacterCardCornerRadius,
                            bottomStart = ThemedDetailConfig.CharacterCardCornerRadius,
                            topEnd = 0.dp,
                            bottomEnd = 0.dp
                        )
                    )
            ) {
                AsyncImage(
                    model = agent.getAlbumImage(),
                    contentDescription = agent.name,
                    modifier = Modifier.fillMaxSize(),
                    contentScale = ContentScale.Crop
                )
            }
        }
        
        // 角色信息（右侧，自适应宽度）
        Column(
            modifier = Modifier
                .weight(1f)
                .padding(ThemedDetailConfig.CharacterCardPadding),
            verticalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            Text(
                text = agent.name,
                fontSize = 14.sp,
                lineHeight = 22.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color.White,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )

            val tags = agent.tags
            Text(
                text = agent.intro,
                fontSize = 12.sp,
                lineHeight = 16.sp,
                color = Color(0xB2FFFFFF),
                maxLines = if (tags.isNullOrEmpty()) 4 else 3,
                overflow = TextOverflow.Ellipsis
            )
            
            if (!tags.isNullOrEmpty()) {
                SmartTagsLayout(
                    tags = tags.filterNotNull(),
                    modifier = Modifier.fillMaxWidth(),
                    isCardTag = true
                )
            }
        }
    }
}
