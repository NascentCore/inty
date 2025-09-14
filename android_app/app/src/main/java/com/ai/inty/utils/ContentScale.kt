package com.ai.inty.utils

import androidx.compose.ui.layout.ContentScale
import kotlin.math.abs

/**
 * 根据容器和图片的宽高比计算最佳的 ContentScale
 * 优先显示完整图片，避免裁剪重要内容。
 * 当图片尺寸未知时，使用 Fit 作为默认值以显示完整图片。
 * 
 * @param containerWidth 容器宽度（dp）
 * @param containerHeight 容器高度（dp）
 * @param imageWidth 图片宽度（像素）
 * @param imageHeight 图片高度（像素）
 * @return 最佳的 ContentScale
 */
fun calculateOptimalContentScale(
    containerWidth: Int,
    containerHeight: Int,
    imageWidth: Int?,
    imageHeight: Int?,
): ContentScale {
    // 图片可能还在加载中，使用 Fit 显示完整图片而不是裁剪
    if (imageWidth == null || imageHeight == null) {
        return ContentScale.Fit
    }
    
    val screenAspectRatio = containerWidth.toFloat() / containerHeight.toFloat()
    val imageAspectRatio = imageWidth.toFloat() / imageHeight.toFloat()
    
    return when {
        // 如果屏幕和图片宽高比接近（差异小于10%），使用 Fit 显示完整图片
        // 例如：屏幕 9:16 (0.5625)，图片 9:16 (0.5625) → 使用 Fit
        abs(screenAspectRatio - imageAspectRatio) / imageAspectRatio < 0.10f -> ContentScale.Fit
        
        // 如果屏幕比图片更宽（屏幕宽高比 > 图片宽高比），图片相对较窄，使用 FillWidth
        // 例如：屏幕 16:9 (1.78)，图片 9:16 (0.5625) → 使用 FillWidth
        screenAspectRatio > imageAspectRatio -> ContentScale.FillWidth
        
        // 如果屏幕比图片更窄（屏幕宽高比 < 图片宽高比），图片相对较宽，使用 FillHeight
        // 例如：屏幕 9:16 (0.5625)，图片 16:9 (1.78) → 使用 FillHeight
        else -> ContentScale.FillHeight
    }
}
