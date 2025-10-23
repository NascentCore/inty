package com.ai.intellimate.agent.report

import ai.sxwl.android.common.base.BaseVM
import ai.sxwl.android.data.api.model.ReportItem
import ai.sxwl.android.data.http.ApiResult
import ai.sxwl.android.data.http.services.ReportService
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.ToastUtils
import ai.sxwl.android.utils.Utils
import android.net.Uri
import androidx.compose.runtime.mutableStateSetOf
import androidx.core.net.toUri
import androidx.lifecycle.viewModelScope
import com.ai.inty.viewmodels.ViewModelEvent
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.io.InputStream

class ReportViewModel : BaseVM() {

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

    var targetID: String = ""
    var targetType: String = "USER"

    // Hard-coded list of report reasons
    private val _reasons =
        MutableStateFlow(
            listOf(
                ReportItem(
                    id = 1,
                    description = "Sensitive or sexual content",
                    code = "SENSITIVE_CONTENT",
                ),
                ReportItem(id = 2, description = "Misinformation", code = "MISINFORMATION"),
                ReportItem(id = 3, description = "Fraud or scams", code = "FRAUD_SCAMS"),
                ReportItem(
                    id = 4,
                    description = "Violation of privacy",
                    code = "PRIVACY_VIOLATION",
                ),
                ReportItem(id = 5, description = "Harmful to minors", code = "HARMFUL_MINORS"),
                ReportItem(
                    id = 6,
                    description = "Violations of my intellectual property",
                    code = "IP_VIOLATION",
                ),
                ReportItem(
                    id = 0,
                    description = "Other, details in report description",
                    code = "OTHER",
                ),
            )
        )
    val reasons = _reasons.asStateFlow()

    var selectIDS = mutableStateSetOf<Int>()

    private val _description = MutableStateFlow("")
    val description = _description.asStateFlow()

    var localImages = mutableStateSetOf<String>()
    var remoteImages = mutableStateSetOf<String>()

    // 提交状态
    private val _isSubmitting = MutableStateFlow(false)
    val isSubmitting = _isSubmitting.asStateFlow()

    fun setDescription(text: String) {
        _description.value = text
    }

    fun submit() {
        if (selectIDS.isEmpty()) {
            ToastUtils.showShort("Please select at least one reason")
            return
        }

        // 如果正在提交，直接返回
        if (_isSubmitting.value) {
            return
        }

        _isSubmitting.value = true

        launchBackground {
            try {
                val uploadedImageUrls = mutableListOf<String>()
                for (imageUri in localImages) {
                    val uri = imageUri.toUri()
                    val inputStream = Utils.getApp().contentResolver.openInputStream(uri)
                    inputStream?.let { stream ->
                        val uploadedUrl = uploadImageWithIntySdk(stream)
                        if (uploadedUrl != null) {
                            uploadedImageUrls.add(uploadedUrl)
                        }
                    }
                }

                val result =
                    ReportService.createReport(
                        reasonIds = selectIDS.map { it.toLong() },
                        targetId = targetID,
                        targetType = targetType,
                        description = description.value.trim(),
                        imageUrls = uploadedImageUrls + remoteImages.toList(),
                    )

                when (result) {
                    is ApiResult.Success -> {
                        ToastUtils.showShort("Submitted successfully. We'll review it soon.")
                        sendEvent(ViewModelEvent.ReportSubmitted)
                    }

                    is ApiResult.Error -> {
                        LogUtils.e("Report creation failed: ${result.message}")
                        ToastUtils.showShort(result.message ?: "Report creation failed")
                    }
                }
            } finally {
                // 无论成功还是失败，都要重置提交状态
                _isSubmitting.value = false
            }
        }
    }

    fun onAddImage(imageUri: Uri) {
        localImages.add(imageUri.toString())
    }

    private suspend fun uploadImageWithIntySdk(inputStream: InputStream): String? {

        val result = ReportService.uploadImage(inputStream, "report-image.jpg")

        return when (result) {
            is ApiResult.Success -> {
                val url = result.data
                LogUtils.i("Image uploaded successfully: $url")
                url
            }

            is ApiResult.Error -> {
                LogUtils.e("Image upload failed: ${result.message}")
                null
            }
        }
    }
}
