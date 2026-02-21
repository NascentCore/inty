package com.ai.intellimate.explore

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.http.services.AgentService

internal const val NEWLY_IMATES_THEME_ID = "newly_imates"
private const val NEWLY_IMATES_MAX_COUNT = 10

/**
 * 组合 Explore 主题区块列表：
 * - 当“最近创建角色”有数据时，在列表首位插入 Newly iMates 横向区块
 * - Newly iMates 最多展示 10 个角色
 */
internal fun buildExploreThemeSections(
    characterThemes: List<AgentService.CharacterThemeItem>,
    newlyCreatedAgents: List<AgentInfo>,
    newlyImatesTitle: String,
    newlyImatesSubtitle: String,
): List<AgentService.CharacterThemeItem> {
    if (newlyCreatedAgents.isEmpty()) {
        return characterThemes
    }

    val latestAgents = newlyCreatedAgents.take(NEWLY_IMATES_MAX_COUNT)
    if (latestAgents.isEmpty()) {
        return characterThemes
    }

    val newlyImatesSection =
        AgentService.CharacterThemeItem(
            id = NEWLY_IMATES_THEME_ID,
            name = newlyImatesTitle,
            description = newlyImatesSubtitle,
            agents = latestAgents,
        )

    return buildList(capacity = characterThemes.size + 1) {
        add(newlyImatesSection)
        addAll(characterThemes)
    }
}

internal fun getExploreThemeClickSource(themeId: String): String {
    return if (themeId == NEWLY_IMATES_THEME_ID) "newly_imates" else "theme"
}
