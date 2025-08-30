package com.ai.inty.net

import com.ai.inty.beans.CreateGuestReq
import com.ai.inty.beans.CreateGuestResult
import com.ai.inty.beans.GoogleLoginRequest
import com.ai.inty.beans.GoogleLoginResponse
import com.ai.inty.beans.SysMsgResponse
import com.ai.inty.beans.TokenBean
import com.ai.inty.beans.UserDeleteResponse
import com.ai.inty.beans.UserDeletionCheckResponse
import com.ai.inty.beans.UserProfile
import com.ai.inty.beans.UploadAvatarResponse
import com.architecture.httplib.core.HttpResult
import com.therouter.inject.Singleton
import okhttp3.MultipartBody
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Query

@Singleton
interface IUserApi {
    @POST("/api/v1/auth/guest")
    suspend fun createGuest(@Body req: CreateGuestReq): HttpResult<CreateGuestResult>

    @POST("/api/v1/auth/google/login")
    suspend fun loginByGoogle(@Body loginRequest: GoogleLoginRequest): HttpResult<GoogleLoginResponse>

    @Multipart
    @POST("/api/v1/images")
    suspend fun uploadAvatar(@Part file: MultipartBody.Part): HttpResult<UploadAvatarResponse>

    @POST("/api/v1/users/device/register")
    suspend fun regFCM(@Body reqq: TokenBean): HttpResult<Any>

    @GET("/api/v1/notifications/")
    suspend fun getSysMsgs(
        @Query("page") page: Int,
        @Query("page_size") pageSize: Int
    ): HttpResult<SysMsgResponse>


    @GET("/api/v1/users/deletion/check")
    suspend fun userDeletionCheck(): HttpResult<UserDeletionCheckResponse>

    @POST("/api/v1/users/delete-account")
    suspend fun userDeleteAccount(): HttpResult<UserDeleteResponse>

}

