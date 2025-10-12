package com.ai.inty.netapi.services

import com.ai.inty.beans.MsgInfo
import com.ai.inty.beans.SendMsgResponse
import com.ai.inty.beans.Usage
import com.ai.inty.netapi.ApiResult
import com.ai.inty.netapi.IntyNetworkManager
import com.inty.api.core.JsonValue
import com.inty.api.models.api.v1.chats.ChatCreateCompletionParams
import com.inty.api.models.api.v1.report.ApiResponseDict

/** 聊天服务 封装所有聊天相关的API调用 替换原有的 IChatApi */
object ChatService {

    /** 发送聊天消息 替换: IChatApi.sendMessage() */
    suspend fun sendMessage(
        agentId: String,
        messages: List<MsgInfo>,
        model: String = "chatbot",
        stream: Boolean = false,
    ): ApiResult<SendMsgResponse> {
        return IntyNetworkManager.executeRequest("Send Message") {
            // 将 MsgInfo 转换为 inty_sdk 的 Message 格式
            val sdkMessages = messages.map { msgInfo ->
                ChatCreateCompletionParams.Message.builder()
                    .content(msgInfo.content)
                    .role(msgInfo.role)
                    .build()
            }

            val response: ApiResponseDict = IntyNetworkManager.getClient()
                .api()
                .v1()
                .chats()
                .createCompletion(
                    agentId = agentId,
                    params = ChatCreateCompletionParams.builder()
                        .agentId(agentId)
                        .messages(sdkMessages)
                        .model(model)
                        .stream(stream)
                        .build()
                )

            // 将 ApiResponseDict 转换为 SendMsgResponse
            convertApiResponseToSendMsgResponse(response)
        }
    }

    /** 获取聊天历史 替换: IChatApi.getChatHistory() */
    suspend fun getChatHistory(
        conversationId: String,
        page: Int = 1,
        pageSize: Int = 20,
    ): ApiResult<List<MsgInfo>> {
        return IntyNetworkManager.executeRequest("Get Chat History") {
            val response =
                IntyNetworkManager.getClient()
                    .api()
                    .v1()
                    .chats()
                    .agents()
                    .getMessages(
                        com.inty.api.models.api.v1.chats.agents.AgentGetMessagesParams.builder()
                            .agentId("temp_agent_id") // 这里需要根据实际情况处理
                            .build()
                    )

            // 这里需要根据实际的IntySDK返回结构进行转换
            emptyList<MsgInfo>()
        }
    }

    /** 创建新对话 替换: IChatApi.createConversation() */
    suspend fun createConversation(agentId: String): ApiResult<String> {
        return IntyNetworkManager.executeRequest("Create Conversation") {
            val chat =
                IntyNetworkManager.getClient()
                    .api()
                    .v1()
                    .chats()
                    .create(
                        com.inty.api.models.api.v1.chats.ChatCreateParams.builder()
                            .agentId(agentId)
                            .build()
                    )

            chat.id() ?: throw IllegalStateException("Conversation ID is null")
        }
    }

    /** 删除对话 替换: IChatApi.deleteConversation() */
    suspend fun deleteConversation(conversationId: String): ApiResult<Unit> {
        return IntyNetworkManager.executeRequest("Delete Conversation") {
            IntyNetworkManager.getClient().api().v1().chats().delete(conversationId)
        }
    }

    /** 获取对话列表 替换: IChatApi.getConversations() */
    suspend fun getConversations(
        page: Int = 1,
        pageSize: Int = 20,
    ): ApiResult<List<ConversationInfo>> {
        return IntyNetworkManager.executeRequest("Get Conversations") {
            val response =
                IntyNetworkManager.getClient()
                    .api()
                    .v1()
                    .chats()
                    .list(
                        com.inty.api.models.api.v1.chats.ChatListParams.builder()
                            .limit(pageSize.toLong())
                            .skip(((page - 1) * pageSize).toLong())
                            .build()
                    )

            // 这里需要根据实际的IntySDK返回结构进行转换
            emptyList<ConversationInfo>()
        }
    }

    /** 对话信息数据类 */
    data class ConversationInfo(
        val id: String,
        val agentId: String,
        val agentName: String,
        val lastMessage: String?,
        val lastMessageTime: Long,
        val messageCount: Int,
    )

    /** 将 ApiResponseDict 转换为 SendMsgResponse */
    private fun convertApiResponseToSendMsgResponse(apiResponse: ApiResponseDict): SendMsgResponse {
        // 从 ApiResponseDict 中提取数据并转换为 SendMsgResponse 格式
        val code = apiResponse.code()?.toInt() ?: 200
        val message = apiResponse.message() ?: "Success"
        val data = apiResponse.data()
        
        // 从 data 的 additionalProperties 中提取实际的响应数据
        val responseData: Map<String, Any> = data?._additionalProperties() ?: emptyMap()
        
        // 提取 choices 数据
        val choices: List<com.ai.inty.beans.Choice> = responseData["choices"]?.let { _ ->
            // 这里需要根据实际的 choices 结构进行解析
            // 暂时返回空列表，实际使用时需要根据 ApiResponseDict.Data 的结构进行解析
            emptyList<com.ai.inty.beans.Choice>()
        } ?: emptyList<com.ai.inty.beans.Choice>()
        
        return SendMsgResponse(
            code = code,
            message = message,
            data = SendMsgResponse.SentMsgRspData(
                choices = choices,
                created = (responseData["created"] as? Number)?.toInt() ?: System.currentTimeMillis().toInt(),
                id = responseData["id"] as? String ?: "",
                model = responseData["model"] as? String ?: "chatbot",
                objectX = responseData["object"] as? String ?: "chat.completion",
                usage = Usage(
                    promptTokens = ((responseData["usage"] as? Map<String, Any>)?.get("prompt_tokens") as? Number)?.toInt() ?: 0,
                    completionTokens = ((responseData["usage"] as? Map<String, Any>)?.get("completion_tokens") as? Number)?.toInt() ?: 0,
                    totalTokens = ((responseData["usage"] as? Map<String, Any>)?.get("total_tokens") as? Number)?.toInt() ?: 0
                )
            )
        )
    }
}
