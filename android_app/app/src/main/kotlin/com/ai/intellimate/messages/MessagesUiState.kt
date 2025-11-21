package com.ai.intellimate.messages

import ai.sxwl.android.data.api.model.ConversationItem

/** Messages页面的UI状态 */
data class MessagesUiState(
    val conversations: List<ConversationItem> = emptyList(),
    val isLoading: Boolean = false,
    val isRefreshing: Boolean = false,
    val hasMore: Boolean = true,
    val error: String? = null,
    val intelliMateAgentIds: Set<String> = emptySet(), // 标记哪些 agent 是 IntelliMate（需要置顶且不可长按）
)
