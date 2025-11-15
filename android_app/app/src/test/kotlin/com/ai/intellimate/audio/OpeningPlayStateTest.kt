package com.ai.intellimate.audio

import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.withTimeout
import org.junit.After
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class OpeningPlayStateTest {

    @Before
    fun setUp() = runBlocking { OpeningPlayState.clearAllPlayed() }

    @After
    fun tearDown() = runBlocking { OpeningPlayState.clearAllPlayed() }

    @OptIn(ExperimentalCoroutinesApi::class)
    @Test
    fun openingPlayed_marksAgentAndClearAgentResets() = runTest {
        val agentId = "agent-1"

        assertFalse(OpeningPlayState.agentOpeningPlayed(agentId))

        OpeningPlayState.openingPlayed(agentId)
        assertTrue(OpeningPlayState.agentOpeningPlayed(agentId))

        OpeningPlayState.clearAgentPlayed(agentId)
        assertFalse(OpeningPlayState.agentOpeningPlayed(agentId))
    }

    @Test
    fun openingPlayedAsync_recordsAgentWithoutBlockingCaller() = runBlocking {
        val agentId = "agent-async"

        OpeningPlayState.openingPlayedAsync(agentId)

        withTimeout(1_000) {
            while (!OpeningPlayState.agentOpeningPlayed(agentId)) {
                delay(10)
            }
        }

        assertTrue(OpeningPlayState.agentOpeningPlayed(agentId))
    }

    @OptIn(ExperimentalCoroutinesApi::class)
    @Test
    fun clearAllPlayed_removesEveryAgentRecord() = runTest {
        val firstAgent = "agent-a"
        val secondAgent = "agent-b"

        OpeningPlayState.openingPlayed(firstAgent)
        OpeningPlayState.openingPlayed(secondAgent)
        assertTrue(OpeningPlayState.agentOpeningPlayed(firstAgent))
        assertTrue(OpeningPlayState.agentOpeningPlayed(secondAgent))

        OpeningPlayState.clearAllPlayed()

        assertFalse(OpeningPlayState.agentOpeningPlayed(firstAgent))
        assertFalse(OpeningPlayState.agentOpeningPlayed(secondAgent))
    }

    @Test
    fun openingPlayedAsync_handlesConcurrentInvocations() = runBlocking {
        val agentIds = (0 until 20).map { "agent-$it" }

        coroutineScope {
            agentIds.forEach { id ->
                launch { OpeningPlayState.openingPlayedAsync(id) }
            }
        }

        withTimeout(1_000) {
            while (agentIds.any { !OpeningPlayState.agentOpeningPlayed(it) }) {
                delay(10)
            }
        }

        agentIds.forEach { id -> assertTrue(OpeningPlayState.agentOpeningPlayed(id)) }
    }
}
