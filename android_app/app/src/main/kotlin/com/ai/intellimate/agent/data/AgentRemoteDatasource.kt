package com.ai.intellimate.agent.data

import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.api.model.CreateAgentRequest
import ai.sxwl.android.data.api.model.UploadAvatarResponse
import ai.sxwl.android.utils.LogUtils
import com.ai.intellimate.utils.HttpErrorHandler
import com.architecture.httplib.core.HttpResult
import java.io.File
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import retrofit2.HttpException

class AgentRemoteDatasource {

    /** 创建Agent */
    suspend fun createAgent(params: CreateAgentRequest): AgentInfo {
        return request { NetServiceMgr.getAgentApi().createAgent(params) }
    }

    /** 更新Agent */
    suspend fun updateAgent(agentId: String, params: CreateAgentRequest): AgentInfo {
        return request { NetServiceMgr.getAgentApi().updateAgent(agentId, params) }
    }

    /** 上传图片 */
    suspend fun uploadImage(file: File): UploadAvatarResponse {
        return request(operation = "Image upload") {
            // 记录文件信息，便于调试
            ai.sxwl.android.utils.LogUtils.i(
                "AgentRemoteDatasource - Uploading image: ${file.name}, size: ${file.length() / 1024}KB"
            )
            val requestFile = file.asRequestBody("image/*".toMediaTypeOrNull())
            val body = MultipartBody.Part.createFormData("file", file.name, requestFile)

            NetServiceMgr.getAgentApi().uploadAvatar(body)
        }
    }
}

private suspend fun <T : Any> request(
    operation: String = "operation",
    action: suspend () -> HttpResult<T>,
): T {
    return withContext(Dispatchers.IO) {
        try {
            when (val result = action()) {
                is HttpResult.Success -> result.data
                is HttpResult.Failure -> {
                    val errorMessage =
                        result.message.ifBlank {
                            "Creation failed, please check network connection"
                        }
                    LogUtils.e("AgentRemoteDatasource - Request failed: $errorMessage")
                    throw Exception(errorMessage)
                }
            }
        } catch (e: HttpException) {
            throw Exception(HttpErrorHandler.handleHttpException(e, operation))
        } catch (e: Exception) {
            throw Exception(HttpErrorHandler.handleGeneralException(e, operation))
        }
    }
}
