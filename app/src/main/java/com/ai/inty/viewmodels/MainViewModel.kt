package com.ai.inty.viewmodels

import androidx.lifecycle.viewModelScope
import com.ai.inty.base.BaseActivityViewModel
import com.ai.inty.beans.CreateGuestReq
import com.ai.inty.net.IUserApi
import com.inty.utils.AppEnv
import com.inty.utils.log.EasyLog
import com.therouter.TheRouter
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class MainViewModel: BaseActivityViewModel() {

    val userApi: IUserApi = TheRouter.get(IUserApi::class.java)!!

    fun createGuest() {
        viewModelScope.launch(Dispatchers.IO) {
            val result = userApi.createGuest(CreateGuestReq(device_id = AppEnv.DeviceID, AppEnv.locale.language))
            EasyLog.log("create guest = $result", EasyLog.INFO)
        }
    }

}