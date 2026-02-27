package ai.sxwl.android.data.http.services

import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.ReportCreateApiResponse
import ai.sxwl.android.data.api.model.ReportCreateRequest
import ai.sxwl.android.data.api.model.ReportReasonCode
import ai.sxwl.android.data.api.model.ReportRequestType
import ai.sxwl.android.data.api.model.ReportTargetType
import ai.sxwl.android.data.http.ApiResult
import ai.sxwl.android.data.http.IntyNetworkManager
import com.architecture.httplib.core.HttpResult
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

    /**
     * 新的 Retrofit 举报创建入口（Phase 1）。
     *
     * 该入口使用 `core/data/api/model` 下的本地 DTO，避免业务层继续透出 `com.inty.api.*` 类型。
     */
    suspend fun createReport(request: ReportCreateRequest): ApiResult<Unit> {
        return IntyNetworkManager.executeRequest("Create Report") {
            when (val result = NetServiceMgr.getReportApi().createReport(request)) {
                is HttpResult.Success -> validateReportCreateResponse(result.data)
                is HttpResult.Failure -> {
                    throw IllegalStateException(
                        "Report creation failed: code=${result.code}, message=${result.message}"
                    )
                }
            }
        }
    }

    /**
     * 旧签名保留用于平滑迁移（调用点暂不改动）。
     *
     * Phase 2 将逐步改为直接传 `ReportCreateRequest`。
     */
    suspend fun createReport(
        reasonCodes: List<ReportCreateParams.ReasonCode>,
        targetId: String?,
        targetType: String?,
        description: String,
        imageUrls: List<String>,
        reportType: ReportType = ReportType.REPORT,
    ): ApiResult<Unit> {
        val request =
            ReportCreateRequest(
                targetId = targetId ?: "",
                targetType = mapTargetType(targetType),
                reasonCodes = reasonCodes.map(::mapLegacyReasonCode),
                description = description.trim(),
                imageUrls = imageUrls,
                reportType = mapReportType(reportType),
            )
        return createReport(request)
    }

    private fun validateReportCreateResponse(response: ReportCreateApiResponse) {
        val responseCode = response.code ?: 200
        if (responseCode != 200) {
            throw IllegalStateException(
                "Report creation failed with code: $responseCode, message=${response.message}"
            )
        }
    }

    private fun mapTargetType(targetType: String?): ReportTargetType {
        return if (targetType == ReportTargetType.USER.name) {
            ReportTargetType.USER
        } else {
            ReportTargetType.AGENT
        }
    }

    private fun mapReportType(reportType: ReportType): ReportRequestType {
        return when (reportType) {
            ReportType.REPORT -> ReportRequestType.REPORT
            ReportType.FEEDBACK -> ReportRequestType.FEEDBACK
        }
    }

    private fun mapLegacyReasonCode(reasonCode: ReportCreateParams.ReasonCode): ReportReasonCode {
        return ReportReasonCode.valueOf(reasonCode.name)
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
