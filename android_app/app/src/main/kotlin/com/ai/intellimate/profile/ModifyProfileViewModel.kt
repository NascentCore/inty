package com.ai.intellimate.profile

import ai.sxwl.android.common.base.BaseVM
import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.UserProfile
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.ToastUtils
import ai.sxwl.android.utils.Utils
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import androidx.core.graphics.scale
import androidx.core.net.toUri
import androidx.lifecycle.viewModelScope
import com.ai.intellimate.R
import com.ai.intellimate.ViewModelEvent
import com.ai.intellimate.profile.data.UserProfileRepository
import com.ai.intellimate.ui.components.EditKey
import com.ai.intellimate.utils.IntyUserProfileSDK
import com.ai.intellimate.utils.NetworkErrorHandler
import com.ai.intellimate.utils.UserProfileManager
import com.architecture.httplib.core.HttpResult
import java.io.File
import java.io.FileOutputStream
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody

class ModifyProfileViewModel : BaseVM() {

    private val repository = UserProfileRepository()

    // 事件通知机制
    private val _events = MutableSharedFlow<ViewModelEvent>()
    val events: SharedFlow<ViewModelEvent> = _events.asSharedFlow()

    private val _userProfile = MutableStateFlow(UserProfile())
    val userProfile = _userProfile.asStateFlow()

    // 保存原始用户信息，用于判断字段是否变化
    private var originalUserProfile: UserProfile? = null

    private val _avatarChanged = MutableStateFlow(false)

    private val _isSaving = MutableStateFlow(false)
    val isSaving = _isSaving.asStateFlow()
    private val _isAppearanceUploading = MutableStateFlow(false)
    val isAppearanceUploading = _isAppearanceUploading.asStateFlow()

    init {
        viewModelScope.launch {
            val profile = UserProfileManager.profile.first()

            originalUserProfile = profile

            UserProfileManager.profile.collect { _userProfile.value = it }
        }
    }

    private fun sanitizeEditValue(editKey: EditKey, editValue: String): String {
        return when (editKey) {
            EditKey.Name -> editValue.trim()
            else -> editValue
        }
    }

    /** 发送事件通知 */
    private fun sendEvent(event: ViewModelEvent) {
        viewModelScope.launch { _events.emit(event) }
    }

    fun init(userProfile: UserProfile?) {}

    fun changeUserProfile(editKey: EditKey, editValue: String) {
        val sanitizedValue = sanitizeEditValue(editKey, editValue)
        when (editKey) {
            EditKey.Name -> {
                _userProfile.value = _userProfile.value.copy(nickname = sanitizedValue)
            }
            EditKey.Pronouns -> {
                _userProfile.value = _userProfile.value.copy(gender = sanitizedValue)
            }
            EditKey.Persona -> {
                _userProfile.value = _userProfile.value.copy(description = sanitizedValue)
            }
            EditKey.Preference,
            EditKey.None -> {}
        }
    }

    /** 单独更新 name/pronoun/persona 字段，在各自的 sheet 中点击 save 时调用 会判断是否真的修改了，如果没变化则不调用接口 */
    fun updateFieldAndSave(editKey: EditKey, editValue: String) {
        launchBackground {
            _isSaving.value = true
            try {
                val sanitizedValue = sanitizeEditValue(editKey, editValue)
                val original = originalUserProfile ?: return@launchBackground
                val current = _userProfile.value
                var hasChanged = false

                // 先判断是否真的变化了
                when (editKey) {
                    EditKey.Name -> {
                        hasChanged = original.nickname != sanitizedValue
                    }

                    EditKey.Pronouns -> {
                        hasChanged = (original.gender ?: "") != sanitizedValue
                    }

                    EditKey.Persona -> {
                        hasChanged = (original.description ?: "") != sanitizedValue
                    }

                    EditKey.Preference,
                    EditKey.None -> {
                        return@launchBackground
                    }
                }

                // 如果没有变化，只更新本地状态（用户可能在 sheet 中修改了但改回了原值），不调用接口
                if (!hasChanged) {
                    changeUserProfile(editKey, sanitizedValue)
                    return@launchBackground
                }

                // 有变化，更新本地状态
                val updatedProfile =
                    when (editKey) {
                        EditKey.Name -> current.copy(nickname = sanitizedValue)
                        EditKey.Pronouns -> current.copy(gender = sanitizedValue)
                        EditKey.Persona -> current.copy(description = sanitizedValue)
                        EditKey.Preference,
                        EditKey.None -> current
                    }
                _userProfile.value = updatedProfile

                // 调用接口更新
                val result = IntyUserProfileSDK.updateUserProfile(updatedProfile)
                if (result != null) {
                    // 更新成功，保存到本地并更新原始值
                    viewModelScope.launch(Dispatchers.Main) {
                        ToastUtils.showShort(R.string.saved_successfully)
                        UserProfileManager.saveUserProfile(result)
                    }
                    // 更新原始值，避免重复更新
                    originalUserProfile = result
                    _userProfile.value = result
                } else {
                    NetworkErrorHandler.showNetworkAwareError("Failed to update user profile")
                    // 更新失败，恢复原值
                    _userProfile.value = current
                }
            } finally {
                _isSaving.value = false
            }
        }
    }

    /**
     * Edit My Persona 界面 save 按钮的保存逻辑 保留原始逻辑：上传头像（如果有变化），然后更新整个 profile 判断是否有变化：只有头像变化或 profile
     * 有变化时才调用接口
     */
    fun onSave() {
        launchBackground {
            //            _isSaving.value = true
            try {
                val original = originalUserProfile ?: UserProfile()
                val current = _userProfile.value

                // 判断是否有任何变化
                val hasProfileChanged =
                    original.nickname != current.nickname ||
                        (original.gender ?: "") != (current.gender ?: "") ||
                        (original.description ?: "") != (current.description ?: "")

                // 如果没有头像变化且没有 profile 变化，直接返回
                if (!_avatarChanged.value && !hasProfileChanged) {
                    return@launchBackground
                }

                // 上传头像（如果有变化）
                if (_avatarChanged.value) {
                    val fileUri = current.avatar?.toUri()

                    if (fileUri?.path == null) {
                        NetworkErrorHandler.showNetworkAwareError("Invalid avatar file")
                        return@launchBackground
                    }

                    // UCrop 返回的是 file:// URI，可以直接使用 File 读取
                    val file = File(fileUri.path!!)
                    if (!file.exists() || file.length() == 0L) {
                        NetworkErrorHandler.showNetworkAwareError("Image file not found")
                        return@launchBackground
                    }

                    val requestBody =
                        file.asRequestBody(contentType = "image/jpg".toMediaTypeOrNull())
                    val result =
                        NetServiceMgr.getUserApi()
                            .uploadAvatar(
                                MultipartBody.Part.createFormData("file", "file.png", requestBody)
                            )

                    when (result) {
                        is HttpResult.Success -> {
                            _userProfile.value =
                                current.copy(
                                    // No cropping, just use the provided url.
                                    avatar = result.data.url
                                )
                            // 头像上传完毕提示
                            viewModelScope.launch(Dispatchers.Main) {
                                ToastUtils.showShort(R.string.avatar_upload_success)
                            }
                        }
                        is HttpResult.Failure -> {
                            _userProfile.value = current.copy(avatar = original.avatar)
                            NetworkErrorHandler.showNetworkAwareError(result.message)
                            return@launchBackground
                        }
                    }
                }

                // 更新整个 profile（如果有头像变化或其他 profile 变化）
                if (_avatarChanged.value || hasProfileChanged) {
                    val updatedProfile = IntyUserProfileSDK.updateUserProfile(_userProfile.value)
                    if (updatedProfile != null) {
                        // Show success toast for profile update
                        viewModelScope.launch(Dispatchers.Main) {
                            //                            ToastUtils.showShort(
                            //
                            // Utils.getApp().getString(R.string.saved_successfully)
                            //                            )
                            UserProfileManager.saveUserProfile(updatedProfile)
                        }
                        // 更新原始值
                        originalUserProfile = updatedProfile
                        _userProfile.value = updatedProfile
                        // 重置头像变化标志
                        _avatarChanged.value = false
                        // 发送用户信息更新成功事件
                        sendEvent(ViewModelEvent.UserProfileUpdated)
                    } else {
                        NetworkErrorHandler.showNetworkAwareError("Failed to update user profile")
                    }
                }
            } finally {
                //                _isSaving.value = false
            }
        }
    }

    fun setAvatar(uri: Uri?) {
        //        LogUtils.i("avatar= $uri")
        _avatarChanged.value = true
        _userProfile.value = _userProfile.value.copy(avatar = uri.toString())
    }

    fun setUserAppearance(uri: Uri, callback: (() -> Unit)? = null) {
        viewModelScope
            .launch(Dispatchers.IO) {
                _isAppearanceUploading.value = true
                var tempFile: File? = null
                var compressedFile: File? = null

                try {
                    // 将 URI 转换为临时文件
                    tempFile =
                        createTempFileFromUri(uri)
                            ?: run {
                                NetworkErrorHandler.showNetworkAwareError(
                                    "Failed to read image file"
                                )
                                return@launch
                            }

                    // 转换为 JPG 并压缩到 2MB 以内
                    compressedFile =
                        convertToJpgAndCompress(tempFile, maxSizeKB = 2048)
                            ?: run {
                                NetworkErrorHandler.showNetworkAwareError(
                                    "Failed to compress image"
                                )
                                return@launch
                            }

                    // 更新用户外观
                    _userProfile.value =
                        repository.updateUserAppearance(_userProfile.value, compressedFile)

                    withContext(Dispatchers.Main) {
                        if (callback == null) {
                            ToastUtils.showShort(
                                Utils.getApp().getString(R.string.saved_successfully)
                            )
                        } else {
                            callback.invoke()
                        }
                    }
                } catch (error: Exception) {
                    LogUtils.e("setUserAppearance error: ${error.message}", error)
                    NetworkErrorHandler.showNetworkAwareError("Failed to update user profile")
                } finally {
                    // 清理临时文件
                    tempFile?.delete()
                    compressedFile?.delete()
                }
            }
            .invokeOnCompletion { _isAppearanceUploading.value = false }
    }

    /** 将 URI 转换为临时文件 */
    private suspend fun createTempFileFromUri(uri: Uri): File? =
        withContext(Dispatchers.IO) {
            try {
                val context = Utils.getApp()
                val inputStream =
                    context.contentResolver.openInputStream(uri) ?: return@withContext null
                val tempFile = File.createTempFile("appearance_", ".tmp", context.cacheDir)

                inputStream.use { input ->
                    FileOutputStream(tempFile).use { output -> input.copyTo(output) }
                }

                tempFile
            } catch (e: Exception) {
                LogUtils.e("Error creating temp file from URI: ${e.message}", e)
                null
            }
        }

    /**
     * 将图片转换为 JPG 格式并压缩到指定大小以内
     *
     * @param imageFile 原始图片文件
     * @param maxSizeKB 最大文件大小（KB），默认 2048KB (2MB)
     * @return 压缩后的 JPG 文件，失败时返回 null
     */
    private suspend fun convertToJpgAndCompress(imageFile: File, maxSizeKB: Int = 2048): File? =
        withContext(Dispatchers.IO) {
            var bitmap: Bitmap? = null
            try {
                if (!imageFile.exists()) {
                    return@withContext null
                }

                // 检查原文件大小，如果已经小于目标大小，尝试直接转换格式
                val originalSizeKB = imageFile.length() / 1024
                if (originalSizeKB <= maxSizeKB) {
                    // 尝试直接读取并转换为 JPG
                    bitmap =
                        BitmapFactory.decodeFile(imageFile.absolutePath) ?: return@withContext null
                    val jpgFile =
                        File(
                            Utils.getApp().cacheDir,
                            "appearance_${System.currentTimeMillis()}.jpg",
                        )

                    // 尝试不同质量值，找到符合大小要求的
                    var quality = 90
                    var found = false
                    while (quality >= 50 && !found) {
                        FileOutputStream(jpgFile).use { out ->
                            bitmap.compress(Bitmap.CompressFormat.JPEG, quality, out)
                        }
                        if (jpgFile.length() / 1024 <= maxSizeKB) {
                            found = true
                        } else {
                            quality -= 10
                        }
                    }

                    bitmap.recycle()

                    // 如果转换后符合大小要求，直接返回
                    if (found && jpgFile.length() / 1024 <= maxSizeKB) {
                        return@withContext jpgFile
                    } else {
                        jpgFile.delete()
                    }
                }

                // 需要压缩，先读取图片
                val options = BitmapFactory.Options().apply { inJustDecodeBounds = true }
                BitmapFactory.decodeFile(imageFile.absolutePath, options)
                val canDecode = options.outWidth > 0 && options.outHeight > 0

                if (!canDecode) {
                    LogUtils.e("Cannot decode image file: ${imageFile.absolutePath}")
                    return@withContext null
                }

                // 计算初始缩放比例，目标尺寸不超过 1920x1920
                val maxDimension = 1920
                var sampleSize = 1
                if (options.outWidth > maxDimension || options.outHeight > maxDimension) {
                    val widthRatio = options.outWidth / maxDimension
                    val heightRatio = options.outHeight / maxDimension
                    sampleSize = maxOf(widthRatio, heightRatio, 1)
                }

                // 加载缩放后的 Bitmap
                val decodeOptions = BitmapFactory.Options().apply { inSampleSize = sampleSize }
                bitmap =
                    BitmapFactory.decodeFile(imageFile.absolutePath, decodeOptions)
                        ?: return@withContext null

                // 如果指定了最大尺寸，进一步缩放
                val finalBitmap =
                    if (bitmap.width > maxDimension || bitmap.height > maxDimension) {
                        val scale =
                            minOf(
                                maxDimension.toFloat() / bitmap.width,
                                maxDimension.toFloat() / bitmap.height,
                            )
                        val scaledWidth = (bitmap.width * scale).toInt()
                        val scaledHeight = (bitmap.height * scale).toInt()
                        bitmap.scale(scaledWidth, scaledHeight)
                    } else {
                        bitmap
                    }

                // 创建 JPG 输出文件
                val jpgFile =
                    File(Utils.getApp().cacheDir, "appearance_${System.currentTimeMillis()}.jpg")

                // 使用二分法找到合适的质量值，使文件大小在目标范围内
                var currentBitmap = finalBitmap
                var quality = 90
                var minQuality = 30
                var maxQuality = 100
                var currentDimension = maxDimension
                var needsCleanup = false

                try {
                    while (true) {
                        FileOutputStream(jpgFile).use { out ->
                            currentBitmap.compress(Bitmap.CompressFormat.JPEG, quality, out)
                        }

                        val fileSizeKB = jpgFile.length() / 1024

                        if (fileSizeKB <= maxSizeKB) {
                            // 文件大小符合要求
                            return@withContext jpgFile
                        } else {
                            // 文件太大，降低质量
                            if (quality <= minQuality) {
                                // 已经是最低质量，尝试进一步缩小尺寸
                                val newDimension = (currentDimension * 0.85).toInt()
                                if (newDimension >= 800) {
                                    currentDimension = newDimension
                                    val scale =
                                        minOf(
                                            currentDimension.toFloat() / currentBitmap.width,
                                            currentDimension.toFloat() / currentBitmap.height,
                                        )
                                    val scaledWidth = (currentBitmap.width * scale).toInt()
                                    val scaledHeight = (currentBitmap.height * scale).toInt()

                                    // 创建新的缩放后的 Bitmap
                                    val newBitmap = currentBitmap.scale(scaledWidth, scaledHeight)

                                    // 如果 currentBitmap 是临时创建的，需要回收
                                    if (needsCleanup) {
                                        currentBitmap.recycle()
                                    }

                                    currentBitmap = newBitmap
                                    needsCleanup = true
                                    quality = 90
                                    minQuality = 30
                                    maxQuality = 100
                                    continue
                                } else {
                                    // 尺寸已经太小，使用最低质量
                                    break
                                }
                            }
                            maxQuality = quality - 1
                            quality = (minQuality + maxQuality) / 2
                        }
                    }

                    // 最后一次尝试，使用最低质量
                    FileOutputStream(jpgFile).use { out ->
                        currentBitmap.compress(Bitmap.CompressFormat.JPEG, 30, out)
                    }
                } finally {
                    // 清理 Bitmap 资源
                    if (needsCleanup) {
                        currentBitmap.recycle()
                    }
                    if (finalBitmap != bitmap) {
                        finalBitmap.recycle()
                    }
                    bitmap.recycle()
                }

                // 最终检查文件大小
                val finalSizeKB = jpgFile.length() / 1024
                if (finalSizeKB > maxSizeKB) {
                    LogUtils.w(
                        "Compressed image still exceeds ${maxSizeKB}KB limit: ${finalSizeKB}KB"
                    )
                }

                jpgFile
            } catch (e: Exception) {
                LogUtils.e("Error converting to JPG and compressing: ${e.message}", e)
                bitmap?.recycle()
                null
            }
        }
}
