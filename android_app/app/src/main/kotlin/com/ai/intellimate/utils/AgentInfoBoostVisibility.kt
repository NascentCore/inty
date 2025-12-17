/*
 * CREATED_BY_AGENT
 */
package com.ai.intellimate.utils

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.store.IntySetting

private const val AGENT_VISIBILITY_PRIVATE = "private"

/**
 * 判断该角色是否为“当前用户创建的私有角色”。
 *
 * 业务含义：
 * - 仅当角色 visibility 为 private 且 creator.id 等于当前登录用户 id 时，视为用户自建私有角色。
 * - 该类角色不应展示 Boost 相关功能（应援入口、弹窗、榜单跳转等）。
 */
fun AgentInfo.isUserCreatedPrivateRole(): Boolean {
    val currentUserId = IntySetting.getCurUserID()
    if (currentUserId.isBlank()) return false

    val isPrivate = visibility.equals(AGENT_VISIBILITY_PRIVATE, ignoreCase = true)
    val creatorId = creator?.id.orEmpty()
    val isCreatedByCurrentUser = creatorId.isNotBlank() && creatorId == currentUserId
    return isPrivate && isCreatedByCurrentUser
}

