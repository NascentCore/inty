package com.ai.intellimate.profile.data

import ai.sxwl.android.data.api.model.UserProfile
import android.net.Uri
import com.ai.intellimate.utils.UserProfileManager
import java.io.File

class UserProfileRepository(
    private val userProfileDataSource: UserProfileDataSource = UserProfileDataSource()
) {
    suspend fun updateUserAppearance(userProfile: UserProfile, file: File): UserProfile {
        val uploadedImage = userProfileDataSource.uploadImage(file).url
        val updatedUserProfile = userProfileDataSource.updateUserProfile(userProfile.copy(userPhoto = uploadedImage))

        if (updatedUserProfile != null) {
            UserProfileManager.saveUserProfile(updatedUserProfile)
        }

        return updatedUserProfile ?: throw Exception("Failed to update user profile")
    }
}