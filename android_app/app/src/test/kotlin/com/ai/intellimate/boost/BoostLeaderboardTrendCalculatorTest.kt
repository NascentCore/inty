package com.ai.intellimate.boost

// CREATED_BY_AGENT

import org.junit.Assert.assertEquals
import org.junit.Test

class BoostLeaderboardTrendCalculatorTest {

    @Test
    fun `applyTrends - unchanged rank is FLAT`() {
        val previous = mapOf("a" to 1)
        val current =
            listOf(
                BoostLeaderboardEntry(
                    rank = 1,
                    agentId = "a",
                    agentName = "A",
                    avatarUrl = null,
                    boostCount = 0,
                    pointsInvested = 100,
                    trend = BoostTrend.FLAT,
                    isSeed = false,
                )
            )

        val trended = BoostLeaderboardTrendCalculator.applyTrends(current, previous)
        assertEquals(BoostTrend.FLAT, trended.single().trend)
    }

    @Test
    fun `applyTrends - rank improved is UP`() {
        val previous = mapOf("a" to 5)
        val current =
            listOf(
                BoostLeaderboardEntry(
                    rank = 2,
                    agentId = "a",
                    agentName = "A",
                    avatarUrl = null,
                    boostCount = 0,
                    pointsInvested = 100,
                    trend = BoostTrend.FLAT,
                    isSeed = false,
                )
            )

        val trended = BoostLeaderboardTrendCalculator.applyTrends(current, previous)
        assertEquals(BoostTrend.UP, trended.single().trend)
    }

    @Test
    fun `applyTrends - rank worsened is DOWN`() {
        val previous = mapOf("a" to 2)
        val current =
            listOf(
                BoostLeaderboardEntry(
                    rank = 6,
                    agentId = "a",
                    agentName = "A",
                    avatarUrl = null,
                    boostCount = 0,
                    pointsInvested = 100,
                    trend = BoostTrend.FLAT,
                    isSeed = false,
                )
            )

        val trended = BoostLeaderboardTrendCalculator.applyTrends(current, previous)
        assertEquals(BoostTrend.DOWN, trended.single().trend)
    }

    @Test
    fun `applyTrends - agent not in cache is FLAT`() {
        val previous = emptyMap<String, Int>()
        val current =
            listOf(
                BoostLeaderboardEntry(
                    rank = 1,
                    agentId = "new",
                    agentName = "New",
                    avatarUrl = null,
                    boostCount = 0,
                    pointsInvested = 100,
                    trend = BoostTrend.UP,
                    isSeed = false,
                )
            )

        val trended = BoostLeaderboardTrendCalculator.applyTrends(current, previous)
        assertEquals(BoostTrend.FLAT, trended.single().trend)
    }

    @Test
    fun `toRankMap - maps agentId to rank`() {
        val entries =
            listOf(
                BoostLeaderboardEntry(
                    rank = 3,
                    agentId = "a",
                    agentName = "A",
                    avatarUrl = null,
                    boostCount = 0,
                    pointsInvested = 100,
                    trend = BoostTrend.FLAT,
                    isSeed = false,
                ),
                BoostLeaderboardEntry(
                    rank = 1,
                    agentId = "b",
                    agentName = "B",
                    avatarUrl = null,
                    boostCount = 0,
                    pointsInvested = 100,
                    trend = BoostTrend.FLAT,
                    isSeed = false,
                ),
            )

        assertEquals(mapOf("a" to 3, "b" to 1), BoostLeaderboardTrendCalculator.toRankMap(entries))
    }
}

