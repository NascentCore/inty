package com.ai.inty.utils

import ai.sxwl.android.utils.LogUtils
import com.ai.inty.beans.UserProfile
import com.ai.inty.netapi.services.UserService

/** 使用 inty-sdk 进行用户信息操作的工具类 */
object IntyUserProfileSDK {

    /** 获取用户信息 */
    suspend fun getUserProfile(): UserProfile? {
        return try {
            val result = UserService.getUserProfile()

            when (result) {
                is com.ai.inty.netapi.ApiResult.Success -> {
                    val userProfile = result.data
                    LogUtils.i("Updated user profile from inty-sdk: ${userProfile.nickname}")
                    userProfile
                }

                is com.ai.inty.netapi.ApiResult.Error -> {
                    LogUtils.e("Failed to get user profile with inty-sdk: ${result.message}")
                    null
                }
            }
        } catch (e: Exception) {
            LogUtils.e("Exception getting user profile with inty-sdk: ${e.message}")
            null
        }
    }

    /** 更新用户信息 */
    suspend fun updateUserProfile(userProfile: UserProfile): UserProfile? {
        return try {

            val result = UserService.updateUserProfile(userProfile)

            when (result) {
                is com.ai.inty.netapi.ApiResult.Success -> {
                    val updatedUserProfile = result.data
                    LogUtils.d("Updated user profile with inty-sdk: ${updatedUserProfile.nickname}")
                    updatedUserProfile
                }

                is com.ai.inty.netapi.ApiResult.Error -> {
                    LogUtils.e("Failed to update user profile with inty-sdk: ${result.message}")
                    null
                }
            }
        } catch (e: Exception) {
            LogUtils.e("Exception updating user profile with inty-sdk: ${e.message}")
            null
        }
    }
}
