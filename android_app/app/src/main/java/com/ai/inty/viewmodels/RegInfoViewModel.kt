package com.ai.inty.viewmodels

import android.content.Intent
import com.ai.inty.MainActivity
import com.ai.inty.base.BaseActivityViewModel
import com.ai.inty.beans.GENDER
import com.ai.inty.utils.IntyUserProfileSDK
import com.ai.inty.utils.UserProfileManager
import com.inty.utils.AppEnv
import com.inty.utils.log.EasyLog
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class RegInfoViewModel : BaseActivityViewModel() {

    fun onSave(gender: GENDER, age: String) {
        launchWithNetCheck {
            val info = UserProfileManager.getUserProfile()
            // 调用接口，需要让服务端存储游客的性别和年龄数据
            val updatedProfile = info.copy(gender = gender.value, ageGroup = age)

            val result = IntyUserProfileSDK.updateUserProfile(updatedProfile)
            EasyLog.log("setUserProfile($gender, $age) = $result")

            if (result != null) {
                // 用户信息更新成功
                withContext(Dispatchers.Main) {
                    // 关闭当前设置页面
                    closeActivity()

                    // 重启 MainActivity 以清理所有缓存数据
                    val intent =
                        Intent(AppEnv.context, MainActivity::class.java).apply {
                            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                        }
                    AppEnv.context.startActivity(intent)
                }
            } else {
                showNetworkAwareError("Failed to update user profile")
            }
        }
    }
}
