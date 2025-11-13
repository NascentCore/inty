package ai.sxwl.android.data.http.services

import ai.sxwl.android.data.http.ApiResult
import ai.sxwl.android.data.http.IntyNetworkManager
import com.inty.api.models.api.v1.report.ReportCreateParams
import java.io.InputStream

/** 举报服务 封装所有举报相关的API调用 */
object ReportService {

    /** 创建举报 */
    suspend fun createReport(
        reasonIds: List<Long>,
        targetId: String,
        targetType: String?,
        description: String,
        imageUrls: List<String>,
    ): ApiResult<Unit> {
        return IntyNetworkManager.executeRequest("Create Report") {
            val type =
                if (targetType == "USER") {
                    ReportCreateParams.TargetType.USER
                } else {
                    ReportCreateParams.TargetType.AGENT
                }
            val reportParams =
                ReportCreateParams.builder()
                    .reasonIds(reasonIds)
                    .targetId(targetId)
                    .targetType(type)
                    .description(description.trim())
                    .imageUrls(imageUrls)
                    .build()

            val response = IntyNetworkManager.getClient().api().v1().report().create(reportParams)

            if (response.code() != 200L) {
                throw Exception("Report creation failed with code: ${response.code()}")
            }
        }
    }

    /** 上传图片 */
    suspend fun uploadImage(
        inputStream: InputStream,
        filename: String = "report-image.jpg",
    ): ApiResult<String> {
        return IntyNetworkManager.executeRequest("Upload Image") {
            val response =
                IntyNetworkManager.getClient()
                    .api()
                    .v1()
                    .uploadImage(
                        com.inty.api.models.api.v1.V1UploadImageParams.builder()
                            .file(inputStream.readBytes())
                            .build()
                    )

            val data = response.data()
            val additionalProperties = data?._additionalProperties() ?: emptyMap()
            val imageUrl = additionalProperties["url"]?.asString()
                ?: additionalProperties["image_url"]?.asString()
                ?: throw IllegalStateException("Image URL not found in response")

            imageUrl
        }
    }
}
