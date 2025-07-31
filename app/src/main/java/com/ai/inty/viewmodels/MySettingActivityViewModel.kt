package com.ai.inty.viewmodels

import android.net.Uri
import androidx.core.net.toUri
import androidx.lifecycle.viewModelScope
import com.ai.inty.Constant
import com.ai.inty.EditKey
import com.ai.inty.R
import com.ai.inty.base.BaseActivityViewModel
import com.ai.inty.base.ToastUtils
import com.ai.inty.beans.UserProfile
import com.ai.inty.net.IUserApi
import com.ai.inty.net.IUserApi2
import com.ai.inty.utils.UserProfileManager
import com.architecture.httplib.core.HttpResult
import com.inty.utils.log.EasyLog
import com.therouter.TheRouter
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import java.io.File

class MySettingActivityViewModel: BaseActivityViewModel() {

    private val _userProfile = MutableStateFlow<UserProfile>(UserProfile())
    val userProfile = _userProfile.asStateFlow()

    private val _avatarChanged = MutableStateFlow(false)

    // 延迟获取依赖，避免在构造函数中立即获取导致空指针异常
    private val userApi by lazy {
        TheRouter.get(IUserApi::class.java)
            ?: throw IllegalStateException("IUserApi not found in TheRouter")
    }

    fun init(userProfile: UserProfile?) {
        _userProfile.value = userProfile!!
    }

    fun changeUserProfile(editKey: EditKey, editValue: String) {
        when (editKey) {
            EditKey.Name -> {
                _userProfile.value = _userProfile.value.copy(nickname = editValue)
            }
            EditKey.Pronouns -> {
                _userProfile.value = _userProfile.value.copy(gender = editValue)
            }
            EditKey.Persona -> {
                _userProfile.value = _userProfile.value.copy(description = editValue)
            }
            EditKey.None -> {}
        }
    }

    fun onSave() {
        viewModelScope.launch(Dispatchers.IO) {
            if (_avatarChanged.value) {
                val fileUri = _userProfile.value.avatar?.toUri()
                val requestBody = File(
                    fileUri?.path ?: return@launch
                ).asRequestBody(contentType = "image/jpg".toMediaTypeOrNull())
                val result = userApi.uploadAvatar(MultipartBody.Part.createFormData("file", "file.png", requestBody))
                EasyLog.log("upload avatar = $result")

                when (result) {
                    is HttpResult.Success -> {
                        _userProfile.value = _userProfile.value.copy(
                            avatar = result.data.avatar
                        )
                        // Show success toast for avatar upload
                        viewModelScope.launch(Dispatchers.Main) {
                            ToastUtils.showToast(R.string.saved_successfully)
                        }
                    }
                    is HttpResult.Failure -> {
                        showSnackbar(result.message)
                    }
                }
            }

            val userApi2 by lazy {
                TheRouter.get(IUserApi2::class.java)
                    ?: throw IllegalStateException("IUserApi2 not found in TheRouter")
            }
            val result2 = userApi2.setUserProfile(_userProfile.value)
            EasyLog.log("set user profile = $result2")
            when (result2) {
                is HttpResult.Success -> {
                    // Show success toast for profile update
                    viewModelScope.launch(Dispatchers.Main) {
                        ToastUtils.showToast(R.string.saved_successfully)
                        UserProfileManager.saveUserProfile(_userProfile.value)
                    }
                }
                is HttpResult.Failure -> {
                    showSnackbar(result2.message)
                }
            }


            TheRouter.build(Constant.ACTION_USER_PROFILE_CHANGED).action()

            closeActivity()

        }
    }

    fun setAvatar(uri: Uri?) {
        EasyLog.log("avatar= $uri")
        _avatarChanged.value = true
        _userProfile.value = _userProfile.value.copy(
            avatar = uri.toString()
        )
    }


}