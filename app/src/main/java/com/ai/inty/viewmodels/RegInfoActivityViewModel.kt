package com.ai.inty.viewmodels

import android.content.Intent
import androidx.lifecycle.viewModelScope
import com.ai.inty.MainActivity
import com.ai.inty.base.BaseActivityViewModel
import com.ai.inty.beans.GENDER
import com.ai.inty.beans.UserProfile
import com.ai.inty.net.IUserApi2
import com.architecture.httplib.core.HttpResult
import com.inty.utils.AppEnv
import com.inty.utils.log.EasyLog
import com.therouter.TheRouter
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class RegInfoActivityViewModel: BaseActivityViewModel() {

    private val userApi2 = TheRouter.get(IUserApi2::class.java)!!

    fun onSave(gender: GENDER, age: String) {
        viewModelScope.launch(Dispatchers.IO) {

            //调用接口，需要让服务端存储游客的性别和年龄数据
            val result = userApi2.setUserProfile(
                userProfile = UserProfile(
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
                    showSnackbar(result.message)
                }
            }
        }
    }
}