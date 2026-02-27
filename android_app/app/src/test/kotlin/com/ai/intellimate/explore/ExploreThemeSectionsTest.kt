package com.ai.intellimate.explore

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.api.model.CharacterThemeAgentItem
import ai.sxwl.android.data.api.model.CharacterThemeItem
import ai.sxwl.android.data.api.model.CharacterThemeVisibility
import org.junit.Assert.assertEquals
import org.junit.Test

class ExploreThemeSectionsTest {

    @Test
    fun `buildExploreThemeSections - no newly agents keeps original themes`() {
        val themes =
            listOf(
                CharacterThemeItem(
                    id = "theme_1",
                    name = "Theme 1",
                    description = "desc",
                    visibility = CharacterThemeVisibility.PRIMARY,
                    agents =
                        listOf(
                            CharacterThemeAgentItem(
                                agentId = "a1",
                                orderIndex = 0,
                                agent = AgentInfo(id = "a1", name = "A1"),
                            )
                        ),
                )
            )

        val result =
            buildExploreThemeSections(
                characterThemes = themes,
                newlyCreatedAgents = emptyList(),
                newlyImatesTitle = "Newly iMates",
                newlyImatesSubtitle = "Newly crafted based on your preference",
            )

        assertEquals(1, result.size)
        assertEquals("theme_1", result.first().id)
        assertEquals("Theme 1", result.first().name)
        assertEquals(1, result.first().agents.size)
        assertEquals("a1", result.first().agents.first().id)
    }

    @Test
    fun `buildExploreThemeSections - prepends newly section and limits to ten`() {
        val themes =
            listOf(
                CharacterThemeItem(
                    id = "theme_1",
                    name = "Theme 1",
                    description = "desc",
                    visibility = CharacterThemeVisibility.PRIMARY,
                    agents =
                        listOf(
                            CharacterThemeAgentItem(
                                agentId = "a1",
                                orderIndex = 0,
                                agent = AgentInfo(id = "a1", name = "A1"),
                            )
                        ),
                )
            )
        val newlyAgents = (1..12).map { index -> AgentInfo(id = "new_$index", name = "New $index") }

        val result =
            buildExploreThemeSections(
                characterThemes = themes,
                newlyCreatedAgents = newlyAgents,
                newlyImatesTitle = "Newly iMates",
                newlyImatesSubtitle = "Newly crafted based on your preference",
            )

        val first = result.first()
        assertEquals(NEWLY_IMATES_THEME_ID, first.id)
        assertEquals("Newly iMates", first.name)
        assertEquals("Newly crafted based on your preference", first.description)
        assertEquals(10, first.agents.size)
        assertEquals("new_1", first.agents.first().id)
        assertEquals("new_10", first.agents.last().id)
        assertEquals(themes.first().id, result[1].id)
    }

    @Test
    fun `getExploreThemeClickSource - newly section returns dedicated source`() {
        assertEquals("newly_imates", getExploreThemeClickSource(NEWLY_IMATES_THEME_ID))
        assertEquals("theme", getExploreThemeClickSource("theme_x"))
    }
}
