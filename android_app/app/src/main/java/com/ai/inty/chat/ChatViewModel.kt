package com.ai.inty.chat

import ai.sxwl.android.utils.Utils
import android.content.Context
import androidx.lifecycle.viewModelScope
import com.ai.inty.R
import com.ai.inty.audio.AudioManager
import com.ai.inty.base.BaseViewModel
import com.ai.inty.beans.AgentInfo
import com.ai.inty.beans.ChatSettingsReq
import com.ai.inty.beans.ChatSettingsResponse
import com.ai.inty.beans.ConversationItem
import com.ai.inty.beans.MsgInfo
import com.ai.inty.beans.SendMsgReq
import com.ai.inty.beans.UserProfile
import com.ai.inty.billing.VipStatusHelper
import com.ai.inty.net.NetServiceMgr
import com.ai.inty.netapi.BusinessErrorCodes
import com.ai.inty.utils.FirebaseManager
import com.ai.inty.utils.FirebasePerformanceHelper
import com.ai.inty.utils.PageTrackingHelper
import com.ai.inty.utils.UserProfileManager
import com.architecture.httplib.core.HttpResult
import com.inty.utils.log.EasyLog
import com.inty.utils.storage.IntySetting
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

// 操作什么数据，支持什么 UI？Model 是 beans
// View 是各类 page/activity。
class ChatViewModel : BaseViewModel() {

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
    private val QUERY_DEBOUNCE_TIME = 2000L // 2秒防抖

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

    // 延迟获取依赖，避免在构造函数中立即获取导致空指针异常
    private val chatApi by lazy { NetServiceMgr.getChatApi() }


    fun setAgentInfo(agentInfo: AgentInfo?) {

        // Firebase Analytics - 记录聊天会话开始
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

        // 如果 agent 为空，清理所有状态
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

        // 如果是同一个 agent，只更新信息，不重新查询消息
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

        // 查询新 agent 的消息
        queryMsgs()
        // 查询改聊天设置
        getChatSetting()
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
        _msgs.update { currentMsgs ->
            val updatedMsgs =
                currentMsgs.map { msg ->
                    if (msg.localMsgId == messageId) {
                        msg.copy(audio_url = audioUrl)
                    } else {
                        msg
                    }
                }
            updatedMsgs
        }
    }

    // endregion

    fun queryMsgs() {
        queryMsgs(loadMore = false)
    }

    fun queryMsgs(loadMore: Boolean = false) {
        // 防重复请求检查
        val currentTime = System.currentTimeMillis()
        val currentAgentId = agentInfo.value?.id

        if (isQueryingMsgs) {
            EasyLog.log("Already querying messages, skipping", EasyLog.WARN)
            return
        }

        if (currentAgentId == null) {
            EasyLog.log("No agent info available, skipping query", EasyLog.WARN)
            return
        }

        // 加载更多时完全跳过防抖检查，首次加载使用完整防抖时间
        if (
            !loadMore &&
            lastQueryAgentId == currentAgentId &&
            currentTime - lastQueryTime < QUERY_DEBOUNCE_TIME
        ) {
            EasyLog.log(
                "Query debounced for agent $currentAgentId (loadMore: $loadMore, debounceTime: ${QUERY_DEBOUNCE_TIME}ms)",
                EasyLog.WARN
            )
            return
        }

        isQueryingMsgs = true
        lastQueryAgentId = currentAgentId
        lastQueryTime = currentTime

        if (loadMore) {
            _isLoadingMore.value = true
        }

        viewModelScope.launch(Dispatchers.IO) {
            try {
                val currentAgentValue = agentInfo.value
                currentAgentValue?.let { agent ->

                    val result = chatApi.getMsgs(agent.id, PAGE_SIZE, currentOffset)
                    EasyLog.log("queryMsgs result for ${agent.id} = $result")
                    when (result) {
                        is HttpResult.Success -> {
                            val newMessages = result.data.messages ?: emptyList()
                            val hasMore = result.data.hasMore

                            EasyLog.log("Loaded ${newMessages.size} messages, hasMore: $hasMore")

                            if (loadMore) {
                                // 加载更多：旧数据应追加到列表尾部（在 reverseLayout 下显示在顶部）
                                _msgs.update { currentMsgs ->
                                    val combinedMessages = currentMsgs + newMessages
                                    // 去重处理
                                    val uniqueMessages =
                                        combinedMessages.distinctBy { msg ->
                                            "${msg.role}_${msg.content}_${msg.localMsgId}"
                                        }
                                    uniqueMessages
                                }
                                currentOffset += PAGE_SIZE
                            } else {
                                // 首次加载：替换消息列表
                                // 修复：只有当currentOffset为0时才进行首次加载，避免错误清空数据
                                if (currentOffset == 0) {
                                    val uniqueMessages =
                                        newMessages.distinctBy { msg ->
                                            "${msg.role}_${msg.content}_${msg.localMsgId}"
                                        }
                                    _msgs.update { uniqueMessages }
                                    currentOffset = PAGE_SIZE
                                } else {
                                    // 如果currentOffset不为0，说明这不是真正的首次加载，跳过数据替换
                                    EasyLog.log(
                                        "Skipping data replacement for non-first load: currentOffset=$currentOffset"
                                    )
                                }
                            }

                            _hasMoreMessages.value = hasMore
                            EasyLog.log(
                                "Successfully loaded messages. Total: ${_msgs.value.size}, hasMore: $hasMore"
                            )
                            // 标记消息查询完成
                            _isQueryMsgsCompleted.value = true
                        }

                        is HttpResult.Failure -> {
                            EasyLog.log("Failed to query messages: ${result.message}")
                            showNetworkAwareError(result.message)
                            // 即使查询失败，也标记为完成，避免开场白永远不播放
                            _isQueryMsgsCompleted.value = true
                        }
                    }
                }
            } catch (e: Exception) {
                EasyLog.log("queryMsgs exception: ${e.message}", priority = EasyLog.ERROR)
                handleNetworkException(e)
                // 即使出现异常，也标记为完成，避免开场白永远不播放
                _isQueryMsgsCompleted.value = true
            } finally {
                isQueryingMsgs = false
                _isLoadingMore.value = false
            }
        }
    }

    /** 加载更多消息 */
    fun loadMoreMessages() {
        EasyLog.log(
            "loadMoreMessages called: hasMore=${_hasMoreMessages.value}, isLoading=${_isLoadingMore.value}, isQueryingMsgs=$isQueryingMsgs, currentOffset=$currentOffset"
        )

        if (!_hasMoreMessages.value) {
            EasyLog.log("Cannot load more messages: no more messages available")
            return
        }

        if (_isLoadingMore.value) {
            EasyLog.log("Cannot load more messages: already loading more")
            return
        }

        if (isQueryingMsgs) {
            EasyLog.log("Cannot load more messages: already querying messages")
            return
        }

        EasyLog.log("Loading more messages, current offset: $currentOffset")
        queryMsgs(loadMore = true)
    }

    val showLimitDialog = MutableStateFlow(false)
    val requestLogin = MutableStateFlow(false)

    fun sendMsg() {
        // 防抖检查
        val currentTime = System.currentTimeMillis()
        if (currentTime - lastSendTime < SEND_DEBOUNCE_TIME) {
            EasyLog.log("Send message debounced, ignoring rapid clicks")
            return
        }
        lastSendTime = currentTime

        // 确保状态正确
        if (_isWaitingForReply.value) {
            EasyLog.log("Already waiting for reply, ignoring new send request")
            return
        }

        // 开始性能追踪
        FirebasePerformanceHelper.trace("send_message") { trace ->
            FirebasePerformanceHelper.putAttribute(
                trace,
                "agent_id",
                agentInfo.value?.id ?: "unknown",
            )
            FirebasePerformanceHelper.putAttribute(
                trace,
                "message_length",
                inputData.value.length.toString(),
            )

            launchWithNetCheck {
                try {
                    val inputMsg = inputData.value
                    if (inputMsg.isBlank()) {
                        EasyLog.log("Empty message, ignoring send request")
                        return@launchWithNetCheck
                    }

                    inputData.update { "" }

                    val msgInfo = MsgInfo(content = inputMsg.trimEnd(), role = "user")

                    // 添加临时的加载消息
                    val loadingMsg =
                        MsgInfo(
                            content = "loading_animation", // 特殊标识符
                            role = "assistant",
                        )

                    // 使用 StateFlow 的 update 方法安全地更新列表
                    _msgs.update { currentMsgs ->
                        try {
                            val newMsgs = mutableListOf<MsgInfo>()
                            newMsgs.add(loadingMsg) // 添加加载动画消息
                            newMsgs.add(msgInfo) // 添加用户消息
                            // 创建当前消息的副本以避免并发修改
                            newMsgs.addAll(currentMsgs.toList())
                            EasyLog.log(
                                "Successfully updated messages - new count: ${newMsgs.size}"
                            )
                            newMsgs
                        } catch (e: Exception) {
                            EasyLog.log(
                                "Error updating messages list: ${e.message}",
                                priority = EasyLog.ERROR,
                            )
                            currentMsgs // 返回原列表，避免数据丢失
                        }
                    }
                    _isWaitingForReply.value = true

                    val req = SendMsgReq(listOf(msgInfo))
                    val currentAgent = agentInfo.value
                    currentAgent?.let { agent ->

                        // Firebase Analytics - 记录消息发送
                        FirebaseManager.logEvent(
                            "message_sent",
                            mapOf(
                                "agent_id" to agent.id,
                                "message_length" to inputMsg.length,
                                "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                            ),
                        )

                        // Firebase Crashlytics - 记录消息发送上下文
                        FirebaseManager.setCustomKey(
                            "last_message_length",
                            inputMsg.length.toString(),
                        )
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
                        val result = chatApi.sendMsg(agent.id, req)

                        EasyLog.log("sendMsg($agent, $req) -> $result")

                        // 移除加载消息
                        _msgs.update { currentMsgs ->
                            currentMsgs.filterNot {
                                it.content == "loading_animation" && it.role == "assistant"
                            }
                        }
                        _isWaitingForReply.value = false

                        when (result) {
                            is HttpResult.Success -> {
                                // Firebase Analytics - 记录消息发送成功
                                FirebaseManager.logEvent(
                                    "message_send_success",
                                    mapOf(
                                        "agent_id" to agent.id,
                                        "response_code" to (result.data.code ?: 0),
                                        "user_type" to
                                                if (VipStatusHelper.isUserVip()) "vip" else "free",
                                    ),
                                )

                                runCatching {
                                    if (
                                        result.data.code ==
                                        BusinessErrorCodes.GUEST_NEED_LOGIN_CODE
                                    ) {
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
                                            "free_limit_reached",
                                            mapOf("agent_id" to agent.id, "user_type" to "free"),
                                        )
                                        showLimitDialog.emit(true)
                                    }
                                    // 添加AI回复
                                    _msgs.update { currentMsgs ->
                                        try {
                                            val newMsgs = mutableListOf<MsgInfo>()
                                            result.data.data?.choices?.forEach { choice ->
                                                newMsgs.add(choice.message)
                                            }
                                            // 创建当前消息的副本以避免并发修改
                                            newMsgs.addAll(currentMsgs.toList())
                                            newMsgs
                                        } catch (e: Exception) {
                                            EasyLog.log(
                                                "Error adding AI response: ${e.message}",
                                                priority = EasyLog.ERROR,
                                            )
                                            currentMsgs // 返回原列表，避免数据丢失
                                        }
                                    }

                                    result.data.data
                                        ?.choices
                                        ?.lastOrNull()
                                        ?.message
                                        ?.content
                                        ?.let { str ->
                                            IntySetting.setConversationReaded(agent.id, str)
                                        }
                                }.onFailure {
                                    EasyLog.log(
                                        "Error processing AI response: ${it.message}",
                                        priority = EasyLog.ERROR,
                                    )
                                    it.printStackTrace()
                                    // 错误恢复：确保状态正确
                                    _isWaitingForReply.value = false
                                }
                            }

                            is HttpResult.Failure -> {
                                // Firebase Analytics - 记录消息发送失败
                                FirebaseManager.logEvent(
                                    "message_send_failure",
                                    mapOf(
                                        "agent_id" to agent.id,
                                        "error_message" to result.message,
                                        "user_type" to
                                                if (VipStatusHelper.isUserVip()) "vip" else "free",
                                    ),
                                )

                                // Firebase Crashlytics - 记录非致命错误
                                FirebaseManager.recordException(
                                    Exception("Message send failed: ${result.message}")
                                )
                                // 所有消息接口错误，暂时统一文案
                                showNetworkAwareError(
                                    "Something went wrong. Please try again later."
                                )
                                // 错误恢复：确保状态正确
                                _isWaitingForReply.value = false
                            }
                        }
                    } ?: run {
                        // 如果没有 agent 信息，恢复状态
                        _isWaitingForReply.value = false
                        EasyLog.log(
                            "No agent info available for sending message",
                            priority = EasyLog.ERROR,
                        )
                    }
                } catch (e: Exception) {
                    EasyLog.log(
                        "Unexpected error in sendMsg: ${e.message}",
                        priority = EasyLog.ERROR,
                    )
                    _isWaitingForReply.value = false
                    showNetworkAwareError("An unexpected error occurred while sending message")
                } finally {
                    // 确保状态在最后被正确重置
                    if (_isWaitingForReply.value) {
                        EasyLog.log("Force reset waiting state due to completion")
                        _isWaitingForReply.value = false
                    }
                }
            }
        }
    }

    // 关闭limit次数 拦截消息的弹窗
    fun dismissDialog() = viewModelScope.launch { showLimitDialog.emit(false) }

    fun dismissLoginRequest() = viewModelScope.launch { requestLogin.emit(false) }

    fun sendKeepTalkingMessage() {
        // 防抖检查
        val currentTime = System.currentTimeMillis()
        if (currentTime - lastSendTime < SEND_DEBOUNCE_TIME) {
            EasyLog.log("Send keep talking message debounced, ignoring rapid clicks")
            return
        }
        lastSendTime = currentTime

        launchWithNetCheck {
            val keepTalkingMsg = "continue"

            val msgInfo = MsgInfo(content = keepTalkingMsg, role = "user")

            // 添加临时的加载消息 (keep talking不显示用户消息，只显示加载动画)
            val loadingMsg =
                MsgInfo(
                    content = "loading_animation", // 特殊标识符
                    role = "assistant",
                )
            // 使用 StateFlow 的 update 方法安全地更新列表
            _msgs.update { currentMsgs ->
                val newMsgs = mutableListOf<MsgInfo>()
                newMsgs.add(msgInfo) // 添加用户continue消息(会被过滤不显示)
                newMsgs.add(loadingMsg) // 添加加载动画消息
                // 创建当前消息的副本以避免并发修改
                newMsgs.addAll(currentMsgs.toList())
                newMsgs
            }
            _isWaitingForReply.value = true

            val req = SendMsgReq(listOf(msgInfo))

            agentInfo.value?.let { agent ->
                val result = chatApi.sendMsg(agent.id, req)

                EasyLog.log("sendKeepTalkingMessage($agent, $req) -> $result")

                // 移除加载消息
                _msgs.update { currentMsgs ->
                    currentMsgs.filterNot {
                        it.content == "loading_animation" && it.role == "assistant"
                    }
                }
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
                            // 添加AI回复
                            _msgs.update { currentMsgs ->
                                val newMsgs = mutableListOf<MsgInfo>()
                                result.data.data?.choices?.forEach { choice ->
                                    newMsgs.add(choice.message)
                                }
                                // 创建当前消息的副本以避免并发修改
                                newMsgs.addAll(currentMsgs.toList())
                                newMsgs
                            }

                            result.data.data?.choices?.lastOrNull()?.message?.content?.let { str
                                ->
                                IntySetting.setConversationReaded(agent.id, str)
                            }
                        }.onFailure {
                            EasyLog.log(
                                "Error processing keep talking AI response: ${it.message}",
                                priority = EasyLog.ERROR,
                            )
                            it.printStackTrace()
                            // 错误恢复：确保状态正确
                            _isWaitingForReply.value = false
                        }
                    }

                    is HttpResult.Failure -> {
                        showNetworkAwareError(result.message)
                        // 错误恢复：确保状态正确
                        _isWaitingForReply.value = false
                    }
                }
            }
                ?: run {
                    // 如果没有 agent 信息，恢复状态
                    _isWaitingForReply.value = false
                    EasyLog.log(
                        "No agent info available for keep talking",
                        priority = EasyLog.ERROR,
                    )
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

    private fun getChatSetting() = launchWithNetCheck {
        val agentId = agentInfo.value?.id ?: return@launchWithNetCheck
        // 有agent信息，才请求
        val result = chatApi.getChatSettings(agentId)
        when (result) {
            is HttpResult.Failure -> {
                // 此设置，暂时不用toast显示
                EasyLog.log(result.message)
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
    fun updateChatReplySettings(prompt: String) = launchWithNetCheck {
        val agentId = agentInfo.value?.id ?: return@launchWithNetCheck
        // 有agent信息，才请求
        val req = ChatSettingsReq(style_prompt = prompt)
        val result = chatApi.updateChatSettings(agentId, req)
        when (result) {
            is HttpResult.Failure -> showNetworkAwareError(result.message)
            is HttpResult.Success -> {
                showNetworkAwareError(Utils.getApp().getString(R.string.custom_reply_successful))
                // 要更新指定agent的chatsetting
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

        // 如果已经有数据，则不显示loading，直接后台刷新
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
            EasyLog.log(
                "loadMoreConversations - 跳过加载: isLoading=${_isLoadingConversations.value}, hasMoreData=$hasMoreConversations"
            )
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
                        EasyLog.log(
                            "loadConversationsSilently - 第${currentConversationsPage + 1}页加载失败: ${result.message}",
                            priority = EasyLog.ERROR,
                        )
                    }
                }
            } catch (e: Exception) {
                EasyLog.log(
                    "loadConversationsSilently - 第${currentConversationsPage + 1}页加载异常: ${e.message}",
                    priority = EasyLog.ERROR,
                )
            }
        }
    }

    private fun loadConversations() {
        if (_isLoadingConversations.value || _isRefreshingConversations.value) return

        // 记录当前页码，用于后续状态重置
        val isFirstPage = currentConversationsPage == 0

        // 根据当前页码决定使用哪个loading状态
        if (isFirstPage) {
            // 第一页，使用刷新状态
            _isRefreshingConversations.value = true
        } else {
            // 后续页，使用加载更多状态
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
                                // 第一页，直接替换（这里才清空并替换数据）
                                _conversations.value = userInitiatedConversations
                            } else {
                                // 后续页，追加到现有列表
                                _conversations.value =
                                    _conversations.value + userInitiatedConversations
                            }
                        }
                    }

                    is HttpResult.Failure -> {
                        EasyLog.log(
                            "loadConversations - 第${currentConversationsPage + 1}页加载失败: ${result.message}",
                            priority = EasyLog.ERROR,
                        )
                        // 如果加载失败，回退页码
                        if (currentConversationsPage > 0) {
                            currentConversationsPage--
                            EasyLog.log("loadConversations - 页码回退到: $currentConversationsPage")
                        }
                    }
                }
            } catch (e: Exception) {
                EasyLog.log(
                    "loadConversations - 第${currentConversationsPage + 1}页加载异常: ${e.message}",
                    priority = EasyLog.ERROR,
                )
                // 如果加载失败，回退页码
                if (currentConversationsPage > 0) {
                    currentConversationsPage--
                    EasyLog.log("loadConversations - 页码回退到: $currentConversationsPage")
                }
            }

            // 重置对应的loading状态
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
                EasyLog.log("getAgentInfo = $result")
                when (result) {
                    is HttpResult.Success -> {
                        setAgentInfo(result.data)
                    }

                    is HttpResult.Failure -> {
                        showNetworkAwareError(result.message)
                    }
                }
            } catch (e: Exception) {
                EasyLog.log("setAgentID exception: ${e.message}", priority = EasyLog.ERROR)
                handleNetworkException(e)
            }
        }
    }

    // 标记会话消息 已读
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
