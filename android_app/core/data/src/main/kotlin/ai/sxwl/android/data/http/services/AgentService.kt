package ai.sxwl.android.data.http.services

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.http.ApiResult
import ai.sxwl.android.data.http.IntyNetworkManager
import ai.sxwl.android.data.http.models.toAgentInfo

/** 智能体服务 封装所有智能体相关的API调用 替换原有的 IAgentApi */
object AgentService {

    /** 获取推荐智能体列表 替换: IAgentApi.recommendAgents() */
    suspend fun getRecommendAgents(
        page: Int = 1,
        pageSize: Int = 10,
        sort: String = "random",
        sortSeed: String = "default",
    ): ApiResult<List<AgentInfo>> {
        return IntyNetworkManager.executeRequest("Get Recommend Agents") {
            val response =
                IntyNetworkManager.getClient()
                    .api()
                    .v1()
                    .ai()
                    .agents()
                    .recommend(
                        com.inty.api.models.api.v1.ai.agents.AgentRecommendParams.builder()
                            .page(page.toLong())
                            .pageSize(pageSize.toLong())
                            .sort(
                                when (sort) {
                                    "random" ->
                                        com.inty.api.models.api.v1.ai.agents.AgentRecommendParams
                                            .Sort
                                            .RANDOM
                                    "created_asc" ->
                                        com.inty.api.models.api.v1.ai.agents.AgentRecommendParams
                                            .Sort
                                            .CREATED_ASC
                                    "created_desc" ->
                                        com.inty.api.models.api.v1.ai.agents.AgentRecommendParams
                                            .Sort
                                            .CREATED_DESC
                                    else ->
                                        com.inty.api.models.api.v1.ai.agents.AgentRecommendParams
                                            .Sort
                                            .RANDOM
                                }
                            )
                            .sortSeed(sortSeed)
                            .build()
                    )

            response.data()?.list()?.map { it.toAgentInfo() } ?: emptyList()
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
            val paramsBuilder = com.inty.api.models.api.v1.ai.agents.AgentCreateParams.builder()
                .name(agentInfo.name)
                .gender(agentInfo.gender)
                .intro(agentInfo.intro)
                .opening(agentInfo.opening)
                .visibility(
                    when (agentInfo.visibility) {
                        "PUBLIC" -> com.inty.api.models.api.v1.ai.agents.AgentVisibility.PUBLIC
                        "PRIVATE" -> com.inty.api.models.api.v1.ai.agents.AgentVisibility.PRIVATE
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
                IntyNetworkManager.getClient().api().v1().ai().agents()
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

    /** 关注智能体 */
    suspend fun followAgent(agentId: String): ApiResult<Unit> {
        return IntyNetworkManager.executeRequest("Follow Agent") {
            IntyNetworkManager.getClient()
                .api()
                .v1()
                .ai()
                .agents()
                .followAgent(agentId)
        }
    }

    /** 取消关注智能体 */
    suspend fun unfollowAgent(agentId: String): ApiResult<Unit> {
        return IntyNetworkManager.executeRequest("Unfollow Agent") {
            IntyNetworkManager.getClient()
                .api()
                .v1()
                .ai()
                .agents()
                .unfollowAgent(agentId)
        }
    }

    /** 获取我关注的智能体列表 */
    suspend fun getFollowingAgents(
        page: Int = 1,
        pageSize: Int = 10,
    ): ApiResult<List<AgentInfo>> {
        return IntyNetworkManager.executeRequest("Get Following Agents") {
            val response =
                IntyNetworkManager.getClient()
                    .api()
                    .v1()
                    .ai()
                    .agents()
                    .following(
                        com.inty.api.models.api.v1.ai.agents.AgentFollowingParams.builder()
                            .page(page.toLong())
                            .pageSize(pageSize.toLong())
                            .build()
                    )

            response.data()?.list()?.map { it.toAgentInfo() } ?: emptyList()
        }
    }
}
