package ai.sxwl.android.data.store

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

    /** 更新Keep Talking按钮显示状态 */
    fun updateShowKeepTalking(enabled: Boolean) {
        IntySetting.setShowKeepTalking(enabled)
        _showKeepTalkingFlow.value = enabled
    }

    /** 更新自动播放语音消息状态 */
    fun updateAutoPlayAudio(enabled: Boolean) {
        IntySetting.setAutoPlayAudio(enabled)
        _autoPlayAudioFlow.value = enabled
    }
}
