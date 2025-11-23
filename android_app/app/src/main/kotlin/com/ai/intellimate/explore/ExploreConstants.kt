package com.ai.intellimate.explore

/** Explore页面相关常量 */
object ExploreConstants {
    /** 页面大小 - 统一管理，确保启动预加载和分页逻辑一致 */
    const val PAGE_SIZE = 20

    /** 预取距离 - 提前加载下一页 设置为8，意味着当还有8个项目时就开始预加载下一页 对于20个/页，相当于在显示到第12个时就开始加载下一页 */
    const val PREFETCH_DISTANCE = 8

    /** 是否启用占位符 - 禁用占位符，提高性能 */
    const val ENABLE_PLACEHOLDERS = false

    /** 最大缓存页数 - 最大缓存3页数据 */
    const val MAX_CACHE_PAGES = 3

    /** 初始页码 */
    const val INITIAL_PAGE = 1

    /** Explore页面滚动 - 初始速度缩放，用于整体放缓或加速手势 */
    const val SCROLL_INITIAL_VELOCITY_MULTIPLIER = 0.92f

    /** Explore页面滚动 - 触发滑动的最小速度，避免轻微抖动 */
    const val SCROLL_MIN_FLING_VELOCITY = 80f

    /** Explore页面滚动 - 限制最大速度，防止 fling 过猛 */
    const val SCROLL_MAX_FLING_VELOCITY = 7500f

    /** Explore页面滚动 - 减速度因子，>1 表示更快停下，<1 表示惯性更强 */
    const val SCROLL_DECELERATION_MULTIPLIER = 1.15f

    /** Explore页面滚动 - 每次手势允许的最大即时位移 */
    const val SCROLL_DELTA_THRESHOLD = 24f
}
