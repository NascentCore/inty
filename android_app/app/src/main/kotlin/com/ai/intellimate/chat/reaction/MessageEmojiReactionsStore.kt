// CREATED_BY_AGENT: GPT-5.2
package com.ai.intellimate.chat.reaction

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update


// TODO: 使用 Room Database 存储而非目前的内存数据存储。
/**
 * 消息 Emoji 反应存储，内存内保持，新的 session 会丢失掉内容。
 *
 * 使用场景：
 * - 聊天消息底部操作栏允许用户为单条消息追加多个 emoji reaction
 *
 * 设计目标：
 * - 可单元测试：不依赖 ViewModel / Repository / Firebase
 * - 行为简单明确：对同一条消息多次添加时“追加”而不是“覆盖”
 */
class MessageEmojiReactionsStore {

    /**
     * key：消息 localMsgId
     * value：该消息的 emoji reaction（按追加顺序）
     */
    private val _reactions = MutableStateFlow<Map<String, List<String>>>(emptyMap())
    val reactions: StateFlow<Map<String, List<String>>> = _reactions.asStateFlow()

    fun addReaction(localMsgId: String, emoji: String) {
        _reactions.update { current ->
            val existing = current[localMsgId].orEmpty()
            current + (localMsgId to (existing + emoji))
        }
    }
}

