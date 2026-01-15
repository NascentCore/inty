package ai.sxwl.android.data.chat

// CREATED_BY_AGENT

import ai.sxwl.android.data.chat.local.db.IntyChatDatabase

/**
 * 为上层模块提供“按 agent 统计本地消息条数”的能力。
 *
 * 注意：不要在对外 API 里暴露 Room 相关类型，避免上层模块需要 room-runtime 出现在编译 classpath。
 */
object ChatMessageCountStore {

    suspend fun getMessageCounts(agentIds: List<String>): Map<String, Int> {
        val distinctIds = agentIds.filter { it.isNotBlank() }.distinct()
        if (distinctIds.isEmpty()) return emptyMap()

        val dao = IntyChatDatabase.getInstance().chatMessageDao()
        val countsByAgentId = dao.getMessageCounts(distinctIds).associate { it.agentId to it.messageCount }
        return distinctIds.associateWith { countsByAgentId[it] ?: 0 }
    }
}

