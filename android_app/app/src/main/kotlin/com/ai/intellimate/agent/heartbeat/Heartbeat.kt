package com.ai.intellimate.agent.heartbeat

import ai.sxwl.android.common.analytics.PageTrackingHelper
import ai.sxwl.android.common.utils.HeartAppUtils
import ai.sxwl.android.data.character.local.db.FestivalMemory
import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.design.theme.IntelliMateTheme
import ai.sxwl.android.design.theme.loveJournalAccent
import ai.sxwl.android.design.theme.loveJournalBackground
import ai.sxwl.android.design.theme.loveJournalBackgroundGradientEnd
import ai.sxwl.android.design.theme.loveJournalCardBackground
import ai.sxwl.android.design.theme.loveJournalOnBackground
import androidx.compose.foundation.background
import androidx.compose.foundation.Image
import androidx.compose.foundation.clickable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.layout.SubcomposeLayout
import androidx.compose.ui.layout.onGloballyPositioned
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.Constraints
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.res.dimensionResource
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.layout.positionInRoot
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import androidx.navigation.NavGraphBuilder
import androidx.navigation.compose.composable
import androidx.navigation.navOptions
import androidx.navigation.toRoute
import com.ai.intellimate.R
import com.ai.intellimate.agent.heartbeat.viewmodel.HeartbeatViewModel
import kotlin.math.roundToInt
import kotlinx.serialization.Serializable

/** 从聊天/推送打开某条时，高亮卡片外 scrim 的透明度（0=全透明，1=全黑）。 */
private const val HeartbeatScrimAlpha = 0.5f
/** 高亮卡片柔光：spot 阴影透明度。 */
private const val HeartbeatGlowSpotAlpha = 0.45f
/** 高亮卡片柔光：ambient 阴影透明度。 */
private const val HeartbeatGlowAmbientAlpha = 0.25f

/** 高亮卡片浮层信息：相对于 Love Journal 屏根 Box 的偏移与尺寸，用于全屏 scrim 上绘制卡片。 */
private data class HeartbeatOverlayInfo(
    val offsetXDp: Dp,
    val offsetYDp: Dp,
    val widthDp: Dp,
    val heightDp: Dp,
    val memory: FestivalMemory,
)

@Serializable data class Heartbeat(val agentId: String, val memoryId: Long?)

fun NavController.toHeartbeat(agentId: String, memoryId: Long? = null, pageSource: String? = null) {

    PageTrackingHelper.trackPageView(
        "Heartbeat",
        "MainActivity",
        mapOf("agent_id" to agentId, "page_source" to (pageSource ?: "unknown")),
    )

    navigate(
        route = Heartbeat(agentId, memoryId),
        navOptions = navOptions { launchSingleTop = true },
    )
}

fun NavGraphBuilder.heartbeat(onBack: () -> Unit) {
    composable<Heartbeat> {
        val heartbeat = it.toRoute<Heartbeat>()

        Heartbeat(agentId = heartbeat.agentId, memoryId = heartbeat.memoryId, onBack = onBack)
    }
}

@Composable
fun Heartbeat(
    agentId: String,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: HeartbeatViewModel = viewModel(),
    memoryId: Long? = null,
) {
    val memories by viewModel.memories.collectAsState()
    val agentFirstName by viewModel.agentFirstName.collectAsState()

    LaunchedEffect(agentId) { viewModel.setAgentId(agentId) }

    Heartbeat(
        onBack = onBack,
        initialId = memoryId,
        memories = memories,
        agentFirstName = agentFirstName,
        modifier = modifier,
    )
}

/**
 * Love Journal 顶栏标题 + 下划线。使用 SubcomposeLayout 先测量标题宽度，再按该宽度绘制下划线，保证与标题等长。
 * 下划线为横向渐变：左侧为强调色（红橙），向右渐隐至透明；左侧两端带圆角。
 * 空标题时下划线宽度为 0，不会报错。
 *
 * 可配置项：title、titleColor、underlineHeight、underlineSpacing、underlineColor、underlineCornerRadius。
 */
@Composable
private fun HeartbeatTitleWithUnderline(
    title: String,
    titleColor: Color,
    underlineHeight: Dp,
    underlineSpacing: Dp,
    underlineColor: Color,
    underlineCornerRadius: Dp,
) {
    val density = LocalDensity.current
    SubcomposeLayout(modifier = Modifier.fillMaxWidth()) { constraints ->
        // 用宽松约束测标题，得到文字内在宽度，便于 TopAppBar 将整块居中且下划线与标题等长
        val textConstraints =
            Constraints(
                minWidth = 0,
                maxWidth = constraints.maxWidth,
                minHeight = 0,
                maxHeight = Constraints.Infinity,
            )
        val textPlaceable =
            subcompose("title") {
                Text(text = title, color = titleColor)
            }
                .map { it.measure(textConstraints) }
                .single()
        val underlineHeightPx = with(density) { underlineHeight.toPx().roundToInt() }
        val spacingPx = with(density) { underlineSpacing.toPx().roundToInt() }
        val underlineWidthPx = textPlaceable.width.toFloat()
        val leftRoundedShape =
            RoundedCornerShape(
                topStart = underlineCornerRadius,
                topEnd = 0.dp,
                bottomEnd = 0.dp,
                bottomStart = underlineCornerRadius,
            )
        val underlinePlaceable =
            subcompose("underline") {
                Box(
                    modifier =
                        Modifier.fillMaxWidth()
                            .height(underlineHeight)
                            .background(
                                brush =
                                    Brush.linearGradient(
                                        colors = listOf(underlineColor, Color.Transparent),
                                        start = Offset(0f, 0f),
                                        end = Offset(underlineWidthPx, 0f),
                                    ),
                                shape = leftRoundedShape,
                            ),
                )
            }
                .map {
                    it.measure(
                        Constraints(
                            minWidth = textPlaceable.width,
                            maxWidth = textPlaceable.width,
                            minHeight = underlineHeightPx,
                            maxHeight = underlineHeightPx,
                        ),
                    )
                }
                .single()
        val totalHeight = textPlaceable.height + spacingPx + underlinePlaceable.height
        val contentWidth = textPlaceable.width
        layout(contentWidth, totalHeight) {
            textPlaceable.place(0, 0)
            underlinePlaceable.place(0, textPlaceable.height + spacingPx)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun Heartbeat(
    onBack: () -> Unit,
    memories: List<FestivalMemory>,
    modifier: Modifier = Modifier,
    initialId: Long? = null,
    agentFirstName: String? = null,
) {
    val title =
        if (agentFirstName != null) {
            stringResource(R.string.heartbeat_journal_title_with_name, agentFirstName)
        } else {
            stringResource(R.string.heartbeat_journal)
        }
    val cs = MaterialTheme.colorScheme
    val titleUnderlineHeight = dimensionResource(R.dimen.heartbeat_title_underline_height)
    val titleUnderlineSpacing = dimensionResource(R.dimen.heartbeat_title_underline_spacing)
    val titleUnderlineCornerRadius = dimensionResource(R.dimen.heartbeat_title_underline_corner_radius)
    val navIconAreaWidth = dimensionResource(R.dimen.heartbeat_top_bar_nav_icon_area_width)
    var highlightedMemoryId by remember(initialId) { mutableStateOf(initialId) }
    var overlayInfo by remember { mutableStateOf<HeartbeatOverlayInfo?>(null) }
    var screenRootOffset by remember { mutableStateOf(Offset.Zero) }
    val cardElevation = dimensionResource(R.dimen.heartbeat_card_elevation)
    val cardGlowElevation = dimensionResource(R.dimen.heartbeat_card_glow_elevation)
    val cardPaddingH = dimensionResource(R.dimen.heartbeat_card_padding_horizontal)
    val cardPaddingV = dimensionResource(R.dimen.heartbeat_card_padding_vertical)
    val cardInnerSpacing = dimensionResource(R.dimen.heartbeat_card_inner_spacing)

    Box(
        modifier =
            modifier
                .then(Modifier.fillMaxSize())
                .onGloballyPositioned { screenRootOffset = it.positionInRoot() },
    ) {
        Scaffold(
            modifier = Modifier.fillMaxSize(),
            containerColor = Color.Transparent,
            topBar = {
                CenterAlignedTopAppBar(
                    colors =
                        TopAppBarDefaults.topAppBarColors().copy(containerColor = Color.Transparent),
                    title = {
                        HeartbeatTitleWithUnderline(
                            title = title,
                            titleColor = cs.loveJournalOnBackground,
                            underlineHeight = titleUnderlineHeight,
                            underlineSpacing = titleUnderlineSpacing,
                            underlineColor = cs.loveJournalAccent,
                            underlineCornerRadius = titleUnderlineCornerRadius,
                        )
                    },
                    navigationIcon = {
                        Image(
                            modifier =
                                Modifier.padding(horizontal = dimensionResource(R.dimen.padding_medium))
                                    .noRippleClickable(onClick = onBack),
                            painter = painterResource(R.drawable.back),
                            contentDescription = null,
                            colorFilter = ColorFilter.tint(Color.Black),
                        )
                    },
                    actions = {
                        Spacer(modifier = Modifier.width(navIconAreaWidth))
                    },
                )
            },
        ) { contentPadding ->
            Box(modifier = Modifier.fillMaxSize()) {
                Box(
                    modifier =
                        Modifier.fillMaxSize()
                            .background(
                                Brush.linearGradient(
                                    colors = listOf(cs.loveJournalBackground, cs.loveJournalBackgroundGradientEnd),
                                    start = Offset.Zero,
                                    end = Offset(Float.POSITIVE_INFINITY, Float.POSITIVE_INFINITY),
                                ),
                            ),
                )
                Box(
                    modifier =
                        Modifier.padding(contentPadding)
                            .padding(horizontal = dimensionResource(R.dimen.page_padding_horizontal))
                            .fillMaxSize(),
                ) {
                    if (memories.isEmpty()) {
                        HeartbeatEmpty()
                    } else {
                        HeartbeatContent(
                            memories = memories,
                            initialId = initialId,
                            agentFirstName = agentFirstName,
                            highlightedMemoryId = highlightedMemoryId,
                            onClearHighlight = { highlightedMemoryId = null },
                            screenRootOffset = screenRootOffset,
                            onOverlayInfo = { overlayInfo = it },
                        )
                    }
                }
            }
        }

        if (highlightedMemoryId != null) {
            Box(
                modifier =
                    Modifier.fillMaxSize()
                        .background(Color.Black.copy(alpha = HeartbeatScrimAlpha))
                        .clickable { highlightedMemoryId = null },
            )
        }

        overlayInfo?.let { info ->
            Box(
                modifier =
                    Modifier.offset(x = info.offsetXDp, y = info.offsetYDp)
                        .size(info.widthDp, info.heightDp)
                        .clickable { /* 点击卡片不关闭高亮，仅点击 scrim 关闭 */ },
            ) {
                HeartbeatJournalCard(
                    memory = info.memory,
                    modifier = Modifier.fillMaxSize(),
                    cardElevation = cardElevation,
                    glowElevation = cardGlowElevation,
                    cardPaddingH = cardPaddingH,
                    cardPaddingV = cardPaddingV,
                    cardInnerSpacing = cardInnerSpacing,
                )
            }
        }
    }
}

/** 单条 Love Journal 卡片：标题 + 正文，可选柔光效果。用于列表与浮层复用。 */
@Composable
private fun HeartbeatJournalCard(
    memory: FestivalMemory,
    modifier: Modifier = Modifier,
    cardElevation: Dp,
    glowElevation: Dp? = null,
    cardPaddingH: Dp,
    cardPaddingV: Dp,
    cardInnerSpacing: Dp,
) {
    val cs = MaterialTheme.colorScheme
    // 柔光：强调色半透明，spot 稍强、ambient 更淡，与 HeartbeatScrimAlpha 一样避免魔法数
    val glowModifier =
        if (glowElevation != null) {
            Modifier.shadow(
                elevation = glowElevation,
                shape = MaterialTheme.shapes.medium,
                spotColor = cs.loveJournalAccent.copy(alpha = HeartbeatGlowSpotAlpha),
                ambientColor = cs.loveJournalAccent.copy(alpha = HeartbeatGlowAmbientAlpha),
            )
        } else {
            Modifier
        }
    Surface(
        modifier = modifier.then(glowModifier).shadow(
            elevation = cardElevation,
            shape = MaterialTheme.shapes.medium,
        ),
        shape = MaterialTheme.shapes.medium,
        color = cs.loveJournalCardBackground,
    ) {
        Column(
            modifier =
                Modifier.fillMaxWidth()
                    .padding(horizontal = cardPaddingH, vertical = cardPaddingV),
        ) {
            Text(
                text = memory.title,
                style =
                    MaterialTheme.typography.titleMedium.copy(
                        fontWeight = FontWeight.Bold,
                    ),
                color = cs.loveJournalAccent,
            )
            Spacer(Modifier.height(cardInnerSpacing))
            Text(
                text = memory.memory,
                style = MaterialTheme.typography.bodyMedium,
                color = cs.loveJournalOnBackground,
            )
            if (HeartAppUtils.isAppDebugMode()) {
                Spacer(Modifier.height(cardInnerSpacing))
                FestivalMemoryDebugMetadata(memory = memory)
            }
        }
    }
}

/**
 * Love Journal 列表内容：副标题 + 卡片列表。高亮状态由父组件持有；本组件负责在列表内绘制卡片，
 * 并向父组件上报浮层位置（供父组件在全屏 scrim 上绘制高亮卡片）。
 * @param screenRootOffset 屏根 Box 的 positionInRoot，用于将卡片位置换算为屏根坐标系。
 */
@Composable
private fun HeartbeatContent(
    memories: List<FestivalMemory>,
    modifier: Modifier = Modifier,
    initialId: Long? = null,
    agentFirstName: String? = null,
    highlightedMemoryId: Long?,
    onClearHighlight: () -> Unit,
    screenRootOffset: Offset,
    onOverlayInfo: (HeartbeatOverlayInfo?) -> Unit,
) {
    val cs = MaterialTheme.colorScheme
    val density = LocalDensity.current
    val initialIndex =
        remember(initialId, memories) {
            memories.indexOfFirst { it.id == initialId }.takeIf { it >= 0 } ?: 0
        }
    val count = remember(memories) { memories.size }
    val listState = rememberLazyListState(initialIndex)

    // initialId 不在当前列表中时（如已删或未加载到）取消高亮
    LaunchedEffect(initialId, memories, highlightedMemoryId) {
        if (highlightedMemoryId != null && memories.none { it.id == highlightedMemoryId }) {
            onClearHighlight()
        }
    }

    // 高亮卡片滚出可见区域时取消高亮
    LaunchedEffect(listState, highlightedMemoryId) {
        if (highlightedMemoryId == null) return@LaunchedEffect
        snapshotFlow { listState.layoutInfo.visibleItemsInfo }
            .collect { visibleItems ->
                if (visibleItems.none { it.key == highlightedMemoryId }) {
                    onClearHighlight()
                }
            }
    }

    val cardElevation = dimensionResource(R.dimen.heartbeat_card_elevation)
    val cardPaddingH = dimensionResource(R.dimen.heartbeat_card_padding_horizontal)
    val cardPaddingV = dimensionResource(R.dimen.heartbeat_card_padding_vertical)
    val cardInnerSpacing = dimensionResource(R.dimen.heartbeat_card_inner_spacing)
    val listSpacing = dimensionResource(R.dimen.heartbeat_list_spacing)
    val subtitleBottom = dimensionResource(R.dimen.heartbeat_subtitle_bottom)
    val listPaddingBottom = dimensionResource(R.dimen.heartbeat_list_content_padding_bottom)

    val subtitleText =
        if (agentFirstName != null) {
            stringResource(R.string.heartbeat_subtitle_from_agent, count, agentFirstName)
        } else {
            stringResource(R.string.heartbeat_subtitle, count)
        }

    var contentBoxRootOffset by remember { mutableStateOf(Offset.Zero) }
    var lazyColumnRootOffset by remember { mutableStateOf(Offset.Zero) }
    var lazyColumnSizePx by remember { mutableStateOf(IntSize.Zero) }

    val layoutInfo = listState.layoutInfo
    val itemInfo = if (highlightedMemoryId != null) layoutInfo.visibleItemsInfo.find { it.key == highlightedMemoryId } else null
    val highlightedMemory = if (highlightedMemoryId != null) memories.find { it.id == highlightedMemoryId } else null
    val scrollOffset = listState.firstVisibleItemScrollOffset
    val computedOverlayInfo: HeartbeatOverlayInfo? =
        if (itemInfo != null && highlightedMemory != null) {
            val itemH = itemInfo.size
            val itemW = lazyColumnSizePx.width
            if (itemW > 0 && itemH > 0) {
                val itemOffsetY = itemInfo.offset
                val cardX = lazyColumnRootOffset.x - contentBoxRootOffset.x
                val cardY = lazyColumnRootOffset.y - contentBoxRootOffset.y - scrollOffset + itemOffsetY
                val cardRootX = contentBoxRootOffset.x + cardX
                val cardRootY = contentBoxRootOffset.y + cardY
                val offsetX = cardRootX - screenRootOffset.x
                val offsetY = cardRootY - screenRootOffset.y
                HeartbeatOverlayInfo(
                    offsetXDp = with(density) { offsetX.toDp() },
                    offsetYDp = with(density) { offsetY.toDp() },
                    widthDp = with(density) { itemW.toDp() },
                    heightDp = with(density) { itemH.toDp() },
                    memory = highlightedMemory,
                )
            } else null
        } else null

    LaunchedEffect(computedOverlayInfo) { onOverlayInfo(computedOverlayInfo) }

    Box(modifier = modifier.onGloballyPositioned { contentBoxRootOffset = it.positionInRoot() }) {
        Column(modifier = Modifier.fillMaxWidth()) {
            Text(
                text = subtitleText,
                style = MaterialTheme.typography.bodySmall,
                color = cs.loveJournalOnBackground,
                modifier = Modifier.fillMaxWidth(),
                textAlign = TextAlign.Center,
            )

            Spacer(Modifier.height(subtitleBottom))

            LazyColumn(
                state = listState,
                modifier =
                    Modifier.onGloballyPositioned {
                        lazyColumnRootOffset = it.positionInRoot()
                        lazyColumnSizePx = it.size
                    },
                contentPadding = PaddingValues(bottom = listPaddingBottom),
                verticalArrangement = Arrangement.spacedBy(listSpacing),
            ) {
                items(memories, key = { it.id }) { memory ->
                    HeartbeatJournalCard(
                        memory = memory,
                        cardElevation = cardElevation,
                        glowElevation = null,
                        cardPaddingH = cardPaddingH,
                        cardPaddingV = cardPaddingV,
                        cardInnerSpacing = cardInnerSpacing,
                    )
                }
            }
        }
    }
}

@Composable
private fun HeartbeatEmpty(modifier: Modifier = Modifier) {
    Box(contentAlignment = Alignment.Center, modifier = modifier.fillMaxSize()) {
        Text(
            text = stringResource(R.string.heartbeat_empty),
            color = MaterialTheme.colorScheme.loveJournalOnBackground,
        )
    }
}

@Preview(showSystemUi = true, showBackground = true)
@Composable
private fun HeartbeatPreview() {
    IntelliMateTheme {
        Heartbeat(
            onBack = {},
            memories =
                listOf(
                    FestivalMemory(
                        id = 1,
                        agentId = "preview",
                        festivalDate = "2025-02-05",
                        festivalName = "春节",
                        memory = "一起贴春联、吃年夜饭的回忆",
                    ),
                    FestivalMemory(
                        id = 2,
                        agentId = "preview",
                        festivalDate = "2025-01-01",
                        festivalName = "元旦",
                        memory = "新年第一天的问候与祝福",
                    ),
                    FestivalMemory(
                        id = 3,
                        agentId = "preview",
                        festivalDate = "2024-12-25",
                        festivalName = null,
                        memory = "平凡日子里的小确幸",
                    ),
                    FestivalMemory(
                        id = 4,
                        agentId = "preview",
                        festivalDate = "2024-10-01",
                        festivalName = "国庆节",
                        memory = "短",
                    ),
                    FestivalMemory(
                        id = 5,
                        agentId = "preview",
                        festivalDate = "2024-09-15",
                        festivalName = "中秋节阖家团圆",
                        memory = "一起赏月、吃月饼，聊了很久以后想做的事，从工作到旅行到养猫，说到半夜还不困。",
                    ),
                    FestivalMemory(
                        id = 6,
                        agentId = "preview",
                        festivalDate = "2024-08-08",
                        festivalName = null,
                        memory = "那天你说想学游泳，我们就从憋气开始练。虽然呛了几口水，但最后能漂起来的时候特别开心，约好下次再去。",
                    ),
                ),
            agentFirstName = "Stella",
        )
    }
}
