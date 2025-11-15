package com.ai.intellimate.utils

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.store.IntySetting
import com.ai.intellimate.testing.LogUtilsTestHelper
import io.mockk.every
import io.mockk.mockkObject
import io.mockk.unmockkObject
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class AgentCacheManagerTest {

    private val store = mutableMapOf<String, String?>()

    @Before
    fun setUp() {
        LogUtilsTestHelper.mock()
        mockkObject(IntySetting)
        every { IntySetting.setUserProfileData(any(), any()) } answers
            {
                store[firstArg()] = secondArg()
            }
        every { IntySetting.getUserProfileData(any()) } answers { store[firstArg()] }
    }

    @After
    fun tearDown() {
        store.clear()
        unmockkObject(IntySetting)
        LogUtilsTestHelper.unmock()
    }

    @Test
    fun cacheAgents_roundTripsRecommendedAgents() {
        val agents = listOf(agent("1"), agent("2"))

        AgentCacheManager.cacheAgents(agents)

        assertEquals(agents, AgentCacheManager.getCachedAgents())
    }

    @Test
    fun cacheChatAgents_roundTripsChatAgents() {
        val agents = listOf(agent("11"), agent("22"))

        AgentCacheManager.cacheChatAgents(agents)

        assertEquals(agents, AgentCacheManager.getCachedChatAgents())
    }

    @Test
    fun cacheUserCreatedAgents_roundTripsAgents() {
        val agents = listOf(agent("31"), agent("32"))

        AgentCacheManager.cacheUserCreatedAgents(agents)

        assertEquals(agents, AgentCacheManager.getCachedUserCreatedAgents())
    }

    @Test
    fun isCacheExpired_respectsThirtyMinuteWindow() {
        AgentCacheManager.cacheAgents(listOf(agent("40")))
        // 31分钟之前的时间戳
        store[KEY_RECOMMENDED_TIMESTAMP] =
            (System.currentTimeMillis() - 31 * 60 * 1000L).toString()

        assertTrue(AgentCacheManager.isCacheExpired())

        store[KEY_RECOMMENDED_TIMESTAMP] = System.currentTimeMillis().toString()
        assertFalse(AgentCacheManager.isCacheExpired())
    }

    @Test
    fun isUserCreatedCacheExpired_respectsThirtyMinuteWindow() {
        AgentCacheManager.cacheUserCreatedAgents(listOf(agent("50")))
        store[KEY_USER_CREATED_TIMESTAMP] =
            (System.currentTimeMillis() - 31 * 60 * 1000L).toString()

        assertTrue(AgentCacheManager.isUserCreatedCacheExpired())

        store[KEY_USER_CREATED_TIMESTAMP] = System.currentTimeMillis().toString()
        assertFalse(AgentCacheManager.isUserCreatedCacheExpired())
    }

    @Test
    fun removeAgent_updatesRecommendedAndUserCreatedCaches() {
        val target = agent("99")
        val remaining = agent("100")
        AgentCacheManager.cacheAgents(listOf(target, remaining))
        AgentCacheManager.cacheUserCreatedAgents(listOf(target, remaining))

        AgentCacheManager.removeAgent(target.id)

        assertEquals(listOf(remaining), AgentCacheManager.getCachedAgents())
        assertEquals(listOf(remaining), AgentCacheManager.getCachedUserCreatedAgents())
    }

    @Test
    fun clearCache_removesAllCachedData() {
        AgentCacheManager.cacheAgents(listOf(agent("1")))
        AgentCacheManager.cacheChatAgents(listOf(agent("2")))
        AgentCacheManager.cacheUserCreatedAgents(listOf(agent("3")))

        AgentCacheManager.clearCache()

        assertTrue(AgentCacheManager.getCachedAgents().isEmpty())
        assertTrue(AgentCacheManager.getCachedChatAgents().isEmpty())
        assertTrue(AgentCacheManager.getCachedUserCreatedAgents().isEmpty())
        assertTrue(AgentCacheManager.isCacheExpired())
        assertTrue(AgentCacheManager.isUserCreatedCacheExpired())
    }

    @Test
    fun getCacheStats_reportsCountsAndExpiry() {
        AgentCacheManager.cacheAgents(listOf(agent("k1")))
        AgentCacheManager.cacheChatAgents(listOf(agent("k2"), agent("k3")))
        store[KEY_RECOMMENDED_TIMESTAMP] =
            (System.currentTimeMillis() - 31 * 60 * 1000L).toString()

        val stats = AgentCacheManager.getCacheStats()

        assertEquals(1, stats.recommendedAgentsCount)
        assertEquals(2, stats.chatAgentsCount)
        assertTrue(stats.isExpired)
    }

    private fun agent(id: String) =
        AgentInfo(
            id = id,
            name = "Agent $id",
            avatar = "https://images/$id/avatar",
            background = "https://images/$id/background",
        )

    companion object {
        private const val KEY_RECOMMENDED_TIMESTAMP = "agents_cache_timestamp"
        private const val KEY_USER_CREATED_TIMESTAMP = "user_created_agents_cache_timestamp"
    }
}
