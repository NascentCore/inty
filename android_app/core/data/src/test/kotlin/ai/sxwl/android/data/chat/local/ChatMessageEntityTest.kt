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
    fun `toEntity uses remote id as stable id and toModel preserves localMsgId`() {
        val message = MsgInfo(id = "remote-id", content = "hello", role = "user")

        val entity = message.toEntity(agentId = "agent-1")

        assertEquals("remote-id", entity.id)
        assertEquals("remote-id", entity.toModel().localMsgId)
    }

    @Test
    fun `toEntity with generatedImage stores it and toModel without generatedImage has null`() {
        val agentId = "agent-2"
        val withImage =
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

        val entityWithImage = withImage.toEntity(agentId = agentId)
        assertEquals("https://inty.ai/image.png", entityWithImage.getGeneratedImageUrl())
        assertEquals(320, entityWithImage.getGeneratedImageWidth())
        assertEquals(640, entityWithImage.getGeneratedImageHeight())

        val withoutImage =
            withImage.copy(
                meta_data = MsgInfo.MsgMetaData(agentId = agentId, generatedImage = null)
            )
        val entityWithoutImage = withoutImage.toEntity(agentId = agentId)
        assertNull(entityWithoutImage.getGeneratedImageUrl())
        assertNull(entityWithoutImage.getGeneratedImageWidth())
        assertNull(entityWithoutImage.getGeneratedImageHeight())
    }
}
