package com.ai.intellimate.explore

import ai.sxwl.android.common.analytics.PageTrackingHelper
import ai.sxwl.android.common.startup.ImagePreloadManager
import ai.sxwl.android.common.utils.HeartAppUtils
import ai.sxwl.android.data.api.model.AgentInfo
import android.annotation.SuppressLint
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Rocket
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
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
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import androidx.paging.LoadState
import androidx.paging.compose.collectAsLazyPagingItems
import coil3.compose.AsyncImage
import com.ai.intellimate.R
import com.ai.intellimate.boost.BoostLeaderboardActivity
import com.ai.intellimate.ui.UiConfigs
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
    val localLeaderboard by
        if (isDebugMode) BoostManager.leaderboard.collectAsState()
        else remember { mutableStateOf(emptyList<BoostLeaderboardEntry>()) }
    
    // 从 API 获取的能量排行榜
    val energyLeaderboard by viewModel.energyLeaderboard.collectAsState()
    val isLoadingEnergyLeaderboard by viewModel.isLoadingEnergyLeaderboard.collectAsState()
    
    // 当切换到 Boost tab 时，加载能量排行榜
    LaunchedEffect(selectedTab) {
        if (selectedTab == ExploreSubTab.Boost) {
            viewModel.loadEnergyLeaderboard()
        }
    }
    
    // 将 API 返回的 AgentInfo 转换为 BoostLeaderboardEntry
    val apiLeaderboard = remember(energyLeaderboard) {
        energyLeaderboard.mapIndexed { index, agentInfo ->
            // 暂时使用 0 作为 points，因为 AgentInfo 中可能还没有 points 字段
            // TODO: 当 SDK 更新后，从 agentInfo 中获取 points 值
            val points = 0 // agentInfo.points ?: 0
            val boostCount = points / com.ai.intellimate.boost.BoostConfig.BOOST_STEP_POINTS
            BoostLeaderboardEntry(
                rank = index + 1,
                agentId = agentInfo.id,
                agentName = agentInfo.name,
                avatarUrl = agentInfo.avatar,
                boostCount = boostCount,
                pointsInvested = points,
                trend = com.ai.intellimate.boost.BoostTrend.FLAT,
                isSeed = false,
            )
        }
    }
    
    // 优先使用 API 返回的排行榜，如果为空则使用本地排行榜
    val leaderboard = if (apiLeaderboard.isNotEmpty()) apiLeaderboard else localLeaderboard
    val density = LocalDensity.current
    val tabSwipeThresholdPx =
        remember(density) { with(density) { ExploreTabSwipeThreshold.toPx() } }
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
                                    (selectedTab.ordinal + 1).coerceAtMost(
                                        ExploreSubTab.entries.lastIndex
                                    )
                                if (nextIndex != selectedTab.ordinal) {
                                    selectedTab = ExploreSubTab.entries[nextIndex]
                                }
                            }

                            totalDrag >= tabSwipeThresholdPx -> {
                                val previousIndex = (selectedTab.ordinal - 1).coerceAtLeast(0)
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
                    if (isDebugMode) {
                        Box(modifier = Modifier.padding(end = UiConfigs.Padding.ScreenHorizontal)) {
                            BoostShortcutButton(
                                onClick = { BoostLeaderboardActivity.launch(context) }
                            )
                        }
                    }
                },
            )

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
                )
            }
        }
    }
}

@Composable
private fun BoostShortcutButton(onClick: () -> Unit) {
    val label = stringResource(R.string.explore_boost_shortcut)
    Button(
        onClick = onClick,
        shape = RoundedCornerShape(100.dp),
        colors =
            ButtonDefaults.buttonColors(
                containerColor = Color(0xFF9C5BFF),
                contentColor = Color.White,
            ),
        contentPadding = PaddingValues(horizontal = 14.dp, vertical = 6.dp),
    ) {
        Icon(
            imageVector = Icons.Rounded.Rocket,
            contentDescription = stringResource(R.string.explore_boost_shortcut_cd),
            modifier = Modifier.height(18.dp),
            tint = Color.White,
        )
        Spacer(Modifier.width(6.dp))
        Text(text = label, color = Color.White, fontWeight = FontWeight.SemiBold)
    }
}
