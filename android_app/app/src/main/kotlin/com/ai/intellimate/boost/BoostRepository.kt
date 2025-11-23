/*
 * CREATED_BY_AGENT
 */
package com.ai.intellimate.boost

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.utils.LogUtils
import android.content.Context
import java.time.LocalDate
import java.time.ZoneId
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** 管理 Boost 相关的持久化状态与排行榜。 */
class BoostRepository(
    context: Context,
    private val seedProvider: BoostSeedProvider = BoostSeedProvider(),
    dispatcher: CoroutineDispatcher = Dispatchers.IO,
) {

    private val scope = CoroutineScope(SupervisorJob() + dispatcher)
    private val dataStore = context.applicationContext.boostStateDataStore

    private val _state = MutableStateFlow(BoostState())
    val stateFlow: StateFlow<BoostState> = _state.asStateFlow()

    private val _leaderboard = MutableStateFlow<List<BoostLeaderboardEntry>>(emptyList())
    val leaderboardFlow: StateFlow<List<BoostLeaderboardEntry>> = _leaderboard.asStateFlow()

    init {
        scope.launch { runDailyResetIfNeeded() }
        scope.launch {
            dataStore.data.collectLatest { snapshot ->
                _state.value = snapshot.toDomain()
                _leaderboard.value = buildLeaderboard(snapshot)
            }
        }
    }

    suspend fun addPoints(points: Int, source: PointSource) {
        if (points <= 0) return
        dataStore.updateData { snapshot ->
            val gain =
                when (source) {
                    PointSource.SignIn, PointSource.Manual -> points
                    else -> BoostCalculator.clampDailyGain(snapshot.dailyEnergyEarned, points)
                }
            if (gain <= 0) {
                snapshot
            } else {
                snapshot.copy(
                    availablePoints = snapshot.availablePoints + gain,
                    dailyEnergyEarned = snapshot.dailyEnergyEarned + gain,
                )
            }
        }
    }

    suspend fun claimDailyReward(): Int {
        var claimed = 0
        dataStore.updateData { snapshot ->
            if (snapshot.hasClaimedDailyReward) {
                throw BoostException(BoostError.DailyRewardAlreadyClaimed)
            }
            claimed = BoostConfig.DAILY_SIGN_IN_REWARD
            snapshot.copy(
                availablePoints = snapshot.availablePoints + BoostConfig.DAILY_SIGN_IN_REWARD,
                hasClaimedDailyReward = true,
            )
        }
        return claimed
    }

    suspend fun boostAgent(agentInfo: AgentInfo, points: Int): AgentBoostInfo {
        if (points <= 0 || points % BoostConfig.BOOST_STEP_POINTS != 0) {
            throw BoostException(BoostError.InvalidAmount)
        }
        var updatedInfo: AgentBoostInfoSnapshot? = null
        dataStore.updateData { snapshot ->
            if (snapshot.availablePoints < points) throw BoostException(BoostError.NotEnoughPoints)
            val now = System.currentTimeMillis()
            val existing =
                snapshot.boostsByAgent[agentInfo.id]
                    ?: AgentBoostInfoSnapshot(
                        agentId = agentInfo.id,
                        agentName = agentInfo.name,
                        avatarUrl = agentInfo.avatar,
                    )
            val merged =
                existing
                    .copy(agentName = agentInfo.name, avatarUrl = agentInfo.avatar)
                    .increment(points, now)

            updatedInfo = merged

            snapshot.copy(
                availablePoints = snapshot.availablePoints - points,
                boostsByAgent = snapshot.boostsByAgent + (agentInfo.id to merged),
            )
        }
        return checkNotNull(updatedInfo).toDomain()
    }

    suspend fun runDailyResetIfNeeded() =
        withContext(scope.coroutineContext) {
            val today = LocalDate.now(ZoneId.systemDefault()).toString()
            runCatching {
                    dataStore.updateData { snapshot ->
                        if (snapshot.lastResetDate == today) {
                            snapshot
                        } else {
                            snapshot.copy(
                                dailyEnergyEarned = 0,
                                hasClaimedDailyReward = false,
                                lastResetDate = today,
                            )
                        }
                    }
                }
                .onFailure { LogUtils.e("BoostRepository", "Daily reset failed: ${it.message}") }
        }

    private fun buildLeaderboard(snapshot: BoostStateSnapshot): List<BoostLeaderboardEntry> {
        val actual =
            snapshot.boostsByAgent.values
                .filter { it.boostCount > 0 }
                .sortedByDescending { it.boostCount }
                .mapIndexed { index, info ->
                    BoostLeaderboardEntry(
                        rank = index + 1,
                        agentId = info.agentId,
                        agentName = info.agentName,
                        avatarUrl = info.avatarUrl,
                        boostCount = info.boostCount,
                        pointsInvested = info.pointsInvested,
                        trend = BoostTrend.UP,
                        isSeed = false,
                    )
                }

        val seeds =
            seedProvider
                .seeds(snapshot.boostsByAgent.keys)
                .mapIndexed { index, entry ->
                    entry.copy(rank = actual.size + index + 1)
                }

        return (actual + seeds)
            .sortedWith(
                compareByDescending<BoostLeaderboardEntry> { it.boostCount }.thenBy { it.agentName }
            )
            .take(BoostConfig.LEADERBOARD_LIMIT)
            .mapIndexed { index, entry -> entry.copy(rank = index + 1) }
    }
}
