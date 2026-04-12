package ai.sxwl.android.data.chat.data

import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.ChatImageGenerationRequest
import ai.sxwl.android.data.api.model.ChatImageGenerationResult
import ai.sxwl.android.data.api.model.ChatMessageContentPart
import ai.sxwl.android.data.api.model.ChatMode
import ai.sxwl.android.data.api.model.ChatSettingsReq
import ai.sxwl.android.data.api.model.ChatSettingsResponse
import ai.sxwl.android.data.api.model.ClearMessagesRequest
import ai.sxwl.android.data.api.model.QueryMsgsResponse
import ai.sxwl.android.data.api.model.SendMsgReq
import ai.sxwl.android.data.api.model.SendMsgReqMessage
import ai.sxwl.android.data.api.model.SendMsgResponse
import ai.sxwl.android.data.api.model.SurpriseSnapUnlockReq
import ai.sxwl.android.data.api.model.SurpriseSnapUnlockResp
import ai.sxwl.android.data.api.model.UserTimeContext
import ai.sxwl.android.data.api.model.VoteMessageReq
import ai.sxwl.android.data.api.model.VoteMessageRsp
import ai.sxwl.android.data.http.BusinessErrorCodes
import ai.sxwl.android.data.http.config.DebugBackendEndpointStore
import ai.sxwl.android.utils.LogUtils
import com.architecture.httplib.core.HttpResult
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter

/** 聊天远程数据源 负责处理与服务器的聊天相关API调用 遵循Clean Architecture的数据层模式 */
class ChatRemoteDataSource {

    companion object {
        /** Release 默认上报；Debug 可在调试设置中关闭。供 POST chat completions 请求体中的 time_context 使用。 */
        fun buildUserTimeContextOrNull(): UserTimeContext? {
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
            if (!DebugBackendEndpointStore.isRuntimeOverrideSupported()) {
                return true
            }
            return DebugBackendEndpointStore.getUserTimeContextReportingEnabled()
        }
    }

    suspend fun getChatModes(): HttpResult<List<ChatMode>> {

        return NetServiceMgr.getChatApi().fetchChatModes()
    }

    suspend fun updateChatSettings(
        agentId: String,
        chatSettingsReq: ChatSettingsReq,
    ): HttpResult<ChatSettingsResponse> {
        return NetServiceMgr.getChatApi().updateChatSettings(agentId, chatSettingsReq)
    }

    suspend fun getChatSettings(
        agentId: String
    ): HttpResult<ChatSettingsResponse.ChatSettingRspData> {
        return NetServiceMgr.getChatApi().getChatSettings(agentId)
    }

    suspend fun unlockSurpriseSnap(messageId: Long): HttpResult<SurpriseSnapUnlockResp> {
        return NetServiceMgr.getChatApi().unlockSurpriseSnap(SurpriseSnapUnlockReq(messageId))
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

    /** 构建与 HTTP 发送一致的 SendMsgReq。 */
    fun buildSendMsgReq(
        agentId: String,
        userText: String,
        userImageUrl: String? = null,
    ): SendMsgReq {
        val trimmedUserText = userText.trimEnd()
        val requestMessage =
            if (userImageUrl.isNullOrBlank()) {
                SendMsgReqMessage.text(role = "user", text = trimmedUserText)
            } else {
                SendMsgReqMessage.multimodal(
                    role = "user",
                    parts =
                        buildList {
                            if (trimmedUserText.isNotBlank()) {
                                add(ChatMessageContentPart(type = "text", text = trimmedUserText))
                            }
                            add(
                                ChatMessageContentPart(
                                    type = "image_url",
                                    imageUrl =
                                        ChatMessageContentPart.ImageUrlPayload(url = userImageUrl),
                                )
                            )
                        },
                )
            }
        return SendMsgReq(
            messages = listOf(requestMessage),
            timeContext = buildUserTimeContextOrNull(),
            targetImateId = agentId,
        )
    }

    suspend fun sendMessage(
        agentId: String,
        userText: String,
        userImageUrl: String? = null,
    ): HttpResult<SendMsgResponse> {
        return try {
            LogUtils.i(
                "ChatRemoteDataSource.sendMessage: agentId=$agentId, hasImage=${!userImageUrl.isNullOrBlank()}"
            )
            val request = buildSendMsgReq(agentId, userText, userImageUrl)
            NetServiceMgr.getChatApi().sendMsg(agentId, request)
        } catch (e: Exception) {
            LogUtils.e("ChatRemoteDataSource.sendMessage exception: ${e.message}")
            HttpResult.Failure(e.message ?: "Network error", -1)
        }
    }

    /** 消息生图的接口请求 */
    suspend fun messageGenerateImage(
        agentId: String,
        messageId: String,
    ): HttpResult<ChatImageGenerationResult> {
        return try {
            LogUtils.i("ChatRemoteDataSource.generateImage: agentId=$agentId, messageId=$messageId")
            when (
                val result =
                    NetServiceMgr.getChatApi()
                        .generateMessageImage(
                            agentId,
                            ChatImageGenerationRequest(messageId = messageId.toLongOrNull() ?: 0L),
                        )
            ) {
                is HttpResult.Success -> {
                    mapGenerateImageResponse(messageId, result.data)
                }

                is HttpResult.Failure -> {
                    HttpResult.Failure(result.message, result.code)
                }
            }
        } catch (e: Exception) {
            LogUtils.e("ChatRemoteDataSource.generateImage exception: ${e.message}")
            HttpResult.Failure(e.message ?: "Network error", -1)
        }
    }

    internal fun mapGenerateImageResponse(
        requestedMessageId: String,
        response: ai.sxwl.android.data.api.model.ChatImageGenerationApiResponse,
    ): HttpResult<ChatImageGenerationResult> {
        val payload = response.data
        val responseCode = response.code
        val hasBusinessError =
            (responseCode != null && responseCode != 200) || !payload?.errorCode.isNullOrBlank()

        if (hasBusinessError) {
            val mappedCode = mapBusinessErrorCode(payload?.errorCode, responseCode)
            val mappedMessage =
                payload?.message
                    ?: response.message
                    ?: BusinessErrorCodes.BUSINESS_ERROR_MESSAGES[mappedCode]
                    ?: "Image generation failed"
            return HttpResult.Failure(mappedMessage, mappedCode)
        }

        if (responseCode != 200) {
            return HttpResult.Failure(response.message ?: "Image generation failed", -1)
        }

        if (payload == null || payload.imageUrl.isNullOrEmpty()) {
            return HttpResult.Failure("Image generation response is empty", -1)
        }

        return HttpResult.Success(
            ChatImageGenerationResult(
                imageUrl = payload.imageUrl,
                width = payload.imageMetadata.toDimension("width"),
                height = payload.imageMetadata.toDimension("height"),
                messageId = payload.messageId ?: (requestedMessageId.toLongOrNull() ?: 0L),
            )
        )
    }

    private fun Map<String, Any?>?.toDimension(key: String): Int {
        val value = this?.get(key) ?: return 0
        return when (value) {
            is Number -> value.toInt()
            is String -> value.toIntOrNull() ?: 0
            else -> 0
        }
    }

    private fun mapBusinessErrorCode(errorCode: String?, responseCode: Int?): Int {
        return when (errorCode) {
            BusinessErrorCodes.SUBSCRIPTION_REQUIRED_ERROR_CODE ->
                BusinessErrorCodes.SUBSCRIPTION_REQUIRED_CODE
            BusinessErrorCodes.IMAGE_GENERATION_LIMIT_REACHED_ERROR_CODE ->
                BusinessErrorCodes.IMAGE_GENERATION_LIMIT_REACHED_CODE
            BusinessErrorCodes.AGENT_CREATION_LIMIT_REACHED_ERROR_CODE ->
                BusinessErrorCodes.AGENT_CREATION_LIMIT_REACHED_CODE
            BusinessErrorCodes.VOICE_GENERATION_LIMIT_REACHED_ERROR_CODE ->
                BusinessErrorCodes.VOICE_GENERATION_LIMIT_REACHED_CODE
            BusinessErrorCodes.GUEST_LOGIN_REQUIRED_ERROR_CODE ->
                BusinessErrorCodes.GUEST_LOGIN_REQUIRED_CODE
            BusinessErrorCodes.IMAGE_GENERATION_BLOCKED_ERROR_CODE ->
                BusinessErrorCodes.IMAGE_GENERATION_BLOCKED_CODE
            BusinessErrorCodes.LIVE_CHAT_AGENT_LIMIT_REACHED_ERROR_CODE ->
                BusinessErrorCodes.LIVE_CHAT_AGENT_LIMIT_REACHED_CODE
            BusinessErrorCodes.LIVE_CHAT_DURATION_LIMIT_REACHED_ERROR_CODE ->
                BusinessErrorCodes.LIVE_CHAT_DURATION_LIMIT_REACHED_CODE
            else -> responseCode ?: -1
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
        return when (
            val result = NetServiceMgr.getChatApi().clearMessages(agentId, ClearMessagesRequest())
        ) {
            is HttpResult.Success -> {
                result.data.success
            }

            is HttpResult.Failure -> {
                LogUtils.e(
                    "ChatRemoteDataSource.clearMessage failed: code=${result.code}, message=${result.message}"
                )
                false
            }
        }
    }
}
