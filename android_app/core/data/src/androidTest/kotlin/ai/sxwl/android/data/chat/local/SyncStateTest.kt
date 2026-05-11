package ai.sxwl.android.data.chat.local

// CREATED_BY_AGENT

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
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

/** 测试同步状态管理 验证 hasMore/offset/isInitialLoaded 的状态管理 */
@RunWith(AndroidJUnit4::class)
class SyncStateTest {

    private lateinit var database: IntyChatDatabase
    private lateinit var dataSource: RoomDataSource
    private val agentId = "test-agent-sync"

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

    private suspend fun waitForFlowValue(
        flow: kotlinx.coroutines.flow.StateFlow<Boolean>,
        expectedValue: Boolean,
        timeout: Long = 5000,
    ): Boolean {
        return withTimeout(timeout) {
            var value: Boolean
            do {
                value = flow.first()
                if (value != expectedValue) {
                    delay(50)
                }
            } while (value != expectedValue)
            value
        }
    }

    @Test
    fun setHasMoreAndGetHasMoreFlow() = runBlocking {
        // Given: 初始状态（默认 true）
        val hasMoreFlow = dataSource.getHasMoreFlow(agentId)
        assertTrue("初始 hasMore 应该为 true", hasMoreFlow.value)

        // When: 设置 hasMore 为 false
        dataSource.setHasMore(agentId, false)

        // Then: Flow 应该更新为 false
        val updatedValue = waitForFlowValue(hasMoreFlow, false)
        assertFalse("hasMore 应该更新为 false", updatedValue)

        // When: 设置 hasMore 为 true
        dataSource.setHasMore(agentId, true)

        // Then: Flow 应该更新为 true
        val updatedValue2 = waitForFlowValue(hasMoreFlow, true)
        assertTrue("hasMore 应该更新为 true", updatedValue2)
    }

    @Test
    fun setOffsetAndGetOffset() = runBlocking {
        // Given: 初始 offset 为 0
        val initialOffset = dataSource.getOffset(agentId)
        assertEquals("初始 offset 应该为 0", 0, initialOffset)

        // When: 设置 offset 为 20
        dataSource.setOffset(agentId, 20)

        // Then: offset 应该为 20
        val offset = dataSource.getOffset(agentId)
        assertEquals("offset 应该为 20", 20, offset)

        // When: 设置 offset 为 40
        dataSource.setOffset(agentId, 40)

        // Then: offset 应该为 40
        val offset2 = dataSource.getOffset(agentId)
        assertEquals("offset 应该为 40", 40, offset2)
    }

    @Test
    fun setOffsetWithNegativeValueBecomesZero() = runBlocking {
        // Given: 初始 offset 为 0
        val initialOffset = dataSource.getOffset(agentId)
        assertEquals("初始 offset 应该为 0", 0, initialOffset)

        // When: 设置 offset 为负数
        dataSource.setOffset(agentId, -10)

        // Then: offset 应该为 0（max(0, offset)）
        val offset = dataSource.getOffset(agentId)
        assertEquals("负数 offset 应该变为 0", 0, offset)
    }

    @Test
    fun incrementOffset() = runBlocking {
        // Given: 初始 offset 为 0
        val initialOffset = dataSource.getOffset(agentId)
        assertEquals("初始 offset 应该为 0", 0, initialOffset)

        // When: 增加 offset 20
        dataSource.incrementOffset(agentId, 20)

        // Then: offset 应该为 20
        val offset = dataSource.getOffset(agentId)
        assertEquals("offset 应该增加为 20", 20, offset)

        // When: 再增加 offset 20
        dataSource.incrementOffset(agentId, 20)

        // Then: offset 应该为 40
        val offset2 = dataSource.getOffset(agentId)
        assertEquals("offset 应该增加为 40", 40, offset2)
    }

    @Test
    fun incrementOffsetWithNegativeValue() = runBlocking {
        // Given: offset 为 20
        dataSource.setOffset(agentId, 20)
        assertEquals("offset 应该为 20", 20, dataSource.getOffset(agentId))

        // When: 增加负数 offset（减少）
        dataSource.incrementOffset(agentId, -30)

        // Then: offset 应该为 0（max(0, 20 + (-30)) = max(0, -10) = 0）
        val offset = dataSource.getOffset(agentId)
        assertEquals("offset 减少后应该为 0（不能为负数）", 0, offset)
    }

    @Test
    fun setInitialLoadedAndIsInitialLoaded() = runBlocking {
        // Given: 初始状态为 false
        val initialLoaded = dataSource.isInitialLoaded(agentId)
        assertFalse("初始 isInitialLoaded 应该为 false", initialLoaded)

        // When: 设置 isInitialLoaded 为 true
        dataSource.setInitialLoaded(agentId, true)

        // Then: isInitialLoaded 应该为 true
        val loaded = dataSource.isInitialLoaded(agentId)
        assertTrue("isInitialLoaded 应该为 true", loaded)

        // When: 设置 isInitialLoaded 为 false
        dataSource.setInitialLoaded(agentId, false)

        // Then: isInitialLoaded 应该为 false
        val loaded2 = dataSource.isInitialLoaded(agentId)
        assertFalse("isInitialLoaded 应该为 false", loaded2)
    }

    @Test
    fun setLoadingMoreAndGetLoadingMoreFlow() = runBlocking {
        // Given: 初始状态为 false
        val loadingFlow = dataSource.getLoadingMoreFlow(agentId)
        assertFalse("初始 loading 应该为 false", loadingFlow.value)

        // When: 设置 loading 为 true
        dataSource.setLoadingMore(agentId, true)

        // Then: Flow 应该立即更新为 true（MutableStateFlow）
        assertTrue("loading 应该更新为 true", loadingFlow.value)

        // When: 设置 loading 为 false
        dataSource.setLoadingMore(agentId, false)

        // Then: Flow 应该立即更新为 false
        assertFalse("loading 应该更新为 false", loadingFlow.value)
    }

    @Test
    fun syncStateIsIsolatedPerAgentId() = runBlocking {
        // Given: 两个不同的 agentId
        val agentId1 = "agent-1"
        val agentId2 = "agent-2"

        // When: 为 agentId1 设置状态
        dataSource.setHasMore(agentId1, false)
        dataSource.setOffset(agentId1, 20)
        dataSource.setInitialLoaded(agentId1, true)

        // 等待 Flow 更新（因为 getHasMoreFlow 使用 SharingStarted.Eagerly，需要等待数据库更新）
        delay(100)

        // Then: agentId2 的状态应该不受影响（默认值）
        val hasMore2 = dataSource.getHasMoreFlow(agentId2).value
        val offset2 = dataSource.getOffset(agentId2)
        val initialLoaded2 = dataSource.isInitialLoaded(agentId2)

        assertTrue("agentId2 的 hasMore 应该为默认值 true", hasMore2)
        assertEquals("agentId2 的 offset 应该为默认值 0", 0, offset2)
        assertFalse("agentId2 的 isInitialLoaded 应该为默认值 false", initialLoaded2)

        // 验证 agentId1 的状态保持不变
        val hasMore1 = waitForFlowValue(dataSource.getHasMoreFlow(agentId1), false)
        val offset1 = dataSource.getOffset(agentId1)
        val initialLoaded1 = dataSource.isInitialLoaded(agentId1)

        assertFalse("agentId1 的 hasMore 应该为 false", hasMore1)
        assertEquals("agentId1 的 offset 应该为 20", 20, offset1)
        assertTrue("agentId1 的 isInitialLoaded 应该为 true", initialLoaded1)
    }
}
