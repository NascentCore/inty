package ai.sxwl.android.data.store

import ai.sxwl.android.data.billing.VipStatusHelper
import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.utils.LogUtils
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.runBlocking

/** 全局设置状态管理器 用于在多个Compose屏幕之间同步设置状态 */
object SettingStateManager {

    const val CHAT_FONT_SIZE_MIN_SP = 12f
    const val CHAT_FONT_SIZE_MAX_SP = 20f
    const val CHAT_FONT_SIZE_DEFAULT_SP = 14f

    // Keep Talking按钮显示状态
    private val _showKeepTalkingFlow = MutableStateFlow(IntySetting.isShowKeepTalking())
    val showKeepTalkingFlow: Flow<Boolean> =
        _showKeepTalkingFlow.combine(VipStatusHelper.vipStatus) { isShow, vipStatus ->
            isShow && vipStatus.isSubscribed
        }

    // 自动播放语音消息状态
    private val _autoPlayAudioFlow = MutableStateFlow(IntySetting.isAutoPlayAudio())
    val autoPlayAudioFlow: Flow<Boolean> =
        _autoPlayAudioFlow.combine(VipStatusHelper.vipStatus) { autoPlay, vipStatus ->
            autoPlay && vipStatus.isSubscribed
        }

    // 自动播放背景动画状态
    private val _autoPlayAnimationFlow = MutableStateFlow(IntySetting.isAutoPlayAnimation())
    val autoPlayAnimationFlow: StateFlow<Boolean> = _autoPlayAnimationFlow.asStateFlow()

    private val _textStreamingFlow = MutableStateFlow(IntySetting.isTextStreaming())
    val textStreaming = _textStreamingFlow.asStateFlow()

    // 显示场景动作输入按钮状态
    private val _showSceneActionButtonFlow = MutableStateFlow(IntySetting.isShowSceneActionButton())
    val showSceneActionButtonFlow: StateFlow<Boolean> = _showSceneActionButtonFlow.asStateFlow()

    // 是否发送 UX/UI 手势信号（背景点击/滑动）
    private val _sendUxUiGestureSignalsFlow =
        MutableStateFlow(IntySetting.isSendUxUiGestureSignals())
    val sendUxUiGestureSignalsFlow: StateFlow<Boolean> = _sendUxUiGestureSignalsFlow.asStateFlow()

    private val settingScope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    val keyboardHeight: StateFlow<Float> =
        IntySetting.keyboardHeightFlow().stateIn(settingScope, SharingStarted.Eagerly, 0f)

    // 聊天字体大小设置
    private val _chatFontSizeFlow =
        MutableStateFlow(
            IntySetting.getChatFontSizeSp().coerceIn(CHAT_FONT_SIZE_MIN_SP, CHAT_FONT_SIZE_MAX_SP)
        )
    val chatFontSizeFlow: StateFlow<Float> = _chatFontSizeFlow.asStateFlow()

    // 聊天模型选择（全局设置）
    private val _chatModelIdFlow = MutableStateFlow(IntySetting.getChatModelId())
    val chatModelIdFlow: StateFlow<String> = _chatModelIdFlow.asStateFlow()

    // 消息列表是否全屏状态
    private val _chatListFullScreenFlow = MutableStateFlow(IntySetting.isChatListFullScreen())
    val chatListFullScreenFlow: StateFlow<Boolean> = _chatListFullScreenFlow.asStateFlow()

    // 标记是否已经初始化过（避免重复初始化）
    @Volatile private var initialized = false

    /**
     * 从 Remote Config 初始化默认值 只在用户未手动设置过的情况下使用 Remote Config 的值 如果 Remote Config 未读取到，使用本地默认值（false
     * 和 true）
     */
    fun initializeFromRemoteConfig() {
        // 避免重复初始化
        if (initialized) {
            return
        }

        try {
            // 检查用户是否已经手动设置过 Keep Talking
            val hasUserSetKeepTalking = runBlocking { IntySetting.hasUserSetKeepTalking() }
            if (!hasUserSetKeepTalking) {
                // 从 Remote Config 读取默认值
                val keepTalkingDefault =
                    FirebaseManager.getRemoteConfigBoolean(
                        FirebaseManager.RemoteConfigKeys.AUTO_ENABLE_KEEP_TALKING
                    )
                // 如果 Remote Config 返回 false（默认值），说明可能未配置，使用本地默认值 false
                // 但这里我们直接使用 Remote Config 的值，因为已经在 setRemoteConfigDefaults 中设置了默认值
                IntySetting.setShowKeepTalking(keepTalkingDefault)
                _showKeepTalkingFlow.value = keepTalkingDefault
                // 记录 Remote Config 分配的值到 Firebase Analytics（用于验证随机百分比配置）
                FirebaseManager.logEvent(
                    "remote_config_applied",
                    FirebaseManager.safeEventParams(
                        "config_key" to FirebaseManager.RemoteConfigKeys.AUTO_ENABLE_KEEP_TALKING,
                        "config_value" to keepTalkingDefault.toString(),
                        "source" to "remote_config",
                    ),
                )
            } else {
                // 用户已设置过，使用用户设置的值
                _showKeepTalkingFlow.value = IntySetting.isShowKeepTalking()
            }

            // 检查用户是否已经手动设置过 Auto Play Opening Voice
            val hasUserSetAutoPlayVoice = IntySetting.hasUserSetAutoPlayVoice()
            if (!hasUserSetAutoPlayVoice) {
                // 从 Remote Config 读取默认值
                val autoPlayVoiceDefault =
                    FirebaseManager.getRemoteConfigBoolean(
                        FirebaseManager.RemoteConfigKeys.AUTO_PLAY_OPENING_VOICE
                    )
                // 如果 Remote Config 返回 false（默认值），说明可能未配置，使用本地默认值 true
                // 但这里我们直接使用 Remote Config 的值，因为已经在 setRemoteConfigDefaults 中设置了默认值
                IntySetting.setAutoPlayAudio(autoPlayVoiceDefault)
                _autoPlayAudioFlow.value = autoPlayVoiceDefault
                // 记录 Remote Config 分配的值到 Firebase Analytics（用于验证随机百分比配置）
                FirebaseManager.logEvent(
                    "remote_config_applied",
                    FirebaseManager.safeEventParams(
                        "config_key" to FirebaseManager.RemoteConfigKeys.AUTO_PLAY_OPENING_VOICE,
                        "config_value" to autoPlayVoiceDefault.toString(),
                        "source" to "remote_config",
                    ),
                )
            } else {
                // 用户已设置过，使用用户设置的值
                _autoPlayAudioFlow.value = IntySetting.isAutoPlayAudio()
            }

            // 自动播放背景动画暂不依赖 Remote Config，直接使用本地存储值
            _autoPlayAnimationFlow.value = IntySetting.isAutoPlayAnimation()

            initialized = true
        } catch (e: Exception) {
            LogUtils.e("SettingStateManager", "从 Remote Config 初始化失败: ${e.message}", e)
            // 初始化失败时，使用本地存储的当前值（如果有）或默认值
            _showKeepTalkingFlow.value = IntySetting.isShowKeepTalking()
            _autoPlayAudioFlow.value = IntySetting.isAutoPlayAudio()
            _autoPlayAnimationFlow.value = IntySetting.isAutoPlayAnimation()
        }
    }

    suspend fun setKeyboardHeight(height: Float) {
        IntySetting.setKeyboardHeight(height)
    }

    /** 更新Keep Talking按钮显示状态 */
    suspend fun updateShowKeepTalking(enabled: Boolean) {
        IntySetting.setShowKeepTalking(enabled)
        IntySetting.markUserSetKeepTalking()
        _showKeepTalkingFlow.value = enabled
    }

    /** 更新自动播放语音消息状态 */
    suspend fun updateAutoPlayAudio(enabled: Boolean) {
        IntySetting.setAutoPlayAudio(enabled)
        IntySetting.markUserSetAutoPlayVoice()
        _autoPlayAudioFlow.value = enabled
    }

    /** 更新自动播放背景动画状态 */
    fun updateAutoPlayAnimation(enabled: Boolean) {
        IntySetting.setAutoPlayAnimation(enabled)
        IntySetting.markUserSetAutoPlayAnimation()
        _autoPlayAnimationFlow.value = enabled
    }

    fun updateTextStreaming(enabled: Boolean) {
        IntySetting.setTextStreaming(enabled)
        IntySetting.markUserTextStreaming()
        _textStreamingFlow.value = enabled
    }

    /** 更新显示场景动作输入按钮状态 */
    suspend fun updateShowSceneActionButton(enabled: Boolean) {
        IntySetting.setShowSceneActionButton(enabled)
        IntySetting.markUserSetSceneActionButton()
        _showSceneActionButtonFlow.value = enabled
    }

    fun updateSendUxUiGestureSignals(enabled: Boolean) {
        IntySetting.setSendUxUiGestureSignals(enabled)
        _sendUxUiGestureSignalsFlow.value = enabled
    }

    /** 更新聊天消息字体大小（sp） */
    fun updateChatFontSize(fontSizeSp: Float) {
        val clamped = fontSizeSp.coerceIn(CHAT_FONT_SIZE_MIN_SP, CHAT_FONT_SIZE_MAX_SP)
        IntySetting.setChatFontSizeSp(clamped)
        _chatFontSizeFlow.value = clamped
    }

    /** 更新聊天模型 */
    fun updateChatModelId(modelId: String) {
        IntySetting.setChatModelId(modelId)
        _chatModelIdFlow.value = modelId
    }

    /** 更新消息列表是否全屏状态 */
    fun updateChatListFullScreen(fullScreen: Boolean) {
        IntySetting.setChatListFullScreen(fullScreen)
        _chatListFullScreenFlow.value = fullScreen
    }
}
