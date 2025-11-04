package com.ai.intellimate.chat.viewmodel

import ai.sxwl.android.common.analytics.PageTrackingHelper
import ai.sxwl.android.common.base.BaseVM
import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.api.model.ChatSettingsReq
import ai.sxwl.android.data.api.model.ChatSettingsResponse
import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.api.model.UserProfile
import ai.sxwl.android.data.billing.VipStatusHelper
import ai.sxwl.android.data.chat.domain.ChatRepository
import ai.sxwl.android.data.di.DataModule
import ai.sxwl.android.data.http.BusinessErrorCodes
import ai.sxwl.android.data.store.IntySetting
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

// 操作什么数据，支持什么 UI？Model 是 beans
// View 是各类 page/activity。
class ChatViewModel : BaseVM() {

    // 依赖注入 - 使用新的架构
    private val chatRepository: ChatRepository = DataModule.getChatRepository()
    private val sendMessageUseCase = DataModule.sendMessageUseCase
    private val loadChatHistoryUseCase = DataModule.loadChatHistoryUseCase
    private val syncChatDataUseCase = DataModule.syncChatDataUseCase
    private val updateMessageFeedbackUseCase = DataModule.updateMessageFeedbackUseCase
    private val recallMessageUseCase = DataModule.recallMessageUseCase
    private val generateImageUseCase = DataModule.generateImageUseCase

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

    val inputData = MutableStateFlow<String>("")
    val inputSelection = MutableStateFlow<Int>(0)

    // 用于标识当前是否在等待AI回复
    private val _isWaitingForReply = MutableStateFlow<Boolean>(false)
    val isWaitingForReply = _isWaitingForReply.asStateFlow()

    private val _userProfile = MutableStateFlow<UserProfile>(UserProfile())
    val userProfile = _userProfile.asStateFlow()

    // 防抖机制：避免快速点击发送按钮
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

    // 延迟获取依赖，避免在构造函数中立即获取导致空指针异常
    private val chatApi by lazy { NetServiceMgr.getChatApi() }

    // 绑定到 ChatSessionManager 的收集任务
    private var messagesJob: Job? = null
    private var loadingMoreJob: Job? = null
    private var hasMoreJob: Job? = null
    private var boundAgentId: String? = null

    fun setAgentInfo(agentInfo: AgentInfo?) {

        // Firebase Analytics - Agent 信息已设置（不再记录 chat_session_start，避免 HorizontalPager 缓存机制导致的误触发）
        agentInfo?.let { agent ->

            // Firebase Crashlytics - 设置自定义键
            FirebaseManager.setCustomKey("current_agent_id", agent.id)
            FirebaseManager.setCustomKey("current_agent_name", agent.name)

            // 追踪聊天会话开始（用户操作：开始会话）
            PageTrackingHelper.trackUserInteraction(
                PageTrackingHelper.UserActions.START_SESSION,
                agent.name,
                mapOf(
                    "agent_id" to agent.id,
                    "agent_category" to agent.category,
                    "is_followed" to agent.isFollowed,
                ),
            )
        }

        // 如果 agent 为空，清理所有状态
        if (agentInfo == null) {
            _agentInfo.value = null
            _msgs.update { emptyList() }
            lastQueryAgentId = null
            isQueryingMsgs = false
            _isQueryMsgsCompleted.value = false
            // 停止语音播放
            audioManager?.stopAllPlayback()
            return
        }

        // 如果是同一个 agent，只更新信息，不重新查询消息
        if (_agentInfo.value?.id == agentInfo.id) {
            _agentInfo.value = agentInfo
            return
        }

        // 记录上一个Agent信息用于事件上报
        val previousAgent = _agentInfo.value

        // 上报Agent切换事件
        FirebaseManager.logEvent(
            FirebaseManager.Events.AGENT_SWITCH,
            FirebaseManager.safeEventParams(
                "from_agent_id" to (previousAgent?.id ?: ""),
                "from_agent_name" to (previousAgent?.name ?: ""),
                "to_agent_id" to agentInfo.id,
                "to_agent_name" to agentInfo.name,
                "switch_method" to "manual",
                "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                "timestamp" to System.currentTimeMillis()
            )
        )

        _agentInfo.value = agentInfo
        lastQueryAgentId = agentInfo.id
        isQueryingMsgs = false

        // 重置分页状态
        currentOffset = 0
        _hasMoreMessages.value = true
        _isLoadingMore.value = false

        // 立即绑定到Agent会话，获取本地缓存数据
        bindToAgentSession(agentInfo.id)

        // 检查是否有本地缓存数据
        val hasLocalData = chatRepository.getMessagesFlow(agentInfo.id).value.isNotEmpty()

        if (hasLocalData) {
            // 有本地数据，立即标记为完成，然后后台同步
            _isQueryMsgsCompleted.value = true
            // 后台同步最新数据
            viewModelScope.launch(Dispatchers.IO) {
                try {
                    syncChatDataUseCase(agentInfo.id)
                } catch (e: Exception) {
                    LogUtils.e("ChatViewModel.setAgentInfo background sync error: ${e.message}")
                }
            }
        } else {
            // 没有本地数据，需要加载
            _isQueryMsgsCompleted.value = false
            loadChatHistory(agentInfo.id)
        }

        // 查询聊天设置
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

        messagesJob =
            viewModelScope.launch(Dispatchers.IO) {
                chatRepository.getMessagesFlow(agentId).collect { list -> _msgs.value = list }
            }
        loadingMoreJob =
            viewModelScope.launch(Dispatchers.IO) {
                chatRepository.getLoadingMoreFlow(agentId).collect { loading ->
                    _isLoadingMore.value = loading
                }
            }
        hasMoreJob =
            viewModelScope.launch(Dispatchers.IO) {
                chatRepository.getHasMoreFlow(agentId).collect { more ->
                    _hasMoreMessages.value = more
                }
            }
    }

    /** 加载聊天历史 - 使用增量同步优化体验 */
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

    /** 同步最新消息 - 用于应用恢复、页面切换等场景 优先显示本地数据，后台检查服务器更新 */
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

    /** 发送消息 - 使用新架构 */
    fun sendMsg() {
        // 防抖检查
        val currentTime = System.currentTimeMillis()
        if (currentTime - lastSendTime < SEND_DEBOUNCE_TIME) {
            LogUtils.i("Send message debounced, ignoring rapid clicks")
            return
        }
        lastSendTime = currentTime

        // 确保状态正确
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
        // 记录端到端时间的起始点（用户点击发送按钮的时间）
        val endToEndStartTime = System.currentTimeMillis()

        // 检查是否是第一次聊天（没有历史消息）
        val currentMessages = _msgs.value
        val hasChatHistory = currentMessages.any { it.role == "user" }

        // 如果是第一次聊天，上报聊天开始事件（准确反映用户第一次发送消息的行为）
        if (!hasChatHistory) {
            _agentInfo.value?.let { agent ->
                FirebaseManager.logEvent(
                    FirebaseManager.Events.CHAT_STARTED,
                    FirebaseManager.safeEventParams(
                        "agent_id" to agent.id,
                        "agent_name" to agent.name,
                        "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                        "timestamp" to endToEndStartTime
                    )
                )
            }
        }
        _agentInfo.value?.let { agent ->
            FirebaseManager.logEvent(
                FirebaseManager.Events.MESSAGE_SENT,
                FirebaseManager.safeEventParams(
                    "agent_id" to agent.id,
                    "agent_name" to agent.name,
                    "message_length" to inputMsg.length,
                    "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                    "timestamp" to endToEndStartTime
                )
            )

            // Firebase Crashlytics - 记录消息发送上下文
            FirebaseManager.setCustomKey("last_message_length", inputMsg.length.toString())
            FirebaseManager.setCustomKey("last_message_preview", inputMsg.take(50))
            FirebaseManager.setCustomKey("last_agent_id", agent.id)

            // 追踪消息发送（用户操作：发送消息）
            PageTrackingHelper.trackUserInteraction(
                PageTrackingHelper.UserActions.SEND_MESSAGE,
                "chat_input",
                FirebaseManager.safeEventParams(
                    "agent_id" to agent.id,
                    "agent_name" to agent.name,
                    "message_length" to inputMsg.length,
                    "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                    "timestamp" to endToEndStartTime
                )
            )
        }

        viewModelScope.launch(Dispatchers.IO) {
            val aiResponseStartTime = System.currentTimeMillis()
            try {
                val result = sendMessageUseCase(agentId, inputMsg.trimEnd())
                LogUtils.i("Send message result: $result")

                // 处理发送结果
                when (result) {
                    is HttpResult.Success -> {
                        val responseTime = System.currentTimeMillis() - aiResponseStartTime
                        val endToEndTime = System.currentTimeMillis() - endToEndStartTime

                        // Firebase Analytics - 记录消息发送成功、AI响应时间和端到端时间
                        FirebaseManager.logEvent(
                            FirebaseManager.Events.MESSAGE_SEND_SUCCESS,
                            FirebaseManager.safeEventParams(
                                "agent_id" to agentId,
                                "agent_name" to (_agentInfo.value?.name),
                                "response_code" to (result.data.code ?: 0),
                                "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                                "ai_response_time" to responseTime,
                                "end_to_end_time" to endToEndTime
                            )
                        )

                        // 记录AI响应时间性能指标（API调用时间）
                        FirebaseManager.logPerformanceMetric(
                            FirebaseManager.Events.AI_RESPONSE_TIME,
                            responseTime,
                            "ms",
                            FirebaseManager.safeEventParams(
                                "agent_id" to agentId,
                                "agent_name" to (_agentInfo.value?.name),
                                "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free"
                            )
                        )

                        runCatching {
                            // 向后兼容：后端可能仍返回 GUEST_NEED_LOGIN_CODE 错误码
                            // 即使客户端已移除 guest 流程，也要处理此错误码，提示用户登录
                                if (result.data.code == BusinessErrorCodes.GUEST_NEED_LOGIN_CODE) {
                                    requestLogin.emit(true)
                                    return@runCatching
                                }
                                // 有免费次数限制，需要vip订阅
                                if (
                                    result.data.code ==
                                        BusinessErrorCodes.SUBSCRIPTION_REQUIRED_CODE
                                ) {
                                    // Firebase Analytics - 记录免费次数限制
                                    FirebaseManager.logEvent(
                                        FirebaseManager.Events.FREE_LIMIT_REACHED,
                                        FirebaseManager.safeEventParams(
                                            "agent_id" to agentId,
                                            "agent_name" to (_agentInfo.value?.name ?: ""),
                                            "user_type" to "free",
                                            "timestamp" to System.currentTimeMillis()
                                        )
                                    )
                                    showLimitDialog.emit(true)
                                }
                                result.data.data?.choices?.lastOrNull()?.message?.content?.let {
                                    content ->
                                    IntySetting.setConversationReaded(agentId, content)
                                }
                            }
                            .onFailure {
                                LogUtils.e("Error processing AI response: ${it.message}")
                                it.printStackTrace()
                                _isWaitingForReply.value = false
                            }
                    }
                    is HttpResult.Failure -> {
                        val responseTime = System.currentTimeMillis() - aiResponseStartTime
                        val endToEndTime = System.currentTimeMillis() - endToEndStartTime

                        // Firebase Analytics - 记录消息发送失败（包含API响应时间和端到端时间）
                        FirebaseManager.logEvent(
                            FirebaseManager.Events.MESSAGE_SEND_FAILURE,
                            FirebaseManager.safeEventParams(
                                "agent_id" to agentId,
                                "agent_name" to (_agentInfo.value?.name),
                                "error_message" to result.message,
                                "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                                "ai_response_time" to responseTime,
                                "end_to_end_time" to endToEndTime
                            )
                        )

                        // Firebase Crashlytics - 记录非致命错误
                        FirebaseManager.recordException(
                            Exception("Message send failed: ${result.message}"),
                            FirebaseManager.safeEventParams(
                                "agent_id" to agentId,
                                "agent_name" to (_agentInfo.value?.name),
                                "response_time" to responseTime,
                                "end_to_end_time" to endToEndTime
                            )
                        )

                        // 显示网络错误
                        NetworkErrorHandler.showNetworkAwareError(
                            "Something went wrong. Please try again later."
                        )
                        _isWaitingForReply.value = false
                    }
                }
            } catch (e: Exception) {
                val endToEndTime = System.currentTimeMillis() - endToEndStartTime
                LogUtils.e("Unexpected error in sendMsg: ${e.message}")

                // Firebase Analytics - 记录异常情况下的端到端时间
                FirebaseManager.logEvent(
                    FirebaseManager.Events.MESSAGE_SEND_EXCEPTION,
                    FirebaseManager.safeEventParams(
                        "agent_id" to agentId,
                        "agent_name" to (_agentInfo.value?.name),
                        "error_message" to (e.message ?: "unknown error"),
                        "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                        "end_to_end_time" to endToEndTime
                    )
                )

                // Firebase Crashlytics - 记录异常
                FirebaseManager.recordException(
                    e,
                    FirebaseManager.safeEventParams(
                        "agent_id" to agentId,
                        "agent_name" to (_agentInfo.value?.name),
                        "end_to_end_time" to endToEndTime
                    )
                )

                NetworkErrorHandler.showNetworkAwareError(
                    "An unexpected error occurred while sending message"
                )
                _isWaitingForReply.value = false
            } finally {
                // 确保状态在最后被正确重置
                if (_isWaitingForReply.value) {
                    LogUtils.i("Force reset waiting state due to completion")
                    _isWaitingForReply.value = false
                }
            }
        }
    }

    // region 语音播报相关

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

    // endregion

    // region TTS相关功能

    /** 更新消息的音频URL（供AudioManager回调使用） */
    fun updateMessageAudioUrl(messageId: String, audioUrl: String) {
        val agentId = agentInfo.value?.id ?: return
        chatRepository.updateMessageAudioUrl(agentId, messageId, audioUrl)
    }

    // endregion

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

    /** 同步最新消息：优先加载本地数据，然后检查服务器更新 */
    private fun syncLatestMessages(agentId: String) {
        LogUtils.i("ChatViewModel.syncLatestMessages called for agentId=$agentId")
        viewModelScope.launch(Dispatchers.IO) {
            syncChatDataUseCase(agentId, PAGE_SIZE)
            _isQueryMsgsCompleted.value = true
        }
    }

    /** 加载更多消息 */
    fun loadMoreMessages() {
        LogUtils.d(
            "loadMoreMessages called: hasMore=${_hasMoreMessages.value}, isLoading=${_isLoadingMore.value}, isQueryingMsgs=$isQueryingMsgs, currentOffset=$currentOffset"
        )

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

    // 关闭limit次数 拦截消息的弹窗
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
                            // 向后兼容：后端可能仍返回 GUEST_NEED_LOGIN_CODE 错误码
                            // 即使客户端已移除 guest 流程，也要处理此错误码，提示用户登录
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
                                result.data.data?.choices?.lastOrNull()?.message?.content?.let { str
                                    ->
                                    IntySetting.setConversationReaded(agent.id, str)
                                }
                            }
                            .onFailure {
                                LogUtils.e(
                                    "Error processing keep talking AI response: ${it.message}"
                                )
                                it.printStackTrace()
                                // 错误恢复：确保状态正确
                                _isWaitingForReply.value = false
                            }
                    }
                    is HttpResult.Failure -> {
                        NetworkErrorHandler.showNetworkAwareError(result.message)
                        // 错误恢复：确保状态正确
                        _isWaitingForReply.value = false
                    }
                }
            }
                ?: run {
                    // 如果没有 agent 信息，恢复状态
                    _isWaitingForReply.value = false
                    LogUtils.e("No agent info available for keep talking")
                }
        }
    }

    /** Like 消息 - 通过 Repository 更新 */
    fun likeMessage(localMsgId: String) {
        val agentId = _agentInfo.value?.id ?: return
        updateMessageFeedbackUseCase(agentId, localMsgId, MsgInfo.UserFeedback.LIKE)
        LogUtils.i("Message liked: $localMsgId")
    }

    /** Dislike 消息 - 通过 Repository 更新 */
    fun dislikeMessage(localMsgId: String) {
        val agentId = _agentInfo.value?.id ?: return
        updateMessageFeedbackUseCase(agentId, localMsgId, MsgInfo.UserFeedback.DISLIKE)
        LogUtils.i("Message disliked: $localMsgId")
    }

    /** Recall 消息 - 重新生成最新消息 */
    fun recallMessage() {
        val agentId = _agentInfo.value?.id ?: return
        viewModelScope.launch(Dispatchers.IO) {
            try {
                recallMessageUseCase(agentId)
            } catch (e: Exception) {
                LogUtils.e("Recall message error: ${e.message}")
                NetworkErrorHandler.showNetworkAwareError("Failed to recall message: ${e.message}")
            }
        }
    }

    /** 删除消息 */
    fun deleteMessage(localMsgId: String) {
        val agentId = _agentInfo.value?.id ?: return
        viewModelScope.launch(Dispatchers.IO) {
            chatRepository.removeMessage(agentId, localMsgId)
        }
    }

    /** 生成图片消息 */
    fun generateImageForMessage(messageId: String) {
        val agentId = _agentInfo.value?.id ?: return
        val agent = _agentInfo.value ?: return

        val startTime = System.currentTimeMillis()

        // Firebase Analytics - 记录图片生成开始
        FirebaseManager.logEvent(
            FirebaseManager.Events.IMAGE_GENERATION_START,
            FirebaseManager.safeEventParams(
                "agent_id" to agentId,
                "agent_name" to agent.name,
                "message_id" to messageId,
                "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                "timestamp" to startTime
            )
        )

        viewModelScope.launch(Dispatchers.IO) {
            try {
                val result = generateImageUseCase(agentId, messageId)
                val endTime = System.currentTimeMillis()
                val generationTime = endTime - startTime

                when (result) {
                    is HttpResult.Success -> {
                        LogUtils.i("Image generated successfully: ${result.data.imageUrl}")

                        // Firebase Analytics - 记录图片生成成功
                        FirebaseManager.logEvent(
                            FirebaseManager.Events.IMAGE_GENERATION_SUCCESS,
                            FirebaseManager.safeEventParams(
                                "agent_id" to agentId,
                                "agent_name" to agent.name,
                                "message_id" to messageId,
                                "image_url" to result.data.imageUrl,
                                "image_width" to result.data.width,
                                "image_height" to result.data.height,
                                "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                                "generation_time_ms" to generationTime,
                                "timestamp" to endTime
                            )
                        )

                        // Firebase Performance - 记录图片生成耗时
                        FirebaseManager.logPerformanceMetric(
                            FirebaseManager.Events.IMAGE_GENERATION_TIME,
                            generationTime.toLong(),
                            "ms",
                            FirebaseManager.safeEventParams(
                                "agent_id" to agentId,
                                "agent_name" to agent.name,
                                "message_id" to messageId,
                                "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free"
                            )
                        )
                    }

                    is HttpResult.Failure -> {
                        LogUtils.e("Image generation failed: code=${result.code}, message=${result.message}")

                        // 检查是否是业务错误码（订阅限制）
                        if (result.code == BusinessErrorCodes.IMAGE_GENERATION_LIMIT_REACHED_CODE ||
                            result.code == BusinessErrorCodes.SUBSCRIPTION_REQUIRED_CODE
                        ) {
                            // Firebase Analytics - 记录图片生成限制达到
                            FirebaseManager.logEvent(
                                FirebaseManager.Events.IMAGE_GENERATION_LIMIT_REACHED,
                                FirebaseManager.safeEventParams(
                                    "agent_id" to agentId,
                                    "agent_name" to agent.name,
                                    "message_id" to messageId,
                                    "error_code" to result.code,
                                    "error_message" to (result.message ?: "unknown"),
                                    "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                                    "generation_time_ms" to generationTime,
                                    "timestamp" to endTime
                                )
                            )

                            // 显示订阅弹窗（类似sendMsg的处理）
                            showLimitDialog.emit(true)
                        } else {
                            // Firebase Analytics - 记录图片生成失败
                            FirebaseManager.logEvent(
                                FirebaseManager.Events.IMAGE_GENERATION_FAILURE,
                                FirebaseManager.safeEventParams(
                                    "agent_id" to agentId,
                                    "agent_name" to agent.name,
                                    "message_id" to messageId,
                                    "error_code" to result.code,
                                    "error_message" to (result.message ?: "unknown"),
                                    "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                                    "generation_time_ms" to generationTime,
                                    "timestamp" to endTime
                                )
                            )

                            // 其他错误显示网络错误提示
                            NetworkErrorHandler.showNetworkAwareError(result.message)
                        }
                    }
                }
            } catch (e: Exception) {
                val endTime = System.currentTimeMillis()
                val generationTime = endTime - startTime
                LogUtils.e("Image generation error: ${e.message}")

                // Firebase Analytics - 记录图片生成异常
                FirebaseManager.logEvent(
                    FirebaseManager.Events.IMAGE_GENERATION_FAILURE,
                    FirebaseManager.safeEventParams(
                        "agent_id" to agentId,
                        "agent_name" to agent.name,
                        "message_id" to messageId,
                        "error_type" to e.javaClass.simpleName,
                        "error_message" to (e.message ?: "unknown error"),
                        "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                        "generation_time_ms" to generationTime,
                        "timestamp" to endTime
                    )
                )

                // Firebase Crashlytics - 记录异常
                FirebaseManager.recordException(
                    e,
                    FirebaseManager.safeEventParams(
                        "agent_id" to agentId,
                        "agent_name" to agent.name,
                        "message_id" to messageId,
                        "generation_time_ms" to generationTime
                    )
                )

                NetworkErrorHandler.showNetworkAwareError("Failed to generate image: ${e.message}")
            }
        }
    }

    // 获取聊天消息设置 - 按agentId存储，确保每个agent的设置独立
    private val _chatSettings =
        MutableStateFlow<Map<String, ChatSettingsResponse.ChatSettingRspData>>(emptyMap())
    val chatSettings = _chatSettings.asStateFlow()

    /** 获取指定agent的聊天设置 */
    fun getChatSettingForAgent(agentId: String): ChatSettingsResponse.ChatSettingRspData? {
        return _chatSettings.value[agentId]
    }

    private fun getChatSetting() = launchBackground {
        val agentId = agentInfo.value?.id ?: return@launchBackground
        // 有agent信息，才请求
        val result = chatApi.getChatSettings(agentId)
        when (result) {
            is HttpResult.Failure -> {
                // 此设置，暂时不用toast显示
                LogUtils.e(result.message)
                //                showNetworkAwareError(result.message)
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
        // 有agent信息，才请求
        val req = ChatSettingsReq(style_prompt = prompt)
        val result = chatApi.updateChatSettings(agentId, req)
        when (result) {
            is HttpResult.Failure -> NetworkErrorHandler.showNetworkAwareError(result.message)
            is HttpResult.Success -> {
                NetworkErrorHandler.showNetworkAwareError(
                    Utils.getApp().getString(R.string.custom_reply_successful)
                )
                // 要更新指定agent的chatsetting
                result.data.data?.let { chatSettingData ->
                    _chatSettings.update { currentSettings ->
                        currentSettings + (agentId to chatSettingData)
                    }
                }
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


    // 新增：清理所有数据的方法
    fun clearAllData() {
        _msgs.update { emptyList() }
        _agentInfo.value = null
        _userProfile.value = UserProfile()
        inputData.update { "" }
        inputSelection.value = 0
        _isWaitingForReply.value = false
        isQueryingMsgs = false
        lastQueryAgentId = null
        lastQueryTime = 0L
        lastSendTime = 0L

        // 清理chatSettings
        _chatSettings.value = emptyMap()

        // 清理消息查询完成状态
        _isQueryMsgsCompleted.value = false
    }

    fun setUserProfile(userProfile: UserProfile) {
        _userProfile.value = userProfile
    }

    // 本地userInfo的更新，而非接口
    fun updateUserInfo() {
        if (UserProfileManager.hasUserProfile()) {
            _userProfile.value = UserProfileManager.getUserProfile()
        }
    }
}
