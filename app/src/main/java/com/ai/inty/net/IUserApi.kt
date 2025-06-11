package com.ai.inty.net

import com.ai.inty.beans.CreateGuestReq
import com.ai.inty.beans.CreateGuestResult
import com.ai.inty.beans.UserProfile
import com.architecture.httplib.core.HttpResult
import com.therouter.inject.Singleton
import okhttp3.MultipartBody
import retrofit2.http.Body
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part

@Singleton
interface IUserApi {
    @POST("/api/v1/auth/guest")
    suspend fun createGuest(@Body req: CreateGuestReq): HttpResult<CreateGuestResult>

    @Multipart
    @POST("/api/v1/users/avatar")
    suspend fun uploadAvatar(@Part file: MultipartBody.Part): HttpResult<UserProfile>


}

