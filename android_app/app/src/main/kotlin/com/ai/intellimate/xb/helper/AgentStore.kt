package com.ai.intellimate.xb.helper

import ai.sxwl.android.data.api.model.AgentInfo

object AgentStore {
    // App 中用到的Agent缓存
    val agents = mutableListOf<AgentInfo>()

    // 添加AgentInfo
    fun addAgent(agentInfo: AgentInfo) {
        synchronized(this) {
            var hasAgent = false
            val count = agents.count();
            for (i in 0 until count) {
                val a = agents[i]
                if (a.id == agentInfo.id) hasAgent = true
            }
            if (!hasAgent) agents.add(agentInfo)
        }
    }

    // 获取缓存中的AgentInfo
    fun getAgent(agentId: String?): AgentInfo? {
        if (agentId == null) return null
        var index = -1
        for (i in 0 until agents.count()) {
            val a = agents[i]
            if (a.id == agentId) index = i;
        }
        return if (index > -1) agents[index] else null
    }


}