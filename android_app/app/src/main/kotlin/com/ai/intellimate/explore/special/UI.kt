package com.ai.intellimate.explore.special

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.design.isInPreview
import ai.sxwl.android.design.noRippleClickable
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
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
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
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.constraintlayout.compose.ConstraintLayout
import androidx.constraintlayout.compose.Dimension
import androidx.constraintlayout.compose.Visibility
import coil3.compose.AsyncImage
import com.ai.intellimate.R
import com.ai.intellimate.ui.components.ShimmerPlaceholder
import com.ai.intellimate.ui.components.SmartTagsLayout

/** 主题详情页面配置常量 */
internal object ThemedDetailConfig {
    val EventCardHeight = 142.dp
    val EventCardPadding = 24.dp
    val EventCardCornerRadius = 6.dp
    const val EventDescriptionMaxLines = 4

    // 边框渐变宽度
    val CharacterCardHeight = 142.dp
    val CharacterImageWidth = 80.dp
    val CharacterCardSpacing = 8.dp
    val CharacterCardPadding = 8.dp
    val CharacterCardCornerRadius = 6.dp
    val ListSpacing = 24.dp
    val ContentHorizontalPadding = 16.dp

    // 横向角色卡片列表配置
    val HorizontalCardListHeight = 242.dp
    val HorizontalCardListPadding = 16.dp
    val HorizontalCardItemWidth = 80.dp
    val HorizontalCardItemHeight = 142.dp
    val HorizontalCardItemSpacing = 12.dp
    val HorizontalCardItemCornerRadius = 8.dp
    val HorizontalCardTitleSpacing = 8.dp
    val HorizontalCardDescriptionSpacing = 4.dp
}

/** 事件卡片组件 */
@Composable
internal fun EventCard(description: String, isChristmas: Boolean = false) {
    var isExpanded by remember { mutableStateOf(false) }
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

        // 圣诞的装饰
        Image(
            modifier =
                Modifier.fillMaxWidth().constrainAs(christmasBg) {
                    visibility = if (isChristmas) Visibility.Visible else Visibility.Invisible
                },
            painter = painterResource(R.drawable.img_christmas_bg),
            contentScale = ContentScale.Crop,
            contentDescription = "",
        )
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
            // 记录文本是否真的需要展开（只在折叠状态下检测）
            var hasTextOverflow by remember { mutableStateOf(false) }
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
                    // 只在折叠状态下检测是否有 overflow，并保存状态
                    if (!isExpanded) {
                        val hasVisualOverflow = layoutResult.hasVisualOverflow
                        val lineCount = layoutResult.lineCount
                        hasTextOverflow =
                            hasVisualOverflow ||
                                lineCount > ThemedDetailConfig.EventDescriptionMaxLines
                        // 为箭头图标留出空间（24dp 图标 + 4dp 间距）
                        textPaddingEnd = if (hasTextOverflow) 28 else 0
                    } else {
                        // 展开状态下不需要留出空间
                        textPaddingEnd = 0
                    }
                },
            )

            // 箭头图标，定位在最后一行文本的最右端（Box 的右端），而不是紧跟文本
            // 只有当文本真的需要展开时才显示按钮
            if (hasTextOverflow && textLayoutResult != null) {
                val layout = textLayoutResult!!
                val lastLineIndex = layout.lineCount - 1
                val lastLineBaseline = layout.getLineBaseline(lastLineIndex)

                // 计算图标位置：位于 Box 的最右端
                val iconSize = 24.dp
                val iconOffsetX =
                    if (boxWidth > 0.dp) {
                        boxWidth - iconSize
                    } else {
                        0.dp
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
                            .noRippleClickable { isExpanded = !isExpanded },
                    tint = Color.White,
                )
            }
        }
    }
}

/** 主题角色卡片组件（横向布局） */
@Composable
internal fun ThemedCharacterCard(agent: AgentInfo, onClick: () -> Unit) {
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
        Box(modifier = Modifier.width(ThemedDetailConfig.CharacterImageWidth).fillMaxHeight()) {
            val imageUrl = if (isInPreview) null else agent.getAlbumImage()
            var imageLoaded by remember(agent.id) { mutableStateOf(false) }
            var imageLoadError by remember(agent.id) { mutableStateOf(false) }

            // 图片圆角形状（左侧圆角）
            val imageShape = remember {
                RoundedCornerShape(
                    topStart = ThemedDetailConfig.EventCardCornerRadius,
                    bottomStart = ThemedDetailConfig.EventCardCornerRadius,
                )
            }

            // 如果没有图片 URL，直接显示默认图片
            if (imageUrl == null || isInPreview) {
                AsyncImage(
                    model = ai.sxwl.android.design.R.drawable.img_girl_lite,
                    contentDescription = agent.name,
                    modifier = Modifier.fillMaxSize().clip(imageShape),
                    contentScale = ContentScale.Crop,
                )
            } else {
                // 显示加载占位符
                if (!imageLoaded && !imageLoadError) {
                    ShimmerPlaceholder(
                        modifier = Modifier.fillMaxSize().clip(imageShape),
                        cornerRadius = ThemedDetailConfig.EventCardCornerRadius,
                    )
                }

                // 如果加载失败，显示默认图片
                if (imageLoadError) {
                    AsyncImage(
                        model = ai.sxwl.android.design.R.drawable.img_girl_lite,
                        contentDescription = agent.name,
                        modifier = Modifier.fillMaxSize().clip(imageShape),
                        contentScale = ContentScale.Crop,
                    )
                }

                // 加载实际图片
                AsyncImage(
                    model = imageUrl,
                    contentDescription = agent.name,
                    modifier = Modifier.fillMaxSize().clip(imageShape),
                    contentScale = ContentScale.Crop,
                    onSuccess = { imageLoaded = true },
                    onError = {
                        imageLoadError = true
                        imageLoaded = false
                    },
                )
            }
        }

        // 角色信息（右侧，自适应宽度）
        Column(
            modifier =
                Modifier.fillMaxHeight()
                    .weight(1f)
                    .padding(ThemedDetailConfig.CharacterCardPadding),
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
                maxLines = if (tags.isNullOrEmpty()) 5 else 4,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.fillMaxWidth().weight(1f),
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

/** 横向角色卡片列表组件 */
@Composable
internal fun HorizontalAgentCardList(
    title: String,
    description: String,
    agents: List<AgentInfo>,
    isChristmas: Boolean = false,
    onAgentClick: (AgentInfo) -> Unit,
    onCardClick: (() -> Unit)? = null,
) {
    ConstraintLayout(modifier = Modifier.fillMaxWidth()) {
        val (christmasBg, cardBg, content) = createRefs()

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
                modifier = Modifier.fillMaxWidth().height(242.dp).constrainAs(christmasBg) {},
                painter = painterResource(R.drawable.img_christmas_bg),
                contentScale = ContentScale.Crop,
                contentDescription = "",
            )
        }

        // 内容层
        Column(
            modifier =
                Modifier.fillMaxWidth()
                    .height(ThemedDetailConfig.HorizontalCardListHeight)
                    .padding(ThemedDetailConfig.HorizontalCardListPadding)
                    .constrainAs(content) { centerVerticallyTo(cardBg) }
                    .then(
                        if (onCardClick != null) {
                            Modifier.clickable { onCardClick() }
                        } else {
                            Modifier
                        }
                    ),
            verticalArrangement =
                Arrangement.spacedBy(ThemedDetailConfig.HorizontalCardDescriptionSpacing),
        ) {
            // Title（带模糊阴影效果）和右箭头
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = title,
                    style =
                        TextStyle(
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.White,
                            shadow =
                                Shadow(
                                    color = Color(0xFF8C8992),
                                    offset = Offset(2f, 2f),
                                    blurRadius = 10f,
                                ),
                        ),
                )
                Spacer(Modifier.width(6.dp))
                Image(
                    painter = painterResource(ai.sxwl.android.design.R.drawable.ic_arrow_forward),
                    contentDescription = "",
                )
            }

            // Description（单行）
            Text(
                text = description,
                style = TextStyle(fontSize = 12.sp, lineHeight = 16.sp, color = Color(0xB2FFFFFF)),
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )

            Spacer(Modifier.height(ThemedDetailConfig.HorizontalCardTitleSpacing))

            // 横向滚动的角色卡片列表
            // 注意：LazyRow 中的点击事件会优先处理，不会触发父组件的点击
            LazyRow(
                horizontalArrangement =
                    Arrangement.spacedBy(ThemedDetailConfig.HorizontalCardItemSpacing),
                modifier = Modifier.fillMaxWidth(),
            ) {
                items(agents) { agent ->
                    HorizontalAgentCardItem(agent = agent, onClick = { onAgentClick(agent) })
                }
            }
        }
    }
}

/** 横向角色卡片项 */
@Composable
private fun HorizontalAgentCardItem(agent: AgentInfo, onClick: () -> Unit) {
    Box(
        modifier =
            Modifier.width(ThemedDetailConfig.HorizontalCardItemWidth)
                .height(ThemedDetailConfig.HorizontalCardItemHeight)
                .clip(RoundedCornerShape(ThemedDetailConfig.HorizontalCardItemCornerRadius))
                .clickable { onClick() }
    ) {
        // 角色图片
        AsyncImage(
            model =
                if (isInPreview) ai.sxwl.android.design.R.drawable.img_girl_lite
                else agent.getAlbumImage(),
            contentDescription = agent.name,
            modifier = Modifier.fillMaxSize(),
            contentScale = ContentScale.Crop,
        )

        // 角色名称（叠加在图片底部）
        Box(
            modifier =
                Modifier.fillMaxWidth()
                    .align(Alignment.BottomCenter)
                    .background(
                        brush =
                            Brush.verticalGradient(
                                colors = listOf(Color.Transparent, Color.Black.copy(alpha = 0.6f))
                            )
                    )
                    .padding(horizontal = 8.dp, vertical = 6.dp)
        ) {
            Text(
                text = agent.name,
                fontSize = 12.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color.White,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

@Preview
@Composable
private fun PreviewEventCard() {
    EventCard(
        description =
            "Ready for some holiday magic? Meet our brand-new Christmas-themed AI companion—sparkly, cheerful, and here to light up your winter feed. Come take a look and get into the festive spirit!Ready for some holiday magic? Meet our brand-new Christmas-themed AI companion—sparkly, cheerful, and here to light up your winter feed. Come take a look and get into the festive spirit!",
        isChristmas = true,
    )
}

@Preview(showBackground = true, backgroundColor = 0xFF1C1523)
@Composable
private fun PreviewThemedCard() {
    val previewAgent =
        AgentInfo(
            id = "preview_agent_1",
            name = "Christmas AI Companion",
            intro =
                "A cheerful and sparkly AI companion designed to light up your winter feed. Perfect for festive conversations and holiday magic!",
            avatar = "",
            background = "",
            category = "Holiday",
            gender = "Female",
            tags = listOf("Christmas", "Festive", "Cheerful", "Holiday"),
        )

    Column(
        modifier = Modifier.fillMaxWidth().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        ThemedCharacterCard(agent = previewAgent, onClick = {})
    }
}

@Preview(showBackground = true, backgroundColor = 0xFF1C1523)
@Composable
private fun PreviewHorizontalAgentCardList() {
    val previewAgents =
        listOf(
            AgentInfo(
                id = "preview_agent_1",
                name = "RealPink",
                intro = "A cheerful and sparkly AI companion",
                avatar = "",
                background = "",
                category = "Holiday",
                gender = "Female",
                tags = listOf("Christmas", "Festive"),
            ),
            AgentInfo(
                id = "preview_agent_2",
                name = "RealPink",
                intro = "Anime-style character with magical powers",
                avatar = "",
                background = "",
                category = "Fantasy",
                gender = "Female",
                tags = listOf("Anime", "Magic"),
            ),
            AgentInfo(
                id = "preview_agent_3",
                name = "RealPink",
                intro = "Vintage style character with retro charm",
                avatar = "",
                background = "",
                category = "Vintage",
                gender = "Female",
                tags = listOf("Vintage", "Retro"),
            ),
            AgentInfo(
                id = "preview_agent_4",
                name = "RealPink",
                intro = "Gentle and kind-hearted companion",
                avatar = "",
                background = "",
                category = "Romance",
                gender = "Female",
                tags = listOf("Romance", "Gentle"),
            ),
            AgentInfo(
                id = "preview_agent_5",
                name = "Real",
                intro = "Adventurous explorer ready for new journeys",
                avatar = "",
                background = "",
                category = "Adventure",
                gender = "Female",
                tags = listOf("Adventure", "Explorer"),
            ),
        )

    Column(modifier = Modifier.fillMaxWidth().padding(16.dp)) {
        HorizontalAgentCardList(
            title = "# Merry Christmas",
            description =
                "Ready for some holiday magic? Meet our brand-new Christmas-themed AI companion",
            agents = previewAgents,
            isChristmas = true,
            onAgentClick = {},
        )
    }
}
