/*
 * CREATED_BY_AGENT
 */
package com.ai.intellimate.boost

import kotlinx.serialization.Serializable

/** MMKV 中的原始快照，用于序列化存储。 */
@Serializable
data class BoostStateSnapshot(
    val availablePoints: Int = 0,
    val chatMessagePoints: Int = 0,
    val dailyEnergyEarned: Int = 0,
    val hasClaimedDailyReward: Boolean = false,
    val lastResetDate: String = "",
    val boostsByAgent: Map<String, AgentBoostInfoSnapshot> = emptyMap(),
    /** 上次领取每日登录奖励的日期，格式为 "yyyy-MM-dd"，用于判断当日是否已领取。 */
    val lastClaimedDailyLoginReward: String = "",
    /** 上次领取月度奖励的月份，格式为 "yyyy-MM"，用于判断当月是否已领取。 */
    val lastClaimedMonthReward: String = "",
)

/** 单个角色在 MMKV 中的快照。 */
@Serializable
data class AgentBoostInfoSnapshot(
    val agentId: String = "",
    val agentName: String = "",
    val avatarUrl: String? = null,
    val pointsInvested: Int = 0,
    val boostCount: Int = 0,
    val lastBoostedAt: Long = 0,
)

/** 面向 UI 的 Boost 状态。 */
data class BoostState(
    val availablePoints: Int = 0,
    val chatMessagePoints: Int = 0,
    val dailyEnergyEarned: Int = 0,
    val hasClaimedDailyReward: Boolean = false,
    /** 当日是否已领取每日登录奖励。 */
    val hasClaimedDailyLoginReward: Boolean = false,
    val boostsByAgent: Map<String, AgentBoostInfo> = emptyMap(),
    val lastResetDate: String = "",
    /** 当月是否已领取月度奖励。 */
    val hasClaimedMonthReward: Boolean = false,
)

/** 面向 UI 的单个角色 Boost 信息。 */
data class AgentBoostInfo(
    val agentId: String,
    val agentName: String,
    val avatarUrl: String?,
    val boostCount: Int,
    val pointsInvested: Int,
    val lastBoostedAt: Long,
    val trend: BoostTrend = BoostTrend.FLAT,
    val isLocal: Boolean = true,
)

/** 排行榜条目，统一用于 Explore 子 Tab 展示。 */
data class BoostLeaderboardEntry(
    val rank: Int,
    val agentId: String,
    val agentName: String,
    val avatarUrl: String?,
    val boostCount: Int,
    val pointsInvested: Int,
    val trend: BoostTrend,
    val isSeed: Boolean,
)

/** 记录积分来源，方便事件与 UI 展示。 */
sealed class PointSource(val analyticsName: String) {
    data class Chat(val agentId: String) : PointSource("chat")

    data class Image(val agentId: String) : PointSource("image")

    data class Audio(val agentId: String) : PointSource("audio")

    object SignIn : PointSource("sign_in")

    object DailyLogin : PointSource("daily_login")

    object MonthlyVip : PointSource("monthly_vip")

    object Manual : PointSource("manual")

    object ForMoment : PointSource("for_moment")
}

/** Boost 功能相关的错误类型。 */
sealed class BoostError {
    data object NotEnoughPoints : BoostError()

    data object DailyRewardAlreadyClaimed : BoostError()

    data object MonthRewardAlreadyClaimed : BoostError()

    data object InvalidAmount : BoostError()

    data object NotInitialized : BoostError()
}

data class BoostResult(val info: AgentBoostInfo, val pointsSpent: Int)

class BoostException(val error: BoostError) : IllegalStateException(error.toString())

internal fun BoostStateSnapshot.toDomain(): BoostState {
    val today = java.time.LocalDate.now().toString()
    val currentMonth = java.time.YearMonth.now().toString()
    return BoostState(
        availablePoints = availablePoints,
        chatMessagePoints = chatMessagePoints,
        dailyEnergyEarned = dailyEnergyEarned,
        hasClaimedDailyReward = hasClaimedDailyReward,
        hasClaimedDailyLoginReward = lastClaimedDailyLoginReward == today,
        boostsByAgent = boostsByAgent.mapValues { it.value.toDomain() },
        lastResetDate = lastResetDate,
        hasClaimedMonthReward = lastClaimedMonthReward == currentMonth,
    )
}

internal fun AgentBoostInfoSnapshot.toDomain(): AgentBoostInfo {
    return AgentBoostInfo(
        agentId = agentId,
        agentName = agentName,
        avatarUrl = avatarUrl,
        boostCount = boostCount,
        pointsInvested = pointsInvested,
        lastBoostedAt = lastBoostedAt,
        trend = BoostTrend.UP,
        isLocal = true,
    )
}

internal fun AgentBoostInfo.toSnapshot(): AgentBoostInfoSnapshot {
    return AgentBoostInfoSnapshot(
        agentId = agentId,
        agentName = agentName,
        avatarUrl = avatarUrl,
        boostCount = boostCount,
        pointsInvested = pointsInvested,
        lastBoostedAt = lastBoostedAt,
    )
}

internal fun AgentBoostInfoSnapshot.increment(
    points: Int,
    timestamp: Long,
): AgentBoostInfoSnapshot {
    val additionalBoosts = points / BoostConfig.BOOST_STEP_POINTS
    return copy(
        pointsInvested = pointsInvested + points,
        boostCount = boostCount + additionalBoosts,
        lastBoostedAt = timestamp,
    )
}
