package com.ai.inty.viewmodels

import androidx.compose.runtime.mutableStateListOf
import androidx.lifecycle.viewModelScope
import com.ai.inty.base.BaseActivityViewModel
import com.ai.inty.beans.SysMsgItem
import com.ai.inty.net.IUserApi
import com.architecture.httplib.core.HttpResult
import com.inty.utils.log.EasyLog
import com.therouter.TheRouter
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class SysMsgsActivityViewModel: BaseActivityViewModel() {

    // 延迟获取依赖，避免在构造函数中立即获取导致空指针异常
    private val userApi by lazy {
        TheRouter.get(IUserApi::class.java)
            ?: throw IllegalStateException("IUserApi not found in TheRouter")
    }

    val sysMsgs = mutableStateListOf<SysMsgItem>()

    init {
        queryHistory()
    }


    fun queryHistory() {
        viewModelScope.launch(Dispatchers.IO) {
            val result = userApi.getSysMsgs(1, 20)
            EasyLog.log("getSysMsgs = $result")
            when (result) {
                is HttpResult.Success -> {
                    sysMsgs.addAll(result.data.list)
                }
                is HttpResult.Failure -> {
                    showSnackbar(result.message)
                }
            }
        }
    }
}