package com.ai.intellimate.explore

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.api.model.CharacterThemeItem

internal const val NEWLY_IMATES_THEME_ID = "newly_imates"
private const val NEWLY_IMATES_MAX_COUNT = 10

internal data class ExploreThemeSectionItem(
    val id: String,
    val name: String,
    val description: String,
    val agents: List<AgentInfo>,
    val isChristmas: Boolean,
)

internal fun CharacterThemeItem.flattenAgents(): List<AgentInfo> {
    return agents.sortedBy { it.orderIndex }.mapNotNull { it.agent }
}

internal fun CharacterThemeItem.isChristmasTheme(): Boolean {
    val loweredName = name.lowercase()
    val loweredDescription = description.lowercase()
    return loweredName.contains("christmas") ||
        loweredName.contains("圣诞") ||
        loweredDescription.contains("christmas") ||
        loweredDescription.contains("圣诞")
}

/**
 * 组合 Explore 主题区块列表：
 * - 当“最近创建角色”有数据时，在列表首位插入 Newly iMates 横向区块
 * - Newly iMates 最多展示 10 个角色
 */
internal fun buildExploreThemeSections(
    characterThemes: List<CharacterThemeItem>,
    newlyCreatedAgents: List<AgentInfo>,
    newlyImatesTitle: String,
    newlyImatesSubtitle: String,
): List<ExploreThemeSectionItem> {
    val remoteThemeSections =
        characterThemes
            .map { theme ->
                ExploreThemeSectionItem(
                    id = theme.id,
                    name = theme.name,
                    description = theme.description,
                    agents = theme.flattenAgents(),
                    isChristmas = theme.isChristmasTheme(),
                )
            }.filter { it.agents.isNotEmpty() }

    if (newlyCreatedAgents.isEmpty()) return remoteThemeSections
    val latestAgents = newlyCreatedAgents.take(NEWLY_IMATES_MAX_COUNT)
    if (latestAgents.isEmpty()) return remoteThemeSections

    val newlyImatesSection =
        ExploreThemeSectionItem(
            id = NEWLY_IMATES_THEME_ID,
            name = newlyImatesTitle,
            description = newlyImatesSubtitle,
            agents = latestAgents,
            isChristmas = false,
        )

    return buildList(capacity = remoteThemeSections.size + 1) {
        add(newlyImatesSection)
        addAll(remoteThemeSections)
    }
}

internal fun getExploreThemeClickSource(themeId: String): String {
    return if (themeId == NEWLY_IMATES_THEME_ID) "newly_imates" else "theme"
}
