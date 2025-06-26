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

class ChatViewModel: BaseActivityViewModel() {

    private val _agentInfo = MutableStateFlow<AgentInfo?>(null)
    val agentInfo = _agentInfo.asStateFlow()

    val msgs = mutableStateListOf<MsgInfo>()
    val conversions = mutableStateListOf<ConversationItem>()

    val inputData = MutableStateFlow<String>("")

    private val _userProfile = MutableStateFlow<UserProfile>(UserProfile())
    val userProfile = _userProfile.asStateFlow()


    val chatApi = TheRouter.get(IChatApi::class.java)!!

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
        msgs.clear()

        queryMsgs()
    }
    
    fun updateAgentFollowState(agentId: String, isFollowed: Boolean) {
        _agentInfo.value?.let { currentAgent ->
            if (currentAgent.id == agentId) {
                _agentInfo.value = currentAgent.copy(isFollowed = isFollowed)
            }
        }
    }

    fun queryMsgs() {
        viewModelScope.launch(Dispatchers.IO) {
//            for (i in 0 .. 100) {
//                msgs.add(
//                    0,
//                    MsgInfo(
//                        content = "msgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsg $i",
//                        senderType = if (i % 2 == 0) "AI" else "USER"
//                    )
//                )
//            }

            agentInfo.value?.let { agent ->
                val result = chatApi.getMsgs(agent.id, 100, 0)
                EasyLog.log("get msgs($agent) = $result")

                when (result) {
                    is HttpResult.Success -> {
                        msgs.addAll(result.data.messages)
                    }
                    is HttpResult.Failure -> {
                        showSnackbar(result.message)
                    }
                }

            }
        }
    }

    fun sendMsg() {
        viewModelScope.launch(Dispatchers.IO) {
            val inputMsg = inputData.value
            inputData.value = ""
            EasyLog.log("send msg ${inputMsg}")

            val msgInfo = MsgInfo(
                content = inputMsg,
                role = "user"
            )

            withContext(Dispatchers.Main) {
                EasyLog.log("msgs count = ${msgs.size}")
                msgs.add(
                    0,
                    msgInfo
                )
                EasyLog.log("msgs count = ${msgs.size}")
            }

            val req = SendMsgReq(listOf(msgInfo))

            agentInfo.value?.let { agent ->
                // 标记为用户主动发起的对话
                IntySetting.setUserInitiatedConversation(agent.id)
                
                val result = chatApi.sendMsg(agent.id, req)

                EasyLog.log("sendMsg($agent, $req) -> $result")

                when (result) {
                    is HttpResult.Success -> {
                        for (choice in result.data.choices) {
                            msgs.add(0, choice.message)
                        }
                        IntySetting.setConversationReaded(agent.id, result.data.choices.last()?.message?.content ?: "")
                    }
                    is HttpResult.Failure -> {
                        showSnackbar(result.message)
                    }
                }
            }


        }
    }

    fun sendKeepTalkingMessage() {
        viewModelScope.launch(Dispatchers.IO) {
            val keepTalkingMsg = "keep talking"
            EasyLog.log("send keep talking msg")

            val msgInfo = MsgInfo(
                content = keepTalkingMsg,
                role = "user"
            )

            withContext(Dispatchers.Main) {
                msgs.add(0, msgInfo)
            }

            val req = SendMsgReq(listOf(msgInfo))

            agentInfo.value?.let { agent ->
                // 标记为用户主动发起的对话
                IntySetting.setUserInitiatedConversation(agent.id)
                
                val result = chatApi.sendMsg(agent.id, req)

                EasyLog.log("sendKeepTalkingMessage($agent, $req) -> $result")

                when (result) {
                    is HttpResult.Success -> {
                        for (choice in result.data.choices) {
                            msgs.add(0, choice.message)
                        }
                        IntySetting.setConversationReaded(agent.id, result.data.choices.last()?.message?.content ?: "")
                    }
                    is HttpResult.Failure -> {
                        showSnackbar(result.message)
                    }
                }
            }
        }
    }

    fun getConversions() {
        viewModelScope.launch(Dispatchers.IO) {
            val result = chatApi.getConversions(0, 100)
            EasyLog.log("get msgs = $result")
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
                    showSnackbar(result.message)
                }

            }
        }
    }

    fun setAgentID(agentId: String) {
        viewModelScope.launch(Dispatchers.IO) {
            val result = chatApi.getAgentInfo(agentId)
            EasyLog.log("getAgentInfo = $result")
            when (result) {
                is HttpResult.Success -> {
                    setAgentInfo(result.data)

                }
                is HttpResult.Failure -> {
                    showSnackbar(result.message)
                }
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
        inputData.value = ""
        EasyLog.log("ChatViewModel cleared all data")
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