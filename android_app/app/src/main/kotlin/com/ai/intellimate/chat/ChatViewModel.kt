package com.ai.intellimate.chat

import ai.sxwl.android.common.analytics.PageTrackingHelper
import ai.sxwl.android.common.base.BaseVM
import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.api.model.ChatSettingsReq
import ai.sxwl.android.data.api.model.ChatSettingsResponse
import ai.sxwl.android.data.api.model.ConversationItem
import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.api.model.UserProfile
import ai.sxwl.android.data.billing.VipStatusHelper
import ai.sxwl.android.data.di.ChatModule
import ai.sxwl.android.data.domain.ChatRepository
import ai.sxwl.android.data.http.BusinessErrorCodes
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.data.usecase.LoadChatHistoryUseCase
import ai.sxwl.android.data.usecase.SendMessageUseCase
import ai.sxwl.android.data.usecase.SyncChatDataUseCase
import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.Utils
import android.content.Context
import androidx.lifecycle.viewModelScope
import com.ai.intellimate.R
import com.ai.intellimate.audio.AudioManager
import com.ai.intellimate.utils.NetworkErrorHandler
import com.ai.intellimate.utils.UserProfileManager
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
// 操作什么数据，支持什么UI？Model 是 beans
// 查看的是主流页面/活动。
class ChatViewModel : BaseVM() {
// 依赖注入 - 使用新的架构
    private val chatRepository: ChatRepository = ChatModule.getChatRepository()
    private val sendMessageUseCase: SendMessageUseCase = ChatModule.sendMessageUseCase
    private val loadChatHistoryUseCase: LoadChatHistoryUseCase = ChatModule.loadChatHistoryUseCase
    private val syncChatDataUseCase: SyncChatDataUseCase = ChatModule.syncChatDataUseCase

    private val _agentInfo = MutableStateFlow<AgentInfo?>(null)
    val agentInfo = _agentInfo.asStateFlow()
// 使用 StateFlow 替代 mutableStateListOf 来解决并发问题
    private val _msgs = MutableStateFlow<List<MsgInfo>>(emptyList())
    val msgs = _msgs.asStateFlow()
// 分页相关状态
    private val _isLoadingMore = MutableStateFlow(false)
    val isLoadingMore = _isLoadingMore.asStateFlow()

    private val _hasMoreMessages = MutableStateFlow(true)
    val hasMoreMessages = _hasMoreMessages.asStateFlow()

    private var currentOffset = 0
    private val PAGE_SIZE = 20
    private val _conversations = MutableStateFlow<List<ConversationItem>>(emptyList())
    val conversations = _conversations.asStateFlow()

    val inputData = MutableStateFlow<String>("")
    val inputSelection = MutableStateFlow<Int>(0)
// 用于当前标识是否在等待AI回复
    private val _isWaitingForReply = MutableStateFlow<Boolean>(false)
    val isWaitingForReply = _isWaitingForReply.asStateFlow()

    private val _userProfile = MutableStateFlow<UserProfile>(UserProfile())
    val userProfile = _userProfile.asStateFlow()
// 反馈防机制：避免快速点击发送按钮
    private var lastSendTime = 0L
    private val SEND_DEBOUNCE_TIME = 1000L // 1秒防抖
// 音频管理器
    private var audioManager: AudioManager? = null
// 防重复请求机制
    private var isQueryingMsgs = false
    private var lastQueryAgentId: String? = null
    private var lastQueryTime = 0L
// 消息查询完成状态，用于控制开场白自动播放时机
    private val _isQueryMsgsCompleted = MutableStateFlow<Boolean>(false)
    val isQueryMsgsCompleted = _isQueryMsgsCompleted.asStateFlow()
// 对话列表分页状态
    private var currentConversationsPage = 0
    private var _isLoadingConversations = MutableStateFlow(false)
    val isLoadingConversations = _isLoadingConversations.asStateFlow()
    private var hasMoreConversations = true
// 刷新状态，用于区分首次加载和刷新操作
    private var _isRefreshingConversations = MutableStateFlow(false)
    val isRefreshingConversations = _isRefreshingConversations.asStateFlow()
// 延迟获取依赖，避免在构造函数中立即导致获取空指针异常
    private val chatApi by lazy { NetServiceMgr.getChatApi() }
// 绑定到 ChatSessionManager 的收集任务
    private var messagesJob: Job? = null
    private var loadingMoreJob: Job? = null
    private var hasMoreJob: Job? = null
    private var boundAgentId: String? = null


    fun setAgentInfo(agentInfo: AgentInfo?) {
// Firebase Analytics - 聊天会话开始
        agentInfo?.let { agent ->
            FirebaseManager.logEvent(
                "chat_session_start",
                mapOf(
                    "agent_id" to agent.id,
                    "agent_name" to agent.name,
                    "agent_category" to agent.category,
                    "is_followed" to agent.isFollowed,
                    "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                ),
            )
// Firebase Crashlytics - 设置自定义键
            FirebaseManager.setCustomKey("current_agent_id", agent.id)
            FirebaseManager.setCustomKey("current_agent_name", agent.name)
// 追踪聊天会话开始
            PageTrackingHelper.trackUserInteraction(
                "chat_session_start",
                agent.name,
                mapOf(
                    "agent_id" to agent.id,
                    "agent_category" to agent.category,
                    "is_followed" to agent.isFollowed,
                ),
            )
        }
// 如果代理为空，清理所有状态
        if (agentInfo == null) {
            _agentInfo.value = null
            _msgs.update { emptyList() }
            lastQueryAgentId = null
            isQueryingMsgs = false
            _isQueryMsgsCompleted.value = false
// 停止语音播放
            audioManager?.stopAllPlayback()
// Firebase Analytics - 记录聊天会话结束
            FirebaseManager.logEvent("chat_session_end", mapOf("reason" to "agent_cleared"))
            return
        }
// 如果是同一个代理，只更新信息，不重新查询消息
        if (_agentInfo.value?.id == agentInfo.id) {
            _agentInfo.value = agentInfo
            return
        }

        _agentInfo.value = agentInfo
        _msgs.update { emptyList() }
        lastQueryAgentId = agentInfo.id
        isQueryingMsgs = false
        _isQueryMsgsCompleted.value = false
// 重置分页状态
        currentOffset = 0
        _hasMoreMessages.value = true
        _isLoadingMore.value = false
// 使用查询新代理的消息 - 新架构
        bindToAgentSession(agentInfo.id)
// 使用增量同步，优先加载本地数据，然后同步服务器 - 使用UseCase
        loadChatHistory(agentInfo.id)
// 查询改聊天设置
        getChatSetting()
    }

    private fun bindToAgentSession(agentId: String) {
        if (boundAgentId == agentId) return
        boundAgentId = agentId
        messagesJob?.cancel()
        loadingMoreJob?.cancel()
        hasMoreJob?.cancel()

        runCatching {
            _msgs.value = chatRepository.getMessagesFlow(agentId).value
            _isLoadingMore.value = chatRepository.getLoadingMoreFlow(agentId).value
            _hasMoreMessages.value = chatRepository.getHasMoreFlow(agentId).value
        }

        messagesJob = viewModelScope.launch(Dispatchers.IO) {
            chatRepository.getMessagesFlow(agentId).collect { list ->
                _msgs.value = list
            }
        }
        loadingMoreJob = viewModelScope.launch(Dispatchers.IO) {
            chatRepository.getLoadingMoreFlow(agentId).collect { loading ->
                _isLoadingMore.value = loading
            }
        }
        hasMoreJob = viewModelScope.launch(Dispatchers.IO) {
            chatRepository.getHasMoreFlow(agentId).collect { more ->
                _hasMoreMessages.value = more
            }
        }
    }

    /**
     * 加载聊天历史 - 使用增量同步优化体验
     */
    private fun loadChatHistory(agentId: String) {
        LogUtils.i("ChatViewModel.loadChatHistory called for agentId=$agentId")
        viewModelScope.launch(Dispatchers.IO) {
            try {
// 使用增量同步，优先显示本地数据，然后检查服务器更新
                syncChatDataUseCase(agentId)
                _isQueryMsgsCompleted.value = true
            } catch (e: Exception) {
                LogUtils.e("ChatViewModel.loadChatHistory error: ${e.message}")
                _isQueryMsgsCompleted.value = true
            }
        }
    }

    /**
     * 同步最新消息 - 用于应用恢复、页面切换等场景
     * 优先显示本地数据，后台查看服务器更新
     */
    fun syncLatestMessages() {
        val agentId = _agentInfo.value?.id ?: return
        LogUtils.i("ChatViewModel.syncLatestMessages called for agentId=$agentId")
        viewModelScope.launch(Dispatchers.IO) {
            try {
                syncChatDataUseCase(agentId)
            } catch (e: Exception) {
                LogUtils.e("ChatViewModel.syncLatestMessages error: ${e.message}")
            }
        }
    }

    /**
     * 发送消息 - 使用新架构
     */
    fun sendMsg() {
// 防抖检查
        val currentTime = System.currentTimeMillis()
        if (currentTime - lastSendTime < SEND_DEBOUNCE_TIME) {
            LogUtils.i("Send message debounced, ignoring rapid clicks")
            return
        }
        lastSendTime = currentTime
//保证状态正确
        if (_isWaitingForReply.value) {
            LogUtils.i("Already waiting for reply, ignoring new send request")
            return
        }

        val inputMsg = inputData.value
        if (inputMsg.isBlank()) {
            LogUtils.i("Empty message, ignoring send request")
            return
        }

        val agentId = _agentInfo.value?.id ?: return
        inputData.value = ""
        _isWaitingForReply.value = true
// Firebase Analytics - 记录消息发送
        _agentInfo.value?.let { agent ->
            FirebaseManager.logEvent(
                "message_sent",
                mapOf(
                    "agent_id" to agent.id,
                    "message_length" to inputMsg.length,
                    "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                ),
            )
// Firebase Crashlytics - 记录消息传输上下文
            FirebaseManager.setCustomKey("last_message_length", inputMsg.length.toString())
            FirebaseManager.setCustomKey("last_message_preview", inputMsg.take(50))
// 追踪消息发送
            PageTrackingHelper.trackUserInteraction(
                "message_send",
                "chat_input",
                mapOf(
                    "agent_id" to agent.id,
                    "message_length" to inputMsg.length,
                    "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                ),
            )
        }

        viewModelScope.launch(Dispatchers.IO) {
            try {
                val result = sendMessageUseCase(agentId, inputMsg.trimEnd())
                LogUtils.i("Send message result: $result")
// 处理发送结果
                when (result) {
                    is HttpResult.Success -> {
// Firebase Analytics - 记录消息发送成功
                        FirebaseManager.logEvent(
                            "message_send_success",
                            mapOf(
                                "agent_id" to agentId,
                                "response_code" to (result.data.code ?: 0),
                                "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                            ),
                        )

                        runCatching {
                            if (result.data.code == BusinessErrorCodes.GUEST_NEED_LOGIN_CODE) {
                                requestLogin.emit(true)
                                return@runCatching
                            }
// 有免费次数限制，需要vip订阅
                            if (result.data.code == BusinessErrorCodes.SUBSCRIPTION_REQUIRED_CODE) {
// Firebase Analytics - 记录免费次数限制
                                FirebaseManager.logEvent(
                                    "free_limit_reached",
                                    mapOf("agent_id" to agentId, "user_type" to "free"),
                                )
                                showLimitDialog.emit(true)
                            }
                            result.data.data?.choices?.lastOrNull()?.message?.content?.let { content ->
                                IntySetting.setConversationReaded(agentId, content)
                            }
                        }.onFailure {
                            LogUtils.e("Error processing AI response: ${it.message}")
                            it.printStackTrace()
                            _isWaitingForReply.value = false
                        }
                    }
                    is HttpResult.Failure -> {
// Firebase Analytics - 记录消息发送失败
                        FirebaseManager.logEvent(
                            "message_send_failure",
                            mapOf(
                                "agent_id" to agentId,
                                "error_message" to result.message,
                                "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                            ),
                        )
// Firebase Crashlytics - 记录非致命错误
                        FirebaseManager.recordException(Exception("Message send failed: ${result.message}"))
// 显示网络错误
                        NetworkErrorHandler.showNetworkAwareError("Something went wrong. Please try again later.")
                        _isWaitingForReply.value = false
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("Unexpected error in sendMsg: ${e.message}")
                NetworkErrorHandler.showNetworkAwareError("An unexpected error occurred while sending message")
                _isWaitingForReply.value = false
            } finally {
//确保状态在最后被正确重置
                if (_isWaitingForReply.value) {
                    LogUtils.i("Force reset waiting state due to completion")
                    _isWaitingForReply.value = false
                }
            }
        }
    }
// 地区语音播报相关

    /** 初始化音频管理器 */
    fun initVoiceService(context: Context) {
        if (audioManager == null) {
            audioManager = AudioManager.Companion.getInstance(context, viewModelScope)
        }
    }

    /** 暂停语音播放（页面离开时调用） */
    fun pauseVoicePlayback() {
        audioManager?.pausePlayback()
    }

    /** 恢复语音播放（页面恢复时调用） */
    fun resumeVoicePlayback() {
        audioManager?.resumePlayback()
    }

    /** 重置语音播放状态（页面切换时调用） */
    fun resetVoicePlayback() {
        audioManager?.resetForPageChange()
    }

    /** 停止非当前Agent的音频播放 */
    fun stopNonCurrentAgentPlayback() {
        val currentAgentId = agentInfo.value?.id
        if (currentAgentId != null) {
            audioManager?.stopNonCurrentAgentPlayback(currentAgentId)
        }
    }
// 区域结束
// 区域TTS相关功能

    /** 更新消息的音频URL（供AudioManager回调使用） */
    fun updateMessageAudioUrl(messageId: String, audioUrl: String) {
        val agentId = agentInfo.value?.id ?: return
        chatRepository.updateMessageAudioUrl(agentId, messageId, audioUrl)
    }
// 区域结束

    fun queryMsgs(loadMore: Boolean = false) {
        val currentAgentId = agentInfo.value?.id ?: return
        if (loadMore) {
            viewModelScope.launch(Dispatchers.IO) {
                chatRepository.loadMoreMessages(currentAgentId, PAGE_SIZE)
            }
        } else {
            viewModelScope.launch(Dispatchers.IO) {
                loadChatHistoryUseCase(currentAgentId, PAGE_SIZE)
                _isQueryMsgsCompleted.value = true
            }
        }
    }

    /**
     * 同步最新消息：优先加载本地数据，然后检查服务器更新
     */
    private fun syncLatestMessages(agentId: String) {
        LogUtils.i("ChatViewModel.syncLatestMessages called for agentId=$agentId")
        viewModelScope.launch(Dispatchers.IO) {
            syncChatDataUseCase(agentId, PAGE_SIZE)
            _isQueryMsgsCompleted.value = true
        }
    }

    /** 加载更多消息 */
    fun loadMoreMessages() {
        LogUtils.d("loadMoreMessages called: hasMore=${_hasMoreMessages.value}, isLoading=${_isLoadingMore.value}, isQueryingMsgs=$isQueryingMsgs, currentOffset=$currentOffset")

        if (!_hasMoreMessages.value) {
            LogUtils.i("Cannot load more messages: no more messages available")
            return
        }

        if (_isLoadingMore.value) {
            LogUtils.i("Cannot load more messages: already loading more")
            return
        }

        if (isQueryingMsgs) {
            LogUtils.i("Cannot load more messages: already querying messages")
            return
        }

        LogUtils.i("Loading more messages, current offset: $currentOffset")
        val currentAgentId = agentInfo.value?.id ?: return
        viewModelScope.launch(Dispatchers.IO) {
            chatRepository.loadMoreMessages(currentAgentId, PAGE_SIZE)
        }
    }

    val showLimitDialog = MutableStateFlow(false)
    val requestLogin = MutableStateFlow(false)
// 关闭限制次数拦截消息的弹窗
    fun dismissDialog() = viewModelScope.launch { showLimitDialog.emit(false) }

    fun dismissLoginRequest() = viewModelScope.launch { requestLogin.emit(false) }

    fun sendKeepTalkingMessage() {
// 防抖检查
        val currentTime = System.currentTimeMillis()
        if (currentTime - lastSendTime < SEND_DEBOUNCE_TIME) {
            LogUtils.i("Send keep talking message debounced, ignoring rapid clicks")
            return
        }
        lastSendTime = currentTime

        launchBackground {
            val keepTalkingMsg = "continue"
            _isWaitingForReply.value = true

            agentInfo.value?.let { agent ->
                val result = sendMessageUseCase(agent.id, keepTalkingMsg)

                LogUtils.i("sendKeepTalkingMessage to ${agent.id} -> $result")
                _isWaitingForReply.value = false

                when (result) {
                    is HttpResult.Success -> {
                        runCatching {
                            if (result.data.code == BusinessErrorCodes.GUEST_NEED_LOGIN_CODE) {
                                requestLogin.emit(true)
                                return@runCatching
                            }
// 有免费次数限制，需要vip订阅
                            if (
                                result.data.code ==
                                BusinessErrorCodes.SUBSCRIPTION_REQUIRED_CODE
                            ) {
                                showLimitDialog.emit(true)
                            }
                            result.data.data?.choices?.lastOrNull()?.message?.content?.let { str ->
                                IntySetting.setConversationReaded(agent.id, str)
                            }
                        }.onFailure {
                            LogUtils.e("Error processing keep talking AI response: ${it.message}")
                            it.printStackTrace()
// 错误恢复：确保正确状态
                            _isWaitingForReply.value = false
                        }
                    }

                    is HttpResult.Failure -> {
                        NetworkErrorHandler.showNetworkAwareError(result.message)
// 错误恢复：确保正确状态
                        _isWaitingForReply.value = false
                    }
                }
            }
                ?: run {
// 如果没有代理信息，恢复状态
                    _isWaitingForReply.value = false
                    LogUtils.e("No agent info available for keep talking")
                }
        }
    }
// 获取聊天消息设置 - 按agentId存储，确保每个agent的设置独立
    private val _chatSettings =
        MutableStateFlow<Map<String, ChatSettingsResponse.ChatSettingRspData>>(emptyMap())
    val chatSettings = _chatSettings.asStateFlow()

    /** 获取指定代理的聊天设置 */
    fun getChatSettingForAgent(agentId: String): ChatSettingsResponse.ChatSettingRspData? {
        return _chatSettings.value[agentId]
    }

    private fun getChatSetting() = launchBackground {
        val agentId = agentInfo.value?.id ?: return@launchBackground
// 有代理信息，才请求
        val result = chatApi.getChatSettings(agentId)
        when (result) {
            is HttpResult.Failure -> {
// 此设置，暂时不用toast显示
                LogUtils.e(result.message)
// 显示NetworkAwareError(结果。信息）
            }

            is HttpResult.Success -> {
// 更新指定agent的设置，保持其他agent的设置不变
                _chatSettings.update { currentSettings ->
                    currentSettings + (agentId to result.data)
                }
            }
        }
    }
// 高级模型定制化回复的接口调用
    fun updateChatReplySettings(prompt: String) = launchBackground {
        val agentId = agentInfo.value?.id ?: return@launchBackground
// 有代理信息，才请求
        val req = ChatSettingsReq(style_prompt = prompt)
        val result = chatApi.updateChatSettings(agentId, req)
        when (result) {
            is HttpResult.Failure -> NetworkErrorHandler.showNetworkAwareError(result.message)
            is HttpResult.Success -> {
                NetworkErrorHandler.showNetworkAwareError(
                    Utils.getApp().getString(R.string.custom_reply_successful)
                )
// 要更新指定代理的聊天设置
                result.data.data?.let { chatSettingData ->
                    _chatSettings.update { currentSettings ->
                        currentSettings + (agentId to chatSettingData)
                    }
                }
            }
        }
    }

    fun getConversations() {
        currentConversationsPage = 0
        hasMoreConversations = true
// 如果已经有数据，则不显示加载中，直接后台刷新
        if (_conversations.value.isNotEmpty()) {
            loadConversationsSilently()
        } else {
// 没有数据时才显示loading
            loadConversations()
        }
    }

    fun loadMoreConversations() {
        if (!_isLoadingConversations.value && hasMoreConversations) {
            currentConversationsPage++
            loadConversations()
        } else {
            LogUtils.d("loadMoreConversations - 跳过加载: isLoading=${_isLoadingConversations.value}, hasMoreData=$hasMoreConversations")
        }
    }

    private fun loadConversationsSilently() {
        if (_isLoadingConversations.value || _isRefreshingConversations.value) return

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
// 静默更新数据，不显示loading
                            _conversations.value = userInitiatedConversations
                        }
                    }

                    is HttpResult.Failure -> {
                        LogUtils.e("loadConversationsSilently - 第${currentConversationsPage + 1}页加载失败: ${result.message}")
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("loadConversationsSilently - 第${currentConversationsPage + 1}页加载异常: ${e.message}")
            }
        }
    }

    private fun loadConversations() {
        if (_isLoadingConversations.value || _isRefreshingConversations.value) return
// 记录当前页码，用于后续状态重置
        val isFirstPage = currentConversationsPage == 0
// 根据当前页码决定使用哪个加载状态
        if (isFirstPage) {
// 第一页，使用刷新状态
            _isRefreshingConversations.value = true
        } else {
// 后续页面，使用加载更多状态
            _isLoadingConversations.value = true
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
                            if (currentConversationsPage == 0) {
//第一页，直接替换（这里才清空并替换数据）
                                _conversations.value = userInitiatedConversations
                            } else {
// 后续页面，追加到现有列表
                                _conversations.value =
                                    _conversations.value + userInitiatedConversations
                            }
                        }
                    }

                    is HttpResult.Failure -> {
                        LogUtils.e("loadConversations - 第${currentConversationsPage + 1}页加载失败: ${result.message}")
// 如果加载失败，返回退页码
                        if (currentConversationsPage > 0) {
                            currentConversationsPage--
                            LogUtils.i("loadConversations - 页码回退到: $currentConversationsPage")
                        }
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("loadConversations - 第${currentConversationsPage + 1}页加载异常: ${e.message}")
// 如果加载失败，返回退页码
                if (currentConversationsPage > 0) {
                    currentConversationsPage--
                    LogUtils.i("loadConversations - 页码回退到: $currentConversationsPage")
                }
            }
// 重置的加载状态
            if (isFirstPage) {
                _isRefreshingConversations.value = false
            } else {
                _isLoadingConversations.value = false
            }
        }
    }

    fun setAgentID(agentId: String) {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val result = chatApi.getAgentInfo(agentId)
                LogUtils.i("getAgentInfo = $result")
                when (result) {
                    is HttpResult.Success -> {
                        setAgentInfo(result.data)
                    }

                    is HttpResult.Failure -> {
                        NetworkErrorHandler.showNetworkAwareError(result.message)
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("setAgentID exception: ${e.message}")
                NetworkErrorHandler.handleNetworkException(e)
            }
        }
    }
// 标记会话消息已读
    fun setConversationReaded(conversationItem: ConversationItem) {
        IntySetting.setConversationReaded(conversationItem.agentId, conversationItem.lastMessage)

        _conversations.update { currentConversations ->
            currentConversations.map { conversation ->
                if (
                    conversation.id == conversationItem.id &&
                    conversation.agentId == conversationItem.agentId
                ) {
                    conversation.copy(isNew = false)
                } else {
                    conversation
                }
            }
        }
    }
// 新增：清理所有数据的方法
    fun clearAllData() {
        _msgs.update { emptyList() }
        _conversations.value = emptyList()
        _agentInfo.value = null
        _userProfile.value = UserProfile()
        inputData.update { "" }
        inputSelection.value = 0
        _isWaitingForReply.value = false
        isQueryingMsgs = false
        lastQueryAgentId = null
        lastQueryTime = 0L
        lastSendTime = 0L
// 清理分页状态
        currentConversationsPage = 0
        hasMoreConversations = true
        _isLoadingConversations.value = false
//清理聊天设置
        _chatSettings.value = emptyMap()
// 清理消息完成查询状态
        _isQueryMsgsCompleted.value = false
    }

    fun setUserProfile(userProfile: UserProfile) {
        _userProfile.value = userProfile
    }
// 本地userInfo的更新，接口
    fun updateUserInfo() {
        if (UserProfileManager.hasUserProfile()) {
            _userProfile.value = UserProfileManager.getUserProfile()
        }
    }
}
