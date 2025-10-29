package com.ai.intellimate.utils

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.cache.RecommendedAgentCacheProvider
import ai.sxwl.android.data.store.IntySetting

/**
 * 推荐Agent缓存提供者实现
 * 在app模块中实现core/data模块定义的接口
 * 解决跨模块依赖问题
 */
class RecommendedAgentCacheProviderImpl : RecommendedAgentCacheProvider {

    override suspend fun getCachedRecommendedAgents(): List<AgentInfo> {
        return AgentCacheManager.getCachedAgents()
    }

    override suspend fun cacheRecommendedAgents(agents: List<AgentInfo>) {
        AgentCacheManager.cacheAgents(agents)
    }

    override suspend fun shouldUpdateFromNetwork(): Boolean {
        // 检查缓存是否过期
        if (AgentCacheManager.isCacheExpired()) {
            return true
        }

        // 检查是否有缓存数据
        val cachedAgents = AgentCacheManager.getCachedAgents()
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

    override suspend fun refreshRecommendedAgents() {
        // 触发UnifiedStartupManager刷新
        UnifiedStartupManager.refreshRecommendedAgents()
    }
}
