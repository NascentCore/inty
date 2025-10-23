package com.ai.inty.viewmodels

import ai.sxwl.android.data.api.model.UserProfile
import ai.sxwl.android.utils.ToastUtils
import ai.sxwl.android.utils.Utils
import android.net.Uri
import androidx.core.net.toUri
import androidx.lifecycle.viewModelScope
import com.ai.inty.R
import com.ai.inty.base.BaseViewModel
import com.ai.inty.base.ViewModelEvent
import com.ai.inty.net.NetServiceMgr
import com.ai.inty.ui.components.EditKey
import com.ai.inty.utils.IntyUserProfileSDK
import com.ai.inty.utils.NetworkErrorHandler
import com.ai.inty.utils.UserProfileManager
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import java.io.File

class MySettingViewModel : BaseViewModel() {

    private val _userProfile = MutableStateFlow<UserProfile>(UserProfile())
    val userProfile = _userProfile.asStateFlow()

    private val _avatarChanged = MutableStateFlow(false)

    private val _isSaving = MutableStateFlow(false)
    val isSaving = _isSaving.asStateFlow()

    // 延迟获取依赖，避免在构造函数中立即获取导致空指针异常
    private val userApi by lazy { NetServiceMgr.getUserApi() }

    fun init(userProfile: UserProfile?) {
        viewModelScope.launch { userProfile?.let { _userProfile.emit(userProfile) } }
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
        launchWithNetCheck {
            _isSaving.value = true
            try {
                if (_avatarChanged.value) {
                    val fileUri = _userProfile.value.avatar?.toUri()

                    if (fileUri?.path == null) {
                        NetworkErrorHandler.showNetworkAwareError("Invalid avatar file")
                        return@launchWithNetCheck
                    }

                    val requestBody =
                        File(fileUri.path!!)
                            .asRequestBody(contentType = "image/jpg".toMediaTypeOrNull())
                    val result =
                        userApi.uploadAvatar(
                            MultipartBody.Part.createFormData("file", "file.png", requestBody)
                        )

                    when (result) {
                        is HttpResult.Success -> {
                            _userProfile.value =
                                _userProfile.value.copy(
                                    // No cropping, just use the provided url.
                                    avatar = result.data.url
                                )
                            // Show success toast for avatar upload
                            viewModelScope.launch(Dispatchers.Main) {
                                ToastUtils.showShort(R.string.saved_successfully)
                            }
                        }

                        is HttpResult.Failure -> {
                            NetworkErrorHandler.showNetworkAwareError(result.message)
                            return@launchWithNetCheck
                        }
                    }
                }

                val updatedProfile = IntyUserProfileSDK.updateUserProfile(_userProfile.value)
                if (updatedProfile != null) {
                    // Show success toast for profile update
                    viewModelScope.launch(Dispatchers.Main) {
                        ToastUtils.showShort(Utils.getApp().getString(R.string.saved_successfully))
                        UserProfileManager.saveUserProfile(updatedProfile)
                    }
                    // 发送用户信息更新成功事件
                    sendEvent(ViewModelEvent.UserProfileUpdated)
                } else {
                    NetworkErrorHandler.showNetworkAwareError("Failed to update user profile")
                }
            } finally {
                _isSaving.value = false
            }
        }
    }

    fun setAvatar(uri: Uri?) {
        //        LogUtils.i("avatar= $uri")
        _avatarChanged.value = true
        _userProfile.value = _userProfile.value.copy(avatar = uri.toString())
    }
}
