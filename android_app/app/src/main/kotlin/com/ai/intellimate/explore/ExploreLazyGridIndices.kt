package com.ai.intellimate.explore

/**
 * Explore `LazyVerticalGrid` 最后一项的全局索引（含）：主题块 + Paging 角色 + 加载区 + 底部 Spacer。
 *
 * @param pagingItemCount 为 null 时表示无 Paging（仅占位 + Spacer，共 2 项，最后一项索引为 1）。
 */
internal fun exploreLazyGridMaxItemIndex(themeItemCount: Int, pagingItemCount: Int?): Int {
    if (pagingItemCount == null) {
        return 1
    }
    return (themeItemCount + pagingItemCount + 2 - 1).coerceAtLeast(0)
}
