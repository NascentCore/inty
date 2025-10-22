package ai.sxwl.android.common

import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.Utils
import coil3.SingletonImageLoader
import coil3.request.ImageRequest
import coil3.size.Size
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

/**
 * 图片预加载助手
 * 提供业务相关的图片预加载方法，使用Coil3的SingletonImageLoader
 */
object ImagePreloadHelper {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    /**
     * 预加载单个图片
     * @param imageUrl 图片URL
     */
    private fun preloadImage(imageUrl: String?) {
        if (imageUrl.isNullOrBlank()) return

        scope.launch {
            try {
                val request = ImageRequest.Builder(Utils.getApp())
                    .data(imageUrl)
                    .size(Size.ORIGINAL)
                    .build()

                SingletonImageLoader.get(Utils.getApp()).enqueue(request)
//                LogUtils.d("预加载图片成功: $imageUrl")
            } catch (e: Exception) {
                LogUtils.e("预加载图片失败: $imageUrl", e)
            }
        }
    }

    /**
     * 预加载多个图片
     * @param imageUrls 图片URL列表
     */
    private fun preloadImages(imageUrls: List<String?>) {
        imageUrls.forEach { imageUrl ->
            preloadImage(imageUrl)
        }
    }

    /**
     * 预加载指定尺寸的图片
     * @param imageUrl 图片URL
     * @param width 宽度
     * @param height 高度
     */
    private fun preloadImageWithSize(imageUrl: String?, width: Int, height: Int) {
        if (imageUrl.isNullOrBlank()) return

        scope.launch {
            try {
                val request = ImageRequest.Builder(Utils.getApp())
                    .data(imageUrl)
                    .size(Size(width, height))
                    .build()

                SingletonImageLoader.get(Utils.getApp()).enqueue(request)
                LogUtils.d("预加载图片成功: $imageUrl (${width}x${height})")
            } catch (e: Exception) {
                LogUtils.e("预加载图片失败: $imageUrl", e)
            }
        }
    }

    /**
     * 预加载Agent相关图片
     * @param avatarUrl 头像URL
     * @param backgroundUrl 背景图片URL
     */
    fun preloadAgentImages(avatarUrl: String?, backgroundUrl: String?) {
        preloadImages(listOf(avatarUrl, backgroundUrl))
        LogUtils.d("预加载Agent图片: avatar=$avatarUrl, background=$backgroundUrl")
    }


    /**
     * 预加载用户头像
     * @param avatarUrl 头像URL
     */
    fun preloadUserAvatar(avatarUrl: String?) {
        preloadImage(avatarUrl)
        LogUtils.d("预加载用户头像: $avatarUrl")
    }


    /**
     * 预加载Agent头像（指定尺寸）
     * @param avatarUrl 头像URL
     * @param size 头像尺寸
     */
    fun preloadAgentAvatar(avatarUrl: String?, size: Int = 120) {
        preloadImageWithSize(avatarUrl, size, size)
        LogUtils.d("预加载Agent头像: $avatarUrl (${size}x${size})")
    }

    /**
     * 预加载Agent背景图片
     * @param backgroundUrl 背景图片URL
     * @param width 宽度
     * @param height 高度
     */
    fun preloadAgentBackground(backgroundUrl: String?, width: Int = 400, height: Int = 300) {
        preloadImageWithSize(backgroundUrl, width, height)
        LogUtils.d("预加载Agent背景: $backgroundUrl (${width}x${height})")
    }


    /**
     * 清理图片缓存
     */
    fun clearImageCache() {
        try {
            SingletonImageLoader.get(Utils.getApp()).memoryCache?.clear()
            SingletonImageLoader.get(Utils.getApp()).diskCache?.clear()
            LogUtils.d("清理图片缓存成功")
        } catch (e: Exception) {
            LogUtils.e("清理图片缓存失败", e)
        }
    }

    /**
     * 获取图片缓存大小
     * @return 格式化的缓存大小字符串
     */
    fun getImageCacheSize(): String {
        return try {
            val memorySize = SingletonImageLoader.get(Utils.getApp()).memoryCache?.size ?: 0
            val diskSize = SingletonImageLoader.get(Utils.getApp()).diskCache?.size ?: 0
            val totalSize = memorySize + diskSize
            formatCacheSize(totalSize)
        } catch (e: Exception) {
            "0 B"
        }
    }

    /**
     * 格式化缓存大小
     */
    private fun formatCacheSize(bytes: Long): String {
        val units = arrayOf("B", "KB", "MB", "GB")
        var size = bytes.toDouble()
        var unitIndex = 0

        while (size >= 1024 && unitIndex < units.size - 1) {
            size /= 1024
            unitIndex++
        }

        return "%.1f %s".format(size, units[unitIndex])
    }
}
