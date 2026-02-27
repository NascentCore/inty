package com.ai.intellimate.agent.report

import ai.sxwl.android.common.base.BaseVM
import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.ReportCreateRequest
import ai.sxwl.android.data.api.model.ReportReasonCode
import ai.sxwl.android.data.api.model.ReportRequestType
import ai.sxwl.android.data.api.model.ReportTargetType
import ai.sxwl.android.utils.ImageCompressUtils
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.ToastUtils
import ai.sxwl.android.utils.Utils
import android.net.Uri
import androidx.compose.runtime.mutableStateSetOf
import androidx.core.net.toUri
import androidx.lifecycle.viewModelScope
import com.ai.intellimate.BuildConfig
import com.ai.intellimate.R
import com.ai.intellimate.ViewModelEvent
import com.architecture.httplib.core.HttpResult
import java.io.File
import java.io.FileOutputStream
import java.util.LinkedHashSet
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody

/** 举报原因项，包含本地 `ReportReasonCode` 和对应的字符串资源ID */
data class ReportReasonItem(val reasonCode: ReportReasonCode, val stringResId: Int)

private const val REPORT_DESCRIPTION_APP_VERSION_MARKER = "[INTY_APP_VERSION]"

internal fun buildReportDescriptionWithAppVersion(
    userDescription: String,
    versionName: String,
    versionCode: Int,
): String {
    if (userDescription.contains(REPORT_DESCRIPTION_APP_VERSION_MARKER)) {
        return userDescription
    }
    val suffix = buildString {
        append("--- ")
        append(REPORT_DESCRIPTION_APP_VERSION_MARKER)
        append(" ---")
        append('\n')
        append("App版本：")
        append(versionName)
        append(" (")
        append(versionCode)
        append(')')
    }
    val separator = if (userDescription.endsWith("\n")) "\n" else "\n\n"
    return userDescription + separator + suffix
}

internal fun mergeEvidenceImageUrls(
    remoteImages: Collection<String>,
    localImages: Collection<String>,
): List<String> {
    val mergedImageUrls = LinkedHashSet<String>()
    remoteImages
        .asSequence()
        .map { it.trim() }
        .filter { it.isNotEmpty() }
        .forEach { mergedImageUrls.add(it) }
    localImages
        .asSequence()
        .map { it.trim() }
        .filter { it.isNotEmpty() }
        .forEach { mergedImageUrls.add(it) }
    return mergedImageUrls.toList()
}

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

    // 使用本地 ReportReasonCode 枚举和映射（从 ReportReasonMappings 生成，避免硬编码）
    private val reportReasons =
        ReportReasonMappings.REPORT_REASON_CODE_TO_STRING_RES.map { (reasonCode, stringResId) ->
            ReportReasonItem(reasonCode, stringResId)
        }

    // 使用本地 ReportReasonCode 枚举和映射（从 ReportReasonMappings 生成，避免硬编码）
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

    // 使用本地 ReasonCode 而不是 Int ID
    var selectedReasonCodes = mutableStateSetOf<ReportReasonCode>()

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

    fun setInitialEvidenceImage(imageUrl: String) {
        val normalizedUrl = imageUrl.trim()
        if (normalizedUrl.isNotEmpty()) {
            remoteImages.add(normalizedUrl)
        }
    }

    fun evidenceImagesForDisplay(): List<String> {
        return mergeEvidenceImageUrls(remoteImages = remoteImages, localImages = localImages)
    }

    fun submit() {
        if (selectedReasonCodes.isEmpty()) {
            ToastUtils.showShort(R.string.toast_please_select_reason)
            return
        }

        val trimmedDescription = description.value.trim()
        if (trimmedDescription.isEmpty()) {
            ToastUtils.showShort(R.string.toast_please_enter_description)
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

                val request =
                    ReportCreateRequest(
                        targetId = if (isFeedbackMode) "" else targetID,
                        targetType =
                            if (!isFeedbackMode && targetType == ReportTargetType.USER.name) {
                                ReportTargetType.USER
                            } else {
                                ReportTargetType.AGENT
                            },
                        reasonCodes = selectedReasonCodes.toList(),
                        description =
                            buildReportDescriptionWithAppVersion(
                                userDescription = trimmedDescription,
                                versionName = BuildConfig.VERSION_NAME,
                                versionCode = BuildConfig.VERSION_CODE,
                            ),
                        imageUrls = uploadedImageUrls + remoteImages.toList(),
                        reportType =
                            if (isFeedbackMode) {
                                ReportRequestType.FEEDBACK
                            } else {
                                ReportRequestType.REPORT
                            },
                    )

                when (val result = NetServiceMgr.getReportApi().createReport(request)) {
                    is HttpResult.Success -> {
                        val responseCode = result.data.code ?: 200
                        if (responseCode == 200) {
                            if (isFeedbackMode) {
                                ToastUtils.showShort(R.string.toast_feedback_submitted)
                            } else {
                                ToastUtils.showShort(R.string.toast_submitted_successfully)
                            }
                            sendEvent(ViewModelEvent.ReportSubmitted)
                        } else {
                            val errorMessage =
                                result.data.message
                                    ?: Utils.getApp()
                                        ?.getString(R.string.toast_report_creation_failed)
                                    ?: "Report creation failed"
                            LogUtils.e(
                                "Report creation failed: code=$responseCode, message=$errorMessage"
                            )
                            ToastUtils.showShort(errorMessage)
                        }
                    }

                    is HttpResult.Failure -> {
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
        val normalizedUri = imageUri.toString().trim()
        if (normalizedUri.isNotEmpty()) {
            localImages.add(normalizedUri)
        }
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
                    val uploadedUrl = uploadReportImage(tempFile, "report-image.jpg")
                    if (uploadedUrl != null) {
                        LogUtils.i("Image uploaded successfully (no compression needed): $uploadedUrl")
                    }
                    return@withContext uploadedUrl
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
                val uploadedUrl = uploadReportImage(compressedFile, filename)
                if (uploadedUrl != null) {
                    LogUtils.i(
                        "Image uploaded successfully (compressed from ${originalSizeKB}KB to ${compressedFile.length() / 1024}KB): $uploadedUrl"
                    )
                }
                uploadedUrl
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

    private suspend fun uploadReportImage(file: File, filename: String): String? {
        return withContext(Dispatchers.IO) {
            val requestBody = file.asRequestBody("image/*".toMediaTypeOrNull())
            val multipart = MultipartBody.Part.createFormData("file", filename, requestBody)
            when (val result = NetServiceMgr.getUserApi().uploadAvatar(multipart)) {
                is HttpResult.Success -> {
                    val resolvedUrl = result.data.url.ifBlank { result.data.avatar_url }
                    if (resolvedUrl.isBlank()) {
                        LogUtils.e("Image upload failed: empty url in response")
                        null
                    } else {
                        resolvedUrl
                    }
                }

                is HttpResult.Failure -> {
                    LogUtils.e("Image upload failed: ${result.message}")
                    null
                }
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
