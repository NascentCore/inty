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

    /** 上传头像 替换: IUserApi.uploadAvatar() 注意: 当前 IntySDK 没有直接的头像上传 API，需要通过通用图片上传实现 */
    suspend fun uploadAvatar(filePath: String): ApiResult<String> {
        return IntyNetworkManager.executeRequest("Upload Avatar") {
            // 当前 IntySDK 没有直接的头像上传 API
            // 可以通过通用图片上传 API 实现，然后更新用户头像字段
            throw Exception("Avatar upload not supported, use image upload API instead")
        }
    }

    /** 删除用户账户 替换: IUserApi.deleteUser() 注意: 当前 IntySDK 没有直接的 delete user API */
    suspend fun deleteUser(): ApiResult<Unit> {
        return IntyNetworkManager.executeRequest("Delete User") {
            // 当前 IntySDK 没有直接的 delete user API
            // 可能需要通过其他方式实现，比如联系管理员
            throw Exception("Delete user not supported, contact administrator")
        }
    }

    /** 获取用户统计信息 替换: IUserApi.getUserStats() */
    suspend fun getUserStats(): ApiResult<UserStats> {
        return IntyNetworkManager.executeRequest("Get User Stats") {
            val response = IntyNetworkManager.getClient().api().v1().users().profile().me()

            val user = response.data() ?: throw IllegalStateException("User data is null")
            UserStats(
                publicAgentsCount = user.publicAgentsCount()?.toInt() ?: 0,
                totalAgentsFollows = user.totalPublicAgentsFollows()?.toInt() ?: 0,
                followerCount = user.followersCount()?.toInt() ?: 0,
                connectorCount = user.connectorCount()?.toInt() ?: 0,
            )
        }
    }

    /** 用户统计信息数据类 */
    data class UserStats(
        val publicAgentsCount: Int,
        val totalAgentsFollows: Int,
        val followerCount: Int,
        val connectorCount: Int,
    )
}
