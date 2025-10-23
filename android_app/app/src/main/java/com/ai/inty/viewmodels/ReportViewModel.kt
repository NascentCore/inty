package com.ai.inty.viewmodels

import ai.sxwl.android.utils.Utils
import android.net.Uri
import androidx.compose.runtime.mutableStateSetOf
import androidx.core.net.toUri
import com.ai.inty.base.BaseViewModel
import com.ai.inty.base.ViewModelEvent
import com.ai.inty.beans.ReportItem
import com.ai.inty.netapi.services.ReportService
import com.inty.api.models.api.v1.report.ReportCreateParams
import com.inty.utils.log.EasyLog
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.io.InputStream

class ReportViewModel : BaseViewModel() {

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
            showSnackbar("Please select at least one reason")
            return
        }

        // 如果正在提交，直接返回
        if (_isSubmitting.value) {
            return
        }

        _isSubmitting.value = true

        launchWithNetCheck {
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
                        targetType =
                            if (targetType == "USER") {
                                ReportCreateParams.TargetType.USER
                            } else {
                                ReportCreateParams.TargetType.AGENT
                            },
                        description = description.value.trim(),
                        imageUrls = uploadedImageUrls + remoteImages.toList(),
                    )

                when (result) {
                    is com.ai.inty.netapi.ApiResult.Success -> {
                        showSnackbar("Submitted successfully. We'll review it soon.")
                        sendEvent(ViewModelEvent.ReportSubmitted)
                    }

                    is com.ai.inty.netapi.ApiResult.Error -> {
                        EasyLog.log("Report creation failed: ${result.message}", EasyLog.ERROR)
                        showSnackbar(result.message ?: "Report creation failed")
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
            is com.ai.inty.netapi.ApiResult.Success -> {
                val url = result.data
                EasyLog.log("Image uploaded successfully: $url")
                url
            }

            is com.ai.inty.netapi.ApiResult.Error -> {
                EasyLog.log("Image upload failed: ${result.message}", EasyLog.ERROR)
                null
            }
        }
    }
}
