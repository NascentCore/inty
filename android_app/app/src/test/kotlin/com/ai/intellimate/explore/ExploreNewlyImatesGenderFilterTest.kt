package com.ai.intellimate.explore

import ai.sxwl.android.data.api.model.AgentInfo
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ExploreNewlyImatesGenderFilterTest {
    @Test
    fun `filterNewlyCreatedAgentsByUserGender - male user keeps only female agents`() {
        val agents =
            listOf(
                AgentInfo(id = "female_1", gender = "FEMALE"),
                AgentInfo(id = "male_1", gender = "MALE"),
                AgentInfo(id = "female_2", gender = "female"),
                AgentInfo(id = "other_1", gender = "OTHER"),
            )

        val filtered = filterNewlyCreatedAgentsByUserGender(agents = agents, userGender = "MALE")

        assertEquals(listOf("female_1", "female_2"), filtered.map { it.id })
    }

    @Test
    fun `filterNewlyCreatedAgentsByUserGender - female user keeps only male agents`() {
        val agents =
            listOf(
                AgentInfo(id = "female_1", gender = "FEMALE"),
                AgentInfo(id = "male_1", gender = "MALE"),
                AgentInfo(id = "male_2", gender = "Male"),
                AgentInfo(id = "unknown_1", gender = ""),
            )

        val filtered = filterNewlyCreatedAgentsByUserGender(agents = agents, userGender = "female")

        assertEquals(listOf("male_1", "male_2"), filtered.map { it.id })
    }

    @Test
    fun `filterNewlyCreatedAgentsByUserGender - other and non binary keep current logic`() {
        val agents =
            listOf(
                AgentInfo(id = "female_1", gender = "FEMALE"),
                AgentInfo(id = "male_1", gender = "MALE"),
                AgentInfo(id = "other_1", gender = "OTHER"),
            )

        val filteredForOther =
            filterNewlyCreatedAgentsByUserGender(agents = agents, userGender = "OTHER")
        val filteredForNonBinary =
            filterNewlyCreatedAgentsByUserGender(agents = agents, userGender = "non-binary")

        assertEquals(agents.map { it.id }, filteredForOther.map { it.id })
        assertEquals(agents.map { it.id }, filteredForNonBinary.map { it.id })
    }

    @Test
    fun `shouldUseOppositeGenderFilter - only male and female return true`() {
        assertTrue(shouldUseOppositeGenderFilter("MALE"))
        assertTrue(shouldUseOppositeGenderFilter("female"))
        assertFalse(shouldUseOppositeGenderFilter("OTHER"))
        assertFalse(shouldUseOppositeGenderFilter("NON_BINARY"))
        assertFalse(shouldUseOppositeGenderFilter(null))
    }
}
