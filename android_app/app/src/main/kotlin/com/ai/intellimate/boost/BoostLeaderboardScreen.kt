package com.ai.intellimate.boost

import ai.sxwl.android.data.http.ApiResult
import ai.sxwl.android.data.http.services.AgentService
import ai.sxwl.android.data.store.BoostLeaderboardRankCache
import ai.sxwl.android.data.store.BoostLeaderboardRankStore
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.HelpOutline
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.navigation.NavController
import com.ai.intellimate.R
import com.ai.intellimate.boost.ui.BoostLeaderboardTab
import com.ai.intellimate.boost.ui.BoostPointsHelpSheet
import com.ai.intellimate.chat.ChatActivity
import com.ai.intellimate.ui.components.EmptyStateComponent
import com.ai.intellimate.ui.components.EmptyStateType
import com.ai.intellimate.xb.helper.AgentStore
import com.ai.intellimate.xb.navigation.Routes

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BoostLeaderboardScreen(
    navController: NavController,
    onClick: (() -> Unit)? = null
) {
    val context = LocalContext.current
    val boostState by BoostManager.boostState.collectAsState()

    // 从后端获取排行榜数据
    var leaderboardEntries by remember { mutableStateOf<List<BoostLeaderboardEntry>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var retryTrigger by remember { mutableStateOf(0) }

    LaunchedEffect(retryTrigger) {
        isLoading = true
        errorMessage = null

        val previousCache = BoostLeaderboardRankStore.readCache(context)
        when (
            val result =
                AgentService.getRecommendAgents(
                    page = 1,
                    pageSize = 10,
                    sort = "energy_points",
                    sortSeed = "",
                )
        ) {
            is ApiResult.Success -> {
                val baseEntries =
                    result.data.mapIndexed { index, agent ->
                        val energyPoints = agent.energyPoints
                        // 使用 energyPoints / BOOST_STEP_POINTS 估算 boost 次数
                        val estimatedBoostCount =
                            if (energyPoints > 0) {
                                energyPoints / BoostConfig.BOOST_STEP_POINTS
                            } else {
                                0
                            }
                        BoostLeaderboardEntry(
                            rank = index + 1,
                            agentId = agent.id,
                            agentName = agent.name,
                            avatarUrl = agent.avatar,
                            boostCount = estimatedBoostCount,
                            pointsInvested = energyPoints,
                            trend = BoostTrend.FLAT,
                            isSeed = false,
                        )
                    }

                val entriesWithTrend =
                    BoostLeaderboardTrendCalculator.applyTrends(
                        entries = baseEntries,
                        previousRanksByAgentId = previousCache.ranksByAgentId,
                    )

                leaderboardEntries = entriesWithTrend
                BoostLeaderboardRankStore.saveCache(
                    context,
                    BoostLeaderboardRankCache(
                        updatedAtMs = System.currentTimeMillis(),
                        ranksByAgentId = BoostLeaderboardTrendCalculator.toRankMap(baseEntries),
                    ),
                )

                isLoading = false
            }
            is ApiResult.Error -> {
                errorMessage = result.message
                isLoading = false
            }
        }
    }

    val handleLeaderboardAction =
        remember(context) {
            { entry: BoostLeaderboardEntry, showSheet: Boolean ->
                navController.navigate(Routes.chatPage(entry.agentId, showSheet))
//                ChatActivity.launch(
//                    context,
//                    agentInfo = null,
//                    agentId = entry.agentId,
//                    pageSource = ChatActivity.EXPLORE_TAB,
//                    showBoostSheet = showSheet,
//                )
            }
        }
    var showHelpSheet by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            CenterAlignedTopAppBar(
                title = {
                    Text(
                        text = stringResource(R.string.boost_leaderboard_title),
                        color = Color.White,
                    )
                },
                navigationIcon = {
                    IconButton(onClick = {
                        navController.popBackStack()
                    }) {
                        Icon(
                            painter = painterResource(R.drawable.back),
                            contentDescription = stringResource(R.string.boost_leaderboard_back_cd),
                            tint = Color.White,
                        )
                    }
                },
                actions = {
                    IconButton(
                        onClick = { showHelpSheet = true}
                    ) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Outlined.HelpOutline,
                            contentDescription = "help",
                            tint = Color.White
                        )
                    }
                },
                colors =
                    TopAppBarDefaults.centerAlignedTopAppBarColors(
                        containerColor = Color.Transparent
                    ),
            )
        }
    ) { innerPadding ->
        when {
            isLoading -> {
                Box(
                    modifier = Modifier.padding(innerPadding).fillMaxSize(),
                    contentAlignment = Alignment.Center,
                ) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(24.dp),
                        color = Color.White.copy(alpha = 0.7f),
                    )
                }
            }
            errorMessage != null -> {
                EmptyStateComponent(
                    type = EmptyStateType.NETWORK_ERROR,
                    title = stringResource(R.string.empty_explore_error),
                    showRetryButton = true,
                    onRetry = { retryTrigger++ },
                    modifier = Modifier.padding(innerPadding).fillMaxSize(),
                )
            }
            else -> {
                BoostLeaderboardTab(
                    navController,
                    modifier = Modifier.padding(innerPadding).fillMaxSize(),
                    availablePoints = boostState.availablePoints,
                    entries = leaderboardEntries,
                    onChat = { handleLeaderboardAction(it, false) },
                    onBoost = { handleLeaderboardAction(it, true) },
                )
            }
        }
    }

    if (showHelpSheet) {
        BoostPointsHelpSheet(
            availablePoints = boostState.availablePoints,
            onDismiss = { showHelpSheet = false },
            onOpenLeaderboard = {
                showHelpSheet = false
                BoostLeaderboardActivity.launch(context)
            },
        )
    }
}