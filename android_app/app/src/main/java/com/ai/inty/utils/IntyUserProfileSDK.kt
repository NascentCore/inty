package com.ai.inty.utils

import com.ai.inty.beans.UserProfile
import com.ai.inty.net.INTY_CLIENT_SUCCESS_CODE
import com.ai.inty.net.getBaseUrl
import com.inty.api.client.okhttp.IntyOkHttpClient
import com.inty.api.models.api.v1.users.profile.ProfileUpdateParams
import com.inty.utils.log.EasyLog
import com.inty.utils.storage.IntySetting
import com.inty.api.models.api.v1.users.profile.User as IntyUser

/**
 * 使用 inty-sdk 进行用户信息操作的工具类
 */
object IntyUserProfileSDK {

    /**
     * 获取用户信息
     */
    suspend fun getUserProfile(): UserProfile? {
        return try {
            EasyLog.log("Getting user profile with inty-sdk...")
            
            val intyClient = IntyOkHttpClient.builder()
                .apiKey(IntySetting.getCurToken())
                .baseUrl(getBaseUrl())
                .build()

            val response = intyClient.api().v1().users().profile().retrieve()
            EasyLog.log("getUserProfile result: $response")

            if (response.code() == INTY_CLIENT_SUCCESS_CODE) {
                val intyUser = response.data()!!
                val userProfile = convertIntyUserToUserProfile(intyUser)
                EasyLog.log("Updated user profile from inty-sdk: ${userProfile.nickname}")
                userProfile
            } else {
                EasyLog.log("Failed to get user profile with inty-sdk: ${response.message()}", EasyLog.ERROR)
                null
            }
        } catch (e: Exception) {
            EasyLog.log("Exception getting user profile with inty-sdk: ${e.message}", EasyLog.ERROR)
            null
        }
    }

    /**
     * 更新用户信息
     */
    suspend fun updateUserProfile(userProfile: UserProfile): UserProfile? {
        return try {
            EasyLog.log("Updating user profile with inty-sdk...")
            
            val intyClient = IntyOkHttpClient.builder()
                .apiKey(IntySetting.getCurToken())
                .baseUrl(getBaseUrl())
                .build()

            val updateParams = ProfileUpdateParams.builder()
                .nickname(userProfile.nickname)
                .avatar(userProfile.avatar)
                .description(userProfile.description)
                .gender(userProfile.gender?.let { 
                    when (it) {
                        "MALE" -> com.inty.api.models.api.v1.users.profile.Gender.MALE
                        "FEMALE" -> com.inty.api.models.api.v1.users.profile.Gender.FEMALE
                        "OTHER" -> com.inty.api.models.api.v1.users.profile.Gender.OTHER
                        else -> null
                    }
                })
                .ageGroup(userProfile.ageGroup?.toString())
                .phone(userProfile.phone)
                .systemLanguage(userProfile.systemLanguage)
                .build()

            val response = intyClient.api().v1().users().profile().update(updateParams)
            EasyLog.log("updateUserProfile result: $response")

            val updatedUserProfile = convertIntyUserToUserProfile(response)
            EasyLog.log("Updated user profile with inty-sdk: ${updatedUserProfile.nickname}")
            updatedUserProfile
        } catch (e: Exception) {
            EasyLog.log("Exception updating user profile with inty-sdk: ${e.message}", EasyLog.ERROR)
            null
        }
    }

    /**
     * 将 inty-sdk 的 User 对象转换为 UserProfile 对象
     */
    private fun convertIntyUserToUserProfile(intyUser: IntyUser): UserProfile {
        return UserProfile(
            id = intyUser.id(),
            nickname = intyUser.nickname() ?: "",
            avatar = intyUser.avatar(),
            description = intyUser.description(),
            email = intyUser.email(),
            gender = intyUser.gender()?.toString(),
            authType = intyUser.authType(),
            createdAt = intyUser.createdAt().toString(),
            updatedAt = intyUser.updatedAt()?.toString(),
            systemLanguage = intyUser.systemLanguage() ?: "",
            isActive = intyUser.isActive(),
            isSuperuser = intyUser.isSuperuser() ?: false,
            phone = intyUser.phone(),
            ageGroup = intyUser.ageGroup(),
            readableId = intyUser.readableId(),
            publicAgentsCount = intyUser.publicAgentsCount()?.toInt() ?: 0,
            totalAgentsFollows = intyUser.totalPublicAgentsFollows()?.toInt() ?: 0,
            followerCount = intyUser.followersCount()?.toInt() ?: 0,
            connectorCount = intyUser.connectorCount()?.toInt() ?: 0
        )
    }
}
