package com.ai.inty.utils

import android.content.Context
import android.graphics.BitmapFactory
import android.graphics.Point
import android.util.LruCache
import android.view.WindowManager
import androidx.compose.ui.unit.dp
import com.inty.utils.log.EasyLog
import java.net.URL
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/** 图片尺寸缓存管理器 用于预加载图片尺寸，实现稳定的瀑布流布局 */
object ImageSizeCache {

  // 内存缓存，存储图片URL到尺寸的映射
  private val sizeCache = LruCache<String, Point>(100)

  // 屏幕宽度
  private var screenWidth = 0
  // 屏幕密度
  private var density = 1f
  // 内容边距
  private val contentPadding = 16.dp
  // 水平间距
  private val horizontalSpacing = 6.dp
  // 列数
  private val columnCount = 2

  // 宽高比范围限制
  private const val MIN_ASPECT_RATIO = 9f / 16f // 9:16 (更窄，高度更高)
  private const val MAX_ASPECT_RATIO = 3f / 4f // 3:4 (更宽，高度更低)

  /** 初始化缓存管理器 */
  fun init(context: Context) {
    val windowManager = context.getSystemService(Context.WINDOW_SERVICE) as WindowManager
    val size = Point()
    windowManager.currentWindowMetrics.bounds.let { bounds ->
      size.x = bounds.width()
      size.y = bounds.height()
    }
    screenWidth = size.x
    density = context.resources.displayMetrics.density
    EasyLog.log("ImageSizeCache initialized, screen width: $screenWidth, density: $density")
  }

  /** 计算每个item的实际宽度（像素） */
  fun getItemWidthPx(): Int {
    val contentPaddingPx = (contentPadding.value * 2).toInt() // 左右padding
    val spacingPx = horizontalSpacing.value.toInt() // 中间间距
    val availableWidth = screenWidth - contentPaddingPx - spacingPx
    return availableWidth / columnCount
  }

  /**
   * 获取图片的显示高度（像素）
   *
   * @param imageUrl 图片URL
   * @return 显示高度（像素）
   */
  fun getDisplayHeightPx(imageUrl: String?): Int {
    // 如果还没有初始化，返回一个安全的默认高度
    if (screenWidth == 0 || density == 0f) {
      return (290 * 3f).toInt() // 使用290dp作为安全默认值，假设density=3
    }

    if (imageUrl.isNullOrBlank()) {
      return getDefaultHeightPx()
    }

    // 先从缓存中查找
    val cachedSize = sizeCache.get(imageUrl)
    if (cachedSize != null) {
      return calculateDisplayHeightPx(cachedSize.x, cachedSize.y)
    }

    // 如果缓存中没有，使用默认高度
    return getDefaultHeightPx()
  }

  /** 预加载图片尺寸 */
  suspend fun preloadImageSize(imageUrl: String) {
    if (imageUrl.isBlank()) return

    // 如果已经缓存，直接返回
    if (sizeCache.get(imageUrl) != null) return

    try {
      withContext(Dispatchers.IO) {
        val url = URL(imageUrl)
        val connection = url.openConnection()
        connection.connectTimeout = 5000
        connection.readTimeout = 5000

        val inputStream = connection.getInputStream()
        val options = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeStream(inputStream, null, options)
        inputStream.close()

        if (options.outWidth > 0 && options.outHeight > 0) {
          val size = Point(options.outWidth, options.outHeight)
          sizeCache.put(imageUrl, size)
          EasyLog.log("Preloaded image size: $imageUrl -> ${size.x}x${size.y}")
        }
      }
    } catch (e: Exception) {
      EasyLog.log("Failed to preload image size: $imageUrl, error: ${e.message}", EasyLog.ERROR)
    }
  }

  /** 批量预加载图片尺寸 */
  suspend fun preloadImageSizes(imageUrls: List<String>) {
    imageUrls.forEach { url -> preloadImageSize(url) }
  }

  /** 同步预加载关键图片尺寸（用于瀑布流稳定布局） 优先加载前几屏的图片尺寸，确保初始渲染稳定 */
  suspend fun preloadCriticalImageSizes(imageUrls: List<String>, maxCount: Int = 10) {
    val criticalUrls = imageUrls.take(maxCount)
    criticalUrls.forEach { url -> preloadImageSize(url) }
  }

  /** 根据图片尺寸计算显示高度（像素） */
  private fun calculateDisplayHeightPx(imageWidth: Int, imageHeight: Int): Int {
    val originalAspectRatio = imageWidth.toFloat() / imageHeight.toFloat()

    // 限制宽高比在指定范围内
    val clampedAspectRatio = originalAspectRatio.coerceIn(MIN_ASPECT_RATIO, MAX_ASPECT_RATIO)

    // 计算显示高度
    val itemWidthPx = getItemWidthPx()
    val displayHeightPx = (itemWidthPx / clampedAspectRatio).toInt()

    // 限制高度范围，避免过高或过低
    val minHeightPx = (150 * density).toInt()
    val maxHeightPx = (400 * density).toInt()

    return displayHeightPx.coerceIn(minHeightPx, maxHeightPx)
  }

  /** 获取默认高度（像素） */
  private fun getDefaultHeightPx(): Int {
    val itemWidthPx = getItemWidthPx()
    // 使用默认宽高比 4:5 计算默认高度
    val defaultAspectRatio = 4f / 5f
    return (itemWidthPx / defaultAspectRatio).toInt()
  }

  /** 清除缓存 */
  fun clearCache() {
    sizeCache.evictAll()
    EasyLog.log("ImageSizeCache cleared")
  }

  /** 获取缓存大小 */
  fun getCacheSize(): Int {
    return sizeCache.size()
  }
}
