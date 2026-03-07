package ai.sxwl.android.data.api

import ai.sxwl.android.data.api.model.ReportCreateApiResponse
import ai.sxwl.android.data.api.model.ReportCreateRequest
import com.architecture.httplib.core.HttpResult
import retrofit2.http.Body
import retrofit2.http.POST

interface IReportApi {
    @POST("/api/v1/report/")
    suspend fun createReport(
        @Body request: ReportCreateRequest
    ): HttpResult<ReportCreateApiResponse>
}
