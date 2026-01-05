package com.ai.intellimate.call.data

import ai.sxwl.android.utils.LogUtils
import androidx.annotation.StringRes
import com.ai.intellimate.R
import com.ai.intellimate.call.data.bean.CallPacket
import io.ktor.client.HttpClient
import io.ktor.client.plugins.websocket.DefaultClientWebSocketSession
import io.ktor.client.plugins.websocket.receiveDeserialized
import io.ktor.client.plugins.websocket.sendSerialized
import io.ktor.client.plugins.websocket.webSocketSession
import io.ktor.client.request.url
import io.ktor.websocket.close
import kotlinx.coroutines.channels.ClosedReceiveChannelException
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.onCompletion
import kotlinx.coroutines.flow.onEach
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

/** WebSocket连接状态 */
enum class ConnectionState(@StringRes val textRes: Int? = null) {
    DISCONNECTED, // 未连接
    CONNECTING(R.string.voice_call_connecting), // 连接中
    CONNECTED(R.string.voice_call_connected), // 已连接
    DISCONNECTING, // 断开中
    ERROR(R.string.voice_call_error), // 错误
}

/** AI语音通话数据源 负责WebSocket连接的建立、维护和数据传输 */
class AICallDataSource(private val httpClient: HttpClient) {
    private var _session: DefaultClientWebSocketSession? = null
    private val sessionMutex = Mutex()

    // 连接状态
    private val _connectionState = MutableStateFlow<ConnectionState>(ConnectionState.DISCONNECTED)
    val connectionState: StateFlow<ConnectionState> = _connectionState.asStateFlow()

    init {
        LogUtils.d("语音通话创建AICallDataSource")
    }

    /**
     * 建立websocket连接
     *
     * @param url WebSocket服务器地址
     * @return 接收到的CallPacket数据流
     */
    suspend fun connect(url: String): Flow<CallPacket> {
        close()

        _connectionState.value = ConnectionState.CONNECTING
        LogUtils.d("开始建立WebSocket连接: $url")

        return flow {
                val session = httpClient.webSocketSession { url(url) }

                sessionMutex.withLock { _session = session }
                _connectionState.value = ConnectionState.CONNECTED
                LogUtils.d("WebSocket连接已建立")
                while (true) {
                    emit(session.receiveDeserialized<CallPacket>())
                }
            }
            .onEach { LogUtils.d("语音聊天：收到消息${it}") }
            .catch { error -> if (error !is ClosedReceiveChannelException) throw error }
            .onCompletion { cause ->
                LogUtils.d("WebSocket接收流完成，原因: ${cause?.message}")
                if (cause != null) {
                    _connectionState.value = ConnectionState.ERROR
                } else {
                    _connectionState.value = ConnectionState.DISCONNECTED
                }
            }
    }

    /**
     * 发送CallPacket数据
     *
     * @param packet CallPacket数据包
     */
    suspend fun sendPacket(packet: CallPacket) {
        val session = sessionMutex.withLock { _session }
        if (session == null) {
            LogUtils.e("WebSocket连接未建立，无法发送数据")
            throw IllegalStateException("WebSocket连接未建立")
        }

        if (_connectionState.value != ConnectionState.CONNECTED) {
            LogUtils.e("WebSocket连接状态异常: ${_connectionState.value}，无法发送数据")
            throw IllegalStateException("WebSocket连接状态异常: ${_connectionState.value}")
        }

        try {
            session.sendSerialized(packet)
            // LogUtils.d("语音聊天:发送${packet}")
        } catch (e: Exception) {
            LogUtils.e("发送CallPacket失败: ${e.message}")
            _connectionState.value = ConnectionState.ERROR
            throw e
        }
    }

    /** 检查连接状态 */
    fun isConnected(): Boolean {
        return _connectionState.value == ConnectionState.CONNECTED && _session != null
    }

    /** 关闭连接 */
    suspend fun close() {
        _connectionState.value = ConnectionState.DISCONNECTING

        val session =
            sessionMutex.withLock {
                val current = _session
                _session = null
                current
            }

        session?.let {
            try {
                it.close()
                LogUtils.d("WebSocket连接已关闭")
            } catch (e: Exception) {
                LogUtils.d("关闭WebSocket连接时发生异常: ${e.message}")
            }
        }

        _connectionState.value = ConnectionState.DISCONNECTED
    }
}
