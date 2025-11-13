package ai.sxwl.android.data.http.services

import ai.sxwl.android.data.api.model.UserProfile
import ai.sxwl.android.data.http.ApiResult
import ai.sxwl.android.data.http.IntyNetworkManager
import ai.sxwl.android.data.http.models.toUserProfile
import com.inty.api.models.api.v1.users.profile.ProfileUpdateParams

/** 用户服务 封装所有用户相关的API调用 替换原有的 IUserApi 用户相关方法 */
object UserService {

    /** 获取用户信息 替换: IUserApi.getUserProfile() */
    suspend fun getUserProfile(): ApiResult<UserProfile> {
        return IntyNetworkManager.executeRequest("Get User Profile") {
            val response = IntyNetworkManager.getClient().api().v1().users().profile().me()

            response.data()?.toUserProfile() ?: throw IllegalStateException("User data is null")
        }
    }

    /** 更新用户信息 替换: IUserApi.setUserProfile() */
    suspend fun updateUserProfile(userProfile: UserProfile): ApiResult<UserProfile> {
        return IntyNetworkManager.executeRequest("Update User Profile") {
            val builder = ProfileUpdateParams.builder()
            if (userProfile.nickname.isNotEmpty()) {
                builder.nickname(userProfile.nickname)
            }
            if (!userProfile.avatar.isNullOrEmpty()) {
                builder.avatar(userProfile.avatar)
            }
            if (!userProfile.description.isNullOrEmpty()) {
                builder.description(userProfile.description)
            }
            if (!userProfile.ageGroup.isNullOrEmpty()) {
                builder.ageGroup(userProfile.ageGroup)
            }
            val genderObj =
                userProfile.gender?.let {
                    when (it) {
                        "MALE" -> com.inty.api.models.api.v1.users.profile.Gender.MALE
                        "FEMALE" -> com.inty.api.models.api.v1.users.profile.Gender.FEMALE
                        "OTHER" -> com.inty.api.models.api.v1.users.profile.Gender.OTHER
                        else -> null
                    }
                }
            if (genderObj != null) {
                builder.gender(genderObj)
            }
            val updateParams = builder.build()

            val response =
                IntyNetworkManager.getClient().api().v1().users().profile().update(updateParams)

            response.data()?.toUserProfile()
                ?: throw IllegalStateException("Updated user data is null")
        }
    }

    /** 上传头像 替换: IUserApi.uploadAvatar() */
    suspend fun uploadAvatar(
        inputStream: java.io.InputStream,
        filename: String = "avatar.jpg"
    ): ApiResult<String> {
        return IntyNetworkManager.executeRequest("Upload Avatar") {
            val response =
                IntyNetworkManager.getClient()
                    .api()
                    .v1()
                    .uploadImage(
                        com.inty.api.models.api.v1.V1UploadImageParams.builder()
                            .file(inputStream.readBytes())
                            .build()
                    )

            val data = response.data()
            val additionalProperties = data?._additionalProperties() ?: emptyMap()
            val imageUrl = additionalProperties["url"]?.asString()
                ?: additionalProperties["image_url"]?.asString()
                ?: additionalProperties["avatar_url"]?.asString()
                ?: throw IllegalStateException("Image URL not found in response")

            imageUrl
        }
    }

    /** 删除用户账户 替换: IUserApi.deleteUser() */
    suspend fun deleteUser(): ApiResult<Unit> {
        return IntyNetworkManager.executeRequest("Delete User") {
            IntyNetworkManager.getClient()
                .api()
                .v1()
                .users()
                .deleteAccount()
        }
    }

    /** Register device token for FCM push notifications */
    suspend fun registerDeviceToken(fcmToken: String): ApiResult<Unit> {
        return IntyNetworkManager.executeRequest("Register Device Token") {
            // Use Retrofit directly since this endpoint is not in inty_sdk
            // (include_in_schema=False in backend, so not generated in SDK)
            val api = ai.sxwl.android.data.api.NetServiceMgr.getUserApi()
            val request =
                ai.sxwl.android.data.api.model.DeviceTokenRegisterRequest(token = fcmToken)
            when (val result = api.registerDeviceToken(request)) {
                is com.architecture.httplib.core.HttpResult.Success -> {
                    Unit
                }

                is com.architecture.httplib.core.HttpResult.Failure -> {
                    throw Exception(result.message)
                }
            }
        }
    }

}
