package ai.sxwl.android.data.http.services

import ai.sxwl.android.data.http.ApiResult
import ai.sxwl.android.data.http.IntyNetworkManager
import ai.sxwl.android.utils.LogUtils
import com.inty.api.models.api.v1.V1UploadImageParams
import com.inty.api.models.api.v1.report.ApiResponseDict
import java.io.File
import java.nio.file.Paths

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

            // 使用 Path 而不是 FileInputStream，这是 SDK 推荐的方式
            val filePath = Paths.get(filePath)
            LogUtils.d("ImageService: Created Path object: $filePath")

            val params = V1UploadImageParams.builder()
                .file(filePath)  // ✅ 使用 Path 对象
                .croppingAvatar(croppingAvatar)
                .build()

            LogUtils.d("ImageService: Created upload params - croppingAvatar: $croppingAvatar")

            val response = IntyNetworkManager.getClient().api().v1().uploadImage(params)
            
            LogUtils.d("ImageService: Received response from server")
            
            // 记录完整的响应信息用于调试
            LogUtils.d("ImageService: Response code: ${response.code()}")
            LogUtils.d("ImageService: Response message: ${response.message()}")
            LogUtils.d("ImageService: Response data: ${response.data()}")
            LogUtils.d("ImageService: Response additionalProperties: ${response._additionalProperties()}")
            
            // 尝试多种方式提取URL
            var url: String? = null
            
            // 方式1: 从data字段的additionalProperties中提取
            val data = response.data()
            if (data != null) {
                LogUtils.d("ImageService: Data field exists - additionalProperties: ${data._additionalProperties()}")
                url = data._additionalProperties()["url"]?.toString()?.trim('"')
                if (url != null) {
                    LogUtils.d("ImageService: Found URL in data.additionalProperties: $url")
                }
            } else {
                LogUtils.w("ImageService: Data field is null, trying alternative approaches")
            }
            
            // 方式2: 从response的additionalProperties中提取
            if (url == null) {
                LogUtils.d("ImageService: Trying response.additionalProperties")
                url = response._additionalProperties()["url"]?.toString()?.trim('"')
                if (url != null) {
                    LogUtils.d("ImageService: Found URL in response.additionalProperties: $url")
                }
            }
            
            // 方式3: 检查是否有其他可能的字段名
            if (url == null) {
                LogUtils.d("ImageService: Checking for alternative field names")
                val allProps = response._additionalProperties()
                LogUtils.d("ImageService: All response properties: $allProps")
                
                // 尝试常见的字段名
                val possibleKeys = listOf("url", "imageUrl", "image_url", "fileUrl", "file_url", "uploadUrl", "upload_url")
                for (key in possibleKeys) {
                    val value = allProps[key]?.toString()?.trim('"')
                    if (value != null && value.isNotEmpty()) {
                        url = value
                        LogUtils.d("ImageService: Found URL with key '$key': $url")
                        break
                    }
                }
            }
            
            if (url == null) {
                LogUtils.e("ImageService: URL not found in any location")
                LogUtils.e("ImageService: Response structure: code=${response.code()}, message=${response.message()}, data=${response.data()}")
                LogUtils.e("ImageService: All additionalProperties: ${response._additionalProperties()}")
                throw IllegalStateException("URL not found in response. Response structure: code=${response.code()}, message=${response.message()}, data=${response.data()}")
            }
            
            LogUtils.d("ImageService: Successfully extracted URL: $url")
            url
        }
    }
}