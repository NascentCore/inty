package com.ai.intellimate.boost

// CREATED_BY_AGENT

/**
 * 排行榜趋势计算器。
 *
 * 用户在查看排行榜时，可以看到每个角色的排名变化趋势（上升、下降或持平）。 该功能通过比较当前排名和上次保存的排名来确定趋势：
 * - 排名数字越小越好（第1名最佳）
 * - 当前排名 < 之前排名 → 排名上升（UP），显示绿色上升箭头
 * - 当前排名 > 之前排名 → 排名下降（DOWN），显示红色下降箭头
 * - 排名相同或无历史记录 → 持平（FLAT），显示灰色标识
 */
internal object BoostLeaderboardTrendCalculator {

    /**
     * 为排行榜条目添加趋势信息。
     *
     * 用户每次打开排行榜时，系统会比较当前排名和上次保存的排名， 为每个角色计算并显示排名变化趋势，帮助用户了解角色的排名动态。
     */
    fun applyTrends(
        entries: List<BoostLeaderboardEntry>,
        previousRanksByAgentId: Map<String, Int>,
    ): List<BoostLeaderboardEntry> {
        if (entries.isEmpty()) return entries
        return entries.map { entry ->
            val previousRank = previousRanksByAgentId[entry.agentId]
            entry.copy(trend = compareRank(currentRank = entry.rank, previousRank = previousRank))
        }
    }

    /**
     * 将排行榜条目转换为角色ID到排名的映射，用于保存当前排名快照。
     *
     * 用户查看排行榜后，系统会保存当前排名信息，以便下次打开时计算趋势。 该映射会被持久化存储，作为下次比较的基准。
     */
    fun toRankMap(entries: List<BoostLeaderboardEntry>): Map<String, Int> {
        if (entries.isEmpty()) return emptyMap()
        return entries.associate { it.agentId to it.rank }
    }

    /**
     * 比较当前排名和之前排名，返回趋势类型。
     *
     * 排名数字越小表示排名越靠前，因此：
     * - 当前排名数字更小 → 排名上升（UP）
     * - 当前排名数字更大 → 排名下降（DOWN）
     * - 排名相同或无历史记录 → 持平（FLAT）
     */
    private fun compareRank(currentRank: Int, previousRank: Int?): BoostTrend {
        if (previousRank == null) return BoostTrend.FLAT
        return when {
            currentRank < previousRank -> BoostTrend.UP
            currentRank > previousRank -> BoostTrend.DOWN
            else -> BoostTrend.FLAT
        }
    }
}
