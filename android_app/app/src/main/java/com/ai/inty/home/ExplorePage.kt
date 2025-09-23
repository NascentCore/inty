package com.ai.inty.home

import android.annotation.SuppressLint
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.staggeredgrid.LazyVerticalStaggeredGrid
import androidx.compose.foundation.lazy.staggeredgrid.StaggeredGridCells
import androidx.compose.foundation.lazy.staggeredgrid.itemsIndexed
import androidx.compose.foundation.lazy.staggeredgrid.rememberLazyStaggeredGridState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.nestedscroll.NestedScrollConnection
import androidx.compose.ui.input.nestedscroll.NestedScrollSource
import androidx.compose.ui.input.nestedscroll.nestedScroll
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.Velocity
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.unit.times
import com.ai.inty.R
import com.ai.inty.base.IntyCircleImage
import com.ai.inty.base.IntyImage
import com.ai.inty.base.noRippleClickable
import com.ai.inty.beans.AgentInfo
import com.ai.inty.ui.components.SmartTagsLayout
import com.ai.inty.utils.AspectRatio
import com.ai.inty.utils.CHARACTER_CARD_ASPECT_RATIO
import com.ai.inty.utils.getHeightByWidth
import kotlinx.coroutines.delay
import kotlin.math.roundToInt

// 一个父容器内多个分布式子容器之间及与父容器边缘的间距相对父容器的比例
// 水平方向的padding，包括左侧和右侧，子容器上下左右之间的间距
const val SPACER_PERCENTAGE = 0.012f
const val HORIZONTAL_PADDING_MULTIPLIER = 1.8

// 预加载下一页的缓冲区数量
// 当前已经加载但是还未被显示的角色数量
const val COLUMN_COUNT = 2
val TitleHeight = 40.dp // 标题栏高度，文字居中显示，未预留与标题下方内容间距。
val TitleLeftPadding = 24.dp // 标题栏内显示内容距离左侧边缘间距，用于与标题下方内容垂直对齐。


private fun calculateSpacerWidth(containerWidth: Int): Int {
    val spacerPercentage = SPACER_PERCENTAGE
    return (containerWidth * spacerPercentage).toInt()
}

private fun getCharacterCardSize(containerWidth: Int): AspectRatio {
    // Portrait aspect ratio
    val portraitAspectRatio = CHARACTER_CARD_ASPECT_RATIO
    val spacerPercentage = 0.03f
    val spacerWidth = (containerWidth * spacerPercentage).toInt()
    val columnCount = 2
    val subContainerWidth = (containerWidth - (columnCount + 1) * spacerWidth) / columnCount
    val subContainerHeight = getHeightByWidth(subContainerWidth, portraitAspectRatio)
    return AspectRatio(subContainerWidth, subContainerHeight)
}

@SuppressLint("ConfigurationScreenWidthHeight")
@Composable
fun RecommendPage(
    modifier: Modifier,
    innerPadding: PaddingValues,
    agents: List<AgentInfo>,
    isLoading: Boolean = false,
    onClickAgent: (AgentInfo) -> Unit,
    onLoadMore: () -> Unit = {},
    onRefresh: () -> Unit = {},
) {
    // 下拉刷新状态
    var pullOffset by remember { mutableFloatStateOf(0f) }
    var isRefreshing by remember { mutableStateOf(false) }
    val pullThreshold = 120f // 触发刷新的阈值

    // 动画化偏移
    val animatedOffset by animateFloatAsState(
        targetValue = if (isRefreshing) 80f else pullOffset,
        animationSpec = tween(if (isRefreshing) 300 else 0),
        label = "pullOffset"
    )

    // 监听加载状态变化，刷新完成时重置状态
    LaunchedEffect(isLoading) {
        if (!isLoading && isRefreshing) {
            isRefreshing = false
            pullOffset = 0f
        }
    }

    // NestedScroll连接，处理下拉刷新
    val nestedScrollConnection = remember {
        object : NestedScrollConnection {
            override fun onPreScroll(available: Offset, source: NestedScrollSource): Offset {
                // 当向上滚动且有下拉偏移时，先消费下拉偏移
                return if (available.y < 0 && pullOffset > 0) {
                    val consumed = -pullOffset.coerceAtMost(-available.y)
                    pullOffset += consumed
                    Offset(0f, consumed)
                } else {
                    Offset.Zero
                }
            }

            override fun onPostScroll(
                consumed: Offset,
                available: Offset,
                source: NestedScrollSource
            ): Offset {
                // 当向下滚动且已经滚动到顶部时，开始下拉
                return if (available.y > 0 && source == NestedScrollSource.UserInput) {
                    pullOffset = (pullOffset + available.y).coerceAtMost(pullThreshold * 1.5f)
                    Offset(0f, available.y)
                } else {
                    Offset.Zero
                }
            }

            override suspend fun onPreFling(available: Velocity): Velocity {
                // 处理下拉刷新触发
                return if (pullOffset >= pullThreshold && !isLoading) {
                    isRefreshing = true
                    onRefresh()
                    available
                } else {
                    if (pullOffset > 0) {
                        pullOffset = 0f
                    }
                    Velocity.Zero
                }
            }
        }
    }

    Box(
        modifier = modifier.nestedScroll(nestedScrollConnection)
    ) {
        IntyImage(
            modifier = Modifier.align(Alignment.TopEnd),
            model = R.drawable.notify_header_bg
        )
        // 下拉刷新指示器
        if (animatedOffset > 0) {
            Box(
                modifier = Modifier
                    .align(Alignment.TopCenter)
                    .offset { IntOffset(0, (animatedOffset - 30f).roundToInt()) }
                    .padding(top = 60.dp),
                contentAlignment = Alignment.Center
            ) {
                CircularProgressIndicator(
                    modifier = Modifier.size(24.dp),
                    color = Color.White.copy(0.8f),
                    strokeWidth = 2.dp
                )
            }
        }

        Column(
            modifier = Modifier
                .fillMaxSize()
                .background(Color.Transparent)
                .offset { IntOffset(0, animatedOffset.roundToInt()) }
                // 允许留出顶部系统工具栏如日期/时间/信号强度等。
                .padding(top = innerPadding.calculateTopPadding())
        ) {
            Row(
                modifier = Modifier
                    .height(TitleHeight)
                    .padding(start = TitleLeftPadding),
                verticalAlignment = Alignment.CenterVertically
            ) {
                IntyImage(model = R.drawable.popular1)
                Spacer(Modifier.width(7.dp))
                IntyImage(model = R.drawable.popular)
            }

            val gridState = rememberLazyStaggeredGridState()

            // 检测是否在顶部
            val isAtTop by remember {
                derivedStateOf {
                    gridState.firstVisibleItemIndex == 0 && gridState.firstVisibleItemScrollOffset == 0
                }
            }

            // 检测是否滚动到底部
            val reachedBottom by remember {
                derivedStateOf {
                    val lastVisibleItem = gridState.layoutInfo.visibleItemsInfo.lastOrNull()
                    lastVisibleItem?.index != null && lastVisibleItem.index >= agents.size - 3
                }
            }

            // 触发加载更多，添加防抖机制
            LaunchedEffect(reachedBottom) {
                if (reachedBottom && agents.isNotEmpty() && !isLoading) {
                    // 添加延迟，避免快速滚动时重复触发
                    delay(100)
                    onLoadMore()
                }
            }

            // Calculate dynamic spacing based on container width
            val containerWidth = LocalConfiguration.current.screenWidthDp
            val characterCardSize = getCharacterCardSize(containerWidth)
            // 用于角色卡上下左右的间距
            val spacerWidth = calculateSpacerWidth(containerWidth)

            LazyVerticalStaggeredGrid(
                columns = StaggeredGridCells.Fixed(COLUMN_COUNT),
                modifier = Modifier.padding(
                    bottom = BottomNavigationBarHeight,
                    // Left padding
                    start = HORIZONTAL_PADDING_MULTIPLIER * spacerWidth.dp,
                    // Right padding
                    end = HORIZONTAL_PADDING_MULTIPLIER * spacerWidth.dp,
                ),
                state = gridState,
                horizontalArrangement = Arrangement.spacedBy(spacerWidth.dp),
                verticalItemSpacing = spacerWidth.dp,
            ) {
                runCatching {
                    if (agents.isNotEmpty()) {
                        itemsIndexed(
                            items = agents,
                            key = { index, agent -> "${agent.id}_$index" }
                        ) { _, agent ->

                            CharacterCard(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clip(RoundedCornerShape(8.dp))
                                    .noRippleClickable {
                                        onClickAgent(agent)
                                    },
                                agentInfo = agent,
                            )
                        }
                    }
                }.onFailure { it.printStackTrace() }

                // 加载更多指示器
                if (isLoading && agents.isNotEmpty()) {
                    item {
                        Box(
                            modifier = Modifier
                                .size(165.dp, 60.dp)
                                .padding(16.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(24.dp),
                                color = Color.White.copy(0.7f)
                            )
                        }
                    }
                }

                item {
                    Spacer(Modifier.height(16.dp))
                }
            }
        }
    }
}

@Composable
fun CharacterCard(
    modifier: Modifier = Modifier,
    agentInfo: AgentInfo,
) {

    Box(modifier = modifier) {
        IntyImage(
            modifier = Modifier.fillMaxWidth(),
            model = agentInfo.background,
            placeholder = painterResource(R.drawable.app_icon),
            error = painterResource(R.drawable.app_icon),
            contentScale = ContentScale.FillWidth,
        )
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .background(
                    brush = Brush.verticalGradient(
                        colors = listOf(
                            Color.Transparent,
                            Color.Black.copy(.7f),
                            Color.Black,
                        )
                    )
                )
                .padding(start = 8.dp, end = 8.dp, top = 15.dp, bottom = 8.dp)
                .align(Alignment.BottomCenter),
            verticalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                IntyCircleImage(
                    modifier = Modifier.size(18.dp),
                    url = agentInfo.avatar,
                    placeholderResID = R.drawable.app_icon
                )
                Spacer(Modifier.width(4.dp))
                Text(
                    modifier = Modifier,
                    text = agentInfo.name,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color.White,
                )
            }
            Text(
                modifier = Modifier,
                text = agentInfo.intro,
                fontSize = 12.sp,
                lineHeight = 12.sp,
                color = Color.White.copy(.7f),
                maxLines = 3,
                overflow = TextOverflow.Ellipsis
            )
            agentInfo.tags?.filterNotNull()?.let { tags ->
                SmartTagsLayout(tags = tags, isCardTag = true)
            }

        }

    }
}
