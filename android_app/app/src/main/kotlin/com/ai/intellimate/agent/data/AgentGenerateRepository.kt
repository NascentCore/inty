package com.ai.intellimate.agent.data

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.api.model.CreateAgentRequest
import ai.sxwl.android.data.api.model.UploadAvatarResponse
import java.io.File

class AgentGenerateRepository(
    private val remoteDatasource: AgentRemoteDatasource = AgentRemoteDatasource()
) {

    suspend fun createAgent(request: CreateAgentRequest): AgentInfo {
        return remoteDatasource.createAgent(request)
    }

    suspend fun updateAgent(agentId: String, request: CreateAgentRequest): AgentInfo {
        return remoteDatasource.updateAgent(agentId, request)
    }

    suspend fun uploadImage(file: File): UploadAvatarResponse {
        return remoteDatasource.uploadImage(file)
    }
}