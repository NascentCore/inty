package com.ai.intellimate.profile

import ai.sxwl.android.common.base.BaseVM
import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.UserProfile
import ai.sxwl.android.utils.ToastUtils
import ai.sxwl.android.utils.Utils
import android.net.Uri
import androidx.core.net.toUri
import androidx.lifecycle.viewModelScope
import com.ai.intellimate.R
import com.ai.intellimate.ViewModelEvent
import com.ai.intellimate.ui.components.EditKey
import com.ai.intellimate.utils.IntyUserProfileSDK
import com.ai.intellimate.utils.NetworkErrorHandler
import com.ai.intellimate.utils.UserProfileManager
import com.architecture.httplib.core.HttpResult
import java.io.File
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

class ModifyProfileViewModel : BaseVM() {

    // 事件通知机制
    private val _events = MutableSharedFlow<ViewModelEvent>()
    val events: SharedFlow<ViewModelEvent> = _events.asSharedFlow()

    private val _userProfile = MutableStateFlow(UserProfile())
    val userProfile = _userProfile.asStateFlow()

    // 保存原始用户信息，用于判断字段是否变化
    private var originalUserProfile: UserProfile? = null

    private val _avatarChanged = MutableStateFlow(false)

    private val _isSaving = MutableStateFlow(false)
    val isSaving = _isSaving.asStateFlow()

    /** 发送事件通知 */
    private fun sendEvent(event: ViewModelEvent) {
        viewModelScope.launch { _events.emit(event) }
    }

    fun init(userProfile: UserProfile?) {
        viewModelScope.launch {
            userProfile?.let {
                _userProfile.emit(it)
                // 保存原始值用于判断是否变化
                originalUserProfile = it
            }
        }
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
            EditKey.Preference,
            EditKey.None -> {}
        }
    }

    /** 单独更新 name/pronoun/persona 字段，在各自的 sheet 中点击 save 时调用 会判断是否真的修改了，如果没变化则不调用接口 */
    fun updateFieldAndSave(editKey: EditKey, editValue: String) {
        launchBackground {
            _isSaving.value = true
            try {
                val original = originalUserProfile ?: return@launchBackground
                val current = _userProfile.value
                var hasChanged = false

                // 先判断是否真的变化了
                when (editKey) {
                    EditKey.Name -> {
                        hasChanged = original.nickname != editValue
                    }

                    EditKey.Pronouns -> {
                        hasChanged = (original.gender ?: "") != editValue
                    }

                    EditKey.Persona -> {
                        hasChanged = (original.description ?: "") != editValue
                    }

                    EditKey.Preference,
                    EditKey.None -> {
                        return@launchBackground
                    }
                }

                // 如果没有变化，只更新本地状态（用户可能在 sheet 中修改了但改回了原值），不调用接口
                if (!hasChanged) {
                    changeUserProfile(editKey, editValue)
                    return@launchBackground
                }

                // 有变化，更新本地状态
                val updatedProfile =
                    when (editKey) {
                        EditKey.Name -> current.copy(nickname = editValue)
                        EditKey.Pronouns -> current.copy(gender = editValue)
                        EditKey.Persona -> current.copy(description = editValue)
                        EditKey.Preference,
                        EditKey.None -> current
                    }
                _userProfile.value = updatedProfile

                // 调用接口更新
                val result = IntyUserProfileSDK.updateUserProfile(updatedProfile)
                if (result != null) {
                    // 更新成功，保存到本地并更新原始值
                    viewModelScope.launch(Dispatchers.Main) {
                        ToastUtils.showShort(R.string.saved_successfully)
                        UserProfileManager.saveUserProfile(result)
                    }
                    // 更新原始值，避免重复更新
                    originalUserProfile = result
                    _userProfile.value = result
                } else {
                    NetworkErrorHandler.showNetworkAwareError("Failed to update user profile")
                    // 更新失败，恢复原值
                    _userProfile.value = current
                }
            } finally {
                _isSaving.value = false
            }
        }
    }

    /**
     * Edit My Persona 界面 save 按钮的保存逻辑 保留原始逻辑：上传头像（如果有变化），然后更新整个 profile 判断是否有变化：只有头像变化或 profile
     * 有变化时才调用接口
     */
    fun onSave() {
        launchBackground {
            _isSaving.value = true
            try {
                val original = originalUserProfile ?: UserProfile()
                val current = _userProfile.value

                // 判断是否有任何变化
                val hasProfileChanged =
                    original.nickname != current.nickname ||
                        (original.gender ?: "") != (current.gender ?: "") ||
                        (original.description ?: "") != (current.description ?: "")

                // 如果没有头像变化且没有 profile 变化，直接返回
                if (!_avatarChanged.value && !hasProfileChanged) {
                    return@launchBackground
                }

                // 上传头像（如果有变化）
                if (_avatarChanged.value) {
                    val fileUri = current.avatar?.toUri()

                    if (fileUri?.path == null) {
                        NetworkErrorHandler.showNetworkAwareError("Invalid avatar file")
                        return@launchBackground
                    }

                    // UCrop 返回的是 file:// URI，可以直接使用 File 读取
                    val file = File(fileUri.path!!)
                    if (!file.exists() || file.length() == 0L) {
                        NetworkErrorHandler.showNetworkAwareError("Image file not found")
                        return@launchBackground
                    }

                    val requestBody =
                        file.asRequestBody(contentType = "image/jpg".toMediaTypeOrNull())
                    val result =
                        NetServiceMgr.getUserApi()
                            .uploadAvatar(
                                MultipartBody.Part.createFormData("file", "file.png", requestBody)
                            )

                    when (result) {
                        is HttpResult.Success -> {
                            _userProfile.value =
                                current.copy(
                                    // No cropping, just use the provided url.
                                    avatar = result.data.url
                                )
                            // 头像上传完毕提示
                            viewModelScope.launch(Dispatchers.Main) {
                                ToastUtils.showShort(R.string.avatar_upload_success)
                            }
                        }
                        is HttpResult.Failure -> {
                            NetworkErrorHandler.showNetworkAwareError(result.message)
                            return@launchBackground
                        }
                    }
                }

                // 更新整个 profile（如果有头像变化或其他 profile 变化）
                if (_avatarChanged.value || hasProfileChanged) {
                    val updatedProfile = IntyUserProfileSDK.updateUserProfile(_userProfile.value)
                    if (updatedProfile != null) {
                        // Show success toast for profile update
                        viewModelScope.launch(Dispatchers.Main) {
                            ToastUtils.showShort(
                                Utils.getApp().getString(R.string.saved_successfully)
                            )
                            UserProfileManager.saveUserProfile(updatedProfile)
                        }
                        // 更新原始值
                        originalUserProfile = updatedProfile
                        _userProfile.value = updatedProfile
                        // 重置头像变化标志
                        _avatarChanged.value = false
                        // 发送用户信息更新成功事件
                        sendEvent(ViewModelEvent.UserProfileUpdated)
                    } else {
                        NetworkErrorHandler.showNetworkAwareError("Failed to update user profile")
                    }
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
