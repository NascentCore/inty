package com.ai.inty.net

import com.ai.inty.beans.CreateGuestReq
import com.ai.inty.beans.CreateGuestResult
import com.architecture.httplib.core.HttpResult
import com.therouter.inject.Singleton
import retrofit2.http.Body
import retrofit2.http.POST

@Singleton
interface IUserApi {
    @POST("/api/v1/auth/guest")
    suspend fun createGuest(@Body req: CreateGuestReq): HttpResult<CreateGuestResult>

}

