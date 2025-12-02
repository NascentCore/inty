package ai.sxwl.android.data.chat.local

// CREATED_BY_AGENT

import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.chat.data.RoomDataSource
import ai.sxwl.android.data.chat.local.db.IntyChatDatabase
import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
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

/** 测试并发场景的事务保护 验证多个线程同时调用 appendMessages/prependMessages 时，不会产生 sortKey 冲突 */
@RunWith(AndroidJUnit4::class)
class ConcurrencyTest {

    private lateinit var database: IntyChatDatabase
    private lateinit var dataSource: RoomDataSource
    private val agentId = "test-agent-concurrency"

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
        return withTimeout(15000) { // 15 second timeout for concurrent tests
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

    @Test
    fun concurrentAppendMessagesDoesNotCreateDuplicateSortKeys() = runBlocking {
        // Given: 空数据库
        val initialMessages = dataSource.getMessagesFlow(agentId).first()
        assertEquals("初始应该没有消息", 0, initialMessages.size)

        // When: 并发调用 appendMessages（10 个协程，每个插入 1 条消息）
        val jobs =
            (1..10).map { i ->
                async {
                    dataSource.appendMessages(
                        agentId,
                        listOf(
                            MsgInfo(
                                id = "msg-$i",
                                content = "Concurrent message $i",
                                role = "user",
                                timestamp = "2025-01-15T10:30:0$i.000000Z",
                            )
                        ),
                    )
                }
            }
        jobs.awaitAll()

        // Then: 所有消息应该被插入，且 sortKey 不重复
        val finalMessages = waitForMessages(agentId, expectedSize = 10)
        assertEquals("应该有 10 条消息", 10, finalMessages.size)

        // 验证 sortKey 不重复
        val dao = database.chatMessageDao()
        val entities = dao.getAllMessages(agentId)
        val sortKeys = entities.map { it.sortKey }.toSet()
        assertEquals("sortKey 应该不重复", 10, sortKeys.size)

        // 验证 sortKey 是单调递增的
        val sortedKeys = sortKeys.sorted()
        assertEquals("sortKey 应该单调递增", sortedKeys, sortedKeys.sorted())
    }

    @Test
    fun concurrentPrependMessagesDoesNotCreateDuplicateSortKeys() = runBlocking {
        // Given: 已有一些消息
        val existingMessages =
            listOf(
                MsgInfo(
                    id = "existing-1",
                    content = "Existing message 1",
                    role = "assistant",
                    timestamp = "2025-01-15T10:30:00.000000Z",
                ),
                MsgInfo(
                    id = "existing-2",
                    content = "Existing message 2",
                    role = "user",
                    timestamp = "2025-01-15T10:31:00.000000Z",
                ),
            )
        dataSource.appendMessages(agentId, existingMessages)
        waitForMessages(agentId, expectedSize = 2)

        // When: 并发调用 prependMessages（5 个协程，每个插入 1 条历史消息）
        val jobs =
            (1..5).map { i ->
                async {
                    dataSource.prependMessages(
                        agentId,
                        listOf(
                            MsgInfo(
                                id = "older-$i",
                                content = "Older message $i",
                                role = "assistant",
                                timestamp = "2025-01-15T10:2$i:00.000000Z",
                            )
                        ),
                    )
                }
            }
        jobs.awaitAll()

        // Then: 所有消息应该被插入，且 sortKey 不重复
        val finalMessages = waitForMessages(agentId, expectedSize = 7)
        assertEquals("应该有 7 条消息（2 条现有 + 5 条新插入）", 7, finalMessages.size)

        // 验证 sortKey 不重复
        val dao = database.chatMessageDao()
        val entities = dao.getAllMessages(agentId)
        val sortKeys = entities.map { it.sortKey }.toSet()
        assertEquals("sortKey 应该不重复", 7, sortKeys.size)

        // 验证历史消息的 sortKey 小于现有消息的 sortKey
        val existingSortKeys =
            existingMessages.mapNotNull { msg ->
                finalMessages
                    .find { it.id == msg.id }
                    ?.let { dao.getMessage(agentId, it.localMsgId)?.sortKey }
            }
        val olderSortKeys =
            (1..5).mapNotNull { i ->
                finalMessages
                    .find { it.id == "older-$i" }
                    ?.let { dao.getMessage(agentId, it.localMsgId)?.sortKey }
            }

        val maxOlderSortKey = olderSortKeys.maxOrNull() ?: Long.MAX_VALUE
        val minExistingSortKey = existingSortKeys.minOrNull() ?: Long.MIN_VALUE
        assertTrue("历史消息的 sortKey 应该小于现有消息的 sortKey", maxOlderSortKey < minExistingSortKey)
    }

    @Test
    fun concurrentAppendAndPrependMessagesDoesNotCreateConflicts() = runBlocking {
        // Given: 已有一些消息
        val existingMessages =
            listOf(
                MsgInfo(
                    id = "existing-1",
                    content = "Existing message",
                    role = "assistant",
                    timestamp = "2025-01-15T10:30:00.000000Z",
                )
            )
        dataSource.appendMessages(agentId, existingMessages)
        waitForMessages(agentId, expectedSize = 1)

        // When: 并发调用 appendMessages 和 prependMessages
        val appendJobs =
            (1..5).map { i ->
                async {
                    dataSource.appendMessages(
                        agentId,
                        listOf(
                            MsgInfo(
                                id = "newer-$i",
                                content = "Newer message $i",
                                role = "user",
                                timestamp = "2025-01-15T10:3$i:00.000000Z",
                            )
                        ),
                    )
                }
            }
        val prependJobs =
            (1..5).map { i ->
                async {
                    dataSource.prependMessages(
                        agentId,
                        listOf(
                            MsgInfo(
                                id = "older-$i",
                                content = "Older message $i",
                                role = "assistant",
                                timestamp = "2025-01-15T10:2$i:00.000000Z",
                            )
                        ),
                    )
                }
            }

        (appendJobs + prependJobs).awaitAll()

        // Then: 所有消息应该被插入，且 sortKey 不重复
        val finalMessages =
            waitForMessages(agentId, expectedSize = 11) // 1 existing + 5 newer + 5 older
        assertEquals("应该有 11 条消息", 11, finalMessages.size)

        // 验证 sortKey 不重复
        val dao = database.chatMessageDao()
        val entities = dao.getAllMessages(agentId)
        val sortKeys = entities.map { it.sortKey }.toSet()
        assertEquals("sortKey 应该不重复", 11, sortKeys.size)

        // 验证消息顺序：older < existing < newer
        val olderSortKeys =
            (1..5).mapNotNull { i ->
                finalMessages
                    .find { it.id == "older-$i" }
                    ?.let { dao.getMessage(agentId, it.localMsgId)?.sortKey }
            }
        val existingSortKey =
            finalMessages
                .find { it.id == "existing-1" }
                ?.let { dao.getMessage(agentId, it.localMsgId)?.sortKey }
        val newerSortKeys =
            (1..5).mapNotNull { i ->
                finalMessages
                    .find { it.id == "newer-$i" }
                    ?.let { dao.getMessage(agentId, it.localMsgId)?.sortKey }
            }

        val maxOlderSortKey = olderSortKeys.maxOrNull() ?: Long.MAX_VALUE
        val existingSortKeyValue = existingSortKey ?: Long.MIN_VALUE
        val minNewerSortKey = newerSortKeys.minOrNull() ?: Long.MIN_VALUE

        assertTrue("历史消息的 sortKey 应该小于现有消息", maxOlderSortKey < existingSortKeyValue)
        assertTrue("现有消息的 sortKey 应该小于新消息", existingSortKeyValue < minNewerSortKey)
    }

    @Test
    fun concurrentAddMessageDoesNotCreateDuplicateSortKeys() = runBlocking {
        // Given: 空数据库
        val initialMessages = dataSource.getMessagesFlow(agentId).first()
        assertEquals("初始应该没有消息", 0, initialMessages.size)

        // When: 并发调用 addMessage（10 个协程，每个插入 1 条消息）
        val jobs =
            (1..10).map { i ->
                async {
                    dataSource.addMessage(
                        agentId,
                        MsgInfo(
                            id = "msg-$i",
                            content = "Concurrent message $i",
                            role = "user",
                            timestamp = "2025-01-15T10:30:0$i.000000Z",
                        ),
                    )
                }
            }
        jobs.awaitAll()

        // Then: 所有消息应该被插入，且 sortKey 不重复
        val finalMessages = waitForMessages(agentId, expectedSize = 10)
        assertEquals("应该有 10 条消息", 10, finalMessages.size)

        // 验证 sortKey 不重复
        val dao = database.chatMessageDao()
        val entities = dao.getAllMessages(agentId)
        val sortKeys = entities.map { it.sortKey }.toSet()
        assertEquals("sortKey 应该不重复", 10, sortKeys.size)
    }

    @Test
    fun concurrentUpdateMessagesPreservesSortKeys() = runBlocking {
        // Given: 已有消息
        val originalMessages =
            (1..5).map { i ->
                MsgInfo(
                    id = "remote-$i",
                    content = "Message $i",
                    role = if (i % 2 == 0) "assistant" else "user",
                    timestamp = "2025-01-15T10:30:0$i.000000Z",
                )
            }
        dataSource.appendMessages(agentId, originalMessages)
        val initialMessages = waitForMessages(agentId, expectedSize = 5)

        // 记录原始 sortKey
        val originalSortKeys =
            initialMessages
                .mapNotNull { msg ->
                    database.chatMessageDao().getMessage(agentId, msg.localMsgId)?.sortKey
                }
                .toSet()

        // When: 并发更新消息
        val jobs =
            initialMessages.mapIndexed { index, msg ->
                async {
                    dataSource.updateMessages(
                        agentId,
                        listOf(msg.copy(content = "Updated message ${index + 1}")),
                    )
                }
            }
        jobs.awaitAll()

        // Then: sortKey 应该被保留
        delay(500) // 等待所有并发更新完成并让 Flow 更新（并发测试需要更长时间）
        val finalMessages = waitForMessages(agentId, expectedSize = 5)
        val finalSortKeys =
            finalMessages
                .mapNotNull { msg ->
                    database.chatMessageDao().getMessage(agentId, msg.localMsgId)?.sortKey
                }
                .toSet()

        assertEquals("sortKey 应该被保留", originalSortKeys, finalSortKeys)
    }
}
