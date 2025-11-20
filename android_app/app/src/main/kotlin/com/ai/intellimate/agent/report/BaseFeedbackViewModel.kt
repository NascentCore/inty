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
import com.ai.intellimate.R
import com.ai.intellimate.ViewModelEvent
import java.io.InputStream
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * 反馈表单 ViewModel 基类
 *
 * 复用举报与 Feature Request 提交逻辑
 */
abstract class BaseFeedbackViewModel : BaseVM() {

    // 事件通知机制
    private val _events = MutableSharedFlow<ViewModelEvent>()
    val events: SharedFlow<ViewModelEvent> = _events.asSharedFlow()

    /** 发送事件 */
    protected fun sendEvent(event: ViewModelEvent) {
        viewModelScope.launch { _events.emit(event) }
    }

    protected abstract fun createReasonItems(): List<ReportItem>

    private val _reasons = MutableStateFlow(createReasonItems())
    val reasons = _reasons.asStateFlow()

    val selectIDS = mutableStateSetOf<Int>()

    private val _description = MutableStateFlow("")
    val description = _description.asStateFlow()

    val localImages = mutableStateSetOf<String>()
    val remoteImages = mutableStateSetOf<String>()

    // 提交状态
    private val _isSubmitting = MutableStateFlow(false)
    val isSubmitting = _isSubmitting.asStateFlow()

    private var targetID: String = ""
    private var targetType: String = "USER"

    fun updateTarget(targetId: String?, targetType: String?) {
        this.targetID = targetId ?: ""
        this.targetType = targetType ?: "USER"
    }

    fun setDescription(text: String) {
        _description.value = text
    }

    fun submit() {
        if (selectIDS.isEmpty()) {
            ToastUtils.showShort(R.string.toast_please_select_reason)
            return
        }

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
                        ToastUtils.showShort(R.string.toast_submitted_successfully)
                        sendEvent(ViewModelEvent.ReportSubmitted)
                    }
                    is ApiResult.Error -> {
                        LogUtils.e("Feedback creation failed: ${result.message}")
                        ToastUtils.showShort(
                            result.message
                                ?: Utils.getApp()
                                    ?.getString(R.string.toast_report_creation_failed)
                                ?: "Report creation failed"
                        )
                    }
                }
            } finally {
                _isSubmitting.value = false
            }
        }
    }

    fun onAddImage(imageUri: Uri) {
        localImages.add(imageUri.toString())
    }

    private suspend fun uploadImageWithIntySdk(inputStream: InputStream): String? {
        return when (val result = ReportService.uploadImage(inputStream, "report-image.jpg")) {
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
