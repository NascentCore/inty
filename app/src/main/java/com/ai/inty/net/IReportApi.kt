package com.ai.inty.net

import com.ai.inty.beans.ReportItem
import com.ai.inty.beans.ReportReq
import com.ai.inty.beans.ReportResponse
import com.architecture.httplib.core.HttpResult
import com.therouter.inject.Singleton
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST


@Singleton
interface IReportApi {
    @GET("/api/v1/report/reasons")
    suspend fun getReasons(): HttpResult<List<ReportItem>>

    @POST("/api/v1/report/")
    suspend fun report(@Body req: ReportReq): ReportResponse
}