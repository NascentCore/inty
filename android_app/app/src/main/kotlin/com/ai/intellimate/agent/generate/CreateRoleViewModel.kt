package com.ai.intellimate.agent.generate

import ai.sxwl.android.common.base.BaseVM
import ai.sxwl.android.data.api.model.CreateAgentRequest
import ai.sxwl.android.utils.ImageCompressUtils
import ai.sxwl.android.utils.LogUtils
import android.content.Context
import android.graphics.Bitmap
import android.net.Uri
import androidx.core.graphics.scale
import androidx.core.net.toUri
import coil3.SingletonImageLoader
import coil3.asDrawable
import coil3.request.ImageRequest
import coil3.request.SuccessResult
import com.ai.intellimate.agent.data.AgentGenerateRepository
import java.io.File
import java.io.FileOutputStream
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/** CreateRoleActivity 的 ViewModel 负责管理 Agent 的创建和更新逻辑 */
class CreateRoleViewModel : BaseVM() {
    private val repository = AgentGenerateRepository()

    suspend fun updateAgent(
        agentId: String? = null,
        request: CreateAgentRequest,
        createTempFile: (Uri) -> File,
        context: Context? = null,
    ) {
        // 上传背景图片列表，记录每张图片的上传状态
        val remoteImageUrls = mutableListOf<String>()
        request.backgroundImages.forEachIndexed { index, uri ->
            try {
                val remoteUrl = convertToRemoteImage(uri, createTempFile, context)
                remoteImageUrls.add(remoteUrl)
                LogUtils.i(
                    "CreateRoleViewModel - Background image $index uploaded successfully: $remoteUrl"
                )
            } catch (e: Exception) {
                LogUtils.e(
                    "CreateRoleViewModel - Failed to upload background image $index: ${e.message}",
                    e,
                )
                // 提取原始错误信息，避免重复嵌套
                val errorMessage = e.message ?: "Unknown error"
                throw Exception("Failed to upload background image ${index + 1}: $errorMessage")
            }
        }

        // 上传背景图片（如果不在列表中）
        val remoteBackgroundImage =
            request.background?.let { uri ->
                val index = request.backgroundImages.indexOf(uri)

                if (index >= 0) {
                    remoteImageUrls[index]
                } else {
                    try {
                        val remoteUrl = convertToRemoteImage(uri, createTempFile, context)
                        LogUtils.i(
                            "CreateRoleViewModel - Background image uploaded successfully: $remoteUrl"
                        )
                        remoteUrl
                    } catch (e: Exception) {
                        LogUtils.e(
                            "CreateRoleViewModel - Failed to upload background image: ${e.message}",
                            e,
                        )
                        // 提取原始错误信息，避免重复嵌套
                        val errorMessage = e.message ?: "Unknown error"
                        throw Exception("Failed to upload background image: $errorMessage")
                    }
                }
            }

        // 上传头像（注意：如果 avatar 指向 background 或 backgroundImages 中的同一张图片，则复用已上传的 URL，避免重复上传）
        val remoteAvatar =
            when {
                request.avatar.isNullOrBlank() -> remoteBackgroundImage
                request.avatar == request.background && remoteBackgroundImage != null ->
                    remoteBackgroundImage
                else -> {
                    val avatarInBackgroundIndex = request.backgroundImages.indexOf(request.avatar)
                    if (avatarInBackgroundIndex >= 0 && avatarInBackgroundIndex < remoteImageUrls.size) {
                        remoteImageUrls[avatarInBackgroundIndex]
                    } else {
                        try {
                            val remoteUrl =
                                convertToRemoteImage(request.avatar!!, createTempFile, context)
                            LogUtils.i("CreateRoleViewModel - Avatar uploaded successfully: $remoteUrl")
                            remoteUrl
                        } catch (e: Exception) {
                            LogUtils.e("CreateRoleViewModel - Failed to upload avatar: ${e.message}", e)
                            val errorMessage = e.message ?: "Unknown error"
                            throw Exception("Failed to upload avatar: $errorMessage")
                        }
                    }
                }
            }

        val newRequest =
            request.copy(
                background = remoteBackgroundImage,
                backgroundImages = remoteImageUrls,
                avatar = remoteAvatar,
            )

        if (agentId.isNullOrBlank()) {
            val result = repository.createAgent(newRequest)

            LogUtils.i("CreateRoleViewModel - createAgent success: ${result.id}")
        } else {
            repository.updateAgent(agentId, newRequest)

            LogUtils.i("CreateRoleViewModel - updateAgent success: $agentId")
        }
    }

    private suspend fun convertToRemoteImage(
        uri: String,
        createTempFile: (Uri) -> File,
        context: Context? = null,
    ): String {
        return withContext(Dispatchers.IO) {
            if (uri.startsWith("http") || uri.startsWith("https")) {
                uri
            } else {
                var tempFile: File? = null
                var webpFile: File? = null
                var compressedFile: File? = null
                try {
                    tempFile = createTempFile(uri.toUri())
                    // 验证文件是否存在且可读
                    if (!tempFile.exists() || tempFile.length() == 0L) {
                        throw Exception("Image file is empty or does not exist: ${tempFile.name}")
                    }

                    var fileToUpload = tempFile

                    // 如果是本地文件且有 context，尝试处理图片
                    if (context != null) {
                        // 1. 优先尝试转换为 WebP 格式
                        webpFile =
                            convertToWebPWithHeicSupport(
                                context = context,
                                imageFile = tempFile,
                                quality = 85,
                                maxWidth = -1,
                                maxHeight = -1,
                            )

                        if (webpFile != null && webpFile.exists() && webpFile.length() > 0) {
                            val webpSizeKB = webpFile.length() / 1024
                            LogUtils.i(
                                "CreateRoleViewModel - Image converted to WebP: ${webpSizeKB}KB"
                            )
                            fileToUpload = webpFile
                        } else {
                            // WebP 转换失败：保持原图上传，避免尺寸变化导致裁剪坐标失效
                            LogUtils.w(
                                "CreateRoleViewModel - WebP conversion failed, uploading original file to preserve dimensions"
                            )
                        }
                    }

                    val result = repository.uploadImage(fileToUpload)
                    result.url
                } catch (e: Exception) {
                    LogUtils.e(
                        "CreateRoleViewModel - Failed to upload image: ${e.javaClass.simpleName}: ${e.message}",
                        e,
                    )
                    throw e
                } finally {
                    // 清理 WebP 临时文件
                    if (webpFile != null && webpFile != tempFile) {
                        try {
                            webpFile.delete()
                        } catch (e: Exception) {
                            LogUtils.w(
                                "CreateRoleViewModel - Failed to delete WebP file: ${e.message}"
                            )
                        }
                    }
                    // 清理压缩后的临时文件
                    if (
                        compressedFile != null &&
                            compressedFile != tempFile &&
                            compressedFile != webpFile
                    ) {
                        try {
                            compressedFile.delete()
                        } catch (e: Exception) {
                            LogUtils.w(
                                "CreateRoleViewModel - Failed to delete compressed file: ${e.message}"
                            )
                        }
                    }
                }
            }
        }
    }

    /**
     * 将图片转换为 WebP 格式，支持 HEIC/HEIF 格式（使用 Coil 加载） 先尝试使用 ImageCompressUtils.convertToWebPSync（标准格式）
     * 如果失败，尝试使用 Coil 加载（HEIC 格式）后转换为 WebP
     */
    private suspend fun convertToWebPWithHeicSupport(
        context: Context,
        imageFile: File,
        quality: Int = 85,
        maxWidth: Int = 1920,
        maxHeight: Int = 1920,
    ): File? {
        return withContext(Dispatchers.IO) {
            // 先尝试使用标准方法（BitmapFactory 可以解码的格式）
            val webpFile =
                ImageCompressUtils.convertToWebPSync(
                    context = context,
                    imageFile = imageFile,
                    quality = quality,
                    maxWidth = maxWidth,
                    maxHeight = maxHeight,
                )

            if (webpFile != null && webpFile.exists() && webpFile.length() > 0) {
                return@withContext webpFile
            }

            // 标准方法失败，可能是 HEIC 格式，使用 Coil 加载
            var bitmap: Bitmap? = null
            try {
                val imageLoader = SingletonImageLoader.get(context)
                val request =
                    ImageRequest.Builder(context)
                        .data(imageFile)
                        .size(coil3.size.Size.ORIGINAL)
                        .build()

                val result = imageLoader.execute(request)
                if (result !is SuccessResult) {
                    return@withContext null
                }

                val image = result.image
                val drawable = image.asDrawable(context.resources)
                bitmap =
                    if (drawable is android.graphics.drawable.BitmapDrawable) {
                        drawable.bitmap
                    } else {
                        // 从 Drawable 创建 Bitmap
                        val width = drawable.intrinsicWidth
                        val height = drawable.intrinsicHeight
                        if (width <= 0 || height <= 0) {
                            return@withContext null
                        }
                        val bmp = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
                        val canvas = android.graphics.Canvas(bmp)
                        drawable.setBounds(0, 0, width, height)
                        drawable.draw(canvas)
                        bmp
                    }

                if (bitmap == null) {
                    return@withContext null
                }

                // 如果指定了最大尺寸，进行缩放
                val finalBitmap =
                    if (
                        maxWidth > 0 &&
                            maxHeight > 0 &&
                            (bitmap.width > maxWidth || bitmap.height > maxHeight)
                    ) {
                        val scale =
                            minOf(
                                maxWidth.toFloat() / bitmap.width,
                                maxHeight.toFloat() / bitmap.height,
                            )
                        val scaledWidth = (bitmap.width * scale).toInt()
                        val scaledHeight = (bitmap.height * scale).toInt()
                        bitmap.scale(scaledWidth, scaledHeight)
                    } else {
                        bitmap
                    }

                // 创建 WebP 输出文件
                val cacheDir = File(context.cacheDir, "luban_compress")
                if (!cacheDir.exists()) {
                    cacheDir.mkdirs()
                }
                val outputWebpFile =
                    File(
                        cacheDir,
                        "${imageFile.nameWithoutExtension}_${System.currentTimeMillis()}.webp",
                    )

                // 保存为 WebP 格式
                FileOutputStream(outputWebpFile).use { out ->
                    finalBitmap.compress(Bitmap.CompressFormat.WEBP, quality, out)
                }

                // 清理临时 Bitmap
                if (finalBitmap != bitmap) {
                    finalBitmap.recycle()
                }
                bitmap.recycle()

                if (outputWebpFile.exists() && outputWebpFile.length() > 0) {
                    outputWebpFile
                } else {
                    null
                }
            } catch (e: Exception) {
                LogUtils.e("CreateRoleViewModel - Failed to convert HEIC to WebP: ${e.message}", e)
                bitmap?.recycle()
                null
            }
        }
    }
}
