package com.ai.intellimate.login

import ai.sxwl.android.common.base.BaseVM
import ai.sxwl.android.data.api.model.GENDER
import ai.sxwl.android.utils.Utils
import android.content.Intent
import androidx.lifecycle.viewModelScope
import com.ai.intellimate.MainActivity
import com.ai.intellimate.utils.IntyUserProfileSDK
import com.ai.intellimate.utils.NetworkErrorHandler
import com.ai.intellimate.utils.UserProfileManager
import com.ai.intellimate.ViewModelEvent
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class RegInfoViewModel : BaseVM() {
// 事件通知机制
    private val _events = MutableSharedFlow<ViewModelEvent>()
    val events: SharedFlow<ViewModelEvent> = _events.asSharedFlow()

    /**
     * 发送事件通知
     */
    private fun sendEvent(event: ViewModelEvent) {
        viewModelScope.launch {
            _events.emit(event)
        }
    }

    fun onSave(gender: GENDER, age: String) {
        launchBackground {
            val info = UserProfileManager.getUserProfile()
// 调用接口，需要让服务端存储游客的性别和年龄数据
            val updatedProfile = info.copy(gender = gender.value, ageGroup = age)

            val result = IntyUserProfileSDK.updateUserProfile(updatedProfile)

            if (result != null) {
// 用户信息更新成功
                withContext(Dispatchers.Main) {
// 更新本地服务器
                    UserProfileManager.saveUserProfile(result)
// 发送用户信息更新成功事件
                    sendEvent(ViewModelEvent.UserProfileUpdated)
// 重启MainActivity以清理所有服务器数据
                    val intent =
                        Intent(Utils.getApp(), MainActivity::class.java).apply {
                            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                        }
                    Utils.getApp().startActivity(intent)
                }
            } else {
                NetworkErrorHandler.showNetworkAwareError("Failed to update user profile")
            }
        }
    }
}
