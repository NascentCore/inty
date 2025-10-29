package com.ai.intellimate.utils

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.cache.AgentCacheProvider
import ai.sxwl.android.data.store.IntySetting

/** Agent缓存提供者实现 在app模块中实现core/data模块定义的接口 解决跨模块依赖问题 */
class AgentCacheProviderImpl : AgentCacheProvider {

    override suspend fun getCachedChatAgents(): List<AgentInfo> {
        return AgentCacheManager.getCachedChatAgents()
    }

    override suspend fun cacheChatAgents(agents: List<AgentInfo>) {
        AgentCacheManager.cacheChatAgents(agents)
    }

    override suspend fun shouldUpdateFromNetwork(): Boolean {
        // 检查缓存是否过期
        if (AgentCacheManager.isCacheExpired()) {
            return true
        }

        // 检查是否有缓存数据
        val cachedAgents = AgentCacheManager.getCachedChatAgents()
        if (cachedAgents.isEmpty()) {
            return true
        }

        // 检查用户登录状态
        if (!IntySetting.isLogin()) {
            return false
        }

        // 默认策略：缓存30分钟内不更新
        return false
    }

    override suspend fun refreshChatAgents() {
        // 触发UnifiedStartupManager刷新
        UnifiedStartupManager.refreshChatAgents()
    }
}
