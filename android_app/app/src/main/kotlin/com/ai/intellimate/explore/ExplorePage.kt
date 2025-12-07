package com.ai.intellimate.explore

import ai.sxwl.android.common.analytics.PageTrackingHelper
import ai.sxwl.android.common.startup.ImagePreloadManager
import ai.sxwl.android.common.utils.HeartAppUtils
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.utils.ToastUtils
import android.annotation.SuppressLint
import androidx.compose.foundation.Image
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
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
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.input.pointer.pointerInput
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.paging.LoadState
import androidx.paging.compose.collectAsLazyPagingItems
import coil3.compose.AsyncImage
import com.ai.intellimate.R
import com.ai.intellimate.boost.BoostLeaderboardEntry
import com.ai.intellimate.boost.BoostManager
import com.ai.intellimate.boost.BoostState
import com.ai.intellimate.boost.ui.BoostLeaderboardTab
import com.ai.intellimate.chat.ChatActivity
import kotlinx.coroutines.delay

private enum class ExploreSubTab {
    Recommended,
    Boost,
}

private val ExploreTabSwipeThreshold = 72.dp

/** Explore页面 - 推荐agents展示 */
@OptIn(ExperimentalMaterial3Api::class)
@SuppressLint("ConfigurationScreenWidthHeight")
@Composable
fun ExplorePage(
    modifier: Modifier = Modifier,
    innerPadding: PaddingValues,
    onClickAgent: (AgentInfo) -> Unit,
    viewModel: ExploreViewModel = viewModel(),
    /** 外部重置信号（来自底部导航栏双击），当值变化时触发滚动到顶部并刷新 */
    externalResetSignal: Int = 0,
) {
    val context = LocalContext.current
    val isDebugMode = HeartAppUtils.isAppDebugMode()
    var selectedTab by remember { mutableStateOf(ExploreSubTab.Recommended) }
    val boostState by
        if (isDebugMode) BoostManager.boostState.collectAsState()
        else remember { mutableStateOf(BoostState()) }
    val leaderboard by
        if (isDebugMode) BoostManager.leaderboard.collectAsState()
        else remember { mutableStateOf(emptyList<BoostLeaderboardEntry>()) }
    val density = LocalDensity.current
    val tabSwipeThresholdPx = remember(density) { with(density) { ExploreTabSwipeThreshold.toPx() } }
    val tabSwipeModifier =
        if (isDebugMode) {
            Modifier.pointerInput(selectedTab, tabSwipeThresholdPx) {
                var totalDrag = 0f
                detectHorizontalDragGestures(
                    onDragStart = { totalDrag = 0f },
                    onHorizontalDrag = { change, dragAmount ->
                        change.consume()
                        totalDrag += dragAmount
                    },
                    onDragCancel = { totalDrag = 0f },
                    onDragEnd = {
                        when {
                            totalDrag <= -tabSwipeThresholdPx -> {
                                val nextIndex =
                                    (selectedTab.ordinal + 1)
                                        .coerceAtMost(ExploreSubTab.entries.lastIndex)
                                if (nextIndex != selectedTab.ordinal) {
                                    selectedTab = ExploreSubTab.entries[nextIndex]
                                }
                            }

                            totalDrag >= tabSwipeThresholdPx -> {
                                val previousIndex =
                                    (selectedTab.ordinal - 1).coerceAtLeast(0)
                                if (previousIndex != selectedTab.ordinal) {
                                    selectedTab = ExploreSubTab.entries[previousIndex]
                                }
                            }
                        }
                        totalDrag = 0f
                    },
                )
            }
        } else {
            Modifier
        }

    // 获取Paging数据流
    val agentsFlow = viewModel.getRecommendAgentsFlow()
    val lazyPagingItems = agentsFlow?.collectAsLazyPagingItems()

    val handleLeaderboardAction: (BoostLeaderboardEntry, Boolean) -> Unit = { entry, showSheet ->
        if (entry.isSeed || entry.agentId.isBlank()) {
            ToastUtils.showShort(R.string.boost_seed_placeholder_toast)
        } else {
            ChatActivity.launch(
                context,
                agentInfo = null,
                agentId = entry.agentId,
                pageSource = ChatActivity.EXPLORE_TAB,
                showBoostSheet = showSheet,
            )
        }
    }

    // 使用 PageTrackingHelper 进行页面跟踪
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

    // 初始化图片尺寸缓存管理器和图片预加载管理器
    LaunchedEffect(Unit) { ImagePreloadManager.init(context) }

    Box(modifier = modifier) {
        AsyncImage(
            modifier = Modifier.align(Alignment.TopEnd),
            model = R.drawable.notify_header_bg,
            contentDescription = null,
        )

        Column(
            modifier = Modifier.fillMaxSize().background(Color.Transparent).then(tabSwipeModifier)
        ) {
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
            )

            if (isDebugMode) {
                TabRow(
                    selectedTabIndex = selectedTab.ordinal,
                    containerColor = Color.Transparent,
                    contentColor = Color.White,
                ) {
                    ExploreSubTab.entries.forEach { tab ->
                        Tab(
                            selected = selectedTab == tab,
                            onClick = { selectedTab = tab },
                            text = {
                                Text(
                                    text =
                                        stringResource(
                                            if (tab == ExploreSubTab.Recommended)
                                                R.string.boost_tab_recommend
                                            else R.string.boost_tab_leaderboard
                                        ),
                                    color = Color.White,
                                )
                            },
                        )
                    }
                }
            }

            if (!isDebugMode || selectedTab == ExploreSubTab.Recommended) {
                var isRefreshing by remember { mutableStateOf(false) }
                var refreshStartTime by remember { mutableLongStateOf(0L) }

                LaunchedEffect(lazyPagingItems?.loadState?.refresh, isRefreshing) {
                    val currentTime = System.currentTimeMillis()
                    val minRefreshDuration = 400L
                    val elapsedTime =
                        if (refreshStartTime > 0) currentTime - refreshStartTime else 0L

                    when (lazyPagingItems?.loadState?.refresh) {
                        is LoadState.Loading -> {
                            if (isRefreshing && refreshStartTime == 0L) {
                                refreshStartTime = currentTime
                            }
                        }

                        is LoadState.NotLoading -> {
                            if (isRefreshing) {
                                if (elapsedTime >= minRefreshDuration) {
                                    isRefreshing = false
                                    refreshStartTime = 0L
                                } else {
                                    delay(minRefreshDuration - elapsedTime)
                                    isRefreshing = false
                                    refreshStartTime = 0L
                                }
                            }
                        }

                        is LoadState.Error -> {
                            if (isRefreshing) {
                                if (elapsedTime >= minRefreshDuration) {
                                    isRefreshing = false
                                    refreshStartTime = 0L
                                } else {
                                    delay(minRefreshDuration - elapsedTime)
                                    isRefreshing = false
                                    refreshStartTime = 0L
                                }
                            }
                        }

                        null -> {
                            if (isRefreshing) {
                                if (elapsedTime >= minRefreshDuration) {
                                    isRefreshing = false
                                    refreshStartTime = 0L
                                } else {
                                    delay(minRefreshDuration - elapsedTime)
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
                    )
                }
            } else if (isDebugMode && selectedTab == ExploreSubTab.Boost) {
                BoostLeaderboardTab(
                    modifier = Modifier.fillMaxSize(),
                    availablePoints = boostState.availablePoints,
                    entries = leaderboard,
                    onChat = { entry -> handleLeaderboardAction(entry, false) },
                    onBoost = { entry -> handleLeaderboardAction(entry, true) },
                )
            }
        }
    }
}
