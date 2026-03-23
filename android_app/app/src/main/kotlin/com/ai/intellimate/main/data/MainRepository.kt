package com.ai.intellimate.main.data

import ai.sxwl.android.data.api.model.SendMsgReq
import ai.sxwl.android.data.billing.VipStatusHelper
import ai.sxwl.android.data.chat.local.db.MessageEntity
import ai.sxwl.android.data.chat.local.db.toEntity
import ai.sxwl.android.data.http.BusinessErrorCodes
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.utils.LogUtils
import com.ai.intellimate.chat.data.ChatLocalDataSource
import com.ai.intellimate.chat.viewmodel.ChatViewModel
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.receiveAsFlow

/** 主 WebSocket 订阅/额度相关弹窗信号（与 [ChatViewModel.ChatLimitDialogType] 对齐）。 */
data class SubLimitSignal(
    val dialogType: ChatViewModel.ChatLimitDialogType,
    val sourceAgentId: String?,
)

class MainRepository(
    val chatLocalDataSource: ChatLocalDataSource = ChatLocalDataSource(),
    val mainRemoteDataSource: MainRemoteDataSource = MainRemoteDataSource,
) {

    private val _subLimitChannel = Channel<SubLimitSignal>()
    val subLimit = _subLimitChannel.receiveAsFlow()

    /** 通过主 WebSocket 发送消息，不等待响应。 */
    suspend fun sendMessageViaWebSocketFireAndForget(agentId: String, request: SendMsgReq) {
        mainRemoteDataSource.sendMessageFireAndForget(agentId, request)
    }

    suspend fun connectWebSocket() {
        IntySetting.isLoginFlow().distinctUntilChanged().collectLatest {
            if (it) {
                mainRemoteDataSource.connectWebsocket().collect { message ->
                    val errAgentId = message.agentId ?: message.data?.sourceImateId
                    when (message.code) {
                        BusinessErrorCodes.SUBSCRIPTION_REQUIRED_CODE -> {
                            if (!errAgentId.isNullOrBlank()) {
                                chatLocalDataSource
                                    .markEarliestSendingUserAsFailedAndRemoveLoadingIfLast(errAgentId)
                            }
                            val dialogType =
                                ChatViewModel.resolveChatLimitDialogType(VipStatusHelper.isUserVip())
                            _subLimitChannel.send(SubLimitSignal(dialogType, errAgentId))
                        }
                        else -> {
                            val data = message.data ?: return@collect
                            val agentId = message.agentId ?: data.sourceImateId ?: return@collect
                            // 与 HTTP 一致：非 200 视为失败，只将最早一条发送中标记为失败（与成功路径一致）
                            if (message.code != null && message.code != 200) {
                                chatLocalDataSource
                                    .markEarliestSendingUserAsFailedAndRemoveLoadingIfLast(agentId)
                                return@collect
                            }
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
                                    if (agentId.isNotBlank()) choice.message.toEntity(agentId)
                                    else choice.message.toEntity()
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
    }
}
