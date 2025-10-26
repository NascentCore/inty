package ai.sxwl.android.data.http.services

import ai.sxwl.android.data.http.ApiResult
import ai.sxwl.android.data.http.IntyNetworkManager
import com.inty.api.models.api.v1.report.ReportCreateParams
import java.io.InputStream

/** 报告服务封装报告所有相关的 API 调用 */
object ReportService {

    /**创建报告*/
    suspend fun createReport(
        reasonIds: List<Long>,
        targetId: String,
        targetType: String?,
        description: String,
        imageUrls: List<String>,
    ): ApiResult<Unit> {
        return IntyNetworkManager.executeRequest("Create Report") {
            val type = if (targetType == "USER") {
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

    /**
     * 上传图片注意：当前 IntySDK 的图片上传 API 解析复杂度，返回临时占位符
     *
     * TODO: 等 IntySDK 完美图片上传 API 之后实现真实上传
     */
    suspend fun uploadImage(
        inputStream: InputStream,
        filename: String = "report-image.jpg",
    ): ApiResult<String> {
        return IntyNetworkManager.executeRequest("Upload Image") {
// 返回基于当前计时器的占位符URL
// 等 IntySDK 图片上传 API 完善后再实现真实上传
            "https://placeholder.com/uploaded-image-${System.currentTimeMillis()}.jpg"
        }
    }
}
