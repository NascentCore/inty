package ai.sxwl.android.data.chat.local

// CREATED_BY_AGENT

import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.chat.data.RoomDataSource
import ai.sxwl.android.data.chat.local.db.IntyChatDatabase
import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

/** 测试 updateMessages 的行为 验证更新消息时保留现有 sortKey，避免重新排序 */
@RunWith(AndroidJUnit4::class)
class UpdateMessagesTest {

    private lateinit var database: IntyChatDatabase
    private lateinit var dataSource: RoomDataSource
    private val agentId = "test-agent-update"

    @Before
    fun setup() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        database =
            Room.inMemoryDatabaseBuilder(context, IntyChatDatabase::class.java)
                .allowMainThreadQueries()
                .build()
        dataSource = RoomDataSource(database = database)
    }

    @After
    fun tearDown() {
        runBlocking { delay(100) }
        database.close()
    }

    private suspend fun waitForMessages(agentId: String, expectedSize: Int): List<MsgInfo> {
        return withTimeout(10000) { // 增加超时时间到 10 秒
            var messages: List<MsgInfo>
            do {
                messages = dataSource.getMessagesFlow(agentId).first()
                if (messages.size != expectedSize) {
                    delay(50)
                }
            } while (messages.size != expectedSize)
            messages
        }
    }

    private suspend fun getEntitySortKey(agentId: String, messageId: String): Long? {
        return withTimeout(5000) {
            val dao = database.chatMessageDao()
            val entity = dao.getMessage(agentId, messageId)
            entity?.sortKey
        }
    }

    @Test
    fun updateMessagesPreservesSortKeyForExistingMessagesByLocalId() = runBlocking {
        // Given: 已有消息
        val originalMessages =
            listOf(
                MsgInfo(
                    id = "remote-1",
                    content = "Message 1",
                    role = "assistant",
                    timestamp = "2025-01-15T10:30:00.000000Z",
                ),
                MsgInfo(
                    id = "remote-2",
                    content = "Message 2",
                    role = "user",
                    timestamp = "2025-01-15T10:31:00.000000Z",
                ),
            )
        dataSource.appendMessages(agentId, originalMessages)
        val initialMessages = waitForMessages(agentId, expectedSize = 2)

        // 获取原始 sortKey
        val originalSortKey1 = getEntitySortKey(agentId, initialMessages[0].localMsgId)
        val originalSortKey2 = getEntitySortKey(agentId, initialMessages[1].localMsgId)
        assertTrue("原始消息应该有 sortKey", originalSortKey1 != null && originalSortKey2 != null)

        // When: 更新消息（通过 localMsgId 匹配）
        val updatedMessages =
            listOf(
                initialMessages[0].copy(
                    localMsgId = initialMessages[0].localMsgId,
                    content = "Updated Message 1",
                ),
                initialMessages[1].copy(
                    localMsgId = initialMessages[1].localMsgId,
                    content = "Updated Message 2",
                ),
            )
        dataSource.updateMessages(agentId, updatedMessages)

        // Then: sortKey 应该被保留
        delay(100) // 等待 Flow 更新
        val finalMessages = waitForMessages(agentId, expectedSize = 2)

        // 通过 id 查找消息，因为顺序可能变化
        val finalMessage1 = finalMessages.find { it.id == "remote-1" }
        val finalMessage2 = finalMessages.find { it.id == "remote-2" }
        assertTrue("应该找到 remote-1 消息", finalMessage1 != null)
        assertTrue("应该找到 remote-2 消息", finalMessage2 != null)

        val finalSortKey1 = getEntitySortKey(agentId, finalMessage1!!.localMsgId)
        val finalSortKey2 = getEntitySortKey(agentId, finalMessage2!!.localMsgId)

        assertEquals("sortKey 应该被保留", originalSortKey1, finalSortKey1)
        assertEquals("sortKey 应该被保留", originalSortKey2, finalSortKey2)
        assertEquals("内容应该被更新", "Updated Message 1", finalMessage1.content)
        assertEquals("内容应该被更新", "Updated Message 2", finalMessage2.content)
    }

    @Test
    fun updateMessagesPreservesSortKeyForExistingMessagesByRemoteId() = runBlocking {
        // Given: 已有消息（使用 remoteId）
        val originalMessages =
            listOf(
                MsgInfo(
                    id = "remote-1",
                    content = "Message 1",
                    role = "assistant",
                    timestamp = "2025-01-15T10:30:00.000000Z",
                )
            )
        dataSource.appendMessages(agentId, originalMessages)
        val initialMessages = waitForMessages(agentId, expectedSize = 1)

        // 获取原始 sortKey
        val originalSortKey = getEntitySortKey(agentId, initialMessages[0].localMsgId)
        assertTrue("原始消息应该有 sortKey", originalSortKey != null)

        // When: 更新消息（通过 remoteId 匹配，不提供 localMsgId）
        val updatedMessages =
            listOf(
                MsgInfo(
                    id = "remote-1", // 使用 remoteId 匹配
                    content = "Updated Message 1",
                    role = "assistant",
                    timestamp = "2025-01-15T10:30:00.000000Z",
                )
            )
        dataSource.updateMessages(agentId, updatedMessages)

        // Then: sortKey 应该被保留
        delay(100) // 等待 Flow 更新
        val finalMessages = waitForMessages(agentId, expectedSize = 1)
        val finalSortKey = getEntitySortKey(agentId, finalMessages[0].localMsgId)

        assertEquals("sortKey 应该被保留（通过 remoteId 匹配）", originalSortKey, finalSortKey)
        assertEquals("内容应该被更新", "Updated Message 1", finalMessages[0].content)
    }

    @Test
    fun updateMessagesAssignsNewSortKeyForNewMessages() = runBlocking {
        // Given: 已有消息
        val originalMessages =
            listOf(
                MsgInfo(
                    id = "remote-1",
                    content = "Message 1",
                    role = "assistant",
                    timestamp = "2025-01-15T10:30:00.000000Z",
                )
            )
        dataSource.appendMessages(agentId, originalMessages)
        waitForMessages(agentId, expectedSize = 1)

        // 获取最大 sortKey
        val maxSortKeyBefore = database.chatMessageDao().getMaxSortKey(agentId) ?: 0L

        // When: 添加新消息（不匹配现有消息）
        val newMessages =
            listOf(
                MsgInfo(
                    id = "remote-2", // 新的 remoteId
                    content = "New Message",
                    role = "user",
                    timestamp = "2025-01-15T10:35:00.000000Z",
                )
            )
        dataSource.updateMessages(agentId, listOf(originalMessages[0], newMessages[0]))

        // Then: 新消息应该得到新的 sortKey（大于现有最大 sortKey）
        val finalMessages = waitForMessages(agentId, expectedSize = 2)
        val newMessage = finalMessages.find { it.id == "remote-2" }
        assertTrue("新消息应该存在", newMessage != null)

        val newMessageSortKey = getEntitySortKey(agentId, newMessage!!.localMsgId)
        assertTrue("新消息的 sortKey 应该大于现有最大 sortKey", newMessageSortKey!! > maxSortKeyBefore)
    }

    @Test
    fun updateMessagesHandlesMixedScenario() = runBlocking {
        // Given: 已有消息
        val originalMessages =
            listOf(
                MsgInfo(
                    id = "remote-1",
                    content = "Message 1",
                    role = "assistant",
                    timestamp = "2025-01-15T10:30:00.000000Z",
                ),
                MsgInfo(
                    id = "remote-2",
                    content = "Message 2",
                    role = "user",
                    timestamp = "2025-01-15T10:31:00.000000Z",
                ),
            )
        dataSource.appendMessages(agentId, originalMessages)
        val initialMessages = waitForMessages(agentId, expectedSize = 2)

        // 获取原始 sortKey
        val originalSortKey1 = getEntitySortKey(agentId, initialMessages[0].localMsgId)
        val originalSortKey2 = getEntitySortKey(agentId, initialMessages[1].localMsgId)
        val maxSortKeyBefore = database.chatMessageDao().getMaxSortKey(agentId) ?: 0L

        // When: 混合场景（部分消息匹配，部分不匹配）
        val updatedMessages =
            listOf(
                // 匹配的消息 1（通过 localMsgId）
                initialMessages[0].copy(
                    localMsgId = initialMessages[0].localMsgId,
                    content = "Updated Message 1",
                ),
                // 匹配的消息 2（通过 remoteId）
                MsgInfo(
                    id = "remote-2",
                    content = "Updated Message 2",
                    role = "user",
                    timestamp = "2025-01-15T10:31:00.000000Z",
                ),
                // 新消息
                MsgInfo(
                    id = "remote-3",
                    content = "New Message 3",
                    role = "assistant",
                    timestamp = "2025-01-15T10:32:00.000000Z",
                ),
            )
        dataSource.updateMessages(agentId, updatedMessages)

        // Then: 匹配的消息保留 sortKey，新消息得到新 sortKey
        // 等待 Flow 更新
        delay(300) // 增加延迟以确保所有更新完成
        val finalMessages = waitForMessages(agentId, expectedSize = 3)

        val finalMessage1 = finalMessages.find { it.id == "remote-1" }
        val finalMessage2 = finalMessages.find { it.id == "remote-2" }
        val finalMessage3 = finalMessages.find { it.id == "remote-3" }
        assertTrue("应该找到 remote-1 消息", finalMessage1 != null)
        assertTrue("应该找到 remote-2 消息", finalMessage2 != null)
        assertTrue("应该找到 remote-3 消息", finalMessage3 != null)

        val finalSortKey1 = getEntitySortKey(agentId, finalMessage1!!.localMsgId)
        val finalSortKey2 = getEntitySortKey(agentId, finalMessage2!!.localMsgId)
        val newMessageSortKey = getEntitySortKey(agentId, finalMessage3!!.localMsgId)

        assertEquals("匹配的消息 1 应该保留 sortKey", originalSortKey1, finalSortKey1)
        assertEquals("匹配的消息 2 应该保留 sortKey", originalSortKey2, finalSortKey2)
        assertTrue("新消息的 sortKey 应该大于现有最大 sortKey", newMessageSortKey!! > maxSortKeyBefore)
    }

    @Test
    fun updateMessagesPreservesMessageOrder() = runBlocking {
        // Given: 已有消息，按时间顺序
        val originalMessages =
            listOf(
                MsgInfo(
                    id = "remote-1",
                    content = "First message",
                    role = "user",
                    timestamp = "2025-01-15T10:30:00.000000Z",
                ),
                MsgInfo(
                    id = "remote-2",
                    content = "Second message",
                    role = "assistant",
                    timestamp = "2025-01-15T10:31:00.000000Z",
                ),
                MsgInfo(
                    id = "remote-3",
                    content = "Third message",
                    role = "user",
                    timestamp = "2025-01-15T10:32:00.000000Z",
                ),
            )
        dataSource.appendMessages(agentId, originalMessages)
        val initialMessages = waitForMessages(agentId, expectedSize = 3)

        // 记录原始顺序（通过 sortKey）
        val originalOrder = initialMessages.map { it.id }

        // When: 更新所有消息的内容
        val updatedMessages = originalMessages.map { it.copy(content = "Updated: ${it.content}") }
        dataSource.updateMessages(agentId, updatedMessages)

        // Then: 消息顺序应该保持不变（sortKey 保留）
        val finalMessages = waitForMessages(agentId, expectedSize = 3)
        val finalOrder = finalMessages.map { it.id }

        assertEquals("消息顺序应该保持不变", originalOrder, finalOrder)
    }

    @Test
    fun updateMessagesWithEmptyListClearsAllMessages() = runBlocking {
        // Given: 已有消息
        val originalMessages =
            listOf(
                MsgInfo(
                    id = "remote-1",
                    content = "Message 1",
                    role = "assistant",
                    timestamp = "2025-01-15T10:30:00.000000Z",
                ),
                MsgInfo(
                    id = "remote-2",
                    content = "Message 2",
                    role = "user",
                    timestamp = "2025-01-15T10:31:00.000000Z",
                ),
            )
        dataSource.appendMessages(agentId, originalMessages)
        waitForMessages(agentId, expectedSize = 2)

        // When: 使用空列表更新
        dataSource.updateMessages(agentId, emptyList())

        // Then: 所有消息应该被删除
        // 等待 Flow 更新（因为 deleteByAgent 后 Flow 需要时间更新）
        delay(100)
        val finalMessages = waitForMessages(agentId, expectedSize = 0)
        assertEquals("所有消息应该被删除", 0, finalMessages.size)
    }
}
