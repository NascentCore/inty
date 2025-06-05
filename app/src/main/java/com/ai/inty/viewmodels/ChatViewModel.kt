package com.ai.inty.viewmodels

import androidx.compose.runtime.mutableStateListOf
import androidx.lifecycle.viewModelScope
import com.ai.inty.base.BaseActivityViewModel
import com.ai.inty.beans.AgentInfo
import com.ai.inty.beans.MsgInfo
import com.inty.utils.log.EasyLog
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class ChatViewModel: BaseActivityViewModel() {

    private val _agentInfo = MutableStateFlow<AgentInfo?>(null)
    val agentInfo = _agentInfo.asStateFlow()

    val msgs = mutableStateListOf<MsgInfo>()

    val inputData = MutableStateFlow<String>("")

    init {

        EasyLog.log("ChatViewModel = ${hashCode()}")
    }


    fun setAgentInfo(agentInfo: AgentInfo?) {
        _agentInfo.value = agentInfo

        queryMsgs()
    }

    fun queryMsgs() {
        viewModelScope.launch(Dispatchers.IO) {
            for (i in 0 .. 100) {
                msgs.add(
                    0,
                    MsgInfo(
                        content = "msgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsgmsg $i",
                        senderType = if (i % 2 == 0) "AI" else "USER"
                    )
                )
            }
        }
    }

    fun sendMsg() {
        viewModelScope.launch(Dispatchers.IO) {
            val inputMsg = inputData.value
            inputData.value = ""
            EasyLog.log("send msg ${inputMsg}")

            delay(100)

            withContext(Dispatchers.Main) {
                EasyLog.log("msgs count = ${msgs.size}")
                msgs.add(
                    0,
                    MsgInfo(
                        content = inputMsg,
                        senderType = "USER"
                    )
                )
                EasyLog.log("msgs count = ${msgs.size}")
            }

        }
    }

}