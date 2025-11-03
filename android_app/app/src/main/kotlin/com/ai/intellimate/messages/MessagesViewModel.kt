package com.ai.intellimate.messages

import ai.sxwl.android.common.analytics.PageTrackingHelper
import ai.sxwl.android.common.base.BaseVM
import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.ConversationItem
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.utils.LogUtils
import androidx.lifecycle.viewModelScope
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/** Messages页面ViewModel 负责管理会话列表的状态和业务逻辑 */
class MessagesViewModel : BaseVM() {

    // 延迟获取依赖，避免在构造函数中立即获取导致空指针异常
    private val chatApi by lazy { NetServiceMgr.getChatApi() }

    // UI状态
    private val _uiState = MutableStateFlow(MessagesUiState())
    val uiState = _uiState.asStateFlow()

    // 对话列表分页状态
    private var currentConversationsPage = 0
    private var hasMoreConversations = true

    // 页面跟踪上下文名称（默认为当前类名，可在外部设置）
    private var pageTrackingContext: String = "MessagesViewModel"

    init {
        // 页面跟踪
        trackPageView()
    }

    /**
     * 跟踪页面访问
     * @param contextName 上下文名称，默认为 "MessagesViewModel"
     */
    fun trackPageView(contextName: String = "MessagesViewModel") {
        pageTrackingContext = contextName
        val currentState = _uiState.value
        PageTrackingHelper.trackPageView(
            "MessagesPage",
            contextName,
            mapOf(
                "conversation_count" to currentState.conversations.size,
                "is_loading" to currentState.isLoading,
            )
        )
    }

    /**
     * 获取会话列表（首次加载或刷新）
     */
    fun getConversations() {
        currentConversationsPage = 0
        hasMoreConversations = true

        // 如果已经有数据，则不显示loading，直接后台刷新
        if (_uiState.value.conversations.isNotEmpty()) {
            loadConversationsSilently()
        } else {
            // 没有数据时才显示loading
            loadConversations()
        }
    }

    /**
     * 加载更多会话
     */
    fun loadMoreConversations() {
        val currentState = _uiState.value
        if (!currentState.isLoading && hasMoreConversations) {
            currentConversationsPage++
            loadConversations()
        } else {
            LogUtils.d(
                "loadMoreConversations - 跳过加载: isLoading=${currentState.isLoading}, hasMoreData=$hasMoreConversations"
            )
        }
    }

    /**
     * 静默加载会话（后台刷新，不显示loading）
     */
    private fun loadConversationsSilently() {
        val currentState = _uiState.value
        if (currentState.isLoading || currentState.isRefreshing) return

        viewModelScope.launch(Dispatchers.IO) {
            try {
                val skip = currentConversationsPage * 20
                val result = chatApi.getConversations(skip, 20)

                when (result) {
                    is HttpResult.Success -> {
                        val userInitiatedConversations = result.data

                        if (userInitiatedConversations.isEmpty()) {
                            hasMoreConversations = false
                        } else {
                            // 应用 Pin/Hide 逻辑：排序和过滤
                            val processedConversations =
                                processConversationsWithPinHide(userInitiatedConversations)
                            // 静默更新数据，不显示loading
                            _uiState.update { it.copy(conversations = processedConversations) }
                        }
                    }

                    is HttpResult.Failure -> {
                        LogUtils.e(
                            "loadConversationsSilently - 第${currentConversationsPage + 1}页加载失败: ${result.message}"
                        )
                    }
                }
            } catch (e: Exception) {
                LogUtils.e(
                    "loadConversationsSilently - 第${currentConversationsPage + 1}页加载异常: ${e.message}"
                )
            }
        }
    }

    /**
     * 加载会话列表（显示loading）
     */
    private fun loadConversations() {
        val currentState = _uiState.value
        if (currentState.isLoading || currentState.isRefreshing) return

        // 记录当前页码，用于后续状态重置
        val isFirstPage = currentConversationsPage == 0

        // 根据当前页码决定使用哪个loading状态
        if (isFirstPage) {
            // 第一页，使用刷新状态
            _uiState.update { it.copy(isRefreshing = true) }
        } else {
            // 后续页，使用加载更多状态
            _uiState.update { it.copy(isLoading = true) }
        }

        viewModelScope.launch(Dispatchers.IO) {
            try {
                val skip = currentConversationsPage * 20
                val result = chatApi.getConversations(skip, 20)

                when (result) {
                    is HttpResult.Success -> {
                        val userInitiatedConversations = result.data

                        if (userInitiatedConversations.isEmpty()) {
                            hasMoreConversations = false
                        } else {
                            // 应用 Pin/Hide 逻辑：排序和过滤
                            val processedConversations =
                                processConversationsWithPinHide(userInitiatedConversations)

                            if (currentConversationsPage == 0) {
                                // 第一页，直接替换
                                _uiState.update { it.copy(conversations = processedConversations) }
                            } else {
                                // 后续页，追加到现有列表（需要重新处理整个列表以保持排序）
                                val currentConversations = _uiState.value.conversations
                                val allConversations =
                                    currentConversations + userInitiatedConversations
                                val allProcessed = processConversationsWithPinHide(allConversations)
                                _uiState.update {
                                    it.copy(conversations = allProcessed)
                                }
                            }
                        }
                    }

                    is HttpResult.Failure -> {
                        LogUtils.e(
                            "loadConversations - 第${currentConversationsPage + 1}页加载失败: ${result.message}"
                        )
                        // 如果加载失败，回退页码
                        if (currentConversationsPage > 0) {
                            currentConversationsPage--
                            LogUtils.i("loadConversations - 页码回退到: $currentConversationsPage")
                        }
                    }
                }
            } catch (e: Exception) {
                LogUtils.e(
                    "loadConversations - 第${currentConversationsPage + 1}页加载异常: ${e.message}"
                )
                // 如果加载失败，回退页码
                if (currentConversationsPage > 0) {
                    currentConversationsPage--
                    LogUtils.i("loadConversations - 页码回退到: $currentConversationsPage")
                }
            }

            // 重置对应的loading状态
            _uiState.update { currentState ->
                if (isFirstPage) {
                    currentState.copy(isRefreshing = false)
                } else {
                    currentState.copy(isLoading = false)
                }
            }
        }
    }

    /**
     * 标记会话消息已读
     */
    fun setConversationReaded(conversationItem: ConversationItem) {
        IntySetting.setConversationReaded(conversationItem.agentId, conversationItem.lastMessage)

        _uiState.update { currentState ->
            currentState.copy(
                conversations = currentState.conversations.map { conversation ->
                    if (
                        conversation.id == conversationItem.id &&
                        conversation.agentId == conversationItem.agentId
                    ) {
                        conversation.copy(isNew = false)
                    } else {
                        conversation
                    }
                }
            )
        }
    }

    /**
     * 处理会话列表：排序（Pin在前）和过滤（隐藏的移除，除非有新消息）
     */
    private fun processConversationsWithPinHide(
        rawConversations: List<ConversationItem>
    ): List<ConversationItem> {
        return rawConversations
            .filter { conversation ->
                // 过滤隐藏的会话，除非有新消息
                !conversation.isHidden || conversation.shouldShow()
            }
            .sortedWith(
                compareBy<ConversationItem> { !it.isPinned }
                    .thenByDescending { conversation ->
                        // 将 lastMessageTime（ISO 8601 格式）转换为时间戳进行比较
                        ai.sxwl.android.utils.TimeUtils.parseIsoTimeToTimestamp(conversation.lastMessageTime)
                            ?: 0L
                    }
            )
    }

    /**
     * 置顶会话
     */
    fun pinConversation(agentId: String) {
        IntySetting.setConversationPinned(agentId, true)
        refreshConversationsWithPinHide()
    }

    /**
     * 取消置顶
     */
    fun unpinConversation(agentId: String) {
        IntySetting.setConversationPinned(agentId, false)
        refreshConversationsWithPinHide()
    }

    /**
     * 隐藏会话
     */
    fun hideConversation(agentId: String) {
        IntySetting.setConversationHidden(agentId, true)
        refreshConversationsWithPinHide()
    }

    /**
     * 取消隐藏
     */
    fun unhideConversation(agentId: String) {
        IntySetting.setConversationHidden(agentId, false)
        refreshConversationsWithPinHide()
    }

    /**
     * 刷新会话列表（应用Pin/Hide逻辑）
     */
    private fun refreshConversationsWithPinHide() {
        _uiState.update { currentState ->
            currentState.copy(
                conversations = processConversationsWithPinHide(currentState.conversations)
            )
        }
    }

    /**
     * 检查是否有新消息，自动取消隐藏
     */
    fun checkAndUnhideConversations() {
        val currentConversations = _uiState.value.conversations
        var needRefresh = false

        currentConversations.forEach { conversation ->
            if (conversation.isHidden && conversation.shouldShow()) {
                // 有新消息，自动取消隐藏
                IntySetting.setConversationHidden(conversation.agentId, false)
                needRefresh = true
            }
        }

        if (needRefresh) {
            refreshConversationsWithPinHide()
        }
    }

    /**
     * 清理所有数据
     */
    fun clearAllData() {
        currentConversationsPage = 0
        hasMoreConversations = true
        _uiState.value = MessagesUiState()
    }
}
