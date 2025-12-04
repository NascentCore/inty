package com.ai.intellimate.explore.special

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.design.theme.HeartColor
import ai.sxwl.android.design.ui.HeartTopAppBar
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Image
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
import androidx.compose.foundation.layout.offset
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
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shadow
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.TextLayoutResult
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.constraintlayout.compose.ConstraintLayout
import androidx.constraintlayout.compose.Dimension
import coil3.compose.AsyncImage
import com.ai.intellimate.R
import com.ai.intellimate.ui.components.SmartTagsLayout

/** 主题详情页面配置常量 */
private object ThemedDetailConfig {
    val EventCardHeight = 142.dp
    val EventCardPadding = 24.dp
    val EventCardCornerRadius = 6.dp
    val EventDescriptionMaxLines = 4
    // 边框渐变宽度
    val CharacterCardHeight = 142.dp
    val CharacterImageWidth = 80.dp
    val CharacterCardSpacing = 8.dp
    val CharacterCardPadding = 8.dp
    val CharacterCardCornerRadius = 6.dp
    val ListSpacing = 24.dp
    val ContentHorizontalPadding = 16.dp
}

/** 主题详情页面 */
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

    Column(modifier = Modifier.fillMaxSize().background(HeartColor.primaryColor)) {
        HeartTopAppBar(
            title = themeTitle,
            onBack = onBack,
            titleTextStyle =
                TextStyle(
                    fontSize = 20.sp,
                    color = Color.White,
                    fontWeight = FontWeight.Bold,
                    shadow =
                        Shadow(color = Color(0xFF8C8992), offset = Offset(5f, 3f), blurRadius = 15f),
                ),
        )

        EventCard(
            description = eventDescription,
            isExpanded = isEventExpanded,
            isChristmas = true,
            onToggleExpanded = { viewModel.toggleEventExpanded() },
        )

        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding =
                androidx.compose.foundation.layout.PaddingValues(
                    horizontal = ThemedDetailConfig.ContentHorizontalPadding,
                    vertical = ThemedDetailConfig.ListSpacing,
                ),
            verticalArrangement = Arrangement.spacedBy(ThemedDetailConfig.ListSpacing),
        ) {
            items(agents) { agent ->
                ThemedCharacterCard(agent = agent, onClick = { onClickAgent(agent) })
            }
        }
    }
}

/** 事件卡片组件 */
@Composable
private fun EventCard(
    description: String,
    isExpanded: Boolean,
    isChristmas: Boolean = false,
    onToggleExpanded: () -> Unit,
) {
    val rotationAngle by
        animateFloatAsState(
            targetValue = if (isExpanded) 180f else 0f,
            animationSpec = tween(durationMillis = 300),
            label = "arrowRotation",
        )

    ConstraintLayout(modifier = Modifier.fillMaxWidth()) {
        val (
            christmasBg,
            cardBg,
            content,
        ) = createRefs()

        // 卡片背景层（带边框向内渐变效果）
        Box(
            modifier =
                Modifier.constrainAs(cardBg) {
                    top.linkTo(christmasBg.top, 20.dp)
                    bottom.linkTo(christmasBg.bottom)
                    start.linkTo(parent.start)
                    end.linkTo(parent.end)
                    width = Dimension.fillToConstraints
                    height = Dimension.fillToConstraints
                }
        ) {

            // 横向渐变边框（左右边缘向内渐变）
            Box(
                modifier =
                    Modifier.fillMaxSize()
                        .background(
                            brush =
                                Brush.horizontalGradient(
                                    colors =
                                        listOf(
                                            Color.White.copy(0.1f),
                                            Color.Transparent,
                                            Color.Transparent,
                                            Color.Transparent,
                                            Color.Transparent,
                                            Color.Transparent,
                                            Color.White.copy(0.1f),
                                        )
                                ),
                            shape = RoundedCornerShape(ThemedDetailConfig.EventCardCornerRadius),
                        )
            )

            // 纵向渐变边框（上下边缘向内渐变）
            Box(
                modifier =
                    Modifier.matchParentSize()
                        .background(
                            brush =
                                Brush.verticalGradient(
                                    colors =
                                        listOf(
                                            Color.White.copy(0.1f),
                                            Color.Transparent,
                                            Color.Transparent,
                                            Color.Transparent,
                                            Color.Transparent,
                                            Color.White.copy(0.1f),
                                        )
                                ),
                            shape = RoundedCornerShape(ThemedDetailConfig.EventCardCornerRadius),
                        )
            )
        }

        if (isChristmas) {
            // 圣诞的装饰
            Image(
                modifier = Modifier.fillMaxWidth().constrainAs(christmasBg) {},
                painter = painterResource(R.drawable.img_christmas_bg),
                contentScale = ContentScale.Crop,
                contentDescription = "",
            )
        }

        // 文本内容层
        Box(
            modifier =
                Modifier.fillMaxWidth()
                    .height(ThemedDetailConfig.EventCardHeight)
                    .padding(ThemedDetailConfig.EventCardPadding)
                    .constrainAs(content) { centerVerticallyTo(cardBg) }
        ) {
            val density = LocalDensity.current
            var textLayoutResult by remember { mutableStateOf<TextLayoutResult?>(null) }
            var hasOverflow by remember { mutableStateOf(false) }
            var textPaddingEnd by remember { mutableIntStateOf(0) }
            var boxWidth by remember { mutableStateOf(0.dp) }

            // 获取 Box 的宽度
            Box(
                modifier =
                    Modifier.fillMaxWidth().onSizeChanged { size ->
                        boxWidth = with(density) { size.width.toDp() }
                    }
            )

            Text(
                text = description,
                style =
                    TextStyle(
                        fontSize = 12.sp,
                        lineHeight = 16.sp,
                        color = Color(0xB2FFFFFF),
                        letterSpacing = 0.1.sp, // 轻微增加字母间距，改善英文排版
                    ),
                maxLines =
                    if (isExpanded) Int.MAX_VALUE else ThemedDetailConfig.EventDescriptionMaxLines,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.fillMaxWidth().padding(end = textPaddingEnd.dp),
                onTextLayout = { layoutResult ->
                    textLayoutResult = layoutResult
                    val hasVisualOverflow = layoutResult.hasVisualOverflow
                    val lineCount = layoutResult.lineCount
                    hasOverflow =
                        hasVisualOverflow || lineCount > ThemedDetailConfig.EventDescriptionMaxLines
                    // 为箭头图标留出空间（24dp 图标 + 4dp 间距）
                    // 只在折叠时留出空间，展开时图标会跟随文本末尾，通过边界检查确保不超出
                    textPaddingEnd = if (hasOverflow && !isExpanded) 28 else 0
                },
            )

            // 箭头图标，定位在文本末尾，确保不超出边界
            if ((hasOverflow || isExpanded) && textLayoutResult != null) {
                val layout = textLayoutResult!!
                val lastLineIndex = layout.lineCount - 1
                val lastLineRight = layout.getLineRight(lastLineIndex)
                val lastLineBaseline = layout.getLineBaseline(lastLineIndex)

                // 计算图标位置：文本末尾 + 小间距
                val iconSize = 24.dp
                val iconSpacing = 4.dp
                val iconOffsetX =
                    with(density) {
                        val calculatedX = lastLineRight.toDp() + iconSpacing
                        // 确保图标不超出 Box 边界（boxWidth 是内容区域的宽度，已经减去了 padding）
                        val maxX = if (boxWidth > 0.dp) boxWidth - iconSize else calculatedX
                        calculatedX.coerceAtMost(maxX.coerceAtLeast(0.dp))
                    }
                // 使用基线位置，使图标与文本垂直居中对齐
                val iconOffsetY =
                    with(density) {
                        (lastLineBaseline - 12.sp.toPx()).toDp() // 12sp 是字体大小，用于垂直居中
                    }

                Icon(
                    imageVector = Icons.Default.KeyboardArrowDown,
                    contentDescription = null,
                    modifier =
                        Modifier.size(iconSize)
                            .offset(x = iconOffsetX, y = iconOffsetY)
                            .rotate(rotationAngle)
                            .noRippleClickable { onToggleExpanded() },
                    tint = Color.White,
                )
            }
        }
    }
}

/** 主题角色卡片组件（横向布局） */
@Composable
private fun ThemedCharacterCard(agent: AgentInfo, onClick: () -> Unit) {
    Row(
        modifier =
            Modifier.fillMaxWidth()
                .height(ThemedDetailConfig.CharacterCardHeight)
                .background(
                    color = Color(0x991C1523),
                    shape = RoundedCornerShape(ThemedDetailConfig.CharacterCardCornerRadius),
                )
                .border(
                    width = 0.5.dp,
                    color = Color(0x33FFFFFF),
                    shape = RoundedCornerShape(ThemedDetailConfig.CharacterCardCornerRadius),
                )
                .clickable { onClick() },
        horizontalArrangement = Arrangement.spacedBy(ThemedDetailConfig.CharacterCardSpacing),
    ) {
        // 角色图片（左侧，固定宽度）
        Box(modifier = Modifier.width(ThemedDetailConfig.CharacterImageWidth).fillMaxSize()) {
            Box(
                modifier =
                    Modifier.fillMaxSize()
                        .background(
                            color = Color(0x1AFFFFFF),
                            shape =
                                RoundedCornerShape(
                                    topStart = ThemedDetailConfig.CharacterCardCornerRadius,
                                    bottomStart = ThemedDetailConfig.CharacterCardCornerRadius,
                                    topEnd = 0.dp,
                                    bottomEnd = 0.dp,
                                ),
                        )
            ) {
                AsyncImage(
                    model = agent.getAlbumImage(),
                    contentDescription = agent.name,
                    modifier = Modifier.fillMaxSize(),
                    contentScale = ContentScale.Crop,
                )
            }
        }

        // 角色信息（右侧，自适应宽度）
        Column(
            modifier = Modifier.weight(1f).padding(ThemedDetailConfig.CharacterCardPadding),
            verticalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            Text(
                text = agent.name,
                fontSize = 14.sp,
                lineHeight = 22.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color.White,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )

            val tags = agent.tags
            Text(
                text = agent.intro,
                fontSize = 12.sp,
                lineHeight = 16.sp,
                color = Color(0xB2FFFFFF),
                maxLines = if (tags.isNullOrEmpty()) 4 else 3,
                overflow = TextOverflow.Ellipsis,
            )

            if (!tags.isNullOrEmpty()) {
                SmartTagsLayout(
                    tags = tags.filterNotNull(),
                    modifier = Modifier.fillMaxWidth(),
                    isCardTag = true,
                )
            }
        }
    }
}
