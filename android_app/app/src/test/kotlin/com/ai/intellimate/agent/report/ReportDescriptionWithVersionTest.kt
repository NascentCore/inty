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
                agentId = "",
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
                agentId = "",
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
                agentId = "",
            )

        assertEquals("desc\n\n--- [INTY_APP_VERSION] ---\nApp版本：1.0.0 (1)", result)
    }

    @Test
    fun `appends agent id block when agent id provided`() {
        val result =
            buildReportDescriptionWithAppVersion(
                userDescription = "desc",
                versionName = "1.0.0",
                versionCode = 1,
                agentId = "agent-123",
            )

        assertEquals(
            "desc\n\n--- [INTY_APP_VERSION] ---\nApp版本：1.0.0 (1)\n--- [INTY_AGENT_ID] ---\nAgent ID: agent-123",
            result,
        )
    }

    @Test
    fun `appends only agent block when app marker already present`() {
        val input = "desc\n\n--- [INTY_APP_VERSION] ---\nApp版本：1.0.0 (1)"
        val result =
            buildReportDescriptionWithAppVersion(
                userDescription = input,
                versionName = "9.9.9",
                versionCode = 999,
                agentId = "agent-456",
            )

        assertEquals(
            "desc\n\n--- [INTY_APP_VERSION] ---\nApp版本：1.0.0 (1)\n\n--- [INTY_AGENT_ID] ---\nAgent ID: agent-456",
            result,
        )
    }

    @Test
    fun `does not append agent id twice when marker already exists`() {
        val input =
            "desc\n\n--- [INTY_APP_VERSION] ---\nApp版本：1.0.0 (1)\n--- [INTY_AGENT_ID] ---\nAgent ID: agent-1"
        val result =
            buildReportDescriptionWithAppVersion(
                userDescription = input,
                versionName = "9.9.9",
                versionCode = 999,
                agentId = "agent-2",
            )

        assertEquals(input, result)
    }
}
