// CREATED_BY_AGENT
package com.ai.intellimate.settings.feature

import ai.sxwl.android.common.base.BaseVM
import ai.sxwl.android.data.http.ApiResult
import ai.sxwl.android.data.http.services.ReportService
import ai.sxwl.android.utils.ImageCompressUtils
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.ToastUtils
import ai.sxwl.android.utils.Utils
import android.net.Uri
import androidx.core.net.toUri
import com.ai.intellimate.R
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

private const val FEATURE_REQUEST_REASON_ID = 6L
private const val MAX_IMAGE_SIZE_KB = 1024
private const val IMAGE_FILE_PREFIX = "feature-request"

/** Feature Request 可选分类 */
data class FeatureRequestCategory(
    val type: FeatureRequestCategoryType,
    val titleRes: Int,
)

enum class FeatureRequestCategoryType {
    UI,
    AI_CHARACTER,
    AI_MODELS,
    VOICE,
    IMAGE,
    SUBSCRIPTION,
    OTHERS,
}

sealed interface FeatureRequestEvent {
    data object Submitted : FeatureRequestEvent
}

class FeatureRequestViewModel : BaseVM() {

    val categories: List<FeatureRequestCategory> = FEATURE_CATEGORIES

    private val _selectedCategory = MutableStateFlow<FeatureRequestCategoryType?>(null)
    val selectedCategory: StateFlow<FeatureRequestCategoryType?> = _selectedCategory.asStateFlow()

    private val _description = MutableStateFlow("")
    val description: StateFlow<String> = _description.asStateFlow()

    private val _imageUris = MutableStateFlow<List<String>>(emptyList())
    val imageUris: StateFlow<List<String>> = _imageUris.asStateFlow()

    private val _isSubmitting = MutableStateFlow(false)
    val isSubmitting: StateFlow<Boolean> = _isSubmitting.asStateFlow()

    private val _events = MutableSharedFlow<FeatureRequestEvent>()
    val events: SharedFlow<FeatureRequestEvent> = _events.asSharedFlow()

    fun selectCategory(type: FeatureRequestCategoryType) {
        _selectedCategory.value =
            if (_selectedCategory.value == type) {
                null
            } else {
                type
            }
    }

    fun updateDescription(text: String) {
        _description.value = text
    }

    fun onAddImage(uri: Uri) {
        _imageUris.value = listOf(uri.toString())
    }

    fun clearImage() {
        _imageUris.value = emptyList()
    }

    fun submit() {
        val categoryType = _selectedCategory.value
        if (categoryType == null) {
            ToastUtils.showShort(R.string.feature_request_error_select_category)
            return
        }

        val descriptionText = _description.value.trim()
        if (descriptionText.isEmpty()) {
            ToastUtils.showShort(R.string.feature_request_error_description_required)
            return
        }

        if (_isSubmitting.value) return

        _isSubmitting.value = true

        launchBackground {
            try {
                val context = Utils.getApp() ?: return@launchBackground
                val uploadedImageUrls = mutableListOf<String>()

                val localUri = _imageUris.value.firstOrNull()
                if (localUri != null) {
                    val uri = localUri.toUri()
                    val uploadedUrl = uploadImageWithCompression(context, uri)
                    if (uploadedUrl != null) {
                        uploadedImageUrls.add(uploadedUrl)
                    }
                }

                val category =
                    categories.firstOrNull { it.type == categoryType }
                        ?: categories.first() // fallback, should not happen
                val categoryLabel = context.getString(category.titleRes)
                val finalDescription =
                    buildString {
                        append("[Category] ")
                        append(categoryLabel)
                        append('\n')
                        append('\n')
                        append(descriptionText)
                    }

                val result =
                    ReportService.createReport(
                        reasonIds = listOf(FEATURE_REQUEST_REASON_ID),
                        targetId = null,
                        targetType = null,
                        description = finalDescription,
                        imageUrls = uploadedImageUrls,
                        reportType = ReportService.ReportType.FEEDBACK,
                    )

                when (result) {
                    is ApiResult.Success -> {
                        ToastUtils.showShort(R.string.feature_request_submit_success)
                        _events.emit(FeatureRequestEvent.Submitted)
                    }
                    is ApiResult.Error -> {
                        val errorMessage =
                            result.message
                                ?: context.getString(R.string.feature_request_submit_failed)
                        ToastUtils.showShort(errorMessage)
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("FeatureRequestViewModel", "submit failed: ${e.message}", e)
                ToastUtils.showShort(R.string.feature_request_submit_failed)
            } finally {
                _isSubmitting.value = false
            }
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
                tempFile = createTempFileFromUri(context, uri) ?: return@withContext null

                val originalSizeKB = tempFile.length() / 1024
                if (originalSizeKB <= MAX_IMAGE_SIZE_KB) {
                    val inputStream = FileInputStream(tempFile)
                    val result =
                        ReportService.uploadImage(
                            inputStream,
                            "$IMAGE_FILE_PREFIX-original.jpg",
                        )
                    inputStream.close()
                    return@withContext when (result) {
                        is ApiResult.Success -> result.data
                        is ApiResult.Error -> {
                            LogUtils.e("FeatureRequestViewModel", "upload failed: ${result.message}")
                            null
                        }
                    }
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
                    compressedFile =
                        if (webpSizeKB <= MAX_IMAGE_SIZE_KB) {
                            webpFile
                        } else {
                            ImageCompressUtils.compressImageSync(
                                context = context,
                                imageFile = webpFile,
                                config = ImageCompressUtils.CompressConfig(maxSize = 800),
                            )?.also { webpFile.delete() } ?: webpFile
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
                    LogUtils.e("FeatureRequestViewModel", "image compression failed")
                    return@withContext null
                }

                val compressedSizeKB = compressedFile.length() / 1024
                if (compressedSizeKB > MAX_IMAGE_SIZE_KB) {
                    val moreCompressedFile =
                        ImageCompressUtils.convertToWebPSync(
                            context = context,
                            imageFile = compressedFile,
                            quality = 60,
                            maxWidth = 1280,
                            maxHeight = 1280,
                        )
                    if (moreCompressedFile != null && moreCompressedFile.exists()) {
                        compressedFile.delete()
                        compressedFile = moreCompressedFile
                    }
                }

                val filename =
                    if (compressedFile.name.endsWith(".webp", ignoreCase = true)) {
                        "$IMAGE_FILE_PREFIX-image.webp"
                    } else {
                        "$IMAGE_FILE_PREFIX-image.jpg"
                    }
                val inputStream = FileInputStream(compressedFile)
                val result = ReportService.uploadImage(inputStream, filename)
                inputStream.close()

                when (result) {
                    is ApiResult.Success -> result.data
                    is ApiResult.Error -> {
                        LogUtils.e("FeatureRequestViewModel", "upload failed: ${result.message}")
                        null
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("FeatureRequestViewModel", "upload error: ${e.message}", e)
                null
            } finally {
                tempFile?.delete()
                compressedFile?.delete()
            }
        }
    }

    private suspend fun createTempFileFromUri(
        context: android.content.Context,
        uri: Uri,
    ): File? {
        return withContext(Dispatchers.IO) {
            try {
                val inputStream =
                    context.contentResolver.openInputStream(uri) ?: return@withContext null
                val tempFile =
                    File.createTempFile(
                        "${IMAGE_FILE_PREFIX}_upload_",
                        ".jpg",
                        context.cacheDir,
                    )
                val outputStream = FileOutputStream(tempFile)

                inputStream.use { input -> outputStream.use { output -> input.copyTo(output) } }

                tempFile
            } catch (e: Exception) {
                LogUtils.e("FeatureRequestViewModel", "temp file error: ${e.message}", e)
                null
            }
        }
    }

    companion object {
        private val FEATURE_CATEGORIES =
            listOf(
                FeatureRequestCategory(
                    type = FeatureRequestCategoryType.UI,
                    titleRes = R.string.feature_request_category_ui,
                ),
                FeatureRequestCategory(
                    type = FeatureRequestCategoryType.AI_CHARACTER,
                    titleRes = R.string.feature_request_category_ai_character,
                ),
                FeatureRequestCategory(
                    type = FeatureRequestCategoryType.AI_MODELS,
                    titleRes = R.string.feature_request_category_ai_models,
                ),
                FeatureRequestCategory(
                    type = FeatureRequestCategoryType.VOICE,
                    titleRes = R.string.feature_request_category_voice,
                ),
                FeatureRequestCategory(
                    type = FeatureRequestCategoryType.IMAGE,
                    titleRes = R.string.feature_request_category_image,
                ),
                FeatureRequestCategory(
                    type = FeatureRequestCategoryType.SUBSCRIPTION,
                    titleRes = R.string.feature_request_category_subscription,
                ),
                FeatureRequestCategory(
                    type = FeatureRequestCategoryType.OTHERS,
                    titleRes = R.string.feature_request_category_others,
                ),
            )
    }
}
