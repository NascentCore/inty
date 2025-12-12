package ai.sxwl.android.data.http.services

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.http.ApiResult
import ai.sxwl.android.data.http.IntyNetworkManager
import ai.sxwl.android.data.http.models.toAgentInfo
import ai.sxwl.android.utils.LogUtils
import com.squareup.moshi.JsonClass
import kotlinx.coroutines.withContext

/** 智能体服务 封装所有智能体相关的API调用 替换原有的 IAgentApi */
object AgentService {

    /** 主题专区数据项 */
    @JsonClass(generateAdapter = true)
    data class CharacterThemeItem(
        val id: String,
        val name: String,
        val description: String,
        val agents: List<AgentInfo>,
        val isChristmas: Boolean = false,
    )

    /** 获取推荐智能体列表 替换: IAgentApi.recommendAgents() */
    suspend fun getRecommendAgents(
        page: Int = 1,
        pageSize: Int = 10,
        sort: String = "random",
        sortSeed: String = "default",
    ): ApiResult<List<AgentInfo>> {
        return IntyNetworkManager.executeRequest("Get Recommend Agents") {
            val params =
                com.inty.api.models.api.v1.ai.agents.AgentRecommendParams.builder()
                    .page(page.toLong())
                    .pageSize(pageSize.toLong())
                    .sort(
                        when (sort) {
                            "random" ->
                                com.inty.api.models.api.v1.ai.agents.AgentRecommendParams.Sort
                                    .RANDOM

                            "created_asc" ->
                                com.inty.api.models.api.v1.ai.agents.AgentRecommendParams.Sort
                                    .CREATED_ASC

                            "created_desc" ->
                                com.inty.api.models.api.v1.ai.agents.AgentRecommendParams.Sort
                                    .CREATED_DESC

                            "energy_points" ->
                                com.inty.api.models.api.v1.ai.agents.AgentRecommendParams.Sort
                                    .ENERGY_POINTS

                            else ->
                                com.inty.api.models.api.v1.ai.agents.AgentRecommendParams.Sort
                                    .RANDOM
                        }
                    )
                    .sortSeed(sortSeed)
                    .build()

            // 使用 withContext 确保阻塞调用在 IO 线程执行，避免 NetworkOnMainThreadException
            val response =
                withContext(kotlinx.coroutines.Dispatchers.IO) {
                    IntyNetworkManager.getClient().api().v1().ai().agents().recommend(params)
                }

            val rawData = response.data()
            rawData?.list()?.map { it.toAgentInfo() } ?: emptyList()
        }
    }

    /** 获取智能体详情 替换: IAgentApi.getAgentInfo() */
    suspend fun getAgentInfo(agentId: String): ApiResult<AgentInfo> {
        return IntyNetworkManager.executeRequest("Get Agent Info") {
            val response = IntyNetworkManager.getClient().api().v1().ai().agents().retrieve(agentId)
            response.toAgentInfo()
        }
    }

    /** 创建智能体 替换: IAgentApi.createAgent() */
    suspend fun createAgent(agentInfo: AgentInfo): ApiResult<AgentInfo> {
        return IntyNetworkManager.executeRequest("Create Agent") {
            val paramsBuilder =
                com.inty.api.models.api.v1.ai.agents.AgentCreateParams.builder()
                    .name(agentInfo.name)
                    .gender(agentInfo.gender)
                    .intro(agentInfo.intro)
                    .opening(agentInfo.opening)
                    .visibility(
                        when (agentInfo.visibility) {
                            "PUBLIC" -> com.inty.api.models.api.v1.ai.agents.AgentVisibility.PUBLIC
                            "PRIVATE" ->
                                com.inty.api.models.api.v1.ai.agents.AgentVisibility.PRIVATE

                            else -> com.inty.api.models.api.v1.ai.agents.AgentVisibility.PRIVATE
                        }
                    )

            if (agentInfo.avatar.isNotEmpty()) {
                paramsBuilder.avatar(agentInfo.avatar)
            }
            if (agentInfo.background.isNotEmpty()) {
                paramsBuilder.background(agentInfo.background)
            }
            if (agentInfo.backgroundImages.isNotEmpty()) {
                paramsBuilder.backgroundImages(agentInfo.backgroundImages)
            }
            if (agentInfo.category.isNotEmpty()) {
                paramsBuilder.category(agentInfo.category)
            }
            if (agentInfo.prompt.isNotEmpty()) {
                paramsBuilder.prompt(agentInfo.prompt)
            }
            if (agentInfo.tags != null && agentInfo.tags.isNotEmpty()) {
                paramsBuilder.tags(agentInfo.tags.filterNotNull())
            }

            val response =
                IntyNetworkManager.getClient()
                    .api()
                    .v1()
                    .ai()
                    .agents()
                    .create(paramsBuilder.build())
            val data = response.data()
            if (data != null && data.isAgent()) {
                data.asAgent().toAgentInfo()
            } else {
                throw IllegalStateException("Created agent data is null or invalid")
            }
        }
    }

    /** 更新智能体 替换: IAgentApi.updateAgent() */
    suspend fun updateAgent(agentId: String, agentInfo: AgentInfo): ApiResult<AgentInfo> {
        return IntyNetworkManager.executeRequest("Update Agent") {
            val paramsBuilder = com.inty.api.models.api.v1.ai.agents.AgentUpdateParams.builder()

            if (agentInfo.name.isNotEmpty()) {
                paramsBuilder.name(agentInfo.name)
            }
            if (agentInfo.gender.isNotEmpty()) {
                paramsBuilder.gender(agentInfo.gender)
            }
            if (agentInfo.intro.isNotEmpty()) {
                paramsBuilder.intro(agentInfo.intro)
            }
            if (agentInfo.opening.isNotEmpty()) {
                paramsBuilder.opening(agentInfo.opening)
            }
            if (agentInfo.avatar.isNotEmpty()) {
                paramsBuilder.avatar(agentInfo.avatar)
            }
            if (agentInfo.background.isNotEmpty()) {
                paramsBuilder.background(agentInfo.background)
            }
            if (agentInfo.backgroundImages.isNotEmpty()) {
                paramsBuilder.backgroundImages(agentInfo.backgroundImages)
            }
            if (agentInfo.category.isNotEmpty()) {
                paramsBuilder.category(agentInfo.category)
            }
            if (agentInfo.prompt.isNotEmpty()) {
                paramsBuilder.prompt(agentInfo.prompt)
            }
            if (agentInfo.tags != null && agentInfo.tags.isNotEmpty()) {
                paramsBuilder.tags(agentInfo.tags.filterNotNull())
            }
            if (agentInfo.visibility.isNotEmpty()) {
                paramsBuilder.visibility(
                    when (agentInfo.visibility) {
                        "PUBLIC" -> com.inty.api.models.api.v1.ai.agents.AgentVisibility.PUBLIC
                        "PRIVATE" -> com.inty.api.models.api.v1.ai.agents.AgentVisibility.PRIVATE
                        else -> com.inty.api.models.api.v1.ai.agents.AgentVisibility.PRIVATE
                    }
                )
            }

            val response =
                IntyNetworkManager.getClient()
                    .api()
                    .v1()
                    .ai()
                    .agents()
                    .update(agentId, paramsBuilder.build())
            response.toAgentInfo()
        }
    }

    /** 更新智能体的 energy points（增量） */
    suspend fun updateAgentEnergyPoints(
        agentId: String,
        energyPointsDelta: Int,
    ): ApiResult<AgentInfo> {
        return IntyNetworkManager.executeRequest("Update Agent Energy Points") {
            val params =
                com.inty.api.models.api.v1.ai.agents.AgentUpdateParams.builder()
                    .energyPoints(energyPointsDelta.toLong())
                    .build()
            val response =
                IntyNetworkManager.getClient().api().v1().ai().agents().update(agentId, params)
            response.toAgentInfo()
        }
    }

    /** 删除智能体 替换: IAgentApi.deleteAgent() */
    suspend fun deleteAgent(agentId: String): ApiResult<Unit> {
        return IntyNetworkManager.executeRequest("Delete Agent") {
            IntyNetworkManager.getClient().api().v1().ai().agents().delete(agentId)
        }
    }

    /** 获取我创建的智能体列表 替换: IAgentApi.getMyAgents() */
    suspend fun getMyAgents(page: Int = 1, pageSize: Int = 10): ApiResult<List<AgentInfo>> {
        return IntyNetworkManager.executeRequest("Get My Agents") {
            // 后端API使用skip和limit参数，而不是page和pageSize
            // skip是从0开始的偏移量，limit是每页的数量
            val skip = ((page - 1) * pageSize).toLong()
            val limit = pageSize.toLong()

            val response =
                IntyNetworkManager.getClient()
                    .api()
                    .v1()
                    .ai()
                    .agents()
                    .list(
                        com.inty.api.models.api.v1.ai.agents.AgentListParams.builder()
                            .skip(skip)
                            .limit(limit)
                            .build()
                    )

            response.data()?.map { it.toAgentInfo() } ?: emptyList()
        }
    }

    /** 搜索智能体 */
    suspend fun searchAgents(
        query: String,
        page: Int = 1,
        pageSize: Int = 10,
    ): ApiResult<List<AgentInfo>> {
        return IntyNetworkManager.executeRequest("Search Agents") {
            val response =
                IntyNetworkManager.getClient()
                    .api()
                    .v1()
                    .ai()
                    .agents()
                    .search(
                        com.inty.api.models.api.v1.ai.agents.AgentSearchParams.builder()
                            .q(query)
                            .page(page.toLong())
                            .pageSize(pageSize.toLong())
                            .build()
                    )

            response.data()?.list()?.map { it.toAgentInfo() } ?: emptyList()
        }
    }

    /**
     * 获取主题专区列表
     *
     * @param skip 跳过的记录数（分页参数）
     * @param limit 返回的记录数（分页参数）
     */
    suspend fun getCharacterThemes(skip: Int = 0, limit: Int): ApiResult<List<CharacterThemeItem>> {
        return IntyNetworkManager.executeRequest("Get Character Themes") {
            LogUtils.d("AgentService - 请求主题专区列表: skip=$skip, limit=$limit")

            // 使用 inty_sdk 同步 API，与其他接口保持一致（如 getRecommendAgents, getAgentInfo）
            // 注意：同步阻塞调用必须在 IO 线程执行，避免 NetworkOnMainThreadException
            val response =
                try {
                    withContext(kotlinx.coroutines.Dispatchers.IO) {
                        IntyNetworkManager.getClient()
                            .api()
                            .v1()
                            .characterThemes()
                            .list(
                                com.inty.api.models.api.v1.characterthemes.CharacterThemeListParams
                                    .builder()
                                    .skip(skip.toLong())
                                    .limit(limit.toLong())
                                    .build()
                            )
                    }
                } catch (e: Exception) {
                    LogUtils.e(
                        "AgentService - 请求主题专区列表异常: ${e.javaClass.simpleName}, message=${e.message}",
                        e,
                    )
                    throw e
                }

            LogUtils.d(
                "AgentService - 主题专区接口响应: code=${response.code()}, message=${response.message()}, data=${response.data()?.size ?: 0} 条"
            )

            // 详细日志：检查响应对象的各个字段
            try {
                LogUtils.d(
                    "AgentService - 响应详情: code=${response.code()}, message=${response.message()}, data是否为null=${response.data() == null}"
                )
                if (response.data() != null) {
                    LogUtils.d("AgentService - data列表大小: ${response.data()!!.size}")
                }
            } catch (e: Exception) {
                LogUtils.w("AgentService - 读取响应详情失败: ${e.message}", e)
            }

            // 参考 getRecommendAgents 的处理方式：直接使用 data，不检查 code
            // 原因：response.code() 返回 Long?（可空），如果为 null，null != 200L 会返回 true，导致错误地抛出异常
            // 如果响应解析成功，response.data() 应该有值；如果解析失败，data 为 null，此时再检查错误信息
            val rawThemes = response.data()
            if (rawThemes == null) {
                // 如果 data 为 null，检查是否有错误信息
                val responseCode = response.code()
                val errorMessage = response.message() ?: "获取主题专区列表失败"
                if (responseCode != null && responseCode != 200L) {
                    LogUtils.w(
                        "AgentService - 获取主题专区列表失败: code=$responseCode, message=$errorMessage"
                    )
                    throw Exception("获取主题专区列表失败: code=$responseCode, message=$errorMessage")
                } else {
                    // code 为 null 或等于 200，但 data 为 null，可能是正常情况（空列表）或解析失败
                    LogUtils.w(
                        "AgentService - 主题专区列表数据为空: code=$responseCode, message=$errorMessage"
                    )
                    return@executeRequest emptyList()
                }
            }

            LogUtils.d("AgentService - 原始主题数量: ${rawThemes.size}")

            val themes =
                rawThemes
                    .filter { theme ->
                        try {
                            // 只显示可见的主题（PRIMARY 或 SECONDARY）
                            val visibility = theme.visibility()
                            val isVisible =
                                visibility ==
                                    com.inty.api.models.api.v1.characterthemes
                                        .CharacterThemeVisibility
                                        .PRIMARY ||
                                    visibility ==
                                        com.inty.api.models.api.v1.characterthemes
                                            .CharacterThemeVisibility
                                            .SECONDARY
                            LogUtils.d(
                                "AgentService - 主题 ${theme.id()}: visibility=$visibility, isVisible=$isVisible"
                            )
                            isVisible
                        } catch (e: Exception) {
                            LogUtils.w("AgentService - 获取主题可见性失败: ${e.message}")
                            false
                        }
                    }
                    .mapNotNull { theme ->
                        try {
                            val agents =
                                theme.agents()?.mapNotNull { themeAgent ->
                                    try {
                                        themeAgent.agent()?.toAgentInfo()
                                    } catch (e: Exception) {
                                        LogUtils.w("AgentService - 转换 Agent 失败: ${e.message}")
                                        null
                                    }
                                } ?: emptyList()

                            LogUtils.d(
                                "AgentService - 主题 ${theme.id()}: name=${theme.name()}, agents数量=${agents.size}"
                            )

                            CharacterThemeItem(
                                id = theme.id(),
                                name = theme.name(),
                                description = theme.description() ?: "",
                                agents = agents,
                                isChristmas = isChristmasTheme(theme),
                            )
                        } catch (e: Exception) {
                            LogUtils.w("AgentService - 处理主题失败: ${e.message}")
                            null
                        }
                    }

            LogUtils.d("AgentService - 最终返回主题数量: ${themes.size}")
            themes
        }
    }

    /** 判断是否为圣诞主题（根据名称或其他特征判断） */
    private fun isChristmasTheme(
        theme: com.inty.api.models.api.v1.characterthemes.CharacterTheme
    ): Boolean {
        return try {
            val name = theme.name().lowercase()
            val description = theme.description()?.lowercase() ?: ""
            name.contains("christmas") ||
                name.contains("圣诞") ||
                description.contains("christmas") ||
                description.contains("圣诞")
        } catch (e: Exception) {
            LogUtils.w("AgentService - 判断圣诞主题失败: ${e.message}")
            false
        }
    }

    /** 创建模拟主题专区数据（用于测试 UI 效果） */
    fun createMockCharacterThemes(
        exploreAgents: List<AgentInfo> = emptyList()
    ): List<CharacterThemeItem> {
        // 如果提供了真实的 explore agents 数据，使用它们；否则使用完全模拟的数据
        val agentsForTheme1 =
            if (exploreAgents.isNotEmpty()) {
                exploreAgents.take(5)
            } else {
                createMockAgents(5)
            }

        val agentsForTheme2 =
            if (exploreAgents.size > 5) {
                exploreAgents.drop(5).take(3)
            } else if (exploreAgents.isNotEmpty()) {
                exploreAgents.take(3)
            } else {
                createMockAgents(3)
            }

        return listOf(
            CharacterThemeItem(
                id = "mock_christmas_1",
                name = "# Merry Christmas",
                description =
                    "Ready for some holiday magic? Meet our brand-new Christmas-themed AI companion—sparkly, cheerful, and here to light up your winter feed. Come take a look and get into the festive spirit!",
                agents = agentsForTheme1,
                isChristmas = true,
            ),
            CharacterThemeItem(
                id = "mock_theme_2",
                name = "# Winter Wonderland",
                description =
                    "Explore the magical world of winter with our special winter-themed characters.",
                agents = agentsForTheme2,
                isChristmas = false,
            ),
        )
    }

    /** 创建模拟 AgentInfo 列表 */
    private fun createMockAgents(count: Int): List<AgentInfo> {
        return (1..count).map { index ->
            AgentInfo(
                id = "mock_agent_$index",
                name = "Character $index",
                intro = "This is a mock character for testing purposes.",
                avatar = "",
                background = "",
                category = "Mock",
                gender = "Female",
                tags = listOf("Mock", "Test"),
            )
        }
    }
}
