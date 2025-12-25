package com.ai.intellimate.utils

// CREATED_BY_AGENT

import android.content.ContentValues
import android.content.Context
import android.graphics.Bitmap
import android.net.Uri
import android.os.Environment
import android.provider.MediaStore
import coil3.SingletonImageLoader
import coil3.asDrawable
import coil3.request.ImageRequest
import coil3.request.SuccessResult
import coil3.size.Size
import java.io.File
import java.io.FileInputStream
import java.io.IOException
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter
import java.util.Locale
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

object GalleryImageDownloadUtils {

    private val RELATIVE_PATH = "${Environment.DIRECTORY_PICTURES}/IntelliMate"
    private const val FILE_NAME_PREFIX = "IntelliMate_"
    private val FILE_NAME_TIME_FORMATTER = DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss", Locale.US)

    suspend fun saveImageUrlToGallery(context: Context, imageUrl: String): Result<Uri> =
        withContext(Dispatchers.IO) {
            if (imageUrl.isBlank()) {
                return@withContext Result.failure(IllegalArgumentException("imageUrl is blank"))
            }

            val output = inferOutputFromUrl(imageUrl)
            val imageLoader = SingletonImageLoader.get(context)

            val request = ImageRequest.Builder(context).data(imageUrl).size(Size.ORIGINAL).build()

            val result = imageLoader.execute(request)
            if (result !is SuccessResult) {
                return@withContext Result.failure(IOException("Coil image request failed"))
            }

            val displayName = buildDisplayName(output.fileExtension)

            val cachedFile =
                result.diskCacheKey
                    ?.let { key -> imageLoader.diskCache?.openSnapshot(key) }
                    ?.use { it.data.toFile() }

            val savedUri =
                if (cachedFile != null && cachedFile.exists() && cachedFile.length() > 0) {
                    saveEncodedImageFileToGallery(
                        context = context,
                        sourceFile = cachedFile,
                        displayName = displayName,
                        mimeType = output.mimeType,
                    )
                } else {
                    val bitmap =
                        tryDecodeBitmapFromResult(context = context, result = result)
                            ?: return@withContext Result.failure(
                                IOException("Decode bitmap failed")
                            )

                    saveBitmapToGallery(
                        context = context,
                        bitmap = bitmap,
                        displayName = displayName,
                        mimeType = output.mimeType,
                        compressFormat = output.compressFormat,
                    )
                }

            return@withContext savedUri
        }

    private fun buildDisplayName(fileExtension: String): String {
        val timestamp = FILE_NAME_TIME_FORMATTER.format(LocalDateTime.now())
        return "$FILE_NAME_PREFIX$timestamp.$fileExtension"
    }

    private fun inferOutputFromUrl(imageUrl: String): Output {
        val lower = imageUrl.lowercase(Locale.US)
        return if (lower.endsWith(".png")) {
            Output(
                mimeType = "image/png",
                fileExtension = "png",
                compressFormat = Bitmap.CompressFormat.PNG,
            )
        } else {
            Output(
                mimeType = "image/jpeg",
                fileExtension = "jpg",
                compressFormat = Bitmap.CompressFormat.JPEG,
            )
        }
    }

    private fun saveEncodedImageFileToGallery(
        context: Context,
        sourceFile: File,
        displayName: String,
        mimeType: String,
    ): Result<Uri> {
        val resolver = context.contentResolver
        val values =
            ContentValues().apply {
                put(MediaStore.Images.Media.DISPLAY_NAME, displayName)
                put(MediaStore.Images.Media.MIME_TYPE, mimeType)
                put(MediaStore.Images.Media.RELATIVE_PATH, RELATIVE_PATH)
                put(MediaStore.Images.Media.IS_PENDING, 1)
            }

        val uri =
            resolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values)
                ?: return Result.failure(IOException("MediaStore insert failed"))

        try {
            val outputStream =
                resolver.openOutputStream(uri)
                    ?: run {
                        resolver.delete(uri, null, null)
                        return Result.failure(IOException("MediaStore output stream is null"))
                    }

            outputStream.use { output ->
                FileInputStream(sourceFile).use { input ->
                    val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
                    while (true) {
                        val read = input.read(buffer)
                        if (read <= 0) break
                        output.write(buffer, 0, read)
                    }
                }
            }

            ContentValues()
                .apply { put(MediaStore.Images.Media.IS_PENDING, 0) }
                .also { doneValues -> resolver.update(uri, doneValues, null, null) }

            return Result.success(uri)
        } catch (e: IOException) {
            resolver.delete(uri, null, null)
            return Result.failure(e)
        } catch (e: SecurityException) {
            resolver.delete(uri, null, null)
            return Result.failure(e)
        }
    }

    private fun saveBitmapToGallery(
        context: Context,
        bitmap: Bitmap,
        displayName: String,
        mimeType: String,
        compressFormat: Bitmap.CompressFormat,
    ): Result<Uri> {
        val resolver = context.contentResolver
        val values =
            ContentValues().apply {
                put(MediaStore.Images.Media.DISPLAY_NAME, displayName)
                put(MediaStore.Images.Media.MIME_TYPE, mimeType)
                put(MediaStore.Images.Media.RELATIVE_PATH, RELATIVE_PATH)
                put(MediaStore.Images.Media.IS_PENDING, 1)
            }

        val uri =
            resolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values)
                ?: return Result.failure(IOException("MediaStore insert failed"))

        try {
            val outputStream =
                resolver.openOutputStream(uri)
                    ?: run {
                        resolver.delete(uri, null, null)
                        return Result.failure(IOException("MediaStore output stream is null"))
                    }

            outputStream.use { output ->
                val quality = if (compressFormat == Bitmap.CompressFormat.JPEG) 95 else 100
                val ok = bitmap.compress(compressFormat, quality, output)
                if (!ok) {
                    throw IOException("Bitmap compress failed")
                }
            }

            ContentValues()
                .apply { put(MediaStore.Images.Media.IS_PENDING, 0) }
                .also { doneValues -> resolver.update(uri, doneValues, null, null) }

            return Result.success(uri)
        } catch (e: IOException) {
            resolver.delete(uri, null, null)
            return Result.failure(e)
        } catch (e: SecurityException) {
            resolver.delete(uri, null, null)
            return Result.failure(e)
        }
    }

    private fun tryDecodeBitmapFromResult(context: Context, result: SuccessResult): Bitmap? {
        val drawable = result.image.asDrawable(context.resources)
        return if (drawable is android.graphics.drawable.BitmapDrawable) {
            drawable.bitmap
        } else {
            val width = drawable.intrinsicWidth
            val height = drawable.intrinsicHeight
            if (width <= 0 || height <= 0) {
                return null
            }
            val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
            val canvas = android.graphics.Canvas(bitmap)
            drawable.setBounds(0, 0, width, height)
            drawable.draw(canvas)
            bitmap
        }
    }

    private data class Output(
        val mimeType: String,
        val fileExtension: String,
        val compressFormat: Bitmap.CompressFormat,
    )
}
