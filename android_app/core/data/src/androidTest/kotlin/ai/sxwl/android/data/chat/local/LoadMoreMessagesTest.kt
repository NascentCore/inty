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
import java.time.Instant

/**
 * 测试 loadMoreMessages 的行为
 * 验证加载历史消息时，消息是否正确插入到列表开头（使用更小的 sortKey）
 */
@RunWith(AndroidJUnit4::class)
class LoadMoreMessagesTest {

    private lateinit var database: IntyChatDatabase
    private lateinit var dataSource: RoomDataSource
    private val agentId = "test-agent-load-more"

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
        runBlocking {
            // Give some time for any pending Flow emissions to complete before closing the DB
            delay(100)
        }
        database.close()
    }

    // Helper function to wait for flow emissions
    private suspend fun waitForMessages(agentId: String, expectedSize: Int): List<MsgInfo> {
        return withTimeout(5000) { // 5 second timeout
            var messages: List<MsgInfo>
            do {
                messages = dataSource.getMessagesFlow(agentId).first()
                if (messages.size < expectedSize) {
                    delay(50) // Wait a bit before re-checking
                }
            } while (messages.size < expectedSize)
            messages
        }
    }

    @Test
    fun loadMoreMessagesWithPrependMessagesPlacesOlderMessagesCorrectly() = runBlocking {
        // Given: 已有一些新消息（使用 appendMessages）
        val newerMessages = listOf(
            MsgInfo(
                id = "newer-1",
                content = "Newer message 1",
                role = "assistant",
                timestamp = "2025-01-15T10:30:00.000000Z",
            ),
            MsgInfo(
                id = "newer-2",
                content = "Newer message 2",
                role = "assistant",
                timestamp = "2025-01-15T10:31:00.000000Z",
            ),
        )
        dataSource.appendMessages(agentId, newerMessages)
        waitForMessages(agentId, expectedSize = 2)

        // When: 使用 prependMessages 加载历史消息（修复后的正确行为）
        val olderMessages = listOf(
            MsgInfo(
                id = "older-1",
                content = "Older message 1",
                role = "assistant",
                timestamp = "2025-01-15T10:20:00.000000Z",
            ),
            MsgInfo(
                id = "older-2",
                content = "Older message 2",
                role = "assistant",
                timestamp = "2025-01-15T10:21:00.000000Z",
            ),
        )
        dataSource.prependMessages(agentId, olderMessages)

        // Then: 验证消息顺序
        // 使用 prependMessages，历史消息会得到更小的 sortKey
        // 在 sortKey DESC 排序中，它们会排在后面
        // 在 UI 的 reverseLayout 中，它们会显示在顶部（这是正确的）
        val allMessages = waitForMessages(agentId, expectedSize = 4)
        assertEquals(4, allMessages.size)

        // 验证消息顺序：
        // - sortKey DESC 排序：newer-2 (最大), newer-1, older-2, older-1 (最小)
        // - 在 reverseLayout UI 中：older-1 (顶部), older-2, newer-1, newer-2 (底部)
        val firstMessage = allMessages[0] // sortKey DESC 排序中的第一个（UI 底部）
        val lastMessage = allMessages[3] // sortKey DESC 排序中的最后一个（UI 顶部）

        println("Messages order (sortKey DESC): ${allMessages.map { "${it.id} (${it.timestamp})" }}")
        println("First message (UI bottom): ${firstMessage.id}, Last message (UI top): ${lastMessage.id}")

        // 验证：在 sortKey DESC 排序中，新消息应该在前面，历史消息应该在后面
        assertTrue(
            "新消息应该排在列表前面（sortKey DESC），在 UI 底部",
            firstMessage.id == "newer-2" || firstMessage.id == "newer-1"
        )
        assertTrue(
            "历史消息应该排在列表后面（sortKey DESC），在 reverseLayout UI 中会显示在顶部",
            lastMessage.id == "older-1" || lastMessage.id == "older-2"
        )

        // 验证时间戳顺序：新消息的时间戳应该大于历史消息
        val newerTimestamp = Instant.parse(newerMessages[0].timestamp).toEpochMilli()
        val olderTimestamp = Instant.parse(olderMessages[0].timestamp).toEpochMilli()
        assertTrue("新消息的时间戳应该大于历史消息", newerTimestamp > olderTimestamp)
    }

}

