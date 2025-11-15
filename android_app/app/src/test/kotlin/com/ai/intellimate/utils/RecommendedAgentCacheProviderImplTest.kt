package com.ai.intellimate.utils

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.store.IntySetting
import io.mockk.Runs
import io.mockk.every
import io.mockk.just
import io.mockk.mockkObject
import io.mockk.unmockkObject
import io.mockk.verify
import kotlinx.coroutines.test.runTest
import org.junit.After
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class RecommendedAgentCacheProviderImplTest {

    private val provider = RecommendedAgentCacheProviderImpl()

    @Before
    fun setUp() {
        mockkObject(AgentCacheManager)
        mockkObject(IntySetting)
        mockkObject(UnifiedStartupManager)
        every { UnifiedStartupManager.refreshRecommendedAgents() } just Runs
    }

    @After
    fun tearDown() {
        unmockkObject(AgentCacheManager)
        unmockkObject(IntySetting)
        unmockkObject(UnifiedStartupManager)
    }

    @Test
    fun shouldUpdateFromNetwork_returnsTrueWhenCacheMissingOrExpired() = runTest {
        every { AgentCacheManager.isCacheExpired() } returns true
        assertTrue(provider.shouldUpdateFromNetwork())

        every { AgentCacheManager.isCacheExpired() } returns false
        every { AgentCacheManager.getCachedAgents() } returns emptyList()
        assertTrue(provider.shouldUpdateFromNetwork())
    }

    @Test
    fun shouldUpdateFromNetwork_returnsFalseWhenCacheValidRegardlessLogin() = runTest {
        val cached = listOf(AgentInfo(id = "10"))
        every { AgentCacheManager.isCacheExpired() } returns false
        every { AgentCacheManager.getCachedAgents() } returns cached

        every { IntySetting.isLogin() } returns false
        assertFalse(provider.shouldUpdateFromNetwork())

        every { IntySetting.isLogin() } returns true
        assertFalse(provider.shouldUpdateFromNetwork())
    }

    @Test
    fun refreshRecommendedAgents_triggersUnifiedStartupManager() = runTest {
        provider.refreshRecommendedAgents()

        verify(exactly = 1) { UnifiedStartupManager.refreshRecommendedAgents() }
    }
}
