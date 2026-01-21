/*
 * CREATED_BY_AGENT
 */
package com.ai.intellimate.boost

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.utils.LogUtils
import android.content.Context
import java.time.LocalDate
import java.time.YearMonth
import java.time.ZoneId
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** 管理 Boost 相关的持久化状态与排行榜。 */
class BoostRepository(
    context: Context,
    private val seedProvider: BoostSeedProvider = BoostSeedProvider(),
    dispatcher: CoroutineDispatcher = Dispatchers.IO,
) {

    private val scope = CoroutineScope(SupervisorJob() + dispatcher)

    private val _state = MutableStateFlow(BoostState())
    val stateFlow: StateFlow<BoostState> = _state.asStateFlow()

    private val _leaderboard = MutableStateFlow<List<BoostLeaderboardEntry>>(emptyList())
    val leaderboardFlow: StateFlow<List<BoostLeaderboardEntry>> = _leaderboard.asStateFlow()

    init {
        // 执行每日重置检查
        scope.launch {
            // 加载初始状态
            val initialSnapshot = BoostStorage.getBoostState()
            _state.value = initialSnapshot.toDomain()
            _leaderboard.value = buildLeaderboard(initialSnapshot)
            runDailyResetIfNeeded()
        }
    }

    /** 更新状态流（在每次写入后调用） */
    private suspend fun updateStateFlows() {
        val snapshot = BoostStorage.getBoostState()
        _state.value = snapshot.toDomain()
        _leaderboard.value = buildLeaderboard(snapshot)
    }

    suspend fun addPoints(points: Int, source: PointSource) {
        if (points <= 0) return
        withContext(scope.coroutineContext) {
            val current = BoostStorage.getBoostState()
            val gain =
                when (source) {
                    PointSource.SignIn,
                    PointSource.Manual -> points
                    else -> BoostCalculator.clampDailyGain(current.dailyEnergyEarned, points)
                }
            if (gain > 0) {
                val updated =
                    current.copy(
                        availablePoints = current.availablePoints + gain,
                        dailyEnergyEarned = current.dailyEnergyEarned + gain,
                        chatMessagePoints =
                            if (source is PointSource.Chat) {
                                current.chatMessagePoints + gain
                            } else {
                                current.chatMessagePoints
                            },
                    )
                BoostStorage.saveBoostState(updated)
                updateStateFlows()
            }
        }
    }

    suspend fun claimDailyReward(): Int {
        return withContext(scope.coroutineContext) {
            val current = BoostStorage.getBoostState()
            if (current.hasClaimedDailyReward) {
                throw BoostException(BoostError.DailyRewardAlreadyClaimed)
            }
            val claimed = BoostConfig.DAILY_SIGN_IN_REWARD
            val updated =
                current.copy(
                    availablePoints = current.availablePoints + BoostConfig.DAILY_SIGN_IN_REWARD,
                    hasClaimedDailyReward = true,
                )
            BoostStorage.saveBoostState(updated)
            updateStateFlows()
            claimed
        }
    }

    /**
     * 领取订阅会员月度奖励。
     *
     * @return 领取的积分数量
     * @throws BoostException 如果当月已领取则抛出 [BoostError.MonthRewardAlreadyClaimed]
     */
    suspend fun claimMonthReward(): Int {
        return withContext(scope.coroutineContext) {

            var claimed = 0

            BoostStorage.update { current ->
                val currentMonth = YearMonth.now().toString()
                if (current.lastClaimedMonthReward != currentMonth) {
                    claimed = BoostConfig.MONTHLY_VIP_REWARD
                }

                current.copy(
                    availablePoints = current.availablePoints + claimed,
                    lastClaimedMonthReward = currentMonth,
                )
            }
            updateStateFlows()
            claimed
        }
    }

    suspend fun boostAgent(agentInfo: AgentInfo, points: Int): AgentBoostInfo {
        if (points <= 0 || points % BoostConfig.BOOST_STEP_POINTS != 0) {
            throw BoostException(BoostError.InvalidAmount)
        }
        return withContext(scope.coroutineContext) {
            val current = BoostStorage.getBoostState()
            if (current.availablePoints < points) {
                throw BoostException(BoostError.NotEnoughPoints)
            }
            val now = System.currentTimeMillis()
            val existing =
                current.boostsByAgent[agentInfo.id]
                    ?: AgentBoostInfoSnapshot(
                        agentId = agentInfo.id,
                        agentName = agentInfo.name,
                        avatarUrl = agentInfo.avatar,
                    )
            val merged =
                existing
                    .copy(agentName = agentInfo.name, avatarUrl = agentInfo.avatar)
                    .increment(points, now)

            val updated =
                current.copy(
                    availablePoints = current.availablePoints - points,
                    boostsByAgent = current.boostsByAgent + (agentInfo.id to merged),
                )
            BoostStorage.saveBoostState(updated)
            updateStateFlows()
            merged.toDomain()
        }
    }

    /**
     * 领取每日登录奖励（无需签到，自动发放）。
     *
     * @param isVip 是否为订阅用户，决定奖励数量
     * @return 领取的积分数量，如果当日已领取则返回 0
     */
    suspend fun claimDailyLoginReward(isVip: Boolean): Int {
        return withContext(scope.coroutineContext) {
            var claimed = 0
            val today = LocalDate.now(ZoneId.systemDefault()).toString()
            BoostStorage.update { current ->
                if (current.lastClaimedDailyLoginReward != today) {
                    claimed =
                        if (isVip) BoostConfig.DAILY_LOGIN_REWARD_VIP
                        else BoostConfig.DAILY_LOGIN_REWARD_FREE
                }
                current.copy(
                    availablePoints = current.availablePoints + claimed,
                    lastClaimedDailyLoginReward = today,
                )
            }
            updateStateFlows()
            claimed
        }
    }

    suspend fun runDailyResetIfNeeded() =
        withContext(scope.coroutineContext) {
            val today = LocalDate.now(ZoneId.systemDefault()).toString()
            runCatching {
                    val current = BoostStorage.getBoostState()
                    if (current.lastResetDate != today) {
                        val updated =
                            current.copy(
                                dailyEnergyEarned = 0,
                                hasClaimedDailyReward = false,
                                lastResetDate = today,
                            )
                        BoostStorage.saveBoostState(updated)
                        updateStateFlows()
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
            seedProvider.seeds(snapshot.boostsByAgent.keys).mapIndexed { index, entry ->
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
