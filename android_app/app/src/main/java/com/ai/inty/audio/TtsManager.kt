package com.ai.inty.audio

import android.content.Context
import com.ai.inty.base.ToastUtils
import com.ai.inty.net.IChatApi
import com.ai.inty.netapi.BusinessErrorCodes
import com.architecture.httplib.core.HttpResult
import com.inty.utils.log.EasyLog
import com.therouter.TheRouter
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
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
    private val chatApi by lazy {
        EasyLog.log("音频LOG测试 Getting IChatApi from TheRouter")
        val api = TheRouter.get(IChatApi::class.java)
        if (api == null) {
            EasyLog.log("音频LOG测试 IChatApi not found in TheRouter", EasyLog.ERROR)
            throw IllegalStateException("IChatApi not found in TheRouter")
        }
        EasyLog.log("音频LOG测试 IChatApi obtained successfully")
        api
    }

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
        EasyLog.log(
            "音频LOG测试 TtsManager.generateMessageVoice called: messageId=$messageId, agentId=$agentId, forceRegenerate=$forceRegenerate"
        )
        EasyLog.log("音频LOG测试 Current generating TTS messages: ${_isGeneratingTts.value}")
        EasyLog.log("音频LOG测试 TtsManager ioScope isActive=${ioScope.isActive}")

        // 检查是否正在生成（除非强制重新生成）
        if (!forceRegenerate && _isGeneratingTts.value.contains(messageId)) {
            EasyLog.log("音频LOG测试 TTS already generating for message: $messageId")
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
                EasyLog.log("音频LOG测试 TTS request deduped: $dedupKey, pendingCallbacks=${list.size}")
                return
            }
        }

        // 添加到生成队列（用于UI状态）
        _isGeneratingTts.value = _isGeneratingTts.value + messageId

        ioScope.launch {
            try {
                EasyLog.log("音频LOG测试 Generating TTS for message: $messageId, agent: $agentId")
                EasyLog.log("音频LOG测试 About to call chatApi.fetchMsgVoice")
                EasyLog.log(
                    "音频LOG测试 Request URL will be: /api/v1/chats/agents/$agentId/messages/$messageId/voice"
                )

                if (agentId.isEmpty() || messageId.isEmpty()) {
                    EasyLog.log(
                        "音频LOG测试 TTS generation failed: agentId='$agentId', messageId='$messageId'",
                        EasyLog.ERROR,
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
                    EasyLog.log(
                        "音频LOG测试 TTS generation failed: Invalid ID format - agentId='$agentId', messageId='$messageId'",
                        EasyLog.ERROR,
                    )
                    completeWithError(dedupKey, messageId, "TTS生成失败：ID格式无效", onError)
                    return@launch
                }
                val response = withTimeout(30_000) { chatApi.fetchMsgVoice(agentId, messageId) }
                EasyLog.log("音频LOG测试 fetchMsgVoice response received: $response")

                when (response) {
                    is HttpResult.Success -> {
                        if (response.data.code == BusinessErrorCodes.VOICE_TTS_LIMIT_CODE) {
                            // 音频生成到达次数限制，需要给用户toast提示文案
                            ToastUtils.showToast("${response.data.message}")
                            EasyLog.log("音频LOG测试 TTS 生成次数到达限制 (Agent: $agentId)", EasyLog.ERROR)
                            completeWithError(
                                dedupKey,
                                messageId,
                                "${response.data.message}",
                                onError,
                            )
                        } else {
                            val audioUrl = response.data.data?.audio_url
                            if (audioUrl != null && audioUrl.isNotEmpty()) {
                                EasyLog.log(
                                    "音频LOG测试 TTS generated successfully: $audioUrl (Agent: $agentId)"
                                )
                                completeWithSuccess(dedupKey, messageId, audioUrl, onSuccess)
                            } else {
                                EasyLog.log(
                                    "音频LOG测试 TTS generation returned empty audio_url (Agent: $agentId)",
                                    EasyLog.ERROR,
                                )
                                completeWithError(dedupKey, messageId, "TTS生成失败：返回空音频URL", onError)
                            }
                        }
                    }

                    is HttpResult.Failure -> {
                        EasyLog.log(
                            "音频LOG测试 TTS generation failed: ${response.message} (Agent: $agentId)",
                            EasyLog.ERROR,
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
                EasyLog.log(
                    "音频LOG测试 TTS generation exception: ${e.message} (Agent: $agentId)",
                    EasyLog.ERROR,
                )
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
        EasyLog.log(
            "音频LOG测试 TTS complete success, dispatched to ${callbacks.size} callbacks for key=$key"
        )
    }

    private fun completeWithError(
        key: String,
        messageId: String,
        errorMsg: String,
        directError: (String) -> Unit,
    ) {
        val callbacks = synchronized(inFlight) { inFlight.remove(key) ?: emptyList() }
        if (callbacks.isEmpty()) return directError(errorMsg)
        callbacks.forEach { it(Result.failure(IllegalStateException(errorMsg))) }
        EasyLog.log(
            "音频LOG测试 TTS complete error, dispatched to ${callbacks.size} callbacks for key=$key : $errorMsg",
            EasyLog.ERROR,
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
