package com.ai.inty.audio

import android.content.Context
import com.ai.inty.net.IChatApi
import com.architecture.httplib.core.HttpResult
import com.inty.utils.log.EasyLog
import com.therouter.TheRouter
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * TTS管理器
 * 专门处理文本转语音的生成和管理
 */
class TtsManager private constructor(
    private val context: Context,
    private val scope: CoroutineScope
) {

    companion object {
        @Volatile
        private var INSTANCE: TtsManager? = null

        fun getInstance(context: Context, scope: CoroutineScope): TtsManager {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: TtsManager(context.applicationContext, scope).also { INSTANCE = it }
            }
        }
    }

    // TTS生成状态
    private val _isGeneratingTts = MutableStateFlow<Set<String>>(emptySet())
    val isGeneratingTts: StateFlow<Set<String>> = _isGeneratingTts.asStateFlow()

    // 延迟获取API依赖
    private val chatApi by lazy {
        TheRouter.get(IChatApi::class.java)
            ?: throw IllegalStateException("IChatApi not found in TheRouter")
    }

    /**
     * 生成消息语音
     * @param messageId 消息ID
     * @param agentId Agent ID
     * @param onSuccess 成功回调，返回生成的音频URL
     * @param onError 失败回调
     */
    fun generateMessageVoice(
        messageId: String,
        agentId: String,
        onSuccess: (String) -> Unit,
        onError: (String) -> Unit
    ) {
        // 检查是否正在生成
        if (_isGeneratingTts.value.contains(messageId)) {
            EasyLog.log("音频LOG测试 TTS already generating for message: $messageId")
            return
        }

        // 添加到生成队列
        _isGeneratingTts.value = _isGeneratingTts.value + messageId

        scope.launch(Dispatchers.IO) {
            try {
                EasyLog.log("音频LOG测试 Generating TTS for message: $messageId, agent: $agentId")

                val response = chatApi.fetchMsgVoice(agentId, messageId)

                when (response) {
                    is HttpResult.Success -> {
                        val audioUrl = response.data.audio_url
                        if (audioUrl != null && audioUrl.isNotEmpty()) {
                            EasyLog.log("音频LOG测试 TTS generated successfully: $audioUrl")
                            onSuccess(audioUrl)
                        } else {
                            EasyLog.log("音频LOG测试 TTS generation returned empty audio_url", EasyLog.ERROR)
                            onError("TTS生成失败：返回空音频URL")
                        }
                    }

                    is HttpResult.Failure -> {
                        EasyLog.log("音频LOG测试 TTS generation failed: ${response.message}", EasyLog.ERROR)
                        onError("TTS生成失败：${response.message}")
                    }
                }
            } catch (e: Exception) {
                EasyLog.log("音频LOG测试 TTS generation exception: ${e.message}", EasyLog.ERROR)
                onError("TTS生成异常：${e.message}")
            } finally {
                // 从生成队列中移除
                _isGeneratingTts.value = _isGeneratingTts.value - messageId
            }
        }
    }

    /**
     * 检查是否正在生成指定消息的TTS
     */
    fun isGeneratingForMessage(messageId: String): Boolean {
        return _isGeneratingTts.value.contains(messageId)
    }

    /**
     * 取消指定消息的TTS生成
     */
    fun cancelGeneration(messageId: String) {
        _isGeneratingTts.value = _isGeneratingTts.value - messageId
    }

    /**
     * 取消所有TTS生成
     */
    fun cancelAllGenerations() {
        _isGeneratingTts.value = emptySet()
    }
}
