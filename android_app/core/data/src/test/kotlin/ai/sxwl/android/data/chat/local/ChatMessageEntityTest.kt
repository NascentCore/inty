package ai.sxwl.android.data.chat.local

// CREATED_BY_AGENT

import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.chat.local.db.toEntity
import ai.sxwl.android.data.chat.local.db.toModel
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class ChatMessageEntityTest {

    @Test
    fun `toEntity uses remote id as stable local id`() {
        val message = MsgInfo(id = "remote-id", content = "hello", role = "user")

        val entity = message.toEntity(agentId = "agent-1")

        assertEquals("remote-id", entity.localId)
        assertEquals("remote-id", entity.toModel().localMsgId)
    }

    @Test
    fun `generated image removal clears persisted columns`() {
        val agentId = "agent-2"
        val initial =
            MsgInfo(
                content = "image",
                role = "assistant",
                meta_data =
                    MsgInfo.MsgMetaData(
                        agentId = agentId,
                        generatedImage =
                            MsgInfo.MsgMetaData.GeneratedImage(
                                imageUrl = "https://inty.ai/image.png",
                                width = 320,
                                height = 640,
                            ),
                    ),
            )

        val stored = initial.toEntity(agentId = agentId)
        val removed =
            initial.copy(meta_data = MsgInfo.MsgMetaData(agentId = agentId, generatedImage = null))

        val updated = removed.toEntity(agentId = agentId, existing = stored)

        assertNull(updated.generatedImageUrl)
        assertNull(updated.generatedImageWidth)
        assertNull(updated.generatedImageHeight)
    }
}
