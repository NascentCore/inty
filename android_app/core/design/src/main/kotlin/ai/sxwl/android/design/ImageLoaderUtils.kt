package ai.sxwl.android.design

import android.content.Context
import androidx.annotation.DrawableRes
import coil3.request.ImageRequest
import coil3.request.crossfade
import coil3.request.error
import coil3.request.placeholder
import coil3.size.Size
import java.io.File

/**
 * 图片加载工具类
 * 根据Coil 3.x官方文档优化，专门处理大图片加载的优化策略
 */
object ImageLoaderUtils {

    /**
     * 创建设备适配的图片请求
     * 根据设备屏幕密度和尺寸自动压缩图片，提供最佳性能
     * 参考：https://coil-kt.github.io/coil/
     * @param context 上下文
     * @param imageUrl 图片URL
     * @param placeholder 占位图资源ID
     * @param error 错误图资源ID
     * @param maxWidth 最大宽度，null表示使用屏幕宽度
     * @param maxHeight 最大高度，null表示使用屏幕高度
     * @return 优化后的ImageRequest
     */
    fun createDeviceAdaptiveImageRequest(
        context: Context,
        imageUrl: String?,
        @DrawableRes placeholder: Int = R.drawable.img_girl_lite,
        @DrawableRes error: Int = R.drawable.img_girl_lite,
        maxWidth: Int? = null,
        maxHeight: Int? = null
    ): ImageRequest {
        val displayMetrics = context.resources.displayMetrics
        val screenWidth = maxWidth ?: displayMetrics.widthPixels
        val screenHeight = maxHeight ?: displayMetrics.heightPixels

        // 根据屏幕密度调整目标尺寸，确保图片清晰度
        val density = displayMetrics.density
        val targetWidth = (screenWidth * density).toInt()
        val targetHeight = (screenHeight * density).toInt()

        return ImageRequest.Builder(context)
            .data(imageUrl)
            .size(Size(targetWidth, targetHeight)) // 设备适配的尺寸
            .crossfade(true)
            .crossfade(300) // 300ms的交叉淡入淡出
            .placeholder(placeholder)
            .error(error)
            .build()
    }

    /**
     * 创建针对大图片优化的ImageRequest
     * 根据官方文档：https://coil-kt.github.io/coil/network/
     * @param context 上下文
     * @param imageUrl 图片URL
     * @param placeholder 占位图资源ID
     * @param error 错误图资源ID
     * @return 优化后的ImageRequest
     */
    fun createLargeImageRequest(
        context: Context,
        imageUrl: String?,
        @DrawableRes placeholder: Int = R.drawable.img_girl_lite,
        @DrawableRes error: Int = R.drawable.img_girl_lite
    ): ImageRequest {
        return ImageRequest.Builder(context)
            .data(imageUrl)
            .size(Size.ORIGINAL) // 使用原始尺寸，让Coil自动处理
            .crossfade(true)
            .crossfade(300) // 300ms的交叉淡入淡出
            .placeholder(placeholder)
            .error(error)
            .build()
    }

    /**
     * 创建针对头像优化的ImageRequest
     * @param context 上下文
     * @param imageUrl 图片URL
     * @param size 目标尺寸
     * @return 优化后的ImageRequest
     */
    fun createAvatarImageRequest(
        context: Context,
        imageUrl: String?,
        size: Int = 120
    ): ImageRequest {
        return ImageRequest.Builder(context)
            .data(imageUrl)
            .size(Size(size, size)) // 固定尺寸
            .crossfade(true)
            .crossfade(200) // 200ms的交叉淡入淡出
            .build()
    }

    /**
     * 创建针对缩略图优化的ImageRequest
     * @param context 上下文
     * @param imageUrl 图片URL
     * @param width 宽度
     * @param height 高度
     * @return 优化后的ImageRequest
     */
    fun createThumbnailImageRequest(
        context: Context,
        imageUrl: String?,
        width: Int = 300,
        height: Int = 200
    ): ImageRequest {
        return ImageRequest.Builder(context)
            .data(imageUrl)
            .size(Size(width, height)) // 固定尺寸
            .crossfade(true)
            .crossfade(150) // 150ms的交叉淡入淡出
            .build()
    }

    /**
     * 创建针对大图片的渐进式加载ImageRequest
     * 适用于网络较慢的情况
     * @param context 上下文
     * @param imageUrl 图片URL
     * @param placeholder 占位图
     * @param error 错误图
     * @return 优化后的ImageRequest
     */
    fun createProgressiveImageRequest(
        context: Context,
        imageUrl: String?,
        @DrawableRes placeholder: Int = R.drawable.img_girl_lite,
        @DrawableRes error: Int = R.drawable.img_girl_lite
    ): ImageRequest {
        return ImageRequest.Builder(context)
            .data(imageUrl)
            .size(Size.ORIGINAL)
            .crossfade(true)
            .crossfade(500) // 更长的交叉淡入淡出时间
            .placeholder(placeholder)
            .error(error)
            .build()
    }

    /**
     * 检查图片URL是否有效
     * @param imageUrl 图片URL
     * @return 是否有效
     */
    fun isValidImageUrl(imageUrl: String?): Boolean {
        return !imageUrl.isNullOrBlank() &&
                (imageUrl.startsWith("http://") ||
                        imageUrl.startsWith("https://") ||
                        imageUrl.startsWith("file://") ||
                        imageUrl.startsWith("content://"))
    }

    /**
     * 获取图片文件大小（如果可能）
     * @param imageUrl 图片URL
     * @return 文件大小（字节），如果无法获取则返回null
     */
    fun getImageFileSize(imageUrl: String?): Long? {
        return try {
            if (imageUrl?.startsWith("file://") == true) {
                val file = File(imageUrl.substring(7))
                if (file.exists()) file.length() else null
            } else {
                null
            }
        } catch (e: Exception) {
            null
        }
    }

    /**
     * 检查是否为超大图片（超过5MB）
     * @param imageUrl 图片URL
     * @return 是否为超大图片
     */
    fun isLargeImage(imageUrl: String?): Boolean {
        val fileSize = getImageFileSize(imageUrl)
        return fileSize != null && fileSize > 5 * 1024 * 1024 // 5MB
    }

    /**
     * 检查是否为超大图片（超过10MB）
     * @param imageUrl 图片URL
     * @return 是否为超大图片
     */
    fun isVeryLargeImage(imageUrl: String?): Boolean {
        val fileSize = getImageFileSize(imageUrl)
        return fileSize != null && fileSize > 10 * 1024 * 1024 // 10MB
    }
}
