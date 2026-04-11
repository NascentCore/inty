package com.ai.intellimate.call.uistate

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.inty.voicecall.CallStatus
import com.ai.intellimate.call.VoiceCallConnectionUi

/** Ui状态 */
data class VoiceCallUiState(
    /** 网络连接状态 */
    val connectionState: VoiceCallConnectionUi = VoiceCallConnectionUi.DISCONNECTED,
    /** 通话状态 */
    val callState: CallStatus? = null,
    /** 静音 */
    val isMuted: Boolean = false,
    val agent: AgentInfo? = null,
    val time: Time? = null,
) {
    data class Time(val duration: Long = 0, val remaining: Long = 0)
}
