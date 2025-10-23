package ai.sxwl.android.data.api

import ai.sxwl.android.data.api.model.GoogleLoginRequest
import ai.sxwl.android.data.api.model.GoogleLoginResponse
import ai.sxwl.android.data.api.model.UploadAvatarResponse
import ai.sxwl.android.data.api.model.UserDeleteResponse
import ai.sxwl.android.data.api.model.UserDeletionCheckResponse
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
