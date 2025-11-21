package ai.sxwl.android.data.api.model

/**
 * Agent 相关常量
 * CREATED_BY_AGENT
 */
object AgentConstants {
    /** IntelliMate 官方 agent 的 ID */
    const val INTELLIMATE_AGENT_ID = "879e5e14-fec2-4d63-9704-4f3141bed74f"

    /** IntelliMate 官方 agent 的名称 */
    const val INTELLIMATE_AGENT_NAME = "IntelliMate"

    /**
     * 判断给定的 agent 是否为 IntelliMate agent
     *
     * @param agentId agent 的 ID
     * @param agentName agent 的名称
     * @return 如果是 IntelliMate agent 返回 true，否则返回 false
     */
    fun isIntelliMateAgent(agentId: String?, agentName: String?): Boolean {
        return agentId == INTELLIMATE_AGENT_ID || agentName == INTELLIMATE_AGENT_NAME
    }
}

