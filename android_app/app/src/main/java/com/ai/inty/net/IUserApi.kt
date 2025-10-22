package com.ai.inty.net

import com.ai.inty.beans.GoogleLoginRequest
import com.ai.inty.beans.GoogleLoginResponse
import com.ai.inty.beans.UploadAvatarResponse
import com.ai.inty.beans.UserDeleteResponse
import com.ai.inty.beans.UserDeletionCheckResponse
import com.architecture.httplib.core.HttpResult
import okhttp3.MultipartBody
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part

interface IUserApi {

    @POST("/api/v1/auth/google/login")
    suspend fun loginByGoogle(
        @Body loginRequest: GoogleLoginRequest
    ): HttpResult<GoogleLoginResponse>

    @Multipart
    @POST("/api/v1/images")
    suspend fun uploadAvatar(@Part file: MultipartBody.Part): HttpResult<UploadAvatarResponse>

    @GET("/api/v1/users/deletion/check")
    suspend fun userDeletionCheck(): HttpResult<UserDeletionCheckResponse>

    @POST("/api/v1/users/delete-account")
    suspend fun userDeleteAccount(): HttpResult<UserDeleteResponse>
}
