package ai.sxwl.android.data.character.local.db

import ai.sxwl.android.data.api.model.CreatorInfo
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.Instant

/**
 * CharacterEntity 扩展函数测试
 * 验证虚拟 #New tag 的逻辑
 */
class CharacterEntityTest {

    @Test
    fun `isNewCharacter returns true for character created within 1 week`() {
        // Given: 3天前创建的角色
        val threeDaysAgo = Instant.now().minusSeconds(3L * 24 * 60 * 60).toString()
        val entity = createCharacterEntity(createdAt = threeDaysAgo)

        // When: 判断是否为新角色
        val result = entity.isNewCharacter()

        // Then: 应该返回 true
        assertTrue(result)
    }

    @Test
    fun `isNewCharacter returns false for character created more than 1 week ago`() {
        // Given: 8天前创建的角色
        val eightDaysAgo = Instant.now().minusSeconds(8L * 24 * 60 * 60).toString()
        val entity = createCharacterEntity(createdAt = eightDaysAgo)

        // When: 判断是否为新角色
        val result = entity.isNewCharacter()

        // Then: 应该返回 false
        assertFalse(result)
    }

    @Test
    fun `isNewCharacter returns false for character with blank createdAt`() {
        // Given: createdAt 为空字符串的角色
        val entity = createCharacterEntity(createdAt = "")

        // When: 判断是否为新角色
        val result = entity.isNewCharacter()

        // Then: 应该返回 false
        assertFalse(result)
    }

    @Test
    fun `isNewCharacter returns false for character with invalid createdAt format`() {
        // Given: createdAt 格式无效的角色
        val entity = createCharacterEntity(createdAt = "invalid-date")

        // When: 判断是否为新角色
        val result = entity.isNewCharacter()

        // Then: 应该返回 false
        assertFalse(result)
    }

    @Test
    fun `isNewCharacter returns true for character created within 7 days`() {
        // Given: 6天23小时59分前创建的角色（接近7天但仍在1周内）
        val almostSevenDaysAgo = Instant.now().minusSeconds(6L * 24 * 60 * 60 + 23 * 60 * 60 + 59 * 60).toString()
        val entity = createCharacterEntity(createdAt = almostSevenDaysAgo)

        // When: 判断是否为新角色
        val result = entity.isNewCharacter()

        // Then: 应该返回 true（仍在1周内）
        assertTrue(result)
    }

    @Test
    fun `getTagsWithVirtual adds New tag for new character`() {
        // Given: 3天前创建的角色，已有 tags
        val threeDaysAgo = Instant.now().minusSeconds(3L * 24 * 60 * 60).toString()
        val entity = createCharacterEntity(
            createdAt = threeDaysAgo,
            tags = listOf("tag1", "tag2")
        )

        // When: 获取包含虚拟 tag 的列表
        val tagsWithVirtual = entity.getTagsWithVirtual()

        // Then: 应该包含原有的 tags 和 #New
        assertEquals(3, tagsWithVirtual.size)
        assertTrue(tagsWithVirtual.contains("tag1"))
        assertTrue(tagsWithVirtual.contains("tag2"))
        assertTrue(tagsWithVirtual.contains("#New"))
    }

    @Test
    fun `getTagsWithVirtual does not add New tag for old character`() {
        // Given: 8天前创建的角色，已有 tags
        val eightDaysAgo = Instant.now().minusSeconds(8L * 24 * 60 * 60).toString()
        val entity = createCharacterEntity(
            createdAt = eightDaysAgo,
            tags = listOf("tag1", "tag2")
        )

        // When: 获取包含虚拟 tag 的列表
        val tagsWithVirtual = entity.getTagsWithVirtual()

        // Then: 应该只包含原有的 tags，不包含 #New
        assertEquals(2, tagsWithVirtual.size)
        assertTrue(tagsWithVirtual.contains("tag1"))
        assertTrue(tagsWithVirtual.contains("tag2"))
        assertFalse(tagsWithVirtual.contains("#New"))
    }

    @Test
    fun `getTagsWithVirtual adds New tag for new character with no existing tags`() {
        // Given: 3天前创建的角色，没有 tags
        val threeDaysAgo = Instant.now().minusSeconds(3L * 24 * 60 * 60).toString()
        val entity = createCharacterEntity(
            createdAt = threeDaysAgo,
            tags = null
        )

        // When: 获取包含虚拟 tag 的列表
        val tagsWithVirtual = entity.getTagsWithVirtual()

        // Then: 应该只包含 #New
        assertEquals(1, tagsWithVirtual.size)
        assertTrue(tagsWithVirtual.contains("#New"))
    }

    @Test
    fun `getTagsWithVirtual returns empty list for old character with no tags`() {
        // Given: 8天前创建的角色，没有 tags
        val eightDaysAgo = Instant.now().minusSeconds(8L * 24 * 60 * 60).toString()
        val entity = createCharacterEntity(
            createdAt = eightDaysAgo,
            tags = null
        )

        // When: 获取包含虚拟 tag 的列表
        val tagsWithVirtual = entity.getTagsWithVirtual()

        // Then: 应该返回空列表
        assertTrue(tagsWithVirtual.isEmpty())
    }

    // 辅助方法：创建测试用的 CharacterEntity
    private fun createCharacterEntity(
        agentId: String = "test-agent-1",
        createdAt: String = Instant.now().toString(),
        tags: List<String>? = null,
    ): CharacterEntity {
        return CharacterEntity(
            agentId = agentId,
            name = "Test Character",
            avatar = "https://example.com/avatar.jpg",
            intro = "Test intro",
            readableId = "test-character",
            category = "test",
            energyPoints = 100,
            updatedAt = System.currentTimeMillis(),
            background = "https://example.com/background.jpg",
            backgroundAnimatedUrl = "",
            gender = "MALE",
            isFollowed = false,
            opening = "Hello",
            openingAudioUrl = "",
            voicePreview = "",
            createdAt = createdAt,
            creator = null,
            tags = tags,
            settings = null,
            visibility = "public",
            prompt = "Test prompt",
            followerCount = 0,
            connectorCount = 0,
            deletedAt = null,
            backgroundImages = null,
        )
    }
}

