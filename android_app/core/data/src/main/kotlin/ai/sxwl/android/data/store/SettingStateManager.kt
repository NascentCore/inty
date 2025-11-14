package ai.sxwl.android.data.store

import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.utils.LogUtils
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/** 全局设置状态管理器 用于在多个Compose屏幕之间同步设置状态 */
object SettingStateManager {

    // Keep Talking按钮显示状态
    private val _showKeepTalkingFlow = MutableStateFlow(IntySetting.isShowKeepTalking())
    val showKeepTalkingFlow: StateFlow<Boolean> = _showKeepTalkingFlow.asStateFlow()

    // 自动播放语音消息状态
    private val _autoPlayAudioFlow = MutableStateFlow(IntySetting.isAutoPlayAudio())
    val autoPlayAudioFlow: StateFlow<Boolean> = _autoPlayAudioFlow.asStateFlow()

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
            val hasUserSetKeepTalking = IntySetting.hasUserSetKeepTalking()
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
                LogUtils.d(
                    "SettingStateManager",
                    "从 Remote Config 初始化 Keep Talking 默认值: $keepTalkingDefault (key: ${FirebaseManager.RemoteConfigKeys.AUTO_ENABLE_KEEP_TALKING})",
                )
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
                val currentValue = IntySetting.isShowKeepTalking()
                _showKeepTalkingFlow.value = currentValue
                LogUtils.d("SettingStateManager", "用户已设置过 Keep Talking，使用用户设置: $currentValue")
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
                LogUtils.d(
                    "SettingStateManager",
                    "从 Remote Config 初始化 Auto Play Opening Voice 默认值: $autoPlayVoiceDefault (key: ${FirebaseManager.RemoteConfigKeys.AUTO_PLAY_OPENING_VOICE})",
                )
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
                val currentValue = IntySetting.isAutoPlayAudio()
                _autoPlayAudioFlow.value = currentValue
                LogUtils.d(
                    "SettingStateManager",
                    "用户已设置过 Auto Play Opening Voice，使用用户设置: $currentValue",
                )
            }

            initialized = true
        } catch (e: Exception) {
            LogUtils.e("SettingStateManager", "从 Remote Config 初始化失败: ${e.message}", e)
            // 初始化失败时，使用本地存储的当前值（如果有）或默认值
            _showKeepTalkingFlow.value = IntySetting.isShowKeepTalking()
            _autoPlayAudioFlow.value = IntySetting.isAutoPlayAudio()
        }
    }

    /** 更新Keep Talking按钮显示状态 */
    fun updateShowKeepTalking(enabled: Boolean) {
        IntySetting.setShowKeepTalking(enabled)
        IntySetting.markUserSetKeepTalking()
        _showKeepTalkingFlow.value = enabled
    }

    /** 更新自动播放语音消息状态 */
    fun updateAutoPlayAudio(enabled: Boolean) {
        IntySetting.setAutoPlayAudio(enabled)
        IntySetting.markUserSetAutoPlayVoice()
        _autoPlayAudioFlow.value = enabled
    }
}
