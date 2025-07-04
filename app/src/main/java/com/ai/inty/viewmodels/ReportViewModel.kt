package com.ai.inty.viewmodels

import android.net.Uri
import androidx.compose.runtime.mutableStateSetOf
import androidx.lifecycle.viewModelScope
import com.ai.inty.base.BaseActivityViewModel
import com.ai.inty.beans.ReportItem
import com.ai.inty.beans.ReportReq
import com.ai.inty.beans.ReportResponse
import com.ai.inty.net.IReportApi
import com.architecture.httplib.core.HttpResult
import com.inty.utils.log.EasyLog
import com.therouter.TheRouter
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class ReportViewModel : BaseActivityViewModel() {

    var targetID: String = ""
    var targetType: String = "USER"

    val reportApi = TheRouter.get(IReportApi::class.java)!!

    private val _reasons = MutableStateFlow<List<ReportItem>>(listOf())
    val reasons = _reasons.asStateFlow()

    var selectIDS = mutableStateSetOf<Int>()

    private val _description = MutableStateFlow("")
    val description = _description.asStateFlow()

    var localImages = mutableStateSetOf<String>()
    var remoteImages = mutableStateSetOf<String>()


    init {
        getReasons()
    }

    fun getReasons() {
        viewModelScope.launch(Dispatchers.IO) {
            val result = reportApi.getReasons()

            EasyLog.log("getReasons = ${result}")

            when (result) {
                is HttpResult.Success -> {
                    _reasons.value = result.data
                }
                is HttpResult.Failure -> {
                    EasyLog.log("getReasons failed", EasyLog.ERROR)
                    showSnackbar(result.message)
                }
            }
        }
    }

    fun setDescription(text: String) {
        _description.value = text
    }

    fun submit() {
        // 必填项检查
        if (selectIDS.isEmpty()) {
            showSnackbar("Please select at least one reason")
            return
        }
        
        if (description.value.trim().isEmpty()) {
            showSnackbar("Please fill in the report description")
            return
        }
        
        viewModelScope.launch(Dispatchers.IO) {
            val result = reportApi.report(
                ReportReq(
                    reasonIds = selectIDS.toList(),
                    description = description.value.trim(),
                    targetId = targetID,
                    targetType = targetType,
                )
            )
            EasyLog.log(result)
            if (result.code == 200) {
                showSnackbar("Report Successfully")
                closeActivity()
            } else {
                EasyLog.log("submit report failed", EasyLog.ERROR)
                showSnackbar(result.message)
            }
        }
    }

    fun onAddImage(imageUri: Uri) {
        localImages.add(imageUri.toString())
    }

}