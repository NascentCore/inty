package com.ai.inty.audio

import android.content.Context
import android.util.LruCache
import com.inty.utils.log.EasyLog
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.security.MessageDigest
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request

/** 音频缓存管理器 提供内存缓存和本地文件缓存功能 */
class AudioCacheManager private constructor(private val context: Context) {

  companion object {
    @Volatile private var INSTANCE: AudioCacheManager? = null

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
          .connectTimeout(10, TimeUnit.SECONDS)
          .readTimeout(30, TimeUnit.SECONDS)
          .writeTimeout(30, TimeUnit.SECONDS)
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
            EasyLog.log("音频LOG测试 Audio preloaded: $url")
          }
        } catch (e: Exception) {
          EasyLog.log("音频LOG测试 Failed to preload audio: ${e.message}", EasyLog.ERROR)
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

      EasyLog.log("音频LOG测试 Audio cache cleared")
    } catch (e: Exception) {
      EasyLog.log("音频LOG测试 Failed to clear cache: ${e.message}", EasyLog.ERROR)
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

      EasyLog.log("音频LOG测试 Expired audio cache cleaned")
    } catch (e: Exception) {
      EasyLog.log("音频LOG测试 Failed to clean expired cache: ${e.message}", EasyLog.ERROR)
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
        try {
          val request = Request.Builder().url(url).build()

          httpClient.newCall(request).execute().use { response ->
            if (response.isSuccessful) {
              response.body?.bytes()
            } else {
              EasyLog.log("音频LOG测试 Failed to download audio: ${response.code}", EasyLog.ERROR)
              null
            }
          }
        } catch (e: Exception) {
          EasyLog.log("音频LOG测试 Failed to download audio: ${e.message}", EasyLog.ERROR)
          null
        }
      }

  /** 保存数据到文件 */
  private fun saveToFile(file: File, data: ByteArray) {
    try {
      FileOutputStream(file).use { fos -> fos.write(data) }
    } catch (e: IOException) {
      EasyLog.log("音频LOG测试 Failed to save audio to file: ${e.message}", EasyLog.ERROR)
    }
  }
}
