// CREATED_BY_AGENT: GPT-5.2
package com.ai.intellimate.agent.report

import org.junit.Assert.assertEquals
import org.junit.Test

class ReportDescriptionWithVersionTest {
    @Test
    fun `appends app version block after user description`() {
        val result =
            buildReportDescriptionWithAppVersion(
                userDescription = "用户输入的描述",
                versionName = "1.2.3",
                versionCode = 123,
            )

        assertEquals("用户输入的描述\n\n--- [INTY_APP_VERSION] ---\nApp版本：1.2.3 (123)", result)
    }

    @Test
    fun `does not append twice when marker already present`() {
        val input = "desc\n\n--- [INTY_APP_VERSION] ---\nApp版本：1.0.0 (1)"
        val result =
            buildReportDescriptionWithAppVersion(
                userDescription = input,
                versionName = "9.9.9",
                versionCode = 999,
            )

        assertEquals(input, result)
    }

    @Test
    fun `keeps a single extra newline when description already ends with newline`() {
        val result =
            buildReportDescriptionWithAppVersion(
                userDescription = "desc\n",
                versionName = "1.0.0",
                versionCode = 1,
            )

        assertEquals("desc\n\n--- [INTY_APP_VERSION] ---\nApp版本：1.0.0 (1)", result)
    }
}
