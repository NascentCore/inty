package ai.sxwl.android.utils

import android.content.Context
import android.net.Uri
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import top.zibin.luban.Luban
import top.zibin.luban.OnCompressListener
import java.io.File
import java.io.IOException

/**
 * 图片压缩工具类
 * 基于Luban库封装，提供简洁的API供上层模块使用
 */
object ImageCompressUtils {

    /**
     * 压缩配置类
     */
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
        val keepOriginal: Boolean = false
    )

    /**
     * 压缩结果回调接口
     */
    interface CompressCallback {
        /** 压缩成功 */
        fun onSuccess(compressedFile: File)

        /** 压缩失败 */
        fun onError(throwable: Throwable)

        /** 压缩进度 */
        fun onProgress(progress: Int) {}
    }

    /**
     * 压缩单个图片文件
     *
     * @param context 上下文
     * @param imageFile 要压缩的图片文件
     * @param config 压缩配置
     * @param callback 压缩结果回调
     */
    fun compressImage(
        context: Context,
        imageFile: File,
        config: CompressConfig = CompressConfig(),
        callback: CompressCallback
    ) {
        try {
            if (!imageFile.exists()) {
                callback.onError(IOException("图片文件不存在: ${imageFile.absolutePath}"))
                return
            }

            Luban.with(context)
                .load(imageFile)
                .ignoreBy(config.maxSize)
                .setTargetDir(getCompressCacheDir(context))
                .filter { path ->
                    try {
                        // 过滤条件：只处理图片文件
                        val extension = if (path.contains('.')) {
                            path.substringAfterLast('.', "").lowercase()
                        } else {
                            ""
                        }
                        extension in listOf("jpg", "jpeg", "png", "webp", "bmp")
                    } catch (e: Exception) {
                        false
                    }
                }
                .setCompressListener(object : OnCompressListener {
                    override fun onStart() {
                        // 压缩开始
                    }

                    override fun onSuccess(file: File) {
                        callback.onSuccess(file)
                    }

                    override fun onError(e: Throwable) {
                        callback.onError(e)
                    }
                })
                .launch()
        } catch (e: Exception) {
            callback.onError(e)
        }
    }

    /**
     * 压缩多个图片文件
     *
     * @param context 上下文
     * @param imageFiles 要压缩的图片文件列表
     * @param config 压缩配置
     * @param callback 压缩结果回调
     */
    fun compressImages(
        context: Context,
        imageFiles: List<File>,
        config: CompressConfig = CompressConfig(),
        callback: CompressCallback
    ) {
        try {
            if (imageFiles.isEmpty()) {
                callback.onError(kotlin.IllegalArgumentException("图片文件列表不能为空"))
                return
            }

            val validFiles = imageFiles.filter { it.exists() }
            if (validFiles.isEmpty()) {
                callback.onError(IOException("没有找到有效的图片文件"))
                return
            }

            Luban.with(context)
                .load(validFiles)
                .ignoreBy(config.maxSize)
                .setTargetDir(getCompressCacheDir(context))
                .filter { path ->
                    try {
                        val extension = if (path.contains('.')) {
                            path.substringAfterLast('.', "").lowercase()
                        } else {
                            ""
                        }
                        extension in listOf("jpg", "jpeg", "png", "webp", "bmp")
                    } catch (e: Exception) {
                        false
                    }
                }
                .setCompressListener(object : OnCompressListener {
                    override fun onStart() {
                        // 压缩开始
                    }

                    override fun onSuccess(file: File) {
                        callback.onSuccess(file)
                    }

                    override fun onError(e: Throwable) {
                        callback.onError(e)
                    }
                })
                .launch()
        } catch (e: Exception) {
            callback.onError(e)
        }
    }

    /**
     * 压缩图片URI
     *
     * @param context 上下文
     * @param imageUri 要压缩的图片URI
     * @param config 压缩配置
     * @param callback 压缩结果回调
     */
    fun compressImageUri(
        context: Context,
        imageUri: Uri,
        config: CompressConfig = CompressConfig(),
        callback: CompressCallback
    ) {
        Luban.with(context)
            .load(imageUri)
            .ignoreBy(config.maxSize)
            .setTargetDir(getCompressCacheDir(context))
            .setCompressListener(object : OnCompressListener {
                override fun onStart() {
                    // 压缩开始
                }

                override fun onSuccess(file: File) {
                    callback.onSuccess(file)
                }

                override fun onError(e: Throwable) {
                    callback.onError(e)
                }
            })
            .launch()
    }

    /**
     * 同步压缩图片（在协程中使用）
     * 注意：Luban的get()方法可能返回List<File>，这里简化为返回第一个文件
     *
     * @param context 上下文
     * @param imageFile 要压缩的图片文件
     * @param config 压缩配置
     * @return 压缩后的文件，失败时返回null
     */
    suspend fun compressImageSync(
        context: Context,
        imageFile: File,
        config: CompressConfig = CompressConfig()
    ): File? = withContext(Dispatchers.IO) {
        try {
            if (!imageFile.exists()) {
                return@withContext null
            }

            val result = Luban.with(context)
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
     * 清理压缩缓存
     *
     * @param context 上下文
     * @return 是否清理成功
     */
    fun clearCompressCache(context: Context): Boolean {
        return try {
            val cacheDir = File(context.cacheDir, "luban_compress")
            if (cacheDir.exists()) {
                cacheDir.deleteRecursively()
            }
            true
        } catch (e: Exception) {
            false
        }
    }

    /**
     * 获取压缩缓存大小
     *
     * @param context 上下文
     * @return 缓存大小（字节）
     */
    fun getCompressCacheSize(context: Context): Long {
        return try {
            val cacheDir = File(context.cacheDir, "luban_compress")
            if (cacheDir.exists()) {
                cacheDir.walkTopDown().sumOf {
                    try {
                        it.length()
                    } catch (e: Exception) {
                        0L
                    }
                }
            } else {
                0L
            }
        } catch (e: Exception) {
            0L
        }
    }

    /**
     * 检查文件是否为支持的图片格式
     *
     * @param file 文件
     * @return 是否为支持的图片格式
     */
    fun isSupportedImageFormat(file: File): Boolean {
        if (!file.exists() || !file.isFile) {
            return false
        }

        val extension = file.extension.lowercase()
        return extension in listOf("jpg", "jpeg", "png", "webp", "bmp")
    }

    /**
     * 检查文件是否为支持的图片格式
     *
     * @param filePath 文件路径
     * @return 是否为支持的图片格式
     */
    fun isSupportedImageFormat(filePath: String): Boolean {
        return isSupportedImageFormat(File(filePath))
    }
}
