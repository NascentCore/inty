package com.ai.imate.chat.data.datasource

import com.ai.imate.chat.data.bean.GenerateAvatarRequest
import com.ai.imate.chat.data.bean.GenerateAvatarResponse
import com.ai.core.http.utils.post
import io.ktor.client.request.setBody
import javax.inject.Inject

class InitChatRemoteDataSource @Inject constructor() {
    suspend fun generateAvatar(prompt: String): GenerateAvatarResponse {
        return post<GenerateAvatarResponse>("/api/v1/ai/agents/text-to-image") {
            setBody(GenerateAvatarRequest(prompt = prompt))
        }
    }
}

