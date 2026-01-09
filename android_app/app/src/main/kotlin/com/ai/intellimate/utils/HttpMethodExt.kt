package com.ai.intellimate.utils

import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.UploadAvatarResponse
import ai.sxwl.android.utils.LogUtils
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import retrofit2.HttpException
import java.io.File

suspend fun <T : Any> request(
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