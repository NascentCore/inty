package com.ai.inty.audio

import ai.sxwl.android.utils.LogUtils
import android.content.Context
import android.util.LruCache
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.security.MessageDigest
import java.util.concurrent.TimeUnit

/** 音频缓存管理器 提供内存缓存和本地文件缓存功能 */
class AudioCacheManager private constructor(private val context: Context) {

    companion object {
        @Volatile
        private var INSTANCE: AudioCacheManager? = null

        fun getInstance(context: Context): AudioCacheManager {
            return INSTANCE
                ?: synchronized(this) {
                    INSTANCE ?: AudioCacheManager(context.applicationContext).also { INSTANCE = it }
                }
        }

        private const val CACHE_DIR_NAME = "audio_cache"
        private const val MAX_CACHE_SIZE = 50 * 1024 * 1024L // 50MB
        private const val MAX_MEMORY_CACHE_SIZE = 20 // 最多缓存20个音频文件
    }

    private val httpClient =
        OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(60, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .retryOnConnectionFailure(true)
            .build()

    // 内存缓存
    private val memoryCache = LruCache<String, ByteArray>(MAX_MEMORY_CACHE_SIZE)

    // 缓存目录
    private val cacheDir: File by lazy {
        File(context.cacheDir, CACHE_DIR_NAME).apply {
            if (!exists()) {
                mkdirs()
            }
        }
    }

    /** 预加载音频数据 */
    suspend fun preloadAudio(url: String) =
        withContext(Dispatchers.IO) {
            try {
                val cacheKey = generateCacheKey(url)

                // 如果已经缓存，直接返回
                if (memoryCache.get(cacheKey) != null || getCachedFile(cacheKey).exists()) {
                    return@withContext
                }

                // 下载并缓存
                val data = downloadAudio(url)
                if (data != null) {
                    memoryCache.put(cacheKey, data)
                    saveToFile(getCachedFile(cacheKey), data)
                }
            } catch (e: Exception) {
                LogUtils.e("音频LOG测试 Failed to preload audio: ${e.message}")
            }
        }

    /** 检查音频是否已缓存 */
    fun isCached(url: String): Boolean {
        val cacheKey = generateCacheKey(url)
        return memoryCache.get(cacheKey) != null || getCachedFile(cacheKey).exists()
    }

    /** 获取缓存文件路径 */
    fun getCachedFilePath(url: String): String? {
        val cacheKey = generateCacheKey(url)
        val cachedFile = getCachedFile(cacheKey)
        return if (cachedFile.exists()) cachedFile.absolutePath else null
    }

    /** 清理缓存 */
    fun clearCache() {
        try {
            // 清理内存缓存
            memoryCache.evictAll()

            // 清理文件缓存
            cacheDir.listFiles()?.forEach { file ->
                if (file.isFile) {
                    file.delete()
                }
            }

        } catch (e: Exception) {
            LogUtils.e("音频LOG测试 Failed to clear cache: ${e.message}")
        }
    }

    /** 清理过期缓存 */
    fun cleanExpiredCache() {
        try {
            val currentTime = System.currentTimeMillis()
            val maxAge = 7 * 24 * 60 * 60 * 1000L // 7天

            cacheDir.listFiles()?.forEach { file ->
                if (file.isFile && currentTime - file.lastModified() > maxAge) {
                    file.delete()
                }
            }

        } catch (e: Exception) {
            LogUtils.e("音频LOG测试 Failed to clean expired cache: ${e.message}")
        }
    }

    /** 获取缓存大小 */
    fun getCacheSize(): Long {
        return try {
            cacheDir.listFiles()?.sumOf { file -> if (file.isFile) file.length() else 0L } ?: 0L
        } catch (e: Exception) {
            0L
        }
    }

    /** 生成缓存键 */
    private fun generateCacheKey(url: String): String {
        val digest = MessageDigest.getInstance("MD5")
        val hash = digest.digest(url.toByteArray())
        return hash.joinToString("") { "%02x".format(it) }
    }

    /** 获取缓存文件 */
    private fun getCachedFile(cacheKey: String): File {
        return File(cacheDir, "$cacheKey.opus")
    }

    /** 从网络下载音频 */
    private suspend fun downloadAudio(url: String): ByteArray? =
        withContext(Dispatchers.IO) {
            var retryCount = 0
            val maxRetries = 3

            while (retryCount <= maxRetries) {
                try {
                    val request =
                        Request.Builder().url(url).addHeader("User-Agent", "IntyApp/1.0").build()

                    httpClient.newCall(request).execute().use { response ->
                        if (response.isSuccessful) {
                            val body = response.body?.bytes()
                            if (body != null && body.isNotEmpty()) {
                                return@withContext body
                            } else {
                                LogUtils.e("音频LOG测试 Downloaded audio is empty: $url")
                                return@withContext null
                            }
                        } else {
                            val errorMsg =
                                when (response.code) {
                                    404 -> "音频文件不存在"
                                    403 -> "音频文件访问被拒绝"
                                    500 -> "服务器内部错误"
                                    else -> "HTTP错误: ${response.code}"
                                }
                            LogUtils.e("音频LOG测试 Failed to download audio: $errorMsg (${response.code})")

                            // 对于4xx错误，不重试
                            if (response.code in 400..499) {
                                return@withContext null
                            }
                        }
                    }
                } catch (e: Exception) {
                    val errorMsg =
                        when {
                            e.message?.contains("Connection reset", ignoreCase = true) == true ->
                                "连接被重置"

                            e.message?.contains("timeout", ignoreCase = true) == true -> "连接超时"
                            e.message?.contains("network", ignoreCase = true) == true -> "网络错误"
                            else -> e.message ?: "未知错误"
                        }

                    LogUtils.e("音频LOG测试 Failed to download audio (attempt ${retryCount + 1}): $errorMsg")


                    // 如果是最后一次重试，返回null
                    if (retryCount == maxRetries) {
                        return@withContext null
                    }
                }

                retryCount++
                if (retryCount <= maxRetries) {
                    // 指数退避重试
                    val delayMs = 1000L * (1 shl (retryCount - 1))
                    delay(delayMs)
                }
            }

            null
        }

    /** 保存数据到文件 */
    private fun saveToFile(file: File, data: ByteArray) {
        try {
            FileOutputStream(file).use { fos -> fos.write(data) }
        } catch (e: IOException) {
            LogUtils.e("音频LOG测试 Failed to save audio to file: ${e.message}")
        }
    }
}
