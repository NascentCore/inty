package com.inty.imate.chat.data

import com.inty.imate.chat.data.bean.SendMsgReq
import com.inty.imate.chat.data.bean.SendMsgReqMessage
import com.inty.imate.chat.data.datasource.ChatWebSocketRemoteDataSource
import java.util.UUID
import kotlinx.serialization.json.JsonPrimitive

object ChatTextSendRequestFactory {

    fun buildTextSendMsgReq(agentId: String, userText: String): SendMsgReq {
        val trimmed = userText.trimEnd()
        return SendMsgReq(
            messages =
                listOf(
                    SendMsgReqMessage(
                        role = "user",
                        content = JsonPrimitive(trimmed),
                    )
                ),
            timeContext = ChatWebSocketRemoteDataSource.buildUserTimeContextOrNull(),
            targetImateId = agentId,
            messageId = UUID.randomUUID().toString(),
        )
    }
}
