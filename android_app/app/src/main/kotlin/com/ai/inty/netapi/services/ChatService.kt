package com.ai.inty.netapi.services

import com.ai.inty.beans.MsgInfo
import com.ai.inty.netapi.ApiResult
import com.ai.inty.netapi.IntyNetworkManager

/** 聊天服务 封装所有聊天相关的API调用 替换原有的 IChatApi */
object ChatService {

  /** 发送聊天消息 替换: IChatApi.sendMessage() */
  suspend fun sendMessage(
      agentId: String,
      message: String,
      conversationId: String? = null,
  ): ApiResult<MsgInfo> {
    return IntyNetworkManager.executeRequest("Send Message") {
      val response =
          IntyNetworkManager.getClient()
              .api()
              .v1()
              .chats()
              .agents()
              .generateMessageVoice(
                  com.inty.api.models.api.v1.chats.agents.AgentGenerateMessageVoiceParams.builder()
                      .agentId(agentId)
                      .messageId("temp_message_id") // 这里需要根据实际情况处理
                      .language("en") // 这里需要根据实际情况处理
                      .build()
              )

      // 当前 IntySDK 的 Chat 数据结构与业务层不匹配
      // 需要根据实际返回结构进行数据转换
      throw Exception("Chat message conversion not implemented, need data mapping")
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
}
