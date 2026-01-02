package ai.sxwl.android.data.character.repository

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.character.local.db.CharacterDao
import ai.sxwl.android.data.character.local.db.CharacterEntity
import io.mockk.coEvery
import io.mockk.mockk
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.time.Instant

/**
 * CharacterRepository 测试
 * 验证虚拟 #New tag 的搜索和转换逻辑
 */
class CharacterRepositoryTest {

    private lateinit var mockDao: CharacterDao
    private lateinit var repository: CharacterRepository
    private val testDispatcher = StandardTestDispatcher()

    @Before
    fun setup() {
        Dispatchers.setMain(testDispatcher)
        mockDao = mockk()
        repository = CharacterRepository(dao = mockDao, dispatcher = testDispatcher)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun `searchCharactersByTag with new tag returns only new characters`() =
        runTest(testDispatcher) {
            // Given: 混合的新旧角色
            val newCharacter1 = createCharacterEntity(
                agentId = "new-1",
                createdAt = Instant.now().minusSeconds(3L * 24 * 60 * 60).toString()
            )
            val newCharacter2 = createCharacterEntity(
                agentId = "new-2",
                createdAt = Instant.now().minusSeconds(1L * 24 * 60 * 60).toString()
            )
            val oldCharacter = createCharacterEntity(
                agentId = "old-1",
                createdAt = Instant.now().minusSeconds(10L * 24 * 60 * 60).toString()
            )

            coEvery { mockDao.getAllCharacters(any()) } returns listOf(
                newCharacter1,
                newCharacter2,
                oldCharacter
            )

            // When: 搜索 #new tag
            val results = repository.searchCharactersByTag("#new", limit = 100)

            // Then: 应该只返回新角色
            assertEquals(2, results.size)
            assertTrue(results.any { it.id == "new-1" })
            assertTrue(results.any { it.id == "new-2" })
            assertFalse(results.any { it.id == "old-1" })
        }

    @Test
    fun `searchCharactersByTag with new tag (lowercase) returns only new characters`() =
        runTest(testDispatcher) {
            // Given: 新角色
            val newCharacter = createCharacterEntity(
                agentId = "new-1",
                createdAt = Instant.now().minusSeconds(2L * 24 * 60 * 60).toString()
            )

            coEvery { mockDao.getAllCharacters(any()) } returns listOf(newCharacter)

            // When: 搜索 "new" (小写，不带 #)
            val results = repository.searchCharactersByTag("new", limit = 100)

            // Then: 应该返回新角色
            assertEquals(1, results.size)
            assertEquals("new-1", results[0].id)
        }

    @Test
    fun `searchCharactersByTag with regular tag uses dao searchCharactersByTag`() =
        runTest(testDispatcher) {
            // Given: 带有特定 tag 的角色
            val characterWithTag = createCharacterEntity(
                agentId = "tagged-1",
                tags = listOf("fantasy", "adventure")
            )

            coEvery { mockDao.searchCharactersByTag("fantasy", 100) } returns listOf(
                characterWithTag
            )

            // When: 搜索普通 tag
            val results = repository.searchCharactersByTag("fantasy", limit = 100)

            // Then: 应该使用 dao 的 searchCharactersByTag 方法
            assertEquals(1, results.size)
            assertEquals("tagged-1", results[0].id)
        }

    @Test
    fun `searchCharactersByTag includes New tag in results for new characters`() =
        runTest(testDispatcher) {
            // Given: 3天前创建的新角色，已有 tags
            val newCharacter = createCharacterEntity(
                agentId = "new-1",
                createdAt = Instant.now().minusSeconds(3L * 24 * 60 * 60).toString(),
                tags = listOf("tag1", "tag2")
            )

            coEvery { mockDao.getAllCharacters(any()) } returns listOf(newCharacter)

            // When: 搜索 #new tag
            val results = repository.searchCharactersByTag("#new", limit = 100)

            // Then: 结果应该包含新角色，且 tags 包含 #New
            assertEquals(1, results.size)
            val tags = results[0].tags?.filterNotNull() ?: emptyList()
            assertEquals(3, tags.size)
            assertTrue(tags.contains("tag1"))
            assertTrue(tags.contains("tag2"))
            assertTrue(tags.contains("#New"))
        }

    @Test
    fun `searchCharactersByTag does not include New tag for old characters`() =
        runTest(testDispatcher) {
            // Given: 8天前创建的旧角色，已有 tags
            val oldCharacter = createCharacterEntity(
                agentId = "old-1",
                createdAt = Instant.now().minusSeconds(8L * 24 * 60 * 60).toString(),
                tags = listOf("tag1", "tag2")
            )

            coEvery { mockDao.searchCharactersByTag("tag1", 100) } returns listOf(oldCharacter)

            // When: 搜索普通 tag
            val results = repository.searchCharactersByTag("tag1", limit = 100)

            // Then: tags 应该只包含原有的 tags，不包含 #New
            assertEquals(1, results.size)
            val tags = results[0].tags?.filterNotNull() ?: emptyList()
            assertEquals(2, tags.size)
            assertTrue(tags.contains("tag1"))
            assertTrue(tags.contains("tag2"))
            assertFalse(tags.contains("#New"))
        }

    @Test
    fun `searchCharactersByTag includes New tag for new character with no existing tags`() =
        runTest(testDispatcher) {
            // Given: 3天前创建的新角色，没有 tags
            val newCharacter = createCharacterEntity(
                agentId = "new-1",
                createdAt = Instant.now().minusSeconds(3L * 24 * 60 * 60).toString(),
                tags = null
            )

            coEvery { mockDao.getAllCharacters(any()) } returns listOf(newCharacter)

            // When: 搜索 #new tag
            val results = repository.searchCharactersByTag("#new", limit = 100)

            // Then: tags 应该只包含 #New
            assertEquals(1, results.size)
            val tags = results[0].tags?.filterNotNull() ?: emptyList()
            assertEquals(1, tags.size)
            assertTrue(tags.contains("#New"))
        }

    @Test
    fun `searchCharactersByTag with new tag respects limit`() =
        runTest(testDispatcher) {
            // Given: 多个新角色
            val newCharacters = (1..10).map { i ->
                createCharacterEntity(
                    agentId = "new-$i",
                    createdAt = Instant.now().minusSeconds(i * 24L * 60 * 60).toString()
                )
            }

            coEvery { mockDao.getAllCharacters(any()) } returns newCharacters

            // When: 搜索 #new tag，限制为 5
            val results = repository.searchCharactersByTag("#new", limit = 5)

            // Then: 应该只返回 5 个结果
            assertEquals(5, results.size)
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

