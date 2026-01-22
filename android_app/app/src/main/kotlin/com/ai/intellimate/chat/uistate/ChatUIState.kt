package com.ai.intellimate.chat.uistate

data class ChatUIState(val vipAgentLockType: VipAgentLockType = VipAgentLockType.NONE) {
    enum class VipAgentLockType {
        DIALOG,
        INPUT,
        NONE,
    }
}
