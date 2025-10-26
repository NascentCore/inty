package com.ai.intellimate.chat.constants

/** 聊天页面相关常量 */
object ChatConstants {
    /** 页面大小 - 与Explore保持一致，确保数据加载逻辑统一 */
    const val PAGE_SIZE = 20

    /** 预取距离 - 提前加载下一页设置为8，意味着当还有8个项目时就开始预加载下一页，对于20个/页，相当于在显示到第12个时就开始加载下一页 */
    const val PREFETCH_DISTANCE = 8

    /** 是否启用占位符 - 取消占位符，提高性能 */
    const val ENABLE_PLACEHOLDERS = false

    /** 初始页码 */
    const val INITIAL_PAGE = 1

    /** ChatAgents服务器键外部 */
    const val CHAT_AGENTS_CACHE_PREFIX = "chat_agents_"

    /** 预加载的ChatAgents数量（启动时） */
    const val PRELOAD_CHAT_AGENTS_COUNT = 20
}
