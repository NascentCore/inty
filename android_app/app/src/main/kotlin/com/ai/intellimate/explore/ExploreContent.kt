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
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.nestedscroll.nestedScroll
import androidx.compose.ui.layout.layout
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.Constraints
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.paging.LoadState
import androidx.paging.PagingData
import androidx.paging.compose.collectAsLazyPagingItems
import androidx.paging.compose.itemKey
import com.ai.intellimate.R
import com.ai.intellimate.explore.special.HorizontalAgentCardList
import com.ai.intellimate.explore.special.SpecialDetailActivity
import com.ai.intellimate.ui.UiConfigs
import com.ai.intellimate.ui.components.EmptyDataState
import com.ai.intellimate.ui.components.NetworkErrorState
import com.ai.intellimate.ui.components.ShimmerPlaceholder
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow

// 判断是否为动图URL（非视频）
private fun isAnimatedImageUrl(url: String?): Boolean {
    if (url.isNullOrBlank()) return false
    val lowerUrl = url.lowercase()
    return lowerUrl.endsWith(".gif") ||
            lowerUrl.endsWith(".webp") ||
            lowerUrl.endsWith(".avif") ||
            lowerUrl.contains(".gif?") ||
            lowerUrl.contains(".webp?") ||
            lowerUrl.contains(".avif?")
}

/**
 * 创建全屏宽度的 Modifier，突破 LazyVerticalGrid 的 contentPadding 限制
 * @param screenWidthPx 屏幕宽度（像素）
 */
private fun Modifier.fullWidthLayout(screenWidthPx: Float): Modifier {
    return this.layout { measurable, constraints ->
        // 突破父容器的约束，使用屏幕宽度实现全屏显示
        val fullWidthConstraints =
            Constraints(
                minWidth = screenWidthPx.toInt(),
                maxWidth = screenWidthPx.toInt(),
                minHeight = constraints.minHeight,
                maxHeight = constraints.maxHeight,
            )
        val placeable = measurable.measure(fullWidthConstraints)
        layout(placeable.width, placeable.height) {
            placeable.placeRelative(0, 0)
        }
    }
}

/** Explore页面的主要内容组件 */
@Composable
fun ExploreContent(
    modifier: Modifier = Modifier,
    agentsFlow: Flow<PagingData<AgentInfo>>?,
    innerPadding: PaddingValues,
    onClickAgent: (AgentInfo) -> Unit,
    isRefreshing: Boolean = false,
    onRetry: (() -> Unit)? = null,
    viewModel: ExploreViewModel = viewModel(),
    resetToTopSignal: Int = 0,
) {
    val lazyPagingItems = agentsFlow?.collectAsLazyPagingItems()
    val vm: ExploreViewModel = viewModel
    val context = LocalContext.current
    val density = LocalDensity.current
    val configuration = LocalConfiguration.current

    // 获取主题专区数据
    val characterThemes by vm.characterThemes.collectAsState()
    // 获取缓存加载状态
    val isCacheLoaded by vm.isCacheLoaded.collectAsState()

    // 计算全屏宽度（在 Composable 顶层计算，避免在 item lambda 中调用 CompositionLocal）
    val screenWidthPx = with(density) {
        configuration.screenWidthDp.dp.toPx()
    }

    // 加载主题专区列表
    // 1. ViewModel 创建时从缓存加载（在 ViewModel.init 中已处理），确保快速显示
    // 2. 等待缓存加载完成后再决定是否需要网络请求，避免竞态条件
    // 3. 如果缓存为空或过期，从网络加载并更新缓存
    LaunchedEffect(isCacheLoaded) {
        // 只有在缓存加载完成后才检查是否需要网络请求
        if (!isCacheLoaded) {
            return@LaunchedEffect
        }

        val currentThemes = vm.characterThemes.value
        if (currentThemes.isEmpty()) {
            // 缓存为空，从网络加载
            vm.loadCharacterThemes(skip = 0, limit = 100)
        } else {
            // 缓存有数据，检查是否过期，如果过期则在后台刷新
            val isCacheExpired =
                com.ai.intellimate.utils.AgentCacheManager.isCharacterThemesCacheExpired()
            if (isCacheExpired) {
                vm.loadCharacterThemes(skip = 0, limit = 100)
            }
        }
    }

    // 更新当前UI中显示的agents总数
    LaunchedEffect(lazyPagingItems?.itemCount) {
        lazyPagingItems?.itemCount?.let { count -> vm.updateCurrentUiAgentsCount(count) }
    }

    // 计算主题专区的 item 数量（每个有 agents 的 theme 是一个 item）
    val themeItemCount = remember(characterThemes) {
        characterThemes.count { it.agents.isNotEmpty() }
    }

    val gridState =
        rememberLazyGridState(
            // 将保存的 agent 索引转换为网格索引（加上当前主题项数量）
            initialFirstVisibleItemIndex = vm.getRestoredGridIndex(themeItemCount),
            initialFirstVisibleItemScrollOffset = vm.savedFirstVisibleOffset.collectAsState().value,
        )

    val scrollConnection =
        rememberExploreScrollConnection(
            initialVelocityMultiplier = UiConfigs.Explore.SCROLL_INITIAL_VELOCITY_MULTIPLIER,
            minFlingVelocity = UiConfigs.Explore.SCROLL_MIN_FLING_VELOCITY,
            maxFlingVelocity = UiConfigs.Explore.SCROLL_MAX_FLING_VELOCITY,
            decelerationMultiplier = UiConfigs.Explore.SCROLL_DECELERATION_MULTIPLIER,
            scrollDeltaThreshold = UiConfigs.Explore.SCROLL_DELTA_THRESHOLD,
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

    // 检测应该播放动图的 item 索引列表（所有可见区域>=70%的item，按位置从上到下排序）
    // 注意：返回的是 lazyPagingItems 的索引（从 0 开始），不是网格索引
    val visibleItemIndices by remember(themeItemCount) {
        derivedStateOf {
            val layoutInfo = gridState.layoutInfo
            val viewportHeight = layoutInfo.viewportEndOffset - layoutInfo.viewportStartOffset
            if (viewportHeight <= 0) return@derivedStateOf emptyList<Int>()

            val agentItemCount = lazyPagingItems?.itemCount ?: 0
            if (agentItemCount == 0) return@derivedStateOf emptyList<Int>()

            // 过滤出 agent items（排除 theme items、加载状态指示器和 Spacer）
            // 网格索引范围：themeItemCount 到 themeItemCount + agentItemCount - 1
            val agentItems =
                layoutInfo.visibleItemsInfo.filter { itemInfo ->
                    val gridIndex = itemInfo.index
                    // agent items 的网格索引范围是 [themeItemCount, themeItemCount + agentItemCount)
                    gridIndex >= themeItemCount && gridIndex < themeItemCount + agentItemCount
                }

            // 找到所有可见比例 >= 70% 的 item 索引（按位置排序，从上到下）
            // 注意：这里存储的是 lazyPagingItems 的索引（网格索引减去 themeItemCount）
            val visibleIndices = mutableListOf<Int>()
            for (itemInfo in agentItems.sortedBy { it.offset.y }) {
                val itemTop = itemInfo.offset.y
                val itemBottom = itemInfo.offset.y + itemInfo.size.height
                val viewportTop = layoutInfo.viewportStartOffset
                val viewportBottom = layoutInfo.viewportEndOffset

                // 计算可见区域
                val visibleTop = maxOf(itemTop, viewportTop)
                val visibleBottom = minOf(itemBottom, viewportBottom)
                val visibleHeight = maxOf(0, visibleBottom - visibleTop)
                val itemHeight = itemInfo.size.height

                // 计算可见比例
                val visibleRatio = if (itemHeight > 0) visibleHeight.toFloat() / itemHeight else 0f

                // 如果可见比例 >= 70%，添加到列表中（保持从上到下的顺序）
                // 将网格索引转换为 lazyPagingItems 索引
                if (visibleRatio >= 0.7f) {
                    val agentIndex = itemInfo.index - themeItemCount
                    visibleIndices.add(agentIndex)
                }
            }

            visibleIndices
        }
    }

    // 找到第一个可见且有 backgroundAnimatedUrl 的 item 索引
    // 注意：存储的是 lazyPagingItems 的索引（从 0 开始），不是网格索引
    var firstPlayingItemIndex by remember { mutableIntStateOf(-1) }

    // 监听可见项和 item 数据变化，更新播放索引
    // 使用 snapshotFlow 监听 gridState.layoutInfo 的变化，确保滚动时也能及时更新
    LaunchedEffect(lazyPagingItems?.itemCount, themeItemCount) {
        snapshotFlow { gridState.layoutInfo }
            .collect {
                val itemCount = lazyPagingItems?.itemCount ?: 0
                if (itemCount == 0) {
                    firstPlayingItemIndex = -1
                    return@collect
                }

                // 获取当前可见的 item 索引列表（已经是 lazyPagingItems 的索引）
                val indices = visibleItemIndices

                // 按顺序遍历可见的 item（已经按从上到下排序），找到第一个有 backgroundAnimatedUrl 且是动图的
                firstPlayingItemIndex = -1
                for (index in indices) {
                    // 检查索引是否在有效范围内，避免 IndexOutOfBoundsException
                    // index 已经是 lazyPagingItems 的索引，直接使用
                    if (index !in 0..<itemCount) {
                        continue
                    }
                    val agent = lazyPagingItems?.get(index)
                    if (agent != null && agent.backgroundAnimatedUrl.isNotBlank()) {
                        // 只处理动图，不处理视频
                        if (isAnimatedImageUrl(agent.backgroundAnimatedUrl)) {
                            firstPlayingItemIndex = index
                            break
                        }
                    }
                }
            }
    }

    // 监听滚动状态，保存位置和更新滚动标记
    LaunchedEffect(gridState, themeItemCount) {
        snapshotFlow { gridState.isScrollInProgress to gridState.firstVisibleItemIndex }
            .collect { (isScrollInProgress, firstVisibleItemIndex) ->
                if (isScrollInProgress) {
                    lastScrollTime = System.currentTimeMillis()
                    hasUserScrolled = true // 标记用户已主动滚动
                } else {
                    // 滚动停止时保存位置
                    // 将网格索引转换为 agent 索引（如果第一个可见项是 agent 项）
                    val agentIndex = if (firstVisibleItemIndex >= themeItemCount) {
                        // 第一个可见项是 agent 项，转换为 agent 索引
                        firstVisibleItemIndex - themeItemCount
                    } else {
                        // 第一个可见项是主题项或加载状态指示器，保存 0（表示滚动到顶部）
                        0
                    }
                    vm.saveScrollPosition(
                        agentIndex,
                        gridState.firstVisibleItemScrollOffset,
                    )
                }
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

    LaunchedEffect(resetToTopSignal) {
        if (resetToTopSignal > 0) {
            gridState.scrollToItem(0)
            vm.saveScrollPosition(0, 0)
            if (lazyPagingItems != null) {
                lazyPagingItems.refresh()
            } else {
                vm.refreshRecommendAgents()
            }
            // 刷新时也重新加载主题专区（从网络加载，更新缓存）
            vm.loadCharacterThemes(skip = 0, limit = 100)
        }
    }

    // 如果是错误状态且没有数据，显示错误状态
    when (loadState) {
        is LoadState.Error if lazyPagingItems.itemCount == 0 -> {
            NetworkErrorState(
                onRetry = onRetry ?: { lazyPagingItems.retry() },
                modifier = modifier.fillMaxSize(),
            )
        }

        is LoadState.NotLoading if lazyPagingItems.itemCount == 0 -> {
            // 如果没有数据且加载完成，显示空数据状态
            EmptyDataState(
                subtitle = stringResource(R.string.empty_explore_data),
                modifier = modifier.fillMaxSize(),
            )
        }

        else -> {
            LazyVerticalGrid(
                columns = GridCells.Fixed(2),
                modifier =
                    modifier
                        .padding(bottom = innerPadding.calculateBottomPadding())
                        .nestedScroll(scrollConnection),
                state = gridState,
                contentPadding = PaddingValues(horizontal = 16.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                // 如果没有Paging数据，显示加载状态
                if (lazyPagingItems == null) {
                    item(span = { GridItemSpan(maxLineSpan) }) { EmptyStateIndicator() }
                } else {
                    // 主题专区的item数据，如果有接口数据则显示，无则不显示
                    // 注意：主题专区需要全屏宽度，不受 contentPadding 影响
                    characterThemes.forEach { theme ->
                        if (theme.agents.isNotEmpty()) {
                            item(span = { GridItemSpan(maxLineSpan) }) {
                                // 使用全屏宽度布局，突破 LazyVerticalGrid 的 contentPadding 限制
                                Box(modifier = Modifier.fullWidthLayout(screenWidthPx)) {
                                    HorizontalAgentCardList(
                                        title = theme.name,
                                        description = theme.description,
                                        agents = theme.agents,
                                        isChristmas = theme.isChristmas,
                                        onAgentClick = onClickAgent,
                                        onTitleClick = {
                                            // 跳转到主题详情页面
                                            SpecialDetailActivity.launch(
                                                context = context,
                                                themeId = theme.id,
                                                themeTitle = theme.name,
                                                themeDescription = theme.description,
                                                isChristmas = theme.isChristmas,
                                                agents = theme.agents,
                                            )
                                        },
                                    )
                                }
                            }
                        }
                    }

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
                            // 只播放第一个可见且有 backgroundAnimatedUrl 的 item
                            // index 是 lazyPagingItems 的索引（从 0 开始），firstPlayingItemIndex 也是
                            val shouldPlay = index == firstPlayingItemIndex

                            ExploreCharacterCard(
                                modifier = Modifier.fillMaxWidth(),
                                agentInfo = agent,
                                onClick = { onClickAgent(agent) },
                                index = index,
                                shouldPlayAnimated = shouldPlay,
                            )
                        } else {
                            // 显示加载占位符
                            ShimmerPlaceholder(
                                modifier = Modifier
                                    .fillMaxWidth()
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
}

/** 空状态指示器 */
@Composable
private fun EmptyStateIndicator() {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .height(200.dp), contentAlignment = Alignment.Center
    ) {
        CircularProgressIndicator(modifier = Modifier.size(24.dp), color = Color.White.copy(0.7f))
    }
}
