package com.ai.inty.utils

import android.content.Context
import android.graphics.BitmapFactory
import android.graphics.Point
import android.util.LruCache
import com.ai.inty.beans.AgentInfo
import com.inty.utils.log.EasyLog
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.net.URL

/**
 * 稳定的卡片高度管理器
 * 在卡片渲染后记录实际尺寸，确保UI复用时不会跳动
 */
object StableCardHeightManager {
    
    // 缓存图片的实际尺寸
    private val imageSizeCache = LruCache<String, Point>(100)
    
    // 屏幕相关参数
    private var screenWidth = 0
    private var density = 1f
    private val contentPadding = 16f // dp - 对应 LazyList 的 contentPadding
    private val horizontalSpacing = 6f // dp - 对应 LazyList 的 horizontalArrangement.spacedBy
    private val columnCount = 2 // 对应 StaggeredGridCells.Fixed(2)
    
    // 高度范围限制
    private val minHeightDp = 120f
    private val maxHeightDp = 450f
    
    /**
     * 初始化管理器
     */
    fun init(context: Context) {
        try {
            val displayMetrics = context.resources.displayMetrics
            screenWidth = displayMetrics.widthPixels
            density = displayMetrics.density
            
            EasyLog.log("StableCardHeightManager - 初始化完成, 屏幕宽度: $screenWidth, 密度: $density")
        } catch (e: Exception) {
            EasyLog.log("StableCardHeightManager - 初始化失败: ${e.message}", EasyLog.ERROR)
            // 设置默认值
            screenWidth = 1080
            density = 3.0f
        }
    }
    
    /**
     * 获取卡片的稳定高度（dp）
     * 基于图片真实比例计算，确保瀑布流效果
     */
    fun getStableCardHeightDp(agentInfo: AgentInfo): Float {
        val calculatedHeight = calculateCardHeightDp(agentInfo)
        EasyLog.log("StableCardHeightManager - 计算卡片高度: $calculatedHeight dp", EasyLog.DEBUG)
        return calculatedHeight
    }
    
    /**
     * 获取图片的显示高度（像素）
     * 直接返回像素值，避免dp转换的精度问题
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
        val cachedSize = imageSizeCache.get(imageUrl)
        if (cachedSize != null) {
            return calculateDisplayHeightPx(cachedSize.x, cachedSize.y)
        }
        
        // 如果缓存中没有，使用默认高度
        return getDefaultHeightPx()
    }
    
    /**
     * 预加载图片尺寸，用于更准确的高度计算
     */
    suspend fun preloadImageSize(imageUrl: String) {
        if (imageUrl.isBlank()) return
        
        // 如果已经缓存，直接返回
        if (imageSizeCache.get(imageUrl) != null) return
        
        try {
            withContext(Dispatchers.IO) {
                val url = URL(imageUrl)
                val connection = url.openConnection()
                connection.connectTimeout = 5000
                connection.readTimeout = 5000
                
                val inputStream = connection.getInputStream()
                val options = BitmapFactory.Options().apply {
                    inJustDecodeBounds = true
                }
                BitmapFactory.decodeStream(inputStream, null, options)
                inputStream.close()
                
                if (options.outWidth > 0 && options.outHeight > 0) {
                    val size = Point(options.outWidth, options.outHeight)
                    imageSizeCache.put(imageUrl, size)
                    EasyLog.log("StableCardHeightManager - 预加载图片尺寸: $imageUrl -> ${size.x}x${size.y}")
                }
            }
        } catch (e: Exception) {
            EasyLog.log("StableCardHeightManager - 预加载图片尺寸失败: $imageUrl, 错误: ${e.message}", EasyLog.WARN)
        }
    }
    
    /**
     * 批量预加载图片尺寸
     */
    suspend fun preloadImageSizes(imageUrls: List<String>) {
        imageUrls.forEach { url ->
            preloadImageSize(url)
        }
    }
    
    /**
     * 计算卡片高度（dp）
     */
    private fun calculateCardHeightDp(agentInfo: AgentInfo): Float {
        val imageUrl = AvatarManager.getChatBackgroundForAgent(agentInfo)
        
        if (imageUrl.isNullOrBlank()) {
            return getDefaultHeightDp()
        }
        
        // 从缓存中获取图片尺寸
        val imageSize = imageSizeCache.get(imageUrl)
        if (imageSize != null) {
            return calculateHeightFromImageSize(imageSize.x, imageSize.y)
        }
        
        // 如果没有缓存，使用默认高度
        return getDefaultHeightDp()
    }
    
    /**
     * 根据图片尺寸计算高度
     * 基于图片真实比例，确保瀑布流效果
     */
    private fun calculateHeightFromImageSize(imageWidth: Int, imageHeight: Int): Float {
        if (imageWidth <= 0 || imageHeight <= 0) {
            return getDefaultHeightDp()
        }
        
        val originalAspectRatio = imageWidth.toFloat() / imageHeight.toFloat()
        val itemWidthPx = getItemWidthPx()
        
        // 模拟 FillWidth 模式：图片宽度填满容器，高度按比例缩放
        val fillWidthHeightPx = itemWidthPx / originalAspectRatio
        val fillWidthHeightDp = fillWidthHeightPx / density
        
        EasyLog.log("StableCardHeightManager - 图片尺寸: ${imageWidth}x${imageHeight}, 宽高比: $originalAspectRatio, 卡片宽度: ${itemWidthPx}px, 计算高度: ${fillWidthHeightDp}dp", EasyLog.DEBUG)
        
        // 应用合理的高度限制，但不要过度限制，保持瀑布流效果
        return fillWidthHeightDp.coerceIn(minHeightDp, maxHeightDp)
    }
    
    /**
     * 根据图片尺寸计算显示高度（像素）
     * 直接返回像素值，避免dp转换的精度问题
     */
    private fun calculateDisplayHeightPx(imageWidth: Int, imageHeight: Int): Int {
        if (imageWidth <= 0 || imageHeight <= 0) {
            return getDefaultHeightPx()
        }
        
        val originalAspectRatio = imageWidth.toFloat() / imageHeight.toFloat()
        
        // 限制宽高比在合理范围内，避免极端比例
        val minAspectRatio = 9f / 16f // 9:16 (更窄，高度更高)
        val maxAspectRatio = 3f / 4f  // 3:4 (更宽，高度更低)
        val clampedAspectRatio = originalAspectRatio.coerceIn(minAspectRatio, maxAspectRatio)
        
        // 计算显示高度
        val itemWidthPx = getItemWidthPx()
        val displayHeightPx = (itemWidthPx / clampedAspectRatio).toInt()
        
        // 限制高度范围，避免过高或过低
        val minHeightPx = (minHeightDp * density).toInt()
        val maxHeightPx = (maxHeightDp * density).toInt()
        
        return displayHeightPx.coerceIn(minHeightPx, maxHeightPx)
    }
    
    /**
     * 获取默认高度（dp）
     */
    private fun getDefaultHeightDp(): Float {
        val itemWidthPx = getItemWidthPx()
        val defaultAspectRatio = 3f / 4f
        val defaultHeightPx = itemWidthPx / defaultAspectRatio
        val defaultHeightDp = defaultHeightPx / density
        
        return defaultHeightDp.coerceIn(minHeightDp, maxHeightDp)
    }
    
    /**
     * 获取默认高度（像素）
     */
    private fun getDefaultHeightPx(): Int {
        val itemWidthPx = getItemWidthPx()
        // 使用默认宽高比 4:5 计算默认高度
        val defaultAspectRatio = 4f / 5f
        return (itemWidthPx / defaultAspectRatio).toInt()
    }
    
    /**
     * 计算每个item的实际宽度（像素）
     */
    private fun getItemWidthPx(): Int {
        val contentPaddingPx = (contentPadding * 2 * density).toInt()
        val spacingPx = (horizontalSpacing * density).toInt()
        val availableWidth = screenWidth - contentPaddingPx - spacingPx
        return availableWidth / columnCount
    }
    
    /**
     * 生成缓存键
     */
    private fun generateCacheKey(agentInfo: AgentInfo): String {
        val imageUrl = AvatarManager.getChatBackgroundForAgent(agentInfo)
        return "${agentInfo.id}_${imageUrl}"
    }
    
    /**
     * 清除缓存
     */
    fun clearCache() {
        imageSizeCache.evictAll()
        EasyLog.log("StableCardHeightManager - 清除缓存")
    }
    
    /**
     * 获取缓存统计信息
     */
    fun getCacheStats(): String {
        return "图片尺寸缓存: ${imageSizeCache.size()}"
    }
}
