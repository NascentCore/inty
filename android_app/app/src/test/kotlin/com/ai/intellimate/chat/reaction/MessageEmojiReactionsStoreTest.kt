// CREATED_BY_AGENT: GPT-5.2
package com.ai.intellimate.chat.reaction

import org.junit.Assert.assertEquals
import org.junit.Test

class MessageEmojiReactionsStoreTest {

    @Test
    fun addReaction_appendsInsteadOfOverwriting() {
        // 复现点：如果实现写成 current + (id to listOf(emoji))，会导致后一次覆盖前一次
        val store = MessageEmojiReactionsStore()
        val messageId = "msg_1"

        store.addReaction(messageId, "😀")
        store.addReaction(messageId, "😭")

        assertEquals(listOf("😀", "😭"), store.reactions.value[messageId])
    }

    @Test
    fun addReaction_keepsReactionsIsolatedBetweenMessages() {
        val store = MessageEmojiReactionsStore()

        store.addReaction("msg_1", "😀")
        store.addReaction("msg_2", "💯")
        store.addReaction("msg_1", "😍")

        assertEquals(listOf("😀", "😍"), store.reactions.value["msg_1"])
        assertEquals(listOf("💯"), store.reactions.value["msg_2"])
    }
}

