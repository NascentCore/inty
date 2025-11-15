package com.ai.intellimate.utils

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.store.IntySetting
import io.mockk.every
import io.mockk.just
import io.mockk.mockkObject
import io.mockk.unmockkObject
import io.mockk.verify
import io.mockk.Runs
import kotlinx.coroutines.test.runTest
import org.junit.After
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class AgentCacheProviderImplTest {

    private val provider = AgentCacheProviderImpl()

    @Before
    fun setUp() {
        mockkObject(AgentCacheManager)
        mockkObject(IntySetting)
        mockkObject(UnifiedStartupManager)
        every { UnifiedStartupManager.refreshChatAgents() } just Runs
    }

    @After
    fun tearDown() {
        unmockkObject(AgentCacheManager)
        unmockkObject(IntySetting)
        unmockkObject(UnifiedStartupManager)
    }

    @Test
    fun shouldUpdateFromNetwork_returnsTrueWhenCacheExpired() = runTest {
        every { AgentCacheManager.isCacheExpired() } returns true

        assertTrue(provider.shouldUpdateFromNetwork())
    }

    @Test
    fun shouldUpdateFromNetwork_returnsTrueWhenCacheEmpty() = runTest {
        every { AgentCacheManager.isCacheExpired() } returns false
        every { AgentCacheManager.getCachedChatAgents() } returns emptyList()

        assertTrue(provider.shouldUpdateFromNetwork())
    }

    @Test
    fun shouldUpdateFromNetwork_respectsLoginState() = runTest {
        val cached = listOf(AgentInfo(id = "1"))
        every { AgentCacheManager.isCacheExpired() } returns false
        every { AgentCacheManager.getCachedChatAgents() } returns cached

        every { IntySetting.isLogin() } returns false
        assertFalse(provider.shouldUpdateFromNetwork())

        every { IntySetting.isLogin() } returns true
        assertFalse(provider.shouldUpdateFromNetwork())
    }

    @Test
    fun refreshChatAgents_triggersUnifiedStartupManager() = runTest {
        provider.refreshChatAgents()

        verify(exactly = 1) { UnifiedStartupManager.refreshChatAgents() }
    }
}
