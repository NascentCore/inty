package com.ai.intellimate.chat.uistate

/** 聊天列表项：索引均指向 LazyPagingItems / ItemSnapshotList 中的下标 */
sealed class MessageItem {
    data object Intro : MessageItem()

    data object Opening : MessageItem()

    /** messages：语音组内每条消息在 messages 列表中的下标 */
    data class CallMessageIndexs(val messages: List<Int>) : MessageItem()

    /** index：单条消息在 messages 列表中的下标 */
    data class MessageIndex(val index: Int) : MessageItem()
}
