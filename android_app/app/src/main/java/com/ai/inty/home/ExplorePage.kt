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
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.Velocity
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.inty.R
import com.ai.inty.base.IntyCircleImage
import com.ai.inty.base.IntyImage
import com.ai.inty.base.noRippleClickable
import com.ai.inty.beans.AgentInfo
import com.ai.inty.ui.components.SmartTagsLayout
import kotlinx.coroutines.delay
import kotlin.math.roundToInt

// 预加载下一页的缓冲区数量
// 当前已经加载但是还未被显示的角色数量
const val COLUMN_COUNT = 2
val TitleHeight = 40.dp // 标题栏高度，文字居中显示，未预留与标题下方内容间距。
val TitleLeftPadding = 24.dp // 标题栏内显示内容距离左侧边缘间距，用于与标题下方内容垂直对齐。


@SuppressLint("ConfigurationScreenWidthHeight")
@Composable
fun ExplorePage(
    modifier: Modifier,
    innerPadding: PaddingValues,
    agents: List<AgentInfo>,
    isLoading: Boolean = false,
    onClickAgent: (AgentInfo) -> Unit,
    onLoadMore: () -> Unit = {},
    onRefresh: () -> Unit = {},
) {
    // 对 agents 进行去重处理，确保没有重复的数据
    val deduplicatedAgents = remember(agents) {
        agents.distinctBy { agent ->
            // 使用多个字段组合作为唯一标识，确保去重的准确性
            "${agent.id}_${agent.name}_${agent.avatar}"
        }
    }
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

            // 检测是否滚动到底部 - 使用更稳定的计算方式
            val reachedBottom by remember {
                derivedStateOf {
                    val layoutInfo = gridState.layoutInfo
                    val totalItemsCount = layoutInfo.totalItemsCount
                    val lastVisibleItemIndex = layoutInfo.visibleItemsInfo.lastOrNull()?.index ?: -1

                    // 当最后一个可见项接近列表末尾时触发加载更多
                    totalItemsCount > 0 && lastVisibleItemIndex >= totalItemsCount - 3
                }
            }

            // 触发加载更多，添加防抖机制
            LaunchedEffect(reachedBottom, deduplicatedAgents.size) {
                if (reachedBottom && deduplicatedAgents.isNotEmpty() && !isLoading) {
                    // 添加延迟，避免快速滚动时重复触发
                    delay(200)
                    onLoadMore()
                }
            }

            LazyVerticalStaggeredGrid(
                columns = StaggeredGridCells.Fixed(COLUMN_COUNT),
                modifier = Modifier,
                state = gridState,
                contentPadding = PaddingValues(16.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                verticalItemSpacing = 8.dp,
            ) {
                runCatching {
                    if (deduplicatedAgents.isNotEmpty()) {
                        // 使用组合 key 策略，确保唯一性同时保持 LazyList 复用机制
                        // 当 agent.id 重复时，使用 index 作为后备方案
                        itemsIndexed(
                            items = deduplicatedAgents,
                            key = { index, agent ->
                                // 优先使用 agent.id，如果为空则使用 index
                                agent.id.ifEmpty { "agent_$index" }
                            }
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
                if (isLoading && deduplicatedAgents.isNotEmpty()) {
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
    // 缓存渐变画笔，避免每次重组时重新创建
    val gradientBrush = remember {
        Brush.verticalGradient(
            colors = listOf(
                Color.Transparent,
                Color.Black.copy(.3f),
                Color.Black.copy(.5f),
                Color.Black.copy(.7f),
                Color.Black.copy(.9f),
                Color.Black,
                Color.Black,
                Color.Black,
            )
        )
    }

    // 缓存过滤后的标签，避免每次重组时重新计算
    val filteredTags = remember(agentInfo.tags) {
        agentInfo.tags?.filterNotNull() ?: emptyList()
    }

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
                .background(brush = gradientBrush)
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
            if (filteredTags.isNotEmpty()) {
                SmartTagsLayout(tags = filteredTags, isCardTag = true)
            }
        }
    }
}
