package com.ai.inty.viewmodels

import ai.sxwl.android.data.api.model.GENDER
import ai.sxwl.android.utils.Utils
import android.content.Intent
import com.ai.inty.MainActivity
import com.ai.inty.base.BaseViewModel
import com.ai.inty.base.ViewModelEvent
import com.ai.inty.utils.IntyUserProfileSDK
import com.ai.inty.utils.UserProfileManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class RegInfoViewModel : BaseViewModel() {

    fun onSave(gender: GENDER, age: String) {
        launchWithNetCheck {
            val info = UserProfileManager.getUserProfile()
            // 调用接口，需要让服务端存储游客的性别和年龄数据
            val updatedProfile = info.copy(gender = gender.value, ageGroup = age)

            val result = IntyUserProfileSDK.updateUserProfile(updatedProfile)

            if (result != null) {
                // 用户信息更新成功
                withContext(Dispatchers.Main) {
                    // 更新本地缓存
                    UserProfileManager.saveUserProfile(result)

                    // 发送用户信息更新成功事件
                    sendEvent(ViewModelEvent.UserProfileUpdated)

                    // 重启 MainActivity 以清理所有缓存数据
                    val intent =
                        Intent(Utils.getApp(), MainActivity::class.java).apply {
                            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                        }
                    Utils.getApp().startActivity(intent)
                }
            } else {
                showNetworkAwareError("Failed to update user profile")
            }
        }
    }
}
