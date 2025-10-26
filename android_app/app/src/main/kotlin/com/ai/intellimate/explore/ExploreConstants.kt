package com.ai.intellimate.explore

/** 探索页面相关常量 */
object ExploreConstants {
    /** 页面大小统一管理，保证启动预加载和分页逻辑一致 */
    const val PAGE_SIZE = 20

    /** 预取距离 - 提前加载下一页设置为8，意味着当还有8个项目时就开始预加载下一页，对于20个/页，相当于在显示到第12个时就开始加载下一页 */
    const val PREFETCH_DISTANCE = 8

    /** 是否启用占位符 - 取消占位符，提高性能 */
    const val ENABLE_PLACEHOLDERS = false

    /** 最大服务器页数 - 最大服务器3页数据 */
    const val MAX_CACHE_PAGES = 3

    /** 初始页码 */
    const val INITIAL_PAGE = 1
}
