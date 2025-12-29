package com.ai.intellimate.call.uistate

import ai.sxwl.android.data.api.model.AgentInfo
import com.ai.intellimate.call.data.ConnectionState
import com.ai.intellimate.call.data.bean.CallStatus

/** Ui状态 */
data class VoiceCallUiState(
    /** 网络连接状态 */
    val connectionState: ConnectionState = ConnectionState.DISCONNECTED,
    /** 通话状态 */
    val callState: CallStatus? = null,
    /** 静音 */
    val isMuted: Boolean = true,
    val agent: AgentInfo? = null,
)
