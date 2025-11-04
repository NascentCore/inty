package com.ai.intellimate.messages

import ai.sxwl.android.data.api.model.ConversationItem

/** Messages页面的UI状态 */
data class MessagesUiState(
    val conversations: List<ConversationItem> = emptyList(),
    val isLoading: Boolean = false,
    val isRefreshing: Boolean = false,
    val hasMore: Boolean = true,
    val error: String? = null
)
