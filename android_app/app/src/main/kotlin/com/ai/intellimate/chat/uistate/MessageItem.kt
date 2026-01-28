package com.ai.intellimate.chat.uistate

import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.chat.local.db.ChatMessageEntity

sealed class MessageItem {
    data object Intro: MessageItem()
    data object Opening: MessageItem()
    data class CallMessages(val messages: List<MsgInfo>): MessageItem()
    data class NormalMessage(val message: MsgInfo): MessageItem()
}
