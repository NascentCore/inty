package com.ai.core.utils

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import androidx.core.graphics.scale
import java.io.File
import java.io.FileOutputStream
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import top.zibin.luban.Luban

/** 图片压缩工具类 基于Luban库封装，提供简洁的API供上层模块使用 */
object ImageCompressUtils {

    /** 压缩配置类 */
    data class CompressConfig(
        /** 压缩质量，范围0-100，默认80 */
        val quality: Int = 80,
        /** 最大宽度，默认1080 */
        val maxWidth: Int = 1080,
        /** 最大高度，默认1920 */
        val maxHeight: Int = 1920,
        /** 最大文件大小，单位KB，默认500KB */
        val maxSize: Int = 500,
        /** 是否保留原文件，默认false */
        val keepOriginal: Boolean = false,
    )

    /**
     * 同步压缩图片（在协程中使用） 注意：Luban的get()方法可能返回List<File>，这里简化为返回第一个文件
     *
     * @param context 上下文
     * @param imageFile 要压缩的图片文件
     * @param config 压缩配置
     * @return 压缩后的文件，失败时返回null
     */
    suspend fun compressImageSync(
        context: Context,
        imageFile: File,
        config: CompressConfig = CompressConfig(),
    ): File? =
        withContext(Dispatchers.IO) {
            try {
                if (!imageFile.exists()) {
                    return@withContext null
                }

                val result =
                    Luban.with(context)
                        .load(imageFile)
                        .ignoreBy(config.maxSize)
                        .setTargetDir(getCompressCacheDir(context))
                        .get()

                // Luban的get()方法返回List<File>，取第一个
                if (result is List<*> && result.isNotEmpty()) {
                    result.first() as? File
                } else {
                    null
                }
            } catch (e: Exception) {
                null
            }
        }

    /**
     * 获取压缩缓存目录
     *
     * @param context 上下文
     * @return 缓存目录
     */
    private fun getCompressCacheDir(context: Context): String {
        return try {
            val cacheDir = File(context.cacheDir, "luban_compress")
            if (!cacheDir.exists()) {
                cacheDir.mkdirs()
            }
            cacheDir.absolutePath
        } catch (e: Exception) {
            // 如果缓存目录创建失败，使用临时目录
            File(System.getProperty("java.io.tmpdir"), "luban_compress").absolutePath
        }
    }

    /**
     * 将图片转换为 WebP 格式（同步方法，在协程中使用） 仅支持 BitmapFactory 可以解码的格式（JPEG、PNG 等标准格式） 对于 HEIC/HEIF 格式，请在使用处使用
     * Coil 加载后再调用此方法
     *
     * @param context 上下文
     * @param imageFile 要转换的图片文件
     * @param quality WebP 压缩质量，范围 0-100，默认 80
     * @param maxWidth 最大宽度，如果超过则缩放，默认不限制
     * @param maxHeight 最大高度，如果超过则缩放，默认不限制
     * @return 转换后的 WebP 文件，失败时返回 null
     */
    suspend fun convertToWebPSync(
        context: Context,
        imageFile: File,
        quality: Int = 80,
        maxWidth: Int = -1,
        maxHeight: Int = -1,
    ): File? =
        withContext(Dispatchers.IO) {
            var bitmap: Bitmap? = null
            try {
                if (!imageFile.exists()) {
                    return@withContext null
                }

                // 尝试用 BitmapFactory 解码
                val options = BitmapFactory.Options().apply { inJustDecodeBounds = true }
                BitmapFactory.decodeFile(imageFile.absolutePath, options)
                val canDecode = options.outWidth > 0 && options.outHeight > 0

                if (!canDecode) {
                    // 无法用 BitmapFactory 解码（可能是 HEIC 格式），返回 null
                    return@withContext null
                }

                // 可以用 BitmapFactory 解码（JPEG、PNG 等标准格式）
                // 计算缩放比例
                var sampleSize = 1
                if (maxWidth > 0 && maxHeight > 0) {
                    val widthRatio = options.outWidth / maxWidth
                    val heightRatio = options.outHeight / maxHeight
                    sampleSize = maxOf(widthRatio, heightRatio, 1)
                }

                // 加载缩放后的 Bitmap
                val decodeOptions = BitmapFactory.Options().apply { inSampleSize = sampleSize }
                bitmap =
                    BitmapFactory.decodeFile(imageFile.absolutePath, decodeOptions)
                        ?: return@withContext null

                // 如果指定了最大尺寸，进一步缩放
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
                val webpFile =
                    File(
                        getCompressCacheDir(context),
                        "${imageFile.nameWithoutExtension}_${System.currentTimeMillis()}.webp",
                    )

                // 保存为 WebP 格式
                FileOutputStream(webpFile).use { out ->
                    finalBitmap.compress(Bitmap.CompressFormat.WEBP, quality, out)
                }

                // 清理临时 Bitmap
                if (finalBitmap != bitmap) {
                    finalBitmap.recycle()
                }
                bitmap.recycle()

                webpFile
            } catch (e: Exception) {
                bitmap?.recycle()
                null
            }
        }
}
