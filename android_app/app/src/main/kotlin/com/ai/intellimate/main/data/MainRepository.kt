package com.ai.intellimate.main.data

import ai.sxwl.android.data.chat.local.db.toEntity
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.utils.LogUtils
import com.ai.intellimate.chat.data.ChatLocalDataSource
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.flow.distinctUntilChanged

class MainRepository(
    val chatLocalDataSource: ChatLocalDataSource = ChatLocalDataSource(),
    val mainRemoteDataSource: MainRemoteDataSource = MainRemoteDataSource()
) {

    suspend fun connectWebSocket() {
        IntySetting.isLoginFlow()
            .distinctUntilChanged()
            .collectLatest {
                if (it) {
                    mainRemoteDataSource
                        .connectWebsocket()
                        .collect { message ->
                            val data = message.data ?: return@collect
                            val agentId = data.sourceImateId
                            val entities =
                                data.choices.mapNotNull { choice ->
                                    if (!agentId.isNullOrBlank()) {
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