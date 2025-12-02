package ai.sxwl.android.data.chat.local

// CREATED_BY_AGENT

import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.chat.data.RoomDataSource
import ai.sxwl.android.data.chat.local.db.IntyChatDatabase
import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import java.time.Instant
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Hermetic tests for timestamp behavior in Room database. These tests verify that:
 * 1. Server timestamps are preserved when syncing messages
 * 2. Local messages get timestamps set correctly
 * 3. Timestamps are preserved during updates
 * 4. sortKey and timestamp are independent
 */
@RunWith(AndroidJUnit4::class)
class ChatTimestampTest {

    private lateinit var database: IntyChatDatabase
    private lateinit var dataSource: RoomDataSource
    private val agentId = "test-agent-1"

    /**
     * Helper function to wait for Flow to emit after database changes. Room Flows emit when the
     * database changes, but we need to wait for the emission.
     */
    private suspend fun waitForMessages(agentId: String, expectedSize: Int? = null): List<MsgInfo> {
        val flow = dataSource.getMessagesFlow(agentId)
        // Check current value first (StateFlow always has a value)
        val currentValue = flow.value
        if (expectedSize != null && currentValue.size == expectedSize) {
            return currentValue
        }
        // Wait for Flow to emit after database change
        // Filter out empty lists and wait for the expected size
        return withTimeout(5000) {
            if (expectedSize != null) {
                flow.first { it.size == expectedSize }
            } else {
                flow.first { it.isNotEmpty() }
            }
        }
    }

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
    fun tearDown() = runBlocking {
        // Wait a bit for any pending Flow emissions to complete
        delay(100)
        database.close()
    }

    @Test
    fun serverMessageWithTimestampPreservesServerTimestamp() = runBlocking {
        // Given: A server message with a timestamp
        val serverTimestamp = "2025-01-15T10:30:45.123456Z"
        val serverMessage =
            MsgInfo(
                id = "server-msg-1",
                content = "Hello from server",
                role = "assistant",
                timestamp = serverTimestamp,
            )

        // When: Inserting the message
        dataSource.appendMessages(agentId, listOf(serverMessage))

        // Then: The timestamp should be preserved
        val messages = waitForMessages(agentId, expectedSize = 1)
        assertEquals(serverTimestamp, messages[0].timestamp)
    }

    @Test
    fun localMessageWithoutTimestampGetsTimestampFromSortKey() = runBlocking {
        // Given: A local message without timestamp (e.g., user message before sending)
        val localMessage =
            MsgInfo(
                content = "Local message",
                role = "user",
                // No timestamp field
            )

        // When: Inserting the message
        dataSource.appendMessages(agentId, listOf(localMessage))

        // Then: The message should have a timestamp (from sortKey conversion)
        val messages = waitForMessages(agentId, expectedSize = 1)
        assertNotNull("Message should have timestamp", messages[0].timestamp)
        // Verify timestamp is valid ISO format
        assertNotNull("Timestamp should be parseable", Instant.parse(messages[0].timestamp!!))
    }

    @Test
    fun updateMessagesPreservesExistingTimestampsWhenUpdating() = runBlocking {
        // Given: A message with a server timestamp
        val originalTimestamp = "2025-01-15T10:30:45.123456Z"
        val originalMessage =
            MsgInfo(
                id = "msg-1",
                content = "Original content",
                role = "assistant",
                timestamp = originalTimestamp,
            )
        dataSource.appendMessages(agentId, listOf(originalMessage))

        // When: Updating the message (e.g., during sync) without providing timestamp
        val updatedMessage =
            MsgInfo(
                id = "msg-1",
                content = "Updated content",
                role = "assistant",
                // No timestamp - should preserve existing
            )
        dataSource.updateMessages(agentId, listOf(updatedMessage))

        // Then: The timestamp should be preserved
        val messages = waitForMessages(agentId, expectedSize = 1)
        assertEquals(originalTimestamp, messages[0].timestamp)
    }

    @Test
    fun updateMessagesUpdatesTimestampWhenNewTimestampIsProvided() = runBlocking {
        // Given: A message with an old timestamp
        val oldTimestamp = "2025-01-15T10:30:45.123456Z"
        val originalMessage =
            MsgInfo(
                id = "msg-1",
                content = "Original content",
                role = "assistant",
                timestamp = oldTimestamp,
            )
        dataSource.appendMessages(agentId, listOf(originalMessage))

        // When: Updating with a new timestamp from server
        val newTimestamp = "2025-01-15T10:35:00.789012Z"
        val updatedMessage =
            MsgInfo(
                id = "msg-1",
                content = "Updated content",
                role = "assistant",
                timestamp = newTimestamp,
            )
        dataSource.updateMessages(agentId, listOf(updatedMessage))

        // Then: The timestamp should be updated
        delay(100) // 等待 Flow 更新
        val messages = waitForMessages(agentId, expectedSize = 1)
        assertEquals(newTimestamp, messages[0].timestamp)
    }

    @Test
    fun multipleServerMessagesPreserveTheirIndividualTimestamps() = runBlocking {
        // Given: Multiple server messages with different timestamps
        val messages =
            listOf(
                MsgInfo(
                    id = "msg-1",
                    content = "First message",
                    role = "assistant",
                    timestamp = "2025-01-15T10:30:45.123456Z",
                ),
                MsgInfo(
                    id = "msg-2",
                    content = "Second message",
                    role = "assistant",
                    timestamp = "2025-01-15T10:31:00.654321Z",
                ),
                MsgInfo(
                    id = "msg-3",
                    content = "Third message",
                    role = "user",
                    timestamp = "2025-01-15T10:31:15.987654Z",
                ),
            )

        // When: Inserting all messages
        dataSource.updateMessages(agentId, messages)

        // Then: All timestamps should be preserved
        val storedMessages = waitForMessages(agentId, expectedSize = 3)
        assertEquals(
            "2025-01-15T10:30:45.123456Z",
            storedMessages.find { it.id == "msg-1" }?.timestamp,
        )
        assertEquals(
            "2025-01-15T10:31:00.654321Z",
            storedMessages.find { it.id == "msg-2" }?.timestamp,
        )
        assertEquals(
            "2025-01-15T10:31:15.987654Z",
            storedMessages.find { it.id == "msg-3" }?.timestamp,
        )
    }

    @Test
    fun sortKeyAndTimestampAreIndependent() = runBlocking {
        // Given: Messages with timestamps that don't match sortKey order
        val earlierTimestamp = "2025-01-15T10:30:00.000000Z"
        val laterTimestamp = "2025-01-15T10:35:00.000000Z"

        // Insert first message (will get sortKey = baseTime)
        val message1 =
            MsgInfo(
                id = "msg-1",
                content = "First",
                role = "assistant",
                timestamp = laterTimestamp, // Later timestamp
            )
        dataSource.appendMessages(agentId, listOf(message1))

        // Insert second message (will get sortKey = baseTime + 1)
        val message2 =
            MsgInfo(
                id = "msg-2",
                content = "Second",
                role = "assistant",
                timestamp = earlierTimestamp, // Earlier timestamp
            )
        dataSource.appendMessages(agentId, listOf(message2))

        // Then: Messages should be ordered by sortKey (not timestamp)
        // Message 1 should appear first (lower sortKey), Message 2 second (higher sortKey)
        val messages = waitForMessages(agentId, expectedSize = 2)
        // Messages are ordered by sortKey DESC, so newest first
        assertEquals("msg-2", messages[0].id) // Second inserted, higher sortKey
        assertEquals("msg-1", messages[1].id) // First inserted, lower sortKey

        // But timestamps should be preserved as-is
        assertEquals(laterTimestamp, messages.find { it.id == "msg-1" }?.timestamp)
        assertEquals(earlierTimestamp, messages.find { it.id == "msg-2" }?.timestamp)
    }

    @Test
    fun prependMessagesPreservesTimestamps() = runBlocking {
        // Given: Existing messages
        val existingMessage =
            MsgInfo(
                id = "existing-1",
                content = "Existing",
                role = "assistant",
                timestamp = "2025-01-15T10:30:00.000000Z",
            )
        dataSource.appendMessages(agentId, listOf(existingMessage))

        // When: Prepending older messages
        val olderMessage =
            MsgInfo(
                id = "older-1",
                content = "Older",
                role = "assistant",
                timestamp = "2025-01-15T10:25:00.000000Z",
            )
        dataSource.prependMessages(agentId, listOf(olderMessage))

        // Then: Both messages should have their timestamps preserved
        val messages = waitForMessages(agentId, expectedSize = 2)
        assertEquals("2025-01-15T10:25:00.000000Z", messages.find { it.id == "older-1" }?.timestamp)
        assertEquals(
            "2025-01-15T10:30:00.000000Z",
            messages.find { it.id == "existing-1" }?.timestamp,
        )
    }

    @Test
    fun appendMessagesWithServerTimestampsPreservesAllTimestamps() = runBlocking {
        // Given: Multiple messages to append
        val messages =
            listOf(
                MsgInfo(
                    id = "append-1",
                    content = "First",
                    role = "user",
                    timestamp = "2025-01-15T10:30:00.111111Z",
                ),
                MsgInfo(
                    id = "append-2",
                    content = "Second",
                    role = "assistant",
                    timestamp = "2025-01-15T10:30:05.222222Z",
                ),
            )

        // When: Appending messages
        dataSource.appendMessages(agentId, messages)

        // Then: All timestamps should be preserved
        val storedMessages = waitForMessages(agentId, expectedSize = 2)
        assertEquals(
            "2025-01-15T10:30:00.111111Z",
            storedMessages.find { it.id == "append-1" }?.timestamp,
        )
        assertEquals(
            "2025-01-15T10:30:05.222222Z",
            storedMessages.find { it.id == "append-2" }?.timestamp,
        )
    }

    @Test
    fun messageWithoutTimestampAndWithoutExistingEntityGetsTimestamp() = runBlocking {
        // Given: A completely new message without timestamp
        val newMessage =
            MsgInfo(
                content = "New message",
                role = "user",
                // No id, no timestamp
            )

        // When: Adding the message
        dataSource.addMessage(agentId, newMessage)

        // Then: The message should have a timestamp
        val messages = waitForMessages(agentId, expectedSize = 1)
        assertNotNull("Message should have timestamp", messages[0].timestamp)
        // Verify it's a valid ISO timestamp
        assertNotNull("Timestamp should be parseable", Instant.parse(messages[0].timestamp!!))
    }

    @Test
    fun updateMessagePreservesTimestampWhenNotProvided() = runBlocking {
        // Given: A message with a timestamp
        val originalTimestamp = "2025-01-15T10:30:45.123456Z"
        val originalMessage =
            MsgInfo(
                id = "update-1",
                content = "Original",
                role = "assistant",
                timestamp = originalTimestamp,
            )
        dataSource.appendMessages(agentId, listOf(originalMessage))

        // When: Updating the message without providing timestamp
        val updatedMessage =
            originalMessage.copy(
                content = "Updated",
                timestamp = null, // Explicitly null
            )
        val storedMessages = waitForMessages(agentId, expectedSize = 1)
        val localMsgId = storedMessages[0].localMsgId
        dataSource.updateMessage(agentId, localMsgId, updatedMessage)

        // Then: The timestamp should be preserved
        val finalMessages = waitForMessages(agentId, expectedSize = 1)
        assertEquals(originalTimestamp, finalMessages[0].timestamp)
    }
}
