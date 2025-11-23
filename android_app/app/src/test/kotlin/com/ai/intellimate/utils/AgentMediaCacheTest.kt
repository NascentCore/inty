package com.ai.intellimate.utils

import ai.sxwl.android.data.api.model.AgentInfo
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

// CREATED_BY_AGENT

class AgentMediaCacheTest {

    @Before
    fun setUp() {
        AgentMediaCache.clear()
    }

    @After
    fun tearDown() {
        AgentMediaCache.clear()
    }

    @Test
    fun `image cache prevents duplicate preloads`() {
        val agent = createAgent(id = "agent-image", background = "https://images.sxwl.dev/inty-static/bg.jpg")

        val firstBatch = AgentMediaCache.filterAgentsNeedingImages(listOf(agent))
        assertEquals(1, firstBatch.size)

        AgentMediaCache.markImagesCached(listOf(agent))
        val secondBatch = AgentMediaCache.filterAgentsNeedingImages(listOf(agent))
        assertTrue(secondBatch.isEmpty())
    }

    @Test
    fun `audio cache tracks both opening and preview`() {
        val agent =
            createAgent(
                id = "agent-audio",
                openingAudio = "https://cdn.inty.ai/opening.opus",
                voicePreview = "https://cdn.inty.ai/preview.opus",
            )

        val pending = AgentMediaCache.filterAgentsNeedingOpeningAudios(listOf(agent))
        assertEquals(1, pending.size)

        AgentMediaCache.markOpeningAudiosCached(listOf(agent))
        val nextRound = AgentMediaCache.filterAgentsNeedingOpeningAudios(listOf(agent))
        assertTrue(nextRound.isEmpty())
    }

    @Test
    fun `video cache resets after clear`() {
        val agent =
            createAgent(
                id = "agent-video",
                backgroundAnimated = "https://cdn.inty.ai/video.mp4",
            )

        assertEquals(1, AgentMediaCache.filterAgentsNeedingBackgroundVideos(listOf(agent)).size)
        AgentMediaCache.markBackgroundVideosCached(listOf(agent))
        assertTrue(AgentMediaCache.filterAgentsNeedingBackgroundVideos(listOf(agent)).isEmpty())

        AgentMediaCache.clear()
        assertEquals(1, AgentMediaCache.filterAgentsNeedingBackgroundVideos(listOf(agent)).size)
    }

    private fun createAgent(
        id: String,
        background: String = "",
        openingAudio: String = "",
        voicePreview: String = "",
        backgroundAnimated: String = "",
    ): AgentInfo {
        return AgentInfo(
            id = id,
            background = background,
            opening_audio_url = openingAudio,
            voicePreview = voicePreview,
            backgroundAnimatedUrl = backgroundAnimated,
        )
    }
}
