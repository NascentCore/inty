package com.ai.inty.viewmodels

import android.content.Intent
import com.ai.inty.MainActivity
import com.ai.inty.base.BaseActivityViewModel
import com.ai.inty.beans.GENDER
import com.ai.inty.net.IUserApi2
import com.ai.inty.utils.UserProfileManager
import com.architecture.httplib.core.HttpResult
import com.inty.utils.AppEnv
import com.inty.utils.log.EasyLog
import com.therouter.TheRouter
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class RegInfoViewModel : BaseActivityViewModel() {

    // 延迟获取依赖，避免在构造函数中立即获取导致空指针异常
    private val userApi2 by lazy {
        TheRouter.get(IUserApi2::class.java)
            ?: throw IllegalStateException("IUserApi2 not found in TheRouter")
    }

    fun onSave(gender: GENDER, age: String) {
        launchWithNetCheck {
            val info = UserProfileManager.getUserProfile()
            //调用接口，需要让服务端存储游客的性别和年龄数据
            val result = userApi2.setUserProfile(
                userProfile = info.copy(
                    gender = gender.value,
                    ageGroup = age,
                )
            )
            EasyLog.log("setUserProfile($gender, $age) = $result")

            when (result) {
                is HttpResult.Success -> {
                    //用户信息更新成功
                    withContext(Dispatchers.Main) {
                        // 关闭当前设置页面
                        closeActivity()

                        // 重启 MainActivity 以清理所有缓存数据
                        val intent = Intent(AppEnv.context, MainActivity::class.java).apply {
                            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                        }
                        AppEnv.context.startActivity(intent)
                    }
                }

                is HttpResult.Failure -> {
                    showNetworkAwareError(result.message)
                }
            }
        }
    }
}
