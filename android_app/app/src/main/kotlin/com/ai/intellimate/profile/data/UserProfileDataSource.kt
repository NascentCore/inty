package com.ai.intellimate.profile.data

import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.UploadAvatarResponse
import ai.sxwl.android.data.api.model.UserProfile
import ai.sxwl.android.utils.LogUtils
import com.ai.intellimate.utils.IntyUserProfileSDK
import com.ai.intellimate.utils.request
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import java.io.File

class UserProfileDataSource {
    suspend fun updateUserProfile(userProfile: UserProfile): UserProfile? {
        return IntyUserProfileSDK.updateUserProfile(userProfile)
    }

    /** 上传图片 */
    suspend fun uploadImage(file: File): UploadAvatarResponse {
        return request(operation = "Image upload") {
            // 记录文件信息，便于调试
            LogUtils.i(
                "AgentRemoteDatasource - Uploading image: ${file.name}, size: ${file.length() / 1024}KB"
            )
            val requestFile = file.asRequestBody("image/*".toMediaTypeOrNull())
            val body = MultipartBody.Part.createFormData("file", file.name, requestFile)

            NetServiceMgr.getUserApi().uploadAvatar(body)
        }
    }
}