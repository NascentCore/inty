package com.ai.intellimate.explore

import ai.sxwl.android.data.api.model.AgentInfo
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.GridItemSpan
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.rememberLazyGridState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.paging.LoadState
import androidx.paging.PagingData
import androidx.paging.compose.collectAsLazyPagingItems
import androidx.paging.compose.itemKey
import com.ai.intellimate.R
import com.ai.intellimate.ui.components.EmptyDataState
import com.ai.intellimate.ui.components.NetworkErrorState
import com.ai.intellimate.ui.components.ShimmerPlaceholder
import com.ai.intellimate.utils.GuestLoginLimiter
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow

/** Explore页面的主要内容组件 */
@Composable
fun ExploreContent(
    modifier: Modifier = Modifier,
    agentsFlow: Flow<PagingData<AgentInfo>>?,
    innerPadding: PaddingValues,
    onClickAgent: (AgentInfo) -> Unit,
    isRefreshing: Boolean = false,
    onRetry: (() -> Unit)? = null,
) {
    val lazyPagingItems = agentsFlow?.collectAsLazyPagingItems()
    val vm: ExploreViewModel = viewModel()
    val context = LocalContext.current

    val gridState =
        rememberLazyGridState(
            initialFirstVisibleItemIndex = vm.savedFirstVisibleIndex.collectAsState().value,
            initialFirstVisibleItemScrollOffset = vm.savedFirstVisibleOffset.collectAsState().value,
        )

    // 检测用户是否主动滚动到底部触发加载更多
    var showLoadMoreLoading by remember { mutableStateOf(false) }
    var lastScrollTime by remember { mutableLongStateOf(0L) }
    var hasUserScrolled by remember { mutableStateOf(false) } // 标记用户是否主动滚动过

    // 检测底部Spacer是否可见（Spacer总是最后一个item，索引为 totalItemsCount - 1）
    val isSpacerVisible by remember {
        derivedStateOf {
            val layoutInfo = gridState.layoutInfo
            val totalItemsCount = layoutInfo.totalItemsCount
            if (totalItemsCount == 0) return@derivedStateOf false

            // Spacer是最后一个item，检查最后一个item的索引是否可见
            val spacerIndex = totalItemsCount - 1
            layoutInfo.visibleItemsInfo.any { it.index == spacerIndex }
        }
    }

    // 检测是否到达第一页末尾（最后一个可见的agent item索引 >= 19，即第20个item）
    val isAtPageEnd by remember {
        derivedStateOf {
            val layoutInfo = gridState.layoutInfo
            // 找到最后一个可见的agent item（排除加载状态指示器和Spacer）
            val agentItems =
                layoutInfo.visibleItemsInfo.filter { itemInfo ->
                    // 计算agent items的数量：totalItemsCount - 2（加载状态 + Spacer）
                    val agentItemCount = lazyPagingItems?.itemCount ?: 0
                    itemInfo.index < agentItemCount
                }
            val lastVisibleAgentIndex = agentItems.lastOrNull()?.index ?: -1
            lastVisibleAgentIndex >= 19 // 第20个agent item，索引为19
        }
    }

    // 检测滚动方向：记录上一次的第一可见item索引
    var lastFirstVisibleIndex by remember { mutableIntStateOf(-1) }
    var isScrollingDown by remember { mutableStateOf(false) } // 是否向下滚动（期待加载更多）

    // 监听滚动状态，检测滚动方向和保存位置
    LaunchedEffect(gridState.isScrollInProgress, gridState.firstVisibleItemIndex) {
        if (gridState.isScrollInProgress) {
            val currentFirstVisibleIndex = gridState.firstVisibleItemIndex

            // 判断滚动方向：向下滚动时，firstVisibleItemIndex增大
            isScrollingDown = currentFirstVisibleIndex > lastFirstVisibleIndex

            lastScrollTime = System.currentTimeMillis()
            hasUserScrolled = true // 标记用户已主动滚动
            lastFirstVisibleIndex = currentFirstVisibleIndex
        } else {
            // 滚动停止时保存位置
            vm.saveScrollPosition(
                gridState.firstVisibleItemIndex,
                gridState.firstVisibleItemScrollOffset,
            )
            lastFirstVisibleIndex = gridState.firstVisibleItemIndex
        }
    }

    // Guest用户拦截逻辑：当Spacer可见 + 向下滚动 + 到达第一页末尾时触发
    LaunchedEffect(isSpacerVisible, isAtPageEnd, isScrollingDown) {
        if (
            isSpacerVisible &&
                isAtPageEnd &&
                isScrollingDown &&
                hasUserScrolled &&
                GuestLoginLimiter.shouldLimitGuest()
        ) {
            // 触发guest登录拦截
            GuestLoginLimiter.checkAndNavigateToLogin(context)
        }
    }

    // 监听滚动到底部事件（用于显示loading指示器）
    LaunchedEffect(isSpacerVisible, lazyPagingItems?.loadState?.append) {
        if (isSpacerVisible && hasUserScrolled) { // 只有用户主动滚动过才检查
            val currentTime = System.currentTimeMillis()

            // 只有在Paging正在加载时才显示loading指示器
            if (lazyPagingItems?.loadState?.append is LoadState.Loading) {
                // 只有在用户主动滚动且不是首次加载时才显示loading
                // 首次进入时使用缓存数据，不应该显示加载更多loading
                if (
                    currentTime - lastScrollTime < 1000 &&
                        lazyPagingItems.itemCount > 0 &&
                        lazyPagingItems.loadState.refresh is LoadState.NotLoading
                ) {
                    showLoadMoreLoading = true
                    // 延迟隐藏loading
                    delay(2000)
                    showLoadMoreLoading = false
                }
            }
        }
    }

    // 检查加载状态
    val loadState = lazyPagingItems?.loadState?.refresh

    // 如果是错误状态且没有数据，显示错误状态
    if (loadState is LoadState.Error && lazyPagingItems.itemCount == 0) {
        NetworkErrorState(
            onRetry = onRetry ?: { lazyPagingItems.retry() },
            modifier = modifier.fillMaxSize(),
        )
    } else if (loadState is LoadState.NotLoading && lazyPagingItems.itemCount == 0) {
        // 如果没有数据且加载完成，显示空数据状态
        EmptyDataState(
            subtitle = stringResource(R.string.empty_explore_data),
            modifier = modifier.fillMaxSize(),
        )
    } else {
        LazyVerticalGrid(
            columns = GridCells.Fixed(2),
            modifier = modifier.padding(bottom = innerPadding.calculateBottomPadding()),
            state = gridState,
            contentPadding = PaddingValues(16.dp),
            horizontalArrangement = Arrangement.spacedBy(6.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            // 如果没有Paging数据，显示加载状态
            if (lazyPagingItems == null) {
                item(span = { GridItemSpan(maxLineSpan) }) { EmptyStateIndicator() }
            } else {
                // 使用Paging的items
                items(
                    count = lazyPagingItems.itemCount,
                    key =
                        lazyPagingItems.itemKey { agent ->
                            // 确保key的唯一性，避免空id导致的重复key问题
                            agent.id.ifEmpty {
                                // 如果id为空，使用其他字段组合生成唯一key
                                "${agent.name}_${agent.avatar}_${agent.createdAt}"
                            }
                        },
                ) { index ->
                    val agent = lazyPagingItems[index]
                    if (agent != null) {
                        ExploreCharacterCard(
                            modifier = Modifier.fillMaxWidth(),
                            agentInfo = agent,
                            onClick = { onClickAgent(agent) },
                        )
                    } else {
                        // 显示加载占位符
                        ShimmerPlaceholder(
                            modifier =
                                Modifier.fillMaxWidth()
                                    .height(200.dp)
                                    .clip(RoundedCornerShape(8.dp))
                        )
                    }
                }

                // 加载状态指示器
                item(span = { GridItemSpan(maxLineSpan) }) {
                    ExploreLoadingStates(lazyPagingItems, showLoadMoreLoading, isRefreshing)
                }
            }

            item { Spacer(Modifier.height(16.dp)) }
        }
    }
}

/** 空状态指示器 */
@Composable
private fun EmptyStateIndicator() {
    Box(modifier = Modifier.fillMaxSize().height(200.dp), contentAlignment = Alignment.Center) {
        CircularProgressIndicator(modifier = Modifier.size(24.dp), color = Color.White.copy(0.7f))
    }
}
