package ai.sxwl.android.data.http.services

import ai.sxwl.android.data.http.ApiResult
import ai.sxwl.android.data.http.IntyNetworkManager
import com.inty.api.core.MultipartField
import com.inty.api.models.api.v1.report.ReportCreateParams
import java.io.InputStream

/** 举报服务 封装所有举报相关的API调用 */
object ReportService {

    /** 举报类型枚举（桥接层，避免直接依赖 SDK 类型） */
    enum class ReportType {
        /** 举报 */
        REPORT,

        /** 反馈 */
        FEEDBACK,
    }

    /** 创建举报 */
    suspend fun createReport(
        reasonCodes: List<ReportCreateParams.ReasonCode>,
        targetId: String?,
        targetType: String?,
        description: String,
        imageUrls: List<String>,
        reportType: ReportType = ReportType.REPORT,
    ): ApiResult<Unit> {
        return IntyNetworkManager.executeRequest("Create Report") {
            // 如果 targetId 和 targetType 为 null（Feedback 模式），使用空字符串和默认类型
            val finalTargetId = targetId ?: ""
            val finalTargetType =
                if (targetType == "USER") {
                    ReportCreateParams.TargetType.USER
                } else {
                    ReportCreateParams.TargetType.AGENT
                }

            // 将桥接层的 ReportType 转换为 SDK 的 ReportType
            val sdkReportType =
                when (reportType) {
                    ReportType.REPORT -> ReportCreateParams.ReportType.REPORT
                    ReportType.FEEDBACK -> ReportCreateParams.ReportType.FEEDBACK
                }

            val reportParams =
                ReportCreateParams.builder()
                    .reasonCodes(reasonCodes)
                    .targetId(finalTargetId)
                    .targetType(finalTargetType)
                    .description(description.trim())
                    .imageUrls(imageUrls)
                    .reportType(sdkReportType)
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
            val fileBytes = inputStream.readBytes()
            val multipartField =
                MultipartField.builder<InputStream>()
                    .value(fileBytes.inputStream())
                    .filename(filename)
                    .build()

            val response =
                IntyNetworkManager.getClient()
                    .api()
                    .v1()
                    .uploadImage(
                        com.inty.api.models.api.v1.V1UploadImageParams.builder()
                            .file(multipartField)
                            .build()
                    )

            val data = response.data()
            val additionalProperties = data?._additionalProperties() ?: emptyMap()
            val imageUrl =
                additionalProperties["url"]?.asString()
                    ?: additionalProperties["image_url"]?.asString()
                    ?: throw IllegalStateException("Image URL not found in response")

            imageUrl
        }
    }
}
