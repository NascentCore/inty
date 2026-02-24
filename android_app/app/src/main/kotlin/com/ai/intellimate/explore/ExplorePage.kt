package com.ai.intellimate.explore

import ai.sxwl.android.common.analytics.PageTrackingHelper
import ai.sxwl.android.common.startup.ImagePreloadManager
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.design.noRippleClickable
import android.annotation.SuppressLint
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import androidx.paging.LoadState
import androidx.paging.compose.collectAsLazyPagingItems
import coil3.compose.AsyncImage
import com.ai.intellimate.R
import com.ai.intellimate.ui.UiConfigs
import com.ai.intellimate.ui.components.IntelliMateCtaButton
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

            CreateIMateEntryBanner(
                modifier = Modifier.padding(horizontal = UiConfigs.Padding.ScreenHorizontal),
                onClick = { navController.navigate(Routes.Creat.CreateRole) },
            )
            Spacer(modifier = Modifier.height(UiConfigs.Spacing.Small))

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

/**
 * Explore 页顶部「Create your own iMate」横幅 CTA。
 *
 * 使用场景：作为创建 iMate 的主入口，固定展示在 Explore 顶部工具栏下方，便于用户在浏览推荐角色时立即进入创建流程。
 * 预期视觉效果：与全局 CTA 一致的横向渐变全宽按钮，文案为 "Create your own iMate"。
 * 可配置项：[modifier] 用于外层布局控制；[onClick] 处理点击后的导航行为。
 */
@Composable
private fun CreateIMateEntryBanner(modifier: Modifier = Modifier, onClick: () -> Unit) {
    IntelliMateCtaButton(
        text = stringResource(R.string.me_create_character_banner_title),
        onClick = onClick,
        modifier = modifier,
    )
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
