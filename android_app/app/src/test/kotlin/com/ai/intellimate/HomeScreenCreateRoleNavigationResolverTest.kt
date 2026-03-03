package com.ai.intellimate

import com.ai.intellimate.agent.generate.CreateRoleNavigationState
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class HomeScreenCreateRoleNavigationResolverTest {
    @Test
    fun `official assistant create success should open created chat`() {
        val action =
            resolveCreateRoleSuccessAction(
                createEntrySource = CreateRoleNavigationState.EntrySourceOfficialAssistantChat,
                createdAgentId = "agent_123",
            )

        assertTrue(action is CreateRoleSuccessAction.NavigateToCreatedChat)
        assertEquals(
            "agent_123",
            (action as CreateRoleSuccessAction.NavigateToCreatedChat).agentId,
        )
    }

    @Test
    fun `official assistant create without id should fallback to profile`() {
        val action =
            resolveCreateRoleSuccessAction(
                createEntrySource = CreateRoleNavigationState.EntrySourceOfficialAssistantChat,
                createdAgentId = "",
            )

        assertEquals(CreateRoleSuccessAction.NavigateToProfile, action)
    }

    @Test
    fun `non official source should fallback to profile`() {
        val action =
            resolveCreateRoleSuccessAction(
                createEntrySource = "profile",
                createdAgentId = "agent_456",
            )

        assertEquals(CreateRoleSuccessAction.NavigateToProfile, action)
    }
}
