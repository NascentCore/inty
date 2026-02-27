package com.ai.intellimate.call.data

import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.http.config.NetworkConfig
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.utils.LogUtils
import android.util.Base64
import com.ai.intellimate.call.data.bean.CallPacket
import com.ai.intellimate.call.data.bean.CallType
import com.ai.intellimate.utils.NetworkErrorHandler
import com.ai.intellimate.xb.helper.AgentStore
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.retryWhen

/** AI语音通话Repository实现 只负责WebSocket连接和数据传输，不处理音频录制和播放 */
class AICallRepository(private val dataSource: AICallDataSource) {
    // 重连相关
    private var reconnectAttempts = 0
    private val maxReconnectAttempts = 5
    private val reconnectDelayMs = 2000L
    private var shouldReconnect = false

    /**
     * 建立WebSocket连接（带重连机制）
     *
     * @return 接收到的CallPacket数据流
     */
    fun call(agentId: String): Flow<CallPacket> {
        val url =
            "${NetworkConfig.getWebsocketAddress()}api/v1/live-chat/$agentId?token=${IntySetting.getCurToken()}"
        LogUtils.d("开始连接语音通话，agentId: $agentId, url: $url")
        reconnectAttempts = 0

        return createReconnectableFlow(url)
    }

    /** 创建可重连的Flow */
    private fun createReconnectableFlow(url: String): Flow<CallPacket> =
        flow {
                // 收集数据，如果Flow完成（正常或异常），会继续循环尝试重连
                dataSource.connect(url).collect { packet -> emit(packet) }
            }
            .retryWhen { cause, attempt ->
                delay(attempt * reconnectDelayMs)
                true
            }

    /** 发送CallPacket数据 */
    suspend fun sendPacket(packet: CallPacket) {
        dataSource.sendPacket(packet)
    }

    suspend fun sendVoice(audio: ByteArray) {
        // 将audio编码为base64并发送
        val base64String = Base64.encodeToString(audio, Base64.NO_WRAP)
        val packet = CallPacket(CallType.AUDIO.name.lowercase(), base64String)
        dataSource.sendPacket(packet)
    }

    suspend fun sendActivityStart() {
        val packet = CallPacket(CallType.ACTIVITY_START.name.lowercase())
        dataSource.sendPacket(packet)
    }

    suspend fun sendActivityEnd() {
        val packet = CallPacket(CallType.ACTIVITY_END.name.lowercase())
        dataSource.sendPacket(packet)
    }

    /** 关闭连接 */
    suspend fun closeCall() {
        LogUtils.d("关闭语音通话")
        shouldReconnect = false // 停止重连
        dataSource.close()
    }

    /** 获取连接状态 */
    fun getConnectionState(): StateFlow<ConnectionState> {
        return dataSource.connectionState
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
