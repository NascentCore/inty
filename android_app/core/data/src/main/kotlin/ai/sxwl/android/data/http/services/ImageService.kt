package ai.sxwl.android.data.http.services

import ai.sxwl.android.data.http.ApiResult
import ai.sxwl.android.data.http.IntyNetworkManager
import ai.sxwl.android.utils.LogUtils
import com.inty.api.models.api.v1.V1UploadImageParams
import com.inty.api.models.api.v1.report.ApiResponseDict
import java.io.File
import java.io.FileInputStream

/** 图片服务 封装图片上传API调用 使用 Inty SDK */
object ImageService {

    /** 上传图片文件 */
    suspend fun uploadImage(filePath: String, croppingAvatar: Boolean = false): ApiResult<String> {
        return IntyNetworkManager.executeRequest("Upload Image") {
            LogUtils.d("ImageService: Starting image upload - filePath: $filePath, croppingAvatar: $croppingAvatar")
            
            val file = File(filePath)
            if (!file.exists()) {
                LogUtils.e("ImageService: File does not exist: $filePath")
                throw IllegalArgumentException("File does not exist: $filePath")
            }

            // 记录文件信息
            LogUtils.d("ImageService: File exists - size: ${file.length()} bytes, name: ${file.name}, absolutePath: ${file.absolutePath}")

            val params = V1UploadImageParams.builder()
                .file(FileInputStream(file))
                .croppingAvatar(croppingAvatar)
                .build()

            LogUtils.d("ImageService: Created upload params - croppingAvatar: $croppingAvatar")

            val response = IntyNetworkManager.getClient().api().v1().uploadImage(params)
            
            LogUtils.d("ImageService: Received response from server")
            
            // 从 ApiResponseDict 中提取 URL
            val data = response.data()
            if (data == null) {
                LogUtils.e("ImageService: Response data is null")
                throw IllegalStateException("Response data is null")
            }
            
            LogUtils.d("ImageService: Response data received - additionalProperties: ${data._additionalProperties()}")
            
            val url = data._additionalProperties()["url"]?.toString()?.trim('"')
            if (url == null) {
                LogUtils.e("ImageService: URL not found in response data")
                throw IllegalStateException("URL not found in response")
            }
            
            LogUtils.d("ImageService: Successfully extracted URL: $url")
            url
        }
    }
}