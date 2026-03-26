package com.ai.intellimate.utils

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.api.model.CharacterThemeItem
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.utils.LogUtils
import com.squareup.moshi.Moshi
import com.squareup.moshi.Types
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

/** Agent缓存管理器 负责缓存推荐agents和关注agents数据 */
object AgentCacheManager {
    private val cacheScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    private const val KEY_RECOMMENDED_AGENTS = "cached_recommended_agents"
    private const val KEY_CHAT_AGENTS = "cached_chat_agents"
    private const val KEY_FOLLOWING_AGENTS = "cached_following_agents"
    private const val KEY_USER_CREATED_AGENTS = "cached_user_created_agents"
    private const val KEY_CHARACTER_THEMES = "cached_character_themes"
    private const val KEY_CACHE_TIMESTAMP = "agents_cache_timestamp"
    private const val KEY_CHAT_CACHE_TIMESTAMP = "chat_agents_cache_timestamp"
    private const val KEY_USER_CREATED_CACHE_TIMESTAMP = "user_created_agents_cache_timestamp"
    private const val KEY_CHARACTER_THEMES_CACHE_TIMESTAMP = "character_themes_cache_timestamp"
    private const val CACHE_EXPIRY_TIME = 30 * 60 * 1000L // 30分钟缓存过期时间

    private val moshi = Moshi.Builder().addLast(KotlinJsonAdapterFactory()).build()

    private val agentListType = Types.newParameterizedType(List::class.java, AgentInfo::class.java)
    private val agentListAdapter = moshi.adapter<List<AgentInfo>>(agentListType)

    private val characterThemeListType =
        Types.newParameterizedType(List::class.java, CharacterThemeItem::class.java)
    private val characterThemeListAdapter =
        moshi.adapter<List<CharacterThemeItem>>(characterThemeListType)

    private val _themeAgentCache = MutableStateFlow(emptyList<CharacterThemeItem>())
    val themeAgentCache = _themeAgentCache.asStateFlow()

    /** 缓存推荐agents */
    fun cacheAgents(agents: List<AgentInfo>) {
        try {
            val agentsJson = agentListAdapter.toJson(agents)
            IntySetting.setUserProfileData(KEY_RECOMMENDED_AGENTS, agentsJson)
            IntySetting.setUserProfileData(
                KEY_CACHE_TIMESTAMP,
                System.currentTimeMillis().toString(),
            )
            LogUtils.d("AgentCacheManager - 缓存推荐agents成功: ${agents.size}个")
        } catch (e: Exception) {
            LogUtils.e("AgentCacheManager - 缓存推荐agents失败: ${e.message}")
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
                LogUtils.d("AgentCacheManager - 获取缓存推荐agents: ${agents.size}个")
                agents
            }
        } catch (e: Exception) {
            LogUtils.e("AgentCacheManager - 获取缓存推荐agents失败: ${e.message}")
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
            LogUtils.d("AgentCacheManager - 缓存聊天agents成功: ${agents.size}个")
        } catch (e: Exception) {
            LogUtils.e("AgentCacheManager - 缓存聊天agents失败: ${e.message}")
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
                LogUtils.d("AgentCacheManager - 获取缓存聊天agents: ${agents.size}个")
                agents
            }
        } catch (e: Exception) {
            LogUtils.e("AgentCacheManager - 获取缓存聊天agents失败: ${e.message}")
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
            LogUtils.d("AgentCacheManager - 缓存过期检查: ${if (isExpired) "已过期" else "未过期"}")
            isExpired
        } catch (e: Exception) {
            LogUtils.e("AgentCacheManager - 检查缓存过期失败: ${e.message}")
            true
        }
    }

    /** 缓存用户自建的agents */
    fun cacheUserCreatedAgents(agents: List<AgentInfo>) {
        try {
            val agentsJson = agentListAdapter.toJson(agents)
            IntySetting.setUserProfileData(KEY_USER_CREATED_AGENTS, agentsJson)
            IntySetting.setUserProfileData(
                KEY_USER_CREATED_CACHE_TIMESTAMP,
                System.currentTimeMillis().toString(),
            )
            LogUtils.d("AgentCacheManager - 缓存用户自建agents成功: ${agents.size}个")
        } catch (e: Exception) {
            LogUtils.e("AgentCacheManager - 缓存用户自建agents失败: ${e.message}")
        }
    }

    /** 获取缓存的用户自建agents */
    fun getCachedUserCreatedAgents(): List<AgentInfo> {
        return try {
            val agentsJson = IntySetting.getUserProfileData(KEY_USER_CREATED_AGENTS)
            if (agentsJson.isNullOrEmpty()) {
                emptyList()
            } else {
                val agents = agentListAdapter.fromJson(agentsJson) ?: emptyList()
                LogUtils.i("AgentCacheManager - 获取缓存用户自建agents: ${agents.size}个")
                agents
            }
        } catch (e: Exception) {
            LogUtils.e("AgentCacheManager - 获取缓存用户自建agents失败: ${e.message}")
            emptyList()
        }
    }

    /** 检查用户自建agents缓存是否过期 */
    fun isUserCreatedCacheExpired(): Boolean {
        val timestampStr = IntySetting.getUserProfileData(KEY_USER_CREATED_CACHE_TIMESTAMP)
        if (timestampStr.isNullOrEmpty()) {
            return true
        }

        return try {
            val timestamp = timestampStr.toLong()
            val currentTime = System.currentTimeMillis()
            val isExpired = (currentTime - timestamp) > CACHE_EXPIRY_TIME
            LogUtils.d("AgentCacheManager - 用户自建agents缓存过期检查: ${if (isExpired) "已过期" else "未过期"}")
            isExpired
        } catch (e: Exception) {
            LogUtils.e("AgentCacheManager - 检查用户自建agents缓存过期失败: ${e.message}")
            true
        }
    }

    /** 从缓存中删除agent */
    fun removeAgent(agentId: String) {
        try {
            // 从推荐列表移除
            val recommendedAgents = getCachedAgents().toMutableList()
            recommendedAgents.removeAll { it.id == agentId }
            cacheAgents(recommendedAgents)

            // 从用户自建列表移除
            val userCreatedAgents = getCachedUserCreatedAgents().toMutableList()
            userCreatedAgents.removeAll { it.id == agentId }
            cacheUserCreatedAgents(userCreatedAgents)

            LogUtils.i("AgentCacheManager - 从缓存移除agent: $agentId")
        } catch (e: Exception) {
            LogUtils.e("AgentCacheManager - 从缓存移除agent失败: ${e.message}")
        }
    }

    /** 缓存主题专区列表 */
    fun cacheCharacterThemes(themes: List<CharacterThemeItem>) {
        try {
            val themesJson = characterThemeListAdapter.toJson(themes)
            cacheScope.launch {
                IntySetting.setUserProfileDataSuspend(KEY_CHARACTER_THEMES, themesJson)
                IntySetting.setUserProfileDataSuspend(
                    KEY_CHARACTER_THEMES_CACHE_TIMESTAMP,
                    System.currentTimeMillis().toString(),
                )
            }
            _themeAgentCache.value = themes
            LogUtils.d("AgentCacheManager - 缓存主题专区列表成功: ${themes.size}个")
        } catch (e: Exception) {
            LogUtils.e("AgentCacheManager - 缓存主题专区列表失败: ${e.message}")
        }
    }

    /** 获取缓存的主题专区列表 */
    fun getCachedCharacterThemes(): List<CharacterThemeItem> {
        return try {
            val themesJson = IntySetting.getUserProfileData(KEY_CHARACTER_THEMES)
            if (themesJson.isNullOrEmpty()) {
                emptyList()
            } else {
                val themes = characterThemeListAdapter.fromJson(themesJson) ?: emptyList()
                LogUtils.d("AgentCacheManager - 获取缓存主题专区列表: ${themes.size}个")
                themes
            }
        } catch (e: Exception) {
            LogUtils.e("AgentCacheManager - 获取缓存主题专区列表失败: ${e.message}")
            emptyList()
        }
    }

    /** 检查主题专区缓存是否过期 */
    fun isCharacterThemesCacheExpired(): Boolean {
        val timestampStr = IntySetting.getUserProfileData(KEY_CHARACTER_THEMES_CACHE_TIMESTAMP)
        if (timestampStr.isNullOrEmpty()) {
            return true
        }

        return try {
            val timestamp = timestampStr.toLong()
            val currentTime = System.currentTimeMillis()
            val isExpired = (currentTime - timestamp) > CACHE_EXPIRY_TIME
            LogUtils.d("AgentCacheManager - 主题专区缓存过期检查: ${if (isExpired) "已过期" else "未过期"}")
            isExpired
        } catch (e: Exception) {
            LogUtils.e("AgentCacheManager - 检查主题专区缓存过期失败: ${e.message}")
            true
        }
    }

    /** 清理所有缓存 */
    fun clearCache() {
        try {
            IntySetting.setUserProfileData(KEY_RECOMMENDED_AGENTS, "")
            IntySetting.setUserProfileData(KEY_CHAT_AGENTS, "")
            IntySetting.setUserProfileData(KEY_FOLLOWING_AGENTS, "")
            IntySetting.setUserProfileData(KEY_USER_CREATED_AGENTS, "")
            IntySetting.setUserProfileData(KEY_CHARACTER_THEMES, "")
            IntySetting.setUserProfileData(KEY_CACHE_TIMESTAMP, "")
            IntySetting.setUserProfileData(KEY_CHAT_CACHE_TIMESTAMP, "")
            IntySetting.setUserProfileData(KEY_USER_CREATED_CACHE_TIMESTAMP, "")
            IntySetting.setUserProfileData(KEY_CHARACTER_THEMES_CACHE_TIMESTAMP, "")
            LogUtils.i("AgentCacheManager - 缓存已清理")
        } catch (e: Exception) {
            LogUtils.e("AgentCacheManager - 清理缓存失败: ${e.message}")
        }
    }

    /** 获取缓存统计信息 */
    fun getCacheStats(): CacheStats {
        val recommendedCount = getCachedAgents().size
        val chatCount = getCachedChatAgents().size
        val isExpired = isCacheExpired()

        return CacheStats(
            recommendedAgentsCount = recommendedCount,
            chatAgentsCount = chatCount,
            isExpired = isExpired,
        )
    }

    /** 缓存统计信息数据类 */
    data class CacheStats(
        val recommendedAgentsCount: Int,
        val chatAgentsCount: Int,
        val isExpired: Boolean,
    )
}
