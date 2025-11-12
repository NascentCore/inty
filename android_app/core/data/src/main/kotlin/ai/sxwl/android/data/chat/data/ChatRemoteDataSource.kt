package ai.sxwl.android.data.chat.data

import ai.sxwl.android.data.api.IChatApi
import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.api.model.QueryMsgsResponse
import ai.sxwl.android.data.api.model.SendMsgReq
import ai.sxwl.android.data.api.model.SendMsgResponse
import ai.sxwl.android.utils.LogUtils
import com.architecture.httplib.core.HttpResult

/** 聊天远程数据源 负责处理与服务器的聊天相关API调用 遵循Clean Architecture的数据层模式 */
class ChatRemoteDataSource {

    private val chatApi: IChatApi by lazy { NetServiceMgr.getChatApi() }

    suspend fun getMessages(
        agentId: String,
        pageSize: Int,
        offset: Int
    ): HttpResult<QueryMsgsResponse> {
        return try {
            LogUtils.i(
                "ChatRemoteDataSource.getMessages: agentId=$agentId, pageSize=$pageSize, offset=$offset"
            )
            chatApi.getMsgs(agentId, pageSize, offset)
        } catch (e: Exception) {
            LogUtils.e("ChatRemoteDataSource.getMessages exception: ${e.message}")
            HttpResult.Failure(e.message ?: "Network error", -1)
        }
    }

    suspend fun sendMessage(agentId: String, messages: List<MsgInfo>): HttpResult<SendMsgResponse> {
        return try {
            LogUtils.i(
                "ChatRemoteDataSource.sendMessage: agentId=$agentId, messagesCount=${messages.size}"
            )
            val request = SendMsgReq(messages)
            chatApi.sendMsg(agentId, request)
        } catch (e: Exception) {
            LogUtils.e("ChatRemoteDataSource.sendMessage exception: ${e.message}")
            HttpResult.Failure(e.message ?: "Network error", -1)
        }
    }

    /**
     * 消息生图的接口请求
     */
    suspend fun messageGenerateImage(
        agentId: String,
        messageId: String,
    ): HttpResult<ai.sxwl.android.data.http.services.ChatService.ChatImageGenerationResult> {
        return try {
            LogUtils.i(
                "ChatRemoteDataSource.generateImage: agentId=$agentId, messageId=$messageId"
            )
            val result =
                ai.sxwl.android.data.http.services.ChatService.messageGenerateImage(
                    agentId,
                    messageId
                )
            when (result) {
                is ai.sxwl.android.data.http.ApiResult.Success -> {
                    HttpResult.Success(result.data)
                }

                is ai.sxwl.android.data.http.ApiResult.Error -> {
                    // 检查是否是业务错误（限制异常）
                    val exception = result.exception
                    if (exception is ai.sxwl.android.data.http.services.ChatImageGenerationLimitException) {
                        // 返回业务错误，包含错误码信息
                        HttpResult.Failure(
                            exception.error.message ?: "Image generation limit reached",
                            exception.error.code.toInt()
                        )
                    } else {
                        HttpResult.Failure(result.message ?: "Unknown error", result.code)
                    }
                }
            }
        } catch (e: ai.sxwl.android.data.http.services.ChatImageGenerationLimitException) {
            // 捕获业务错误，返回包含错误码的失败结果
            LogUtils.e("ChatRemoteDataSource.generateImage limit exception: ${e.error.message}")
            HttpResult.Failure(
                e.error.message ?: "Image generation limit reached",
                e.error.code.toInt()
            )
        } catch (e: Exception) {
            LogUtils.e("ChatRemoteDataSource.generateImage exception: ${e.message}")
            HttpResult.Failure(e.message ?: "Network error", -1)
        }
    }
}
