package ai.sxwl.android.data.chat.remote

import ai.sxwl.android.data.api.IChatApi
import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.api.model.QueryMsgsResponse
import ai.sxwl.android.data.api.model.SendMsgReq
import ai.sxwl.android.data.api.model.SendMsgResponse
import ai.sxwl.android.utils.LogUtils
import com.architecture.httplib.core.HttpResult

/** 聊天远程数据源 负责处理与服务器的聊天相关API调用 */
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
}
