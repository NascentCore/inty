package com.ai.intellimate.audio

import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.http.BusinessErrorCodes
import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.ToastUtils
import android.content.Context
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withTimeout

/** TTS管理器 专门处理文本转语音的生成和管理 */
class TtsManager private constructor(private val context: Context) {

    companion object {
        @Volatile private var INSTANCE: TtsManager? = null

        fun getInstance(context: Context): TtsManager {
            return INSTANCE
                ?: synchronized(this) {
                    INSTANCE ?: TtsManager(context.applicationContext).also { INSTANCE = it }
                }
        }
    }

    // TTS生成状态
    private val _isGeneratingTts = MutableStateFlow<Set<String>>(emptySet())
    val isGeneratingTts: StateFlow<Set<String>> = _isGeneratingTts.asStateFlow()

    // 内部稳定作用域（应用级别，避免外部scope失活）
    private val ioScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    // 去重与并发控制：同一个( agentId, messageId ) 在同一时刻只能有一个in-flight
    private val inFlight = mutableMapOf<String, MutableList<(Result<String>) -> Unit>>()

    // 延迟获取API依赖
    private val chatApi by lazy { NetServiceMgr.getChatApi() }

    /**
     * 生成消息语音
     *
     * @param messageId 消息ID
     * @param agentId Agent ID
     * @param onSuccess 成功回调，返回生成的音频URL
     * @param onError 失败回调
     * @param forceRegenerate 是否强制重新生成（用于失败后重试）
     */
    fun generateMessageVoice(
        messageId: String,
        agentId: String,
        onSuccess: (String) -> Unit,
        onError: (String) -> Unit,
        forceRegenerate: Boolean = false,
    ) {
        // 检查是否正在生成（除非强制重新生成）
        if (!forceRegenerate && _isGeneratingTts.value.contains(messageId)) {
            LogUtils.i("音频LOG测试 TTS already generating for message: $messageId")
            return
        }

        val dedupKey = "$agentId::$messageId"
        val callback: (Result<String>) -> Unit = { r ->
            r.fold(
                onSuccess = { url -> onSuccess(url) },
                onFailure = { e -> onError(e.message ?: "TTS Failed") },
            )
        }

        // 去重：合并相同请求的回调
        synchronized(inFlight) {
            val list = inFlight.getOrPut(dedupKey) { mutableListOf() }
            list.add(callback)
            if (list.size > 1 && !forceRegenerate) {
                LogUtils.i("音频LOG测试 TTS request deduped: $dedupKey, pendingCallbacks=${list.size}")
                return
            }
        }

        // 添加到生成队列（用于UI状态）
        _isGeneratingTts.value = _isGeneratingTts.value + messageId

        // 记录TTS生成开始时间
        val ttsGenerationStartTime = System.currentTimeMillis()

        ioScope.launch {
            try {
                if (agentId.isEmpty() || messageId.isEmpty()) {
                    LogUtils.e(
                        "音频LOG测试 TTS generation failed: agentId='$agentId', messageId='$messageId'"
                    )
                    completeWithError(
                        dedupKey,
                        messageId,
                        "TTS生成失败：参数无效 - agentId='$agentId', messageId='$messageId'",
                        onError,
                    )
                    return@launch
                }

                // 验证agentId和messageId格式
                if (agentId.length < 3 || messageId.length < 3) {
                    LogUtils.e(
                        "音频LOG测试 TTS generation failed: Invalid ID format - agentId='$agentId', messageId='$messageId'"
                    )
                    completeWithError(dedupKey, messageId, "TTS生成失败：ID格式无效", onError)
                    return@launch
                }
                val response = withTimeout(30_000) { chatApi.fetchMsgVoice(agentId, messageId) }

                when (response) {
                    is HttpResult.Success -> {
                        if (response.data.code == BusinessErrorCodes.VOICE_TTS_LIMIT_CODE) {
                            // 音频生成到达次数限制，需要给用户toast提示文案
                            ToastUtils.showShort("${response.data.message}")
                            LogUtils.e("音频LOG测试 TTS 生成次数到达限制 (Agent: $agentId)")
                            completeWithError(
                                dedupKey,
                                messageId,
                                "${response.data.message}",
                                onError,
                            )
                        } else {
                            val audioUrl = response.data.data?.audio_url
                            if (audioUrl != null && audioUrl.isNotEmpty()) {
                                // 计算TTS生成耗时
                                val ttsGenerationTime =
                                    System.currentTimeMillis() - ttsGenerationStartTime

                                // 记录TTS生成时间性能指标
                                FirebaseManager.logPerformanceMetric(
                                    FirebaseManager.Events.TTS_GENERATION_TIME,
                                    ttsGenerationTime,
                                    "ms",
                                    FirebaseManager.safeEventParams(
                                        "agent_id" to agentId,
                                        "message_id" to messageId,
                                        "timestamp" to System.currentTimeMillis(),
                                    ),
                                )

                                completeWithSuccess(dedupKey, messageId, audioUrl, onSuccess)
                            } else {
                                completeWithError(dedupKey, messageId, "TTS生成失败：返回空音频URL", onError)
                            }
                        }
                    }
                    is HttpResult.Failure -> {
                        LogUtils.e(
                            "音频LOG测试 TTS generation failed: ${response.message} (Agent: $agentId)"
                        )
                        completeWithError(
                            dedupKey,
                            messageId,
                            "TTS生成失败：${response.message}",
                            onError,
                        )
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("音频LOG测试 TTS generation exception: ${e.message} (Agent: $agentId)")
                completeWithError(dedupKey, messageId, "TTS生成异常：${e.message}", onError)
            } finally {
                // UI状态标记移除
                _isGeneratingTts.value = _isGeneratingTts.value - messageId
            }
        }
    }

    private fun completeWithSuccess(
        key: String,
        messageId: String,
        url: String,
        directSuccess: (String) -> Unit,
    ) {
        val callbacks = synchronized(inFlight) { inFlight.remove(key) ?: emptyList() }
        if (callbacks.isEmpty()) return directSuccess(url)
        callbacks.forEach { it(Result.success(url)) }
    }

    private fun completeWithError(
        key: String,
        messageId: String,
        errorMsg: String,
        directError: (String) -> Unit,
    ) {
        // 检查是否为取消操作，如果是则不显示错误toast
        if (
            errorMsg.contains("cancelled", ignoreCase = true) ||
                errorMsg.contains("cancel", ignoreCase = true)
        ) {
            LogUtils.d("音频LOG测试 TTS生成被取消: $messageId")
            return
        }

        val callbacks = synchronized(inFlight) { inFlight.remove(key) ?: emptyList() }
        if (callbacks.isEmpty()) return directError(errorMsg)
        callbacks.forEach { it(Result.failure(IllegalStateException(errorMsg))) }
        LogUtils.e(
            "音频LOG测试 TTS complete error, dispatched to ${callbacks.size} callbacks for key=$key : $errorMsg"
        )
    }

    /** 检查是否正在生成指定消息的TTS */
    fun isGeneratingForMessage(messageId: String): Boolean {
        return _isGeneratingTts.value.contains(messageId)
    }

    /** 取消指定消息的TTS生成 */
    fun cancelGeneration(messageId: String) {
        _isGeneratingTts.value = _isGeneratingTts.value - messageId
    }

    /** 取消所有TTS生成 */
    fun cancelAllGenerations() {
        _isGeneratingTts.value = emptySet()
    }
}
