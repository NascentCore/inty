package com.ai.intellimate.explore.special

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.design.isInPreview
import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.design.ui.BlurBgCard
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
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.AnnotatedString
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
    val EventCardCornerRadius = 6.dp
    const val EventDescriptionMaxLines = 4

    // 边框渐变宽度
    val CharacterCardHeight = 142.dp
    val CharacterImageWidth = 80.dp
    val CharacterCardSpacing = 8.dp
    val CharacterCardPadding = 8.dp
    val CharacterCardCornerRadius = 6.dp

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
internal fun EventCard(
    description: String,
    isChristmas: Boolean = false,
    modifier: Modifier = Modifier,
) {
    ThemedEventCard(modifier = modifier.fillMaxWidth(), isChristmas) {
        ExpandableText(
            text = description,
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 24.dp, vertical = 40.dp),
            collapsedMaxLines = ThemedDetailConfig.EventDescriptionMaxLines,
            textStyle = TextStyle(
                fontSize = 12.sp,
                lineHeight = 16.sp,
                color = Color(0xB2FFFFFF),
                letterSpacing = 0.1.sp,
            ),
            buttonPosition = ExpandableTextButtonPosition.TextEnd,
            iconSize = 24.dp,
            iconSpacing = 4.dp,
            iconTint = Color.White,
            useRotationAnimation = true,
        )
    }
}

/** 主题角色卡片组件（横向布局） */
@Composable
internal fun ThemedCharacterCard(agent: AgentInfo, onClick: () -> Unit) {
    Row(
        modifier =
            Modifier
                .fillMaxWidth()
                .height(ThemedDetailConfig.CharacterCardHeight)
                .padding(horizontal = 16.dp)
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
        Box(
            modifier = Modifier
                .width(ThemedDetailConfig.CharacterImageWidth)
                .fillMaxHeight()
        ) {
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
                    modifier = Modifier
                        .fillMaxSize()
                        .clip(imageShape),
                    contentScale = ContentScale.Crop,
                )
            } else {
                // 显示加载占位符
                if (!imageLoaded && !imageLoadError) {
                    ShimmerPlaceholder(
                        modifier = Modifier
                            .fillMaxSize()
                            .clip(imageShape),
                        cornerRadius = ThemedDetailConfig.EventCardCornerRadius,
                    )
                }

                // 如果加载失败，显示默认图片
                if (imageLoadError) {
                    AsyncImage(
                        model = ai.sxwl.android.design.R.drawable.img_girl_lite,
                        contentDescription = agent.name,
                        modifier = Modifier
                            .fillMaxSize()
                            .clip(imageShape),
                        contentScale = ContentScale.Crop,
                    )
                }

                // 加载实际图片
                AsyncImage(
                    model = imageUrl,
                    contentDescription = agent.name,
                    modifier = Modifier
                        .fillMaxSize()
                        .clip(imageShape),
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
                Modifier
                    .fillMaxHeight()
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
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f),
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
    onTitleClick: (() -> Unit)? = null,
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
                    Modifier
                        .fillMaxSize()
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
                    Modifier
                        .matchParentSize()
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
            modifier = Modifier
                .fillMaxWidth()
                .height(ThemedDetailConfig.HorizontalCardListHeight)
                .constrainAs(christmasBg) {
                    visibility = if (isChristmas) Visibility.Visible else Visibility.Invisible
                },
            painter = painterResource(R.drawable.img_christmas_bg),
            contentScale = ContentScale.Crop,
            contentDescription = "",
        )


        // 内容层
        Column(
            modifier =
                Modifier
                    .fillMaxWidth()
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
                modifier = Modifier
                    .fillMaxWidth()
                    .then(
                        if (onTitleClick != null) {
                            Modifier.clickable { onTitleClick() }
                        } else {
                            Modifier
                        }
                    ),
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
            Modifier
                .width(ThemedDetailConfig.HorizontalCardItemWidth)
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
                Modifier
                    .fillMaxWidth()
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
        modifier = Modifier.fillMaxWidth(),
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

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp)
    ) {
        HorizontalAgentCardList(
            title = "# Merry Christmas",
            description =
                "Ready for some holiday magic? Meet our brand-new Christmas-themed AI companion",
            agents = previewAgents,
            isChristmas = true,
            onAgentClick = {},
            onTitleClick = null,
        )

        HorizontalAgentCardList(
            title = "# Merry Christmas",
            description =
                "Ready for some holiday magic? Meet our brand-new Christmas-themed AI companion",
            agents = previewAgents,
            isChristmas = false,
            onAgentClick = {},
            onTitleClick = null,
        )
    }
}


//region 使用BlurBgCard

@Composable
fun ThemedEventCard(
    modifier: Modifier = Modifier,
    isChristmas: Boolean = false,
    contentAlignment: Alignment = Alignment.Center,
    content: @Composable () -> Unit
) {
    ConstraintLayout(modifier.padding(top = 16.dp)) {
        val (leftPine, rightPine, leftSnow, rightSnow, blurBg) = createRefs()

        BlurBgCard(
            modifier = Modifier
                .fillMaxWidth()
                .constrainAs(blurBg) {
                    top.linkTo(parent.top)
                    bottom.linkTo(parent.bottom)
                },
            contentAlignment,
            content = { content() }
        )

        if (isChristmas) {
            Image(
                painter = painterResource(R.drawable.img_pine_left),
                contentDescription = null,
                modifier = Modifier.constrainAs(leftPine) {
                    start.linkTo(blurBg.start)
                    top.linkTo(blurBg.top)
                })

            Image(
                painter = painterResource(R.drawable.img_snow_left),
                contentDescription = null,
                modifier = Modifier.constrainAs(leftSnow) {
                    start.linkTo(leftPine.start)
                    top.linkTo(leftPine.top, (-16).dp)
                })
            Image(
                painter = painterResource(R.drawable.img_pine_right),
                contentDescription = null,
                modifier = Modifier.constrainAs(rightPine) {
                    end.linkTo(blurBg.end)
                    top.linkTo(blurBg.top)
                })
            Image(
                painter = painterResource(R.drawable.img_snow_right),
                contentDescription = null,
                modifier = Modifier.constrainAs(rightSnow) {
                    end.linkTo(rightPine.end)
                    top.linkTo(rightPine.top, (-16).dp)
                })
        }

    }

}


@Preview
@Composable
private fun PreviewThemedEventCard() {
    Column {
        ThemedEventCard(
            modifier = Modifier.fillMaxWidth(),
            isChristmas = true,
            content = {
                ExpandableText(
                    text = "Ready for some holiday magic? Meet our brand-new Christmas-themed AI companion—sparkly, cheerful, and here to light up your winter feed. Come take a look and get into the festive spirit!Ready for some holiday magic? Meet our brand-new Christmas-themed AI companion—sparkly, cheerful, and here to light up your winter feed. Come take a look and get into the festive spirit!",
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 24.dp, vertical = 40.dp),
                    textStyle = TextStyle(color = Color.White)
                )
            }
        )
        ThemedEventCard(
            modifier = Modifier
                .fillMaxWidth()
                .height(170.dp),
            content = { Text("哈哈哈哈🤣", color = Color.White) }
        )
    }
}

/**
 * 可折叠文本组件
 * 默认最多显示指定行数，超出部分显示省略号，并在文本末尾显示展开/收起按钮
 *
 * @param text 文本内容（String 或 AnnotatedString）
 * @param modifier 修饰符
 * @param collapsedMaxLines 折叠状态下最大显示行数，默认4行
 * @param textStyle 文本样式
 * @param buttonPosition 按钮位置，默认为文本末尾（TextEnd），可选右下角（BottomEnd）
 * @param iconSize 图标大小，默认24.dp
 * @param iconSpacing 图标与文本的间距，默认4.dp
 * @param iconTint 图标颜色，默认白色
 * @param useRotationAnimation 是否使用旋转动画，默认true（使用KeyboardArrowDown图标旋转），false则使用不同的上下箭头图标
 */
@Composable
private fun ExpandableText(
    text: String,
    modifier: Modifier = Modifier,
    collapsedMaxLines: Int = 4,
    textStyle: TextStyle = TextStyle.Default,
    buttonPosition: ExpandableTextButtonPosition = ExpandableTextButtonPosition.TextEnd,
    iconSize: androidx.compose.ui.unit.Dp = 24.dp,
    iconSpacing: androidx.compose.ui.unit.Dp = 4.dp,
    iconTint: Color = Color.White,
    useRotationAnimation: Boolean = true,
) {
    ExpandableText(
        text = AnnotatedString(text),
        modifier = modifier,
        collapsedMaxLines = collapsedMaxLines,
        textStyle = textStyle,
        buttonPosition = buttonPosition,
        iconSize = iconSize,
        iconSpacing = iconSpacing,
        iconTint = iconTint,
        useRotationAnimation = useRotationAnimation,
    )
}

@Composable
private fun ExpandableText(
    text: AnnotatedString,
    modifier: Modifier = Modifier,
    collapsedMaxLines: Int = 4,
    textStyle: TextStyle = TextStyle.Default,
    buttonPosition: ExpandableTextButtonPosition = ExpandableTextButtonPosition.TextEnd,
    iconSize: androidx.compose.ui.unit.Dp = 24.dp,
    iconSpacing: androidx.compose.ui.unit.Dp = 4.dp,
    iconTint: Color = Color.White,
    useRotationAnimation: Boolean = true,
) {
    var isExpanded by remember { mutableStateOf(false) }
    var hasTextOverflow by remember { mutableStateOf(false) }
    var textLayoutResult by remember { mutableStateOf<TextLayoutResult?>(null) }
    var textPaddingEnd by remember { mutableIntStateOf(0) }
    val density = LocalDensity.current
    val rotationAngle by animateFloatAsState(
        targetValue = if (isExpanded) 180f else 0f,
        animationSpec = tween(durationMillis = 300),
        label = "arrowRotation",
    )

    Box(modifier = modifier.fillMaxWidth()) {
        Text(
            text = text,
            style = textStyle,
            maxLines = if (isExpanded) Int.MAX_VALUE else collapsedMaxLines,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier
                .fillMaxWidth()
                .padding(end = textPaddingEnd.dp),
            onTextLayout = { layoutResult ->
                textLayoutResult = layoutResult
                if (!isExpanded) {
                    val hasVisualOverflow = layoutResult.hasVisualOverflow
                    val lineCount = layoutResult.lineCount
                    hasTextOverflow =
                        hasVisualOverflow || lineCount > collapsedMaxLines
                    textPaddingEnd =
                        if (hasTextOverflow && buttonPosition == ExpandableTextButtonPosition.TextEnd) {
                            (iconSize + iconSpacing).value.toInt()
                        } else {
                            0
                        }
                } else {
                    textPaddingEnd = 0
                }
            },
        )

        if (hasTextOverflow && textLayoutResult != null) {
            when (buttonPosition) {
                ExpandableTextButtonPosition.TextEnd -> {
                    val layout = textLayoutResult!!
                    val lastLineIndex = layout.lineCount - 1
                    val lastLineBaseline = layout.getLineBaseline(lastLineIndex)
                    val lastLineEnd = layout.getLineEnd(lastLineIndex)
                    val lastLineEndX =
                        layout.getHorizontalPosition(lastLineEnd, usePrimaryDirection = true)

                    val iconOffsetX = with(density) {
                        lastLineEndX.toDp() + iconSpacing
                    }
                    val iconOffsetY = with(density) {
                        (lastLineBaseline - iconSize.toPx() / 2).toDp()
                    }

                    if (useRotationAnimation) {
                        Icon(
                            imageVector = Icons.Default.KeyboardArrowDown,
                            contentDescription = null,
                            modifier = Modifier
                                .size(iconSize)
                                .offset(x = iconOffsetX, y = iconOffsetY)
                                .rotate(rotationAngle)
                                .noRippleClickable { isExpanded = !isExpanded },
                            tint = iconTint,
                        )
                    } else {
                        Icon(
                            painter = painterResource(
                                if (isExpanded) R.drawable.ic_arrow_up else R.drawable.ic_arrow_down
                            ),
                            contentDescription = null,
                            modifier = Modifier
                                .size(iconSize)
                                .offset(x = iconOffsetX, y = iconOffsetY)
                                .noRippleClickable { isExpanded = !isExpanded },
                            tint = iconTint,
                        )
                    }
                }

                ExpandableTextButtonPosition.BottomEnd -> {
                    if (useRotationAnimation) {
                        Icon(
                            imageVector = Icons.Default.KeyboardArrowDown,
                            contentDescription = null,
                            modifier = Modifier
                                .size(iconSize)
                                .align(Alignment.BottomEnd)
                                .rotate(rotationAngle)
                                .noRippleClickable { isExpanded = !isExpanded },
                            tint = iconTint,
                        )
                    } else {
                        Icon(
                            painter = painterResource(
                                if (isExpanded) R.drawable.ic_arrow_up else R.drawable.ic_arrow_down
                            ),
                            contentDescription = null,
                            modifier = Modifier
                                .size(iconSize)
                                .align(Alignment.BottomEnd)
                                .noRippleClickable { isExpanded = !isExpanded },
                            tint = iconTint,
                        )
                    }
                }
            }
        }
    }
}

/**
 * 展开按钮位置枚举
 */
enum class ExpandableTextButtonPosition {
    /** 按钮定位在文本最后一行的末尾（紧跟在省略号后） */
    TextEnd,

    /** 按钮定位在容器的右下角 */
    BottomEnd,
}

//endregion
