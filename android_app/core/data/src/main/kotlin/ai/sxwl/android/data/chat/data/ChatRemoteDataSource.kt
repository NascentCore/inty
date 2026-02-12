package ai.sxwl.android.data.chat.data

import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.api.model.QueryMsgsResponse
import ai.sxwl.android.data.api.model.SendMsgReq
import ai.sxwl.android.data.api.model.SendMsgResponse
import ai.sxwl.android.data.api.model.UserTimeContext
import ai.sxwl.android.data.api.model.VoteMessageReq
import ai.sxwl.android.data.api.model.VoteMessageRsp
import ai.sxwl.android.data.http.UnifiedOkHttpClient
import ai.sxwl.android.data.http.IntyNetworkManager
import ai.sxwl.android.data.http.config.DebugBackendEndpointStore
import ai.sxwl.android.data.http.config.NetworkConfig
import ai.sxwl.android.utils.LogUtils
import com.architecture.httplib.core.HttpResult
import com.inty.api.core.RequestOptions
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import java.time.Duration
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject

/** 聊天远程数据源 负责处理与服务器的聊天相关API调用 遵循Clean Architecture的数据层模式 */
class ChatRemoteDataSource {
    private val moshi: Moshi = Moshi.Builder().addLast(KotlinJsonAdapterFactory()).build()
    private val sendMsgReqAdapter = moshi.adapter(SendMsgReq::class.java)
    private val sendMsgResponseAdapter = moshi.adapter(SendMsgResponse::class.java)

    private companion object {
        private val JSON_MEDIA_TYPE = "application/json; charset=utf-8".toMediaType()
        private const val STREAM_ACCEPT_HEADER = "text/event-stream, application/json"
    }

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

    suspend fun sendMessage(
        agentId: String,
        messages: List<MsgInfo>,
        stream: Boolean = false,
        onStreamDelta: (suspend (String) -> Unit)? = null,
    ): HttpResult<SendMsgResponse> {
        return try {
            LogUtils.i(
                "ChatRemoteDataSource.sendMessage: agentId=$agentId, messagesCount=${messages.size}, stream=$stream"
            )
            val request = SendMsgReq(messages = messages, timeContext = buildUserTimeContext())
            if (!stream) {
                NetServiceMgr.getChatApi().sendMsg(agentId, request)
            } else {
                sendMessageStreaming(agentId, request, onStreamDelta)
            }
        } catch (e: Exception) {
            LogUtils.e("ChatRemoteDataSource.sendMessage exception: ${e.message}")
            HttpResult.Failure(e.message ?: "Network error", -1)
        }
    }

    private suspend fun sendMessageStreaming(
        agentId: String,
        request: SendMsgReq,
        onStreamDelta: (suspend (String) -> Unit)?,
    ): HttpResult<SendMsgResponse> {
        return withContext(Dispatchers.IO) {
            val streamEnabledRequest = request.copy(stream = true)
            val requestJson = sendMsgReqAdapter.toJson(streamEnabledRequest)
            val baseUrl = NetServiceMgr.baseUrl().trimEnd('/')
            val url = "$baseUrl/api/v1/chat/completions/$agentId"

            val httpRequest =
                Request.Builder()
                    .url(url)
                    .post(requestJson.toRequestBody(JSON_MEDIA_TYPE))
                    .header("Accept", STREAM_ACCEPT_HEADER)
                    .build()

            val httpClient = UnifiedOkHttpClient.create()
            httpClient.newCall(httpRequest).execute().use { response ->
                val responseBody = response.body
                if (responseBody == null) {
                    return@withContext HttpResult.Failure("Empty response body", -1)
                }

                // 对于订阅限制等业务错误，后端会返回常规 JSON。
                val contentType = response.header("Content-Type").orEmpty().lowercase()
                if (!contentType.contains("text/event-stream")) {
                    val bodyText = responseBody.string()
                    if (!response.isSuccessful) {
                        return@withContext HttpResult.Failure(
                            bodyText.ifBlank { "HTTP ${response.code}" },
                            response.code,
                        )
                    }
                    val parsed = sendMsgResponseAdapter.fromJson(bodyText)
                    return@withContext if (parsed != null) {
                        HttpResult.Success(parsed)
                    } else {
                        HttpResult.Failure("Invalid JSON response", -1)
                    }
                }

                if (!response.isSuccessful) {
                    return@withContext HttpResult.Failure(
                        "HTTP ${response.code}",
                        response.code,
                    )
                }

                val assistantContent = StringBuilder()
                var finishReason = "stop"
                val source = responseBody.source()

                while (!source.exhausted()) {
                    val rawLine = source.readUtf8Line() ?: continue
                    val line = rawLine.trim()
                    if (line.isEmpty() || !line.startsWith("data:")) {
                        continue
                    }

                    val payload = line.removePrefix("data:").trim()
                    if (payload == "[DONE]") {
                        break
                    }

                    val json = runCatching { JSONObject(payload) }.getOrNull() ?: continue
                    if (json.has("error")) {
                        val errMsg =
                            json.optJSONObject("error")
                                ?.optString("message", "Stream error")
                                ?: "Stream error"
                        return@withContext HttpResult.Failure(errMsg, -1)
                    }

                    val choices = json.optJSONArray("choices") ?: continue
                    if (choices.length() == 0) {
                        continue
                    }
                    val choice = choices.optJSONObject(0) ?: continue

                    if (!choice.isNull("finish_reason")) {
                        finishReason = choice.optString("finish_reason", finishReason)
                    }

                    val delta = choice.optJSONObject("delta")
                    val deltaText = delta?.optString("content", "") ?: ""
                    if (deltaText.isNotEmpty()) {
                        assistantContent.append(deltaText)
                        onStreamDelta?.invoke(deltaText)
                    }
                }

                val finalText = assistantContent.toString()
                if (finalText.isBlank()) {
                    return@withContext HttpResult.Failure("Empty streaming response", -1)
                }

                val syntheticResponse =
                    SendMsgResponse(
                        code = 200,
                        message = "success",
                        data =
                            SendMsgResponse.SentMsgRspData(
                                user_message_id = 0,
                                choices =
                                    listOf(
                                        ai.sxwl.android.data.api.model.Choice(
                                            finishReason = finishReason,
                                            index = 0,
                                            message =
                                                MsgInfo(
                                                    content = finalText,
                                                    role = "assistant",
                                                ),
                                        )
                                    ),
                                created = (System.currentTimeMillis() / 1000L).toInt(),
                                id = "chatcmpl-stream",
                                model = "chatbot",
                                objectX = "chat.completion",
                                usage = ai.sxwl.android.data.api.model.Usage(),
                            ),
                    )

                HttpResult.Success(syntheticResponse)
            }
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
            false
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
