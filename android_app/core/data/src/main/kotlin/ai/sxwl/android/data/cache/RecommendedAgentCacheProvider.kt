package ai.sxwl.android.data.cache

import ai.sxwl.android.data.api.model.AgentInfo

/** 推荐Agent缓存提供者接口 定义在core/data模块中，由app模块实现 解决跨模块依赖问题 */
interface RecommendedAgentCacheProvider {

    /**
     * 获取缓存的推荐agents
     *
     * @return 缓存的agents列表
     */
    suspend fun getCachedRecommendedAgents(): List<AgentInfo>

    /**
     * 缓存推荐agents
     *
     * @param agents 要缓存的agents列表
     */
    suspend fun cacheRecommendedAgents(agents: List<AgentInfo>)

    /**
     * 检查是否需要从网络更新
     *
     * @return true如果需要更新，false如果使用缓存即可
     */
    suspend fun shouldUpdateFromNetwork(): Boolean

    /** 刷新推荐agents缓存 */
    suspend fun refreshRecommendedAgents()
}
