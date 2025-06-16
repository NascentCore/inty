package com.ai.inty.viewmodels

import androidx.lifecycle.viewModelScope
import com.ai.inty.base.BaseActivityViewModel
import com.ai.inty.beans.GENDER
import com.ai.inty.beans.UserProfile
import com.ai.inty.net.IUserApi2
import com.architecture.httplib.core.HttpResult
import com.inty.utils.log.EasyLog
import com.therouter.TheRouter
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class RegInfoActivityViewModel: BaseActivityViewModel() {

    private val userApi2 = TheRouter.get(IUserApi2::class.java)!!

    fun onSave(gender: GENDER, age: String) {
        viewModelScope.launch(Dispatchers.IO) {
            val result = userApi2.setUserProfile(
                userProfile = UserProfile(
                    gender = gender.value,
                    ageGroup = age,
                )
            )
            EasyLog.log("setUserProfile($gender, $age) = $result")

            when (result) {
                is HttpResult.Success -> {
                    closeActivity()
                }
                is HttpResult.Failure -> {
                    showSnackbar(result.message)
                }
            }
        }
    }
}