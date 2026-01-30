package com.ai.intellimate.explore

import ai.sxwl.android.common.analytics.PageTrackingHelper
import ai.sxwl.android.common.startup.ImagePreloadManager
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.design.theme.AppColors
import android.annotation.SuppressLint
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.text.font.FontWeight
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import androidx.paging.LoadState
import androidx.paging.compose.collectAsLazyPagingItems
import coil3.compose.AsyncImage
import com.ai.intellimate.R
import com.ai.intellimate.ui.UiConfigs
import com.ai.intellimate.xb.navigation.Routes
import kotlinx.coroutines.delay

private const val MIN_REFRESH_DURATION_MS = 400L

/** Explore页面 - 推荐agents展示 */
@OptIn(ExperimentalMaterial3Api::class)
@SuppressLint("ConfigurationScreenWidthHeight")
@Composable
fun ExplorePage(
    navController: NavController,
    modifier: Modifier = Modifier,
    innerPadding: PaddingValues,
    onClickAgent: (AgentInfo, String) -> Unit,
    viewModel: ExploreViewModel = viewModel(),
    /** 外部重置信号（来自底部导航栏双击），当值变化时触发滚动到顶部并刷新 */
    externalResetSignal: Int = 0,
) {
    val context = LocalContext.current

    val agentsFlow = viewModel.getRecommendAgentsFlow()
    val lazyPagingItems = agentsFlow?.collectAsLazyPagingItems()

    // 搜索相关状态
    var showSearchOverlay by rememberSaveable { mutableStateOf(false) }
    val searchResults by viewModel.searchResults.collectAsState()
    val isSearching by viewModel.isSearching.collectAsState()
    val hasSearchExecuted by viewModel.hasSearchExecuted.collectAsState()
    val relationshipFilter by viewModel.relationshipFilter.collectAsState()

    LaunchedEffect(Unit) {
        PageTrackingHelper.trackPageView(
            "ExplorePage",
            "MainActivity",
            mapOf(
                "agent_count" to (lazyPagingItems?.itemCount ?: 0),
                "is_loading" to (lazyPagingItems?.loadState?.refresh is LoadState.Loading),
            ),
        )
    }

    LaunchedEffect(Unit) { ImagePreloadManager.init(context) }

    Box(modifier = modifier) {
        AsyncImage(
            modifier = Modifier.align(Alignment.TopEnd),
            model = R.drawable.notify_header_bg,
            contentDescription = null,
        )

        Column(modifier = Modifier.fillMaxSize().background(Color.Transparent)) {
            TopAppBar(
                title = {
                    Image(
                        painter = painterResource(R.drawable.img_explore_title),
                        contentDescription = null,
                        modifier = Modifier.height(30.dp).fillMaxWidth(),
                        contentScale = ContentScale.Fit,
                        alignment = Alignment.CenterStart,
                    )
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.Transparent),
                actions = {
                    Row(
                        modifier = Modifier.padding(end = UiConfigs.Padding.ScreenHorizontal),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        BoostShortcutButton {
                            navController.navigate(Routes.Explore.BoostLeaderboard)
                        }
                        Spacer(Modifier.width(UiConfigs.TopIconsRow.Spacing))
                        SearchButton { showSearchOverlay = true }
                    }
                },
            )

            RelationshipTypeFilterRow(
                modifier =
                    Modifier.fillMaxWidth()
                        .padding(horizontal = UiConfigs.Padding.ScreenHorizontal),
                selectedType = relationshipFilter,
                onTypeSelected = { viewModel.setRelationshipFilter(it) },
            )
            Spacer(Modifier.height(UiConfigs.Spacing.Small))

            var isRefreshing by remember { mutableStateOf(false) }
            var refreshStartTime by remember { mutableLongStateOf(0L) }

            LaunchedEffect(lazyPagingItems?.loadState?.refresh, isRefreshing) {
                val currentTime = System.currentTimeMillis()
                val elapsedTime = if (refreshStartTime > 0) currentTime - refreshStartTime else 0L

                when (lazyPagingItems?.loadState?.refresh) {
                    is LoadState.Loading -> {
                        if (isRefreshing && refreshStartTime == 0L) {
                            refreshStartTime = currentTime
                        }
                    }

                    is LoadState.NotLoading,
                    is LoadState.Error,
                    null -> {
                        if (isRefreshing) {
                            if (elapsedTime >= MIN_REFRESH_DURATION_MS) {
                                isRefreshing = false
                                refreshStartTime = 0L
                            } else {
                                delay(MIN_REFRESH_DURATION_MS - elapsedTime)
                                isRefreshing = false
                                refreshStartTime = 0L
                            }
                        }
                    }
                }
            }

            PullToRefreshBox(
                isRefreshing = isRefreshing,
                onRefresh = {
                    refreshStartTime = System.currentTimeMillis()
                    isRefreshing = true
                    viewModel.refreshRecommendAgents()
                    viewModel.refreshCharacterThemes()
                },
                modifier = Modifier.fillMaxSize(),
            ) {
                ExploreContent(
                    modifier = Modifier.fillMaxSize(),
                    agentsFlow = agentsFlow,
                    innerPadding = innerPadding,
                    onClickAgent = onClickAgent,
                    isRefreshing = isRefreshing,
                    onRetry = { viewModel.refreshRecommendAgents() },
                    viewModel = viewModel,
                    resetToTopSignal = externalResetSignal,
                    navController = navController,
                )
            }
        }

        // 搜索浮层
        if (showSearchOverlay) {
            ExploreSearchOverlay(
                modifier = Modifier.fillMaxSize(),
                innerPadding = innerPadding,
                searchResults = searchResults,
                isSearching = isSearching,
                hasSearchExecuted = hasSearchExecuted,
                onDismiss = {
                    showSearchOverlay = false
                    viewModel.resetSearchState()
                },
                onQuerySubmit = { query ->
                    if (query.isNotBlank()) {
                        viewModel.searchAgentsByName(query)
                    }
                },
                onClickAgent = { agent ->
                    //                    showSearchOverlay = false
                    //                    viewModel.resetSearchState()
                    onClickAgent(agent, "search")
                },
            )
        }
    }
}

@Composable
private fun SearchButton(onClick: () -> Unit) {
    Box(
        modifier = Modifier.size(UiConfigs.TopIconsRow.Size).noRippleClickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Icon(
            painter = painterResource(R.drawable.search_24px),
            contentDescription = stringResource(R.string.explore_search_icon_desc),
            modifier = Modifier.size(UiConfigs.TopIconsRow.Size),
            tint = Color.White,
        )
    }
}

@Composable
private fun BoostShortcutButton(onClick: () -> Unit) {
    Box(
        modifier = Modifier.size(UiConfigs.TopIconsRow.Size).noRippleClickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Icon(
            painter = painterResource(R.drawable.rocket_launch_24px),
            contentDescription = stringResource(R.string.explore_boost_shortcut_cd),
            modifier = Modifier.size(UiConfigs.TopIconsRow.Size),
            tint = Color.White,
        )
    }
}

/**
 * Explore 关系类型筛选条。
 *
 * 使用场景：
 * - Explore 页顶部，用于快速切换角色关系类型的筛选条件。
 *
 * 预期视觉效果：
 * - 横向排列的胶囊筛选项，选中态高亮。
 *
 * 可配置项：
 * - [selectedType]：当前选中的关系类型。
 * - [onTypeSelected]：点击筛选项时触发的回调。
 * - [modifier]：容器布局修饰。
 */
@Composable
private fun RelationshipTypeFilterRow(
    modifier: Modifier = Modifier,
    selectedType: RelationshipType,
    onTypeSelected: (RelationshipType) -> Unit,
) {
    val options =
        remember {
            listOf(
                RelationshipType.ALL,
                RelationshipType.ENCOUNTERING,
                RelationshipType.LONG_TERM,
                RelationshipType.EXOTIC,
            )
        }
    Row(
        modifier =
            modifier.horizontalScroll(rememberScrollState())
                .padding(vertical = UiConfigs.Explore.RelationshipFilter.RowVerticalPadding),
        horizontalArrangement =
            Arrangement.spacedBy(UiConfigs.Explore.RelationshipFilter.ChipSpacing),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        options.forEach { type ->
            RelationshipTypeChip(
                label = relationshipTypeLabel(type),
                selected = type == selectedType,
                onClick = { onTypeSelected(type) },
            )
        }
    }
}

/**
 * 关系类型筛选项。
 *
 * 使用场景：
 * - 仅用于 [RelationshipTypeFilterRow] 内部。
 *
 * 预期视觉效果：
 * - 胶囊形背景，选中态更亮且文字加粗。
 *
 * 可配置项：
 * - [label]：展示文案。
 * - [selected]：是否选中。
 * - [onClick]：点击回调。
 * - [modifier]：容器布局修饰。
 */
@Composable
private fun RelationshipTypeChip(
    label: String,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val shape = RoundedCornerShape(UiConfigs.Explore.RelationshipFilter.ChipCornerRadius)
    val backgroundColor =
        if (selected) {
            AppColors.DarkPurpleOverlay60
        } else {
            AppColors.EmailLoginButtonGray
        }
    val borderAlpha =
        if (selected) {
            UiConfigs.Alpha.SecondaryText
        } else {
            UiConfigs.Alpha.SubtleBorder
        }
    val textAlpha = if (selected) 1f else UiConfigs.Alpha.SecondaryText
    val fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Medium

    Box(
        modifier =
            modifier.height(UiConfigs.Explore.RelationshipFilter.ChipHeight)
                .clip(shape)
                .background(backgroundColor)
                .border(
                    width = UiConfigs.Explore.RelationshipFilter.ChipBorderWidth,
                    color = Color.White.copy(alpha = borderAlpha),
                    shape = shape,
                )
                .noRippleClickable(onClick = onClick)
                .padding(
                    horizontal = UiConfigs.Explore.RelationshipFilter.ChipHorizontalPadding,
                    vertical = UiConfigs.Explore.RelationshipFilter.ChipVerticalPadding,
                ),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = label,
            color = Color.White.copy(alpha = textAlpha),
            fontSize = UiConfigs.Typography.Caption,
            fontWeight = fontWeight,
        )
    }
}

@Composable
private fun relationshipTypeLabel(type: RelationshipType): String {
    return when (type) {
        RelationshipType.ALL -> stringResource(R.string.explore_relationship_filter_all)
        RelationshipType.ENCOUNTERING ->
            stringResource(R.string.explore_relationship_filter_encountering)
        RelationshipType.LONG_TERM -> stringResource(R.string.explore_relationship_filter_long_term)
        RelationshipType.EXOTIC -> stringResource(R.string.explore_relationship_filter_exotic)
    }
}
