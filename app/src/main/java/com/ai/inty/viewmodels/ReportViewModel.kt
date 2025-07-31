package com.ai.inty.viewmodels

import android.net.Uri
import androidx.compose.runtime.mutableStateSetOf
import androidx.lifecycle.viewModelScope
import com.ai.inty.base.BaseActivityViewModel
import com.ai.inty.beans.ReportItem
import com.ai.inty.beans.ReportReq
import com.ai.inty.net.IReportApi
import com.inty.utils.log.EasyLog
import com.therouter.TheRouter
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class ReportViewModel : BaseActivityViewModel() {

    var targetID: String = ""
    var targetType: String = "USER"

    // 延迟获取依赖，避免在构造函数中立即获取导致空指针异常
    val reportApi by lazy {
        TheRouter.get(IReportApi::class.java)
            ?: throw IllegalStateException("IReportApi not found in TheRouter")
    }

    // Hard-coded list of report reasons
    private val _reasons = MutableStateFlow<List<ReportItem>>(
        listOf(
            ReportItem(
                id = 1,
                description = "Sensitive or sexual content",
                code = "SENSITIVE_CONTENT"
            ),
            ReportItem(
                id = 2,
                description = "Misinformation",
                code = "MISINFORMATION"
            ),
            ReportItem(
                id = 3,
                description = "Fraud or scams",
                code = "FRAUD_SCAMS"
            ),
            ReportItem(
                id = 4,
                description = "Violation of privacy",
                code = "PRIVACY_VIOLATION"
            ),
            ReportItem(
                id = 5,
                description = "Harmful to minors",
                code = "HARMFUL_MINORS"
            ),
            ReportItem(
                id = 6,
                description = "Violations of my intellectual property",
                code = "IP_VIOLATION"
            ),
            ReportItem(
                id = 0,
                description = "Other, details in report description",
                code = "OTHER"
            ),
        )
    )
    val reasons = _reasons.asStateFlow()

    var selectIDS = mutableStateSetOf<Int>()

    private val _description = MutableStateFlow("")
    val description = _description.asStateFlow()

    var localImages = mutableStateSetOf<String>()
    var remoteImages = mutableStateSetOf<String>()

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