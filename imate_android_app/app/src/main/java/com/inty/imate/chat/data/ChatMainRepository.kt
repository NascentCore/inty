package com.inty.imate.chat.data

import com.ai.core.utils.LogUtils
import com.inty.imate.account.data.AuthRepository
import com.inty.imate.chat.data.api.BusinessErrorCodes
import com.inty.imate.chat.data.bean.SendMsgReq
import com.inty.imate.chat.data.bean.SendMsgResponse
import com.inty.imate.chat.data.datasource.ChatLocalDataSource
import com.inty.imate.chat.data.datasource.ChatWebSocketRemoteDataSource
import com.inty.imate.chat.local.db.MessageEntity
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.receiveAsFlow

enum class ChatSubLimitKind {
    FREE_USER_SUBSCRIPTION_REQUIRED,
    SUBSCRIBER_LIMIT_REACHED,
}

data class ChatSubLimitSignal(
    val kind: ChatSubLimitKind,
    val sourceAgentId: String?,
)

@Singleton
class ChatMainRepository
@Inject
constructor(
    private val chatLocalDataSource: ChatLocalDataSource,
    private val chatWebSocketRemoteDataSource: ChatWebSocketRemoteDataSource,
    private val authRepository: AuthRepository,
) {

    private val _subLimitChannel = Channel<ChatSubLimitSignal>(Channel.BUFFERED)
    val subLimit = _subLimitChannel.receiveAsFlow()

    private val _agentStatusLineChannel = Channel<Pair<String, String>>(Channel.BUFFERED)
    val agentStatusLineUpdates = _agentStatusLineChannel.receiveAsFlow()

    val isChatWebSocketConnected: StateFlow<Boolean> = chatWebSocketRemoteDataSource.isSessionActive

    suspend fun sendMessageViaWebSocketFireAndForget(agentId: String, request: SendMsgReq) {
        chatWebSocketRemoteDataSource.sendMessageFireAndForget(agentId, request)
    }

    suspend fun sendImplicitUserSignedOnFireAndForget(agentId: String) {
        chatWebSocketRemoteDataSource.sendImplicitUserSignedOnFireAndForget(agentId)
    }

    /** Best-effort server-side session reset; clears local chat cache before auth is cleared. */
    suspend fun signOutFromChatSession(agentId: String?) {
        val aid = agentId?.trim().orEmpty()
        if (aid.isNotEmpty()) {
            try {
                chatWebSocketRemoteDataSource.sendUserSignedOutFireAndForget(aid)
            } catch (e: Exception) {
                LogUtils.d("sendUserSignedOutFireAndForget failed: ${e.message}")
            }
        }
        chatLocalDataSource.clearAllMessages()
    }

    suspend fun connectWebSocketWhenLoggedIn() {
        authRepository.isLogin.distinctUntilChanged().collectLatest { loggedIn ->
            if (loggedIn) {
                chatWebSocketRemoteDataSource.connectWebsocket().collect { message ->
                    handleIncoming(message)
                }
            }
        }
    }

    private suspend fun handleIncoming(message: SendMsgResponse) {
        val errAgentId = message.agentId ?: message.data?.sourceImateId
        when (message.code) {
            BusinessErrorCodes.SUBSCRIPTION_REQUIRED_CODE -> {
                if (!errAgentId.isNullOrBlank()) {
                    chatLocalDataSource.markEarliestSendingUserAsFailedAndRemoveLoadingIfLast(errAgentId)
                }
                val kind =
                    if (isUserVip()) {
                        ChatSubLimitKind.SUBSCRIBER_LIMIT_REACHED
                    } else {
                        ChatSubLimitKind.FREE_USER_SUBSCRIPTION_REQUIRED
                    }
                _subLimitChannel.send(ChatSubLimitSignal(kind, errAgentId))
            }
            else -> {
                val agentIdHint = message.agentId ?: message.data?.sourceImateId
                if (message.code != null && message.code != 200) {
                    if (!agentIdHint.isNullOrBlank()) {
                        chatLocalDataSource.markEarliestSendingUserAsFailedAndRemoveLoadingIfLast(agentIdHint)
                    }
                    return
                }
                val data = message.data ?: return
                val agentId = message.agentId ?: data.sourceImateId ?: return
                val sendingUser = chatLocalDataSource.getEarliestSendingUserMessage(agentId)
                chatLocalDataSource.removeEarliestSendingUserAndLoadingIfLast(agentId)
                if (sendingUser != null) {
                    chatLocalDataSource.appendMessages(
                        listOf(
                            sendingUser.copy(
                                id = data.user_message_id.toString(),
                                status = MessageEntity.Status.SUCCESS,
                            )
                        )
                    )
                }
                val entities =
                    data.choices.mapNotNull { choice ->
                        if (agentId.isNotBlank()) choice.message.toMessageEntity(agentId)
                        else choice.message.toMessageEntity()
                    }
                delay(200)
                if (entities.isNotEmpty()) {
                    LogUtils.d("Chat WS incoming messages: ${entities.size}")
                    chatLocalDataSource.appendMessages(entities)
                }
                val sl = message.statusLine?.trim().orEmpty()
                _agentStatusLineChannel.send(agentId to sl)
            }
        }
    }

    private fun isUserVip(): Boolean = false
}
