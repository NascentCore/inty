package ai.sxwl.android.data.http.services

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.http.ApiResult
import ai.sxwl.android.data.http.IntyNetworkManager

/** 智能体服务封装所有智能体相关的API调用替换原有的IAgentApi */
object AgentService {

    /** 获取推荐智能体列表替换：IAgentApi。推荐代理() */
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
// 这里需要根据实际的IntySDK返回结构进行转换
// 目前先返回空列表，等IntySDK完善后再实现
            emptyList<AgentInfo>()
        }
    }

    /** 获取智能体详情替换：IAgentApi。获取代理信息() */
    suspend fun getAgentInfo(agentId: String): ApiResult<AgentInfo> {
        return IntyNetworkManager.executeRequest("Get Agent Info") {
            val response = IntyNetworkManager.getClient().api().v1().ai().agents().retrieve(agentId)
// 当前 IntySDK 的 Agent 数据结构与业务层不匹配
// 需要根据实际结构返回进行数据转换
            throw Exception("Agent info conversion not implemented, need data mapping")
        }
    }

    /**创建智能体替换：IAgentApi。createAgent()注意: 当前 IntySDK 没有直接的创建代理 API */
    suspend fun createAgent(agentInfo: AgentInfo): ApiResult<AgentInfo> {
        return IntyNetworkManager.executeRequest("Create Agent") {
// 当前 IntySDK 没有直接的创建代理 API
// 可能需要通过其他方式实现
            throw Exception("Create agent not supported, check API documentation")
        }
    }

    /** 更新智能体替换：IAgentApi。updateAgent() 注意: 当前 IntySDK 没有直接的更新代理 API */
    suspend fun updateAgent(agentId: String, agentInfo: AgentInfo): ApiResult<AgentInfo> {
        return IntyNetworkManager.executeRequest("Update Agent") {
// 当前 IntySDK 没有直接的更新代理 API
// 可能需要通过其他方式实现
            throw Exception("Update agent not supported, check API documentation")
        }
    }

    /** 删除智能体替换：IAgentApi。删除代理() */
    suspend fun deleteAgent(agentId: String): ApiResult<Unit> {
        return IntyNetworkManager.executeRequest("Delete Agent") {
            IntyNetworkManager.getClient().api().v1().ai().agents().delete(agentId)
        }
    }

    /** 关注智能体替换：IAgentApi。接下来代理() */
    suspend fun followAgent(agentId: String): ApiResult<Unit> {
        return IntyNetworkManager.executeRequest("Follow Agent") {
            IntyNetworkManager.getClient().api().v1().ai().agents().followAgent(agentId)
        }
    }

    /** 取消关注智能体替换：IAgentApi。取消关注代理() */
    suspend fun unfollowAgent(agentId: String): ApiResult<Unit> {
        return IntyNetworkManager.executeRequest("Unfollow Agent") {
            IntyNetworkManager.getClient().api().v1().ai().agents().unfollowAgent(agentId)
        }
    }

    /** 获取我的智能体列表替换：IAgentApi。获取我的代理() */
    suspend fun getMyAgents(page: Int = 1, pageSize: Int = 10): ApiResult<List<AgentInfo>> {
        return IntyNetworkManager.executeRequest("Get My Agents") {
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
// 这里需要根据实际的IntySDK返回结构进行转换
            emptyList<AgentInfo>()
        }
    }
}
