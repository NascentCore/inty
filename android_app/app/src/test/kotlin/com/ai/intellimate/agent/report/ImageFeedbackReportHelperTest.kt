// CREATED_BY_AGENT: gpt-5.3-codex-high
package com.ai.intellimate.agent.report

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ImageFeedbackReportHelperTest {
    @Test
    fun `buildImageFeedbackTargetId keeps stable hash for same image url`() {
        val imageUrl = "https://cdn.example.com/chat_images/abc.jpg"
        val first = buildImageFeedbackTargetId(imageUrl)
        val second = buildImageFeedbackTargetId(imageUrl)

        assertEquals(first, second)
        assertTrue(first.startsWith(IMAGE_FEEDBACK_TARGET_PREFIX))
        assertTrue(first.length <= 100)
    }

    @Test
    fun `buildImageFeedbackDescription adds image marker and vote marker`() {
        val description =
            buildImageFeedbackDescription(
                userDescription = "looks weird around hands",
                vote = "dislike",
            )

        assertEquals("[IMAGE_FEEDBACK][vote=dislike] looks weird around hands", description)
    }

    @Test
    fun `normalizeImageFeedbackVote only accepts like and dislike`() {
        assertEquals("like", normalizeImageFeedbackVote("LIKE"))
        assertEquals("dislike", normalizeImageFeedbackVote(" dislike "))
        assertEquals(null, normalizeImageFeedbackVote("good"))
    }
}
