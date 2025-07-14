package com.ai.inty.home

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.grid.rememberLazyGridState
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.nestedscroll.NestedScrollConnection
import androidx.compose.ui.input.nestedscroll.NestedScrollSource
import androidx.compose.ui.input.nestedscroll.nestedScroll
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.Velocity
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.inty.R
import com.ai.inty.base.IntyImage
import com.ai.inty.base.noRippleClickable
import com.ai.inty.beans.AgentInfo
import kotlin.math.roundToInt

/**
 * 推荐的ai伴侣
 */
@Composable
fun RecommendPage(
    modifier: Modifier,
    agents: List<AgentInfo>,
    isLoading: Boolean = false,
    onClickAgent: (AgentInfo) -> Unit,
    onLoadMore: () -> Unit = {},
    onRefresh: () -> Unit = {},
) {
    // 下拉刷新状态
    var pullOffset by remember { mutableStateOf(0f) }
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

            override fun onPostScroll(consumed: Offset, available: Offset, source: NestedScrollSource): Offset {
                // 当向下滚动且已经滚动到顶部时，开始下拉
                return if (available.y > 0 && source == NestedScrollSource.Drag) {
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

        Scaffold(
            modifier = Modifier
                .fillMaxSize()
                .background(Color.Transparent)
                .offset { IntOffset(0, animatedOffset.roundToInt()) },
            containerColor = Color.Transparent
        ) { innerPadding ->

            Column {
                Spacer(Modifier.height(innerPadding.calculateTopPadding() + 28.dp))

                Row(
                    modifier = Modifier.padding(24.dp, 0.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    IntyImage(
                        model = R.drawable.popular1
                    )
                    Spacer(Modifier.width(7.dp))
                    IntyImage(
                        model = R.drawable.popular
                    )
                }

                Spacer(Modifier.height(30.dp))

                val gridState = rememberLazyGridState()

                // 检测是否在顶部
                remember {
                    derivedStateOf {
                        gridState.firstVisibleItemIndex == 0 && gridState.firstVisibleItemScrollOffset == 0
                    }
                }

                // 检测是否滚动到底部
                val reachedBottom = remember {
                    derivedStateOf {
                        val lastVisibleItem = gridState.layoutInfo.visibleItemsInfo.lastOrNull()
                        lastVisibleItem?.index != null && lastVisibleItem.index >= agents.size - 3
                    }
                }

                // 触发加载更多
                LaunchedEffect(reachedBottom.value) {
                    if (reachedBottom.value && agents.isNotEmpty() && !isLoading) {
                        onLoadMore()
                    }
                }

                LazyVerticalGrid(
                    state = gridState,
                    modifier = Modifier.padding(bottom = innerPadding.calculateBottomPadding() + 80.dp, start = 16.dp, end = 16.dp),
                    columns = GridCells.Fixed(2),
                    horizontalArrangement = Arrangement.spacedBy(13.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp),
                ) {
                    items(agents) { agent ->
                        RecommendPageItem(
                            modifier = Modifier
                                .size(165.dp, 220.dp)
                                .noRippleClickable {
                                    onClickAgent(agent)
                                },
                            agentInfo = agent
                        )
                    }

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
}

@Composable
fun RecommendPageItem(
    modifier: Modifier,
    agentInfo: AgentInfo
) {
    Box(
        modifier = modifier.size(165.dp, 220.dp)
    ) {
        IntyImage(
            modifier = Modifier.fillMaxSize(),
            model = agentInfo.avatar,
            placeholder = painterResource(R.drawable.app_icon),
            error = painterResource(R.drawable.app_icon),
        )
        Text(
            modifier = Modifier
                .align(Alignment.BottomStart)
                .padding(12.dp),
            text = agentInfo.name,
            fontSize = 14.sp,
            fontWeight = FontWeight.SemiBold,
            color = Color.White,
        )
    }
}
