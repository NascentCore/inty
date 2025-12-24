package com.ai.intellimate.xb.helper

import ai.sxwl.android.data.api.model.AgentInfo

object AgentStore {
    // App 中用到的Agent缓存
    val agents = mutableListOf<AgentInfo>()

    // 添加AgentInfo
    fun addAgent(agentInfo: AgentInfo) {
        synchronized(this) {
            // 移除旧的记录
            agents.removeIf { it.id == agentInfo.id }
            // 更新为记录
            agents.add(agentInfo)
        }
    }

    // 获取缓存中的AgentInfo
    fun getAgent(agentId: String?): AgentInfo? {
        return agents.find { it.id == agentId }
    }

    var agentInfoDraft: AgentInfo? = null
    fun setDraftAgentInfo(agentInfo: AgentInfo?) {
        synchronized(this) {
            agentInfoDraft = agentInfo
        }
    }
}
