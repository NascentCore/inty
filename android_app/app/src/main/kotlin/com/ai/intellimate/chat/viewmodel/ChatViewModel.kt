package com.ai.intellimate.chat.viewmodel

import ai.sxwl.android.common.analytics.PageTrackingHelper
import ai.sxwl.android.common.base.BaseVM
import ai.sxwl.android.common.utils.HeartAppUtils
import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.api.model.ChatSettingsReq
import ai.sxwl.android.data.api.model.ChatSettingsResponse
import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.api.model.UserProfile
import ai.sxwl.android.data.api.model.VoteConstants
import ai.sxwl.android.data.billing.VipStatusHelper
import ai.sxwl.android.data.character.repository.CharacterRepository
import ai.sxwl.android.data.chat.domain.ChatRepository
import ai.sxwl.android.data.chat.local.db.toModel
import ai.sxwl.android.data.di.DataModule
import ai.sxwl.android.data.http.BusinessErrorCodes
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.firebase.logEvent
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.ToastUtils
import ai.sxwl.android.utils.Utils
import android.content.Context
import androidx.lifecycle.viewModelScope
import androidx.paging.cachedIn
import androidx.paging.map
import com.ai.intellimate.R
import com.ai.intellimate.audio.AudioManager
import com.ai.intellimate.audio.OpeningPlayState
import com.ai.intellimate.boost.BoostManager
import com.ai.intellimate.chat.data.ChatMessageRepository
import com.ai.intellimate.chat.uistate.ChatUIState
import com.ai.intellimate.ui.UiConfigs
import com.ai.intellimate.utils.NetworkErrorHandler
import com.ai.intellimate.utils.UserProfileManager
import com.ai.intellimate.xb.helper.AgentStore
import com.architecture.httplib.core.HttpResult
import java.time.LocalDate
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.Job
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.emptyFlow
import kotlinx.coroutines.flow.filterNotNull
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

private const val LOADING_PLACEHOLDER_CONTENT = "loading_animation"

class ChatViewModel : BaseVM() {

    // 依赖注入 - 使用新的架构
    private val chatMessageRepository = ChatMessageRepository()
    private val chatRepository: ChatRepository = DataModule.getChatRepository()
    private val characterRepository: CharacterRepository = DataModule.getCharacterRepository()
    private val sendMessageUseCase = DataModule.sendMessageUseCase
    private val loadChatHistoryUseCase = DataModule.loadChatHistoryUseCase
    private val syncChatDataUseCase = DataModule.syncChatDataUseCase
    private val updateMessageFeedbackUseCase = DataModule.updateMessageFeedbackUseCase
    private val recallMessageUseCase = DataModule.recallMessageUseCase
    private val generateImageUseCase = DataModule.generateImageUseCase
    private val voteMessageUseCase = DataModule.voteMessageUseCase

    private val _uiState = MutableStateFlow(ChatUIState())
    val uiState = _uiState.asStateFlow()

    private val _agentId = MutableStateFlow<String?>(null)

    @OptIn(ExperimentalCoroutinesApi::class)
    val agentFlow =
        _agentId
            .flatMapLatest {
                if (it.isNullOrBlank()) {
                    flowOf(null)
                } else {
                    characterRepository.getCharacterFlow(it)
                }
            }
            .stateIn(viewModelScope, SharingStarted.Eagerly, null)

    @Deprecated("应该直接在room中更新数据，但需要考虑旧有逻辑的数据同步")
    private val _agentInfo = MutableStateFlow<AgentInfo?>(null)
    @Deprecated("使用agentFlow从本地数据库查询") val agentInfo = _agentInfo.asStateFlow()

    // 使用 StateFlow 替代 mutableStateListOf 来解决并发问题
    /*private val _msgs = MutableStateFlow<List<MsgInfo>>(emptyList())
    val msgs = _msgs.asStateFlow()*/

    @OptIn(ExperimentalCoroutinesApi::class)
    val messages =
        _agentId
            .flatMapLatest {
                if (it.isNullOrBlank()) {
                    emptyFlow()
                } else {
                    chatMessageRepository.getMessagesFlow(it)
                }
            }
            .map { it.map { entity -> entity.toModel() } }
            .cachedIn(viewModelScope)

    private var lastAiMsgInfo: MsgInfo? = null
    private val _shouldFlowShow = MutableStateFlow(false)
    val shouldFlowShow = _shouldFlowShow.asStateFlow()

    // 分页相关状态
    private val _isLoadingMore = MutableStateFlow(false)
    val isLoadingMore = _isLoadingMore.asStateFlow()

    private val _hasMoreMessages = MutableStateFlow(true)
    val hasMoreMessages = _hasMoreMessages.asStateFlow()

    // 反馈对话框显示状态
    private val _showFeedbackRequestDialog = MutableStateFlow(false)
    val showFeedbackRequestDialog = _showFeedbackRequestDialog.asStateFlow()

    private val _imagePickMessageId = MutableStateFlow<String?>(null)
    val imagePickMessageId = _imagePickMessageId.asStateFlow()

    // 会话级别的消息计数（app 打开到进入后台/退出之间的消息数）
    private var sessionMessageCount = 0

    private var currentOffset = 0
    private val PAGE_SIZE = 20

    val inputData = MutableStateFlow<String>("")
    val inputSelection = MutableStateFlow<Int>(0)

    // 用于标识当前是否在等待AI回复
    private val _isWaitingForReply = MutableStateFlow<Boolean>(false)
    val isWaitingForReply = _isWaitingForReply.asStateFlow()

    val userProfile =
        UserProfileManager.profile.stateIn(viewModelScope, SharingStarted.Eagerly, UserProfile())

    private val _characterEnergy = MutableStateFlow(0)
    val characterEnergy = _characterEnergy.asStateFlow()

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

    // 绑定到 ChatSessionManager 的收集任务
    private var messagesJob: Job? = null
    private var loadingMoreJob: Job? = null
    private var hasMoreJob: Job? = null
    private var characterEnergyJob: Job? = null
    private var boundAgentId: String? = null
    private var lastSyncedEnergyPoints = 0

    // 显示订阅
    private val _vipRequest = Channel<String>()
    val vipRequest = _vipRequest.receiveAsFlow()

    init {
        checkVipAgentUnlock()

        viewModelScope.launch {
            _agentId.filterNotNull().collect {
                withContext(Dispatchers.IO) { characterRepository.refreshAgent(it) }
            }
        }
    }

    fun setAgentInfo(agentInfo: AgentInfo?, forceSync: Boolean = false) {

        _agentId.value = agentInfo?.id
        _imagePickMessageId.value = null

        // Firebase Analytics - Agent 信息已设置（不再记录 chat_session_start，避免 HorizontalPager 缓存机制导致的误触发）
        agentInfo?.let { agent ->
            viewModelScope.launch {
                characterRepository.updateLocalAgent(agent.id) {
                    it.copy(
                        intro = agent.intro,
                        opening = agent.opening,
                        opening_audio_url = agent.opening_audio_url,
                        isFollowed = agent.isFollowed,
                    )
                }
            }

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
            lastQueryAgentId = null
            isQueryingMsgs = false
            _isQueryMsgsCompleted.value = false
            // 停止语音播放
            audioManager?.stopAllPlayback()
            characterEnergyJob?.cancel()
            _characterEnergy.value = 0
            lastSyncedEnergyPoints = 0
            return
        }

        // 如果是同一个 agent，总是触发后台同步以确保获取最新消息
        // syncLatestMessages 内部已经有逻辑判断是否有新消息，如果没有新消息不会更新本地数据
        if (_agentInfo.value?.id == agentInfo.id) {
            val previousIsDeleted = _agentInfo.value?.isDeleted ?: false
            val currentIsDeleted = agentInfo.isDeleted

            // StateFlow使用引用相等性检测变化，如果传入同一个对象引用，即使内部属性变化也不会触发更新
            // 如果isDeleted状态变化，需要创建新对象确保StateFlow能检测到变化
            if (previousIsDeleted != currentIsDeleted) {
                // 使用copy函数创建新对象,找一个无用字段readableId触发更新，然后设置isDeleted属性
                val updatedAgent =
                    agentInfo.copy(readableId = "deleted").apply {
                        this.isDeleted = agentInfo.isDeleted
                    }
                _agentInfo.value = updatedAgent
            } else {
                // isDeleted状态没有变化，直接更新
                _agentInfo.value = agentInfo
            }

            // 重新启动能量点数观察，确保数据实时更新
            observeCharacterEnergy(agentInfo.id)
            viewModelScope.launch(Dispatchers.IO) {
                characterRepository.updateEnergy(agentInfo.id, lastSyncedEnergyPoints)
            }
            // 总是触发后台同步，确保用户看到最新消息
            viewModelScope.launch(Dispatchers.IO) {
                try {
                    syncChatDataUseCase(agentInfo.id)
                } catch (e: Exception) {
                    LogUtils.e("ChatViewModel.setAgentInfo sync error: ${e.message}")
                }
            }
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
                "timestamp" to System.currentTimeMillis(),
            ),
        )

        _agentInfo.value = agentInfo
        lastSyncedEnergyPoints = 0
        _characterEnergy.value = 0
        observeCharacterEnergy(agentInfo.id)
        viewModelScope.launch(Dispatchers.IO) {
            characterRepository.updateEnergy(agentInfo.id, lastSyncedEnergyPoints)
        }
        lastQueryAgentId = agentInfo.id
        isQueryingMsgs = false

        // 重置分页状态
        currentOffset = 0
        _hasMoreMessages.value = true
        _isLoadingMore.value = false

        // 切换到不同 agent 时，清空输入状态，避免输入文案残留
        inputData.value = ""
        inputSelection.value = 0

        // 立即绑定到Agent会话，获取本地缓存数据
        bindToAgentSession(agentInfo.id)

        // 检查是否有本地缓存数据
        val hasLocalData = chatRepository.getMessagesFlow(agentInfo.id).value.isNotEmpty()

        if (hasLocalData) {
            if (forceSync) {
                // 🔧 修复：从通知进入时（forceSync=true），先同步最新数据，等待完成后再标记为完成
                // 确保UI显示的是最新消息，而不是旧的本地缓存
                _isQueryMsgsCompleted.value = false
                viewModelScope.launch(Dispatchers.IO) {
                    try {
                        syncChatDataUseCase(agentInfo.id)
                        _isQueryMsgsCompleted.value = true
                        LogUtils.i(
                            "ChatViewModel.setAgentInfo forceSync completed for ${agentInfo.id}"
                        )
                    } catch (e: Exception) {
                        LogUtils.e("ChatViewModel.setAgentInfo forceSync error: ${e.message}")
                        // 即使同步失败，也标记为完成，避免UI一直等待
                        _isQueryMsgsCompleted.value = true
                    }
                }
            } else {
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
            }
        } else {
            // 没有本地数据，需要加载
            _isQueryMsgsCompleted.value = false
            loadChatHistory(agentInfo.id)
        }

        // 查询聊天设置
        getChatSetting()
    }

    @OptIn(ExperimentalCoroutinesApi::class)
    private fun checkVipAgentUnlock() {

        viewModelScope.launch {
            combine(VipStatusHelper.vipStatus, agentFlow) { vipStatus, agent ->
                    when {
                        agent?.tags?.any { it.lowercase().contains("vip") } != true ||
                            vipStatus.isSubscribed ||
                            agent.lastUnlockByCredits == LocalDate.now().toString() -> {

                            ChatUIState.VipAgentLockType.NONE
                        }
                        chatMessageRepository.getMessageCounts(agent.agentId) > 0 ->
                            ChatUIState.VipAgentLockType.INPUT
                        else -> ChatUIState.VipAgentLockType.DIALOG
                    }
                }
                .collect { type -> _uiState.update { it.copy(vipAgentLockType = type) } }
        }
    }

    fun chatUnlockByCredits() {
        viewModelScope.launch {
            _agentId.value?.let { agentId ->
                val currentCredits = BoostManager.boostState.value.availablePoints
                if (BoostManager.unlockVipAgent()) {
                    characterRepository.unlockAgentByCredits(agentId)
                } else {
                    ToastUtils.showShort(R.string.credits_not_enough)
                    _vipRequest.trySend("Credits not enough!")
                }
                FirebaseManager.Events.VIP_AGENT_UNLOCK.logEvent(
                    "agent_id" to agentId,
                    "unlock_method" to "credits",
                    "owed_credits" to currentCredits,
                )
            }
        }
    }

    /** 检查错误消息是否包含取消相关的关键字 用于避免在用户退出 Activity 后显示错误 Toast */
    private fun isCancellationError(errorMessage: String?): Boolean {
        if (errorMessage == null) return false
        val message = errorMessage.lowercase()
        return message.contains("cancel") ||
            message.contains("interrupted") ||
            message.contains("socket closed") ||
            message.contains("connection reset")
    }

    private fun bindToAgentSession(agentId: String) {
        if (boundAgentId == agentId) return
        lastAiMsgInfo = null
        boundAgentId = agentId
        messagesJob?.cancel()
        loadingMoreJob?.cancel()
        hasMoreJob?.cancel()
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

    private fun observeCharacterEnergy(agentId: String) {
        characterEnergyJob?.cancel()
        characterEnergyJob =
            viewModelScope.launch {
                characterRepository.observeCharacter(agentId).collect { entity ->
                    val points = entity?.energyPoints ?: 0
                    _characterEnergy.value = points
                    lastSyncedEnergyPoints = points
                }
            }
    }

    // FIXME: 如果点数在其他地方被消耗，会因为此处的处理逻辑又会使得点数被恢复，没有正确计算消耗
    private fun syncCharacterEnergyFromMessages(agent: AgentInfo, messages: List<MsgInfo>) {
        val energyPoints =
            messages.count { msg ->
                msg.role == "assistant" &&
                    !msg.isOpening() &&
                    msg.content != LOADING_PLACEHOLDER_CONTENT
            }
        if (energyPoints <= lastSyncedEnergyPoints) return
        lastSyncedEnergyPoints = energyPoints
        viewModelScope.launch(Dispatchers.IO) {
            characterRepository.updateEnergy(agent.id, energyPoints)
        }
    }

    /** 加载聊天历史 - 使用增量同步优化体验 */
    private fun loadChatHistory(agentId: String) {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                // ✅ 修复：使用 loadChatHistoryUseCase 而不是 syncChatDataUseCase
                // 添加超时机制，避免无限等待
                kotlinx.coroutines.withTimeout(10000) { // 10秒超时
                    loadChatHistoryUseCase(agentId, PAGE_SIZE)
                }
                _isQueryMsgsCompleted.value = true
                LogUtils.i("ChatViewModel.loadChatHistory completed for $agentId")
            } catch (e: kotlinx.coroutines.TimeoutCancellationException) {
                LogUtils.e("ChatViewModel.loadChatHistory timeout for $agentId")
                // 超时也标记为完成，避免一直等待，让用户至少能看到 intro/opening
                _isQueryMsgsCompleted.value = true
            } catch (e: Exception) {
                LogUtils.e("ChatViewModel.loadChatHistory error for $agentId: ${e.message}")
                // 即使出错也标记为完成，避免 UI 一直等待
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

    fun newMsgFlowFinish() {
        _shouldFlowShow.value = false
    }

    /** 发送消息 - 使用新架构 */
    fun sendMsg() {
        // 防抖检查
        val currentTime = System.currentTimeMillis()
        if (currentTime - lastSendTime < SEND_DEBOUNCE_TIME) {
            return
        }
        lastSendTime = currentTime

        // 确保状态正确
        if (_isWaitingForReply.value) {
            return
        }

        val inputMsg = inputData.value
        if (inputMsg.isBlank()) {
            return
        }

        val agentId = _agentInfo.value?.id ?: return
        val agent = _agentInfo.value ?: return
        inputData.value = ""
        _isWaitingForReply.value = true
        _imagePickMessageId.value = null

        // 记录端到端时间的起始点（用户点击发送按钮的时间）
        val endToEndStartTime = System.currentTimeMillis()

        viewModelScope.launch(Dispatchers.IO) {
            // 如果是第一次聊天，上报聊天开始事件（准确反映用户第一次发送消息的行为）
            if (chatMessageRepository.countUserMessages(agentId) > 0) {
                FirebaseManager.logEvent(
                    FirebaseManager.Events.CHAT_STARTED,
                    FirebaseManager.safeEventParams(
                        "agent_id" to agent.id,
                        "agent_name" to agent.name,
                        "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                        "timestamp" to endToEndStartTime,
                    ),
                )
            }

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
                    "timestamp" to endToEndStartTime,
                ),
            )

            // Firebase Analytics - 记录消息发送按钮点击（CHAT_PAGE_CLICK事件）
            FirebaseManager.logEvent(
                FirebaseManager.Events.CHAT_PAGE_CLICK,
                FirebaseManager.safeEventParams(
                    "click_type" to "message_sent",
                    "agent_id" to agent.id,
                    "agent_name" to agent.name,
                    "message_length" to inputMsg.length,
                    "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                    "timestamp" to endToEndStartTime,
                ),
            )

            val aiResponseStartTime = System.currentTimeMillis()

            // ✅ 修复：将 MESSAGE_SENT 事件移到 API 调用开始时上报，确保与 MESSAGE_SEND_SUCCESS/FAILURE 一一对应
            FirebaseManager.logEvent(
                FirebaseManager.Events.MESSAGE_SENT,
                FirebaseManager.safeEventParams(
                    "agent_id" to agentId,
                    "agent_name" to agent.name,
                    "message_length" to inputMsg.length,
                    "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                    "timestamp" to aiResponseStartTime,
                ),
            )

            try {
                // 处理发送结果
                when (val result = chatMessageRepository.sendMessage(agentId, inputMsg.trimEnd())) {
                    is HttpResult.Success -> {
                        val responseTime = System.currentTimeMillis() - aiResponseStartTime
                        val endToEndTime = System.currentTimeMillis() - endToEndStartTime

                        // Firebase Analytics - 记录消息发送成功、AI响应时间和端到端时间
                        FirebaseManager.logEvent(
                            FirebaseManager.Events.MESSAGE_SEND_SUCCESS,
                            FirebaseManager.safeEventParams(
                                "agent_id" to agentId,
                                "agent_name" to (_agentInfo.value?.name),
                                "message_type" to "normal",
                                "response_code" to (result.data.code ?: 0),
                                "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                                "ai_response_time" to responseTime,
                                "end_to_end_time" to endToEndTime,
                            ),
                        )

                        // 记录AI响应时间性能指标（API调用时间）
                        FirebaseManager.logPerformanceMetric(
                            FirebaseManager.Events.AI_RESPONSE_TIME,
                            responseTime,
                            "ms",
                            FirebaseManager.safeEventParams(
                                "agent_id" to agentId,
                                "agent_name" to (_agentInfo.value?.name),
                                "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                            ),
                        )

                        val assistantContent =
                            result.data.data?.choices?.lastOrNull()?.message?.content
                        if (HeartAppUtils.isAppDebugMode(Utils.getApp())) {
                            BoostManager.recordChatTokens(agent, inputMsg)
                        }
                        val hasAssistantReply =
                            !result.data.data?.choices.isNullOrEmpty() ||
                                !assistantContent.isNullOrBlank()
                        if (hasAssistantReply) {
                            BoostManager.recordAssistantMessage(agent)
                        }

                        // 增加会话级别的消息计数（app 打开到进入后台/退出之间的消息数）
                        sessionMessageCount++
                        val lastShowTime = IntySetting.getFeedbackDialogLastShowTime()
                        val currentTime = System.currentTimeMillis()
                        val timeSinceLastShow = currentTime - lastShowTime

                        if (
                            // 会话消息数达到阈值
                            sessionMessageCount >=
                                UiConfigs.FeedbackDialog.SESSION_MESSAGES_COUNT_THRESHOLD &&
                                // 距离上次显示已超过最小间隔时间
                                timeSinceLastShow >= UiConfigs.FeedbackDialog.MIN_SHOW_INTERVAL_MS
                        ) {
                            IntySetting.setFeedbackDialogLastShowTime(currentTime)
                            // 确保在主线程更新 UI 状态
                            withContext(Dispatchers.Main) {
                                _showFeedbackRequestDialog.value = true
                            }
                        }

                        if (!result.data.data?.choices.isNullOrEmpty()) {
                            _shouldFlowShow.value = true
                        }

                        runCatching {
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
                                            "timestamp" to System.currentTimeMillis(),
                                        ),
                                    )
                                    showLimitDialog.emit(true)
                                }
                            }
                            .onFailure {
                                LogUtils.e("Error processing AI response: ${it.message}")
                                it.printStackTrace()
                                _isWaitingForReply.value = false
                            }
                    }

                    is HttpResult.Failure -> {
                        // 检查是否是取消相关的错误，避免在 Activity 退出后显示 Toast
                        if (
                            runCatching { ensureActive() }.isFailure ||
                                isCancellationError(result.message)
                        ) {
                            LogUtils.d(
                                "ChatViewModel.sendMsg: 请求被取消，不显示错误 Toast: ${result.message}"
                            )
                            return@launch
                        }

                        val responseTime = System.currentTimeMillis() - aiResponseStartTime
                        val endToEndTime = System.currentTimeMillis() - endToEndStartTime

                        // Firebase Analytics - 记录消息发送错误（包含API响应时间和端到端时间）
                        FirebaseManager.logEvent(
                            FirebaseManager.Events.MESSAGE_SEND_FAILURE,
                            FirebaseManager.safeEventParams(
                                "agent_id" to agentId,
                                "agent_name" to (_agentInfo.value?.name),
                                "message_type" to "normal",
                                "error_message" to "failure: ${result.message.take(100)}",
                                "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                                "ai_response_time" to responseTime,
                                "end_to_end_time" to endToEndTime,
                            ),
                        )

                        // Firebase Crashlytics - 记录非致命错误
                        FirebaseManager.recordException(
                            Exception("Message send failed: ${result.message}"),
                            FirebaseManager.safeEventParams(
                                "agent_id" to agentId,
                                "agent_name" to (_agentInfo.value?.name),
                                "response_time" to responseTime,
                                "end_to_end_time" to endToEndTime,
                            ),
                        )

                        // 显示网络错误
                        NetworkErrorHandler.showNetworkAwareError(
                            "Something went wrong. Please try again later."
                        )
                        _isWaitingForReply.value = false
                    }
                }
            } catch (e: Exception) {
                // 检查是否是取消相关的异常，如果是则不显示错误 Toast
                if (
                    e is CancellationException ||
                        runCatching { ensureActive() }.isFailure ||
                        isCancellationError(e.message)
                ) {
                    LogUtils.d("ChatViewModel.sendMsg: 请求被取消，不显示错误 Toast: ${e.message}")
                    return@launch
                }

                val endToEndTime = System.currentTimeMillis() - endToEndStartTime
                LogUtils.e("Unexpected error in sendMsg: ${e.message}")

                // Firebase Analytics - 记录异常情况下的端到端时间
                FirebaseManager.logEvent(
                    FirebaseManager.Events.MESSAGE_SEND_FAILURE,
                    FirebaseManager.safeEventParams(
                        "agent_id" to agentId,
                        "agent_name" to (_agentInfo.value?.name),
                        "message_type" to "normal",
                        "error_message" to
                            "exception: ${e.javaClass.simpleName}, ${
                            e.message?.take(
                                100
                            ) ?: "unknown error"
                        }",
                        "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                        "end_to_end_time" to endToEndTime,
                    ),
                )

                // Firebase Crashlytics - 记录异常
                FirebaseManager.recordException(
                    e,
                    FirebaseManager.safeEventParams(
                        "agent_id" to agentId,
                        "agent_name" to (_agentInfo.value?.name),
                        "end_to_end_time" to endToEndTime,
                    ),
                )

                NetworkErrorHandler.showNetworkAwareError(
                    "An unexpected error occurred while sending message"
                )
                _isWaitingForReply.value = false
            } finally {
                // 确保状态在最后被正确重置
                if (_isWaitingForReply.value) {
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
        /*val currentAgentId = agentInfo.value?.id ?: return
        if (loadMore) {
            viewModelScope.launch(Dispatchers.IO) {
                chatRepository.loadMoreMessages(currentAgentId, PAGE_SIZE)
            }
        } else {
            viewModelScope.launch(Dispatchers.IO) {
                loadChatHistoryUseCase(currentAgentId, PAGE_SIZE)
                _isQueryMsgsCompleted.value = true
            }
        }*/
    }

    /** 同步最新消息：优先加载本地数据，然后检查服务器更新 */
    private fun syncLatestMessages(agentId: String) {
        viewModelScope.launch(Dispatchers.IO) {
            syncChatDataUseCase(agentId, PAGE_SIZE)
            _isQueryMsgsCompleted.value = true
        }
    }

    /** 加载更多消息 */
    fun loadMoreMessages() {
        /*if (!_hasMoreMessages.value || _isLoadingMore.value || isQueryingMsgs) {
            return
        }
        val currentAgentId = agentInfo.value?.id ?: return
        viewModelScope.launch(Dispatchers.IO) {
            chatRepository.loadMoreMessages(currentAgentId, PAGE_SIZE)
        }*/
    }

    val showLimitDialog = MutableStateFlow(false)
    val requestLogin = MutableStateFlow(false)

    // 图片生成错误弹窗相关
    enum class ImageGenerationErrorType {
        FREE_USER_SUBSCRIPTION_REQUIRED, // 免费用户需要订阅
        VIP_USER_LIMIT_REACHED, // 会员用户达到每日限制
    }

    data class ImageGenerationDialogData(val errorType: ImageGenerationErrorType)

    val showImageGenerationDialog = MutableStateFlow<ImageGenerationDialogData?>(null)

    // 关闭limit次数 拦截消息的弹窗
    fun dismissDialog() = viewModelScope.launch { showLimitDialog.emit(false) }

    /** 隐藏反馈对话框 */
    fun hideFeedbackRequestDialog() {
        _showFeedbackRequestDialog.value = false
    }

    /** 重置会话消息计数（当 app 进入后台或退出时调用） */
    fun resetSessionMessageCount() {
        sessionMessageCount = 0
    }

    fun dismissImageGenerationDialog() =
        viewModelScope.launch { showImageGenerationDialog.emit(null) }

    fun dismissLoginRequest() = viewModelScope.launch { requestLogin.emit(false) }

    fun sendKeepTalkingMessage() {
        // 防抖检查
        val currentTime = System.currentTimeMillis()
        if (currentTime - lastSendTime < SEND_DEBOUNCE_TIME) {
            return
        }
        lastSendTime = currentTime

        // Firebase Analytics - 记录Keep Talking按钮点击
        agentInfo.value?.let { agent ->
            FirebaseManager.logEvent(
                FirebaseManager.Events.CHAT_PAGE_CLICK,
                FirebaseManager.safeEventParams(
                    "click_type" to "keep_talking",
                    "agent_id" to agent.id,
                    "agent_name" to agent.name,
                    "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                    "timestamp" to currentTime,
                ),
            )
        }

        launchBackground {
            val keepTalkingMsg = "continue"
            val keepTalkingStartTime = System.currentTimeMillis()
            _isWaitingForReply.value = true

            agentInfo.value?.let { agent ->
                try {
                    val aiResponseStartTime = System.currentTimeMillis()

                    // ✅ 修复：添加缺失的 MESSAGE_SENT 事件上报（在 API 调用开始时）
                    FirebaseManager.logEvent(
                        FirebaseManager.Events.MESSAGE_SENT,
                        FirebaseManager.safeEventParams(
                            "agent_id" to agent.id,
                            "agent_name" to agent.name,
                            "message_type" to "keep_talking",
                            "message_length" to keepTalkingMsg.length,
                            "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                            "timestamp" to aiResponseStartTime,
                        ),
                    )

                    val result = chatMessageRepository.sendMessage(agent.id, keepTalkingMsg)
                    _isWaitingForReply.value = false

                    when (result) {
                        is HttpResult.Success -> {
                            val responseTime = System.currentTimeMillis() - aiResponseStartTime
                            val endToEndTime = System.currentTimeMillis() - keepTalkingStartTime

                            // Firebase Analytics - 记录 Keep Talking 消息发送成功
                            FirebaseManager.logEvent(
                                FirebaseManager.Events.MESSAGE_SEND_SUCCESS,
                                FirebaseManager.safeEventParams(
                                    "agent_id" to agent.id,
                                    "agent_name" to agent.name,
                                    "message_type" to "keep_talking",
                                    "response_code" to (result.data.code ?: 0),
                                    "user_type" to
                                        if (VipStatusHelper.isUserVip()) "vip" else "free",
                                    "ai_response_time" to responseTime,
                                    "end_to_end_time" to endToEndTime,
                                ),
                            )

                            val assistantContent =
                                result.data.data?.choices?.lastOrNull()?.message?.content
                            if (HeartAppUtils.isAppDebugMode(Utils.getApp())) {
                                BoostManager.recordChatTokens(agent, keepTalkingMsg)
                            }
                            val hasAssistantReply =
                                !result.data.data?.choices.isNullOrEmpty() ||
                                    !assistantContent.isNullOrBlank()
                            if (hasAssistantReply) {
                                BoostManager.recordAssistantMessage(agent)
                            }

                            runCatching {
                                    // 有免费次数限制，需要vip订阅
                                    if (
                                        result.data.code ==
                                            BusinessErrorCodes.SUBSCRIPTION_REQUIRED_CODE
                                    ) {
                                        showLimitDialog.emit(true)
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
                            // 检查是否是取消相关的错误，避免在 Activity 退出后显示 Toast
                            if (
                                runCatching { ensureActive() }.isFailure ||
                                    isCancellationError(result.message)
                            ) {
                                LogUtils.d(
                                    "ChatViewModel.sendKeepTalkingMessage: 请求被取消，不显示错误 Toast: ${result.message}"
                                )
                                return@launchBackground
                            }

                            val responseTime = System.currentTimeMillis() - aiResponseStartTime
                            val endToEndTime = System.currentTimeMillis() - keepTalkingStartTime

                            // Firebase Analytics - 记录 Keep Talking 消息发送错误
                            FirebaseManager.logEvent(
                                FirebaseManager.Events.MESSAGE_SEND_FAILURE,
                                FirebaseManager.safeEventParams(
                                    "agent_id" to agent.id,
                                    "agent_name" to agent.name,
                                    "message_type" to "keep_talking",
                                    "error_message" to "failure: ${result.message.take(100)}",
                                    "user_type" to
                                        if (VipStatusHelper.isUserVip()) "vip" else "free",
                                    "ai_response_time" to responseTime,
                                    "end_to_end_time" to endToEndTime,
                                ),
                            )

                            NetworkErrorHandler.showNetworkAwareError(result.message)
                            // 错误恢复：确保状态正确
                            _isWaitingForReply.value = false
                        }
                    }
                } catch (e: Exception) {
                    // 检查是否是取消相关的异常，如果是则不显示错误 Toast
                    if (
                        e is CancellationException ||
                            runCatching { ensureActive() }.isFailure ||
                            isCancellationError(e.message)
                    ) {
                        LogUtils.d(
                            "ChatViewModel.sendKeepTalkingMessage: 请求被取消，不显示错误 Toast: ${e.message}"
                        )
                        return@launchBackground
                    }
                    val endToEndTime = System.currentTimeMillis() - keepTalkingStartTime
                    LogUtils.e("Unexpected error in sendKeepTalkingMessage: ${e.message}")

                    // Firebase Analytics - 记录 Keep Talking 消息发送异常
                    FirebaseManager.logEvent(
                        FirebaseManager.Events.MESSAGE_SEND_FAILURE,
                        FirebaseManager.safeEventParams(
                            "agent_id" to agent.id,
                            "agent_name" to agent.name,
                            "message_type" to "keep_talking",
                            "error_message" to
                                "exception: ${e.javaClass.simpleName}, ${
                                e.message?.take(
                                    100
                                ) ?: "unknown error"
                            }",
                            "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                            "end_to_end_time" to endToEndTime,
                        ),
                    )

                    NetworkErrorHandler.showNetworkAwareError(
                        "An unexpected error occurred while sending keep talking message"
                    )
                    _isWaitingForReply.value = false
                }
            }
                ?: run {
                    // 如果没有 agent 信息，恢复状态
                    _isWaitingForReply.value = false
                    LogUtils.e("No agent info available for keep talking")
                }
        }
    }

    /** Like 消息 - 通过 Repository 更新并上报 Firebase 事件 */
    fun likeMessage(localMsgId: String) {
        val agentId = _agentId.value ?: return

        viewModelScope.launch(Dispatchers.IO) {
            val targetMessage = chatMessageRepository.getMessage(agentId, localMsgId)

            // 如果找不到消息，记录日志但不发送事件
            if (targetMessage == null) {
                LogUtils.e("Cannot find message with localMsgId: $localMsgId")
            } else {
                // 业务逻辑：本地状态更新始终使用localMsgId（这是本地标识符）
                updateMessageFeedbackUseCase(agentId, localMsgId, MsgInfo.UserFeedback.LIKE)

                // 如果消息有服务端id，调用投票接口
                val messageId = targetMessage.localId

                if (messageId.isNotEmpty()) {
                    when (val result = voteMessageUseCase(agentId, messageId, VoteConstants.LIKE)) {
                        is HttpResult.Success -> {
                            LogUtils.i("Vote message success: like")
                        }

                        is HttpResult.Failure -> {
                            LogUtils.e("Vote message failure: ${result.message}")
                        }
                    }
                }

                // Firebase事件统计：优先使用服务端id（message_id），这是有意义的标识
                // 如果服务端id为空，说明消息还未同步到服务端，此时使用localMsgId作为fallback
                val messageIdForEvent = messageId.ifEmpty { localMsgId }

                val eventParams =
                    FirebaseManager.safeEventParams(
                        "click_type" to "message_like",
                        "agent_id" to agentId,
                        "agent_name" to agentFlow.value?.name.orEmpty(),
                        "message_id" to messageIdForEvent, // 优先使用服务端id，这才是有意义的标识
                        "message_length" to targetMessage.content.length,
                        "has_generated_image" to !targetMessage.generatedImageUrl.isNullOrBlank(),
                        "is_opening" to targetMessage.isOpening,
                        "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                        "timestamp" to System.currentTimeMillis(),
                    )
                FirebaseManager.logEvent(FirebaseManager.Events.CHAT_PAGE_CLICK, eventParams)
            }
        }
    }

    /** Dislike 消息 - 通过 Repository 更新并上报 Firebase 事件 */
    fun dislikeMessage(localMsgId: String) {
        val agent = agentFlow.value ?: return

        viewModelScope.launch(Dispatchers.IO) {
            val targetMessage = chatMessageRepository.getMessage(agent.agentId, localMsgId)
            // 如果找不到消息，记录日志但不发送事件
            if (targetMessage == null) {
                LogUtils.e("Cannot find message with localMsgId: $localMsgId")
                return@launch
            }

            val previousFeedback = targetMessage.userFeedback ?: "NONE"

            // 业务逻辑：本地状态更新始终使用localMsgId（这是本地标识符）
            updateMessageFeedbackUseCase(agent.agentId, localMsgId, MsgInfo.UserFeedback.DISLIKE)

            // 如果消息有服务端id，调用投票接口
            val messageId = targetMessage.remoteId
            if (!messageId.isNullOrBlank()) {
                viewModelScope.launch(Dispatchers.IO) {
                    when (
                        val result =
                            voteMessageUseCase(agent.agentId, messageId, VoteConstants.DISLIKE)
                    ) {
                        is HttpResult.Success -> {
                            LogUtils.i("Vote message success: dislike")
                        }

                        is HttpResult.Failure -> {
                            LogUtils.e("Vote message failure: ${result.message}")
                        }
                    }
                }
            }

            // Firebase事件统计：优先使用服务端id（message_id），这是有意义的标识
            // 如果服务端id为空，说明消息还未同步到服务端，此时使用localMsgId作为fallback
            val messageIdForEvent = messageId?.ifEmpty { localMsgId }

            val eventParams =
                FirebaseManager.safeEventParams(
                    "click_type" to "message_dislike",
                    "agent_id" to agent.agentId,
                    "agent_name" to agent.name,
                    "message_id" to messageIdForEvent, // 优先使用服务端id，这才是有意义的标识
                    "message_length" to targetMessage.content.length,
                    "has_generated_image" to !targetMessage.generatedImageUrl.isNullOrBlank(),
                    "is_opening" to targetMessage.isOpening,
                    "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                    "timestamp" to System.currentTimeMillis(),
                )

            FirebaseManager.logEvent(FirebaseManager.Events.CHAT_PAGE_CLICK, eventParams)
        }
    }

    /** Recall 消息 - 重新生成最新消息（类似 keep talking 的实现） */
    fun recallMessage() {
        // 防抖检查
        val currentTime = System.currentTimeMillis()
        if (currentTime - lastSendTime < SEND_DEBOUNCE_TIME) {
            return
        }
        lastSendTime = currentTime

        // 确保状态正确
        if (_isWaitingForReply.value) {
            return
        }

        val agentId = _agentInfo.value?.id ?: return
        _isWaitingForReply.value = true

        launchBackground {
            try {
                chatMessageRepository.recallLastAssistantMessage(agentId)
                _isWaitingForReply.value = false
                _shouldFlowShow.value = true
            } catch (e: Exception) {
                LogUtils.e("Recall message error: ${e.message}")
                NetworkErrorHandler.showNetworkAwareError("Failed to recall message: ${e.message}")
                _isWaitingForReply.value = false
            }
        }
    }

    fun deleteMessage(localMsgId: String) {
        val agentId = _agentInfo.value?.id ?: return
        viewModelScope.launch(Dispatchers.IO) { chatRepository.removeMessage(agentId, localMsgId) }
    }

    fun clearGeneratedImage(messageId: String) {
        val agentId = _agentInfo.value?.id ?: return
        chatRepository.updateMessageGeneratedImage(agentId, messageId, null)
    }

    fun generateImageForMessageOrPickImage(messageId: String) {
        viewModelScope.launch {
            if (UserProfileManager.profile.first().userPhoto.isNullOrEmpty()) {
                _imagePickMessageId.value = messageId
            } else {
                generateImageForMessage(messageId)
            }
        }
    }

    fun generateImageForMessage() {
        imagePickMessageId.value?.let { generateImageForMessage(it) }
        _imagePickMessageId.value = null
    }

    fun generateImageForMessage(messageId: String) {
        val agent = agentFlow.value ?: return

        // ✅ 修复：将 clicked 事件移到协程内部，确保即使参数检查失败也能上报
        // 同时，即使参数为空也先上报 clicked 事件，然后在协程内部检查并上报 failure
        viewModelScope.launch(Dispatchers.IO) {
            val startTime = System.currentTimeMillis()

            // ✅ 修复：在协程内部、API 调用前上报 clicked 事件，确保不会丢失
            FirebaseManager.logEvent(
                FirebaseManager.Events.MESSAGE_TO_IMAGE_GENERATION_BUTTON_CLICKED,
                FirebaseManager.safeEventParams(
                    "agent_id" to (agent.agentId),
                    "agent_name" to (agent.name),
                    "message_id" to messageId,
                    "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                    "timestamp" to startTime,
                ),
            )

            // Firebase Analytics - 记录消息生图按钮点击（CHAT_PAGE_CLICK事件）
            FirebaseManager.logEvent(
                FirebaseManager.Events.CHAT_PAGE_CLICK,
                FirebaseManager.safeEventParams(
                    "click_type" to "message_to_image",
                    "agent_id" to (agent.agentId),
                    "agent_name" to (agent.name),
                    "message_id" to messageId,
                    "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                    "timestamp" to startTime,
                ),
            )

            // ✅ 修复：参数检查失败时，上报 failure 事件并重置状态
            val endTime = System.currentTimeMillis()
            FirebaseManager.logEvent(
                FirebaseManager.Events.MESSAGE_TO_IMAGE_GENERATION_FAILURE,
                FirebaseManager.safeEventParams(
                    "agent_id" to (agent.agentId),
                    "agent_name" to (agent.name),
                    "message_id" to messageId,
                    "error_message" to "agent_id or agent is null",
                    "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                    "generation_time_ms" to (endTime - startTime),
                    "timestamp" to endTime,
                ),
            )
            LogUtils.e("generateImageForMessage: agentId or agent is null")
            // 重置生图状态，确保可以再次点击
            chatRepository.updateMessageGeneratedImage(agent.agentId, messageId, null)

            try {
                val result = generateImageUseCase(agent.agentId, messageId)
                val endTime = System.currentTimeMillis()
                val generationTime = endTime - startTime

                when (result) {
                    is HttpResult.Success -> {
                        if (HeartAppUtils.isAppDebugMode(Utils.getApp())) {
                            BoostManager.recordImageGeneration(agent.agentId)
                        }
                        // Firebase Analytics - 记录图片生成成功
                        FirebaseManager.logEvent(
                            FirebaseManager.Events.MESSAGE_TO_IMAGE_GENERATION_SUCCESS,
                            FirebaseManager.safeEventParams(
                                "agent_id" to agent.name,
                                "agent_name" to agent.name,
                                "message_id" to messageId,
                                "image_url" to result.data.imageUrl,
                                "image_width" to result.data.width,
                                "image_height" to result.data.height,
                                "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                                "generation_time_ms" to generationTime,
                                "timestamp" to endTime,
                            ),
                        )

                        // Firebase Performance - 记录图片生成耗时
                        FirebaseManager.logPerformanceMetric(
                            FirebaseManager.Events.IMAGE_GENERATION_TIME,
                            generationTime.toLong(),
                            "ms",
                            FirebaseManager.safeEventParams(
                                "agent_id" to agent,
                                "agent_name" to agent.name,
                                "message_id" to messageId,
                                "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                            ),
                        )

                        // 重置点赞/点踩状态，确保生图后可以重新点赞/点踩
                        val targetMessage =
                            chatMessageRepository.getMessage(agent.agentId, messageId)
                        targetMessage?.let {
                            updateMessageFeedbackUseCase(agent.agentId, targetMessage.localId, null)
                        }
                    }

                    is HttpResult.Failure -> {
                        LogUtils.e(
                            "Image generation failed: code=${result.code}, message=${result.message}"
                        )

                        val isVip = VipStatusHelper.isUserVip()

                        // 检查是否是业务错误码
                        when {
                            // 免费用户的订阅限制：显示会员引导弹窗
                            result.code == BusinessErrorCodes.SUBSCRIPTION_REQUIRED_CODE -> {
                                // Firebase Analytics - 记录图片生成限制达到
                                FirebaseManager.logEvent(
                                    FirebaseManager.Events.IMAGE_GENERATION_LIMIT_REACHED,
                                    FirebaseManager.safeEventParams(
                                        "agent_id" to agent.agentId,
                                        "agent_name" to agent.name,
                                        "message_id" to messageId,
                                        "error_code" to result.code,
                                        "error_message" to result.message,
                                        "user_type" to "free",
                                        "generation_time_ms" to generationTime,
                                        "timestamp" to endTime,
                                    ),
                                )

                                // 显示会员引导弹窗（使用 UnlimitChatDialog，但文案特殊）
                                val dialogData =
                                    ImageGenerationDialogData(
                                        errorType =
                                            ImageGenerationErrorType.FREE_USER_SUBSCRIPTION_REQUIRED
                                    )
                                showImageGenerationDialog.emit(dialogData)
                            }
                            // 会员用户的每日限制：显示错误提示弹窗
                            result.code == BusinessErrorCodes.IMAGE_GENERATION_LIMIT_REACHED_CODE &&
                                isVip -> {
                                // Firebase Analytics - 记录图片生成限制达到
                                FirebaseManager.logEvent(
                                    FirebaseManager.Events.IMAGE_GENERATION_LIMIT_REACHED,
                                    FirebaseManager.safeEventParams(
                                        "agent_id" to agent.agentId,
                                        "agent_name" to agent.name,
                                        "message_id" to messageId,
                                        "error_code" to result.code,
                                        "error_message" to result.message,
                                        "user_type" to "vip",
                                        "generation_time_ms" to generationTime,
                                        "timestamp" to endTime,
                                    ),
                                )

                                // 显示会员用户的错误提示弹窗
                                val dialogData =
                                    ImageGenerationDialogData(
                                        errorType = ImageGenerationErrorType.VIP_USER_LIMIT_REACHED
                                    )
                                showImageGenerationDialog.emit(dialogData)
                            }
                            // 其他错误：在消息列表中显示 tips 消息
                            else -> {
                                // Firebase Analytics - 记录图片生成失败
                                FirebaseManager.logEvent(
                                    FirebaseManager.Events.MESSAGE_TO_IMAGE_GENERATION_FAILURE,
                                    FirebaseManager.safeEventParams(
                                        "agent_id" to agent.agentId,
                                        "agent_name" to agent.name,
                                        "message_id" to messageId,
                                        "error_code" to result.code,
                                        "error_message" to result.message,
                                        "user_type" to if (isVip) "vip" else "free",
                                        "generation_time_ms" to generationTime,
                                        "timestamp" to endTime,
                                    ),
                                )

                                // 在消息列表中添加 tips 消息（使用字符串常量，后续在 UI 层处理）
                                val tipMessage =
                                    MsgInfo(
                                        content = "image_generation_error_tip", // 特殊标记，UI 层会转换为实际文案
                                        role = "system",
                                        localMsgId = "image_generation_error_${System.nanoTime()}",
                                        meta_data = MsgInfo.MsgMetaData(agentId = agent.agentId),
                                    )
                                chatRepository.addMessage(agent.agentId, tipMessage)
                            }
                        }
                    }
                }
            } catch (e: Exception) {
                val endTime = System.currentTimeMillis()
                val generationTime = endTime - startTime
                LogUtils.e("Image generation error: ${e.message}")

                // Firebase Analytics - 记录图片生成异常
                FirebaseManager.logEvent(
                    FirebaseManager.Events.MESSAGE_TO_IMAGE_GENERATION_FAILURE,
                    FirebaseManager.safeEventParams(
                        "agent_id" to agent.agentId,
                        "agent_name" to agent.name,
                        "message_id" to messageId,
                        "error_message" to
                            "exception: ${e.javaClass.simpleName}, ${e.message ?: "unknown error"}",
                        "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                        "generation_time_ms" to generationTime,
                        "timestamp" to endTime,
                    ),
                )

                // Firebase Crashlytics - 记录异常
                FirebaseManager.recordException(
                    e,
                    FirebaseManager.safeEventParams(
                        "agent_id" to agent.agentId,
                        "agent_name" to agent.name,
                        "message_id" to messageId,
                        "generation_time_ms" to generationTime,
                    ),
                )

                // 重置生图状态，确保可以再次点击
                chatRepository.updateMessageGeneratedImage(agent.agentId, messageId, null)

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
        val result = NetServiceMgr.getChatApi().getChatSettings(agentId)
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
        val result = NetServiceMgr.getChatApi().updateChatSettings(agentId, req)
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

    fun setAgentID(agentId: String, forceSync: Boolean = false) {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                _agentId.value = agentId
                when (val result = characterRepository.refreshAgent(agentId)) {
                    is HttpResult.Success -> {
                        AgentStore.addAgent(result.data)
                        setAgentInfo(result.data, forceSync = forceSync)
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
        _agentInfo.value = null
        inputData.update { "" }
        inputSelection.value = 0
        _isWaitingForReply.value = false
        isQueryingMsgs = false
        lastQueryAgentId = null
        lastQueryTime = 0L
        lastSendTime = 0L
        characterEnergyJob?.cancel()
        _characterEnergy.value = 0
        lastSyncedEnergyPoints = 0

        // 清理chatSettings
        _chatSettings.value = emptyMap()

        // 清理消息查询完成状态
        _isQueryMsgsCompleted.value = false
    }

    suspend fun appendBoostSystemMessage(agent: AgentInfo, points: Int, totalBoosts: Int) {
        val message =
            MsgInfo(
                content =
                    Utils.getApp()
                        .getString(R.string.boost_system_message, points, agent.name, totalBoosts),
                role = "system",
                localMsgId = "boost_${System.nanoTime()}",
                meta_data = MsgInfo.MsgMetaData(agentId = agent.id),
            )
        chatRepository.addMessage(agent.id, message)
    }

    suspend fun reset() {
        val agentId = agentInfo.value?.id ?: throw Exception("Agent is null")

        if (!chatRepository.clearMessage(agentId)) {
            throw Exception("Reset Failed")
        }

        // 1. 删除本地历史消息
        chatMessageRepository.clearMessages(agentId)
        // 2. 清理 ViewModel 中的状态
        _isLoadingMore.value = false
        _hasMoreMessages.value = true
        _isQueryMsgsCompleted.value = false
        _imagePickMessageId.value = null
        OpeningPlayState.clearAgentPlayed(agentId)

        // 3. 重新绑定消息流（因为 clearChatData 会清理内存缓存）
        // 注意：如果使用了 RoomDataSource，消息流会自动更新
        // 4. 拉取最新消息
        _isQueryMsgsCompleted.value = true

        LogUtils.i("ChatViewModel.resetChatState completed for $agentId")
    }
}
