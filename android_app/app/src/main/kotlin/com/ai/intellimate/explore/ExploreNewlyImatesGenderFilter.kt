package com.ai.intellimate.explore

import ai.sxwl.android.data.api.model.AgentInfo
import java.util.Locale

private const val GENDER_MALE = "MALE"
private const val GENDER_FEMALE = "FEMALE"

/**
 * 为 Explore 顶部 Newly iMates 分区执行性别过滤：
 * - 用户为 MALE/FEMALE：仅保留异性 iMate
 * - 用户为 OTHER/NON_BINARY/未知：保持现有逻辑，不做性别过滤
 */
internal fun filterNewlyCreatedAgentsByUserGender(
    agents: List<AgentInfo>,
    userGender: String?,
): List<AgentInfo> {
    val oppositeGender = getOppositeGenderForExplore(userGender) ?: return agents
    return agents.filter { normalizeGenderForExplore(it.gender) == oppositeGender }
}

internal fun shouldUseOppositeGenderFilter(userGender: String?): Boolean {
    return getOppositeGenderForExplore(userGender) != null
}

private fun getOppositeGenderForExplore(userGender: String?): String? {
    return when (normalizeGenderForExplore(userGender)) {
        GENDER_MALE -> GENDER_FEMALE
        GENDER_FEMALE -> GENDER_MALE
        else -> null
    }
}

private fun normalizeGenderForExplore(rawGender: String?): String? {
    if (rawGender.isNullOrBlank()) return null
    return rawGender.trim().replace('-', '_').uppercase(Locale.ROOT)
}
