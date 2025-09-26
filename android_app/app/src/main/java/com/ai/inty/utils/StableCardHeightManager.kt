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

    // 高度范围限制 - 放宽限制以保持瀑布流效果
    private val minHeightDp = 100f
    private val maxHeightDp = 600f

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
     * 优先使用缓存在AgentInfo中的高度，避免UI重组时的高度跳动
     */
    fun getStableCardHeightDp(agentInfo: AgentInfo): Float {
        // 如果AgentInfo中已经缓存了高度，直接使用
        if (agentInfo.cachedCardHeightDp > 0f) {
            EasyLog.log(
                "StableCardHeightManager - 使用缓存高度: ${agentInfo.cachedCardHeightDp} dp",
                EasyLog.DEBUG
            )
            return agentInfo.cachedCardHeightDp
        }

        // 计算新高度并缓存到AgentInfo中
        val calculatedHeight = calculateCardHeightDp(agentInfo)
        agentInfo.cachedCardHeightDp = calculatedHeight
        EasyLog.log(
            "StableCardHeightManager - 计算并缓存卡片高度: $calculatedHeight dp",
            EasyLog.DEBUG
        )
        return calculatedHeight
    }

    /**
     * 预计算并缓存AgentInfo的卡片高度
     * 只有在图片尺寸已缓存时才预计算，否则延迟到UI渲染时计算
     */
    fun preCalculateAndCacheHeight(agentInfo: AgentInfo) {
        if (agentInfo.cachedCardHeightDp <= 0f) {
            val imageUrl = agentInfo.getAlbumImage()

            // 只有当图片尺寸已经缓存时才预计算高度
            if (!imageUrl.isNullOrBlank() && imageSizeCache.get(imageUrl) != null) {
                val calculatedHeight = calculateCardHeightDp(agentInfo)
                agentInfo.cachedCardHeightDp = calculatedHeight
                EasyLog.log(
                    "StableCardHeightManager - 预计算卡片高度: ${agentInfo.name} -> $calculatedHeight dp",
                    EasyLog.DEBUG
                )
            } else {
                EasyLog.log(
                    "StableCardHeightManager - 图片尺寸未缓存，延迟计算: ${agentInfo.name}",
                    EasyLog.DEBUG
                )
            }
        }
    }

    /**
     * 批量预计算并缓存多个AgentInfo的卡片高度
     * 只有在图片尺寸已缓存时才预计算，保持瀑布流效果
     */
    fun preCalculateAndCacheHeights(agents: List<AgentInfo>) {
        var preCalculatedCount = 0
        var delayedCount = 0

        agents.forEach { agent ->
            val beforeHeight = agent.cachedCardHeightDp
            preCalculateAndCacheHeight(agent)

            if (agent.cachedCardHeightDp > beforeHeight) {
                preCalculatedCount++
            } else {
                delayedCount++
            }
        }

        EasyLog.log("StableCardHeightManager - 批量预计算完成: 预计算${preCalculatedCount}个, 延迟${delayedCount}个")
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
            EasyLog.log(
                "StableCardHeightManager - 预加载图片尺寸失败: $imageUrl, 错误: ${e.message}",
                EasyLog.WARN
            )
        }
    }


    /**
     * 计算卡片高度（dp）
     */
    private fun calculateCardHeightDp(agentInfo: AgentInfo): Float {
        val imageUrl = agentInfo.getAlbumImage()

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

        EasyLog.log(
            "StableCardHeightManager - 图片尺寸: ${imageWidth}x${imageHeight}, 宽高比: $originalAspectRatio, 卡片宽度: ${itemWidthPx}px, 计算高度: ${fillWidthHeightDp}dp",
            EasyLog.DEBUG
        )

        // 应用合理的高度限制，但不要过度限制，保持瀑布流效果
        return fillWidthHeightDp.coerceIn(minHeightDp, maxHeightDp)
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
     * 计算每个item的实际宽度（像素）
     */
    private fun getItemWidthPx(): Int {
        val contentPaddingPx = (contentPadding * 2 * density).toInt()
        val spacingPx = (horizontalSpacing * density).toInt()
        val availableWidth = screenWidth - contentPaddingPx - spacingPx
        return availableWidth / columnCount
    }


    /**
     * 清除缓存
     */
    fun clearCache() {
        imageSizeCache.evictAll()
        EasyLog.log("StableCardHeightManager - 清除缓存")
    }

}
