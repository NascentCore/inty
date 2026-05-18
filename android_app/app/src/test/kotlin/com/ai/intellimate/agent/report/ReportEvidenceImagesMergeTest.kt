// CREATED_BY_AGENT: gpt-5.3-codex-high
package com.ai.intellimate.agent.report

import org.junit.Assert.assertEquals
import org.junit.Test

class ReportEvidenceImagesMergeTest {
    @Test
    fun `filters blank values and de-duplicates image urls while preserving order`() {
        val result =
            mergeEvidenceImageUrls(
                remoteImages =
                    listOf("  https://cdn.example.com/evidence-initial.jpg  ", "", "   "),
                localImages =
                    listOf(
                        "content://media/external/images/media/42",
                        "https://cdn.example.com/evidence-initial.jpg",
                        " ",
                    ),
            )

        assertEquals(
            listOf(
                "https://cdn.example.com/evidence-initial.jpg",
                "content://media/external/images/media/42",
            ),
            result,
        )
    }
}
