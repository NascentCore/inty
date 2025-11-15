package ai.sxwl.android.data.api.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class AgentBeanTest {

    @Test
    fun getAlbumImage_fallsBackToAvatarWhenBackgroundMissing() {
        val agent =
            AgentInfo(
                avatar = "https://images.sxwl.dev/inty-static/agents/sample/avatar.png",
                background = "",
            )

        val expectedAvatar = agent.getLargeAvatar()
        val albumImage = agent.getAlbumImage()

        assertEquals(expectedAvatar, albumImage)
    }

    @Test
    fun getAlbumImage_returnsNullWhenNoImagesAvailable() {
        val agent = AgentInfo(avatar = "", background = "")

        assertNull(agent.getAlbumImage())
    }

    @Test
    fun getOriginShowImage_prefersBackgroundThenAvatar() {
        val agent =
            AgentInfo(
                avatar = "avatar.png",
                background = "background.png",
            )

        assertEquals("background.png", agent.getOriginShowImage())

        val avatarOnly = agent.copy(background = "")
        assertEquals("avatar.png", avatarOnly.getOriginShowImage())

        val emptyAgent = agent.copy(background = "", avatar = "")
        assertNull(emptyAgent.getOriginShowImage())
    }
}
