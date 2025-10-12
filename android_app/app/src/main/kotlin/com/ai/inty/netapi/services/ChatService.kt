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
            val sdkMessages =
                messages.map { msgInfo ->
                    ChatCreateCompletionParams.Message.builder()
                        .content(msgInfo.content)
                        .role(msgInfo.role)
                        .build()
                }

            val params =
                ChatCreateCompletionParams.builder()
                    .agentId(agentId)
                    .messages(sdkMessages)
                    .model(model)
                    .stream(stream)
                    .build()

            val response: ApiResponseDict =
                IntyNetworkManager.getClient()
                    .api()
                    .v1()
                    .chats()
                    .createCompletion(agentId = agentId, params = params)

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

    /** 将 JsonValue 转换为 Any 类型的辅助函数 */
    private fun convertJsonValueToAny(jsonValue: JsonValue): Any? {
        return when (jsonValue) {
            is com.inty.api.core.JsonString -> jsonValue.value
            is com.inty.api.core.JsonNumber -> jsonValue.value
            is com.inty.api.core.JsonBoolean -> jsonValue.value
            is com.inty.api.core.JsonArray -> jsonValue.values.map { convertJsonValueToAny(it) }
            is com.inty.api.core.JsonObject ->
                jsonValue.values.mapValues { (_, objValue) -> convertJsonValueToAny(objValue) }
            is com.inty.api.core.JsonNull -> null
            else -> jsonValue.toString()
        }
    }

    /** 将 ApiResponseDict 转换为 SendMsgResponse */
    private fun convertApiResponseToSendMsgResponse(apiResponse: ApiResponseDict): SendMsgResponse {
        // 从 ApiResponseDict 中提取数据并转换为 SendMsgResponse 格式
        val code = apiResponse.code()?.toInt() ?: 200
        val message = apiResponse.message() ?: "Success"
        val data = apiResponse.data()

        // 从 data 的 additionalProperties 中提取实际的响应数据
        val responseDataJsonValues: Map<String, JsonValue> =
            data?._additionalProperties() ?: emptyMap()

        // 将 JsonValue 转换为实际的值
        val responseData: Map<String, Any> =
            responseDataJsonValues.mapValues { (_, jsonValue) ->
                convertJsonValueToAny(jsonValue)!!
            }

        // 提取 choices 数据
        val choices: List<com.ai.inty.beans.Choice> =
            responseData["choices"]?.let { choicesData ->
                val parsedChoices = mutableListOf<com.ai.inty.beans.Choice>()

                try {
                    // 直接处理 List 类型的数据
                    when (choicesData) {
                        is List<*> -> {
                            choicesData.forEachIndexed { index, choiceItem ->
                                try {
                                    if (choiceItem != null) {
                                        // 尝试将 choiceItem 转换为 Map
                                        val choiceMap =
                                            when (choiceItem) {
                                                is Map<*, *> -> choiceItem as Map<String, Any>
                                                else -> {
                                                    // 使用反射获取属性
                                                    val itemClass = choiceItem.javaClass
                                                    val fields = itemClass.declaredFields
                                                    val choiceMap = mutableMapOf<String, Any>()

                                                    fields.forEach { field ->
                                                        field.isAccessible = true
                                                        val value = field.get(choiceItem)
                                                        choiceMap[field.name] = value ?: ""
                                                    }
                                                    choiceMap
                                                }
                                            }

                                        // 提取 message 数据
                                        val messageData = choiceMap["message"]

                                        if (messageData != null) {
                                            val messageMap =
                                                when (messageData) {
                                                    is Map<*, *> -> messageData as Map<String, Any>
                                                    else -> {
                                                        // 使用反射获取 message 属性
                                                        val messageClass = messageData.javaClass
                                                        val messageFields =
                                                            messageClass.declaredFields
                                                        val messageMap = mutableMapOf<String, Any>()

                                                        messageFields.forEach { field ->
                                                            field.isAccessible = true
                                                            val value = field.get(messageData)
                                                            messageMap[field.name] = value ?: ""
                                                        }
                                                        messageMap
                                                    }
                                                }

                                            val messageId = messageMap["id"] as? String ?: ""
                                            val messageContent =
                                                messageMap["content"] as? String ?: ""
                                            val messageRole =
                                                messageMap["role"] as? String ?: "assistant"
                                            val messageTimestamp =
                                                messageMap["timestamp"] as? String ?: ""

                                            val message =
                                                com.ai.inty.beans.MsgInfo(
                                                    id = messageId,
                                                    content = messageContent,
                                                    role = messageRole,
                                                    timestamp = messageTimestamp,
                                                )

                                            val choiceIndex =
                                                (choiceMap["index"] as? Number)?.toInt() ?: index
                                            val finishReason =
                                                choiceMap["finish_reason"] as? String ?: "stop"

                                            val choice =
                                                com.ai.inty.beans.Choice(
                                                    index = choiceIndex,
                                                    message = message,
                                                    finishReason = finishReason,
                                                )
                                            parsedChoices.add(choice)
                                        }
                                    }
                                } catch (e: Exception) {
                                    // 忽略解析错误的 choice
                                }
                            }
                        }
                    }

                    parsedChoices
                } catch (e: Exception) {
                    emptyList<com.ai.inty.beans.Choice>()
                }
            } ?: emptyList<com.ai.inty.beans.Choice>()

        // Extract usage data
        val usageData = responseData["usage"] as? Map<String, Any>

        val usage =
            Usage(
                promptTokens = (usageData?.get("prompt_tokens") as? Number)?.toInt() ?: 0,
                completionTokens = (usageData?.get("completion_tokens") as? Number)?.toInt() ?: 0,
                totalTokens = (usageData?.get("total_tokens") as? Number)?.toInt() ?: 0,
            )

        return SendMsgResponse(
            code = code,
            message = message,
            data =
                SendMsgResponse.SentMsgRspData(
                    choices = choices,
                    created =
                        (responseData["created"] as? Number)?.toInt()
                            ?: System.currentTimeMillis().toInt(),
                    id = responseData["id"] as? String ?: "",
                    model = responseData["model"] as? String ?: "chatbot",
                    objectX = responseData["object"] as? String ?: "chat.completion",
                    usage = usage,
                ),
        )
    }
}
