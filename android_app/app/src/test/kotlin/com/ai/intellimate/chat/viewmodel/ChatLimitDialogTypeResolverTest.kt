package com.ai.intellimate.chat.viewmodel

import org.junit.Assert.assertEquals
import org.junit.Test

class ChatLimitDialogTypeResolverTest {

    @Test
    fun `resolveChatLimitDialogType returns free user dialog for non vip`() {
        val type = ChatViewModel.resolveChatLimitDialogType(isUserVip = false)

        assertEquals(ChatViewModel.ChatLimitDialogType.FREE_USER_SUBSCRIPTION_REQUIRED, type)
    }

    @Test
    fun `resolveChatLimitDialogType returns subscriber dialog for vip`() {
        val type = ChatViewModel.resolveChatLimitDialogType(isUserVip = true)

        assertEquals(ChatViewModel.ChatLimitDialogType.SUBSCRIBER_LIMIT_REACHED, type)
    }
}
