package com.ai.inty.explore

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
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.paging.LoadState
import androidx.paging.PagingData
import androidx.paging.compose.collectAsLazyPagingItems
import androidx.paging.compose.itemKey
import com.ai.inty.beans.AgentInfo
import com.ai.inty.ui.components.EmptyDataState
import com.ai.inty.ui.components.NetworkErrorState
import com.ai.inty.ui.components.ShimmerPlaceholder
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

    val gridState =
        rememberLazyGridState(
            initialFirstVisibleItemIndex = vm.savedFirstVisibleIndex.collectAsState().value,
            initialFirstVisibleItemScrollOffset = vm.savedFirstVisibleOffset.collectAsState().value,
        )

    // 检测用户是否主动滚动到底部触发加载更多
    var showLoadMoreLoading by remember { mutableStateOf(false) }
    var lastScrollTime by remember { mutableLongStateOf(0L) }

    // 检测滚动状态
    val isScrolledToBottom by remember {
        derivedStateOf {
            val layoutInfo = gridState.layoutInfo
            val totalItemsCount = layoutInfo.totalItemsCount
            val lastVisibleItemIndex = layoutInfo.visibleItemsInfo.lastOrNull()?.index ?: -1

            // 检测是否滚动到底部
            totalItemsCount > 0 && lastVisibleItemIndex >= totalItemsCount - 1
        }
    }

    // 监听滚动到底部事件
    LaunchedEffect(isScrolledToBottom, lazyPagingItems?.loadState?.append) {
        if (isScrolledToBottom && lazyPagingItems?.loadState?.append is LoadState.Loading) {
            val currentTime = System.currentTimeMillis()
            // 关键修复：只有在用户主动滚动且不是首次加载时才显示loading
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

    // 更新滚动时间与保存滚动位置
    LaunchedEffect(gridState.isScrollInProgress) {
        if (gridState.isScrollInProgress) {
            lastScrollTime = System.currentTimeMillis()
        } else {
            // 滚动停止时保存位置
            vm.saveScrollPosition(
                gridState.firstVisibleItemIndex,
                gridState.firstVisibleItemScrollOffset,
            )
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
            subtitle = stringResource(com.ai.inty.R.string.empty_explore_data),
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
