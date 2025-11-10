package com.ai.intellimate.ui.components

import ai.sxwl.android.utils.LogUtils
import android.content.Context
import android.util.LruCache
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.io.FileOutputStream
import java.security.MessageDigest
import java.util.concurrent.TimeUnit

/**
 * 视频缓存管理器
 * 提供视频文件的本地缓存功能，优化加载性能
 */
class VideoCacheManager private constructor(private val context: Context) {

    companion object {
        @Volatile
        private var INSTANCE: VideoCacheManager? = null

        fun getInstance(context: Context): VideoCacheManager {
            return INSTANCE
                ?: synchronized(this) {
                    INSTANCE ?: VideoCacheManager(context.applicationContext).also { INSTANCE = it }
                }
        }

        private const val CACHE_DIR_NAME = "video_cache"
        private const val MAX_CACHE_SIZE = 100 * 1024 * 1024L // 100MB
        private const val MAX_MEMORY_CACHE_SIZE = 5 // 最多缓存5个视频文件路径
    }

    private val httpClient =
        OkHttpClient.Builder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(60, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .retryOnConnectionFailure(true)
            .build()

    // 内存缓存（存储文件路径）
    private val memoryCache = LruCache<String, String>(MAX_MEMORY_CACHE_SIZE)

    // 缓存目录
    private val cacheDir: File by lazy {
        File(context.cacheDir, CACHE_DIR_NAME).apply {
            if (!exists()) {
                mkdirs()
            }
        }
    }

    /**
     * 获取视频文件路径（优先使用缓存）
     * @param url 视频 URL
     * @return 本地文件路径或原始 URL
     */
    suspend fun getVideoPath(url: String): String = withContext(Dispatchers.IO) {
        LogUtils.d("VideoCacheManager - [getVideoPath] 开始获取视频路径: $url")
        val cacheKey = generateCacheKey(url)
        LogUtils.d("VideoCacheManager - [getVideoPath] 缓存键: $cacheKey")

        // 检查内存缓存
        val memoryCachedPath = memoryCache.get(cacheKey)
        if (memoryCachedPath != null) {
            val cachedFile = File(memoryCachedPath)
            if (cachedFile.exists()) {
                LogUtils.d("VideoCacheManager - [getVideoPath] ✓ 使用内存缓存: $url -> $memoryCachedPath, size=${cachedFile.length()}")
                return@withContext cachedFile.absolutePath
            } else {
                LogUtils.w("VideoCacheManager - [getVideoPath] 内存缓存路径不存在，移除: $memoryCachedPath")
                memoryCache.remove(cacheKey)
            }
        } else {
            LogUtils.d("VideoCacheManager - [getVideoPath] 内存缓存未命中")
        }

        // 检查文件缓存
        val cachedFile = getCachedFile(cacheKey)
        LogUtils.d("VideoCacheManager - [getVideoPath] 检查文件缓存: ${cachedFile.absolutePath}, exists=${cachedFile.exists()}")
        if (cachedFile.exists()) {
            memoryCache.put(cacheKey, cachedFile.absolutePath)
            LogUtils.d("VideoCacheManager - [getVideoPath] ✓ 使用文件缓存: $url -> ${cachedFile.absolutePath}, size=${cachedFile.length()}")
            return@withContext cachedFile.absolutePath
        }

        // 返回原始 URL（VideoView 会处理网络加载）
        LogUtils.d("VideoCacheManager - [getVideoPath] ✗ 未找到缓存，使用网络 URL: $url")
        url
    }

    /**
     * 预加载视频到缓存
     * @param url 视频 URL
     */
    suspend fun preloadVideo(url: String) = withContext(Dispatchers.IO) {
        val startTime = System.currentTimeMillis()
        try {
            LogUtils.d("VideoCacheManager - [preloadVideo] ========== 开始预加载视频 ==========")
            LogUtils.d("VideoCacheManager - [preloadVideo] URL: $url")

            val cacheKey = generateCacheKey(url)
            LogUtils.d("VideoCacheManager - [preloadVideo] 缓存键: $cacheKey")

            // 如果已经缓存，直接返回
            val memoryCachedPath = memoryCache.get(cacheKey)
            val cachedFile = getCachedFile(cacheKey)
            if (memoryCachedPath != null || cachedFile.exists()) {
                LogUtils.d("VideoCacheManager - [preloadVideo] ✓ 视频已缓存，跳过预加载: $url")
                if (cachedFile.exists()) {
                    LogUtils.d("VideoCacheManager - [preloadVideo] 缓存文件: ${cachedFile.absolutePath}, size=${cachedFile.length()}")
                }
                return@withContext
            }

            LogUtils.d("VideoCacheManager - [preloadVideo] 开始下载视频...")
            val downloadStartTime = System.currentTimeMillis()

            // 下载视频
            val request = Request.Builder().url(url).build()
            LogUtils.d("VideoCacheManager - [preloadVideo] 发送 HTTP 请求...")
            val response = httpClient.newCall(request).execute()

            val connectTime = System.currentTimeMillis() - downloadStartTime
            LogUtils.d("VideoCacheManager - [preloadVideo] HTTP 响应: code=${response.code}, connectTime=${connectTime}ms")

            if (response.isSuccessful) {
                val body = response.body
                if (body != null) {
                    val contentLength = body.contentLength()
                    LogUtils.d("VideoCacheManager - [preloadVideo] 响应体大小: $contentLength bytes")

                    val cachedFile = getCachedFile(cacheKey)
                    LogUtils.d("VideoCacheManager - [preloadVideo] 保存到: ${cachedFile.absolutePath}")

                    var downloadedBytes = 0L
                    val buffer = ByteArray(8192)
                    body.byteStream().use { input ->
                        FileOutputStream(cachedFile).use { output ->
                            var bytesRead: Int
                            while (input.read(buffer).also { bytesRead = it } != -1) {
                                output.write(buffer, 0, bytesRead)
                                downloadedBytes += bytesRead

                                // 每下载 1MB 记录一次进度
                                if (downloadedBytes % (1024 * 1024) == 0L || downloadedBytes == contentLength) {
                                    val progress = if (contentLength > 0) {
                                        (downloadedBytes * 100 / contentLength).toInt()
                                    } else {
                                        0
                                    }
                                    LogUtils.d("VideoCacheManager - [preloadVideo] 下载进度: $downloadedBytes/$contentLength bytes ($progress%)")
                                }
                            }
                        }
                    }

                    val downloadTime = System.currentTimeMillis() - downloadStartTime
                    val totalTime = System.currentTimeMillis() - startTime
                    memoryCache.put(cacheKey, cachedFile.absolutePath)
                    LogUtils.d("VideoCacheManager - [preloadVideo] ✓ 视频预加载完成: $url")
                    LogUtils.d("VideoCacheManager - [preloadVideo] 文件大小: ${cachedFile.length()} bytes")
                    LogUtils.d("VideoCacheManager - [preloadVideo] 下载时间: ${downloadTime}ms, 总时间: ${totalTime}ms")
                    LogUtils.d("VideoCacheManager - [preloadVideo] ========== 预加载完成 ==========")
                } else {
                    LogUtils.w("VideoCacheManager - [preloadVideo] ✗ 响应体为 null")
                }
            } else {
                LogUtils.w("VideoCacheManager - [preloadVideo] ✗ HTTP 请求失败: code=${response.code}, message=${response.message}")
            }
        } catch (e: Exception) {
            val totalTime = System.currentTimeMillis() - startTime
            LogUtils.e("VideoCacheManager - [preloadVideo] ✗ 预加载异常: $url, error=${e.message}, time=${totalTime}ms")
            LogUtils.e("VideoCacheManager - [preloadVideo] 异常堆栈: ${e.stackTraceToString()}")
        }
    }

    /**
     * 检查视频是否已缓存
     */
    fun isCached(url: String): Boolean {
        val cacheKey = generateCacheKey(url)
        val memoryCached = memoryCache.get(cacheKey) != null
        val fileCached = getCachedFile(cacheKey).exists()
        val result = memoryCached || fileCached
        LogUtils.d("VideoCacheManager - [isCached] URL: $url, memoryCached=$memoryCached, fileCached=$fileCached, result=$result")
        return result
    }

    /**
     * 清理缓存
     */
    fun clearCache() {
        try {
            memoryCache.evictAll()
            cacheDir.listFiles()?.forEach { file ->
                if (file.isFile) {
                    file.delete()
                }
            }
        } catch (e: Exception) {
            LogUtils.e("VideoCacheManager - 清理缓存失败: ${e.message}")
        }
    }

    /**
     * 清理过期缓存
     */
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
            LogUtils.e("VideoCacheManager - 清理过期缓存失败: ${e.message}")
        }
    }

    /**
     * 生成缓存键
     */
    private fun generateCacheKey(url: String): String {
        val digest = MessageDigest.getInstance("MD5")
        val hash = digest.digest(url.toByteArray())
        return hash.joinToString("") { "%02x".format(it) }
    }

    /**
     * 获取缓存文件
     */
    private fun getCachedFile(cacheKey: String): File {
        // 根据 URL 判断文件扩展名
        val extension = if (cacheKey.contains(".mp4")) ".mp4" else ".video"
        return File(cacheDir, "$cacheKey$extension")
    }
}
