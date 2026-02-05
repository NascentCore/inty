package ai.sxwl.android.data.chat.data

import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.api.model.QueryMsgsResponse
import ai.sxwl.android.data.api.model.SendMsgReq
import ai.sxwl.android.data.api.model.SendMsgResponse
import ai.sxwl.android.data.api.model.UserTimeContext
import ai.sxwl.android.data.api.model.VoteMessageReq
import ai.sxwl.android.data.api.model.VoteMessageRsp
import ai.sxwl.android.data.http.IntyNetworkManager
import ai.sxwl.android.data.http.config.DebugBackendEndpointStore
import ai.sxwl.android.data.http.config.NetworkConfig
import ai.sxwl.android.utils.LogUtils
import com.architecture.httplib.core.HttpResult
import com.inty.api.core.RequestOptions
import java.time.Duration
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/** 聊天远程数据源 负责处理与服务器的聊天相关API调用 遵循Clean Architecture的数据层模式 */
class ChatRemoteDataSource {
    suspend fun getMessages(
        agentId: String,
        pageSize: Int,
        offset: Int,
    ): HttpResult<QueryMsgsResponse> {
        return try {
            val result = NetServiceMgr.getChatApi().getMsgs(agentId, pageSize, offset)
            when (result) {
                is HttpResult.Success -> {
                    val messages = result.data.messages ?: emptyList()
                    val messagesCount = messages.size
                    val messagesPreview =
                        messages.take(3).joinToString(separator = " | ") { msg ->
                            "[${msg.role}] ${msg.content.take(50)}"
                        }
                    LogUtils.i(
                        "聊天接口数据",
                        "getMsgs 调用成功: agentId=$agentId, messagesCount=$messagesCount, hasMore=${result.data.hasMore}, preview=$messagesPreview",
                    )
                }
                is HttpResult.Failure -> {
                    LogUtils.e(
                        "聊天接口数据",
                        "getMsgs 调用失败: agentId=$agentId, error=${result.message}, code=${result.code}",
                    )
                }
            }
            result
        } catch (e: Exception) {
            LogUtils.e("聊天接口数据", "getMsgs 调用异常: agentId=$agentId, exception=${e.message}")
            HttpResult.Failure(e.message ?: "Network error", -1)
        }
    }

    suspend fun sendMessage(agentId: String, messages: List<MsgInfo>): HttpResult<SendMsgResponse> {
        return try {
            LogUtils.i(
                "ChatRemoteDataSource.sendMessage: agentId=$agentId, messagesCount=${messages.size}"
            )
            val request = SendMsgReq(messages = messages, timeContext = buildUserTimeContext())
            NetServiceMgr.getChatApi().sendMsg(agentId, request)
        } catch (e: Exception) {
            LogUtils.e("ChatRemoteDataSource.sendMessage exception: ${e.message}")
            HttpResult.Failure(e.message ?: "Network error", -1)
        }
    }

    private fun buildUserTimeContext(): UserTimeContext? {
        if (!shouldReportUserTimeContext()) return null
        val now = ZonedDateTime.now()
        val utcOffsetMinutes = now.offset.totalSeconds / 60
        return UserTimeContext(
            localTime = now.format(DateTimeFormatter.ISO_OFFSET_DATE_TIME),
            timezone = now.zone.id,
            utcOffsetMinutes = utcOffsetMinutes,
        )
    }

    private fun shouldReportUserTimeContext(): Boolean {
        return if (DebugBackendEndpointStore.isRuntimeOverrideSupported()) {
            DebugBackendEndpointStore.getUserTimeContextReportingEnabled()
        } else {
            true
        }
    }

    /** 消息生图的接口请求 */
    suspend fun messageGenerateImage(
        agentId: String,
        messageId: String,
    ): HttpResult<ai.sxwl.android.data.http.services.ChatService.ChatImageGenerationResult> {
        return try {
            LogUtils.i("ChatRemoteDataSource.generateImage: agentId=$agentId, messageId=$messageId")
            val result =
                ai.sxwl.android.data.http.services.ChatService.messageGenerateImage(
                    agentId,
                    messageId,
                )
            when (result) {
                is ai.sxwl.android.data.http.ApiResult.Success -> {
                    HttpResult.Success(result.data)
                }

                is ai.sxwl.android.data.http.ApiResult.Error -> {
                    // 检查是否是业务错误（限制异常）
                    val exception = result.exception
                    if (
                        exception
                            is ai.sxwl.android.data.http.services.ChatImageGenerationLimitException
                    ) {
                        // 返回业务错误，包含错误码信息
                        HttpResult.Failure(
                            exception.error.message ?: "Image generation limit reached",
                            exception.error.code.toInt(),
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
                e.error.code.toInt(),
            )
        } catch (e: Exception) {
            LogUtils.e("ChatRemoteDataSource.generateImage exception: ${e.message}")
            HttpResult.Failure(e.message ?: "Network error", -1)
        }
    }

    /** 消息投票接口请求 */
    suspend fun voteMessage(
        agentId: String,
        messageId: String,
        vote: String, // "like" 或 "dislike"
    ): HttpResult<VoteMessageRsp> {
        return try {
            LogUtils.i(
                "ChatRemoteDataSource.voteMessage: agentId=$agentId, messageId=$messageId, vote=$vote"
            )
            val request = VoteMessageReq(agent_id = agentId, message_id = messageId, vote = vote)
            NetServiceMgr.getChatApi().voteMessage(request)
        } catch (e: Exception) {
            LogUtils.e("ChatRemoteDataSource.voteMessage exception: ${e.message}")
            HttpResult.Failure(e.message ?: "Network error", -1)
        }
    }

    /** Reset聊天 */
    suspend fun clearMessage(agentId: String): Boolean {

        return withContext(Dispatchers.IO) {
            val result =
                runCatching {
                        IntyNetworkManager.getClient()
                            .async()
                            .api()
                            .v1()
                            .chats()
                            .agents()
                            .clearMessages(
                                agentId = agentId,
                                requestOptions =
                                    RequestOptions.builder()
                                        .timeout(
                                            Duration.ofMillis(
                                                NetworkConfig.getCurrentEnvironmentConfig()
                                                    .timeout
                                                    .connectTimeoutMs
                                            )
                                        )
                                        .build(),
                            )
                    }
                    .onFailure { LogUtils.e(it.localizedMessage) }
                    .getOrNull()

            result?.success() == true
        }
    }
}
