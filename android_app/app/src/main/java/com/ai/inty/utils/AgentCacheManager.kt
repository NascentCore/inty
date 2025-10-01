package com.ai.inty.utils

import com.ai.inty.beans.AgentInfo
import com.inty.utils.log.EasyLog
import com.inty.utils.storage.IntySetting
import com.squareup.moshi.Moshi
import com.squareup.moshi.Types
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory

/** Agent缓存管理器 负责缓存推荐agents和关注agents数据 */
object AgentCacheManager {

    private const val KEY_RECOMMENDED_AGENTS = "cached_recommended_agents"
    private const val KEY_CHAT_AGENTS = "cached_chat_agents"
    private const val KEY_FOLLOWING_AGENTS = "cached_following_agents"
    private const val KEY_CACHE_TIMESTAMP = "agents_cache_timestamp"
    private const val KEY_CHAT_CACHE_TIMESTAMP = "chat_agents_cache_timestamp"
    private const val CACHE_EXPIRY_TIME = 30 * 60 * 1000L // 30分钟缓存过期时间

    private val moshi = Moshi.Builder().addLast(KotlinJsonAdapterFactory()).build()

    private val agentListType = Types.newParameterizedType(List::class.java, AgentInfo::class.java)
    private val agentListAdapter = moshi.adapter<List<AgentInfo>>(agentListType)

    /** 缓存推荐agents */
    fun cacheAgents(agents: List<AgentInfo>) {
        try {
            val agentsJson = agentListAdapter.toJson(agents)
            IntySetting.setUserProfileData(KEY_RECOMMENDED_AGENTS, agentsJson)
            IntySetting.setUserProfileData(
                KEY_CACHE_TIMESTAMP,
                System.currentTimeMillis().toString(),
            )
            EasyLog.log("AgentCacheManager - 缓存推荐agents成功: ${agents.size}个")
        } catch (e: Exception) {
            EasyLog.log("AgentCacheManager - 缓存推荐agents失败: ${e.message}", EasyLog.ERROR)
        }
    }

    /** 获取缓存的推荐agents */
    fun getCachedAgents(): List<AgentInfo> {
        return try {
            val agentsJson = IntySetting.getUserProfileData(KEY_RECOMMENDED_AGENTS)
            if (agentsJson.isNullOrEmpty()) {
                emptyList()
            } else {
                val agents = agentListAdapter.fromJson(agentsJson) ?: emptyList()
                EasyLog.log("AgentCacheManager - 获取缓存推荐agents: ${agents.size}个")
                agents
            }
        } catch (e: Exception) {
            EasyLog.log("AgentCacheManager - 获取缓存推荐agents失败: ${e.message}", EasyLog.ERROR)
            emptyList()
        }
    }

    /** 缓存聊天agents */
    fun cacheChatAgents(agents: List<AgentInfo>) {
        try {
            val agentsJson = agentListAdapter.toJson(agents)
            IntySetting.setUserProfileData(KEY_CHAT_AGENTS, agentsJson)
            IntySetting.setUserProfileData(
                KEY_CHAT_CACHE_TIMESTAMP,
                System.currentTimeMillis().toString(),
            )
            EasyLog.log("AgentCacheManager - 缓存聊天agents成功: ${agents.size}个")
        } catch (e: Exception) {
            EasyLog.log("AgentCacheManager - 缓存聊天agents失败: ${e.message}", EasyLog.ERROR)
        }
    }

    /** 获取缓存的聊天agents */
    fun getCachedChatAgents(): List<AgentInfo> {
        return try {
            val agentsJson = IntySetting.getUserProfileData(KEY_CHAT_AGENTS)
            if (agentsJson.isNullOrEmpty()) {
                emptyList()
            } else {
                val agents = agentListAdapter.fromJson(agentsJson) ?: emptyList()
                EasyLog.log("AgentCacheManager - 获取缓存聊天agents: ${agents.size}个")
                agents
            }
        } catch (e: Exception) {
            EasyLog.log("AgentCacheManager - 获取缓存聊天agents失败: ${e.message}", EasyLog.ERROR)
            emptyList()
        }
    }

    /** 缓存关注agents */
    fun cacheFollowingAgents(agents: List<AgentInfo>) {
        try {
            val agentsJson = agentListAdapter.toJson(agents)
            IntySetting.setUserProfileData(KEY_FOLLOWING_AGENTS, agentsJson)
            EasyLog.log("AgentCacheManager - 缓存关注agents成功: ${agents.size}个")
        } catch (e: Exception) {
            EasyLog.log("AgentCacheManager - 缓存关注agents失败: ${e.message}", EasyLog.ERROR)
        }
    }

    /** 获取缓存的关注agents */
    fun getCachedFollowingAgents(): List<AgentInfo> {
        return try {
            val agentsJson = IntySetting.getUserProfileData(KEY_FOLLOWING_AGENTS)
            if (agentsJson.isNullOrEmpty()) {
                emptyList()
            } else {
                val agents = agentListAdapter.fromJson(agentsJson) ?: emptyList()
                EasyLog.log("AgentCacheManager - 获取缓存关注agents: ${agents.size}个")
                agents
            }
        } catch (e: Exception) {
            EasyLog.log("AgentCacheManager - 获取缓存关注agents失败: ${e.message}", EasyLog.ERROR)
            emptyList()
        }
    }

    /** 检查缓存是否过期 */
    fun isCacheExpired(): Boolean {
        val timestampStr = IntySetting.getUserProfileData(KEY_CACHE_TIMESTAMP)
        if (timestampStr.isNullOrEmpty()) {
            return true
        }

        return try {
            val timestamp = timestampStr.toLong()
            val currentTime = System.currentTimeMillis()
            val isExpired = (currentTime - timestamp) > CACHE_EXPIRY_TIME
            EasyLog.log("AgentCacheManager - 缓存过期检查: ${if (isExpired) "已过期" else "未过期"}")
            isExpired
        } catch (e: Exception) {
            EasyLog.log("AgentCacheManager - 检查缓存过期失败: ${e.message}", EasyLog.ERROR)
            true
        }
    }

    /** 更新单个agent的关注状态 */
    fun updateAgentFollowState(agentId: String, isFollowed: Boolean) {
        try {
            // 更新推荐agents列表中的关注状态
            val recommendedAgents = getCachedAgents().toMutableList()
            val recommendedIndex = recommendedAgents.indexOfFirst { it.id == agentId }
            if (recommendedIndex != -1) {
                recommendedAgents[recommendedIndex] =
                    recommendedAgents[recommendedIndex].copy(isFollowed = isFollowed)
                cacheAgents(recommendedAgents)
            }

            // 更新关注agents列表
            val followingAgents = getCachedFollowingAgents().toMutableList()
            if (isFollowed) {
                // 添加到关注列表
                val agent = recommendedAgents.find { it.id == agentId }
                if (agent != null && followingAgents.none { it.id == agentId }) {
                    followingAgents.add(agent.copy(isFollowed = true))
                    cacheFollowingAgents(followingAgents)
                }
            } else {
                // 从关注列表移除
                followingAgents.removeAll { it.id == agentId }
                cacheFollowingAgents(followingAgents)
            }

            EasyLog.log("AgentCacheManager - 更新agent关注状态: $agentId -> $isFollowed")
        } catch (e: Exception) {
            EasyLog.log("AgentCacheManager - 更新agent关注状态失败: ${e.message}", EasyLog.ERROR)
        }
    }

    /** 添加用户创建的agent到缓存 */
    fun addUserCreatedAgent(agent: AgentInfo) {
        try {
            val recommendedAgents = getCachedAgents().toMutableList()
            // 检查是否已存在
            val existingIndex = recommendedAgents.indexOfFirst { it.id == agent.id }
            if (existingIndex != -1) {
                recommendedAgents[existingIndex] = agent
            } else {
                recommendedAgents.add(agent)
            }
            cacheAgents(recommendedAgents)
            EasyLog.log("AgentCacheManager - 添加用户创建agent到缓存: ${agent.name}")
        } catch (e: Exception) {
            EasyLog.log("AgentCacheManager - 添加用户创建agent失败: ${e.message}", EasyLog.ERROR)
        }
    }

    /** 从缓存中删除agent */
    fun removeAgent(agentId: String) {
        try {
            // 从推荐列表移除
            val recommendedAgents = getCachedAgents().toMutableList()
            recommendedAgents.removeAll { it.id == agentId }
            cacheAgents(recommendedAgents)

            // 从关注列表移除
            val followingAgents = getCachedFollowingAgents().toMutableList()
            followingAgents.removeAll { it.id == agentId }
            cacheFollowingAgents(followingAgents)

            EasyLog.log("AgentCacheManager - 从缓存移除agent: $agentId")
        } catch (e: Exception) {
            EasyLog.log("AgentCacheManager - 从缓存移除agent失败: ${e.message}", EasyLog.ERROR)
        }
    }

    /** 清理所有缓存 */
    fun clearCache() {
        try {
            IntySetting.setUserProfileData(KEY_RECOMMENDED_AGENTS, "")
            IntySetting.setUserProfileData(KEY_CHAT_AGENTS, "")
            IntySetting.setUserProfileData(KEY_FOLLOWING_AGENTS, "")
            IntySetting.setUserProfileData(KEY_CACHE_TIMESTAMP, "")
            IntySetting.setUserProfileData(KEY_CHAT_CACHE_TIMESTAMP, "")
            EasyLog.log("AgentCacheManager - 缓存已清理")
        } catch (e: Exception) {
            EasyLog.log("AgentCacheManager - 清理缓存失败: ${e.message}", EasyLog.ERROR)
        }
    }

    /** 获取缓存统计信息 */
    fun getCacheStats(): CacheStats {
        val recommendedCount = getCachedAgents().size
        val chatCount = getCachedChatAgents().size
        val followingCount = getCachedFollowingAgents().size
        val isExpired = isCacheExpired()

        return CacheStats(
            recommendedAgentsCount = recommendedCount,
            chatAgentsCount = chatCount,
            followingAgentsCount = followingCount,
            isExpired = isExpired,
        )
    }

    /** 缓存统计信息数据类 */
    data class CacheStats(
        val recommendedAgentsCount: Int,
        val chatAgentsCount: Int,
        val followingAgentsCount: Int,
        val isExpired: Boolean,
    )
}
