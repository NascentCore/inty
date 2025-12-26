package com.ai.intellimate.call.data

import ai.sxwl.android.utils.LogUtils
import android.util.Base64
import com.ai.intellimate.call.data.bean.CallPacket
import com.ai.intellimate.call.data.bean.CallType
import com.ai.intellimate.ui.UiConfigs
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.flow

/**
 * AI语音通话Repository实现
 * 只负责WebSocket连接和数据传输，不处理音频录制和播放
 */
class AICallRepository(
    private val dataSource: AICallDataSource = AICallDataSource(KtorHttpClientFactory.getInstance())
) {
    // 重连相关
    private var reconnectAttempts = 0
    private val maxReconnectAttempts = 5
    private val reconnectDelayMs = 2000L
    private var shouldReconnect = true

    /**
     * 建立WebSocket连接（带重连机制）
     * @return 接收到的CallPacket数据流
     */
    fun call(agentId: String): Flow<CallPacket> {
        val url = UiConfigs.Urls.getVoiceCallWebSocketUrl(agentId)
        LogUtils.d("开始连接语音通话，agentId: $agentId, url: $url")

        shouldReconnect = true
        reconnectAttempts = 0

        return createReconnectableFlow(url)
    }

    /**
     * 创建可重连的Flow
     */
    private fun createReconnectableFlow(url: String): Flow<CallPacket> = flow {
        while (shouldReconnect && reconnectAttempts < maxReconnectAttempts) {
            try {
                // 建立连接并获取Flow
                val packetFlow = dataSource.connect(url)
                reconnectAttempts = 0 // 连接成功，重置重连次数

                // 收集数据，如果Flow完成（正常或异常），会继续循环尝试重连
                packetFlow.collect { packet ->
                    emit(packet)
                }

                // 如果Flow正常完成（没有异常），退出循环
                if (!shouldReconnect) {
                    break
                }
            } catch (e: Exception) {
                LogUtils.e("WebSocket连接失败: ${e.message}")

                if (!shouldReconnect) {
                    break
                }

                if (reconnectAttempts >= maxReconnectAttempts) {
                    LogUtils.e("达到最大重连次数，停止重连")
                    break
                }

                reconnectAttempts++
                val delayMs = reconnectDelayMs * reconnectAttempts // 指数退避
                LogUtils.d("准备重连，第 $reconnectAttempts 次尝试，延迟 ${delayMs}ms")
                delay(delayMs)
            }
        }
    }

    /**
     * 发送CallPacket数据
     */
    suspend fun sendPacket(packet: CallPacket) {
        dataSource.sendPacket(packet)
    }

    suspend fun sendVoice(audio: ByteArray) {
        // 将audio编码为base64并发送
        val base64String = Base64.encodeToString(audio, Base64.NO_WRAP)
        val packet = CallPacket(CallType.AUDIO, base64String)
        dataSource.sendPacket(packet)
    }

    /**
     * 关闭连接
     */
    suspend fun closeCall() {
        LogUtils.d("关闭语音通话")
        shouldReconnect = false // 停止重连
        dataSource.close()
    }

    /**
     * 获取连接状态
     */
    fun getConnectionState(): StateFlow<ConnectionState> {
        return dataSource.connectionState
    }
}

