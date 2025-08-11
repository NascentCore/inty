package com.ai.inty.viewmodels

import android.app.Activity
import androidx.compose.runtime.mutableStateListOf
import androidx.lifecycle.viewModelScope
import com.ai.inty.R
import com.ai.inty.base.BaseActivityViewModel
import com.ai.inty.beans.AgentInfo
import com.ai.inty.beans.ChatSettingsReq
import com.ai.inty.beans.ConversationItem
import com.ai.inty.beans.MsgInfo
import com.ai.inty.beans.SendMsgReq
import com.ai.inty.beans.UserProfile
import com.ai.inty.billing.BillingRepository
import com.ai.inty.billing.BillingRepository.plansFlow
import com.ai.inty.billing.BillingRepository.vipStatusFlow
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
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

// 聊天对话 app + backend 交互
// app 启动
// app 请求聊天记录（/agents/{agent_id}/messages
// backednf 创建对话（如果是首次对话）
// backend 返回对话 ID
// app 请求聊天回复（/agents/{agent_id}/chat/completions
class ChatViewModel : BaseActivityViewModel() {

    private val _agentInfo = MutableStateFlow<AgentInfo?>(null)
    val agentInfo = _agentInfo.asStateFlow()

    val msgs = mutableStateListOf<MsgInfo>()
    val conversations = mutableStateListOf<ConversationItem>()

    val inputData = MutableStateFlow<String>("")
    val inputSelection = MutableStateFlow<Int>(0)

    // 用于标识当前是否在等待AI回复
    private val _isWaitingForReply = MutableStateFlow<Boolean>(false)
    val isWaitingForReply = _isWaitingForReply.asStateFlow()

    private val _userProfile = MutableStateFlow<UserProfile>(UserProfile())
    val userProfile = _userProfile.asStateFlow()

    // 防止重复请求的机制
    private var lastQueryAgentId: String? = null
    private var isQuerying = false

    // 延迟获取依赖，避免在构造函数中立即获取导致空指针异常
    private val chatApi by lazy {
        TheRouter.get(IChatApi::class.java)
            ?: throw IllegalStateException("IChatApi not found in TheRouter")
    }

    init {
        EasyLog.log("ChatViewModel = ${hashCode()}")
    }


    fun setAgentInfo(agentInfo: AgentInfo?) {
        EasyLog.log("agent = $agentInfo")
        if (_agentInfo.value?.id == agentInfo?.id) {
            // 如果ID相同，只更新agent信息，不重新查询消息
            _agentInfo.value = agentInfo
            EasyLog.log("Agent ID is the same, skipping queryMsgs")
            return
        }
        _agentInfo.value = agentInfo
        queryMsgs()
    }

    fun updateAgentFollowState(agentId: String, isFollowed: Boolean) {
        EasyLog.log("ChatViewModel updateAgentFollowState - agentId: $agentId, isFollowed: $isFollowed")
        _agentInfo.value?.let { currentAgent ->
            if (currentAgent.id == agentId) {
                val updatedAgent = currentAgent.copy(isFollowed = isFollowed)
                _agentInfo.value = updatedAgent
                EasyLog.log("Updated agent follow state - ${updatedAgent.name} isFollowed: ${updatedAgent.isFollowed}")
            } else {
                EasyLog.log("Agent ID mismatch - current: ${currentAgent.id}, target: $agentId")
            }
        } ?: EasyLog.log("No current agent info available")
    }

    fun queryMsgs() {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                agentInfo.value?.let { agent ->
                    // 防止重复请求
                    if (isQuerying && lastQueryAgentId == agent.id) {
                        EasyLog.log("queryMsgs: Skipping duplicate request for agent ${agent.id}")
                        return@launch
                    }
                    
                    isQuerying = true
                    lastQueryAgentId = agent.id
                    
                    val result = chatApi.getMsgs(agent.id, 100, 0)
                    EasyLog.log("queryMsgs ($agent) = $result")
                    
                    when (result) {
                        is HttpResult.Success -> {
                            msgs.clear()
                            msgs.addAll(result.data.messages)
                            
                            // If no messages exist and agent has an opening message, show it
                            if (result.data.messages.isEmpty() && agent.opening.isNotEmpty()) {
                                withContext(Dispatchers.Main) {
                                    msgs.add(0, MsgInfo(content = agent.opening, role = "assistant"))
                                    EasyLog.log("Added opening message: ${agent.opening}")
                                }
                            }
                        }

                        is HttpResult.Failure -> {
                            showNetworkAwareError(result.message)
                        }
                    }
                    
                    isQuerying = false
                }
            } catch (e: Exception) {
                EasyLog.log("queryMsgs exception: ${e.message}", priority = EasyLog.ERROR)
                handleNetworkException(e)
                isQuerying = false
            }
        }
    }

    val showLimitDialog = MutableStateFlow(false)
    fun sendMsg() {
        launchWithNetCheck {
            val inputMsg = inputData.value
            inputData.value = ""
            EasyLog.log("send msg $inputMsg")

            val msgInfo = MsgInfo(content = inputMsg, role = "user")

            // 添加临时的加载消息
            val loadingMsg = MsgInfo(
                content = "loading_animation", // 特殊标识符
                role = "assistant"
            )

            withContext(Dispatchers.Main) {
                EasyLog.log("msgs count = ${msgs.size}")
                msgs.add(0, msgInfo) // 添加用户消息
                msgs.add(0, loadingMsg) // 添加加载动画消息
                _isWaitingForReply.value = true
                EasyLog.log("msgs count = ${msgs.size}")
            }

            val req = SendMsgReq(listOf(msgInfo))

            agentInfo.value?.let { agent ->
                // 标记为用户主动发起的对话
                IntySetting.setUserInitiatedConversation(agent.id)

                val result = chatApi.sendMsg(agent.id, req)

                EasyLog.log("sendMsg($agent, $req) -> $result")

                withContext(Dispatchers.Main) {
                    // 移除加载消息
                    val loadingIndex =
                        msgs.indexOfFirst { it.content == "loading_animation" && it.role == "assistant" }
                    if (loadingIndex >= 0) {
                        msgs.removeAt(loadingIndex)
                    }
                    _isWaitingForReply.value = false
                }

                when (result) {
                    is HttpResult.Success -> {
                        //有免费次数限制，需要vip订阅
                        if (result.data.code == 10001001) {
                            showLimitDialog.emit(true)
                        }
                        withContext(Dispatchers.Main) {
                            for (choice in result.data.data?.choices ?: emptyList()) {
                                msgs.add(0, choice.message)
                            }
                        }
                        IntySetting.setConversationReaded(
                            agent.id,
                            result.data.data?.choices?.lastOrNull()?.message?.content ?: ""
                        )

                    }

                    is HttpResult.Failure -> {
                        showNetworkAwareError(result.message)
                    }
                }
            }
        }
    }

    //关闭limit次数 拦截消息的弹窗
    fun dismissDialog() = viewModelScope.launch {
        showLimitDialog.emit(false)
    }

    fun sendKeepTalkingMessage() {
        launchWithNetCheck {
            val keepTalkingMsg = "continue"
            EasyLog.log("send keep talking msg")

            val msgInfo = MsgInfo(content = keepTalkingMsg, role = "user")

            // 添加临时的加载消息 (keep talking不显示用户消息，只显示加载动画)
            val loadingMsg = MsgInfo(
                content = "loading_animation", // 特殊标识符
                role = "assistant"
            )

            withContext(Dispatchers.Main) {
                msgs.add(0, msgInfo) // 添加用户continue消息(会被过滤不显示)
                msgs.add(0, loadingMsg) // 添加加载动画消息
                _isWaitingForReply.value = true
            }

            val req = SendMsgReq(listOf(msgInfo))

            agentInfo.value?.let { agent ->
                // 标记为用户主动发起的对话
                IntySetting.setUserInitiatedConversation(agent.id)

                val result = chatApi.sendMsg(agent.id, req)

                EasyLog.log("sendKeepTalkingMessage($agent, $req) -> $result")

                withContext(Dispatchers.Main) {
                    // 移除加载消息
                    val loadingIndex =
                        msgs.indexOfFirst { it.content == "loading_animation" && it.role == "assistant" }
                    if (loadingIndex >= 0) {
                        msgs.removeAt(loadingIndex)
                    }
                    _isWaitingForReply.value = false
                }

                when (result) {
                    is HttpResult.Success -> {
                        //有免费次数限制，需要vip订阅
                        if (result.data.code == 10001001) {
                            showLimitDialog.emit(true)
                        }
                        withContext(Dispatchers.Main) {
                            for (choice in result.data.data?.choices ?: emptyList()) {
                                msgs.add(0, choice.message)
                            }
                        }
                        IntySetting.setConversationReaded(
                            agent.id,
                            result.data.data?.choices?.lastOrNull()?.message?.content ?: ""
                        )
                    }

                    is HttpResult.Failure -> {
                        showNetworkAwareError(result.message)
                    }
                }
            }
        }
    }

    //获取聊天消息设置
    fun getChatSetting() = launchWithNetCheck {
        val agentId = agentInfo.value?.id ?: return@launchWithNetCheck
        //有agent信息，才请求
        val result = chatApi.getChatSettings(agentId)
        when (result) {
            is HttpResult.Failure -> showNetworkAwareError(result.message)
            is HttpResult.Success -> {
                val isPremiumMode = result.data.data?.premium_mode == true
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
                showNetworkAwareError(
                    result.data.message
                        ?: AppEnv.context.getString(R.string.custom_reply_successful)
                )
            }
        }
    }

    fun getConversations() {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val result = chatApi.getConversations(0, 100)
                EasyLog.log("getConversations = $result")
                conversations.clear()
                when (result) {
                    is HttpResult.Success -> {
                        // 只显示用户主动发起的对话
                        val userInitiatedConversations = result.data.filter { conversation ->
                            IntySetting.isUserInitiatedConversation(conversation.agentId)
                        }
                        conversations.addAll(userInitiatedConversations)
                        EasyLog.log("Filtered conversations: ${userInitiatedConversations.size} out of ${result.data.size}")
                    }

                    is HttpResult.Failure -> {
                        showNetworkAwareError(result.message)
                    }
                }
            } catch (e: Exception) {
                EasyLog.log("getConversations exception: ${e.message}", priority = EasyLog.ERROR)
                handleNetworkException(e)
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

    //标记会话消息 已读
    fun setConversationReaded(conversationItem: ConversationItem) {
        IntySetting.setConversationReaded(conversationItem.agentId, conversationItem.lastMessage)

        val index = conversations.indexOfFirst {
            (it.id == conversationItem.id) && (it.agentId == conversationItem.agentId)
        }
        if (index >= 0) {
            conversations[index] = conversationItem.copy(isNew = false)
        }
    }

    // 新增：清理所有数据的方法
    fun clearAllData() {
        msgs.clear()
        conversations.clear()
        _agentInfo.value = null
        _userProfile.value = UserProfile()
        inputData.value = ""
        inputSelection.value = 0
        _isWaitingForReply.value = false
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

        val currentPlans = plansFlow.value

        if (currentPlans.isNotEmpty()) {
            val selectedPlan = currentPlans[0]
            EasyLog.log("purchaseFirstVip 准备购买订阅计划: ${selectedPlan.name} (${selectedPlan.googleProductId}) - ${selectedPlan.price}")

            // 检查用户是否已经订阅
            if (vipStatusFlow.value.isSubscribed) {
                EasyLog.log("purchaseFirstVip 用户已经是订阅用户，无需重复购买", EasyLog.WARN)
                showNetworkAwareError("User Already Subscribed !")
                return
            }

            // 启动购买流程
            BillingRepository.launchBillingFlow(activity, selectedPlan.googleProductId)
        } else {
            EasyLog.log("purchaseFirstVip 无可用会员订阅计划plan", EasyLog.WARN)
            showNetworkAwareError("Chat Purchase No Vip Plan !")
        }
    }
}
