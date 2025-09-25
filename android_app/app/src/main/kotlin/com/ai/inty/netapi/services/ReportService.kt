package com.ai.inty.netapi.services

import com.ai.inty.netapi.ApiResult
import com.ai.inty.netapi.IntyNetworkManager
import com.inty.api.models.api.v1.report.ReportCreateParams
import java.io.InputStream

/** 举报服务 封装所有举报相关的API调用 */
object ReportService {

    /** 创建举报 */
    suspend fun createReport(
        reasonIds: List<Long>,
        targetId: String,
        targetType: ReportCreateParams.TargetType,
        description: String,
        imageUrls: List<String>,
    ): ApiResult<Unit> {
        return IntyNetworkManager.executeRequest("Create Report") {
            val reportParams =
                ReportCreateParams.builder()
                    .reasonIds(reasonIds)
                    .targetId(targetId)
                    .targetType(targetType)
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
     * 上传图片 注意: 当前 IntySDK 的图片上传 API 解析复杂，暂时返回占位符
     *
     * TODO: 等 IntySDK 完善图片上传 API 后再实现真实上传
     */
    suspend fun uploadImage(
        inputStream: InputStream,
        filename: String = "report-image.jpg",
    ): ApiResult<String> {
        return IntyNetworkManager.executeRequest("Upload Image") {
            // 暂时返回基于时间戳的占位符 URL
            // 等 IntySDK 图片上传 API 完善后再实现真实上传
            "https://placeholder.com/uploaded-image-${System.currentTimeMillis()}.jpg"
        }
    }
}
