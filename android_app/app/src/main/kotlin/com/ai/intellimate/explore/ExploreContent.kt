package com.ai.intellimate.explore

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.design.noRippleClickable
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.input.nestedscroll.nestedScroll
import androidx.compose.ui.layout.layout
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.res.vectorResource
import androidx.compose.ui.unit.Constraints
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import androidx.paging.LoadState
import androidx.paging.PagingData
import androidx.paging.compose.collectAsLazyPagingItems
import androidx.paging.compose.itemKey
import com.ai.intellimate.BuildConfig
import com.ai.intellimate.R
import com.ai.intellimate.chat.ui.BackToTop
import com.ai.intellimate.explore.special.HorizontalAgentCardList
import com.ai.intellimate.ui.UiConfigs
import com.ai.intellimate.ui.components.EmptyDataState
import com.ai.intellimate.ui.components.NetworkErrorState
import com.ai.intellimate.ui.components.ShimmerPlaceholder
import com.ai.intellimate.xb.navigation.Routes
import com.squareup.moshi.Moshi
import com.squareup.moshi.Types
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

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
 *
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
        layout(placeable.width, placeable.height) { placeable.placeRelative(0, 0) }
    }
}

/** Explore页面的主要内容组件 */
@Composable
fun ExploreContent(
    modifier: Modifier = Modifier,
    agentsFlow: Flow<PagingData<AgentInfo>>?,
    innerPadding: PaddingValues,
    onClickAgent: (AgentInfo, String) -> Unit,
    isRefreshing: Boolean = false,
    onRetry: (() -> Unit)? = null,
    viewModel: ExploreViewModel = viewModel(),
    resetToTopSignal: Int = 0,
    navController: NavController? = null,
) {
    val lazyPagingItems = agentsFlow?.collectAsLazyPagingItems()
    val vm: ExploreViewModel = viewModel
    val context = LocalContext.current

    val moshi = remember { Moshi.Builder().addLast(KotlinJsonAdapterFactory()).build() }
    val agentListType = remember {
        Types.newParameterizedType(List::class.java, AgentInfo::class.java)
    }
    val agentListAdapter = remember { moshi.adapter<List<AgentInfo>>(agentListType) }
    val density = LocalDensity.current
    val configuration = LocalConfiguration.current

    // 获取主题专区数据
    val characterThemes by vm.characterThemes.collectAsState()
    // 获取最近创建角色数据（用于 Newly iMates 分区）
    val newlyCreatedAgents by vm.newlyCreatedAgents.collectAsState()
    // 获取缓存加载状态
    val isCacheLoaded by vm.isCacheLoaded.collectAsState()
    val newlyImatesTitle = stringResource(R.string.explore_newly_imates_title)
    val newlyImatesSubtitle = stringResource(R.string.explore_newly_imates_subtitle)
    val exploreThemeSections =
        remember(characterThemes, newlyCreatedAgents, newlyImatesTitle, newlyImatesSubtitle) {
            buildExploreThemeSections(
                characterThemes = characterThemes,
                newlyCreatedAgents = newlyCreatedAgents,
                newlyImatesTitle = newlyImatesTitle,
                newlyImatesSubtitle = newlyImatesSubtitle,
            )
        }

    // 计算全屏宽度（在 Composable 顶层计算，避免在 item lambda 中调用 CompositionLocal）
    val screenWidthPx = with(density) { configuration.screenWidthDp.dp.toPx() }

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

    // 计算主题专区的 item 数量（每个有 agents 的 theme section 是一个 item）
    val themeItemCount =
        remember(exploreThemeSections) { exploreThemeSections.count { it.agents.isNotEmpty() } }

    // 获取保存的滚动位置
    val savedGridIndex by vm.savedFirstVisibleGridIndex.collectAsState()
    val savedOffset by vm.savedFirstVisibleOffset.collectAsState()

    val gridState =
        rememberLazyGridState(
            // 直接使用保存的网格索引，如果没有保存位置（默认是0），会显示第一个item（theme或agent）
            initialFirstVisibleItemIndex = vm.getRestoredGridIndex(themeItemCount),
            initialFirstVisibleItemScrollOffset = savedOffset,
        )

    val scope = rememberCoroutineScope()
    val isAtExploreStart by remember {
        derivedStateOf {
            gridState.firstVisibleItemIndex == 0 && gridState.firstVisibleItemScrollOffset == 0
        }
    }
    val showBackToTopButton by remember { derivedStateOf { !isAtExploreStart } }
    val showGoToBottomButton by remember {
        derivedStateOf { BuildConfig.DEBUG && (lazyPagingItems?.itemCount ?: 0) > 0 }
    }

    // 标记是否正在恢复滚动位置，用于防止在恢复期间保存错误的位置
    var isRestoringScrollPosition by remember { mutableStateOf(false) }

    // 当缓存加载完成且themeItemCount确定后，恢复滚动位置
    // 这确保了在characterThemes加载完成后，能够正确恢复之前的位置（包括theme项的位置）
    // 使用基于isCacheLoaded和themeItemCount的key，确保每次这些值变化时都重新评估是否需要恢复位置
    LaunchedEffect(isCacheLoaded, themeItemCount) {
        // 只有在缓存加载完成后才恢复位置
        if (!isCacheLoaded) {
            return@LaunchedEffect
        }

        // 检查保存的网格索引是否有效（非负数）
        // 注意：scrollToItem 会自动处理超出范围的索引，所以不需要手动检查上限
        if (savedGridIndex < 0) {
            // 如果保存的索引是负数，重置为0（显示第一个item）
            vm.saveScrollPosition(gridIndex = 0, offset = 0)
            return@LaunchedEffect
        }

        // 检查当前显示的位置是否与保存的位置一致
        val currentIndex = gridState.firstVisibleItemIndex
        val currentOffset = gridState.firstVisibleItemScrollOffset

        // 如果保存的位置与当前显示的位置不一致，需要恢复位置
        // 注意：这里不检查savedGridIndex是否为0，因为0也可能是有效的位置（第一个theme的位置或第一个agent的位置）
        if (savedGridIndex != currentIndex || savedOffset != currentOffset) {
            // 在延迟之前捕获保存的位置值，避免在延迟期间响应式状态被更新导致恢复错误的位置
            val targetGridIndex = savedGridIndex
            val targetOffset = savedOffset
            // 设置恢复标志，防止在恢复期间保存位置
            isRestoringScrollPosition = true
            // 添加小延迟确保LazyVerticalGrid已经布局完成
            delay(50)
            // scrollToItem 会自动处理超出范围的索引（会滚动到最接近的有效索引）
            gridState.scrollToItem(index = targetGridIndex, scrollOffset = targetOffset)
            // 等待滚动完成后再清除恢复标志
            // 轮询检查滚动状态，直到滚动完成（最多等待1秒，防止无限等待）
            var waitTime = 0L
            val maxWaitTime = 1000L // 最多等待1秒
            while (gridState.isScrollInProgress && waitTime < maxWaitTime) {
                delay(16) // 约一帧的时间
                waitTime += 16
            }
            // 滚动已完成或超时，清除恢复标志
            isRestoringScrollPosition = false
        }
    }

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
    val visibleItemIndices by
        remember(themeItemCount) {
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
                    val visibleRatio =
                        if (itemHeight > 0) visibleHeight.toFloat() / itemHeight else 0f

                    // 如果可见比例 >= 70%，添加到列表中（保持从上到下的顺序）
                    // 将网格索引转换为 lazyPagingItems 索引
                    if (visibleRatio >= 0.7f) {
                        val agentIndex = itemInfo.index - themeItemCount
                        // 确保 agentIndex 在有效范围内（双重检查，防止边界情况）
                        if (agentIndex in 0..<agentItemCount) {
                            visibleIndices.add(agentIndex)
                        }
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
                    // 如果正在恢复滚动位置，跳过保存操作，避免覆盖正确的保存位置
                    if (isRestoringScrollPosition) {
                        return@collect
                    }
                    // 直接保存网格索引，可以区分theme项和agent项
                    vm.saveScrollPosition(
                        gridIndex = firstVisibleItemIndex,
                        offset = gridState.firstVisibleItemScrollOffset,
                    )
                }
            }
    }

    // 监听滚动到底部事件（用于显示loading指示器）
    LaunchedEffect(isSpacerVisible, lazyPagingItems?.loadState?.append) {
        if (isSpacerVisible && hasUserScrolled) { // 只有用户主动滚动过才检查
            val currentTime = System.currentTimeMillis()
            val pagingItems = lazyPagingItems ?: return@LaunchedEffect

            // 只有在Paging正在加载时才显示loading指示器
            if (pagingItems.loadState.append is LoadState.Loading) {
                // 只有在用户主动滚动且不是首次加载时才显示loading
                // 首次进入时使用缓存数据，不应该显示加载更多loading
                if (
                    currentTime - lastScrollTime < 1000 &&
                        pagingItems.itemCount > 0 &&
                        pagingItems.loadState.refresh is LoadState.NotLoading
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
            // 重置时保存网格索引0，表示滚动到顶部（第一个theme的位置）
            vm.saveScrollPosition(gridIndex = 0, offset = 0)
            if (lazyPagingItems != null) {
                lazyPagingItems.refresh()
            } else {
                vm.refreshRecommendAgents()
            }
            // 刷新时也重新加载主题专区（从网络加载，更新缓存）
            vm.loadCharacterThemes(skip = 0, limit = 100)
            vm.loadNewlyCreatedAgents()
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
            Box(modifier = modifier.fillMaxSize()) {
                LazyVerticalGrid(
                    columns = GridCells.Fixed(2),
                    modifier =
                        Modifier.fillMaxSize()
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
                        exploreThemeSections.forEach { theme ->
                            if (theme.agents.isNotEmpty()) {
                                item(span = { GridItemSpan(maxLineSpan) }) {
                                    // 使用全屏宽度布局，突破 LazyVerticalGrid 的 contentPadding 限制
                                    Box(modifier = Modifier.fullWidthLayout(screenWidthPx)) {
                                        HorizontalAgentCardList(
                                            title = theme.name,
                                            description = theme.description,
                                            agents = theme.agents,
                                            isChristmas = theme.isChristmas,
                                            onAgentClick = {
                                                onClickAgent(
                                                    it,
                                                    getExploreThemeClickSource(theme.id),
                                                )
                                            },
                                            onTitleClick = {
                                                // 跳转到主题详情页面
                                                navController?.let { nav ->
                                                    val agentsJson =
                                                        try {
                                                            agentListAdapter.toJson(theme.agents)
                                                        } catch (e: Exception) {
                                                            ""
                                                        }
                                                    nav.navigate(
                                                        Routes.Explore.collectionDetail(
                                                            themeId = theme.id,
                                                            themeTitle = theme.name,
                                                            themeDescription = theme.description,
                                                            isChristmas = theme.isChristmas,
                                                            agentsJson = agentsJson,
                                                        )
                                                    )
                                                }
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

                                // 对创建于7天内的角色显示 "new" tag
                                ExploreCharacterCard(
                                    modifier = Modifier.fillMaxWidth(),
                                    agentInfo = agent,
                                    onClick = { onClickAgent(agent, "normal") },
                                    index = index,
                                    shouldPlayAnimated = shouldPlay,
                                    showNewTag = isCreatedWithin7Days(agent),
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
                            // TODO: 传入 onExploreMore，跳转到官方小助手以拓展角色发现；参考 项目管理/Explore
                            // 页面限制角色数量.md，开场白填充「你似乎没有在 Explore 页面找到你心仪的交往对象？他们还缺少什么呢？」。当前未传导致点击
                            // Explore More 无响应。
                            ExploreLoadingStates(
                                onRetry = { lazyPagingItems.retry() },
                                lazyPagingItems,
                                showLoadMoreLoading,
                                isRefreshing,
                            )
                        }
                    }

                    // 底部留白 ≥ Back to top 按钮高度 + 与 Explore More 的间距，避免二者重叠
                    item {
                        Spacer(
                            Modifier.height(
                                UiConfigs.ChatPage.FloatingScrollButton.ButtonSize +
                                    UiConfigs.Spacing.MediumPlus
                            )
                        )
                    }
                }

                // 复用 Chat 的回到顶部按钮样式与交互：不在顶部时显示，点击平滑滚动回第一个 item。
                // Debug 下增加 Go to bottom：点击持续请求下一页直到没有新角色，再滚到底部。
                Row(
                    modifier =
                        Modifier.align(Alignment.BottomCenter)
                            .padding(
                                bottom =
                                    innerPadding.calculateBottomPadding() +
                                        UiConfigs.Spacing.MediumPlus
                            ),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    GoToBottomButton(
                        visible = showGoToBottomButton,
                        onClick = {
                            val items = lazyPagingItems ?: return@GoToBottomButton
                            scope.launch {
                                var previousCount = items.itemCount
                                while (true) {
                                    val lastIndex =
                                        themeItemCount + (items.itemCount - 1).coerceAtLeast(0)
                                    if (lastIndex < themeItemCount) break
                                    gridState.animateScrollToItem(lastIndex)
                                    snapshotFlow { items.loadState.append }
                                        .first { it is LoadState.NotLoading }
                                    val appendState = items.loadState.append
                                    if (
                                        appendState is LoadState.NotLoading &&
                                            appendState.endOfPaginationReached
                                    )
                                        break
                                    if (items.itemCount == previousCount) break
                                    previousCount = items.itemCount
                                }
                                val finalLast =
                                    themeItemCount + (items.itemCount - 1).coerceAtLeast(0)
                                if (finalLast >= themeItemCount) {
                                    gridState.animateScrollToItem(finalLast)
                                }
                            }
                        },
                    )
                    BackToTop(
                        visible = showBackToTopButton,
                        onClick = { scope.launch { gridState.animateScrollToItem(0) } },
                    )
                }
            }
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

/**
 * Explore 页 Go to bottom 悬浮按钮（仅 debug 构建显示）。 与 Back to top
 * 同风格：圆形、白边、半透明黑底，双下箭头图标；点击后持续请求下一页直到没有新角色并滚到底部。
 */
@Composable
private fun GoToBottomButton(modifier: Modifier = Modifier, visible: Boolean, onClick: () -> Unit) {
    val config = UiConfigs.ChatPage.FloatingScrollButton
    AnimatedVisibility(visible = visible, enter = fadeIn(), exit = fadeOut(), modifier = modifier) {
        Box(
            modifier =
                Modifier.size(config.ButtonSize)
                    .clip(CircleShape)
                    .border(
                        config.BorderWidth,
                        brush =
                            Brush.horizontalGradient(
                                colors =
                                    listOf(
                                        Color.White.copy(config.BorderGradientStartAlpha),
                                        Color.White.copy(config.BorderGradientEndAlpha),
                                    )
                            ),
                        shape = CircleShape,
                    )
                    .background(Color.Black.copy(alpha = config.BackgroundAlpha), CircleShape)
                    .alpha(1f)
                    .noRippleClickable(onClick = onClick)
                    .padding(config.InnerPadding),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                imageVector =
                    ImageVector.vectorResource(R.drawable.keyboard_double_arrow_down_24px),
                contentDescription = stringResource(R.string.explore_go_to_bottom_cd),
                modifier = Modifier.size(config.IconSize),
                tint = Color.White,
            )
        }
    }
}
