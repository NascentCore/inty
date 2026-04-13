package com.inty.imate.system.report

import android.content.Context
import android.net.Uri
import androidx.compose.runtime.mutableStateSetOf
import androidx.core.net.toUri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ai.core.utils.AppUtils
import com.ai.core.utils.ImageCompressUtils
import com.ai.core.utils.ToastUtils
import com.inty.imate.BuildConfig
import com.inty.imate.R
import com.inty.imate.system.SystemReportEntry
import com.inty.imate.system.report.data.CreateReportOutcome
import com.inty.imate.system.report.data.ReportCreateRequest
import com.inty.imate.system.report.data.ReportReasonCode
import com.inty.imate.system.report.data.ReportRemoteDataSource
import com.inty.imate.system.report.data.ReportRequestType
import com.inty.imate.system.report.data.ReportTargetType
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import java.io.File
import java.io.FileOutputStream
import javax.inject.Inject
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@HiltViewModel
class ReportViewModel
@Inject
constructor(
    private val reportRemoteDataSource: ReportRemoteDataSource,
    @ApplicationContext private val appContext: Context,
) : ViewModel() {
    private data class ImageFeedbackContext(val vote: String, val targetId: String)

    private val _submitted = MutableSharedFlow<Unit>(extraBufferCapacity = 1)
    val submitted: SharedFlow<Unit> = _submitted.asSharedFlow()

    var isFeedbackMode: Boolean = false
    var targetID: String = ""
    var targetType: String = "USER"
    private var imageFeedbackContext: ImageFeedbackContext? = null

    private val reportReasons =
        ReportReasonMappings.REPORT_REASON_CODE_TO_STRING_RES.map { (reasonCode, stringResId) ->
            ReportReasonItem(reasonCode, stringResId)
        }

    private val feedbackReasons =
        ReportReasonMappings.FEEDBACK_REASON_CODE_TO_STRING_RES.map { (reasonCode, stringResId) ->
            ReportReasonItem(reasonCode, stringResId)
        }

    private val imageFeedbackReasons =
        ReportReasonMappings.IMAGE_FEEDBACK_REASON_CODE_TO_STRING_RES.map { (reasonCode, stringResId) ->
            ReportReasonItem(reasonCode, stringResId)
        }

    private val _reasons = MutableStateFlow(reportReasons)
    val reasons = _reasons.asStateFlow()

    fun updateReasonsForMode() {
        _reasons.value =
            if (isFeedbackMode && imageFeedbackContext != null) {
                imageFeedbackReasons
            } else if (isFeedbackMode) {
                feedbackReasons
            } else {
                reportReasons
            }
    }

    fun configureImageFeedbackContext(
        vote: String?,
        evidenceImageUrl: String,
        feedbackTargetType: String,
        feedbackTargetId: String,
    ) {
        val normalizedVote = normalizeImageFeedbackVote(vote)
        val normalizedImageUrl = evidenceImageUrl.trim()
        val normalizedTargetId = feedbackTargetId.trim()
        val isImageFeedbackTarget = normalizedTargetId.startsWith(IMAGE_FEEDBACK_TARGET_PREFIX)
        imageFeedbackContext =
            if (
                isFeedbackMode &&
                    normalizedVote != null &&
                    normalizedImageUrl.isNotEmpty() &&
                    feedbackTargetType == ReportTargetType.USER.name &&
                    isImageFeedbackTarget
            ) {
                ImageFeedbackContext(vote = normalizedVote, targetId = normalizedTargetId)
            } else {
                null
            }
    }

    val selectedReasonCodes = mutableStateSetOf<ReportReasonCode>()

    private val _description = MutableStateFlow("")
    val description = _description.asStateFlow()

    val localImages = mutableStateSetOf<String>()
    val remoteImages = mutableStateSetOf<String>()

    private val _isSubmitting = MutableStateFlow(false)
    val isSubmitting = _isSubmitting.asStateFlow()

    fun bindEntry(entry: SystemReportEntry) {
        selectedReasonCodes.clear()
        localImages.clear()
        remoteImages.clear()
        _description.value = ""
        isFeedbackMode = entry.isFeedback
        targetID = entry.targetId
        targetType = entry.targetType
        configureImageFeedbackContext(
            vote = entry.imageFeedbackVote,
            evidenceImageUrl = entry.initialEvidenceImageUrl,
            feedbackTargetType = entry.targetType,
            feedbackTargetId = entry.targetId,
        )
        updateReasonsForMode()
        setInitialEvidenceImage(entry.initialEvidenceImageUrl)
    }

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
            ToastUtils.showShort(R.string.system_toast_please_select_reason)
            return
        }

        val trimmedDescription = description.value.trim()
        if (trimmedDescription.isEmpty()) {
            ToastUtils.showShort(R.string.system_toast_please_enter_description)
            return
        }

        if (_isSubmitting.value) {
            return
        }

        _isSubmitting.value = true
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val uploadedImageUrls = mutableListOf<String>()

                for (imageUri in localImages) {
                    val uri = imageUri.toUri()
                    val uploadedUrl = uploadImageWithCompression(appContext, uri)
                    if (uploadedUrl != null) {
                        uploadedImageUrls.add(uploadedUrl)
                    }
                }

                val selectedReasonCodesList = selectedReasonCodes.toList()
                val imageFeedbackReasonCodes =
                    selectedReasonCodesList.filter { it in IMAGE_FEEDBACK_REASON_CODES }

                val request =
                    ReportCreateRequest(
                        targetId =
                            if (isFeedbackMode) {
                                imageFeedbackContext?.targetId ?: ""
                            } else {
                                targetID
                            },
                        targetType =
                            if (imageFeedbackContext != null) {
                                ReportTargetType.USER
                            } else if (!isFeedbackMode && targetType == ReportTargetType.USER.name) {
                                ReportTargetType.USER
                            } else {
                                ReportTargetType.AGENT
                            },
                        reasonCodes = selectedReasonCodesList,
                        description =
                            if (imageFeedbackContext != null) {
                                buildImageFeedbackDescription(
                                    userDescription = trimmedDescription,
                                    vote = imageFeedbackContext?.vote,
                                    selectedReasonCodes = imageFeedbackReasonCodes,
                                )
                            } else {
                                buildReportDescriptionWithAppVersion(
                                    userDescription = trimmedDescription,
                                    versionName = BuildConfig.VERSION_NAME,
                                    versionCode = BuildConfig.VERSION_CODE,
                                    agentId = if (isFeedbackMode) targetID else "",
                                )
                            },
                        imageUrls = uploadedImageUrls + remoteImages.toList(),
                        reportType =
                            if (isFeedbackMode) {
                                ReportRequestType.FEEDBACK
                            } else {
                                ReportRequestType.REPORT
                            },
                    )

                val outcome =
                    createReportWithImageFeedbackCompatibility(
                        request = request,
                        imageFeedbackReasonCodes = imageFeedbackReasonCodes,
                    )
                withContext(Dispatchers.Main) {
                    when (outcome) {
                        is CreateReportOutcome.Success -> {
                            if (isFeedbackMode) {
                                ToastUtils.showShort(R.string.system_toast_feedback_submitted)
                            } else {
                                ToastUtils.showShort(R.string.system_toast_submitted_successfully)
                            }
                            _submitted.tryEmit(Unit)
                        }
                        is CreateReportOutcome.BusinessError -> {
                            ToastUtils.showShort(
                                outcome.message.ifBlank {
                                    appContext.getString(R.string.system_toast_report_creation_failed)
                                }
                            )
                        }
                        is CreateReportOutcome.TransportError -> {
                            ToastUtils.showShort(
                                outcome.message.ifBlank {
                                    appContext.getString(R.string.system_toast_report_creation_failed)
                                }
                            )
                        }
                        is CreateReportOutcome.UnprocessableEntity -> {
                            ToastUtils.showShort(R.string.system_toast_report_creation_failed)
                        }
                    }
                }
            } finally {
                _isSubmitting.value = false
            }
        }
    }

    private suspend fun createReportWithImageFeedbackCompatibility(
        request: ReportCreateRequest,
        imageFeedbackReasonCodes: List<ReportReasonCode>,
    ): CreateReportOutcome {
        val first = reportRemoteDataSource.createReport(request)
        if (
            first is CreateReportOutcome.UnprocessableEntity &&
                imageFeedbackContext != null &&
                imageFeedbackReasonCodes.isNotEmpty()
        ) {
            return reportRemoteDataSource.createReport(
                request.copy(reasonCodes = listOf(ReportReasonCode.OTHER))
            )
        }
        return first
    }

    fun onAddImage(imageUri: Uri) {
        val normalizedUri = imageUri.toString().trim()
        if (normalizedUri.isNotEmpty()) {
            localImages.add(normalizedUri)
        }
    }

    private suspend fun uploadImageWithCompression(context: Context, uri: Uri): String? {
        return withContext(Dispatchers.IO) {
            var tempFile: File? = null
            var compressedFile: File? = null
            try {
                tempFile = createTempFileFromUri(context, uri) ?: return@withContext null

                val originalSizeKB = tempFile.length() / 1024
                if (originalSizeKB <= 1024) {
                    return@withContext reportRemoteDataSource.uploadReportImage(tempFile, "report-image.jpg")
                }

                var webpFile =
                    ImageCompressUtils.convertToWebPSync(
                        context = context,
                        imageFile = tempFile,
                        quality = 85,
                        maxWidth = 1920,
                        maxHeight = 1920,
                    )

                if (webpFile != null && webpFile.exists()) {
                    val webpSizeKB = webpFile.length() / 1024
                    if (webpSizeKB <= 1024) {
                        compressedFile = webpFile
                    } else {
                        compressedFile =
                            ImageCompressUtils.compressImageSync(
                                context = context,
                                imageFile = webpFile,
                                config = ImageCompressUtils.CompressConfig(maxSize = 800),
                            )
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
                            webpFile.delete()
                        }
                    }
                } else {
                    compressedFile =
                        ImageCompressUtils.compressImageSync(
                            context = context,
                            imageFile = tempFile,
                            config = ImageCompressUtils.CompressConfig(maxSize = 800),
                        )
                }

                if (compressedFile == null || !compressedFile.exists()) {
                    return@withContext null
                }

                val compressedSizeKB = compressedFile.length() / 1024
                if (compressedSizeKB > 1024) {
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

                val filename =
                    if (compressedFile.name.endsWith(".webp", ignoreCase = true)) {
                        "report-image.webp"
                    } else {
                        "report-image.jpg"
                    }
                reportRemoteDataSource.uploadReportImage(compressedFile, filename)
            } catch (_: Throwable) {
                null
            } finally {
                tempFile?.delete()
                compressedFile?.delete()
            }
        }
    }

    private suspend fun createTempFileFromUri(context: Context, uri: Uri): File? {
        return withContext(Dispatchers.IO) {
            try {
                val inputStream = context.contentResolver.openInputStream(uri) ?: return@withContext null
                val tempFile = File.createTempFile("upload_", ".jpg", context.cacheDir)
                val outputStream = FileOutputStream(tempFile)
                inputStream.use { input -> outputStream.use { output -> input.copyTo(output) } }
                tempFile
            } catch (_: Throwable) {
                null
            }
        }
    }
}
