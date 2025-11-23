package com.ai.intellimate.explore

/** Explore页面相关常量 */
object ExploreConstants {
    /** 页面大小 - 统一管理，确保启动预加载和分页逻辑一致 */
    const val PAGE_SIZE = 8

    const val PREFETCH_DISTANCE = 4

    const val ENABLE_PLACEHOLDERS = false

    // 缓存至多 800 个角色，从而让用户回滚时不需要重新加载数据。
    const val MAX_CACHE_PAGES = 100

    /** 初始页码 */
    const val INITIAL_PAGE = 1

    /** Explore页面滚动 - 初始速度缩放，用于整体放缓或加速手势 */
    const val SCROLL_INITIAL_VELOCITY_MULTIPLIER = 0.6f

    /** Explore页面滚动 - 触发滑动的最小速度，避免轻微抖动 */
    const val SCROLL_MIN_FLING_VELOCITY = 80f

    /** Explore页面滚动 - 限制最大速度，防止 fling 过猛 */
    const val SCROLL_MAX_FLING_VELOCITY = 12000f

    /** Explore页面滚动 - 减速度因子，>1 表示更快停下，<1 表示惯性更强 */
    const val SCROLL_DECELERATION_MULTIPLIER = 1.5f

    /** Explore页面滚动 - 每次手势允许的最大即时位移 */
    const val SCROLL_DELTA_THRESHOLD = 216f
}
