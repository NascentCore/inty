package com.ai.inty.utils

import ai.sxwl.android.utils.LogUtils
import com.ai.inty.beans.UserProfile
import com.inty.utils.storage.IntySetting

/** 用户信息的数据管理类 */
object UserProfileManager {

    fun saveUserProfile(userProfile: UserProfile) {
        IntySetting.setUserProfileData("id", userProfile.id)
        IntySetting.setUserProfileData("nickname", userProfile.nickname)
        IntySetting.setUserProfileData("avatar", userProfile.avatar ?: "")
        IntySetting.setUserProfileData("description", userProfile.description ?: "")
        IntySetting.setUserProfileData("email", userProfile.email ?: "")
        IntySetting.setUserProfileData("gender", userProfile.gender ?: "")
        IntySetting.setUserProfileData("auth_type", userProfile.authType)
        IntySetting.setUserProfileData("created_at", userProfile.createdAt)
        IntySetting.setUserProfileData("updated_at", userProfile.updatedAt ?: "")
        IntySetting.setUserProfileData("system_language", userProfile.systemLanguage)
        IntySetting.setUserProfileBoolean("is_active", userProfile.isActive)
        IntySetting.setUserProfileBoolean("is_superuser", userProfile.isSuperuser)
        IntySetting.setUserProfileData("phone", userProfile.phone ?: "")

        // 处理 ageGroup（可能是字符串或其他类型）
        userProfile.ageGroup?.let { ageGroup ->
            when (ageGroup) {
                is String -> IntySetting.setUserProfileData("age_group", ageGroup)
                is Int -> IntySetting.setUserProfileInt("age_group_int", ageGroup)
                else -> IntySetting.setUserProfileData("age_group", ageGroup.toString())
            }
        }

        LogUtils.i("Saved user profile: $userProfile")
    }

    fun getUserProfile(): UserProfile {
        return UserProfile(
            id = IntySetting.getUserProfileData("id") ?: "",
            nickname = IntySetting.getUserProfileData("nickname") ?: "",
            avatar = IntySetting.getUserProfileData("avatar")?.takeIf { it.isNotEmpty() },
            description = IntySetting.getUserProfileData("description")?.takeIf { it.isNotEmpty() },
            email = IntySetting.getUserProfileData("email")?.takeIf { it.isNotEmpty() },
            gender = IntySetting.getUserProfileData("gender")?.takeIf { it.isNotEmpty() },
            authType = IntySetting.getUserProfileData("auth_type") ?: "",
            createdAt = IntySetting.getUserProfileData("created_at") ?: "",
            updatedAt = IntySetting.getUserProfileData("updated_at")?.takeIf { it.isNotEmpty() },
            systemLanguage = IntySetting.getUserProfileData("system_language") ?: "",
            isActive = IntySetting.getUserProfileBoolean("is_active", false),
            isSuperuser = IntySetting.getUserProfileBoolean("is_superuser", false),
            phone = IntySetting.getUserProfileData("phone")?.takeIf { it.isNotEmpty() },
            ageGroup =
                IntySetting.getUserProfileData("age_group")
                    ?: IntySetting.getUserProfileInt("age_group_int", 0).takeIf { it > 0 }
                        .toString(),
        )
    }

    fun hasUserProfile(): Boolean {
        return IntySetting.hasUserProfileData("id")
    }

    fun clearUserProfile() {
        IntySetting.clearAllUserProfileData()
    }
}
