package com.ai.inty.viewmodels

import androidx.compose.runtime.mutableStateListOf
import androidx.lifecycle.viewModelScope
import com.ai.inty.base.BaseActivityViewModel
import com.ai.inty.beans.AgentInfo
import com.ai.inty.beans.ConversationItem
import com.ai.inty.beans.MsgInfo
import com.ai.inty.beans.SendMsgReq
import com.ai.inty.beans.UserProfile
import com.ai.inty.net.IChatApi
import com.ai.inty.utils.UserProfileManager
import com.architecture.httplib.core.HttpResult
import com.inty.utils.log.EasyLog
import com.inty.utils.storage.IntySetting
import com.therouter.TheRouter
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class ChatViewModel : BaseActivityViewModel() {

    private val _agentInfo = MutableStateFlow<AgentInfo?>(null)
    val agentInfo = _agentInfo.asStateFlow()

    val msgs = mutableStateListOf<MsgInfo>()
    val conversions = mutableStateListOf<ConversationItem>()

    val inputData = MutableStateFlow<String>("")
    val inputSelection = MutableStateFlow<Int>(0)

    // 用于标识当前是否在等待AI回复
    private val _isWaitingForReply = MutableStateFlow<Boolean>(false)
    val isWaitingForReply = _isWaitingForReply.asStateFlow()

    private val _userProfile = MutableStateFlow<UserProfile>(UserProfile())
    val userProfile = _userProfile.asStateFlow()


    // 延迟获取依赖，避免在构造函数中立即获取导致空指针异常
    val chatApi by lazy {
        TheRouter.get(IChatApi::class.java)
            ?: throw IllegalStateException("IChatApi not found in TheRouter")
    }

    init {
        EasyLog.log("ChatViewModel = ${hashCode()}")
    }


    fun setAgentInfo(agentInfo: AgentInfo?) {
        EasyLog.log("agent = $agentInfo")
        if (_agentInfo.value?.id == agentInfo?.id) {
            _agentInfo.value = agentInfo
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
                    val result = chatApi.getMsgs(agent.id, 100, 0)
                    EasyLog.log("queryMsgs ($agent) = $result")
                    when (result) {
                        is HttpResult.Success -> {
                            msgs.clear()
                            msgs.addAll(result.data.messages)
                        }

                        is HttpResult.Failure -> {
                            showNetworkAwareError(result.message)
                        }
                    }
                }
            } catch (e: Exception) {
                EasyLog.log("queryMsgs exception: ${e.message}", priority = EasyLog.ERROR)
                handleNetworkException(e)
            }
        }
    }

    fun sendMsg() {
        launchWithNetCheck {
            val inputMsg = inputData.value
            inputData.value = ""
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
                        withContext(Dispatchers.Main) {
                            for (choice in result.data.choices) {
                                msgs.add(0, choice.message)
                            }
                        }
                        IntySetting.setConversationReaded(
                            agent.id,
                            result.data.choices.last()?.message?.content ?: ""
                        )
                    }

                    is HttpResult.Failure -> {
                        showNetworkAwareError(result.message)
                    }
                }
            }
        }
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
                        withContext(Dispatchers.Main) {
                            for (choice in result.data.choices) {
                                msgs.add(0, choice.message)
                            }
                        }
                        IntySetting.setConversationReaded(
                            agent.id,
                            result.data.choices.last()?.message?.content ?: ""
                        )
                    }

                    is HttpResult.Failure -> {
                        showNetworkAwareError(result.message)
                    }
                }
            }
        }
    }

    fun getConversions() {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val result = chatApi.getConversions(0, 100)
                EasyLog.log("getConversions = $result")
                conversions.clear()
                when (result) {
                    is HttpResult.Success -> {
                        // 只显示用户主动发起的对话
                        val userInitiatedConversations = result.data.filter { conversation ->
                            IntySetting.isUserInitiatedConversation(conversation.agentId)
                        }
                        conversions.addAll(userInitiatedConversations)
                        EasyLog.log("Filtered conversations: ${userInitiatedConversations.size} out of ${result.data.size}")
                    }

                    is HttpResult.Failure -> {
                        showNetworkAwareError(result.message)
                    }
                }
            } catch (e: Exception) {
                EasyLog.log("getConversions exception: ${e.message}", priority = EasyLog.ERROR)
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

    fun setConversionReaded(conversationItem: ConversationItem) {
        IntySetting.setConversationReaded(conversationItem.agentId, conversationItem.lastMessage)

        val index = conversions.indexOfFirst {
            (it.id == conversationItem.id) && (it.agentId == conversationItem.agentId)
        }
        if (index >= 0) {
            conversions[index] = conversationItem.copy(isNew = false)
        }
    }

    // 新增：清理所有数据的方法
    fun clearAllData() {
        msgs.clear()
        conversions.clear()
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
}