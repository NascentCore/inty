package com.ai.intellimate.agent.report

import ai.sxwl.android.common.base.BaseVM
import ai.sxwl.android.data.http.ApiResult
import ai.sxwl.android.data.http.services.ReportService
import ai.sxwl.android.utils.ImageCompressUtils
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.ToastUtils
import ai.sxwl.android.utils.Utils
import android.net.Uri
import androidx.compose.runtime.mutableStateSetOf
import androidx.core.net.toUri
import androidx.lifecycle.viewModelScope
import com.ai.intellimate.R
import com.ai.intellimate.ViewModelEvent
import com.inty.api.models.api.v1.report.ReportCreateParams
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * 举报原因项，包含 SDK 的 ReasonCode 和对应的字符串资源ID
 */
data class ReportReasonItem(
    val reasonCode: ReportCreateParams.ReasonCode,
    val stringResId: Int,
)

class ReportViewModel : BaseVM() {

    // 事件通知机制
    private val _events = MutableSharedFlow<ViewModelEvent>()
    val events: SharedFlow<ViewModelEvent> = _events.asSharedFlow()

    /** 发送事件通知 */
    private fun sendEvent(event: ViewModelEvent) {
        viewModelScope.launch { _events.emit(event) }
    }

    var isFeedbackMode: Boolean = false
    var targetID: String = ""
    var targetType: String = "USER"

    // 使用 SDK 的 ReasonCode 枚举和映射（从 ReportReasonMappings 生成，避免硬编码）
    private val reportReasons =
        ReportReasonMappings.REPORT_REASON_CODE_TO_STRING_RES.map { (reasonCode, stringResId) ->
            ReportReasonItem(reasonCode, stringResId)
        }

    // 使用 SDK 的 ReasonCode 枚举和映射（从 ReportReasonMappings 生成，避免硬编码）
    private val feedbackReasons =
        ReportReasonMappings.FEEDBACK_REASON_CODE_TO_STRING_RES.map { (reasonCode, stringResId) ->
            ReportReasonItem(reasonCode, stringResId)
        }

    private val _reasons = MutableStateFlow(reportReasons)
    val reasons = _reasons.asStateFlow()

    fun updateReasonsForMode() {
        _reasons.value =
            if (isFeedbackMode) {
                feedbackReasons
            } else {
                reportReasons
            }
    }

    // 使用 ReasonCode 而不是 Int ID
    var selectedReasonCodes = mutableStateSetOf<ReportCreateParams.ReasonCode>()

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
        if (selectedReasonCodes.isEmpty()) {
            ToastUtils.showShort(R.string.toast_please_select_reason)
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
                val context = Utils.getApp() ?: return@launchBackground

                for (imageUri in localImages) {
                    val uri = imageUri.toUri()
                    val uploadedUrl = uploadImageWithCompression(context, uri)
                    if (uploadedUrl != null) {
                        uploadedImageUrls.add(uploadedUrl)
                    }
                }

                val result =
                    ReportService.createReport(
                        reasonCodes = selectedReasonCodes.toList(),
                        targetId = if (isFeedbackMode) null else targetID,
                        targetType = if (isFeedbackMode) null else targetType,
                        description = description.value.trim(),
                        imageUrls = uploadedImageUrls + remoteImages.toList(),
                        reportType =
                            if (isFeedbackMode) {
                                ReportService.ReportType.FEEDBACK
                            } else {
                                ReportService.ReportType.REPORT
                            },
                    )

                when (result) {
                    is ApiResult.Success -> {
                        if (isFeedbackMode) {
                            ToastUtils.showShort(R.string.toast_feedback_submitted)
                        } else {
                            ToastUtils.showShort(R.string.toast_submitted_successfully)
                        }
                        sendEvent(ViewModelEvent.ReportSubmitted)
                    }
                    is ApiResult.Error -> {
                        LogUtils.e("Report creation failed: ${result.message}")
                        ToastUtils.showShort(
                            result.message
                                ?: Utils.getApp()?.getString(R.string.toast_report_creation_failed)
                                ?: "Report creation failed"
                        )
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

    private suspend fun uploadImageWithCompression(
        context: android.content.Context,
        uri: Uri,
    ): String? {
        return withContext(Dispatchers.IO) {
            var tempFile: File? = null
            var compressedFile: File? = null
            try {
                // 将 Uri 转换为临时 File
                tempFile = createTempFileFromUri(context, uri) ?: return@withContext null

                // 检查原文件大小，如果已经小于 1024KB，直接使用
                val originalSizeKB = tempFile.length() / 1024
                if (originalSizeKB <= 1024) {
                    // 原文件已经小于 1024KB，直接上传
                    val inputStream = FileInputStream(tempFile)
                    val result = ReportService.uploadImage(inputStream, "report-image.jpg")
                    inputStream.close()

                    return@withContext when (result) {
                        is ApiResult.Success -> {
                            val url = result.data
                            LogUtils.i("Image uploaded successfully (no compression needed): $url")
                            url
                        }

                        is ApiResult.Error -> {
                            LogUtils.e("Image upload failed: ${result.message}")
                            null
                        }
                    }
                }

                // 先尝试转换为 WebP 格式（通常能获得更好的压缩率）
                var webpFile =
                    ImageCompressUtils.convertToWebPSync(
                        context = context,
                        imageFile = tempFile,
                        quality = 85,
                        maxWidth = 1920,
                        maxHeight = 1920,
                    )

                // 如果 WebP 转换成功，检查文件大小
                if (webpFile != null && webpFile.exists()) {
                    val webpSizeKB = webpFile.length() / 1024
                    if (webpSizeKB <= 1024) {
                        // WebP 文件已经小于 1024KB，直接使用
                        compressedFile = webpFile
                    } else {
                        // WebP 文件还是太大，使用 Luban 进一步压缩
                        compressedFile =
                            ImageCompressUtils.compressImageSync(
                                context = context,
                                imageFile = webpFile,
                                config = ImageCompressUtils.CompressConfig(maxSize = 800),
                            )
                        // 如果 Luban 压缩失败，使用更低质量的 WebP
                        if (compressedFile == null || !compressedFile.exists()) {
                            webpFile.delete()
                            webpFile =
                                ImageCompressUtils.convertToWebPSync(
                                    context = context,
                                    imageFile = tempFile,
                                    quality = 70,
                                    maxWidth = 1600,
                                    maxHeight = 1600,
                                )
                            compressedFile = webpFile
                        } else {
                            webpFile.delete() // 清理中间文件
                        }
                    }
                } else {
                    // WebP 转换失败，使用 Luban 压缩原图
                    compressedFile =
                        ImageCompressUtils.compressImageSync(
                            context = context,
                            imageFile = tempFile,
                            config = ImageCompressUtils.CompressConfig(maxSize = 800),
                        )
                }

                if (compressedFile == null || !compressedFile.exists()) {
                    LogUtils.e("Image compression failed")
                    return@withContext null
                }

                // 检查最终文件大小
                val compressedSizeKB = compressedFile.length() / 1024
                if (compressedSizeKB > 1024) {
                    LogUtils.w(
                        "Compressed image size ($compressedSizeKB KB) still exceeds 1024KB limit, trying more aggressive compression"
                    )
                    // 如果还是太大，尝试更激进的 WebP 压缩
                    val moreCompressedFile =
                        ImageCompressUtils.convertToWebPSync(
                            context = context,
                            imageFile = tempFile,
                            quality = 60,
                            maxWidth = 1280,
                            maxHeight = 1280,
                        )
                    if (moreCompressedFile != null && moreCompressedFile.exists()) {
                        val moreCompressedSizeKB = moreCompressedFile.length() / 1024
                        if (moreCompressedSizeKB <= 1024) {
                            compressedFile.delete()
                            compressedFile = moreCompressedFile
                        } else {
                            moreCompressedFile.delete()
                        }
                    }
                }

                // 读取压缩后的文件并上传
                // 根据文件扩展名确定上传的文件名
                val filename =
                    if (compressedFile.name.endsWith(".webp", ignoreCase = true)) {
                        "report-image.webp"
                    } else {
                        "report-image.jpg"
                    }
                val inputStream = FileInputStream(compressedFile)
                val result = ReportService.uploadImage(inputStream, filename)
                inputStream.close()

                when (result) {
                    is ApiResult.Success -> {
                        val url = result.data
                        LogUtils.i(
                            "Image uploaded successfully (compressed from ${originalSizeKB}KB to ${compressedFile.length() / 1024}KB): $url"
                        )
                        url
                    }

                    is ApiResult.Error -> {
                        LogUtils.e("Image upload failed: ${result.message}")
                        null
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("Error uploading image: ${e.message}", e)
                null
            } finally {
                // 清理临时文件
                tempFile?.delete()
                compressedFile?.delete()
            }
        }
    }

    private suspend fun createTempFileFromUri(context: android.content.Context, uri: Uri): File? {
        return withContext(Dispatchers.IO) {
            try {
                val inputStream =
                    context.contentResolver.openInputStream(uri) ?: return@withContext null
                val tempFile = File.createTempFile("upload_", ".jpg", context.cacheDir)
                val outputStream = FileOutputStream(tempFile)

                inputStream.use { input -> outputStream.use { output -> input.copyTo(output) } }

                tempFile
            } catch (e: Exception) {
                LogUtils.e("Error creating temp file from URI: ${e.message}", e)
                null
            }
        }
    }
}
