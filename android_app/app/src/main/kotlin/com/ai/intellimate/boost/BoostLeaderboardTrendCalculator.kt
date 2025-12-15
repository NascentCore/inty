package com.ai.intellimate.boost

// CREATED_BY_AGENT

internal object BoostLeaderboardTrendCalculator {

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

    fun toRankMap(entries: List<BoostLeaderboardEntry>): Map<String, Int> {
        if (entries.isEmpty()) return emptyMap()
        return entries.associate { it.agentId to it.rank }
    }

    private fun compareRank(currentRank: Int, previousRank: Int?): BoostTrend {
        if (previousRank == null) return BoostTrend.FLAT
        return when {
            currentRank < previousRank -> BoostTrend.UP
            currentRank > previousRank -> BoostTrend.DOWN
            else -> BoostTrend.FLAT
        }
    }
}

