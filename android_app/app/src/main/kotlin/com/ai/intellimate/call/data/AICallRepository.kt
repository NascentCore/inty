package com.ai.intellimate.call.data

import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.http.config.NetworkConfig
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.inty.voicecall.CallPacket
import ai.sxwl.android.inty.voicecall.IntyVoiceCallClient
import ai.sxwl.android.inty.voicecall.IntyVoiceCallUrls
import ai.sxwl.android.inty.voicecall.VoiceCallConnectionState
import ai.sxwl.android.utils.LogUtils
import com.ai.intellimate.utils.NetworkErrorHandler
import com.ai.intellimate.xb.helper.AgentStore
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.flow

class AICallRepository(private val voiceCallClient: IntyVoiceCallClient) {
    fun call(
        agentId: String,
        speechLanguageCode: String? = null,
        responseLanguageName: String? = null,
    ): Flow<CallPacket> {
        val url =
            IntyVoiceCallUrls.liveChatWebSocketUrl(
                NetworkConfig.getWebsocketAddress(),
                agentId,
                IntySetting.getCurToken(),
                speechLanguageCode = speechLanguageCode,
                responseLanguageName = responseLanguageName,
            )
        LogUtils.d("开始连接语音通话，agentId: $agentId, url: $url")
        return voiceCallClient.packets(url)
    }

    suspend fun sendPacket(packet: CallPacket) {
        voiceCallClient.sendPacket(packet)
    }

    suspend fun sendVoice(audio: ByteArray) {
        voiceCallClient.sendVoicePcm16kBase64(audio)
    }

    suspend fun sendActivityStart() {
        voiceCallClient.sendActivityStart()
    }

    suspend fun sendActivityEnd() {
        voiceCallClient.sendActivityEnd()
    }

    suspend fun closeCall() {
        LogUtils.d("关闭语音通话")
        voiceCallClient.close()
    }

    fun getConnectionState(): StateFlow<VoiceCallConnectionState> {
        return voiceCallClient.connectionState()
    }

    fun getAgentInfo(agentId: String): Flow<Result<AgentInfo>> =
        flow {
                AgentStore.getAgent(agentId)?.let { emit(Result.success(it)) }

                when (val result = NetServiceMgr.getAgentApi().getAgentDetail(agentId)) {
                    is HttpResult.Success -> {
                        AgentStore.addAgent(result.data)
                        emit(Result.success(result.data))
                    }
                    is HttpResult.Failure -> {
                        NetworkErrorHandler.showNetworkAwareError(result.message)
                    }
                }
            }
            .catch { emit(Result.failure(it)) }
}
