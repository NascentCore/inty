package com.ai.inty.newchat.data
import ai.sxwl.android.data.api.IAgentApi
import ai.sxwl.android.data.api.IChatApi
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.api.model.ConversationItem
import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.api.model.SendMsgReq
import ai.sxwl.android.utils.LogUtils
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * 消息状态枚举
 */
enum class MessageStatus {
    SENDING, SENT, FAILED
}

/**
 * 消息事件类型
 */
sealed class MessageEvent {
    data class MessageAdded(val agentId: String, val message: MsgInfo) : MessageEvent()
    data class MessageUpdated(
        val agentId: String,
        val messageId: String,
        val status: MessageStatus
    ) : MessageEvent()

    data class MessagesUpdated(val agentId: String, val messages: List<MsgInfo>) : MessageEvent()
    data class MessageDeleted(val agentId: String, val messageId: String) : MessageEvent()
}

/**
 * 错误事件（携带本地消息ID以便前端精确匹配）
 */
data class ErrorEvent(
    val agentId: String,
    val message: String,
    val localMessageId: String,
)

/**
 * 全局聊天数据管理器
 * 负责统一管理所有聊天数据，实现多UI数据同步
 */
class ChatDataManager(
    private val chatApi: IChatApi,
    private val agentApi: IAgentApi,
    private val coroutineScope: CoroutineScope
) {

    // 按Agent分组的消息缓存
    private val messagesCache = mutableMapOf<String, MutableStateFlow<List<MsgInfo>>>()

    // 按Agent分组的AgentInfo数据流
    private val agentInfosCache = mutableMapOf<String, MutableStateFlow<AgentInfo?>>()

    // 消息事件总线 - 用于跨组件通信
    private val _messageEvents = MutableSharedFlow<MessageEvent>()
    val messageEvents: SharedFlow<MessageEvent> = _messageEvents.asSharedFlow()

    // 错误事件总线
    private val _errorEvents = MutableSharedFlow<ErrorEvent>(
        replay = 0,
        extraBufferCapacity = 64
    )
    val errorEvents: SharedFlow<ErrorEvent> = _errorEvents.asSharedFlow()

    // 当前活跃的Agent
    private val _activeAgentId = MutableStateFlow<String?>(null)
    val activeAgentId: StateFlow<String?> = _activeAgentId.asStateFlow()

    /**
     * 获取指定Agent的消息流
     */
    fun getMessagesFlow(agentId: String): StateFlow<List<MsgInfo>> {
        return messagesCache.getOrPut(agentId) {
            MutableStateFlow(emptyList())
        }.asStateFlow()
    }

    /**
     * 获取指定Agent的AgentInfo信息流
     */
    fun getAgentInfoFlow(agentId: String): StateFlow<AgentInfo?> {
        return agentInfosCache.getOrPut(agentId) {
            MutableStateFlow<AgentInfo?>(null)
        }.asStateFlow()
    }

    /**
     * 设置当前活跃的Agent
     */
    fun setActiveAgent(agentId: String) {
        _activeAgentId.value = agentId
    }


    /**
     * 添加消息到指定Agent
     */
    private suspend fun addMessage(agentId: String, message: MsgInfo) {
        val messagesFlow = messagesCache.getOrPut(agentId) {
            MutableStateFlow(emptyList())
        }

        messagesFlow.update { currentMessages ->
            val newMessages = currentMessages.toMutableList()
            newMessages.add(
                0,
                message
            )//因为消息messages的列表数据，是最新的在最前面，所以新发送的消息，也是添加到最前面。在UI上是reverseLayout实现了聊天列表的底部最新消息效果
            // 不排序，保持添加顺序，配合reverseLayout使用
            newMessages
        }

        // 发送消息事件
        _messageEvents.emit(MessageEvent.MessageAdded(agentId, message))
    }

    /**
     * 更新消息状态
     */
    private suspend fun updateMessageStatus(
        agentId: String,
        messageId: String,
        status: MessageStatus
    ) {
        val messagesFlow = messagesCache[agentId] ?: return

        messagesFlow.update { currentMessages ->
            currentMessages.map { message ->
                if (message.id == messageId) {
                    // 这里需要根据实际的MsgInfo结构来更新状态
                    message
                } else {
                    message
                }
            }
        }

        // 发送更新事件
        _messageEvents.emit(MessageEvent.MessageUpdated(agentId, messageId, status))
    }

    /**
     * 批量更新消息
     */
    private suspend fun updateMessages(agentId: String, messages: List<MsgInfo>) {
        val messagesFlow = messagesCache.getOrPut(agentId) {
            MutableStateFlow(emptyList())
        }

        messagesFlow.value = messages

        // 发送批量更新事件
        _messageEvents.emit(MessageEvent.MessagesUpdated(agentId, messages))
    }

    /**
     * 发送消息
     */
    suspend fun sendMessage(agentId: String, content: String): Result<MsgInfo> {
        return try {
            // 1. 创建本地消息（带loading状态）
            val localMessage = MsgInfo(
                id = generateMessageId(),
                content = content,
                role = "user",
                timestamp = System.currentTimeMillis().toString(),
                localMsgId = generateMessageId()
            )

            // 2. 添加loading消息
            val loadingMessage = MsgInfo(
                id = generateMessageId(),
                content = "loading_animation", // 特殊标识符
                role = "assistant",
                timestamp = System.currentTimeMillis().toString()
            )

            // 3. 立即添加到本地缓存
            addMessage(agentId, localMessage)
            addMessage(agentId, loadingMessage)

            // 4. 异步发送到服务器（确保在协程作用域内启动）
            try {
                sendMessageToServer(agentId, localMessage, content)
            } catch (e: Exception) {
                // 如果启动异步任务失败，更新消息状态为失败
                updateMessageStatus(agentId, localMessage.id, MessageStatus.FAILED)
                throw e
            }

            Result.success(localMessage)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * 异步发送消息到服务器
     */
    private fun sendMessageToServer(agentId: String, localMessage: MsgInfo, content: String) {
        // 使用注入的全局作用域，避免因页面生命周期取消
        coroutineScope.launch(Dispatchers.IO) {
            try {
                val request = SendMsgReq(
                    messages = listOf(
                        MsgInfo(
                            content = content,
                            role = "user",
                            timestamp = System.currentTimeMillis().toString()
                        )
                    ),
                    model = "chatbot",
                    stream = false
                )

                val result = chatApi.sendMsg(agentId, request)

                when (result) {
                    is HttpResult.Success -> {
                        // 移除loading消息
                        removeLoadingMessage(agentId)

                        // 检查业务错误码
                        val responseData = result.data
                        if (responseData.code in arrayOf(10001001, 10001002, 10001004, 10001005)) {
                            // 订阅错误，发送错误事件
                            val errorMessage =
                                responseData.data?.description ?: responseData.data?.error_code
                                ?: "Subscription required"

                            // 发送错误事件（包含本地消息ID）
                            _errorEvents.emit(
                                ErrorEvent(
                                    agentId = agentId,
                                    message = errorMessage,
                                    localMessageId = localMessage.id,
                                )
                            )

                            // 更新消息状态为发送失败
                            updateMessageStatus(agentId, localMessage.id, MessageStatus.FAILED)
                        } else {
                            // 更新消息状态为已发送
                            updateMessageStatus(agentId, localMessage.id, MessageStatus.SENT)

                            responseData.data?.choices?.forEach { choice ->
                                val aiMessage = choice.message.copy(
                                    id = generateMessageId(),
                                    timestamp = System.currentTimeMillis().toString()
                                )
                                addMessage(agentId, aiMessage)
                            }

                        }
                    }

                    is HttpResult.Failure -> {
                        // 发送网络错误事件
                        val errorMessage = "网络请求失败"
                        _errorEvents.emit(
                            ErrorEvent(
                                agentId = agentId,
                                message = errorMessage,
                                localMessageId = localMessage.id,
                            )
                        )

                        // 更新消息状态为发送失败
                        updateMessageStatus(agentId, localMessage.id, MessageStatus.FAILED)
                    }
                }
            } catch (e: Exception) {
                // 发送异常错误事件
                val errorMessage = "发送消息失败: ${e.message ?: "未知错误"}"
                _errorEvents.emit(
                    ErrorEvent(
                        agentId = agentId,
                        message = errorMessage,
                        localMessageId = localMessage.id,
                    )
                )

                // 更新消息状态为发送失败
                updateMessageStatus(agentId, localMessage.id, MessageStatus.FAILED)
            }
        }
    }

    /**
     * 加载历史消息
     */
    suspend fun loadHistoryMessages(agentId: String, limit: Int = 20, offset: Int = 0) {
        try {
            val result = chatApi.getMsgs(agentId, limit, offset)

            when (result) {
                is HttpResult.Success -> {
                    val response = result.data
                    val newMessages = response.messages ?: emptyList()

                    if (offset == 0) {
                        // 首次加载，直接替换
                        updateMessages(agentId, newMessages)
                    } else {
                        // 分页加载，追加到现有消息
                        appendMessages(agentId, newMessages)
                    }
                }

                is HttpResult.Failure -> {
                    // 处理加载失败
                    LogUtils.w("ChatDataManager - 加载$agentId 的消息历史 失败${result.message}")
                }
            }
        } catch (e: Exception) {
            // 处理加载失败
            LogUtils.e("ChatDataManager - 加载$agentId 的消息历史 接口异常${e.message}")
        }
    }

    /**
     * 追加消息到现有列表
     */
    private suspend fun appendMessages(agentId: String, newMessages: List<MsgInfo>) {
        val messagesFlow = messagesCache.getOrPut(agentId) {
            MutableStateFlow(emptyList())
        }

        messagesFlow.update { currentMessages ->
            val combinedMessages = currentMessages + newMessages
            combinedMessages
        }

        // 发送批量更新事件
        _messageEvents.emit(MessageEvent.MessagesUpdated(agentId, newMessages))
    }

    /**
     * 获取探索Agents列表
     */
    suspend fun getExploreAgents(page: Int = 1, pageSize: Int = 20): Result<List<AgentInfo>> {
        return try {
            val result = agentApi.exploreAgents(
                page = page,
                pageSize = pageSize,
                sort = "created_desc",
                sort_seed = "0"
            )

            when (result) {
                is HttpResult.Success -> {
                    val agents = result.data.list ?: emptyList()
                    Result.success(agents)
                }

                is HttpResult.Failure -> {
                    Result.failure(Exception(result.message))
                }
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * 清理指定Agent的缓存
     */
    private fun clearAgentCache(agentId: String) {
        messagesCache.remove(agentId)
        agentInfosCache.remove(agentId)
    }

    /**
     * 获取会话列表
     */
    private suspend fun getConversations(): Result<List<ConversationItem>> {
        return try {
            val result = chatApi.getConversations(0, 20)

            when (result) {
                is HttpResult.Success -> {
                    val conversations = result.data
                    Result.success(conversations)
                }

                is HttpResult.Failure -> {
                    Result.failure(Exception(result.message))
                }
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * 移除loading消息
     */
    private suspend fun removeLoadingMessage(agentId: String) {
        val messagesFlow = messagesCache[agentId] ?: return

        messagesFlow.update { currentMessages ->
            currentMessages.filterNot {
                it.content == "loading_animation" && it.role == "assistant"
            }
        }
    }

    /**
     * 清理所有缓存
     */
    private fun clearAllCache() {
        messagesCache.clear()
        agentInfosCache.clear()
    }
}

/**
 * 生成消息ID
 */
private fun generateMessageId(): String {
    return "${System.currentTimeMillis()}_${(0..9999).random()}"
}
