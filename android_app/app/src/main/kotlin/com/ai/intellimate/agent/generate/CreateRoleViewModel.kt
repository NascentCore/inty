package com.ai.intellimate.agent.generate

import ai.sxwl.android.common.base.BaseVM
import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.api.model.CreateAgentRequest
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.ToastUtils
import ai.sxwl.android.utils.Utils
import android.net.Uri
import androidx.core.net.toUri
import com.ai.intellimate.R
import com.ai.intellimate.agent.data.AgentGenerateRepository
import com.ai.intellimate.utils.HttpErrorHandler
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import retrofit2.HttpException
import java.io.File

/** CreateRoleActivity 的 ViewModel 负责管理 Agent 的创建和更新逻辑 */
class CreateRoleViewModel : BaseVM() {
    private val repository = AgentGenerateRepository()

    suspend fun updateAgent(
        agentId: String? = null,
        request: CreateAgentRequest,
        createTempFile: (Uri) -> File
    ) {
        val remoteImageUrls = request.backgroundImages.map { uri ->
            convertToRemoteImage(uri, createTempFile)
        }

        val remoteBackgroundImage = request.background?.let { uri ->
            val index = request.backgroundImages.indexOf(uri)

            if (index >= 0) {
                remoteImageUrls[index]
            } else {
                convertToRemoteImage(uri, createTempFile)
            }
        }

        val newRequest = request.copy(
            background = remoteBackgroundImage,
            backgroundImages = remoteImageUrls
        )

        if (agentId.isNullOrBlank()) {
            val result = repository.createAgent(newRequest)

            LogUtils.i(
                "CreateRoleViewModel - createAgent success: ${result.id}"
            )
        } else {
            repository.updateAgent(agentId, newRequest)

            LogUtils.i("CreateRoleViewModel - updateAgent success: $agentId")
        }
    }

    private suspend fun convertToRemoteImage(uri: String, createTempFile: (Uri) -> File): String {
        return withContext(Dispatchers.IO) {
            if (uri.startsWith("http") || uri.startsWith("https")) {
                uri
            } else {
                repository.uploadImage(createTempFile(uri.toUri())).url
            }
        }
    }
}
