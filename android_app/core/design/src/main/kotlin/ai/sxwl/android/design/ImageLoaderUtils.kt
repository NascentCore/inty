package ai.sxwl.android.design

import android.content.Context
import androidx.annotation.DrawableRes
import coil3.request.ImageRequest
import coil3.request.crossfade
import coil3.request.error
import coil3.request.placeholder
import coil3.size.Size
import java.io.File

/** 图片加载工具类 根据Coil 3.x官方文档优化，专门处理大图片加载的优化策略 */
object ImageLoaderUtils {

    /**
     * 创建设备适配的图片请求 根据设备屏幕密度和尺寸自动压缩图片，提供最佳性能 参考：https://coil-kt.github.io/coil/
     *
     * @param context 上下文
     * @param imageUrl 图片URL
     * @param placeholder 占位图资源ID，null表示不设置占位图
     * @param error 错误图资源ID，null表示不设置错误图
     * @param maxWidth 最大宽度，null表示使用屏幕宽度
     * @param maxHeight 最大高度，null表示使用屏幕高度
     * @return 优化后的ImageRequest
     */
    fun createDeviceAdaptiveImageRequest(
        context: Context,
        imageUrl: String?,
        @DrawableRes placeholder: Int? = null,
        @DrawableRes error: Int? = null,
        maxWidth: Int? = null,
        maxHeight: Int? = null,
    ): ImageRequest {
        val displayMetrics = context.resources.displayMetrics
        val screenWidth = maxWidth ?: displayMetrics.widthPixels
        val screenHeight = maxHeight ?: displayMetrics.heightPixels

        // 直接使用像素单位的屏幕尺寸，避免重复乘密度
        val targetWidth = screenWidth
        val targetHeight = screenHeight

        val builder =
            ImageRequest.Builder(context)
                .data(imageUrl)
                .size(Size(targetWidth, targetHeight)) // 设备适配的尺寸
                .crossfade(true)
                .crossfade(300) // 300ms的交叉淡入淡出

        // 只有在明确传入时才设置 placeholder 和 error
        placeholder?.let { builder.placeholder(it) }
        error?.let { builder.error(it) }

        return builder.build()
    }
}
