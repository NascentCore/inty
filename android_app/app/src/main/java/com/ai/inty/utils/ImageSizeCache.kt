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
        try {
            val windowManager = context.getSystemService(Context.WINDOW_SERVICE) as WindowManager
            val size = Point()

            // 使用更安全的方式获取屏幕尺寸
            try {
                windowManager.currentWindowMetrics.bounds.let { bounds ->
                    size.x = bounds.width()
                    size.y = bounds.height()
                }
            } catch (e: Exception) {
                // 如果新API失败，使用旧API作为备选
                windowManager.defaultDisplay.getSize(size)
                EasyLog.log("ImageSizeCache - 使用旧API获取屏幕尺寸", EasyLog.WARN)
            }

            screenWidth = size.x
            density = context.resources.displayMetrics.density
            EasyLog.log("ImageSizeCache initialized, screen width: $screenWidth, density: $density")
        } catch (e: Exception) {
            EasyLog.log("ImageSizeCache - 初始化失败: ${e.message}", EasyLog.ERROR)
            // 设置默认值，确保应用不会崩溃
            screenWidth = 1080 // 默认宽度
            density = 3.0f // 默认密度
        }
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
            return (270 * 3f).toInt() // 使用270dp作为安全默认值，假设density=3
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
            EasyLog.log(
                "Failed to preload image size: $imageUrl, error: ${e.message}",
                EasyLog.ERROR,
            )
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

    /** 根据图片尺寸计算显示高度（像素） 模拟 ContentScale.FillWidth 模式下的实际显示高度 */
    private fun calculateDisplayHeightPx(imageWidth: Int, imageHeight: Int): Int {
        if (imageWidth <= 0 || imageHeight <= 0) {
            return getDefaultHeightPx()
        }

        val originalAspectRatio = imageWidth.toFloat() / imageHeight.toFloat()
        val itemWidthPx = getItemWidthPx()

        // 模拟 FillWidth 模式：图片宽度填满容器，高度按比例缩放
        // 在 FillWidth 模式下，显示高度 = 容器宽度 / 图片原始宽高比
        val fillWidthHeightPx = (itemWidthPx / originalAspectRatio).toInt()

        // 应用合理的宽高比限制，避免极端情况
        val clampedAspectRatio = originalAspectRatio.coerceIn(MIN_ASPECT_RATIO, MAX_ASPECT_RATIO)
        val clampedHeightPx = (itemWidthPx / clampedAspectRatio).toInt()

        // 选择更合理的高度：优先使用 FillWidth 的实际高度，但不超过限制范围
        val finalHeightPx =
            if (fillWidthHeightPx in (120 * density).toInt()..(450 * density).toInt()) {
                fillWidthHeightPx
            } else {
                clampedHeightPx
            }

        // 最终高度范围限制（稍微放宽范围）
        val minHeightPx = (120 * density).toInt()
        val maxHeightPx = (450 * density).toInt()

        return finalHeightPx.coerceIn(minHeightPx, maxHeightPx)
    }

    /** 获取默认高度（像素） 使用更合理的默认宽高比，模拟常见图片比例 */
    private fun getDefaultHeightPx(): Int {
        val itemWidthPx = getItemWidthPx()
        // 使用默认宽高比 3:4 计算默认高度（更接近常见图片比例）
        val defaultAspectRatio = 3f / 4f
        val defaultHeightPx = (itemWidthPx / defaultAspectRatio).toInt()

        // 确保默认高度在合理范围内
        val minHeightPx = (120 * density).toInt()
        val maxHeightPx = (450 * density).toInt()

        return defaultHeightPx.coerceIn(minHeightPx, maxHeightPx)
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
