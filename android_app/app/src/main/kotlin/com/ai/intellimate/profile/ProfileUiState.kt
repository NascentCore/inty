package com.ai.intellimate.profile

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.api.model.UserProfile

/** Profile 页面的 UI 状态 */
data class ProfileUiState(
    val userProfile: UserProfile = UserProfile(),
    val userCreatedAgents: List<AgentInfo> = emptyList(),
    val isLoading: Boolean = false,
    val isRefreshing: Boolean = false,
    val hasMore: Boolean = true,
    val error: String? = null,
)

