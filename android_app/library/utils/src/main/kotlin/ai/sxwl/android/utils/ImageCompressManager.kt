package ai.sxwl.android.utils

import android.content.Context
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOn
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.io.IOException

/**
 * 图片压缩管理器
 * 提供更高级的图片压缩功能，包括批量压缩、进度监控、结果统计等
 */
class ImageCompressManager private constructor() {

    companion object {
        @Volatile
        private var INSTANCE: ImageCompressManager? = null

        fun getInstance(): ImageCompressManager {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: ImageCompressManager().also { INSTANCE = it }
            }
        }
    }

    private val compressScope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    /**
     * 压缩统计信息
     */
    data class CompressStats(
        val totalFiles: Int = 0,
        val successCount: Int = 0,
        val failedCount: Int = 0,
        val originalSize: Long = 0L,
        val compressedSize: Long = 0L,
        val compressionRatio: Float = 0f
    ) {
        val isCompleted: Boolean
            get() = successCount + failedCount >= totalFiles
    }

    /**
     * 压缩任务信息
     */
    data class CompressTask(
        val id: String,
        val files: List<File>,
        val config: ImageCompressUtils.CompressConfig,
        val startTime: Long = System.currentTimeMillis()
    )

    private val activeTasks = mutableMapOf<String, CompressTask>()
    private val taskStats = mutableMapOf<String, CompressStats>()

    /**
     * 批量压缩图片（带进度监控）
     *
     * @param context 上下文
     * @param imageFiles 要压缩的图片文件列表
     * @param config 压缩配置
     * @param taskId 任务ID，用于跟踪进度
     * @return 压缩进度Flow
     */
    fun compressImagesWithProgress(
        context: Context,
        imageFiles: List<File>,
        config: ImageCompressUtils.CompressConfig = ImageCompressUtils.CompressConfig(),
        taskId: String = generateTaskId()
    ): Flow<CompressStats> = flow {
        val validFiles = imageFiles.filter { ImageCompressUtils.isSupportedImageFormat(it) }

        if (validFiles.isEmpty()) {
            emit(CompressStats())
            return@flow
        }

        val task = CompressTask(taskId, validFiles, config)
        activeTasks[taskId] = task

        val originalSize = try {
            validFiles.sumOf {
                try {
                    it.length()
                } catch (e: Exception) {
                    0L
                }
            }
        } catch (e: Exception) {
            0L
        }
        var successCount = 0
        var failedCount = 0
        var compressedSize = 0L

        emit(
            CompressStats(
                totalFiles = validFiles.size,
                originalSize = originalSize
            )
        )

        validFiles.forEachIndexed { index, file ->
            try {
                val compressedFile = ImageCompressUtils.compressImageSync(context, file, config)
                if (compressedFile != null) {
                    successCount++
                    compressedSize += try {
                        compressedFile.length()
                    } catch (e: Exception) {
                        0L
                    }
                } else {
                    failedCount++
                }
            } catch (e: Exception) {
                failedCount++
            }

            val stats = CompressStats(
                totalFiles = validFiles.size,
                successCount = successCount,
                failedCount = failedCount,
                originalSize = originalSize,
                compressedSize = compressedSize,
                compressionRatio = if (originalSize > 0) {
                    (1f - compressedSize.toFloat() / originalSize.toFloat()) * 100f
                } else 0f
            )

            taskStats[taskId] = stats
            emit(stats)
        }

        activeTasks.remove(taskId)
    }.flowOn(Dispatchers.IO)

    /**
     * 压缩单个图片（带回调）
     *
     * @param context 上下文
     * @param imageFile 要压缩的图片文件
     * @param config 压缩配置
     * @param callback 压缩结果回调
     */
    fun compressImageAsync(
        context: Context,
        imageFile: File,
        config: ImageCompressUtils.CompressConfig = ImageCompressUtils.CompressConfig(),
        callback: ImageCompressUtils.CompressCallback
    ) {
        compressScope.launch {
            try {
                val compressedFile =
                    ImageCompressUtils.compressImageSync(context, imageFile, config)
                if (compressedFile != null) {
                    withContext(Dispatchers.Main) {
                        callback.onSuccess(compressedFile)
                    }
                } else {
                    withContext(Dispatchers.Main) {
                        callback.onError(IOException("压缩失败"))
                    }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    callback.onError(e)
                }
            }
        }
    }

    /**
     * 智能压缩：根据文件大小自动调整压缩参数
     *
     * @param context 上下文
     * @param imageFile 要压缩的图片文件
     * @param targetSizeKB 目标文件大小（KB）
     * @param callback 压缩结果回调
     */
    fun smartCompress(
        context: Context,
        imageFile: File,
        targetSizeKB: Int = 500,
        callback: ImageCompressUtils.CompressCallback
    ) {
        if (!imageFile.exists()) {
            callback.onError(IOException("图片文件不存在"))
            return
        }

        val fileSizeKB = try {
            imageFile.length() / 1024
        } catch (e: Exception) {
            0
        }
        
        if (fileSizeKB <= targetSizeKB) {
            // 文件已经足够小，直接返回原文件
            callback.onSuccess(imageFile)
            return
        }

        // 根据文件大小动态调整压缩参数
        val config = when {
            fileSizeKB > 5000 -> ImageCompressUtils.CompressConfig(
                quality = 60,
                maxWidth = 800,
                maxHeight = 1200,
                maxSize = targetSizeKB
            )

            fileSizeKB > 2000 -> ImageCompressUtils.CompressConfig(
                quality = 70,
                maxWidth = 1000,
                maxHeight = 1500,
                maxSize = targetSizeKB
            )

            else -> ImageCompressUtils.CompressConfig(
                quality = 80,
                maxWidth = 1200,
                maxHeight = 1800,
                maxSize = targetSizeKB
            )
        }

        compressImageAsync(context, imageFile, config, callback)
    }

    /**
     * 获取任务统计信息
     *
     * @param taskId 任务ID
     * @return 统计信息
     */
    fun getTaskStats(taskId: String): CompressStats? {
        return taskStats[taskId]
    }

    /**
     * 获取所有活跃任务
     *
     * @return 活跃任务列表
     */
    fun getActiveTasks(): List<CompressTask> {
        return activeTasks.values.toList()
    }

    /**
     * 取消压缩任务
     *
     * @param taskId 任务ID
     */
    fun cancelTask(taskId: String) {
        activeTasks.remove(taskId)
        taskStats.remove(taskId)
    }

    /**
     * 清理所有任务和统计信息
     */
    fun clearAllTasks() {
        activeTasks.clear()
        taskStats.clear()
    }

    /**
     * 生成任务ID
     */
    private fun generateTaskId(): String {
        return try {
            "compress_${System.currentTimeMillis()}_${(1000..9999).random()}"
        } catch (e: Exception) {
            "compress_${System.currentTimeMillis()}_${System.nanoTime() % 10000}"
        }
    }

    /**
     * 释放资源
     */
    fun destroy() {
        compressScope.cancel()
        clearAllTasks()
        INSTANCE = null
    }
}

/**
 * 图片压缩扩展函数
 */

/**
 * 快速压缩单个图片
 */
fun File.compressImage(
    context: Context,
    config: ImageCompressUtils.CompressConfig = ImageCompressUtils.CompressConfig(),
    callback: (File) -> Unit
) {
    ImageCompressManager.getInstance().compressImageAsync(
        context,
        this,
        config,
        object : ImageCompressUtils.CompressCallback {
            override fun onSuccess(compressedFile: File) {
                callback(compressedFile)
            }

            override fun onError(throwable: Throwable) {
                // 忽略错误，或者可以添加日志
            }
        }
    )
}

/**
 * 智能压缩单个图片
 */
fun File.smartCompress(
    context: Context,
    targetSizeKB: Int = 500,
    callback: (File) -> Unit
) {
    ImageCompressManager.getInstance().smartCompress(
        context,
        this,
        targetSizeKB,
        object : ImageCompressUtils.CompressCallback {
            override fun onSuccess(compressedFile: File) {
                callback(compressedFile)
            }

            override fun onError(throwable: Throwable) {
                // 忽略错误，或者可以添加日志
            }
        }
    )
}

/**
 * 批量压缩图片列表
 */
fun List<File>.compressImages(
    context: Context,
    config: ImageCompressUtils.CompressConfig = ImageCompressUtils.CompressConfig(),
    taskId: String = "batch_${System.currentTimeMillis()}"
): Flow<ImageCompressManager.CompressStats> {
    return ImageCompressManager.getInstance()
        .compressImagesWithProgress(context, this, config, taskId)
}
