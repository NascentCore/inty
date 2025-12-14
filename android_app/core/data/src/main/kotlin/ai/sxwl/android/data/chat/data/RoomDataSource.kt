package ai.sxwl.android.data.chat.data

import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.chat.local.db.ChatMessageDao
import ai.sxwl.android.data.chat.local.db.ChatMessageEntity
import ai.sxwl.android.data.chat.local.db.ChatSyncStateDao
import ai.sxwl.android.data.chat.local.db.ChatSyncStateEntity
import ai.sxwl.android.data.chat.local.db.IntyChatDatabase
import ai.sxwl.android.data.chat.local.db.toEntity
import ai.sxwl.android.data.chat.local.db.toModel
import androidx.room.withTransaction
import java.util.concurrent.ConcurrentHashMap
import kotlin.math.max
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import mu.KotlinLogging

/**
 * 聊天本地数据源 使用 Room 作为单一可信数据源，遵循 Offline-First 设计：
 * - 所有 UI 读取来自本地数据库（StateFlow）
 * - 网络同步只负责刷新数据库
 * - 分页状态（hasMore/offset）持久化到 sync 表
 *
 * 目前还未接入 IntelliMate，是引入 Room IntelliMate 中的一步
 */
class RoomDataSource(
    private val database: IntyChatDatabase? = null,
    private val dispatcher: CoroutineDispatcher = Dispatchers.IO,
) {

    private val logger = KotlinLogging.logger {}

    // 延迟初始化数据库，避免在应用未初始化时调用Utils.getApp()
    private val db: IntyChatDatabase by lazy { database ?: IntyChatDatabase.getInstance() }

    private val scope = CoroutineScope(SupervisorJob() + dispatcher)
    private val messageDao: ChatMessageDao by lazy { db.chatMessageDao() }
    private val syncStateDao: ChatSyncStateDao by lazy { db.chatSyncStateDao() }

    private val messageFlows = ConcurrentHashMap<String, StateFlow<List<MsgInfo>>>()
    private val loadingFlows = ConcurrentHashMap<String, MutableStateFlow<Boolean>>()
    private val hasMoreFlows = ConcurrentHashMap<String, StateFlow<Boolean>>()

    fun getMessagesFlow(agentId: String): StateFlow<List<MsgInfo>> =
        messageFlows.getOrPut(agentId) {
            logger.debug { "RoomDataSource.getMessagesFlow creating new flow for agentId=$agentId" }
            messageDao
                .streamMessages(agentId)
                .map { list ->
                    logger.debug {
                        "RoomDataSource.getMessagesFlow received ${list.size} messages for agentId=$agentId"
                    }
                    list.map(ChatMessageEntity::toModel)
                }
                .stateIn(scope, SharingStarted.Eagerly, emptyList())
                .also { flow ->
                    logger.debug {
                        "RoomDataSource.getMessagesFlow initial value: ${flow.value.size} messages for agentId=$agentId"
                    }
                }
        }

    fun getLoadingMoreFlow(agentId: String): StateFlow<Boolean> = loadingFlow(agentId)

    fun getHasMoreFlow(agentId: String): StateFlow<Boolean> =
        hasMoreFlows.getOrPut(agentId) {
            syncStateDao
                .observe(agentId)
                .map { it?.hasMore ?: true }
                .stateIn(scope, SharingStarted.Eagerly, true)
        }

    suspend fun updateMessages(agentId: String, messages: List<MsgInfo>) =
        withContext(dispatcher) {
            logger.debug {
                "RoomDataSource.updateMessages updating ${messages.size} messages for agentId=$agentId"
            }
            // 获取现有消息，用于保留本地消息和去重
            val existingMessages = messageDao.getAllMessages(agentId)
            val existingMapByLocalId = existingMessages.associateBy { it.localId }
            val existingMapByRemoteId =
                existingMessages.filter { it.remoteId != null }.associateBy { it.remoteId!! }

            db.withTransaction {
                messageDao.deleteByAgent(agentId)
                if (messages.isNotEmpty()) {
                    // 创建服务器消息的键集合，用于去重和识别本地消息
                    val serverMessageKeys = mutableSetOf<String>()
                    messages.forEach { msg ->
                        val key = msg.id.ifEmpty { msg.localMsgId.ifEmpty { null } }
                        if (key != null) {
                            serverMessageKeys.add(key)
                        }
                    }

                    // 处理服务器消息：按列表顺序，确保 timestamp 正确设置
                    val baseTime = System.currentTimeMillis()
                    val serverEntities = messages.mapIndexed { index, msg ->
                        // 尝试匹配现有消息
                        val existingEntity =
                            when {
                                msg.localMsgId.isNotEmpty() -> {
                                    existingMapByLocalId[msg.localMsgId]
                                        ?: if (msg.id.isNotEmpty())
                                            existingMapByRemoteId[msg.id]
                                        else null
                                }
                                msg.id.isNotEmpty() -> {
                                    existingMapByRemoteId[msg.id]
                                        ?: existingMapByLocalId[msg.id]
                                }
                                else -> null
                            }

                        // 确保 timestamp 存在：优先使用服务器返回的 timestamp，否则使用列表索引生成
                        val messageWithTimestamp =
                            if (msg.timestamp.isNullOrEmpty()) {
                                // 如果服务器消息没有 timestamp，根据列表索引生成递增的时间戳
                                // 列表顺序即为排序依据，索引越大（越靠后）时间戳越大
                                val generatedTimestamp =
                                    java.time.Instant.ofEpochMilli(baseTime + index * 1000)
                                        .toString()
                                msg.copy(timestamp = generatedTimestamp)
                            } else {
                                msg
                            }

                        messageWithTimestamp.toEntity(agentId, existing = existingEntity)
                    }

                    // 保留不在服务器消息列表中的本地消息
                    val localEntities = existingMessages
                        .filter { entity ->
                            val key = entity.remoteId ?: entity.localId
                            key !in serverMessageKeys
                        }
                        .map { entity ->
                            // 保持本地消息的 timestamp，如果不存在则使用 createdAt
                            val localTimestamp =
                                entity.timestamp
                                    ?: java.time.Instant.ofEpochMilli(entity.createdAt).toString()
                            val msg = entity.toModel()
                            msg.copy(timestamp = localTimestamp).toEntity(agentId, existing = entity)
                        }

                    // 合并服务器消息和本地消息，服务器消息在前（按列表顺序）
                    val allEntities = serverEntities + localEntities

                    messageDao.upsert(allEntities)
                }
                // 如果 messages 为空，deleteByAgent 已经删除了所有消息，Flow 会自动更新
            }
            logger.debug {
                "RoomDataSource.updateMessages updated messages, current flow value: ${getMessagesFlow(agentId).value.size}"
            }
        }

    suspend fun appendMessages(agentId: String, newMessages: List<MsgInfo>) =
        withContext(dispatcher) {
            if (newMessages.isEmpty()) return@withContext
            logger.debug {
                "RoomDataSource.appendMessages saving ${newMessages.size} messages for agentId=$agentId"
            }
            // 在事务中原子性地读取最大 timestamp 并插入消息，避免并发竞争
            db.withTransaction {
                val existingMessages = messageDao.getAllMessages(agentId)
                // 获取现有消息的最大 timestamp（转换为毫秒）
                val maxTimestampMs =
                    existingMessages
                        .mapNotNull { entity ->
                            entity.timestamp?.let { ts ->
                                try {
                                    java.time.Instant.parse(ts).toEpochMilli()
                                } catch (e: Exception) {
                                    null
                                }
                            } ?: entity.createdAt
                        }
                        .maxOrNull() ?: 0L

                val baseTime = max(System.currentTimeMillis(), maxTimestampMs + 1)
                messageDao.upsert(
                    newMessages.mapIndexed { index, msg ->
                        // 为每个消息生成递增的 timestamp（ISO 8601 格式）
                        val timestamp =
                            java.time.Instant.ofEpochMilli(baseTime + index * 1000).toString()
                        val msgWithTimestamp =
                            if (msg.timestamp.isNullOrEmpty()) {
                                msg.copy(timestamp = timestamp)
                            } else {
                                msg
                            }
                        msgWithTimestamp.toEntity(agentId)
                    }
                )
            }
            logger.debug {
                "RoomDataSource.appendMessages saved messages, current flow value: ${getMessagesFlow(agentId).value.size}"
            }
        }

    suspend fun prependMessages(agentId: String, newMessages: List<MsgInfo>) =
        withContext(dispatcher) {
            if (newMessages.isEmpty()) return@withContext
            logger.debug {
                "RoomDataSource.prependMessages prepending ${newMessages.size} messages for agentId=$agentId"
            }
            // 在事务中原子性地读取最小 timestamp 并插入消息，避免并发竞争
            db.withTransaction {
                val existingMessages = messageDao.getAllMessages(agentId)
                // 获取现有消息的最小 timestamp（转换为毫秒）
                val minTimestampMs =
                    existingMessages
                        .mapNotNull { entity ->
                            entity.timestamp?.let { ts ->
                                try {
                                    java.time.Instant.parse(ts).toEpochMilli()
                                } catch (e: Exception) {
                                    null
                                }
                            } ?: entity.createdAt
                        }
                        .minOrNull()

                val baseTime =
                    if (minTimestampMs != null && minTimestampMs > 0) {
                        // 如果已有消息，新消息的 timestamp 应该比最小 timestamp 更小
                        minTimestampMs - newMessages.size * 1000 - 1000
                    } else {
                        // 如果还没有消息，使用当前时间作为基准
                        System.currentTimeMillis()
                    }

                messageDao.upsert(
                    newMessages.mapIndexed { index, msg ->
                        // 为每个消息生成递减的 timestamp（ISO 8601 格式）
                        // 索引越大，timestamp 越小（因为要插入到列表开头）
                        val timestamp =
                            java.time.Instant.ofEpochMilli(baseTime + index * 1000).toString()
                        val msgWithTimestamp =
                            if (msg.timestamp.isNullOrEmpty()) {
                                msg.copy(timestamp = timestamp)
                            } else {
                                msg
                            }
                        msgWithTimestamp.toEntity(agentId)
                    }
                )
            }
            logger.debug {
                "RoomDataSource.prependMessages prepended messages, current flow value: ${getMessagesFlow(agentId).value.size}"
            }
        }

    suspend fun setLoadingMore(agentId: String, loading: Boolean) {
        loadingFlow(agentId).value = loading
    }

    suspend fun setHasMore(agentId: String, hasMore: Boolean) =
        updateSyncState(agentId) { it.copy(hasMore = hasMore) }

    suspend fun setInitialLoaded(agentId: String, loaded: Boolean) =
        updateSyncState(agentId) { it.copy(isInitialLoaded = loaded, lastSyncedAt = now()) }

    suspend fun isInitialLoaded(agentId: String): Boolean =
        withContext(dispatcher) { syncStateDao.get(agentId)?.isInitialLoaded ?: false }

    suspend fun setOffset(agentId: String, offset: Int) =
        updateSyncState(agentId) { it.copy(offset = max(0, offset)) }

    suspend fun getOffset(agentId: String): Int =
        withContext(dispatcher) { syncStateDao.get(agentId)?.offset ?: 0 }

    suspend fun incrementOffset(agentId: String, increment: Int) =
        updateSyncState(agentId) { current ->
            current.copy(offset = max(0, current.offset + increment))
        }

    fun updateMessageAudioUrl(agentId: String, messageId: String, audioUrl: String) {
        scope.launch { messageDao.updateAudioUrl(agentId, messageId, audioUrl, now()) }
    }

    fun updateMessageFeedback(agentId: String, messageId: String, feedback: MsgInfo.UserFeedback?) {
        scope.launch { messageDao.updateUserFeedback(agentId, messageId, feedback?.name, now()) }
    }

    suspend fun updateMessage(agentId: String, messageId: String, updatedMessage: MsgInfo) =
        withContext(dispatcher) {
            val existing = messageDao.getMessage(agentId, messageId)
            messageDao.upsert(updatedMessage.toEntity(agentId, existing))
        }

    fun updateMessageGeneratedImage(
        agentId: String,
        messageId: String,
        generatedImage: MsgInfo.MsgMetaData.GeneratedImage?,
    ) {
        scope.launch {
            messageDao.updateGeneratedImage(
                agentId = agentId,
                messageId = messageId,
                url = generatedImage?.imageUrl,
                width = generatedImage?.width,
                height = generatedImage?.height,
                updatedAt = now(),
            )
        }
    }

    suspend fun removeMessage(agentId: String, messageId: String) =
        withContext(dispatcher) { messageDao.deleteMessage(agentId, messageId) }

    suspend fun addMessage(agentId: String, message: MsgInfo) =
        withContext(dispatcher) {
            // 在事务中原子性地读取最大 timestamp 并插入消息，避免并发竞争
            db.withTransaction {
                val existingMessages = messageDao.getAllMessages(agentId)
                // 获取现有消息的最大 timestamp（转换为毫秒）
                val maxTimestampMs =
                    existingMessages
                        .mapNotNull { entity ->
                            entity.timestamp?.let { ts ->
                                try {
                                    java.time.Instant.parse(ts).toEpochMilli()
                                } catch (e: Exception) {
                                    null
                                }
                            } ?: entity.createdAt
                        }
                        .maxOrNull() ?: 0L

                val timestampMs = max(System.currentTimeMillis(), maxTimestampMs + 1)
                val timestamp =
                    if (message.timestamp.isNullOrEmpty()) {
                        java.time.Instant.ofEpochMilli(timestampMs).toString()
                    } else {
                        message.timestamp
                    }

                val messageWithTimestamp = message.copy(timestamp = timestamp)
                messageDao.upsert(messageWithTimestamp.toEntity(agentId))
            }
        }

    suspend fun clearChatData(agentId: String) =
        withContext(dispatcher) {
            logger.debug { "RoomDataSource.clearChatData starting for agent $agentId" }
            db.withTransaction {
                messageDao.deleteByAgent(agentId)
                syncStateDao.delete(agentId)
            }
            // 等待数据库操作完成后再清理内存状态和设置
            loadingFlows.remove(agentId)
            messageFlows.remove(agentId)
            hasMoreFlows.remove(agentId)
            logger.info { "RoomDataSource cleared chat data for agent $agentId" }
        }

    suspend fun clearAllChatData() =
        withContext(dispatcher) {
            logger.debug { "RoomDataSource.clearAllChatData starting" }
            db.withTransaction {
                messageDao.deleteAll()
                syncStateDao.deleteAll()
            }
            // 等待数据库操作完成后再清理内存状态和设置
            loadingFlows.clear()
            messageFlows.clear()
            hasMoreFlows.clear()
            logger.info { "RoomDataSource cleared all chat data" }
        }

    private suspend fun updateSyncState(
        agentId: String,
        updater: (ChatSyncStateEntity) -> ChatSyncStateEntity,
    ) =
        withContext(dispatcher) {
            val current = syncStateDao.get(agentId) ?: ChatSyncStateEntity(agentId = agentId)
            syncStateDao.upsert(updater(current).copy(updatedAt = now()))
        }

    private fun loadingFlow(agentId: String): MutableStateFlow<Boolean> =
        loadingFlows.getOrPut(agentId) { MutableStateFlow(false) }

    private fun now(): Long = System.currentTimeMillis()
}
