package ai.sxwl.android.data.http.services

import ai.sxwl.android.data.http.ApiResult
import ai.sxwl.android.data.http.IntyNetworkManager
import com.inty.api.models.api.v1.V1UploadImageParams
import com.inty.api.models.api.v1.report.ApiResponseDict
import java.io.File
import java.io.FileInputStream

/** 图片服务 封装图片上传API调用 使用 Inty SDK */
object ImageService {

    /** 上传图片文件 */
    suspend fun uploadImage(filePath: String, croppingAvatar: Boolean = false): ApiResult<String> {
        return IntyNetworkManager.executeRequest("Upload Image") {
            val file = File(filePath)
            if (!file.exists()) {
                throw IllegalArgumentException("File does not exist: $filePath")
            }

            val params = V1UploadImageParams.builder()
                .file(FileInputStream(file))
                .croppingAvatar(croppingAvatar)
                .build()

            val response = IntyNetworkManager.getClient().api().v1().uploadImage(params)
            
            // 从 ApiResponseDict 中提取 URL
            val data = response.data() ?: throw IllegalStateException("Response data is null")
            val url = data._additionalProperties()["url"]?.toString()?.trim('"')
                ?: throw IllegalStateException("URL not found in response")
            
            url
        }
    }
}