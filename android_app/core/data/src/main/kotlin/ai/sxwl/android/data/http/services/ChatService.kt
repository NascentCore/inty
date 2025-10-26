package ai.sxwl.android.data.http.services

import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.http.ApiResult
import ai.sxwl.android.data.http.IntyNetworkManager

/** 聊天服务封装所有聊天相关的 API 调用替换原有的 IChatApi */
object ChatService {

    /** 发送聊天消息替换：IChatApi。发送消息() */
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
                        com.inty.api.models.api.v1.chats.agents.AgentGenerateMessageVoiceParams
                            .builder()
                            .agentId(agentId)
                            .messageId("temp_message_id") // 这里需要根据实际情况处理
                            .language("en") // 这里需要根据实际情况处理
                            .build()
                    )
// 当前 IntySDK 的聊天数据结构与业务层不匹配
// 需要根据实际结构返回进行数据转换
            throw Exception("Chat message conversion not implemented, need data mapping")
        }
    }

    /** 获取聊天历史替换：IChatApi。获取聊天历史记录() */
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

    /**创建新对话替换：IChatApi。创建对话（）*/
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

    /** 删除对话替换：IChatApi。删除对话() */
    suspend fun deleteConversation(conversationId: String): ApiResult<Unit> {
        return IntyNetworkManager.executeRequest("Delete Conversation") {
            IntyNetworkManager.getClient().api().v1().chats().delete(conversationId)
        }
    }

    /** 获取对话列表替换：IChatApi。获取对话（）*/
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
