package ai.sxwl.android.data.chat.data

import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.chat.local.db.ChatMessageEntity
import ai.sxwl.android.data.chat.local.db.IntyChatDatabase
import ai.sxwl.android.data.chat.local.db.toEntity
import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Before
import org.junit.Test
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

/**
 * RoomDataSource 单元测试
 * 使用真实的 Room 内存数据库进行测试
 * 
 * 使用 Robolectric 提供 Android 环境，可以创建真实的 Room 数据库实例
 */
@Config(sdk = [33])
@org.junit.runner.RunWith(RobolectricTestRunner::class)
class RoomDataSourceTest {

    private lateinit var database: IntyChatDatabase
    private lateinit var dataSource: RoomDataSource
    private val testDispatcher = StandardTestDispatcher()
    private val agentId = "test-agent-1"

    @Before
    fun setup() {
        Dispatchers.setMain(testDispatcher)

        // 使用真实的 Room 内存数据库
        val context = ApplicationProvider.getApplicationContext<Context>()
        database = Room.inMemoryDatabaseBuilder(context, IntyChatDatabase::class.java)
            .allowMainThreadQueries()
            .build()

        // 创建数据源实例
        dataSource = RoomDataSource(database = database, dispatcher = testDispatcher)
    }

    @After
    fun tearDown() {
        database.close()
    }

    @Test
    fun `getMessagesFlow 返回消息流`() = runTest(testDispatcher) {
        // Given: 插入测试消息到数据库
        val entities = listOf(
            createMessageEntity("msg-1", "Hello", "user"),
            createMessageEntity("msg-2", "Hi there", "assistant"),
        )
        database.chatMessageDao().upsert(entities)
        advanceUntilIdle()

        // When: 获取消息流
        val flow = dataSource.getMessagesFlow(agentId)
        // 等待 Flow 发出初始值
        val messages = flow.first { it.isNotEmpty() }

        // Then: 应该返回转换后的消息列表
        assertEquals(2, messages.size)
        assertEquals("Hello", messages[0].content)
        assertEquals("Hi there", messages[1].content)
    }

    // 辅助方法：创建测试用的消息实体
    private fun createMessageEntity(
        localId: String,
        content: String,
        role: String,
        sortKey: Long = System.nanoTime(),
    ): ChatMessageEntity {
        val message = MsgInfo(
            id = localId,
            content = content,
            role = role,
            timestamp = "2025-01-15T10:30:00.000000Z",
        )
        return message.toEntity(agentId, now = sortKey)
    }
}
