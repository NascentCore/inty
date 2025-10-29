package ai.sxwl.android.data.cache

import ai.sxwl.android.data.api.model.AgentInfo

/**
 * Agent缓存提供者接口
 * 定义在core/data模块中，由app模块实现
 * 解决跨模块依赖问题
 */
interface AgentCacheProvider {

    /**
     * 获取缓存的聊天agents
     * @return 缓存的agents列表
     */
    suspend fun getCachedChatAgents(): List<AgentInfo>

    /**
     * 缓存聊天agents
     * @param agents 要缓存的agents列表
     */
    suspend fun cacheChatAgents(agents: List<AgentInfo>)

    /**
     * 检查是否需要从网络更新
     * @return true如果需要更新，false如果使用缓存即可
     */
    suspend fun shouldUpdateFromNetwork(): Boolean

    /**
     * 刷新聊天agents缓存
     */
    suspend fun refreshChatAgents()
}
