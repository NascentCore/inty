package com.ai.intellimate.explore

import ai.sxwl.android.data.api.model.AgentInfo
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.paging.LoadState
import androidx.paging.compose.LazyPagingItems

/** Explore页面的加载状态组件 */
@Composable
fun ExploreLoadingStates(
    lazyPagingItems: LazyPagingItems<AgentInfo>,
    showLoadMoreLoading: Boolean = false,
    isRefreshing: Boolean = false,
) {
    // 加载更多状态指示器
    when (lazyPagingItems.loadState.append) {
        is LoadState.Loading -> {
            // 只在用户主动滚动触发加载更多时显示loading
            // 关键修复：下拉刷新时不应该显示加载更多loading
            if (showLoadMoreLoading && lazyPagingItems.itemCount > 0 && !isRefreshing) {
                LoadingMoreIndicator()
            }
        }
        is LoadState.Error -> {
            LoadMoreErrorIndicator()
        }
        is LoadState.NotLoading -> {
            // 只有在真正没有更多数据且不是初始状态时才显示
            // 增加更严格的条件：确保不是首次加载，且确实没有更多数据
            if (
                lazyPagingItems.loadState.append.endOfPaginationReached &&
                    lazyPagingItems.itemCount > 0 &&
                    lazyPagingItems.loadState.refresh is LoadState.NotLoading &&
                    !lazyPagingItems.loadState.prepend.endOfPaginationReached
            ) { // 确保不是初始状态
                NoMoreDataIndicator()
            }
        }
    }
}

/** 加载更多指示器 */
@Composable
private fun LoadingMoreIndicator() {
    Box(
        modifier = Modifier.size(165.dp, 60.dp).padding(16.dp),
        contentAlignment = Alignment.Center,
    ) {
        CircularProgressIndicator(modifier = Modifier.size(24.dp), color = Color.White.copy(0.7f))
    }
}

/** 加载更多错误指示器 */
@Composable
private fun LoadMoreErrorIndicator() {
    Box(modifier = Modifier.fillMaxWidth().padding(16.dp), contentAlignment = Alignment.Center) {
        Text(
            text = "Failed to load more data",
            color = Color.White.copy(0.7f),
            fontSize = 12.sp,
            textAlign = TextAlign.Center,
        )
    }
}

/** 没有更多数据指示器 - 跨两列显示 */
@Composable
private fun NoMoreDataIndicator() {
    Box(modifier = Modifier.fillMaxWidth().padding(16.dp), contentAlignment = Alignment.Center) {
        Text(
            text = "No more data available",
            color = Color.White.copy(0.6f),
            fontSize = 12.sp,
            textAlign = TextAlign.Center,
        )
    }
}
