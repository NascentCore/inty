package com.ai.inty.viewmodels

import android.app.Activity
import androidx.lifecycle.viewModelScope
import com.ai.inty.R
import com.ai.inty.base.BaseActivityViewModel
import com.ai.inty.beans.AgentInfo
import com.ai.inty.beans.ChatSettingsReq
import com.ai.inty.beans.ChatSettingsResponse
import com.ai.inty.beans.ConversationItem
import com.ai.inty.beans.MsgInfo
import com.ai.inty.beans.SendMsgReq
import com.ai.inty.beans.UserProfile
import com.ai.inty.billing.VipStatusHelper
import com.ai.inty.net.IChatApi
import com.ai.inty.utils.UserProfileManager
import com.architecture.httplib.core.HttpResult
import com.inty.utils.AppEnv
import com.inty.utils.log.EasyLog
import com.inty.utils.storage.IntySetting
import com.therouter.TheRouter
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

// 聊天对话 app + backend 交互
// app 启动
// app 请求聊天记录（/agents/{agent_id}/messages
// backednf 创建对话（如果是首次对话）
// backend 返回对话 ID
// app 请求聊天回复（/api/v1/chat/completions/{agent_id}）

// 操作什么数据，支持什么 UI？Model 是 beans
// View 是各类 page/activity。
class ChatViewModel : BaseActivityViewModel() {

    private val _agentInfo = MutableStateFlow<AgentInfo?>(null)
    val agentInfo = _agentInfo.asStateFlow()

    // 使用 StateFlow 替代 mutableStateListOf 来解决并发问题
    private val _msgs = MutableStateFlow<List<MsgInfo>>(emptyList())
    val msgs = _msgs.asStateFlow()
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

    // 防重复请求机制
    private var isQueryingMsgs = false
    private var lastQueryAgentId: String? = null
    private var lastQueryTime = 0L
    private val QUERY_DEBOUNCE_TIME = 2000L // 2秒防抖

    // 对话列表分页状态
    private var currentConversationsPage = 0
    private var _isLoadingConversations = MutableStateFlow(false)
    val isLoadingConversations = _isLoadingConversations.asStateFlow()
    private var hasMoreConversations = true


    // 延迟获取依赖，避免在构造函数中立即获取导致空指针异常
    private val chatApi by lazy {
        TheRouter.get(IChatApi::class.java)
            ?: throw IllegalStateException("IChatApi not found in TheRouter")
    }

    init {
        EasyLog.log("ChatViewModel = ${hashCode()}")
    }


    fun setAgentInfo(agentInfo: AgentInfo?) {
        EasyLog.log("setAgentInfo called with agent: ${agentInfo?.id}")

        // 如果 agent 为空，清理所有状态
        if (agentInfo == null) {
            _agentInfo.value = null
            _msgs.update { emptyList() }
            lastQueryAgentId = null
            isQueryingMsgs = false
            return
        }

        // 如果是同一个 agent，只更新信息，不重新查询消息
        if (_agentInfo.value?.id == agentInfo.id) {
            EasyLog.log("Same agent, only updating info")
            _agentInfo.value = agentInfo
            return
        }

        _agentInfo.value = agentInfo
        _msgs.update { emptyList() }
        lastQueryAgentId = agentInfo.id
        isQueryingMsgs = false

        // 查询新 agent 的消息
        queryMsgs()
        //查询改聊天设置
        getChatSetting()
    }

    fun updateAgentFollowState(agentId: String, isFollowed: Boolean) {
        EasyLog.log("ChatViewModel updateAgentFollowState - agentId: $agentId, isFollowed: $isFollowed")
        _agentInfo.update { currentAgent ->
            currentAgent?.let { agent ->
                if (agent.id == agentId) {
                    agent.copy(isFollowed = isFollowed)
                } else {
                    agent
                }
            }
        }
    }

    fun queryMsgs() {
        // 防重复请求检查
        val currentTime = System.currentTimeMillis()
        val currentAgentId = agentInfo.value?.id

        if (isQueryingMsgs) {
            EasyLog.log("Already querying messages, skipping")
            return
        }

        if (currentAgentId == null) {
            EasyLog.log("No agent info available, skipping query")
            return
        }

        if (lastQueryAgentId == currentAgentId &&
            currentTime - lastQueryTime < QUERY_DEBOUNCE_TIME
        ) {
            EasyLog.log("Query debounced for agent $currentAgentId")
            return
        }

        isQueryingMsgs = true
        lastQueryAgentId = currentAgentId
        lastQueryTime = currentTime

        viewModelScope.launch(Dispatchers.IO) {
            try {
                val currentAgentValue = agentInfo.value
                currentAgentValue?.let { agent ->
                    EasyLog.log("Querying messages for agent: ${agent.id}")
                    val result = chatApi.getMsgs(agent.id, 100, 0)
                    EasyLog.log("queryMsgs result for ${agent.id} = $result")
                    when (result) {
                        is HttpResult.Success -> {
                            // 去重处理：基于内容和角色的组合去重，同时考虑时间戳
                            val uniqueMessages = result.data.messages.distinctBy { msg ->
                                "${msg.role}_${msg.content}_${msg.msgId}"
                            }
                            _msgs.update { uniqueMessages }
                            EasyLog.log("Successfully loaded ${uniqueMessages.size} unique messages for agent ${agent.id} (original: ${result.data.messages.size})")
                        }

                        is HttpResult.Failure -> {
                            EasyLog.log("Failed to query messages: ${result.message}")
                            showNetworkAwareError(result.message)
                        }
                    }
                }
            } catch (e: Exception) {
                EasyLog.log("queryMsgs exception: ${e.message}", priority = EasyLog.ERROR)
                handleNetworkException(e)
            } finally {
                isQueryingMsgs = false
            }
        }
    }

    val showLimitDialog = MutableStateFlow(false)
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

        launchWithNetCheck {
            try {
                val inputMsg = inputData.value
                if (inputMsg.isBlank()) {
                    EasyLog.log("Empty message, ignoring send request")
                    return@launchWithNetCheck
                }

                inputData.update { "" }
                EasyLog.log("send msg $inputMsg")

                val msgInfo = MsgInfo(
                    content = inputMsg,
                    role = "user"
                )

                // 添加临时的加载消息
                val loadingMsg = MsgInfo(
                    content = "loading_animation", // 特殊标识符
                    role = "assistant"
                )

                // 使用 StateFlow 的 update 方法安全地更新列表
                _msgs.update { currentMsgs ->
                    try {
                        val newMsgs = mutableListOf<MsgInfo>()
                        newMsgs.add(loadingMsg) // 添加加载动画消息
                        newMsgs.add(msgInfo) // 添加用户消息
                        // 创建当前消息的副本以避免并发修改
                        newMsgs.addAll(currentMsgs.toList())
                        EasyLog.log("Successfully updated messages - new count: ${newMsgs.size}")
                        newMsgs
                    } catch (e: Exception) {
                        EasyLog.log(
                            "Error updating messages list: ${e.message}",
                            priority = EasyLog.ERROR
                        )
                        currentMsgs // 返回原列表，避免数据丢失
                    }
                }
                _isWaitingForReply.value = true

                val req = SendMsgReq(listOf(msgInfo))
                val currentAgent = agentInfo.value
                currentAgent?.let { agent ->

                    val result = chatApi.sendMsg(agent.id, req)

                    EasyLog.log("sendMsg($agent, $req) -> $result")

                    // 移除加载消息
                    _msgs.update { currentMsgs ->
                        currentMsgs.filterNot { it.content == "loading_animation" && it.role == "assistant" }
                    }
                    _isWaitingForReply.value = false

                    when (result) {
                        is HttpResult.Success -> {
                            runCatching {
                                //有免费次数限制，需要vip订阅
                                if (result.data.code == 10001001) {
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
                                            priority = EasyLog.ERROR
                                        )
                                        currentMsgs // 返回原列表，避免数据丢失
                                    }
                                }

                                result.data.data?.choices?.lastOrNull()?.message?.content?.let { str ->
                                    IntySetting.setConversationReaded(
                                        agent.id,
                                        str
                                    )
                                }
                            }.onFailure {
                                EasyLog.log(
                                    "Error processing AI response: ${it.message}",
                                    priority = EasyLog.ERROR
                                )
                                it.printStackTrace()
                                // 错误恢复：确保状态正确
                                _isWaitingForReply.value = false
                            }
                        }

                        is HttpResult.Failure -> {
                            // 错误恢复：确保状态正确
                            _isWaitingForReply.value = false
                        }
                    }
                } ?: run {
                    // 如果没有 agent 信息，恢复状态
                    _isWaitingForReply.value = false
                    EasyLog.log(
                        "No agent info available for sending message",
                        priority = EasyLog.ERROR
                    )
                }
            } catch (e: Exception) {
                EasyLog.log("Unexpected error in sendMsg: ${e.message}", priority = EasyLog.ERROR)
                _isWaitingForReply.value = false
            } finally {
                // 确保状态在最后被正确重置
                if (_isWaitingForReply.value) {
                    EasyLog.log("Force reset waiting state due to completion")
                    _isWaitingForReply.value = false
                }
            }
        }
    }

    //关闭limit次数 拦截消息的弹窗
    fun dismissDialog() = viewModelScope.launch {
        showLimitDialog.emit(false)
    }

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
            EasyLog.log("send keep talking msg")

            val msgInfo = MsgInfo(content = keepTalkingMsg, role = "user")

            // 添加临时的加载消息 (keep talking不显示用户消息，只显示加载动画)
            val loadingMsg = MsgInfo(
                content = "loading_animation", // 特殊标识符
                role = "assistant"
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
                    currentMsgs.filterNot { it.content == "loading_animation" && it.role == "assistant" }
                }
                _isWaitingForReply.value = false

                when (result) {
                    is HttpResult.Success -> {
                        runCatching {
                            //有免费次数限制，需要vip订阅
                            if (result.data.code == 10001001) {
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

                            result.data.data?.choices?.lastOrNull()?.message?.content?.let { str ->
                                IntySetting.setConversationReaded(
                                    agent.id,
                                    str
                                )
                            }

                        }.onFailure {
                            EasyLog.log(
                                "Error processing keep talking AI response: ${it.message}",
                                priority = EasyLog.ERROR
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
            } ?: run {
                // 如果没有 agent 信息，恢复状态
                _isWaitingForReply.value = false
                EasyLog.log("No agent info available for keep talking", priority = EasyLog.ERROR)
            }
        }
    }

    //获取聊天消息设置
    val chatSetting = MutableStateFlow<ChatSettingsResponse.ChatSettingRspData?>(null)
    private fun getChatSetting() = launchWithNetCheck {
        val agentId = agentInfo.value?.id ?: return@launchWithNetCheck
        //有agent信息，才请求
        val result = chatApi.getChatSettings(agentId)
        when (result) {
            is HttpResult.Failure -> showNetworkAwareError(result.message)
            is HttpResult.Success -> {
                chatSetting.update { result.data }
            }
        }
    }

    //高级模型定制化回复的接口调用
    fun updateChatReplySettings(prompt: String) = launchWithNetCheck {
        val agentId = agentInfo.value?.id ?: return@launchWithNetCheck
        //有agent信息，才请求
        val req = ChatSettingsReq(style_prompt = prompt)
        val result = chatApi.updateChatSettings(agentId, req)
        when (result) {
            is HttpResult.Failure -> showNetworkAwareError(result.message)
            is HttpResult.Success -> {
                showNetworkAwareError(AppEnv.context.getString(R.string.custom_reply_successful))
                //要更新chatsetting
                chatSetting.emit(result.data.data)
            }
        }
    }

    fun getConversations() {
        EasyLog.log("getConversations - 开始加载第一页")
        currentConversationsPage = 0
        hasMoreConversations = true
        _conversations.value = emptyList()
        loadConversations()
    }

    fun loadMoreConversations() {
        if (!_isLoadingConversations.value && hasMoreConversations) {
            EasyLog.log("loadMoreConversations - 开始加载第${currentConversationsPage + 1}页")
            currentConversationsPage++
            loadConversations()
        } else {
            EasyLog.log("loadMoreConversations - 跳过加载: isLoading=${_isLoadingConversations.value}, hasMoreData=$hasMoreConversations")
        }
    }

    private fun loadConversations() {
        if (_isLoadingConversations.value) return

        _isLoadingConversations.value = true
        EasyLog.log("loadConversations - 当前页索引: $currentConversationsPage, 显示页码: ${currentConversationsPage + 1}")

        viewModelScope.launch(Dispatchers.IO) {
            try {
                val skip = currentConversationsPage * 20
                val result = chatApi.getConversations(skip, 20)
                EasyLog.log("loadConversations - skip: $skip, limit: 20, result: $result")

                when (result) {
                    is HttpResult.Success -> {
                        val userInitiatedConversations = result.data

                        if (userInitiatedConversations.isEmpty()) {
                            hasMoreConversations = false
                            EasyLog.log("loadConversations - 第${currentConversationsPage + 1}页数据为空，没有更多数据")
                        } else {
                            if (currentConversationsPage == 0) {
                                // 第一页，直接替换
                                _conversations.value = userInitiatedConversations
                                EasyLog.log("loadConversations - 替换第一页数据: ${userInitiatedConversations.size}个")
                            } else {
                                // 后续页，追加到现有列表
                                _conversations.value =
                                    _conversations.value + userInitiatedConversations
                                EasyLog.log("loadConversations - 追加第${currentConversationsPage + 1}页数据: ${userInitiatedConversations.size}个，总计: ${_conversations.value.size}个")
                            }
                        }
                    }

                    is HttpResult.Failure -> {
                        EasyLog.log(
                            "loadConversations - 第${currentConversationsPage + 1}页加载失败: ${result.message}",
                            priority = EasyLog.ERROR
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
                    priority = EasyLog.ERROR
                )
                // 如果加载失败，回退页码
                if (currentConversationsPage > 0) {
                    currentConversationsPage--
                    EasyLog.log("loadConversations - 页码回退到: $currentConversationsPage")
                }
            }
            _isLoadingConversations.value = false

            EasyLog.log("loadConversations - 完成，当前列表大小: ${_conversations.value.size}")
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

    //标记会话消息 已读
    fun setConversationReaded(conversationItem: ConversationItem) {
        IntySetting.setConversationReaded(conversationItem.agentId, conversationItem.lastMessage)

        _conversations.update { currentConversations ->
            currentConversations.map { conversation ->
                if (conversation.id == conversationItem.id && conversation.agentId == conversationItem.agentId) {
                    conversation.copy(isNew = false)
                } else {
                    conversation
                }
            }
        }
    }

    // 新增：清理所有数据的方法
    fun clearAllData() {
        EasyLog.log("Clearing all data for ChatViewModel ${hashCode()}")
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

        EasyLog.log("All data cleared for ChatViewModel ${hashCode()}")
    }

    fun setUserProfile(userProfile: UserProfile) {
        _userProfile.value = userProfile
    }

    fun updateUserInfo() {
        if (UserProfileManager.hasUserProfile()) {
            _userProfile.value = UserProfileManager.getUserProfile()
            EasyLog.log("Loaded user profile from cache: ${_userProfile.value.nickname}")
        }
    }


    //购买vip会员订阅，最低档
    fun purchaseFirstVip(activity: Activity) {
        VipStatusHelper.purchaseFirstVip(activity) { error ->
            showNetworkAwareError(error)
        }
    }
}
