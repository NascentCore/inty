package com.ai.intellimate.messages

import ai.sxwl.android.data.api.model.ConversationItem
import ai.sxwl.android.data.store.IntySetting
import io.mockk.every
import io.mockk.mockkObject
import io.mockk.unmockkObject
import kotlinx.coroutines.flow.MutableStateFlow
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class MessagesViewModelTest {

    private lateinit var intySetting: IntySettingStub
    private lateinit var viewModel: MessagesViewModel

    @Before
    fun setUp() {
        intySetting = IntySettingStub().also { it.install() }
        viewModel = MessagesViewModel()
    }

    @After
    fun tearDown() {
        intySetting.uninstall()
    }

    @Test
    fun processConversationsWithPinHide_sortsAndFiltersCorrectly() {
        intySetting.setPinned("pinned", true)
        intySetting.setHidden("hidden-no-news", hidden = true, hasNewMessage = false)
        intySetting.setHidden("hidden-with-news", hidden = true, hasNewMessage = true)

        val conversations =
            listOf(
                conversation("visible-old", "2025-11-15T10:00:00Z"),
                conversation("pinned", "2025-11-16T09:00:00Z"),
                conversation("hidden-no-news", "2025-11-16T08:00:00Z"),
                conversation("hidden-with-news", "2025-11-16T07:00:00Z"),
                conversation("visible-newer", "2025-11-16T11:00:00Z"),
            )

        val processed = viewModel.invokeProcess(conversations)

        assertEquals(
            listOf("pinned", "visible-newer", "hidden-with-news", "visible-old"),
            processed.map { it.agentId },
        )
    }

    @Test
    fun checkAndUnhideConversations_unhidesWhenNewMessageArrives() {
        val toUnhide = conversation("hidden-to-show", "2025-11-16T12:00:00Z")
        val remainHidden = conversation("still-hidden", "2025-11-16T11:00:00Z")
        intySetting.setHidden(toUnhide.agentId, hidden = true, hasNewMessage = true)
        intySetting.setHidden(remainHidden.agentId, hidden = true, hasNewMessage = false)

        viewModel.setConversations(listOf(toUnhide, remainHidden))

        viewModel.checkAndUnhideConversations()

        assertFalse(intySetting.isHidden(toUnhide.agentId))
        assertTrue(intySetting.isHidden(remainHidden.agentId))
        assertEquals(listOf("hidden-to-show"), viewModel.uiState.value.conversations.map { it.agentId })
    }

    @Test
    fun setConversationReaded_marksOnlyTargetConversation() {
        val unread = conversation("agent-1", "2025-11-16T13:00:00Z", lastMessage = "hello")
        val untouched = conversation("agent-2", "2025-11-16T12:00:00Z", lastMessage = "bye")
        viewModel.setConversations(listOf(unread, untouched))

        viewModel.setConversationReaded(unread)

        val updated = viewModel.uiState.value.conversations
        assertFalse(updated.first { it.agentId == unread.agentId }.isNew)
        assertTrue(updated.first { it.agentId == untouched.agentId }.isNew)
        assertEquals("hello", intySetting.readState[unread.agentId])
    }

    private fun conversation(
        agentId: String,
        lastMessageTime: String,
        lastMessage: String = "msg-$agentId",
    ): ConversationItem {
        return ConversationItem(
            agentId = agentId,
            agentName = "Agent $agentId",
            agentAvatar = "",
            agentBackground = "",
            agentBackgroundAnimated = "",
            agentIntro = "",
            agentOpening = "",
            agentOpeningAudioUrl = "",
            createdAt = lastMessageTime,
            id = agentId,
            lastMessage = lastMessage,
            lastMessageTime = lastMessageTime,
            settings = null,
            updatedAt = null,
            userId = "user",
            isDeleted = false,
        )
    }

    private fun MessagesViewModel.invokeProcess(
        conversations: List<ConversationItem>
    ): List<ConversationItem> {
        val method =
            MessagesViewModel::class.java.getDeclaredMethod(
                "processConversationsWithPinHide",
                List::class.java,
            )
        method.isAccessible = true
        @Suppress("UNCHECKED_CAST")
        return method.invoke(this, conversations) as List<ConversationItem>
    }

    private fun MessagesViewModel.setConversations(conversations: List<ConversationItem>) {
        val field = MessagesViewModel::class.java.getDeclaredField("_uiState")
        field.isAccessible = true
        val state = field.get(this) as MutableStateFlow<MessagesUiState>
        state.value = state.value.copy(conversations = conversations)
    }

    private class IntySettingStub {
        private val pinned = mutableSetOf<String>()
        private val hidden = mutableSetOf<String>()
        private val newMessageAfterHidden = mutableSetOf<String>()
        val readState = mutableMapOf<String, String>()

        fun install() {
            mockkObject(IntySetting)
            every { IntySetting.isConversationPinned(any()) } answers { pinned.contains(firstArg()) }
            every { IntySetting.setConversationPinned(any(), any()) } answers {
                val agentId = firstArg<String>()
                if (secondArg<Boolean>()) pinned.add(agentId) else pinned.remove(agentId)
            }
            every { IntySetting.isConversationHidden(any()) } answers { hidden.contains(firstArg()) }
            every { IntySetting.setConversationHidden(any(), any()) } answers {
                val agentId = firstArg<String>()
                val hide = secondArg<Boolean>()
                if (hide) {
                    hidden.add(agentId)
                } else {
                    hidden.remove(agentId)
                    newMessageAfterHidden.remove(agentId)
                }
            }
            every { IntySetting.hasNewMessageSinceHidden(any(), any()) } answers {
                newMessageAfterHidden.contains(firstArg())
            }
            every { IntySetting.isConversationReaded(any(), any()) } answers {
                val agentId = firstArg<String>()
                val message = secondArg<String>()
                readState[agentId] == message
            }
            every { IntySetting.setConversationReaded(any(), any()) } answers {
                readState[firstArg()] = secondArg()
            }
        }

        fun setPinned(agentId: String, value: Boolean) {
            if (value) pinned.add(agentId) else pinned.remove(agentId)
        }

        fun setHidden(agentId: String, hidden: Boolean, hasNewMessage: Boolean) {
            if (hidden) {
                this.hidden.add(agentId)
                if (hasNewMessage) {
                    newMessageAfterHidden.add(agentId)
                } else {
                    newMessageAfterHidden.remove(agentId)
                }
            } else {
                this.hidden.remove(agentId)
                newMessageAfterHidden.remove(agentId)
            }
        }

        fun isHidden(agentId: String) = hidden.contains(agentId)

        fun uninstall() {
            unmockkObject(IntySetting)
        }
    }
}
