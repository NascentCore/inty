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

    suspend fun getMessages(agentId: String): List<MsgInfo> {
        return messageDao.getAllMessages(agentId).map(ChatMessageEntity::toModel)
    }

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

    fun getMessagesWithImagesFlow(agentId: String): StateFlow<List<MsgInfo>> =
        messageDao
            .streamMessagesWithImages(agentId)
            .map { list ->
                logger.debug {
                    "RoomDataSource.getMessagesWithImagesFlow received ${list.size} messages with images for agentId=$agentId"
                }
                list.map(ChatMessageEntity::toModel)
            }
            .stateIn(scope, SharingStarted.Eagerly, emptyList())

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
            // 在事务之前获取现有消息以保留它们的sortKey
            val existingMessages =
                messageDao.getAllMessages(agentId).filterNot {
                    it.content == "loading_animation" && it.role == "assistant"
                }
            // 创建现有消息的映射表，以localId为key，也支持remoteId匹配
            val existingMapByLocalId = existingMessages.associateBy { it.localId }
            val existingMapByRemoteId =
                existingMessages.filter { it.remoteId != null }.associateBy { it.remoteId!! }

            db.withTransaction {
                messageDao.deleteByAgent(agentId)
                if (messages.isNotEmpty()) {
                    // 为消息分配sortKey，优先使用现有的sortKey以保持稳定
                    val lastSortKey = existingMessages.maxOfOrNull { it.sortKey } ?: 0L
                    val baseTime = max(System.nanoTime(), lastSortKey + 1)
                    var currentSortKey = baseTime

                    // 先匹配所有消息，收集已使用的 sortKey，避免冲突
                    val usedSortKeys = mutableSetOf<Long>()

                    messageDao.upsert(
                        messages.map { msg ->
                            // 尝试从现有消息中获取sortKey
                            // 匹配逻辑：
                            // 1. 如果 msg.localMsgId 不为空，优先使用 localMsgId 匹配 existingMapByLocalId
                            // 2. 如果 msg.id 不为空，使用 id 匹配 existingMapByRemoteId
                            // 3. 如果都匹配不到，使用新的 sortKey
                            val existingEntity =
                                when {
                                    msg.localMsgId.isNotEmpty() -> {
                                        existingMapByLocalId[msg.localMsgId]
                                            ?: if (msg.id.isNotEmpty())
                                                existingMapByRemoteId[msg.id]
                                            else null
                                    }
                                    msg.id.isNotEmpty() -> {
                                        // 先尝试通过 remoteId 匹配，如果失败，再尝试通过 localId 匹配（因为 localId 可能等于
                                        // id）
                                        existingMapByRemoteId[msg.id]
                                            ?: existingMapByLocalId[msg.id]
                                    }
                                    else -> null
                                }

                            val sortKey =
                                if (existingEntity != null) {
                                    // 使用现有消息的 sortKey，并将其加入 usedSortKeys 以避免冲突
                                    val reusedSortKey = existingEntity.sortKey
                                    usedSortKeys.add(reusedSortKey)
                                    reusedSortKey
                                } else {
                                    // 为新消息分配 sortKey，确保不与已使用的 sortKey 冲突
                                    while (
                                        usedSortKeys.contains(currentSortKey) ||
                                            existingMessages.any { it.sortKey == currentSortKey }
                                    ) {
                                        currentSortKey++
                                    }
                                    val newSortKey = currentSortKey++
                                    usedSortKeys.add(newSortKey)
                                    newSortKey
                                }

                            msg.toEntity(agentId, existing = existingEntity, now = sortKey)
                        }
                    )
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
            // 在事务中原子性地读取sortKey并插入消息，避免并发竞争
            db.withTransaction {
                val lastSortKey = messageDao.getMaxSortKey(agentId) ?: 0L
                val baseTime = max(System.nanoTime(), lastSortKey + 1)
                var currentSortKey = baseTime
                messageDao.upsert(
                    newMessages.map { msg ->
                        val sortKey = currentSortKey++
                        msg.toEntity(agentId, now = sortKey)
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
            // 在事务中原子性地读取sortKey并插入消息，避免并发竞争
            db.withTransaction {
                val minSortKey = messageDao.getMinSortKey(agentId) ?: 0L
                // 如果已有消息，新消息的sortKey应该比最小sortKey更小
                // 如果还没有消息，使用当前时间作为基准
                val baseTime =
                    if (minSortKey > 0) {
                        minSortKey - newMessages.size - 1
                    } else {
                        System.nanoTime()
                    }
                var currentSortKey = baseTime
                messageDao.upsert(
                    newMessages.map { msg ->
                        val sortKey = currentSortKey++
                        msg.toEntity(agentId, now = sortKey)
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
            // 在事务中原子性地读取sortKey并插入消息，避免并发竞争
            db.withTransaction {
                val lastSortKey = messageDao.getMaxSortKey(agentId) ?: 0L
                val sortKey = max(System.nanoTime(), lastSortKey + 1)
                messageDao.upsert(message.toEntity(agentId, now = sortKey))
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

    /** 获取指定agent的最后一条消息的sortKey，用于确保新消息的sortKey单调递增 */
    suspend fun getLastSortKey(agentId: String): Long =
        withContext(dispatcher) { messageDao.getMaxSortKey(agentId) ?: 0L }

    /** 获取指定agent的第一条消息的sortKey，用于prependMessages */
    private suspend fun getMinSortKey(agentId: String): Long =
        withContext(dispatcher) { messageDao.getMinSortKey(agentId) ?: 0L }

    private fun now(): Long = System.currentTimeMillis()
}
