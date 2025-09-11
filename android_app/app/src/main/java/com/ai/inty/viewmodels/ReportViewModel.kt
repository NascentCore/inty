package com.ai.inty.viewmodels

import android.net.Uri
import androidx.compose.runtime.mutableStateSetOf
import com.ai.inty.base.BaseActivityViewModel
import com.ai.inty.beans.ReportItem
import com.inty.api.client.okhttp.IntyOkHttpClient
import com.inty.api.models.api.v1.report.ReportCreateParams
import com.inty.api.models.api.v1.report.ReportUploadImageParams
import com.inty.utils.log.EasyLog
import com.ai.inty.net.getBaseUrl
import com.ai.inty.net.INTY_CLIENT_SUCCESS_CODE
import com.inty.utils.storage.IntySetting
import com.inty.utils.AppEnv
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import androidx.core.net.toUri

class ReportViewModel : BaseActivityViewModel() {

    var targetID: String = ""
    var targetType: String = "USER"

    private val intyClient by lazy {
        IntyOkHttpClient.builder()
            .apiKey(IntySetting.getCurToken())
            .baseUrl(getBaseUrl())
            .build()
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
        if (selectIDS.isEmpty()) {
            showSnackbar("Please select at least one reason")
            return
        }

        launchWithNetCheck {
            val uploadedImageUrls = mutableListOf<String>()
            for (imageUri in localImages) {
                val uri = imageUri.toUri()
                val inputStream = AppEnv.context.contentResolver.openInputStream(uri)
                inputStream?.let { stream ->
                    val uploadParams = ReportUploadImageParams.builder()
                        .file(stream)
                        .build()
                    
                    val uploadResult = intyClient.api().v1().report().uploadImage(uploadParams)
                    if (uploadResult.code() != INTY_CLIENT_SUCCESS_CODE) {
                        EasyLog.log("Image upload failed with code: ${uploadResult.code()}", EasyLog.ERROR)
                        continue
                    }

                    val dataValue = uploadResult._data()
                    val url = dataValue.asString()
                    if (url == null) {
                        EasyLog.log("Upload response data is not a string: $dataValue", EasyLog.WARN)
                        continue
                    }
                    uploadedImageUrls.add(url)
                }
            }

            val reportParams = ReportCreateParams.builder()
                .reasonIds(selectIDS.map { it.toLong() })
                .targetId(targetID)
                .targetType(
                    if (targetType == "USER") {
                        ReportCreateParams.TargetType.USER
                    } else {
                        ReportCreateParams.TargetType.AGENT
                    }
                )
                .description(description.value.trim())
                .imageUrls(uploadedImageUrls + remoteImages.toList())
                .build()

            val result = intyClient.api().v1().report().create(reportParams)
            if (result.code() != INTY_CLIENT_SUCCESS_CODE) {
                EasyLog.log("Report creation failed with code: ${result.code()}", EasyLog.ERROR)
                showSnackbar(result.message() ?: "Report creation failed")
            } else {
                EasyLog.log("Report created successfully: $result")
                showSnackbar("Report sent")
                closeActivity()
            }
        }
    }

    fun onAddImage(imageUri: Uri) {
        localImages.add(imageUri.toString())
    }

}
