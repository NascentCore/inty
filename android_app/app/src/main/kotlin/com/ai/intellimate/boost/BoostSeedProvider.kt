/*
 * CREATED_BY_AGENT
 */
package com.ai.intellimate.boost

/** 本地假数据，方便在 Explore 子 Tab 展示排行榜占位。 */
class BoostSeedProvider {

    private val seeds =
        listOf(
            Seed(
                agentId = "aurora_star",
                agentName = "Aurora Starfall",
                boostCount = 640,
                trend = BoostTrend.UP,
            ),
            Seed(
                agentId = "midnight_rain",
                agentName = "Midnight Rain",
                boostCount = 590,
                trend = BoostTrend.FLAT,
            ),
            Seed(
                agentId = "akira_wave",
                agentName = "Akira Wave",
                boostCount = 520,
                trend = BoostTrend.UP,
            ),
            Seed(
                agentId = "scarlett_fox",
                agentName = "Scarlett Fox",
                boostCount = 440,
                trend = BoostTrend.DOWN,
            ),
            Seed(
                agentId = "noah_companion",
                agentName = "Noah Companion",
                boostCount = 420,
                trend = BoostTrend.UP,
            ),
            Seed(
                agentId = "echo_dream",
                agentName = "Echo Dreamer",
                boostCount = 380,
                trend = BoostTrend.FLAT,
            ),
            Seed(
                agentId = "ivy_muse",
                agentName = "Ivy Muse",
                boostCount = 360,
                trend = BoostTrend.UP,
            ),
            Seed(
                agentId = "sage_warm",
                agentName = "Sage Warmth",
                boostCount = 340,
                trend = BoostTrend.FLAT,
            ),
        )

    fun seeds(excludedIds: Set<String>): List<BoostLeaderboardEntry> {
        return seeds
            .filterNot { excludedIds.contains(it.agentId) }
            .mapIndexed { index, seed ->
                BoostLeaderboardEntry(
                    rank = index + 1,
                    agentId = seed.agentId,
                    agentName = seed.agentName,
                    avatarUrl = seed.avatarUrl,
                    boostCount = seed.boostCount,
                    pointsInvested = seed.boostCount * BoostConfig.BOOST_STEP_POINTS,
                    trend = seed.trend,
                    isSeed = true,
                )
            }
    }

    private data class Seed(
        val agentId: String,
        val agentName: String,
        val avatarUrl: String? = null,
        val boostCount: Int,
        val trend: BoostTrend,
    )
}
