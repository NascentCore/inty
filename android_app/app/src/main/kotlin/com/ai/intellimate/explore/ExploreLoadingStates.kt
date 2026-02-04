package com.ai.intellimate.explore

import ai.sxwl.android.data.api.model.AgentInfo
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.IconButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.paging.LoadState
import androidx.paging.compose.LazyPagingItems
import com.ai.intellimate.R
import com.ai.intellimate.ui.UiConfigs

/** Explore页面的加载状态组件 */
@Composable
fun ExploreLoadingStates(
    onRetry: () -> Unit,
    lazyPagingItems: LazyPagingItems<AgentInfo>,
    showLoadMoreLoading: Boolean = false,
    isRefreshing: Boolean = false,
    onExploreMore: () -> Unit = {},
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
            LoadMoreErrorIndicator(onRetry = onRetry)
        }
        is LoadState.NotLoading -> {
            // 只有在真正没有更多数据且不是初始状态时才显示
            // Explore 页面只向下加载（append），不向上加载（prepend），所以只需要检查 append 状态
            if (
                lazyPagingItems.loadState.append.endOfPaginationReached &&
                    lazyPagingItems.itemCount > 0 &&
                    lazyPagingItems.loadState.refresh is LoadState.NotLoading
            ) {
                NoMoreDataIndicator(onExploreMore = onExploreMore)
            }
        }
    }
}

/** 加载更多指示器 */
@Composable
private fun LoadingMoreIndicator() {
    Box(
        modifier = Modifier.fillMaxWidth().padding(UiConfigs.Spacing.MediumPlus),
        contentAlignment = Alignment.Center,
    ) {
        CircularProgressIndicator(
            modifier = Modifier.size(UiConfigs.TopIconsRow.Size),
            color = Color.White.copy(alpha = UiConfigs.Alpha.SecondaryText),
        )
    }
}

/** 加载更多错误指示器 */
@Composable
private fun LoadMoreErrorIndicator(onRetry: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(UiConfigs.Spacing.MediumPlus),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.Center,
    ) {
        Text(
            text = stringResource(R.string.explore_loading_more_hint),
            color = Color.White.copy(alpha = UiConfigs.Alpha.SecondaryText),
            style = MaterialTheme.typography.bodySmall,
            textAlign = TextAlign.Center,
        )

        IconButton(
            onClick = onRetry,
            colors = IconButtonDefaults.iconButtonColors(contentColor = Color.White),
        ) {
            Icon(
                imageVector = Icons.Rounded.Refresh,
                contentDescription = stringResource(R.string.retry_button),
            )
        }
    }
}

/**
 * 末尾 Explore More 按钮 - 跨两列显示。
 *
 * 使用场景：推荐列表加载完毕时，提示用户还有更多内容可探索。
 * 预期视觉效果：居中显示描边按钮，文字为 Explore More，保持轻量提示感。
 * 可配置项：onExploreMore - 按钮点击回调（当前为占位）。
 */
@Composable
private fun NoMoreDataIndicator(onExploreMore: () -> Unit = {}) {
    Box(
        modifier = Modifier.fillMaxWidth().padding(UiConfigs.Spacing.MediumPlus),
        contentAlignment = Alignment.Center,
    ) {
        OutlinedButton(
            onClick = onExploreMore,
            shape = RoundedCornerShape(UiConfigs.Shape.PrimaryButton),
            colors = ButtonDefaults.outlinedButtonColors(contentColor = Color.White),
        ) {
            Text(
                text = stringResource(R.string.explore_loading_explore_more),
                style = MaterialTheme.typography.labelLarge,
                textAlign = TextAlign.Center,
            )
        }
    }
}
