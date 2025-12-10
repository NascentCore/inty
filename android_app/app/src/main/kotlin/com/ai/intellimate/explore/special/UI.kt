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
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.constraintlayout.compose.ConstraintLayout
import coil3.compose.AsyncImage
import com.ai.intellimate.R
import com.ai.intellimate.ui.components.ShimmerPlaceholder
import com.ai.intellimate.ui.components.SmartTagsLayout

/**
 * 主题详情页面配置常量
 * 包含专题详情界面和主题专区界面中使用的各种尺寸和样式配置
 */
internal object ThemedDetailConfig {
    /** EventCard 和图片的圆角半径 */
    val EventCardCornerRadius = 6.dp

    /** EventCard 中事件描述文本的默认最大折叠行数 */
    const val EventDescriptionMaxLines = 4

    // ========== 专题详情界面的角色卡片配置（ThemedCharacterCard） ==========

    /** 专题详情界面角色卡片的高度 */
    val CharacterCardHeight = 142.dp

    /** 专题详情界面角色卡片中图片的宽度 */
    val CharacterImageWidth = 80.dp

    /** 专题详情界面角色卡片中图片和信息之间的间距 */
    val CharacterCardSpacing = 8.dp

    /** 专题详情界面角色卡片内部内容的 padding */
    val CharacterCardPadding = 8.dp

    /** 专题详情界面角色卡片的圆角半径 */
    val CharacterCardCornerRadius = 6.dp

    // ========== 主题专区的横向角色卡片列表配置（HorizontalAgentCardList） ==========

    /** 主题专区横向卡片列表内部内容的 padding */
    val HorizontalCardListPadding = 16.dp

    /** 主题专区横向列表中单个角色卡片项的宽度 */
    val HorizontalCardItemWidth = 80.dp

    /** 主题专区横向列表中单个角色卡片项的高度 */
    val HorizontalCardItemHeight = 142.dp

    /** 主题专区横向列表中角色卡片项之间的间距 */
    val HorizontalCardItemSpacing = 12.dp

    /** 主题专区横向列表中角色卡片项的圆角半径 */
    val HorizontalCardItemCornerRadius = 8.dp

    /** 主题专区横向卡片列表中标题和描述之间的间距 */
    val HorizontalCardTitleSpacing = 8.dp

    /** 主题专区横向卡片列表中描述和角色列表之间的间距 */
    val HorizontalCardDescriptionSpacing = 4.dp
}

/**
 * 专题详情界面的事件描述卡片
 *
 * 用途：显示在专题详情界面（SpecialDetailScreen）顶部，展示该专题的事件描述信息
 * 特点：
 * - 使用 ThemedEventCard 作为容器，支持圣诞主题装饰
 * - 内部使用 ExpandableText 实现文本折叠/展开功能
 * - 默认显示4行，超出部分可展开查看
 *
 * @param description 事件描述文本
 * @param isChristmas 是否为圣诞主题，true 时显示圣诞装饰元素
 * @param modifier 修饰符，可用于设置位置、大小等
 */
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

/**
 * 专题详情界面的角色卡片（横向布局）
 *
 * 用途：显示在专题详情界面（SpecialDetailScreen）的 LazyColumn 列表中，展示单个 AI 角色信息
 * 特点：
 * - 横向布局：左侧为角色图片，右侧为角色信息（名称、简介、标签）
 * - 固定高度，宽度自适应
 * - 支持图片加载状态（占位符、加载失败处理）
 * - 点击可跳转到角色详情
 *
 * @param agent AI 角色信息
 * @param onClick 点击回调，用于跳转到角色详情页面
 */
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
        // 角色图片区域（左侧，固定宽度 80dp）
        Box(
            modifier = Modifier
                .width(ThemedDetailConfig.CharacterImageWidth)
                .fillMaxHeight()
        ) {
            val imageUrl = if (isInPreview) null else agent.getAlbumImage()
            var imageLoaded by remember(agent.id) { mutableStateOf(false) }
            var imageLoadError by remember(agent.id) { mutableStateOf(false) }

            // 图片圆角形状（仅左侧有圆角，与卡片左侧圆角对齐）
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

        // 角色信息区域（右侧，自适应宽度，包含名称、简介、标签）
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

            // 角色简介文本（根据是否有标签决定最大行数：有标签4行，无标签5行）
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

/**
 * 主题专区的横向角色卡片列表容器
 *
 * 用途：显示在主题专区界面（如 ExploreContent），展示某个主题下的多个 AI 角色
 * 特点：
 * - 使用 ThemedEventCard 作为容器，支持圣诞主题装饰
 * - 包含标题、描述和横向滚动的角色卡片列表
 * - 标题和整个卡片区域都支持点击事件
 * - 内部使用 LazyRow 实现横向滚动
 *
 * @param title 列表标题，如 "# Merry Christmas"
 * @param description 列表描述文本
 * @param agents AI 角色列表
 * @param isChristmas 是否为圣诞主题，true 时显示圣诞装饰元素
 * @param onAgentClick 点击单个角色卡片的回调
 * @param onCardClick 点击整个卡片区域的回调（可选）
 * @param onTitleClick 点击标题的回调（可选）
 */
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
    ThemedEventCard(modifier = Modifier.fillMaxWidth(), isChristmas = isChristmas) {
        // 内容层：包含标题、描述和横向滚动的角色卡片列表
        Column(
            modifier =
                Modifier
                    .fillMaxWidth()
                    .padding(ThemedDetailConfig.HorizontalCardListPadding)
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
            // 标题区域（带模糊阴影效果）和右箭头，支持点击跳转
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

            // 描述文本（单行显示，超出部分省略）
            Text(
                text = description,
                style = TextStyle(fontSize = 12.sp, lineHeight = 16.sp, color = Color(0xB2FFFFFF)),
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )

            Spacer(Modifier.height(ThemedDetailConfig.HorizontalCardTitleSpacing))

            // 横向滚动的角色卡片列表（LazyRow）
            // 注意：LazyRow 中的点击事件会优先处理，不会触发父组件的点击事件
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

/**
 * 主题专区横向列表中的单个角色卡片项
 *
 * 用途：作为 HorizontalAgentCardList 中 LazyRow 的单个 item，展示一个 AI 角色
 * 特点：
 * - 固定尺寸的卡片（宽度 80dp，高度 142dp）
 * - 角色图片作为背景，角色名称叠加在底部
 * - 底部有渐变遮罩，确保文字可读性
 * - 点击可跳转到角色详情
 *
 * @param agent AI 角色信息
 * @param onClick 点击回调，用于跳转到角色详情页面
 */
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
        // 角色图片（作为卡片背景，填充整个卡片区域）
        AsyncImage(
            model =
                if (isInPreview) ai.sxwl.android.design.R.drawable.img_girl_lite
                else agent.getAlbumImage(),
            contentDescription = agent.name,
            modifier = Modifier.fillMaxSize(),
            contentScale = ContentScale.Crop,
        )

        // 角色名称（叠加在图片底部，带渐变遮罩确保文字可读性）
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

/**
 * Preview：专题详情界面的事件描述卡片（EventCard）
 */
@Preview
@Composable
private fun PreviewEventCard() {
    EventCard(
        description =
            "Ready for some holiday magic? Meet our brand-new Christmas-themed AI companion—sparkly, cheerful, and here to light up your winter feed. Come take a look and get into the festive spirit!Ready for some holiday magic? Meet our brand-new Christmas-themed AI companion—sparkly, cheerful, and here to light up your winter feed. Come take a look and get into the festive spirit!",
        isChristmas = true,
    )
}

/**
 * Preview：专题详情界面的角色卡片（ThemedCharacterCard）
 */
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

/**
 * Preview：主题专区的横向角色卡片列表（HorizontalAgentCardList）
 * 包含圣诞主题和普通主题两种样式
 */
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

/**
 * 带主题装饰的卡片容器组件
 *
 * 用途：作为 EventCard 和 HorizontalAgentCardList 的容器，提供统一的卡片样式和主题装饰
 * 特点：
 * - 使用 BlurBgCard 作为背景，提供模糊背景效果
 * - 支持圣诞主题装饰（松枝、雪花等装饰元素）
 * - 使用 ConstraintLayout 实现装饰元素的精确定位
 * - 高度自适应内容
 *
 * 使用场景：
 * 1. EventCard - 专题详情界面的事件描述卡片
 * 2. HorizontalAgentCardList - 主题专区的横向角色卡片列表
 *
 * @param modifier 修饰符
 * @param isChristmas 是否为圣诞主题，true 时显示圣诞装饰元素（松枝、雪花）
 * @param contentAlignment 内容对齐方式
 * @param content 卡片内容
 */
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


/**
 * Preview：带主题装饰的卡片容器（ThemedEventCard）
 * 展示圣诞主题和普通主题两种样式
 */
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
            content = {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text("哈哈哈哈🤣", color = Color.White)
                }
            }
        )
    }
}

/**
 * 可折叠文本组件
 *
 * 用途：用于显示长文本，支持折叠/展开功能，节省界面空间
 * 特点：
 * - 默认最多显示指定行数，超出部分显示省略号
 * - 在文本末尾或右下角显示展开/收起按钮
 * - 支持两种按钮位置：文本末尾（TextEnd）和右下角（BottomEnd）
 * - 支持两种动画方式：旋转动画和图标切换
 *
 * 使用场景：
 * 1. EventCard - 专题详情界面的事件描述文本
 * 2. ChatItem - 聊天消息中的长文本（使用 BottomEnd 位置）
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
    iconSize: Dp = 24.dp,
    iconSpacing: Dp = 4.dp,
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
 * 用于 ExpandableText 组件，控制展开/收起按钮的显示位置
 */
enum class ExpandableTextButtonPosition {
    /**
     * 按钮定位在文本最后一行的末尾（紧跟在省略号后）
     * 适用于：EventCard 中的事件描述文本
     */
    TextEnd,

    /**
     * 按钮定位在容器的右下角
     * 适用于：ChatItem 中的聊天消息文本
     */
    BottomEnd,
}

//endregion
