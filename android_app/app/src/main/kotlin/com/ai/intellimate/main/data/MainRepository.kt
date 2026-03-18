package com.ai.intellimate.main.data

import ai.sxwl.android.common.event.ChatEvent
import ai.sxwl.android.common.event.EventBus
import ai.sxwl.android.data.api.model.SendMsgReq
import ai.sxwl.android.data.chat.local.db.MessageEntity
import ai.sxwl.android.data.chat.local.db.toEntity
import ai.sxwl.android.data.http.BusinessErrorCodes
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.utils.LogUtils
import com.ai.intellimate.chat.data.ChatLocalDataSource
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.flow.distinctUntilChanged

class MainRepository(
    val chatLocalDataSource: ChatLocalDataSource = ChatLocalDataSource(),
    val mainRemoteDataSource: MainRemoteDataSource = MainRemoteDataSource,
) {

    /** 通过主 WebSocket 发送消息，不等待响应。 */
    suspend fun sendMessageViaWebSocketFireAndForget(agentId: String, request: SendMsgReq) {
        mainRemoteDataSource.sendMessageFireAndForget(agentId, request)
    }

    suspend fun connectWebSocket() {
        IntySetting.isLoginFlow().distinctUntilChanged().collectLatest {
            if (it) {
                mainRemoteDataSource.connectWebsocket().collect { message ->
                    val agentIdForError =
                        message.agentId ?: message.data?.sourceImateId
                    if (message.code == BusinessErrorCodes.SUBSCRIPTION_REQUIRED_CODE) {
                        if (!agentIdForError.isNullOrBlank()) {
                            chatLocalDataSource
                                .markEarliestSendingUserAsFailedAndRemoveLoadingIfLast(agentIdForError)
                        }
                        EventBus.postOnMainThread(
                            ChatEvent.WebSocketSubscriptionRequired(agentIdForError ?: ""),
                        )
                        return@collect
                    }
                    val data = message.data ?: return@collect
                    val agentId = message.agentId ?: data.sourceImateId ?: return@collect
                    if (message.code != null && message.code != 200) {
                        chatLocalDataSource.markEarliestSendingUserAsFailedAndRemoveLoadingIfLast(
                            agentId
                        )
                        return@collect
                    }
                    val sendingUser = chatLocalDataSource.getEarliestSendingUserMessage(agentId)
                    chatLocalDataSource.removeEarliestSendingUserAndLoadingIfLast(agentId)
                    if (sendingUser != null) {
                        val userMessage =
                            sendingUser.copy(
                                id = data.user_message_id.toString(),
                                status = MessageEntity.Status.SUCCESS,
                            )
                        chatLocalDataSource.appendMessages(listOf(userMessage))
                    }
                    val entities =
                        data.choices.mapNotNull { choice ->
                            if (agentId.isNotBlank()) {
                                choice.message.toEntity(agentId)
                            } else {
                                choice.message.toEntity()
                            }
                        }
                    if (entities.isNotEmpty()) {
                        LogUtils.d("收到实时消息:${entities}")
                        chatLocalDataSource.appendMessages(entities)
                    }
                }
            }
        }
    }
}
