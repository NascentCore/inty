package com.ai.inty.netapi.services

import com.ai.inty.beans.MsgInfo
import com.ai.inty.beans.SendMsgResponse
import com.ai.inty.beans.Usage
import com.ai.inty.netapi.ApiResult
import com.ai.inty.netapi.IntyNetworkManager
import com.inty.utils.log.EasyLog
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
        EasyLog.log("=== CHAT DEBUG: ChatService.sendMessage called")
        EasyLog.log("=== CHAT DEBUG: agentId: $agentId")
        EasyLog.log("=== CHAT DEBUG: messages count: ${messages.size}")
        EasyLog.log("=== CHAT DEBUG: model: $model")
        EasyLog.log("=== CHAT DEBUG: stream: $stream")
        
        return IntyNetworkManager.executeRequest("Send Message") {
            // 将 MsgInfo 转换为 inty_sdk 的 Message 格式
            val sdkMessages = messages.map { msgInfo ->
                EasyLog.log("=== CHAT DEBUG: Converting message - Role: ${msgInfo.role}, Content: '${msgInfo.content}'")
                ChatCreateCompletionParams.Message.builder()
                    .content(msgInfo.content)
                    .role(msgInfo.role)
                    .build()
            }
            EasyLog.log("=== CHAT DEBUG: Converted ${sdkMessages.size} messages to SDK format")

            val params = ChatCreateCompletionParams.builder()
                .agentId(agentId)
                .messages(sdkMessages)
                .model(model)
                .stream(stream)
                .build()
            EasyLog.log("=== CHAT DEBUG: Created ChatCreateCompletionParams: $params")

            EasyLog.log("=== CHAT DEBUG: Making API call to createCompletion")
            try {
                val response: ApiResponseDict = IntyNetworkManager.getClient()
                    .api()
                    .v1()
                    .chats()
                    .createCompletion(
                        agentId = agentId,
                        params = params
                    )
                EasyLog.log("=== CHAT DEBUG: Received API response: $response")
                EasyLog.log("=== CHAT DEBUG: API call completed successfully")
                // 将 ApiResponseDict 转换为 SendMsgResponse
                val convertedResponse = convertApiResponseToSendMsgResponse(response)
                EasyLog.log("=== CHAT DEBUG: Converted response: $convertedResponse")
                convertedResponse
            } catch (e: Exception) {
                EasyLog.log("=== CHAT DEBUG: API call failed with exception: ${e.message}", priority = EasyLog.ERROR)
                EasyLog.log("=== CHAT DEBUG: Exception type: ${e.javaClass.simpleName}", priority = EasyLog.ERROR)
                e.printStackTrace()
                throw e
            }
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
        EasyLog.log("=== CHAT DEBUG: Converting ApiResponseDict to SendMsgResponse")
        
        // 从 ApiResponseDict 中提取数据并转换为 SendMsgResponse 格式
        val code = apiResponse.code()?.toInt() ?: 200
        val message = apiResponse.message() ?: "Success"
        val data = apiResponse.data()
        
        EasyLog.log("=== CHAT DEBUG: Extracted code: $code, message: $message")
        EasyLog.log("=== CHAT DEBUG: Data object: $data")
        
        // 从 data 的 additionalProperties 中提取实际的响应数据
        val responseData: Map<String, Any> = data?._additionalProperties() ?: emptyMap()
        EasyLog.log("=== CHAT DEBUG: Response data map: $responseData")
        
        // 提取 choices 数据
        val choices: List<com.ai.inty.beans.Choice> = responseData["choices"]?.let { choicesData ->
            EasyLog.log("=== CHAT DEBUG: Found choices data: $choicesData")
            EasyLog.log("=== CHAT DEBUG: Choices data type: ${choicesData.javaClass.simpleName}")
            EasyLog.log("=== CHAT DEBUG: Choices data class: ${choicesData.javaClass.name}")
            
            // 解析 choices 数据 - 使用通用方法处理不同类型的集合
            val parsedChoices = mutableListOf<com.ai.inty.beans.Choice>()
            
            try {
                // 尝试将 choicesData 转换为可迭代的集合
                val iterable = when (choicesData) {
                    is List<*> -> {
                        EasyLog.log("=== CHAT DEBUG: Choices data is List, size: ${choicesData.size}")
                        choicesData
                    }
                    is Array<*> -> {
                        EasyLog.log("=== CHAT DEBUG: Choices data is Array, size: ${choicesData.size}")
                        choicesData.toList()
                    }
                    else -> {
                        EasyLog.log("=== CHAT DEBUG: Choices data is other type, trying reflection")
                        // 尝试使用反射获取 size 和 get 方法
                        val sizeMethod = choicesData.javaClass.getMethod("size")
                        val getMethod = choicesData.javaClass.getMethod("get", Int::class.java)
                        val size = sizeMethod.invoke(choicesData) as Int
                        EasyLog.log("=== CHAT DEBUG: Reflection found size: $size")
                        (0 until size).map { getMethod.invoke(choicesData, it) }
                    }
                }
                
                EasyLog.log("=== CHAT DEBUG: Iterable size: ${iterable.size}")
                
                iterable.forEachIndexed { index, choiceItem ->
                    try {
                        if (choiceItem != null) {
                            // 尝试获取 choice 对象的属性
                            val choiceMap = when (choiceItem) {
                                is Map<*, *> -> choiceItem as Map<String, Any>
                                else -> {
                                    // 使用反射获取属性
                                    val itemClass = choiceItem.javaClass
                                    val messageField = itemClass.getDeclaredField("message")
                                    val indexField = itemClass.getDeclaredField("index")
                                    val finishReasonField = itemClass.getDeclaredField("finish_reason")
                                    
                                    messageField.isAccessible = true
                                    indexField.isAccessible = true
                                    finishReasonField.isAccessible = true
                                    
                                    mapOf(
                                        "message" to messageField.get(choiceItem),
                                        "index" to indexField.get(choiceItem),
                                        "finish_reason" to finishReasonField.get(choiceItem)
                                    )
                                }
                            }
                            
                            val messageData = choiceMap["message"] as? Map<String, Any>
                            
                            if (messageData != null) {
                                val message = com.ai.inty.beans.MsgInfo(
                                    content = messageData["content"] as? String ?: "",
                                    role = messageData["role"] as? String ?: "assistant",
                                    localMsgId = messageData["id"] as? String ?: "",
                                    timestamp = messageData["timestamp"] as? String ?: ""
                                )
                                
                                val choice = com.ai.inty.beans.Choice(
                                    index = (choiceMap["index"] as? Number)?.toInt() ?: index,
                                    message = message,
                                    finishReason = choiceMap["finish_reason"] as? String ?: "stop"
                                )
                                parsedChoices.add(choice)
                                EasyLog.log("=== CHAT DEBUG: Parsed choice $index: role=${message.role}, content='${message.content}'")
                            }
                        }
                    } catch (e: Exception) {
                        EasyLog.log("=== CHAT DEBUG: Error parsing choice $index: ${e.message}", priority = EasyLog.ERROR)
                    }
                }
                
                EasyLog.log("=== CHAT DEBUG: Successfully parsed ${parsedChoices.size} choices")
                parsedChoices
            } catch (e: Exception) {
                EasyLog.log("=== CHAT DEBUG: Error parsing choices data: ${e.message}", priority = EasyLog.ERROR)
                EasyLog.log("=== CHAT DEBUG: Choices data type: ${choicesData.javaClass.simpleName}", priority = EasyLog.ERROR)
                emptyList<com.ai.inty.beans.Choice>()
            }
        } ?: run {
            EasyLog.log("=== CHAT DEBUG: No choices data found in response")
            emptyList<com.ai.inty.beans.Choice>()
        }
        
        EasyLog.log("=== CHAT DEBUG: Final choices count: ${choices.size}")
        
        val finalResponse = SendMsgResponse(
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
        
        EasyLog.log("=== CHAT DEBUG: Final converted response: $finalResponse")
        return finalResponse
    }
}
