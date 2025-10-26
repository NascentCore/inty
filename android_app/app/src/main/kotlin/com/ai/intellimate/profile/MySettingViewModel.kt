package com.ai.intellimate.profile

import ai.sxwl.android.common.base.BaseVM
import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.http.services.ImageService
import ai.sxwl.android.data.http.ApiResult
import ai.sxwl.android.data.api.model.UserProfile
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.ToastUtils
import ai.sxwl.android.utils.Utils
import android.net.Uri
import androidx.core.net.toUri
import androidx.lifecycle.viewModelScope
import com.ai.intellimate.R
import com.ai.intellimate.ui.components.EditKey
import com.ai.intellimate.utils.IntyUserProfileSDK
import com.ai.intellimate.utils.NetworkErrorHandler
import com.ai.intellimate.utils.UserProfileManager
import com.ai.intellimate.ViewModelEvent
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import java.io.File

class MySettingViewModel : BaseVM() {

    // 事件通知机制
    private val _events = MutableSharedFlow<ViewModelEvent>()
    val events: SharedFlow<ViewModelEvent> = _events.asSharedFlow()

    private val _userProfile = MutableStateFlow<UserProfile>(UserProfile())
    val userProfile = _userProfile.asStateFlow()

    private val _avatarChanged = MutableStateFlow(false)

    private val _isSaving = MutableStateFlow(false)
    val isSaving = _isSaving.asStateFlow()

    /**
     * 发送事件通知
     */
    private fun sendEvent(event: ViewModelEvent) {
        viewModelScope.launch {
            _events.emit(event)
        }
    }

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
        launchBackground {
            LogUtils.d("MySettingViewModel: Starting onSave operation")
            _isSaving.value = true
            try {
                if (_avatarChanged.value) {
                    LogUtils.d("MySettingViewModel: Avatar has changed, uploading new avatar")
                    val fileUri = _userProfile.value.avatar?.toUri()
                    LogUtils.d("MySettingViewModel: Avatar URI: $fileUri")

                    if (fileUri?.path == null) {
                        LogUtils.e("MySettingViewModel: Invalid avatar file - path is null")
                        NetworkErrorHandler.showNetworkAwareError("Invalid avatar file")
                        return@launchBackground
                    }

                    LogUtils.d("MySettingViewModel: Starting avatar upload - path: ${fileUri.path}")
                    val result = ImageService.uploadImage(fileUri.path!!, croppingAvatar = true)
                    LogUtils.d("MySettingViewModel: Avatar upload result: ${result::class.simpleName}")

                    when (result) {
                        is ApiResult.Success -> {
                            LogUtils.i("MySettingViewModel: Avatar uploaded successfully: ${result.data}")
                            _userProfile.value =
                                _userProfile.value.copy(
                                    // No cropping, just use the provided url.
                                    avatar = result.data
                                )
                            // Show success toast for avatar upload
                            viewModelScope.launch(Dispatchers.Main) {
                                ToastUtils.showShort(R.string.saved_successfully)
                            }
                        }

                        is ApiResult.Error -> {
                            LogUtils.e("MySettingViewModel: Avatar upload failed - Code: ${result.code}, Message: ${result.message}")
                            LogUtils.e("MySettingViewModel: Avatar upload exception: ${result.exception}")
                            
                            // 根据错误码提供更友好的错误信息
                            val errorMessage = when (result.code) {
                                500 -> "服务器内部错误，请稍后重试"
                                400 -> "图片格式不支持或文件过大"
                                401 -> "登录已过期，请重新登录"
                                403 -> "没有权限上传图片"
                                404 -> "上传服务不可用"
                                else -> result.message ?: "上传失败，请重试"
                            }
                            
                            NetworkErrorHandler.showNetworkAwareError(errorMessage)
                            return@launchBackground
                        }
                    }
                } else {
                    LogUtils.d("MySettingViewModel: Avatar unchanged, skipping upload")
                }

                LogUtils.d("MySettingViewModel: Updating user profile")
                val updatedProfile = IntyUserProfileSDK.updateUserProfile(_userProfile.value)
                if (updatedProfile != null) {
                    LogUtils.i("MySettingViewModel: User profile updated successfully")
                    // Show success toast for profile update
                    viewModelScope.launch(Dispatchers.Main) {
                        ToastUtils.showShort(Utils.getApp().getString(R.string.saved_successfully))
                        UserProfileManager.saveUserProfile(updatedProfile)
                    }
                    // 发送用户信息更新成功事件
                    sendEvent(ViewModelEvent.UserProfileUpdated)
                } else {
                    LogUtils.e("MySettingViewModel: Failed to update user profile - returned null")
                    NetworkErrorHandler.showNetworkAwareError("Failed to update user profile")
                }
            } catch (e: Exception) {
                LogUtils.e("MySettingViewModel: onSave exception: ${e.message}")
                LogUtils.e("MySettingViewModel: Exception type: ${e.javaClass.simpleName}")
                LogUtils.e("MySettingViewModel: Exception stack trace:", e)
                NetworkErrorHandler.showNetworkAwareError("Save failed: ${e.message ?: "Unknown error"}")
            } finally {
                LogUtils.d("MySettingViewModel: onSave operation completed")
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
