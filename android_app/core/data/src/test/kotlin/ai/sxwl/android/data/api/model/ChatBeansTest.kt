package ai.sxwl.android.data.api.model

import ai.sxwl.android.data.store.IntySetting
import io.mockk.every
import io.mockk.mockkObject
import io.mockk.unmockkObject
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class ChatBeansTest {

    private lateinit var intySetting: IntySettingStub

    @Before
    fun setUp() {
        intySetting = IntySettingStub().also { it.install() }
    }

    @After
    fun tearDown() {
        intySetting.uninstall()
    }

    @Test
    fun msgInfoHelpersReflectMetaData() {
        val meta =
            MsgInfo.MsgMetaData(
                agentId = "agent-1",
                isOpening = true,
                generatedImage =
                    MsgInfo.MsgMetaData.GeneratedImage(
                        imageUrl = "https://example.com/image.png",
                        width = 512,
                        height = 768,
                    ),
            )
        val msg = MsgInfo(meta_data = meta)

        assertTrue(msg.isOpening())
        assertEquals("agent-1", msg.agentId())
        assertTrue(msg.hasGeneratedImage())
        assertEquals(512, msg.getGeneratedImageWidth())
        assertEquals(768, msg.getGeneratedImageHeight())
    }

    @Test
    fun conversationItemShouldShowDependsOnHiddenState() {
        val visible = conversation("visible")
        val hiddenWithoutNews = conversation("hidden-no-news")
        val hiddenWithNews = conversation("hidden-with-news")

        intySetting.setHidden(hiddenWithoutNews.agentId, hidden = true, hasNewMessage = false)
        intySetting.setHidden(hiddenWithNews.agentId, hidden = true, hasNewMessage = true)

        assertTrue(visible.shouldShow())
        assertFalse(hiddenWithoutNews.shouldShow())
        assertTrue(hiddenWithNews.shouldShow())
    }

    @Test
    fun convertToAgentInfoCopiesFieldsAndDeletionFlag() {
        val conversation =
            conversation(
                agentId = "agent-3",
                agentName = "Tester",
                avatar = "avatar.png",
                background = "bg.png",
                isDeleted = true,
            )

        val agentInfo = conversation.convertToAgentInfo()

        assertEquals("agent-3", agentInfo.id)
        assertEquals("Tester", agentInfo.name)
        assertEquals("avatar.png", agentInfo.avatar)
        assertEquals("bg.png", agentInfo.background)
        assertTrue(agentInfo.isDeleted)
    }

    private fun conversation(
        agentId: String,
        agentName: String = "Agent $agentId",
        avatar: String = "",
        background: String = "",
        isDeleted: Boolean = false,
    ): ConversationItem {
        return ConversationItem(
            agentId = agentId,
            agentName = agentName,
            agentAvatar = avatar,
            agentBackground = background,
            agentBackgroundAnimated = "",
            agentIntro = "",
            agentOpening = "",
            agentOpeningAudioUrl = "",
            createdAt = "2025-11-15T10:00:00Z",
            id = agentId,
            lastMessage = "hello",
            lastMessageTime = "2025-11-15T10:00:00Z",
            settings = null,
            updatedAt = null,
            userId = "user",
            isDeleted = isDeleted,
        )
    }

    private class IntySettingStub {
        private val hidden = mutableSetOf<String>()
        private val newMessageAfterHidden = mutableSetOf<String>()

        fun install() {
            mockkObject(IntySetting)
            every { IntySetting.isConversationHidden(any()) } answers { hidden.contains(firstArg()) }
            every { IntySetting.hasNewMessageSinceHidden(any(), any()) } answers {
                newMessageAfterHidden.contains(firstArg())
            }
            every { IntySetting.isConversationReaded(any(), any()) } returns false
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

        fun uninstall() {
            unmockkObject(IntySetting)
        }
    }
}
