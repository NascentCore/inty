package com.ai.intellimate.utils

import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.UserProfile
import ai.sxwl.android.data.api.model.UserProfileUpdateRequest
import ai.sxwl.android.utils.LogUtils
import com.architecture.httplib.core.HttpResult

/** 用户信息远端读写入口。保留原对象名以避免上层调用点一次性改动过大。 */
object IntyUserProfileSDK {

    /** 获取用户信息 */
    suspend fun getUserProfile(): UserProfile? {
        return try {
            val result = NetServiceMgr.getUserApi().getMe()

            when (result) {
                is HttpResult.Success -> {
                    val userProfile = result.data
                    LogUtils.d("Updated user profile from retrofit: ${userProfile.nickname}")
                    userProfile
                }
                is HttpResult.Failure -> {
                    LogUtils.e("Failed to get user profile with retrofit: ${result.message}")
                    null
                }
            }
        } catch (e: Exception) {
            LogUtils.e("Exception getting user profile with retrofit: ${e.message}")
            null
        }
    }

    /** 更新用户信息 */
    suspend fun updateUserProfile(userProfile: UserProfile): UserProfile? {
        return try {
            // Phase 2 迁移：使用 Retrofit 本地 DTO，避免 app 层继续依赖 SDK builder 类型。
            val request =
                UserProfileUpdateRequest(
                    nickname = userProfile.nickname.takeIf { it.isNotBlank() },
                    avatar = userProfile.avatar.takeIf { !it.isNullOrBlank() },
                    userPhoto = userProfile.userPhoto.takeIf { !it.isNullOrBlank() },
                    gender = userProfile.gender.takeIf { !it.isNullOrBlank() },
                    ageGroup = userProfile.ageGroup.takeIf { !it.isNullOrBlank() },
                    description = userProfile.description.takeIf { !it.isNullOrBlank() },
                    systemLanguage = userProfile.systemLanguage.takeIf { it.isNotBlank() },
                )

            val result = NetServiceMgr.getUserApi().updateProfile(request)

            when (result) {
                is HttpResult.Success -> {
                    val updatedUserProfile = result.data
                    LogUtils.d("Updated user profile with retrofit: ${updatedUserProfile.nickname}")
                    updatedUserProfile
                }
                is HttpResult.Failure -> {
                    LogUtils.e("Failed to update user profile with retrofit: ${result.message}")
                    null
                }
            }
        } catch (e: Exception) {
            LogUtils.e("Exception updating user profile with retrofit: ${e.message}")
            null
        }
    }
}
